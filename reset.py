import sqlite3

# Data stok awal sesuai dengan seed di aplikasi
stok_awal = {
    # Gadget (Semua 10)
    "iPhone 17 256GB": 10, "iPhone 17 512GB": 10, "iPhone 17 PRO 256GB": 10, "iPhone 17 PRO 512GB": 10,
    "iPhone 17 PRO 1TB": 10, "iPhone 17 PRO MAX 256GB": 10, "iPhone 17 PRO MAX 512GB": 10, "iPhone 17 PRO MAX 1TB": 10,
    "iPhone 17 PRO MAX 2TB": 10, "iPhone 17 AIR 256GB": 10, "iPhone 17 AIR 512GB": 10, "iPhone 17 AIR 1TB": 10,
    "iPhone 17e 256GB": 10, "iPhone 17e 512GB": 10, "iPhone 16 128GB": 10, "iPhone 16 256GB": 10,
    "iPhone 16 PLUS 128GB": 10, "iPhone 16 PLUS 256GB": 10, "iPhone 15 128GB": 10, "Galaxy S26 Ultra 256GB": 10,
    "Galaxy S26 Ultra 512GB": 10, "Galaxy S26 Ultra 1TB": 10, "Galaxy S26+ 256GB": 10, "Galaxy S26+ 512GB": 10,
    "Galaxy S26 256GB": 10, "Galaxy S25 Ultra 256GB": 10, "Reno 16 Pro 256GB": 10, "Reno 16 256GB (8GB)": 10,
    "Reno 16 256GB (12GB)": 10, "Reno 16 F 128GB": 10, "Find X9 Ultra": 10, "OPPO A6 128GB": 10,
    # Pakaian
    "Tunik Lop Top": 1, "Rok Lurus": 1, "Atasan Orange": 1, "Hem": 1, "Mini Dress": 2, "Casual Dress": 1,
    "Atasan Polkadot": 1, "Outer": 2, "Spanya Dress": 3, "Mini Dress Navy": 1, "Celana Merah": 1,
    "Batik Premium (Keterangan 2)": 1, "Batik Reguler (Keterangan 2)": 10, "Dress Premium (Keterangan 3)": 30,
    "Dress Ibu Merah": 1, "Dress Baru (Keterangan 3)": 1, "Jeans Wool": 1, "Midi Dress Hitam Merah": 1,
    "Atasan Ibu Merah": 1, "Atasan Basic (Keterangan 3)": 5, "Long Dress / Gamis (Keterangan 4)": 20
}

try:
    conn = sqlite3.connect('toko_kredit.db')
    c = conn.cursor()

    print("⏳ Menghapus semua data transaksi (Kredit & Pembayaran)...")
    c.execute("DELETE FROM pembayaran")
    c.execute("DELETE FROM kredit")
    c.execute("DELETE FROM transaksi_in") # Menghapus riwayat barang masuk (opsional)

    print("⏳ Mengembalikan stok produk ke angka awal...")
    for nama, stok in stok_awal.items():
        c.execute("UPDATE produk SET stok = ? WHERE nama = ?", (stok, nama))

    # Untuk berjaga-jaga, set semua produk yang tidak ada di list agar stoknya jadi 10
    c.execute("UPDATE produk SET stok = 10 WHERE nama NOT IN ({})".format(','.join('?'*len(stok_awal))), tuple(stok_awal.keys()))

    conn.commit()
    conn.close()
    
    print("✅ BERHASIL! Semua transaksi telah dihapus dan stok produk sudah kembali normal.")
    print("Silakan jalankan kembali Streamlit Anda.")

except Exception as e:
    print(f"❌ Terjadi kesalahan: {e}")
