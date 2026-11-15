import streamlit as st
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# KONFIGURASI HALAMAN
# =========================================================
st.set_page_config(
    page_title="Grace's Store · Invoice & Perjanjian",
    page_icon="📱",
    layout="wide"
)

# =========================================================
# FUNGSI BANTU
# =========================================================
def format_rupiah(angka: int) -> str:
    return f"Rp {angka:,.0f}".replace(",", ".")

def hitung_jadwal(pokok: int, bunga_persen: float, tenor: int, tanggal_mulai: datetime):
    bunga_per_bulan = pokok * (bunga_persen / 100)
    total_bunga = bunga_per_bulan * tenor
    total_hutang = pokok + total_bunga
    angsuran = total_hutang / tenor if tenor > 0 else 0

    jadwal = []
    sisa = total_hutang
    for i in range(1, tenor + 1):
        jatuh_tempo = tanggal_mulai + timedelta(days=30 * i)
        sisa -= angsuran
        jadwal.append({
            "no": i,
            "jatuh_tempo": jatuh_tempo.strftime("%d-%m-%Y"),
            "angsuran": int(round(angsuran)),
            "sisa": max(0, int(round(sisa)))
        })
    return int(round(angsuran)), int(round(total_hutang)), jadwal

def buat_gambar_emeterai() -> Image.Image:
    img = Image.new("RGB", (300, 150), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    try:
        font_besar = ImageFont.truetype("arial.ttf", 20)
        font_kecil = ImageFont.truetype("arial.ttf", 12)
    except:
        font_besar = ImageFont.load_default()
        font_kecil = ImageFont.load_default()

    draw.rectangle([5, 5, 295, 145], outline="black", width=2)
    draw.text((20, 20), "E-METERAI", font=font_besar, fill="black")
    draw.text((20, 55), "Rp 10.000", font=font_besar, fill="black")
    draw.text((20, 90), "Peruri · Sah", font=font_kecil, fill="black")
    draw.text((20, 110), "Nomor: 0000-0000-0000", font=font_kecil, fill="black")
    return img

def simpan_gambar_ke_file(uploaded_file, path: str, max_width: int = 800) -> str:
    if uploaded_file is None:
        return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_width:
        rasio = max_width / img.width
        img = img.resize((max_width, int(img.height * rasio)))
    img.save(path, format="JPEG", quality=85)
    return path

# =========================================================
# GENERATE INVOICE PDF
# =========================================================
def generate_invoice_pdf(data: dict, mode: str, total_hutang: int,
                          angsuran: int, jadwal: list = None) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "INVOICE", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "GRACE'S ELECTRONIC · CASH & CREDIT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Jl. Barong Tongkok, Kutai Barat · HP/WA: 0822-9954-8411", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"No. Invoice: {data['nomor_invoice']}", ln=True)
    pdf.cell(0, 5, f"Tanggal: {data['tanggal_perjanjian']}", ln=True)
    pdf.cell(0, 5, f"Metode: {'TUNAI (CASH)' if mode == 'tunai' else 'KREDIT'}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "KEPADA:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Nama: {data['nama']}", ln=True)
    pdf.cell(0, 5, f"Telepon: {data['telepon']}", ln=True)
    pdf.multi_cell(0, 5, f"Alamat: {data['alamat']}")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PRODUK:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"{data['produk']} (SKU: {data['sku']}) · Garansi: {data['garansi']}", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "RINCIAN PEMBAYARAN:", ln=True)
    pdf.set_font("Helvetica", "", 9)

    if mode == "tunai":
        pdf.cell(0, 5, f"Harga Cash: {format_rupiah(data['harga_cash'])}", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"TOTAL DIBAYAR: {format_rupiah(data['harga_cash'])}", ln=True)
    else:
        pdf.cell(0, 5, f"Harga Cash: {format_rupiah(data['harga_cash'])}", ln=True)
        pdf.cell(0, 5, f"Uang Muka (DP): {format_rupiah(data['dp'])}", ln=True)
        pdf.cell(0, 5, f"Pokok Hutang: {format_rupiah(data['pokok'])}", ln=True)
        pdf.cell(0, 5, f"Bunga Flat: {data['bunga']}% / bulan", ln=True)
        pdf.cell(0, 5, f"Tenor: {data['tenor']} bulan", ln=True)
        pdf.cell(0, 5, f"Angsuran / Bulan: {format_rupiah(angsuran)}", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"TOTAL HUTANG: {format_rupiah(total_hutang)}", ln=True)
        pdf.set_font("Helvetica", "", 9)

        if jadwal:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(20, 6, "No", border=1)
            pdf.cell(45, 6, "Jatuh Tempo", border=1)
            pdf.cell(45, 6, "Angsuran", border=1)
            pdf.cell(45, 6, "Sisa", border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            for row in jadwal:
                pdf.cell(20, 5, str(row["no"]), border=1)
                pdf.cell(45, 5, row["jatuh_tempo"], border=1)
                pdf.cell(45, 5, format_rupiah(row["angsuran"]), border=1)
                pdf.cell(45, 5, format_rupiah(row["sisa"]), border=1)
                pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 4, "Terima kasih telah berbelanja di Grace's Electronic.", ln=True, align="C")

    return pdf.output(dest="S").encode("latin-1")

# =========================================================
# GENERATE PERJANJIAN PDF
# =========================================================
def generate_perjanjian_pdf(data: dict, jadwal: list, total_hutang: int, angsuran: int,
                             path_ktp: str = None, path_kk: str = None) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # HEADER
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "PERJANJIAN PEMBIAYAAN KONSUMEN", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "GRACE'S ELECTRONIC · CASH & CREDIT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Jl. Barong Tongkok, Kutai Barat · HP/WA: 0822-9954-8411", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Nomor: {data['nomor_invoice']}", ln=True)
    pdf.cell(0, 5, f"Tanggal: {data['tanggal_perjanjian']}", ln=True)
    pdf.ln(3)

    # PARA PIHAK
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PARA PIHAK", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, "PIHAK PERTAMA (KREDITUR): GRACE'S ELECTRONIC, beralamat di Jl. Barong Tongkok, Kutai Barat.")
    pdf.multi_cell(0, 5, f"PIHAK KEDUA (DEBITUR): {data['nama']}, KTP: {data['no_ktp']}, Telepon: {data['telepon']}, Alamat: {data['alamat']}.")
    pdf.ln(3)

    # PASAL 1
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PASAL 1 — OBJEK PEMBIAYAAN", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, f"Debitur membeli secara kredit barang elektronik: {data['produk']} (SKU: {data['sku']}), garansi {data['garansi']}. Barang telah diterima dalam keadaan baik dan berfungsi normal.")
    pdf.ln(2)

    # PASAL 2
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PASAL 2 — NILAI DAN RINCIAN PEMBIAYAAN", ln=True)
    pdf.set_font("Helvetica", "", 9)
    rincian = [
        f"Harga Tunai: {format_rupiah(data['harga_cash'])}",
        f"Uang Muka (DP): {format_rupiah(data['dp'])}",
        f"Pokok Hutang: {format_rupiah(data['pokok'])}",
        f"Suku Bunga Flat: {data['bunga']}% per bulan",
        f"Tenor: {data['tenor']} bulan",
        f"Total Hutang: {format_rupiah(total_hutang)}",
        f"Angsuran per Bulan: {format_rupiah(angsuran)}",
    ]
    for r in rincian:
        pdf.cell(0, 5, r, ln=True)
    pdf.ln(2)

    # JADWAL ANGSURAN
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 6, "No", border=1)
    pdf.cell(45, 6, "Jatuh Tempo", border=1)
    pdf.cell(45, 6, "Angsuran", border=1)
    pdf.cell(45, 6, "Sisa", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in jadwal:
        pdf.cell(20, 5, str(row["no"]), border=1)
        pdf.cell(45, 5, row["jatuh_tempo"], border=1)
        pdf.cell(45, 5, format_rupiah(row["angsuran"]), border=1)
        pdf.cell(45, 5, format_rupiah(row["sisa"]), border=1)
        pdf.ln()
    pdf.ln(3)

    # PASAL 3-7
    pasal_texts = [
        ("PASAL 3 — HAK DAN KEWAJIBAN",
         "Kreditur berhak menerima angsuran tepat waktu dan berkewajiban memberikan informasi transparan. "
         "Debitur berhak mendapatkan salinan perjanjian dan berkewajiban membayar angsuran sesuai jadwal serta merawat barang."),
        ("PASAL 4 — DENDA KETERLAMBATAN",
         f"Keterlambatan dikenakan denda {data['denda']}% per hari dari angsuran tertunggak, "
         "dengan total denda tidak melebihi 100% dari Pokok Hutang."),
        ("PASAL 5 — JAMINAN FIDUSIA",
         "Debitur memberikan jaminan fidusia atas Objek Pembiayaan sesuai UU No. 42 Tahun 1999. "
         "Kreditur dilarang melakukan tindakan sepihak atas barang jaminan di luar ketentuan hukum."),
        ("PASAL 6 — PENYELESAIAN SENGKETA",
         "Sengketa diselesaikan secara musyawarah. Jika gagal, diselesaikan melalui Pengadilan Negeri yang berwenang. "
         "Debitur berhak menggugat Kreditur."),
        ("PASAL 7 — LARANGAN KLAUSUL EKSONERASI",
         "Kreditur dilarang mengalihkan tanggung jawab secara sepihak, membatasi hak Debitur menggugat, "
         "atau melakukan perubahan sepihak setelah perjanjian ditandatangani."),
    ]
    for judul, isi in pasal_texts:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, judul, ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4, isi)
        pdf.ln(2)

    # PERSETUJUAN
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PERNYATAAN DAN PERSETUJUAN", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4,
        "Debitur menyatakan telah membaca, memahami, dan menyetujui seluruh isi Perjanjian ini tanpa paksaan. "
        "Debitur menerima salinan Perjanjian. Debitur juga menyatakan bahwa dokumen identitas (KTP dan KK) "
        "yang dilampirkan adalah benar dan masih berlaku."
    )
    pdf.ln(4)

    # TANDA TANGAN
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(90, 5, "KREDITUR", ln=0)
    pdf.cell(90, 5, "DEBITUR", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(90, 5, "GRACE'S ELECTRONIC", ln=0)
    pdf.cell(90, 5, data["nama"], ln=1)
    pdf.ln(15)
    pdf.cell(90, 5, "(_________________________)", ln=0)
    pdf.cell(90, 5, "(_________________________)", ln=1)
    pdf.ln(5)

    # E-METERAI
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "E-METERAI", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 4, "Dokumen ini telah dibubuhi e-Meterai resmi Peruri senilai Rp10.000 sesuai UU No. 10 Tahun 2020.", ln=True)

    emeterai_img = buat_gambar_emeterai()
    emeterai_path = "emeterai_temp.png"
    emeterai_img.save(emeterai_path, format="PNG")
    y_pos = pdf.get_y() + 2
    pdf.image(emeterai_path, x=130, y=y_pos, w=50)
    pdf.ln(40)

    # LAMPIRAN KTP & KK
    if path_ktp or path_kk:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "LAMPIRAN DOKUMEN IDENTITAS DEBITUR", ln=True, align="C")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5,
            f"Lampiran ini merupakan bagian tidak terpisahkan dari Perjanjian Pembiayaan Konsumen "
            f"Nomor {data['nomor_invoice']} atas nama {data['nama']}."
        )
        pdf.ln(4)

        if path_ktp and os.path.exists(path_ktp):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "A. Fotokopi / Scan KTP", ln=True)
            pdf.image(path_ktp, x=25, w=160)
            pdf.ln(4)

        if path_kk and os.path.exists(path_kk):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "B. Fotokopi / Scan Kartu Keluarga (KK)", ln=True)
            pdf.image(path_kk, x=25, w=160)
            pdf.ln(4)

        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4,
            "Dokumen identitas di atas telah diverifikasi oleh Kreditur dan sesuai dengan data Debitur "
            "dalam Perjanjian ini."
        )

    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 4, "Dokumen ini sah dan mengikat setelah ditandatangani kedua pihak. Simpan sebagai bukti.", ln=True, align="C")

    return pdf.output(dest="S").encode("latin-1")

# =========================================================
# HEADER APLIKASI
# =========================================================
st.title("📱 Grace's Store · Invoice & Perjanjian")
st.caption("Cash & Credit · Authorized Retailer · Jl. Barong Tongkok, Kutai Barat")

# =========================================================
# TOGGLE MODE
# =========================================================
mode = st.radio(
    "**Pilih Metode Transaksi:**",
    options=["Kredit", "Tunai (Cash)"],
    horizontal=True,
    help="Mode Tunai akan menyembunyikan kolom bunga, DP, tenor, dan jadwal angsuran."
)

# =========================================================
# FORM INPUT
# =========================================================
with st.form("form_transaksi"):
    st.subheader("1. Data Pelanggan")
    col1, col2 = st.columns(2)
    with col1:
        nama = st.text_input("Nama Lengkap *", placeholder="Contoh: Lilis Wihani")
        no_ktp = st.text_input("No. KTP *", placeholder="16 digit")
        telepon = st.text_input("No. Telepon *", placeholder="08xxxxxxxxxx")
    with col2:
        alamat = st.text_area("Alamat *", placeholder="Alamat lengkap")
        nomor_invoice = st.text_input("Nomor Invoice *", value="GRC-INV-4")

    # UPLOAD DOKUMEN
    st.subheader("2. Upload Dokumen Identitas")
    if mode == "Kredit":
        st.caption("Dokumen identitas **wajib** diunggah sebagai lampiran perjanjian kredit.")
    else:
        st.caption("Dokumen identitas **opsional** untuk transaksi tunai.")

    col_doc1, col_doc2 = st.columns(2)
    with col_doc1:
        file_ktp = st.file_uploader("Foto / Scan KTP", type=["jpg", "jpeg", "png"], key="upload_ktp")
    with col_doc2:
        file_kk = st.file_uploader("Foto / Scan Kartu Keluarga (KK)", type=["jpg", "jpeg", "png"], key="upload_kk")

    if file_ktp or file_kk:
        st.write("**Preview Dokumen:**")
        prev1, prev2 = st.columns(2)
        if file_ktp:
            with prev1:
                st.image(file_ktp, caption="KTP", use_container_width=True)
        if file_kk:
            with prev2:
                st.image(file_kk, caption="KK", use_container_width=True)

    # DATA PRODUK
    st.subheader("3. Data Produk")
    col3, col4 = st.columns(2)
    with col3:
        produk = st.text_input("Nama Produk *", value="Samsung A07 4/128 Black")
        sku = st.text_input("SKU *", value="GRC-72")
    with col4:
        garansi = st.text_input("Garansi *", value="3 Bulan")

    # SKEMA PEMBIAYAAN
    st.subheader("4. Skema Pembiayaan")

    if mode == "Tunai (Cash)":
        harga_cash = st.number_input(
            "Harga Cash (Rp) *",
            min_value=0, value=3118200, step=1000,
            help="Harga ini bisa diedit sesuai kesepakatan."
        )
        dp = 0
        bunga = 0.0
        tenor = 1
        denda = 0.0
        st.info("ℹ️ Kolom bunga, DP, tenor, dan denda disembunyikan karena mode **Tunai**.")
    else:
        col5, col6, col7 = st.columns(3)
        with col5:
            harga_cash = st.number_input(
                "Harga Cash (Rp) *",
                min_value=0, value=3118200, step=1000,
                help="Harga tunai sebagai dasar perhitungan pokok hutang. Bisa diedit."
            )
            dp = st.number_input(
                "Uang Muka / DP (Rp) *",
                min_value=0, value=630000, step=1000,
                help="DP bisa diedit sesuai kesepakatan."
            )
        with col6:
            bunga = st.number_input(
                "Bunga Flat (% per bulan) *",
                min_value=0.0, value=6.67, step=0.01, format="%.2f",
                help="Bunga flat per bulan. Bisa diedit."
            )
            tenor = st.number_input(
                "Tenor (bulan) *",
                min_value=1, max_value=24, value=6, step=1
            )
        with col7:
            denda = st.number_input(
                "Denda Keterlambatan (% per hari) *",
                min_value=0.0, value=1.0, step=0.1, format="%.1f",
                help="Hanya berlaku untuk transaksi kredit."
            )

    # KONFIRMASI
    st.subheader("5. Konfirmasi")
    if mode == "Kredit":
        setuju = st.checkbox(
            "Saya telah membaca dan memahami seluruh isi Perjanjian Pembiayaan Konsumen ini, "
            "dan menyetujui untuk menandatanganinya secara elektronik."
        )
    else:
        setuju = True

    submitted = st.form_submit_button("📄 Generate Invoice & Perjanjian")

# =========================================================
# PROSES SETELAH SUBMIT
# =========================================================
if submitted:
    error_list = []
    if not nama or not no_ktp or not telepon or not alamat:
        error_list.append("Data pelanggan wajib diisi lengkap.")
    if mode == "Kredit" and not file_ktp:
        error_list.append("Foto KTP wajib diunggah untuk transaksi kredit.")
    if mode == "Kredit" and not file_kk:
        error_list.append("Foto KK wajib diunggah untuk transaksi kredit.")
    if mode == "Kredit" and not setuju:
        error_list.append("Anda harus menyetujui Perjanjian sebelum melanjutkan.")

    if error_list:
        for err in error_list:
            st.error(f"❌ {err}")
    else:
        if mode == "Kredit":
            pokok = harga_cash - dp
            if pokok < 0:
                st.error("❌ DP tidak boleh melebihi harga cash.")
                st.stop()
            tanggal = datetime.now()
            angsuran, total_hutang, jadwal = hitung_jadwal(
                pokok=pokok, bunga_persen=bunga, tenor=tenor, tanggal_mulai=tanggal
            )
        else:
            pokok = 0
            angsuran = 0
            total_hutang = harga_cash
            jadwal = []
            tanggal = datetime.now()

        data = {
            "nama": nama, "no_ktp": no_ktp, "telepon": telepon, "alamat": alamat,
            "nomor_invoice": nomor_invoice,
            "tanggal_perjanjian": tanggal.strftime("%d-%m-%Y %H:%M WITA"),
            "produk": produk, "sku": sku, "garansi": garansi,
            "harga_cash": harga_cash, "dp": dp, "pokok": pokok,
            "bunga": bunga, "tenor": tenor, "denda": denda,
        }

        mode_key = "tunai" if mode == "Tunai (Cash)" else "kredit"
        invoice_bytes = generate_invoice_pdf(data, mode_key, total_hutang, angsuran, jadwal)

        st.session_state["data"] = data
        st.session_state["mode"] = mode
        st.session_state["total_hutang"] = total_hutang
        st.session_state["angsuran"] = angsuran
        st.session_state["jadwal"] = jadwal
        st.session_state["invoice_bytes"] = invoice_bytes

        if mode == "Kredit":
            path_ktp = simpan_gambar_ke_file(file_ktp, "ktp_temp.jpg")
            path_kk = simpan_gambar_ke_file(file_kk, "kk_temp.jpg")
            perjanjian_bytes = generate_perjanjian_pdf(
                data, jadwal, total_hutang, angsuran, path_ktp, path_kk
            )
            st.session_state["perjanjian_bytes"] = perjanjian_bytes
            st.success("✅ Invoice dan Perjanjian Kredit berhasil dibuat!")
        else:
            st.session_state.pop("perjanjian_bytes", None)
            st.success("✅ Invoice Tunai berhasil dibuat!")

# =========================================================
# TAMPILKAN HASIL
# =========================================================
if "invoice_bytes" in st.session_state:
    data = st.session_state["data"]
    mode_tampil = st.session_state["mode"]
    total_hutang = st.session_state["total_hutang"]
    angsuran = st.session_state["angsuran"]
    jadwal = st.session_state["jadwal"]
    invoice_bytes = st.session_state["invoice_bytes"]

    st.divider()
    st.subheader(f"📋 Ringkasan Transaksi — Mode {mode_tampil}")

    if mode_tampil == "Kredit":
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Hutang", format_rupiah(total_hutang))
        col_b.metric("Angsuran / Bulan", format_rupiah(angsuran))
        col_c.metric("Tenor", f"{data['tenor']} bulan")

        st.write("**Jadwal Angsuran**")
        st.table([
            {"No": row["no"], "Jatuh Tempo": row["jatuh_tempo"],
             "Angsuran": format_rupiah(row["angsuran"]), "Sisa": format_rupiah(row["sisa"])}
            for row in jadwal
        ])
    else:
        st.metric("Total Dibayar (Tunai)", format_rupiah(total_hutang))

    # PREVIEW INVOICE
    st.subheader("🧾 Preview Invoice")
    st.pdf(invoice_bytes, height=500)
    st.download_button(
        label="⬇️ Unduh Invoice PDF",
        data=invoice_bytes,
        file_name=f"Invoice_{data['nomor_invoice']}_{data['nama'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

    # PREVIEW PERJANJIAN (hanya kredit)
    if mode_tampil == "Kredit" and "perjanjian_bytes" in st.session_state:
        perjanjian_bytes = st.session_state["perjanjian_bytes"]
        st.divider()
        st.subheader("📜 Preview Perjanjian Pembiayaan Konsumen")
        st.pdf(perjanjian_bytes, height=700)
        st.download_button(
            label="⬇️ Unduh Perjanjian PDF",
            data=perjanjian_bytes,
            file_name=f"Perjanjian_{data['nomor_invoice']}_{data['nama'].replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
        st.info(
            "🔐 **E-Meterai:** PDF di atas menggunakan **placeholder e-Meterai** (simulasi). "
            "Untuk e-Meterai resmi, integrasikan API Peruri via mitra resmi "
            "(Mekari Sign, OnlinePajak, atau VIDA). Tarif: **Rp10.000 per dokumen** sesuai UU No. 10 Tahun 2020."
        )

# =========================================================
# FOOTER
# =========================================================
st.divider()
st.caption(
    "© 2026 Grace's Electronic · Disusun dengan prinsip transparansi dan larangan klausul eksonerasi "
    "berdasarkan POJK No. 22 Tahun 2023."
)
