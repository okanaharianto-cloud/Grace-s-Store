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

# ==================== KONEKSI DATABASE (PATH ABSOLUT & AUTO BACKUP) ====================
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
c.execute('''CREATE TABLE IF NOT EXISTS produk 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_cash 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, 
              harga_jual_satuan REAL, total_harga REAL, uang_bayar REAL, kembalian REAL, laba REAL, tanggal TEXT)''')
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
c.execute('''CREATE TABLE IF NOT EXISTS pengaturan
             (kunci TEXT PRIMARY KEY, nilai TEXT, keterangan TEXT)''')
# Tabel baru untuk menyimpan jadwal kustom
c.execute('''CREATE TABLE IF NOT EXISTS jadwal_kustom
             (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, opsi TEXT, 
              ke INTEGER, jatuh_tempo TEXT, angsuran REAL, sisa REAL)''')
conn.commit()

# ==================== MIGRASI KOLOM ====================
for sql in [
    "ALTER TABLE produk ADD COLUMN markup_persen REAL DEFAULT 5.0",
    "ALTER TABLE produk ADD COLUMN harga_jual REAL",
    "ALTER TABLE transaksi_cash ADD COLUMN harga_jual_satuan REAL DEFAULT 0",
    "ALTER TABLE transaksi_cash ADD COLUMN laba REAL DEFAULT 0",
    "ALTER TABLE kredit ADD COLUMN tanggal_kredit TEXT",
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
    "denda_per_hari_persen":     ("1.0",   "Denda keterlambatan per hari (%) dari cicilan"),
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
    c.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai, keterangan) VALUES (?,?,?)",
              (kunci, str(nilai), keterangan or ""))
    conn.commit()
    st.session_state.pop(f"_setting_{kunci}", None)

def log_aksi(username, aksi, detail=""):
    try:
        c.execute("INSERT INTO log_aktivitas (username, aksi, detail, waktu) VALUES (?,?,?,?)",
                  (username, aksi, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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

def hitung_denda(cicilan_bulan, hari_telat):
    persen = get_pengaturan_float("denda_per_hari_persen", 1.0)
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
        schedule.append({
            "ke": i,
            "jatuh_tempo": tgl.strftime("%d-%m-%Y"),
            "angsuran": bayar,
            "sisa": sisa,
        })
    return schedule

def get_schedule_for_invoice(kredit_id, opsi, total, cicilan, tenor, tgl_str):
    # Cek apakah ada jadwal kustom di database
    df_custom = pd.read_sql_query("SELECT ke, jatuh_tempo, angsuran, sisa FROM jadwal_kustom WHERE kredit_id=? AND opsi=? ORDER BY ke", conn, params=(kredit_id, opsi))
    if not df_custom.empty:
        return df_custom
    else:
        return pd.DataFrame(build_jadwal_angsuran(total, cicilan, tenor, tgl_str))

# Seed admin
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)",
              ("admin", hash_password("admin123"), "Administrator", "admin"))
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
        ("Dress Putih Lengan Panjang", "Dress", 0, 5),
        ("Hoodie Orange Female Monster", "Atasan", 0, 5),
        ("Dress Stripe Hitam Putih", "Dress", 0, 5),
        ("Jumpeuit Apron Hitam", "Pakaian", 0, 5),
        ("Kemeja Two-Way Jolene Olive", "Atasan", 0, 5),
        ("Dress Double-Breasted Olive", "Dress", 0, 5),
        ("Dress Lace Pink Mutiara", "Dress", 0, 5),
        ("Blouse Ruffle Cream", "Atasan", 0, 5),
        ("Atasan Puff Sleeve Floral Mint", "Atasan", 0, 5),
        ("Dress Textured Khaki Sabuk", "Dress", 0, 5),
        ("Tunik Textured Abu-abu", "Atasan", 0, 5),
        ("Sweater Rajut Chunky Cream", "Atasan", 0, 5),
        ("Blouse Lace Turtleneck Putih", "Atasan", 0, 5),
        ("Trench Coat Khaki Pink Lining", "Outerwear", 0, 5),
        ("Dress Textured Abu Tanpa Lengan", "Dress", 0, 5),
        ("Dress Textured Beige Kancing", "Dress", 0, 5),
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
        "💰 Pembayaran Cicilan", 
        "🖨️ Cetak Slip Kredit",
        "👥 Data Customer", 
        "📦 Stok Barang",
        "🚨 Overdue & Denda", 
        "🔔 Alert & Reminder", 
        "📊 Laporan & Analitik",
        "👕 Modal vs Profit", 
        "💾 Backup, Cetak & Impor",
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
    denda_val = st.number_input("Denda per hari telat (% dari cicilan)", min_value=0.0, max_value=20.0, value=get_pengaturan_float("denda_per_hari_persen", 1.0), step=0.1, format="%.2f", key="input_denda_owner")
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

    # === FITUR BARU: SIMULASI SKEMA (BISA HIDE RINCIAN) ===
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

        # Kalkulasi Simulasi
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

    pakaian_belum_harga = c.execute(
        f"SELECT COUNT(*) FROM produk WHERE kategori IN ({','.join(['?']*len(PAKAIAN_KATEGORI))}) "
        f"AND (harga_jual IS NULL OR harga_jual <= 0)", tuple(PAKAIAN_KATEGORI)).fetchone()[0]

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
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    if pakaian_belum_harga > 0:
        st.warning(f"⚠️ **{pakaian_belum_harga} produk pakaian belum diisi harga jual.** Buka menu **📦 Stok Barang** → **Edit Harga Jual Pakaian**.")

    st.markdown('<div class="section-header"><h3>📊 Analitik Penjualan</h3></div>', unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**🏆 Top 5 Produk Terlaris (Kredit + Cash)**")
        df_top = pd.read_sql_query("""
            SELECT produk, SUM(qty) as jumlah_terjual FROM (
                SELECT p.nama as produk, 1 as qty FROM kredit k JOIN produk p ON k.produk_id = p.id
                UNION ALL
                SELECT p.nama as produk, t.jumlah as qty FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
            ) GROUP BY produk ORDER BY jumlah_terjual DESC LIMIT 5
        """, conn)
        
        if not df_top.empty:
            chart = alt.Chart(df_top).mark_bar(cornerRadiusTopRight=10, cornerRadiusBottomRight=10).encode(
                x=alt.X('jumlah_terjual:Q', title='Jumlah Terjual'),
                y=alt.Y('produk:N', sort='-x', title='Produk'),
                color=alt.Color('jumlah_terjual:Q', scale=alt.Scale(scheme='purples'), legend=None)
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")

    with col_chart2:
        st.markdown("**📈 Cicilan Masuk per Bulan**")
        df_bayar = pd.read_sql_query("SELECT substr(tanggal,1,7) as bulan, SUM(jumlah_bayar) as total FROM pembayaran GROUP BY bulan ORDER BY bulan", conn)
        if not df_bayar.empty:
            chart = alt.Chart(df_bayar).mark_area(
                line={'color':'#667eea'}, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#f093fb', offset=0), alt.GradientStop(color='#667eea', offset=1)],
                    x1=1, x2=1, y1=1, y2=0)
            ).encode(
                x=alt.X('bulan:N', title='Bulan'),
                y=alt.Y('total:Q', title='Total (Rp)')
            ).properties(height=300)
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
                    c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,?,?)",
                              (nama_produk, kategori, harga_modal, stok_awal, markup_persen, harga_jual))
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
                            
                            # Cek stok jika jumlah bertambah
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
                                    # Sesuaikan stok
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
            dp_persen = st.number_input(
                "DP (%)", 
                min_value=float(dp_min_persen_default), 
                max_value=100.0, 
                value=float(dp_min_persen_default), 
                step=1.0,
                help=f"Minimal DP dari Owner adalah {dp_min_persen_default}%"
            )
        with col_tenor:
            tenor = st.selectbox("Tenor (Bulan)", tenor_list, index=min(3, len(tenor_list)-1))
        with col_bunga:
            bunga_flat = st.number_input(
                "Bunga Flat / 6 Bln (%)", 
                min_value=0.0, 
                value=float(bunga_flat_default), 
                step=1.0,
                help="Bisa diubah manual jika ada nego bunga"
            )

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
                c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (id_c, id_p, h_cash, dp, pokok, total, tenor, cicilan, total, tgl_tempo, "Berjalan", tgl_kredit))
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
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 1.0)

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
                    c.execute("INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan) VALUES (?,?,?,?,?)",
                              (kredit_id, jumlah_bayar, denda, datetime.now().strftime("%Y-%m-%d"), keterangan))
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

# ==================== 6b. CETAK SLIP KREDIT (PRINT & FOOTER) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit & Jadwal Angsuran</h1><p>Slip DP + jadwal cicilan untuk diberikan ke customer</p></div>', unsafe_allow_html=True)

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
            SELECT k.*, c.nama as cn, c.telepon, c.alamat, p.nama as pn
            FROM kredit k 
            LEFT JOIN customer c ON k.customer_id = c.id 
            LEFT JOIN produk p ON k.produk_id = p.id 
            WHERE k.id=?
        """, conn, params=(kid,)).iloc[0].fillna('-')

        # ================= PENGATURAN CETAK & EDIT MANUAL =================
        st.markdown('<div class="section-header"><h3>✏️ Edit Manual Data Akad (Khusus Cetakan Ini)</h3></div>', unsafe_allow_html=True)
        with st.expander("Buka Form Edit Manual", expanded=True):
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
                m_metode = st.radio("Metode", ["Tunai (Cash)", "Transfer Bank"], horizontal=True)

            if st.button("💾 Simpan Perubahan Ini ke Database"):
                try:
                    c.execute("""UPDATE kredit SET harga_cash=?, dp=?, pokok_hutang=?, total_hutang=?, cicilan_bulan=?, tenor=?, jatuh_tempo=?, status=? WHERE id=?""",
                              (m_harga_cash, m_dp, m_pokok, m_total_hutang, m_cicilan, m_tenor, m_tempo.strftime("%Y-%m-%d"), m_status, kid))
                    recalculate_kredit(kid)
                    conn.commit()
                    log_aksi(st.session_state.username, "EDIT_AKAD_KREDIT", f"ID {kid}")
                    flash("✅ Perubahan berhasil disimpan ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

        df_bayar = pd.read_sql_query("""
            SELECT id, tanggal, jumlah_bayar, denda, keterangan
            FROM pembayaran WHERE kredit_id=? ORDER BY id
        """, conn, params=(kid,))

        tanggal_kredit_str = d['tanggal_kredit'] if pd.notna(d['tanggal_kredit']) else (datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        
        tenor_asli = int(m_tenor)
        total_asli = float(m_total_hutang)
        rate_bulan = m_bunga_bln / 100
        
        # Toggle perbandingan tenor
        tampilkan_banding = st.toggle("Tampilkan Perbandingan 2 Tenor", value=True, help="Aktifkan untuk menampilkan 2 opsi tenor (misal 2x & 3x) untuk perbandingan. Matikan untuk hanya menampilkan 1 tenor yang dipilih.")
        # Toggle Hide Sensitif
        hide_sensitive = st.toggle("🙈 Sembunyikan Rincian (Mode Pelanggan)", value=False, help="Jika aktif, Harga Cash, Pokok Hutang, Bunga Flat, dan Sisa Hutang akan disembunyikan.")
        
        hide_style = "display: none !important;" if hide_sensitive else ""
        hide_col_style = "display: none !important;" if hide_sensitive else "table-cell"
        grid_cols = "1fr" if hide_sensitive else "repeat(4, 1fr)"

        if tampilkan_banding:
            tenor_opsi_1 = 2
            tenor_opsi_2 = 3
            pokok_awal = float(m_pokok)
            
            total_1 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_1)), -2)
            cicilan_1 = round(total_1 / tenor_opsi_1, -2)
            
            total_2 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_2)), -2)
            cicilan_2 = round(total_2 / tenor_opsi_2, -2)
            
            # --- FITUR BARU: EDIT JADWAL ANGSURAN (OPSI A & B) ---
            st.markdown("### ✏️ Edit Tabel Jadwal (Opsi A & B)")
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.markdown("**Tabel Opsi A**")
                df_sched_1 = get_schedule_for_invoice(kid, 'A', total_1, cicilan_1, tenor_opsi_1, tanggal_kredit_str)
                df_sched_1['jatuh_tempo'] = pd.to_datetime(df_sched_1['jatuh_tempo'], format="%d-%m-%Y").dt.date
                edited_sched_1 = st.data_editor(df_sched_1, disabled=["ke", "sisa"], hide_index=True, key="edit_sched_1",
                    column_config={"ke": "Ke", "jatuh_tempo": "Tgl Tempo", "angsuran": "Nominal", "sisa": "Sisa"})
                
            with col_s2:
                st.markdown("**Tabel Opsi B**")
                df_sched_2 = get_schedule_for_invoice(kid, 'B', total_2, cicilan_2, tenor_opsi_2, tanggal_kredit_str)
                df_sched_2['jatuh_tempo'] = pd.to_datetime(df_sched_2['jatuh_tempo'], format="%d-%m-%Y").dt.date
                edited_sched_2 = st.data_editor(df_sched_2, disabled=["ke", "sisa"], hide_index=True, key="edit_sched_2",
                    column_config={"ke": "Ke", "jatuh_tempo": "Tgl Tempo", "angsuran": "Nominal", "sisa": "Sisa"})
                    
            if st.button("💾 Simpan Jadwal Kustom (Opsi A & B)"):
                try:
                    # Hapus jadwal lama untuk opsi A & B kredit ini
                    c.execute("DELETE FROM jadwal_kustom WHERE kredit_id=? AND opsi IN ('A', 'B')", (kid,))
                    
                    # Simpan Opsi A
                    sisa_a = edited_sched_1['angsuran'].sum()
                    for idx, row in edited_sched_1.iterrows():
                        sisa_a -= row['angsuran']
                        c.execute("INSERT INTO jadwal_kustom (kredit_id, opsi, ke, jatuh_tempo, angsuran, sisa) VALUES (?,?,?,?,?,?)",
                                  (kid, 'A', row['ke'], row['jatuh_tempo'].strftime("%d-%m-%Y"), row['angsuran'], max(sisa_a, 0)))
                        
                    # Simpan Opsi B
                    sisa_b = edited_sched_2['angsuran'].sum()
                    for idx, row in edited_sched_2.iterrows():
                        sisa_b -= row['angsuran']
                        c.execute("INSERT INTO jadwal_kustom (kredit_id, opsi, ke, jatuh_tempo, angsuran, sisa) VALUES (?,?,?,?,?,?)",
                                  (kid, 'B', row['ke'], row['jatuh_tempo'].strftime("%d-%m-%Y"), row['angsuran'], max(sisa_b, 0)))
                        
                    conn.commit()
                    flash("✅ Jadwal Kustom berhasil disimpan ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan jadwal: {e}")
            
            # Generate HTML dari hasil edit (diambil dari edited_sched)
            total_1_edit = edited_sched_1['angsuran'].sum()
            total_2_edit = edited_sched_2['angsuran'].sum()
            
            html_tenor_options = f"""
            <div class="tenor-options">
                <div class="tenor-card">
                    <div class="tc-label">Opsi A</div>
                    <div class="tc-title">Tenor {tenor_opsi_1}× ({tenor_opsi_1} Bulan)</div>
                    <div class="tc-row" style="{hide_style}"><span class="k">Bunga total ({(rate_bulan*100):.2f}%/bln)</span><span class="v">{format_rp(total_1_edit - pokok_awal)}</span></div>
                    <div class="tc-row" style="{hide_style}"><span class="k">Total hutang</span><span class="v">{format_rp(total_1_edit)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_1)}</span></div>
                </div>
                <div class="tenor-card recommended">
                    <div class="tc-label">Opsi B</div>
                    <div class="tc-title">Tenor {tenor_opsi_2}× ({tenor_opsi_2} Bulan)</div>
                    <div class="tc-row" style="{hide_style}"><span class="k">Bunga total ({(rate_bulan*100):.2f}%/bln)</span><span class="v">{format_rp(total_2_edit - pokok_awal)}</span></div>
                    <div class="tc-row" style="{hide_style}"><span class="k">Total hutang</span><span class="v">{format_rp(total_2_edit)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_2)}</span></div>
                </div>
            </div>
            """
            
            paid_count = len(df_bayar)
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r' style='{hide_col_style}'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_1.iterrows()])
            rows_2 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r' style='{hide_col_style}'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_2.iterrows()])
            
            html_schedule = f"""
            <div class="sched-wrap" style="grid-template-columns: 1fr 1fr;">
                <div class="sched">
                    <div class="sched-h two">📅 Opsi A — Tenor {tenor_opsi_1}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r" style="{hide_col_style}">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_1_edit)}</td><td class="r" style="{hide_col_style}">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
                <div class="sched">
                    <div class="sched-h three">📅 Opsi B — Tenor {tenor_opsi_2}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r" style="{hide_col_style}">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_2}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_2_edit)}</td><td class="r" style="{hide_col_style}">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
            </div>
            """
        else:
            # --- FITUR BARU: EDIT JADWAL ANGSURAN (SINGLE) ---
            st.markdown("### ✏️ Edit Tabel Jadwal")
            df_sched_1 = get_schedule_for_invoice(kid, 'SINGLE', total_asli, m_cicilan, tenor_asli, tanggal_kredit_str)
            df_sched_1['jatuh_tempo'] = pd.to_datetime(df_sched_1['jatuh_tempo'], format="%d-%m-%Y").dt.date
            edited_sched_1 = st.data_editor(df_sched_1, disabled=["ke", "sisa"], hide_index=True, key="edit_sched_1_single",
                column_config={"ke": "Ke", "jatuh_tempo": "Tgl Tempo", "angsuran": "Nominal", "sisa": "Sisa"})
                
            if st.button("💾 Simpan Jadwal Kustom"):
                try:
                    c.execute("DELETE FROM jadwal_kustom WHERE kredit_id=? AND opsi='SINGLE'", (kid,))
                    sisa_a = edited_sched_1['angsuran'].sum()
                    for idx, row in edited_sched_1.iterrows():
                        sisa_a -= row['angsuran']
                        c.execute("INSERT INTO jadwal_kustom (kredit_id, opsi, ke, jatuh_tempo, angsuran, sisa) VALUES (?,?,?,?,?,?)",
                                  (kid, 'SINGLE', row['ke'], row['jatuh_tempo'].strftime("%d-%m-%Y"), row['angsuran'], max(sisa_a, 0)))
                    conn.commit()
                    flash("✅ Jadwal Kustom berhasil disimpan ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan jadwal: {e}")
            
            total_1_edit = edited_sched_1['angsuran'].sum()
            
            html_tenor_options = f"""
            <div class="tenor-options" style="grid-template-columns: 1fr;">
                <div class="tenor-card recommended">
                    <div class="tc-label">Tenor Dipilih</div>
                    <div class="tc-title">Tenor {tenor_asli}× ({tenor_asli} Bulan)</div>
                    <div class="tc-row" style="{hide_style}"><span class="k">Total hutang (Pokok + Bunga)</span><span class="v">{format_rp(total_1_edit)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
                </div>
            </div>
            """
            
            paid_count = len(df_bayar)
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r' style='{hide_col_style}'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_1.iterrows()])
            
            html_schedule = f"""
            <div class="sched-wrap" style="grid-template-columns: 1fr;">
                <div class="sched">
                    <div class="sched-h two">📅 Jadwal Angsuran — Tenor {tenor_asli}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r" style="{hide_col_style}">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_1_edit)}</td><td class="r" style="{hide_col_style}">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
            </div>
            """

        # ================= PERJANJIAN KHUSUS OJK & MATERAI =================
        # Tampilkan Materai jika Total Hutang >= 5.000.000
        materai_html = ""
        if m_total_hutang >= 5000000:
            # Generate unique serial number for E-Materai
            serial_materai = f"EM-{uuid.uuid4().hex[:8].upper()}-{datetime.now().strftime('%Y')}"
            materai_html = f"""
            <div class="materai-box">
                <div class="materai-header">METERAI<br>TEMPEL</div>
                <div class="materai-value">Rp 10.000</div>
                <div class="materai-serial">{serial_materai}</div>
                <div class="materai-footer">E-Meterai Sah</div>
            </div>
            """
            
        # Teks Perjanjian (Hitam di atas putih, tanpa nominal bunga)
        perjanjian_html = f"""
        <div class="agreement-container">
            <div class="agreement-title">SURAT PERJANJIAN KREDIT BARANG & SURAT KUASA PEMBEBANAN</div>
            <div class="agreement-number">Nomor: GRC-INV-{kid}/PERJ/2026</div>
            
            <p>Pada hari ini, <b>{datetime.now().strftime('%d %B %Y')}</b>, yang bertanda tangan di bawah ini:</p>
            
            <table class="agreement-table">
                <tr>
                    <td style="width: 150px; vertical-align: top;"><b>PIHAK PERTAMA (Kreditur)</b></td>
                    <td style="vertical-align: top;">: <b>Grace's Electronic</b>, berkedudukan di {ALAMAT_TOKO}.</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><b>PIHAK KEDUA (Debitur)</b></td>
                    <td style="vertical-align: top;">: <b>{d['cn']}</b>, beralamat di {d['alamat']}, Telp/WA: {d['telepon']}.</td>
                </tr>
            </table>
            
            <p>Kedua belah pihak sepakat untuk mengikatkan diri dalam Perjanjian Kredit dengan ketentuan sebagai berikut:</p>
            
            <div class="agreement-articles">
                <b>Pasal 1 - Objek Perjanjian</b>
                <p>Pihak Pertama menyerahkan hak milik barang berupa <b>{d['pn']}</b> kepada Pihak Kedua, dan Pihak Kedua setuju untuk membeli barang tersebut secara kredit dengan harga cash sebesar <b>{format_rp(m_harga_cash)}</b>.</p>
                
                <b>Pasal 2 - Ketentuan Pembiayaan (Sesuai Standar OJK)</b>
                <p>1. Uang Muka (DP) yang telah dibayarkan adalah sebesar <b>{format_rp(m_dp)}</b>.</p>
                <p>2. Sisa pembayaran yang harus dilunasi adalah sebesar <b>{format_rp(m_pokok)}</b> (Pokok).</p>
                <p>3. Pihak Kedua setuju untuk melunasi total kewajiban (angsuran + bunga) sebesar <b>{format_rp(m_total_hutang)}</b>.</p>
                <p>4. Pelunasan dilakukan secara angsuran selama <b>{m_tenor} bulan</b>, dengan nominal angsuran sebesar <b>{format_rp(m_cicilan)} per bulan</b>.</p>
                <p>5. Pembayaran angsuran perdana wajib dilakukan pada tanggal <b>{m_tempo.strftime('%d-%m-%Y')}</b> dan selambat-lambatnya setiap tanggal yang sama pada bulan berikutnya.</p>
                
                <b>Pasal 3 - Jatuh Tempo & Denda</b>
                <p>1. Angsuran wajib dibayarkan setiap tanggal jatuh tempo sesuai jadwal yang telah disepakati.</p>
                <p>2. Keterlambatan pembayaran dikenakan denda sebesar <b>{get_pengaturan_float("denda_per_hari_persen", 1.0)}% per hari</b> dari nominal angsuran yang tertunggak.</p>
                
                <b>Pasal 4 - Wanprestasi</b>
                <p>Apabila Pihak Kedua gagal membayar angsuran selama 2 (dua) bulan berturut-turut, maka Pihak Pertama berhak melakukan penarikan barang secara paksa (Parate Eksekusi) dan Pihak Kedua bersedia menyerahkannya tanpa syarat.</p>
            </div>
            
            <p>Demikian perjanjian ini dibuat dengan sadar, tanpa paksaan, dan dibuat dalam keadaan sehat jasmani dan rohani.</p>
        </div>
        """
        
        # ================= E-SIGNATURE =================
        signature_html = f"""
        <div class="signature-area">
            <div class="sig-box">
                <div class="sig-title">PIHAK PERTAMA (TOKO)</div>
                <div class="sig-space">
                    {materai_html}
                    <svg id="signatureBarcode"></svg>
                </div>
                <div class="sig-name">Grace's Electronic</div>
                <div class="sig-verify">Digital Signature by System</div>
            </div>
            <div class="sig-box">
                <div class="sig-title">PIHAK KEDUA (CUSTOMER)</div>
                <div class="sig-space">
                    <div class="customer-ttd">{d['cn']}</div>
                </div>
                <div class="sig-name">( {d['cn']} )</div>
                <div class="sig-verify">E-Sign / Tanda Tangan Basah</div>
            </div>
        </div>
        """

        # ================= INVOICE HTML (HALAMAN 1) =================
        html_page1 = f"""
        <div class="page">
            <header class="hdr">
                <div class="brand">
                    <h1>Grace's Electronic</h1>
                    <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                    <div class="addr">{ALAMAT_TOKO} • HP/WA: 0822-9954-8411</div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Invoice Kredit</div>
                    <div class="inv-no">#GRC-INV-{kid}</div>
                    <div class="inv-date">{datetime.now().strftime('%d %B %Y · %H:%M')} WITA</div>
                </div>
            </header>

            <div class="meta">
                <div>Status: <b style="color:#059669;">● {m_status.upper()}</b></div>
                <div>Metode: <b>{m_metode}</b></div>
                <div style="{hide_style}">Bunga Flat: <b>{(rate_bulan*100):.2f}% / bln</b></div>
            </div>

            <div class="body">
                <!-- Customer + Product -->
                <div class="top-grid">
                    <div class="sec">
                        <div class="sec-title"><span class="ic">👤</span> Customer</div>
                        <div class="kv">
                            <div class="k">Nama</div><div class="v">{d['cn']}</div>
                            <div class="k">Telepon</div><div class="v">{d['telepon']}</div>
                            <div class="k">Alamat</div><div class="v">{d['alamat']}</div>
                        </div>
                    </div>
                    <div class="sec">
                        <div class="sec-title"><span class="ic">📱</span> Produk</div>
                        <div class="kv">
                            <div class="k">Nama</div><div class="v">{d['pn']}</div>
                            <div class="k">SKU</div><div class="v">GRC-{d['produk_id']}</div>
                            <div class="k">Garansi</div><div class="v">3 Bulan</div>
                        </div>
                    </div>
                </div>

                <!-- Summary Cards -->
                <div class="summary" style="grid-template-columns: {grid_cols};">
                    <div class="sum-card" style="{hide_style}"><div class="lbl">Harga Cash</div><div class="val">{format_rp(m_harga_cash)}</div></div>
                    <div class="sum-card green"><div class="lbl">DP Dibayar</div><div class="val">{format_rp(m_dp)}</div></div>
                    <div class="sum-card blue" style="{hide_style}"><div class="lbl">Pokok Hutang</div><div class="val">{format_rp(m_pokok)}</div></div>
                    <div class="sum-card amber" style="{hide_style}"><div class="lbl">Bunga Flat</div><div class="val">{(rate_bulan*100):.2f}% / bln</div></div>
                </div>

                <!-- Pilihan Tenor -->
                {html_tenor_options}

                <!-- Jadwal Angsuran -->
                {html_schedule}
            </div>

            <!-- Terms -->
            <div class="terms-section">
                <div class="terms-title">Syarat &amp; Ketentuan Tambahan</div>
                <ol class="terms-list">
                    <li><b>Metode:</b> Tunai atau transfer bank sesuai kesepakatan.</li>
                    <li><b>Jatuh Tempo:</b> Setiap 30 hari, dimulai {m_tempo.strftime('%d-%m-%Y')}.</li>
                    <li style="{hide_style}"><b>Bunga:</b> Flat {(rate_bulan*100):.2f}% per bulan dari pokok hutang.</li>
                    <li><b>Keterlambatan:</b> Denda {get_pengaturan_float("denda_per_hari_persen", 1.0)}% per hari dari angsuran.</li>
                </ol>
            </div>

            <footer class="footer">
                <div class="footer-brand">GRACE'S ELECTRONIC</div>
                <div>Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak. Simpan untuk pembayaran berikutnya.</div>
                <div style="font-size:7.5px; margin-top:2px;">Pemalsuan dokumen dapat ditindak sesuai hukum yang berlaku di Republik Indonesia.</div>
            </footer>
        </div>
        """

        # ================= SURAT PERJANJIAN HTML (HALAMAN 2) =================
        html_page2 = f"""
        <div class="page" style="page-break-before: always;">
            <header class="hdr">
                <div class="brand">
                    <h1>Grace's Electronic</h1>
                    <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                    <div class="addr">{ALAMAT_TOKO} • HP/WA: 0822-9954-8411</div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Surat Perjanjian Kredit</div>
                    <div class="inv-no">#GRC-INV-{kid}</div>
                    <div class="inv-date">{datetime.now().strftime('%d %B %Y · %H:%M')} WITA</div>
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

        # Gabungkan kedua halaman ke dalam satu dokumen HTML
        invoice_html = f"""
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
            
            /* Tombol Print - Fixed di atas */
            .btn-print-wrap {{
                position: sticky;
                top: 0;
                z-index: 9999;
                background: #e2e8f0;
                padding: 10px 0;
                text-align: center;
            }}
            .btn-print {{
                background-color: #667eea; color: white; border: none;
                padding: 12px 24px; font-size: 16px; border-radius: 8px;
                cursor: pointer; font-weight: bold; width: 100%; max-width: 820px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .btn-print:hover {{ background-color: #764ba2; }}

            /* HEADER */
            .hdr {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 70%, #1e40af 100%); color: #fff; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow: hidden; }}
            .hdr::before {{ content:''; position:absolute; top:-50%; right:-5%; width:220px; height:220px; background: radial-gradient(circle, rgba(16,185,129,0.3), transparent 70%); border-radius:50%; }}
            .hdr::after {{ content:''; position:absolute; bottom:-70%; right:15%; width:180px; height:180px; background: radial-gradient(circle, rgba(245,158,11,0.25), transparent 70%); border-radius:50%; }}
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
            .body {{ padding: 10px 22px 12px; }}

            /* TOP 2-COLUMN */
            .top-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }}
            .sec {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }}
            .sec-title {{ font-size: 9.5px; font-weight: 800; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.6px; padding-bottom: 4px; margin-bottom: 5px; border-bottom: 1.5px solid #f1f5f9; display: flex; align-items: center; gap: 5px; }}
            .sec-title span.ic {{ display: inline-flex; width: 16px; height: 16px; align-items: center; justify-content: center; background: linear-gradient(135deg,#1e3a8a,#1e40af); color: #fff; border-radius: 4px; font-size: 9px; }}
            .kv {{ display: grid; grid-template-columns: 68px 1fr; gap: 3px 6px; font-size: 10px; }}
            .kv .k {{ color: #64748b; }}
            .kv .v {{ color: #0f172a; font-weight: 600; }}

            /* SUMMARY ROW */
            .summary {{ display: grid; grid-template-columns: {grid_cols}; gap: 6px; margin-bottom: 8px; }}
            .sum-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 8px; text-align: center; }}
            .sum-card.green {{ background: #ecfdf5; border-color: #a7f3d0; }}
            .sum-card.blue {{ background: #eff6ff; border-color: #bfdbfe; }}
            .sum-card.amber {{ background: #fffbeb; border-color: #fde68a; }}
            .sum-card .lbl {{ font-size: 8.5px; color: #64748b; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 700; }}
            .sum-card .val {{ font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 2px; }}
            .sum-card.green .val {{ color: #065f46; }}
            .sum-card.blue .val {{ color: #1e40af; }}
            .sum-card.amber .val {{ color: #92400e; }}

            /* OPTIONS TABLE */
            .tenor-options {{ display: grid; gap: 8px; margin-bottom: 8px; }}
            .tenor-card {{ position: relative; border: 1.5px solid #d1d5db; border-radius: 8px; padding: 10px 14px; }}
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

            /* SCHEDULE 2-COLUMN */
            .sched-wrap {{ display: grid; gap: 8px; margin-bottom: 8px; }}
            .sched {{ border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
            .sched-h {{ padding: 5px 8px; font-size: 9px; font-weight: 800; color: #fff; text-transform: uppercase; letter-spacing: 0.5px; }}
            .sched-h.two {{ background: linear-gradient(90deg, #1e40af, #2563eb); }}
            .sched-h.three {{ background: linear-gradient(90deg, #7c3aed, #8b5cf6); }}
            .sched table {{ width: 100%; border-collapse: collapse; font-size: 9.5px; }}
            .sched th {{ background: #f8fafc; color: #475569; font-size: 8.5px; text-transform: uppercase; letter-spacing: 0.3px; padding: 4px 6px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            .sched td {{ padding: 4px 6px; border-bottom: 1px solid #f1f5f9; }}
            .sched tr:last-child td {{ border-bottom: none; }}
            .sched .r {{ text-align: right; }}
            .sched .c {{ text-align: center; }}
            .sched .total td {{ background: #f8fafc; font-weight: 700; }}
            .status-pending {{ display: inline-block; padding: 1px 6px; border-radius: 8px; background: #fef3c7; color: #92400e; font-size: 8px; font-weight: 700; }}
            .status-lunas {{ display: inline-block; padding: 1px 6px; border-radius: 8px; background: #d1fae5; color: #065f46; font-size: 8px; font-weight: 700; }}

            /* PERJANJIAN OJK */
            .agreement-container {{ 
                background: #ffffff; border: 2px solid #000000; padding: 20px; margin-top: 15px; margin-bottom: 15px; 
                font-family: 'Times New Roman', Times, serif; font-size: 10.5px; color: #000000; line-height: 1.6;
            }}
            .agreement-title {{ text-align: center; font-weight: bold; font-size: 12px; text-decoration: underline; margin-bottom: 4px; }}
            .agreement-number {{ text-align: center; font-weight: bold; margin-bottom: 15px; }}
            .agreement-table {{ width: 100%; margin-bottom: 15px; }}
            .agreement-articles {{ margin-top: 10px; }}
            .agreement-articles b {{ display: block; margin-top: 10px; margin-bottom: 4px; font-size: 11px; }}
            .agreement-articles p {{ margin-bottom: 4px; text-align: justify; }}

            /* SIGNATURE & MATERAI */
            .signature-area {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
            .sig-box {{ border: 1px solid #000; border-radius: 8px; padding: 15px; text-align: center; position: relative; }}
            .sig-title {{ font-size: 10px; font-weight: bold; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            .sig-space {{ height: 100px; display: flex; align-items: center; justify-content: center; position: relative; }}
            .sig-name {{ font-size: 11px; font-weight: bold; text-decoration: underline; margin-top: 10px; }}
            .sig-verify {{ font-size: 8.5px; color: #555; margin-top: 2px; }}
            
            /* E-MATERAI STYLE */
            .materai-box {{
                position: absolute; left: 10px; top: 10px; width: 75px; height: 45px;
                background: linear-gradient(135deg, #6b21a8, #4c1d95); color: white;
                border-radius: 4px; padding: 4px; text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 10;
            }}
            .materai-header {{ font-size: 6px; font-weight: bold; letter-spacing: 1px; opacity: 0.8; }}
            .materai-value {{ font-size: 11px; font-weight: 900; margin: 1px 0; }}
            .materai-serial {{ font-size: 6px; font-family: monospace; opacity: 0.9; }}
            .materai-footer {{ font-size: 5px; margin-top: 2px; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 1px; }}
            
            .customer-ttd {{ font-family: 'Brush Script MT', 'Segoe Script', cursive; font-size: 28px; color: #1e3a8a; transform: rotate(-5deg); opacity: 0.8; }}

            /* TERMS & FOOTER */
            .terms-section {{ padding: 10px 22px; background: #f9fafb; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin-top: 15px; }}
            .terms-title {{ font-family: Georgia, serif; font-size: 9px; font-weight: 700; color: #1a2b47; letter-spacing: 1.4px; text-transform: uppercase; margin-bottom: 4px; }}
            .terms-list {{ counter-reset: item; list-style: none; display: grid; grid-template-columns: 1fr 1fr; gap: 3px 20px; font-size: 9px; color: #4b5563; }}
            .terms-list li {{ display: flex; gap: 6px; line-height: 1.5; }}
            .terms-list li::before {{ counter-increment: item; content: counter(item); font-weight: 700; color: #b8956a; flex-shrink: 0; }}
            .footer {{ padding: 8px 22px 12px; text-align: center; font-size: 8.5px; color: #9ca3af; line-height: 1.6; }}
            .footer-brand {{ font-family: Georgia, serif; font-size: 9.5px; color: #1a2b47; font-weight: 700; letter-spacing: 0.8px; }}

            @media print {{
                @page {{ size: A4 portrait; margin: 6mm; }}
                body {{ background: #fff; padding: 0; margin: 0; font-size: 9px; }}
                .btn-print-wrap {{ display: none !important; }}
                .page {{ box-shadow: none; border-radius: 0; max-width: 100%; width: 100%; border: none; margin-bottom: 0; }}
                .page:nth-child(2) {{ page-break-before: always; }} /* Halaman 2 pindah sheet */
                .hdr {{ padding: 10px 16px; }}
                .body {{ padding: 6px 16px 8px; }}
                .meta {{ padding: 4px 16px; }}
                .terms-section {{ padding: 8px 16px; }}
                .footer {{ padding: 5px 16px; }}
                * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            }}
        </style>
        </head>
        <body>
        
        <div class="btn-print-wrap">
            <button class="btn-print" onclick="window.print()">🖨️ Cetak Sekarang (Print / Simpan PDF)</button>
        </div>

        {html_page1}
        {html_page2}
        
        <script>
            window.onload = function() {{
                JsBarcode("#signatureBarcode", "GRC-{kid}-TN", {{
                    format: "CODE128",
                    width: 1.2,
                    height: 34,
                    displayValue: false,
                    margin: 0,
                    lineColor: "#1a2b47",
                    background: "#ffffff"
                }});
            }};
        </script>
        </body>
        </html>
        """

        # Tampilkan tombol Print JavaScript
        components.html(invoice_html, height=1800, scrolling=True)
        
        st.info("💡 **Tips Cetak:** Jika saat mencetak (Print) layout di atas terpotong, silakan klik tombol **📥 Download File Slip (HTML)** di bawah ini. Buka file tersebut di browser (Chrome/Edge), lalu tekan **Ctrl+P** untuk mendapatkan hasil PDF yang 100% sempurna.")
        
        st.download_button(
            f"📥 Download File Slip (HTML)",
            invoice_html,
            f"invoice_kredit_{kid}.html",
            "text/html",
            use_container_width=True
        )

# ==================== 7. DATA CUSTOMER ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Pelanggan</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Customer", "📋 Daftar & Riwayat", "✏️ Edit / Hapus Customer"])

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
                    try:
                        c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (n, t, a))
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
            SELECT c.id, c.nama, c.telepon, c.alamat,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id) as total_kredit,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id AND status='Berjalan') as aktif
            FROM customer c ORDER BY c.id DESC
        """, conn)
        st.dataframe(df_c, use_container_width=True, hide_index=True)

        if not df_c.empty:
            st.markdown('<div class="section-header"><h3>🔍 Riwayat Kredit Customer</h3></div>', unsafe_allow_html=True)
            opsi = {r['nama']: r['id'] for _, r in df_c.iterrows()}
            pilih = st.selectbox("Pilih Customer", list(opsi.keys()))
            cid = opsi[pilih]
            df_riw = pd.read_sql_query("""
                SELECT k.id, p.nama as produk, k.total_hutang, k.sisa_hutang, k.tenor, k.cicilan_bulan, k.jatuh_tempo, k.status
                FROM kredit k JOIN produk p ON k.produk_id = p.id WHERE k.customer_id=? ORDER BY k.id DESC
            """, conn, params=(cid,))
            if not df_riw.empty:
                for col in ["total_hutang", "sisa_hutang", "cicilan_bulan"]:
                    df_riw[col] = df_riw[col].apply(format_rp)
                st.dataframe(df_riw, use_container_width=True, hide_index=True)
            else:
                st.info("Customer ini belum punya kredit")

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

# ==================== 8. STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Daftar Stok", "✏️ Edit Harga Jual Pakaian", "🗑️ Edit/Hapus Produk"])

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
        total_nilai  = (df_p['stok'] * df_p['harga_modal']).sum() if not df_p.empty else 0

        html = '<div class="metric-grid">'
        html += metric_card("📦 Jenis Produk", f"{total_item} item", "card-blue")
        html += metric_card("🎒 Sisa Stok", f"{total_unit} unit", "card-purple")
        html += metric_card("🛍️ Barang Terjual", f"{total_terjual} unit", "card-orange")
        html += metric_card("💎 Nilai Stok (Modal)", format_rp(total_nilai), "card-green")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            filter_kat = st.multiselect("Filter Kategori", df_p['kategori'].unique().tolist(), default=df_p['kategori'].unique().tolist())
        with col2:
            cari = st.text_input("🔍 Cari Nama Produk")

        df_f = df_p[df_p['kategori'].isin(filter_kat)]
        if cari:
            df_f = df_f[df_f['nama'].str.contains(cari, case=False, na=False)]

        df_f = df_f.copy()
        df_f['harga_cash'] = df_f.apply(lambda r: hitung_harga_cash(r['harga_modal'], r.get('markup_persen', 5), r.get('harga_jual')), axis=1)
        df_f = df_f.rename(columns={'id': 'ID', 'nama': 'Nama Produk', 'kategori': 'Kategori', 'harga_modal': 'Harga Modal', 'harga_cash': 'Harga Cash', 'stok': 'Sisa Stok', 'terjual': 'Terjual', 'markup_persen': 'Markup %', 'harga_jual': 'Harga Jual (Pakaian)'})
        df_f['Harga Modal'] = df_f['Harga Modal'].apply(format_rp)
        df_f['Harga Cash'] = df_f['Harga Cash'].apply(format_rp)
        df_f['Harga Jual (Pakaian)'] = df_f['Harga Jual (Pakaian)'].apply(lambda x: format_rp(x) if pd.notna(x) and x > 0 else "—")
        st.dataframe(df_f, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 👕 Isi Harga Jual untuk Semua Produk Pakaian")
        st.info("Isi kolom **Harga Jual (Rp)** untuk setiap produk pakaian. Kosongkan jika belum dijual. Klik **💾 Simpan Semua** setelah selesai.")

        placeholders = ",".join(["?"] * len(PAKAIAN_KATEGORI))
        df_pk = pd.read_sql_query(f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ({placeholders}) ORDER BY kategori, nama", conn, params=tuple(PAKAIAN_KATEGORI))

        if df_pk.empty:
            st.info("Belum ada produk pakaian.")
        else:
            df_edit = df_pk.copy()
            df_edit['harga_jual'] = df_edit['harga_jual'].fillna(0).astype(float)

            edited = st.data_editor(
                df_edit,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "nama": st.column_config.TextColumn("Produk", disabled=True, width="large"),
                    "kategori": st.column_config.TextColumn("Kategori", disabled=True, width="small"),
                    "harga_modal": st.column_config.NumberColumn("Modal (Rp)", disabled=True, format="Rp %d", width="medium"),
                    "harga_jual": st.column_config.NumberColumn("Harga Jual (Rp)", min_value=0, step=1000, format="Rp %d", width="medium"),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_harga_jual_pakaian"
            )

            colA, colB = st.columns([1, 1])
            with colA:
                if st.button("💾 Simpan Semua Harga Jual", key="simpan_bulk"):
                    n_updated = 0
                    try:
                        for _, row in edited.iterrows():
                            hj = row['harga_jual'] if row['harga_jual'] > 0 else None
                            c.execute("UPDATE produk SET harga_jual=? WHERE id=?", (hj, row['id']))
                            n_updated += 1
                        conn.commit()
                        log_aksi(st.session_state.username, "EDIT_HARGA_JUAL_BULK", f"{n_updated} produk")
                        flash(f"✅ Harga jual {n_updated} produk pakaian tersimpan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
            with colB:
                belum = int((edited['harga_jual'] <= 0).sum())
                if belum > 0:
                    st.warning(f"⚠️ **{belum} produk** belum diisi harga jual.")
                else:
                    st.success("✅ Semua produk pakaian sudah punya harga jual.")

    with tab3:
        if st.session_state.role != "admin":
            st.info("Hanya admin yang dapat edit/hapus produk.")
        else:
            df_p = pd.read_sql_query("SELECT * FROM produk ORDER BY nama", conn)
            if df_p.empty:
                st.info("Belum ada produk.")
            else:
                opsi_edit = {f"{r['nama']} (ID:{r['id']})": r['id'] for _, r in df_p.iterrows()}
                pilih_edit = st.selectbox("Pilih Produk", list(opsi_edit.keys()), key="edit_prod_sel")
                pid = opsi_edit[pilih_edit]
                row = c.execute("SELECT nama, kategori, harga_modal, stok, COALESCE(markup_persen, 5), harga_jual FROM produk WHERE id=?", (pid,)).fetchone()
                is_pk = is_pakaian(row[1])

                with st.form("form_edit"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_nama = st.text_input("Nama", row[0])
                        new_kat = st.selectbox("Kategori", SEMUA_KATEGORI, index=SEMUA_KATEGORI.index(row[1]) if row[1] in SEMUA_KATEGORI else 0)
                    with col2:
                        new_harga = st.number_input("Harga Modal", value=float(row[2]), step=1000.0)
                        new_stok = st.number_input("Stok", value=int(row[3]), step=1)

                    if is_pk:
                        st.caption("👕 Kategori pakaian — isi **Harga Jual (Rp)** manual.")
                        new_harga_jual = st.number_input("Harga Jual (Rp)", value=float(row[5]) if row[5] else 0.0, step=1000.0)
                        new_markup = 0.0
                    else:
                        st.caption(f"⚙️ Non-pakaian — gunakan **Markup (%)**. *(default owner: {get_pengaturan_float('markup_default_persen', 5.0):.1f}%)*")
                        new_markup = st.number_input("Markup / Margin (%)", value=float(row[4]), min_value=0.0, max_value=500.0, step=1.0)
                        new_harga_jual = row[5]

                    colA, colB = st.columns(2)
                    with colA:
                        simpan = st.form_submit_button("💾 Update")
                    with colB:
                        hapus = st.form_submit_button("🗑️ Hapus")

                    if simpan:
                        try:
                            c.execute("UPDATE produk SET nama=?, kategori=?, harga_modal=?, stok=?, markup_persen=?, harga_jual=? WHERE id=?", (new_nama, new_kat, new_harga, new_stok, new_markup, new_harga_jual, pid))
                            conn.commit()
                            log_aksi(st.session_state.username, "EDIT_PRODUK", f"ID {pid}")
                            flash("✅ Produk diupdate!", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")
                    if hapus:
                        try:
                            c.execute("DELETE FROM produk WHERE id=?", (pid,))
                            conn.commit()
                            log_aksi(st.session_state.username, "HAPUS_PRODUK", f"ID {pid}")
                            flash("🗑️ Produk dihapus!", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")

# ==================== 9. OVERDUE & DENDA ====================
elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Daftar Kredit Overdue</h1></div>', unsafe_allow_html=True)
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    df_ov = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, c.telepon, p.nama as produk, k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo, k.tenor
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ? ORDER BY k.jatuh_tempo
    """, conn, params=(tgl_skrg,))

    if df_ov.empty:
        st.success("✅ Tidak ada akun overdue hari ini")
    else:
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 1.0)
        df_ov['hari_telat'] = df_ov['jatuh_tempo'].apply(lambda x: (datetime.now().date() - datetime.strptime(x, "%Y-%m-%d").date()).days)
        df_ov['denda'] = df_ov.apply(lambda r: hitung_denda(r['cicilan_bulan'], r['hari_telat']), axis=1)

        html = '<div class="metric-grid">'
        html += metric_card("⚠️ Akun Overdue", f"{len(df_ov)} akun", "card-pink")
        html += metric_card("💰 Total Tunggakan", format_rp(df_ov['sisa_hutang'].sum()), "card-dark")
        html += metric_card(f"💸 Total Denda ({denda_persen:.2f}%/hari)", format_rp(df_ov['denda'].sum()), "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        df_show = df_ov.copy()
        for col in ["cicilan_bulan", "sisa_hutang", "denda"]:
            df_show[col] = df_show[col].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==================== 10. ALERT & REMINDER ====================
elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder Otomatis</h1></div>', unsafe_allow_html=True)
    tgl_skrg = datetime.now().date()

    st.markdown('<div class="section-header"><h3>🚨 Sudah Jatuh Tempo</h3></div>', unsafe_allow_html=True)
    df_ov = pd.read_sql_query("SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo, k.tenor, k.sisa_hutang FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan' AND k.jatuh_tempo < ?", conn, params=(tgl_skrg.strftime("%Y-%m-%d"),))

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
                    nomor = r['telepon'].replace('-', '').replace(' ', '')
                    if nomor.startswith('0'): nomor = '62' + nomor[1:]
                    pesan = f"Halo {r['nama']}, cicilan Anda sebesar {format_rp(r['cicilan_bulan'])} sudah jatuh tempo pada {r['jatuh_tempo']} ({hari} hari lalu). Mohon segera diselesaikan. Terima kasih 🙏"
                    wa = f"https://wa.me/{nomor}?text={quote(pesan)}"
                    st.markdown(f'<a href="{wa}" target="_blank" style="text-decoration:none;"><button style="background:#25D366;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;font-weight:600;">📱 WA</button></a>', unsafe_allow_html=True)

    st.markdown('<div class="section-header"><h3>⏰ Akan Jatuh Tempo 3 Hari</h3></div>', unsafe_allow_html=True)
    tgl_h3 = (tgl_skrg + timedelta(days=3)).strftime("%Y-%m-%d")
    df_h3 = pd.read_sql_query("SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?", conn, params=(tgl_skrg.strftime("%Y-%m-%d"), tgl_h3))

    if df_h3.empty:
        st.info("Tidak ada jatuh tempo 3 hari ke depan")
    else:
        for _, r in df_h3.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.warning(f"📢 **{r['nama']}** ({r['telepon']}) - Jatuh tempo {r['jatuh_tempo']} | Cicilan: {format_rp(r['cicilan_bulan'])}")
            with col2:
                if r['telepon']:
                    nomor = r['telepon'].replace('-', '').replace(' ', '')
                    if nomor.startswith('0'): nomor = '62' + nomor[1:]
                    pesan = f"Halo {r['nama']}, ini reminder cicilan Anda {format_rp(r['cicilan_bulan'])} akan jatuh tempo pada {r['jatuh_tempo']}. Terima kasih 🙏"
                    wa = f"https://wa.me/{nomor}?text={quote(pesan)}"
                    st.markdown(f'<a href="{wa}" target="_blank" style="text-decoration:none;"><button style="background:#25D366;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;font-weight:600;">📱 WA</button></a>', unsafe_allow_html=True)

# ==================== 11. LAPORAN & ANALITIK ====================
elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📈 Penjualan", "💵 Pembayaran", "📦 Stok"])

    with tab1:
        df_kredit = pd.read_sql_query("SELECT total_hutang, dp, harga_modal, (dp + total_hutang) - harga_modal as laba FROM kredit k JOIN produk p ON k.produk_id = p.id", conn)
        df_cash = pd.read_sql_query("SELECT total_harga as pendapatan, laba FROM transaksi_cash", conn)
        
        tot_pen_kredit = df_kredit['dp'].sum() + df_kredit['total_hutang'].sum() if not df_kredit.empty else 0
        tot_laba_kredit = df_kredit['laba'].sum() if not df_kredit.empty else 0
        
        tot_pen_cash = df_cash['pendapatan'].sum() if not df_cash.empty else 0
        tot_laba_cash = df_cash['laba'].sum() if not df_cash.empty else 0
        
        total_transaksi = len(df_kredit) + len(df_cash)
        total_pendapatan = tot_pen_kredit + tot_pen_cash
        total_laba = tot_laba_kredit + tot_laba_cash
        margin = (total_laba / total_pendapatan * 100) if total_pendapatan > 0 else 0

        html = '<div class="metric-grid">'
        html += metric_card("Total Transaksi", f"{total_transaksi}", "card-blue")
        html += metric_card("Total Pendapatan", format_rp(total_pendapatan), "card-purple")
        html += metric_card("Total Laba", format_rp(total_laba), "card-green")
        html += metric_card("Margin Profit", f"{margin:.1f}%", "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("**🏆 Distribusi Laba per Produk**")
        df_g = pd.read_sql_query("""
            SELECT produk, SUM(laba) as total_laba FROM (
                SELECT p.nama as produk, ((k.dp + k.total_hutang) - p.harga_modal) as laba 
                FROM kredit k JOIN produk p ON k.produk_id = p.id
                UNION ALL
                SELECT p.nama as produk, t.laba as laba 
                FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
            ) GROUP BY produk ORDER BY total_laba DESC LIMIT 10
        """, conn)
        
        if not df_g.empty:
            chart = alt.Chart(df_g).mark_bar(cornerRadiusTopRight=8, cornerRadiusBottomRight=8).encode(
                x=alt.X('total_laba:Q', title='Laba (Rp)'), y=alt.Y('produk:N', sort='-x', title=''),
                color=alt.Color('total_laba:Q', scale=alt.Scale(scheme='reds'), legend=None)
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)

        st.markdown('<div class="section-header"><h3>✏️ Edit / Hapus Transaksi Terjual (Kredit)</h3></div>', unsafe_allow_html=True)
        
        df_kredit_all = pd.read_sql_query("""
            SELECT k.id, c.nama as customer, p.nama as produk, k.harga_cash, k.dp, k.pokok_hutang,
                   k.total_hutang, k.sisa_hutang, k.status, k.jatuh_tempo, k.tenor, k.cicilan_bulan
            FROM kredit k 
            JOIN customer c ON k.customer_id = c.id 
            JOIN produk p ON k.produk_id = p.id
            ORDER BY k.id DESC
        """, conn)
        st.dataframe(df_kredit_all, use_container_width=True, hide_index=True)

        if not df_kredit_all.empty:
            opsi_kredit = {f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})": r['id'] for _, r in df_kredit_all.iterrows()}
            pilih_kredit = st.selectbox("🔍 Pilih Transaksi Terjual", list(opsi_kredit.keys()))
            kid_edit = opsi_kredit[pilih_kredit]
            detail_k = df_kredit_all[df_kredit_all['id'] == kid_edit].iloc[0]

            with st.form("form_edit_kredit"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    e_status = st.selectbox("Status", ["Berjalan", "Lunas", "Batal"], index=["Berjalan", "Lunas", "Batal"].index(detail_k['status']) if detail_k['status'] in ["Berjalan", "Lunas", "Batal"] else 0)
                    e_jatuh_tempo = st.date_input("Jatuh Tempo", value=pd.to_datetime(detail_k['jatuh_tempo']).date())
                with c2:
                    e_harga_cash = st.number_input("Harga Cash (Rp)", value=float(detail_k['harga_cash']), step=10000.0)
                    e_dp = st.number_input("DP Dibayar (Rp)", value=float(detail_k['dp']), step=10000.0)
                    e_pokok = st.number_input("Pokok Hutang (Rp)", value=float(detail_k['pokok_hutang']), step=10000.0)
                with c3:
                    e_total = st.number_input("Total Hutang (Rp)", value=float(detail_k['total_hutang']), step=10000.0)
                    e_cicilan = st.number_input("Cicilan/Bulan (Rp)", value=float(detail_k['cicilan_bulan']), step=10000.0)
                    e_tenor = st.number_input("Tenor (Bulan)", value=int(detail_k['tenor']), step=1)
                    e_sisa = st.number_input("Sisa Hutang (Rp)", value=float(detail_k['sisa_hutang']), step=10000.0)
                
                st.info("⚠️ **Perhatian:** Menghapus transaksi terjual akan mengembalikan stok produk (+1) dan **menghapus semua riwayat pembayaran** untuk transaksi ini.")
                
                btn_edit = st.form_submit_button("💾 Simpan Perubahan")
                btn_hapus = st.form_submit_button("🗑️ Hapus Transaksi (Kembalikan Stok)")

                if btn_edit:
                    if e_status == "Lunas": e_sisa = 0.0
                    try:
                        c.execute("""UPDATE kredit SET status=?, jatuh_tempo=?, harga_cash=?, dp=?, pokok_hutang=?, total_hutang=?, sisa_hutang=?, cicilan_bulan=?, tenor=? WHERE id=?""",
                                  (e_status, e_jatuh_tempo.strftime("%Y-%m-%d"), e_harga_cash, e_dp, e_pokok, e_total, e_sisa, e_cicilan, e_tenor, kid_edit))
                        conn.commit()
                        log_aksi(st.session_state.username, "EDIT_KREDIT", f"ID {kid_edit}")
                        flash("✅ Transaksi terjual berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")

                if btn_hapus:
                    try:
                        c.execute("UPDATE produk SET stok = stok + 1 WHERE id = (SELECT produk_id FROM kredit WHERE id=?)", (kid_edit,))
                        c.execute("DELETE FROM pembayaran WHERE kredit_id=?", (kid_edit,))
                        c.execute("DELETE FROM jadwal_kustom WHERE kredit_id=?", (kid_edit,))
                        c.execute("DELETE FROM kredit WHERE id=?", (kid_edit,))
                        conn.commit()
                        log_aksi(st.session_state.username, "HAPUS_KREDIT", f"ID {kid_edit}")
                        flash("🗑️ Transaksi dihapus, stok dikembalikan, dan riwayat dibersihkan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
        else:
            st.info("Belum ada transaksi kredit untuk diedit.")

    with tab2:
        df_b = pd.read_sql_query("""
            SELECT p.id, p.kredit_id, p.tanggal, c.nama, p.jumlah_bayar, p.denda, p.keterangan
            FROM pembayaran p JOIN kredit k ON p.kredit_id = k.id JOIN customer c ON k.customer_id = c.id
            ORDER BY p.id DESC
        """, conn)
        if not df_b.empty:
            html = '<div class="metric-grid">'
            html += metric_card("Total Pemasukan", format_rp(df_b['jumlah_bayar'].sum()), "card-green")
            html += metric_card("Total Denda", format_rp(df_b['denda'].sum()), "card-orange")
            html += metric_card("Jumlah Transaksi", f"{len(df_b)}", "card-blue")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
            
            df_show_b = df_b.copy()
            df_show_b['jumlah_bayar'] = df_show_b['jumlah_bayar'].apply(format_rp)
            df_show_b['denda'] = df_show_b['denda'].apply(format_rp)
            st.dataframe(df_show_b[['tanggal', 'nama', 'jumlah_bayar', 'denda', 'keterangan']], use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-header"><h3>✏️ Edit / Hapus Pembayaran</h3></div>', unsafe_allow_html=True)
            st.info("💡 Menghapus atau mengedit pembayaran di sini akan otomatis mengembalikan/menyesuaikan Sisa Hutang pada akun Kredit terkait.")
            
            df_b['label'] = df_b.apply(lambda r: f"#{r['id']} - {r['nama']} - {format_rp(r['jumlah_bayar'])} ({r['tanggal']})", axis=1)
            opsi_bayar = dict(zip(df_b['label'], df_b['id']))
            pilih_bayar = st.selectbox("🔍 Pilih Data Pembayaran", list(opsi_bayar.keys()))
            bayar_id = opsi_bayar[pilih_bayar]
            detail_b = df_b[df_b['id'] == bayar_id].iloc[0]
            
            with st.form("form_edit_bayar"):
                col1, col2 = st.columns(2)
                with col1:
                    new_jumlah = st.number_input("Jumlah Bayar (Rp)", value=float(detail_b['jumlah_bayar']), step=50000.0)
                    new_denda = st.number_input("Denda (Rp)", value=float(detail_b['denda']), step=50000.0)
                with col2:
                    new_ket = st.text_input("Keterangan", value=detail_b['keterangan'] if detail_b['keterangan'] else "")
                    new_tgl = st.date_input("Tanggal Bayar", value=pd.to_datetime(detail_b['tanggal']).date())
                    
                colA, colB = st.columns(2)
                with colA:
                    submit_edit = st.form_submit_button("💾 Update Pembayaran")
                with colB:
                    submit_hapus = st.form_submit_button("🗑️ Hapus Pembayaran")
                    
                if submit_edit:
                    try:
                        c.execute("UPDATE pembayaran SET jumlah_bayar=?, denda=?, keterangan=?, tanggal=? WHERE id=?",
                                  (new_jumlah, new_denda, new_ket, new_tgl.strftime("%Y-%m-%d"), bayar_id))
                        recalculate_kredit(detail_b['kredit_id'])
                        conn.commit()
                        log_aksi(st.session_state.username, "EDIT_PEMBAYARAN", f"ID {bayar_id}")
                        flash("✅ Pembayaran diupdate & Sisa Hutang disesuaikan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                    
                if submit_hapus:
                    try:
                        c.execute("DELETE FROM pembayaran WHERE id=?", (bayar_id,))
                        recalculate_kredit(detail_b['kredit_id'])
                        conn.commit()
                        log_aksi(st.session_state.username, "HAPUS_PEMBAYARAN", f"ID {bayar_id}")
                        flash("🗑️ Pembayaran dihapus & Sisa Hutang disesuaikan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
        else:
            st.info("Belum ada pembayaran")

    with tab3:
        df_p = pd.read_sql_query("SELECT kategori, SUM(stok) as total_stok, COUNT(*) as jenis FROM produk GROUP BY kategori", conn)
        if not df_p.empty:
            chart = alt.Chart(df_p).mark_arc(innerRadius=60).encode(
                theta=alt.Theta('total_stok:Q'), color=alt.Color('kategori:N', scale=alt.Scale(scheme='set3')), tooltip=['kategori', 'total_stok', 'jenis']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

# ==================== 12. MODAL VS PROFIT ====================
elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Analisis Modal vs Profit</h1><p>Perbandingan HPP (Harga Pokok) vs Laba per Kategori</p></div>', unsafe_allow_html=True)

    kat_tersedia = pd.read_sql_query("SELECT DISTINCT kategori FROM produk ORDER BY kategori", conn)['kategori'].tolist()
    if not kat_tersedia:
        st.warning("Belum ada produk. Tambahkan produk terlebih dahulu.")
    else:
        default_kat = "Pakaian" if "Pakaian" in kat_tersedia else "Semua"
        opsi_kat = ["Semua"] + kat_tersedia
        kat_pilih = st.selectbox("🏷️ Filter Kategori", opsi_kat, index=opsi_kat.index(default_kat))

        q_base = """
            SELECT p.id, p.nama, p.kategori, p.harga_modal, COALESCE(p.markup_persen, 5) as markup_persen, p.stok, p.harga_jual,
                   (
                       COALESCE((SELECT SUM(k.dp + k.total_hutang) FROM kredit k WHERE k.produk_id = p.id), 0) +
                       COALESCE((SELECT SUM(t.total_harga) FROM transaksi_cash t WHERE t.produk_id = p.id), 0)
                   ) as total_revenue,
                   (
                       (SELECT COUNT(*) FROM kredit k WHERE k.produk_id = p.id) +
                       COALESCE((SELECT SUM(t.jumlah) FROM transaksi_cash t WHERE t.produk_id = p.id), 0)
                   ) as terjual
            FROM produk p
        """
        if kat_pilih == "Semua":
            df_data = pd.read_sql_query(q_base + " ORDER BY p.kategori, p.nama", conn)
        elif kat_pilih == "Pakaian":
            placeholders = ",".join(["?"] * len(PAKAIAN_KATEGORI))
            df_data = pd.read_sql_query(q_base + f" WHERE p.kategori IN ({placeholders}) ORDER BY p.kategori, p.nama", conn, params=tuple(PAKAIAN_KATEGORI))
        else:
            df_data = pd.read_sql_query(q_base + " WHERE p.kategori = ? ORDER BY p.nama", conn, params=(kat_pilih,))

        df_data['harga_modal'] = df_data['harga_modal'].fillna(0)
        df_data['markup_persen'] = df_data['markup_persen'].fillna(5)
        df_data['harga_cash']   = df_data.apply(lambda r: hitung_harga_cash(r['harga_modal'], r['markup_persen'], r.get('harga_jual')), axis=1)
        df_data['profit_unit']  = df_data['harga_cash'] - df_data['harga_modal']
        df_data['margin_persen'] = df_data.apply(lambda r: (r['profit_unit'] / r['harga_cash'] * 100) if r['harga_cash'] > 0 else 0, axis=1)
        df_data['total_modal']  = df_data['harga_modal'] * df_data['terjual']
        df_data['total_profit'] = df_data['total_revenue'] - df_data['total_modal']

        if kat_pilih in ["Semua", "Pakaian"]:
            belum = df_data[df_data['kategori'].isin(PAKAIAN_KATEGORI) & ((df_data['harga_jual'].isna()) | (df_data['harga_jual'] <= 0))]
            if not belum.empty:
                st.warning(f"⚠️ **{len(belum)} produk pakaian belum diisi harga jual.** Buka **📦 Stok Barang → ✏️ Edit Harga Jual Pakaian** untuk mengisi.")

        tot_modal   = df_data['total_modal'].sum()
        tot_revenue = df_data['total_revenue'].sum()
        tot_profit  = tot_revenue - tot_modal
        margin_all  = (tot_profit / tot_revenue * 100) if tot_revenue > 0 else 0
        tot_terjual = int(df_data['terjual'].sum())

        html = '<div class="metric-grid">'
        html += metric_card("💸 Total Modal (HPP)", format_rp(tot_modal), "card-dark")
        html += metric_card("💰 Total Penjualan", format_rp(tot_revenue), "card-blue")
        html += metric_card("💵 Total Profit", format_rp(tot_profit), "card-green")
        html += metric_card("📈 Margin Profit", f"{margin_all:.1f}%", "card-orange")
        html += metric_card("🛍️ Unit Terjual", f"{tot_terjual} unit", "card-purple")
        html += metric_card("📦 Sisa Stok", f"{int(df_data['stok'].sum())} unit", "card-pink")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        st.markdown('<div class="section-header"><h3>📊 Perbandingan Modal vs Profit per Produk (Top 10)</h3></div>', unsafe_allow_html=True)
        df_chart = df_data[df_data['terjual'] > 0].sort_values('total_profit', ascending=False).head(10).copy()

        if df_chart.empty:
            st.info(f"Belum ada produk terjual untuk kategori **{kat_pilih}**.")
        else:
            order = df_chart['nama'].tolist()
            df_long = df_chart.melt(id_vars=['nama'], value_vars=['total_modal', 'total_profit'], var_name='Tipe', value_name='Nilai')
            df_long['Tipe'] = df_long['Tipe'].map({'total_modal': '💸 Modal (HPP)', 'total_profit': '💵 Profit'})

            chart = alt.Chart(df_long).mark_bar(cornerRadiusTopRight=6, cornerRadiusTopLeft=6).encode(
                x=alt.X('nama:N', sort=order, title='Produk'), xOffset=alt.XOffset('Tipe:N', sort=['💸 Modal (HPP)', '💵 Profit']),
                y=alt.Y('Nilai:Q', title='Rupiah (Rp)'), color=alt.Color('Tipe:N', scale=alt.Scale(domain=['💸 Modal (HPP)', '💵 Profit'], range=['#e74c3c', '#2ecc71']), legend=alt.Legend(orient='top', title=None)),
                tooltip=['nama', 'Tipe', alt.Tooltip('Nilai:Q', format=',.0f')]
            ).properties(height=420)
            st.altair_chart(chart, use_container_width=True)

        st.markdown('<div class="section-header"><h3>📋 Detail Modal vs Profit per Produk</h3></div>', unsafe_allow_html=True)
        df_show = df_data.copy()
        df_show['harga_jual_label'] = df_show.apply(lambda r: format_rp(r['harga_jual']) if (r['harga_jual'] and r['harga_jual'] > 0) else "—", axis=1)
        df_show = df_show.rename(columns={'nama': 'Produk', 'kategori': 'Kategori', 'harga_modal': 'Modal/Unit', 'markup_persen': 'Markup', 'harga_cash': 'Harga Cash', 'harga_jual_label': 'Harga Jual', 'profit_unit': 'Profit/Unit', 'margin_persen': 'Margin %', 'terjual': 'Terjual', 'total_modal': 'Total Modal', 'total_profit': 'Total Profit', 'total_revenue': 'Total Revenue', 'stok': 'Stok'})
        for col in ['Modal/Unit', 'Harga Cash', 'Profit/Unit', 'Total Modal', 'Total Revenue', 'Total Profit']: df_show[col] = df_show[col].apply(format_rp)
        df_show['Margin %'] = df_show['Margin %'].apply(lambda x: f"{x:.1f}%")
        df_show['Markup']   = df_show['Markup'].apply(lambda x: f"{x:.0f}%")
        st.dataframe(df_show[['Produk', 'Kategori', 'Modal/Unit', 'Harga Jual', 'Harga Cash', 'Profit/Unit', 'Margin %', 'Markup', 'Terjual', 'Total Modal', 'Total Revenue', 'Total Profit', 'Stok']], use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header"><h3>🏷️ Ringkasan per Kategori</h3></div>', unsafe_allow_html=True)
        df_kat = df_data.groupby('kategori', as_index=False).agg(jenis_produk=('id', 'count'), total_terjual=('terjual', 'sum'), total_modal=('total_modal', 'sum'), total_revenue=('total_revenue', 'sum'), total_profit=('total_profit', 'sum'))
        df_kat['margin_%'] = df_kat.apply(lambda r: (r['total_profit'] / r['total_revenue'] * 100) if r['total_revenue'] > 0 else 0, axis=1)

        def highlight_pakaian(row):
            if row['Kategori'] in PAKAIAN_KATEGORI: return ['background-color: #fff3cd; font-weight: bold'] * len(row)
            return [''] * len(row)

        df_kat_show = df_kat.copy()
        for col in ['total_modal', 'total_revenue', 'total_profit']: df_kat_show[col] = df_kat_show[col].apply(format_rp)
        df_kat_show['margin_%'] = df_kat_show['margin_%'].apply(lambda x: f"{x:.1f}%")
        df_kat_show = df_kat_show.rename(columns={'kategori': 'Kategori', 'jenis_produk': 'Jenis Produk', 'total_terjual': 'Terjual', 'total_modal': 'Total Modal', 'total_revenue': 'Total Revenue', 'total_profit': 'Total Profit', 'margin_%': 'Margin'})
        st.dataframe(df_kat_show.style.apply(highlight_pakaian, axis=1), use_container_width=True, hide_index=True)
        st.caption("💡 Baris sub-kategori **Pakaian** (Atasan/Bawahan/Dress/Outerwear/Batik) disorot kuning.")

        st.markdown('<div class="section-header"><h3>📊 Perbandingan per Kategori</h3></div>', unsafe_allow_html=True)
        df_kat_long = df_kat.melt(id_vars=['kategori'], value_vars=['total_modal', 'total_profit'], var_name='Tipe', value_name='Nilai')
        df_kat_long['Tipe'] = df_kat_long['Tipe'].map({'total_modal': '💸 Modal', 'total_profit': '💵 Profit'})
        chart2 = alt.Chart(df_kat_long).mark_bar(cornerRadiusTopRight=8, cornerRadiusTopLeft=8).encode(
            x=alt.X('kategori:N', title='Kategori'), xOffset='Tipe:N', y=alt.Y('Nilai:Q', title='Rupiah'),
            color=alt.Color('Tipe:N', scale=alt.Scale(domain=['💸 Modal', '💵 Profit'], range=['#e74c3c', '#2ecc71']), legend=alt.Legend(orient='top', title=None)),
            tooltip=['kategori', 'Tipe', alt.Tooltip('Nilai:Q', format=',.0f')]
        ).properties(height=350)
        st.altair_chart(chart2, use_container_width=True)

# ==================== 13. BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["🗄️ Backup DB", "📤 Ekspor CSV", "📥 Impor CSV", "⚠️ Hapus Data"])

    with tab1:
        st.markdown("### 🗄️ Backup Database")
        st.info("💡 **PENTING:** Sistem sekarang menyimpan database **tepat di folder tempat Anda meletakkan file `app.py`**. File bernama `toko_kredit.db` tidak akan hilang meskipun Anda menutup aplikasi atau memindahkan foldernya.")
        st.success(f"📁 Lokasi Database saat ini: `{DB_PATH}`")
        st.success(f"📁 Lokasi Folder Backup: `{BACKUP_DIR}` (Sistem otomatis mencadangkan setiap hari)")
        
        conn.commit()
        with open(DB_PATH, 'rb') as f:
            st.download_button("💾 Download Backup DB ke Komputer", f.read(), f"backup_toko_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", "application/octet-stream")

    with tab2:
        tabel = st.selectbox("Pilih Data", ["Produk", "Customer", "Kredit", "Transaksi Masuk", "Pembayaran", "Log Aktivitas", "Pengaturan"])
        map_tabel = {"Produk": "produk", "Customer": "customer", "Kredit": "kredit", "Transaksi Masuk": "transaksi_in", "Pembayaran": "pembayaran", "Log Aktivitas": "log_aktivitas", "Pengaturan": "pengaturan"}
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
            tpl = pd.DataFrame(columns=["nama", "kategori", "harga_modal", "stok"]).to_csv(index=False).encode()
            st.download_button("📥 Template Produk", tpl, "template_produk.csv", "text/csv")
        else:
            st.markdown("Format: `nama, telepon, alamat`")
            tpl = pd.DataFrame(columns=["nama", "telepon", "alamat"]).to_csv(index=False).encode()
            st.download_button("📥 Template Customer", tpl, "template_customer.csv", "text/csv")

        f = st.file_uploader(f"Upload CSV {jenis}", type=["csv"])
        if f is not None:
            try:
                df_imp = pd.read_csv(f)
                st.dataframe(df_imp.head(), use_container_width=True)
                if st.button("✅ Proses Impor"):
                    try:
                        if jenis == "Produk":
                            for _, r in df_imp.iterrows():
                                c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,0,NULL)", (r['nama'], r['kategori'], r['harga_modal'], r['stok']))
                        else:
                            for _, r in df_imp.iterrows():
                                c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (r['nama'], r['telepon'], r['alamat']))
                        conn.commit()
                        log_aksi(st.session_state.username, "IMPOR", f"{jenis}: {len(df_imp)} baris")
                        flash(f"✅ Berhasil impor {len(df_imp)} data! (Isi harga jual pakaian di menu Stok Barang)", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal impor: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    with tab4:
        st.markdown("### ⚠️ Hapus Data (Gunakan dengan Hati-hati)")
        st.warning("Fitur ini berguna jika Anda ingin memulai dari nol (menghapus semua data transaksi, customer, dan produk), namun akun login (users) dan pengaturan toko tetap aman.")
        
        konfirmasi = st.text_input("Ketik **HAPUS SEMUA DATA** untuk mengonfirmasi:")
        if st.button("🗑️ Hapus Semua Data Transaksi & Master"):
            if konfirmasi == "HAPUS SEMUA DATA":
                try:
                    c.execute("DELETE FROM pembayaran")
                    c.execute("DELETE FROM kredit")
                    c.execute("DELETE FROM transaksi_cash")
                    c.execute("DELETE FROM transaksi_in")
                    c.execute("DELETE FROM customer")
                    c.execute("DELETE FROM produk")
                    c.execute("DELETE FROM log_aktivitas")
                    c.execute("DELETE FROM jadwal_kustom")
                    conn.commit()
                    log_aksi(st.session_state.username, "HAPUS_SEMUA_DATA", "Data di-reset")
                    flash("🗑️ Seluruh data berhasil dihapus. Aplikasi bersih seperti baru!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")
            else:
                st.error("❌ Konfirmasi salah. Data tidak dihapus.")

# ==================== 14. MANAJEMEN USER ====================
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
                        c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", (u, hash_password(p), n, r))
                        conn.commit()
                        flash(f"✅ User {u} ditambahkan!", "success")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Username sudah ada")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                else:
                    st.warning("Semua field wajib diisi")

    st.markdown('<div class="section-header"><h3>📋 Daftar User</h3></div>', unsafe_allow_html=True)
    df_u = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users", conn)
    st.dataframe(df_u, use_container_width=True, hide_index=True)

    opsi = {f"{r['username']} ({r['nama_lengkap']})": r['id'] for _, r in df_u.iterrows()}
    pilih_u = st.selectbox("Pilih User", list(opsi.keys()))
    uid = opsi[pilih_u]
    current = c.execute("SELECT aktif FROM users WHERE id=?", (uid,)).fetchone()[0]

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{'🚫 Nonaktifkan' if current else '✅ Aktifkan'}"):
            try:
                c.execute("UPDATE users SET aktif=? WHERE id=?", (0 if current else 1, uid))
                conn.commit()
                flash("Status diubah!", "success")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Gagal: {e}")
    with col2:
        if uid != 1:
            if st.button("🗑️ Hapus User"):
                try:
                    c.execute("DELETE FROM users WHERE id=?", (uid,))
                    conn.commit()
                    flash("User dihapus!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

# ==================== 15. LOG AKTIVITAS ====================
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas Sistem</h1></div>', unsafe_allow_html=True)
    df_log = pd.read_sql_query("SELECT * FROM log_aktivitas ORDER BY id DESC LIMIT 200", conn)
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Log CSV", csv, "log_aktivitas.csv", "text/csv")
    else:
        st.info("Belum ada aktivitas")

# ==================== FALLBACK ====================
else:
    st.warning("⚠️ Menu tidak tersedia untuk role Anda.")
