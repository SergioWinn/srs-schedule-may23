import streamlit as st
import pandas as pd
import requests
from supabase import create_client

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS - LOVE DREAM PASSION", page_icon="🎫", layout="wide")

# --- 2. PREMIUM UI STYLING ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, .stApp { font-family: 'Inter', sans-serif; }
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
.srs-card { background: rgba(30, 41, 59, 0.5); border-radius: 15px; padding: 20px 15px; border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; text-align: center; height: 100%; border-bottom: 5px solid #475569; }
.srs-card.active { border-bottom: 5px solid #10B981; }
.c-jalur { font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
.c-member { font-weight: 800; font-size: 18px; color: #f8fafc; margin-bottom: 15px; }
.c-users { padding: 10px; border-radius: 12px; margin-top: auto; display: flex; flex-direction: column; gap: 4px; }
.srs-card.active .c-users { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.2); }
.srs-card.empty .c-users { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
.user-count { font-size: 11px; text-transform: uppercase; font-weight: 800; }
.user-names { font-size: 13px; font-weight: 600; }
.live-badge { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 12px; color: #10B981; background: rgba(16,185,129,0.1); padding: 5px 15px; border-radius: 30px; border: 1px solid rgba(16,185,129,0.2); }
.live-dot { height: 8px; width: 8px; background: #10B981; border-radius: 50%; animation: blink 2s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.2); } }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- 3. KONEKSI & API ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_connection()
    db_connected = True
except:
    db_connected = False

@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = response.json()
        records = []
        for sesi in data.get('data', []):
            s_nama = sesi.get('label', 'TBA')
            for m in sesi.get('session_members', []):
                records.append({'sesi': s_nama, 'nama_member': m.get('member_name', 'TBA'), 'jalur': m.get('label', 'TBA')})
        return pd.DataFrame(records).drop_duplicates()
    except: return pd.DataFrame()

API_URLS = {"2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id", "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"}

# --- 4. FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)")
    tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
    df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
    
    if not df_api.empty:
        p_member = st.selectbox("Pilih Member:", sorted(df_api['nama_member'].unique().tolist()))
        df_m = df_api[df_api['nama_member'] == p_member]
        p_sesi = st.selectbox("Pilih Sesi:", sorted(df_m['sesi'].unique().tolist()))
        p_jalur = st.selectbox("Pilih Jalur:", sorted(df_m[df_m['sesi'] == p_sesi]['jalur'].unique().tolist()))
        
        if st.button("Simpan Jadwal", type="primary", use_container_width=True):
            if nama_user and db_connected:
                supabase.table("srs_schedule").insert({
                    "name": nama_user, 
                    "type": tipe_tiket, 
                    "member": p_member, 
                    "sesi": p_sesi, 
                    "jalur": p_jalur
                }).execute()
                st.rerun()
    else:
        st.warning("API JKT48 sedang down.")

# --- 5. UI UTAMA ---
col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.subheader("Meet & Greet Festival: LOVE DREAM PASSION")
    st.markdown('<div class="live-badge"><span class="live-dot"></span> REAL-TIME REKAP</div>', unsafe_allow_html=True)

with col_btn:
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- 6. RENDER GRID DENGAN FRAGMENT ---
@st.fragment(run_every=5)
def render_realtime_dashboard():
    tab1, tab2 = st.tabs(["📸 2-Shot", "🤝 Meet & Greet"])
    
    with tab1:
        render_grid_section("2-Shot")
    with tab2:
        render_grid_section("Meet & Greet")

def render_grid_section(tipe):
    df_master = fetch_jkt48_api(API_URLS[tipe])
    df_user = pd.DataFrame()
    if db_connected:
        res = supabase.table("srs_schedule").select("*").eq("type", tipe).execute()
        if res.data:
            df_user = pd.DataFrame(res.data).rename(columns={"name": "nama_user", "member": "nama_member"})

    if not df_master.empty:
        if not df_user.empty:
            grouped_user = df_user.groupby(['sesi', 'nama_member', 'jalur'])['nama_user'].apply(list).reset_index()
            df_final = pd.merge(df_master, grouped_user, on=['sesi', 'nama_member', 'jalur'], how='left')
        else:
            df_final = df_master.copy()
            df_final['nama_user'] = None
    else:
        return

    df_final['nama_user'] = df_final['nama_user'].apply(lambda x: x if isinstance(x, list) else [])
    
    search_query = st.text_input(f"🔍 Cari Sesi / Member / Anak SRS di {tipe}...", key=f"search_{tipe}")
    if search_query:
        mask = df_final.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df_final = df_final[mask]

    for sesi in sorted(df_final['sesi'].unique().tolist()):
        st.markdown(f"#### {sesi}")
        df_sesi = df_final[df_final['sesi'] == sesi]
        html = '<div class="cards-grid">'
        for _, row in df_sesi.iterrows():
            member, jalur, users_list = row['nama_member'], row['jalur'], row['nama_user']
            count = len(users_list)
            card_class, users_str = ("active", ", ".join(users_list)) if count > 0 else ("empty", "Belum ada anak SRS")
            html += f'<div class="srs-card {card_class}"><div class="c-jalur">{jalur}</div><div class="c-member">{member}</div><div class="c-users"><div class="user-count">👥 {count} ORANG</div><div class="user-names">{users_str}</div></div></div>'
        st.markdown(html + '</div>', unsafe_allow_html=True)

# Panggil fungsi fragment
render_realtime_dashboard()