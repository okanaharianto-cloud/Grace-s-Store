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

# --- 2. FITUR OTOMATIS DATA BROSUR ---
def tanam_data_brosur_otomatis():
    c.execute("SELECT COUNT(*) FROM produk")
    if c.fetchone()[0] == 0:
        data_ponsel = [
            ("iPhone 17 256GB", "Gadget", 19046700, 10),
            ("iPhone 17 512GB", "Gadget", 22141900, 10),
            ("iPhone 17 PRO 256GB", "Gadget", 20951400, 10),
            ("iPhone 17 PRO 512GB", "Gadget", 25237100, 10),
            ("iPhone 17 PRO 1TB", "Gadget", 29761000, 10),
            ("iPhone 17 PRO MAX 256GB", "Gadget", 22856200, 10),
            ("iPhone 17 PRO MAX 512GB", "Gadget", 27141900, 10),
            ("iPhone 17 PRO MAX 1TB", "Gadget", 31427600, 10),
            ("iPhone 17 PRO MAX 2TB", "Gadget", 40237100, 10),
            ("iPhone 17 AIR 256GB", "Gadget", 15951400, 10),
            ("iPhone 17 AIR 512GB", "Gadget", 20237100, 10),
            ("iPhone 17 AIR 1TB", "Gadget", 23618100, 10),
            ("iPhone 17e 256GB", "Gadget", 12380000, 10),
            ("iPhone 17e 512GB", "Gadget", 16475200, 10),
            ("iPhone 16 128GB", "Gadget", 15951400, 10),
            ("iPhone 16 256GB", "Gadget", 16903800, 10),
            ("iPhone 16 PLUS 128GB", "Gadget", 15141900, 10),
            ("iPhone 16 PLUS 256GB", "Gadget", 16380000, 10),
            ("iPhone 15 128GB", "Gadget", 13332400, 10),
            ("Galaxy S26 Ultra 256GB", "Gadget", 23332400, 10),
            ("Galaxy S26 Ultra 512GB", "Gadget", 26189500, 10),
            ("Galaxy S26 Ultra 1TB", "Gadget", 30475200, 10),
            ("Galaxy S26+ 256GB", "Gadget", 18570500, 10),
            ("Galaxy S26+ 512GB", "Gadget", 21427600, 10),
            ("Galaxy S26 256GB", "Gadget", 15713300, 10),
            ("Galaxy S25 Ultra 256GB", "Gadget", 18570500, 10),
            ("Reno 16 Pro 256GB", "Gadget", 14284800, 10),
            ("Reno 16 256GB (8GB)", "Gadget", 11427600, 10),
            ("Reno 16 256GB (12GB)", "Gadget", 12380000, 10),
            ("Reno 16 F 128GB", "Gadget", 7618100, 10),
            ("Find X9 Ultra", "Gadget", 26665700, 10),
            ("OPPO A6 128GB", "Gadget", 3808600, 10)
        ]
        c.executemany("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", data_ponsel)
        conn.commit()

tanam_data_brosur_otomatis()

# --- TAMPILAN UTAMA APLIKASI ---
str.set_page_config(page_title="Sistem Toko & Kredit Kasir", layout="wide")
str.title("🏪 Sistem Manajemen Toko & Cicilan Kredit")

menu = [
    "1. Input Kategori & Skema Kredit", 
    "2. Input Barang Masuk (In)", 
    "3. Input Barang Keluar / Kredit (Out)", 
    "4. Data Customer", 
    "5. Stok Barang", 
    "6. Overdue", 
    "7. Alert Kelayakan",
    "8. Cetak, Ekspor & Impor"
]
pilihan = str.sidebar.selectbox("Menu Navigasi", menu)

# --- FEATURE 1: INPUT MANUAL BARANG ---
if pilihan == "1. Input Kategori & Skema Kredit":
    str.header("🧮 Input Produk & Kalkulator Simulasi Fleksibel")
    str.success("💡 INFO SISTEM: 32 Tipe HP dari Brosur (iPhone, Samsung, OPPO) sudah otomatis di-import ke sistem!")
    
    nama_produk = str.text_input("Nama Barang Baru (Jika ingin tambah manual di luar brosur)")
    kategori = str.selectbox("Kategori", ["Gadget", "Elektronik", "Furnitur", "Motor", "Lainnya"])
    harga_modal = str.number_input("Harga Modal (Rp)", min_value=0.0, step=1000.0)
    stok_awal = str.number_input("Stok Awal", min_value=0, step=1)
    
    harga_cash = round(harga_modal * 1.05, -2)
    dp_minimal = round(harga_cash * 0.2, -2)
    
    str.markdown("---")
    str.subheader("⚙️ Parameter Kredit Fleksibel (DP & Tenor)")
    col_input1, col_input2 = str.columns(2)
    with col_input1:
        dp_input = str.number_input(f"Uang Muka / DP (Bisa diisi lebih besar! Min: Rp {dp_minimal:,.2f})", min_value=float(dp_minimal), value=float(dp_minimal), step=50000.0)
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
    
    if str.button("Simpan Produk Baru ke Database"):
        if nama_produk:
            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)", (nama_produk, kategori, harga_modal, stok_awal))
            conn.commit()
            str.success(f"Produk {nama_produk} berhasil dimasukkan!")
        else:
            str.warning("Nama barang wajib diisi jika ingin menambah manual.")

# --- FEATURE 2: BARANG MASUK ---
elif pilihan == "2. Input Barang Masuk (In)":
    str.header("📥 Input Barang Masuk (Restock)")
    df_produk = pd.read_sql_query("SELECT id, nama FROM produk", conn)
    if not df_produk.empty:
        opsi_produk = {row['nama']: row['id'] for index, row in df_produk.iterrows()}
        pilih_produk = str.selectbox("Pilih Barang dari Database (Data Brosur Sudah Terbaca)", list(opsi_produk.keys()))
        jumlah_masuk = str.number_input("Jumlah Masuk", min_value=1, step=1)
        if str.button("Tambah Stok"):
            p_id = opsi_produk[pilih_produk]
            c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)", (p_id, jumlah_masuk, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah_masuk, p_id))
            conn.commit()
            str.success("Stok gudang berhasil ditambahkan!")
    else:
        str.info("Belum ada produk terdaftar.")

# --- FEATURE 3: BARANG KELUAR ---
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
        pilih_p = str.selectbox("Pilih HP Brosur yang Dikredit", list(opsi_prod.keys()))
        
        id_p, mod_p = opsi_prod[pilih_p]
        h_cash = round(mod_p * 1.05, -2)
        dp_min_transaksi = round(h_cash * 0.2, -2)
        
        str.markdown("---")
        col_t1, col_t2 = str.columns(2)
        with col_t1:
            dp_transaksi = str.number_input(f"Besar DP dari Cust (Bisa diisi lebih besar! Min: Rp {dp_min_transaksi:,.0f})", min_value=float(dp_min_transaksi), value=float(dp_min_transaksi), step=50000.0)
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
            str.success(f"Akad Kredit Fleksibel Sukses! Transaksi tercatat.")

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

# --- FEATURE 5: STOK REALTIME ---
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
            str.error(f"⚠️ ALERT KELAYAKAN: Pelanggan {r['nama']} (WA: {r['telepon']}) sudah jatuh tempo pada {r['jatuh_tempo']}. Tenor: {r['tenor']}Bln. Angsuran: Rp {r['cicilan_bulan']:,.0f}")
    else:
        str.success("✅ Status Kelayakan Kredit Toko Aman Terkendali.")

# --- FEATURE 8: CETAK, EKSPOR & IMPOR ---
elif pilihan == "8. Cetak, Ekspor & Impor":
    str.header("🖨️ Cetak, Ekspor & Impor Data")
    tab1, tab2, tab3 = str.tabs(["Cetak Invoice", "Ekspor Data", "Impor Data"])
    
    # --- TAB CETAK INVOICE ---
    with tab1:
        str.subheader("Cetak Invoice / Akad Kredit")
        df_kredit = pd.read_sql_query('''
            SELECT k.id, c.nama as customer_nama, p.nama as produk_nama, k.harga_cash, k.dp, k.pokok_hutang, k.total_hutang, k.tenor, k.cicilan_bulan, k.jatuh_tempo, k.status
            FROM kredit k
            JOIN customer c ON k.customer_id = c.id
            JOIN produk p ON k.produk_id = p.id
            ORDER BY k.id DESC
        ''', conn)
        if not df_kredit.empty:
            df_kredit['label'] = df_kredit['id'].astype(str) + " - " + df_kredit['customer_nama'] + " - " + df_kredit['produk_nama']
            opsi_kredit = dict(zip(df_kredit['label'], df_kredit['id']))
            pilih_kredit = str.selectbox("Pilih Transaksi Kredit", list(opsi_kredit.keys()))
            if pilih_kredit:
                kredit_id = opsi_kredit[pilih_kredit]
                detail = pd.read_sql_query('''
                    SELECT k.*, c.nama as customer_nama, c.telepon, c.alamat, p.nama as produk_nama
                    FROM kredit k
                    JOIN customer c ON k.customer_id = c.id
                    JOIN produk p ON k.produk_id = p.id
                    WHERE k.id = ?
                ''', conn, params=(kredit_id,)).iloc[0]
                
                html_invoice = f"""
                <html>
                <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ text-align: center; }}
                    .details {{ margin-top: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .total {{ font-weight: bold; }}
                </style>
                </head>
                <body>
                    <div class="header">
                        <h2>INVOICE / AKAD KREDIT</h2>
                        <p>Tanggal Cetak: {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
                    </div>
                    <div class="details">
                        <p><strong>Customer:</strong> {detail['customer_nama']}</p>
                        <p><strong>Telepon:</strong> {detail['telepon']}</p>
                        <p><strong>Alamat:</strong> {detail['alamat']}</p>
                        <p><strong>Produk:</strong> {detail['produk_nama']}</p>
                    </div>
                    <table>
                        <tr><th>Deskripsi</th><th>Jumlah (Rp)</th></tr>
                        <tr><td>Harga Cash</td><td>{detail['harga_cash']:,.0f}</td></tr>
                        <tr><td>DP</td><td>{detail['dp']:,.0f}</td></tr>
                        <tr><td>Pokok Hutang</td><td>{detail['pokok_hutang']:,.0f}</td></tr>
                        <tr><td>Total Hutang (termasuk bunga)</td><td>{detail['total_hutang']:,.0f}</td></tr>
                        <tr><td>Tenor</td><td>{detail['tenor']} Bulan</td></tr>
                        <tr><td>Cicilan per Bulan</td><td>{detail['cicilan_bulan']:,.0f}</td></tr>
                        <tr><td>Jatuh Tempo Pertama</td><td>{detail['jatuh_tempo']}</td></tr>
                        <tr><td>Status</td><td>{detail['status']}</td></tr>
                    </table>
                    <p style="margin-top: 30px;">Terima kasih telah berbelanja.</p>
                </body>
                </html>
                """
                str.download_button(
                    label="📥 Download Invoice (HTML)",
                    data=html_invoice,
                    file_name=f"invoice_kredit_{kredit_id}.html",
                    mime="text/html"
                )
                str.info("Setelah diunduh, buka file HTML dan gunakan fitur print (Ctrl+P) untuk mencetak.")
        else:
            str.info("Belum ada data kredit.")
    
    # --- TAB EKSPOR DATA ---
    with tab2:
        str.subheader("Ekspor Data ke CSV")
        tabel = str.selectbox("Pilih Data yang Ingin Diekspor", ["Produk", "Customer", "Kredit", "Transaksi Masuk"])
        if tabel == "Produk":
            df = pd.read_sql_query("SELECT * FROM produk", conn)
        elif tabel == "Customer":
            df = pd.read_sql_query("SELECT * FROM customer", conn)
        elif tabel == "Kredit":
            df = pd.read_sql_query("SELECT * FROM kredit", conn)
        elif tabel == "Transaksi Masuk":
            df = pd.read_sql_query("SELECT * FROM transaksi_in", conn)
        
        if not df.empty:
            str.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            str.download_button(
                label=f"📥 Download {tabel} (CSV)",
                data=csv,
                file_name=f"{tabel.lower()}.csv",
                mime="text/csv"
            )
        else:
            str.info("Tidak ada data.")
    
    # --- TAB IMPOR DATA ---
    with tab3:
        str.subheader("Impor Data dari CSV")
        jenis_impor = str.selectbox("Pilih Jenis Data yang Ingin Diimpor", ["Produk", "Customer"])
        
        if jenis_impor == "Produk":
            str.markdown("Format CSV: `nama, kategori, harga_modal, stok`")
            template_df = pd.DataFrame(columns=["nama", "kategori", "harga_modal", "stok"])
            template_csv = template_df.to_csv(index=False).encode('utf-8')
            str.download_button("📥 Download Template Produk (CSV)", template_csv, "template_produk.csv", "text/csv")
            
            uploaded_file = str.file_uploader("Pilih file CSV Produk", type=["csv"])
            if uploaded_file is not None:
                try:
                    df_import = pd.read_csv(uploaded_file)
                    str.dataframe(df_import.head())
                    if str.button("Proses Impor Produk"):
                        for _, row in df_import.iterrows():
                            c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok) VALUES (?,?,?,?)",
                                      (row['nama'], row['kategori'], row['harga_modal'], row['stok']))
                        conn.commit()
                        str.success(f"Berhasil mengimpor {len(df_import)} produk.")
                except Exception as e:
                    str.error(f"Gagal membaca file: {e}")
        
        elif jenis_impor == "Customer":
            str.markdown("Format CSV: `nama, telepon, alamat`")
            template_df = pd.DataFrame(columns=["nama", "telepon", "alamat"])
            template_csv = template_df.to_csv(index=False).encode('utf-8')
            str.download_button("📥 Download Template Customer (CSV)", template_csv, "template_customer.csv", "text/csv")
            
            uploaded_file = str.file_uploader("Pilih file CSV Customer", type=["csv"])
            if uploaded_file is not None:
                try:
                    df_import = pd.read_csv(uploaded_file)
                    str.dataframe(df_import.head())
                    if str.button("Proses Impor Customer"):
                        for _, row in df_import.iterrows():
                            c.execute("INSERT INTO customer (nama, telepon, alamat) VALUES (?,?,?)",
                                      (row['nama'], row['telepon'], row['alamat']))
                        conn.commit()
                        str.success(f"Berhasil mengimpor {len(df_import)} customer.")
                except Exception as e:
                    str.error(f"Gagal membaca file: {e}")

# Koneksi database tidak ditutup agar tidak error saat Streamlit rerun
# conn.close()
