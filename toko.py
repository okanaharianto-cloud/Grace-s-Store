import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import shutil
import uuid
import io
from datetime import datetime, timedelta
import altair as alt
import streamlit.components.v1 as components
from PIL import Image

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="GRACE'S STORE (CASH & CREDIT)",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)


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
        "🤝 Serah Terima Barang",
        "📦 Stok Barang",
        "🚨 Overdue & Denda", 
        "🔔 Alert & Reminder", 
        "📊 Laporan & Analitik",
        "👕 Modal vs Profit", 
        "💾 Backup, Cetak & Impor",
    ]
    if st.session_state.role == "admin":
        menu_list.extend(["⚙️ Pengaturan Owner", "👤 Manajemen User", "📝 Log Aktivitas"])

    pilihan = st.radio("📋 Menu", menu_list, key="menu_utama")
    
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
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

# ==================== PANGGIL FLASH & BACKUP ====================
show_flash()
auto_backup_database()
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
    denda_val = st.number_input("Denda per hari telat (% dari cicilan)", min_value=0.0, max_value=20.0, value=get_pengaturan_float("denda_per_hari_persen", 0.4), step=0.1, format="%.2f", key="input_denda_owner")
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
    pakaian_belum_harga = c.execute(f"SELECT COUNT(*) FROM produk WHERE kategori IN ({','.join(['?']*len(PAKAIAN_KATEGORI))}) AND (harga_jual IS NULL OR harga_jual <= 0)", tuple(PAKAIAN_KATEGORI)).fetchone()[0]
    
    pending_serah = c.execute("SELECT COUNT(*) FROM kredit WHERE id NOT IN (SELECT kredit_id FROM serah_terima)").fetchone()[0]

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
    html += metric_card("📦 Pending Serah Terima", f"{pending_serah} akun", "card-pink")
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    if pakaian_belum_harga > 0:
        st.warning(f"⚠️ **{pakaian_belum_harga} produk pakaian belum diisi harga jual.** Buka menu **📦 Stok Barang** → **Edit Harga Jual Pakaian**.")
        
    if pending_serah > 0:
        st.warning(f"⚠️ **{pending_serah} akun kredit belum diserahterimakan.** Segera buka menu **🤝 Serah Terima Barang** untuk mencegah pelanggan kabur.")

    st.markdown('<div class="section-header"><h3>📊 Analitik Penjualan</h3></div>', unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**🏆 Top 5 Produk Terlaris (Kredit + Cash)**")
        df_top = pd.read_sql_query("SELECT produk, SUM(qty) as jumlah_terjual FROM (SELECT p.nama as produk, 1 as qty FROM kredit k JOIN produk p ON k.produk_id = p.id UNION ALL SELECT p.nama as produk, t.jumlah as qty FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id) GROUP BY produk ORDER BY jumlah_terjual DESC LIMIT 5", conn)
        if not df_top.empty:
            chart = alt.Chart(df_top).mark_bar(cornerRadiusTopRight=10, cornerRadiusBottomRight=10).encode(x=alt.X('jumlah_terjual:Q', title='Jumlah Terjual'), y=alt.Y('produk:N', sort='-x', title='Produk'), color=alt.Color('jumlah_terjual:Q', scale=alt.Scale(scheme='purples'), legend=None)).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")

    with col_chart2:
        st.markdown("**📈 Cicilan Masuk per Bulan**")
        df_bayar = pd.read_sql_query("SELECT substr(tanggal,1,7) as bulan, SUM(jumlah_bayar) as total FROM pembayaran GROUP BY bulan ORDER BY bulan", conn)
        if not df_bayar.empty:
            chart = alt.Chart(df_bayar).mark_area(line={'color':'#667eea'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#f093fb', offset=0), alt.GradientStop(color='#667eea', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X('bulan:N', title='Bulan'), y=alt.Y('total:Q', title='Total (Rp)')).properties(height=300)
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
                    c.execute("INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual) VALUES (?,?,?,?,?,?)", (nama_produk, kategori, harga_modal, stok_awal, markup_persen, harga_jual))
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
                        # ==================== 4. JUAL CASH ====================

# ==================== 5. KREDIT BARU (DENGAN FITUR EDIT/DELETE/CANCEL) ====================
# ==================== 5. KREDIT BARU ====================
elif pilihan == "📤 Kredit Baru":
    st.markdown('<div class="main-header"><h1>📤 Transaksi Kredit Baru</h1></div>', unsafe_allow_html=True)

    # SUB-MENU UNTUK EDIT / HAPUS KREDIT
    tab_input, tab_edit = st.tabs(["➕ Buat Kredit Baru", "✏️ Edit / Hapus / Batalkan Kredit"])
    
    with tab_input:
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

            if st.button("✅ Proses Kredit & Keluarkan Barang", use_container_width=True):
                id_c = opsi_cust[pilih_c]
                tgl_kredit = datetime.now().strftime("%Y-%m-%d")
                tgl_tempo = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                try:
                    c.execute('''INSERT INTO kredit (customer_id, produk_id, harga_cash, dp, pokok_hutang, total_hutang, tenor, cicilan_bulan, sisa_hutang, jatuh_tempo, status, tanggal_kredit, updated_at, updated_by) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (id_c, id_p, h_cash, dp, pokok, total, tenor, cicilan, total, tgl_tempo, "Berjalan", tgl_kredit, get_current_time(), st.session_state.username))
                    c.execute("UPDATE produk SET stok = stok - 1 WHERE id = ?", (id_p,))
                    conn.commit()
                    log_aksi(st.session_state.username, "KREDIT_BARU", f"Customer {pilih_c}, Produk {pilih_p}")
                    flash("🎉 Akad kredit berhasil! Silakan buka menu **🖨️ Cetak Slip Kredit** untuk mencetak invoice.", "success")
                    st.session_state.balloons = True
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan kredit: {e}")

    with tab_edit:
        st.subheader("Edit / Hapus / Batalkan Kredit")
        st.info("Gunakan tab ini jika ada kesalahan input data kredit. Menghapus data akan mengembalikan stok barang.")
        
        df_kredit_all = pd.read_sql_query("""
            SELECT k.id, c.nama as customer, p.nama as produk, k.status, k.total_hutang
            FROM kredit k JOIN customer c ON k.customer_id = c.id JOIN produk p ON k.produk_id = p.id
            ORDER BY k.id DESC
        """, conn)
        
        if not df_kredit_all.empty:
            opsi_kredit = {f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})": r['id'] for _, r in df_kredit_all.iterrows()}
            pilih_kredit = st.selectbox("Pilih Kredit yang akan diedit/dihapus", list(opsi_kredit.keys()))
            kid = opsi_kredit[pilih_kredit]
            
            d = pd.read_sql_query("SELECT * FROM kredit WHERE id=?", conn, params=(kid,)).iloc[0]
            
            with st.form("form_edit_kredit_baru"):
                col1, col2 = st.columns(2)
                with col1:
                    m_harga_cash = st.number_input("Harga Cash", value=float(d['harga_cash']), step=10000.0)
                    m_dp = st.number_input("DP", value=float(d['dp']), step=10000.0)
                    m_status = st.selectbox("Status Kredit", ["Berjalan", "Lunas", "Batal"], index=["Berjalan", "Lunas", "Batal"].index(d['status']))
                with col2:
                    m_total = st.number_input("Total Hutang", value=float(d['total_hutang']), step=10000.0)
                    m_cicilan = st.number_input("Cicilan / Bulan", value=float(d['cicilan_bulan']), step=10000.0)
                    m_tenor = st.number_input("Tenor (Bulan)", value=int(d['tenor']), min_value=1)
                
                submit_edit = st.form_submit_button("💾 Simpan Perubahan")
                if submit_edit:
                    try:
                        c.execute("UPDATE kredit SET harga_cash=?, dp=?, total_hutang=?, cicilan_bulan=?, tenor=?, status=? WHERE id=?", 
                                  (m_harga_cash, m_dp, m_total, m_cicilan, m_tenor, m_status, kid))
                        conn.commit()
                        flash("✅ Data Kredit berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")
                        
            if st.button("🗑️ Hapus Kredit & Kembalikan Stok", type="primary"):
                try:
                    produk_id = d['produk_id']
                    c.execute("UPDATE produk SET stok = stok + 1 WHERE id = ?", (produk_id,))
                    c.execute("DELETE FROM pembayaran WHERE kredit_id = ?", (kid,))
                    c.execute("DELETE FROM serah_terima WHERE kredit_id = ?", (kid,))
                    c.execute("DELETE FROM kredit WHERE id = ?", (kid,))
                    conn.commit()
                    flash("🗑️ Kredit berhasil dihapus dan stok telah dikembalikan!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menghapus: {e}")
        else:
            st.info("Belum ada data kredit.")
            # ==================== 6. PEMBAYARAN CICILAN ====================
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
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 0.4)

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

        if st.button("💳 Proses Pembayaran", use_container_width=True):
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
                    c.execute("INSERT INTO pembayaran (kredit_id, jumlah_bayar, denda, tanggal, keterangan) VALUES (?,?,?,?,?)", (kredit_id, jumlah_bayar, denda, datetime.now().strftime("%Y-%m-%d"), keterangan))
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

# ==================== 7. DATA CUSTOMER ====================
elif pilihan == "👥 Data Customer":
    st.markdown('<div class="main-header"><h1>👥 Data Pelanggan & Berkas</h1></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Customer", "📋 Daftar & Berkas", "✏️ Edit / Hapus Customer"])

    with tab1:
        with st.form("form_cust"):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nama Lengkap")
                t = st.text_input("Telepon/WA")
                nik = st.text_input("NIK")
            with col2:
                a = st.text_area("Alamat")
                tgl_lhr = st.date_input("Tanggal Lahir")
                st_kawin = st.selectbox("Status Kawin", ["Belum Kawin", "Kawin", "Cerai Hidup", "Cerai Mati"])
            
            st.markdown("**Upload Berkas Identitas (KTP & KK)**")
            col_ktp, col_kk = st.columns(2)
            with col_ktp:
                upload_ktp = st.file_uploader("Upload Foto KTP", type=["jpg", "jpeg", "png"])
            with col_kk:
                upload_kk = st.file_uploader("Upload Foto KK", type=["jpg", "jpeg", "png"])

            if st.form_submit_button("💾 Simpan Customer"):
                if n:
                    path_ktp = save_uploaded_file(upload_ktp, "KTP")
                    path_kk = save_uploaded_file(upload_kk, "KK")
                    try:
                        c.execute("INSERT INTO customer (nama, telepon, alamat, nik, tanggal_lahir, status_kawin, foto_ktp, foto_kk) VALUES (?,?,?,?,?,?,?,?)", 
                                  (n, t, a, nik, tgl_lhr.strftime("%d-%m-%Y"), st_kawin, path_ktp, path_kk))
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
            SELECT c.id, c.nama, c.telepon, c.alamat, c.nik, c.foto_ktp, c.foto_kk,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id) as total_kredit,
                   (SELECT COUNT(*) FROM kredit WHERE customer_id=c.id AND status='Berjalan') as aktif
            FROM customer c ORDER BY c.id DESC
        """, conn)
        
        if not df_c.empty:
            st.dataframe(df_c[['nama', 'telepon', 'alamat', 'total_kredit', 'aktif']], use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-header"><h3>🔍 Lihat Berkas & Riwayat Customer</h3></div>', unsafe_allow_html=True)
            opsi = {r['nama']: r['id'] for _, r in df_c.iterrows()}
            pilih = st.selectbox("Pilih Customer", list(opsi.keys()))
            cid = opsi[pilih]
            detail_c = df_c[df_c['id'] == cid].iloc[0]
            
            with st.expander(f"Berkas Identitas: {detail_c['nama']}", expanded=True):
                st.write(f"**NIK:** {detail_c['nik']}")
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    foto_ktp_val = detail_c['foto_ktp']
                    if foto_ktp_val is not None and str(foto_ktp_val) not in ["None", ""] and os.path.exists(str(foto_ktp_val)):
                        st.image(foto_ktp_val, caption="Foto KTP", use_container_width=True)
                    else:
                        st.info("Belum ada foto KTP.")
                with col_img2:
                    foto_kk_val = detail_c['foto_kk']
                    if foto_kk_val is not None and str(foto_kk_val) not in ["None", ""] and os.path.exists(str(foto_kk_val)):
                        st.image(foto_kk_val, caption="Foto KK", use_container_width=True)
                    else:
                        st.info("Belum ada foto KK.")

            df_riw = pd.read_sql_query("""
                SELECT k.id, p.nama as produk, k.total_hutang, k.sisa_hutang, k.tenor, k.cicilan_bulan, k.jatuh_tempo, k.status
                FROM kredit k JOIN produk p ON k.produk_id = p.id WHERE k.customer_id=? ORDER BY k.id DESC
            """, conn, params=(cid,))
            if not df_riw.empty:
                st.markdown("**Riwayat Kredit:**")
                for col in ["total_hutang", "sisa_hutang", "cicilan_bulan"]:
                    df_riw[col] = df_riw[col].apply(format_rp)
                st.dataframe(df_riw, use_container_width=True, hide_index=True)
            else:
                st.info("Customer ini belum punya kredit")
        else:
            st.info("Belum ada data customer.")

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

# ==================== 8. SERAH TERIMA BARANG ====================
elif pilihan == "🤝 Serah Terima Barang":
    st.markdown('<div class="main-header"><h1>🤝 Berita Acara Serah Terima</h1><p>Mencegah pelanggan kabur & bukti sah</p></div>', unsafe_allow_html=True)
    
    df_kredit_aktif = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk 
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id 
        JOIN produk p ON k.produk_id = p.id 
        WHERE k.id NOT IN (SELECT kredit_id FROM serah_terima)
        ORDER BY k.id DESC
    """, conn)

    if df_kredit_aktif.empty:
        st.success("✅ Semua barang kredit telah diserahterimakan.")
    else:
        st.info("Silakan isi data serah terima untuk akun kredit di bawah ini.")
        with st.form("form_serah_terima"):
            opsi_kredit = {f"#{r['id']} - {r['customer']} - {r['produk']}": r['id'] for _, r in df_kredit_aktif.iterrows()}
            pilih_kredit = st.selectbox("Pilih Akun Kredit", list(opsi_kredit.keys()))
            kredit_id = opsi_kredit[pilih_kredit]
            
            col1, col2 = st.columns(2)
            with col1:
                imei = st.text_input("Nomor IMEI Perangkat (Wajib)", placeholder="Contoh: 356789012345678")
                penerima = st.text_input("Nama Lengkap Penerima (Wajib)")
            with col2:
                foto_bukti = st.file_uploader("Upload Foto Bukti Terima / Paket (Wajib)", type=["jpg", "jpeg", "png"])
                tgl_serah = st.date_input("Tanggal Serah Terima")
                
            if st.form_submit_button("✅ Konfirmasi Serah Terima"):
                if not imei or not penerima or not foto_bukti:
                    st.error("❌ IMEI, Nama Penerima, dan Foto Bukti wajib diisi!")
                else:
                    path_bukti = save_uploaded_file(foto_bukti, "BUKTI_TERIMA")
                    try:
                        c.execute("""INSERT INTO serah_terima (kredit_id, imei, foto_bukti, tanggal_serah, penerima) 
                                     VALUES (?, ?, ?, ?, ?)""",
                                  (kredit_id, imei, path_bukti, tgl_serah.strftime("%Y-%m-%d"), penerima))
                        conn.commit()
                        log_aksi(st.session_state.username, "SERAH_TERIMA", f"Kredit ID {kredit_id}, IMEI {imei}")
                        flash("🎉 Serah terima berhasil dicatat! Bukti sah telah disimpan.", "success")
                        st.session_state.balloons = True
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📜 Riwayat Serah Terima</h3></div>', unsafe_allow_html=True)
    df_riwayat = pd.read_sql_query("""
        SELECT s.tanggal_serah, c.nama as customer, s.imei, s.penerima, s.foto_bukti
        FROM serah_terima s
        JOIN kredit k ON s.kredit_id = k.id
        JOIN customer c ON k.customer_id = c.id
        ORDER BY s.id DESC
    """, conn)
    
    if not df_riwayat.empty:
        for _, r in df_riwayat.iterrows():
            with st.expander(f"📅 {r['tanggal_serah']} - {r['customer']} (IMEI: {r['imei']})"):
                st.write(f"**Penerima:** {r['penerima']}")
                foto_bukti_val = r['foto_bukti']
                if foto_bukti_val is not None and str(foto_bukti_val) not in ["None", ""] and os.path.exists(str(foto_bukti_val)):
                    st.image(foto_bukti_val, caption="Bukti Serah Terima", width=400)
    else:
        st.info("Belum ada riwayat serah terima.")

# ==================== 9. STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Daftar Stok", "✏️ Edit Harga Jual Pakaian"])

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

        html = '<div class="metric-grid">'
        html += metric_card("📦 Total Item", f"{total_item} jenis", "card-blue")
        html += metric_card("🎒 Total Unit Stok", f"{total_unit} unit", "card-green")
        html += metric_card("🛍️ Total Terjual", f"{total_terjual} unit", "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        st.dataframe(df_p[['nama', 'kategori', 'harga_modal', 'markup_persen', 'harga_jual', 'stok', 'terjual']], use_container_width=True, hide_index=True)

    with tab2:
        df_pakaian = pd.read_sql_query(f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk WHERE kategori IN ({','.join(['?']*len(PAKAIAN_KATEGORI))}) AND (harga_jual IS NULL OR harga_jual <= 0)", conn, params=tuple(PAKAIAN_KATEGORI))
        if df_pakaian.empty:
            st.success("✅ Semua produk pakaian sudah memiliki harga jual!")
        else:
            st.warning(f"⚠️ Ada {len(df_pakaian)} produk pakaian yang belum diisi harga jualnya.")
            st.dataframe(df_pakaian[['nama', 'kategori', 'harga_modal']], use_container_width=True, hide_index=True)
            
            with st.form("form_edit_harga_pakaian"):
                opsi_pk = {f"{r['nama']} (ID: {r['id']})": r['id'] for _, r in df_pakaian.iterrows()}
                pilih_pk = st.selectbox("Pilih Produk Pakaian", list(opsi_pk.keys()))
                pid_pk = opsi_pk[pilih_pk]
                
                harga_jual_baru = st.number_input("Harga Jual Baru (Rp)", min_value=1000.0, step=1000.0)
                
                if st.form_submit_button("💾 Simpan Harga Jual"):
                    try:
                        c.execute("UPDATE produk SET harga_jual=? WHERE id=?", (harga_jual_baru, pid_pk))
                        conn.commit()
                        flash("✅ Harga jual pakaian berhasil diupdate!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")

# ==================== 10. CETAK SLIP KREDIT (VERSI SEDERHANA & RAPI) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit</h1><p>Dokumen cetak untuk pelanggan</p></div>', unsafe_allow_html=True)

    df_k = pd.read_sql_query("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.status, k.total_hutang, k.tanggal_kredit
        FROM kredit k 
        JOIN customer c ON k.customer_id = c.id 
        JOIN produk p ON k.produk_id = p.id
        ORDER BY k.id DESC
    """, conn)

    if df_k.empty:
        st.info("Belum ada transaksi kredit.")
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

        st.markdown('<div class="section-header"><h3>📄 Preview Slip Kredit</h3></div>', unsafe_allow_html=True)
        
        slip_html = f"""
        <div style="border: 2px solid #667eea; padding: 20px; border-radius: 10px; background-color: white; color: #333;">
            <h2 style="text-align: center; color: #667eea;">GRACE'S STORE</h2>
            <p style="text-align: center; font-size: 12px;">{ALAMAT_TOKO}</p>
            <hr style="border-top: 1px solid #ccc;">
            <table style="width: 100%; font-size: 14px;">
                <tr><td><b>No. Kontrak</b></td><td>: #{d['id']}</td></tr>
                <tr><td><b>Tanggal</b></td><td>: {d['tanggal_kredit']}</td></tr>
                <tr><td><b>Nama Customer</b></td><td>: {d['cn']}</td></tr>
                <tr><td><b>Telepon</b></td><td>: {d['telepon']}</td></tr>
                <tr><td><b>Alamat</b></td><td>: {d['alamat']}</td></tr>
                <tr><td><b>Barang</b></td><td>: {d['pn']}</td></tr>
            </table>
            <hr style="border-top: 1px solid #ccc;">
            <table style="width: 100%; font-size: 14px;">
                <tr><td><b>Harga Cash</b></td><td style="text-align: right;">{format_rp(d['harga_cash'])}</td></tr>
                <tr><td><b>DP Dibayar</b></td><td style="text-align: right;">{format_rp(d['dp'])}</td></tr>
                <tr><td><b>Pokok Hutang</b></td><td style="text-align: right;">{format_rp(d['pokok_hutang'])}</td></tr>
                <tr><td><b>Total Hutang</b></td><td style="text-align: right;"><b>{format_rp(d['total_hutang'])}</b></td></tr>
                <tr><td><b>Cicilan / Bulan</b></td><td style="text-align: right;">{format_rp(d['cicilan_bulan'])}</td></tr>
                <tr><td><b>Tenor</b></td><td style="text-align: right;">{d['tenor']} Bulan</td></tr>
            </table>
            <hr style="border-top: 1px solid #ccc;">
            <p style="font-size: 12px; text-align: justify;">Dengan menandatangani dokumen ini, pelanggan setuju untuk melakukan pembayaran angsuran tepat waktu sesuai dengan jadwal yang telah disepakati. Keterlambatan akan dikenakan denda sesuai ketentuan toko.</p>
            <br><br>
            <table style="width: 100%; text-align: center; font-size: 14px;">
                <tr>
                    <td>Penerima,<br><br><br><br>( {d['cn']} )</td>
                    <td>Hormat Kami,<br><br><br><br>( GRACE STORE )</td>
                </tr>
            </table>
        </div>
        """
        st.markdown(slip_html, unsafe_allow_html=True)

# ==================== 11. MENU SISA (PLACEHOLDER) ====================
elif pilihan in ["🚨 Overdue & Denda", "🔔 Alert & Reminder", "📊 Laporan & Analitik", "👕 Modal vs Profit", "💾 Backup, Cetak & Impor", "👤 Manajemen User", "📝 Log Aktivitas"]:
    st.markdown(f'<div class="main-header"><h1>{pilihan}</h1></div>', unsafe_allow_html=True)
    
    if pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
        df_log = pd.read_sql_query("SELECT waktu, username, aksi, detail FROM log_aktivitas ORDER BY id DESC LIMIT 100", conn)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info(f"Fitur **{pilihan}** sedang dalam tahap pengembangan.")
