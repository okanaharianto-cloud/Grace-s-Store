import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
from datetime import datetime, timedelta
from urllib.parse import quote
import altair as alt
import streamlit.components.v1 as components
import io
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

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
    df_custom = pd.read_sql_query("SELECT ke, jatuh_tempo, angsuran, sisa FROM jadwal_kustom WHERE kredit_id=? AND opsi=? ORDER BY ke", conn, params=(kredit_id, opsi))
    if not df_custom.empty:
        return df_custom
    else:
        return pd.DataFrame(build_jadwal_angsuran(total, cicilan, tenor, tgl_str))

# ==================== HELPER PDF & FOTO ====================
def proses_gambar(uploaded_file, max_width=800):
    if uploaded_file is None:
        return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_width:
        rasio = max_width / img.width
        img = img.resize((max_width, int(img.height * rasio)))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=85)
    img_bytes.seek(0)
    return img_bytes

def buat_emeterai_bytes():
    img = Image.new("RGB", (300, 150), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    try:
        font_besar = ImageFont.truetype("DejaVuSans.ttf", 20)
        font_kecil = ImageFont.truetype("DejaVuSans.ttf", 12)
    except:
        try:
            font_besar = ImageFont.truetype("arial.ttf", 20)
            font_kecil = ImageFont.truetype("arial.ttf", 12)
        except:
            font_besar = ImageFont.load_default()
            font_kecil = ImageFont.load_default()

    draw.rectangle([5, 5, 295, 145], outline="black", width=2)
    draw.text((20, 20), "E-METERAI", font=font_besar, fill="black")
    draw.text((20, 55), "Rp 10.000", font=font_besar, fill="black")
    draw.text((20, 90), "Peruri - Sah", font=font_kecil, fill="black")
    draw.text((20, 110), "Nomor: 0000-0000-0000", font=font_kecil, fill="black")
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes

def generate_kredit_pdf(data, file_ktp, file_kk):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- PAGE 1: INVOICE ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "INVOICE KREDIT", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "GRACE'S ELECTRONIC", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Jl. Barong Tongkok, Kutai Barat | HP/WA: 0822-9954-8411", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"No. Invoice: GRC-INV-{data['kid']}", ln=True)
    pdf.cell(0, 5, f"Tanggal: {datetime.now().strftime('%d-%m-%Y')}", ln=True)
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "KEPADA:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Nama: {data['cn']}", ln=True)
    pdf.cell(0, 5, f"Telepon: {data['telepon']}", ln=True)
    pdf.multi_cell(0, 5, f"Alamat: {data['alamat']}")
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PRODUK:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"{data['pn']} (SKU: GRC-{data['produk_id']})", ln=True)
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "RINCIAN PEMBAYARAN:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Harga Cash: {format_rp(data['harga_cash'])}", ln=True)
    pdf.cell(0, 5, f"Uang Muka (DP): {format_rp(data['dp'])}", ln=True)
    pdf.cell(0, 5, f"Pokok Hutang: {format_rp(data['pokok'])}", ln=True)
    pdf.cell(0, 5, f"Total Hutang: {format_rp(data['total_hutang'])}", ln=True)
    pdf.cell(0, 5, f"Angsuran / Bulan: {format_rp(data['cicilan'])}", ln=True)
    pdf.cell(0, 5, f"Tenor: {data['tenor']} bulan", ln=True)
    pdf.ln(3)
    
    # Table
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 6, "No", border=1)
    pdf.cell(45, 6, "Jatuh Tempo", border=1)
    pdf.cell(45, 6, "Angsuran", border=1)
    pdf.cell(45, 6, "Sisa", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in data['schedule']:
        pdf.cell(20, 5, str(row['ke']), border=1)
        pdf.cell(45, 5, row['jatuh_tempo'], border=1)
        pdf.cell(45, 5, format_rp(row['angsuran']), border=1)
        pdf.cell(45, 5, format_rp(row['sisa']), border=1)
        pdf.ln()
    
    # --- PAGE 2: PERJANJIAN ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "PERJANJIAN PEMBIAYAAN KONSUMEN", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "GRACE'S ELECTRONIC", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Jl. Barong Tongkok, Kutai Barat | HP/WA: 0822-9954-8411", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"No. Perjanjian: GRC-INV-{data['kid']}", ln=True)
    pdf.cell(0, 5, f"Tanggal: {datetime.now().strftime('%d-%m-%Y')}", ln=True)
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "PARA PIHAK", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, "PIHAK PERTAMA (KREDITUR): GRACE'S ELECTRONIC, beralamat di Jl. Barong Tongkok, Kutai Barat.")
    pdf.multi_cell(0, 4, f"PIHAK KEDUA (DEBITUR): {data['cn']}, Telepon: {data['telepon']}, Alamat: {data['alamat']}.")
    pdf.ln(2)
    
    # Pasal 1
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "PASAL 1 - OBJEK PEMBIAYAAN", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, f"Debitur membeli secara kredit barang elektronik: {data['pn']} (SKU: GRC-{data['produk_id']}). Barang telah diterima dalam keadaan baik dan berfungsi normal.")
    pdf.ln(2)
    
    # Pasal 2
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "PASAL 2 - NILAI DAN RINCIAN PEMBIAYAAN", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, f"Harga Cash: {format_rp(data['harga_cash'])}\nUang Muka (DP): {format_rp(data['dp'])}\nPokok Hutang: {format_rp(data['pokok'])}\nTotal Hutang: {format_rp(data['total_hutang'])}\nTenor: {data['tenor']} bulan")
    pdf.ln(2)
    
    # Pasal 3-7
    pasal = [
        ("PASAL 3 - HAK DAN KEWAJIBAN", "Kreditur berhak menerima angsuran tepat waktu dan berkewajiban memberikan informasi transparan. Debitur berhak mendapatkan salinan perjanjian dan berkewajiban membayar angsuran sesuai jadwal serta merawat barang."),
        ("PASAL 4 - DENDA KETERLAMBATAN", f"Keterlambatan dikenakan denda {get_pengaturan_float('denda_per_hari_persen', 1.0)}% per hari dari angsuran tertunggak, dengan total denda tidak melebihi 100% dari Pokok Hutang."),
        ("PASAL 5 - JAMINAN FIDUSIA", "Debitur memberikan jaminan fidusia atas Objek Pembiayaan sesuai UU No. 42 Tahun 1999. Kreditur dilarang melakukan tindakan sepihak atas barang jaminan di luar ketentuan hukum."),
        ("PASAL 6 - PENYELESAIAN SENGKETA", "Sengketa diselesaikan secara musyawarah. Jika gagal, diselesaikan melalui Pengadilan Negeri yang berwenang. Debitur berhak menggugat Kreditur."),
        ("PASAL 7 - LARANGAN KLAUSUL EKSONERASI", "Kreditur dilarang mengalihkan tanggung jawab secara sepihak, membatasi hak Debitur menggugat, atau melakukan perubahan sepihak setelah perjanjian ditandatangani.")
    ]
    for judul, isi in pasal:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, judul, ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4, isi)
        pdf.ln(1)
        
    # Tanda Tangan & E-Meterai
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(90, 5, "KREDITUR", ln=0)
    pdf.cell(90, 5, "DEBITUR", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(90, 5, "GRACE'S ELECTRONIC", ln=0)
    pdf.cell(90, 5, data['cn'], ln=1)
    
    # Place e-meterai between signatures
    emeterai_bio = buat_emeterai_bytes()
    pdf.image(emeterai_bio, x=125, y=pdf.get_y()+2, w=40)
    
    pdf.ln(25)
    pdf.cell(90, 5, "(_________________________)", ln=0)
    pdf.cell(90, 5, "(_________________________)", ln=1)
    
    # --- PAGE 3: LAMPIRAN KTP & KK ---
    ktp_bio = proses_gambar(file_ktp)
    kk_bio = proses_gambar(file_kk)
    
    if ktp_bio or kk_bio:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "LAMPIRAN DOKUMEN IDENTITAS DEBITUR", ln=True, align="C")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, f"Lampiran ini merupakan bagian tidak terpisahkan dari Perjanjian Pembiayaan Konsumen Nomor GRC-INV-{data['kid']} atas nama {data['cn']}.")
        pdf.ln(4)
        
        if ktp_bio:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "A. Fotokopi / Scan KTP", ln=True)
            pdf.image(ktp_bio, x=25, w=160)
            pdf.ln(4)
            
        if kk_bio:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "B. Fotokopi / Scan Kartu Keluarga (KK)", ln=True)
            pdf.image(kk_bio, x=25, w=160)
            pdf.ln(4)
            
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, "Dokumen identitas di atas telah diverifikasi oleh Kreditur dan sesuai dengan data Debitur dalam Perjanjian ini.")
        
    return pdf.output(dest="S").encode("latin-1")


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

        if tampilkan_banding:
            tenor_opsi_1 = 2
            tenor_opsi_2 = 3
            pokok_awal = float(m_pokok)
            
            total_1 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_1)), -2)
            cicilan_1 = round(total_1 / tenor_opsi_1, -2)
            
            total_2 = round(pokok_awal * (1 + (rate_bulan * tenor_opsi_2)), -2)
            cicilan_2 = round(total_2 / tenor_opsi_2, -2)
            
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
                    c.execute("DELETE FROM jadwal_kustom WHERE kredit_id=? AND opsi IN ('A', 'B')", (kid,))
                    
                    sisa_a = edited_sched_1['angsuran'].sum()
                    for idx, row in edited_sched_1.iterrows():
                        sisa_a -= row['angsuran']
                        c.execute("INSERT INTO jadwal_kustom (kredit_id, opsi, ke, jatuh_tempo, angsuran, sisa) VALUES (?,?,?,?,?,?)",
                                  (kid, 'A', row['ke'], row['jatuh_tempo'].strftime("%d-%m-%Y"), row['angsuran'], max(sisa_a, 0)))
                        
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
            
            total_1_edit = edited_sched_1['angsuran'].sum()
            total_2_edit = edited_sched_2['angsuran'].sum()
            
            html_tenor_options = f"""
            <div class="tenor-options">
                <div class="tenor-card">
                    <div class="tc-label">Opsi A</div>
                    <div class="tc-title">Tenor {tenor_opsi_1}× ({tenor_opsi_1} Bulan)</div>
                    <div class="tc-row"><span class="k">Total Harga Cash</span><span class="v">{format_rp(total_1_edit + m_dp)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_1)}</span></div>
                </div>
                <div class="tenor-card recommended">
                    <div class="tc-label">Opsi B</div>
                    <div class="tc-title">Tenor {tenor_opsi_2}× ({tenor_opsi_2} Bulan)</div>
                    <div class="tc-row"><span class="k">Total Harga Cash</span><span class="v">{format_rp(total_2_edit + m_dp)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(cicilan_2)}</span></div>
                </div>
            </div>
            """
            
            paid_count = len(df_bayar)
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_1.iterrows()])
            rows_2 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_2.iterrows()])
            
            html_schedule = f"""
            <div class="sched-wrap" style="grid-template-columns: 1fr 1fr;">
                <div class="sched">
                    <div class="sched-h two">📅 Opsi A — Tenor {tenor_opsi_1}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_1_edit)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
                <div class="sched">
                    <div class="sched-h three">📅 Opsi B — Tenor {tenor_opsi_2}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_2}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_2_edit)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
            </div>
            """
        else:
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
                    <div class="tc-row"><span class="k">Total Harga Cash</span><span class="v">{format_rp(total_1_edit + m_dp)}</span></div>
                    <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
                </div>
            </div>
            """
            
            paid_count = len(df_bayar)
            rows_1 = "".join([f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo'].strftime('%d-%m-%Y')}</td><td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td><td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>" for _, r in edited_sched_1.iterrows()])
            
            html_schedule = f"""
            <div class="sched-wrap" style="grid-template-columns: 1fr;">
                <div class="sched">
                    <div class="sched-h two">📅 Jadwal Angsuran — Tenor {tenor_asli}×</div>
                    <table>
                        <thead><tr><th class="c" style="width:26px;">#</th><th>Jatuh Tempo</th><th class="r">Angsuran</th><th class="r">Sisa</th><th class="c">Status</th></tr></thead>
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL</td><td class="r">{format_rp(total_1_edit)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
            </div>
            """

        st.markdown('<div class="section-header"><h3>📋 Ringkasan Akad Kredit</h3></div>', unsafe_allow_html=True)
        html_metric = '<div class="metric-grid">'
        html_metric += metric_card("Harga Cash", format_rp(m_harga_cash), "card-blue")
        html_metric += metric_card("DP Dibayar (Uang Masuk)", format_rp(m_dp), "card-purple")
        html_metric += metric_card("Pokok Hutang", format_rp(m_pokok), "card-orange")
        html_metric += metric_card("Total Hutang", format_rp(m_total_hutang), "card-dark")
        html_metric += metric_card(f"Cicilan × {int(m_tenor)} bln", format_rp(m_cicilan), "card-pink")
        html_metric += metric_card("Sisa Saat Ini", format_rp(d['sisa_hutang']), "card-green" if float(d['sisa_hutang']) <= 0 else "card-dark")
        html_metric += '</div>'
        st.markdown(html_metric, unsafe_allow_html=True)

        total_keseluruhan = m_dp + m_total_hutang

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
            .page {{ max-width: 820px; margin: 0 auto; background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 30px rgba(15,23,42,0.15); }}
            
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

            .hdr {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 70%, #1e40af 100%); color: #fff; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow: hidden; }}
            .hdr::before {{ content:''; position:absolute; top:-50%; right:-5%; width:220px; height:220px; background: radial-gradient(circle, rgba(16,185,129,0.3), transparent 70%); border-radius:50%; }}
            .hdr::after {{ content:''; position:absolute; bottom:-70%; right:15%; width:180px; height:180px; background: radial-gradient(circle, rgba(245,158,11,0.25), transparent 70%); border-radius:50%; }}
            .brand {{ position: relative; z-index:1; }}
            .brand h1 {{ font-size: 19px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }}
            .brand .tag {{ font-size: 9.5px; color: #94a3b8; letter-spacing: 0.4px; margin-top: 1px; }}
            .brand .addr {{ font-size: 9px; color: #cbd5e1; margin-top: 4px; line-height: 1.4; }}
            .title-box {{ text-align: right; position: relative; z-index: 1; }}
            .badge-inv {{ display: inline-block; background: rgba(245,158,11,0.22); color: #fbbf24; padding: 3px 10px; border-radius: 12px; font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; border: 1px solid rgba(245,158,11,0.4); }}
            .inv-no {{ font-size: 11.5px; font-weight: 700; margin-top: 5px; }}
            .inv-date {{ font-size: 9px; color: #94a3b8; margin-top: 2px; }}

            .meta {{ display: flex; gap: 14px; justify-content: space-between; padding: 6px 22px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 9.5px; color: #475569; }}
            .meta b {{ color: #0f172a; }}

            .body {{ padding: 10px 22px 12px; }}

            .top-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }}
            .sec {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }}
            .sec-title {{ font-size: 9.5px; font-weight: 800; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.6px; padding-bottom: 4px; margin-bottom: 5px; border-bottom: 1.5px solid #f1f5f9; display: flex; align-items: center; gap: 5px; }}
            .sec-title span.ic {{ display: inline-flex; width: 16px; height: 16px; align-items: center; justify-content: center; background: linear-gradient(135deg,#1e3a8a,#1e40af); color: #fff; border-radius: 4px; font-size: 9px; }}
            .kv {{ display: grid; grid-template-columns: 68px 1fr; gap: 3px 6px; font-size: 10px; }}
            .kv .k {{ color: #64748b; }}
            .kv .v {{ color: #0f172a; font-weight: 600; }}

            .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 8px; }}
            .sum-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 8px; text-align: center; }}
            .sum-card.green {{ background: #ecfdf5; border-color: #a7f3d0; }}
            .sum-card.blue {{ background: #eff6ff; border-color: #bfdbfe; }}
            .sum-card.amber {{ background: #fffbeb; border-color: #fde68a; }}
            .sum-card .lbl {{ font-size: 8.5px; color: #64748b; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 700; }}
            .sum-card .val {{ font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 2px; }}
            .sum-card.green .val {{ color: #065f46; }}
            .sum-card.blue .val {{ color: #1e40af; }}
            .sum-card.amber .val {{ color: #92400e; }}

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

            .sig-grid {{ position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px; }}
            .sig-card {{ border: 2px dashed #1e3a8a; border-radius: 10px; padding: 10px 12px; background: linear-gradient(135deg, #f8fafc, #eff6ff); text-align: center; position: relative; }}
            .sig-card.customer {{ border-color: #b8956a; background: linear-gradient(135deg, #faf5ff, #f3e8ff); }}
            .sig-card .seal {{ position: absolute; top: 45%; left: 50%; transform: translate(-50%,-50%) rotate(-15deg); width: 80px; height: 80px; border: 3px solid rgba(16,185,129,0.14); border-radius: 50%; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 6.5px; font-weight: 900; color: rgba(16,185,129,0.18); text-transform: uppercase; letter-spacing: 0.8px; line-height: 1.2; pointer-events: none; }}
            .sig-title {{ font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; color: #1e3a8a; margin-bottom: 4px; position: relative; z-index: 1; }}
            .sig-card.customer .sig-title {{ color: #b8956a; }}
            .sig-subtitle {{ font-size: 8px; color: #64748b; margin-bottom: 5px; position: relative; z-index: 1; }}
            #signatureBarcode {{ max-width: 100%; background: #fff; padding: 3px 8px; border-radius: 4px; display: inline-block; border: 1px solid #e2e8f0; position: relative; z-index: 1; }}
            .sig-meta {{ font-size: 8.5px; color: #475569; margin-top: 4px; line-height: 1.4; position: relative; z-index: 1; }}
            .sig-verify {{ font-family: 'Courier New', monospace; font-size: 8px; color: #6b7280; text-align: center; margin-top: 2px; }}
            .sig-verify b {{ color: #1a2b47; }}
            .sign-space {{ height: 40px; border-bottom: 1.5px solid #b8956a; margin: 6px 6px 4px; position: relative; z-index: 1; display: flex; align-items: flex-end; justify-content: center; }}
            .sign-space .hint {{ font-size: 8px; color: #94a3b8; font-style: italic; padding-bottom: 2px; }}
            .sign-name {{ font-size: 9.5px; font-weight: 700; color: #1a2b47; margin-top: 4px; position: relative; z-index: 1; }}
            .customer-options {{ margin-top: 5px; font-size: 8px; color: #64748b; position: relative; z-index: 1; line-height: 1.5; }}

            .meterai-box {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-5deg);
                width: 75px;
                height: 55px;
                background: #e74c3c;
                border: 2px dashed #fff;
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-size: 8px;
                font-weight: bold;
                text-align: center;
                border-radius: 4px;
                z-index: 10;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }}
            .meterai-box .garuda {{ font-size: 14px; margin-bottom: 2px; }}
            .meterai-box .price {{ font-size: 10px; letter-spacing: 1px; }}

            .terms-section {{ padding: 10px 22px; background: #f9fafb; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; }}
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
                .page {{ box-shadow: none; border-radius: 0; max-width: 100%; width: 100%; border: none; }}
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

        <div class="page">
            <header class="hdr">
                <div class="brand">
                    <h1>Grace's Electronic</h1>
                    <div class="tag">Cash &amp; Credit · Authorized Retailer</div>
                    <div class="addr">Jl. Barong Tongkok, Kutai Barat • HP/WA: 0822-9954-8411</div>
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
                <div>Tenor: <b>{m_tenor} Bulan</b></div>
            </div>

            <div class="body">
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

                <div class="summary">
                    <div class="sum-card"><div class="lbl">Total Pembayaran</div><div class="val">{format_rp(total_keseluruhan)}</div></div>
                    <div class="sum-card green"><div class="lbl">DP Dibayar</div><div class="val">{format_rp(m_dp)}</div></div>
                    <div class="sum-card blue"><div class="lbl">Total Hutang</div><div class="val">{format_rp(m_total_hutang)}</div></div>
                    <div class="sum-card amber"><div class="lbl">Angsuran / Bulan</div><div class="val">{format_rp(m_cicilan)}</div></div>
                </div>

                <div class="tenor-options">
                    <div class="tenor-card recommended">
                        <div class="tc-label">Tenor Dipilih</div>
                        <div class="tc-title">Tenor {tenor_asli}× ({tenor_asli} Bulan)</div>
                        <div class="tc-row"><span class="k">Total Hutang (Pokok + Bunga)</span><span class="v">{format_rp(m_total_hutang)}</span></div>
                        <div class="tc-row main"><span class="k">Angsuran / bulan</span><span class="v">{format_rp(m_cicilan)}</span></div>
                    </div>
                </div>

                {html_schedule}

                <div class="sig-grid">
                    <div class="meterai-box">
                        <div class="garuda">🦅</div>
                        <div>METERAI</div>
                        <div class="price">10.000</div>
                    </div>

                    <div class="sig-card">
                        <div class="seal">GRACE'S<br>VERIFIED<br>★</div>
                        <div class="sig-title">✓ Tanda Tangan Toko</div>
                        <div class="sig-subtitle">Digital — Sah &amp; Terverifikasi</div>
                        <svg id="signatureBarcode"></svg>
                        <div class="sig-verify"><b>Kode:</b> GRC-{kid}-TN</div>
                        <div class="sig-verify"><b>Tgl:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}</div>
                    </div>
                    <div class="sig-card customer">
                        <div class="sig-title">✍ Tanda Tangan Customer</div>
                        <div class="sig-subtitle">Manual (basah) atau E-Sign</div>
                        <div class="sign-space"><span class="hint">[ Tanda tangan di sini ]</span></div>
                        <div class="sign-name">( {d['cn']} )</div>
                        <div class="customer-options"><b>Tenor:</b> ☐ {tenor_asli}x &nbsp; <b>Metode:</b> ☐ Manual ☐ E-Sign</div>
                    </div>
                </div>
            </div>

            <div class="terms-section">
                <div class="terms-title">Syarat &amp; Ketentuan</div>
                <ol class="terms-list">
                    <li><b>Metode:</b> Tunai atau transfer bank sesuai kesepakatan.</li>
                    <li><b>Jatuh Tempo:</b> Setiap 30 hari, dimulai {m_tempo.strftime('%d-%m-%Y')}.</li>
                    <li><b>Keterlambatan:</b> Denda {get_pengaturan_float("denda_per_hari_persen", 1.0)}% per hari dari angsuran.</li>
                </ol>
            </div>

            <footer class="footer">
                <div class="footer-brand">GRACE'S ELECTRONIC</div>
                <div>Bukti sah akad kredit. Mengikat setelah ditandatangani kedua pihak. Simpan untuk pembayaran berikutnya.</div>
                <div style="font-size:7.5px; margin-top:2px;">Pemalsuan dokumen dapat ditindak sesuai hukum yang berlaku di Republik Indonesia.</div>
            </footer>
        </div>
        
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

        components.html(invoice_html, height=1200, scrolling=True)
        
        st.info("💡 **Tips Cetak:** Jika saat mencetak (Print) layout di atas terpotong, silakan klik tombol **📥 Download File Slip (HTML)** di bawah ini. Buka file tersebut di browser (Chrome/Edge), lalu tekan **Ctrl+P** untuk mendapatkan hasil PDF yang 100% sempurna.")
        
        st.download_button(
            f"📥 Download File Slip (HTML)",
            data=invoice_html,
            file_name=f"Slip_Kredit_{kid}.html",
            mime="text/html",
            use_container_width=True
        )

        # ================= DOKUMEN PDF RESMI (OJK & E-METERAI) =================
        st.divider()
        st.markdown('<div class="section-header"><h3>📄 Dokumen PDF Resmi (Sesuai OJK)</h3></div>', unsafe_allow_html=True)
        st.info("💡 Fitur ini akan menghasilkan **satu file PDF lengkap** berisi: Invoice, Perjanjian Pembiayaan Konsumen (OJK), Lampiran KTP & KK, dan E-Meterai resmi.")
        
        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            pdf_ktp = st.file_uploader("Upload Foto KTP Pelanggan", type=["jpg", "jpeg", "png"], key="pdf_ktp")
        with col_pdf2:
            pdf_kk = st.file_uploader("Upload Foto KK Pelanggan", type=["jpg", "jpeg", "png"], key="pdf_kk")
            
        setuju_pdf = st.checkbox("Pelanggan telah membaca dan menyetujui seluruh isi Perjanjian Pembiayaan Konsumen.")
        
        if st.button("📥 Generate PDF Perjanjian & Invoice", use_container_width=True):
            if not pdf_ktp or not pdf_kk:
                st.error("❌ Wajib mengunggah Foto KTP dan KK!")
            elif not setuju_pdf:
                st.warning("⚠️ Centang persetujuan pelanggan terlebih dahulu.")
            else:
                with st.spinner("Membuat PDF..."):
                    # Prepare data dictionary for PDF function
                    pdf_data = {
                        'kid': kid,
                        'cn': d['cn'],
                        'telepon': d['telepon'],
                        'alamat': d['alamat'],
                        'pn': d['pn'],
                        'produk_id': d['produk_id'],
                        'harga_cash': m_harga_cash,
                        'dp': m_dp,
                        'pokok': m_pokok,
                        'total_hutang': m_total_hutang,
                        'cicilan': m_cicilan,
                        'tenor': m_tenor,
                        'schedule': []
                    }
                    
                    # Convert schedule to serializable and format dates
                    for _, row in edited_sched_1.iterrows():
                        pdf_data['schedule'].append({
                            'ke': row['ke'],
                            'jatuh_tempo': row['jatuh_tempo'].strftime('%d-%m-%Y'),
                            'angsuran': row['angsuran'],
                            'sisa': row['sisa']
                        })
                    
                    try:
                        pdf_bytes = generate_kredit_pdf(pdf_data, pdf_ktp, pdf_kk)
                        
                        st.success("✅ PDF berhasil dibuat! Silakan unduh di bawah ini.")
                        st.download_button(
                            label="⬇️ DOWNLOAD PDF (Invoice + Perjanjian)",
                            data=pdf_bytes,
                            file_name=f"Perjanjian_Kredit_{kid}_{d['cn'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"❌ Gagal membuat PDF: {e}")
