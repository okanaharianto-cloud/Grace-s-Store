import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
import uuid
import io
from datetime import datetime, timedelta
import altair as alt
import streamlit.components.v1 as components
from PIL import Image
from PIL import Image

# ===== LIBRARY UNTUK  DOKUMEN =====
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image as PILImage
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

import re
# Di bagian atas file, setelah import
try:
    import pytesseract
    from PIL import Image as PILImage
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Tambahkan baris ini untuk mengatur path di Streamlit Cloud
if OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
# ==================== KONFIGURASI HALAMAN ====================
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
ALAMAT_TOKO = "Jl. Barong Tongkok, Kutai Barat"
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def is_pakaian(kat):
    return kat in PAKAIAN_KATEGORI

# ==================== KONEKSI DATABASE ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "toko_kredit.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
    
# Backup harian
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
    if st.session_state.get("snow"):
        st.snow(); st.session_state.snow = False

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        file_path = os.path.join(UPLOAD_DIR, f"{prefix}_{uuid.uuid4().hex[:8]}.jpg")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def auto_backup_database():
    """Fungsi untuk membackup database setiap 5 menit secara otomatis."""
    now = datetime.now()
    last_backup_time = st.session_state.get('last_backup_time', datetime.min)
    if (now - last_backup_time).total_seconds() >= 300: # 300 detik = 5 menit
        try:
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            backup_name = os.path.join(BACKUP_DIR, f"autobackup_{timestamp}.db")
            shutil.copy2(DB_PATH, backup_name)
            
            script_path = os.path.join(BASE_DIR, "toko.py")
            if os.path.exists(script_path):
                script_backup = os.path.join(BACKUP_DIR, f"script_autobackup_{timestamp}.py")
                shutil.copy2(script_path, script_backup)
                
            st.session_state['last_backup_time'] = now
            
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('autobackup_')], reverse=True)
            for old_b in backups[10:]:
                try: os.remove(os.path.join(BACKUP_DIR, old_b))
                except: pass
        except Exception:
            pass

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
        "🏠 Dashboard", 
        "🧮 Input Produk & Skema", 
        "📥 Barang Masuk", 
        "🛒 Jual Cash", 
        "📤 Kredit Baru",
        "📥 Import Dokumen (PDF/Word/Foto)", 
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
        st.session_state.pop("snow", None)
        for k in list(st.session_state.keys()):
            if k.startswith("_setting_"):
                st.session_state.pop(k, None)
        st.rerun()

show_flash()
auto_backup_database()

# ==================== 0. PENGATURAN OWNER ====================
if pilihan == "⚙️ Pengaturan Owner" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Owner</h1><p>Atur persentase default toko sesuai keinginan Anda</p></div>', unsafe_allow_html=True)
    st.info("💡 **PENTING:** Pengaturan di halaman ini adalah **NILAI DEFAULT** untuk transaksi baru. Saat Anda membuat Kredit Baru, Anda tetap bisa mengedit persentase Bunga dan DP secara manual per transaksi.")

    st.markdown('<div class="section-header"><h3>💰 Markup / Margin Default</h3></div>', unsafe_allow_html=True)
    markup_val = st.number_input("Markup default untuk produk **non-pakaian** (%)", min_value=0.0, max_value=500.0, value=get_pengaturan_float("markup_default_persen", 5.0), step=1.0, key="input_markup_owner")
    if st.button("💾 Simpan Markup Default", key="save_markup"):
        try:
            set_pengaturan("markup_default_persen", f"{markup_val:.2f}")
            log_aksi(st.session_state.username, "SET_MARKUP", f"{markup_val}%")
            flash(f"✅ Markup default diubah ke **{markup_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>💳 Bunga Kredit Default</h3></div>', unsafe_allow_html=True)
    bunga_val = st.number_input("Bunga flat per **6 bulan** (%)", min_value=0.0, max_value=200.0, value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0, key="input_bunga_owner")
    if st.button("💾 Simpan Bunga Default", key="save_bunga"):
        try:
            set_pengaturan("bunga_flat_6bln_persen", f"{bunga_val:.2f}")
            log_aksi(st.session_state.username, "SET_BUNGA", f"{bunga_val}%")
            flash(f"✅ Bunga flat 6 bulan diubah ke **{bunga_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>🪙 DP Minimal</h3></div>', unsafe_allow_html=True)
    dp_val = st.number_input("DP minimal (% dari harga cash)", min_value=0.0, max_value=100.0, value=get_pengaturan_float("dp_minimal_persen", 20.0), step=1.0, key="input_dp_owner")
    if st.button("💾 Simpan DP Minimal", key="save_dp"):
        try:
            set_pengaturan("dp_minimal_persen", f"{dp_val:.2f}")
            log_aksi(st.session_state.username, "SET_DP", f"{dp_val}%")
            flash(f"✅ DP minimal diubah ke **{dp_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>⏰ Denda Keterlambatan</h3></div>', unsafe_allow_html=True)
    denda_val = st.number_input("Denda per hari telat (% dari cicilan)", min_value=0.0, max_value=20.0, value=get_pengaturan_float("denda_per_hari_persen", 0.4), step=0.1, format="%.2f", key="input_denda_owner")
    if st.button("💾 Simpan Denda", key="save_denda"):
        try:
            set_pengaturan("denda_per_hari_persen", f"{denda_val:.2f}")
            log_aksi(st.session_state.username, "SET_DENDA", f"{denda_val}%")
            flash(f"✅ Denda diubah ke **{denda_val:.2f}% per hari**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📅 Pilihan Tenor</h3></div>', unsafe_allow_html=True)
    tenor_val = st.text_input("Pilihan tenor (bulan, pisahkan dengan koma)", value=get_pengaturan("tenor_options", "1,2,3,6,12,18,24"), key="input_tenor_owner")
    if st.button("💾 Simpan Tenor", key="save_tenor"):
        try:
            _ = [int(x.strip()) for x in tenor_val.split(",") if x.strip()]
            set_pengaturan("tenor_options", tenor_val)
            log_aksi(st.session_state.username, "SET_TENOR", tenor_val)
            flash(f"✅ Pilihan tenor diubah ke **{tenor_val}**", "success")
            st.rerun()
        except Exception:
            st.error("❌ Format tenor tidak valid. Gunakan angka dipisah koma, contoh: 1,3,6,12")

    st.markdown('<div class="section-header"><h3>🔄 Reset ke Default</h3></div>', unsafe_allow_html=True)
    st.warning("⚠️ Tombol ini akan mengembalikan **semua** pengaturan ke nilai default pabrik.")
    if st.button("🔄 Reset Semua Pengaturan ke Default"):
        try:
            for k, (v, ket) in DEFAULT_PENGATURAN.items():
                set_pengaturan(k, v, ket)
            log_aksi(st.session_state.username, "RESET_PENGATURAN", "Semua ke default")
            flash("✅ Semua pengaturan dikembalikan ke default!", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📋 Ringkasan Pengaturan Aktif</h3></div>', unsafe_allow_html=True)
    df_set = pd.read_sql_query("SELECT kunci, nilai, keterangan FROM pengaturan ORDER BY kunci", conn)
    st.dataframe(df_set, use_container_width=True, hide_index=True)

# ==================== 1. DASHBOARD ====================
elif pilihan == "🏠 Dashboard":
    st.markdown(f'<div class="main-header"><h1>🏠 Dashboard Utama</h1><p>Selamat datang kembali, <b>{st.session_state.nama}</b> 👋</p></div>', unsafe_allow_html=True)

    with st.expander("🧮 Simulasi Skema Kredit & Cash (Bisa Diedit)", expanded=True):
        st.markdown("Gunakan kalkulator ini untuk mensimulasikan skema ke customer. Anda bisa mengedit nilai di bawah dan menyembunyikan rincian tertentu untuk *Mode Presentasi Pelanggan*.")
        
        col_sim1, col_sim2, col_sim3 = st.columns(3)
        with col_sim1:
            sim_modal = st.number_input("Harga Modal (Rp)", min_value=0.0, value=1000000.0, step=100000.0)
            sim_dp_persen = st.number_input("DP (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
        with col_sim2:
            sim_markup = st.number_input("Markup (%)", min_value=0.0, value=10.0, step=1.0)
            sim_harga_jual = st.number_input("Harga Jual Override (Rp) - (0 = pakai markup)", min_value=0.0, value=0.0, step=100000.0)
        with col_sim3:
            sim_tenor = st.selectbox("Tenor (Bulan)", get_tenor_list(), index=min(3, len(get_tenor_list())-1))
            sim_bunga_6bln = st.number_input("Bunga Flat / 6 Bln (%)", min_value=0.0, value=40.0, step=1.0)
        
        hide_detail = st.toggle("🙈 Sembunyikan Rincian Sensitif (Mode Presentasi Pelanggan)", value=False, help="Jika aktif, hanya Harga Cash, DP, dan Cicilan yang muncul. Bunga, Pokok, dan Total Hutang disembunyikan.")

        h_cash = sim_harga_jual if sim_harga_jual > 0 else round(sim_modal * (1 + sim_markup/100), -2)
        dp_val = round(h_cash * sim_dp_persen / 100, -2)
        pokok = round(h_cash - dp_val, -2)
        rate_bulan = (sim_bunga_6bln / 100) / 6
        total_bunga = round(pokok * rate_bulan * sim_tenor, -2)
        total_hutang = pokok + total_bunga
        cicilan = round(total_hutang / sim_tenor, -2)

        st.markdown("### Hasil Simulasi:")
        html_sim = '<div class="metric-grid">'
        if not hide_detail:
            html_sim += metric_card("Harga Cash", format_rp(h_cash), "card-blue")
        html_sim += metric_card(f"DP ({sim_dp_persen}%)", format_rp(dp_val), "card-purple")
        html_sim += metric_card(f"Cicilan ({sim_tenor}x)", format_rp(cicilan), "card-pink")
        
        if not hide_detail:
            html_sim += metric_card("Pokok Hutang", format_rp(pokok), "card-dark")
            html_sim += metric_card("Total Bunga", format_rp(total_bunga), "card-orange")
            html_sim += metric_card("Total Hutang", format_rp(total_hutang), "card-dark")
            
        html_sim += '</div>'
        st.markdown(html_sim, unsafe_allow_html=True)

    st.markdown("---")

    total_produk   = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    total_stok     = c.execute("SELECT COALESCE(SUM(stok),0) FROM produk").fetchone()[0]
    total_customer = c.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    
    terjual_kredit = c.execute("SELECT COUNT(*) FROM kredit").fetchone()[0]
    terjual_cash = c.execute("SELECT COALESCE(SUM(jumlah),0) FROM transaksi_cash").fetchone()[0]
    total_terjual = terjual_kredit + terjual_cash

    kredit_aktif   = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    kredit_lunas   = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Lunas'").fetchone()[0]
    total_piutang  = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]

    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    overdue_count = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan' AND jatuh_tempo < ?", (tgl_skrg,)).fetchone()[0]

    pendapatan_kredit = c.execute("SELECT COALESCE(SUM(dp + total_hutang),0) FROM kredit").fetchone()[0]
    pendapatan_cash = c.execute("SELECT COALESCE(SUM(total_harga),0) FROM transaksi_cash").fetchone()[0]
    total_pendapatan = pendapatan_kredit + pendapatan_cash

    laba_kredit = c.execute("SELECT COALESCE(SUM((k.dp + k.total_hutang) - p.harga_modal),0) FROM kredit k JOIN produk p ON k.produk_id = p.id").fetchone()[0]
    laba_cash = c.execute("SELECT COALESCE(SUM(laba),0) FROM transaksi_cash").fetchone()[0]
    total_laba = laba_kredit + laba_cash

    margin_persen = (total_laba / total_pendapatan * 100) if total_pendapatan > 0 else 0
    pakaian_belum_harga = c.execute(f"SELECT COUNT(*) FROM produk WHERE kategori IN ({','.join(['?']*len(PAKAIAN_KATEGORI))}) AND (harga_jual IS NULL OR harga_jual <= 0)", tuple(PAKAIAN_KATEGORI)).fetchone()[0]
    
    pending_serah = c.execute("SELECT COUNT(*) FROM kredit WHERE id NOT IN (SELECT kredit_id FROM serah_terima)").fetchone()[0]

    html = '<div class="metric-grid">'
    html += metric_card("📦 Total Produk", f"{total_produk} item", "card-blue")
    html += metric_card("🎒 Total Stok", f"{total_stok} unit", "card-purple")
    html += metric_card("🛍️ Barang Terjual", f"{total_terjual} unit", "card-orange")
    html += metric_card("👥 Customer", f"{total_customer} orang", "card-green")
    html += metric_card("💳 Kredit Aktif", f"{kredit_aktif} akun", "card-orange")
    html += metric_card("💰 Total Piutang", format_rp(total_piutang), "card-dark")
    html += metric_card("💵 Total Pendapatan", format_rp(total_pendapatan), "card-blue")
    html += metric_card("💵 Total Laba", format_rp(total_laba), "card-green")
    html += metric_card("📈 Margin Laba", f"{margin_persen:.1f}%", "card-pink")
    html += metric_card("⚠️ Overdue", f"{overdue_count} akun", "card-pink")
    html += metric_card("✅ Kredit Lunas", f"{kredit_lunas} akun", "card-green")
    html += metric_card("📦 Pending Serah Terima", f"{pending_serah} akun", "card-pink")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    if pakaian_belum_harga > 0:
        st.warning(f"⚠️ **{pakaian_belum_harga} produk pakaian belum diisi harga jual.** Buka menu **📦 Stok Barang** → **Edit Harga Jual Pakaian**.")
        
    if pending_serah > 0:
        st.warning(f"⚠️ **{pending_serah} akun kredit belum diserahterimakan.** Segera buka menu **🤝 Serah Terima Barang** untuk mencegah pelanggan kabur.")

    st.markdown('<div class="section-header"><h3>📊 Analitik Penjualan</h3></div>', unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**🏆 Top 5 Produk Terlaris (Kredit + Cash)**")
        df_top = pd.read_sql_query("SELECT produk, SUM(qty) as jumlah_terjual FROM (SELECT p.nama as produk, 1 as qty FROM kredit k JOIN produk p ON k.produk_id = p.id UNION ALL SELECT p.nama as produk, t.jumlah as qty FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id) GROUP BY produk ORDER BY jumlah_terjual DESC LIMIT 5", conn)
        if not df_top.empty:
            chart = alt.Chart(df_top).mark_bar(cornerRadiusTopRight=10, cornerRadiusBottomRight=10).encode(x=alt.X('jumlah_terjual:Q', title='Jumlah Terjual'), y=alt.Y('produk:N', sort='-x', title='Produk'), color=alt.Color('jumlah_terjual:Q', scale=alt.Scale(scheme='purples'), legend=None)).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")

    with col_chart2:
        st.markdown("**📈 Cicilan Masuk per Bulan**")
        df_bayar = pd.read_sql_query("SELECT substr(tanggal,1,7) as bulan, SUM(jumlah_bayar) as total FROM pembayaran GROUP BY bulan ORDER BY bulan", conn)
        if not df_bayar.empty:
            chart = alt.Chart(df_bayar).mark_area(line={'color':'#667eea'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#f093fb', offset=0), alt.GradientStop(color='#667eea', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X('bulan:N', title='Bulan'), y=alt.Y('total:Q', title='Total (Rp)')).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada pembayaran")

    st.markdown('<div class="section-header"><h3>⚠️ Peringatan Stok Menipis (≤3 unit)</h3></div>', unsafe_allow_html=True)
    df_tipis = pd.read_sql_query("SELECT nama, kategori, stok FROM produk WHERE stok <= 3 ORDER BY stok ASC", conn)
    if not df_tipis.empty:
        st.dataframe(df_tipis, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Semua stok aman")

    st.markdown('<div class="section-header"><h3>⏰ Jatuh Tempo 7 Hari ke Depan</h3></div>', unsafe_allow_html=True)
    tgl_7 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    df_dekat = pd.read_sql_query("SELECT c.nama as customer, c.telepon, k.cicilan_bulan, k.jatuh_tempo FROM kredit k JOIN customer c ON k.customer_id = c.id WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ? ORDER BY k.jatuh_tempo", conn, params=(tgl_skrg, tgl_7))
    if not df_dekat.empty:
        st.dataframe(df_dekat, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Tidak ada jatuh tempo dalam 7 hari ke depan")

# ==================== 2. INPUT PRODUK & SKEMA ====================
elif pilihan == "🧮 Input Produk & Skema":
    st.markdown('<div class="main-header"><h1>🧮 Input Produk & Kalkulator Kredit</h1></div>', unsafe_allow_html=True)

    markup_default = get_pengaturan_float("markup_default_persen", 5.0)
    bunga_flat = get_pengaturan_float("bunga_flat_6bln_persen", 40.0)
    dp_min_persen = get_pengaturan_float("dp_minimal_persen", 20.0)
    tenor_list = get_tenor_list()

    with st.expander("➕ Tambah Produk Baru Manual", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nama_produk = st.text_input("Nama Produk")
            kategori = st.selectbox("Kategori", SEMUA_KATEGORI)
        with col2:
            harga_modal = st.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0)
            stok_awal = st.number_input("Stok Awal", min_value=0, step=1)

        if is_pakaian(kategori):
            st.info("👕 **Kategori pakaian**: isi **Harga Jual (Rp)** manual — markup dinonaktifkan.")
            harga_jual = st.number_input("Harga Jual (Rp)", min_value=0.0, step=1000.0, help="Harga yang akan dijual ke customer")
            markup_persen = 0
        else:
            st.info(f"⚙️ **Non-pakaian**: gunakan **Markup (%)** dari harga modal. *(default owner: {markup_default:.1f}%)*")
            markup_persen = st.number_input("Markup / Margin (%)", min_value=0.0, max_value=500.0, value=markup_default, step=1.0)
            harga_jual = None
            st.caption(f"💡 Harga Cash Otomatis = Modal × (1 + {markup_persen:.1f}%) = **{format_rp(round(harga_modal * (1 + markup_persen/100), -2))}**")

        if st.button("💾 Simpan Produk"):
            if not nama_produk or harga_modal <= 0:
                st.warning("⚠️ Nama dan harga modal wajib diisi")
            else:
                try:
                    c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,?,?)", (nama_produk, kategori, harga_modal, stok_awal, markup_persen, harga_jual))
                    conn.commit()
                    log_aksi(st.session_state.username, "TAMBAH_PRODUK", nama_produk)
                    flash(f"✅ Produk **{nama_produk}** berhasil disimpan!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan produk: {e}")

    st.markdown('<div class="section-header"><h3>⚙️ Simulasi Skema Kredit & Margin</h3></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        modal_sim = st.number_input("Harga Modal Simulasi (Rp)", min_value=0.0, value=5000000.0, step=100000.0)
        dp_sim = st.slider(f"DP (%) — minimal {dp_min_persen:.0f}%", int(dp_min_persen), 80, int(dp_min_persen), 5)
    with col2:
        tenor_sim = st.selectbox("Tenor (Bulan)", tenor_list, index=min(3, len(tenor_list)-1))
        bunga_sim = st.number_input(f"Bunga Flat / 6 Bln (%) — default owner: {bunga_flat:.1f}%", min_value=0.0, value=bunga_flat, step=1.0)

    harga_cash = round(modal_sim * (1 + markup_default/100), -2)
    dp_min     = round(harga_cash * dp_sim / 100, -2)
    rate       = (bunga_sim / 100) / 6
    bunga_total = rate * tenor_sim
    pokok = round(harga_cash - dp_min, -2)
    total = round(pokok * (1 + bunga_total), -2)
    cicilan = round(total / tenor_sim, -2) if tenor_sim > 0 else 0

    laba_kotor = (dp_min + total) - modal_sim
    margin_sim = (laba_kotor / (dp_min + total) * 100) if (dp_min + total) > 0 else 0

    html = '<div class="metric-grid">'
    html += metric_card("Harga Cash", format_rp(harga_cash), "card-blue")
    html += metric_card(f"DP ({dp_sim}%)", format_rp(dp_min), "card-purple")
    html += metric_card("Total Hutang", format_rp(total), "card-dark")
    html += metric_card("Laba Kotor", format_rp(laba_kotor), "card-green")
    html += metric_card("Margin Profit", f"{margin_sim:.1f}%", "card-orange")
    html += metric_card(f"Cicilan ({tenor_sim}x)", format_rp(cicilan), "card-pink")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ==================== 3. BARANG MASUK ====================
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
            try:
                c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)", (pid, jumlah, datetime.now().strftime("%Y-%m-%d")))
                c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah, pid))
                conn.commit()
                log_aksi(st.session_state.username, "RESTOCK", f"Produk ID {pid}, +{jumlah}")
                flash(f"✅ Stok bertambah {jumlah} unit!", "success")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Gagal: {e}")

        st.markdown('<div class="section-header"><h3>📜 Riwayat Barang Masuk Terakhir</h3></div>', unsafe_allow_html=True)
        df_in = pd.read_sql_query("SELECT t.id, t.produk_id, p.nama as produk, t.jumlah, t.tanggal FROM transaksi_in t JOIN produk p ON t.produk_id = p.id ORDER BY t.id DESC LIMIT 20", conn)
        st.dataframe(df_in.drop(columns=['id', 'produk_id']), use_container_width=True, hide_index=True)
        
        if not df_in.empty:
            st.markdown("**✏️ Edit / Hapus Barang Masuk**")
            opsi_in = {f"ID #{r['id']} - {r['produk']} - {r['jumlah']} unit ({r['tanggal']})": (r['id'], r['produk_id'], r['jumlah'], r['tanggal']) for _, r in df_in.iterrows()}
            pilih_in = st.selectbox("Pilih Riwayat Barang Masuk", list(opsi_in.keys()), key="sel_edit_in")
            id_in, pid_in, qty_in, tgl_in = opsi_in[pilih_in]
            
            with st.form("form_edit_in"):
                col_ed1, col_ed2 = st.columns(2)
                with col_ed1:
                    new_qty = st.number_input("Jumlah Masuk Baru", min_value=1, value=int(qty_in), step=1)
                with col_ed2:
                    new_tgl_in = st.date_input("Tanggal Masuk Baru", value=pd.to_datetime(tgl_in).date())
                    
                colA, colB = st.columns(2)
                with colA:
                    sub_edit_in = st.form_submit_button("💾 Update Data")
                with colB:
                    sub_hapus_in = st.form_submit_button("🗑️ Hapus Riwayat")
                    
                if sub_edit_in:
                    try:
                        selisih = new_qty - qty_in
                        c.execute("UPDATE transaksi_in SET jumlah=?, tanggal=? WHERE id=?", (new_qty, new_tgl_in.strftime("%Y-%m-%d"), id_in))
                        c.execute("UPDATE produk SET stok = stok + ? WHERE id=?", (selisih, pid_in))
                        conn.commit()
                        flash("✅ Barang masuk diupdate & stok disesuaikan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                        
                if sub_hapus_in:
                    try:
                        c.execute("DELETE FROM transaksi_in WHERE id=?", (id_in,))
                        c.execute("UPDATE produk SET stok = stok - ? WHERE id=?", (qty_in, pid_in))
                        conn.commit()
                        flash("🗑️ Riwayat barang masuk dihapus & stok dikurangi!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")


# ==================== 4. JUAL CASH ====================
elif pilihan == "🛒 Jual Cash":
    st.markdown('<div class="main-header"><h1>🛒 Kasir - Penjualan Tunai (Cash)</h1><p>Masukkan Harga Jual manual, sistem otomatis hitung profit.</p></div>', unsafe_allow_html=True)
    
    df_prod = pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok, COALESCE(markup_persen, 5) as markup_persen, harga_jual FROM produk WHERE stok > 0 ORDER BY nama", conn)

    if df_prod.empty:
        st.warning("⚠️ Semua stok barang kosong.")
    else:
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.markdown('<div class="section-header"><h3>💵 Input Transaksi</h3></div>', unsafe_allow_html=True)
            
            opsi_prod = {f"{r['nama']} | Modal: {format_rp(r['harga_modal'])} | Sisa: {r['stok']}": (r['id'], r['nama'], r['kategori'], r['harga_modal'], r['markup_persen'], r['harga_jual'], r['stok']) for _, r in df_prod.iterrows()}
            pilih_p = st.selectbox("📱 Pilih Produk", list(opsi_prod.keys()))
            
            id_p, nama_p, kat_p, mod_p, mk_p, hj_p, stok_p = opsi_prod[pilih_p]
            
            default_price = hitung_harga_cash(mod_p, mk_p, hj_p)
            
            with st.form("form_jual_cash"):
                st.info(f"Harga Modal Produk ini: **{format_rp(mod_p)}**")
                
                harga_jual_input = st.number_input(
                    "Harga Jual Satuan (Rp) - *Bisa diubah*", 
                    min_value=0.0, 
                    value=float(default_price), 
                    step=1000.0,
                    help="Anda bisa menegosiasi harga jual di sini. Profit akan dihitung otomatis."
                )
                
                jumlah_beli = st.number_input("Jumlah Beli", min_value=1, max_value=int(stok_p), value=1, step=1)
                
                total_belanja = harga_jual_input * jumlah_beli
                
                profit_satuan = harga_jual_input - mod_p
                total_profit = profit_satuan * jumlah_beli
                
                st.markdown(f"### Total Belanja: **{format_rp(total_belanja)}**")
                
                if profit_satuan < 0:
                    st.error(f"⚠️ **RUGI!** Anda menjual di bawah modal. (Rugi: {format_rp(abs(total_profit))})")
                else:
                    st.success(f"📈 **Estimasi Profit:** **{format_rp(total_profit)}** ({format_rp(profit_satuan)}/pcs)")
                
                uang_bayar = st.number_input("Uang Diterima (Rp)", min_value=0.0, value=float(total_belanja), step=10000.0)
                kembalian = uang_bayar - total_belanja
                
                if uang_bayar >= total_belanja:
                    st.info(f"Kembalian: **{format_rp(kembalian)}**")
                else:
                    st.warning(f"Uang Kurang: **{format_rp(abs(kembalian))}**")
                    
                submit_cash = st.form_submit_button("💳 Proses Pembayaran")
                
                if submit_cash:
                    if uang_bayar < total_belanja:
                        st.error("❌ Transaksi gagal: Uang pembayaran kurang.")
                    else:
                        try:
                            c.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (jumlah_beli, id_p))
                            c.execute('''INSERT INTO transaksi_cash (produk_id, jumlah, harga_jual_satuan, total_harga, uang_bayar, kembalian, laba, tanggal) 
                                         VALUES (?,?,?,?,?,?,?,?)''', 
                                      (id_p, jumlah_beli, harga_jual_input, total_belanja, uang_bayar, kembalian, total_profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            log_aksi(st.session_state.username, "JUAL_CASH", f"{nama_p} x{jumlah_beli}, Profit: {total_profit}")
                            flash(f"🎉 Transaksi Berhasil! {nama_p} terjual {jumlah_beli} unit.", "success")
                            st.session_state.balloons = True
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")

        with col2:
            st.markdown('<div class="section-header"><h3>🧾 Struk Transaksi Terakhir</h3></div>', unsafe_allow_html=True)
            df_riw = pd.read_sql_query("""
                SELECT t.id, t.tanggal, p.nama as produk, t.jumlah, t.harga_jual_satuan, t.total_harga, t.uang_bayar, t.kembalian, t.laba 
                FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id 
                ORDER BY t.id DESC LIMIT 1
            """, conn)
            
            if not df_riw.empty:
                r = df_riw.iloc[0]
                st.markdown(f"""
                <div style="border: 1px dashed #ccc; padding: 20px; border-radius: 10px; background-color: white; color: #333;">
                    <h3 style="text-align: center; margin-bottom: 0; color:#667eea;">GRACE STORE</h3>
                    <p style="text-align: center; font-size: 12px; color: #666;">{r['tanggal']}</p>
                    <hr style="border-top: 1px dashed #ccc;">
                    <table style="width: 100%; font-size: 14px;">
                        <tr><td><b>{r['produk']}</b></td></tr>
                        <tr><td>{r['jumlah']} x {format_rp(r['harga_jual_satuan'])}</td><td style="text-align: right;">{format_rp(r['total_harga'])}</td></tr>
                    </table>
                    <hr style="border-top: 1px dashed #ccc;">
                    <table style="width: 100%; font-size: 14px;">
                        <tr><td><b>Total</b></td><td style="text-align: right;"><b>{format_rp(r['total_harga'])}</b></td></tr>
                        <tr><td>Tunai</td><td style="text-align: right;">{format_rp(r['uang_bayar'])}</td></tr>
                        <tr><td>Kembali</td><td style="text-align: right;">{format_rp(r['kembalian'])}</td></tr>
                    </table>
                    <hr style="border-top: 1px dashed #ccc;">
                    <p style="text-align: center; font-size: 11px; color: #888;">Profit Toko: {format_rp(r['laba'])}</p>
                    <p style="text-align: center; font-size: 12px;">Terima Kasih!</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Belum ada transaksi tunai pada sesi ini.")
                
            st.markdown('<div class="section-header"><h3>📜 Riwayat Jual Cash (5 Terakhir)</h3></div>', unsafe_allow_html=True)
            df_riw_all = pd.read_sql_query("""
                SELECT t.id, t.produk_id, t.tanggal, p.nama as produk, t.jumlah, t.harga_jual_satuan, t.uang_bayar, t.total_harga, t.laba 
                FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id 
                ORDER BY t.id DESC LIMIT 5
            """, conn)
            
            if not df_riw_all.empty:
                df_show = df_riw_all.drop(columns=['id', 'produk_id', 'harga_jual_satuan', 'uang_bayar']).copy()
                df_show['total_harga'] = df_show['total_harga'].apply(format_rp)
                df_show['laba'] = df_show['laba'].apply(format_rp)
                df_show = df_show.rename(columns={'tanggal':'Tanggal', 'produk':'Produk', 'jumlah':'Qty', 'total_harga':'Total Jual', 'laba':'Profit'})
                st.dataframe(df_show, use_container_width=True, hide_index=True)
                
                st.markdown("**🗑️ Hapus Transaksi & Kembalikan Stok**")
                opsi_hapus = {f"ID #{r['id']} - {r['produk']} - {format_rp(r['total_harga'])} ({r['tanggal']})": (r['id'], r['produk_id'], r['jumlah']) for _, r in df_riw_all.iterrows()}
                pilih_hapus = st.selectbox("Pilih transaksi yang ingin dihapus:", list(opsi_hapus.keys()))
                
                if st.button("Hapus Transaksi Terpilih", type="primary"):
                    id_transaksi, produk_id, qty = opsi_hapus[pilih_hapus]
                    try:
                        c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (qty, produk_id))
                        c.execute("DELETE FROM transaksi_cash WHERE id = ?", (id_transaksi,))
                        conn.commit()
                        log_aksi(st.session_state.username, "HAPUS_CASH", f"ID {id_transaksi}, Kembalikan Stok {qty}")
                        flash("🗑️ Transaksi berhasil dihapus dan stok telah dikembalikan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                st.markdown("**✏️ Edit Harga / Jumlah / Nominal Transaksi**")
                opsi_edit_cash = {f"ID #{r['id']} - {r['produk']} - {format_rp(r['total_harga'])} ({r['tanggal']})": r['id'] for _, r in df_riw_all.iterrows()}
                pilih_edit_cash = st.selectbox("Pilih transaksi untuk diedit:", list(opsi_edit_cash.keys()), key="sel_edit_cash")
                id_edit_cash = opsi_edit_cash[pilih_edit_cash]
                
                detail_cash = df_riw_all[df_riw_all['id'] == id_edit_cash].iloc[0]
                
                produk_id_edit = int(detail_cash['produk_id'])
                row_modal = c.execute("SELECT harga_modal FROM produk WHERE id=?", (produk_id_edit,)).fetchone()

                if row_modal is None:
                    st.error("❌ Data produk untuk transaksi ini tidak ditemukan di database.")
                    st.stop()
                    
                modal_asli = row_modal[0]

                with st.form("form_edit_cash"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_hj = st.number_input("Harga Jual Satuan Baru (Rp)", value=float(detail_cash['harga_jual_satuan']), step=1000.0)
                    with col2:
                        new_qty_cash = st.number_input("Jumlah Beli Baru", min_value=1, value=int(detail_cash['jumlah']), step=1)
                    with col3:
                        new_uang = st.number_input("Uang Diterima Baru (Rp)", value=float(detail_cash['uang_bayar']), step=10000.0)
                    
                    if st.form_submit_button("💾 Simpan Perubahan"):
                        try:
                            # Konversi ke int untuk mencegah error sqlite
                            selisih_qty = int(new_qty_cash) - int(detail_cash['jumlah'])
                            stok_tersedia = c.execute("SELECT stok FROM produk WHERE id=?", (produk_id_edit,)).fetchone()[0]
                            
                            if selisih_qty > 0 and stok_tersedia < selisih_qty:
                                st.error(f"❌ Stok tidak mencukupi untuk menambah {selisih_qty} unit! Sisa stok: {stok_tersedia}")
                            else:
                                new_total = new_hj * new_qty_cash
                                new_profit = (new_hj - modal_asli) * new_qty_cash
                                new_kembalian = new_uang - new_total
                                
                                if new_uang < new_total:
                                    st.error("❌ Uang diterima kurang dari total belanja baru!")
                                else:
                                    c.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (selisih_qty, produk_id_edit))
                                    c.execute("""UPDATE transaksi_cash SET harga_jual_satuan=?, jumlah=?, total_harga=?, uang_bayar=?, kembalian=?, laba=? WHERE id=?""",
                                              (new_hj, new_qty_cash, new_total, new_uang, new_kembalian, new_profit, id_edit_cash))
                                    conn.commit()
                                    log_aksi(st.session_state.username, "EDIT_CASH", f"ID {id_edit_cash}")
                                    flash("✅ Transaksi berhasil diupdate, stok & profit disesuaikan!", "success")
                                    st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")
            else:
                st.write("Belum ada data.")

# ==================== 5. KREDIT BARU (DENGAN FITUR EDIT/DELETE/CANCEL) ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Transaksi Kredit Baru</h1></div>', unsafe_allow_html=True)

    # SUB-MENU UNTUK EDIT / HAPUS KREDIT
    tab_input, tab_edit = st.tabs(["➕ Buat Kredit Baru", "✏️ Edit / Hapus / Batalkan Kredit"])
    
    with tab_input:
        bunga_flat_default = get_pengaturan_float("bunga_flat_6bln_persen", 40.0)
        dp_min_persen_default = get_pengaturan_float("dp_minimal_persen", 20.0)
        tenor_list = get_tenor_list()

        df_cust = pd.read_sql_query("SELECT id, nama FROM customer ORDER BY nama", conn)
        df_prod = pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok, COALESCE(markup_persen, 5) as markup_persen, harga_jual FROM produk WHERE stok > 0 ORDER BY nama", conn)

        if df_cust.empty or df_prod.empty:
            st.warning("⚠️ Pastikan Data Customer dan Stok Barang Tersedia!")
        else:
            col1, col2 = st.columns(2)
            with col1:
                opsi_cust = {f"{r['nama']} (ID: {r['id']})": r['id'] for _, r in df_cust.iterrows()}
                pilih_c = st.selectbox("👤 Pilih Customer", list(opsi_cust.keys()))
            with col2:
                opsi_prod = {f"{r['nama']} (stok: {r['stok']})": (r['id'], r['nama'], r['kategori'], r['harga_modal'], r['markup_persen'], r['harga_jual']) for _, r in df_prod.iterrows()}
                pilih_p = st.selectbox("📱 Pilih Produk", list(opsi_prod.keys()))

            id_p, nama_p, kat_p, mod_p, mk_p, hj_p = opsi_prod[pilih_p]

            if is_pakaian(kat_p) and (not hj_p or hj_p <= 0):
                st.error(f"❌ Harga jual untuk **{nama_p}** belum diisi.\n\nBuka menu **📦 Stok Barang** → tab **Edit Harga Jual Pakaian** untuk mengisi harga jual terlebih dahulu.")
                st.stop()

            h_cash = hitung_harga_cash(mod_p, mk_p, hj_p)

            if is_pakaian(kat_p):
                st.caption(f"👕 Pakaian — **Harga Jual (manual)**: {format_rp(h_cash)}")
            else:
                st.caption(f"⚙️ Markup: **{mk_p:.0f}%** — Harga Cash: {format_rp(h_cash)}")

            st.markdown('<div class="section-header"><h3>💰 Pengaturan DP & Bunga (Bisa Diedit Manual)</h3></div>', unsafe_allow_html=True)
            
            col_dp, col_tenor, col_bunga = st.columns(3)
            with col_dp:
                # Mengubah min_value menjadi 0.0 agar bisa diketik manual berapapun
                dp_persen = st.number_input("DP (%)", min_value=0.0, max_value=100.0, value=float(dp_min_persen_default), step=1.0, help=f"Minimal DP dari Owner adalah {dp_min_persen_default}%")
                if dp_persen < dp_min_persen_default:
                    st.warning(f"⚠️ DP di bawah batas minimal Owner ({dp_min_persen_default}%). Pastikan sudah disetujui!")
            with col_tenor:
                tenor = st.selectbox("Tenor (Bulan)", tenor_list, index=min(3, len(tenor_list)-1))
            with col_bunga:
                bunga_flat = st.number_input("Bunga Flat / 6 Bln (%)", min_value=0.0, value=float(bunga_flat_default), step=1.0, help="Bisa diubah manual jika ada nego bunga")
            dp = round(h_cash * dp_persen / 100, -2)
            rate = (bunga_flat / 100) / 6
            bunga_total = rate * tenor
            pokok = round(h_cash - dp, -2)
            total = round(pokok * (1 + bunga_total), -2)
            cicilan = round(total / tenor, -2) if tenor > 0 else 0

            revenue = dp + total
            laba_transaksi = revenue - mod_p
            margin_transaksi = (laba_transaksi / revenue * 100) if revenue > 0 else 0

            html = '<div class="metric-grid">'
            html += metric_card("Harga Cash", format_rp(h_cash), "card-blue")
            html += metric_card("Nominal DP", format_rp(dp), "card-purple")
            html += metric_card("Total Hutang", format_rp(total), "card-dark")
            html += metric_card("Potensi Laba", format_rp(laba_transaksi), "card-green")
            html += metric_card("Margin (%)", f"{margin_transaksi:.1f}%", "card-orange")
            html += metric_card("Cicilan / Bulan", format_rp(cicilan), "card-pink")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
            st.caption(f"⚙️ Bunga transaksi ini: **{bunga_flat:.1f}% / 6 bulan** → tenor {tenor} bln = {bunga_total*100:.1f}%")

            cek = c.execute("SELECT COUNT(*) FROM kredit WHERE customer_id=? AND status='Berjalan'", (opsi_cust[pilih_c],)).fetchone()[0]
            if cek > 0:
                st.warning(f"⚠️ Customer ini punya {cek} kredit aktif. Pastikan tidak menumpuk!")

            if st.button("✅ Proses Kredit & Keluarkan Barang"):
                id_c = opsi_cust[pilih_c]
                tgl_kredit = datetime.now().strftime("%Y-%m-%d")
                tgl_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                try:
                    c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit, updated_at, updated_by) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (id_c, id_p, h_cash, dp, pokok, total, tenor, cicilan, total, tgl_tempo, "Berjalan", tgl_kredit, get_current_time(), st.session_state.username))
                    c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
                    conn.commit()
                    log_aksi(st.session_state.username, "KREDIT_BARU", f"Customer {pilih_c}, Produk {pilih_p}")
                    flash("🎉 Akad kredit berhasil! Silakan buka menu **🖨️ Cetak Slip Kredit** untuk mencetak invoice.", "success")
                    st.session_state.balloons = True
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan kredit: {e}")

    with tab_edit:
        st.subheader("Edit / Hapus / Batalkan Kredit")
        st.info("Gunakan tab ini jika ada kesalahan input data kredit. Menghapus data akan mengembalikan stok barang.")
        
        df_kredit_all = pd.read_sql_query("""
            SELECT k.id, c.nama as customer, p.nama as produk, k.status, k.total_hutang
            FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id
            ORDER BY k.id DESC
        """, conn)
        
        if not df_kredit_all.empty:
            opsi_kredit = {f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})": r['id'] for _, r in df_kredit_all.iterrows()}
            pilih_kredit = st.selectbox("Pilih Kredit yang akan diedit/dihapus", list(opsi_kredit.keys()))
            kid = opsi_kredit[pilih_kredit]
            
            d = pd.read_sql_query("SELECT * FROM kredit WHERE id=?", conn, params=(kid,)).iloc[0]
            
            with st.form("form_edit_kredit_baru"):
                col1, col2 = st.columns(2)
                with col1:
                    m_harga_cash = st.number_input("Harga Cash", value=float(d['harga_cash']), step=10000.0)
                    m_dp = st.number_input("DP", value=float(d['dp']), step=10000.0)
                    m_status = st.selectbox("Status Kredit", ["Berjalan", "Lunas", "Batal"], index=["Berjalan", "Lunas", "Batal"].index(d['status']))
                with col2:
                    m_total = st.number_input("Total Hutang", value=float(d['total_hutang']), step=10000.0)
                    m_cicilan = st.number_input("Cicilan / Bulan", value=float(d['cicilan_bulan']), step=10000.0)
                    m_tenor = st.number_input("Tenor (Bulan)", value=int(d['tenor']), min_value=1)
                
                submit_edit = st.form_submit_button("💾 Simpan Perubahan")
                if submit_edit:
                    try:
                        c.execute("UPDATE kredit SET harga_cash=?, dp=?, total_hutang=?, cicilan_bulan=?, tenor=?, status=? WHERE id=?", 
                                  (m_harga_cash, m_dp, m_total, m_cicilan, m_tenor, m_status, kid))
                        conn.commit()
                        flash("✅ Data Kredit berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                        
            if st.button("🗑️ Hapus Kredit & Kembalikan Stok", type="primary"):
                try:
                    produk_id = d['produk_id']
                    # Kembalikan stok
                    c.execute("UPDATE produk SET stok = stok + 1 WHERE id = ?", (produk_id,))
                    # Hapus riwayat pembayaran terkait
                    c.execute("DELETE FROM pembayaran WHERE kredit_id = ?", (kid,))
                    # Hapus serah terima terkait
                    c.execute("DELETE FROM serah_terima WHERE kredit_id = ?", (kid,))
                    # Hapus kredit
                    c.execute("DELETE FROM kredit WHERE id = ?", (kid,))
                    conn.commit()
                    flash("🗑️ Kredit berhasil dihapus dan stok telah dikembalikan!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menghapus: {e}")
        else:
            st.info("Belum ada data kredit.")



# ==================== 6. PEMBAYARAN CICILAN ====================
elif pilihan == "💰 Pembayaran Cicilan":
    st.markdown('<div class="main-header"><h1>💰 Pembayaran Cicilan</h1></div>', unsafe_allow_html=True)
    df_kredit = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.sisa_hutang, k.cicilan_bulan, k.jatuh_tempo, k.tenor
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan' ORDER BY k.jatuh_tempo ASC
    """, conn)

    if df_kredit.empty:
        st.success("✅ Tidak ada kredit aktif")
    else:
        df_kredit['label'] = df_kredit.apply(lambda r: f"#{r['id']} - {r['customer']} - {r['produk']} (Sisa: {format_rp(r['sisa_hutang'])})", axis=1)
        opsi = dict(zip(df_kredit['label'], df_kredit['id']))
        pilih = st.selectbox("🔍 Pilih Akun Kredit", list(opsi.keys()))
        kredit_id = opsi[pilih]
        detail = df_kredit[df_kredit['id'] == kredit_id].iloc[0]

        tgl_skrg = datetime.now().date()
        tgl_tempo = datetime.strptime(detail['jatuh_tempo'], "%Y-%m-%d").date()
        hari_telat = (tgl_skrg - tgl_tempo).days
        denda = hitung_denda(detail['cicilan_bulan'], hari_telat)
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 0.4)

        html = '<div class="metric-grid">'
        html += metric_card("Sisa Hutang", format_rp(detail['sisa_hutang']), "card-dark")
        html += metric_card("Cicilan / Bulan", format_rp(detail['cicilan_bulan']), "card-blue")
        html += metric_card("Jatuh Tempo", detail['jatuh_tempo'], "card-orange")
        html += metric_card("Hari Telat", f"{max(hari_telat,0)} hari", "card-pink" if hari_telat > 0 else "card-green")
        html += metric_card(f"Denda ({denda_persen:.2f}%/hari)", format_rp(denda), "card-pink")
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
            tagihan = detail['sisa_hutang'] + denda
            if jumlah_bayar <= 0:
                st.error("Jumlah bayar harus > 0")
            elif jumlah_bayar > tagihan:
                st.error(f"❌ Jumlah bayar melebihi total tagihan ({format_rp(tagihan)}).")
            else:
                principal_paid = max(jumlah_bayar - denda, 0)
                sisa_baru = max(round(detail['sisa_hutang'] - principal_paid, -2), 0)
                tgl_next = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                status_baru = "Lunas" if sisa_baru <= 0 else "Berjalan"
                try:
                    c.execute("INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan) VALUES (?,?,?,?,?)", (kredit_id, jumlah_bayar, denda, datetime.now().strftime("%Y-%m-%d"), keterangan))
                    c.execute("UPDATE kredit SET sisa_hutang=?, jatuh_tempo=?, status=? WHERE id=?", (sisa_baru, tgl_next, status_baru, kredit_id))
                    conn.commit()
                    log_aksi(st.session_state.username, "PEMBAYARAN", f"Kredit #{kredit_id}, Rp {jumlah_bayar:,.0f}")
                    if status_baru == "Lunas":
                        flash(f"🎉 LUNAS! Pembayaran {format_rp(jumlah_bayar)} berhasil. Kredit #{kredit_id} selesai.", "success")
                        st.session_state.balloons = True
                    else:
                        flash(f"✅ Pembayaran {format_rp(jumlah_bayar)} berhasil! Sisa: {format_rp(sisa_baru)}", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

        st.markdown('<div class="section-header"><h3>📜 Riwayat Pembayaran Akun Ini</h3></div>', unsafe_allow_html=True)
        df_riw = pd.read_sql_query("SELECT tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id DESC", conn, params=(kredit_id,))
        if not df_riw.empty:
            df_riw['jumlah_bayar'] = df_riw['jumlah_bayar'].apply(format_rp)
            df_riw['denda'] = df_riw['denda'].apply(format_rp)
            st.dataframe(df_riw, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pembayaran untuk akun ini")

# ==================== 7. DATA CUSTOMER (DENGAN FITUR KTP/KK) ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Pelanggan & Berkas</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Customer", "📋 Daftar & Berkas", "✏️ Edit / Hapus Customer"])

    with tab1:
        with st.form("form_cust"):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nama Lengkap")
                t = st.text_input("Telepon/WA")
                nik = st.text_input("NIK")
            with col2:
                a = st.text_area("Alamat")
                tgl_lhr = st.date_input("Tanggal Lahir", min_value=datetime(1940, 1, 1).date())
                st_kawin = st.selectbox("Status Kawin", ["Belum Kawin", "Kawin", "Cerai Hidup", "Cerai Mati"])
            
            st.markdown("**Upload Berkas Identitas (KTP & KK)**")
            col_ktp, col_kk = st.columns(2)
            with col_ktp:
                upload_ktp = st.file_uploader("Upload Foto KTP", type=["jpg", "jpeg", "png"])
            with col_kk:
                upload_kk = st.file_uploader("Upload Foto KK", type=["jpg", "jpeg", "png"])

            if st.form_submit_button("💾 Simpan Customer"):
                if n:
                    path_ktp = save_uploaded_file(upload_ktp, "KTP")
                    path_kk = save_uploaded_file(upload_kk, "KK")
                    try:
                        c.execute("INSERT INTO customer (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk) VALUES (?,?,?,?,?,?,?,?)", 
                                  (n, t, a, nik, tgl_lhr.strftime("%d-%m-%Y"), st_kawin, path_ktp, path_kk))
                        conn.commit()
                        log_aksi(st.session_state.username, "TAMBAH_CUSTOMER", n)
                        flash(f"✅ Customer {n} disimpan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal menyimpan customer: {e}")
                else:
                    st.warning("Nama wajib diisi")

    with tab2:
        df_c = pd.read_sql_query("""
            SELECT c.id, c.nama, c.telepon, c.alamat, c.nik, c.foto_ktp, c.foto_kk,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id) as total_kredit,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id AND status='Berjalan') as aktif
            FROM customer c ORDER BY c.id DESC
        """, conn)
        
        if not df_c.empty:
            st.dataframe(df_c[['nama', 'telepon', 'alamat', 'total_kredit', 'aktif']], use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-header"><h3>🔍 Lihat Berkas & Riwayat Customer</h3></div>', unsafe_allow_html=True)
            opsi = {r['nama']: r['id'] for _, r in df_c.iterrows()}
            pilih = st.selectbox("Pilih Customer", list(opsi.keys()))
            cid = opsi[pilih]
            detail_c = df_c[df_c['id'] == cid].iloc[0]
            
            with st.expander(f"Berkas Identitas: {detail_c['nama']}", expanded=True):
                st.write(f"**NIK:** {detail_c['nik']}")
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    foto_ktp_val = detail_c['foto_ktp']
                    if foto_ktp_val is not None and str(foto_ktp_val) not in ["None", ""] and os.path.exists(str(foto_ktp_val)):
                        st.image(foto_ktp_val, caption="Foto KTP", use_column_width=True)
                    else:
                        st.info("Belum ada foto KTP.")
                with col_img2:
                    foto_kk_val = detail_c['foto_kk']
                    if foto_kk_val is not None and str(foto_kk_val) not in ["None", ""] and os.path.exists(str(foto_kk_val)):
                        st.image(foto_kk_val, caption="Foto KK", use_column_width=True)
                    else:
                        st.info("Belum ada foto KK.")

            df_riw = pd.read_sql_query("""
                SELECT k.id, p.nama as produk, k.total_hutang, k.sisa_hutang, k.tenor, k.cicilan_bulan, k.jatuh_tempo, k.status
                FROM kredit k JOIN produk p ON k.produk_id = p.id WHERE k.customer_id=? ORDER BY k.id DESC
            """, conn, params=(cid,))
            if not df_riw.empty:
                st.markdown("**Riwayat Kredit:**")
                for col in ["total_hutang", "sisa_hutang", "cicilan_bulan"]:
                    df_riw[col] = df_riw[col].apply(format_rp)
                st.dataframe(df_riw, use_container_width=True, hide_index=True)
            else:
                st.info("Customer ini belum punya kredit")
        else:
            st.info("Belum ada data customer.")

    with tab3:
        st.markdown("### ✏️ Edit / Hapus Data Pelanggan")
        df_c_edit = pd.read_sql_query("SELECT id, nama, telepon, alamat FROM customer ORDER BY nama", conn)
        if df_c_edit.empty:
            st.info("Belum ada data customer.")
        else:
            opsi_c_edit = {f"{r['nama']} (ID: {r['id']})": r['id'] for _, r in df_c_edit.iterrows()}
            pilih_c_edit = st.selectbox("Pilih Customer yang akan diedit", list(opsi_c_edit.keys()), key="sel_edit_cust")
            cid_edit = opsi_c_edit[pilih_c_edit]
            
            row_c = c.execute("SELECT nama, telepon, alamat FROM customer WHERE id=?", (cid_edit,)).fetchone()
            
            with st.form("form_edit_cust"):
                new_nama = st.text_input("Nama Lengkap", value=row_c[0])
                new_telepon = st.text_input("Telepon/WA", value=row_c[1] if row_c[1] else "")
                new_alamat = st.text_area("Alamat", value=row_c[2] if row_c[2] else "")
                
                colA, colB = st.columns(2)
                with colA:
                    submit_edit_c = st.form_submit_button("💾 Update Customer")
                with colB:
                    submit_hapus_c = st.form_submit_button("🗑️ Hapus Customer")
                    
                if submit_edit_c:
                    if not new_nama:
                        st.error("Nama tidak boleh kosong!")
                    else:
                        try:
                            c.execute("UPDATE customer SET nama=?, telepon=?, alamat=? WHERE id=?", (new_nama, new_telepon, new_alamat, cid_edit))
                            conn.commit()
                            log_aksi(st.session_state.username, "EDIT_CUSTOMER", new_nama)
                            flash(f"✅ Data customer {new_nama} berhasil diupdate!", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")
                            
                if submit_hapus_c:
                    cek_kredit = c.execute("SELECT COUNT(*) FROM kredit WHERE customer_id=?", (cid_edit,)).fetchone()[0]
                    if cek_kredit > 0:
                        st.error("❌ Customer tidak bisa dihapus karena masih memiliki riwayat transaksi Kredit.")
                    else:
                        try:
                            c.execute("DELETE FROM customer WHERE id=?", (cid_edit,))
                            conn.commit()
                            log_aksi(st.session_state.username, "HAPUS_CUSTOMER", row_c[0])
                            flash(f"🗑️ Customer {row_c[0]} berhasil dihapus!", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")

# ==================== 8. SERAH TERIMA BARANG (IMEI & BUKTI) ====================
elif pilihan == "🤝 Serah Terima Barang":
    st.markdown('<div class="main-header"><h1>🤝 Berita Acara Serah Terima</h1><p>Mencegah pelanggan kabur & bukti sah</p></div>', unsafe_allow_html=True)
    
    df_kredit_aktif = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk 
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id 
        JOIN produk p ON k.produk_id = p.id 
        WHERE k.id NOT IN (SELECT kredit_id FROM serah_terima)
        ORDER BY k.id DESC
    """, conn)

    if df_kredit_aktif.empty:
        st.success("✅ Semua barang kredit telah diserahterimakan.")
    else:
        st.info("Silakan isi data serah terima untuk akun kredit di bawah ini.")
        with st.form("form_serah_terima"):
            opsi_kredit = {f"#{r['id']} - {r['customer']} - {r['produk']}": r['id'] for _, r in df_kredit_aktif.iterrows()}
            pilih_kredit = st.selectbox("Pilih Akun Kredit", list(opsi_kredit.keys()))
            kredit_id = opsi_kredit[pilih_kredit]
            
            col1, col2 = st.columns(2)
            with col1:
                imei = st.text_input("Nomor IMEI Perangkat (Wajib)", placeholder="Contoh: 356789012345678")
                penerima = st.text_input("Nama Lengkap Penerima (Wajib)")
            with col2:
                foto_bukti = st.file_uploader("Upload Foto Bukti Terima / Paket (Wajib)", type=["jpg", "jpeg", "png"])
                tgl_serah = st.date_input("Tanggal Serah Terima")
                
            if st.form_submit_button("✅ Konfirmasi Serah Terima"):
                if not imei or not penerima or not foto_bukti:
                    st.error("❌ IMEI, Nama Penerima, dan Foto Bukti wajib diisi!")
                else:
                    path_bukti = save_uploaded_file(foto_bukti, "BUKTI_TERIMA")
                    try:
                        c.execute("""INSERT INTO serah_terima (kredit_id, imei, foto_bukti, tanggal_serah, penerima) 
                                     VALUES (?, ?, ?, ?, ?)""",
                                  (kredit_id, imei, path_bukti, tgl_serah.strftime("%Y-%m-%d"), penerima))
                        conn.commit()
                        log_aksi(st.session_state.username, "SERAH_TERIMA", f"Kredit ID {kredit_id}, IMEI {imei}")
                        flash("🎉 Serah terima berhasil dicatat! Bukti sah telah disimpan.", "success")
                        st.session_state.balloons = True
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📜 Riwayat Serah Terima</h3></div>', unsafe_allow_html=True)
    df_riwayat = pd.read_sql_query("""
        SELECT s.tanggal_serah, c.nama as customer, s.imei, s.penerima, s.foto_bukti
        FROM serah_terima s
        JOIN kredit k ON s.kredit_id = k.id
        JOIN customer c ON k.customer_id = c.id
        ORDER BY s.id DESC
    """, conn)
    
    if not df_riwayat.empty:
        for _, r in df_riwayat.iterrows():
            with st.expander(f"📅 {r['tanggal_serah']} - {r['customer']} (IMEI: {r['imei']})"):
                st.write(f"**Penerima:** {r['penerima']}")
                foto_bukti_val = r['foto_bukti']
                if foto_bukti_val is not None and str(foto_bukti_val) not in ["None", ""] and os.path.exists(str(foto_bukti_val)):
                    st.image(foto_bukti_val, caption="Bukti Serah Terima", width=400)
    else:
        st.info("Belum ada riwayat serah terima.")


# ==================== 9. STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Daftar Stok", "✏️ Edit Harga Jual Pakaian"])

    with tab1:
        df_p = pd.read_sql_query("""
            SELECT p.*, 
                   ((SELECT COUNT(*) FROM kredit k WHERE k.produk_id = p.id) + 
                    (SELECT COALESCE(SUM(jumlah), 0) FROM transaksi_cash t WHERE t.produk_id = p.id)) as terjual 
            FROM produk p ORDER BY stok ASC
        """, conn)
        
        total_item   = len(df_p)
        total_unit   = df_p['stok'].sum() if not df_p.empty else 0
        total_terjual = df_p['terjual'].sum() if not df_p.empty else 0

        html = '<div class="metric-grid">'
        html += metric_card("📦 Total Item", f"{total_item} jenis", "card-blue")
        html += metric_card("🎒 Total Unit Stok", f"{total_unit} unit", "card-green")
        html += metric_card("🛍️ Total Terjual", f"{total_terjual} unit", "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        st.dataframe(df_p[['nama', 'kategori', 'harga_modal', 'markup_persen', 'harga_jual', 'stok', 'terjual']], use_container_width=True, hide_index=True)

    with tab2:
        df_pakaian = pd.read_sql_query(f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ({','.join(['?']*len(PAKAIAN_KATEGORI))}) AND (harga_jual IS NULL OR harga_jual <= 0)", conn, params=tuple(PAKAIAN_KATEGORI))
        if df_pakaian.empty:
            st.success("✅ Semua produk pakaian sudah memiliki harga jual!")
        else:
            st.warning(f"⚠️ Ada {len(df_pakaian)} produk pakaian yang belum diisi harga jualnya.")
            st.dataframe(df_pakaian[['nama', 'kategori', 'harga_modal']], use_container_width=True, hide_index=True)
            
            with st.form("form_edit_harga_pakaian"):
                opsi_pk = {f"{r['nama']} (ID: {r['id']})": r['id'] for _, r in df_pakaian.iterrows()}
                pilih_pk = st.selectbox("Pilih Produk Pakaian", list(opsi_pk.keys()))
                pid_pk = opsi_pk[pilih_pk]
                
                harga_jual_baru = st.number_input("Harga Jual Baru (Rp)", min_value=1000.0, step=1000.0)
                
                if st.form_submit_button("💾 Simpan Harga Jual"):
                    try:
                        c.execute("UPDATE produk SET harga_jual=? WHERE id=?", (harga_jual_baru, pid_pk))
                        conn.commit()
                        flash("✅ Harga jual pakaian berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
# ==================== 5B. IMPORT DOKUMEN (PDF / WORD / FOTO) ====================
elif pilihan == "📥 Import Dokumen (PDF/Word/Foto)":
    st.markdown('<div class="main-header"><h1>📥 Import Dokumen Lama</h1><p>Migrasi data dari PDF / Word / Foto ke sistem</p></div>', unsafe_allow_html=True)

    # ============== HELPER: EKSTRAKSI ==============
    def parse_rupiah(s):
        if not s: return 0.0
        digits = re.sub(r"[^\d]", "", str(s))
        return float(digits) if digits else 0.0

    def extract_field(text, patterns):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip()
        return ""

    def auto_extract_fields(text):
        hasil = {}
        # NIK
        hasil["nik"] = extract_field(text, [
            r"NIK[:\s]+(\d{16})",
            r"NIK[:\s]+([\d\.\s]{16,20})",
            r"N\.I\.K[:\s]+(\d{16})",
        ]).replace(" ", "").replace(".", "")

        # Nama
        hasil["nama"] = extract_field(text, [
            r"Nama(?:\s+Lengkap)?[:\s]+([A-Z][A-Za-z\s\.\']+?)(?=\n|Telepon|Alamat|NIK|HP|WA|$)",
            r"PIHAK KEDUA[^:]*:\s*([A-Z][A-Za-z\s\.\']+?)(?=,)",
        ])

        # Telepon
        hasil["telepon"] = extract_field(text, [
            r"(?:Telepon|Telp|HP|WA|Phone|No\.?\s*HP)[:\s\/]+([\+0-9\-\s\(\)]{9,20})",
        ])

        # Alamat
        hasil["alamat"] = extract_field(text, [
            r"Alamat[:\s]+(.+?)(?=\n|Telepon|NIK|HP|$)",
            r"bertempat tinggal di\s+(.+?),\s*Telp",
        ])

        # Tanggal lahir
        hasil["tanggal_lahir"] = extract_field(text, [
            r"lahir di\s+([A-Za-z\s]+,\s*\d{1,2}[\s\-][A-Za-z0-9\s\-]+)",
            r"Tanggal Lahir[:\s]+(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{2,4})",
            r"TTL[:\s]+([^\n]+)",
        ])

        # Status kawin
        sw = extract_field(text, [r"Status(?:\s+Perkawinan|\s+Kawin)?[:\s]+(Belum Kawin|Kawin|Menikah|Cerai Hidup|Cerai Mati)"])
        if sw.lower() in ["menikah", "kawin"]: hasil["status_kawin"] = "Kawin"
        elif sw.lower() == "belum kawin": hasil["status_kawin"] = "Belum Kawin"
        elif sw.lower() == "cerai hidup": hasil["status_kawin"] = "Cerai Hidup"
        elif sw.lower() == "cerai mati": hasil["status_kawin"] = "Cerai Mati"
        else: hasil["status_kawin"] = ""

        # Harga cash
        hasil["harga_cash"] = parse_rupiah(extract_field(text, [
            r"Harga\s+Cash[:\s]+Rp[\s\.]*([\d\.,]{5,})",
            r"Harga\s+Jual[:\s]+Rp[\s\.]*([\d\.,]{5,})",
            r"Harga[:\s]+Rp[\s\.]*([\d\.,]{5,})",
        ]))

        # DP
        hasil["dp"] = parse_rupiah(extract_field(text, [
            r"\bDP\b[:\s]+Rp[\s\.]*([\d\.,]{5,})",
            r"Uang\s+Muka[:\s]+Rp[\s\.]*([\d\.,]{5,})",
        ]))

        # Pokok
        hasil["pokok"] = parse_rupiah(extract_field(text, [
            r"Pokok(?:\s+Hutang)?[:\s]+Rp[\s\.]*([\d\.,]{5,})",
        ]))

        # Total hutang
        hasil["total_hutang"] = parse_rupiah(extract_field(text, [
            r"Total\s+Hutang[:\s]+Rp[\s\.]*([\d\.,]{5,})",
            r"Total\s+Kewajiban[:\s]+Rp[\s\.]*([\d\.,]{5,})",
        ]))

        # Tenor
        tenor_str = extract_field(text, [
            r"Tenor[:\s]+(\d+)\s*(?:bulan|bln|×|x)",
            r"Jangka\s+waktu[^0-9]*(\d+)\s*\(?\s*bulan",
        ])
        hasil["tenor"] = int(tenor_str) if tenor_str.isdigit() else 0

        # Cicilan
        hasil["cicilan"] = parse_rupiah(extract_field(text, [
            r"Cicilan(?:\s*\/\s*Bulan)?[:\s]+Rp[\s\.]*([\d\.,]{5,})",
            r"Angsuran(?:\s*\/\s*bulan)?[:\s]+Rp[\s\.]*([\d\.,]{5,})",
        ]))

        # Bunga per bulan
        bunga_str = extract_field(text, [
            r"Bunga(?:\s+Flat)?[^0-9]*(\d+[\.,]?\d*)\s*%\s*(?:\/\s*Bulan|per\s+Bulan)",
            r"Bunga(?:\s+Flat)?\s*\/\s*6\s*Bln[^0-9]*(\d+[\.,]?\d*)\s*%",
        ])
        try:
            b = float(bunga_str.replace(",", "."))
            # Kalau nilainya > 20 kemungkinan itu per 6 bulan → bagi 6
            hasil["bunga"] = round(b / 6, 2) if b > 20 else b
        except Exception:
            hasil["bunga"] = 0.0

        return hasil

    # ============== UI UPLOAD ==============
    tab_upload, tab_manual = st.tabs(["📤 Upload & Ekstrak", "✏️ Review & Migrasi Data"])

    with tab_upload:
        st.info("""
        **Format didukung:** PDF (text-based), Word (.docx), Foto KTP/KK/Invoice (.jpg, .png)
        - 📄 **PDF**: pakai `pdfplumber` — bisa extract teks & tabel
        - 📝 **Word**: pakai `python-docx` — extract paragraf & tabel
        - 🖼️ **Foto**: pakai `pytesseract` OCR — perlu Tesseract-OCR terinstall
        """)

        col_status1, col_status2, col_status3 = st.columns(3)
        col_status1.metric("📄 PDF Support", "✅ Aktif" if PDF_AVAILABLE else "❌ pip install pdfplumber")
        col_status2.metric("📝 Word Support", "✅ Aktif" if DOCX_AVAILABLE else "❌ pip install python-docx")
        col_status3.metric("🖼️ OCR Support", "✅ Aktif" if OCR_AVAILABLE else "❌ pip install pytesseract")

        uploaded_files = st.file_uploader(
            "Pilih file (bisa multiple)",
            type=["pdf", "docx", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="upload_import"
        )

        if uploaded_files:
            all_text = ""
            progress = st.progress(0)
            for idx, f in enumerate(uploaded_files):
                progress.progress((idx + 1) / len(uploaded_files))
                ext = f.name.lower().rsplit(".", 1)[-1]
                try:
                    if ext == "pdf":
                        if not PDF_AVAILABLE:
                            st.warning(f"⚠️ {f.name}: pdfplumber tidak terinstall"); continue
                        with pdfplumber.open(f) as pdf:
                            txt = "\n".join([p.extract_text() or "" for p in pdf.pages])
                        all_text += f"\n\n=== {f.name} ===\n" + txt

                    elif ext == "docx":
                        if not DOCX_AVAILABLE:
                            st.warning(f"⚠️ {f.name}: python-docx tidak terinstall"); continue
                        doc_obj = Document(f)
                        txt = "\n".join([p.text for p in doc_obj.paragraphs])
                        for tbl in doc_obj.tables:
                            for row in tbl.rows:
                                txt += "\n" + " | ".join([cell.text for cell in row.cells])
                        all_text += f"\n\n=== {f.name} ===\n" + txt

                    elif ext in ("jpg", "jpeg", "png"):
                        if not OCR_AVAILABLE:
                            st.warning(f"⚠️ {f.name}: pytesseract tidak terinstall"); continue
                        img = PILImage.open(f)
                        try:
                            txt = pytesseract.image_to_string(img, lang="ind")
                        except Exception:
                            txt = pytesseract.image_to_string(img, lang="eng")
                        all_text += f"\n\n=== {f.name} ===\n" + txt

                except Exception as e:
                    st.warning(f"⚠️ Gagal proses {f.name}: {e}")

            progress.empty()

            st.session_state["_import_text"] = all_text
            st.success(f"✅ Ekstrak selesai — total **{len(all_text)} karakter** dari {len(uploaded_files)} file.")

            with st.expander("👁️ Preview Teks Hasil Ekstrak", expanded=False):
                st.text_area("Teks mentah:", all_text, height=280, key="preview_raw", disabled=True)

            # Tombol langsung pindah ke tab review
            if st.button("➡️ Lanjut ke Review & Migrasi Data"):
                st.info("Silakan buka tab **✏️ Review & Migrasi Data** di atas.")

    with tab_manual:
        text = st.session_state.get("_import_text", "")
        if not text:
            st.warning("⚠️ Belum ada file yang di-upload. Silakan upload di tab **📤 Upload & Ekstrak** dulu.")
        else:
            extracted = auto_extract_fields(text)

            st.markdown('<div class="section-header"><h3>👤 Data Customer (hasil ekstrak otomatis — bisa diedit)</h3></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                imp_nama     = st.text_input("Nama Lengkap *", value=extracted.get("nama", ""), key="imp_nama")
                imp_nik      = st.text_input("NIK (16 digit)", value=extracted.get("nik", ""), key="imp_nik")
                imp_telepon  = st.text_input("Telepon / WA", value=extracted.get("telepon", ""), key="imp_telepon")
            with col2:
                imp_alamat   = st.text_area("Alamat", value=extracted.get("alamat", ""), key="imp_alamat", height=80)
                imp_tgl_lhr  = st.text_input("Tanggal Lahir / TTL", value=extracted.get("tanggal_lahir", ""), key="imp_tgl_lhr")
                opsi_sk = ["Belum Kawin", "Kawin", "Cerai Hidup", "Cerai Mati"]
                imp_status_kawin = st.selectbox(
                    "Status Kawin", opsi_sk,
                    index=opsi_sk.index(extracted["status_kawin"]) if extracted.get("status_kawin") in opsi_sk else 1,
                    key="imp_status_kawin"
                )

            st.markdown('<div class="section-header"><h3>📱 Data Kredit / Barang</h3></div>', unsafe_allow_html=True)
            df_produk_imp = pd.read_sql_query("SELECT id, nama, harga_modal FROM produk ORDER BY nama", conn)
            opsi_prod_imp = {"— Pilih Produk —": None}
            for _, r in df_produk_imp.iterrows():
                opsi_prod_imp[f"{r['nama']} (ID: {r['id']})"] = r['id']
            pilih_prod_imp = st.selectbox("Produk *", list(opsi_prod_imp.keys()), key="imp_produk")

            col3, col4, col5 = st.columns(3)
            with col3:
                imp_harga_cash = st.number_input("Harga Cash (Rp)", value=float(extracted.get("harga_cash", 0)), step=10000.0, key="imp_hc")
                imp_dp         = st.number_input("DP Dibayar (Rp)", value=float(extracted.get("dp", 0)), step=10000.0, key="imp_dp")
            with col4:
                imp_pokok      = st.number_input("Pokok Hutang (Rp)", value=float(extracted.get("pokok", 0)), step=10000.0, key="imp_pokok")
                imp_total      = st.number_input("Total Hutang (Rp)", value=float(extracted.get("total_hutang", 0)), step=10000.0, key="imp_total")
            with col5:
                imp_tenor      = st.number_input("Tenor (bulan)", value=int(extracted.get("tenor", 3)) or 3, min_value=1, key="imp_tenor")
                imp_cicilan    = st.number_input("Cicilan / Bulan (Rp)", value=float(extracted.get("cicilan", 0)), step=10000.0, key="imp_cicilan")

            col6, col7 = st.columns(2)
            with col6:
                imp_bunga = st.number_input("Bunga / Bulan (%)", value=float(extracted.get("bunga", 0)), step=0.1, format="%.2f", key="imp_bunga")
            with col7:
                imp_jatuh_tempo = st.date_input("Jatuh Tempo Pertama", value=(datetime.now() + timedelta(days=30)).date(), min_value=datetime(2000, 1, 1).date(), key="imp_jt")

            st.markdown('<div class="section-header"><h3>📎 Lampiran Foto (opsional)</h3></div>', unsafe_allow_html=True)
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                imp_foto_ktp = st.file_uploader("Foto KTP", type=["jpg", "jpeg", "png"], key="imp_ktp")
            with col_f2:
                imp_foto_kk = st.file_uploader("Foto KK", type=["jpg", "jpeg", "png"], key="imp_kk")

            st.markdown('<div class="section-header"><h3>🚀 Migrasi ke Database</h3></div>', unsafe_allow_html=True)

            mode_simpan = st.radio(
                "Mode penyimpanan",
                ["Buat customer baru + kredit baru", "Gunakan customer yang sudah ada (pilih di bawah)"],
                horizontal=True, key="mode_simpan"
            )

            existing_cust_id = None
            if mode_simpan.startswith("Gunakan"):
                df_cust_imp = pd.read_sql_query("SELECT id, nama FROM customer ORDER BY nama", conn)
                if not df_cust_imp.empty:
                    opsi_exist = {f"{r['nama']} (ID: {r['id']})": r['id'] for _, r in df_cust_imp.iterrows()}
                    pilih_exist = st.selectbox("Pilih Customer Existing", list(opsi_exist.keys()), key="imp_exist_cust")
                    existing_cust_id = opsi_exist[pilih_exist]
                else:
                    st.warning("Belum ada customer. Pakai mode **Buat customer baru**.")

            if st.button("💾 MIGRASI KE DATABASE", type="primary"):
                # Validasi
                errors = []
                if mode_simpan.startswith("Buat") and not imp_nama.strip():
                    errors.append("Nama customer wajib diisi")
                if not opsi_prod_imp[pilih_prod_imp]:
                    errors.append("Produk wajib dipilih")
                if imp_total <= 0:
                    errors.append("Total hutang harus > 0")
                if imp_tenor <= 0:
                    errors.append("Tenor harus >= 1")
                if mode_simpan.startswith("Gunakan") and existing_cust_id is None:
                    errors.append("Pilih customer existing")

                if errors:
                    for e in errors: st.error(f"❌ {e}")
                else:
                    try:
                        # === 1. Simpan / dapatkan customer_id ===
                        if mode_simpan.startswith("Buat"):
                            # Cek duplikat NIK
                            if imp_nik and len(imp_nik) == 16:
                                dup = c.execute("SELECT id FROM customer WHERE nik=?", (imp_nik,)).fetchone()
                                if dup:
                                    st.warning(f"⚠️ NIK sudah terdaftar di customer ID #{dup[0]}. Menggunakan customer yang ada.")
                                    customer_id = dup[0]
                                else:
                                    path_ktp = save_uploaded_file(imp_foto_ktp, "KTP") if imp_foto_ktp else None
                                    path_kk  = save_uploaded_file(imp_foto_kk, "KK")  if imp_foto_kk  else None
                                    c.execute("""INSERT INTO customer
                                        (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                        (imp_nama, imp_telepon, imp_alamat, imp_nik, imp_tgl_lhr, imp_status_kawin, path_ktp, path_kk))
                                    customer_id = c.lastrowid
                            else:
                                path_ktp = save_uploaded_file(imp_foto_ktp, "KTP") if imp_foto_ktp else None
                                path_kk  = save_uploaded_file(imp_foto_kk, "KK")  if imp_foto_kk  else None
                                c.execute("""INSERT INTO customer
                                    (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk)
                                    VALUES (?,?,?,?,?,?,?,?)""",
                                    (imp_nama, imp_telepon, imp_alamat, imp_nik, imp_tgl_lhr, imp_status_kawin, path_ktp, path_kk))
                                customer_id = c.lastrowid
                        else:
                            customer_id = existing_cust_id
                            # Update customer dengan data terbaru kalau ada yang kosong
                            c.execute("""UPDATE customer SET
                                            telepon = COALESCE(NULLIF(?, ''), telepon),
                                            alamat  = COALESCE(NULLIF(?, ''), alamat),
                                            nik     = COALESCE(NULLIF(?, ''), nik)
                                        WHERE id=?""",
                                        (imp_telepon, imp_alamat, imp_nik, customer_id))

                        # === 2. Simpan kredit ===
                        produk_id_imp = opsi_prod_imp[pilih_prod_imp]
                        tgl_kredit = datetime.now().strftime("%Y-%m-%d")
                        c.execute("""INSERT INTO kredit
                            (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor,
                             cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit, updated_at, updated_by)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (customer_id, produk_id_imp, imp_harga_cash, imp_dp, imp_pokok, imp_total,
                             imp_tenor, imp_cicilan, imp_total, imp_jatuh_tempo.strftime("%Y-%m-%d"),
                             "Berjalan", tgl_kredit, get_current_time(), st.session_state.username))
                        kredit_id_baru = c.lastrowid

                        # === 3. Kurangi stok 1 unit ===
                        c.execute("UPDATE produk SET stok = stok - 1 WHERE id=?", (produk_id_imp,))

                        conn.commit()
                        log_aksi(st.session_state.username, "IMPORT_DOKUMEN",
                                 f"Customer ID {customer_id}, Kredit ID {kredit_id_baru}")

                        st.session_state.pop("_import_text", None)
                        st.session_state.balloons = True
                        flash(
                            f"✅ **MIGRASI BERHASIL!** "
                            f"Customer ID #{customer_id} & Kredit ID #{kredit_id_baru} telah tersimpan. "
                            f"Silakan buka menu **🖨️ Cetak Slip Kredit** untuk melihat & mencetak dokumen resminya.",
                            "success"
                        )
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal migrasi: {e}")

            # ============== RIWAYAT IMPORT ==============
            st.markdown('<div class="section-header"><h3>📜 Riwayat Import Terakhir</h3></div>', unsafe_allow_html=True)
            df_hist = pd.read_sql_query("""
                SELECT k.id, c.nama AS customer, p.nama AS produk, k.total_hutang, k.tanggal_kredit, k.status
                FROM kredit k
                JOIN customer c ON k.customer_id = c.id
                JOIN produk p ON k.produk_id = p.id
                WHERE k.updated_by = ?
                ORDER BY k.id DESC LIMIT 10
            """, conn, params=(st.session_state.username,))
            if not df_hist.empty:
                df_hist['total_hutang'] = df_hist['total_hutang'].apply(format_rp)
                df_hist = df_hist.rename(columns={'id':'ID','customer':'Customer','produk':'Produk',
                                                  'total_hutang':'Total','tanggal_kredit':'Tanggal','status':'Status'})
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada riwayat import oleh Anda.")
# ==================== 10. CETAK SLIP KREDIT (FULL HTML) ====================
# ==================== 10. CETAK SLIP KREDIT (PDF 1 & PDF 2 IDENTIK) ====================
# ==================== 10. CETAK SLIP KREDIT (PDF 1 & PDF 2 IDENTIK) ====================
# ==================== 10. CETAK SLIP KREDIT (PDF 1 & PDF 2 IDENTIK) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit & Perjanjian</h1><p>Dokumen cetak profesional - PDF 1 & PDF 2 satu template</p></div>', unsafe_allow_html=True)

    df_k = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.status, k.total_hutang, k.sisa_hutang, k.tanggal_kredit
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id 
        JOIN produk p ON k.produk_id = p.id
        ORDER BY k.id DESC
    """, conn)

    if df_k.empty:
        st.info("Belum ada transaksi kredit.")
        st.stop()

    df_k['label'] = df_k.apply(lambda r: f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})", axis=1)
    opsi = dict(zip(df_k['label'], df_k['id']))
    pilih = st.selectbox("🔍 Pilih Transaksi Kredit", list(opsi.keys()))
    kid = opsi[pilih]

    d = pd.read_sql_query("""
        SELECT k.*, c.nama as cn, c.telepon, c.alamat, c.nik, c.tanggal_lahir, c.status_kawin, p.nama as pn
        FROM kredit k 
        LEFT JOIN customer c ON k.customer_id = c.id 
        LEFT JOIN produk p ON k.produk_id = p.id 
        WHERE k.id=?
    """, conn, params=(kid,)).iloc[0].fillna('-')

    nik_cust        = d['nik'] if d['nik'] != '-' else '.........................'
    tgl_lahir_cust  = d['tanggal_lahir'] if d['tanggal_lahir'] != '-' else '.........................'
    status_kawin_cust = d['status_kawin'] if d['status_kawin'] != '-' else '.........................'

    st.markdown('<div class="section-header"><h3>✏️ Edit Manual Data Akad & Jadwal</h3></div>', unsafe_allow_html=True)
    with st.expander("Buka Form Edit Manual", expanded=False):
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            m_harga_cash = st.number_input("Harga Cash (Rp)", value=float(d['harga_cash']), step=10000.0)
            m_dp         = st.number_input("DP Dibayar (Rp)", value=float(d['dp']), step=10000.0)
            m_pokok      = st.number_input("Pokok Hutang (Rp)", value=float(d['pokok_hutang']), step=10000.0)
        with col_e2:
            m_total_hutang = st.number_input("Total Hutang (Rp) (Disembunyikan)", value=float(d['total_hutang']), step=10000.0)
            m_cicilan      = st.number_input("Cicilan / Bulan (Rp)", value=float(d['cicilan_bulan']), step=10000.0)
            m_tenor        = st.number_input("Tenor (Bulan)", value=int(d['tenor']), step=1, min_value=1)
        with col_e3:
            # Form input Tanggal Cetak yang bisa diedit
            m_tgl_cetak = st.date_input("Tanggal Cetak Invoice & Perjanjian", value=datetime.now().date(), help="Tanggal 'Pada hari ini' di Perjanjian dan Header Invoice")
            m_tempo     = st.date_input("Jatuh Tempo Awal", value=pd.to_datetime(d['jatuh_tempo']).date())
            m_status    = st.selectbox("Status", ["Berjalan", "Lunas", "Batal"], index=["Berjalan", "Lunas", "Batal"].index(d['status']) if d['status'] in ["Berjalan", "Lunas", "Batal"] else 0)
            m_metode    = st.radio("Metode", ["Tunai (Cash)", "Transfer Bank", "Kredit Angsuran"], index=2, horizontal=True)

        if st.button("💾 Simpan Perubahan Ini ke Database"):
            try:
                c.execute("""UPDATE kredit SET harga_cash=?, dp=?, pokok_hutang=?, total_hutang=?, cicilan_bulan=?, tenor=?, jatuh_tempo=?, status=?, updated_at=?, updated_by=? WHERE id=?""",
                          (m_harga_cash, m_dp, m_pokok, m_total_hutang, m_cicilan, m_tenor, m_tempo.strftime("%Y-%m-%d"), m_status, get_current_time(), st.session_state.username, kid))
                recalculate_kredit(kid)
                conn.commit()
                log_aksi(st.session_state.username, "EDIT_AKAD_KREDIT", f"ID {kid}")
                flash("✅ Perubahan tersimpan!", "success")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Gagal: {e}")

    df_bayar = pd.read_sql_query("SELECT id, tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id", conn, params=(kid,))
    tanggal_kredit_str = d['tanggal_kredit'] if pd.notna(d['tanggal_kredit']) else (datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")

    tenor_asli   = int(m_tenor)
    rate_bulan   = m_bunga_bln / 100 if 'm_bunga_bln' in locals() else (get_pengaturan_float("bunga_flat_6bln_persen", 40.0) / 6 / 100)
    paid_count   = len(df_bayar)
    biaya_materai = 10000
    cicilan_terakhir = m_cicilan + biaya_materai

    # Translate Month for Indonesian
    bulan_indo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    tgl_cetak_str = f"{m_tgl_cetak.day} {bulan_indo[m_tgl_cetak.month-1]} {m_tgl_cetak.year}"

    # ====== BANGUN JADWAL DEFAULT ======
    total_1 = m_total_hutang
    default_sched = build_jadwal_angsuran(total_1, m_cicilan, tenor_asli, tanggal_kredit_str)

    # ====== FORM EDIT TANGGAL JATUH TEMPO PER BULAN ======
    st.markdown('<div class="section-header"><h3>📅 Edit Tanggal Jatuh Tempo (Tabel)</h3></div>', unsafe_allow_html=True)
    st.info("Ubah tanggal di bawah ini jika ada penyesuaian khusus dengan pelanggan sebelum dicetak.")
    
    edited_dates = []
    cols_date = st.columns(3)
    for i in range(tenor_asli):
        with cols_date[i % 3]:
            try:
                def_date = datetime.strptime(default_sched[i]['jatuh_tempo'], "%d-%m-%Y").date()
            except:
                def_date = datetime.now().date()
            
            # Input tanggal per bulan
            new_date = st.date_input(f"Bulan ke-{i+1}", value=def_date, key=f"edit_due_{kid}_{i}")
            edited_dates.append(new_date)

    # Apply edits to schedule
    sched_1 = default_sched
    for i, r in enumerate(sched_1):
        if i < len(edited_dates):
            r['jatuh_tempo'] = edited_dates[i].strftime("%d-%m-%Y")

    rows_1 = "".join([
        f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td>"
        f"<td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td>"
        f"<td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>"
        f"{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>"
        for r in sched_1
    ])

    # ====== CSS BERSAMA ======
    shared_css = """
    :root { --primary:#1e3a8a; --primary-light:#eff6ff; --accent:#d97706; --accent-light:#fffbeb; --success:#059669; --success-light:#ecfdf5; --danger:#dc2626; --danger-light:#fef2f2; --text-main:#1f2937; --text-muted:#6b7280; --border:#e5e7eb; }
    * { box-sizing:border-box; margin:0; padding:0; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    body { font-family:'Inter','Segoe UI',Helvetica,Arial,sans-serif; background:#f3f4f6; padding:20px 10px; color:var(--text-main); font-size:12px; line-height:1.5; }
    .page { max-width:820px; margin:0 auto 30px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 10px 25px -5px rgba(0,0,0,0.1); }
    .btn-print-wrap { position:sticky; top:0; z-index:9999; background:rgba(243,244,246,0.95); padding:12px 0; text-align:center; border-bottom:1px solid var(--border); margin-bottom:20px; }
    .btn-print { background:linear-gradient(135deg,#2563eb,#1e40af); color:white; border:none; padding:10px 24px; font-size:14px; border-radius:50px; cursor:pointer; font-weight:600; width:100%; max-width:350px; box-shadow:0 4px 12px rgba(37,99,235,0.3); }
    .hdr { background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%); color:#fff; padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; position:relative; overflow:hidden; }
    .brand { position:relative; z-index:1; max-width:70%; }
    .brand h1 { font-size:22px; font-weight:800; letter-spacing:0.5px; margin-bottom:4px; }
    .brand .tag { font-size:11px; color:#93c5fd; font-weight:500; letter-spacing:0.5px; margin-bottom:8px; }
    .brand .addr { font-size:10px; color:#cbd5e1; line-height:1.5; }
    .title-box { text-align:right; position:relative; z-index:1; margin-top:5px; }
    .badge-inv { display:inline-block; background:rgba(217,119,6,0.2); color:#fcd34d; padding:4px 12px; border-radius:6px; font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; border:1px solid rgba(217,119,6,0.4); margin-bottom:8px; }
    .inv-no { font-size:15px; font-weight:700; font-family:monospace; letter-spacing:1px; }
    .inv-date { font-size:11px; color:#94a3b8; margin-top:4px; }
    .meta { display:flex; gap:20px; justify-content:space-between; padding:12px 24px; background:#f8fafc; border-bottom:1px solid var(--border); font-size:11px; color:var(--text-muted); flex-wrap:wrap; }
    .meta b { color:var(--text-main); }
    .body { padding:20px 24px; }
    .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
    .card { border:1px solid var(--border); border-radius:8px; padding:12px 16px; background:#fff; }
    .card-title { font-size:10.5px; font-weight:700; color:var(--primary); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; }
    .kv-row { display:flex; margin-bottom:6px; font-size:11px; }
    .kv-row:last-child { margin-bottom:0; }
    .kv-row .k { width:65px; color:var(--text-muted); }
    .kv-row .v { flex:1; font-weight:600; color:var(--text-main); }
    .summary-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; }
    .sum-card { border-radius:8px; padding:12px 16px; border:1px solid; }
    .sum-card .lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:4px; }
    .sum-card .val { font-size:18px; font-weight:800; }
    .sum-card.green { background:var(--success-light); border-color:#a7f3d0; color:var(--success); }
    .sum-card.amber { background:var(--accent-light); border-color:#fde68a; color:var(--accent); }
    .tenor-options { display:grid; grid-template-columns:1fr; gap:12px; margin-bottom:16px; }
    .tenor-card { border:1.5px solid var(--border); border-radius:8px; padding:12px 16px; background:#fff; }
    .tenor-card.recommended { border-color:var(--primary); background:var(--primary-light); }
    .tc-label { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted); margin-bottom:4px; }
    .tc-title { font-size:13px; font-weight:700; margin-bottom:8px; color:var(--text-main); }
    .tc-row { display:flex; justify-content:space-between; font-size:11px; padding:3px 0; }
    .tc-row.main { border-top:1px dashed var(--border); margin-top:6px; padding-top:6px; font-weight:700; color:var(--primary); }
    .sched-wrap { display:grid; gap:16px; margin-bottom:16px; }
    .sched { border:1px solid var(--border); border-radius:8px; overflow:hidden; }
    .sched-h { background:var(--primary); color:#fff; padding:8px 12px; font-size:11px; font-weight:700; letter-spacing:0.5px; }
    table { width:100%; border-collapse:collapse; font-size:10.5px; }
    th { background:#f8fafc; padding:6px 8px; text-align:left; font-weight:700; color:var(--text-muted); font-size:10px; border-bottom:1px solid var(--border); }
    td { padding:6px 8px; border-bottom:1px solid #f1f5f9; }
    .r { text-align:right; } .c { text-align:center; }
    .status-lunas { background:#d1fae5; color:#065f46; padding:2px 6px; border-radius:4px; font-size:9px; font-weight:700; }
    .status-pending { background:#fef3c7; color:#92400e; padding:2px 6px; border-radius:4px; font-size:9px; font-weight:700; }
    .note-text { font-size:10.5px; color:var(--text-muted); padding:10px 12px; background:#f9fafb; border-left:3px solid var(--accent); border-radius:4px; margin-bottom:16px; line-height:1.6; }
    .bank-box { border:1px dashed var(--primary); background:var(--primary-light); padding:12px 16px; border-radius:8px; margin-bottom:16px; }
    .bank-box .title { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--primary); margin-bottom:4px; }
    .bank-box .acc { font-size:15px; font-weight:800; font-family:monospace; color:var(--primary); }
    .bank-box .name { font-size:11px; color:var(--text-muted); }
    .info-box { background:var(--danger-light); border:1px solid #fecaca; border-radius:8px; padding:12px 16px; font-size:10.5px; color:#7f1d1d; line-height:1.6; }
    .agreement-container { padding:4px 0; }
    .doc-title { text-align:center; border-bottom:2px solid var(--primary); padding-bottom:12px; margin-bottom:16px; }
    .doc-title h2 { font-size:15px; font-weight:800; color:var(--primary); letter-spacing:1px; margin-bottom:4px; }
    .doc-number { font-size:11px; color:var(--text-muted); font-family:monospace; }
    .pasal-title { background:var(--primary-light); color:var(--primary); padding:8px 14px; border-radius:6px; font-size:11px; font-weight:800; text-align:center; margin:16px 0 10px 0; letter-spacing:1px; text-transform:uppercase; border-left:4px solid var(--primary); }
    .pasal-list { padding-left:20px; font-size:11px; line-height:1.7; }
    .pasal-list li { margin-bottom:6px; }
    .agreement-container p { font-size:11px; line-height:1.7; margin-bottom:8px; text-align:justify; }
    .signature-area { display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-top:32px; padding-top:24px; border-top:1px dashed var(--border); }
    .sig-box { text-align:center; }
    .sig-title { font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted); margin-bottom:10px; }
    .sig-name { font-size:12px; font-weight:800; color:var(--text-main); margin-top:14px; }
    .sig-role { font-size:10px; color:var(--text-muted); margin-top:2px; }
    .cert-sig-box { border:1.5px solid var(--success); background:var(--success-light); border-radius:8px; padding:10px; margin:12px 0; }
    .cert-sig-header { font-size:8.5px; font-weight:800; color:var(--success); letter-spacing:1px; margin-bottom:6px; display:flex; align-items:center; justify-content:center; gap:4px; }
    .cert-sig-name { font-size:11px; font-weight:800; color:var(--text-main); margin-bottom:4px; }
    .cert-sig-text { font-size:8.5px; color:var(--text-muted); line-height:1.4; }
    .cert-sig-barcode { margin-top:8px; display:flex; justify-content:center; }
    .ematerai-box { border:2px dashed var(--accent); background:var(--accent-light); border-radius:8px; padding:24px 10px; margin:12px 0; font-size:10px; color:var(--accent); font-weight:700; letter-spacing:0.5px; }
    .ematerai-box::before { content:'🔖'; display:block; font-size:20px; margin-bottom:6px; }
    .footer { background:#f8fafc; padding:12px 24px; text-align:center; font-size:9.5px; color:var(--text-muted); border-top:1px solid var(--border); }
    @media print { body { background:#fff; padding:0; } .page { box-shadow:none; border-radius:0; margin:0; } .btn-print-wrap { display:none; } .page + .page { page-break-before:always; } }
    """

    # ====== HALAMAN 1: INVOICE (PDF 1) ======
    html_page1 = f"""
    <div class="page">
        <header class="hdr">
            <div class="brand">
                <h1>GRACE'S ELECTRONIC</h1>
                <div class="tag">CASH &amp; CREDIT - AUTHORIZED RETAILER</div>
                <div class="addr">{ALAMAT_TOKO}<br>HP/WA: 0822-9954-8411</div>
            </div>
            <div class="title-box">
                <div class="badge-inv">Invoice Kredit</div>
                <div class="inv-no">#GRC-INV-{kid}</div>
                <div class="inv-date">{tgl_cetak_str}</div>
            </div>
        </header>
        <div class="meta">
            <div>Status: <b style="color:var(--success);">● {m_status.upper()}</b></div>
            <div>Metode: <b>{m_metode}</b></div>
        </div>
        <div class="body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title">👤 Penerima / Customer</div>
                    <div class="kv-row"><div class="k">Nama</div><div class="v">{d['cn']}</div></div>
                    <div class="kv-row"><div class="k">Telepon</div><div class="v">{d['telepon']}</div></div>
                    <div class="kv-row"><div class="k">Alamat</div><div class="v" style="font-weight:400;font-size:10.5px;">{d['alamat']}</div></div>
                </div>
                <div class="card">
                    <div class="card-title">📱 Detail Produk</div>
                    <div class="kv-row"><div class="k">Deskripsi</div><div class="v">{d['pn']}</div></div>
                    <div class="kv-row"><div class="k">SKU</div><div class="v">GRC-{d['produk_id']}</div></div>
                    <div class="kv-row"><div class="k">Garansi</div><div class="v">3 Bulan</div></div>
                </div>
            </div>
            <div class="summary-grid">
                <div class="sum-card green"><div class="lbl">DP Dibayar</div><div class="val">{format_rp(m_dp)}</div></div>
                <div class="sum-card amber"><div class="lbl">Angsuran / Bulan</div><div class="val">{format_rp(m_cicilan)}</div></div>
            </div>
            <div class="tenor-options">
                <div class="tenor-card recommended">
                    <div class="tc-label">Tenor Dipilih</div>
                    <div class="tc-title">Tenor {tenor_asli}× ({tenor_asli} Bulan)</div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
                </div>
            </div>
            <div class="sched-wrap">
                <div class="sched">
                    <div class="sched-h">📅 Jadwal Angsuran — Tenor {tenor_asli}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_1}</tbody>
                    </table>
                </div>
            </div>
            <div class="note-text">
                *Catatan: Terdapat Biaya Administrasi/Materai sebesar <b>Rp 10.000</b> (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir. Total yang disetor pada bulan ke-{tenor_asli} adalah <b>{format_rp(cicilan_terakhir)}</b>.
            </div>
            <div class="bank-box">
                <div class="title">Pembayaran Transfer Resmi</div>
                <div class="acc">Bank Mandiri: 148-00-2889246-4</div>
                <div class="name">a.n. CV GRACE HAVEN TRANSPORT</div>
            </div>
            <div class="info-box">
                <strong>⚠️ PENTING - KONSEKUENSI MANGKIR</strong><br>
                Jika Debitur lalai/mangkir dalam pembayaran angsuran, Kreditur berhak melaporkan Debitur ke <b>SLIK OJK</b> dan/atau <b>BI Checking</b>. Debitur dapat masuk daftar hitam (blacklist) yang menyulitkan pengajuan kredit di lembaga keuangan manapun.
            </div>
        </div>
        <footer class="footer">
            <div style="font-weight:700;color:var(--primary);margin-bottom:2px;">GRACE'S ELECTRONIC</div>
            <div>Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak.</div>
        </footer>
    </div>
    """

    # ====== HALAMAN 2: PERJANJIAN (PDF 2) - KOP SAMA DENGAN INVOICE ======
    html_page2 = f"""
    <div class="page">
        <header class="hdr">
            <div class="brand">
                <h1>GRACE'S ELECTRONIC</h1>
                <div class="tag">CASH &amp; CREDIT - AUTHORIZED RETAILER</div>
                <div class="addr">{ALAMAT_TOKO}<br>HP/WA: 0822-9954-8411</div>
            </div>
            <div class="title-box">
                <div class="badge-inv">Surat Perjanjian Kredit</div>
                <div class="inv-no">#GRC-INV-{kid}</div>
                <div class="inv-date">{tgl_cetak_str}</div>
            </div>
        </header>
        <div class="meta">
            <div>Dokumen: <b>Perjanjian Pembiayaan</b></div>
            <div>Nomor: <b>GRC-INV-{kid}/PERJ/2026</b></div>
            <div>Tenor: <b>{tenor_asli} Bulan</b></div>
        </div>
        <div class="body">
            <div class="agreement-container">
                <div class="doc-title">
                    <h2>PERJANJIAN PEMBIAYAAN KONSUMEN</h2>
                    <div class="doc-number">Nomor: GRC-INV-{kid}/PERJ/2026</div>
                </div>

                <!-- Tanggal dinamis dari form input -->
                <p>Pada hari ini, <b>{tgl_cetak_str}</b>, yang bertanda tangan di bawah ini:</p>

                <div class="card" style="margin-bottom:10px;">
                    <div class="card-title">🏢 PIHAK PERTAMA (KREDITUR)</div>
                    <p style="margin:0;"><b>CV. GRACE HAVEN TRANSPORT</b> (Grace's Electronic), berkedudukan di {ALAMAT_TOKO}. Akta Notaris Ladi Amelia P, S.H., M.Kn. Nomor 03 Tanggal 23 September 2026, NIB: 1510260022275, NPWP: 1000 0000 1152 1195. Diwakili oleh <b>ADI HARIANTO, S.E.</b> selaku Direktur.</p>
                </div>

                <div class="card" style="margin-bottom:10px;">
                    <div class="card-title">👤 PIHAK KEDUA (DEBITUR)</div>
                    <p style="margin:0;"><b>{d['cn'].upper()}</b>, lahir di {tgl_lahir_cust}, WNI, Pekerjaan Wiraswasta, Status Perkawinan <b>{status_kawin_cust}</b>, bertempat tinggal di {d['alamat']}, Telp/WA: <b>{d['telepon']}</b>. Pemegang KTP dengan NIK: <b>{nik_cust}</b>.</p>
                </div>

                <p>Kedua belah pihak sepakat mengikatkan diri dalam Perjanjian Pembiayaan Konsumen dengan ketentuan:</p>

                <div class="pasal-title">Pasal 1 — Objek Perjanjian</div>
                <p>Pihak Pertama setuju membiayai pembelian barang berupa <b>{d['pn']}</b> kepada Pihak Kedua, dan Pihak Kedua setuju membeli barang tersebut secara angsuran sesuai ketentuan dalam perjanjian ini.</p>

                <div class="pasal-title">Pasal 2 — Ketentuan Pembayaran</div>
                <ol class="pasal-list">
                    <li>Uang Muka (DP) yang telah dibayarkan Pihak Kedua sebesar <b>{format_rp(m_dp)}</b>.</li>
                    <li>Jangka waktu pembiayaan <b>{tenor_asli} (bulan)</b>, dengan angsuran bulanan <b>{format_rp(m_cicilan)}</b>.</li>
                    <!-- Tanggal jatuh tempo diambil dari tabel yang sudah diedit kasir -->
                    <li>Angsuran pertama wajib dibayar tanggal <b>{sched_1[0]['jatuh_tempo']}</b> dan selanjutnya paling lambat tanggal yang sama setiap bulan.</li>
                    <li>Pembayaran dilakukan tunai di toko atau transfer ke rekening resmi: <b>Bank Mandiri No. Rek. 148-00-2889246-4 a.n. CV GRACE HAVEN TRANSPORT</b>.</li>
                    <li>Pihak Kedua dikenakan <b>Biaya Administrasi (bea materai) Rp 10.000</b> di luar nominal angsuran, ditagih bersamaan angsuran terakhir. Total bulan ke-{tenor_asli}: <b>{format_rp(cicilan_terakhir)}</b>.</li>
                </ol>

                <div class="pasal-title">Pasal 3 — Denda dan Wanprestasi</div>
                <ol class="pasal-list">
                    <li>Keterlambatan pembayaran dikenakan denda <b>{get_pengaturan_float("denda_per_hari_persen", 1.0)}% per hari</b> dari angsuran tertunggak.</li>
                    <li>Pihak Kedua dinyatakan wanprestasi apabila gagal membayar angsuran 2 (dua) bulan berturut-turut.</li>
                    <li>Apabila Debitur mangkir, Kreditur berhak melaporkan ke <b>SLIK OJK</b> dan/atau <b>BI Checking</b> yang mengakibatkan Debitur masuk daftar hitam (blacklist).</li>
                </ol>

                <div class="pasal-title">Pasal 4 — Penyelesaian Sengketa &amp; Domisili</div>
                <ol class="pasal-list">
                    <li>Perselisihan diselesaikan secara musyawarah mufakat.</li>
                    <li>Apabila gagal, diselesaikan melalui <b>LAPS SJK</b> atau <b>Pengadilan Negeri Kutai Barat</b>.</li>
                    <li>Kreditur dilarang menarik objek pembiayaan secara paksa tanpa prosedur hukum sesuai POJK No. 22 Tahun 2023 dan Putusan MK No. 18/PUU-XVII/2019.</li>
                    <li>Para pihak memilih domisili hukum di Kantor Panitera Pengadilan Negeri Kutai Barat.</li>
                </ol>

                <div class="pasal-title">Pasal 5 — Ketentuan Penutup</div>
                <p>Perjanjian ini dibuat dengan sadar, tanpa paksaan, dan dalam keadaan sehat jasmani dan rohani. Dibuat rangkap 2 (dua), masing-masing berkekuatan hukum sama, satu untuk Pihak Pertama dan satu untuk Pihak Kedua.</p>

                <div class="signature-area">
                    <div class="sig-box">
                        <div class="sig-title">Pihak Pertama (Kreditur)</div>
                        <div class="cert-sig-box">
                            <div class="cert-sig-header">🛡️ TERSERTIFIKASI</div>
                            <div class="cert-sig-name">ADI HARIANTO, S.E.</div>
                            <div class="cert-sig-text">Ditandatangani secara elektronik<br>Menggunakan Sertifikat PSrE</div>
                        </div>
                        <div class="sig-name">ADI HARIANTO, S.E.</div>
                        <div class="sig-role">Direktur CV. Grace Haven Transport</div>
                    </div>
                    <div class="sig-box">
                        <div class="sig-title">Pihak Kedua (Debitur)</div>
                        <div class="ematerai-box">Tempel e-Meterai / TTD Basah</div>
                        <div class="sig-name">{d['cn'].upper()}</div>
                        <div class="sig-role">Pemegang KTP NIK: {nik_cust}</div>
                    </div>
                </div>
            </div>
        </div>
        <footer class="footer">
            <div style="font-weight:700;color:var(--primary);margin-bottom:2px;">GRACE'S ELECTRONIC</div>
            <div>Dokumen ini sah dan mengikat secara hukum.</div>
        </footer>
    </div>
    """

    # ====== GABUNG & RENDER ======
    full_html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="utf-8">
        <title>Invoice Kredit - GRACE'S ELECTRONIC</title>
        <style>{shared_css}</style>
    </head>
    <body>
        <div class="btn-print-wrap">
            <button class="btn-print" onclick="window.print()">🖨️ Cetak / Simpan sebagai PDF</button>
        </div>
        {html_page1}
        {html_page2}
    </body>
    </html>
    """

    components.html(full_html, height=1900, scrolling=True)

    # ====== DOWNLOAD BUTTONS ======
    st.markdown('<div class="section-header"><h3>💾 Unduh Dokumen</h3></div>', unsafe_allow_html=True)
    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        st.download_button(
            "📄 Download HTML (siap print PDF)",
            data=full_html,
            file_name=f"Invoice_Perjanjian_{kid}.html",
            mime="text/html",
            use_container_width=True
        )

    with col_dl2:
        # (Kode generate_word ke bawah biarkan sama seperti sebelumnya)
        pass 
# ==================== 11. OVERDUE & DENDA ====================
elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Overdue & Denda</h1></div>', unsafe_allow_html=True)
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    df_overdue = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, c.telepon, p.nama as produk, k.cicilan_bulan, k.jatuh_tempo, k.sisa_hutang
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ? ORDER BY k.jatuh_tempo ASC
    """, conn, params=(tgl_skrg,))
    
    if df_overdue.empty:
        st.success("✅ Tidak ada kredit yang menunggak.")
    else:
        st.warning(f"⚠️ Ada **{len(df_overdue)}** akun yang melewati jatuh tempo.")
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 0.4)
        
        for _, r in df_overdue.iterrows():
            tgl_tempo = datetime.strptime(r['jatuh_tempo'], "%Y-%m-%d").date()
            hari_telat = (datetime.now().date() - tgl_tempo).days
            denda = hitung_denda(r['cicilan_bulan'], hari_telat)
            
            with st.expander(f"#{r['id']} - {r['customer']} - {r['produk']} (Telat {hari_telat} hari)"):
                st.write(f"**Telepon:** {r['telepon']}")
                st.write(f"**Sisa Hutang:** {format_rp(r['sisa_hutang'])}")
                st.write(f"**Cicilan:** {format_rp(r['cicilan_bulan'])}")
                st.write(f"**Denda ({denda_persen}%/hari):** {format_rp(denda)}")
                st.error("Segera hubungi customer untuk penagihan!")


# ==================== 12. ALERT & REMINDER ====================
elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder</h1><p>Pusat notifikasi tagihan dan pengingat</p></div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📅 Jatuh Tempo Minggu Ini", "⏰ Jatuh Tempo Bulan Ini", "📦 Stok Kritis"])
    
    with tab1:
        tgl_skrg = datetime.now().strftime("%Y-%m-%d")
        tgl_7 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        df_dekat = pd.read_sql_query("""
            SELECT c.nama as customer, c.telepon, p.nama as produk, k.cicilan_bulan, k.jatuh_tempo, k.sisa_hutang
            FROM kredit k 
            JOIN customer c ON k.customer_id = c.id 
            JOIN produk p ON k.produk_id = p.id 
            WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ? 
            ORDER BY k.jatuh_tempo ASC
        """, conn, params=(tgl_skrg, tgl_7))
        
        if df_dekat.empty:
            st.success("✅ Tidak ada jatuh tempo dalam 7 hari ke depan.")
        else:
            st.warning(f"⚠️ Ada **{len(df_dekat)}** akun yang akan jatuh tempo minggu ini.")
            df_show = df_dekat.copy()
            df_show['cicilan_bulan'] = df_show['cicilan_bulan'].apply(format_rp)
            df_show['sisa_hutang'] = df_show['sisa_hutang'].apply(format_rp)
            st.dataframe(df_show, use_container_width=True, hide_index=True)

    with tab2:
        tgl_skrg = datetime.now().strftime("%Y-%m-%d")
        tgl_30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        df_bulan = pd.read_sql_query("""
            SELECT c.nama as customer, c.telepon, p.nama as produk, k.cicilan_bulan, k.jatuh_tempo, k.sisa_hutang
            FROM kredit k 
            JOIN customer c ON k.customer_id = c.id 
            JOIN produk p ON k.produk_id = p.id 
            WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ? 
            ORDER BY k.jatuh_tempo ASC
        """, conn, params=(tgl_skrg, tgl_30))
        
        if df_bulan.empty:
            st.success("✅ Tidak ada jatuh tempo dalam 30 hari ke depan.")
        else:
            st.info(f"ℹ️ Ada **{len(df_bulan)}** akun yang akan jatuh tempo bulan ini.")
            df_show = df_bulan.copy()
            df_show['cicilan_bulan'] = df_show['cicilan_bulan'].apply(format_rp)
            df_show['sisa_hutang'] = df_show['sisa_hutang'].apply(format_rp)
            st.dataframe(df_show, use_container_width=True, hide_index=True)

    with tab3:
        df_kritis = pd.read_sql_query("SELECT nama, kategori, stok FROM produk WHERE stok <= 3 ORDER BY stok ASC", conn)
        if df_kritis.empty:
            st.success("✅ Semua stok dalam kondisi aman (> 3 unit).")
        else:
            st.error(f"🚨 Ada **{len(df_kritis)}** produk dengan stok kritis (≤ 3 unit). Segera lakukan restock!")
            st.dataframe(df_kritis, use_container_width=True, hide_index=True)

# ==================== 13. LAPORAN & ANALITIK ====================
elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1></div>', unsafe_allow_html=True)
    st.info("Fitur ini menyajikan data visual performa toko.")
    
    tab1, tab2 = st.tabs(["📈 Ringkasan", "📑 Export Data"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Distribusi Status Kredit**")
            df_status = pd.read_sql_query("SELECT status, COUNT(*) as jumlah FROM kredit GROUP BY status", conn)
            if not df_status.empty:
                st.bar_chart(df_status.set_index('status'))
                
        with col2:
            st.markdown("**Pendapatan per Bulan (Cash + Cicilan)**")
            df_pendapatan = pd.read_sql_query("""
                SELECT substr(tanggal,1,7) as bulan, SUM(total_harga) as total_cash FROM transaksi_cash GROUP BY bulan
            """, conn)
            if not df_pendapatan.empty:
                st.line_chart(df_pendapatan.set_index('bulan'))
                
    with tab2:
        st.subheader("Export Laporan ke Excel")
        if st.button("Generate Laporan Excel"):
            try:
                df_invoice = pd.read_sql_query("SELECT * FROM kredit", conn)
                df_pelanggan = pd.read_sql_query("SELECT * FROM customer", conn)
                df_serah = pd.read_sql_query("SELECT * FROM serah_terima", conn)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_invoice.to_excel(writer, sheet_name='Data Invoice', index=False)
                    df_pelanggan.to_excel(writer, sheet_name='Data Pelanggan', index=False)
                    df_serah.to_excel(writer, sheet_name='Serah Terima', index=False)
                
                st.download_button(
                    label="⬇️ Download Laporan Lengkap (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"Laporan_GraceStore_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Gagal membuat Excel: {e}")

# ==================== 14. MODAL VS PROFIT ====================
elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Laporan Modal vs Profit Pakaian</h1></div>', unsafe_allow_html=True)
    df_pk = pd.read_sql_query("SELECT nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ('Pakaian', 'Atasan', 'Bawahan', 'Dress', 'Outerwear', 'Batik')", conn)
    
    if df_pk.empty:
        st.info("Belum ada data produk pakaian.")
    else:
        df_pk['harga_modal'] = pd.to_numeric(df_pk['harga_modal'], errors='coerce').fillna(0)
        df_pk['harga_jual'] = pd.to_numeric(df_pk['harga_jual'], errors='coerce').fillna(0)
        
        df_pk['profit'] = df_pk['harga_jual'] - df_pk['harga_modal']
        
        df_pk['harga_modal'] = df_pk['harga_modal'].apply(format_rp)
        df_pk['harga_jual'] = df_pk['harga_jual'].apply(lambda x: format_rp(x) if x > 0 else "Belum diset")
        df_pk['profit'] = df_pk['profit'].apply(lambda x: format_rp(x) if x != 0 else "-")
        
        st.dataframe(df_pk, use_container_width=True, hide_index=True)
        st.caption("Catatan: Produk dengan harga jual 'Belum diset' tidak akan bisa dijual secara kredit sampai harganya diisi di menu Stok Barang.")

# ==================== 15. BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1></div>', unsafe_allow_html=True)
    
    tab_backup, tab_excel = st.tabs(["💾 Backup Database", "📑 Cetak Laporan Excel"])
    
    with tab_backup:
        st.subheader("Backup Database Manual")
        st.warning("⚠️ **PENTING:** Simpan file `.db` ini ke tempat aman (Google Drive / Flashdisk) secara berkala untuk mencegah kehilangan data.")
        
        try:
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            
            st.download_button(
                label="💾 Download Database Terbaru (toko_kredit.db)",
                data=db_bytes,
                file_name=f"backup_toko_kredit_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                mime="application/x-sqlite3",
                use_container_width=True
            )
        except FileNotFoundError:
            st.error("❌ File database tidak ditemukan.")
            
        st.markdown("---")
        st.subheader("Backup Otomatis (Harian)")
        st.info("Sistem secara otomatis membuat backup harian di folder `backups/` setiap kali aplikasi dijalankan pada hari baru.")
        
        if os.path.exists(BACKUP_DIR):
            list_backup = sorted(os.listdir(BACKUP_DIR), reverse=True)
            if list_backup:
                st.write("**Daftar Backup Otomatis Tersedia:**")
                for b in list_backup[:5]:
                    st.write(f"- `{b}`")
            else:
                st.write("Belum ada backup otomatis.")

    with tab_excel:
        st.subheader("Cetak Laporan Lengkap ke Excel")
        st.info("Fitur ini menggunakan `xlsxwriter` untuk menghasilkan file Excel multi-sheet yang rapi.")
        
        if st.button("📊 Generate Laporan Excel", use_container_width=True):
            try:
                df_invoice = pd.read_sql_query("SELECT * FROM kredit", conn)
                if not df_invoice.empty:
                    df_invoice['total_hutang'] = pd.to_numeric(df_invoice['total_hutang'], errors='coerce').fillna(0)
                    
                df_pelanggan = pd.read_sql_query("SELECT * FROM customer", conn)
                df_serah = pd.read_sql_query("SELECT * FROM serah_terima", conn)
                df_cash = pd.read_sql_query("SELECT * FROM transaksi_cash", conn)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_invoice.to_excel(writer, sheet_name='Data Kredit', index=False)
                    df_cash.to_excel(writer, sheet_name='Data Jual Cash', index=False)
                    df_pelanggan.to_excel(writer, sheet_name='Data Pelanggan', index=False)
                    df_serah.to_excel(writer, sheet_name='Bukti Serah Terima', index=False)
                
                st.download_button(
                    label="⬇️ Download Laporan Lengkap (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"Laporan_GraceStore_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                flash("✅ Laporan Excel berhasil dibuat!", "success")
            except Exception as e:
                st.error(f"❌ Gagal membuat Excel: {e}")

# ==================== 16. MANAJEMEN USER ====================
elif pilihan == "👤 Manajemen User" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Tambah User Baru", "📋 Daftar & Edit User"])
    
    with tab1:
        with st.form("form_add_user"):
            st.subheader("Form Tambah User")
            new_user = st.text_input("Username (unik)")
            new_pass = st.text_input("Password", type="password")
            new_nama = st.text_input("Nama Lengkap")
            new_role = st.selectbox("Role", ["admin", "kasir"])
            
            if st.form_submit_button("💾 Simpan User"):
                if not new_user or not new_pass or not new_nama:
                    st.error("❌ Semua field wajib diisi!")
                else:
                    try:
                        c.execute("INSERT INTO users (username, password, nama_lengkap, role, aktif) VALUES (?,?,?,?,1)",
                                  (new_user, hash_password(new_pass), new_nama, new_role))
                        conn.commit()
                        log_aksi(st.session_state.username, "TAMBAH_USER", new_user)
                        flash(f"✅ User {new_user} berhasil ditambahkan!", "success")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Username sudah digunakan, pilih username lain.")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                        
    with tab2:
        df_users = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY id", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Edit / Nonaktifkan User")
        
        opsi_user = {f"{r['username']} ({r['nama_lengkap']})": r['id'] for _, r in df_users.iterrows()}
        pilih_user = st.selectbox("Pilih User", list(opsi_user.keys()))
        uid_edit = opsi_user[pilih_user]
        
        row_u = df_users[df_users['id'] == uid_edit].iloc[0]
        
        with st.form("form_edit_user"):
            edit_nama = st.text_input("Nama Lengkap", value=row_u['nama_lengkap'])
            edit_role = st.selectbox("Role", ["admin", "kasir"], index=0 if row_u['role'] == 'admin' else 1)
            edit_aktif = st.selectbox("Status Aktif", [1, 0], index=0 if row_u['aktif'] == 1 else 1, format_func=lambda x: "Aktif" if x == 1 else "Nonaktif")
            edit_pass = st.text_input("Password Baru (Biarkan kosong jika tidak diganti)", type="password")
            
            if st.form_submit_button("💾 Update User"):
                try:
                    if edit_pass:
                        c.execute("UPDATE users SET nama_lengkap=?, role=?, aktif=?, password=? WHERE id=?",
                                  (edit_nama, edit_role, edit_aktif, hash_password(edit_pass), uid_edit))
                    else:
                        c.execute("UPDATE users SET nama_lengkap=?, role=?, aktif=? WHERE id=?",
                                  (edit_nama, edit_role, edit_aktif, uid_edit))
                    conn.commit()
                    log_aksi(st.session_state.username, "EDIT_USER", f"ID {uid_edit}")
                    flash("✅ Data user berhasil diupdate!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

# ==================== 17. LOG AKTIVITAS ====================
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas Sistem</h1></div>', unsafe_allow_html=True)
    st.info("Catatan semua aktivitas yang dilakukan oleh pengguna di dalam sistem.")
    
    df_log = pd.read_sql_query("SELECT waktu, username, aksi, detail FROM log_aktivitas ORDER BY id DESC LIMIT 100", conn)
    
    if df_log.empty:
        st.write("Belum ada aktivitas tercatat.")
    else:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        
    if st.button("🔄 Refresh Log"):
        st.rerun()
