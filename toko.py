import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import json
from datetime import datetime, timedelta
from urllib.parse import quote
import altair as alt
import streamlit.components.v1 as components

# ==================== KONFIGURASI ====================
st.set_page_config(page_title="GRACE'S STORE (CASH & CREDIT)", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4); }
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

# Data Toko (dipakai di invoice)
TOKO = {
    "nama": "GRACE'S ELECTRONIC",
    "alamat": "Jl. Barong Tongkok, Kutai Barat",
    "telepon": "0822-9954-8411",
    "nib": "1234567890123",
}

def is_pakaian(kat):
    return kat in PAKAIAN_KATEGORI

# ==================== DATABASE ====================
DB_PATH = os.path.join(os.getcwd(), "toko_kredit.db")

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

conn = get_connection()
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS produk (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_cash (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, harga_jual_satuan REAL, total_harga REAL, uang_bayar REAL, kembalian REAL, laba REAL, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customer (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, telepon TEXT, alamat TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS kredit (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, produk_id INTEGER, harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, tenor INTEGER, cicilan_bulan REAL, sisa_hutang REAL, jatuh_tempo TEXT, status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS pembayaran (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, jumlah_bayar REAL, denda REAL, tanggal TEXT, keterangan TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, nama_lengkap TEXT, role TEXT, aktif INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS log_aktivitas (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, aksi TEXT, detail TEXT, waktu TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS pengaturan (kunci TEXT PRIMARY KEY, nilai TEXT, keterangan TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS draf_kredit (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, customer_nama TEXT, customer_telepon TEXT, produk_id INTEGER, produk_nama TEXT, harga_cash REAL, dp_persen REAL, dp REAL, bunga_persen REAL, tenor INTEGER, pokok_hutang REAL, total_hutang REAL, cicilan_bulan REAL, catatan TEXT, tanggal_dibuat TEXT, dibuat_oleh TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS invoice_custom (id INTEGER PRIMARY KEY AUTOINCREMENT, nomor_invoice TEXT UNIQUE, customer_nama TEXT, customer_telepon TEXT, customer_alamat TEXT, items_json TEXT, subtotal REAL, diskon_persen REAL, diskon_nominal REAL, pajak_persen REAL, pajak_nominal REAL, total REAL, metode_bayar TEXT, catatan TEXT, tanggal TEXT, dibuat_oleh TEXT)''')
conn.commit()

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

DEFAULT_PENGATURAN = {
    "markup_default_persen":     ("5.0",   "Markup default (%) untuk produk non-pakaian"),
    "bunga_flat_6bln_persen":    ("40.0",  "Bunga flat per 6 bulan (%) untuk kredit"),
    "dp_minimal_persen":         ("20.0",  "DP minimal (%) dari harga cash"),
    "denda_per_hari_persen":     ("1.0",   "Denda keterlambatan per hari (%) dari cicilan"),
    "tenor_options":             ("1,2,3,6,12,18,24", "Pilihan tenor (bulan)"),
}
for k, (v, ket) in DEFAULT_PENGATURAN.items():
    c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai, keterangan) VALUES (?,?,?)", (k, v, ket))
conn.commit()

# ==================== HELPER ====================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def format_rp(n):
    try:
        return f"Rp {float(n):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"

def get_pengaturan(kunci, default=None):
    key = f"_setting_{kunci}"
    if key in st.session_state:
        return st.session_state[key]
    row = c.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (kunci,)).fetchone()
    val = row[0] if row else default
    st.session_state[key] = val
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

def hitung_harga_cash(harga_modal, markup_persen, harga_jual):
    if harga_jual and float(harga_jual) > 0:
        return float(harga_jual)
    mk = markup_persen if markup_persen is not None else get_pengaturan_float("markup_default_persen", 5.0)
    return round(float(harga_modal) * (1 + float(mk) / 100), -2)

def recalculate_kredit(kredit_id):
    row = c.execute("SELECT total_hutang FROM kredit WHERE id=?", (kredit_id,)).fetchone()
    if not row: return
    res = c.execute("SELECT COALESCE(SUM(jumlah_bayar - denda), 0) FROM pembayaran WHERE kredit_id=?", (kredit_id,)).fetchone()
    new_sisa = max(row[0] - res[0], 0)
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
        bayar = sisa if (i == int(tenor) or sisa <= float(cicilan_bulan)) else float(cicilan_bulan)
        sisa = max(sisa - bayar, 0)
        schedule.append({"ke": i, "jatuh_tempo": tgl.strftime("%d-%m-%Y"), "angsuran": bayar, "sisa": sisa})
    return schedule

# Seed admin
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)",
              ("admin", hash_password("admin123"), "Administrator", "admin"))
    conn.commit()

# Seed produk
def seed_produk():
    c.execute("SELECT COUNT(*) FROM produk")
    if c.fetchone()[0] == 0:
        data = [
            ("iPhone 17 256GB", "Gadget", 19046700, 10), ("iPhone 17 PRO MAX 256GB", "Gadget", 22856200, 10),
            ("Galaxy S26 Ultra 256GB", "Gadget", 23332400, 10), ("Galaxy S26 256GB", "Gadget", 15713300, 10),
            ("Samsung A07 4/128 Black", "Gadget", 2300000, 10),
            ("Tunik Lop Top", "Atasan", 80000, 1), ("Mini Dress", "Dress", 50000, 2),
            ("Batik Premium", "Batik", 60000, 5), ("Outer", "Outerwear", 70000, 2),
        ]
        c.executemany("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", data)
        conn.commit()
seed_produk()

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
        st.info("🔑 Default: **admin** / **admin123**")
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
        "📤 Kredit Baru", "📝 Draf Kredit", "💰 Pembayaran Cicilan", "🖨️ Cetak Slip Kredit",
        "🧾 Invoice Baru", "👥 Data Customer", "📦 Stok Barang", "🚨 Overdue & Denda",
        "🔔 Alert & Reminder", "📊 Laporan & Analitik", "👕 Modal vs Profit", "💾 Backup, Cetak & Impor",
    ]
    if st.session_state.role == "admin":
        menu_list.extend(["⚙️ Pengaturan Owner", "👤 Manajemen User", "📝 Log Aktivitas"])
    pilihan = st.selectbox("📋 Menu", menu_list)
    st.markdown("---")
    if st.button("🚪 Logout"):
        log_aksi(st.session_state.username, "LOGOUT")
        for k in ["logged_in", "username", "nama", "role"]:
            st.session_state[k] = False if k == "logged_in" else ""
        for k in list(st.session_state.keys()):
            if k.startswith("_setting_"):
                st.session_state.pop(k, None)
        st.rerun()

show_flash()

# ==================== PENGATURAN OWNER ====================
if pilihan == "⚙️ Pengaturan Owner" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Owner</h1><p>Nilai default transaksi baru</p></div>', unsafe_allow_html=True)
    st.info("💡 Nilai default — tetap bisa diubah manual per transaksi.")

    st.markdown('<div class="section-header"><h3>💰 Markup Default</h3></div>', unsafe_allow_html=True)
    markup_val = st.number_input("Markup default non-pakaian (%)", min_value=0.0, max_value=500.0, value=get_pengaturan_float("markup_default_persen", 5.0), step=1.0)
    if st.button("💾 Simpan Markup"):
        set_pengaturan("markup_default_persen", f"{markup_val:.2f}")
        log_aksi(st.session_state.username, "SET_MARKUP", str(markup_val))
        flash(f"✅ Markup: {markup_val}%", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>💳 Bunga Default</h3></div>', unsafe_allow_html=True)
    bunga_val = st.number_input("Bunga flat per 6 bulan (%)", min_value=0.0, max_value=200.0, value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0)
    st.caption(f"⚠️ Bunga ini = **{bunga_val/6:.2f}% per bulan** = **{bunga_val*2:.1f}% per tahun**. OJK merekomendasikan ≤ 3%/bulan untuk pembiayaan.")
    if st.button("💾 Simpan Bunga"):
        set_pengaturan("bunga_flat_6bln_persen", f"{bunga_val:.2f}")
        log_aksi(st.session_state.username, "SET_BUNGA", str(bunga_val))
        flash(f"✅ Bunga: {bunga_val}%", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>🪙 DP Minimal</h3></div>', unsafe_allow_html=True)
    dp_val = st.number_input("DP minimal (%)", min_value=0.0, max_value=100.0, value=get_pengaturan_float("dp_minimal_persen", 20.0), step=1.0)
    if st.button("💾 Simpan DP"):
        set_pengaturan("dp_minimal_persen", f"{dp_val:.2f}")
        flash(f"✅ DP minimal: {dp_val}%", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>⏰ Denda</h3></div>', unsafe_allow_html=True)
    denda_val = st.number_input("Denda per hari (%)", min_value=0.0, max_value=20.0, value=get_pengaturan_float("denda_per_hari_persen", 1.0), step=0.1, format="%.2f")
    if st.button("💾 Simpan Denda"):
        set_pengaturan("denda_per_hari_persen", f"{denda_val:.2f}")
        flash(f"✅ Denda: {denda_val}%/hari", "success")
        st.rerun()

    st.markdown('<div class="section-header"><h3>📅 Tenor</h3></div>', unsafe_allow_html=True)
    tenor_val = st.text_input("Tenor (bulan, pisah koma)", value=get_pengaturan("tenor_options", "1,2,3,6,12,18,24"))
    if st.button("💾 Simpan Tenor"):
        try:
            _ = [int(x.strip()) for x in tenor_val.split(",") if x.strip()]
            set_pengaturan("tenor_options", tenor_val)
            flash(f"✅ Tenor: {tenor_val}", "success")
            st.rerun()
        except Exception:
            st.error("Format tidak valid")

    st.markdown('<div class="section-header"><h3>📋 Pengaturan Aktif</h3></div>', unsafe_allow_html=True)
    st.dataframe(pd.read_sql_query("SELECT kunci, nilai FROM pengaturan ORDER BY kunci", conn), use_container_width=True, hide_index=True)

# ==================== DASHBOARD ====================
elif pilihan == "🏠 Dashboard":
    st.markdown(f'<div class="main-header"><h1>🏠 Dashboard</h1><p>Selamat datang, <b>{st.session_state.nama}</b> 👋</p></div>', unsafe_allow_html=True)

    q = lambda s: c.execute(s).fetchone()[0]
    total_produk = q("SELECT COUNT(*) FROM produk")
    total_stok = q("SELECT COALESCE(SUM(stok),0) FROM produk")
    total_customer = q("SELECT COUNT(*) FROM customer")
    kredit_aktif = q("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'")
    kredit_lunas = q("SELECT COUNT(*) FROM kredit WHERE status='Lunas'")
    total_piutang = q("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'")
    tgl = datetime.now().strftime("%Y-%m-%d")
    overdue = q(f"SELECT COUNT(*) FROM kredit WHERE status='Berjalan' AND jatuh_tempo < '{tgl}'")
    pend_kredit = q("SELECT COALESCE(SUM(dp + total_hutang),0) FROM kredit")
    pend_cash = q("SELECT COALESCE(SUM(total_harga),0) FROM transaksi_cash")
    laba_kredit = q("SELECT COALESCE(SUM((k.dp + k.total_hutang) - p.harga_modal),0) FROM kredit k JOIN produk p ON k.produk_id = p.id")
    laba_cash = q("SELECT COALESCE(SUM(laba),0) FROM transaksi_cash")
    draf = q("SELECT COUNT(*) FROM draf_kredit")
    inv = q("SELECT COUNT(*) FROM invoice_custom")

    html = '<div class="metric-grid">'
    html += metric_card("📦 Total Produk", f"{total_produk} item", "card-blue")
    html += metric_card("🎒 Total Stok", f"{total_stok} unit", "card-purple")
    html += metric_card("👥 Customer", f"{total_customer} orang", "card-green")
    html += metric_card("💳 Kredit Aktif", f"{kredit_aktif} akun", "card-orange")
    html += metric_card("💰 Piutang", format_rp(total_piutang), "card-dark")
    html += metric_card("💵 Pendapatan", format_rp(pend_kredit + pend_cash), "card-blue")
    html += metric_card("💵 Laba", format_rp(laba_kredit + laba_cash), "card-green")
    html += metric_card("⚠️ Overdue", f"{overdue} akun", "card-pink")
    html += metric_card("✅ Lunas", f"{kredit_lunas} akun", "card-green")
    html += metric_card("📝 Draf Kredit", f"{draf} draf", "card-orange")
    html += metric_card("🧾 Invoice Custom", f"{inv} invoice", "card-purple")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown('<div class="section-header"><h3>⏰ Jatuh Tempo 7 Hari</h3></div>', unsafe_allow_html=True)
    tgl7 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    df_dekat = pd.read_sql_query("SELECT c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo FROM kredit k JOIN customer c ON k.customer_id = c.id WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ? ORDER BY k.jatuh_tempo", conn, params=(tgl, tgl7))
    if not df_dekat.empty:
        st.dataframe(df_dekat, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Tidak ada jatuh tempo minggu ini")

# ==================== INPUT PRODUK & SKEMA ====================
elif pilihan == "🧮 Input Produk & Skema":
    st.markdown('<div class="main-header"><h1>🧮 Input Produk & Skema</h1></div>', unsafe_allow_html=True)
    markup_default = get_pengaturan_float("markup_default_persen", 5.0)
    bunga_flat = get_pengaturan_float("bunga_flat_6bln_persen", 40.0)
    dp_min_persen = get_pengaturan_float("dp_minimal_persen", 20.0)
    tenor_list = get_tenor_list()

    with st.expander("➕ Tambah Produk", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nama_produk = st.text_input("Nama")
            kategori = st.selectbox("Kategori", SEMUA_KATEGORI)
        with col2:
            harga_modal = st.number_input("Harga Modal", min_value=0.0, step=1000.0)
            stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
        if is_pakaian(kategori):
            harga_jual = st.number_input("Harga Jual (manual)", min_value=0.0, step=1000.0)
            markup_persen = 0
        else:
            markup_persen = st.number_input("Markup (%)", min_value=0.0, max_value=500.0, value=markup_default, step=1.0)
            harga_jual = None
        if st.button("💾 Simpan Produk"):
            if nama_produk and harga_modal > 0:
                try:
                    c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,?,?)",
                              (nama_produk, kategori, harga_modal, stok_awal, markup_persen, harga_jual))
                    conn.commit()
                    flash(f"✅ {nama_produk} disimpan!", "success")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")

    st.markdown('<div class="section-header"><h3>⚙️ Simulasi Kredit</h3></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        modal_sim = st.number_input("Modal Simulasi", min_value=0.0, value=5000000.0, step=100000.0)
        dp_sim = st.slider(f"DP % (min {dp_min_persen:.0f}%)", int(dp_min_persen), 80, int(dp_min_persen), 5)
    with col2:
        tenor_sim = st.selectbox("Tenor", tenor_list, index=min(3, len(tenor_list)-1))
        bunga_sim = st.number_input(f"Bunga / 6bln (%)", min_value=0.0, value=bunga_flat, step=1.0)

    hc = round(modal_sim * (1 + markup_default/100), -2)
    dp = round(hc * dp_sim / 100, -2)
    rate = (bunga_sim / 100) / 6
    pokok = round(hc - dp, -2)
    total = round(pokok * (1 + rate * tenor_sim), -2)
    cicilan = round(total / tenor_sim, -2) if tenor_sim > 0 else 0
    laba = (dp + total) - modal_sim

    html = '<div class="metric-grid">'
    html += metric_card("Harga Cash", format_rp(hc), "card-blue")
    html += metric_card(f"DP {dp_sim}%", format_rp(dp), "card-purple")
    html += metric_card("Total Hutang", format_rp(total), "card-dark")
    html += metric_card("Laba", format_rp(laba), "card-green")
    html += metric_card(f"Cicilan {tenor_sim}x", format_rp(cicilan), "card-pink")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ==================== BARANG MASUK ====================
elif pilihan == "📥 Barang Masuk":
    st.markdown('<div class="main-header"><h1>📥 Barang Masuk</h1></div>', unsafe_allow_html=True)
    df_produk = pd.read_sql_query("SELECT id, nama, stok FROM produk ORDER BY nama", conn)
    if df_produk.empty:
        st.warning("Belum ada produk")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opsi = {f"{r['nama']} (stok: {r['stok']})": r['id'] for _, r in df_produk.iterrows()}
            pilih = st.selectbox("Produk", list(opsi.keys()))
        with col2:
            jumlah = st.number_input("Jumlah", min_value=1, step=1)
        if st.button("➕ Tambah Stok"):
            pid = opsi[pilih]
            c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)", (pid, jumlah, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah, pid))
            conn.commit()
            flash(f"✅ +{jumlah} unit!", "success")
            st.rerun()
        st.markdown('<div class="section-header"><h3>📜 Riwayat</h3></div>', unsafe_allow_html=True)
        st.dataframe(pd.read_sql_query("SELECT t.id, p.nama, t.jumlah, t.tanggal FROM transaksi_in t JOIN produk p ON t.produk_id = p.id ORDER BY t.id DESC LIMIT 20", conn), use_container_width=True, hide_index=True)

# ==================== JUAL CASH ====================
elif pilihan == "🛒 Jual Cash":
    st.markdown('<div class="main-header"><h1>🛒 Jual Cash</h1></div>', unsafe_allow_html=True)
    df_prod = pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok, COALESCE(markup_persen, 5) as markup_persen, harga_jual FROM produk WHERE stok > 0 ORDER BY nama", conn)
    if df_prod.empty:
        st.warning("Semua stok kosong")
    else:
        col1, col2 = st.columns([1.2, 1])
        with col1:
            opsi_prod = {f"{r['nama']} | Modal: {format_rp(r['harga_modal'])} | Stok: {r['stok']}": (r['id'], r['nama'], r['harga_modal'], r['markup_persen'], r['harga_jual'], r['stok']) for _, r in df_prod.iterrows()}
            pilih = st.selectbox("Produk", list(opsi_prod.keys()))
            id_p, nama_p, mod_p, mk_p, hj_p, stok_p = opsi_prod[pilih]
            default_price = hitung_harga_cash(mod_p, mk_p, hj_p)
            with st.form("cash_form"):
                st.info(f"Modal: **{format_rp(mod_p)}**")
                harga = st.number_input("Harga Jual (bisa diubah)", min_value=0.0, value=float(default_price), step=1000.0)
                qty = st.number_input("Qty", min_value=1, max_value=int(stok_p), value=1)
                total = harga * qty
                profit = (harga - mod_p) * qty
                st.markdown(f"### Total: **{format_rp(total)}**")
                st.success(f"📈 Profit: {format_rp(profit)}") if profit >= 0 else st.error(f"⚠️ Rugi: {format_rp(abs(profit))}")
                uang = st.number_input("Uang Diterima", min_value=0.0, value=float(total), step=10000.0)
                kembalian = uang - total
                if uang >= total:
                    st.info(f"Kembalian: **{format_rp(kembalian)}**")
                submit = st.form_submit_button("💳 Proses")
                if submit:
                    if uang < total:
                        st.error("Uang kurang")
                    else:
                        try:
                            c.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (qty, id_p))
                            c.execute("""INSERT INTO transaksi_cash (produk_id, jumlah, harga_jual_satuan, total_harga, uang_bayar, kembalian, laba, tanggal) 
                                         VALUES (?,?,?,?,?,?,?,?)""",
                                      (id_p, qty, harga, total, uang, kembalian, profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            flash(f"🎉 {nama_p} terjual {qty} unit!", "success")
                            st.session_state.balloons = True
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ {e}")
        with col2:
            st.markdown('<div class="section-header"><h3>Riwayat 5 Terakhir</h3></div>', unsafe_allow_html=True)
            df_riw = pd.read_sql_query("SELECT t.id, p.nama, t.jumlah, t.total_harga, t.laba, t.tanggal FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id ORDER BY t.id DESC LIMIT 5", conn)
            if not df_riw.empty:
                df_show = df_riw.drop(columns=['id']).copy()
                df_show['total_harga'] = df_show['total_harga'].apply(format_rp)
                df_show['laba'] = df_show['laba'].apply(format_rp)
                st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==================== KREDIT BARU ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Kredit Baru</h1></div>', unsafe_allow_html=True)
    bunga_default = get_pengaturan_float("bunga_flat_6bln_persen", 40.0)
    dp_min = get_pengaturan_float("dp_minimal_persen", 20.0)
    tenor_list = get_tenor_list()

    df_cust = pd.read_sql_query("SELECT id, nama FROM customer ORDER BY nama", conn)
    df_prod = pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok, COALESCE(markup_persen, 5) as markup_persen, harga_jual FROM produk WHERE stok > 0 ORDER BY nama", conn)

    if df_cust.empty or df_prod.empty:
        st.warning("⚠️ Butuh customer & produk stok > 0")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opsi_c = {r['nama']: r['id'] for _, r in df_cust.iterrows()}
            pilih_c = st.selectbox("Customer", list(opsi_c.keys()))
        with col2:
            opsi_p = {f"{r['nama']} (stok: {r['stok']})": (r['id'], r['nama'], r['kategori'], r['harga_modal'], r['markup_persen'], r['harga_jual']) for _, r in df_prod.iterrows()}
            pilih_p = st.selectbox("Produk", list(opsi_p.keys()))
        id_p, nama_p, kat_p, mod_p, mk_p, hj_p = opsi_p[pilih_p]

        if is_pakaian(kat_p) and (not hj_p or hj_p <= 0):
            st.error(f"❌ Harga jual **{nama_p}** belum diisi. Isi dulu di **📦 Stok Barang**.")
            st.stop()

        h_cash = hitung_harga_cash(mod_p, mk_p, hj_p)
        col_dp, col_t, col_b = st.columns(3)
        with col_dp:
            dp_persen = st.number_input(f"DP % (min {dp_min:.0f})", min_value=float(dp_min), max_value=100.0, value=float(dp_min), step=1.0)
        with col_t:
            tenor = st.selectbox("Tenor (bln)", tenor_list, index=min(3, len(tenor_list)-1))
        with col_b:
            bunga = st.number_input("Bunga / 6bln (%)", min_value=0.0, value=float(bunga_default), step=1.0)

        dp = round(h_cash * dp_persen / 100, -2)
        rate = (bunga / 100) / 6
        pokok = round(h_cash - dp, -2)
        total = round(pokok * (1 + rate * tenor), -2)
        cicilan = round(total / tenor, -2) if tenor > 0 else 0

        html = '<div class="metric-grid">'
        html += metric_card("Harga Cash", format_rp(h_cash), "card-blue")
        html += metric_card("DP", format_rp(dp), "card-purple")
        html += metric_card("Total Hutang", format_rp(total), "card-dark")
        html += metric_card(f"Cicilan {tenor}x", format_rp(cicilan), "card-pink")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        cek = c.execute("SELECT COUNT(*) FROM kredit WHERE customer_id=? AND status='Berjalan'", (opsi_c[pilih_c],)).fetchone()[0]
        if cek > 0:
            st.warning(f"⚠️ Customer punya {cek} kredit aktif")

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Proses Kredit"):
                tgl_k = datetime.now().strftime("%Y-%m-%d")
                tgl_t = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                try:
                    c.execute("""INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (opsi_c[pilih_c], id_p, h_cash, dp, pokok, total, tenor, cicilan, total, tgl_t, "Berjalan", tgl_k))
                    c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
                    conn.commit()
                    flash("🎉 Akad berhasil!", "success")
                    st.session_state.balloons = True
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ {e}")
        with colB:
            if st.button("📝 Simpan sebagai Draf"):
                try:
                    c.execute("""INSERT INTO draf_kredit (customer_id, customer_nama, produk_id, produk_nama, harga_cash, dp_persen, dp, bunga_persen, tenor, pokok_hutang, total_hutang, cicilan_bulan, tanggal_dibuat, dibuat_oleh) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (opsi_c[pilih_c], pilih_c, id_p, nama_p, h_cash, dp_persen, dp, bunga, tenor, pokok, total, cicilan, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.username))
                    conn.commit()
                    flash("📝 Draf tersimpan!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ {e}")

# ==================== DRAF KREDIT ====================
elif pilihan == "📝 Draf Kredit":
    st.markdown('<div class="main-header"><h1>📝 Draf Kredit</h1></div>', unsafe_allow_html=True)
    df_draf = pd.read_sql_query("SELECT * FROM draf_kredit ORDER BY id DESC", conn)
    if df_draf.empty:
        st.info("Belum ada draf. Buat di menu **📤 Kredit Baru**.")
    else:
        df_show = df_draf[['id', 'customer_nama', 'produk_nama', 'harga_cash', 'dp', 'total_hutang', 'cicilan_bulan', 'tenor']].copy()
        for col in ['harga_cash', 'dp', 'total_hutang', 'cicilan_bulan']:
            df_show[col] = df_show[col].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        opsi = {f"#{r['id']} - {r['customer_nama']} - {r['produk_nama']}": r['id'] for _, r in df_draf.iterrows()}
        pilih = st.selectbox("Pilih Draf", list(opsi.keys()))
        did = opsi[pilih]
        d = df_draf[df_draf['id'] == did].iloc[0]
        stok = c.execute("SELECT stok FROM produk WHERE id=?", (d['produk_id'],)).fetchone()
        stok = stok[0] if stok else 0

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Jadikan Akad", disabled=(stok <= 0)):
                try:
                    tgl_k = datetime.now().strftime("%Y-%m-%d")
                    tgl_t = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    cid = d['customer_id']
                    if cid is None or pd.isna(cid):
                        c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (d['customer_nama'], d['customer_telepon'] or "", ""))
                        conn.commit()
                        cid = c.lastrowid
                    c.execute("""INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (cid, d['produk_id'], d['harga_cash'], d['dp'], d['pokok_hutang'], d['total_hutang'], d['tenor'], d['cicilan_bulan'], d['total_hutang'], tgl_t, "Berjalan", tgl_k))
                    c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (d['produk_id'],))
                    c.execute("DELETE FROM draf_kredit WHERE id = ?", (did,))
                    conn.commit()
                    flash("🎉 Akad dari draf berhasil!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ {e}")
        with colB:
            if st.button("🗑️ Hapus Draf"):
                c.execute("DELETE FROM draf_kredit WHERE id = ?", (did,))
                conn.commit()
                flash("🗑️ Draf dihapus", "success")
                st.rerun()

# ==================== PEMBAYARAN CICILAN ====================
elif pilihan == "💰 Pembayaran Cicilan":
    st.markdown('<div class="main-header"><h1>💰 Pembayaran Cicilan</h1></div>', unsafe_allow_html=True)
    df_k = pd.read_sql_query("""SELECT k.id, c.nama as customer, p.nama as produk, k.sisa_hutang, k.cicilan_bulan, k.jatuh_tempo 
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id 
        WHERE k.status='Berjalan' ORDER BY k.jatuh_tempo ASC""", conn)
    if df_k.empty:
        st.success("✅ Tidak ada kredit aktif")
    else:
        df_k['label'] = df_k.apply(lambda r: f"#{r['id']} - {r['customer']} (Sisa: {format_rp(r['sisa_hutang'])})", axis=1)
        opsi = dict(zip(df_k['label'], df_k['id']))
        pilih = st.selectbox("Kredit", list(opsi.keys()))
        kid = opsi[pilih]
        d = df_k[df_k['id'] == kid].iloc[0]

        hari_telat = (datetime.now().date() - datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d").date()).days
        denda = hitung_denda(d['cicilan_bulan'], hari_telat)
        html = '<div class="metric-grid">'
        html += metric_card("Sisa Hutang", format_rp(d['sisa_hutang']), "card-dark")
        html += metric_card("Cicilan", format_rp(d['cicilan_bulan']), "card-blue")
        html += metric_card("Jatuh Tempo", d['jatuh_tempo'], "card-orange")
        html += metric_card("Hari Telat", f"{max(hari_telat,0)} hari", "card-pink" if hari_telat > 0 else "card-green")
        html += metric_card("Denda", format_rp(denda), "card-pink")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            bayar = st.number_input("Jumlah Bayar", min_value=0.0, value=float(d['cicilan_bulan'] + denda), step=50000.0)
        with col2:
            ket = st.text_input("Keterangan")
        if st.button("💳 Proses"):
            tagihan = d['sisa_hutang'] + denda
            if bayar <= 0 or bayar > tagihan:
                st.error(f"Bayar harus 1..{format_rp(tagihan)}")
            else:
                principal = max(bayar - denda, 0)
                sisa = max(round(d['sisa_hutang'] - principal, -2), 0)
                tgl_next = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                status = "Lunas" if sisa <= 0 else "Berjalan"
                try:
                    c.execute("INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan) VALUES (?,?,?,?,?)",
                              (kid, bayar, denda, datetime.now().strftime("%Y-%m-%d"), ket))
                    c.execute("UPDATE kredit SET sisa_hutang=?, jatuh_tempo=?, status=? WHERE id=?", (sisa, tgl_next, status, kid))
                    conn.commit()
                    if status == "Lunas":
                        flash(f"🎉 LUNAS! {format_rp(bayar)}", "success")
                        st.session_state.balloons = True
                    else:
                        flash(f"✅ Bayar {format_rp(bayar)}. Sisa {format_rp(sisa)}", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ {e}")

        st.markdown('<div class="section-header"><h3>Riwayat Pembayaran</h3></div>', unsafe_allow_html=True)
        df_riw = pd.read_sql_query("SELECT tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id DESC", conn, params=(kid,))
        if not df_riw.empty:
            df_riw['jumlah_bayar'] = df_riw['jumlah_bayar'].apply(format_rp)
            df_riw['denda'] = df_riw['denda'].apply(format_rp)
            st.dataframe(df_riw, use_container_width=True, hide_index=True)

# ==================== CETAK SLIP KREDIT (OJK-COMPLIANT) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit</h1><p>Perjanjian OJK-compliant + E-Materai + TTD Digital</p></div>', unsafe_allow_html=True)

    df_k = pd.read_sql_query("""SELECT k.id, c.nama as customer, p.nama as produk, k.status 
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id 
        ORDER BY k.id DESC""", conn)

    if df_k.empty:
        st.info("Belum ada kredit.")
    else:
        df_k['label'] = df_k.apply(lambda r: f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})", axis=1)
        opsi = dict(zip(df_k['label'], df_k['id']))
        pilih = st.selectbox("Transaksi Kredit", list(opsi.keys()))
        kid = opsi[pilih]

        d = pd.read_sql_query("""SELECT k.*, c.nama as cn, c.telepon, c.alamat, p.nama as pn 
            FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id WHERE k.id=?""",
            conn, params=(kid,)).iloc[0]

        metode = st.radio("Metode Bayar Angsuran", ["Tunai (Cash)", "Transfer Bank"], horizontal=True)
        denda_harian = get_pengaturan_float("denda_per_hari_persen", 1.0)

        tenor_asli = int(d['tenor'])
        total_hutang = float(d['total_hutang'])
        pokok_hutang = float(d['pokok_hutang'])
        bunga_total = total_hutang - pokok_hutang
        bunga_persen_bulan = (bunga_total / pokok_hutang * 100 / tenor_asli) if pokok_hutang > 0 else 0

        tanggal_kredit_str = d['tanggal_kredit'] if pd.notna(d['tanggal_kredit']) else datetime.now().strftime("%Y-%m-%d")
        schedule = build_jadwal_angsuran(total_hutang, d['cicilan_bulan'], tenor_asli, tanggal_kredit_str)
        rows_sched = "".join([
            f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='status-pending'>BELUM</span></td></tr>"
            for r in schedule
        ])

        # ==== KONDISIONAL E-MATERAI (UU 10/2020: > Rp5.000.000) ====
        total_kewajiban = total_hutang + float(d['dp'])
        wajib_materai = total_kewajiban > 5_000_000
        nomor_perjanjian = f"GRC/PJK/{datetime.now().strftime('%Y/%m')}/{kid:04d}"

        if wajib_materai:
            materai_html = f"""
            <div class="materai-box">
                <div class="lbl">⚠️ WAJIB E-MATERAI — UU No. 10/2020</div>
                <div class="isi">Nilai transaksi {format_rp(total_kewajiban)} &gt; Rp 5.000.000<br>
                Wajib dibubuhi <b>e-Materai Rp 10.000</b> dari Peruri (meterai.peruri.co.id)<br>
                <span class="materai-warn">[ Tempel gambar e-Materai di sini sebelum ditandatangani ]</span></div>
            </div>"""
        else:
            materai_html = f"""<div style="text-align:center; padding:5px; font-size:9px; color:#059669; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; margin:6px 0;">✓ Tidak wajib e-Materai (nilai {format_rp(total_kewajiban)} ≤ Rp 5.000.000)</div>"""

        invoice_html = f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8"><title>Perjanjian Kredit #{kid}</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Helvetica Neue',Arial,sans-serif; background:#e2e8f0; padding:20px 10px; color:#1a2b47; font-size:11px; }}
.page {{ max-width:820px; margin:0 auto; background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 8px 30px rgba(15,23,42,0.15); }}
.hdr {{ background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 70%,#1e40af 100%); color:#fff; padding:14px 22px; display:flex; justify-content:space-between; align-items:center; }}
.brand h1 {{ font-size:19px; font-weight:800; letter-spacing:1px; text-transform:uppercase; }}
.brand .tag {{ font-size:9.5px; color:#94a3b8; }}
.brand .addr {{ font-size:9px; color:#cbd5e1; margin-top:4px; }}
.title-box {{ text-align:right; }}
.badge-inv {{ display:inline-block; background:rgba(245,158,11,0.22); color:#fbbf24; padding:3px 10px; border-radius:12px; font-size:9px; font-weight:700; letter-spacing:1px; text-transform:uppercase; border:1px solid rgba(245,158,11,0.4); }}
.inv-no {{ font-size:11.5px; font-weight:700; margin-top:5px; }}
.inv-date {{ font-size:9px; color:#94a3b8; margin-top:2px; }}
.meta {{ display:flex; gap:14px; justify-content:space-between; padding:6px 22px; background:#f8fafc; border-bottom:1px solid #e2e8f0; font-size:9.5px; color:#475569; }}
.body {{ padding:10px 22px 12px; }}
.top-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px; }}
.sec {{ border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px; }}
.sec-title {{ font-size:9.5px; font-weight:800; color:#1e3a8a; text-transform:uppercase; letter-spacing:0.6px; padding-bottom:4px; margin-bottom:5px; border-bottom:1.5px solid #f1f5f9; }}
.kv {{ display:grid; grid-template-columns:78px 1fr; gap:3px 6px; font-size:10px; }}
.kv .k {{ color:#64748b; }}
.kv .v {{ color:#0f172a; font-weight:600; }}
.sched {{ border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; margin-bottom:8px; }}
.sched-h {{ padding:5px 8px; font-size:9px; font-weight:800; color:#fff; text-transform:uppercase; background:linear-gradient(90deg,#1e40af,#2563eb); }}
.sched table {{ width:100%; border-collapse:collapse; font-size:9.5px; }}
.sched th {{ background:#f8fafc; color:#475569; font-size:8.5px; padding:4px 6px; text-align:left; border-bottom:1px solid #e2e8f0; }}
.sched td {{ padding:4px 6px; border-bottom:1px solid #f1f5f9; }}
.sched .r {{ text-align:right; }} .sched .c {{ text-align:center; }}
.sched .total td {{ background:#f8fafc; font-weight:700; }}
.status-pending {{ display:inline-block; padding:1px 6px; border-radius:8px; background:#fef3c7; color:#92400e; font-size:8px; font-weight:700; }}
.materai-box {{ border:2px dashed #b91c1c; border-radius:10px; padding:10px; text-align:center; background:#fef2f2; margin:8px 0; }}
.materai-box .lbl {{ font-size:9px; font-weight:800; color:#b91c1c; text-transform:uppercase; letter-spacing:1px; }}
.materai-box .isi {{ margin-top:4px; font-size:9px; color:#7f1d1d; line-height:1.5; }}
.materai-warn {{ display:inline-block; margin-top:6px; padding:4px 12px; background:#fff; border:1px dashed #b91c1c; color:#b91c1c; font-weight:700; border-radius:4px; }}
.sig-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:8px; }}
.sig-card {{ border:2px dashed #1e3a8a; border-radius:10px; padding:10px 12px; background:linear-gradient(135deg,#f8fafc,#eff6ff); text-align:center; }}
.sig-card.customer {{ border-color:#b8956a; background:linear-gradient(135deg,#faf5ff,#f3e8ff); }}
.sig-title {{ font-size:9px; font-weight:800; text-transform:uppercase; letter-spacing:1.2px; color:#1e3a8a; margin-bottom:4px; }}
.sig-card.customer .sig-title {{ color:#b8956a; }}
.sig-verify {{ font-family:'Courier New',monospace; font-size:8px; color:#6b7280; margin-top:2px; }}
#sigCanvas {{ border:1.5px dashed #b8956a; border-radius:6px; background:#fff; width:100%; height:100px; cursor:crosshair; touch-action:none; display:block; }}
.sig-btn {{ background:#fef3c7; border:1px solid #f59e0b; color:#92400e; padding:3px 8px; border-radius:4px; font-size:8px; font-weight:700; cursor:pointer; margin-top:4px; }}
.ojk-box {{ border:1.5px solid #1e3a8a; border-radius:10px; padding:10px 14px; background:#f0f9ff; margin-bottom:8px; }}
.ojk-title {{ font-size:9.5px; font-weight:800; color:#1e3a8a; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; }}
.ojk-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:3px 14px; font-size:9px; color:#1e3a8a; }}
.terms-section {{ padding:10px 22px; background:#f9fafb; border-top:1px solid #e5e7eb; }}
.terms-title {{ font-family:Georgia,serif; font-size:9px; font-weight:700; color:#1a2b47; letter-spacing:1.4px; text-transform:uppercase; margin-bottom:4px; }}
.terms-list {{ counter-reset:item; list-style:none; display:grid; grid-template-columns:1fr 1fr; gap:3px 20px; font-size:9px; color:#4b5563; }}
.terms-list li {{ display:flex; gap:6px; line-height:1.5; }}
.footer {{ padding:8px 22px 12px; text-align:center; font-size:8.5px; color:#9ca3af; }}
@media print {{ @page {{ size:A4 portrait; margin:6mm; }} body {{ background:#fff; padding:0; }} .page {{ box-shadow:none; border-radius:0; max-width:100%; }} * {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
</style></head><body>
<div class="page">
<header class="hdr">
<div class="brand">
<h1>{TOKO['nama']}</h1>
<div class="tag">Cash &amp; Credit · Authorized Retailer</div>
<div class="addr">{TOKO['alamat']} • HP/WA: {TOKO['telepon']}<br>NIB: {TOKO['nib']}</div>
</div>
<div class="title-box">
<div class="badge-inv">Perjanjian Kredit</div>
<div class="inv-no">#GRC-INV-{kid}</div>
<div class="inv-date">No. Perjanjian: {nomor_perjanjian}</div>
<div class="inv-date">{datetime.now().strftime('%d %B %Y · %H:%M')} WITA</div>
</div>
</header>
<div class="meta">
<div>Status: <b style="color:#059669;">● {d['status'].upper()}</b></div>
<div>Metode: <b>{metode}</b></div>
<div>Bunga: <b>{bunga_persen_bulan:.2f}% / bln</b></div>
<div>Tenor: <b>{tenor_asli} bulan</b></div>
</div>
<div class="body">

<!-- IDENTITAS PIHAK -->
<div class="top-grid">
<div class="sec"><div class="sec-title">🏪 PIHAK PERTAMA (Kreditur)</div>
<div class="kv">
<div class="k">Nama Usaha</div><div class="v">{TOKO['nama']}</div>
<div class="k">Alamat</div><div class="v">{TOKO['alamat']}</div>
<div class="k">Telepon</div><div class="v">{TOKO['telepon']}</div>
<div class="k">NIB</div><div class="v">{TOKO['nib']}</div>
</div></div>
<div class="sec"><div class="sec-title">👤 PIHAK KEDUA (Debitur)</div>
<div class="kv">
<div class="k">Nama</div><div class="v">{d['cn']}</div>
<div class="k">Telepon</div><div class="v">{d['telepon'] or '-'}</div>
<div class="k">Alamat</div><div class="v">{d['alamat'] or '-'}</div>
<div class="k">No. Perjanjian</div><div class="v">{nomor_perjanjian}</div>
</div></div>
</div>

<!-- RINCIAN PEMBIAYAAN (OJK WAJIB - JANGAN DIHILANGKAN) -->
<div class="sec" style="margin-bottom:8px;">
<div class="sec-title">📋 RINCIAN PEMBIAYAAN (Transparansi OJK)</div>
<table style="width:100%; border-collapse:collapse; font-size:10px; margin-top:4px;">
<tr style="background:#f8fafc;"><td style="padding:5px;">Harga Cash (Harga Jual Tunai)</td><td style="padding:5px; text-align:right;"><b>{format_rp(d['harga_cash'])}</b></td></tr>
<tr><td style="padding:5px;">Uang Muka (DP) — {float(d['dp'])/float(d['harga_cash'])*100:.1f}%</td><td style="padding:5px; text-align:right;">{format_rp(d['dp'])}</td></tr>
<tr style="background:#fffbeb;"><td style="padding:5px;"><b>Pokok Hutang (Pokok Pembiayaan)</b></td><td style="padding:5px; text-align:right;"><b>{format_rp(pokok_hutang)}</b></td></tr>
<tr><td style="padding:5px;">Bunga / Margin Flat — {bunga_persen_bulan:.2f}%/bulan × {tenor_asli} bulan</td><td style="padding:5px; text-align:right;">{format_rp(bunga_total)}</td></tr>
<tr><td style="padding:5px;">Biaya Administrasi</td><td style="padding:5px; text-align:right;">Rp 0 (include)</td></tr>
<tr><td style="padding:5px;">Biaya Provisi</td><td style="padding:5px; text-align:right;">Rp 0 (include)</td></tr>
<tr><td style="padding:5px;">Asuransi / Jaminan</td><td style="padding:5px; text-align:right;">Tidak ada</td></tr>
<tr style="background:#eff6ff;"><td style="padding:6px;"><b>TOTAL KEWAJIBAN DEBITUR</b></td><td style="padding:6px; text-align:right;"><b>{format_rp(total_kewajiban)}</b></td></tr>
<tr style="background:#ecfdf5;"><td style="padding:6px;"><b>ANGSURAN PER BULAN × {tenor_asli}</b></td><td style="padding:6px; text-align:right;"><b>{format_rp(d['cicilan_bulan'])} × {tenor_asli}x</b></td></tr>
</table>
</div>

<!-- E-MATERAI (KONDISIONAL) -->
{materai_html}

<!-- JADWAL ANGSURAN -->
<div class="sched">
<div class="sched-h">📅 Jadwal Angsuran — Tenor {tenor_asli}×</div>
<table>
<thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
<tbody>{rows_sched}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_hutang)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
</table>
</div>

<!-- TTD DIGITAL -->
<div class="sig-grid">
<div class="sig-card">
<div class="sig-title">✓ Tanda Tangan Digital Toko</div>
<div class="sig-verify" style="font-size:10px;"><b>{TOKO['nama']}</b></div>
<div class="sig-verify">Kode Verifikasi: GRC-{kid}-TN</div>
<div class="sig-verify">Tgl: {datetime.now().strftime('%d-%m-%Y %H:%M')}</div>
<div style="font-size:9px; color:#059669; font-weight:700; margin-top:6px;">✓ Terverifikasi Sistem</div>
</div>
<div class="sig-card customer">
<div class="sig-title">✍ Tanda Tangan Digital Customer</div>
<div class="sig-verify" style="font-size:10px;"><b>{d['cn']}</b></div>
<canvas id="sigCanvas"></canvas>
<button type="button" class="sig-btn" onclick="clearSig()">🗑️ Hapus TTD</button>
<div class="sig-verify" id="ttdStatus">Tanda tangan di kotak di atas</div>
</div>
</div>

<!-- KLAUSUL OJK -->
<div class="ojk-box">
<div class="ojk-title">⚖️ KLAUSUL &amp; KEPATUHAN (POJK 35/2018 &amp; UU 8/1999 Perlindungan Konsumen)</div>
<div class="ojk-grid">
<div>• Metode bayar: <b>{metode}</b></div>
<div>• Jatuh tempo pertama: <b>{d['jatuh_tempo']}</b></div>
<div>• Denda keterlambatan: <b>{denda_harian}% / hari</b></div>
<div>• Bunga bersifat <b>flat (tetap)</b></div>
<div>• Hak konsumen: <b>komplain &amp; penyelesaian</b></div>
<div>• Sengketa: <b>BPSK / Pengadilan Negeri</b></div>
</div>
<div style="font-size:8.5px; color:#1e3a8a; margin-top:6px; line-height:1.5;">
<b>Pasal Penting:</b> Debitur berhak mengajukan komplain tertulis ke kreditur. Jika tidak tercapai kesepakatan dalam 30 hari, sengketa diselesaikan melalui Badan Penyelesaian Sengketa Konsumen (BPSK) atau Pengadilan Negeri sesuai UU No. 8 Tahun 1999. Debitur berhak mendapat salinan perjanjian ini.
</div>
</div>

</div>
<div class="terms-section"><div class="terms-title">Syarat &amp; Ketentuan</div><ol class="terms-list">
<li><b>Objek:</b> {d['pn']} (SKU: GRC-{d['produk_id']})</li>
<li><b>Jangka Waktu:</b> {tenor_asli} bulan</li>
<li><b>Jatuh Tempo:</b> Setiap 30 hari, mulai {d['jatuh_tempo']}</li>
<li><b>Denda:</b> {denda_harian}% per hari dari angsuran tertunggak</li>
<li><b>Pelunasan dipercepat</b> diperbolehkan tanpa penalti</li>
<li><b>Jaminan:</b> Barang yang dibiayai (fidusia)</li>
<li><b>Penyelesaian sengketa:</b> BPSK / PN setempat</li>
<li><b>Dokumen sah</b> setelah ditandatangani kedua pihak</li>
</ol></div>
<footer class="footer"><div>{TOKO['nama']}</div><div>Perjanjian ini sah menurut hukum Indonesia. Simpan sebagai bukti kepemilikan &amp; pembayaran.</div></footer>
</div>

<script>
const canvas = document.getElementById('sigCanvas');
const ctx = canvas.getContext('2d');
let drawing = false, signed = false;
function resizeCanvas() {{
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1a2b47';
}}
window.addEventListener('load', resizeCanvas);
window.addEventListener('resize', resizeCanvas);
function getXY(e) {{
    const r = canvas.getBoundingClientRect();
    const p = e.touches ? e.touches[0] : e;
    return [p.clientX - r.left, p.clientY - r.top];
}}
function start(e) {{ e.preventDefault(); drawing = true; ctx.beginPath(); const [x,y] = getXY(e); ctx.moveTo(x,y); }}
function move(e) {{ if (!drawing) return; e.preventDefault(); const [x,y] = getXY(e); ctx.lineTo(x,y); ctx.stroke(); signed = true; document.getElementById('ttdStatus').innerHTML = '<span style="color:#059669;font-weight:700;">✓ TTD tersimpan</span>'; }}
function end(e) {{ drawing = false; }}
canvas.addEventListener('mousedown', start); canvas.addEventListener('mousemove', move); canvas.addEventListener('mouseup', end);
canvas.addEventListener('touchstart', start); canvas.addEventListener('touchmove', move); canvas.addEventListener('touchend', end);
function clearSig() {{ ctx.clearRect(0, 0, canvas.width, canvas.height); signed = false; document.getElementById('ttdStatus').innerHTML = 'Tanda tangan di kotak di atas'; }}
</script>
</body></html>"""

        components.html(f"""
        <html><head><style>
        .btn-print {{ background:#667eea; color:white; border:none; padding:12px 24px; font-size:16px; border-radius:8px; cursor:pointer; display:block; margin:0 auto 15px; font-weight:bold; width:100%; }}
        .btn-print:hover {{ background:#764ba2; }}
        .print-area {{ border:1px solid #ddd; padding:20px; border-radius:10px; background:white; }}
        @media print {{ .btn-print {{ display:none; }} .print-area {{ border:none; padding:0; }} }}
        </style></head><body>
        <button class="btn-print" onclick="window.print()">🖨️ Cetak Sekarang (Print / Simpan PDF)</button>
        <div class="print-area">{invoice_html.split('<body>')[1].split('</body>')[0]}</div>
        </body></html>""", height=1200, scrolling=True)

        st.download_button("📥 Download (HTML)", invoice_html, f"perjanjian_kredit_{kid}.html", "text/html", use_container_width=True)

        # Info e-materai
        if wajib_materai:
            st.warning(f"⚠️ **Perjanjian ini WAJIB e-Materai Rp 10.000** (nilai {format_rp(total_kewajiban)} > Rp 5.000.000). Beli di meterai.peruri.co.id.")
        else:
            st.success(f"✅ **Tidak wajib e-Materai** (nilai {format_rp(total_kewajiban)} ≤ Rp 5.000.000). Cukup tanda tangan kedua pihak untuk sah.")

# ==================== INVOICE BARU ====================
elif pilihan == "🧾 Invoice Baru":
    st.markdown('<div class="main-header"><h1>🧾 Invoice Baru</h1><p>Invoice custom (jasa/pesanan khusus)</p></div>', unsafe_allow_html=True)

    tab_buat, tab_riwayat = st.tabs(["➕ Buat", "📋 Riwayat"])

    with tab_buat:
        col1, col2 = st.columns(2)
        with col1:
            inv_nama = st.text_input("Nama Customer")
            inv_telp = st.text_input("Telepon")
        with col2:
            inv_alamat = st.text_area("Alamat", height=68)
            inv_metode = st.selectbox("Metode Bayar", ["Tunai (Cash)", "Transfer Bank", "QRIS", "Kartu Debit/Kredit"])

        inv_tanggal = st.date_input("Tanggal Invoice", value=datetime.now().date())

        st.markdown('<div class="section-header"><h3>🛒 Item</h3></div>', unsafe_allow_html=True)
        if 'inv_items' not in st.session_state:
            st.session_state.inv_items = [{"deskripsi": "", "qty": 1, "harga": 0}]

        for i, item in enumerate(st.session_state.inv_items):
            c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
            with c1:
                item["deskripsi"] = st.text_input(f"Item #{i+1}", value=item["deskripsi"], key=f"inv_desc_{i}")
            with c2:
                item["qty"] = st.number_input(f"Qty #{i+1}", min_value=1, value=int(item["qty"]), step=1, key=f"inv_qty_{i}")
            with c3:
                item["harga"] = st.number_input(f"Harga #{i+1}", min_value=0.0, value=float(item["harga"]), step=1000.0, key=f"inv_harga_{i}")
            with c4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"inv_del_{i}") and len(st.session_state.inv_items) > 1:
                    st.session_state.inv_items.pop(i)
                    st.rerun()

        if st.button("➕ Tambah Item"):
            st.session_state.inv_items.append({"deskripsi": "", "qty": 1, "harga": 0})
            st.rerun()

        subtotal = sum(item["qty"] * item["harga"] for item in st.session_state.inv_items)

        col_d, col_p = st.columns(2)
        with col_d:
            diskon_p = st.number_input("Diskon (%)", min_value=0.0, max_value=100.0, value=0.0)
        with col_p:
            pajak_p = st.number_input("Pajak/PPN (%)", min_value=0.0, max_value=100.0, value=0.0)

        diskon_n = round(subtotal * diskon_p / 100, -2)
        setelah = subtotal - diskon_n
        pajak_n = round(setelah * pajak_p / 100, -2)
        total = setelah + pajak_n

        # Cek e-materai
        wajib_materai_inv = total > 5_000_000

        html = '<div class="metric-grid">'
        html += metric_card("Subtotal", format_rp(subtotal), "card-blue")
        html += metric_card(f"Diskon", f"-{format_rp(diskon_n)}", "card-pink")
        html += metric_card(f"Pajak", f"+{format_rp(pajak_n)}", "card-orange")
        html += metric_card("TOTAL", format_rp(total), "card-green")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        if wajib_materai_inv:
            st.warning(f"⚠️ Total {format_rp(total)} > Rp 5.000.000 — **wajib e-Materai Rp 10.000** untuk alat bukti.")
        else:
            st.success(f"✅ Total {format_rp(total)} ≤ Rp 5.000.000 — tidak wajib e-Materai.")

        inv_catatan = st.text_area("Catatan")
        inv_ttd_nama = st.text_input("Nama Penanda Tangan (pada kolom customer)", placeholder="Opsional — default: nama customer")

        if st.button("💾 Simpan Invoice"):
            valid_items = [it for it in st.session_state.inv_items if it["deskripsi"].strip() and it["harga"] > 0]
            if not inv_nama:
                st.error("Nama customer wajib")
            elif not valid_items:
                st.error("Minimal 1 item valid")
            else:
                try:
                    nomor = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    c.execute("""INSERT INTO invoice_custom (nomor_invoice, customer_nama, customer_telepon, customer_alamat, items_json, subtotal, diskon_persen, diskon_nominal, pajak_persen, pajak_nominal, total, metode_bayar, catatan, tanggal, dibuat_oleh) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (nomor, inv_nama, inv_telp, inv_alamat, json.dumps(valid_items), subtotal, diskon_p, diskon_n, pajak_p, pajak_n, total, inv_metode, inv_catatan, inv_tanggal.strftime("%Y-%m-%d"), st.session_state.username))
                    conn.commit()
                    log_aksi(st.session_state.username, "BUAT_INVOICE", f"{nomor} - {inv_nama}")
                    flash(f"✅ Invoice {nomor} tersimpan!", "success")
                    st.session_state.inv_items = [{"deskripsi": "", "qty": 1, "harga": 0}]
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ {e}")

    with tab_riwayat:
        df_inv = pd.read_sql_query("SELECT id, nomor_invoice, customer_nama, total, metode_bayar, tanggal FROM invoice_custom ORDER BY id DESC", conn)
        if df_inv.empty:
            st.info("Belum ada invoice")
        else:
            df_show = df_inv.copy()
            df_show['total'] = df_show['total'].apply(format_rp)
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            opsi = {f"{r['nomor_invoice']} - {r['customer_nama']}": r['id'] for _, r in df_inv.iterrows()}
            pilih = st.selectbox("Pilih Invoice", list(opsi.keys()))
            iid = opsi[pilih]
            row_inv = pd.read_sql_query("SELECT * FROM invoice_custom WHERE id=?", conn, params=(iid,)).iloc[0]
            items = json.loads(row_inv['items_json'])

            items_rows = "".join([
                f"<tr><td>{it['deskripsi']}</td><td class='c'>{it['qty']}</td><td class='r'>{format_rp(it['harga'])}</td><td class='r'><b>{format_rp(it['qty']*it['harga'])}</b></td></tr>"
                for it in items
            ])

            wajib_mat = row_inv['total'] > 5_000_000
            materai_section = (
                f"""<div style="border:2px dashed #b91c1c; border-radius:10px; padding:10px; text-align:center; background:#fef2f2; margin:10px 0;">
                <div style="font-size:10px; font-weight:800; color:#b91c1c; text-transform:uppercase;">⚠️ WAJIB E-MATERAI — UU 10/2020</div>
                <div style="font-size:9px; color:#7f1d1d; margin-top:4px;">Nilai {format_rp(row_inv['total'])} &gt; Rp 5.000.000<br>[ Tempel e-Materai Rp 10.000 di sini ]</div>
                </div>"""
                if wajib_mat else
                f"""<div style="text-align:center; padding:5px; font-size:9px; color:#059669; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; margin:10px 0;">✓ Tidak wajib e-Materai (≤ Rp 5.000.000)</div>"""
            )

            full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{row_inv['nomor_invoice']}</title>
<style>
body {{ font-family:Arial; background:#e2e8f0; margin:0; padding:20px; }}
.page {{ max-width:820px; margin:0 auto; background:white; border-radius:14px; overflow:hidden; }}
.hdr {{ background:linear-gradient(135deg,#0f172a,#1e3a8a); color:white; padding:18px 24px; display:flex; justify-content:space-between; align-items:center; }}
.hdr h1 {{ margin:0; font-size:20px; }}
.body {{ padding:16px 24px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ background:#f8fafc; padding:8px; text-align:left; border-bottom:2px solid #e2e8f0; }}
td {{ padding:6px 8px; border-bottom:1px solid #f1f5f9; }}
.r {{ text-align:right; }} .c {{ text-align:center; }}
.sig-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:14px; }}
.sig-card {{ border:2px dashed #1e3a8a; border-radius:10px; padding:10px; text-align:center; background:#f8fafc; }}
.sig-card.customer {{ border-color:#b8956a; background:#faf5ff; }}
canvas {{ border:1.5px dashed #b8956a; border-radius:6px; background:#fff; width:100%; height:100px; touch-action:none; display:block; }}
.btn-clear {{ background:#fef3c7; border:1px solid #f59e0b; color:#92400e; padding:3px 8px; border-radius:4px; font-size:9px; margin-top:4px; cursor:pointer; }}
@media print {{ body {{ padding:0; background:white; }} .page {{ border-radius:0; }} }}
</style></head><body>
<div class="page">
<div class="hdr">
<div><h1>{TOKO['nama']}</h1><div style="font-size:11px; color:#94a3b8;">Cash &amp; Credit</div><div style="font-size:10px; color:#cbd5e1;">{TOKO['alamat']}<br>NIB: {TOKO['nib']}</div></div>
<div style="text-align:right;">
<div style="background:rgba(245,158,11,0.2); color:#fbbf24; padding:4px 12px; border-radius:12px; font-size:11px; font-weight:700; display:inline-block;">INVOICE</div>
<div style="margin-top:6px; font-weight:700;">{row_inv['nomor_invoice']}</div>
<div style="font-size:10px; color:#94a3b8;">{row_inv['tanggal']}</div>
</div>
</div>
<div class="body">
<div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
<div style="border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
<div style="font-size:11px; font-weight:800; color:#1e3a8a; margin-bottom:4px;">CUSTOMER</div>
<div style="font-size:12px;"><b>{row_inv['customer_nama']}</b></div>
<div style="font-size:11px; color:#666;">{row_inv['customer_telepon'] or '-'}</div>
<div style="font-size:11px; color:#666;">{row_inv['customer_alamat'] or '-'}</div>
</div>
<div style="border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
<div style="font-size:11px; font-weight:800; color:#1e3a8a; margin-bottom:4px;">INFO</div>
<div style="font-size:11px;"><b>Metode:</b> {row_inv['metode_bayar']}</div>
<div style="font-size:11px;"><b>Tanggal:</b> {row_inv['tanggal']}</div>
</div>
</div>
<table>
<thead><tr><th>Deskripsi</th><th class="c">Qty</th><th class="r">Harga</th><th class="r">Subtotal</th></tr></thead>
<tbody>{items_rows}</tbody>
</table>
<div style="margin-top:12px; text-align:right; font-size:12px;">
<div style="padding:3px 0;">Subtotal: <b>{format_rp(row_inv['subtotal'])}</b></div>
<div style="padding:3px 0; color:#b91c1c;">Diskon ({row_inv['diskon_persen']:.0f}%): <b>-{format_rp(row_inv['diskon_nominal'])}</b></div>
<div style="padding:3px 0; color:#92400e;">Pajak ({row_inv['pajak_persen']:.0f}%): <b>+{format_rp(row_inv['pajak_nominal'])}</b></div>
<div style="padding:8px 0; border-top:2px solid #1e3a8a; margin-top:6px; font-size:15px; color:#1e3a8a;"><b>TOTAL: {format_rp(row_inv['total'])}</b></div>
</div>
{materai_section}
{f"<div style='margin-top:12px; padding:8px 12px; background:#fffbeb; border-left:3px solid #f59e0b; border-radius:4px; font-size:11px;'><b>Catatan:</b> {row_inv['catatan']}</div>" if row_inv['catatan'] else ""}

<div class="sig-grid">
<div class="sig-card">
<div style="font-size:10px; font-weight:800; color:#1e3a8a; text-transform:uppercase; margin-bottom:4px;">✓ TTD Toko</div>
<div style="font-size:10px;"><b>{TOKO['nama']}</b></div>
<div style="font-family:'Courier New',monospace; font-size:8px; color:#6b7280; margin-top:4px;">Kode: {row_inv['nomor_invoice']}-TN</div>
<div style="font-size:9px; color:#059669; font-weight:700; margin-top:6px;">✓ Terverifikasi</div>
</div>
<div class="sig-card customer">
<div style="font-size:10px; font-weight:800; color:#b8956a; text-transform:uppercase; margin-bottom:4px;">✍ TTD Customer</div>
<div style="font-size:10px;"><b>{row_inv['customer_nama']}</b></div>
<canvas id="sigCanvas2"></canvas>
<button type="button" class="btn-clear" onclick="clearSig2()">🗑️ Hapus</button>
<div id="ttdStatus2" style="font-size:8px; color:#6b7280; margin-top:2px;">Tanda tangan di kotak</div>
</div>
</div>
</div>
</div>

<script>
const cv = document.getElementById('sigCanvas2');
const cx = cv.getContext('2d');
let dr = false;
function resizeCv() {{ const r = cv.getBoundingClientRect(); const dpr = window.devicePixelRatio || 1; cv.width = r.width*dpr; cv.height = r.height*dpr; cx.scale(dpr,dpr); cx.lineWidth=2.2; cx.lineCap='round'; cx.lineJoin='round'; cx.strokeStyle='#1a2b47'; }}
window.addEventListener('load', resizeCv); window.addEventListener('resize', resizeCv);
function getXY(e) {{ const r = cv.getBoundingClientRect(); const p = e.touches ? e.touches[0] : e; return [p.clientX - r.left, p.clientY - r.top]; }}
function start(e) {{ e.preventDefault(); dr = true; cx.beginPath(); const [x,y]=getXY(e); cx.moveTo(x,y); }}
function move(e) {{ if(!dr) return; e.preventDefault(); const [x,y]=getXY(e); cx.lineTo(x,y); cx.stroke(); document.getElementById('ttdStatus2').innerHTML='<span style="color:#059669;font-weight:700;">✓ TTD tersimpan</span>'; }}
function end() {{ dr = false; }}
cv.addEventListener('mousedown', start); cv.addEventListener('mousemove', move); cv.addEventListener('mouseup', end);
cv.addEventListener('touchstart', start); cv.addEventListener('touchmove', move); cv.addEventListener('touchend', end);
function clearSig2() {{ cx.clearRect(0, 0, cv.width, cv.height); document.getElementById('ttdStatus2').innerHTML = 'Tanda tangan di kotak'; }}
</script>
</body></html>"""

            components.html(f"""
            <html><head><style>
            .btn-print {{ background:#667eea; color:white; border:none; padding:12px 24px; font-size:16px; border-radius:8px; cursor:pointer; display:block; margin:0 auto 15px; font-weight:bold; width:100%; }}
            .print-area {{ border:1px solid #ddd; padding:20px; border-radius:10px; background:white; }}
            @media print {{ .btn-print {{ display:none; }} .print-area {{ border:none; padding:0; }} }}
            </style></head><body>
            <button class="btn-print" onclick="window.print()">🖨️ Cetak / Simpan PDF</button>
            <div class="print-area">{full_html.split('<body>')[1].split('</body>')[0]}</div>
            </body></html>""", height=1100, scrolling=True)

            st.download_button("📥 Download Invoice (HTML)", full_html, f"{row_inv['nomor_invoice']}.html", "text/html", use_container_width=True)

            if st.button("🗑️ Hapus Invoice"):
                c.execute("DELETE FROM invoice_custom WHERE id=?", (iid,))
                conn.commit()
                flash("🗑️ Invoice dihapus", "success")
                st.rerun()

# ==================== DATA CUSTOMER ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Customer</h1></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["➕ Tambah", "📋 Daftar"])
    with tab1:
        with st.form("f_cust"):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nama")
                t = st.text_input("Telepon")
            with col2:
                a = st.text_area("Alamat")
            if st.form_submit_button("💾 Simpan") and n:
                c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (n, t, a))
                conn.commit()
                flash(f"✅ {n} disimpan!", "success")
                st.rerun()
    with tab2:
        df_c = pd.read_sql_query("""SELECT c.id, c.nama, c.telepon, c.alamat, 
            (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id) as total_kredit,
            (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id AND status='Berjalan') as aktif
            FROM customer c ORDER BY c.id DESC""", conn)
        st.dataframe(df_c, use_container_width=True, hide_index=True)

# ==================== STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Stok Barang</h1></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Daftar", "✏️ Edit Harga Jual Pakaian"])
    with tab1:
        df_p = pd.read_sql_query("SELECT * FROM produk ORDER BY stok ASC", conn)
        df_p['harga_cash'] = df_p.apply(lambda r: hitung_harga_cash(r['harga_modal'], r.get('markup_persen', 5), r.get('harga_jual')), axis=1)
        df_show = df_p[['id', 'nama', 'kategori', 'harga_modal', 'harga_cash', 'stok']].copy()
        df_show['harga_modal'] = df_show['harga_modal'].apply(format_rp)
        df_show['harga_cash'] = df_show['harga_cash'].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    with tab2:
        ph = ",".join(["?"] * len(PAKAIAN_KATEGORI))
        df_pk = pd.read_sql_query(f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ({ph}) ORDER BY kategori, nama", conn, params=tuple(PAKAIAN_KATEGORI))
        if df_pk.empty:
            st.info("Belum ada produk pakaian")
        else:
            df_pk['harga_jual'] = df_pk['harga_jual'].fillna(0).astype(float)
            edited = st.data_editor(df_pk, column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "nama": st.column_config.TextColumn("Produk", disabled=True, width="large"),
                "kategori": st.column_config.TextColumn("Kategori", disabled=True),
                "harga_modal": st.column_config.NumberColumn("Modal", disabled=True, format="Rp %d"),
                "harga_jual": st.column_config.NumberColumn("Harga Jual", min_value=0, step=1000, format="Rp %d"),
            }, hide_index=True, use_container_width=True, key="ed_hj")
            if st.button("💾 Simpan"):
                n = 0
                for _, r in edited.iterrows():
                    hj = r['harga_jual'] if r['harga_jual'] > 0 else None
                    c.execute("UPDATE produk SET harga_jual=? WHERE id=?", (hj, r['id']))
                    n += 1
                conn.commit()
                flash(f"✅ {n} produk tersimpan!", "success")
                st.rerun()

# ==================== OVERDUE & DENDA ====================
elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Overdue & Denda</h1></div>', unsafe_allow_html=True)
    tgl = datetime.now().strftime("%Y-%m-%d")
    df_ov = pd.read_sql_query("""SELECT k.id, c.nama, c.telepon, p.nama as produk, k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo 
        FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id 
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ? ORDER BY k.jatuh_tempo""", conn, params=(tgl,))
    if df_ov.empty:
        st.success("✅ Tidak ada overdue")
    else:
        df_ov['hari_telat'] = df_ov['jatuh_tempo'].apply(lambda x: (datetime.now().date() - datetime.strptime(x, "%Y-%m-%d").date()).days)
        df_ov['denda'] = df_ov.apply(lambda r: hitung_denda(r['cicilan_bulan'], r['hari_telat']), axis=1)
        df_show = df_ov.copy()
        for col in ['cicilan_bulan', 'sisa_hutang', 'denda']:
            df_show[col] = df_show[col].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==================== ALERT & REMINDER ====================
elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder</h1></div>', unsafe_allow_html=True)
    tgl = datetime.now().date()

    st.markdown('<div class="section-header"><h3>🚨 Overdue</h3></div>', unsafe_allow_html=True)
    df_ov = pd.read_sql_query("SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan' AND k.jatuh_tempo < ?", conn, params=(tgl.strftime("%Y-%m-%d"),))
    if df_ov.empty:
        st.success("✅ Tidak ada overdue")
    else:
        for _, r in df_ov.iterrows():
            hari = (tgl - datetime.strptime(r['jatuh_tempo'], "%Y-%m-%d").date()).days
            col1, col2 = st.columns([4, 1])
            with col1:
                st.error(f"⚠️ **{r['nama']}** ({r['telepon']}) - Telat {hari} hari | Cicilan: {format_rp(r['cicilan_bulan'])}")
            with col2:
                if r['telepon']:
                    nomor = r['telepon'].replace('-', '').replace(' ', '')
                    if nomor.startswith('0'): nomor = '62' + nomor[1:]
                    pesan = f"Halo {r['nama']}, cicilan Anda {format_rp(r['cicilan_bulan'])} sudah jatuh tempo {r['jatuh_tempo']} ({hari} hari lalu). Mohon segera diselesaikan. Terima kasih 🙏"
                    st.markdown(f'<a href="https://wa.me/{nomor}?text={quote(pesan)}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;font-weight:600;">📱 WA</button></a>', unsafe_allow_html=True)

    st.markdown('<div class="section-header"><h3>⏰ Jatuh Tempo 3 Hari</h3></div>', unsafe_allow_html=True)
    tgl3 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    df_h3 = pd.read_sql_query("SELECT k.id, c.nama, c.telepon, k.cicilan_bulan, k.jatuh_tempo FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?", conn, params=(tgl.strftime("%Y-%m-%d"), tgl3))
    if df_h3.empty:
        st.success("✅ Tidak ada yang jatuh tempo 3 hari")
    else:
        for _, r in df_h3.iterrows():
            st.warning(f"⏰ **{r['nama']}** ({r['telepon']}) - Tempo: {r['jatuh_tempo']} | Cicilan: {format_rp(r['cicilan_bulan'])}")

# ==================== LAPORAN & ANALITIK ====================
elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1></div>', unsafe_allow_html=True)
    st.markdown("### Penjualan Cash per Bulan")
    df_cash = pd.read_sql_query("SELECT substr(tanggal,1,7) as bulan, COUNT(*) as trx, SUM(jumlah) as unit, SUM(total_harga) as total, SUM(laba) as laba FROM transaksi_cash GROUP BY bulan ORDER BY bulan DESC", conn)
    if not df_cash.empty:
        df_show = df_cash.copy()
        df_show['total'] = df_show['total'].apply(format_rp)
        df_show['laba'] = df_show['laba'].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    st.markdown("### Status Kredit")
    df_k = pd.read_sql_query("SELECT status, COUNT(*) as jumlah, SUM(total_hutang) as total FROM kredit GROUP BY status", conn)
    if not df_k.empty:
        df_show = df_k.copy()
        df_show['total'] = df_show['total'].apply(format_rp)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==================== MODAL VS PROFIT ====================
elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Modal vs Profit</h1></div>', unsafe_allow_html=True)
    ph = ",".join(["?"] * len(PAKAIAN_KATEGORI))
    df_p = pd.read_sql_query(f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ({ph}) ORDER BY kategori, nama", conn, params=tuple(PAKAIAN_KATEGORI))
    if df_p.empty:
        st.info("Belum ada produk pakaian")
    else:
        df_p['harga_jual_valid'] = df_p['harga_jual'].fillna(0)
        df_p['margin_nominal'] = df_p['harga_jual_valid'] - df_p['harga_modal']
        df_p['margin_persen'] = (df_p['margin_nominal'] / df_p['harga_modal'] * 100).fillna(0)
        df_show = df_p[['nama', 'kategori', 'harga_modal', 'harga_jual_valid', 'margin_nominal', 'margin_persen']].copy()
        df_show['harga_modal'] = df_show['harga_modal'].apply(format_rp)
        df_show['harga_jual_valid'] = df_show['harga_jual_valid'].apply(lambda x: format_rp(x) if x > 0 else "—")
        df_show['margin_nominal'] = df_show['margin_nominal'].apply(format_rp)
        df_show['margin_persen'] = df_show['margin_persen'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ==================== BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup & Impor</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📤 Backup DB", "📥 Impor CSV", "📊 Export"])

    with tab1:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                st.download_button("📥 Download Database", f, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", "application/octet-stream", use_container_width=True)
        st.caption(f"📁 {DB_PATH}")

    with tab2:
        st.caption("Format CSV: nama, kategori, harga_modal, stok")
        uploaded = st.file_uploader("Pilih CSV", type=["csv"])
        if uploaded:
            try:
                df_imp = pd.read_csv(uploaded)
                st.dataframe(df_imp.head(), use_container_width=True)
                if st.button("✅ Proses Impor"):
                    n = 0
                    for _, r in df_imp.iterrows():
                        try:
                            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", (r['nama'], r['kategori'], float(r['harga_modal']), int(r['stok'])))
                            n += 1
                        except Exception:
                            pass
                    conn.commit()
                    flash(f"✅ {n} produk diimpor", "success")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

    with tab3:
        df_prod = pd.read_sql_query("SELECT * FROM produk", conn)
        st.download_button("📥 Export Produk (CSV)", df_prod.to_csv(index=False), "produk.csv", "text/csv", use_container_width=True)
        df_kredit = pd.read_sql_query("SELECT * FROM kredit", conn)
        st.download_button("📥 Export Kredit (CSV)", df_kredit.to_csv(index=False), "kredit.csv", "text/csv", use_container_width=True)

# ==================== MANAJEMEN USER ====================
elif pilihan == "👤 Manajemen User" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1></div>', unsafe_allow_html=True)
    with st.form("f_user"):
        col1, col2 = st.columns(2)
        with col1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
        with col2:
            nl = st.text_input("Nama Lengkap")
            role = st.selectbox("Role", ["admin", "kasir"])
        if st.form_submit_button("💾 Simpan") and u and p and nl:
            try:
                c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", (u, hash_password(p), nl, role))
                conn.commit()
                flash(f"✅ User {u} disimpan", "success")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

    df_u = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY id", conn)
    st.dataframe(df_u, use_container_width=True, hide_index=True)

    opsi_u = {f"{r['username']} - {r['nama_lengkap']}": r['id'] for _, r in df_u.iterrows()}
    if opsi_u:
        pilih_u = st.selectbox("Pilih User", list(opsi_u.keys()))
        uid = opsi_u[pilih_u]
        colA, colB = st.columns(2)
        with colA:
            if st.button("🔄 Toggle Aktif"):
                c.execute("UPDATE users SET aktif = 1 - aktif WHERE id=?", (uid,))
                conn.commit()
                flash("✅ Status diubah", "success")
                st.rerun()
        with colB:
            if st.button("🗑️ Hapus") and uid != 1:
                c.execute("DELETE FROM users WHERE id=?", (uid,))
                conn.commit()
                flash("🗑️ User dihapus", "success")
                st.rerun()

# ==================== LOG AKTIVITAS ====================
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas</h1></div>', unsafe_allow_html=True)
    df_log = pd.read_sql_query("SELECT username, aksi, detail, waktu FROM log_aktivitas ORDER BY id DESC LIMIT 200", conn)
    if df_log.empty:
        st.info("Belum ada log")
    else:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
