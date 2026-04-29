import streamlit as st
import pandas as pd
import requests
from supabase import create_client

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS M&G Coordinator", page_icon="🎫", layout="wide")

# --- KONEKSI DATABASE (SUPABASE) ---
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

# --- FUNGSI AMBIL DATA API JKT48 (SMART MAPPING) ---
@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        items = data.get('data', data) if isinstance(data, dict) else data
        df = pd.DataFrame(items)

        if df.empty:
            return pd.DataFrame(columns=['member', 'session', 'lane'])

        # LOGIKA MAPPING: Mencari kolom yang paling mungkin
        # JKT48 API sering menggunakan nama kolom yang berbeda-beda
        mapping = {}
        cols = df.columns.tolist()
        
        # Cari Member
        for c in ['name', 'member_name', 'memberName', 'member']:
            if c in cols:
                mapping[c] = 'member'
                break
        
        # Cari Sesi
        for c in ['session', 'session_name', 'sessionName', 'bonus_session']:
            if c in cols:
                mapping[c] = 'session'
                break
        
        # Cari Jalur
        for c in ['lane', 'lane_name', 'laneName', 'bonus_lane']:
            if c in cols:
                mapping[c] = 'lane'
                break

        df = df.rename(columns=mapping)
        
        # Pastikan kolom utama ada, jika tidak ada baru isi TBA
        for col in ['member', 'session', 'lane']:
            if col not in df.columns:
                df[col] = "TBA"
        
        return df[['member', 'session', 'lane']].drop_duplicates()
    except:
        return pd.DataFrame(columns=['member', 'session', 'lane'])

API_URLS = {
    "2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id",
    "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"
}

# --- FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
    st.write("Pilih jadwal sesuai tiketmu.")
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)")
    tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
    
    df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
    
    if not df_api.empty and df_api['member'].iloc[0] != "TBA":
        list_member = sorted(df_api['member'].unique().tolist())
        pilihan_member = st.selectbox("Pilih Member:", list_member)
        
        df_member = df_api[df_api['member'] == pilihan_member]
        list_sesi = sorted(df_member['session'].unique().tolist())
        pilihan_sesi = st.selectbox("Pilih Sesi:", list_sesi)
        
        df_sesi = df_member[df_member['session'] == pilihan_sesi]
        list_jalur = sorted(df_sesi['lane'].unique().tolist())
        pilihan_jalur = st.selectbox("Pilih Jalur / Bilik:", list_jalur)
        
        if st.button("Simpan Jadwal", type="primary", use_container_width=True):
            if nama_user:
                supabase.table("srs_schedule").insert({
                    "nama_user": nama_user, "tipe_tiket": tipe_tiket,
                    "nama_member": pilihan_member, "sesi": pilihan_sesi, "jalur": pilihan_jalur
                }).execute()
                st.success("Tersimpan! Silakan refresh.")
                st.rerun()
    else:
        st.warning("Data API sedang tidak tersedia. Gunakan input manual?")
        # Fallback input manual jika API error
        m_manual = st.text_input("Nama Member (Manual)")
        s_manual = st.text_input("Sesi (Manual)")
        j_manual = st.text_input("Jalur (Manual)")
        if st.button("Simpan Manual"):
            supabase.table("srs_schedule").insert({
                "nama_user": nama_user, "tipe_tiket": tipe_tiket,
                "nama_member": m_manual, "sesi": s_manual, "jalur": j_manual
            }).execute()
            st.rerun()

# --- UI UTAMA ---
st.image("banner.jpg", width="stretch")
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.caption("Koordinasi Event 23 Mei 2026 - Love Dream Passion")
with col_btn:
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- REKAP TIMETABLE LENGKAP ---
tab1, tab2 = st.tabs(["📸 Timetable 2-Shot", "🤝 Timetable Meet & Greet"])

def display_full_timetable(tipe):
    # 1. Ambil Jadwal Resmi dari API (Master)
    df_master = fetch_jkt48_api(API_URLS[tipe])
    
    # 2. Ambil Data User dari Supabase
    if db_connected:
        res = supabase.table("srs_schedule").select("*").eq("tipe_tiket", tipe).execute()
        df_user = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        if not df_user.empty:
            # Grouping user berdasarkan jadwal yang sama
            df_user_grouped = df_user.groupby(['sesi', 'nama_member', 'jalur'])['nama_user'].apply(lambda x: ', '.join(x)).reset_index()
            df_user_grouped.columns = ['session', 'member', 'lane', 'Anak SRS']
            
            # 3. MERGE: Masukkan data user ke dalam Master Timetable
            # Menggunakan 'left merge' agar semua jadwal API tetap muncul
            df_final = pd.merge(df_master, df_user_grouped, on=['session', 'member', 'lane'], how='left')
        else:
            df_final = df_master.copy()
            df_final['Anak SRS'] = "-"
            
        # Percantik Tampilan
        df_final.columns = ['Member', 'Sesi', 'Jalur', 'Anak SRS']
        df_final = df_final.fillna("-")
        st.dataframe(df_final.sort_values(by=['Sesi', 'Jalur']), use_container_width=True, hide_index=True)
    else:
        st.error("Database tidak terhubung.")

with tab1:
    display_full_timetable("2-Shot")
with tab2:
    display_full_timetable("Meet & Greet")