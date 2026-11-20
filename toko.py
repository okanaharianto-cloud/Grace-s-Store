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
import io
from PIL import Image

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

import psycopg2
from sqlalchemy import create_engine
from supabase import create_client, Client

# --- WRAPPER AGAR KODE SQLITE (?) BISA JALAN DI POSTGRES ---
class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    def execute(self, query, params=None):
        query = query.replace("?", "%s")
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
    def fetchone(self): return self.cursor.fetchone()
    def fetchall(self): return self.cursor.fetchall()
    def __getattr__(self, name): return getattr(self.cursor, name)

class SQLiteConnWrapper:
    def __init__(self, conn):
        self.conn = conn
    def cursor(self): return SQLiteCursorWrapper(self.conn.cursor())
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()

@st.cache_resource
def get_connection():
    DB_URL = st.secrets["DB_URL"]
    engine = create_engine(DB_URL)
    raw_conn = engine.raw_connection()
    return SQLiteConnWrapper(raw_conn)

conn = get_connection()
c = conn.cursor()

# --- SETUP SUPABASE STORAGE UNTUK GAMBAR ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== STRUKTUR DATABASE (DENGAN FITUR BARU) ====================
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
# TABEL BARU UNTUK FITUR SERAH TERIMA
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
    # KOLOM BARU UNTUK KTP & KK
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

# ==================== SIDEBAR (SARAN 7: RADIO) ====================
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
        "🤝 Serah Terima Barang", # MENU BARU
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

    # === FITUR SIMULASI SKEMA ===
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

    # === METRIK UTAMA DASHBOARD ===
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
    
    # CEK PENDING SERAH TERIMA
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
                
                modal_asli = c.execute("SELECT harga_modal FROM produk WHERE id=?", (detail_cash['produk_id'],)).fetchone()[0]
                
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
                            selisih_qty = new_qty_cash - detail_cash['jumlah']
                            stok_tersedia = c.execute("SELECT stok FROM produk WHERE id=?", (detail_cash['produk_id'],)).fetchone()[0]
                            
                            if selisih_qty > 0 and stok_tersedia < selisih_qty:
                                st.error(f"❌ Stok tidak mencukupi untuk menambah {selisih_qty} unit! Sisa stok: {stok_tersedia}")
                            else:
                                new_total = new_hj * new_qty_cash
                                new_profit = (new_hj - modal_asli) * new_qty_cash
                                new_kembalian = new_uang - new_total
                                
                                if new_uang < new_total:
                                    st.error("❌ Uang diterima kurang dari total belanja baru!")
                                else:
                                    c.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (selisih_qty, detail_cash['produk_id']))
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
                # ==================== 5. KREDIT BARU ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Transaksi Kredit Baru</h1></div>', unsafe_allow_html=True)

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
            dp_persen = st.number_input("DP (%)", min_value=float(dp_min_persen_default), max_value=100.0, value=float(dp_min_persen_default), step=1.0, help=f"Minimal DP dari Owner adalah {dp_min_persen_default}%")
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
                tgl_lhr = st.date_input("Tanggal Lahir")
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
if detail_c['foto_ktp']:
    st.image(detail_c['foto_ktp'], caption="Foto KTP", use_column_width=True)
if detail_c['foto_kk']:
    st.image(detail_c['foto_kk'], caption="Foto KK", use_column_width=True)
                    else:
                        st.info("Belum ada foto KTP.")
                with col_img2:
                    if detail_c['foto_kk'] and os.path.exists(detail_c['foto_kk']):
                        st.image(detail_c['foto_kk'], caption="Foto KK", use_column_width=True)
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
    
    # Hanya tampilkan kredit yang belum ada di tabel serah_terima
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
               if r['foto_bukti']:
    st.image(r['foto_bukti'], caption="Bukti Serah Terima", width=400)
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
                        # ==================== 10. CETAK SLIP KREDIT (FULL HTML) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit & Perjanjian</h1><p>Dokumen cetak profesional sesuai standar OJK</p></div>', unsafe_allow_html=True)

    df_k = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.status, k.total_hutang, k.sisa_hutang, k.tanggal_kredit
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id 
        JOIN produk p ON k.produk_id = p.id
        ORDER BY k.id DESC
    """, conn)

    if df_k.empty:
        st.info("Belum ada transaksi kredit. Buat kredit baru terlebih dahulu di menu 📤 Kredit Baru.")
    else:
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
        
        nik_cust = d['nik'] if d['nik'] != '-' else '.........................'
        tgl_lahir_cust = d['tanggal_lahir'] if d['tanggal_lahir'] != '-' else '.........................'
        status_kawin_cust = d['status_kawin'] if d['status_kawin'] != '-' else '.........................'

        st.markdown('<div class="section-header"><h3>✏️ Edit Manual Data Akad (Khusus Cetakan Ini)</h3></div>', unsafe_allow_html=True)
        with st.expander("Buka Form Edit Manual", expanded=False):
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                m_harga_cash = st.number_input("Harga Cash (Rp)", value=float(d['harga_cash']), step=10000.0)
                m_dp = st.number_input("DP Dibayar (Rp)", value=float(d['dp']), step=10000.0)
                m_pokok = st.number_input("Pokok Hutang (Rp)", value=float(d['pokok_hutang']), step=10000.0)
            with col_e2:
                m_total_hutang = st.number_input("Total Hutang (Rp)", value=float(d['total_hutang']), step=10000.0)
                m_cicilan = st.number_input("Cicilan / Bulan (Rp)", value=float(d['cicilan_bulan']), step=10000.0)
                m_tenor = st.number_input("Tenor (Bulan)", value=int(d['tenor']), step=1, min_value=1)
            with col_e3:
                m_bunga_bln = st.number_input("Bunga Flat / Bulan (%)", value=round(get_pengaturan_float("bunga_flat_6bln_persen", 40.0) / 6, 2), step=0.1, format="%.2f")
                m_tempo = st.date_input("Jatuh Tempo", value=pd.to_datetime(d['jatuh_tempo']).date())
                m_status = st.selectbox("Status", ["Berjalan", "Lunas", "Batal"], index=["Berjalan", "Lunas", "Batal"].index(d['status']) if d['status'] in ["Berjalan", "Lunas", "Batal"] else 0)
                m_metode = st.radio("Metode", ["Tunai (Cash)", "Transfer Bank", "Kredit Angsuran"], index=2, horizontal=True)

            if st.button("💾 Simpan Perubahan Ini ke Database"):
                try:
                    c.execute("""UPDATE kredit SET harga_cash=?, dp=?, pokok_hutang=?, total_hutang=?, cicilan_bulan=?, tenor=?, jatuh_tempo=?, status=?, updated_at=?, updated_by=? WHERE id=?""",
                              (m_harga_cash, m_dp, m_pokok, m_total_hutang, m_cicilan, m_tenor, m_tempo.strftime("%Y-%m-%d"), m_status, get_current_time(), st.session_state.username, kid))
                    recalculate_kredit(kid)
                    conn.commit()
                    log_aksi(st.session_state.username, "EDIT_AKAD_KREDIT", f"ID {kid}")
                    flash("✅ Perubahan berhasil disimpan ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

        df_bayar = pd.read_sql_query("SELECT id, tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id", conn, params=(kid,))
        tanggal_kredit_str = d['tanggal_kredit'] if pd.notna(d['tanggal_kredit']) else (datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        
        tenor_asli = int(m_tenor)
        rate_bulan = m_bunga_bln / 100
        
        tampilkan_banding = st.toggle("Tampilkan Perbandingan 2 Tenor (Opsi A & B)", value=True, help="Aktifkan untuk menampilkan 2 opsi tenor.")
        
        if tampilkan_banding:
            tenor_opsi_1 = 2
            tenor_opsi_2 = 3
            pokok_awal = float(m_pokok)
            
            total_1 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_1)), -2)
            cicilan_1 = round(total_1 / tenor_opsi_1, -2)
            
            total_2 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_2)), -2)
            cicilan_2 = round(total_2 / tenor_opsi_2, -2)
            
            paid_count = len(df_bayar)
            sched_1 = build_jadwal_angsuran(total_1, cicilan_1, tenor_opsi_1, tanggal_kredit_str)
            sched_2 = build_jadwal_angsuran(total_2, cicilan_2, tenor_opsi_2, tanggal_kredit_str)
            
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for r in sched_1])
            rows_2 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for r in sched_2])
            
            html_tenor_options = f"""
            <div class="tenor-options">
                <div class="tenor-card recommended">
                    <div class="tc-label">Opsi A (Dipilih)</div>
                    <div class="tc-title">Tenor {tenor_opsi_1}× ({tenor_opsi_1} Bulan)</div>
                    <div class="tc-row"><span class="k">Bunga total ({(rate_bulan*100)*tenor_opsi_1:.0f}%)</span><span class="v">{format_rp(total_1 - pokok_awal)}</span></div>
                    <div class="tc-row"><span class="k">Total hutang</span><span class="v">{format_rp(total_1)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_1)}</span></div>
                </div>
                <div class="tenor-card">
                    <div class="tc-label">Opsi B</div>
                    <div class="tc-title">Tenor {tenor_opsi_2}× ({tenor_opsi_2} Bulan)</div>
                    <div class="tc-row"><span class="k">Bunga total ({(rate_bulan*100)*tenor_opsi_2:.0f}%)</span><span class="v">{format_rp(total_2 - pokok_awal)}</span></div>
                    <div class="tc-row"><span class="k">Total hutang</span><span class="v">{format_rp(total_2)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_2)}</span></div>
                </div>
            </div>
            """
            html_schedule = f"""
            <div class="sched-wrap" style="grid-template-columns: 1fr 1fr;">
                <div class="sched"><div class="sched-h two">📅 Opsi A — Tenor {tenor_opsi_1}×</div>
                    <table><thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                    <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_1)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody></table>
                </div>
                <div class="sched"><div class="sched-h three">📅 Opsi B — Tenor {tenor_opsi_2}×</div>
                    <table><thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                    <tbody>{rows_2}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_2)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody></table>
                </div>
            </div>
            """
        else:
            total_1 = m_total_hutang
            paid_count = len(df_bayar)
            sched_1 = build_jadwal_angsuran(total_1, m_cicilan, tenor_asli, tanggal_kredit_str)
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for r in sched_1])
            
            html_tenor_options = f"""
            <div class="tenor-options" style="grid-template-columns: 1fr;">
                <div class="tenor-card recommended">
                    <div class="tc-label">Tenor Dipilih</div>
                    <div class="tc-title">Tenor {tenor_asli}× ({tenor_asli} Bulan)</div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
                </div>
            </div>
            """
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

        biaya_materai = 10000
        cicilan_terakhir = m_cicilan + biaya_materai
        
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
                    <td>: <b>CV. GRACE HAVEN TRANSPORT</b> (Grace's Electronic), berkedudukan di {ALAMAT_TOKO}. Berdasarkan Akta Notaris Ladi Amelia P, S.H., M.Kn. Nomor 03 Tanggal 23 September 2026, NIB: 1510260022275, NPWP: 1000 0000 1152 1195. Dalam hal ini diwakili oleh <b>ADI HARIANTO, S.E.</b> selaku Direktur.</td>
                </tr>
                <tr>
                    <td class="label"><b>PIHAK KEDUA</b></td>
                    <td>: <b>{d['cn'].upper()}</b>, lahir di {tgl_lahir_cust}, Warga Negara Indonesia, Pekerjaan Wiraswasta, Status Perkawinan <b>{status_kawin_cust}</b>, bertempat tinggal di {d['alamat']}, Telp/WA: <b>{d['telepon']}</b>. Pemegang Kartu Tanda Penduduk (KTP) dengan NIK: <b>{nik_cust}</b>.</td>
                </tr>
            </table>
            
            <p>Kedua belah pihak sepakat untuk mengikatkan diri dalam Perjanjian Pembiayaan Konsumen dengan ketentuan sebagai berikut:</p>
            
            <div class="pasal-title">PASAL 1<br>OBJEK PERJANJIAN</div>
            <p>Pihak Pertama setuju untuk membiayai pembelian barang berupa <b>{d['pn']}</b> dengan harga cash sebesar <b>{format_rp(m_harga_cash)}</b> kepada Pihak Kedua, dan Pihak Kedua setuju untuk membeli barang tersebut secara angsuran sesuai dengan ketentuan yang diatur dalam perjanjian ini.</p>
            
            <div class="pasal-title">PASAL 2<br>KETENTUAN PEMBAYARAN</div>
            <ol class="pasal-list">
                <li>Uang Muka (DP) yang telah dibayarkan oleh Pihak Kedua adalah sebesar <b>{format_rp(m_dp)}</b>.</li>
                <li>Sisa Pokok Hutang setelah DP adalah sebesar <b>{format_rp(m_pokok)}</b>.</li>
                <li>Suku bunga (flat) yang disepakati adalah <b>{m_bunga_bln}% per bulan</b> dari pokok hutang.</li>
                <li>Jangka waktu pembiayaan adalah <b>{tenor_asli} (bulan)</b>, dengan angsuran bulanan sebesar <b>{format_rp(m_cicilan)}</b>.</li>
                <li>Angsuran pertama wajib dibayarkan pada tanggal <b>{m_tempo.strftime('%d-%m-%Y')}</b> dan selanjutnya paling lambat pada tanggal yang sama setiap bulannya.</li>
                <li>Pembayaran angsuran wajib dilakukan secara tunai di toko atau melalui transfer ke rekening resmi perusahaan: <b>Bank Mandiri No. Rekening 148-00-2889246-4 a.n. CV GRACE HAVEN TRANSPORT</b>.</li>
                <li>Pihak Kedua dikenakan <b>Biaya Administrasi berupa bea materai sebesar Rp 10.000</b> yang posisinya <b>BERADA DI LUAR nominal angsuran</b>. Biaya tersebut akan ditagihkan bersamaan dengan setoran angsuran terakhir. Total pembayaran pada bulan ke-{tenor_asli} adalah sebesar <b>{format_rp(cicilan_terakhir)}</b>.</li>
            </ol>
            
            <div class="pasal-title">PASAL 3<br>DENDA DAN WANPRESTASI</div>
            <ol class="pasal-list">
                <li>Apabila Pihak Kedua terlambat membayar angsuran melewati tanggal jatuh tempo, dikenakan denda sebesar <b>{get_pengaturan_float("denda_per_hari_persen", 1.0)}% per hari</b> dari jumlah angsuran yang tertunggak.</li>
                <li>Pihak Kedua dinyatakan wanprestasi apabila gagal membayar angsuran selama 2 (dua) bulan berturut-turut.</li>
                <li>Apabila Debitur mangkir/lalai dalam pembayaran, Kreditur berhak melaporkan Debitur ke <b>Sistem Layanan Informasi Keuangan (SLIK) OJK dan/atau BI Checking</b>, yang mengakibatkan Debitur masuk dalam daftar hitam (<i>blacklist</i>) dan menyulitkan Debitur memperoleh fasilitas kredit di kemudian hari.</li>
            </ol>

            <div class="pasal-title">PASAL 4<br>PENYELESAIAN SENGKETA DAN DOMISILI</div>
            <ol class="pasal-list">
                <li>Segala perselisihan yang timbul dari perjanjian ini akan diselesaikan secara musyawarah mufakat oleh Para Pihak.</li>
                <li>Apabila musyawarah tidak mencapai kesepakatan, Para Pihak sepakat untuk menyelesaikannya melalui <b>Lembaga Alternatif Penyelesaian Sengketa Sektor Jasa Keuangan (LAPS SJK)</b> atau <b>Pengadilan Negeri Kutai Barat</b>.</li>
                <li>Kreditur dilarang melakukan penarikan objek pembiayaan secara paksa tanpa prosedur hukum yang sah sesuai dengan POJK Nomor 22 Tahun 2023 dan Putusan Mahkamah Konstitusi Nomor 18/PUU-XVII/2019.</li>
                <li>Para pihak memilih domisili hukum yang umum dan tetap di Kantor Panitera Pengadilan Negeri Kutai Barat.</li>
            </ol>

            <div class="pasal-title">PASAL 5<br>KETENTUAN PENUTUP</div>
            <p>Perjanjian ini dibuat dengan sadar, tanpa paksaan, dan dalam keadaan sehat jasmani dan rohani. Perjanjian ini dibuat dalam rangkap 2 (dua) yang masing-masing mempunyai kekuatan hukum yang sama, satu untuk Pihak Pertama dan satu untuk Pihak Kedua.</p>
        </div>
        """
        
        signature_html = f"""
        <div class="signature-area">
            <div class="sig-box">
                <div class="sig-title">PIHAK PERTAMA (KREDITUR)</div>
                <div class="cert-sig-box">
                    <div class="cert-sig-header">
                        <svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                        TERSERTIFIKASI
                    </div>
                    <div class="cert-sig-name">ADI HARIANTO, S.E.</div>
                    <div class="cert-sig-text">Ditandatangani secara elektronik<br>Menggunakan Sertifikat PSrE</div>
                    <div class="cert-sig-barcode"><svg id="signatureBarcode"></svg></div>
                </div>
                <div class="sig-name">ADI HARIANTO, S.E.</div>
                <div class="sig-role">Direktur CV. Grace Haven Transport</div>
            </div>
            
            <div class="sig-box">
                <div class="sig-title">PIHAK KEDUA (DEBITUR)</div>
                <div class="ematerai-box">
                    (Tempel e-Meterai / TTD Basah)
                </div>
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
                    <div class="tag">CASH &amp; CREDIT - AUTHORIZED RETAILER</div>
                    <div class="addr">
                        {ALAMAT_TOKO}<br>
                        HP/WA: 0822-9954-8411
                    </div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Invoice Kredit</div>
                    <div class="inv-no">#GRC-INV-{kid}</div>
                    <div class="inv-date">{datetime.now().strftime('%d %B %Y')}</div>
                </div>
            </header>

            <div class="meta">
                <div>Status: <b style="color:var(--success);">● {m_status.upper()}</b></div>
                <div>Metode: <b>{m_metode}</b></div>
                <div>Bunga Flat: <b>{m_bunga_bln}% / Bulan</b></div>
            </div>

            <div class="body">
                <div class="grid-2">
                    <div class="card">
                        <div class="card-title">👤 Penerima / Customer</div>
                        <div class="kv-row"><div class="k">Nama</div><div class="v">{d['cn']}</div></div>
                        <div class="kv-row"><div class="k">Telepon</div><div class="v">{d['telepon']}</div></div>
                        <div class="kv-row"><div class="k">Alamat</div><div class="v" style="font-weight:400; font-size:10.5px;">{d['alamat']}</div></div>
                    </div>
                    <div class="card">
                        <div class="card-title">📱 Detail Produk</div>
                        <div class="kv-row"><div class="k">Deskripsi</div><div class="v">{d['pn']}</div></div>
                        <div class="kv-row"><div class="k">SKU</div><div class="v">GRC-{d['produk_id']}</div></div>
                        <div class="kv-row"><div class="k">Garansi</div><div class="v">3 Bulan</div></div>
                        <div class="kv-row"><div class="k">Harga</div><div class="v">{format_rp(m_harga_cash)}</div></div>
                    </div>
                </div>

                <div class="summary-grid">
                    <div class="sum-card green">
                        <div class="lbl">DP Dibayar</div>
                        <div class="val">{format_rp(m_dp)}</div>
                    </div>
                    <div class="sum-card amber">
                        <div class="lbl">Angsuran / Bulan</div>
                        <div class="val">{format_rp(m_cicilan)}</div>
                    </div>
                </div>

                {html_tenor_options}
                {html_schedule}
                
                <div class="note-text">
                    *Catatan: DP {format_rp(m_dp)} telah diterima. Pokok {format_rp(m_pokok)} diangsur sesuai tenor yang dipilih. Terdapat Biaya Administrasi/Materai sebesar <b>Rp 10.000</b> (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir. Total yang disetor pada bulan ke-{tenor_asli} adalah {format_rp(cicilan_terakhir)}.
                </div>

                <div class="bank-box">
                    <div class="title">Pembayaran Transfer Resmi</div>
                    <div class="acc">Bank Mandiri: 148-00-2889246-4</div>
                    <div class="name">a.n. CV GRACE HAVEN TRANSPORT</div>
                </div>

                <div class="info-box">
                    <strong>⚠️ PENTING - KONSEKUENSI MANGKIR</strong>
                    Jika Debitur lalai/mangkir dalam pembayaran angsuran, Kreditur berhak melaporkan Debitur ke <b>Sistem Layanan Informasi Keuangan (SLIK) OJK</b> dan/atau <b>BI Checking</b>. Hal ini mengakibatkan Debitur masuk dalam daftar hitam (blacklist) yang akan menyulitkan Debitur untuk mengajukan pinjaman/kredit di lembaga keuangan manapun di kemudian hari.
                </div>
            </div>

            <footer class="footer">
                <div style="font-weight: 700; color: var(--primary); margin-bottom: 2px;">GRACE'S ELECTRONIC</div>
                <div>Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak. Simpan sebagai bukti pembayaran yang sah.</div>
            </footer>
        </div>
        """

        html_page2 = f"""
        <div class="page" style="page-break-before: always;">
            <header class="hdr">
                <div class="brand">
                    <h1>GRACE'S ELECTRONIC</h1>
                    <div class="tag">CASH &amp; CREDIT - AUTHORIZED RETAILER</div>
                    <div class="addr">
                        {ALAMAT_TOKO}<br>
                        HP/WA: 0822-9954-8411
                    </div>
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
            
            <footer class="footer">
                <div class="footer-brand">GRACE'S ELECTRONIC</div>
                <div>Dokumen ini sah dan mengikat secara hukum.</div>
            </footer>
        </div>
        """

        invoice_html = f"""
        <!DOCTYPE html>
        <html lang="id">
        <head>
        <meta charset="utf-8">
        <title>Invoice Kredit - GRACE'S ELECTRONIC</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <style>
            :root {{ --primary: #1e3a8a; --primary-light: #eff6ff; --accent: #d97706; --accent-light: #fffbeb; --success: #059669; --success-light: #ecfdf5; --danger: #dc2626; --danger-light: #fef2f2; --text-main: #1f2937; --text-muted: #6b7280; --border: #e5e7eb; }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif; background: #f3f4f6; padding: 20px 10px; color: var(--text-main); font-size: 12px; line-height: 1.4; }}
            .page {{ max-width: 820px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            
            .btn-print-wrap {{ position: sticky; top: 0; z-index: 9999; background: rgba(243,244,246,0.9); padding: 12px 0; text-align: center; border-bottom: 1px solid var(--border); margin-bottom: 20px; }}
            .btn-print {{ background: linear-gradient(135deg, #2563eb, #1e40af); color: white; border: none; padding: 10px 24px; font-size: 14px; border-radius: 50px; cursor: pointer; font-weight: 600; width: 100%; max-width: 350px; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }}
            .btn-print:hover {{ transform: translateY(-2px); }}

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

            .tenor-options {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
            .tenor-card {{ position: relative; border: 1.5px solid #d1d5db; border-radius: 8px; padding: 12px 16px; }}
            .tenor-card.recommended {{ border-color: #1e3a8a; }}
            .tenor-card.recommended::before {{ content: 'DIPILIH'; position: absolute; top: -1.5px; right: -1.5px; background: #b8956a; color: #fff; font-size: 7.5px; font-weight: 700; letter-spacing: 1px; padding: 2px 7px; border-radius: 0 6px 0 6px; }}
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
                .tenor-options {{ gap: 10px; }}
                * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            }}
        </style>
        </head>
        <body>
            <div class="btn-print-wrap">
                <button class="btn-print" onclick="window.print()">🖨️ Cetak Invoice & Perjanjian</button>
            </div>

            {html_page1}
            {html_page2}
            
            <script>
                window.onload = function() {{
                    JsBarcode("#signatureBarcode", "PSrE-ADI-HARIANTO-2026", {{
                        format: "CODE128",
                        width: 1.0,
                        height: 25,
                        displayValue: false,
                        margin: 0,
                        lineColor: "#0f172a",
                        background: "#ffffff"
                    }});
                }};
            </script>
        </body>
        </html>
        """

        components.html(invoice_html, height=1800, scrolling=True)
        
        st.info("💡 **Tips Cetak:** Untuk hasil cetak (Print/PDF) yang sempurna, klik tombol **📥 Download File Slip (HTML)** di bawah. Buka file tersebut di browser (Chrome/Edge), lalu tekan **Ctrl+P**.")
        
        st.download_button(
            f"📥 Download File Slip (HTML)",
            invoice_html,
            f"invoice_kredit_{kid}.html",
            "text/html",
            use_container_width=True
        )

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

# ==================== 12. LAPORAN & ANALITIK ====================
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
                # PERBAIKAN ERROR MODULENOTFOUND: Menggunakan xlsxwriter
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

# ==================== 13. MODAL VS PROFIT ====================
elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Laporan Modal vs Profit Pakaian</h1></div>', unsafe_allow_html=True)
    df_pk = pd.read_sql_query("SELECT nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ('Pakaian', 'Atasan', 'Bawahan', 'Dress', 'Outerwear', 'Batik')", conn)
    
    if df_pk.empty:
        st.info("Belum ada data produk pakaian.")
    else:
        # PERBAIKAN ERROR PANDAS: Pastikan kolom numerik dan tangani NaN
        df_pk['harga_modal'] = pd.to_numeric(df_pk['harga_modal'], errors='coerce').fillna(0)
        df_pk['harga_jual'] = pd.to_numeric(df_pk['harga_jual'], errors='coerce').fillna(0)
        
        # Hitung Profit
        df_pk['profit'] = df_pk['harga_jual'] - df_pk['harga_modal']
        
        # Format ke Rupiah (Safe)
        df_pk['harga_modal'] = df_pk['harga_modal'].apply(format_rp)
        df_pk['harga_jual'] = df_pk['harga_jual'].apply(lambda x: format_rp(x) if x > 0 else "Belum diset")
        df_pk['profit'] = df_pk['profit'].apply(lambda x: format_rp(x) if x != 0 else "-")
        
        st.dataframe(df_pk, use_container_width=True, hide_index=True)
        st.caption("Catatan: Produk dengan harga jual 'Belum diset' tidak akan bisa dijual secara kredit sampai harganya diisi di menu Stok Barang.")
        # ==================== 14. ALERT & REMINDER ====================
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

# ==================== 15. BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1></div>', unsafe_allow_html=True)
    
    tab_backup, tab_excel = st.tabs(["💾 Backup Database", "📑 Cetak Laporan Excel"])
    
            with tab_backup:
        st.success("✅ Sistem telah terhubung ke Database Cloud (Supabase).")
        st.info("Data Anda sekarang aman dan tersimpan permanen di cloud. Data tidak akan hilang meskipun aplikasi di-restart.")
        st.markdown("""
        **Cara Backup Manual:**
        1. Login ke dashboard [Supabase](https://supabase.com).
        2. Buka project Anda.
        3. Buka menu **Database** -> **Backups**.
        4. Supabase otomatis melakukan backup harian (Pro plan), atau Anda bisa menggunakan menu **SQL Editor** untuk export data.
        """)
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
                for b in list_backup[:5]: # Tampilkan 5 terbaru
                    st.write(f"- `{b}`")
            else:
                st.write("Belum ada backup otomatis.")

    with tab_excel:
        st.subheader("Cetak Laporan Lengkap ke Excel")
        st.info("Fitur ini menggunakan `xlsxwriter` untuk menghasilkan file Excel multi-sheet (Invoice, Customer, Serah Terima) yang rapi.")
        
        if st.button("📊 Generate Laporan Excel", use_container_width=True):
            try:
                df_invoice = pd.read_sql_query("SELECT * FROM kredit", conn)
                # Pastikan tipe data aman untuk Excel
                if not df_invoice.empty:
                    df_invoice['total_hutang'] = pd.to_numeric(df_invoice['total_hutang'], errors='coerce').fillna(0)
                    
                df_pelanggan = pd.read_sql_query("SELECT * FROM customer", conn)
                df_serah = pd.read_sql_query("SELECT * FROM serah_terima", conn)
                df_cash = pd.read_sql_query("SELECT * FROM transaksi_cash", conn)
                
                buffer = io.BytesIO()
                # Menggunakan engine xlsxwriter
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
# elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas Sistem</h1></div>', unsafe_allow_html=True)
    st.info("Catatan semua aktivitas yang dilakukan oleh pengguna di dalam sistem.")
    
    df_log = pd.read_sql_query("SELECT waktu, username, aksi, detail FROM log_aktivitas ORDER BY id DESC LIMIT 100", conn)
    
    if df_log.empty:
        st.write("Belum ada aktivitas tercatat.")
    else:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        
    if st.button("🔄 Refresh Log"):
        st.rerun()
