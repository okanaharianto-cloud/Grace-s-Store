import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote
import altair as alt
import streamlit.components.v1 as components

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
ALAMAT_TOKO = "Sekolaq Darat RT 007 Kampung Sekolaq Darat Kec. Sekolaq Darat, Kab. Kutai Barat, Prov. Kaltim"

def is_pakaian(kat):
    return kat in PAKAIAN_KATEGORI

# ==================== KONEKSI DATABASE ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "toko_kredit.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
    
backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d')}.db")
if os.path.exists(DB_PATH) and not os.path.exists(backup_file):
    try:
        shutil.copy2(DB_PATH, backup_file)
    except Exception:
        pass

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
conn.commit()

# ==================== MIGRASI KOLOM ====================
for sql in [
    "ALTER TABLE produk ADD COLUMN markup_persen REAL DEFAULT 5.0",
    "ALTER TABLE produk ADD COLUMN harga_jual REAL",
    "ALTER TABLE transaksi_cash ADD COLUMN harga_jual_satuan REAL DEFAULT 0",
    "ALTER TABLE transaksi_cash ADD COLUMN laba REAL DEFAULT 0",
    "ALTER TABLE kredit ADD COLUMN tanggal_kredit TEXT",
    "ALTER TABLE customer ADD COLUMN nik TEXT",
    "ALTER TABLE customer ADD COLUMN tanggal_lahir TEXT",
    "ALTER TABLE customer ADD COLUMN status_kawin TEXT"
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

# ==================== SEED PENGATURAN DEFAULT ====================
DEFAULT_PENGATURAN = {
    "markup_default_persen":     ("5.0",   "Markup default (%) untuk produk non-pakaian"),
    "bunga_flat_6bln_persen":    ("40.0",  "Bunga flat per 6 bulan (%) untuk kredit"),
    "dp_minimal_persen":         ("20.0",  "DP minimal (%) dari harga cash"),
    "denda_per_hari_persen":     ("0.4",   "Denda keterlambatan per hari (%) dari cicilan"),
    "tenor_options":             ("1,2,3,6,12,18,24", "Pilihan tenor (bulan), pisahkan dengan koma"),
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

# Seed admin
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", ("admin", hash_password("admin123"), "Administrator", "admin"))
    conn.commit()

# ==================== SEED DATA ====================
def tanam_data_brosur():
    c.execute("SELECT COUNT(*) FROM produk")
    if c.fetchone()[0] == 0:
        data = [
            ("iPhone 17 256GB", "Gadget", 19046700, 10), ("iPhone 17 512GB", "Gadget", 22141900, 10),
            ("iPhone 17 PRO 256GB", "Gadget", 20951400, 10), ("iPhone 17 PRO 512GB", "Gadget", 25237100, 10),
            ("iPhone 17 PRO 1TB", "Gadget", 29761000, 10), ("iPhone 17 PRO MAX 256GB", "Gadget", 22856200, 10),
            ("iPhone 17 PRO MAX 512GB", "Gadget", 27141900, 10), ("iPhone 17 PRO MAX 1TB", "Gadget", 31427600, 10),
            ("iPhone 17 PRO MAX 2TB", "Gadget", 40237100, 10), ("iPhone 17 AIR 256GB", "Gadget", 15951400, 10),
            ("iPhone 17 AIR 512GB", "Gadget", 20237100, 10), ("iPhone 17 AIR 1TB", "Gadget", 23618100, 10),
            ("iPhone 17e 256GB", "Gadget", 12380000, 10), ("iPhone 17e 512GB", "Gadget", 16475200, 10),
            ("iPhone 16 128GB", "Gadget", 15951400, 10), ("iPhone 16 256GB", "Gadget", 16903800, 10),
            ("iPhone 16 PLUS 128GB", "Gadget", 15141900, 10), ("iPhone 16 PLUS 256GB", "Gadget", 16380000, 10),
            ("iPhone 15 128GB", "Gadget", 13332400, 10), ("Galaxy S26 Ultra 256GB", "Gadget", 23332400, 10),
            ("Galaxy S26 Ultra 512GB", "Gadget", 26189500, 10), ("Galaxy S26 Ultra 1TB", "Gadget", 30475200, 10),
            ("Galaxy S26+ 256GB", "Gadget", 18570500, 10), ("Galaxy S26+ 512GB", "Gadget", 21427600, 10),
            ("Galaxy S26 256GB", "Gadget", 15713300, 10), ("Galaxy S25 Ultra 256GB", "Gadget", 18570500, 10),
            ("Reno 16 Pro 256GB", "Gadget", 14284800, 10), ("Reno 16 256GB (8GB)", "Gadget", 11427600, 10),
            ("Reno 16 256GB (12GB)", "Gadget", 12380000, 10), ("Reno 16 F 128GB", "Gadget", 7618100, 10),
            ("Find X9 Ultra", "Gadget", 26665700, 10), ("OPPO A6 128GB", "Gadget", 3808600, 10),
        ]
        c.executemany("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", data)
        conn.commit()

def tanam_data_pakaian():
    existing = {row[0] for row in c.execute("SELECT nama FROM produk").fetchall()}
    data_pakaian = [
        ("Tunik Lop Top", "Atasan", 80000, 1), ("Rok Lurus", "Bawahan", 75000, 1),
        ("Atasan Orange", "Atasan", 70000, 1), ("Hem", "Atasan", 50000, 1),
        ("Mini Dress", "Dress", 50000, 2), ("Casual Dress", "Dress", 40000, 1),
        ("Atasan Polkadot", "Atasan", 70000, 1), ("Outer", "Outerwear", 70000, 2),
        ("Spanya Dress", "Dress", 50000, 3), ("Mini Dress Navy", "Dress", 75000, 1),
        ("Celana Merah", "Bawahan", 35000, 1), ("Batik Premium (Keterangan 2)", "Batik", 60000, 1),
        ("Batik Reguler (Keterangan 2)", "Batik", 50000, 10), ("Dress Premium (Keterangan 3)", "Dress", 50000, 30),
        ("Dress Ibu Merah", "Dress", 60000, 1), ("Dress Baru (Keterangan 3)", "Dress", 30000, 1),
        ("Jeans Wool", "Bawahan", 80000, 1), ("Midi Dress Hitam Merah", "Dress", 30000, 1),
        ("Atasan Ibu Merah", "Atasan", 50000, 1), ("Atasan Basic (Keterangan 3)", "Atasan", 20000, 5),
        ("Long Dress / Gamis (Keterangan 4)", "Dress", 50000, 20),
        ("Dress Putih Lengan Panjang", "Dress", 0, 5), ("Hoodie Orange Female Monster", "Atasan", 0, 5),
        ("Dress Stripe Hitam Putih", "Dress", 0, 5), ("Jumpeuit Apron Hitam", "Pakaian", 0, 5),
        ("Kemeja Two-Way Jolene Olive", "Atasan", 0, 5), ("Dress Double-Breasted Olive", "Dress", 0, 5),
        ("Dress Lace Pink Mutiara", "Dress", 0, 5), ("Blouse Ruffle Cream", "Atasan", 0, 5),
        ("Atasan Puff Sleeve Floral Mint", "Atasan", 0, 5), ("Dress Textured Khaki Sabuk", "Dress", 0, 5),
        ("Tunik Textured Abu-abu", "Atasan", 0, 5), ("Sweater Rajut Chunky Cream", "Atasan", 0, 5),
        ("Blouse Lace Turtleneck Putih", "Atasan", 0, 5), ("Trench Coat Khaki Pink Lining", "Outerwear", 0, 5),
        ("Dress Textured Abu Tanpa Lengan", "Dress", 0, 5), ("Dress Textured Beige Kancing", "Dress", 0, 5),
        ("Dress Pinafore Aurora Taupe", "Dress", 0, 5)
    ]
    for nama, kat, modal, stok in data_pakaian:
        if nama not in existing:
            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,0,NULL)", (nama, kat, modal, stok))
    conn.commit()

tanam_data_brosur()
tanam_data_pakaian()
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
        "🏠 Dashboard", "🧮 Input Produk & Skema", "📥 Barang Masuk", "🛒 Jual Cash", 
        "📤 Kredit Baru", "💰 Pembayaran Cicilan", "🖨️ Cetak Slip Kredit", "👥 Data Customer", 
        "📦 Stok Barang", "🚨 Overdue & Denda", "🔔 Alert & Reminder", "📊 Laporan & Analitik",
        "👕 Modal vs Profit", "💾 Backup, Cetak & Impor",
    ]
    if st.session_state.role == "admin":
        menu_list.extend(["⚙️ Pengaturan Owner", "👤 Manajemen User", "📝 Log Aktivitas"])

    pilihan = st.selectbox("📋 Menu", menu_list)
    st.markdown("---")
    if st.button("🚪 Logout"):
        log_aksi(st.session_state.username, "LOGOUT")
        for k in ["logged_in", "username", "nama", "role"]:
            st.session_state[k] = False if k == "logged_in" else ""
        st.session_state.pop("flash", None)
        for k in list(st.session_state.keys()):
            if k.startswith("_setting_"):
                st.session_state.pop(k, None)
        st.rerun()

show_flash()

# ==================== MENU: PENGATURAN OWNER ====================
if pilihan == "⚙️ Pengaturan Owner" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Owner</h1><p>Atur persentase default toko sesuai keinginan Anda</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><h3>💰 Markup / Margin Default</h3></div>', unsafe_allow_html=True)
    markup_val = st.number_input("Markup default untuk produk **non-pakaian** (%)", min_value=0.0, max_value=500.0, value=get_pengaturan_float("markup_default_persen", 5.0), step=1.0)
    if st.button("💾 Simpan Markup Default"):
        set_pengaturan("markup_default_persen", f"{markup_val:.2f}")
        flash(f"✅ Markup default diubah ke **{markup_val:.1f}%**", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>💳 Bunga Kredit Default</h3></div>', unsafe_allow_html=True)
    bunga_val = st.number_input("Bunga flat per **6 bulan** (%)", min_value=0.0, max_value=200.0, value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0)
    if st.button("💾 Simpan Bunga Default"):
        set_pengaturan("bunga_flat_6bln_persen", f"{bunga_val:.2f}")
        flash(f"✅ Bunga flat 6 bulan diubah ke **{bunga_val:.1f}%**", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>⏰ Denda Keterlambatan</h3></div>', unsafe_allow_html=True)
    denda_val = st.number_input("Denda per hari telat (% dari cicilan)", min_value=0.0, max_value=20.0, value=get_pengaturan_float("denda_per_hari_persen", 0.4), step=0.1, format="%.2f")
    if st.button("💾 Simpan Denda"):
        set_pengaturan("denda_per_hari_persen", f"{denda_val:.2f}")
        flash(f"✅ Denda diubah ke **{denda_val:.2f}% per hari**", "success")
        st.rerun()

# ==================== MENU: DASHBOARD ====================
elif pilihan == "🏠 Dashboard":
    st.markdown(f'<div class="main-header"><h1>🏠 Dashboard Utama</h1><p>Selamat datang kembali, <b>{st.session_state.nama}</b> 👋</p></div>', unsafe_allow_html=True)
    total_produk   = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    kredit_aktif   = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    total_piutang  = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]

    html = '<div class="metric-grid">'
    html += metric_card("📦 Total Produk", f"{total_produk} item", "card-blue")
    html += metric_card("💳 Kredit Aktif", f"{kredit_aktif} akun", "card-orange")
    html += metric_card("💰 Total Piutang", format_rp(total_piutang), "card-dark")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ==================== MENU: INPUT PRODUK ====================
elif pilihan == "🧮 Input Produk & Skema":
    st.markdown('<div class="main-header"><h1>🧮 Input Produk & Kalkulator Kredit</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Input Produk & Simulasi Skema")

# ==================== MENU: BARANG MASUK ====================
elif pilihan == "📥 Barang Masuk":
    st.markdown('<div class="main-header"><h1>📥 Input Barang Masuk (Restock)</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Barang Masuk")

# ==================== MENU: JUAL CASH ====================
elif pilihan == "🛒 Jual Cash":
    st.markdown('<div class="main-header"><h1>🛒 Kasir - Penjualan Tunai (Cash)</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Jual Cash")

# ==================== MENU: KREDIT BARU ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Transaksi Kredit Baru</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Kredit Baru")
    # ==================== MENU: PEMBAYARAN CICILAN ====================
elif pilihan == "💰 Pembayaran Cicilan":
    st.markdown('<div class="main-header"><h1>💰 Pembayaran Cicilan</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Pembayaran Cicilan")

# ==================== MENU: CETAK SLIP (OJK) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit & Perjanjian</h1><p>Dokumen cetak profesional sesuai standar OJK</p></div>', unsafe_allow_html=True)
    kid = 1 
    d = {'cn':'Lilis Wihani', 'telepon':'0812', 'alamat':'Jl. Trans', 'pn':'Samsung A07', 'produk_id':1, 'harga_cash':3118200, 'dp':630000, 'pokok_hutang':2488000, 'total_hutang':3528000, 'cicilan_bulan':588000, 'tenor':6, 'jatuh_tempo':'2026-12-15', 'status':'Berjalan'}
    m_harga_cash = d['harga_cash']
    m_dp = d['dp']
    m_pokok = d['pokok_hutang']
    m_total_hutang = d['total_hutang']
    m_cicilan = d['cicilan_bulan']
    m_tenor = d['tenor']
    m_tempo = datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d")
    m_status = d['status']
    m_metode = "Tunai"
    rate_bulan = 6.67 / 100
    tenor_asli = m_tenor
    nik_cust = '6407064804950002'
    tgl_lahir_cust = '03 April 1995'
    status_kawin_cust = 'Cerai Hidup'
    
    biaya_materai = 10000
    cicilan_terakhir = m_cicilan + biaya_materai
    tanggal_kredit_str = "2026-11-15"
    total_1 = m_total_hutang
    sched_1 = build_jadwal_angsuran(total_1, m_cicilan, tenor_asli, tanggal_kredit_str)
    rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='status-pending'>BELUM</span></td></tr>" for r in sched_1])
    
    html_schedule = f"""
    <div class="sched-wrap" style="grid-template-columns: 1fr;">
        <div class="sched">
            <div class="sched-h two">📅 Jadwal Angsuran — Tenor {tenor_asli}×</div>
            <table>
                <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL KEWAJIBAN</td><td class="r">{format_rp(total_1)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
            </table>
        </div>
    </div>
    """
    
    html_tenor_options = f"""
    <div class="tenor-options" style="grid-template-columns: 1fr;">
        <div class="tenor-card recommended">
            <div class="tc-label">Tenor Dipilih</div>
            <div class="tc-title">Tenor {tenor_asli}× ({tenor_asli} Bulan)</div>
            <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
        </div>
    </div>
    """

    perjanjian_html = f"""
    <div class="agreement-container">
        <div class="doc-title">
            <h2>PERJANJIAN PEMBIAYAAN KONSUMEN</h2>
            <div class="doc-number">Nomor: GRC-INV-{kid}/PERJ/2026</div>
        </div>
        <p>Pada hari ini, <b>{datetime.now().strftime('%d %B %Y')}</b>, yang bertanda tangan di bawah ini:</p>
        <table class="party-table">
            <tr>
                <td class="label"><b>PIHAK PERTAMA</b></td>
                <td>: <b>CV. GRACE HAVEN TRANSPORT</b> (Grace's Electronic), berkedudukan di Sekolaq Darat RT 007 RW 000, Kab. Kutai Barat, Prov. Kalimantan Timur. NIB: 1510260022275, NPWP: 1000 0000 1152 1195. Diwakili oleh <b>ADI HARIANTO, S.E.</b></td>
            </tr>
            <tr>
                <td class="label"><b>PIHAK KEDUA</b></td>
                <td>: <b>{d['cn'].upper()}</b>, lahir di Mencimai tanggal <b>{tgl_lahir_cust}</b>, Pekerjaan Wiraswasta, Status Perkawinan <b>{status_kawin_cust}</b>, beralamat di {d['alamat']}, Telp/WA: <b>{d['telepon']}</b>. NIK: <b>{nik_cust}</b>.</td>
            </tr>
        </table>
        <p>Kedua belah pihak sepakat untuk mengikatkan diri dalam Perjanjian Pembiayaan Konsumen dengan ketentuan sebagai berikut:</p>
        <div class="pasal-title">PASAL 1<br>OBJEK PERJANJIAN</div>
        <p>Pihak Pertama setuju untuk membiayai pembelian barang berupa <b>{d['pn']}</b> kepada Pihak Kedua.</p>
        
        <div class="pasal-title">PASAL 2<br>KETENTUAN PEMBAYARAN</div>
        <ol class="pasal-list">
            <li>Uang Muka (DP) yang telah dibayarkan oleh Pihak Kedua adalah sebesar <b>{format_rp(m_dp)}</b>.</li>
            <li>Total kewajiban angsuran yang harus dibayar oleh Pihak Kedua adalah sebesar <b>{format_rp(total_1)}</b>.</li>
            <li>Jangka waktu pembiayaan adalah <b>{tenor_asli} (bulan)</b>, dengan angsuran bulanan sebesar <b>{format_rp(m_cicilan)}</b>.</li>
            <li>Angsuran pertama wajib dibayarkan pada tanggal <b>{m_tempo.strftime('%d-%m-%Y')}</b> dan selanjutnya paling lambat pada tanggal yang sama setiap bulannya sampai dengan tanggal <b>{(m_tempo + timedelta(days=30*(tenor_asli-1))).strftime('%d-%m-%Y')}</b>.</li>
            <li>Pembayaran angsuran wajib dilakukan secara tunai di toko atau melalui transfer ke rekening resmi perusahaan: <b>Bank Mandiri No. Rekening 148-00-2889246-4 a.n. CV GRACE HAVEN TRANSPORT</b>.</li>
            <li>Pihak Kedua dikenakan <b>Biaya Administrasi berupa bea materai sebesar Rp 10.000</b> yang posisinya <b>BERADA DI LUAR nominal angsuran</b>. Total pembayaran pada bulan ke-{tenor_asli} adalah sebesar <b>{format_rp(cicilan_terakhir)}</b>.</li>
        </ol>
        
        <div class="pasal-title">PASAL 3<br>DENDA DAN WANPRESTASI</div>
        <ol class="pasal-list">
            <li>Apabila Pihak Kedua terlambat membayar angsuran melewati tanggal jatuh tempo, dikenakan denda sebesar <b>0,4% (nol koma empat persen) per hari</b> dari jumlah angsuran yang tertunggak, dengan total denda maksimal 100% dari pokok pembiayaan.</li>
            <li>Apabila Debitur mangkir/lalai dalam pembayaran, Kreditur berhak melaporkan Debitur ke <b>Sistem Layanan Informasi Keuangan (SLIK) OJK dan/atau BI Checking</b>, yang mengakibatkan Debitur masuk dalam daftar hitam (<i>blacklist</i>).</li>
        </ol>

        <div class="pasal-title">PASAL 4<br>PENYELESAIAN SENGKETA DAN DOMISILI</div>
        <ol class="pasal-list">
            <li>Segala perselisihan diselesaikan secara musyawarah.</li>
            <li>Apabila tidak mencapai kesepakatan, diselesaikan melalui <b>LAPS SJK</b> atau <b>Pengadilan Negeri Kutai Barat</b>.</li>
            <li>Kreditur dilarang melakukan penarikan objek pembiayaan secara paksa tanpa prosedur hukum yang sah sesuai POJK No. 22 Tahun 2023.</li>
        </ol>
    </div>
    """
    
    signature_html = f"""
    <div class="signature-area">
        <div class="sig-box">
            <div class="sig-title">PIHAK PERTAMA (KREDITUR)</div>
            <div class="cert-sig-box">
                <div class="cert-sig-header">🛡️ TERSERTIFIKASI</div>
                <div class="cert-sig-name">ADI HARIANTO, S.E.</div>
                <div class="cert-sig-text">Ditandatangani secara elektronik<br>Menggunakan Sertifikat PSrE</div>
                <div class="cert-sig-barcode"><svg id="signatureBarcode"></svg></div>
            </div>
            <div class="sig-name">ADI HARIANTO, S.E.</div>
            <div class="sig-role">Direktur CV. Grace Haven Transport</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">PIHAK KEDUA (DEBITUR)</div>
            <div class="ematerai-box">(Tempel e-Meterai / TTD Basah)</div>
            <div class="sig-name">{d['cn'].upper()}</div>
            <div class="sig-role">Pemegang KTP NIK: {nik_cust}</div>
        </div>
    </div>
    """

    html_page1 = f"""
    <div class="page">
        <header class="hdr">
            <div class="brand">
                <h1>GRACE'S ELECTRONIC</h1>
                <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                <div class="addr">Sekolaq Darat RT 007 RW 000, Kab. Kutai Barat<br>HP/WA: 0822-9954-8411</div>
            </div>
            <div class="title-box">
                <div class="badge-inv">Invoice Kredit</div>
                <div class="inv-no">#GRC-INV-{kid}</div>
                <div class="inv-date">{datetime.now().strftime('%d %B %Y')}</div>
            </div>
        </header>
        <div class="meta"><div>Status: <b style="color:var(--success);">● {m_status.upper()}</b></div><div>Metode: <b>{m_metode}</b></div></div>
        <div class="body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title">👤 Data Customer</div>
                    <div class="kv-row"><div class="k">Nama</div><div class="v">{d['cn']}</div></div>
                    <div class="kv-row"><div class="k">Telepon</div><div class="v">{d['telepon']}</div></div>
                    <div class="kv-row"><div class="k">NIK</div><div class="v">{nik_cust}</div></div>
                    <div class="kv-row"><div class="k">Alamat</div><div class="v" style="font-weight:400; font-size:10.5px;">{d['alamat']}</div></div>
                </div>
                <div class="card">
                    <div class="card-title">📱 Detail Produk</div>
                    <div class="kv-row"><div class="k">Nama</div><div class="v">{d['pn']}</div></div>
                    <div class="kv-row"><div class="k">SKU</div><div class="v">GRC-{d['produk_id']}</div></div>
                    <div class="kv-row"><div class="k">Garansi</div><div class="v">3 Bulan</div></div>
                </div>
            </div>
            <div class="summary-grid">
                <div class="sum-card green"><div class="lbl">DP Dibayar</div><div class="val">{format_rp(m_dp)}</div></div>
                <div class="sum-card amber"><div class="lbl">Angsuran / Bulan</div><div class="val">{format_rp(m_cicilan)}</div></div>
            </div>
            {html_tenor_options}
            {html_schedule}
            <div class="note-text">*Catatan: Terdapat Biaya Administrasi/Materai sebesar <b>Rp 10.000</b> (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir. Total yang disetor pada bulan ke-{tenor_asli} adalah {format_rp(cicilan_terakhir)}.</div>
            <div class="bank-box">
                <div class="title">Pembayaran Transfer Resmi</div>
                <div class="acc">Bank Mandiri: 148-00-2889246-4</div>
                <div class="name">a.n. CV GRACE HAVEN TRANSPORT</div>
            </div>
            <div class="info-box">
                <strong>⚠️ PENTING - KONSEKUENSI MANGKIR</strong>
                Jika Debitur lalai/mangkir dalam pembayaran angsuran, Kreditur berhak melaporkan Debitur ke <b>Sistem Layanan Informasi Keuangan (SLIK) OJK</b> dan/atau <b>BI Checking</b>. Hal ini mengakibatkan Debitur masuk dalam daftar hitam (blacklist).
            </div>
        </div>
        <footer class="footer">Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak.</footer>
    </div>
    """

    html_page2 = f"""
    <div class="page" style="page-break-before: always;">
        <header class="hdr">
            <div class="brand">
                <h1>GRACE'S ELECTRONIC</h1>
                <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                <div class="addr">Sekolaq Darat RT 007 RW 000, Kab. Kutai Barat<br>HP/WA: 0822-9954-8411</div>
            </div>
            <div class="title-box">
                <div class="badge-inv">Surat Perjanjian Kredit</div>
                <div class="inv-no">#GRC-INV-{kid}</div>
                <div class="inv-date">{datetime.now().strftime('%d %B %Y')}</div>
            </div>
        </header>
        <div class="body">
            {perjanjian_html}
            {signature_html}
        </div>
        <footer class="footer">Dokumen ini sah dan mengikat secara hukum.</footer>
    </div>
    """

    invoice_html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
    <style>
        :root {{ --primary: #1e3a8a; --primary-light: #eff6ff; --accent: #d97706; --accent-light: #fffbeb; --success: #059669; --success-light: #ecfdf5; --danger: #dc2626; --danger-light: #fef2f2; --text-main: #1f2937; --text-muted: #6b7280; --border: #e5e7eb; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif; background: #f3f4f6; padding: 20px 10px; color: var(--text-main); font-size: 12px; line-height: 1.4; }}
        .page {{ max-width: 820px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        .btn-print-wrap {{ position: sticky; top: 0; z-index: 9999; background: rgba(243,244,246,0.9); padding: 12px 0; text-align: center; border-bottom: 1px solid var(--border); margin-bottom: 20px; }}
        .btn-print {{ background: linear-gradient(135deg, #2563eb, #1e40af); color: white; border: none; padding: 10px 24px; font-size: 14px; border-radius: 50px; cursor: pointer; font-weight: 600; width: 100%; max-width: 350px; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }}
        .hdr {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: #fff; padding: 20px 24px; display: flex; justify-content: space-between; align-items: flex-start; position: relative; overflow: hidden; }}
        .brand {{ position: relative; z-index:1; max-width: 70%; }}
        .brand h1 {{ font-size: 22px; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 4px; }}
        .brand .tag {{ font-size: 11px; color: #93c5fd; font-weight: 500; letter-spacing: 0.5px; margin-bottom: 8px; }}
        .brand .addr {{ font-size: 10px; color: #cbd5e1; line-height: 1.5; font-weight: 400; }}
        .title-box {{ text-align: right; position: relative; z-index: 1; margin-top: 5px; }}
        .badge-inv {{ display: inline-block; background: rgba(217,119,6,0.2); color: #fcd34d; padding: 4px 12px; border-radius: 6px; font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; border: 1px solid rgba(217,119,6,0.4); margin-bottom: 8px; }}
        .inv-no {{ font-size: 15px; font-weight: 700; font-family: monospace; letter-spacing: 1px; }}
        .inv-date {{ font-size: 11px; color: #94a3b8; margin-top: 4px; }}
        .meta {{ display: flex; gap: 20px; justify-content: space-between; padding: 12px 24px; background: #f8fafc; border-bottom: 1px solid var(--border); font-size: 11px; color: var(--text-muted); }}
        .meta b {{ color: var(--text-main); }}
        .body {{ padding: 20px 24px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
        .card {{ border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; background: #fff; position: relative; }}
        .card-title {{ font-size: 10.5px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }}
        .kv-row {{ display: flex; margin-bottom: 6px; font-size: 11px; }}
        .kv-row:last-child {{ margin-bottom: 0; }}
        .kv-row .k {{ width: 65px; color: var(--text-muted); }}
        .kv-row .v {{ flex: 1; font-weight: 600; color: var(--text-main); }}
        .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
        .sum-card {{ border-radius: 8px; padding: 16px; text-align: center; border: 1px solid transparent; }}
        .sum-card.green {{ background: var(--success-light); border-color: #a7f3d0; }}
        .sum-card.amber {{ background: var(--accent-light); border-color: #fde68a; }}
        .sum-card .lbl {{ font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .sum-card .val {{ font-size: 20px; font-weight: 800; margin-top: 4px; }}
        .sum-card.green .val {{ color: var(--success); }}
        .sum-card.amber .val {{ color: var(--accent); }}
        .sched {{ border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin-bottom: 16px; }}
        .sched-h {{ padding: 10px 16px; font-size: 11px; font-weight: 700; color: #fff; background: var(--primary); }}
        .sched table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .sched th {{ background: #f8fafc; color: var(--text-muted); font-size: 9.5px; text-transform: uppercase; padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        .sched td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
        .sched tr:last-child td {{ border-bottom: none; }}
        .sched tr:nth-child(even) {{ background: #f9fafb; }}
        .sched .r {{ text-align: right; }}
        .sched .c {{ text-align: center; }}
        .sched .total td {{ background: var(--primary-light); font-weight: 700; color: var(--primary); border-top: 2px solid var(--primary); }}
        .status-pending {{ background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 9.5px; font-weight: 700; }}
        .status-lunas {{ background: #d1fae5; color: #065f46; padding: 2px 6px; border-radius: 4px; font-size: 9.5px; font-weight: 700; }}
        .note-text {{ font-size: 10px; color: #b91c1c; margin-top: -8px; margin-bottom: 16px; font-weight: 600; background: #fef2f2; padding: 8px 12px; border-radius: 6px; border: 1px solid #fecaca; }}
        .bank-box {{ background: var(--primary-light); border: 1px dashed var(--primary); border-radius: 6px; padding: 12px; margin-bottom: 16px; text-align: center; }}
        .bank-box .title {{ font-size: 10px; font-weight: 700; color: var(--primary); text-transform: uppercase; margin-bottom: 2px; }}
        .bank-box .acc {{ font-size: 18px; font-weight: 800; font-family: monospace; color: var(--primary); letter-spacing: 1px; }}
        .bank-box .name {{ font-size: 11px; font-weight: 600; color: var(--text-main); margin-top: 2px; }}
        .info-box {{ background: var(--danger-light); border: 1px solid #fecaca; border-left: 4px solid var(--danger); border-radius: 6px; padding: 12px 16px; font-size: 10.5px; color: #991b1b; }}
        .info-box strong {{ display: block; margin-bottom: 2px; font-size: 11px; }}
        .tenor-options {{ display: grid; gap: 8px; margin-bottom: 16px; }}
        .tenor-card {{ position: relative; border: 1.5px solid #d1d5db; border-radius: 8px; padding: 12px 16px; }}
        .tenor-card.recommended {{ border-color: #1e3a8a; }}
        .tenor-card.recommended::before {{ content: 'REKOMENDASI'; position: absolute; top: -1.5px; right: -1.5px; background: #b8956a; color: #fff; font-size: 7.5px; font-weight: 700; letter-spacing: 1px; padding: 2px 7px; border-radius: 0 6px 0 6px; }}
        .tc-label {{ font-size: 9px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }}
        .tc-title {{ font-family: Georgia, serif; font-size: 14px; font-weight: 700; color: #1a2b47; margin: 2px 0 6px; }}
        .tc-row {{ display: flex; justify-content: space-between; font-size: 10px; padding: 2px 0; }}
        .tc-row .k {{ color: #6b7280; }}
        .tc-row .v {{ color: #1a2b47; font-weight: 600; }}
        .tc-row.main {{ border-top: 1px solid #e5e7eb; padding-top: 4px; margin-top: 2px; }}
        .tc-row.main .k {{ font-weight: 700; color: #1a2b47; }}
        .tc-row.main .v {{ font-size: 13px; font-weight: 700; color: #b8956a; }}
        .agreement-container {{ background: #fff; padding: 10px 0; font-family: 'Times New Roman', Times, serif; font-size: 11px; color: #000; line-height: 1.35; }}
        .doc-title {{ text-align: center; margin-bottom: 15px; }}
        .doc-title h2 {{ font-size: 14px; font-weight: 700; text-transform: uppercase; text-decoration: underline; margin-bottom: 4px; }}
        .doc-number {{ font-size: 11px; font-weight: 600; text-align: center; margin: 0 auto; padding: 0; display: block; }}
        .agreement-container p {{ text-indent: 25px; text-align: justify; margin-bottom: 6px; }}
        .party-table {{ width: 100%; margin-bottom: 10px; border-collapse: collapse; }}
        .party-table td {{ vertical-align: top; padding: 2px 0; text-align: justify; }}
        .party-table .label {{ width: 110px; font-weight: normal; }}
        .pasal-title {{ font-weight: bold; text-align: center; margin-top: 12px; margin-bottom: 6px; text-decoration: underline; }}
        .pasal-list {{ padding-left: 25px; margin-bottom: 10px; text-align: justify; }}
        .pasal-list li {{ margin-bottom: 3px; }}
        .signature-area {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 25px; page-break-inside: avoid; align-items: flex-start; }}
        .sig-box {{ text-align: center; width: 100%; }}
        .sig-title {{ font-size: 11px; margin-bottom: 10px; font-weight: bold; }}
        .sig-name {{ font-weight: bold; text-decoration: underline; margin-top: 10px; font-size: 11px; }}
        .sig-role {{ font-size: 10.5px; }}
        .cert-sig-box {{ border: 1.5px solid #0ea5e9; border-radius: 6px; padding: 8px 5px; background: #f0f9ff; text-align: center; width: 180px; margin: 0 auto; }}
        .cert-sig-header {{ display: flex; align-items: center; justify-content: center; gap: 4px; color: #0284c7; font-weight: 700; font-size: 8px; margin-bottom: 4px; font-family: 'Inter', sans-serif; }}
        .cert-sig-name {{ font-weight: 800; font-size: 10px; color: #0f172a; margin-bottom: 2px; font-family: 'Inter', sans-serif; }}
        .cert-sig-text {{ font-size: 7.5px; color: #64748b; margin-bottom: 6px; font-family: 'Inter', sans-serif; line-height: 1.1; }}
        .cert-sig-barcode {{ background: #fff; padding: 2px; border-radius: 4px; display: flex; justify-content: center; width: 100%; }}
        .ematerai-box {{ width: 180px; height: 75px; margin: 0 auto; border: 1px dashed #94a3b8; display: flex; align-items: center; justify-content: center; font-size: 9px; color: #94a3b8; font-family: 'Inter', sans-serif; border-radius: 6px; background: #f8fafc; }}
        .footer {{ padding: 12px 24px; background: #f8fafc; border-top: 1px solid var(--border); text-align: center; font-size: 9.5px; color: var(--text-muted); }}
        @media print {{
            @page {{ size: A4 portrait; margin: 8mm 12mm; }}
            body {{ background: #fff; padding: 0; margin: 0; font-size: 10px; }}
            .btn-print-wrap {{ display: none !important; }}
            .page {{ box-shadow: none; border-radius: 0; max-width: 100%; width: 100%; margin-bottom: 0; page-break-after: always; }}
            .page:last-child {{ page-break-after: auto; }}
            .hdr {{ padding: 12px 20px; }}
            .brand h1 {{ font-size: 18px; }}
            .brand .addr {{ font-size: 8.5px; line-height: 1.4; margin-top: 4px; }}
            .meta {{ padding: 6px 20px; font-size: 9.5px; }}
            .body {{ padding: 12px 20px; }}
            .grid-2 {{ margin-bottom: 10px; gap: 10px; }}
            .card {{ padding: 8px 10px; }}
            .card-title {{ margin-bottom: 6px; font-size: 9.5px; }}
            .kv-row {{ margin-bottom: 4px; font-size: 10px; }}
            .summary-grid {{ margin-bottom: 10px; gap: 10px; }}
            .sum-card {{ padding: 10px; }}
            .sum-card .val {{ font-size: 16px; margin-top: 2px; }}
            .sched {{ margin-bottom: 10px; }}
            .sched-h {{ padding: 6px 12px; font-size: 10px; }}
            .sched th {{ padding: 4px 10px; font-size: 8.5px; }}
            .sched td {{ padding: 4px 10px; font-size: 9.5px; }}
            .note-text {{ padding: 6px 10px; font-size: 8.5px; margin-bottom: 10px; margin-top: -4px; }}
            .bank-box {{ padding: 8px; margin-bottom: 10px; }}
            .bank-box .acc {{ font-size: 16px; }}
            .info-box {{ padding: 8px 10px; font-size: 8.5px; }}
            .info-box strong {{ font-size: 9px; }}
            .footer {{ padding: 8px 20px; font-size: 8px; }}
            .agreement-container {{ padding: 0 10px; font-size: 10.5px; line-height: 1.3; }}
            .doc-title {{ margin-bottom: 10px; }}
            .pasal-title {{ margin-top: 10px; margin-bottom: 4px; }}
            .signature-area {{ margin-top: 20px; }}
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        }}
    </style>
    </head>
    <body>
        <div class="btn-print-wrap"><button class="btn-print" onclick="window.print()">🖨️ Cetak Invoice & Perjanjian</button></div>
        {html_page1}
        {html_page2}
        <script>
            window.onload = function() {{
                JsBarcode("#signatureBarcode", "PSrE-ADI-HARIANTO-2026", {{ format: "CODE128", width: 1.0, height: 25, displayValue: false, margin: 0, lineColor: "#0f172a", background: "#ffffff" }});
            }};
        </script>
    </body>
    </html>
    """
    components.html(invoice_html, height=1800, scrolling=True)
    st.download_button("📥 Download File Slip (HTML)", invoice_html, f"invoice_kredit_{kid}.html", "text/html", use_container_width=True)

# ==================== MENU: DATA CUSTOMER ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Pelanggan</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Data Pelanggan")

# ==================== MENU: STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)
    st.info("Fitur Stok Barang")

# ==================== MENU: SISA MENU ====================
elif pilihan in ["🚨 Overdue & Denda", "🔔 Alert & Reminder", "📊 Laporan & Analitik", "👕 Modal vs Profit", "💾 Backup, Cetak & Impor", "👤 Manajemen User", "📝 Log Aktivitas"]:
    st.markdown(f'<div class="main-header"><h1>{pilihan}</h1></div>', unsafe_allow_html=True)
    st.info(f"Fitur {pilihan} sedang dalam perbaikan.")
