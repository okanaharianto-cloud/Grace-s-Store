import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
import uuid
import base64
from datetime import datetime, timedelta
import altair as alt
import streamlit.components.v1 as components
import io
from PIL import Image
import zipfile

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="GRACE'S STORE (CASH & CREDIT)",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px; border-radius: 15px; color: white; text-align: center;
        margin-bottom: 25px; box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    .main-header h1 { color: white !important; margin: 0; font-size: 2.2em; }
    .main-header p { color: #f0f0f0; margin: 5px 0 0 0; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
    .metric-card { padding: 20px; border-radius: 15px; color: white; box-shadow: 0 6px 15px rgba(0,0,0,0.15); transition: transform 0.2s; }
    .metric-card:hover { transform: translateY(-4px); }
    .metric-card .label { font-size: 0.85em; opacity: 0.9; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card .value { font-size: 1.6em; font-weight: bold; }
    .card-blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .card-purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .card-pink { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .card-green { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .card-orange { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    .card-dark { background: linear-gradient(135deg, #232526 0%, #414345 100%); }
    .section-header { background: white; padding: 15px 20px; border-radius: 12px; border-left: 5px solid #667eea; margin: 20px 0 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .section-header h3 { margin: 0; color: #333; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%); }
    section[data-testid="stSidebar"] * { color: #ecf0f1 !important; }
    .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; border: none; border-radius: 10px; padding: 10px 20px; font-weight: 600; transition: all 0.3s; width: 100%; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(102,126,234,0.5); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background: white; border-radius: 10px 10px 0 0; padding: 10px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; }
</style>
""", unsafe_allow_html=True)

# ==================== KONSTANTA ====================
PAKAIAN_KATEGORI = ["Pakaian", "Atasan", "Bawahan", "Dress", "Outerwear", "Batik"]
SEMUA_KATEGORI = ["Gadget", "Elektronik", "Pakaian", "Atasan", "Bawahan", "Dress", "Outerwear", "Batik", "Furnitur", "Motor", "Lainnya"]
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==================== KONEKSI DATABASE ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "toko_kredit.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

conn = get_connection()
c = conn.cursor()

# ==================== STRUKTUR DATABASE ====================
c.execute('''CREATE TABLE IF NOT EXISTS produk (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_cash (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, harga_jual_satuan REAL, total_harga REAL, uang_bayar REAL, kembalian REAL, laba REAL, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customer (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, telepon TEXT, alamat TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS kredit (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, produk_id INTEGER, harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, tenor INTEGER, cicilan_bulan REAL, sisa_hutang REAL, jatuh_tempo TEXT, status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS pembayaran (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, jumlah_bayar REAL, denda REAL, tanggal TEXT, keterangan TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, nama_lengkap TEXT, role TEXT, aktif INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS log_aktivitas (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, aksi TEXT, detail TEXT, waktu TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS pengaturan (kunci TEXT PRIMARY KEY, nilai TEXT, keterangan TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS jadwal_kustom (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, opsi TEXT, ke INTEGER, jatuh_tempo TEXT, angsuran REAL, sisa REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS serah_terima (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, imei TEXT, foto_bukti TEXT, tanggal_serah TEXT, penerima TEXT)''')
conn.commit()

# ==================== MIGRASI KOLOM ====================
for sql in [
    "ALTER TABLE produk ADD COLUMN markup_persen REAL DEFAULT 5.0",
    "ALTER TABLE produk ADD COLUMN harga_jual REAL",
    "ALTER TABLE transaksi_cash ADD COLUMN harga_jual_satuan REAL DEFAULT 0",
    "ALTER TABLE transaksi_cash ADD COLUMN laba REAL DEFAULT 0",
    "ALTER TABLE kredit ADD COLUMN tanggal_kredit TEXT",
    "ALTER TABLE kredit ADD COLUMN updated_at TEXT",
    "ALTER TABLE kredit ADD COLUMN updated_by TEXT",
    "ALTER TABLE customer ADD COLUMN nik TEXT",
    "ALTER TABLE customer ADD COLUMN tanggal_lahir TEXT",
    "ALTER TABLE customer ADD COLUMN status_kawin TEXT",
    "ALTER TABLE customer ADD COLUMN foto_ktp TEXT",
    "ALTER TABLE customer ADD COLUMN foto_kk TEXT"
]:
    try:
        c.execute(sql); conn.commit()
    except sqlite3.OperationalError:
        pass

try:
    c.execute("UPDATE kredit SET tanggal_kredit = date(jatuh_tempo, '-30 days') WHERE tanggal_kredit IS NULL")
    conn.commit()
except Exception:
    pass

# ==================== SEED PENGATURAN ====================
DEFAULT_PENGATURAN = {
    "markup_default_persen":     ("5.0",   "Markup default (%) untuk produk non-pakaian"),
    "bunga_flat_6bln_persen":    ("40.0",  "Bunga flat per 6 bulan (%) untuk kredit"),
    "dp_minimal_persen":         ("20.0",  "DP minimal (%) dari harga cash"),
    "denda_per_hari_persen":     ("0.4",   "Denda keterlambatan per hari (%) dari cicilan"),
    "tenor_options":             ("1,2,3,6,12,18,24", "Pilihan tenor (bulan), pisahkan dengan koma"),
    # Profil Default untuk Invoice
    "bisnis_nama":               ("GRACE'S ELECTRONIC", "Nama Perusahaan"),
    "bisnis_alamat":             ("Sekolah Darat RT 007 RW 000, Kutai Barat, Kalimantan Timur", "Alamat Perusahaan"),
    "bisnis_telepon":            ("0822-9954-8411", "Telepon Perusahaan"),
    "bisnis_email":              ("gracehaven.transport@gmail.com", "Email Perusahaan"),
    "bank_nama":                 ("Bank Mandiri", "Nama Bank"),
    "bank_rekening":             ("148-00-2889246-4", "Nomor Rekening"),
    "bank_atas_nama":            ("CV GRACE HAVEN TRANSPORT", "Atas Nama Rekening"),
    "tema_warna":                ("#1e3a8a", "Warna Tema Dokumen (Hex)"),
    "bisnis_logo":               ("", "Path file Logo"),
    "bisnis_ttd":                ("", "Path file Tanda Tangan"),
}
for k, (v, ket) in DEFAULT_PENGATURAN.items():
    c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai, keterangan) VALUES (?,?,?)", (k, v, ket))
conn.commit()

# ==================== HELPER FUNCTIONS ====================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def format_rp(n):
    try:
        return f"Rp {float(n):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"

def get_pengaturan(kunci, default=None):
    cache_key = f"_setting_{kunci}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    row = c.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (kunci,)).fetchone()
    val = row[0] if row else default
    st.session_state[cache_key] = val
    return val

def get_pengaturan_float(kunci, default=0.0):
    try:
        return float(get_pengaturan(kunci, default))
    except (ValueError, TypeError):
        return float(default)

def get_tenor_list():
    raw = get_pengaturan("tenor_options", "1,2,3,6,12,18,24")
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except Exception:
        return [1, 2, 3, 6, 12, 18, 24]

def set_pengaturan(kunci, nilai, keterangan=None):
    c.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai, keterangan) VALUES (?,?,?)", (kunci, str(nilai), keterangan or ""))
    conn.commit()
    st.session_state.pop(f"_setting_{kunci}", None)

def log_aksi(username, aksi, detail=""):
    try:
        c.execute("INSERT INTO log_aktivitas (username, aksi, detail, waktu) VALUES (?,?,?,?)", (username, aksi, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception:
        conn.rollback()

def metric_card(label, value, warna="card-blue"):
    return f'<div class="metric-card {warna}"><div class="label">{label}</div><div class="value">{value}</div></div>'

def flash(msg, typ="success"):
    st.session_state.flash = (msg, typ)

def show_flash():
    if st.session_state.get("flash"):
        msg, typ = st.session_state.flash
        getattr(st, typ)(msg)
        st.session_state.flash = None
    if st.session_state.get("balloons"):
        st.balloons(); st.session_state.balloons = False

def hitung_harga_cash(harga_modal, markup_persen, harga_jual):
    if harga_jual and float(harga_jual) > 0:
        return float(harga_jual)
    mk = markup_persen if markup_persen is not None else get_pengaturan_float("markup_default_persen", 5.0)
    return round(float(harga_modal) * (1 + float(mk) / 100), -2)

def recalculate_kredit(kredit_id):
    row = c.execute("SELECT total_hutang FROM kredit WHERE id=?", (kredit_id,)).fetchone()
    if not row: return
    total_hutang = row[0]
    res = c.execute("SELECT COALESCE(SUM(jumlah_bayar - denda), 0) FROM pembayaran WHERE kredit_id=?", (kredit_id,)).fetchone()
    total_principal_paid = res[0]
    new_sisa = max(total_hutang - total_principal_paid, 0)
    new_sisa = round(new_sisa, -2)
    new_status = "Lunas" if new_sisa <= 0 else "Berjalan"
    c.execute("UPDATE kredit SET sisa_hutang=?, status=? WHERE id=?", (new_sisa, new_status, kredit_id))
    conn.commit()

def hitung_denda(cicilan_bulan, hari_telat):
    persen = get_pengaturan_float("denda_per_hari_persen", 0.4)
    if hari_telat <= 0:
        return 0.0
    return round(cicilan_bulan * (persen / 100) * hari_telat, -2)

def build_jadwal_angsuran(total_hutang, cicilan_bulan, tenor, tanggal_kredit_str):
    try:
        tgl = datetime.strptime(tanggal_kredit_str, "%Y-%m-%d")
    except Exception:
        tgl = datetime.now()
    schedule = []
    sisa = float(total_hutang)
    for i in range(1, int(tenor) + 1):
        tgl = tgl + timedelta(days=30)
        if i == int(tenor) or sisa <= float(cicilan_bulan):
            bayar = sisa
        else:
            bayar = float(cicilan_bulan)
        sisa = max(sisa - bayar, 0)
        schedule.append({"ke": i, "jatuh_tempo": tgl.strftime("%d-%m-%Y"), "angsuran": bayar, "sisa": sisa})
    return schedule

def get_schedule_for_invoice(kredit_id, opsi, total, cicilan, tenor, tgl_str):
    df_custom = pd.read_sql_query("SELECT ke, jatuh_tempo, angsuran, sisa FROM jadwal_kustom WHERE kredit_id=? AND opsi=? ORDER BY ke", conn, params=(kredit_id, opsi))
    if not df_custom.empty:
        return df_custom
    else:
        return pd.DataFrame(build_jadwal_angsuran(total, cicilan, tenor, tgl_str))

def save_uploaded_file(uploaded_file, prefix):
    if uploaded_file is not None:
        ext = uploaded_file.name.split('.')[-1].lower()
        file_path = os.path.join(UPLOAD_DIR, f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

# Seed admin
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", ("admin", hash_password("admin123"), "Administrator", "admin"))
    conn.commit()

# ==================== LOGIN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.nama = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.markdown('<div class="main-header"><h1>🏪 GRACE\'S STORE</h1><p>Sistem Manajemen Toko & Cicilan</p></div>', unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
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
        "🛒 Jual Cash", 
        "📤 Kredit Baru",
        "💰 Pembayaran Cicilan", 
        "🖨️ Cetak Slip Kredit",
        "👥 Data Customer", 
        "🤝 Serah Terima Barang",
        "📦 Stok Barang",
        "🚨 Overdue & Denda", 
        "🔔 Alert & Reminder", 
        "📊 Laporan & Analitik",
        "👕 Modal vs Profit", 
        "💾 Backup, Cetak & Impor",
        "🏢 Profil & Tema",
        "📄 Dokumen Bisnis",
    ]
    if st.session_state.role == "admin":
        menu_list.extend(["⚙️ Pengaturan Owner", "👤 Manajemen User", "📝 Log Aktivitas"])

    pilihan = st.radio("📋 Menu", menu_list)
    st.markdown("---")
    if st.button("🚪 Logout"):
        log_aksi(st.session_state.username, "LOGOUT")
        for k in ["logged_in", "username", "nama", "role"]:
            st.session_state[k] = False if k == "logged_in" else ""
        st.session_state.pop("flash", None)
        st.session_state.pop("balloons", None)
        for k in list(st.session_state.keys()):
            if k.startswith("_setting_"):
                st.session_state.pop(k, None)
        st.rerun()

show_flash()
# ==================== ROUTING UTAMA ====================
if pilihan == "🏠 Dashboard":
    st.markdown('<div class="main-header"><h1>🏠 Dashboard</h1><p>Ringkasan bisnis Anda hari ini</p></div>', unsafe_allow_html=True)
    total_produk = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    total_stok = c.execute("SELECT COALESCE(SUM(stok),0) FROM produk").fetchone()[0]
    total_cash = c.execute("SELECT COALESCE(SUM(total_harga),0) FROM transaksi_cash").fetchone()[0]
    total_kredit_aktif = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    total_piutang = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    total_laba_cash = c.execute("SELECT COALESCE(SUM(laba),0) FROM transaksi_cash").fetchone()[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Total Produk", total_produk, "card-blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Total Stok", f"{total_stok:,}".replace(",","."), "card-purple"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Penjualan Cash", format_rp(total_cash), "card-green"), unsafe_allow_html=True)
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(metric_card("Kredit Aktif", total_kredit_aktif, "card-pink"), unsafe_allow_html=True)
    with col5:
        st.markdown(metric_card("Total Piutang", format_rp(total_piutang), "card-orange"), unsafe_allow_html=True)
    with col6:
        st.markdown(metric_card("Laba Cash", format_rp(total_laba_cash), "card-dark"), unsafe_allow_html=True)

    st.markdown('<div class="section-header"><h3>📈 Grafik Penjualan 7 Hari Terakhir</h3></div>', unsafe_allow_html=True)
    df_cash = pd.read_sql_query("""
        SELECT date(tanggal) as tgl, SUM(total_harga) as total
        FROM transaksi_cash
        WHERE date(tanggal) >= date('now','-7 days')
        GROUP BY date(tanggal) ORDER BY tgl
    """, conn)
    df_kredit = pd.read_sql_query("""
        SELECT date(tanggal_kredit) as tgl, SUM(total_hutang) as total
        FROM kredit
        WHERE date(tanggal_kredit) >= date('now','-7 days')
        GROUP BY date(tanggal_kredit) ORDER BY tgl
    """, conn)
    if not df_cash.empty or not df_kredit.empty:
        df_gab = pd.DataFrame({"Tanggal": pd.concat([df_cash["tgl"], df_kredit["tgl"]]).unique()})
        df_gab["Cash"] = df_gab["Tanggal"].map(df_cash.set_index("tgl")["total"]).fillna(0)
        df_gab["Kredit"] = df_gab["Tanggal"].map(df_kredit.set_index("tgl")["total"]).fillna(0)
        df_gab = df_gab.sort_values("Tanggal")
        st.bar_chart(df_gab.set_index("Tanggal")[["Cash","Kredit"]])
    else:
        st.info("Belum ada transaksi dalam 7 hari terakhir.")

    st.markdown('<div class="section-header"><h3>📋 5 Transaksi Terakhir</h3></div>', unsafe_allow_html=True)
    df_last_cash = pd.read_sql_query("""
        SELECT tc.id as ID, p.nama as Produk, tc.jumlah as Jumlah,
               tc.total_harga as Total, tc.tanggal as Tanggal, 'Cash' as Tipe
        FROM transaksi_cash tc JOIN produk p ON p.id = tc.produk_id
        ORDER BY tc.id DESC LIMIT 5
    """, conn)
    df_last_kredit = pd.read_sql_query("""
        SELECT k.id as ID, p.nama as Produk, k.total_hutang as Total,
               k.tanggal_kredit as Tanggal, 'Kredit' as Tipe
        FROM kredit k JOIN produk p ON p.id = k.produk_id
        ORDER BY k.id DESC LIMIT 5
    """, conn)
    df_last = pd.concat([df_last_cash, df_last_kredit]).sort_values("Tanggal", ascending=False).head(5)
    if not df_last.empty:
        st.dataframe(df_last, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada transaksi.")

elif pilihan == "🧮 Input Produk & Skema":
    st.markdown('<div class="main-header"><h1>🧮 Input Produk & Skema</h1><p>Tambah produk baru dengan markup otomatis</p></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Produk", "📋 Daftar Produk", "⚙️ Skema Bunga & Tenor"])
    with tab1:
        with st.form("form_produk"):
            nama = st.text_input("Nama Produk")
            kategori = st.selectbox("Kategori", SEMUA_KATEGORI)
            col_a, col_b = st.columns(2)
            with col_a:
                harga_modal = st.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0, format="%.0f")
            with col_b:
                markup = st.number_input("Markup (%)", min_value=0.0, value=5.0, step=0.5, format="%.1f",
                                        help="Kosongkan untuk pakai markup default")
            stok = st.number_input("Stok Awal", min_value=0, step=1)
            harga_jual_manual = st.number_input("Harga Jual Manual (Opsional)", min_value=0.0, step=1000.0, format="%.0f",
                                               help="Jika diisi, akan menimpa markup")
            submitted = st.form_submit_button("Simpan Produk")
            if submitted:
                if not nama.strip():
                    st.error("Nama produk harus diisi.")
                elif harga_modal <= 0:
                    st.error("Harga modal harus lebih dari 0.")
                else:
                    harga_jual = harga_jual_manual if harga_jual_manual > 0 else hitung_harga_cash(harga_modal, markup, 0)
                    c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,?,?)",
                              (nama.strip(), kategori, harga_modal, stok, markup, harga_jual_manual if harga_jual_manual > 0 else None))
                    conn.commit()
                    log_aksi(st.session_state.username, "TAMBAH_PRODUK", f"{nama} ({kategori})")
                    flash(f"Produk '{nama}' berhasil ditambahkan dengan harga jual {format_rp(harga_jual)}")
                    st.rerun()
    with tab2:
        df_prod = pd.read_sql_query("""
            SELECT id, nama as Nama, kategori as Kategori, harga_modal as Modal,
                   COALESCE(harga_jual, ROUND(harga_modal*(1+COALESCE(markup_persen,5)/100),-2)) as Jual,
                   stok as Stok
            FROM produk ORDER BY id
        """, conn)
        st.dataframe(df_prod, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader("Hapus Produk")
        hapus_id = st.number_input("ID Produk yang akan dihapus", min_value=1, step=1)
        if st.button("Hapus Produk"):
            c.execute("DELETE FROM produk WHERE id=?", (hapus_id,))
            conn.commit()
            log_aksi(st.session_state.username, "HAPUS_PRODUK", f"ID {hapus_id}")
            flash(f"Produk ID {hapus_id} dihapus.", "warning")
            st.rerun()
    with tab3:
        st.markdown("### ⚙️ Skema Bunga & Tenor")
        st.info("Pengaturan ini digunakan untuk perhitungan kredit dan denda.")
        with st.form("form_skema"):
            bunga = st.number_input("Bunga flat per 6 bulan (%)", value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0)
            dpmin = st.number_input("DP Minimal (%)", value=get_pengaturan_float("dp_minimal_persen", 20.0), step=1.0)
            denda = st.number_input("Denda per hari (%)", value=get_pengaturan_float("denda_per_hari_persen", 0.4), step=0.1)
            tenor_raw = st.text_input("Tenor (bulan, pisah koma)", value=get_pengaturan("tenor_options", "1,2,3,6,12,18,24"))
            if st.form_submit_button("Simpan Skema"):
                set_pengaturan("bunga_flat_6bln_persen", bunga)
                set_pengaturan("dp_minimal_persen", dpmin)
                set_pengaturan("denda_per_hari_persen", denda)
                set_pengaturan("tenor_options", tenor_raw)
                flash("Skema berhasil diperbarui.")
                st.rerun()

elif pilihan == "📥 Barang Masuk":
    st.markdown('<div class="main-header"><h1>📥 Barang Masuk</h1><p>Catat penambahan stok produk</p></div>', unsafe_allow_html=True)
    produk_list = pd.read_sql_query("SELECT id, nama, stok FROM produk ORDER BY nama", conn)
    if produk_list.empty:
        st.warning("Belum ada produk. Tambahkan produk terlebih dahulu.")
    else:
        with st.form("form_barang_masuk"):
            options = {row['nama']: row['id'] for _, row in produk_list.iterrows()}
            pilih = st.selectbox("Pilih Produk", list(options.keys()))
            jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
            submitted = st.form_submit_button("Tambah Stok")
            if submitted:
                prod_id = options[pilih]
                c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah, prod_id))
                c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)",
                          (prod_id, jumlah, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                log_aksi(st.session_state.username, "BARANG_MASUK", f"{pilih} +{jumlah}")
                flash(f"Stok {pilih} berhasil ditambah {jumlah} unit.")
                st.rerun()
        st.markdown("---")
        st.subheader("📋 Riwayat Barang Masuk")
        df_in = pd.read_sql_query("""
            SELECT ti.id as ID, p.nama as Produk, ti.jumlah as Jumlah, ti.tanggal as Tanggal
            FROM transaksi_in ti JOIN produk p ON p.id = ti.produk_id
            ORDER BY ti.id DESC LIMIT 50
        """, conn)
        st.dataframe(df_in, use_container_width=True, hide_index=True)

elif pilihan == "🛒 Jual Cash":
    st.markdown('<div class="main-header"><h1>🛒 Jual Cash</h1><p>Transaksi penjualan tunai</p></div>', unsafe_allow_html=True)
    produk_list = pd.read_sql_query("SELECT id, nama, stok, harga_modal, harga_jual, markup_persen, kategori FROM produk WHERE stok > 0 ORDER BY nama", conn)
    if produk_list.empty:
        st.warning("Tidak ada produk dengan stok tersedia.")
    else:
        with st.form("form_jual_cash"):
            options = {f"{row['nama']} (Stok: {row['stok']})": row['id'] for _, row in produk_list.iterrows()}
            pilih = st.selectbox("Pilih Produk", list(options.keys()))
            prod_id = options[pilih]
            produk_row = produk_list[produk_list['id'] == prod_id].iloc[0]
            harga_jual_default = hitung_harga_cash(produk_row['harga_modal'], produk_row['markup_persen'], produk_row['harga_jual'])
            col1, col2 = st.columns(2)
            with col1:
                jumlah = st.number_input("Jumlah", min_value=1, max_value=int(produk_row['stok']), step=1, value=1)
            with col2:
                harga_satuan = st.number_input("Harga Jual Satuan (Rp)", min_value=0.0, value=float(harga_jual_default), step=1000.0, format="%.0f")
            total = jumlah * harga_satuan
            st.markdown(f"**Total Harga: {format_rp(total)}**")
            uang_bayar = st.number_input("Uang Dibayar (Rp)", min_value=0.0, step=1000.0, format="%.0f")
            submitted = st.form_submit_button("Proses Pembayaran")
            if submitted:
                if uang_bayar < total:
                    st.error("Uang bayar kurang dari total harga.")
                elif jumlah > produk_row['stok']:
                    st.error("Stok tidak mencukupi.")
                else:
                    kembalian = uang_bayar - total
                    laba = (harga_satuan - produk_row['harga_modal']) * jumlah
                    c.execute("""INSERT INTO transaksi_cash
                                 (produk_id, jumlah, harga_jual_satuan, total_harga, uang_bayar, kembalian, laba, tanggal)
                                 VALUES (?,?,?,?,?,?,?,?)""",
                              (prod_id, jumlah, harga_satuan, total, uang_bayar, kembalian, laba,
                               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    c.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (jumlah, prod_id))
                    conn.commit()
                    log_aksi(st.session_state.username, "JUAL_CASH", f"{produk_row['nama']} x{jumlah} = {format_rp(total)}")
                    flash(f"Transaksi berhasil! Kembalian: {format_rp(kembalian)}", "success")
                    st.session_state.balloons = True
                    st.rerun()
        st.markdown("---")
        st.subheader("📋 Riwayat Penjualan Cash")
        df_cash = pd.read_sql_query("""
            SELECT tc.id as ID, p.nama as Produk, tc.jumlah as Jumlah,
                   tc.total_harga as Total, tc.uang_bayar as Bayar,
                   tc.kembalian as Kembalian, tc.laba as Laba,
                   tc.tanggal as Tanggal
            FROM transaksi_cash tc JOIN produk p ON p.id = tc.produk_id
            ORDER BY tc.id DESC LIMIT 50
        """, conn)
        st.dataframe(df_cash, use_container_width=True, hide_index=True)
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Kredit Baru</h1><p>Buat perjanjian kredit baru</p></div>', unsafe_allow_html=True)

    df_cust = pd.read_sql_query("SELECT id, nama, telepon, alamat, nik FROM customer ORDER BY nama", conn)
    df_prod = pd.read_sql_query("SELECT id, nama, stok, harga_modal, harga_jual, markup_persen, kategori FROM produk WHERE stok > 0 ORDER BY nama", conn)

    if df_prod.empty:
        st.warning("Tidak ada produk dengan stok tersedia. Tambah stok terlebih dahulu.")
    else:
        tab1, tab2 = st.tabs(["➕ Buat Kredit Baru", "📋 Daftar Kredit Aktif"])

        with tab1:
            with st.form("form_kredit_baru"):
                st.subheader("1. Pilih Customer")
                if df_cust.empty:
                    st.info("Belum ada customer. Silakan tambah customer terlebih dahulu di menu Data Customer.")
                    customer_id = None
                else:
                    cust_options = {f"{row['nama']} - {row['telepon'] or ''}": row['id'] for _, row in df_cust.iterrows()}
                    pilih_cust = st.selectbox("Customer", list(cust_options.keys()))
                    customer_id = cust_options[pilih_cust]

                st.subheader("2. Pilih Produk")
                prod_options = {f"{row['nama']} (Stok: {row['stok']})": row['id'] for _, row in df_prod.iterrows()}
                pilih_prod = st.selectbox("Produk", list(prod_options.keys()))
                prod_id = prod_options[pilih_prod]
                produk_row = df_prod[df_prod['id'] == prod_id].iloc[0]
                harga_cash_default = hitung_harga_cash(produk_row['harga_modal'], produk_row['markup_persen'], produk_row['harga_jual'])

                st.subheader("3. Skema Kredit")
                harga_cash = st.number_input("Harga Cash Produk (Rp)", min_value=0.0, value=float(harga_cash_default), step=1000.0, format="%.0f")
                dp_persen = st.number_input("DP (%)", min_value=0.0, max_value=100.0, value=get_pengaturan_float("dp_minimal_persen", 20.0), step=1.0)
                dp = round(harga_cash * dp_persen / 100, -2)
                st.markdown(f"**DP: {format_rp(dp)}**")

                tenor_list = get_tenor_list()
                tenor = st.selectbox("Tenor (bulan)", tenor_list)
                bunga_persen = get_pengaturan_float("bunga_flat_6bln_persen", 40.0)
                bunga_total_persen = bunga_persen * (tenor / 6.0)
                pokok_hutang = harga_cash - dp
                total_hutang = round(pokok_hutang * (1 + bunga_total_persen / 100), -2)
                cicilan_bulan = round(total_hutang / tenor, -2)
                st.markdown(f"**Pokok Hutang: {format_rp(pokok_hutang)}**")
                st.markdown(f"**Total Hutang (dengan bunga {bunga_total_persen:.1f}%): {format_rp(total_hutang)}**")
                st.markdown(f"**Cicilan per bulan: {format_rp(cicilan_bulan)}**")

                submitted = st.form_submit_button("Buat Perjanjian Kredit")
                if submitted:
                    if customer_id is None:
                        st.error("Customer harus dipilih.")
                    elif harga_cash <= 0:
                        st.error("Harga cash harus lebih dari 0.")
                    elif dp < 0:
                        st.error("DP tidak valid.")
                    elif produk_row['stok'] < 1:
                        st.error("Stok produk habis.")
                    else:
                        tanggal_kredit = datetime.now().strftime("%Y-%m-%d")
                        jatuh_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        c.execute("""INSERT INTO kredit
                                     (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit)
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                  (customer_id, prod_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, total_hutang, jatuh_tempo, "Berjalan", tanggal_kredit))
                        kredit_id = c.lastrowid
                        c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (prod_id,))
                        conn.commit()
                        log_aksi(st.session_state.username, "KREDIT_BARU", f"Kredit ID {kredit_id} untuk customer {customer_id}")
                        flash(f"Kredit berhasil dibuat dengan ID {kredit_id}. Total hutang {format_rp(total_hutang)}.")
                        st.session_state.balloons = True
                        st.rerun()

        with tab2:
            st.subheader("📋 Daftar Kredit Aktif")
            df_kredit_aktif = pd.read_sql_query("""
                SELECT k.id as ID, c.nama as Customer, p.nama as Produk,
                       k.total_hutang as Total_Hutang, k.sisa_hutang as Sisa,
                       k.cicilan_bulan as Cicilan, k.tenor as Tenor,
                       k.tanggal_kredit as Tanggal, k.jatuh_tempo as JT
                FROM kredit k
                JOIN customer c ON c.id = k.customer_id
                JOIN produk p ON p.id = k.produk_id
                WHERE k.status = 'Berjalan'
                ORDER BY k.id DESC
            """, conn)
            if df_kredit_aktif.empty:
                st.info("Tidak ada kredit aktif.")
            else:
                st.dataframe(df_kredit_aktif, use_container_width=True, hide_index=True)

elif pilihan == "💰 Pembayaran Cicilan":
    st.markdown('<div class="main-header"><h1>💰 Pembayaran Cicilan</h1><p>Catat pembayaran angsuran kredit</p></div>', unsafe_allow_html=True)

    df_kredit = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.sisa_hutang, k.cicilan_bulan, k.jatuh_tempo, k.status
        FROM kredit k
        JOIN customer c ON c.id = k.customer_id
        JOIN produk p ON p.id = k.produk_id
        WHERE k.status = 'Berjalan'
        ORDER BY k.id DESC
    """, conn)

    if df_kredit.empty:
        st.info("Tidak ada kredit aktif yang perlu dibayar.")
    else:
        with st.form("form_pembayaran"):
            options = {f"ID {row['id']} - {row['customer']} - {row['produk']} (Sisa: {format_rp(row['sisa_hutang'])})": row['id'] for _, row in df_kredit.iterrows()}
            pilih = st.selectbox("Pilih Kredit", list(options.keys()))
            kredit_id = options[pilih]
            row_kredit = df_kredit[df_kredit['id'] == kredit_id].iloc[0]

            st.markdown(f"**Customer:** {row_kredit['customer']}")
            st.markdown(f"**Produk:** {row_kredit['produk']}")
            st.markdown(f"**Sisa Hutang:** {format_rp(row_kredit['sisa_hutang'])}")
            st.markdown(f"**Cicilan per bulan:** {format_rp(row_kredit['cicilan_bulan'])}")
            st.markdown(f"**Jatuh Tempo:** {row_kredit['jatuh_tempo']}")

            jatuh_tempo_dt = datetime.strptime(row_kredit['jatuh_tempo'], "%Y-%m-%d")
            hari_telat = (datetime.now() - jatuh_tempo_dt).days
            denda = hitung_denda(row_kredit['cicilan_bulan'], max(hari_telat, 0))
            if hari_telat > 0:
                st.warning(f"⚠️ Terlambat {hari_telat} hari. Denda: {format_rp(denda)}")
            else:
                st.success("✅ Belum jatuh tempo.")

            jumlah_bayar = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, step=1000.0, format="%.0f")
            keterangan = st.text_input("Keterangan (opsional)")

            submitted = st.form_submit_button("Proses Pembayaran")
            if submitted:
                if jumlah_bayar <= 0:
                    st.error("Jumlah bayar harus lebih dari 0.")
                elif jumlah_bayar > row_kredit['sisa_hutang'] + denda:
                    st.error("Jumlah bayar melebihi sisa hutang + denda.")
                else:
                    c.execute("""INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan)
                                 VALUES (?,?,?,?,?)""",
                              (kredit_id, jumlah_bayar, denda, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), keterangan))
                    conn.commit()
                    recalculate_kredit(kredit_id)
                    log_aksi(st.session_state.username, "PEMBAYARAN", f"Kredit ID {kredit_id} bayar {format_rp(jumlah_bayar)}")
                    flash(f"Pembayaran sebesar {format_rp(jumlah_bayar)} berhasil dicatat.")
                    st.session_state.balloons = True
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Riwayat Pembayaran Terakhir")
        df_bayar = pd.read_sql_query("""
            SELECT pb.id as ID, pb.kredit_id as Kredit_ID, pb.jumlah_bayar as Jumlah,
                   pb.denda as Denda, pb.tanggal as Tanggal, pb.keterangan as Ket
            FROM pembayaran pb
            ORDER BY pb.id DESC LIMIT 20
        """, conn)
        st.dataframe(df_bayar, use_container_width=True, hide_index=True)

elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip & Perjanjian</h1><p>Desain Invoice Modern & Surat Perjanjian Persis PDF</p></div>', unsafe_allow_html=True)

    df_kredit_cetak = pd.read_sql_query("""
        SELECT k.id, c.nama as customer_nama, c.telepon, c.alamat, c.nik, c.tanggal_lahir,
               p.nama as produk_nama, k.harga_cash, k.dp, k.pokok_hutang, k.total_hutang,
               k.tenor, k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo, k.status, k.tanggal_kredit
        FROM kredit k
        JOIN customer c ON c.id = k.customer_id
        JOIN produk p ON p.id = k.produk_id
        ORDER BY k.id DESC
    """, conn)

    if df_kredit_cetak.empty:
        st.info("Belum ada data kredit.")
    else:
        pilih_id = st.selectbox("Pilih ID Kredit untuk dicetak", df_kredit_cetak['id'].tolist())
        kredit_data = df_kredit_cetak[df_kredit_cetak['id'] == pilih_id].iloc[0]

        df_jadwal = pd.DataFrame(build_jadwal_angsuran(
            kredit_data['total_hutang'], kredit_data['cicilan_bulan'],
            kredit_data['tenor'], kredit_data['tanggal_kredit']
        ))

        def format_tgl_indo(tgl_str):
            try:
                dt = datetime.strptime(tgl_str, "%Y-%m-%d")
                bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                return f"{dt.day} {bulan[dt.month-1]} {dt.year}"
            except:
                return tgl_str

        tgl_kredit_indo = format_tgl_indo(kredit_data['tanggal_kredit'])
        jt_pertama_indo = format_tgl_indo(kredit_data['jatuh_tempo'])
        tgl_terakhir = df_jadwal.iloc[-1]['jatuh_tempo'] if not df_jadwal.empty else '-'
        tgl_lahir_indo = format_tgl_indo(kredit_data['tanggal_lahir']) if kredit_data['tanggal_lahir'] else '-'
        
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 0.4)
        biaya_materai = 10000
        cicilan = kredit_data['cicilan_bulan']
        total_bulan_terakhir = cicilan + biaya_materai
        
        # Build Table Rows
        jadwal_rows = ""
        for _, row in df_jadwal.iterrows():
            jadwal_rows += f"""
            <tr>
                <td class="c">{row['ke']}</td>
                <td>{row['jatuh_tempo']}</td>
                <td class="r">{format_rp(row['angsuran'])}</td>
                <td class="c"><span class="status-badge">BELUM</span></td>
            </tr>"""

        # Build HTML
        html_slip = f"""
        <!DOCTYPE html>
        <html lang="id">
        <head>
        <meta charset="utf-8">
        <title>Invoice Kredit - GRACE'S ELECTRONIC</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #e2e8f0; padding: 20px 10px; color: #1a2b47; font-size: 11px; }}
            .page {{ max-width: 820px; margin: 0 auto; background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 30px rgba(15,23,42,0.15); margin-bottom: 20px; }}
            
            /* Tombol Print */
            .btn-print-wrap {{ position: sticky; top: 0; z-index: 9999; background: #e2e8f0; padding: 10px 0; text-align: center; }}
            .btn-print {{ background-color: #1e3a8a; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; max-width: 820px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn-print:hover {{ background-color: #2563eb; }}

            /* HEADER */
            .hdr {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 70%, #1e40af 100%); color: #fff; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow: hidden; }}
            .hdr::before {{ content:''; position:absolute; top:-50%; right:-5%; width:220px; height:220px; background: radial-gradient(circle, rgba(16,185,129,0.3), transparent 70%); border-radius:50%; }}
            .brand {{ position: relative; z-index:1; }}
            .brand h1 {{ font-size: 19px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }}
            .brand .tag {{ font-size: 9.5px; color: #94a3b8; letter-spacing: 0.4px; margin-top: 1px; }}
            .brand .addr {{ font-size: 9px; color: #cbd5e1; margin-top: 4px; line-height: 1.4; max-width: 400px; }}
            .title-box {{ text-align: right; position: relative; z-index: 1; }}
            .badge-inv {{ display: inline-block; background: rgba(245,158,11,0.22); color: #fbbf24; padding: 3px 10px; border-radius: 12px; font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; border: 1px solid rgba(245,158,11,0.4); }}
            .inv-no {{ font-size: 11.5px; font-weight: 700; margin-top: 5px; }}
            .inv-date {{ font-size: 9px; color: #94a3b8; margin-top: 2px; }}

            /* META STRIP */
            .meta {{ display: flex; gap: 14px; justify-content: space-between; padding: 6px 22px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 9.5px; color: #475569; }}
            .meta b {{ color: #0f172a; }}

            /* BODY */
            .body {{ padding: 15px 22px 20px; }}

            /* TOP 2-COLUMN */
            .top-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }}
            .sec {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }}
            .sec-title {{ font-size: 9.5px; font-weight: 800; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.6px; padding-bottom: 4px; margin-bottom: 5px; border-bottom: 1.5px solid #f1f5f9; display: flex; align-items: center; gap: 5px; }}
            .sec-title span.ic {{ display: inline-flex; width: 16px; height: 16px; align-items: center; justify-content: center; background: linear-gradient(135deg,#1e3a8a,#1e40af); color: #fff; border-radius: 4px; font-size: 9px; }}
            .kv {{ display: grid; grid-template-columns: 60px 1fr; gap: 3px 6px; font-size: 10px; }}
            .kv .k {{ color: #64748b; }}
            .kv .v {{ color: #0f172a; font-weight: 600; }}

            /* SUMMARY CARDS (DP & ANGSURAN) */
            .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }}
            .sum-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; text-align: center; }}
            .sum-card.green {{ background: #ecfdf5; border-color: #a7f3d0; }}
            .sum-card.amber {{ background: #fffbeb; border-color: #fde68a; }}
            .sum-card .lbl {{ font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 700; }}
            .sum-card .val {{ font-size: 14px; font-weight: 800; margin-top: 2px; }}
            .sum-card.green .val {{ color: #065f46; }}
            .sum-card.amber .val {{ color: #92400e; }}

            /* SCHEDULE TABLE */
            .sched {{ border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 10px; }}
            .sched-h {{ padding: 6px 10px; font-size: 10px; font-weight: 800; color: #fff; background: #1e3a8a; text-transform: uppercase; letter-spacing: 0.5px; }}
            .sched table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
            .sched th {{ background: #f8fafc; color: #475569; font-size: 9px; padding: 6px 8px; text-align: left; border-bottom: 2px solid #cbd5e1; border-right: 1px solid #e2e8f0; }}
            .sched th:last-child {{ border-right: none; }}
            .sched td {{ padding: 6px 8px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; }}
            .sched td:last-child {{ border-right: none; }}
            .sched .r {{ text-align: right; }}
            .sched .c {{ text-align: center; }}
            .sched .total-row td {{ background: #f1f5f9; font-weight: bold; color: #1e3a8a; border-top: 2px solid #cbd5e1; }}
            .status-badge {{ display: inline-block; padding: 1px 6px; border-radius: 8px; background: #fef3c7; color: #92400e; font-size: 8px; font-weight: 700; }}

            /* CATATAN & WARNING */
            .catatan {{ font-size: 9px; color: #475569; margin-bottom: 12px; line-height: 1.4; }}
            .transfer-box {{ border: 1px dashed #3b82f6; background: #eff6ff; padding: 10px; text-align: center; border-radius: 8px; margin-bottom: 12px; font-size: 10px; color: #1e3a8a; }}
            .warning-box {{ background: #fff1f2; border: 1px solid #f43f5e; padding: 10px; border-radius: 8px; margin-bottom: 15px; }}
            .warning-title {{ color: #be123c; font-weight: bold; font-size: 10px; margin-bottom: 4px; text-transform: uppercase; }}
            .warning-text {{ font-size: 9px; color: #000; line-height: 1.4; text-align: justify; }}

            /* PERJANJIAN OJK */
            .agreement-container {{ background: #ffffff; border: 2px solid #000000; padding: 20px; margin-top: 15px; margin-bottom: 15px; font-family: 'Times New Roman', Times, serif; font-size: 10.5px; color: #000000; line-height: 1.6; }}
            .agreement-title {{ text-align: center; font-weight: bold; font-size: 12px; text-decoration: underline; margin-bottom: 4px; }}
            .agreement-number {{ text-align: center; font-weight: bold; margin-bottom: 15px; }}
            .agreement-articles b {{ display: block; margin-top: 10px; margin-bottom: 4px; font-size: 11px; }}
            .agreement-articles p {{ margin-bottom: 4px; text-align: justify; }}

            /* SIGNATURE AREA (SESUAI GAMBAR 2) */
            .signature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; }}
            .sig-box {{ text-align: center; position: relative; }}
            .sig-title {{ font-size: 10px; font-weight: bold; text-transform: uppercase; margin-bottom: 10px; }}
            
            /* Kreditur Box */
            .sig-box-kreditur {{ border: 1px solid #93c5fd; background: #eff6ff; border-radius: 8px; padding: 15px; position: relative; margin-bottom: 10px; }}
            .cert-badge {{ display: flex; align-items: center; justify-content: center; gap: 5px; color: #0284c7; font-size: 10px; font-weight: bold; margin-bottom: 5px; }}
            .cert-badge svg {{ width: 14px; height: 14px; fill: currentColor; }}
            .sig-name-bold {{ font-weight: bold; font-size: 11px; margin-bottom: 3px; }}
            .sig-sub {{ font-size: 9px; color: #64748b; line-height: 1.3; margin-bottom: 10px; }}
            
            /* Debitur Box */
            .sig-box-debitur {{ border: 1px dashed #94a3b8; background: #f8fafc; border-radius: 8px; padding: 15px; position: relative; margin-bottom: 10px; }}
            .emeterai-wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60px; margin-bottom: 5px; }}
            
            /* Visual E-Meterai */
            .emeterai {{ width: 60px; height: 35px; background: linear-gradient(135deg, #a855f7, #6b21a8); border-radius: 4px; border: 2px solid #d8b4fe; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
            .emeterai-logo {{ font-size: 10px; line-height: 1; }}
            .emeterai-text {{ font-size: 5px; letter-spacing: 0.5px; font-weight: bold; }}
            .emeterai-val {{ font-size: 10px; font-weight: 900; }}
            
            .sig-name-underline {{ font-weight: bold; font-size: 11px; text-decoration: underline; margin-top: 10px; }}
            .sig-nik {{ font-size: 9px; color: #334155; margin-top: 3px; }}

            @media print {{
                @page {{ size: A4 portrait; margin: 10mm; }}
                body {{ background: #fff; padding: 0; margin: 0; font-size: 10px; }}
                .btn-print-wrap {{ display: none !important; }}
                .page {{ box-shadow: none; border-radius: 0; max-width: 100%; width: 100%; border: none; margin-bottom: 0; }}
                .page:nth-child(2) {{ page-break-before: always; }}
                * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            }}
        </style>
        </head>
        <body>
        
        <div class="btn-print-wrap">
            <button class="btn-print" onclick="window.print()">🖨️ Cetak Sekarang (Print / Simpan PDF)</button>
        </div>
        
        <!-- ================= HALAMAN 1 ================= -->
        <div class="page">
            <header class="hdr">
                <div class="brand">
                    <h1>Grace's Electronic</h1>
                    <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                    <div class="addr">Sekolaq Darat RT 007 Kampung Sekolaq Darat Kec. Sekolaq Darat, Kab. Kutai Barat, Prov. Kaltim • HP/WA: 0822-9954-8411</div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Invoice Kredit</div>
                    <div class="inv-no">#GRC-INV-{kredit_data['id']}</div>
                    <div class="inv-date">{tgl_kredit_indo}</div>
                </div>
            </header>

            <div class="meta">
                <div>Status: <b style="color:#059669;">● {kredit_data['status'].upper()}</b></div>
                <div>Metode: <b>Tunai / Transfer</b></div>
            </div>

            <div class="body">
                <!-- Customer + Product -->
                <div class="top-grid">
                    <div class="sec">
                        <div class="sec-title"><span class="ic">👤</span> DATA CUSTOMER</div>
                        <div class="kv">
                            <div class="k">Nama</div><div class="v">{kredit_data['customer_nama']}</div>
                            <div class="k">Telepon</div><div class="v">{kredit_data['telepon'] or '-'}</div>
                            <div class="k">NIK</div><div class="v">{kredit_data['nik'] or '-'}</div>
                            <div class="k">Alamat</div><div class="v">{kredit_data['alamat'] or '-'}</div>
                        </div>
                    </div>
                    <div class="sec">
                        <div class="sec-title"><span class="ic">📱</span> DETAIL PRODUK</div>
                        <div class="kv">
                            <div class="k">Nama</div><div class="v">{kredit_data['produk_nama']}</div>
                            <div class="k">SKU</div><div class="v">GRC-{kredit_data['id']:02d}</div>
                            <div class="k">Garansi</div><div class="v">3 Bulan</div>
                        </div>
                    </div>
                </div>

                <!-- Summary Cards (DP & Angsuran) -->
                <div class="summary-grid">
                    <div class="sum-card green">
                        <div class="lbl">DP DIBAYAR</div>
                        <div class="val">{format_rp(kredit_data['dp'])}</div>
                    </div>
                    <div class="sum-card amber">
                        <div class="lbl">ANGSURAN / BULAN</div>
                        <div class="val">{format_rp(kredit_data['cicilan_bulan'])}</div>
                    </div>
                </div>

                <!-- Jadwal Angsuran -->
                <div class="sched">
                    <div class="sched-h">Jadwal Angsuran — {kredit_data['tenor']} Bulan</div>
                    <table>
                        <thead>
                            <tr>
                                <th class="c" style="width:30px;">KE</th>
                                <th>JATUH TEMPO</th>
                                <th class="r">NOMINAL</th>
                                <th class="c">STATUS</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jadwal_rows}
                            <tr class="total-row">
                                <td colspan="2" class="c">TOTAL ANGSURAN</td>
                                <td class="r">{format_rp(kredit_data['total_hutang'])}</td>
                                <td class="c">—</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="catatan">
                    *Catatan: Terdapat Biaya Administrasi/Materai sebesar {format_rp(biaya_materai)} (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir (ke-{kredit_data['tenor']}). Total yang disetor pada bulan ke-{kredit_data['tenor']} adalah {format_rp(total_bulan_terakhir)}.
                </div>
                
                <!-- Transfer Box -->
                <div class="transfer-box">
                    <div style="font-weight: bold; margin-bottom: 3px;">PEMBAYARAN TRANSFER RESMI</div>
                    <div style="font-size: 14px; font-weight: bold; letter-spacing: 1px;">Bank Mandiri: 148-00-2889246-4</div>
                    <div style="font-weight: 600;">a.n. CV GRACE HAVEN TRANSPORT</div>
                </div>

                <!-- Peringatan Merah -->
                <div class="warning-box">
                    <div class="warning-title">PENTING - KONSEKUENSI MANGKIR</div>
                    <div class="warning-text">Jika Debitur lalai/mangkir dalam pembayaran angsuran, Kreditur berhak melaporkan Debitur ke Sistem Layanan Informasi Keuangan (SLIK) OJK dan/atau BI Checking. Hal ini mengakibatkan Debitur masuk dalam daftar hitam (blacklist) yang akan menyulitkan Debitur untuk mengajukan pinjaman/kredit di lembaga keuangan manapun di kemudian hari.</div>
                </div>
            </div>

            <footer class="footer" style="padding: 8px 22px 12px; text-align: center; font-size: 8.5px; color: #9ca3af; line-height: 1.6; border-top: 1px solid #e5e7eb;">
                <div style="font-family: Georgia, serif; font-size: 9.5px; color: #1a2b47; font-weight: 700; letter-spacing: 0.8px;">GRACE'S ELECTRONIC</div>
                <div>Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak. Simpan untuk pembayaran berikutnya.</div>
            </footer>
        </div>
        
        <!-- ================= HALAMAN 2 ================= -->
        <div class="page" style="page-break-before: always;">
            <header class="hdr">
                <div class="brand">
                    <h1>Grace's Electronic</h1>
                    <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                    <div class="addr">Sekolaq Darat RT 007 Kampung Sekolaq Darat Kec. Sekolaq Darat, Kab. Kutai Barat, Prov. Kaltim • HP/WA: 0822-9954-8411</div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Surat Perjanjian Kredit</div>
                    <div class="inv-no">#GRC-INV-{kredit_data['id']}</div>
                    <div class="inv-date">{tgl_kredit_indo}</div>
                </div>
            </header>
            
            <div class="body">
                <div class="agreement-container">
                    <div class="agreement-title">SURAT PERJANJIAN KREDIT BARANG & SURAT KUASA PEMBEBANAN</div>
                    <div class="agreement-number">Nomor: GRC-INV-{kredit_data['id']}/PERJ/2026</div>
                    
                    <p>Pada hari ini, <b>{tgl_kredit_indo}</b>, yang bertanda tangan di bawah ini:</p>
                    
                    <table style="width: 100%; margin-bottom: 15px; font-size: 10.5px;">
                        <tr>
                            <td style="width: 150px; vertical-align: top;"><b>PIHAK PERTAMA (Kreditur)</b></td>
                            <td style="vertical-align: top;">: CV. GRACE HAVEN TRANSPORT (Grace's Electronic), berkedudukan di Sekolaq Darat RT 007 RW 000, Kelurahan/Desa Sekolaq Darat, Kecamatan Sekolaq Darat, Kabupaten Kutai Barat, Provinsi Kalimantan Timur. Berdasarkan Akta Notaris Ladi Amelia P, S.H., M.Kn. Nomor 03 Tanggal 23 September 2026, NIB: 1510260022275, NPWP: 1000 0000 1152 1195. Dalam hal ini diwakili oleh ADI HARIANTO, S.E. selaku Direktur.</td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top;"><b>PIHAK KEDUA (Debitur)</b></td>
                            <td style="vertical-align: top;">: {kredit_data['customer_nama'].upper()}, lahir di {kredit_data['alamat'].split(',')[0] if kredit_data['alamat'] else '-'} tanggal {tgl_lahir_indo}, Warga Negara Indonesia, Pekerjaan Wiraswasta, bertempat tinggal di {kredit_data['alamat'] or '-'}, Telp/WA: {kredit_data['telepon'] or '-'}. Pemegang Kartu Tanda Penduduk (KTP) dengan NIK: {kredit_data['nik'] or '-'}.</td>
                        </tr>
                    </table>
                    
                    <p>Kedua belah pihak sepakat untuk mengikatkan diri dalam Perjanjian Pembiayaan Konsumen dengan ketentuan sebagai berikut:</p>
                    
                    <div class="agreement-articles">
                        <b>PASAL 1<br>OBJEK PERJANJIAN</b>
                        <p>Pihak Pertama setuju untuk membiayai pembelian barang berupa <b>{kredit_data['produk_nama']}</b> kepada Pihak Kedua, dan Pihak Kedua setuju untuk membeli barang tersebut secara angsuran sesuai dengan ketentuan yang diatur dalam perjanjian ini.</p>
                        
                        <b>PASAL 2<br>KETENTUAN PEMBAYARAN</b>
                        <p>1. Uang Muka (DP) yang telah dibayarkan oleh Pihak Kedua adalah sebesar {format_rp(kredit_data['dp'])}.</p>
                        <p>2. Total kewajiban angsuran yang harus dibayar oleh Pihak Kedua adalah sebesar {format_rp(kredit_data['total_hutang'])}.</p>
                        <p>3. Jangka waktu pembiayaan adalah {kredit_data['tenor']} ({kredit_data['tenor']}) bulan, dengan angsuran bulanan sebesar {format_rp(kredit_data['cicilan_bulan'])}.</p>
                        <p>4. Angsuran pertama wajib dibayarkan pada tanggal {jt_pertama_indo} dan selanjutnya paling lambat pada tanggal yang sama setiap bulannya sampai dengan angsuran terakhir tanggal {tgl_terakhir}.</p>
                        <p>5. Pembayaran angsuran wajib dilakukan secara tunai di toko atau melalui transfer ke rekening resmi perusahaan: Bank Mandiri No. Rekening 148-00-2889246-4 a.n. CV GRACE HAVEN TRANSPORT.</p>
                        <p>6. Pihak Kedua dikenakan Biaya Administrasi berupa bea materai sebesar {format_rp(biaya_materai)} yang posisinya BERADA DI LUAR nominal angsuran. Biaya tersebut akan ditagihkan dan dibayarkan bersamaan dengan setoran angsuran terakhir (angsuran ke-{kredit_data['tenor']}). Dengan demikian, total pembayaran pada bulan ke-{kredit_data['tenor']} adalah sebesar {format_rp(total_bulan_terakhir)} ({format_rp(cicilan)} angsuran + {format_rp(biaya_materai)} materai).</p>
                        
                        <b>PASAL 3<br>DENDA DAN WANPRESTASI</b>
                        <p>1. Apabila Pihak Kedua terlambat membayar angsuran melewati tanggal jatuh tempo, dikenakan denda sebesar {denda_persen}% (nol koma empat persen) per hari dari jumlah angsuran yang tertunggak, dengan total denda maksimal 100% dari pokok pembiayaan.</p>
                        <p>2. Pihak Kedua dinyatakan wanprestasi apabila gagal membayar angsuran selama 2 (dua) bulan berturut-turut.</p>
                        <p>3. Apabila Debitur mangkir/lalai dalam pembayaran, Kreditur berhak melaporkan Debitur ke Sistem Layanan Informasi Keuangan (SLIK) OJK dan/atau BI Checking, yang mengakibatkan Debitur masuk dalam daftar hitam (blacklist) dan menyulitkan Debitur memperoleh fasilitas kredit di kemudian hari.</p>
                        
                        <b>PASAL 4<br>PENYELESAIAN SENGKETA DAN DOMISILI</b>
                        <p>1. Segala perselisihan yang timbul dari perjanjian ini akan diselesaikan secara musyawarah mufakat oleh Para Pihak.</p>
                        <p>2. Apabila musyawarah tidak mencapai kesepakatan, Para Pihak sepakat untuk menyelesaikannya melalui Lembaga Alternatif Penyelesaian Sengketa Sektor Jasa Keuangan (LAPS SJK) atau Pengadilan Negeri Kutai Barat.</p>
                        <p>3. Kreditur dilarang melakukan penarikan objek pembiayaan secara paksa tanpa prosedur hukum yang sah sesuai dengan POJK Nomor 22 Tahun 2023 dan Putusan Mahkamah Konstitusi Nomor 18/PUU-XVII/2019.</p>
                        <p>4. Para pihak memilih domisili hukum yang umum dan tetap di Kantor Panitera Pengadilan Negeri Kutai Barat.</p>
                        
                        <b>PASAL 5<br>KETENTUAN PENUTUP</b>
                        <p>Perjanjian ini dibuat dengan sadar, tanpa paksaan, dan dalam keadaan sehat jasmani dan rohani. Perjanjian ini dibuat dalam rangkap 2 (dua) yang masing-masing mempunyai kekuatan hukum yang sama, satu untuk Pihak Pertama dan satu untuk Pihak Kedua.</p>
                    </div>
                </div>
                
                <!-- SIGNATURE AREA -->
                <div class="signature-grid">
                    <!-- Pihak Pertama (Kreditur) -->
                    <div class="sig-box">
                        <div class="sig-title">PIHAK PERTAMA (KREDITUR)</div>
                        
                        <div class="sig-box-kreditur">
                            <div class="cert-badge">
                                <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                                TERSERTIFIKASI
                            </div>
                            <div class="sig-name-bold">ADI HARIANTO, S.E.</div>
                            <div class="sig-sub">Ditandatangani secara elektronik<br>Menggunakan Sertifikat PSrE</div>
                            <svg id="signatureBarcode" style="margin-top: 5px;"></svg>
                        </div>
                        
                        <div class="sig-name-underline">ADI HARIANTO, S.E.</div>
                        <div class="sig-sub" style="margin-top: 2px;">Direktur CV. Grace Haven Transport</div>
                    </div>
                    
                    <!-- Pihak Kedua (Debitur) -->
                    <div class="sig-box">
                        <div class="sig-title">PIHAK KEDUA (DEBITUR)</div>
                        
                        <div class="sig-box-debitur">
                            <div class="emeterai-wrap">
                                <div class="emeterai">
                                    <div class="emeterai-logo">🦅</div>
                                    <div class="emeterai-text">METERAI TEMPEL</div>
                                    <div class="emeterai-val">10000</div>
                                </div>
                            </div>
                            <div class="sig-sub">(Tempel e-Meterai / TTD Basah)</div>
                        </div>
                        
                        <div class="sig-name-underline">{kredit_data['customer_nama'].upper()}</div>
                        <div class="sig-nik">Pemegang KTP NIK: {kredit_data['nik'] or '-'}</div>
                    </div>
                </div>
            </div>
            
            <footer class="footer" style="padding: 8px 22px 12px; text-align: center; font-size: 8.5px; color: #9ca3af; line-height: 1.6; border-top: 1px solid #e5e7eb;">
                <div style="font-family: Georgia, serif; font-size: 9.5px; color: #1a2b47; font-weight: 700; letter-spacing: 0.8px;">GRACE'S ELECTRONIC</div>
                <div>Dokumen ini sah dan mengikat secara hukum.</div>
            </footer>
        </div>
        
        <script>
            window.onload = function() {{
                JsBarcode("#signatureBarcode", "GRC-{kredit_data['id']}-TN", {{
                    format: "CODE128",
                    width: 1.5,
                    height: 35,
                    displayValue: false,
                    margin: 0,
                    lineColor: "#1e3a8a",
                    background: "transparent"
                }});
            }};
        </script>
        </body>
        </html>
        """
        
        components.html(html_slip, height=1600, scrolling=True)


elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Customer</h1><p>Kelola data pelanggan</p></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Daftar Customer", "➕ Tambah/Edit Customer"])

    with tab1:
        df_cust = pd.read_sql_query("SELECT id, nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk FROM customer ORDER BY id", conn)
        if df_cust.empty:
            st.info("Belum ada customer.")
        else:
            st.dataframe(df_cust, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Tambah / Edit Customer")
        mode = st.radio("Mode", ["Tambah Baru", "Edit Data"])
        if mode == "Edit Data":
            df_cust_all = pd.read_sql_query("SELECT id, nama FROM customer ORDER BY id", conn)
            if df_cust_all.empty:
                st.warning("Belum ada customer untuk diedit.")
                customer_edit_id = None
            else:
                cust_options = {f"ID {row['id']} - {row['nama']}": row['id'] for _, row in df_cust_all.iterrows()}
                pilih_edit = st.selectbox("Pilih Customer", list(cust_options.keys()))
                customer_edit_id = cust_options[pilih_edit]
                data_lama = pd.read_sql_query("SELECT * FROM customer WHERE id = ?", conn, params=(customer_edit_id,)).iloc[0]
        else:
            customer_edit_id = None
            data_lama = None

        with st.form("form_customer"):
            if data_lama is not None:
                nama = st.text_input("Nama Lengkap", value=data_lama['nama'] or "")
                telepon = st.text_input("Telepon", value=data_lama['telepon'] or "")
                alamat = st.text_area("Alamat", value=data_lama['alamat'] or "")
                nik = st.text_input("NIK", value=data_lama['nik'] or "")
                tanggal_lahir = st.text_input("Tanggal Lahir (YYYY-MM-DD)", value=data_lama['tanggal_lahir'] or "")
                status_kawin = st.selectbox("Status Kawin", ["Belum Kawin", "Kawin", "Cerai"], index=0 if data_lama['status_kawin'] == "Belum Kawin" else (1 if data_lama['status_kawin'] == "Kawin" else 2) if data_lama['status_kawin'] else 0)
                foto_ktp_baru = st.file_uploader("Upload Foto KTP (jpg)", type=["jpg", "jpeg", "png"])
                foto_kk_baru = st.file_uploader("Upload Foto KK (jpg)", type=["jpg", "jpeg", "png"])
            else:
                nama = st.text_input("Nama Lengkap")
                telepon = st.text_input("Telepon")
                alamat = st.text_area("Alamat")
                nik = st.text_input("NIK")
                tanggal_lahir = st.text_input("Tanggal Lahir (YYYY-MM-DD)")
                status_kawin = st.selectbox("Status Kawin", ["Belum Kawin", "Kawin", "Cerai"])
                foto_ktp_baru = st.file_uploader("Upload Foto KTP (jpg)", type=["jpg", "jpeg", "png"])
                foto_kk_baru = st.file_uploader("Upload Foto KK (jpg)", type=["jpg", "jpeg", "png"])

            submitted = st.form_submit_button("Simpan Customer")
            if submitted:
                if not nama.strip():
                    st.error("Nama harus diisi.")
                else:
                    foto_ktp_path = data_lama['foto_ktp'] if data_lama is not None else None
                    foto_kk_path = data_lama['foto_kk'] if data_lama is not None else None
                    if foto_ktp_baru is not None:
                        foto_ktp_path = save_uploaded_file(foto_ktp_baru, "ktp")
                    if foto_kk_baru is not None:
                        foto_kk_path = save_uploaded_file(foto_kk_baru, "kk")

                    if mode == "Tambah Baru":
                        c.execute("""INSERT INTO customer (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk)
                                     VALUES (?,?,?,?,?,?,?,?)""",
                                  (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp_path, foto_kk_path))
                        conn.commit()
                        log_aksi(st.session_state.username, "TAMBAH_CUSTOMER", nama)
                        flash(f"Customer '{nama}' berhasil ditambahkan.")
                    else:
                        c.execute("""UPDATE customer SET nama=?, telepon=?, alamat=?, nik=?, tanggal_lahir=?, status_kawin=?, foto_ktp=?, foto_kk=?
                                     WHERE id=?""",
                                  (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp_path, foto_kk_path, customer_edit_id))
                        conn.commit()
                        log_aksi(st.session_state.username, "EDIT_CUSTOMER", f"ID {customer_edit_id} -> {nama}")
                        flash(f"Data customer '{nama}' berhasil diperbarui.")
                    st.rerun()
elif pilihan == "🤝 Serah Terima Barang":
    st.markdown('<div class="main-header"><h1>🤝 Serah Terima Barang</h1><p>Catat bukti serah terima unit kredit (dengan IMEI & foto)</p></div>', unsafe_allow_html=True)

    df_kredit_st = pd.read_sql_query("""
        SELECT k.id, c.nama as customer_nama, c.telepon, p.nama as produk_nama, p.kategori,
               k.total_hutang, k.sisa_hutang, k.status, k.tanggal_kredit
        FROM kredit k
        JOIN customer c ON c.id = k.customer_id
        JOIN produk p ON p.id = k.produk_id
        ORDER BY k.id DESC
    """, conn)

    if df_kredit_st.empty:
        st.info("Belum ada data kredit untuk diserahterimakan.")
    else:
        tab1, tab2 = st.tabs(["➕ Buat Serah Terima", "📋 Riwayat Serah Terima"])

        with tab1:
            st.subheader("Form Serah Terima Barang")
            options = {f"ID {row['id']} - {row['customer_nama']} - {row['produk_nama']}": row['id'] for _, row in df_kredit_st.iterrows()}
            pilih = st.selectbox("Pilih Kredit", list(options.keys()))
            kredit_id = options[pilih]
            row_kredit = df_kredit_st[df_kredit_st['id'] == kredit_id].iloc[0]

            st.markdown(f"**Customer:** {row_kredit['customer_nama']}")
            st.markdown(f"**Produk:** {row_kredit['produk_nama']}")
            st.markdown(f"**Kategori:** {row_kredit['kategori']}")
            st.markdown(f"**Status Kredit:** {row_kredit['status']}")

            is_gadget = row_kredit['kategori'] == "Gadget"

            with st.form("form_serah_terima"):
                st.markdown("### Data Serah Terima")
                if is_gadget:
                    imei = st.text_input("IMEI / Serial Number", help="Wajib untuk produk Gadget/HP")
                else:
                    imei = st.text_input("Nomor Seri / Kode Unit (opsional)")

                tanggal_serah = st.date_input("Tanggal Serah Terima", value=datetime.now().date())
                penerima = st.text_input("Nama Penerima", value=row_kredit['customer_nama'])
                catatan = st.text_area("Catatan Tambahan (opsional)")

                st.markdown("### Bukti Foto")
                st.info("Ambil foto unit yang diserahkan beserta customer (jika memungkinkan).")
                foto_bukti = st.file_uploader("Upload Foto Bukti Serah Terima (jpg/png)", type=["jpg", "jpeg", "png"])

                submitted = st.form_submit_button("Simpan Serah Terima")
                if submitted:
                    if is_gadget and not imei.strip():
                        st.error("IMEI wajib diisi untuk produk Gadget.")
                    elif not penerima.strip():
                        st.error("Nama penerima wajib diisi.")
                    else:
                        foto_path = save_uploaded_file(foto_bukti, f"serah_{kredit_id}")
                        c.execute("""INSERT INTO serah_terima (kredit_id, imei, foto_bukti, tanggal_serah, penerima)
                                     VALUES (?,?,?,?,?)""",
                                  (kredit_id, imei.strip(), foto_path, tanggal_serah.strftime("%Y-%m-%d"), penerima.strip()))
                        conn.commit()
                        log_aksi(st.session_state.username, "SERAH_TERIMA", f"Kredit ID {kredit_id} - IMEI: {imei}")
                        flash(f"Serah terima untuk Kredit ID {kredit_id} berhasil dicatat.")
                        st.session_state.balloons = True
                        st.rerun()

        with tab2:
            st.subheader("📋 Riwayat Serah Terima")
            df_st = pd.read_sql_query("""
                SELECT st.id as ID, st.kredit_id as Kredit_ID, c.nama as Customer,
                       p.nama as Produk, st.imei as IMEI, st.tanggal_serah as Tanggal,
                       st.penerima as Penerima, st.foto_bukti as Foto
                FROM serah_terima st
                JOIN kredit k ON k.id = st.kredit_id
                JOIN customer c ON c.id = k.customer_id
                JOIN produk p ON p.id = k.produk_id
                ORDER BY st.id DESC
            """, conn)
            if df_st.empty:
                st.info("Belum ada data serah terima.")
            else:
                st.dataframe(df_st.drop(columns=["Foto"]), use_container_width=True, hide_index=True)
                st.markdown("---")
                st.subheader("🖼️ Lihat Bukti Foto")
                pilih_foto = st.selectbox("Pilih ID Serah Terima untuk lihat foto",
                                          [row['ID'] for _, row in df_st.iterrows()])
                row_foto = df_st[df_st['ID'] == pilih_foto].iloc[0]
                if row_foto['Foto'] and os.path.exists(row_foto['Foto']):
                    img = Image.open(row_foto['Foto'])
                    st.image(img, caption=f"Bukti Serah Terima ID {pilih_foto} - {row_foto['Customer']}", use_container_width=True)
                else:
                    st.warning("Foto bukti tidak tersedia.")

elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Stok Barang</h1><p>Monitor dan kelola stok produk</p></div>', unsafe_allow_html=True)

    df_stok = pd.read_sql_query("""
        SELECT id, nama as Nama, kategori as Kategori, stok as Stok,
               harga_modal as Modal,
               COALESCE(harga_jual, ROUND(harga_modal*(1+COALESCE(markup_persen,5)/100),-2)) as Harga_Jual
        FROM produk ORDER BY stok ASC, nama ASC
    """, conn)

    col1, col2, col3 = st.columns(3)
    total_stok = df_stok['Stok'].sum() if not df_stok.empty else 0
    total_nilai_modal = (df_stok['Modal'] * df_stok['Stok']).sum() if not df_stok.empty else 0
    total_nilai_jual = (df_stok['Harga_Jual'] * df_stok['Stok']).sum() if not df_stok.empty else 0

    with col1:
        st.markdown(metric_card("Total Stok", f"{total_stok:,}".replace(",", "."), "card-blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Nilai Modal", format_rp(total_nilai_modal), "card-orange"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Nilai Jual", format_rp(total_nilai_jual), "card-green"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔍 Filter & Pencarian")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_kat = st.selectbox("Filter Kategori", ["Semua"] + SEMUA_KATEGORI)
    with col_f2:
        cari_nama = st.text_input("Cari Nama Produk")

    df_tampil = df_stok.copy()
    if filter_kat != "Semua":
        df_tampil = df_tampil[df_tampil['Kategori'] == filter_kat]
    if cari_nama.strip():
        df_tampil = df_tampil[df_tampil['Nama'].str.contains(cari_nama.strip(), case=False, na=False)]

    st.dataframe(df_tampil, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚠️ Produk Stok Rendah (≤ 2 unit)")
    df_low = df_stok[df_stok['Stok'] <= 2]
    if df_low.empty:
        st.success("Semua stok aman.")
    else:
        st.dataframe(df_low, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("✏️ Edit Stok Manual")
    with st.form("form_edit_stok"):
        produk_ids = df_stok['id'].tolist()
        options_edit = {f"ID {row['id']} - {row['Nama']} (Stok: {row['Stok']})": row['id'] for _, row in df_stok.iterrows()}
        pilih_edit = st.selectbox("Pilih Produk", list(options_edit.keys()))
        prod_edit_id = options_edit[pilih_edit]
        stok_baru = st.number_input("Stok Baru", min_value=0, step=1)
        submitted_edit = st.form_submit_button("Update Stok")
        if submitted_edit:
            c.execute("UPDATE produk SET stok = ? WHERE id = ?", (stok_baru, prod_edit_id))
            conn.commit()
            log_aksi(st.session_state.username, "EDIT_STOK", f"ID {prod_edit_id} -> {stok_baru}")
            flash(f"Stok produk ID {prod_edit_id} berhasil diupdate menjadi {stok_baru}.")
            st.rerun()

elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Overdue & Denda</h1><p>Daftar kredit yang terlambat bayar</p></div>', unsafe_allow_html=True)

    df_overdue = pd.read_sql_query("""
        SELECT k.id as ID, c.nama as Customer, c.telepon as Telepon,
               p.nama as Produk, k.sisa_hutang as Sisa,
               k.cicilan_bulan as Cicilan, k.jatuh_tempo as JT, k.status
        FROM kredit k
        JOIN customer c ON c.id = k.customer_id
        JOIN produk p ON p.id = k.produk_id
        WHERE k.status = 'Berjalan'
        ORDER BY k.jatuh_tempo ASC
    """, conn)

    if df_overdue.empty:
        st.info("Tidak ada kredit berjalan.")
    else:
        hari_ini = datetime.now()
        data_overdue = []
        total_denda = 0
        for _, row in df_overdue.iterrows():
            try:
                jt_dt = datetime.strptime(row['JT'], "%Y-%m-%d")
            except Exception:
                continue
            hari_telat = (hari_ini - jt_dt).days
            denda = hitung_denda(row['Cicilan'], max(hari_telat, 0))
            status_telat = "✅ Lancar" if hari_telat <= 0 else f"⚠️ Telat {hari_telat} hari"
            data_overdue.append({
                "ID": row['ID'], "Customer": row['Customer'], "Telepon": row['Telepon'],
                "Produk": row['Produk'], "Sisa": row['Sisa'], "Cicilan": row['Cicilan'],
                "JT": row['JT'], "Hari_Telat": max(hari_telat, 0), "Denda": denda,
                "Status": status_telat
            })
            total_denda += denda

        df_overdue_final = pd.DataFrame(data_overdue)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(metric_card("Total Kredit Berjalan", len(df_overdue_final), "card-blue"), unsafe_allow_html=True)
        with col2:
            n_telat = len(df_overdue_final[df_overdue_final['Hari_Telat'] > 0])
            st.markdown(metric_card("Kredit Terlambat", n_telat, "card-pink"), unsafe_allow_html=True)
        with col3:
            st.markdown(metric_card("Total Denda", format_rp(total_denda), "card-orange"), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📋 Daftar Kredit Berjalan & Status")
        df_tampil = df_overdue_final.copy()
        df_tampil['Sisa'] = df_tampil['Sisa'].apply(format_rp)
        df_tampil['Cicilan'] = df_tampil['Cicilan'].apply(format_rp)
        df_tampil['Denda'] = df_tampil['Denda'].apply(format_rp)
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)

        df_telat = df_overdue_final[df_overdue_final['Hari_Telat'] > 0]
        if not df_telat.empty:
            st.markdown("---")
            st.subheader("🚨 Kredit Terlambat (Perlu Tindakan)")
            for _, row in df_telat.iterrows():
                st.warning(f"**ID {row['ID']}** - {row['Customer']} ({row['Telepon'] or 'no-telp'}) - {row['Produk']} - Telat {row['Hari_Telat']} hari - Denda: {format_rp(row['Denda'])}")
        else:
            st.success("✅ Semua kredit berjalan lancar, tidak ada yang terlambat.")

elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder</h1><p>Pengingat jatuh tempo dan stok</p></div>', unsafe_allow_html=True)

    hari_ini = datetime.now()
    batas_reminder = hari_ini + timedelta(days=7)

    st.subheader("⏰ Kredit Jatuh Tempo dalam 7 Hari ke Depan")
    df_jt = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, c.telepon, p.nama as produk,
               k.sisa_hutang, k.cicilan_bulan, k.jatuh_tempo
        FROM kredit k
        JOIN customer c ON c.id = k.customer_id
        JOIN produk p ON p.id = k.produk_id
        WHERE k.status = 'Berjalan'
        ORDER BY k.jatuh_tempo ASC
    """, conn)

    ada_reminder = False
    for _, row in df_jt.iterrows():
        try:
            jt_dt = datetime.strptime(row['jatuh_tempo'], "%Y-%m-%d")
        except Exception:
            continue
        selisih = (jt_dt - hari_ini).days
        if 0 <= selisih <= 7:
            ada_reminder = True
            st.warning(f"📌 **ID {row['id']}** - {row['customer']} ({row['telepon'] or 'no-telp'}) - {row['produk']} - JT: {row['jatuh_tempo']} ({selisih} hari lagi) - Cicilan: {format_rp(row['cicilan_bulan'])}")
        elif selisih < 0:
            ada_reminder = True
            st.error(f"🚨 **ID {row['id']}** - {row['customer']} - TERLAMBAT {abs(selisih)} hari - JT: {row['jatuh_tempo']}")
    if not ada_reminder:
        st.success("✅ Tidak ada kredit yang perlu diingatkan dalam 7 hari ke depan.")

    st.markdown("---")
    st.subheader("📦 Produk Stok Rendah")
    df_stok_low = pd.read_sql_query("SELECT id, nama, kategori, stok FROM produk WHERE stok <= 3 ORDER BY stok ASC", conn)
    if df_stok_low.empty:
        st.success("✅ Semua stok aman (di atas 3 unit).")
    else:
        for _, row in df_stok_low.iterrows():
            if row['stok'] == 0:
                st.error(f"❌ **{row['nama']}** ({row['kategori']}) - STOK HABIS")
            else:
                st.warning(f"⚠️ **{row['nama']}** ({row['kategori']}) - Sisa {row['stok']} unit")

    st.markdown("---")
    st.subheader("📊 Ringkasan Hari Ini")
    col1, col2, col3 = st.columns(3)
    trx_hari_ini = c.execute("SELECT COUNT(*), COALESCE(SUM(total_harga),0) FROM transaksi_cash WHERE date(tanggal)=date('now')").fetchone()
    kredit_hari_ini = c.execute("SELECT COUNT(*), COALESCE(SUM(total_hutang),0) FROM kredit WHERE date(tanggal_kredit)=date('now')").fetchone()
    bayar_hari_ini = c.execute("SELECT COUNT(*), COALESCE(SUM(jumlah_bayar),0) FROM pembayaran WHERE date(tanggal)=date('now')").fetchone()
    with col1:
        st.markdown(metric_card("Transaksi Cash Hari Ini", f"{trx_hari_ini[0]} trx", "card-green"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Kredit Baru Hari Ini", f"{kredit_hari_ini[0]} kredit", "card-purple"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Pembayaran Hari Ini", format_rp(bayar_hari_ini[1]), "card-blue"), unsafe_allow_html=True)

elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1><p>Analisis performa bisnis</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Ringkasan", "💹 Penjualan & Laba", "📋 Kredit & Piutang", "📊 Per Kategori"])

    with tab1:
        st.subheader("Ringkasan Keseluruhan")
        col1, col2, col3, col4 = st.columns(4)
        total_produk = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
        total_cust = c.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
        total_trx_cash = c.execute("SELECT COUNT(*) FROM transaksi_cash").fetchone()[0]
        total_kredit = c.execute("SELECT COUNT(*) FROM kredit").fetchone()[0]
        with col1:
            st.markdown(metric_card("Total Produk", total_produk, "card-blue"), unsafe_allow_html=True)
        with col2:
            st.markdown(metric_card("Total Customer", total_cust, "card-purple"), unsafe_allow_html=True)
        with col3:
            st.markdown(metric_card("Transaksi Cash", total_trx_cash, "card-green"), unsafe_allow_html=True)
        with col4:
            st.markdown(metric_card("Total Kredit", total_kredit, "card-pink"), unsafe_allow_html=True)

        col5, col6, col7, col8 = st.columns(4)
        total_penjualan_cash = c.execute("SELECT COALESCE(SUM(total_harga),0) FROM transaksi_cash").fetchone()[0]
        total_laba_cash = c.execute("SELECT COALESCE(SUM(laba),0) FROM transaksi_cash").fetchone()[0]
        total_piutang = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]
        total_dp_masuk = c.execute("SELECT COALESCE(SUM(dp),0) FROM kredit").fetchone()[0]
        with col5:
            st.markdown(metric_card("Penjualan Cash", format_rp(total_penjualan_cash), "card-orange"), unsafe_allow_html=True)
        with col6:
            st.markdown(metric_card("Laba Cash", format_rp(total_laba_cash), "card-dark"), unsafe_allow_html=True)
        with col7:
            st.markdown(metric_card("Piutang Aktif", format_rp(total_piutang), "card-orange"), unsafe_allow_html=True)
        with col8:
            st.markdown(metric_card("Total DP Masuk", format_rp(total_dp_masuk), "card-green"), unsafe_allow_html=True)

    with tab2:
        st.subheader("Penjualan & Laba Cash per Bulan")
        df_bulan = pd.read_sql_query("""
            SELECT strftime('%Y-%m', tanggal) as Bulan,
                   COUNT(*) as Jumlah_Trx,
                   SUM(total_harga) as Total_Penjualan,
                   SUM(laba) as Total_Laba
            FROM transaksi_cash
            GROUP BY strftime('%Y-%m', tanggal)
            ORDER BY Bulan DESC
        """, conn)
        if df_bulan.empty:
            st.info("Belum ada transaksi cash.")
        else:
            st.dataframe(df_bulan, use_container_width=True, hide_index=True)
            chart = alt.Chart(df_bulan).mark_bar().encode(
                x=alt.X('Bulan:N', title='Bulan'),
                y=alt.Y('Total_Penjualan:Q', title='Total (Rp)'),
                color=alt.value('#667eea')
            ).properties(height=300, title="Total Penjualan Cash per Bulan")
            st.altair_chart(chart, use_container_width=True)

    with tab3:
        st.subheader("Kredit & Piutang")
        df_kredit_rep = pd.read_sql_query("""
            SELECT status, COUNT(*) as Jumlah, SUM(total_hutang) as Total_Hutang,
                   SUM(sisa_hutang) as Total_Sisa
            FROM kredit GROUP BY status
        """, conn)
        st.dataframe(df_kredit_rep, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Top 10 Customer dengan Piutang Terbesar")
        df_top = pd.read_sql_query("""
            SELECT c.nama as Customer, c.telepon as Telepon,
                   COUNT(k.id) as Jumlah_Kredit,
                   SUM(k.sisa_hutang) as Total_Piutang
            FROM kredit k
            JOIN customer c ON c.id = k.customer_id
            WHERE k.status = 'Berjalan'
            GROUP BY c.id
            ORDER BY Total_Piutang DESC
            LIMIT 10
        """, conn)
        if df_top.empty:
            st.info("Tidak ada piutang aktif.")
        else:
            df_top['Total_Piutang'] = df_top['Total_Piutang'].apply(format_rp)
            st.dataframe(df_top, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Performa per Kategori")
        df_kat = pd.read_sql_query("""
            SELECT p.kategori as Kategori,
                   COUNT(DISTINCT tc.id) as Total_Trx_Cash,
                   COALESCE(SUM(tc.jumlah),0) as Qty_Terjual,
                   COALESCE(SUM(tc.total_harga),0) as Total_Penjualan,
                   COALESCE(SUM(tc.laba),0) as Total_Laba
            FROM transaksi_cash tc
            JOIN produk p ON p.id = tc.produk_id
            GROUP BY p.kategori
            ORDER BY Total_Penjualan DESC
        """, conn)
        if df_kat.empty:
            st.info("Belum ada data penjualan.")
        else:
            st.dataframe(df_kat, use_container_width=True, hide_index=True)
            chart_kat = alt.Chart(df_kat).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Total_Penjualan:Q", title="Penjualan"),
                color=alt.Color("Kategori:N", title="Kategori"),
                tooltip=["Kategori", "Total_Penjualan", "Total_Laba"]
            ).properties(height=350, title="Distribusi Penjualan per Kategori")
            st.altair_chart(chart_kat, use_container_width=True)
elif pilihan == "🏢 Profil & Tema":
    st.markdown('<div class="main-header"><h1>🏢 Profil & Tema</h1><p>Kustomisasi Kop Surat, Bank, dan Warna Invoice</p></div>', unsafe_allow_html=True)
    
    if st.session_state.role != "admin":
        st.error("⛔ Halaman ini hanya untuk Owner/Admin.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["🏢 Data Bisnis", "🏦 Info Bank", "🎨 Tema & Tanda Tangan"])
    
    with tab1:
        with st.form("form_profil_bisnis"):
            st.subheader("Identitas Toko")
            nama_b = st.text_input("Nama Bisnis", value=get_pengaturan("bisnis_nama"))
            alamat_b = st.text_area("Alamat Lengkap", value=get_pengaturan("bisnis_alamat"))
            telp_b = st.text_input("No. Telepon / WA", value=get_pengaturan("bisnis_telepon"))
            email_b = st.text_input("Email", value=get_pengaturan("bisnis_email"))
            
            if st.form_submit_button("Simpan Identitas"):
                set_pengaturan("bisnis_nama", nama_b)
                set_pengaturan("bisnis_alamat", alamat_b)
                set_pengaturan("bisnis_telepon", telp_b)
                set_pengaturan("bisnis_email", email_b)
                flash("Identitas Bisnis berhasil diperbarui.")
                st.rerun()

    with tab2:
        with st.form("form_bank"):
            st.subheader("Informasi Rekening Transfer")
            bank_n = st.text_input("Nama Bank", value=get_pengaturan("bank_nama"))
            bank_r = st.text_input("Nomor Rekening", value=get_pengaturan("bank_rekening"))
            bank_a = st.text_input("Atas Nama", value=get_pengaturan("bank_atas_nama"))
            
            if st.form_submit_button("Simpan Info Bank"):
                set_pengaturan("bank_nama", bank_n)
                set_pengaturan("bank_rekening", bank_r)
                set_pengaturan("bank_atas_nama", bank_a)
                flash("Info Bank berhasil diperbarui.")
                st.rerun()

    with tab3:
        st.subheader("Tema Warna & File Gambar")
        
        warna_tema = st.color_picker("Pilih Warna Utama (Header & Tombol)", get_pengaturan("tema_warna"))
        if st.button("Simpan Warna Tema"):
            set_pengaturan("tema_warna", warna_tema)
            flash("Warna tema berhasil disimpan.")
            st.rerun()
            
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Logo Toko**")
            logo_path = get_pengaturan("bisnis_logo")
            if logo_path and os.path.exists(logo_path):
                st.image(logo_path, width=150)
            upload_logo = st.file_uploader("Upload Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
            if upload_logo and st.button("Simpan Logo"):
                path_baru = save_uploaded_file(upload_logo, "logo")
                set_pengaturan("bisnis_logo", path_baru)
                flash("Logo berhasil diupload.")
                st.rerun()
                
        with col2:
            st.markdown("**Tanda Tangan / Stempel**")
            ttd_path = get_pengaturan("bisnis_ttd")
            if ttd_path and os.path.exists(ttd_path):
                st.image(ttd_path, width=150)
            upload_ttd = st.file_uploader("Upload TTD (PNG transparan lebih baik)", type=["png", "jpg", "jpeg"])
            if upload_ttd and st.button("Simpan TTD"):
                path_baru = save_uploaded_file(upload_ttd, "ttd")
                set_pengaturan("bisnis_ttd", path_baru)
                flash("Tanda tangan berhasil diupload.")
                st.rerun()

elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Modal vs Profit</h1><p>Analisis modal, harga jual, dan potensi laba</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📦 Per Produk", "🏷️ Per Kategori", "💹 Laba Transaksi Cash"])

    with tab1:
        st.subheader("Analisis Modal vs Harga Jual per Produk")
        df_mp = pd.read_sql_query("""
            SELECT id, nama as Nama, kategori as Kategori,
                   harga_modal as Modal,
                   COALESCE(harga_jual, ROUND(harga_modal*(1+COALESCE(markup_persen,5)/100),-2)) as Harga_Jual,
                   stok as Stok
            FROM produk
            ORDER BY kategori, nama
        """, conn)

        if df_mp.empty:
            st.info("Belum ada produk.")
        else:
            df_mp["Laba_Unit"] = df_mp["Harga_Jual"] - df_mp["Modal"]
            df_mp["Margin_Persen"] = df_mp.apply(
                lambda r: round((r["Laba_Unit"] / r["Modal"] * 100), 2) if r["Modal"] > 0 else 0,
                axis=1
            )
            df_mp["Potensi_Laba_Stok"] = df_mp["Laba_Unit"] * df_mp["Stok"]
            df_mp["Nilai_Modal_Stok"] = df_mp["Modal"] * df_mp["Stok"]
            df_mp["Nilai_Jual_Stok"] = df_mp["Harga_Jual"] * df_mp["Stok"]

            col1, col2, col3, col4 = st.columns(4)
            total_modal = df_mp["Nilai_Modal_Stok"].sum()
            total_jual = df_mp["Nilai_Jual_Stok"].sum()
            total_laba = df_mp["Potensi_Laba_Stok"].sum()
            margin_total = (total_laba / total_modal * 100) if total_modal > 0 else 0

            with col1:
                st.markdown(metric_card("Total Nilai Modal", format_rp(total_modal), "card-orange"), unsafe_allow_html=True)
            with col2:
                st.markdown(metric_card("Total Nilai Jual", format_rp(total_jual), "card-green"), unsafe_allow_html=True)
            with col3:
                st.markdown(metric_card("Potensi Laba", format_rp(total_laba), "card-blue"), unsafe_allow_html=True)
            with col4:
                st.markdown(metric_card("Margin Total", f"{margin_total:.1f}%", "card-purple"), unsafe_allow_html=True)

            st.markdown("---")
            filter_kat_mp = st.selectbox("Filter Kategori", ["Semua"] + SEMUA_KATEGORI, key="filter_kat_mp")
            df_tampil_mp = df_mp.copy()
            if filter_kat_mp != "Semua":
                df_tampil_mp = df_tampil_mp[df_tampil_mp["Kategori"] == filter_kat_mp]

            df_tampil_mp = df_tampil_mp.copy()
            df_tampil_mp["Modal"] = df_tampil_mp["Modal"].apply(format_rp)
            df_tampil_mp["Harga_Jual"] = df_tampil_mp["Harga_Jual"].apply(format_rp)
            df_tampil_mp["Laba_Unit"] = df_tampil_mp["Laba_Unit"].apply(format_rp)
            df_tampil_mp["Potensi_Laba_Stok"] = df_tampil_mp["Potensi_Laba_Stok"].apply(format_rp)
            df_tampil_mp["Nilai_Modal_Stok"] = df_tampil_mp["Nilai_Modal_Stok"].apply(format_rp)
            df_tampil_mp["Nilai_Jual_Stok"] = df_tampil_mp["Nilai_Jual_Stok"].apply(format_rp)
            st.dataframe(df_tampil_mp, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("📊 Top 15 Produk dengan Potensi Laba Terbesar")
            df_top_laba = df_mp.sort_values("Potensi_Laba_Stok", ascending=False).head(15)
            chart_laba = alt.Chart(df_top_laba).mark_bar().encode(
                x=alt.X("Potensi_Laba_Stok:Q", title="Potensi Laba (Rp)"),
                y=alt.Y("Nama:N", sort="-x", title="Produk"),
                color=alt.Color("Kategori:N", title="Kategori"),
                tooltip=["Nama", "Kategori", "Potensi_Laba_Stok", "Margin_Persen"]
            ).properties(height=450, title="Potensi Laba per Produk")
            st.altair_chart(chart_laba, use_container_width=True)

    with tab2:
        st.subheader("Analisis Modal vs Profit per Kategori")
        df_kat_mp = pd.read_sql_query("""
            SELECT kategori as Kategori,
                   COUNT(*) as Jumlah_Produk,
                   SUM(stok) as Total_Stok,
                   SUM(harga_modal * stok) as Nilai_Modal_Stok,
                   SUM(COALESCE(harga_jual, ROUND(harga_modal*(1+COALESCE(markup_persen,5)/100),-2)) * stok) as Nilai_Jual_Stok
            FROM produk
            GROUP BY kategori
            ORDER BY Nilai_Jual_Stok DESC
        """, conn)

        if df_kat_mp.empty:
            st.info("Belum ada data produk.")
        else:
            df_kat_mp["Potensi_Laba"] = df_kat_mp["Nilai_Jual_Stok"] - df_kat_mp["Nilai_Modal_Stok"]
            df_kat_mp["Margin_Persen"] = df_kat_mp.apply(
                lambda r: round((r["Potensi_Laba"] / r["Nilai_Modal_Stok"] * 100), 2) if r["Nilai_Modal_Stok"] > 0 else 0,
                axis=1
            )
            df_kat_tampil = df_kat_mp.copy()
            for col in ["Nilai_Modal_Stok", "Nilai_Jual_Stok", "Potensi_Laba"]:
                df_kat_tampil[col] = df_kat_tampil[col].apply(format_rp)
            st.dataframe(df_kat_tampil, use_container_width=True, hide_index=True)

            chart_kat_mp = alt.Chart(df_kat_mp).mark_bar().encode(
                x=alt.X("Kategori:N", title="Kategori"),
                y=alt.Y("Potensi_Laba:Q", title="Potensi Laba (Rp)"),
                color=alt.Color("Kategori:N", title="Kategori"),
                tooltip=["Kategori", "Potensi_Laba", "Margin_Persen"]
            ).properties(height=350, title="Potensi Laba per Kategori")
            st.altair_chart(chart_kat_mp, use_container_width=True)

    with tab3:
        st.subheader("Laba dari Transaksi Cash")
        df_laba_trx = pd.read_sql_query("""
            SELECT tc.id as ID, p.nama as Produk, p.kategori as Kategori,
                   tc.jumlah as Jumlah, tc.harga_jual_satuan as Harga_Satuan,
                   tc.total_harga as Total, tc.laba as Laba, tc.tanggal as Tanggal
            FROM transaksi_cash tc
            JOIN produk p ON p.id = tc.produk_id
            ORDER BY tc.id DESC
        """, conn)

        if df_laba_trx.empty:
            st.info("Belum ada transaksi cash.")
        else:
            total_laba_trx = df_laba_trx["Laba"].sum()
            total_penjualan_trx = df_laba_trx["Total"].sum()
            margin_real = (total_laba_trx / total_penjualan_trx * 100) if total_penjualan_trx > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(metric_card("Total Penjualan Cash", format_rp(total_penjualan_trx), "card-green"), unsafe_allow_html=True)
            with col2:
                st.markdown(metric_card("Total Laba Cash", format_rp(total_laba_trx), "card-blue"), unsafe_allow_html=True)
            with col3:
                st.markdown(metric_card("Margin Real", f"{margin_real:.1f}%", "card-purple"), unsafe_allow_html=True)

            st.markdown("---")
            df_laba_tampil = df_laba_trx.copy()
            df_laba_tampil["Harga_Satuan"] = df_laba_tampil["Harga_Satuan"].apply(format_rp)
            df_laba_tampil["Total"] = df_laba_tampil["Total"].apply(format_rp)
            df_laba_tampil["Laba"] = df_laba_tampil["Laba"].apply(format_rp)
            st.dataframe(df_laba_tampil, use_container_width=True, hide_index=True)

elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1><p>Backup database, cetak laporan, ekspor & impor data</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💾 Backup & Restore", "🖨️ Cetak Laporan", "📤 Ekspor CSV", "📥 Impor Produk"])

    with tab1:
        st.subheader("💾 Backup Database")
        st.info("Backup berisi seluruh data toko: produk, customer, kredit, pembayaran, user, dan log.")
        try:
            c.execute("PRAGMA wal_checkpoint(FULL)")
            conn.commit()
        except Exception:
            pass

        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button(
                label="⬇️ Download Backup Database (.db)",
                data=db_bytes,
                file_name=f"backup_toko_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                mime="application/octet-stream",
                use_container_width=True
            )
        else:
            st.error("File database tidak ditemukan.")

        st.markdown("---")
        st.subheader("♻️ Restore Database")
        st.warning("Restore akan MENGGANTI seluruh data saat ini. Pastikan Anda sudah memiliki backup terbaru.")
        konfirmasi_restore = st.checkbox("Saya mengerti dan ingin melanjutkan restore database")
        file_restore = st.file_uploader("Upload file backup (.db)", type=["db"], key="restore_db")
        if st.button("Restore Database Sekarang", disabled=not konfirmasi_restore):
            if file_restore is None:
                st.error("Pilih file backup terlebih dahulu.")
            else:
                try:
                    backup_sebelum_restore = os.path.join(BACKUP_DIR, f"sebelum_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                    if os.path.exists(DB_PATH):
                        shutil.copy2(DB_PATH, backup_sebelum_restore)
                    with open(DB_PATH, "wb") as f:
                        f.write(file_restore.getbuffer())
                    st.cache_resource.clear()
                    log_aksi(st.session_state.username, "RESTORE_DB", "Restore database dari file upload")
                    flash("Database berhasil direstore. Silakan login ulang jika diperlukan.", "success")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal restore database: {e}")

        st.markdown("---")
        st.subheader("📁 Daftar Backup Otomatis")
        if os.path.exists(BACKUP_DIR):
            daftar_backup = sorted(os.listdir(BACKUP_DIR), reverse=True)
            if daftar_backup:
                for b in daftar_backup[:20]:
                    st.write(f"📄 {b}")
            else:
                st.info("Belum ada file backup otomatis.")
        else:
            st.info("Folder backup belum tersedia.")

    with tab2:
        st.subheader("🖨️ Cetak Laporan Ringkas")
        periode = st.selectbox("Pilih Periode Laporan", ["Hari Ini", "7 Hari Terakhir", "30 Hari Terakhir", "Semua Data"])
        if periode == "Hari Ini":
            where_cash = "WHERE date(tanggal)=date('now')"
            where_kredit = "WHERE date(tanggal_kredit)=date('now')"
            where_bayar = "WHERE date(tanggal)=date('now')"
        elif periode == "7 Hari Terakhir":
            where_cash = "WHERE date(tanggal)>=date('now','-7 days')"
            where_kredit = "WHERE date(tanggal_kredit)>=date('now','-7 days')"
            where_bayar = "WHERE date(tanggal)>=date('now','-7 days')"
        elif periode == "30 Hari Terakhir":
            where_cash = "WHERE date(tanggal)>=date('now','-30 days')"
            where_kredit = "WHERE date(tanggal_kredit)>=date('now','-30 days')"
            where_bayar = "WHERE date(tanggal)>=date('now','-30 days')"
        else:
            where_cash = ""
            where_kredit = ""
            where_bayar = ""

        total_cash_rep = c.execute(f"SELECT COALESCE(SUM(total_harga),0), COALESCE(SUM(laba),0), COUNT(*) FROM transaksi_cash {where_cash}").fetchone()
        total_kredit_rep = c.execute(f"SELECT COALESCE(SUM(total_hutang),0), COALESCE(SUM(dp),0), COUNT(*) FROM kredit {where_kredit}").fetchone()
        total_bayar_rep = c.execute(f"SELECT COALESCE(SUM(jumlah_bayar),0), COUNT(*) FROM pembayaran {where_bayar}").fetchone()
        total_piutang = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]

        html_laporan = f"""
        <div style="font-family: Arial, sans-serif; max-width: 900px; margin: auto; padding: 25px; border: 1px solid #ccc; background: white;">
            <h2 style="text-align:center; margin-bottom:0;">{get_pengaturan('bisnis_nama')}</h2>
            <p style="text-align:center; margin-top:5px;">{get_pengaturan('bisnis_alamat')}</p>
            <hr>
            <h3 style="text-align:center;">LAPORAN RINGKAS</h3>
            <p><strong>Periode:</strong> {periode}</p>
            <p><strong>Dicetak:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
            <hr>
            <h4>Penjualan Cash</h4>
            <table border="1" cellpadding="6" cellspacing="0" style="width:100%; border-collapse:collapse;">
                <tr><th>Jumlah Transaksi</th><th>Total Penjualan</th><th>Total Laba</th></tr>
                <tr>
                    <td>{total_cash_rep[2]} transaksi</td>
                    <td>{format_rp(total_cash_rep[0])}</td>
                    <td>{format_rp(total_cash_rep[1])}</td>
                </tr>
            </table>
            <br>
            <h4>Kredit Baru</h4>
            <table border="1" cellpadding="6" cellspacing="0" style="width:100%; border-collapse:collapse;">
                <tr><th>Jumlah Kredit</th><th>Total Hutang</th><th>Total DP</th></tr>
                <tr>
                    <td>{total_kredit_rep[2]} kredit</td>
                    <td>{format_rp(total_kredit_rep[0])}</td>
                    <td>{format_rp(total_kredit_rep[1])}</td>
                </tr>
            </table>
            <br>
            <h4>Pembayaran Cicilan</h4>
            <table border="1" cellpadding="6" cellspacing="0" style="width:100%; border-collapse:collapse;">
                <tr><th>Jumlah Pembayaran</th><th>Total Diterima</th></tr>
                <tr>
                    <td>{total_bayar_rep[1]} pembayaran</td>
                    <td>{format_rp(total_bayar_rep[0])}</td>
                </tr>
            </table>
            <br>
            <h4>Piutang Aktif Saat Ini</h4>
            <p style="font-size:1.2em;"><strong>{format_rp(total_piutang)}</strong></p>
            <hr>
            <p style="text-align:center; font-size:0.85em;">Laporan ini dihasilkan otomatis oleh sistem {get_pengaturan('bisnis_nama')}.</p>
        </div>
        """
        st.markdown(html_laporan, unsafe_allow_html=True)
        if st.button("🖨️ Cetak Laporan"):
            components.html(
                """
                <script>
                    window.print();
                </script>
                """,
                height=0
            )
            st.success("Perintah cetak dikirim ke browser.")

    with tab3:
        st.subheader("📤 Ekspor Data ke CSV / ZIP")
        st.info("Ekspor seluruh tabel penting ke dalam file ZIP berisi CSV.")
        if st.button("Siapkan File Ekspor ZIP"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                tabel_ekspor = {
                    "produk.csv": "SELECT * FROM produk",
                    "customer.csv": "SELECT * FROM customer",
                    "transaksi_cash.csv": "SELECT * FROM transaksi_cash",
                    "transaksi_in.csv": "SELECT * FROM transaksi_in",
                    "kredit.csv": "SELECT * FROM kredit",
                    "pembayaran.csv": "SELECT * FROM pembayaran",
                    "serah_terima.csv": "SELECT * FROM serah_terima",
                    "users.csv": "SELECT id, username, nama_lengkap, role, aktif FROM users",
                    "log_aktivitas.csv": "SELECT * FROM log_aktivitas",
                }
                for nama_file, query in tabel_ekspor.items():
                    df_export = pd.read_sql_query(query, conn)
                    csv_bytes = df_export.to_csv(index=False).encode("utf-8")
                    zf.writestr(nama_file, csv_bytes)
            zip_buffer.seek(0)
            st.download_button(
                label="⬇️ Download ZIP Ekspor Data",
                data=zip_buffer,
                file_name=f"ekspor_toko_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("📤 Ekspor Cepat per Tabel")
        pilih_tabel = st.selectbox(
            "Pilih Tabel",
            ["produk", "customer", "transaksi_cash", "transaksi_in", "kredit", "pembayaran", "serah_terima"]
        )
        df_cepat = pd.read_sql_query(f"SELECT * FROM {pilih_tabel}", conn)
        csv_cepat = df_cepat.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"⬇️ Download {pilih_tabel}.csv",
            data=csv_cepat,
            file_name=f"{pilih_tabel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.dataframe(df_cepat.head(20), use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("📥 Impor Produk dari CSV")
        st.info("Format CSV wajib memiliki kolom: nama, kategori, harga_modal, stok. Kolom opsional: markup_persen, harga_jual.")
        template_df = pd.DataFrame([
            {"nama": "Contoh Produk", "kategori": "Gadget", "harga_modal": 1000000, "stok": 5, "markup_persen": 10, "harga_jual": ""}
        ])
        st.download_button(
            label="⬇️ Download Template CSV Produk",
            data=template_df.to_csv(index=False).encode("utf-8"),
            file_name="template_impor_produk.csv",
            mime="text/csv",
            use_container_width=True
        )

        file_impor = st.file_uploader("Upload CSV Produk", type=["csv"], key="impor_produk")
        if file_impor is not None:
            try:
                df_impor = pd.read_csv(file_impor)
                st.write("Preview Data:")
                st.dataframe(df_impor.head(20), use_container_width=True, hide_index=True)

                kolom_wajib = {"nama", "kategori", "harga_modal", "stok"}
                if not kolom_wajib.issubset(set(df_impor.columns)):
                    st.error(f"Kolom wajib tidak lengkap. Wajib ada: {', '.join(kolom_wajib)}")
                else:
                    konfirmasi_impor = st.checkbox("Saya yakin ingin mengimpor data produk ini")
                    if st.button("Proses Impor Produk", disabled=not konfirmasi_impor):
                        berhasil = 0
                        gagal = 0
                        for idx, row in df_impor.iterrows():
                            try:
                                nama_prod = str(row["nama"]).strip()
                                kategori_prod = str(row["kategori"]).strip()
                                harga_modal_prod = float(row["harga_modal"])
                                stok_prod = int(row["stok"])
                                markup_prod = float(row["markup_persen"]) if "markup_persen" in df_impor.columns and pd.notna(row.get("markup_persen")) and str(row.get("markup_persen")).strip() != "" else get_pengaturan_float("markup_default_persen", 5.0)
                                harga_jual_prod = None
                                if "harga_jual" in df_impor.columns and pd.notna(row.get("harga_jual")) and str(row.get("harga_jual")).strip() != "":
                                    harga_jual_prod = float(row["harga_jual"])
                                if not nama_prod or nama_prod.lower() == "nan":
                                    gagal += 1
                                    continue
                                if kategori_prod not in SEMUA_KATEGORI:
                                    kategori_prod = "Lainnya"
                                c.execute(
                                    """INSERT INTO produk
                                       (nama, kategori, harga_modal, stok, markup_persen, harga_jual)
                                       VALUES (?,?,?,?,?,?)""",
                                    (nama_prod, kategori_prod, harga_modal_prod, stok_prod, markup_prod, harga_jual_prod)
                                )
                                berhasil += 1
                            except Exception:
                                gagal += 1
                        conn.commit()
                        log_aksi(st.session_state.username, "IMPOR_PRODUK", f"Berhasil: {berhasil}, Gagal: {gagal}")
                        if berhasil > 0:
                            flash(f"Impor selesai. Berhasil: {berhasil}, Gagal: {gagal}.", "success")
                        else:
                            flash(f"Impor selesai. Tidak ada data berhasil. Gagal: {gagal}.", "warning")
                        st.rerun()
            except Exception as e:
                st.error(f"Gagal membaca CSV: {e}")

elif pilihan == "📄 Dokumen Bisnis":
    st.markdown('<div class="main-header"><h1>📄 Dokumen Bisnis</h1><p>Cetak Faktur, Surat Jalan, dan Penawaran Profesional</p></div>', unsafe_allow_html=True)
    
    if st.session_state.role != "admin" and st.session_state.role != "kasir":
        st.error("⛔ Halaman ini hanya untuk Admin/Kasir.")
        st.stop()

    tipe_dokumen = st.selectbox("Pilih Jenis Dokumen", [
        "Faktur / Invoice Cash",
        "Invoice Kredit",
        "Surat Jalan (Delivery Note)",
        "Surat Penawaran (Quotation)"
    ])

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Info Pelanggan")
        df_cust = pd.read_sql_query("SELECT id, nama, telepon, alamat FROM customer ORDER BY nama", conn)
        cust_options = {f"{row['nama']} - {row['telepon'] or ''}": row['id'] for _, row in df_cust.iterrows()}
        pilih_cust = st.selectbox("Pilih Customer", ["(Tanpa Customer / Umum)"] + list(cust_options.keys()))
        
    with col2:
        st.subheader("Detail Dokumen")
        no_dokumen = st.text_input("Nomor Dokumen", value=f"DOC-{datetime.now().strftime('%Y%m%d%H%M')}")
        tgl_dokumen = st.date_input("Tanggal Dokumen", value=datetime.now().date())
        jatuh_tempo = st.date_input("Jatuh Tempo (jika ada)", value=datetime.now().date() + timedelta(days=14))

    st.subheader("Daftar Barang / Jasa")
    df_produk = pd.read_sql_query("SELECT nama, harga_modal, COALESCE(harga_jual, ROUND(harga_modal*(1+COALESCE(markup_persen,5)/100),-2)) as harga_jual, stok FROM produk ORDER BY nama", conn)
    
    init_df = pd.DataFrame([{"Nama Barang": "", "Qty": 1, "Harga Satuan": 0.0, "Total": 0.0}])
    
    edited_df = st.data_editor(
        init_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Nama Barang": st.column_config.SelectboxColumn(
                "Nama Barang",
                help="Pilih dari daftar produk atau ketik manual",
                options=df_produk['nama'].tolist() + ["(Barang Lain)"],
                required=False
            ),
            "Qty": st.column_config.NumberColumn("Qty", min_value=1, step=1, format="%d"),
            "Harga Satuan": st.column_config.NumberColumn("Harga Satuan (Rp)", min_value=0, format="Rp %,.0f"),
            "Total": st.column_config.NumberColumn("Total (Rp)", min_value=0, format="Rp %,.0f", disabled=True)
        }
    )

    total_semua = 0
    for index, row in edited_df.iterrows():
        if row["Nama Barang"] and row["Nama Barang"] != "":
            edited_df.at[index, "Total"] = row["Qty"] * row["Harga Satuan"]
            total_semua += row["Total"]
    
    st.markdown(f"**Total Keseluruhan: {format_rp(total_semua)}**")
    
    catatan_tambahan = st.text_area("Catatan / Keterangan Tambahan", "Barang yang sudah dibeli tidak dapat ditukar atau dikembalikan.")

    if st.button("🖨️ Buat & Cetak Dokumen"):
        if not edited_df.empty and edited_df[edited_df["Nama Barang"] != ""].empty:
            st.error("Pilih minimal satu barang.")
        else:
            logo_path = get_pengaturan("bisnis_logo")
            ttd_path = get_pengaturan("bisnis_ttd")
            warna_tema = get_pengaturan("tema_warna", "#1e3a8a")
            
            logo_base64 = ""
            if logo_path and os.path.exists(logo_path):
                with open(logo_path, "rb") as image_file:
                    logo_base64 = f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
            
            ttd_base64 = ""
            if ttd_path and os.path.exists(ttd_path):
                with open(ttd_path, "rb") as image_file:
                    ttd_base64 = f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"

            nama_cust, telp_cust, alamat_cust = "-", "-", "-"
            if pilih_cust != "(Tanpa Customer / Umum)":
                cust_id = cust_options[pilih_cust]
                c_row = df_cust[df_cust['id'] == cust_id].iloc[0]
                nama_cust = c_row['nama']
                telp_cust = c_row['telepon'] or "-"
                alamat_cust = c_row['alamat'] or "-"

            rows_html = ""
            for _, row in edited_df.iterrows():
                if row["Nama Barang"] != "":
                    rows_html += f"""
                    <tr>
                        <td style="text-align:center;">{row['Qty']}</td>
                        <td>{row['Nama Barang']}</td>
                        <td style="text-align:right;">{format_rp(row['Harga Satuan'])}</td>
                        <td style="text-align:right;">{format_rp(row['Total'])}</td>
                    </tr>
                    """

            title_map = {
                "Faktur / Invoice Cash": "INVOICE",
                "Invoice Kredit": "INVOICE KREDIT",
                "Surat Jalan (Delivery Note)": "SURAT JALAN",
                "Surat Penawaran (Quotation)": "PENAWARAN"
            }
            doc_title = title_map[tipe_dokumen]

            html_doc = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
                .doc-container {{ background: white; max-width: 800px; margin: auto; padding: 40px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid {warna_tema}; padding-bottom: 20px; margin-bottom: 20px; }}
                .header-left {{ display: flex; gap: 15px; align-items: center; }}
                .header-left img {{ max-height: 70px; max-width: 150px; }}
                .company-details h1 {{ margin: 0; color: {warna_tema}; font-size: 22px; }}
                .company-details p {{ margin: 3px 0; font-size: 12px; color: #555; }}
                .doc-title {{ text-align: right; }}
                .doc-title h2 {{ margin: 0; color: {warna_tema}; font-size: 28px; text-transform: uppercase; }}
                .doc-title p {{ margin: 3px 0; font-size: 13px; }}
                
                .info-grid {{ display: flex; justify-content: space-between; margin-bottom: 30px; font-size: 13px; }}
                .info-box h4 {{ margin: 0 0 5px 0; color: #888; text-transform: uppercase; font-size: 11px; }}
                .info-box p {{ margin: 2px 0; }}
                .info-box strong {{ font-size: 14px; }}
                
                .table-data {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
                .table-data th {{ background: #f0f0f0; border-bottom: 2px solid #ccc; padding: 10px; text-align: left; }}
                .table-data td {{ padding: 10px; border-bottom: 1px solid #eee; }}
                
                .total-box {{ background: #f9f9f9; padding: 15px; border-left: 4px solid {warna_tema}; width: 50%; margin-left: auto; font-size: 14px; margin-bottom: 30px; }}
                .total-box .row {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
                .total-box .grand-total {{ font-weight: bold; font-size: 18px; color: {warna_tema}; border-top: 1px solid #ccc; padding-top: 5px; margin-top: 5px; }}
                
                .footer {{ display: flex; justify-content: space-between; margin-top: 40px; font-size: 12px; }}
                .terms {{ width: 60%; }}
                .signature {{ text-align: center; width: 35%; }}
                .signature img {{ height: 60px; margin-bottom: 5px; }}
                
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .doc-container {{ box-shadow: none; padding: 0; }}
                }}
            </style>
            </head>
            <body>
                <div class="doc-container">
                    <div class="header">
                        <div class="header-left">
                            {f'<img src="{logo_base64}" alt="Logo">' if logo_base64 else ''}
                            <div class="company-details">
                                <h1>{get_pengaturan("bisnis_nama")}</h1>
                                <p>{get_pengaturan("bisnis_alamat")}</p>
                                <p>Telp: {get_pengaturan("bisnis_telepon")} | Email: {get_pengaturan("bisnis_email")}</p>
                            </div>
                        </div>
                        <div class="doc-title">
                            <h2>{doc_title}</h2>
                            <p><strong>No:</strong> {no_dokumen}</p>
                            <p><strong>Tanggal:</strong> {tgl_dokumen.strftime('%d-%m-%Y')}</p>
                            {f'<p><strong>Jatuh Tempo:</strong> {jatuh_tempo.strftime("%d-%m-%Y")}</p>' if tipe_dokumen in ["Faktur / Invoice Cash", "Invoice Kredit"] else ''}
                        </div>
                    </div>

                    <div class="info-grid">
                        <div class="info-box">
                            <h4>Kepada Yth:</h4>
                            <p><strong>{nama_cust}</strong></p>
                            <p>{telp_cust}</p>
                            <p>{alamat_cust}</p>
                        </div>
                        <div class="info-box" style="text-align:right;">
                            <h4>Info Pembayaran:</h4>
                            <p><strong>{get_pengaturan("bank_nama")}</strong></p>
                            <p>No. Rek: {get_pengaturan("bank_rekening")}</p>
                            <p>A/N: {get_pengaturan("bank_atas_nama")}</p>
                        </div>
                    </div>

                    <table class="table-data">
                        <thead>
                            <tr>
                                <th style="width:10%; text-align:center;">QTY</th>
                                <th style="width:50%;">DESKRIPSI BARANG</th>
                                <th style="width:20%; text-align:right;">HARGA</th>
                                <th style="width:20%; text-align:right;">TOTAL</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>

                    <div class="total-box">
                        <div class="row grand-total">
                            <span>GRAND TOTAL:</span>
                            <span>{format_rp(total_semua)}</span>
                        </div>
                    </div>

                    <div class="footer">
                        <div class="terms">
                            <p><strong>Syarat & Ketentuan:</strong></p>
                            <p style="white-space: pre-wrap;">{catatan_tambahan}</p>
                        </div>
                        <div class="signature">
                            <p>Hormat Kami,</p>
                            {f'<img src="{ttd_base64}" alt="TTD">' if ttd_base64 else '<div style="height:60px;"></div>'}
                            <p><strong>{get_pengaturan("bisnis_nama")}</strong></p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            components.html(html_doc, height=1100, scrolling=True)
            st.info("💡 Tips: Klik tombol di bawah, lalu pada jendela print browser, pilih 'Save as PDF' dan centang 'Background Graphics'.")
            components.html(
                """
                <script>
                    window.print();
                </script>
                """,
                height=0,
            )
elif pilihan == "⚙️ Pengaturan Owner":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Owner</h1><p>Konfigurasi global toko dan skema kredit</p></div>', unsafe_allow_html=True)

    if st.session_state.role != "admin":
        st.error("⛔ Halaman ini hanya untuk Owner/Admin.")
        st.stop()

    st.subheader("⚙️ Pengaturan Global")
    with st.form("form_pengaturan_owner"):
        markup_default = st.number_input(
            "Markup Default Produk (%)",
            min_value=0.0,
            value=get_pengaturan_float("markup_default_persen", 5.0),
            step=0.5,
            help="Digunakan jika produk tidak memiliki markup manual."
        )
        bunga_flat = st.number_input(
            "Bunga Flat per 6 Bulan (%)",
            min_value=0.0,
            value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0),
            step=1.0,
            help="Bunga flat proporsional terhadap tenor."
        )
        dp_minimal = st.number_input(
            "DP Minimal (%)",
            min_value=0.0,
            max_value=100.0,
            value=get_pengaturan_float("dp_minimal_persen", 20.0),
            step=1.0
        )
        denda_harian = st.number_input(
            "Denda Keterlambatan per Hari (%)",
            min_value=0.0,
            value=get_pengaturan_float("denda_per_hari_persen", 0.4),
            step=0.1,
            help="Dihitung dari nilai cicilan bulanan."
        )
        tenor_options = st.text_input(
            "Pilihan Tenor (bulan, pisahkan dengan koma)",
            value=get_pengaturan("tenor_options", "1,2,3,6,12,18,24")
        )
        simpan = st.form_submit_button("💾 Simpan Pengaturan")
        if simpan:
            set_pengaturan("markup_default_persen", markup_default)
            set_pengaturan("bunga_flat_6bln_persen", bunga_flat)
            set_pengaturan("dp_minimal_persen", dp_minimal)
            set_pengaturan("denda_per_hari_persen", denda_harian)
            set_pengaturan("tenor_options", tenor_options)
            log_aksi(st.session_state.username, "UBAH_PENGATURAN", "Pengaturan global diperbarui")
            flash("Pengaturan berhasil disimpan.")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Pengaturan Saat Ini")
    df_setting = pd.read_sql_query("SELECT kunci as Kunci, nilai as Nilai, keterangan as Keterangan FROM pengaturan ORDER BY kunci", conn)
    st.dataframe(df_setting, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("ℹ️ Informasi Sistem")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Database", os.path.basename(DB_PATH), "card-dark"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Folder Backup", "backups", "card-blue"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Folder Upload", UPLOAD_DIR, "card-purple"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🧹 Pemeliharaan Database")
    st.warning("Gunakan fitur ini hanya jika diperlukan. Selalu backup database terlebih dahulu.")
    if st.button("Optimasi Database (VACUUM)"):
        try:
            conn.commit()
            c.execute("VACUUM")
            conn.commit()
            log_aksi(st.session_state.username, "VACUUM_DB", "Optimasi database")
            flash("Database berhasil dioptimasi.", "success")
        except Exception as e:
            st.error(f"Gagal optimasi database: {e}")
        st.rerun()

elif pilihan == "👤 Manajemen User":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1><p>Kelola akun pengguna sistem</p></div>', unsafe_allow_html=True)

    if st.session_state.role != "admin":
        st.error("⛔ Halaman ini hanya untuk Owner/Admin.")
        st.stop()

    tab1, tab2 = st.tabs(["📋 Daftar User", "➕ Tambah / Edit User"])

    with tab1:
        df_users = pd.read_sql_query("SELECT id as ID, username as Username, nama_lengkap as Nama_Lengkap, role as Role, aktif as Aktif FROM users ORDER BY id", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔐 Reset Password User")
        with st.form("form_reset_password"):
            df_user_pilih = pd.read_sql_query("SELECT id, username, nama_lengkap FROM users ORDER BY username", conn)
            if df_user_pilih.empty:
                st.info("Belum ada user.")
            else:
                opsi_user = {f"{row['username']} - {row['nama_lengkap']}": row['id'] for _, row in df_user_pilih.iterrows()}
                pilih_user = st.selectbox("Pilih User", list(opsi_user.keys()))
                user_id_reset = opsi_user[pilih_user]
                password_baru = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Reset Password"):
                    if not password_baru.strip():
                        st.error("Password baru tidak boleh kosong.")
                    else:
                        c.execute("UPDATE users SET password=? WHERE id=?", (hash_password(password_baru.strip()), user_id_reset))
                        conn.commit()
                        log_aksi(st.session_state.username, "RESET_PASSWORD", f"User ID {user_id_reset}")
                        flash("Password berhasil direset.")
                        st.rerun()

    with tab2:
        st.subheader("Tambah / Edit User")
        mode_user = st.radio("Mode", ["Tambah Baru", "Edit User"], horizontal=True)

        if mode_user == "Edit User":
            df_users_edit = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY username", conn)
            if df_users_edit.empty:
                st.info("Belum ada user untuk diedit.")
                user_edit_id = None
                data_user_lama = None
            else:
                opsi_edit_user = {f"ID {row['id']} - {row['username']} ({row['nama_lengkap']})": row['id'] for _, row in df_users_edit.iterrows()}
                pilih_edit_user = st.selectbox("Pilih User", list(opsi_edit_user.keys()))
                user_edit_id = opsi_edit_user[pilih_edit_user]
                data_user_lama = pd.read_sql_query("SELECT * FROM users WHERE id=?", conn, params=(user_edit_id,)).iloc[0]
        else:
            user_edit_id = None
            data_user_lama = None

        with st.form("form_user"):
            if data_user_lama is not None:
                username = st.text_input("Username", value=data_user_lama["username"] or "", disabled=True)
                nama_lengkap = st.text_input("Nama Lengkap", value=data_user_lama["nama_lengkap"] or "")
                role = st.selectbox("Role", ["admin", "kasir"], index=0 if data_user_lama["role"] == "admin" else 1)
                aktif = st.selectbox("Status", [1, 0], index=0 if data_user_lama["aktif"] == 1 else 1, format_func=lambda x: "Aktif" if x == 1 else "Nonaktif")
                password_baru = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
            else:
                username = st.text_input("Username")
                nama_lengkap = st.text_input("Nama Lengkap")
                role = st.selectbox("Role", ["admin", "kasir"])
                aktif = st.selectbox("Status", [1, 0], index=0, format_func=lambda x: "Aktif" if x == 1 else "Nonaktif")
                password_baru = st.text_input("Password", type="password")

            submitted_user = st.form_submit_button("Simpan User")
            if submitted_user:
                if mode_user == "Tambah Baru":
                    if not username.strip() or not nama_lengkap.strip() or not password_baru.strip():
                        st.error("Username, nama lengkap, dan password wajib diisi.")
                    else:
                        cek = c.execute("SELECT id FROM users WHERE username=?", (username.strip(),)).fetchone()
                        if cek:
                            st.error("Username sudah digunakan.")
                        else:
                            c.execute(
                                "INSERT INTO users (username, password, nama_lengkap, role, aktif) VALUES (?,?,?,?,?)",
                                (username.strip(), hash_password(password_baru.strip()), nama_lengkap.strip(), role, aktif)
                            )
                            conn.commit()
                            log_aksi(st.session_state.username, "TAMBAH_USER", f"{username} ({role})")
                            flash(f"User '{username}' berhasil ditambahkan.")
                            st.rerun()
                else:
                    if not nama_lengkap.strip():
                        st.error("Nama lengkap wajib diisi.")
                    else:
                        if password_baru.strip():
                            c.execute(
                                "UPDATE users SET password=?, nama_lengkap=?, role=?, aktif=? WHERE id=?",
                                (hash_password(password_baru.strip()), nama_lengkap.strip(), role, aktif, user_edit_id)
                            )
                        else:
                            c.execute(
                                "UPDATE users SET nama_lengkap=?, role=?, aktif=? WHERE id=?",
                                (nama_lengkap.strip(), role, aktif, user_edit_id)
                            )
                        conn.commit()
                        log_aksi(st.session_state.username, "EDIT_USER", f"User ID {user_edit_id}")
                        flash("Data user berhasil diperbarui.")
                        st.rerun()

elif pilihan == "📝 Log Aktivitas":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas</h1><p>Riwayat aktivitas pengguna sistem</p></div>', unsafe_allow_html=True)

    if st.session_state.role != "admin":
        st.error("⛔ Halaman ini hanya untuk Owner/Admin.")
        st.stop()

    df_log = pd.read_sql_query("SELECT id as ID, username as Username, aksi as Aksi, detail as Detail, waktu as Waktu FROM log_aktivitas ORDER BY id DESC", conn)

    if df_log.empty:
        st.info("Belum ada aktivitas tercatat.")
    else:
        st.subheader("🔍 Filter Log")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_user = st.selectbox("Filter Username", ["Semua"] + sorted(df_log["Username"].dropna().unique().tolist()))
        with col2:
            filter_aksi = st.selectbox("Filter Aksi", ["Semua"] + sorted(df_log["Aksi"].dropna().unique().tolist()))
        with col3:
            jumlah_tampil = st.number_input("Jumlah baris", min_value=10, max_value=1000, value=100, step=10)

        df_log_tampil = df_log.copy()
        if filter_user != "Semua":
            df_log_tampil = df_log_tampil[df_log_tampil["Username"] == filter_user]
        if filter_aksi != "Semua":
            df_log_tampil = df_log_tampil[df_log_tampil["Aksi"] == filter_aksi]

        st.dataframe(df_log_tampil.head(int(jumlah_tampil)), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📊 Statistik Aktivitas")
        df_stat_aksi = df_log.groupby("Aksi").size().reset_index(name="Jumlah").sort_values("Jumlah", ascending=False)
        st.dataframe(df_stat_aksi, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🧹 Bersihkan Log Lama")
        st.warning("Log yang lebih lama dari batas hari akan dihapus permanen.")
        hari_log = st.number_input("Hapus log lebih lama dari (hari)", min_value=1, max_value=365, value=30, step=1)
        konfirmasi_hapus_log = st.checkbox("Saya yakin ingin menghapus log lama")
        if st.button("Hapus Log Lama", disabled=not konfirmasi_hapus_log):
            try:
                c.execute(f"DELETE FROM log_aktivitas WHERE date(waktu) < date('now', '-{int(hari_log)} days')")
                conn.commit()
                log_aksi(st.session_state.username, "HAPUS_LOG", f"Log lebih lama dari {hari_log} hari")
                flash("Log lama berhasil dihapus.", "success")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menghapus log: {e}")
                
