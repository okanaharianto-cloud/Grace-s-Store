import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# =====================================================================
# 1. KONFIGURASI HALAMAN & DATABASE
# =====================================================================
st.set_page_config(page_title="Grace Store System", layout="wide", page_icon="🏪")

# Fungsi untuk koneksi ke database SQLite
def get_db_connection():
    conn = sqlite3.connect('grace_store.db', check_same_thread=False)
    return conn

# Fungsi untuk membuat tabel otomatis saat pertama kali dijalankan
def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabel Pengaturan Owner
    c.execute('''CREATE TABLE IF NOT EXISTS pengaturan (
        id INTEGER PRIMARY KEY,
        markup_default REAL DEFAULT 5.0,
        bunga_flat_6bln REAL DEFAULT 40.0,
        dp_minimal REAL DEFAULT 20.0,
        denda_harian REAL DEFAULT 0.40,
        pilihan_tenor TEXT DEFAULT '1,2,3,6,12,18,24'
    )''')
    
    # Tabel Kredit
    c.execute('''CREATE TABLE IF NOT EXISTS kredit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_customer TEXT,
        nama_produk TEXT,
        harga_barang REAL,
        dp_nominal REAL,
        tenor INTEGER,
        sisa_pokok REAL,
        total_bunga REAL,
        angsuran_bulanan REAL,
        status TEXT DEFAULT 'AKTIF',
        tanggal_transaksi TEXT
    )''')
    
    # Cek apakah data pengaturan sudah ada, kalau belum buat data default
    c.execute("SELECT COUNT(*) FROM pengaturan")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO pengaturan 
                     (markup_default, bunga_flat_6bln, dp_minimal, denda_harian, pilihan_tenor) 
                     VALUES (5.0, 40.0, 20.0, 0.40, '1,2,3,6,12,18,24')""")
    
    conn.commit()
    conn.close()

# Jalankan inisialisasi database
init_database()

# Fungsi mengambil data pengaturan
def ambil_pengaturan():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM pengaturan WHERE id=1", conn)
    conn.close()
    return df.iloc[0]

# =====================================================================
# 2. FUNGSI LOGIKA HITUNG KREDIT (TANPA INPUT MANUAL)
# =====================================================================
def hitung_kredit_otomatis(harga_barang, tenor_bulan, dp_persen, bunga_flat_6bln):
    # 1. Hitung DP (Down Payment)
    dp_nominal = harga_barang * (dp_persen / 100.0)
    
    # 2. Hitung Sisa Pokok (Harga Barang - DP)
    sisa_pokok = harga_barang - dp_nominal
    
    # 3. Hitung Bunga Flat
    # Jika bunga 6 bulan = 40%, maka bunga 1 bulan = 40 / 6 = 6.67%
    bunga_per_bulan_persen = bunga_flat_6bln / 6.0
    total_bunga = sisa_pokok * (bunga_per_bulan_persen / 100.0) * tenor_bulan
    
    # 4. Hitung Total Hutang & Angsuran
    total_hutang = sisa_pokok + total_bunga
    angsuran_per_bulan = total_hutang / tenor_bulan
    
    return dp_nominal, sisa_pokok, total_bunga, angsuran_per_bulan

# =====================================================================
# 3. TAMPILAN SIDEBAR (MENU KIRI)
# =====================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>👤 Administrator</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Role: ADMIN</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    menu = st.radio(
        "Menu Utama",
        [
            "🏠 Dashboard", 
            "⚙️ Pengaturan Owner", 
            "💳 Kredit Baru", 
            "👥 Data Customer", 
            "📦 Input Produk & Skema"
        ]
    )

# =====================================================================
# 4. HALAMAN: DASHBOARD
# =====================================================================
if menu == "🏠 Dashboard":
    # Header Banner
    st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px;">
            <h1 style="margin: 0; color: white;">🏠 Dashboard Utama</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">Selamat datang, Administrator 👋</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_db_connection()
    
    # Mengambil data statistik dari database
    df_kredit = pd.read_sql_query("SELECT * FROM kredit", conn)
    
    total_akun_kredit = len(df_kredit)
    
    # Jika belum ada transaksi, total piutang 0
    if total_akun_kredit > 0:
        total_piutang = df_kredit['sisa_pokok'].sum()
    else:
        total_piutang = 0
        
    conn.close()

    # Menampilkan Kotak Metrik
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="📦 TOTAL PRODUK", value="72 item")
    col2.metric(label="📥 TOTAL STOK", value="500 unit")
    col3.metric(label="👥 CUSTOMER", value="2 orang")
    col4.metric(label="🔴 KREDIT AKTIF", value=f"{total_akun_kredit} akun")
    
    st.write("") # Spasi
    
    col5, col6, col7 = st.columns(3)
    col5.metric(label="💰 TOTAL PIUTANG", value=f"Rp {total_piutang:,.0f}".replace(",", "."))
    col6.metric(label="⏳ PENDING SERAH TERIMA", value="0 akun")
    col7.metric(label="⚠️ OVERDUE", value="0 akun")

# =====================================================================
# 5. HALAMAN: PENGATURAN OWNER (Sesuai Screenshot)
# =====================================================================
elif menu == "⚙️ Pengaturan Owner":
    # Header Banner
    st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; color: white;">⚙️ Pengaturan Owner</h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Pengaturan ini adalah NILAI DEFAULT untuk transaksi baru.")
    
    set_data = ambil_pengaturan()
    
    # Membuat Tab
    tab1, tab2, tab3 = st.tabs(["📦 Markup", "📈 Bunga & DP", "⏱️ Denda & Tenor"])
    
    with tab1:
        st.subheader("Markup default non-pakaian (%)")
        markup_input = st.number_input("Markup (%)", value=float(set_data['markup_default']), step=0.1)
        if st.button("💾 Simpan Markup", type="primary"):
            conn = get_db_connection()
            conn.execute(f"UPDATE pengaturan SET markup_default={markup_input} WHERE id=1")
            conn.commit()
            conn.close()
            st.success("Markup berhasil disimpan!")
            
    with tab2:
        st.subheader("Bunga flat per 6 bulan (%)")
        bunga_input = st.number_input("Bunga Flat 6 Bulan (%)", value=float(set_data['bunga_flat_6bln']), step=1.0)
        
        st.subheader("DP minimal (%)")
        dp_input = st.number_input("DP Minimal (%)", value=float(set_data['dp_minimal']), step=1.0)
        
        if st.button("💾 Simpan Bunga & DP", type="primary"):
            conn = get_db_connection()
            conn.execute(f"UPDATE pengaturan SET bunga_flat_6bln={bunga_input}, dp_minimal={dp_input} WHERE id=1")
            conn.commit()
            conn.close()
            st.success("Bunga & DP berhasil disimpan!")

    with tab3:
        st.subheader("Denda per hari (%)")
        denda_input = st.number_input("Denda Harian (%)", value=float(set_data['denda_harian']), step=0.1)
        
        st.subheader("Pilihan tenor (pisahkan koma)")
        tenor_input = st.text_input("Pilihan Tenor (Contoh: 1,2,3,6,12)", value=set_data['pilihan_tenor'])
        
        if st.button("💾 Simpan Denda & Tenor", type="primary"):
            conn = get_db_connection()
            conn.execute(f"UPDATE pengaturan SET denda_harian={denda_input}, pilihan_tenor='{tenor_input}' WHERE id=1")
            conn.commit()
            conn.close()
            st.success("Denda & Tenor berhasil disimpan!")

# =====================================================================
# 6. HALAMAN: KREDIT BARU (HITUNG OTOMATIS TANPA MANUAL)
# =====================================================================
elif menu == "💳 Kredit Baru":
    st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; color: white;">💳 Simulasi & Input Kredit Baru</h1>
        </div>
    """, unsafe_allow_html=True)
    
    set_data = ambil_pengaturan()
    
    # Form Input Data
    with st.form("form_input_kredit"):
        col1, col2 = st.columns(2)
        
        with col1:
            nama_cust = st.text_input("Nama Customer", placeholder="Masukkan nama lengkap...")
            nama_barang = st.text_input("Nama Barang / Moda", placeholder="Contoh: Samsung A07 4/128")
            harga_barang = st.number_input("Harga Barang (Rp)", min_value=100000, step=100000, value=4200000)
            
        with col2:
            # Ambil pilihan tenor dari database
            list_tenor = [int(x.strip()) for x in str(set_data['pilihan_tenor']).split(',') if x.strip().isdigit()]
            tenor_pilihan = st.selectbox("Pilih Tenor (Bulan)", list_tenor)
            
            dp_persen = st.number_input(f"DP Minimal (%) - Default: {set_data['dp_minimal']}%", 
                                        value=float(set_data['dp_minimal']), step=1.0)
            st.write("---")
            st.write(f"**Bunga Flat Default:** {set_data['bunga_flat_6bln']}% per 6 bulan")
            
        # PROSES HITUNG OTOMATIS (Dijalankan otomatis berdasarkan input di atas)
        dp_nominal, sisa_pokok, total_bunga, angsuran = hitung_kredit_otomatis(
            harga_barang, tenor_pilihan, dp_persen, set_data['bunga_flat_6bln']
        )
        
        # Menampilkan Hasil Kalkulasi Otomatis ke Layar
        st.markdown("### 📊 Hasil Perhitungan Otomatis (Sistem)")
        
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Uang Muka (DP)", f"Rp {dp_nominal:,.0f}".replace(",", "."))
        r2.metric("Sisa Pokok", f"Rp {sisa_pokok:,.0f}".replace(",", "."))
        r3.metric("Total Bunga", f"Rp {total_bunga:,.0f}".replace(",", "."))
        r4.metric("Angsuran / Bulan", f"Rp {angsuran:,.0f}".replace(",", "."), delta="Otomatis")
        
        st.write("")
        submit = st.form_submit_button("💾 Simpan Transaksi Kredit Ini", type="primary")
        
        if submit:
            if nama_cust == "" or nama_barang == "":
                st.error("⚠️ Nama Customer dan Nama Barang wajib diisi!")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                tanggal_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Simpan ke database
                c.execute("""
                    INSERT INTO kredit (nama_customer, nama_produk, harga_barang, dp_nominal, tenor, sisa_pokok, total_bunga, angsuran_bulanan, tanggal_transaksi) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nama_cust, nama_barang, harga_barang, dp_nominal, tenor_pilihan, sisa_pokok, total_bunga, angsuran, tanggal_sekarang))
                
                conn.commit()
                conn.close()
                
                st.balloons()
                st.success(f"✅ Transaksi Berhasil Disimpan! Angsuran {nama_cust} adalah Rp {angsuran:,.0f}/bulan.".replace(",", "."))

# =====================================================================
# 7. MENU LAINNYA (PLACEHOLDER)
# =====================================================================
elif menu in ["👥 Data Customer", "📦 Input Produk & Skema"]:
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; color: white;">{menu}</h1>
        </div>
    """, unsafe_allow_html=True)
    st.warning("🚧 Halaman ini masih dalam tahap pengembangan.")
