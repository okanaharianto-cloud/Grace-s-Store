import streamlit as st
import sqlite3
import pandas as pd
import datetime
from datetime import datetime, timedelta
import hashlib
import os
import base64
import streamlit.components.v1 as components

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(page_title="Grace's Electronic - POS", page_icon="🏪", layout="wide")

ALAMAT_TOKO = "Jl. Sendawar Raya, Barong Tongkok, Kutai Barat, Kalimantan Timur"

# ==================== KONEKSI DATABASE ====================
def get_db():
    conn = sqlite3.connect('toko.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db()
c = conn.cursor()

# Buat folder untuk upload KTP
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ==================== FUNGSI HELPER ====================
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def format_rp(angka):
    try:
        return f"Rp {int(angka):,}".replace(",", ".")
    except:
        return "Rp 0"

def flash(pesan, tipe="success"):
    st.session_state['flash_msg'] = (pesan, tipe)

def log_aksi(username, aksi, detail):
    try:
        c.execute("INSERT INTO log_aktivitas (waktu, username, aksi, detail) VALUES (?,?,?,?)",
                  (get_current_time(), username, aksi, detail))
        conn.commit()
    except:
        pass

def get_pengaturan_float(key, default):
    try:
        c.execute("SELECT value FROM pengaturan WHERE key=?", (key,))
        row = c.fetchone()
        return float(row['value']) if row else default
    except:
        return default

def build_jadwal_angsuran(total_hutang, cicilan, tenor, tanggal_awal_str):
    try:
        tanggal_awal = datetime.strptime(tanggal_awal_str, "%Y-%m-%d")
    except:
        tanggal_awal = datetime.now()
    jadwal = []
    sisa = total_hutang
    for i in range(1, tenor + 1):
        bulan_baru = tanggal_awal.month + i
        tahun_baru = tanggal_awal.year + (bulan_baru - 1) // 12
        bulan_baru = (bulan_baru - 1) % 12 + 1
        tgl_jatuh_tempo = tanggal_awal.replace(year=tahun_baru, month=bulan_baru)
        
        angsuran = cicilan if i < tenor else sisa
        sisa -= angsuran
        jadwal.append({
            'ke': i,
            'jatuh_tempo': tgl_jatuh_tempo.strftime("%d-%m-%Y"),
            'angsuran': angsuran,
            'sisa': max(0, sisa)
        })
    return jadwal

def recalculate_kredit(kredit_id):
    c.execute("SELECT total_hutang, (SELECT COALESCE(SUM(jumlah_bayar),0) FROM pembayaran WHERE kredit_id=?) as total_bayar FROM kredit WHERE id=?", (kredit_id, kredit_id))
    row = c.fetchone()
    if row:
        sisa = row['total_hutang'] - row['total_bayar']
        status = "Lunas" if sisa <= 0 else "Berjalan"
        c.execute("UPDATE kredit SET sisa_hutang=?, status=? WHERE id=?", (sisa, status, kredit_id))
        conn.commit()

# ==================== INISIALISASI DATABASE ====================
def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, nama_lengkap TEXT, role TEXT, aktif INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customer (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, telepon TEXT, alamat TEXT, nik TEXT, tanggal_lahir TEXT, status_kawin TEXT, foto_ktp TEXT, foto_kk TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS produk (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, harga INTEGER, stok INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS kredit (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, produk_id INTEGER, tanggal_kredit TEXT, harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, cicilan_bulan REAL, tenor INTEGER, jatuh_tempo TEXT, status TEXT, sisa_hutang REAL, updated_at TEXT, updated_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pembayaran (id INTEGER PRIMARY KEY AUTOINCREMENT, kredit_id INTEGER, tanggal TEXT, jumlah_bayar REAL, denda REAL, keterangan TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pengaturan (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS log_aktivitas (id INTEGER PRIMARY KEY AUTOINCREMENT, waktu TEXT, username TEXT, aksi TEXT, detail TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", 
                  ("admin", hash_password("admin123"), "Administrator", "admin"))
    
    c.execute("INSERT OR IGNORE INTO pengaturan (key, value) VALUES ('denda_per_hari_persen', '1.0')")
    c.execute("INSERT OR IGNORE INTO pengaturan (key, value) VALUES ('bunga_flat_6bln_persen', '40.0')")
    conn.commit()

init_db()

# ==================== CSS KUSTOM ====================
st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; }
    .main-header h1 { margin: 0; font-size: 24px; }
    .main-header p { margin: 5px 0 0 0; font-size: 14px; opacity: 0.8; }
    .section-header h3 { border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)
# ==================== SISTEM LOGIN ====================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="main-header"><h1>🏪 Grace\'s Electronic</h1><p>Sistem Manajemen Toko & Kredit</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 🔐 Login Akses")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                c.execute("SELECT * FROM users WHERE username=? AND password=? AND aktif=1", (username, hash_password(password)))
                user = c.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user['username']
                    st.session_state.role = user['role']
                    st.session_state.nama_lengkap = user['nama_lengkap']
                    log_aksi(username, "LOGIN", "Berhasil login")
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah, atau akun nonaktif.")
    st.stop()

# ==================== NAVIGASI SIDEBAR ====================
with st.sidebar:
    st.markdown(f"### 👋 Halo, {st.session_state.nama_lengkap}")
    st.markdown(f"Role: **{st.session_state.role.upper()}**")
    st.divider()
    
    menu_admin = ["📊 Dashboard", "🛒 Jual Cash", "📤 Kredit Baru", "💳 Pembayaran Angsuran", "👥 Data Customer", "📦 Data Produk", "🖨️ Cetak Slip Kredit", "👤 Manajemen User", "📝 Log Aktivitas", "⚙️ Pengaturan"]
    menu_kasir = ["📊 Dashboard", "🛒 Jual Cash", "📤 Kredit Baru", "💳 Pembayaran Angsuran", "👥 Data Customer", "📦 Data Produk", "🖨️ Cetak Slip Kredit"]
    
    pilihan_menu = menu_admin if st.session_state.role == "admin" else menu_kasir
    pilihan = st.radio("Navigasi Menu", pilihan_menu)
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        log_aksi(st.session_state.username, "LOGOUT", "Keluar dari sistem")
        st.session_state.logged_in = False
        st.rerun()

# Tampilkan Flash Message
if 'flash_msg' in st.session_state:
    msg, tipe = st.session_state['flash_msg']
    if tipe == "success": st.success(msg)
    elif tipe == "error": st.error(msg)
    elif tipe == "warning": st.warning(msg)
    del st.session_state['flash_msg']

# ==================== KONTEN MENU ====================

# 1. DASHBOARD
if pilihan == "📊 Dashboard":
    st.markdown('<div class="main-header"><h1>📊 Dashboard</h1><p>Ringkasan Aktivitas Toko</p></div>', unsafe_allow_html=True)
    
    df_k = pd.read_sql_query("SELECT COUNT(*) as total, SUM(sisa_hutang) as piutang FROM kredit WHERE status='Berjalan'", conn)
    df_cash = pd.read_sql_query("SELECT COUNT(*) as total, SUM(total_hutang) as pendapatan FROM kredit WHERE status='Lunas'", conn) 
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Kredit Aktif", f"{df_k['total'][0]} Transaksi", f"Piutang: {format_rp(df_k['piutang'][0] or 0)}")
    col2.metric("Kredit Lunas", f"{df_cash['total'][0]} Transaksi", f"Total: {format_rp(df_cash['pendapatan'][0] or 0)}")
    
    st.markdown("### 📅 Jatuh Tempo Terdekat")
    df_tempo = pd.read_sql_query("SELECT k.id, c.nama, k.jatuh_tempo, k.cicilan_bulan FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan' ORDER BY k.jatuh_tempo ASC LIMIT 5", conn)
    st.dataframe(df_tempo, use_container_width=True, hide_index=True)

# 2. JUAL CASH
elif pilihan == "🛒 Jual Cash":
    st.markdown('<div class="main-header"><h1>🛒 Jual Cash</h1></div>', unsafe_allow_html=True)
    st.info("Silakan pilih produk dan customer untuk transaksi tunai.")
    
    with st.form("form_cash"):
        df_p = pd.read_sql_query("SELECT id, nama, harga FROM produk WHERE stok > 0", conn)
        df_cst = pd.read_sql_query("SELECT id, nama FROM customer", conn)
        if df_p.empty or df_cst.empty:
            st.warning("Data produk atau customer kosong. Silakan tambah di menu Data Master.")
        else:
            p_opts = {f"{r['nama']} - {format_rp(r['harga'])}": r['id'] for _, r in df_p.iterrows()}
            c_opts = {r['nama']: r['id'] for _, r in df_cst.iterrows()}
            
            sel_prod = st.selectbox("Pilih Produk", list(p_opts.keys()))
            sel_cust = st.selectbox("Pilih Customer", list(c_opts.keys()))
            jml_bayar = st.number_input("Jumlah Uang Diterima (Rp)", min_value=0)
            
            if st.form_submit_button("Proses Pembelian Cash"):
                # Logika sederhana: Catat sebagai kredit lunas di database
                prod_id = p_opts[sel_prod]
                cust_id = c_opts[sel_cust]
                harga = df_p[df_p['id']==prod_id]['harga'].values[0]
                
                tgl_sekarang = datetime.now().strftime("%Y-%m-%d")
                c.execute("""INSERT INTO kredit 
                             (customer_id, produk_id, tanggal_kredit, harga_cash, dp, pokok_hutang, total_hutang, cicilan_bulan, tenor, jatuh_tempo, status, sisa_hutang) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (cust_id, prod_id, tgl_sekarang, harga, harga, 0, harga, 0, 1, tgl_sekarang, "Lunas", 0))
                c.execute("UPDATE produk SET stok = stok - 1 WHERE id=?", (prod_id,))
                conn.commit()
                flash("✅ Transaksi Cash berhasil diproses!", "success")
                st.rerun()

# 3. KREDIT BARU
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Kredit Baru</h1></div>', unsafe_allow_html=True)
    
    with st.form("form_kredit_baru"):
        df_cst = pd.read_sql_query("SELECT id, nama, nik FROM customer", conn)
        df_p = pd.read_sql_query("SELECT id, nama, harga FROM produk WHERE stok > 0", conn)
        
        if df_cst.empty or df_p.empty:
            st.warning("⚠️ Anda harus menambahkan Customer dan Produk terlebih dahulu di menu masing-masing.")
        else:
            c_opts = {r['nama']: r['id'] for _, r in df_cst.iterrows()}
            p_opts = {r['nama']: (r['id'], r['harga']) for _, r in df_p.iterrows()}
            
            col1, col2 = st.columns(2)
            with col1:
                cust_pilih = st.selectbox("Pilih Customer", list(c_opts.keys()))
                prod_pilih = st.selectbox("Pilih Produk", list(p_opts.keys()))
                harga_cash = p_opts[prod_pilih][1]
                st.number_input("Harga Cash", value=float(harga_cash), disabled=True)
            with col2:
                dp = st.number_input("DP (Uang Muka)", min_value=0.0, value=float(harga_cash*0.3))
                tenor = st.number_input("Tenor (Bulan)", min_value=1, value=6)
                bunga = st.number_input("Bunga Flat (%)", value=40.0) / 100
                
            pokok = harga_cash - dp
            total_hutang = round(pokok * (1 + bunga), -2)
            cicilan = round(total_hutang / tenor, -2)
            
            st.markdown(f"**Pokok Hutang:** {format_rp(pokok)}")
            st.markdown(f"**Total Hutang (termasuk bunga):** {format_rp(total_hutang)}")
            st.markdown(f"**Angsuran per Bulan:** {format_rp(cicilan)}")
            
            if st.form_submit_button("Simpan Kredit", use_container_width=True):
                try:
                    cust_id = c_opts[cust_pilih]
                    prod_id = p_opts[prod_pilih][0]
                    tgl_sekarang = datetime.now().strftime("%Y-%m-%d")
                    jt = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    
                    c.execute("""INSERT INTO kredit 
                                 (customer_id, produk_id, tanggal_kredit, harga_cash, dp, pokok_hutang, total_hutang, cicilan_bulan, tenor, jatuh_tempo, status, sisa_hutang) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (cust_id, prod_id, tgl_sekarang, harga_cash, dp, pokok, total_hutang, cicilan, tenor, jt, "Berjalan", total_hutang))
                    c.execute("UPDATE produk SET stok = stok - 1 WHERE id=?", (prod_id,))
                    conn.commit()
                    flash("✅ Kredit baru berhasil disimpan!", "success")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")

# 4. DATA CUSTOMER
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Customer</h1></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Tambah Baru", "Daftar Customer"])
    
    with tab1:
        with st.form("form_cust"):
            nama = st.text_input("Nama Lengkap")
            telp = st.text_input("Telepon/WA")
            alamat = st.text_area("Alamat")
            nik = st.text_input("NIK")
            tgl_lahir = st.date_input("Tanggal Lahir", value=datetime(1990,1,1))
            status_kawin = st.selectbox("Status Kawin", ["Belum Menikah", "Menikah", "Cerai"])
            
            if st.form_submit_button("Simpan Customer"):
                if nama:
                    c.execute("INSERT INTO customer (nama, telepon, alamat, nik, tanggal_lahir, status_kawin) VALUES (?,?,?,?,?,?)",
                              (nama, telp, alamat, nik, tgl_lahir.strftime("%Y-%m-%d"), status_kawin))
                    conn.commit()
                    flash("✅ Customer berhasil ditambahkan!", "success")
                    st.rerun()
    with tab2:
        df_c = pd.read_sql_query("SELECT id, nama, telepon, alamat FROM customer", conn)
        st.dataframe(df_c, use_container_width=True, hide_index=True)

# 5. DATA PRODUK
elif pilihan == "📦 Data Produk":
    st.markdown('<div class="main-header"><h1>📦 Data Produk</h1></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Tambah Baru", "Daftar Produk"])
    with tab1:
        with st.form("form_prod"):
            nama_p = st.text_input("Nama Produk")
            harga_p = st.number_input("Harga", min_value=0)
            stok_p = st.number_input("Stok", min_value=0)
            if st.form_submit_button("Simpan Produk"):
                if nama_p:
                    c.execute("INSERT INTO produk (nama, harga, stok) VALUES (?,?,?)", (nama_p, harga_p, stok_p))
                    conn.commit()
                    flash("✅ Produk ditambahkan!", "success")
                    st.rerun()
    with tab2:
        df_p = pd.read_sql_query("SELECT id, nama, harga, stok FROM produk", conn)
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        # 6. PEMBAYARAN ANGSURAN
elif pilihan == "💳 Pembayaran Angsuran":
    st.markdown('<div class="main-header"><h1>💳 Pembayaran Angsuran</h1></div>', unsafe_allow_html=True)
    
    df_k = pd.read_sql_query("SELECT k.id, c.nama, k.sisa_hutang FROM kredit k JOIN customer c ON k.customer_id=c.id WHERE k.status='Berjalan'", conn)
    if df_k.empty:
        st.info("Tidak ada kredit berjalan.")
    else:
        k_opts = {f"#{r['id']} - {r['nama']} (Sisa: {format_rp(r['sisa_hutang'])})": r['id'] for _, r in df_k.iterrows()}
        pilih_k = st.selectbox("Pilih Kredit", list(k_opts.keys()))
        k_id = k_opts[pilih_k]
        
        with st.form("form_bayar"):
            jml = st.number_input("Jumlah Bayar", min_value=0.0)
            ket = st.text_input("Keterangan")
            if st.form_submit_button("Proses Pembayaran"):
                try:
                    c.execute("INSERT INTO pembayaran (kredit_id, tanggal, jumlah_bayar, keterangan) VALUES (?,?,?,?)",
                              (k_id, get_current_time(), jml, ket))
                    recalculate_kredit(k_id)
                    conn.commit()
                    flash("✅ Pembayaran berhasil dicatat!", "success")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")

# 7. CETAK SLIP KREDIT (FULL HTML OJK)
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
        with st.expander("Buka Form Edit Manual (Tersimpan Permanen ke Database)", expanded=False):
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
                    flash("✅ Perubahan berhasil disimpan permanen ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

        df_bayar = pd.read_sql_query("SELECT id, tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id", conn, params=(kid,))
        tanggal_kredit_str = d['tanggal_kredit'] if pd.notna(d['tanggal_kredit']) else (datetime.strptime(d['jatuh_tempo'], "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        
        tenor_asli = int(m_tenor)
        rate_bulan = m_bunga_bln / 100
        
        tampilkan_banding = st.toggle("Tampilkan Perbandingan 2 Tenor (Opsi A & B)", value=True)
        
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
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL KEWAJIBAN</td><td class="r">{format_rp(total_1)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody></table>
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
                    <div class="addr">{ALAMAT_TOKO}<br>HP/WA: 0822-9954-8411</div>
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
                    <div class="sum-card green"><div class="lbl">DP Dibayar</div><div class="val">{format_rp(m_dp)}</div></div>
                    <div class="sum-card amber"><div class="lbl">Angsuran / Bulan</div><div class="val">{format_rp(m_cicilan)}</div></div>
                </div>
                {html_tenor_options}
                {html_schedule}
                <div class="note-text">*Catatan: DP {format_rp(m_dp)} telah diterima. Pokok {format_rp(m_pokok)} diangsur sesuai tenor yang dipilih. Terdapat Biaya Administrasi/Materai sebesar <b>Rp 10.000</b> (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir. Total yang disetor pada bulan ke-{tenor_asli} adalah {format_rp(cicilan_terakhir)}.</div>
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
                    <div class="addr">{ALAMAT_TOKO}<br>HP/WA: 0822-9954-8411</div>
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
                    JsBarcode("#signatureBarcode", "PSrE-ADI-HARIANTO-2026", {{ format: "CODE128", width: 1.0, height: 25, displayValue: false, margin: 0, lineColor: "#0f172a", background: "#ffffff" }});
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
        # 8. MANAJEMEN USER (Khusus Admin)
elif pilihan == "👤 Manajemen User" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Tambah User Baru", "📋 Daftar & Edit User"])
    
    with tab1:
        with st.form("form_add_user"):
            col1, col2 = st.columns(2)
            with col1:
                new_u = st.text_input("Username")
                new_p = st.text_input("Password", type="password")
            with col2:
                new_nama = st.text_input("Nama Lengkap")
                new_role = st.selectbox("Role", ["admin", "kasir"])
                
            if st.form_submit_button("💾 Simpan User"):
                if new_u and new_p and new_nama:
                    try:
                        c.execute("INSERT INTO users (username, password, nama_lengkap, role) VALUES (?,?,?,?)", 
                                  (new_u, hash_password(new_p), new_nama, new_role))
                        conn.commit()
                        flash(f"✅ User {new_u} berhasil ditambahkan!", "success")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Username sudah digunakan!")
                    except Exception as e:
                        st.error(f"❌ Gagal: {e}")
                else:
                    st.warning("Semua field wajib diisi!")
                    
    with tab2:
        df_users = pd.read_sql_query("SELECT id, username, nama_lengkap, role, aktif FROM users", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### ✏️ Edit / Nonaktifkan User")
        opsi_user = {f"{r['username']} - {r['nama_lengkap']} ({r['role']})": r['id'] for _, r in df_users.iterrows()}
        
        if opsi_user:
            pilih_user = st.selectbox("Pilih User", list(opsi_user.keys()))
            uid = opsi_user[pilih_user]
            
            row_u = c.execute("SELECT username, nama_lengkap, role, aktif FROM users WHERE id=?", (uid,)).fetchone()
            
            with st.form("form_edit_user"):
                colA, colB = st.columns(2)
                with colA:
                    edit_nama = st.text_input("Nama Lengkap", value=row_u['nama_lengkap'])
                    edit_role = st.selectbox("Role", ["admin", "kasir"], index=0 if row_u['role'] == "admin" else 1)
                with colB:
                    edit_aktif = st.selectbox("Status", [1, 0], index=0 if row_u['aktif'] == 1 else 1, format_func=lambda x: "Aktif" if x == 1 else "Nonaktif")
                    edit_pw = st.text_input("Password Baru (biarkan kosong jika tidak diubah)", type="password")
                    
                if st.form_submit_button("💾 Update User"):
                    try:
                        if edit_pw:
                            c.execute("UPDATE users SET nama_lengkap=?, role=?, aktif=?, password=? WHERE id=?", (edit_nama, edit_role, edit_aktif, hash_password(edit_pw), uid))
                        else:
                            c.execute("UPDATE users SET nama_lengkap=?, role=?, aktif=? WHERE id=?", (edit_nama, edit_role, edit_aktif, uid))
                        conn.commit()
                        flash("✅ Data user berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal: {e}")

# 9. LOG AKTIVITAS (Khusus Admin)
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas Sistem</h1></div>', unsafe_allow_html=True)
    st.info("Menampilkan 200 aktivitas terakhir di dalam sistem.")
    
    df_log_main = pd.read_sql_query("SELECT waktu, username, aksi, detail FROM log_aktivitas ORDER BY id DESC LIMIT 200", conn)
    st.dataframe(df_log_main, use_container_width=True, hide_index=True)

# 10. PENGATURAN (Khusus Admin)
elif pilihan == "⚙️ Pengaturan" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Aplikasi</h1></div>', unsafe_allow_html=True)
    
    st.markdown("### ⚙️ Pengaturan Bunga & Denda Default")
    with st.form("form_pengaturan"):
        bunga_default = st.number_input("Bunga Flat Default (6 Bulan) %", value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0)
        denda_default = st.number_input("Denda Keterlambatan / Hari (%)", value=get_pengaturan_float("denda_per_hari_persen", 1.0), step=0.1)
        
        if st.form_submit_button("💾 Simpan Pengaturan"):
            try:
                c.execute("UPDATE pengaturan SET value=? WHERE key=?", (str(bunga_default), "bunga_flat_6bln_persen"))
                c.execute("UPDATE pengaturan SET value=? WHERE key=?", (str(denda_default), "denda_per_hari_persen"))
                conn.commit()
                flash("✅ Pengaturan berhasil disimpan!", "success")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal: {e}")

    st.markdown("---")
    st.markdown("### ℹ️ Informasi Toko")
    st.write(f"**Nama Toko:** Grace's Electronic")
    st.write(f"**Alamat:** {ALAMAT_TOKO}")
    st.write("**Aplikasi Versi:** 1.0.0 (Standard OJK Edition)")
    
