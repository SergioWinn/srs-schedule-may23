import streamlit as st
import pandas as pd
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
    st.error("Gagal terhubung ke Database. Pastikan Streamlit Secrets sudah diatur.")
    db_connected = False

# --- FUNGSI AMBIL DATA DATABASE ---
def get_srs_data():
    if db_connected:
        response = supabase.table("srs_schedule").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
    return pd.DataFrame()

# --- FORM MELAYANG (MODAL DIALOG) ---
@st.dialog("📝 Input Data Antrean SRS")
def form_input_melayang():
    st.write("Pastikan data sesuai dengan e-ticket resmi kamu.")
    
    with st.form("form_input"):
        nama_user = st.text_input("Nama Kamu (Panggilan di SRS)", placeholder="Misal: Sergio / Budi")
        tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True)
        
        # Menggunakan text input untuk nama member agar terhindar dari bug ID angka
        pilihan_member = st.text_input("Nama Member", placeholder="Misal: Elin, Kimmy, dll")
        
        col_s, col_j = st.columns(2)
        with col_s:
            sesi = st.text_input("Sesi / Jam", placeholder="Misal: Sesi 1 / 10:00")
        with col_j:
            jalur = st.text_input("Jalur / Bilik", placeholder="Misal: Jalur 5")
            
        submit = st.form_submit_button("Simpan Jadwal", type="primary")
        
        if submit and db_connected:
            if nama_user and pilihan_member and sesi and jalur:
                data_insert = {
                    "nama_user": nama_user,
                    "tipe_tiket": tipe_tiket,
                    "nama_member": pilihan_member,
                    "sesi": sesi,
                    "jalur": jalur
                }
                supabase.table("srs_schedule").insert(data_insert).execute()
                st.success(f"Mantap! Jadwal bareng {pilihan_member} berhasil disimpan.")
                st.rerun() # Refresh halaman agar tabel langsung update
            else:
                st.warning("Harap isi semua kolom!")

# --- HEADER & UI ---
col_logo, col_banner = st.columns([1, 4])
with col_logo:
    st.image("logo.jpg", width=150)
with col_banner:
    st.markdown("<h1 style='color: #b45309; margin-bottom: 0;'>SUMBER REZEKI SQUAD</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Portal Koordinasi Timetable M&G Festival</h3>", unsafe_allow_html=True)

st.divider()

# --- TOMBOL MELAYANG (TRIGGER) ---
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button("➕ KLIK DI SINI UNTUK INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_melayang()

st.write("") # Spacing

# --- TABS TIMETABLE ---
tab_2s, tab_mng = st.tabs(["📸 Timetable 2-Shot", "🤝 Timetable M&G"])

# Tarik data terbaru
df_all = get_srs_data()

def render_timetable(df, tipe):
    if df.empty:
        st.info(f"Belum ada data antrean untuk {tipe}.")
        return
        
    # Filter berdasarkan tipe
    df_filtered = df[df['tipe_tiket'] == tipe].copy()
    
    if df_filtered.empty:
        st.info(f"Belum ada data antrean untuk {tipe}.")
        return

    # MENGELOMPOKKAN DATA (Group By)
    # Ini akan menggabungkan nama-nama anak SRS yang berada di sesi, member, dan jalur yang sama
    df_grouped = df_filtered.groupby(['sesi', 'jalur', 'nama_member'])['nama_user'].apply(
        lambda x: ', '.join(x) # Menggabungkan nama dengan koma
    ).reset_index()
    
    # Merapikan nama kolom untuk ditampilkan
    df_grouped.columns = ['Sesi / Jam', 'Jalur', 'Member', 'Anak SRS di Antrean Ini']
    
    # Tampilkan tabel interaktif
    st.dataframe(
        df_grouped,
        use_container_width=True,
        hide_index=True,
        height=400
    )

with tab_2s:
    st.subheader("Titik Kumpul 2-Shot")
    render_timetable(df_all, "2-Shot")

with tab_mng:
    st.subheader("Titik Kumpul Meet & Greet")
    render_timetable(df_all, "Meet & Greet")