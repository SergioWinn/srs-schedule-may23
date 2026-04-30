import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from st_copy_to_clipboard import st_copy_to_clipboard
import hashlib

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SRS - LOVE DREAM PASSION", page_icon="🎫", layout="wide")

# --- 2. PREMIUM UI STYLING ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* Font & Global Reset */
html, body, .stApp { 
    font-family: 'Inter', sans-serif; 
}

/* 1. FORCE DARK THEME VIBE (Agar Light Mode tetap cakep) */
.cards-grid { 
    display: grid; 
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
    gap: 15px; 
    margin-top: 10px; 
    margin-bottom: 30px; 
}

/* Kartu dibuat solid agar tidak tembus pandang di Light Mode */
.srs-card { 
    background: #1e293b !important; 
    color: #f8fafc !important;
    border-radius: 15px; 
    padding: 20px 15px; 
    border: 1px solid rgba(255,255,255,0.1); 
    display: flex; 
    flex-direction: column; 
    text-align: center; 
    height: 100%; 
    border-bottom: 5px solid #475569; 
}

.srs-card.active { 
    border-bottom: 5px solid #10B981; 
}

.c-jalur { 
    font-size: 11px; 
    color: #94a3b8 !important; 
    font-weight: 700; 
    text-transform: uppercase; 
    margin-bottom: 5px; 
}

.c-member { 
    font-weight: 800; 
    font-size: 18px; 
    color: #f8fafc !important; 
    margin-bottom: 15px; 
}

.c-users { 
    padding: 10px; 
    border-radius: 12px; 
    margin-top: auto; 
    display: flex; 
    flex-direction: column; 
    gap: 4px; 
}

.srs-card.active .c-users { 
    background: rgba(16,185,129,0.15); 
    color: #10B981 !important; 
    border: 1px solid rgba(16,185,129,0.2); 
}

.srs-card.empty .c-users { 
    background: rgba(148, 163, 184, 0.1); 
    color: #94a3b8 !important; 
    border: 1px solid rgba(148, 163, 184, 0.2); 
}

.user-count { 
    font-size: 11px; 
    text-transform: uppercase; 
    font-weight: 800; 
}

.user-names { 
    font-size: 13px; 
    font-weight: 600; 
    line-height: 1.4; 
    color: #f8fafc !important;
}

/* 2. LIVE BADGE ANIMATION */
.live-badge { 
    display: inline-flex; 
    align-items: center; 
    gap: 8px; 
    font-weight: 700; 
    font-size: 12px; 
    color: #10B981; 
    background: rgba(16,185,129,0.1); 
    padding: 5px 15px; 
    border-radius: 30px; 
    border: 1px solid rgba(16,185,129,0.2); 
}

.live-dot { 
    height: 8px; 
    width: 8px; 
    background: #10B981; 
    border-radius: 50%; 
    animation: blink 2s infinite; 
}

@keyframes blink { 
    0%, 100% { opacity: 1; transform: scale(1); } 
    50% { opacity: 0.3; transform: scale(1.2); } 
}

/* 3. JUDUL & LOGO RANTAI REMOVAL */
/* Membunuh ikon rantai (anchor link) secara paksa */
[data-testid="stHeaderActionElements"] {
    display: none !important;
}

h1, h3, h4, h5 { 
    margin-bottom: 0px !important; 
    font-weight: 800 !important; 
}

/* Mengatur warna judul agar tetap kontras di Light/Dark mode */
h1 { color: #f8fafc; }
h3 { color: #94a3b8; }
h4 { padding-top: 15px !important; }
h5 { color: #94a3b8; font-size: 1rem !important; }

hr { 
    margin-top: 5px; 
    margin-bottom: 10px; 
    border-color: rgba(255,255,255,0.1); 
}

/* Khusus perbaikan warna teks filter agar terbaca di Light Mode */
.stMultiSelect label p {
    color: inherit !important;
}
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
    nama_user = st.text_input("Nama Kamu (Panggilan SRS)", placeholder="Pastikan konsisten (contoh: Sergio)")
    
    tab_manual, tab_csv = st.tabs(["✍️ Input Manual", "📁 Upload CSV"])
    
    with tab_manual:
        tipe_tiket = st.radio("Tipe Tiket:", ["2-Shot", "Meet & Greet"], horizontal=True, key="manual_type")
        df_api = fetch_jkt48_api(API_URLS[tipe_tiket])
        
        if not df_api.empty:
            p_member = st.selectbox("Pilih Member:", sorted(df_api['nama_member'].unique().tolist()), key="manual_member")
            df_m = df_api[df_api['nama_member'] == p_member]
            p_sesi = st.selectbox("Pilih Sesi:", sorted(df_m['sesi'].unique().tolist()), key="manual_sesi")
            p_jalur = st.selectbox("Pilih Jalur:", sorted(df_m[df_m['sesi'] == p_sesi]['jalur'].unique().tolist()), key="manual_jalur")
            
            if st.button("Simpan Jadwal Manual", type="primary", use_container_width=True):
                if nama_user and db_connected:
                    check = supabase.table("srs_schedule").select("*")\
                        .ilike("name", nama_user.strip())\
                        .eq("type", tipe_tiket)\
                        .eq("member", p_member)\
                        .eq("sesi", p_sesi).execute()
                    
                    if check.data:
                        st.error(f"Ups! Nama '{nama_user}' sudah terdaftar untuk {p_member} di {p_sesi}.")
                    else:
                        supabase.table("srs_schedule").insert({
                            "name": nama_user.strip(), "type": tipe_tiket, 
                            "member": p_member, "sesi": p_sesi, "jalur": p_jalur
                        }).execute()
                        st.rerun()
                elif not nama_user:
                    st.warning("Harap isi Nama Kamu di kolom atas!")
        else:
            st.warning("API JKT48 sedang down.")

    with tab_csv:
        uploaded_files = st.file_uploader("Pilih file CSV", type=["csv"], accept_multiple_files=True)
        if st.button("Simpan dari CSV", type="primary", use_container_width=True):
            if not nama_user:
                st.warning("Harap isi Nama Kamu!")
            elif uploaded_files and db_connected:
                try:
                    new_records = []
                    for uploaded_file in uploaded_files:
                        df_upload = pd.read_csv(uploaded_file)
                        for _, row in df_upload.iterrows():
                            if all(col in df_upload.columns for col in ['Member', 'Sesi', 'Jalur', 'Tipe Tiket']):
                                t_raw = str(row['Tipe Tiket']).strip()
                                tipe_tiket_final = "2-Shot" if "2shot" in t_raw.lower() or "2-shot" in t_raw.lower() else "Meet & Greet"
                                m_val = str(row['Member']).strip()
                                s_val = str(row['Sesi']).strip()
                                
                                dupe_check = supabase.table("srs_schedule").select("*").ilike("name", nama_user.strip()).eq("type", tipe_tiket_final).eq("member", m_val).eq("sesi", s_val).execute()
                                if not dupe_check.data:
                                    new_records.append({"name": nama_user.strip(), "type": tipe_tiket_final, "member": m_val, "sesi": s_val, "jalur": str(row['Jalur']).strip()})
                    
                    if new_records:
                        supabase.table("srs_schedule").insert(new_records).execute()
                        st.rerun()
                except Exception as e:
                    st.error(f"Eror: {e}")

# --- 5. UI UTAMA (Clean Headers) ---
col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
with col_title:
    st.markdown("<h1>SUMBER REZEKI SQUAD</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Meet & Greet Festival: LOVE DREAM PASSION</h3>", unsafe_allow_html=True)
    st.markdown('<div class="live-badge" style="margin-top:10px;"><span class="live-dot"></span> REAL-TIME REKAP</div>', unsafe_allow_html=True)

with col_btn:
    if st.button("➕ INPUT JADWALMU", type="primary", use_container_width=True):
        form_input_srs()

st.divider()

# --- 6. RENDER GRID ---
@st.fragment(run_every=5)
def render_realtime_dashboard():
    tab1, tab2 = st.tabs(["📸 2-Shot", "🤝 Meet & Greet"])
    with tab1: render_grid_section("2-Shot")
    with tab2: render_grid_section("Meet & Greet")

def render_grid_section(tipe):
    df_master = fetch_jkt48_api(API_URLS[tipe])
    df_user = pd.DataFrame()
    if db_connected:
        res = supabase.table("srs_schedule").select("*").eq("type", tipe).execute()
        if res.data:
            df_user = pd.DataFrame(res.data).rename(columns={"name": "nama_user", "member": "nama_member"})

    if df_master.empty: return

    df_final = pd.merge(df_master, df_user.groupby(['sesi', 'nama_member', 'jalur'])['nama_user'].apply(list).reset_index(), on=['sesi', 'nama_member', 'jalur'], how='left') if not df_user.empty else df_master.assign(nama_user=None)
    df_final['nama_user'] = df_final['nama_user'].apply(lambda x: x if isinstance(x, list) else [])
    
    unique_sesi = sorted(df_final['sesi'].unique().tolist())
    unique_member = sorted(df_final['nama_member'].unique().tolist())
    all_users = sorted(list(set([u for sub in df_final['nama_user'] for u in sub])), key=str.lower)

    # --- UI FILTER (ANTI SELECT-ALL) ---
    st.markdown(f"<h5>🎛️ Filter & Salin Rekap {tipe}</h5>", unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
    
    with f_col1: f_sesi = st.multiselect("Berdasarkan Sesi", unique_sesi, placeholder="Semua Sesi", max_selections=len(unique_sesi), key=f"f_s_{tipe}")
    with f_col2: f_member = st.multiselect("Berdasarkan Member", unique_member, placeholder="Semua Member", max_selections=len(unique_member), key=f"f_m_{tipe}")
    with f_col3: f_user = st.multiselect("Berdasarkan Anak SRS", all_users, placeholder="Semua Anak SRS", max_selections=len(all_users), key=f"f_u_{tipe}")

    df_filtered = df_final.copy()
    if f_sesi: df_filtered = df_filtered[df_filtered['sesi'].isin(f_sesi)]
    if f_member: df_filtered = df_filtered[df_filtered['nama_member'].isin(f_member)]
    if f_user: df_filtered = df_filtered[df_filtered['nama_user'].apply(lambda users: any(u in users for u in f_user))]

    # --- MASTER COPY LOGIC (ANTI-NYANGKUT) ---
    j_u, j_m, j_s = list(f_user), list(f_member), list(f_sesi)
    judul = f"🎫 [SRS] JADWAL {tipe.upper()} - {', '.join(j_u).upper()}" if j_u else f"🎫 [SRS] REKAP MEMBER {tipe.upper()} - {', '.join(j_m).upper()}" if j_m else f"🎫 [SRS] REKAP {tipe.upper()} - {', '.join(j_s).upper()}" if j_s else f"🎫 [SRS] REKAP KESELURUHAN {tipe.upper()}"

    rekap_lines = [f"{judul}\n"]
    ada_isi = False
    for s_name in sorted(df_filtered['sesi'].unique().tolist()):
        df_temp = df_filtered[df_filtered['sesi'] == s_name]
        jalur_lines = [f"📍 {r['jalur']} ({r['nama_member']}): {', '.join(sorted(list(set(r['nama_user']))))}" for _, r in df_temp.iterrows() if r['nama_user']]
        if jalur_lines:
            rekap_lines.append(f"🔹 {s_name}"); rekap_lines.extend(jalur_lines); rekap_lines.append(""); ada_isi = True

    final_text = "\n".join(rekap_lines)
    with f_col4:
        t_hash = hashlib.md5(final_text.encode()).hexdigest()[:8]
        if ada_isi: st_copy_to_clipboard(text=final_text, before_copy_label="📋", after_copy_label="✅", key=f"cp_{tipe}_{t_hash}")
        else: st.button("🚫", disabled=True, key=f"ex_{tipe}_{t_hash}", use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # --- RENDER KOTAK (Clean Headers) ---
    for sesi in sorted(df_filtered['sesi'].unique().tolist()):
        df_sesi = df_filtered[df_filtered['sesi'] == sesi]
        st.markdown(f"<h4>{sesi}</h4>", unsafe_allow_html=True)
        
        html_cards = '<div class="cards-grid">'
        for _, row in df_sesi.iterrows():
            users = sorted(list(dict.fromkeys(row['nama_user']))) if row['nama_user'] else []
            count = len(users)
            card_class, users_str = ("active", ", ".join(users)) if count > 0 else ("empty", "Belum ada anak SRS")
            html_cards += f'<div class="srs-card {card_class}"><div class="c-jalur">{row["jalur"]}</div><div class="c-member">{row["nama_member"]}</div><div class="c-users"><div class="user-count">👥 {count} ORANG</div><div class="user-names">{users_str}</div></div></div>'
        
        html_cards += '</div>'
        st.markdown(html_cards, unsafe_allow_html=True)

render_realtime_dashboard()