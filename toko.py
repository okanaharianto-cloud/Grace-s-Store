import streamlit as str
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. KONEKSI & STRUKTUR DATABASE ---
conn = sqlite3.connect('toko_kredit.db', check_same_thread=False)
c = conn.cursor()

# Membuat tabel-tabel jika belum ada
c.execute('''CREATE TABLE IF NOT EXISTS produk 
             (id INTEGER PRIMARY KEY, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in 
             (id INTEGER PRIMARY KEY, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS customer 
             (id INTEGER PRIMARY KEY, nama TEXT, telepon TEXT, alamat TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS kredit 
             (id INTEGER PRIMARY KEY, customer_id INTEGER, produk_id INTEGER, 
              harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, 
              cicilan_bulan REAL, sisa_hutang REAL, jatuh_tempo TEXT, status TEXT)''')

conn.commit()

# --- SINKRONISASI FUNGSI IMPORT / EXPORT ---
def export_to_csv(table_name):
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df.to_csv(index=False).encode('utf-8')

# --- TAMPILAN UTAMA APLIKASI ---
str.set_page_config(page_title="Sistem Toko & Kredit Kasir", layout="wide")
str.title("🏪 Sistem Manajemen Toko & Cicilan Kredit")

menu = [
    "1. Input Kategori & Skema Kredit", 
    "2. Input Barang Masuk (In)", 
    "3. Input Barang Keluar / Kredit (Out)", 
    "4. Data Customer", 
    "5. Stok Barang", 
    "6. Overdue & 7. Alert Kelayakan", 
    "8. Rekapan Database & Aksi (9-12)"
]
pilihan = str.sidebar.selectbox("Menu Navigasi", menu)

# --- FEATURE 1: INPUT KATEGORI & HITUNG SKEMA KREDIT ---
if pilihan == "1. Input Kategori & Skema Kredit":
    str.header("🧮 Input Produk & Kalkulator Kredit")
    
    nama_produk = str.text_input("Nama Barang")
    kategori = str.selectbox("Kategori", ["Elektronik", "Furnitur", "Gadget", "Motor", "Lainnya"])
    harga_modal = str.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0)
    stok_awal = str.number_input("Stok Awal", min_value=0, step=1)
    
    # Perhitungan otomatis berdasarkan formula cash/kredit Anda
    harga_cash = harga_modal * 1.05
    dp = harga_cash * 0.2
    pokok_hutang = harga_cash * 0.8
    total_hutang = pokok_hutang * 1.40
    cicilan_per_bulan = total_hutang / 6
    
    # Tampilkan simulasi angka
    col1, col2, col3 = str.columns(3)
    col1.metric("Harga Cash (Modal + 5%)", f"Rp {harga_cash:,.2f}")
    col2.metric("Uang Muka / DP (20%)", f"Rp {dp:,.2f}")
    col3.metric("Pokok Hutang / PH (80%)", f"Rp {pokok_hutang:,.2f}")
    
    col4, col5 = str.columns(2)
    col4.metric("Total Hutang (+ Bunga 40%)", f"Rp {total_hutang:,.2f}")
    col5.metric("Cicilan Bulanan (6 Bulan)", f"Rp {cicilan_per_bulan:,.2f}")
    
    if str.button("Simpan Produk ke Database"):
        if nama_produk:
            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", 
                      (nama_produk, kategori, harga_modal, stok_awal))
            conn.commit()
            str.success(f"Produk {nama_produk} berhasil ditambahkan!")
        else:
            str.warning("Nama barang tidak boleh kosong.")

# --- FEATURE 2: INPUT IN (BARANG MASUK) ---
elif pilihan == "2. Input Barang Masuk (In)":
    str.header("📥 Input Barang Masuk (Restock)")
    df_produk = pd.read_sql_query("SELECT id, nama FROM produk", conn)
    
    if not df_produk.empty:
        opsi_produk = {row['nama']: row['id'] for index, row in df_produk.iterrows()}
        pilih_produk = str.selectbox("Pilih Barang", list(opsi_produk.keys()))
        jumlah_masuk = str.number_input("Jumlah Masuk", min_value=1, step=1)
        
        if str.button("Tambah Stok"):
            p_id = opsi_produk[pilih_produk]
            c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)", 
                      (p_id, jumlah_masuk, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah_masuk, p_id))
            conn.commit()
            str.success("Stok berhasil diperbarui!")
    else:
        str.info("Belum ada produk terdaftar. Silakan input produk di Menu 1.")

# --- FEATURE 3: INPUT OUT (BARANG KELUAR / KREDIT) ---
elif pilihan == "3. Input Barang Keluar / Kredit (Out)":
    str.header("📤 Transaksi Keluar (Pengajuan Kredit Baru)")
    
    df_cust = pd.read_sql_query("SELECT id, nama FROM customer", conn)
    df_prod = pd.read_sql_query("SELECT id, nama, harga_modal, stok FROM produk WHERE stok > 0", conn)
    
    if df_cust.empty or df_prod.empty:
        str.warning("Pastikan Data Customer dan Stok Barang Tersedia terlebih dahulu!")
    else:
        opsi_cust = {row['nama']: row['id'] for _, row in df_cust.iterrows()}
        opsi_prod = {row['nama']: (row['id'], row['harga_modal']) for _, row in df_prod.iterrows()}
        
        pilih_c = str.selectbox("Pilih Customer", list(opsi_cust.keys()))
        pilih_p = str.selectbox("Pilih Barang yang Dikredit", list(opsi_prod.keys()))
        
        # Hitung ulang otomatis berdasarkan barang yang dipilih
        id_p, mod_p = opsi_prod[pilih_p]
        h_cash = mod_p * 1.05
        t_dp = h_cash * 0.2
        p_hut = h_cash * 0.8
        tot_hut = p_hut * 1.4
        c_bul = tot_hut / 6
        
        str.info(f"Detail Cicilan: Cicilan Rp {c_bul:,.2f}/bulan selama 6 bulan. DP wajib dibayar: Rp {t_dp:,.2f}")
        
        if str.button("Proses Kredit & Keluarkan Barang"):
            id_c = opsi_cust[pilih_c]
            tgl_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, 
                         total_hutang, cicilan_bulan, sisa_hutang, jatuh_tempo, status) 
                         VALUES (?,?,?,?,?,?,?,?,?,?)''', 
                      (id_c, id_p, h_cash, t_dp, p_hut, tot_hut, c_bul, tot_hut, tgl_tempo, "Berjalan"))
            
            c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
            conn.commit()
            str.success(f"Transaksi Berhasil! Barang {pilih_p} telah diserahkan kepada {pilih_c}.")

# --- FEATURE 4: CUSTOMER ---
elif pilihan == "4. Data Customer":
    str.header("👥 Manajemen Data Customer")
    
    with str.form("Form Customer"):
        n_cust = str.text_input("Nama Lengkap")
        t_cust = str.text_input("Nomor Telepon/WA")
        a_cust = str.text_area("Alamat Rumah")
        submit = str.form_submit_button("Simpan Data")
        
        if submit and n_cust:
            c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (n_cust, t_cust, a_cust))
            conn.commit()
            str.success("Data customer berhasil disimpan!")
            
    str.subheader("Daftar Customer Terdaftar")
    df_all_cust = pd.read_sql_query("SELECT * FROM customer", conn)
    str.dataframe(df_all_cust, use_container_width=True)

# --- FEATURE 5: STOK ---
elif pilihan == "5. Stok Barang":
    str.header("📦 Real-time Stok Gudang")
    df_stok = pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok FROM produk", conn)
    str.dataframe(df_stok, use_container_width=True)

# --- FEATURE 6 & 7: OVERDUE & ALERT ---
elif pilihan == "6. Overdue & 7. Alert Kelayakan":
    str.header("🚨 Peringatan Keterlambatan Bayar (Overdue)")
    
    tgl_sekarang = datetime.now().strftime("%Y-%m-%d")
    
    query_overdue = '''
    SELECT kredit.id, customer.nama, customer.telepon, kredit.total_hutang, 
           kredit.sisa_hutang, kredit.cicilan_bulan, kredit.jatuh_tempo
    FROM kredit 
    JOIN customer ON kredit.customer_id = customer.id
    WHERE kredit.status = 'Berjalan' AND kredit.jatuh_tempo < ?
    '''
    df_ov = pd.read_sql_query(query_overdue, conn, params=(tgl_sekarang,))
    
    if not df_ov.empty:
        str.error(f"⚠️ PERINGATAN: Ditemukan {len(df_ov)} Akun Kredit Overdue / Jatuh Tempo!")
        str.dataframe(df_ov, use_container_width=True)
        for _, r in df_ov.iterrows():
            str.warning(f"🔔 **ALERT**: Pelanggan **{r['nama']}** (WA: {r['telepon']}) melewati batas jatuh tempo ({r['jatuh_tempo']}). Tagihan bulanan: Rp {r['cicilan_bulan']:,.2f}")
    else:
        str.success("✅ Semua tagihan aman. Tidak ada customer yang overdue hari ini.")

# --- FEATURE 8, 9, 10, 11, 12: REKAPAN, CETAK, HAPUS, EXPORT, IMPORT ---
elif pilihan == "8. Rekapan Database & Aksi (9-12)":
    str.header("🗄️ Pusat Rekapan Data & Pemeliharaan Sistem")
    
    tabel_pilihan = str.selectbox("Pilih Data yang Ingin Dikelola", ["produk", "customer", "kredit"])
    df_rekapan = pd.read_sql_query(f"SELECT * FROM {tabel_pilihan}", conn)
    str.dataframe(df_rekapan, use_container_width=True)
    
    col1, col2 = str.columns(2)
    
    # Fitur 9 & 11: Cetak & Eksport (.CSV)
    with col1:
        str.subheader("📤 Fitur Cetak / Eksport")
        csv_data = export_to_csv(tabel_pilihan)
        str.download_button(
            label=f"Unduh / Cetak Data {tabel_pilihan.upper()} (.CSV)",
            data=csv_data,
            file_name=f"rekapan_{tabel_pilihan}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )
        
    # Fitur 10: Hapus Data
    with col2:
        str.subheader("🗑️ Fitur Hapus Data")
        if not df_rekapan.empty:
            id_hapus = str.number_input("Masukkan ID Data yang akan dihapus", min_value=int(df_rekapan['id'].min()), max_value=int(df_rekapan['id'].max()))
            if str.button("Hapus Permanen", type="primary"):
                c.execute(f"DELETE FROM {tabel_pilihan} WHERE id = ?", (id_hapus,))
                conn.commit()
                str.success(f"Data ID {id_hapus} berhasil dihapus!")
                str.rerun()

    # Fitur 12: Import Data
    str.markdown("---")
    str.subheader("📥 Fitur Import Database")
