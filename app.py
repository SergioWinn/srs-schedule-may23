import streamlit as st
import pandas as pd
import requests
from supabase import create_client

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS M&G Coordinator", page_icon="🎫", layout="wide")

# --- 2. PREMIUM UI STYLING (LDP STYLE) ---
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
    border-bottom: 5px solid #10B981; 
    display: flex; 
    flex-direction: column; 
    text-align: center; 
    transition: 0.3s ease;
    height: 100%;
}
.srs-card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.2); border-color: rgba(16,185,129,0.5); }

/* Typography inside Card */
.c-jalur { font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 1px; }
.c-member { font-weight: 800; font-size: 18px; color: #f8fafc; margin-bottom: 15px; line-height: 1.2; }

/* Badge untuk daftar nama */
.c-users { 
    font-size: 13px; 
    font-weight: 600; 
    color: #f59e0b; 
    background: rgba(245, 158, 11, 0.1); 
    padding: 10px; 
    border-radius: 12px; 
    margin-top: auto; /* Push to bottom */
    border: 1px solid rgba(245, 158, 11, 0.2);
}
.user-count { display: block; font-size: 11px; color: #10B981; margin-bottom: 3px; text-transform: uppercase; font-weight: 800;}

/* Mobile optimization */
@media (max-width: 500px) { 
    .cards-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; } 
    .srs-card { padding: 15px 10px; }
    .c-member { font-size: 15px; }
    .c-users { font-size: 11px; padding: 8px;}
}
</style>
"""
st.markdown(css.replace('\n', '').replace('\r', ''), unsafe_allow_html=True)

# --- 3. KONEKSI DATABASE (SUPABASE) ---
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

# --- 4. FUNGSI AMBIL DATA API JKT48 ---
@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        items = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    items = value; break
        elif isinstance(data, list): items = data
            
        if not items: return pd.DataFrame()
        df = pd.DataFrame(items)
        
        mapping = {}
        cols = df.columns.tolist()
        for c in ['name', 'member_name', 'memberName', 'member']:
            if c in cols: mapping[c] = 'member'; break
        for c in ['session', 'session_name', 'sessionName', 'bonus_session']:
            if c in cols: mapping[c] = 'session'; break
        for c in ['lane', 'lane_name', 'laneName', 'bonus_lane']:
            if c in cols: mapping[c] = 'lane'; break

        df = df.rename(columns=mapping)
        for col in ['member', 'session', 'lane']:
            if col not in df.columns: df[col] = "TBA"
        return df[['member', 'session', 'lane']].drop_duplicates()
    except:
        return pd.DataFrame()

API_URLS = {
    "2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id",
    "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"
}

# --- 5. FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)")
    tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
    df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
    
    if not df_api.empty and df_api['member'].iloc[0] != "TBA":
        list_member = sorted(df_api['member'].unique().tolist())
        pilihan_member = st.selectbox("Pilih Member:", list_member)
        
        df_member = df_api[df_api['member'] == pilihan_member]
        pilihan_sesi = st.selectbox("Pilih Sesi:", sorted(df_member['session'].unique().tolist()))
        
        df_sesi = df_member[df_member['session'] == pilihan_sesi]
        pilihan_jalur = st.selectbox("Pilih Jalur / Bilik:", sorted(df_sesi['lane'].unique().tolist()))
        
        if st.button("Simpan Jadwal", type="primary", use_container_width=True):
            if nama_user and db_connected:
                supabase.table("srs_schedule").insert({
                    "nama_user": nama_user, "tipe_tiket": tipe_tiket,
                    "nama_member": pilihan_member, "sesi": pilihan_sesi, "jalur": pilihan_jalur
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
                "nama_user": nama_user, "tipe_tiket": tipe_tiket,
                "nama_member": m_manual, "sesi": s_manual, "jalur": j_manual
            }).execute()
            st.rerun()

# --- 6. UI UTAMA ---
st.image("banner.jpg", width="stretch")
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.caption("Koordinasi Titik Kumpul - 23 Mei")
with col_btn:
    st.write("")
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- 7. RENDER GRID (LDP DASHBOARD STYLE) ---
def render_grid_section(tipe):
    if not db_connected:
        st.error("Database terputus.")
        return
        
    res = supabase.table("srs_schedule").select("*").eq("type", tipe).execute()
    if not res.data:
        st.info(f"Belum ada data anak SRS yang input untuk {tipe}.")
        return

    df = pd.DataFrame(res.data)
    
    # Filter Pencarian (Opsional agar makin mirip dashboard asli)
    search_query = st.text_input(f"🔍 Cari Sesi / Member / Anak SRS di {tipe}...", key=f"search_{tipe}")
    if search_query:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df = df[mask]

    # Mengelompokkan data berdasarkan Sesi
    sesi_list = sorted(df['sesi'].unique().tolist())
    
    for sesi in sesi_list:
        st.markdown(f"#### {sesi}")
        df_sesi = df[df['sesi'] == sesi]
        
        # Mengelompokkan berdasarkan Member & Jalur di dalam Sesi tersebut
        grouped = df_sesi.groupby(['nama_member', 'jalur'])['nama_user'].apply(list).reset_index()
        
        html = '<div class="cards-grid">'
        for _, row in grouped.iterrows():
            member = row['nama_member']
            jalur = row['jalur']
            users_list = row['nama_user']
            count = len(users_list)
            users_str = ", ".join(users_list)
            
            # HTML Card Injection
            html += f"""
            <div class="srs-card">
                <div class="c-jalur">{jalur}</div>
                <div class="c-member">{member}</div>
                <div class="c-users">
                    <span class="user-count">👥 {count} ORANG</span>
                    {users_str}
                </div>
            </div>
            """
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

# --- 8. TABS ---
tab1, tab2 = st.tabs(["📸 2-Shot", "🤝 Meet & Greet"])
with tab1:
    render_grid_section("2-Shot")
with tab2:
    render_grid_section("Meet & Greet")