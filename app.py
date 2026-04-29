import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURASI HALAMAN ---
# Mengubah judul tab browser sesuai permintaan
st.set_page_config(page_title="SRS - LOVE DREAM PASSION", page_icon="🎫", layout="wide")

# --- 2. LOGIKA PENDAKIAN REFRESH ---
if "is_inputting" not in st.session_state:
    st.session_state.is_inputting = False

if not st.session_state.is_inputting:
    st_autorefresh(interval=5000, limit=None, key="srs_refresh")

# --- 3. PREMIUM UI STYLING ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, .stApp { font-family: 'Inter', sans-serif; }
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
.srs-card { background: rgba(30, 41, 59, 0.5); border-radius: 15px; padding: 20px 15px; border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; text-align: center; height: 100%; }
.srs-card.active { border-bottom: 5px solid #10B981; }
.srs-card.empty { border-bottom: 5px solid #475569; opacity: 0.8; }
.c-jalur { font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
.c-member { font-weight: 800; font-size: 18px; color: #f8fafc; margin-bottom: 15px; }
.c-users { font-size: 13px; font-weight: 600; padding: 10px; border-radius: 12px; margin-top: auto; line-height: 1.4; }
.srs-card.active .c-users { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.2); }
.srs-card.empty .c-users { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
.live-badge { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 12px; color: #10B981; background: rgba(16,185,129,0.1); padding: 5px 15px; border-radius: 30px; border: 1px solid rgba(16,185,129,0.2); }
.live-dot { height: 8px; width: 8px; background: #10B981; border-radius: 50%; animation: blink 2s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.2); } }
.user-count { display: block; font-size: 11px; margin-bottom: 4px; text-transform: uppercase; font-weight: 800;}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- 4. KONEKSI DATABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
    db_connected = True
except:
    db_connected = False

# --- 5. FUNGSI API ---
@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        records = []
        for sesi in data.get('data', []):
            sesi_nama = sesi.get('label', 'TBA')
            for m in sesi.get('session_members', []):
                records.append({'sesi': sesi_nama, 'nama_member': m.get('member_name', 'TBA'), 'jalur': m.get('label', 'TBA')})
        return pd.DataFrame(records).drop_duplicates()
    except:
        return pd.DataFrame()

API_URLS = {"2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id", "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"}

# --- 6. FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
    st.write("Timer auto-refresh dimatikan sementara agar input tidak terganggu.")
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)")
    tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
    df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
    
    if not df_api.empty:
        list_member = sorted(df_api['nama_member'].unique().tolist())
        pilihan_member = st.selectbox("Pilih Member:", list_member)
        df_member = df_api[df_api['nama_member'] == pilihan_member]
        pilihan_sesi = st.selectbox("Pilih Sesi:", sorted(df_member['sesi'].unique().tolist()))
        df_sesi = df_member[df_member['sesi'] == pilihan_sesi]
        pilihan_jalur = st.selectbox("Pilih Jalur / Bilik:", sorted(df_sesi['jalur'].unique().tolist()))
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Simpan Jadwal", type="primary", use_container_width=True):
                if nama_user and db_connected:
                    supabase.table("srs_schedule").insert({"name": nama_user, "type": tipe_tiket, "member": pilihan_member, "sesi": pilihan_sesi, "jalur": pilihan_jalur}).execute()
                    st.session_state.is_inputting = False 
                    st.success("Tersimpan!")
                    st.rerun()
        with c2:
            if st.button("Batal / Tutup", use_container_width=True):
                st.session_state.is_inputting = False 
                st.rerun()
    else:
        if st.button("Batal"):
            st.session_state.is_inputting = False
            st.rerun()

# --- 7. UI UTAMA ---
col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.subheader("Meet & Greet Festival: LOVE DREAM PASSION")
    if not st.session_state.is_inputting:
        st.markdown('<div class="live-badge"><span class="live-dot"></span> LIVE UPDATE ON (5s)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="live-badge" style="color:#FBBF24; background:rgba(251,191,36,0.1); border-color:rgba(251,191,36,0.2);"><span class="live-dot" style="background:#FBBF24;"></span> PAUSED FOR INPUT</div>', unsafe_allow_html=True)

with col_btn:
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        st.session_state.is_inputting = True 
        form_input_srs()

st.divider()

# --- 8. RENDER GRID ---
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
        st.error("API Down.")
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
            
            # BUG FIX: Menambahkan <br/> agar spasi antara jumlah orang dan nama menjadi rapi
            html += f'<div class="srs-card {card_class}"><div class="c-jalur">{jalur}</div><div class="c-member">{member}</div><div class="c-users"><span class="user-count">👥 {count} ORANG</span><br/>{users_str}</div></div>'
            
        st.markdown(html + '</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📸 2-Shot", "🤝 Meet & Greet"])
with tab1: render_grid_section("2-Shot")
with tab2: render_grid_section("Meet & Greet")