import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
from datetime import datetime, timedelta
from urllib.parse import quote
import altair as alt

# ==================== KONFIGURASI HALAMAN (HARUS PERTAMA) ====================
st.set_page_config(
    page_title="GRACE'S STORE (CASH & CREDIT)",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS (TAMPILAN HIDUP) ====================
st.markdown("""
<style>
    /* Background utama */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header utama */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    .main-header h1 { color: white !important; margin: 0; font-size: 2.2em; }
    .main-header p { color: #f0f0f0; margin: 5px 0 0 0; }
    
    /* Kartu metrik custom */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .metric-card {
        padding: 20px;
        border-radius: 15px;
        color: white;
        box-shadow: 0 6px 15px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-4px); }
    .metric-card .label { font-size: 0.85em; opacity: 0.9; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card .value { font-size: 1.6em; font-weight: bold; }
    
    .card-blue   { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .card-purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .card-pink   { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .card-green  { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .card-orange { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    .card-dark   { background: linear-gradient(135deg, #232526 0%, #414345 100%); }
    
    /* Section header */
    .section-header {
        background: white;
        padding: 15px 20px;
        border-radius: 12px;
        border-left: 5px solid #667eea;
        margin: 20px 0 15px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .section-header h3 { margin: 0; color: #333; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    section[data-testid="stSidebar"] * { color: #ecf0f1 !important; }
    
    /* Tombol */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(102,126,234,0.5);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== KONEKSI DATABASE ====================
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('toko_kredit.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# ==================== STRUKTUR DATABASE ====================
c.execute('''CREATE TABLE IF NOT EXISTS produk 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customer 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, telepon TEXT, alamat TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS kredit 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, produk_id INTEGER, 
              harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, 
              tenor INTEGER, cicilan_bulan REAL, sisa_hutang REAL, jatuh_tempo TEXT, status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS pembayaran
             (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, jumlah_bayar REAL,
              denda REAL, tanggal TEXT, keterangan TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT,
              nama_lengkap TEXT, role TEXT, aktif INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS log_aktivitas
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, aksi TEXT, detail TEXT, waktu TEXT)''')
conn.commit()

# ==================== HELPER FUNCTIONS ====================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def format_rp(n):
    try:
        return f"Rp {float(n):,.0f}".replace(",", ".")
    except:
        return "Rp 0"

def log_aksi(username, aksi, detail=""):
    c.execute("INSERT INTO log_aktivitas (username, aksi, detail, waktu) VALUES (?,?,?,?)",
              (username, aksi, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def metric_card(label, value, warna="card-blue"):
    return f'<div class="metric-card {warna}"><div class="label">{label}</div><div class="value">{value}</div></div>'

# Seed user admin default
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)",
              ("admin", hash_password("admin123"), "Administrator", "admin"))
    conn.commit()

# Seed data brosur
def tanam_data_brosur():
    c.execute("SELECT COUNT(*) FROM produk")
    if c.fetchone()[0] == 0:
        data_ponsel = [
            ("iPhone 17 256GB", "Gadget", 19046700, 10),
            ("iPhone 17 512GB", "Gadget", 22141900, 10),
            ("iPhone 17 PRO 256GB", "Gadget", 20951400, 10),
            ("iPhone 17 PRO 512GB", "Gadget", 25237100, 10),
            ("iPhone 17 PRO 1TB", "Gadget", 29761000, 10),
            ("iPhone 17 PRO MAX 256GB", "Gadget", 22856200, 10),
            ("iPhone 17 PRO MAX 512GB", "Gadget", 27141900, 10),
            ("iPhone 17 PRO MAX 1TB", "Gadget", 31427600, 10),
            ("iPhone 17 PRO MAX 2TB", "Gadget", 40237100, 10),
            ("iPhone 17 AIR 256GB", "Gadget", 15951400, 10),
            ("iPhone 17 AIR 512GB", "Gadget", 20237100, 10),
            ("iPhone 17 AIR 1TB", "Gadget", 23618100, 10),
            ("iPhone 17e 256GB", "Gadget", 12380000, 10),
            ("iPhone 17e 512GB", "Gadget", 16475200, 10),
            ("iPhone 16 128GB", "Gadget", 15951400, 10),
            ("iPhone 16 256GB", "Gadget", 16903800, 10),
            ("iPhone 16 PLUS 128GB", "Gadget", 15141900, 10),
            ("iPhone 16 PLUS 256GB", "Gadget", 16380000, 10),
            ("iPhone 15 128GB", "Gadget", 13332400, 10),
            ("Galaxy S26 Ultra 256GB", "Gadget", 23332400, 10),
            ("Galaxy S26 Ultra 512GB", "Gadget", 26189500, 10),
            ("Galaxy S26 Ultra 1TB", "Gadget", 30475200, 10),
            ("Galaxy S26+ 256GB", "Gadget", 18570500, 10),
            ("Galaxy S26+ 512GB", "Gadget", 21427600, 10),
            ("Galaxy S26 256GB", "Gadget", 15713300, 10),
            ("Galaxy S25 Ultra 256GB", "Gadget", 18570500, 10),
            ("Reno 16 Pro 256GB", "Gadget", 14284800, 10),
            ("Reno 16 256GB (8GB)", "Gadget", 11427600, 10),
            ("Reno 16 256GB (12GB)", "Gadget", 12380000, 10),
            ("Reno 16 F 128GB", "Gadget", 7618100, 10),
            ("Find X9 Ultra", "Gadget", 26665700, 10),
            ("OPPO A6 128GB", "Gadget", 3808600, 10),
        ]
        c.executemany("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", data_ponsel)
        conn.commit()

tanam_data_brosur()

# ==================== LOGIN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.nama = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.markdown("""
    <div class="main-header">
        <h1>🏪 Toko Kredit PRO</h1>
        <p>Sistem Manajemen Toko & Cicilan Modern</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            st.subheader("🔐 Login")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk")
            if submit:
                row = c.execute("SELECT username, password, nama_lengkap, role, aktif FROM users WHERE username=?", (u,)).fetchone()
                if row and row[1] == hash_password(p) and row[4] == 1:
                    st.session_state.logged_in = True
                    st.session_state.username = row[0]
                    st.session_state.nama = row[2]
                    st.session_state.role = row[3]
                    log_aksi(u, "LOGIN", "Berhasil login")
                    st.rerun()
                else:
                    st.error("❌ Username / password salah atau akun nonaktif")
        st.info("🔑 Default admin: **admin** / **admin123**")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 15px 0;">
        <div style="font-size:3em;">👤</div>
        <h3 style="margin:5px 0;">{st.session_state.nama}</h3>
        <p style="opacity:0.8; margin:0; font-size:0.9em;">Role: {st.session_state.role.upper()}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    menu_list = [
        "🏠 Dashboard",
        "🧮 Input Produk & Skema",
        "📥 Barang Masuk",
        "📤 Kredit Baru",
        "💰 Pembayaran Cicilan",
        "👥 Data Customer",
        "📦 Stok Barang",
        "🚨 Overdue & Denda",
        "🔔 Alert & Reminder",
        "📊 Laporan & Analitik",
        "💾 Backup, Cetak & Impor",
    ]
    if st.session_state.role == "admin":
        menu_list.append("👤 Manajemen User")
        menu_list.append("📝 Log Aktivitas")
    
    pilihan = st.selectbox("📋 Menu", menu_list)
    st.markdown("---")
    if st.button("🚪 Logout"):
        log_aksi(st.session_state.username, "LOGOUT")
        for k in ["logged_in", "username", "nama", "role"]:
            st.session_state[k] = False if k == "logged_in" else ""
        st.rerun()

# ==================== HALAMAN DASHBOARD ====================
if pilihan == "🏠 Dashboard":
    st.markdown(f"""
    <div class="main-header">
        <h1>🏠 Dashboard Utama</h1>
        <p>Selamat datang kembali, <b>{st.session_state.nama}</b> 👋</p>
    </div>
    """, unsafe_allow_html=True)
    
    # === METRIK UTAMA ===
    total_produk = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    total_stok = c.execute("SELECT COALESCE(SUM(stok),0) FROM produk").fetchone()[0]
    total_customer = c.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    kredit_aktif = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    kredit_lunas = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Lunas'").fetchone()[0]
    total_piutang = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    overdue_count = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan' AND jatuh_tempo < ?", (tgl_skrg,)).fetchone()[0]
    
    # Total penjualan bulan ini
    awal_bulan = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    total_bulan_ini = c.execute("""
        SELECT COALESCE(SUM(total_hutang),0) FROM kredit 
        WHERE jatuh_tempo >= ? OR id IN (SELECT id FROM kredit WHERE status='Lunas')
    """, (awal_bulan,)).fetchone()[0]
    
    # Laba estimasi (harga_cash - harga_modal)
    laba = c.execute("""
        SELECT COALESCE(SUM(k.harga_cash - p.harga_modal),0)
        FROM kredit k JOIN produk p ON k.produk_id = p.id
    """).fetchone()[0]
    
    html = '<div class="metric-grid">'
    html += metric_card("📦 Total Produk", f"{total_produk} item", "card-blue")
    html += metric_card("🎒 Total Stok", f"{total_stok} unit", "card-purple")
    html += metric_card("👥 Customer", f"{total_customer} orang", "card-green")
    html += metric_card("💳 Kredit Aktif", f"{kredit_aktif} akun", "card-orange")
    html += metric_card("💰 Total Piutang", format_rp(total_piutang), "card-dark")
    html += metric_card("📈 Estimasi Laba", format_rp(laba), "card-pink")
    html += metric_card("⚠️ Overdue", f"{overdue_count} akun", "card-pink")
    html += metric_card("✅ Kredit Lunas", f"{kredit_lunas} akun", "card-green")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    
    # === GRAFIK ===
    st.markdown('<div class="section-header"><h3>📊 Analitik Penjualan</h3></div>', unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("**🏆 Top 5 Produk Terlaris**")
        df_top = pd.read_sql_query("""
            SELECT p.nama, COUNT(k.id) as jumlah_terjual
            FROM kredit k JOIN produk p ON k.produk_id = p.id
            GROUP BY p.nama ORDER BY jumlah_terjual DESC LIMIT 5
        """, conn)
        if not df_top.empty:
            chart = alt.Chart(df_top).mark_bar(cornerRadiusTopRight=10, cornerRadiusBottomRight=10).encode(
                x=alt.X('jumlah_terjual:Q', title='Jumlah Terjual'),
                y=alt.Y('nama:N', sort='-x', title='Produk'),
                color=alt.Color('jumlah_terjual:Q', scale=alt.Scale(scheme='purples'), legend=None)
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")
    
    with col_chart2:
        st.markdown("**📈 Cicilan Masuk per Bulan**")
        df_bayar = pd.read_sql_query("""
            SELECT substr(tanggal,1,7) as bulan, SUM(jumlah_bayar) as total
            FROM pembayaran GROUP BY bulan ORDER BY bulan
        """, conn)
        if not df_bayar.empty:
            chart = alt.Chart(df_bayar).mark_area(
                line={'color':'#667eea'}, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#f093fb', offset=0),
                           alt.GradientStop(color='#667eea', offset=1)],
                    x1=1, x2=1, y1=1, y2=0)
            ).encode(
                x=alt.X('bulan:N', title='Bulan'),
                y=alt.Y('total:Q', title='Total (Rp)')
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada pembayaran")
    
    # === STOK MENIPIS ===
    st.markdown('<div class="section-header"><h3>⚠️ Peringatan Stok Menipis (≤3 unit)</h3></div>', unsafe_allow_html=True)
    df_tipis = pd.read_sql_query("SELECT nama, kategori, stok FROM produk WHERE stok <= 3 ORDER BY stok ASC", conn)
    if not df_tipis.empty:
        st.dataframe(df_tipis, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Semua stok aman")
    
    # === KREDIT JATUH TEMPO TERDEKAT ===
    st.markdown('<div class="section-header"><h3>⏰ Jatuh Tempo 7 Hari ke Depan</h3></div>', unsafe_allow_html=True)
    tgl_7 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    df_dekat = pd.read_sql_query("""
        SELECT c.nama as customer, c.telepon, k.cicilan_bulan, k.jatuh_tempo
        FROM kredit k JOIN customer c ON k.customer_id = c.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?
        ORDER BY k.jatuh_tempo
    """, conn, params=(tgl_skrg, tgl_7))
    if not df_dekat.empty:
        st.dataframe(df_dekat, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Tidak ada jatuh tempo dalam 7 hari ke depan")


# ==================== 1. INPUT PRODUK & SKEMA ====================
elif pilihan == "🧮 Input Produk & Skema":
    st.markdown('<div class="main-header"><h1>🧮 Input Produk & Kalkulator Kredit</h1></div>', unsafe_allow_html=True)
    
    with st.expander("➕ Tambah Produk Baru Manual", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nama_produk = st.text_input("Nama Produk")
            kategori = st.selectbox("Kategori", ["Gadget", "Elektronik", "Furnitur", "Motor", "Lainnya"])
        with col2:
            harga_modal = st.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0)
            stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
        
        if st.button("💾 Simpan Produk"):
            if nama_produk and harga_modal > 0:
                c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)",
                          (nama_produk, kategori, harga_modal, stok_awal))
                conn.commit()
                log_aksi(st.session_state.username, "TAMBAH_PRODUK", nama_produk)
                st.success(f"✅ Produk **{nama_produk}** berhasil disimpan!")
                st.rerun()
            else:
                st.warning("⚠️ Nama dan harga modal wajib diisi")
    
    st.markdown('<div class="section-header"><h3>⚙️ Simulasi Skema Kredit</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        modal_sim = st.number_input("Harga Modal Simulasi (Rp)", min_value=0.0, value=5000000.0, step=100000.0)
        dp_persen = st.slider("DP Minimal (%)", 10, 80, 20, 5)
    with col2:
        tenor_sim = st.selectbox("Tenor (Bulan)", [1, 2, 3, 6, 12, 18, 24], index=3)
        bunga_flat = st.number_input("Bunga Flat / 6 Bln (%)", min_value=0.0, value=40.0, step=1.0)
    
    harga_cash = round(modal_sim * 1.05, -2)
    dp_min = round(harga_cash * dp_persen / 100, -2)
    rate = (bunga_flat / 100) / 6
    bunga_total = rate * tenor_sim
    pokok = round(harga_cash - dp_min, -2)
    total = round(pokok * (1 + bunga_total), -2)
    cicilan = round(total / tenor_sim, -2)
    
    html = '<div class="metric-grid">'
    html += metric_card("Harga Cash", format_rp(harga_cash), "card-blue")
    html += metric_card(f"DP Min ({dp_persen}%)", format_rp(dp_min), "card-purple")
    html += metric_card("Pokok Hutang", format_rp(pokok), "card-orange")
    html += metric_card(f"Bunga ({bunga_total*100:.1f}%)", format_rp(total - pokok), "card-pink")
    html += metric_card("Total Hutang", format_rp(total), "card-dark")
    html += metric_card(f"Cicilan ({tenor_sim}x)", format_rp(cicilan), "card-green")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ==================== 2. BARANG MASUK ====================
elif pilihan == "📥 Barang Masuk":
    st.markdown('<div class="main-header"><h1>📥 Input Barang Masuk (Restock)</h1></div>', unsafe_allow_html=True)
    
    df_produk = pd.read_sql_query("SELECT id, nama, stok FROM produk ORDER BY nama", conn)
    if df_produk.empty:
        st.warning("Belum ada produk")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opsi = {f"{r['nama']} (stok: {r['stok']})": r['id'] for _, r in df_produk.iterrows()}
            pilih = st.selectbox("Pilih Produk", list(opsi.keys()))
        with col2:
            jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1, value=1)
        
        if st.button("➕ Tambah Stok"):
            pid = opsi[pilih]
            c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)",
                      (pid, jumlah, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah, pid))
            conn.commit()
            log_aksi(st.session_state.username, "RESTOCK", f"Produk ID {pid}, +{jumlah}")
            st.success(f"✅ Stok bertambah {jumlah} unit!")
            st.rerun()
        
        st.markdown('<div class="section-header"><h3>📜 Riwayat Barang Masuk Terakhir</h3></div>', unsafe_allow_html=True)
        df_in = pd.read_sql_query("""
            SELECT t.id, p.nama as produk, t.jumlah, t.tanggal
            FROM transaksi_in t JOIN produk p ON t.produk_id = p.id
            ORDER BY t.id DESC LIMIT 20
        """, conn)
        st.dataframe(df_in, use_container_width=True, hide_index=True)


# ==================== 3. KREDIT BARU ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Transaksi Kredit Baru</h1></div>', unsafe_allow_html=True)
    
    df_cust = pd.read_sql_query("SELECT id, nama FROM customer", conn)
    df_prod = pd.read_sql_query("SELECT id, nama, harga_modal, stok FROM produk WHERE stok > 0 ORDER BY nama", conn)
    
    if df_cust.empty or df_prod.empty:
        st.warning("⚠️ Pastikan Data Customer dan Stok Barang Tersedia!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opsi_cust = {r['nama']: r['id'] for _, r in df_cust.iterrows()}
            pilih_c = st.selectbox("👤 Pilih Customer", list(opsi_cust.keys()))
        with col2:
            opsi_prod = {f"{r['nama']} (stok: {r['stok']})": (r['id'], r['harga_modal']) for _, r in df_prod.iterrows()}
            pilih_p = st.selectbox("📱 Pilih Produk", list(opsi_prod.keys()))
        
        id_p, mod_p = opsi_prod[pilih_p]
        h_cash = round(mod_p * 1.05, -2)
        dp_min = round(h_cash * 0.2, -2)
        
        st.markdown('<div class="section-header"><h3>💰 Pengaturan DP & Tenor</h3></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            dp = st.number_input(f"DP (Min: {format_rp(dp_min)})", min_value=float(dp_min), value=float(dp_min), step=50000.0)
        with col2:
            tenor = st.selectbox("Tenor (Bulan)", [1, 2, 3, 6, 12, 18, 24], index=3)
        
        rate = 0.40 / 6
        bunga = rate * tenor
        pokok = round(h_cash - dp, -2)
        total = round(pokok * (1 + bunga), -2)
        cicilan = round(total / tenor, -2)
        
        html = '<div class="metric-grid">'
        html += metric_card("Harga Cash", format_rp(h_cash), "card-blue")
        html += metric_card("DP", format_rp(dp), "card-purple")
        html += metric_card("Pokok Hutang", format_rp(pokok), "card-orange")
        html += metric_card(f"Bunga ({bunga*100:.1f}%)", format_rp(total - pokok), "card-pink")
        html += metric_card("Total Hutang", format_rp(total), "card-dark")
        html += metric_card(f"Cicilan / Bulan", format_rp(cicilan), "card-green")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        # Cek kredit aktif customer ini
        cek = c.execute("SELECT COUNT(*) FROM kredit WHERE customer_id=? AND status='Berjalan'", (opsi_cust[pilih_c],)).fetchone()[0]
        if cek > 0:
            st.warning(f"⚠️ Customer ini punya {cek} kredit aktif. Pastikan tidak menumpuk!")
        
        if st.button("✅ Proses Kredit & Keluarkan Barang"):
            id_c = opsi_cust[pilih_c]
            tgl_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                      (id_c, id_p, h_cash, dp, pokok, total, tenor, cicilan, total, tgl_tempo, "Berjalan"))
            c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
            conn.commit()
            log_aksi(st.session_state.username, "KREDIT_BARU", f"Customer {pilih_c}, Produk {pilih_p}")
            st.success("🎉 Akad kredit berhasil! Barang siap diserahkan.")
            st.balloons()
            st.rerun()


# ==================== 4. PEMBAYARAN CICILAN ====================
elif pilihan == "💰 Pembayaran Cicilan":
    st.markdown('<div class="main-header"><h1>💰 Pembayaran Cicilan</h1></div>', unsafe_allow_html=True)
    
    df_kredit = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.sisa_hutang, 
               k.cicilan_bulan, k.jatuh_tempo, k.tenor
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id
        JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan'
        ORDER BY k.jatuh_tempo ASC
    """, conn)
    
    if df_kredit.empty:
        st.success("✅ Tidak ada kredit aktif")
    else:
        df_kredit['label'] = df_kredit.apply(
            lambda r: f"#{r['id']} - {r['customer']} - {r['produk']} (Sisa: {format_rp(r['sisa_hutang'])})", axis=1)
        opsi = dict(zip(df_kredit['label'], df_kredit['id']))
        pilih = st.selectbox("🔍 Pilih Akun Kredit", list(opsi.keys()))
        kredit_id = opsi[pilih]
        
        detail = df_kredit[df_kredit['id'] == kredit_id].iloc[0]
        
        # Hitung denda jika terlambat
        tgl_skrg = datetime.now().date()
        tgl_tempo = datetime.strptime(detail['jatuh_tempo'], "%Y-%m-%d").date()
        hari_telat = (tgl_skrg - tgl_tempo).days
        denda = 0
        if hari_telat > 0:
            denda = round(detail['cicilan_bulan'] * 0.01 * hari_telat, -2)
        
        html = '<div class="metric-grid">'
        html += metric_card("Sisa Hutang", format_rp(detail['sisa_hutang']), "card-dark")
        html += metric_card("Cicilan / Bulan", format_rp(detail['cicilan_bulan']), "card-blue")
        html += metric_card("Jatuh Tempo", detail['jatuh_tempo'], "card-orange")
        html += metric_card("Hari Telat", f"{max(hari_telat,0)} hari", "card-pink" if hari_telat > 0 else "card-green")
        html += metric_card("Denda (1%/hari)", format_rp(denda), "card-pink")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header"><h3>💵 Input Pembayaran</h3></div>', unsafe_allow_html=True)
        
        total_bayar_default = detail['cicilan_bulan'] + denda
        col1, col2 = st.columns(2)
        with col1:
            jumlah_bayar = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, value=float(total_bayar_default), step=50000.0)
        with col2:
            keterangan = st.text_input("Keterangan (opsional)", placeholder="Cicilan bulan ke-1, dst.")
        
        if st.button("💳 Proses Pembayaran"):
            if jumlah_bayar <= 0:
                st.error("Jumlah bayar harus > 0")
            else:
                sisa_baru = max(round(detail['sisa_hutang'] - (jumlah_bayar - denda), -2), 0)
                tgl_next = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                status_baru = "Lunas" if sisa_baru <= 0 else "Berjalan"
                
                c.execute("""INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan) 
                             VALUES (?,?,?,?,?)""",
                          (kredit_id, jumlah_bayar, denda, datetime.now().strftime("%Y-%m-%d"), keterangan))
                c.execute("""UPDATE kredit SET sisa_hutang=?, jatuh_tempo=?, status=? WHERE id=?""",
                          (sisa_baru, tgl_next, status_baru, kredit_id))
                conn.commit()
                log_aksi(st.session_state.username, "PEMBAYARAN", f"Kredit #{kredit_id}, Rp {jumlah_bayar:,.0f}")
                st.success(f"✅ Pembayaran {format_rp(jumlah_bayar)} berhasil! Sisa: {format_rp(sisa_baru)}")
                if status_baru == "Lunas":
                    st.balloons()
                    st.success("🎉 Kredit LUNAS!")
                st.rerun()
        
        st.markdown('<div class="section-header"><h3>📜 Riwayat Pembayaran Akun Ini</h3></div>', unsafe_allow_html=True)
        df_riw = pd.read_sql_query("""
            SELECT tanggal, jumlah_bayar, denda, keterangan 
            FROM pembayaran WHERE kredit_id=? ORDER BY id DESC
        """, conn, params=(kredit_id,))
        if not df_riw.empty:
            df_riw['jumlah_bayar'] = df_riw['jumlah_bayar'].apply(format_rp)
            df_riw['denda'] = df_riw['denda'].apply(format_rp)
            st.dataframe(df_riw, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pembayaran untuk akun ini")


# ==================== 5. DATA CUSTOMER ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Pelanggan</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Tambah Customer", "📋 Daftar & Riwayat"])
    
    with tab1:
        with st.form("form_cust"):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nama Lengkap")
                t = st.text_input("Telepon/WA")
            with col2:
                a = st.text_area("Alamat")
            if st.form_submit_button("💾 Simpan"):
                if n:
                    c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (n, t, a))
                    conn.commit()
                    log_aksi(st.session_state.username, "TAMBAH_CUSTOMER", n)
                    st.success(f"✅ Customer {n} disimpan!")
                    st.rerun()
                else:
                    st.warning("Nama wajib diisi")
    
    with tab2:
        df_c = pd.read_sql_query("""
            SELECT c.id, c.nama, c.telepon, c.alamat,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id) as total_kredit,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id AND status='Berjalan') as aktif
            FROM customer c ORDER BY c.id DESC
        """, conn)
        st.dataframe(df_c, use_container_width=True, hide_index=True)
        
        # Riwayat per customer
        if not df_c.empty:
            st.markdown('<div class="section-header"><h3>🔍 Riwayat Kredit Customer</h3></div>', unsafe_allow_html=True)
            opsi = {r['nama']: r['id'] for _, r in df_c.iterrows()}
            pilih = st.selectbox("Pilih Customer", list(opsi.keys()))
            cid = opsi[pilih]
            df_riw = pd.read_sql_query("""
                SELECT k.id, p.nama as produk, k.total_hutang, k.sisa_hutang, 
                       k.tenor, k.cicilan_bulan, k.jatuh_tempo, k.status
                FROM kredit k JOIN produk p ON k.produk_id = p.id
                WHERE k.customer_id=? ORDER BY k.id DESC
            """, conn, params=(cid,))
            if not df_riw.empty:
                df_riw['total_hutang'] = df_riw['total_hutang'].apply(format_rp)
                df_riw['sisa_hutang'] = df_riw['sisa_hutang'].apply(format_rp)
                df_riw['cicilan_bulan'] = df_riw['cicilan_bulan'].apply(format_rp)
                st.dataframe(df_riw, use_container_width=True, hide_index=True)
            else:
                st.info("Customer ini belum punya kredit")


# ==================== 6. STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)
    
    df_p = pd.read_sql_query("SELECT * FROM produk ORDER BY stok ASC", conn)
    
    total_item = len(df_p)
    total_unit = df_p['stok'].sum() if not df_p.empty else 0
    total_nilai = (df_p['stok'] * df_p['harga_modal']).sum() if not df_p.empty else 0
    
    html = '<div class="metric-grid">'
    html += metric_card("📦 Jenis Produk", f"{total_item} item", "card-blue")
    html += metric_card("🎒 Total Unit", f"{total_unit} unit", "card-purple")
    html += metric_card("💎 Nilai Stok", format_rp(total_nilai), "card-green")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    
    # Filter
    col1, col2 = st.columns(2)
    with col1:
        filter_kat = st.multiselect("Filter Kategori", df_p['kategori'].unique().tolist(), default=df_p['kategori'].unique().tolist())
    with col2:
        cari = st.text_input("🔍 Cari Nama Produk")
    
    df_f = df_p[df_p['kategori'].isin(filter_kat)]
    if cari:
        df_f = df_f[df_f['nama'].str.contains(cari, case=False, na=False)]
    
    df_f = df_f.copy()
    df_f['harga_modal'] = df_f['harga_modal'].apply(format_rp)
    st.dataframe(df_f, use_container_width=True, hide_index=True)
    
    # Edit/Hapus (admin only)
    if st.session_state.role == "admin" and not df_p.empty:
        st.markdown('<div class="section-header"><h3>✏️ Edit / Hapus Produk</h3></div>', unsafe_allow_html=True)
        opsi_edit = {f"{r['nama']} (ID:{r['id']})": r['id'] for _, r in df_p.iterrows()}
        pilih_edit = st.selectbox("Pilih Produk", list(opsi_edit.keys()))
        pid = opsi_edit[pilih_edit]
        row = c.execute("SELECT nama, kategori, harga_modal, stok FROM produk WHERE id=?", (pid,)).fetchone()
        
        with st.form("form_edit"):
            col1, col2 = st.columns(2)
            with col1:
                new_nama = st.text_input("Nama", row[0])
                new_kat = st.selectbox("Kategori", ["Gadget","Elektronik","Furnitur","Motor","Lainnya"], 
                                       index=["Gadget","Elektronik","Furnitur","Motor","Lainnya"].index(row[1]) if row[1] in ["Gadget","Elektronik","Furnitur","Motor","Lainnya"] else 0)
            with col2:
                new_harga = st.number_input("Harga Modal", value=float(row[2]), step=1000.0)
                new_stok = st.number_input("Stok", value=int(row[3]), step=1)
            
            colA, colB = st.columns(2)
            with colA:
                simpan = st.form_submit_button("💾 Update")
            with colB:
                hapus = st.form_submit_button("🗑️ Hapus")
            
            if simpan:
                c.execute("UPDATE produk SET nama=?, kategori=?, harga_modal=?, stok=? WHERE id=?",
                          (new_nama, new_kat, new_harga, new_stok, pid))
                conn.commit()
                log_aksi(st.session_state.username, "EDIT_PRODUK", f"ID {pid}")
                st.success("✅ Produk diupdate!")
                st.rerun()
            if hapus:
                c.execute("DELETE FROM produk WHERE id=?", (pid,))
                conn.commit()
                log_aksi(st.session_state.username, "HAPUS_PRODUK", f"ID {pid}")
                st.success("🗑️ Produk dihapus!")
                st.rerun()


# ==================== 7. OVERDUE & DENDA ====================
elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Daftar Kredit Overdue</h1></div>', unsafe_allow_html=True)
    
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    df_ov = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, c.telepon, p.nama as produk,
               k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo, k.tenor
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id
        JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ?
        ORDER BY k.jatuh_tempo
    """, conn, params=(tgl_skrg,))
    
    if df_ov.empty:
        st.success("✅ Tidak ada akun overdue hari ini")
        st.snow()
    else:
        df_ov['hari_telat'] = df_ov['jatuh_tempo'].apply(
            lambda x: (datetime.now().date() - datetime.strptime(x, "%Y-%m-%d").date()).days)
        df_ov['denda'] = df_ov.apply(lambda r: round(r['cicilan_bulan'] * 0.01 * r['hari_telat'], -2), axis=1)
        
        total_denda = df_ov['denda'].sum()
        total_tunggakan = df_ov['sisa_hutang'].sum()
        
        html = '<div class="metric-grid">'
        html += metric_card("⚠️ Akun Overdue", f"{len(df_ov)} akun", "card-pink")
        html += metric_card("💰 Total Tunggakan", format_rp(total_tunggakan), "card-dark")
        html += metric_card("💸 Total Denda", format_rp(total_denda), "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        df_show = df_ov.copy()
        df_show['cicilan_bulan'] = df_show['cicilan_bulan'].apply(format_rp)
        df_show['sisa_hutang'] = df_show['sisa_hutang'].apply(format_rp)
        df_show['denda'] = df_show['denda'].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)


# ==================== 8. ALERT & REMINDER ====================
elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder Otomatis</h1></div>', unsafe_allow_html=True)
    
    tgl_skrg = datetime.now().date()
    
    # Overdue
    st.markdown('<div class="section-header"><h3>🚨 Sudah Jatuh Tempo</h3></div>', unsafe_allow_html=True)
    df_ov = pd.read_sql_query("""
        SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo, k.tenor, k.sisa_hutang
        FROM kredit k JOIN customer c ON k.customer_id=c.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ?
    """, conn, params=(tgl_skrg.strftime("%Y-%m-%d"),))
    
    if df_ov.empty:
        st.success("✅ Tidak ada yang overdue")
    else:
        for _, r in df_ov.iterrows():
            hari = (tgl_skrg - datetime.strptime(r['jatuh_tempo'], "%Y-%m-%d").date()).days
            col1, col2 = st.columns([4, 1])
            with col1:
                st.error(f"⚠️ **{r['nama']}** ({r['telepon']}) - Telat **{hari} hari** | Cicilan: {format_rp(r['cicilan_bulan'])} | Tempo: {r['jatuh_tempo']}")
            with col2:
                if r['telepon']:
                    nomor = r['telepon'].replace('-','').replace(' ','')
                    if nomor.startswith('0'): nomor = '62' + nomor[1:]
                    pesan = f"Halo {r['nama']}, cicilan Anda sebesar {format_rp(r['cicilan_bulan'])} sudah jatuh tempo pada {r['jatuh_tempo']} ({hari} hari lalu). Mohon segera diselesaikan. Terima kasih 🙏"
                    wa_link = f"https://wa.me/{nomor}?text={quote(pesan)}"
                    st.markdown(f'<a href="{wa_link}" target="_blank" style="text-decoration:none;"><button style="background:#25D366;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;font-weight:600;">📱 WA</button></a>', unsafe_allow_html=True)
    
    # H-3 Reminder
    st.markdown('<div class="section-header"><h3>⏰ Akan Jatuh Tempo 3 Hari</h3></div>', unsafe_allow_html=True)
    tgl_h3 = (tgl_skrg + timedelta(days=3)).strftime("%Y-%m-%d")
    df_h3 = pd.read_sql_query("""
        SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo
        FROM kredit k JOIN customer c ON k.customer_id=c.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?
    """, conn, params=(tgl_skrg.strftime("%Y-%m-%d"), tgl_h3))
    
    if df_h3.empty:
        st.info("Tidak ada jatuh tempo 3 hari ke depan")
    else:
        for _, r in df_h3.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.warning(f"📢 **{r['nama']}** ({r['telepon']}) - Jatuh tempo {r['jatuh_tempo']} | Cicilan: {format_rp(r['cicilan_bulan'])}")
            with col2:
                if r['telepon']:
                    nomor = r['telepon'].replace('-','').replace(' ','')
                    if nomor.startswith('0'): nomor = '62' + nomor[1:]
                    pesan = f"Halo {r['nama']}, ini reminder cicilan Anda {format_rp(r['cicilan_bulan'])} akan jatuh tempo pada {r['jatuh_tempo']}. Terima kasih 🙏"
                    wa_link = f"https://wa.me/{nomor}?text={quote(pesan)}"
                    st.markdown(f'<a href="{wa_link}" target="_blank" style="text-decoration:none;"><button style="background:#25D366;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;font-weight:600;">📱 WA</button></a>', unsafe_allow_html=True)


# ==================== 9. LAPORAN & ANALITIK ====================
elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📈 Penjualan", "💵 Pembayaran", "📦 Stok"])
    
    with tab1:
        df_k = pd.read_sql_query("""
            SELECT k.id, k.total_hutang, k.dp, k.harga_cash, p.harga_modal, 
                   k.harga_cash - p.harga_modal as laba, k.status, k.jatuh_tempo, p.nama as produk
            FROM kredit k JOIN produk p ON k.produk_id = p.id
        """, conn)
        
        if not df_k.empty:
            html = '<div class="metric-grid">'
            html += metric_card("Total Transaksi", f"{len(df_k)}", "card-blue")
            html += metric_card("Total Nilai Kredit", format_rp(df_k['total_hutang'].sum()), "card-purple")
            html += metric_card("Total DP Masuk", format_rp(df_k['dp'].sum()), "card-green")
            html += metric_card("Estimasi Laba", format_rp(df_k['laba'].sum()), "card-pink")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
            
            st.markdown("**🏆 Distribusi Laba per Produk**")
            df_g = df_k.groupby('produk')['laba'].sum().reset_index().sort_values('laba', ascending=False).head(10)
            chart = alt.Chart(df_g).mark_bar(cornerRadiusTopRight=8, cornerRadiusBottomRight=8).encode(
                x=alt.X('laba:Q', title='Laba (Rp)'),
                y=alt.Y('produk:N', sort='-x', title=''),
                color=alt.Color('laba:Q', scale=alt.Scale(scheme='reds'), legend=None)
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada data")
    
    with tab2:
        df_b = pd.read_sql_query("""
            SELECT p.tanggal, c.nama, p.jumlah_bayar, p.denda, p.keterangan
            FROM pembayaran p 
            JOIN kredit k ON p.kredit_id = k.id
            JOIN customer c ON k.customer_id = c.id
            ORDER BY p.id DESC
        """, conn)
        if not df_b.empty:
            html = '<div class="metric-grid">'
            html += metric_card("Total Pemasukan", format_rp(df_b['jumlah_bayar'].sum()), "card-green")
            html += metric_card("Total Denda", format_rp(df_b['denda'].sum()), "card-orange")
            html += metric_card("Jumlah Transaksi", f"{len(df_b)}", "card-blue")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
            df_b['jumlah_bayar'] = df_b['jumlah_bayar'].apply(format_rp)
            df_b['denda'] = df_b['denda'].apply(format_rp)
            st.dataframe(df_b, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pembayaran")
    
    with tab3:
        df_p = pd.read_sql_query("SELECT kategori, SUM(stok) as total_stok, COUNT(*) as jenis FROM produk GROUP BY kategori", conn)
        if not df_p.empty:
            chart = alt.Chart(df_p).mark_arc(innerRadius=60).encode(
                theta=alt.Theta('total_stok:Q'),
                color=alt.Color('kategori:N', scale=alt.Scale(scheme='set3')),
                tooltip=['kategori', 'total_stok', 'jenis']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)


# ==================== 10. BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🖨️ Cetak Invoice", "📤 Ekspor CSV", "📥 Impor CSV", "🗄️ Backup DB"])
    
    with tab1:
        df_k = pd.read_sql_query("""
            SELECT k.id, c.nama as cust, p.nama as produk
            FROM kredit k JOIN customer c ON k.customer_id=c.id JOIN produk p ON k.produk_id=p.id
            ORDER BY k.id DESC
        """, conn)
        if not df_k.empty:
            df_k['label'] = df_k.apply(lambda r: f"#{r['id']} - {r['cust']} - {r['produk']}", axis=1)
            opsi = dict(zip(df_k['label'], df_k['id']))
            pilih = st.selectbox("Pilih Transaksi", list(opsi.keys()))
            kid = opsi[pilih]
            d = pd.read_sql_query("""
                SELECT k.*, c.nama as cn, c.telepon, c.alamat, p.nama as pn
                FROM kredit k JOIN customer c ON k.customer_id=c.id JOIN produk p ON k.produk_id=p.id
                WHERE k.id=?
            """, conn, params=(kid,)).iloc[0]
            
            st.markdown(f"""
            <div style="background:white; padding:30px; border-radius:15px; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                <div style="text-align:center; border-bottom:2px dashed #667eea; padding-bottom:15px; margin-bottom:20px;">
                    <h2 style="color:#667eea; margin:0;">🏪 TOKO KREDIT PRO</h2>
                    <p style="color:#888; margin:5px 0;">Invoice / Akad Kredit</p>
                </div>
                <p><b>No. Transaksi:</b> #{d['id']}</p>
                <p><b>Tanggal Cetak:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
                <hr>
                <h4>👤 Data Customer</h4>
                <p><b>Nama:</b> {d['cn']}<br>
                <b>Telepon:</b> {d['telepon']}<br>
                <b>Alamat:</b> {d['alamat']}</p>
                <h4>📱 Produk</h4>
                <p><b>Nama:</b> {d['pn']}</p>
                <h4>💰 Rincian Pembayaran</h4>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="background:#f5f5f5;"><td style="padding:8px;"><b>Harga Cash</b></td><td style="padding:8px; text-align:right;">{format_rp(d['harga_cash'])}</td></tr>
                    <tr><td style="padding:8px;"><b>DP</b></td><td style="padding:8px; text-align:right;">{format_rp(d['dp'])}</td></tr>
                    <tr style="background:#f5f5f5;"><td style="padding:8px;"><b>Pokok Hutang</b></td><td style="padding:8px; text-align:right;">{format_rp(d['pokok_hutang'])}</td></tr>
                    <tr><td style="padding:8px;"><b>Total Hutang (+ Bunga)</b></td><td style="padding:8px; text-align:right;"><b>{format_rp(d['total_hutang'])}</b></td></tr>
                    <tr style="background:#f5f5f5;"><td style="padding:8px;"><b>Tenor</b></td><td style="padding:8px; text-align:right;">{d['tenor']} bulan</td></tr>
                    <tr><td style="padding:8px;"><b>Cicilan / Bulan</b></td><td style="padding:8px; text-align:right;"><b style="color:#e74c3c;">{format_rp(d['cicilan_bulan'])}</b></td></tr>
                    <tr style="background:#f5f5f5;"><td style="padding:8px;"><b>Sisa Hutang</b></td><td style="padding:8px; text-align:right;">{format_rp(d['sisa_hutang'])}</td></tr>
                    <tr><td style="padding:8px;"><b>Jatuh Tempo Pertama</b></td><td style="padding:8px; text-align:right;">{d['jatuh_tempo']}</td></tr>
                    <tr style="background:#f5f5f5;"><td style="padding:8px;"><b>Status</b></td><td style="padding:8px; text-align:right;">{d['status']}</td></tr>
                </table>
                <p style="text-align:center; margin-top:30px; color:#888;">Terima kasih telah berbelanja 🙏</p>
            </div>
            """, unsafe_allow_html=True)
            
            html_inv = f"""<html><head><meta charset="utf-8"><title>Invoice #{kid}</title>
            <style>body{{font-family:Arial;padding:20px;max-width:700px;margin:auto;}}
            table{{width:100%;border-collapse:collapse;}} td{{padding:8px;border-bottom:1px solid #eee;}}
            h2{{color:#667eea;text-align:center;}}</style></head><body>
            <h2>🏪 TOKO KREDIT PRO</h2><p style="text-align:center;">Invoice / Akad Kredit</p><hr>
            <p><b>No. Transaksi:</b> #{d['id']}<br><b>Tanggal:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
            <h3>👤 Customer</h3><p>{d['cn']}<br>Telp: {d['telepon']}<br>{d['alamat']}</p>
            <h3>📱 Produk</h3><p>{d['pn']}</p>
            <h3>💰 Rincian</h3><table>
            <tr><td><b>Harga Cash</b></td><td align="right">{format_rp(d['harga_cash'])}</td></tr>
            <tr><td><b>DP</b></td><td align="right">{format_rp(d['dp'])}</td></tr>
            <tr><td><b>Pokok Hutang</b></td><td align="right">{format_rp(d['pokok_hutang'])}</td></tr>
            <tr><td><b>Total Hutang</b></td><td align="right">{format_rp(d['total_hutang'])}</td></tr>
            <tr><td><b>Tenor</b></td><td align="right">{d['tenor']} bulan</td></tr>
            <tr><td><b>Cicilan/Bulan</b></td><td align="right">{format_rp(d['cicilan_bulan'])}</td></tr>
            <tr><td><b>Sisa Hutang</b></td><td align="right">{format_rp(d['sisa_hutang'])}</td></tr>
            <tr><td><b>Jatuh Tempo</b></td><td align="right">{d['jatuh_tempo']}</td></tr>
            </table><p style="text-align:center;color:#888;margin-top:40px;">Terima kasih 🙏</p></body></html>"""
            
            st.download_button("📥 Download Invoice (HTML)", html_inv, f"invoice_{kid}.html", "text/html")
    
    with tab2:
        tabel = st.selectbox("Pilih Data", ["Produk", "Customer", "Kredit", "Transaksi Masuk", "Pembayaran", "Log Aktivitas"])
        map_tabel = {
            "Produk": "produk", "Customer": "customer", "Kredit": "kredit",
            "Transaksi Masuk": "transaksi_in", "Pembayaran": "pembayaran", "Log Aktivitas": "log_aktivitas"
        }
        df = pd.read_sql_query(f"SELECT * FROM {map_tabel[tabel]}", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(f"📥 Download {tabel}.csv", csv, f"{tabel.lower()}.csv", "text/csv")
        else:
            st.info("Kosong")
    
    with tab3:
        jenis = st.selectbox("Jenis Impor", ["Produk", "Customer"])
        if jenis == "Produk":
            st.markdown("Format: `nama, kategori, harga_modal, stok`")
            tpl = pd.DataFrame(columns=["nama","kategori","harga_modal","stok"]).to_csv(index=False).encode()
            st.download_button("📥 Template Produk", tpl, "template_produk.csv", "text/csv")
        else:
            st.markdown("Format: `nama, telepon, alamat`")
            tpl = pd.DataFrame(columns=["nama","telepon","alamat"]).to_csv(index=False).encode()
            st.download_button("📥 Template Customer", tpl, "template_customer.csv", "text/csv")
        
        f = st.file_uploader(f"Upload CSV {jenis}", type=["csv"])
        if f is not None:
            try:
                df_imp = pd.read_csv(f)
                st.dataframe(df_imp.head(), use_container_width=True)
                if st.button("✅ Proses Impor"):
                    if jenis == "Produk":
                        for _, r in df_imp.iterrows():
                            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)",
                                      (r['nama'], r['kategori'], r['harga_modal'], r['stok']))
                    else:
                        for _, r in df_imp.iterrows():
                            c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)",
                                      (r['nama'], r['telepon'], r['alamat']))
                    conn.commit()
                    log_aksi(st.session_state.username, "IMPOR", f"{jenis}: {len(df_imp)} baris")
                    st.success(f"✅ Berhasil impor {len(df_imp)} data!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with tab4:
        st.markdown("### 🗄️ Backup Database")
        st.info("Download file database SQLite sebagai backup. Simpan di tempat aman.")
        conn.commit()
        with open('toko_kredit.db', 'rb') as f:
            st.download_button("💾 Download Backup DB", f.read(), 
                              f"backup_toko_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                              "application/octet-stream")


# ==================== 11. MANAJEMEN USER (ADMIN) ====================
elif pilihan == "👤 Manajemen User" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1></div>', unsafe_allow_html=True)
    
    with st.expander("➕ Tambah User Baru", expanded=True):
        with st.form("form_user"):
            col1, col2 = st.columns(2)
            with col1:
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
            with col2:
                n = st.text_input("Nama Lengkap")
                r = st.selectbox("Role", ["kasir", "admin"])
            if st.form_submit_button("💾 Simpan"):
                if u and p and n:
                    try:
                        c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)",
                                  (u, hash_password(p), n, r))
                        conn.commit()
                        st.success(f"✅ User {u} ditambahkan!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Username sudah ada")
                else:
                    st.warning("Semua field wajib diisi")
    
    st.markdown('<div class="section-header"><h3>📋 Daftar User</h3></div>', unsafe_allow_html=True)
    df_u = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users", conn)
    st.dataframe(df_u, use_container_width=True, hide_index=True)
    
    # Toggle aktif
    opsi = {f"{r['username']} ({r['nama_lengkap']})": r['id'] for _, r in df_u.iterrows()}
    pilih_u = st.selectbox("Pilih User", list(opsi.keys()))
    uid = opsi[pilih_u]
    current = c.execute("SELECT aktif FROM users WHERE id=?", (uid,)).fetchone()[0]
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{'🚫 Nonaktifkan' if current else '✅ Aktifkan'}"):
            c.execute("UPDATE users SET aktif=? WHERE id=?", (0 if current else 1, uid))
            conn.commit()
            st.success("Status diubah!")
            st.rerun()
    with col2:
        if uid != 1:  # jangan hapus admin utama
            if st.button("🗑️ Hapus User"):
                c.execute("DELETE FROM users WHERE id=?", (uid,))
                conn.commit()
                st.success("User dihapus!")
                st.rerun()


# ==================== 12. LOG AKTIVITAS (ADMIN) ====================
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas Sistem</h1></div>', unsafe_allow_html=True)
    
    df_log = pd.read_sql_query("SELECT * FROM log_aktivitas ORDER BY id DESC LIMIT 200", conn)
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Log CSV", csv, "log_aktivitas.csv", "text/csv")
    else:
        st.info("Belum ada aktivitas")
