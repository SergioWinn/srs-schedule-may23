import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS M&G Coordinator", page_icon="🎫", layout="wide")

# --- 2. AUTO-REFRESH (Setiap 10 Detik) ---
# key="srs_refresh" agar Streamlit tahu ini timer utama
count = st_autorefresh(interval=10000, limit=None, key="srs_refresh")

# --- 3. PREMIUM UI STYLING (LDP STYLE) ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, .stApp { font-family: 'Inter', sans-serif; }

/* Grid System */
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }

/* Card Design */
.srs-card { 
    background: rgba(30, 41, 59, 0.5); 
    border-radius: 15px; 
    padding: 20px 15px; 
    border: 1px solid rgba(255,255,255,0.1); 
    display: flex; 
    flex-direction: column; 
    text-align: center; 
    transition: 0.3s ease;
    height: 100%;
}
.srs-card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.2); }

/* Card Status Border */
.srs-card.active { border-bottom: 5px solid #10B981; }
.srs-card.empty { border-bottom: 5px solid #475569; opacity: 0.8; }

/* Typography inside Card */
.c-jalur { font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 1px; }
.c-member { font-weight: 800; font-size: 18px; color: #f8fafc; margin-bottom: 15px; line-height: 1.2; }

/* Badge untuk daftar nama */
.c-users { 
    font-size: 13px; 
    font-weight: 600; 
    padding: 10px; 
    border-radius: 12px; 
    margin-top: auto;
}
.srs-card.active .c-users { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.2); }
.srs-card.empty .c-users { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }

.user-count { display: block; font-size: 11px; margin-bottom: 3px; text-transform: uppercase; font-weight: 800;}

/* Live Badge Indicator */
.live-badge { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 12px; color: #10B981; background: rgba(16,185,129,0.1); padding: 5px 15px; border-radius: 30px; border: 1px solid rgba(16,185,129,0.2); margin-top: 10px;}
.live-dot { height: 8px; width: 8px; background: #10B981; border-radius: 50%; animation: blink 2s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.2); } }

@media (max-width: 500px) { 
    .cards-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; } 
    .srs-card { padding: 15px 10px; }
    .c-member { font-size: 15px; }
    .c-users { font-size: 11px; padding: 8px;}
}
</style>
"""
st.markdown(css.replace('\n', '').replace('\r', ''), unsafe_allow_html=True)

# --- 4. KONEKSI DATABASE (SUPABASE) ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
    db_connected = True
except Exception as e:
    db_connected = False

# --- 5. FUNGSI AMBIL DATA API JKT48 ---
@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        records = []
        for sesi in data.get('data', []):
            sesi_nama = sesi.get('label', 'TBA')
            members = sesi.get('session_members', [])
            
            for m in members:
                member_nama = m.get('member_name', 'TBA')
                jalur_nama = m.get('label', 'TBA')
                records.append({
                    'sesi': sesi_nama,
                    'nama_member': member_nama,
                    'jalur': jalur_nama
                })
                
        if not records:
            return pd.DataFrame()
            
        return pd.DataFrame(records).drop_duplicates()
    except Exception as e:
        return pd.DataFrame()

API_URLS = {
    "2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id",
    "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"
}

# --- 6. FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
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
        
        if st.button("Simpan Jadwal", type="primary", use_container_width=True):
            if nama_user and db_connected:
                supabase.table("srs_schedule").insert({
                    "name": nama_user, 
                    "type": tipe_tiket,
                    "member": pilihan_member, 
                    "sesi": pilihan_sesi, 
                    "jalur": pilihan_jalur
                }).execute()
                st.success("Tersimpan!")
                st.rerun()
    else:
        st.warning("Gagal load API. Gunakan input manual.")
        m_manual = st.text_input("Member (Manual)")
        s_manual = st.text_input("Sesi (Manual)")
        j_manual = st.text_input("Jalur (Manual)")
        if st.button("Simpan Manual") and db_connected:
            supabase.table("srs_schedule").insert({
                "name": nama_user, 
                "type": tipe_tiket,
                "member": m_manual, 
                "sesi": s_manual, 
                "jalur": j_manual
            }).execute()
            st.rerun()

# --- 7. UI UTAMA (HEADER SIMPEL) ---
col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.subheader("Personal Meet and Greet Festival: LOVE DREAM PASSION")
    st.markdown('<div class="live-badge"><span class="live-dot"></span> LIVE UPDATE ON</div>', unsafe_allow_html=True)
with col_btn:
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- 8. RENDER GRID ---
def render_grid_section(tipe):
    df_master = fetch_jkt48_api(API_URLS[tipe])
    
    df_user = pd.DataFrame()
    if db_connected:
        # PERBAIKAN: Supaya data yang ditarik selalu fresh tiap kali refresh (bukan dari cache browser)
        res = supabase.table("srs_schedule").select("*").eq("type", tipe).execute()
        if res.data:
            df_user = pd.DataFrame(res.data)
            df_user = df_user.rename(columns={"name": "nama_user", "member": "nama_member"})

    if not df_master.empty:
        if not df_user.empty:
            grouped_user = df_user.groupby(['sesi', 'nama_member', 'jalur'])['nama_user'].apply(list).reset_index()
            df_final = pd.merge(df_master, grouped_user, on=['sesi', 'nama_member', 'jalur'], how='left')
        else:
            df_final = df_master.copy()
            df_final['nama_user'] = None
    else:
        st.error("API JKT48 sedang down. Tidak bisa memuat Master Timetable.")
        return

    df_final['nama_user'] = df_final['nama_user'].apply(lambda x: x if isinstance(x, list) else [])

    search_query = st.text_input(f"🔍 Cari Sesi / Member / Anak SRS di {tipe}...", key=f"search_{tipe}")
    if search_query:
        mask = df_final.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df_final = df_final[mask]

    sesi_list = sorted(df_final['sesi'].unique().tolist())
    
    for sesi in sesi_list:
        st.markdown(f"#### {sesi}")
        df_sesi = df_final[df_final['sesi'] == sesi]
        
        html = '<div class="cards-grid">'
        for _, row in df_sesi.iterrows():
            member = row['nama_member']
            jalur = row['jalur']
            users_list = row['nama_user']
            count = len(users_list)
            
            if count > 0:
                card_class = "active"
                users_str = ", ".join(users_list)
            else:
                card_class = "empty"
                users_str = "Belum ada anak SRS"
            
            html += f'<div class="srs-card {card_class}">'
            html += f'<div class="c-jalur">{jalur}</div>'
            html += f'<div class="c-member">{member}</div>'
            html += f'<div class="c-users"><span class="user-count">👥 {count} ORANG</span>{users_str}</div>'
            html += '</div>'
            
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

# --- 9. TABS ---
tab1, tab2 = st.tabs(["📸 2-Shot", "🤝 Meet & Greet"])
with tab1:
    render_grid_section("2-Shot")
with tab2:
    render_grid_section("Meet & Greet")