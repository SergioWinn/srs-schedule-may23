import streamlit as st
import requests
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS M&G Coordinator", page_icon="🎫", layout="wide")

# --- KONEKSI DATABASE (SUPABASE) ---
# Mengambil kredensial dari Streamlit Secrets nantinya
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
    db_connected = True
except Exception as e:
    st.error("Gagal terhubung ke Database. Pastikan Streamlit Secrets sudah diatur.")
    db_connected = False

# --- FUNGSI TARIK DATA API JKT48 ---
@st.cache_data(ttl=3600) # Cache 1 jam agar tidak spam server JKT48
def fetch_api(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Menyesuaikan struktur JSON. Biasanya data ada di dalam key tertentu.
        # Jika strukturnya langsung list, kembalikan data. Jika di dalam dict, cari key-nya.
        if isinstance(data, dict):
            # Mencari list di dalam dictionary
            for key, value in data.items():
                if isinstance(value, list):
                    return value
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Gagal mengambil jadwal resmi: {e}")
        return []

API_2SHOT = "https://jkt48.com/api/v1/exclusives/EX579E/bonus?lang=id"
API_MNG = "https://jkt48.com/api/v1/exclusives/EXE588/bonus?lang=id"

# --- HEADER & UI ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("banner.jpg", width="stretch")

st.markdown("<h1 style='text-align: center; color: #b45309;'>SUMBER REZEKI SQUAD</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Portal Koordinasi LOVE DREAM PASSION (23 Mei 2026)</h3>", unsafe_allow_html=True)
st.divider()

# --- TABS UNTUK INPUT DAN DASHBOARD ---
tab1, tab2 = st.tabs(["📝 Input Jadwalmu", "🔍 Cari Barengan (Dashboard)"])

with tab1:
    col_img, col_form = st.columns([1, 2])
    with col_img:
        st.image("logo.jpg", width=250)
        st.info("Pastikan data yang kamu masukkan sesuai dengan e-ticket resmi.")

    with col_form:
        tipe_tiket = st.radio("Pilih Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
        
        # Tarik data dari API berdasarkan pilihan
        url_target = API_2SHOT if tipe_tiket == "2-Shot" else API_MNG
        raw_data = fetch_api(url_target)
        
        if raw_data:
            df_api = pd.DataFrame(raw_data)
            
            # Catatan: Sesuaikan nama kolom ('memberName', 'session', 'lane') 
            # dengan struktur asli JSON dari API JKT48 setelah kamu mengeceknya.
            # Di bawah ini adalah asumsi penamaan umum.
            kolom_member = 'name' if 'name' in df_api.columns else df_api.columns[0]
            
            with st.form("form_input"):
                nama_user = st.text_input("Nama Kamu (Panggilan di SRS)", placeholder="Misal: Budi, Andi")
                
                list_member = df_api[kolom_member].dropna().unique().tolist()
                pilihan_member = st.selectbox("Pilih Member", sorted(list_member))
                
                # Input manual untuk sesi & jalur sebagai fallback yang aman, 
                # karena struktur detail API bisa bervariasi
                col_s, col_j = st.columns(2)
                with col_s:
                    sesi = st.text_input("Sesi (Sesuai Tiket)", placeholder="Misal: Sesi 1")
                with col_j:
                    jalur = st.text_input("Jalur / Bilik", placeholder="Misal: Jalur 5")
                
                submit = st.form_submit_button("Simpan Jadwal")
                
                if submit and db_connected:
                    if nama_user and sesi and jalur:
                        # Insert ke PostgreSQL (Supabase)
                        data_insert = {
                            "nama_user": nama_user,
                            "tipe_tiket": tipe_tiket,
                            "nama_member": pilihan_member,
                            "sesi": sesi,
                            "jalur": jalur
                        }
                        try:
                            supabase.table("srs_schedule").insert(data_insert).execute()
                            st.success(f"Mantap! Jadwal {nama_user} bersama {pilihan_member} berhasil disimpan.")
                        except Exception as e:
                            st.error(f"Gagal menyimpan ke database: {e}")
                    else:
                        st.warning("Harap isi semua kolom!")

with tab2:
    st.subheader("Data Antrean Komunitas")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        
    if db_connected:
        try:
            # Mengambil data dari PostgreSQL (Supabase)
            response = supabase.table("srs_schedule").select("*").execute()
            data_db = response.data
            
            if data_db:
                df_db = pd.DataFrame(data_db)
                # Membuang kolom id dan created_at agar tabel terlihat bersih
                df_tampil = df_db[['nama_user', 'tipe_tiket', 'nama_member', 'sesi', 'jalur']]
                df_tampil.columns = ['Nama SRS', 'Tipe', 'Member', 'Sesi', 'Jalur']
                
                # Fitur Filter
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filter_sesi = st.selectbox("Filter Sesi:", ["Semua"] + df_tampil['Sesi'].unique().tolist())
                with col_f2:
                    filter_jalur = st.selectbox("Filter Jalur:", ["Semua"] + df_tampil['Jalur'].unique().tolist())
                
                # Aplikasikan filter
                if filter_sesi != "Semua":
                    df_tampil = df_tampil[df_tampil['Sesi'] == filter_sesi]
                if filter_jalur != "Semua":
                    df_tampil = df_tampil[df_tampil['Jalur'] == filter_jalur]
                
                st.dataframe(df_tampil, use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada data jadwal yang masuk. Ayo input jadwalmu!")
        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")