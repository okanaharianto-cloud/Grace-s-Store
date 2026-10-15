import streamlit as str
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. KONEKSI & STRUKTUR DATABASE ---
conn = sqlite3.connect('toko_kredit.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS produk 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kategori TEXT, harga_modal REAL, stok INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS transaksi_in 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, produk_id INTEGER, jumlah INTEGER, tanggal TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customer 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, telepon TEXT, alamat TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS kredit 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, produk_id INTEGER, 
              harga_cash REAL, dp REAL, pokok_hutang REAL, total_hutang REAL, 
              tenor INTEGER, cicilan_bulan REAL, sisa_hutang REAL, jatuh_tempo TEXT, status TEXT)''')
conn.commit()

def export_to_csv(table_name):
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df.to_csv(index=False).encode('utf-8')

# --- TAMPILAN UTAMA APLIKASI ---
str.set_page_config(page_title="Sistem Toko & Kredit Kasir", layout="wide")
str.title("🏪 Sistem Manajemen Toko & Cicilan Kredit Fleksibel Pro")

menu = [
    "1. Input Kategori & Skema Kredit", 
    "2. Input Barang Masuk (In)", 
    "3. Input Barang Keluar / Kredit (Out)", 
    "4. Data Customer", 
    "5. Stok Barang", 
    "6. Overdue", 
    "7. Alert Kelayakan", 
    "8. Rekapan Database",
    "9. Cetak Nota Transaksi",
    "10. Hapus Data",
    "11. Eksport CSV (Download)",
    "12. Import CSV (Unggah)"
]
pilihan = str.sidebar.selectbox("Menu Navigasi", menu)

# --- FEATURE 1: INPUT KATEGORI & KALKULATOR FLEKSIBEL ---
if pilihan == "1. Input Kategori & Skema Kredit":
    str.header("🧮 Input Produk & Kalkulator Simulasi Fleksibel")
    nama_produk = str.text_input("Nama Barang")
    kategori = str.selectbox("Kategori", ["Gadget", "Elektronik", "Furnitur", "Motor", "Lainnya"])
    harga_modal = str.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0)
    stok_awal = str.number_input("Stok Awal", min_value=0, step=1)
    
    harga_cash = round(harga_modal * 1.05, -2)
    dp_minimal = round(harga_cash * 0.2, -2)
    
    str.markdown("---")
    str.subheader("⚙️ Parameter Kredit Fleksibel (DP & Tenor)")
    
    col_input1, col_input2 = str.columns(2)
    with col_input1:
        dp_input = str.number_input(f"Uang Muka / DP (Minimal: Rp {dp_minimal:,.2f})", min_value=float(dp_minimal), value=float(dp_minimal), step=50000.0)
    with col_input2:
        tenor_pilihan = str.selectbox("Pilih Tenor Cicilan (Bulan)", [1, 2, 3, 6, 12, 18, 24], index=3)
    
    rate_bunga_per_bulan = 0.40 / 6
    persen_bunga_custom = rate_bunga_per_bulan * tenor_pilihan
    
    pokok_hutang = round(harga_cash - dp_input, -2)
    total_hutang = round(pokok_hutang * (1 + persen_bunga_custom), -2)
    cicilan_per_bulan = round(total_hutang / tenor_pilihan, -2)
    
    col1, col2, col3 = str.columns(3)
    col1.metric("Harga Cash (Modal + 5%)", f"Rp {harga_cash:,.0f}")
    col2.metric("DP yang Diinput", f"Rp {dp_input:,.0f}")
    col3.metric("Pokok Hutang (PH Baru)", f"Rp {pokok_hutang:,.0f}")
    
    col4, col5 = str.columns(2)
    col4.metric(f"Total Hutang (+Bunga {persen_bunga_custom*100:.1f}%)", f"Rp {total_hutang:,.0f}")
    col5.metric(f"Cicilan Bulanan ({tenor_pilihan}x)", f"Rp {cicilan_per_bulan:,.0f}")
    
    if str.button("Simpan Produk ke Database"):
        if nama_produk:
            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", (nama_produk, kategori, harga_modal, stok_awal))
            conn.commit()
            str.success(f"Produk {nama_produk} berhasil dimasukkan!")
        else:
            str.warning("Nama barang wajib diisi.")

# --- FEATURE 2: INPUT IN ---
elif pilihan == "2. Input Barang Masuk (In)":
    str.header("📥 Input Barang Masuk (Restock)")
    df_produk = pd.read_sql_query("SELECT id, nama FROM produk", conn)
    if not df_produk.empty:
        opsi_produk = {row['nama']: row['id'] for index, row in df_produk.iterrows()}
        pilih_produk = str.selectbox("Pilih Barang", list(opsi_produk.keys()))
        jumlah_masuk = str.number_input("Jumlah Masuk", min_value=1, step=1)
        if str.button("Tambah Stok"):
            p_id = opsi_produk[pilih_produk]
            c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)", (p_id, jumlah_masuk, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah_masuk, p_id))
            conn.commit()
            str.success("Stok gudang berhasil ditambahkan!")
    else:
        str.info("Belum ada produk terdaftar.")

# --- FEATURE 3: INPUT OUT ---
elif pilihan == "3. Input Barang Keluar / Kredit (Out)":
    str.header("📤 Transaksi Keluar (Pengajuan Kredit Baru)")
    df_cust = pd.read_sql_query("SELECT id, nama FROM customer", conn)
    df_prod = pd.read_sql_query("SELECT id, nama, harga_modal, stok FROM produk WHERE stok > 0", conn)
    if df_cust.empty or df_prod.empty:
        str.warning("Pastikan Data Customer dan Stok Barang Tersedia!")
    else:
        opsi_cust = {row['nama']: row['id'] for _, row in df_cust.iterrows()}
        opsi_prod = {row['nama']: (row['id'], row['harga_modal']) for _, row in df_prod.iterrows()}
        pilih_c = str.selectbox("Pilih Customer", list(opsi_cust.keys()))
        pilih_p = str.selectbox("Pilih Barang yang Dikredit", list(opsi_prod.keys()))
        
        id_p, mod_p = opsi_prod[pilih_p]
        h_cash = round(mod_p * 1.05, -2)
        dp_min_transaksi = round(h_cash * 0.2, -2)
        
        str.markdown("---")
        col_t1, col_t2 = str.columns(2)
        with col_t1:
            dp_transaksi = str.number_input(f"Besar DP dari Cust (Min: Rp {dp_min_transaksi:,.0f})", min_value=float(dp_min_transaksi), value=float(dp_min_transaksi), step=50000.0)
        with col_t2:
            tenor_transaksi = str.selectbox("Pilih Jangka Waktu Tenor (Bulan)", [1, 2, 3, 6, 12, 18, 24], index=3)
            
        rate_bunga_per_bulan = 0.40 / 6
        bunga_final = rate_bunga_per_bulan * tenor_transaksi
        p_hut = round(h_cash - dp_transaksi, -2)
        tot_hut = round(p_hut * (1 + bunga_final), -2)
        c_bul = round(tot_hut / tenor_transaksi, -2)
        
        str.info(f"🧾 Akad Terkalkulasi: Tenor {tenor_transaksi} Bulan | Cicilan: Rp {c_bul:,.0f}/bulan | DP Masuk: Rp {dp_transaksi:,.0f}")
        if str.button("Proses Kredit & Keluarkan Barang"):
            id_c = opsi_cust[pilih_c]
            tgl_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (id_c, id_p, h_cash, dp_transaksi, p_hut, tot_hut, tenor_transaksi, c_bul, tot_hut, tgl_tempo, "Berjalan"))
            c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
            conn.commit()
            str.success(f"Akad Kredit Fleksibel Sukses! Cetak nota Anda sekarang di Menu 9.")

# --- FEATURE 4: CUSTOMER ---
elif pilihan == "4. Data Customer":
    str.header("👥 Data Pelanggan")
    with str.form("Form Customer"):
        n_cust = str.text_input("Nama Lengkap")
        t_cust = str.text_input("Nomor Telepon/WA")
        a_cust = str.text_area("Alamat Rumah")
        submit = str.form_submit_button("Simpan Data")
        if submit and n_cust:
            c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)", (n_cust, t_cust, a_cust))
            conn.commit()
            str.success("Data customer berhasil disimpan!")
    str.dataframe(pd.read_sql_query("SELECT * FROM customer", conn), use_container_width=True)

# --- FEATURE 5: STOK ---
elif pilihan == "5. Stok Barang":
    str.header("📦 Real-time Stok Gudang")
    str.dataframe(pd.read_sql_query("SELECT id, nama, kategori, harga_modal, stok FROM produk", conn), use_container_width=True)

# --- FEATURE 6: OVERDUE ---
elif pilihan == "6. Overdue":
    str.header("🚨 Data Pelanggan Telat Bayar (Overdue)")
    tgl_sekarang = datetime.now().strftime("%Y-%m-%d")
    query_overdue = '''SELECT kredit.id, customer.nama, customer.telepon, kredit.total_hutang, kredit.tenor, kredit.cicilan_bulan, kredit.jatuh_tempo FROM kredit JOIN customer ON kredit.customer_id = customer.id WHERE kredit.status = 'Berjalan' AND kredit.jatuh_tempo < ?'''
    df_ov = pd.read_sql_query(query_overdue, conn, params=(tgl_sekarang,))
    if not df_ov.empty:
        str.dataframe(df_ov, use_container_width=True)
    else:
        str.success("✅ Tidak ada akun yang overdue hari ini.")

# --- FEATURE 7: ALERT KELAYAKAN ---
elif pilihan == "7. Alert Kelayakan":
    str.header("🔔 Peringatan Alert Keterlambatan Real-time")
    tgl_sekarang = datetime.now().strftime("%Y-%m-%d")
    query_overdue = '''SELECT customer.nama, customer.telepon, kredit.cicilan_bulan, kredit.tenor, kredit.jatuh_tempo FROM kredit JOIN customer ON kredit.customer_id = customer.id WHERE kredit.status = 'Berjalan' AND kredit.jatuh_tempo < ?'''
    df_ov = pd.read_sql_query(query_overdue, conn, params=(tgl_sekarang,))
    if not df_ov.empty:
        for _, r in df_ov.iterrows():
            str.error(f"⚠️ **ALERT KELAYAKAN**: Pelanggan **{r['nama']}** (WA: {r['telepon']}) sudah jatuh tempo pada {r['jatuh_tempo']}. Tenor: {r['tenor']}Bln. Angsuran: Rp {r['cicilan_bulan']:,.0f}")
    else:
        str.success("✅ Status Kelayakan Kredit Toko Aman Terkendali.")

# --- FEATURE 8: REKAPAN ---
elif pilihan == "8. Rekapan Database":
    str.header("📊 Rekapan Isi Database")
    tabel_pilihan = str.selectbox("Pilih Tabel Data", ["produk", "customer", "kredit"])
