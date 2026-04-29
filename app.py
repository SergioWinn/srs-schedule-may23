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
except Exception as e:
    st.error("Gagal terhubung ke Database.")
    db_connected = False

# --- FUNGSI AMBIL DATA API JKT48 ---
@st.cache_data(ttl=3600)
def fetch_jkt48_api(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # API JKT48 biasanya mengembalikan list di dalam key 'data' atau langsung list
        items = data.get('data', data) if isinstance(data, dict) else data
        df = pd.DataFrame(items)
        
        # Standarisasi kolom (JKT48 API sering menggunakan 'name' untuk member)
        # Kita buat kolom seragam: 'member', 'session', 'lane'
        if 'name' in df.columns:
            df = df.rename(columns={'name': 'member'})
        
        # Jika kolom session/lane tidak ada, kita buat dummy agar tidak error
        for col in ['session', 'lane', 'member']:
            if col not in df.columns:
                df[col] = "TBA"
                
        return df[['member', 'session', 'lane']]
    except Exception as e:
        return pd.DataFrame(columns=['member', 'session', 'lane'])

API_URLS = {
    "2-Shot": "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id",
    "Meet & Greet": "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"
}

# --- FORM INPUT MODAL ---
@st.dialog("📝 Input Jadwal SRS")
def form_input_srs():
    st.write("Pilih jadwal sesuai yang tertera di tiketmu.")
    
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)", placeholder="Sergio")
    tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
    
    # Ambil data API berdasarkan tipe
    df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
    
    if not df_api.empty:
        # 1. Pilih Member
        list_member = sorted(df_api['member'].unique().tolist())
        pilihan_member = st.selectbox("Pilih Member:", list_member)
        
        # 2. Filter Sesi berdasarkan Member
        df_member = df_api[df_api['member'] == pilihan_member]
        list_sesi = sorted(df_member['session'].unique().tolist())
        pilihan_sesi = st.selectbox("Pilih Sesi:", list_sesi)
        
        # 3. Filter Jalur berdasarkan Member & Sesi
        df_sesi = df_member[df_member['session'] == pilihan_sesi]
        list_jalur = sorted(df_sesi['lane'].unique().tolist())
        pilihan_jalur = st.selectbox("Pilih Jalur / Bilik:", list_jalur)
        
        if st.button("Simpan ke Database", type="primary", use_container_width=True):
            if nama_user:
                try:
                    data_insert = {
                        "nama_user": nama_user,
                        "tipe_tiket": tipe_tiket,
                        "nama_member": pilihan_member,
                        "sesi": pilihan_sesi,
                        "jalur": pilihan_jalur
                    }
                    supabase.table("srs_schedule").insert(data_insert).execute()
                    st.success("Berhasil disimpan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal simpan: {e}")
            else:
                st.warning("Nama jangan kosong ya!")
    else:
        st.error("Gagal mengambil data dari API JKT48.")

# --- UI UTAMA ---
st.image("banner.jpg", width="stretch")
col_title, col_btn = st.columns([3, 1])

with col_title:
    st.title("SUMBER REZEKI SQUAD")
    st.subheader("M&G Festival: Love Dream Passion")

with col_btn:
    st.write("") # Spacing
    if st.button("➕ INPUT DATA", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- DASHBOARD TIMETABLE ---
tab1, tab2 = st.tabs(["📸 Rekap 2-Shot", "🤝 Rekap Meet & Greet"])

def display_rekap(tipe):
    if db_connected:
        res = supabase.table("srs_schedule").select("*").eq("type", tipe).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Kelompokkan anak SRS yang jadwalnya sama
            rekap = df.groupby(['sesi', 'nama_member', 'jalur'])['nama_user'].apply(lambda x: ', '.join(x)).reset_index()
            rekap.columns = ['Sesi', 'Member', 'Jalur', 'Anak SRS']
            st.dataframe(rekap, use_container_width=True, hide_index=True)
        else:
            st.info(f"Belum ada data untuk {tipe}.")

with tab1:
    display_rekap("2-Shot")

with tab2:
    display_rekap("Meet & Greet")