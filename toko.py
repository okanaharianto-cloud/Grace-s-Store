# ==================== 0. PENGATURAN OWNER ====================
if pilihan == "⚙️ Pengaturan Owner" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>⚙️ Pengaturan Owner</h1><p>Atur persentase default toko sesuai keinginan Anda</p></div>', unsafe_allow_html=True)
    st.info("💡 **PENTING:** Pengaturan di halaman ini adalah **NILAI DEFAULT** untuk transaksi baru. Saat membuat Kredit Baru, Anda tetap bisa mengedit persentase Bunga dan DP secara manual per transaksi.")

    st.markdown('<div class="section-header"><h3>💰 Markup / Margin Default</h3></div>', unsafe_allow_html=True)
    markup_val = st.number_input("Markup default untuk produk **non-pakaian** (%)", min_value=0.0, max_value=500.0,
                                 value=get_pengaturan_float("markup_default_persen", 5.0), step=1.0, key="input_markup_owner")
    if st.button("💾 Simpan Markup Default", key="save_markup"):
        try:
            set_pengaturan("markup_default_persen", f"{markup_val:.2f}")
            log_aksi(st.session_state.username, "SET_MARKUP", f"{markup_val}%")
            flash(f"✅ Markup default diubah ke **{markup_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>💳 Bunga Kredit Default</h3></div>', unsafe_allow_html=True)
    bunga_val = st.number_input("Bunga flat per **6 bulan** (%)", min_value=0.0, max_value=200.0,
                                value=get_pengaturan_float("bunga_flat_6bln_persen", 40.0), step=1.0, key="input_bunga_owner")
    if st.button("💾 Simpan Bunga Default", key="save_bunga"):
        try:
            set_pengaturan("bunga_flat_6bln_persen", f"{bunga_val:.2f}")
            log_aksi(st.session_state.username, "SET_BUNGA", f"{bunga_val}%")
            flash(f"✅ Bunga flat 6 bulan diubah ke **{bunga_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>🪙 DP Minimal</h3></div>', unsafe_allow_html=True)
    dp_val = st.number_input("DP minimal (% dari harga cash)", min_value=0.0, max_value=100.0,
                             value=get_pengaturan_float("dp_minimal_persen", 20.0), step=1.0, key="input_dp_owner")
    if st.button("💾 Simpan DP Minimal", key="save_dp"):
        try:
            set_pengaturan("dp_minimal_persen", f"{dp_val:.2f}")
            log_aksi(st.session_state.username, "SET_DP", f"{dp_val}%")
            flash(f"✅ DP minimal diubah ke **{dp_val:.1f}%**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>⏰ Denda Keterlambatan</h3></div>', unsafe_allow_html=True)
    denda_val = st.number_input("Denda per hari telat (% dari cicilan)", min_value=0.0, max_value=20.0,
                                value=get_pengaturan_float("denda_per_hari_persen", 0.4), step=0.1,
                                format="%.2f", key="input_denda_owner")
    if st.button("💾 Simpan Denda", key="save_denda"):
        try:
            set_pengaturan("denda_per_hari_persen", f"{denda_val:.2f}")
            log_aksi(st.session_state.username, "SET_DENDA", f"{denda_val}%")
            flash(f"✅ Denda diubah ke **{denda_val:.2f}% per hari**", "success")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📅 Pilihan Tenor</h3></div>', unsafe_allow_html=True)
    tenor_val = st.text_input("Pilihan tenor (bulan, pisahkan dengan koma)",
                              value=str(get_pengaturan("tenor_options", "1,2,3,6,12,18,24")), key="input_tenor_owner")
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
    df_set = read_sql("SELECT kunci, nilai, keterangan FROM pengaturan ORDER BY kunci")
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
            _tenor_list = get_tenor_list()
            sim_tenor = st.selectbox("Tenor (Bulan)", _tenor_list, index=min(3, len(_tenor_list) - 1))
            sim_bunga_6bln = st.number_input("Bunga Flat / 6 Bln (%)", min_value=0.0, value=40.0, step=1.0)

        hide_detail = st.toggle("🙈 Sembunyikan Rincian Sensitif (Mode Presentasi Pelanggan)", value=False,
                                help="Jika aktif, hanya Harga Cash, DP, dan Cicilan yang muncul. Bunga, Pokok, dan Total Hutang disembunyikan.")

        h_cash = sim_harga_jual if sim_harga_jual > 0 else round(sim_modal * (1 + sim_markup / 100), -2)
        dp_val = round(h_cash * sim_dp_persen / 100, -2)
        pokok = round(h_cash - dp_val, -2)
        rate_bulan = (sim_bunga_6bln / 100) / 6
        total_bunga = round(pokok * rate_bulan * sim_tenor, -2)
        total_hutang = pokok + total_bunga
        cicilan = round(total_hutang / sim_tenor, -2) if sim_tenor > 0 else 0

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

    total_produk = c.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    total_stok = c.execute("SELECT COALESCE(SUM(stok),0) FROM produk").fetchone()[0]
    total_customer = c.execute("SELECT COUNT(*) FROM customer").fetchone()[0]

    terjual_kredit = c.execute("SELECT COUNT(*) FROM kredit").fetchone()[0]
    terjual_cash = c.execute("SELECT COALESCE(SUM(jumlah),0) FROM transaksi_cash").fetchone()[0]
    total_terjual = int(terjual_kredit or 0) + int(terjual_cash or 0)

    kredit_aktif = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan'").fetchone()[0]
    kredit_lunas = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Lunas'").fetchone()[0]
    total_piutang = c.execute("SELECT COALESCE(SUM(sisa_hutang),0) FROM kredit WHERE status='Berjalan'").fetchone()[0]

    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    overdue_count = c.execute("SELECT COUNT(*) FROM kredit WHERE status='Berjalan' AND jatuh_tempo < ?", (tgl_skrg,)).fetchone()[0]

    pendapatan_kredit = c.execute("SELECT COALESCE(SUM(dp + total_hutang),0) FROM kredit").fetchone()[0]
    pendapatan_cash = c.execute("SELECT COALESCE(SUM(total_harga),0) FROM transaksi_cash").fetchone()[0]
    total_pendapatan = float(pendapatan_kredit or 0) + float(pendapatan_cash or 0)

    laba_kredit = c.execute("SELECT COALESCE(SUM((k.dp + k.total_hutang) - p.harga_modal),0) FROM kredit k JOIN produk p ON k.produk_id = p.id").fetchone()[0]
    laba_cash = c.execute("SELECT COALESCE(SUM(laba),0) FROM transaksi_cash").fetchone()[0]
    total_laba = float(laba_kredit or 0) + float(laba_cash or 0)

    margin_persen = (total_laba / total_pendapatan * 100) if total_pendapatan > 0 else 0
    placeholders = ",".join(["?"] * len(PAKAIAN_KATEGORI))
    pakaian_belum_harga = c.execute(
        f"SELECT COUNT(*) FROM produk WHERE kategori IN ({placeholders}) AND (harga_jual IS NULL OR harga_jual <= 0)",
        tuple(PAKAIAN_KATEGORI)
    ).fetchone()[0]
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
        df_top = read_sql("""
            SELECT produk, SUM(qty) as jumlah_terjual FROM (
                SELECT p.nama as produk, 1 as qty FROM kredit k JOIN produk p ON k.produk_id = p.id
                UNION ALL
                SELECT p.nama as produk, t.jumlah as qty FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
            ) x GROUP BY produk ORDER BY jumlah_terjual DESC LIMIT 5
        """)
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
        df_bayar = read_sql("SELECT substr(tanggal,1,7) as bulan, SUM(jumlah_bayar) as total FROM pembayaran GROUP BY substr(tanggal,1,7) ORDER BY bulan")
        if not df_bayar.empty:
            chart = alt.Chart(df_bayar).mark_area(
                line={'color': '#667eea'},
                color=alt.Gradient(gradient='linear',
                                   stops=[alt.GradientStop(color='#f093fb', offset=0), alt.GradientStop(color='#667eea', offset=1)],
                                   x1=1, x2=1, y1=1, y2=0)
            ).encode(x=alt.X('bulan:N', title='Bulan'), y=alt.Y('total:Q', title='Total (Rp)')).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Belum ada pembayaran")

    st.markdown('<div class="section-header"><h3>⚠️ Peringatan Stok Menipis (≤3 unit)</h3></div>', unsafe_allow_html=True)
    df_tipis = read_sql("SELECT nama, kategori, stok FROM produk WHERE stok <= 3 ORDER BY stok ASC")
    if not df_tipis.empty:
        st.dataframe(df_tipis, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Semua stok aman")

    st.markdown('<div class="section-header"><h3>⏰ Jatuh Tempo 7 Hari ke Depan</h3></div>', unsafe_allow_html=True)
    tgl_7 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    df_dekat = read_sql("""
        SELECT c.nama as customer, c.telepon, k.cicilan_bulan, k.jatuh_tempo
        FROM kredit k JOIN customer c ON k.customer_id = c.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?
        ORDER BY k.jatuh_tempo
    """, (tgl_skrg, tgl_7))
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
            st.caption(f"💡 Harga Cash Otomatis = Modal × (1 + {markup_persen:.1f}%) = **{format_rp(round(harga_modal * (1 + markup_persen / 100), -2))}**")

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
        tenor_sim = st.selectbox("Tenor (Bulan)", tenor_list, index=min(3, len(tenor_list) - 1))
        bunga_sim = st.number_input(f"Bunga Flat / 6 Bln (%) — default owner: {bunga_flat:.1f}%", min_value=0.0, value=bunga_flat, step=1.0)

    harga_cash = round(modal_sim * (1 + markup_default / 100), -2)
    dp_min = round(harga_cash * dp_sim / 100, -2)
    rate = (bunga_sim / 100) / 6
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
    df_produk = read_sql("SELECT id, nama, stok FROM produk ORDER BY nama")
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
                c.execute("INSERT INTO transaksi_in (produk_id, jumlah, tanggal) VALUES (?,?,?)",
                          (pid, jumlah, datetime.now().strftime("%Y-%m-%d")))
                c.execute("UPDATE produk SET stok = stok + ? WHERE id = ?", (jumlah, pid))
                conn.commit()
                log_aksi(st.session_state.username, "RESTOCK", f"Produk ID {pid}, +{jumlah}")
                flash(f"✅ Stok bertambah {jumlah} unit!", "success")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"❌ Gagal: {e}")

        st.markdown('<div class="section-header"><h3>📜 Riwayat Barang Masuk Terakhir</h3></div>', unsafe_allow_html=True)
        df_in = read_sql("""
            SELECT t.id, t.produk_id, p.nama as produk, t.jumlah, t.tanggal
            FROM transaksi_in t JOIN produk p ON t.produk_id = p.id
            ORDER BY t.id DESC LIMIT 20
        """)
        st.dataframe(df_in.drop(columns=['id', 'produk_id']) if not df_in.empty else df_in,
                     use_container_width=True, hide_index=True)

        if not df_in.empty:
            st.markdown("**✏️ Edit / Hapus Barang Masuk**")
            opsi_in = {f"ID #{r['id']} - {r['produk']} - {r['jumlah']} unit ({r['tanggal']})":
                       (r['id'], r['produk_id'], r['jumlah'], r['tanggal']) for _, r in df_in.iterrows()}
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
                        selisih = int(new_qty) - int(qty_in)
                        c.execute("UPDATE transaksi_in SET jumlah=?, tanggal=? WHERE id=?",
                                  (new_qty, new_tgl_in.strftime("%Y-%m-%d"), id_in))
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

# ==================== 8. SERAH TERIMA BARANG ====================
elif pilihan == "🤝 Serah Terima Barang":
    st.markdown('<div class="main-header"><h1>🤝 Berita Acara Serah Terima</h1><p>Mencegah pelanggan kabur & bukti sah</p></div>', unsafe_allow_html=True)

    df_kredit_aktif = read_sql("""
        SELECT k.id, c.nama as customer, p.nama as produk
        FROM kredit k
        JOIN customer c ON k.customer_id = c.id
        JOIN produk p ON k.produk_id = p.id
        WHERE k.id NOT IN (SELECT kredit_id FROM serah_terima)
        ORDER BY k.id DESC
    """)

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
                        c.execute("""INSERT INTO serah_terima
                                     (kredit_id, imei, foto_bukti, tanggal_serah, penerima)
                                     VALUES (?, ?, ?, ?, ?)""",
                                  (kredit_id, imei, path_bukti,
                                   tgl_serah.strftime("%Y-%m-%d"), penerima))
                        conn.commit()
                        log_aksi(st.session_state.username, "SERAH_TERIMA", f"Kredit ID {kredit_id}, IMEI {imei}")
                        flash("🎉 Serah terima berhasil dicatat! Bukti sah telah disimpan.", "success")
                        st.session_state.balloons = True
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e}")

    st.markdown('<div class="section-header"><h3>📜 Riwayat Serah Terima</h3></div>', unsafe_allow_html=True)
    df_riwayat = read_sql("""
        SELECT s.tanggal_serah, c.nama as customer, s.imei, s.penerima, s.foto_bukti
        FROM serah_terima s
        JOIN kredit k ON s.kredit_id = k.id
        JOIN customer c ON k.customer_id = c.id
        ORDER BY s.id DESC
    """)

    if not df_riwayat.empty:
        for _, r in df_riwayat.iterrows():
            with st.expander(f"📅 {r['tanggal_serah']} - {r['customer']} (IMEI: {r['imei']})"):
                st.write(f"**Penerima:** {r['penerima']}")
                if r['foto_bukti']:
                    try:
                        st.image(r['foto_bukti'], caption="Bukti Serah Terima", width=400)
                    except Exception:
                        st.caption(f"Path: {r['foto_bukti']}")
    else:
        st.info("Belum ada riwayat serah terima.")

# ==================== 9. STOK BARANG ====================
elif pilihan == "📦 Stok Barang":
    st.markdown('<div class="main-header"><h1>📦 Real-time Stok Gudang</h1></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Daftar Stok", "✏️ Edit Harga Jual Pakaian"])

    with tab1:
        df_p = read_sql("""
            SELECT p.*,
                   ((SELECT COUNT(*) FROM kredit k WHERE k.produk_id = p.id) +
                    (SELECT COALESCE(SUM(jumlah), 0) FROM transaksi_cash t WHERE t.produk_id = p.id)) as terjual
            FROM produk p ORDER BY stok ASC
        """)

        total_item = len(df_p)
        total_unit = df_p['stok'].sum() if not df_p.empty else 0
        total_terjual = df_p['terjual'].sum() if not df_p.empty else 0

        html = '<div class="metric-grid">'
        html += metric_card("📦 Total Item", f"{total_item} jenis", "card-blue")
        html += metric_card("🎒 Total Unit Stok", f"{total_unit} unit", "card-green")
        html += metric_card("🛍️ Total Terjual", f"{total_terjual} unit", "card-orange")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        st.dataframe(df_p[['nama', 'kategori', 'harga_modal', 'markup_persen', 'harga_jual', 'stok', 'terjual']],
                     use_container_width=True, hide_index=True)

    with tab2:
        placeholders = ",".join(["?"] * len(PAKAIAN_KATEGORI))
        df_pakaian = read_sql(
            f"SELECT id, nama, kategori, harga_modal, harga_jual FROM produk "
            f"WHERE kategori IN ({placeholders}) AND (harga_jual IS NULL OR harga_jual <= 0)",
            tuple(PAKAIAN_KATEGORI)
        )
        if df_pakaian.empty:
            st.success("✅ Semua produk pakaian sudah memiliki harga jual!")
        else:
            st.warning(f"⚠️ Ada {len(df_pakaian)} produk pakaian yang belum diisi harga jualnya.")
            st.dataframe(df_pakaian[['nama', 'kategori', 'harga_modal']],
                         use_container_width=True, hide_index=True)

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

# ==================== 10. CETAK SLIP KREDIT (FULL HTML) ====================
elif pilihan == "🖨️ Cetak Slip Kredit":
    st.markdown('<div class="main-header"><h1>🖨️ Cetak Slip Kredit & Perjanjian</h1><p>Dokumen cetak profesional sesuai standar OJK</p></div>', unsafe_allow_html=True)

    df_k = read_sql("""
        SELECT k.id, c.nama as customer, p.nama as produk, k.status,
               k.total_hutang, k.sisa_hutang, k.tanggal_kredit
        FROM kredit k
        JOIN customer c ON k.customer_id = c.id
        JOIN produk p ON k.produk_id = p.id
        ORDER BY k.id DESC
    """)

    if df_k.empty:
        st.info("Belum ada transaksi kredit. Buat kredit baru terlebih dahulu di menu 📤 Kredit Baru.")
    else:
        df_k['label'] = df_k.apply(
            lambda r: f"#{r['id']} - {r['customer']} - {r['produk']} ({r['status']})", axis=1)
        opsi = dict(zip(df_k['label'], df_k['id']))
        pilih = st.selectbox("🔍 Pilih Transaksi Kredit", list(opsi.keys()))
        kid = opsi[pilih]

        d = read_sql("""
            SELECT k.*, c.nama as cn, c.telepon, c.alamat, c.nik,
                   c.tanggal_lahir, c.status_kawin, p.nama as pn
            FROM kredit k
            LEFT JOIN customer c ON k.customer_id = c.id
            LEFT JOIN produk p ON k.produk_id = p.id
            WHERE k.id=?
        """, (kid,)).iloc[0]

        def clean(v, fallback="........................."):
            if v is None or pd.isna(v):
                return fallback
            s = str(v).strip()
            if s == "" or s == "-" or s.lower() == "none":
                return fallback
            return s

        nik_cust = clean(d.get('nik'))
        tgl_lahir_cust = clean(d.get('tanggal_lahir'))
        status_kawin_cust = clean(d.get('status_kawin'))

        st.markdown('<div class="section-header"><h3>✏️ Edit Manual Data Akad (Khusus Cetakan Ini)</h3></div>', unsafe_allow_html=True)
        with st.expander("Buka Form Edit Manual", expanded=False):
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
                m_bunga_bln = st.number_input("Bunga Flat / Bulan (%)",
                                              value=round(get_pengaturan_float("bunga_flat_6bln_persen", 40.0) / 6, 2),
                                              step=0.1, format="%.2f")
                m_tempo = st.date_input("Jatuh Tempo", value=pd.to_datetime(d['jatuh_tempo']).date())
                _status_opsi = ["Berjalan", "Lunas", "Batal"]
                _status_idx = _status_opsi.index(d['status']) if d['status'] in _status_opsi else 0
                m_status = st.selectbox("Status", _status_opsi, index=_status_idx)
                m_metode = st.radio("Metode", ["Tunai (Cash)", "Transfer Bank", "Kredit Angsuran"],
                                    index=2, horizontal=True)

            if st.button("💾 Simpan Perubahan Ini ke Database"):
                try:
                    c.execute("""UPDATE kredit
                                 SET harga_cash=?, dp=?, pokok_hutang=?, total_hutang=?,
                                     cicilan_bulan=?, tenor=?, jatuh_tempo=?, status=?,
                                     updated_at=?, updated_by=?
                                 WHERE id=?""",
                              (m_harga_cash, m_dp, m_pokok, m_total_hutang, m_cicilan, m_tenor,
                               m_tempo.strftime("%Y-%m-%d"), m_status,
                               get_current_time(), st.session_state.username, kid))
                    recalculate_kredit(kid)
                    conn.commit()
                    log_aksi(st.session_state.username, "EDIT_AKAD_KREDIT", f"ID {kid}")
                    flash("✅ Perubahan berhasil disimpan ke database!", "success")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Gagal: {e}")

        df_bayar = read_sql(
            "SELECT id, tanggal, jumlah_bayar, denda, keterangan FROM pembayaran WHERE kredit_id=? ORDER BY id",
            (kid,)
        )

        # FIX BUG: cek tanggal_kredit valid (bukan '-')
        tk_raw = d.get('tanggal_kredit')
        if tk_raw is not None and not pd.isna(tk_raw) and str(tk_raw).strip() not in ("", "-", "None"):
            tanggal_kredit_str = str(tk_raw)[:10]
        else:
            try:
                tanggal_kredit_str = (datetime.strptime(str(d['jatuh_tempo'])[:10], "%Y-%m-%d")
                                      - timedelta(days=30)).strftime("%Y-%m-%d")
            except Exception:
                tanggal_kredit_str = datetime.now().strftime("%Y-%m-%d")

        tenor_asli = int(m_tenor)
        rate_bulan = m_bunga_bln / 100

        tampilkan_banding = st.toggle("Tampilkan Perbandingan 2 Tenor (Opsi A & B)", value=True,
                                       help="Aktifkan untuk menampilkan 2 opsi tenor.")

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

            rows_1 = "".join([
                f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td>"
                f"<td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td>"
                f"<td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>"
                f"{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>"
                for r in sched_1
            ])
            rows_2 = "".join([
                f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td>"
                f"<td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td>"
                f"<td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>"
                f"{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>"
                for r in sched_2
            ])

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
            rows_1 = "".join([
                f"<tr><td class='c'>{r['ke']}</td><td>{r['jatuh_tempo']}</td>"
                f"<td class='r'>{format_rp(r['angsuran'])}</td><td class='r'>{format_rp(r['sisa'])}</td>"
                f"<td class='c'><span class='{'status-lunas' if r['ke'] <= paid_count else 'status-pending'}'>"
                f"{'LUNAS' if r['ke'] <= paid_count else 'BELUM'}</span></td></tr>"
                for r in sched_1
            ])
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
                        <tbody>{rows_1}<tr class="total"><td class="c" colspan="2">TOTAL KEWAJIBAN</td><td class="r">{format_rp(total_1)}</td><td class="r">Rp 0</td><td class="c">—</td></tr></tbody>
                    </table>
                </div>
            </div>
            """

        biaya_materai = 10000
        cicilan_terakhir = float(m_cicilan) + biaya_materai
        denpersen = get_pengaturan_float("denda_per_hari_persen", 1.0)
        tgl_cetak_str = datetime.now().strftime('%d %B %Y')

        perjanjian_html = f"""
        <div class="agreement-container">
            <div class="doc-title">
                <h2>PERJANJIAN PEMBIAYAAN KONSUMEN</h2>
                <div class="doc-number">Nomor: GRC-INV-{kid}/PERJ/2026</div>
            </div>
            
            <p>Pada hari ini, <b>{tgl_cetak_str}</b>, yang bertanda tangan di bawah ini:</p>
            
            <table class="party-table">
                <tr>
                    <td class="label"><b>PIHAK PERTAMA</b></td>
                    <td>: <b>CV. GRACE HAVEN TRANSPORT</b> (Grace's Electronic), berkedudukan di {ALAMAT_TOKO}. Berdasarkan Akta Notaris Ladi Amelia P, S.H., M.Kn. Nomor 03 Tanggal 23 September 2026, NIB: 1510260022275, NPWP: 1000 0000 1152 1195. Dalam hal ini diwakili oleh <b>ADI HARIANTO, S.E.</b> selaku Direktur.</td>
                </tr>
                <tr>
                    <td class="label"><b>PIHAK KEDUA</b></td>
                    <td>: <b>{str(d['cn']).upper()}</b>, lahir di {tgl_lahir_cust}, Warga Negara Indonesia, Pekerjaan Wiraswasta, Status Perkawinan <b>{status_kawin_cust}</b>, bertempat tinggal di {d['alamat']}, Telp/WA: <b>{d['telepon']}</b>. Pemegang Kartu Tanda Penduduk (KTP) dengan NIK: <b>{nik_cust}</b>.</td>
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
                <li>Apabila Pihak Kedua terlambat membayar angsuran melewati tanggal jatuh tempo, dikenakan denda sebesar <b>{denpersen}% per hari</b> dari jumlah angsuran yang tertunggak.</li>
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
                    <svg class="cert-sig-barcode" id="signatureBarcode-{kid}"></svg>
                </div>
                <div class="sig-name">ADI HARIANTO, S.E.</div>
                <div class="sig-role">Direktur CV. Grace Haven Transport</div>
            </div>
            
            <div class="sig-box">
                <div class="sig-title">PIHAK KEDUA (DEBITUR)</div>
                <div class="ematerai-box">
                    (Tempel e-Meterai / TTD Basah)
                </div>
                <div class="sig-name">{str(d['cn']).upper()}</div>
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
                    <div class="addr">
                        {ALAMAT_TOKO}<br>
                        HP/WA: 0822-9954-8411
                    </div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Invoice Kredit</div>
                    <div class="inv-no">#GRC-INV-{kid}</div>
                    <div class="inv-date">{tgl_cetak_str}</div>
                </div>
            </header>

            <div class="meta">
                <div>Status: <b style="color:var(--success);">● {str(m_status).upper()}</b></div>
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
                    <div class="sum-card green">
                        <div class="lbl">DP Dibayar</div>
                        <div class="val">{format_rp(m_dp)}</div>
                    </div>
                    <div class="sum-card amber">
                        <div class="lbl">Angsuran / Bulan</div>
                        <div class="val">{format_rp(m_cicilan)}</div>
                    </div>
                </div>

                {html_tenor_options}
                {html_schedule}
                
                <div class="note-text">
                    *Catatan: DP {format_rp(m_dp)} telah diterima. Pokok {format_rp(m_pokok)} diangsur sesuai tenor yang dipilih. Terdapat Biaya Administrasi/Materai sebesar <b>Rp 10.000</b> (di luar angsuran) yang ditagihkan bersamaan dengan pembayaran angsuran terakhir. Total yang disetor pada bulan ke-{tenor_asli} adalah {format_rp(cicilan_terakhir)}.
                </div>

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
                    <div class="addr">
                        {ALAMAT_TOKO}<br>
                        HP/WA: 0822-9954-8411
                    </div>
                </div>
                <div class="title-box">
                    <div class="badge-inv">Surat Perjanjian Kredit</div>
                    <div class="inv-no">#GRC-INV-{kid}</div>
                    <div class="inv-date">{tgl_cetak_str}</div>
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
            
            .btn-print-wrap {{ position: sticky; top: 0; z-index: 9999; background: rgba(243,244,246,0.95); padding: 12px 0; text-align: center; border-bottom: 1px solid var(--border); margin-bottom: 20px; }}
            .btn-print {{ background: linear-gradient(135deg, #2563eb, #1e40af); color: white; border: none; padding: 12px 24px; font-size: 14px; border-radius: 50px; cursor: pointer; font-weight: 600; width: 100%; max-width: 350px; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }}
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

            .tenor-options {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
            .tenor-card {{ position: relative; border: 1.5px solid #d1d5db; border-radius: 8px; padding: 12px 16px; }}
            .tenor-card.recommended {{ border-color: #1e3a8a; }}
            .tenor-card.recommended::before {{ content: 'DIPILIH'; position: absolute; top: -1.5px; right: -1.5px; background: #b8956a; color: #fff; font-size: 7.5px; font-weight: 700; letter-spacing: 1px; padding: 2px 7px; border-radius: 0 6px 0 6px; }}
            .tc-label {{ font-size: 9px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }}
            .tc-title {{ font-family: Georgia, serif; font-size: 14px; font-weight: 700; color: #1a2b47; margin: 2px 0 6px; }}
            .tc-row {{ display: flex; justify-content: space-between; font-size: 10px; padding: 2px 0; }}
            .tc-row .k {{ color: #6b7280; }}
            .tc-row .v {{ color: #1a2b47; font-weight: 600; }}
            .tc-row.main {{ border-top: 1px solid #e5e7eb; padding-top: 4px; margin-top: 2px; font-size: 11px; }}
            .tc-row.main .v {{ color: #1e3a8a; font-size: 13px; }}

            .sched-wrap {{ display: grid; gap: 16px; margin-bottom: 16px; }}
            .sched {{ border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
            .sched-h {{ padding: 10px 16px; font-size: 11px; font-weight: 700; color: #fff; }}
            .sched-h.two {{ background: #1e3a8a; }}
            .sched-h.three {{ background: #475569; }}
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

            .footer {{ background: #f8fafc; padding: 12px 24px; border-top: 1px solid var(--border); text-align: center; font-size: 10px; color: var(--text-muted); }}
            .footer-brand {{ font-weight: 700; color: var(--primary); margin-bottom: 2px; }}

            /* Agreement styles */
            .agreement-container {{ font-size: 11px; line-height: 1.6; color: var(--text-main); }}
            .doc-title {{ text-align: center; margin-bottom: 16px; }}
            .doc-title h2 {{ font-family: Georgia, serif; font-size: 16px; font-weight: 700; color: var(--primary); margin-bottom: 4px; }}
            .doc-number {{ font-family: monospace; font-size: 11px; color: var(--text-muted); }}
            .agreement-container p {{ margin-bottom: 10px; text-align: justify; }}
            .party-table {{ width: 100%; margin-bottom: 12px; font-size: 10.5px; }}
            .party-table td {{ padding: 4px 6px; vertical-align: top; }}
            .party-table td.label {{ width: 100px; }}
            .pasal-title {{ font-size: 11px; font-weight: 700; color: var(--primary); text-align: center; margin: 14px 0 8px 0; letter-spacing: 0.5px; }}
            .pasal-list {{ padding-left: 20px; margin-bottom: 8px; font-size: 10.5px; }}
            .pasal-list li {{ margin-bottom: 4px; text-align: justify; }}

            .signature-area {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 30px; padding-top: 20px; border-top: 1px solid var(--border); }}
            .sig-box {{ text-align: center; }}
            .sig-title {{ font-size: 10px; font-weight: 700; color: var(--primary); margin-bottom: 8px; text-transform: uppercase; }}
            .cert-sig-box {{ border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: #fafbff; margin-bottom: 6px; }}
            .cert-sig-header {{ display: inline-flex; align-items: center; gap: 4px; background: #e0e7ff; color: #3730a3; font-size: 7.5px; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-bottom: 6px; }}
            .cert-sig-name {{ font-weight: 700; color: var(--primary); font-size: 11px; }}
            .cert-sig-text {{ font-size: 8.5px; color: var(--text-muted); margin: 2px 0 6px; line-height: 1.3; }}
            .cert-sig-barcode {{ max-width: 100%; }}
            .ematerai-box {{ border: 2px dashed #cbd5e1; border-radius: 8px; padding: 28px 12px; font-size: 9px; color: var(--text-muted); background: #f9fafb; margin-bottom: 6px; }}
            .sig-name {{ font-weight: 700; font-size: 11px; color: var(--text-main); }}
            .sig-role {{ font-size: 9.5px; color: var(--text-muted); }}

            /* PRINT */
            @media print {{
                body {{ background: #fff; padding: 0; }}
                .page {{ box-shadow: none; margin-bottom: 0; border-radius: 0; max-width: 100%; }}
                .btn-print-wrap {{ display: none; }}
                .page + .page {{ page-break-before: always; }}
            }}
        </style>
        </head>
        <body>
            <div class="btn-print-wrap">
                <button class="btn-print" onclick="window.print()">🖨️ CETAK / SIMPAN PDF (2 Halaman)</button>
            </div>
            {html_page1}
            {html_page2}
            <script>
                try {{
                    JsBarcode("#signatureBarcode-{kid}", "GRC-INV-{kid}-PERJ", {{ format: "CODE128", width: 1, height: 24, displayValue: false, margin: 0 }});
                }} catch(e) {{ console.log(e); }}
            </script>
        </body>
        </html>
        """

        st.info("💡 Klik tombol **CETAK / SIMPAN PDF** di bawah untuk mencetak atau menyimpan sebagai PDF.")
        components.html(invoice_html, height=850, scrolling=True)
        # ==================== 11. OVERDUE & DENDA ====================
elif pilihan == "🚨 Overdue & Denda":
    st.markdown('<div class="main-header"><h1>🚨 Overdue & Denda</h1><p>Pantau kredit macet & hitung denda otomatis</p></div>', unsafe_allow_html=True)

    tgl_skrg_str = datetime.now().strftime("%Y-%m-%d")
    df_overdue = read_sql("""
        SELECT k.id, c.nama as customer, c.telepon, p.nama as produk,
               k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo, k.status
        FROM kredit k
        JOIN customer c ON k.customer_id = c.id
        JOIN produk p ON k.produk_id = p.id
        WHERE k.status='Berjalan' AND k.jatuh_tempo < ?
        ORDER BY k.jatuh_tempo ASC
    """, (tgl_skrg_str,))

    if df_overdue.empty:
        st.success("✅ Tidak ada kredit overdue. Semua pembayaran lancar!")
    else:
        denda_persen = get_pengaturan_float("denda_per_hari_persen", 0.4)
        rows = []
        for _, r in df_overdue.iterrows():
            try:
                tgl_tempo = datetime.strptime(str(r['jatuh_tempo'])[:10], "%Y-%m-%d").date()
            except Exception:
                tgl_tempo = datetime.now().date()
            hari_telat = (datetime.now().date() - tgl_tempo).days
            denda = hitung_denda(r['cicilan_bulan'], hari_telat)
            total_tagih = float(r['sisa_hutang']) + denda
            rows.append({
                "ID": r['id'],
                "Customer": r['customer'],
                "Telepon": r['telepon'],
                "Produk": r['produk'],
                "Cicilan": format_rp(r['cicilan_bulan']),
                "Sisa": format_rp(r['sisa_hutang']),
                "Jatuh Tempo": str(r['jatuh_tempo'])[:10],
                "Hari Telat": hari_telat,
                "Denda": format_rp(denda),
                "Total Tagih": format_rp(total_tagih),
            })

        total_denda = sum(float(r['sisa_hutang']) for r in [dict(x) for _, x in df_overdue.iterrows()])  # placeholder
        total_hari = sum(int(r['Hari Telat']) for r in rows)
        total_tagih_semua = sum(float(r['sisa_hutang']) for _, r in df_overdue.iterrows())

        # hitung denda total per akun
        denda_total_semua = 0.0
        for _, r in df_overdue.iterrows():
            try:
                tgl_tempo = datetime.strptime(str(r['jatuh_tempo'])[:10], "%Y-%m-%d").date()
                hari = (datetime.now().date() - tgl_tempo).days
            except Exception:
                hari = 0
            denda_total_semua += hitung_denda(r['cicilan_bulan'], hari)

        html = '<div class="metric-grid">'
        html += metric_card("🚨 Akun Overdue", f"{len(df_overdue)} akun", "card-pink")
        html += metric_card("📅 Total Hari Telat", f"{total_hari} hari", "card-orange")
        html += metric_card("💰 Total Sisa Pokok", format_rp(total_tagih_semua), "card-dark")
        html += metric_card(f"⚠️ Total Denda ({denda_persen}%/hari)", format_rp(denda_total_semua), "card-pink")
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header"><h3>📲 Kirim Reminder WhatsApp</h3></div>', unsafe_allow_html=True)
        opsi_wa = {
            f"#{r['id']} - {r['customer']} ({r['telepon']})": r
            for r in rows
        }
        pilih_wa = st.selectbox("Pilih Customer", list(opsi_wa.keys()))
        r_wa = opsi_wa[pilih_wa]
        pesan_wa = (
            f"Halo Bapak/Ibu *{r_wa['Customer']}*,\n\n"
            f"Kami dari *GRACE'S ELECTRONIC* mengingatkan bahwa angsuran Anda untuk:\n"
            f"• Produk: {r_wa['Produk']}\n"
            f"• Cicilan: {r_wa['Cicilan']}\n"
            f"• Jatuh tempo: {r_wa['Jatuh Tempo']}\n"
            f"• Terlambat: {r_wa['Hari Telat']} hari\n"
            f"• Denda saat ini: {r_wa['Denda']}\n"
            f"• Total tagihan: *{r_wa['Total Tagih']}*\n\n"
            f"Mohon segera melakukan pembayaran untuk menghindari denda bertambah. Terima kasih 🙏"
        )
        st.text_area("Preview Pesan WA", pesan_wa, height=180)
        telepon = str(r_wa['Telepon']).strip().replace("-", "").replace(" ", "").replace("+", "")
        if telepon:
            wa_link = f"https://wa.me/{telepon}?text={quote(pesan_wa)}"
            st.markdown(f'<a href="{wa_link}" target="_blank" class="stButton"><button style="background: linear-gradient(135deg,#25D366,#128C7E); color:white; border:none; padding:12px 20px; border-radius:10px; font-weight:600; width:100%; cursor:pointer; font-size:14px;">💬 Buka WhatsApp</button></a>', unsafe_allow_html=True)
        else:
            st.warning("Nomor telepon customer tidak tersedia.")

# ==================== 12. ALERT & REMINDER ====================
elif pilihan == "🔔 Alert & Reminder":
    st.markdown('<div class="main-header"><h1>🔔 Alert & Reminder</h1><p>Notifikasi jatuh tempo & konfirmasi pembayaran</p></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["⏰ Jatuh Tempo Mendatang", "💬 Template Pesan"])

    with tab1:
        col_hari = st.number_input("Tampilkan jatuh tempo dalam (hari)", min_value=1, max_value=90, value=7, step=1)
        tgl_batas = (datetime.now() + timedelta(days=int(col_hari))).strftime("%Y-%m-%d")
        tgl_skrg = datetime.now().strftime("%Y-%m-%d")

        df_dekat = read_sql("""
            SELECT k.id, c.nama as customer, c.telepon, p.nama as produk,
                   k.cicilan_bulan, k.sisa_hutang, k.jatuh_tempo
            FROM kredit k
            JOIN customer c ON k.customer_id = c.id
            JOIN produk p ON k.produk_id = p.id
            WHERE k.status='Berjalan' AND k.jatuh_tempo BETWEEN ? AND ?
            ORDER BY k.jatuh_tempo ASC
        """, (tgl_skrg, tgl_batas))

        if df_dekat.empty:
            st.success(f"✅ Tidak ada jatuh tempo dalam {col_hari} hari ke depan.")
        else:
            df_show = df_dekat.copy()
            df_show['cicilan_bulan'] = df_show['cicilan_bulan'].apply(format_rp)
            df_show['sisa_hutang'] = df_show['sisa_hutang'].apply(format_rp)
            st.dataframe(df_show[['id', 'customer', 'telepon', 'produk', 'cicilan_bulan', 'sisa_hutang', 'jatuh_tempo']],
                         use_container_width=True, hide_index=True)

            st.markdown('<div class="section-header"><h3>📲 Kirim Reminder</h3></div>', unsafe_allow_html=True)
            opsi = {f"#{r['id']} - {r['customer']}": r for _, r in df_dekat.iterrows()}
            pilih = st.selectbox("Pilih Akun", list(opsi.keys()), key="sel_reminder")
            r = opsi[pilih]
            pesan = (
                f"Halo Bapak/Ibu *{r['customer']}*,\n\n"
                f"Reminder dari *GRACE'S ELECTRONIC*:\n"
                f"Angsuran Anda untuk *{r['produk']}* akan jatuh tempo pada *{str(r['jatuh_tempo'])[:10]}*.\n"
                f"Nominal cicilan: *{format_rp(r['cicilan_bulan'])}*\n"
                f"Sisa hutang: {format_rp(r['sisa_hutang'])}\n\n"
                f"Mohon siapkan pembayaran. Terima kasih 🙏"
            )
            st.text_area("Preview Pesan", pesan, height=180, key="preview_reminder")
            telp = str(r['telepon']).strip().replace("-", "").replace(" ", "").replace("+", "")
            if telp:
                wa_link = f"https://wa.me/{telp}?text={quote(pesan)}"
                st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background: linear-gradient(135deg,#25D366,#128C7E); color:white; border:none; padding:12px 20px; border-radius:10px; font-weight:600; width:100%; cursor:pointer; font-size:14px;">💬 Kirim via WhatsApp</button></a>', unsafe_allow_html=True)

    with tab2:
        st.markdown("**Template Pesan Cepat:**")
        templates = {
            "Reminder Jatuh Tempo": "Halo Kak {nama}, cicilan Anda sebesar {cicilan} akan jatuh tempo {tanggal}. Mohon persiapkan ya 🙏",
            "Konfirmasi Pembayaran": "Terima kasih Kak {nama}, pembayaran sebesar {nominal} telah kami terima. Sisa hutang: {sisa}.",
            "Kredit Lunas": "Selamat Kak {nama}! Kredit Anda untuk {produk} telah LUNAS. Terima kasih telah berbelanja di GRACE'S ELECTRONIC 🙏",
            "Overdue Keras": "Peringatan: Angsuran Anda untuk {produk} telah terlambat {hari} hari. Mohon segera bayar untuk menghindari denda & pelaporan SLIK OJK.",
        }
        for title, tpl in templates.items():
            with st.expander(f"📝 {title}"):
                st.code(tpl, language=None)

# ==================== 13. LAPORAN & ANALITIK ====================
elif pilihan == "📊 Laporan & Analitik":
    st.markdown('<div class="main-header"><h1>📊 Laporan & Analitik</h1><p>Analisa lengkap performa toko</p></div>', unsafe_allow_html=True)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tgl_mulai = st.date_input("Dari Tanggal", value=(datetime.now() - timedelta(days=30)).date())
    with col_f2:
        tgl_selesai = st.date_input("Sampai Tanggal", value=datetime.now().date())

    tgl_m = tgl_mulai.strftime("%Y-%m-%d")
    tgl_s = tgl_selesai.strftime("%Y-%m-%d") + " 23:59:59"

    tab1, tab2, tab3, tab4 = st.tabs(["💰 Penjualan", "💳 Kredit", "📈 Laba", "📋 Rekap Per Produk"])

    with tab1:
        df_cash = read_sql("""
            SELECT t.tanggal, p.nama as produk, t.jumlah, t.harga_jual_satuan, t.total_harga, t.laba
            FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
            WHERE t.tanggal BETWEEN ? AND ?
            ORDER BY t.tanggal DESC
        """, (tgl_m, tgl_s))

        if df_cash.empty:
            st.info("Tidak ada transaksi cash pada periode ini.")
        else:
            tot_qty = df_cash['jumlah'].sum()
            tot_omzet = df_cash['total_harga'].sum()
            tot_laba = df_cash['laba'].sum()

            html = '<div class="metric-grid">'
            html += metric_card("💵 Total Transaksi", f"{len(df_cash)} trx", "card-blue")
            html += metric_card("🎒 Total Unit", f"{int(tot_qty)} unit", "card-purple")
            html += metric_card("💰 Total Omzet", format_rp(tot_omzet), "card-green")
            html += metric_card("📈 Total Laba", format_rp(tot_laba), "card-orange")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

            df_view = df_cash.copy()
            for col in ['harga_jual_satuan', 'total_harga', 'laba']:
                df_view[col] = df_view[col].apply(format_rp)
            st.dataframe(df_view, use_container_width=True, hide_index=True)

            csv = df_cash.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", csv, f"penjualan_{tgl_m}_{tgl_s}.csv", "text/csv")

    with tab2:
        df_kr = read_sql("""
            SELECT k.tanggal_kredit, c.nama as customer, p.nama as produk,
                   k.harga_cash, k.dp, k.total_hutang, k.tenor, k.cicilan_bulan, k.status
            FROM kredit k
            JOIN customer c ON k.customer_id = c.id
            JOIN produk p ON k.produk_id = p.id
            WHERE k.tanggal_kredit BETWEEN ? AND ?
            ORDER BY k.tanggal_kredit DESC
        """, (tgl_m, tgl_s))

        if df_kr.empty:
            st.info("Tidak ada kredit baru pada periode ini.")
        else:
            tot_dp = df_kr['dp'].sum()
            tot_hutang = df_kr['total_hutang'].sum()
            html = '<div class="metric-grid">'
            html += metric_card("📝 Total Kredit", f"{len(df_kr)} akun", "card-blue")
            html += metric_card("💵 Total DP", format_rp(tot_dp), "card-green")
            html += metric_card("📋 Total Piutang", format_rp(tot_hutang), "card-orange")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

            df_view = df_kr.copy()
            for col in ['harga_cash', 'dp', 'total_hutang', 'cicilan_bulan']:
                df_view[col] = df_view[col].apply(format_rp)
            st.dataframe(df_view, use_container_width=True, hide_index=True)

    with tab3:
        df_bayar = read_sql("""
            SELECT tanggal, SUM(jumlah_bayar) as total_bayar, SUM(denda) as total_denda
            FROM pembayaran
            WHERE tanggal BETWEEN ? AND ?
            GROUP BY tanggal ORDER BY tanggal
        """, (tgl_m, tgl_s[:10]))

        if df_bayar.empty:
            st.info("Tidak ada pembayaran cicilan pada periode ini.")
        else:
            chart = alt.Chart(df_bayar).mark_bar().encode(
                x=alt.X('tanggal:N', title='Tanggal'),
                y=alt.Y('total_bayar:Q', title='Total Bayar (Rp)'),
                color=alt.value('#43e97b')
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(df_bayar, use_container_width=True, hide_index=True)

    with tab4:
        df_rekap = read_sql("""
            SELECT produk, SUM(jumlah) as total_qty, SUM(total_harga) as total_omzet, SUM(laba) as total_laba
            FROM (
                SELECT p.nama as produk, t.jumlah as jumlah, t.total_harga as total_harga, t.laba as laba
                FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
                WHERE t.tanggal BETWEEN ? AND ?
            ) x
            GROUP BY produk ORDER BY total_omzet DESC
        """, (tgl_m, tgl_s))

        if df_rekap.empty:
            st.info("Belum ada penjualan pada periode ini.")
        else:
            df_view = df_rekap.copy()
            for col in ['total_omzet', 'total_laba']:
                df_view[col] = df_view[col].apply(format_rp)
            st.dataframe(df_view, use_container_width=True, hide_index=True)

            csv = df_rekap.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Rekap CSV", csv, f"rekap_{tgl_m}_{tgl_s}.csv", "text/csv", key="dl_rekap")

# ==================== 14. MODAL VS PROFIT ====================
elif pilihan == "👕 Modal vs Profit":
    st.markdown('<div class="main-header"><h1>👕 Modal vs Profit</h1><p>Analisa profit per kategori & per produk</p></div>', unsafe_allow_html=True)

    df_kategori = read_sql("""
        SELECT p.kategori,
               COUNT(DISTINCT p.id) as jumlah_produk,
               COALESCE(SUM(p.stok), 0) as total_stok,
               COALESCE(SUM(p.harga_modal * p.stok), 0) as modal_tertanam
        FROM produk p
        GROUP BY p.kategori ORDER BY modal_tertanam DESC
    """)

    if df_kategori.empty:
        st.info("Belum ada produk.")
    else:
        df_view = df_kategori.copy()
        df_view['modal_tertanam'] = df_view['modal_tertanam'].apply(format_rp)
        st.markdown('<div class="section-header"><h3>📊 Modal Tertanam per Kategori</h3></div>', unsafe_allow_html=True)
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        chart = alt.Chart(df_kategori).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("modal_tertanam:Q"),
            color=alt.Color("kategori:N", scale=alt.Scale(scheme='tableau10')),
            tooltip=["kategori", alt.Tooltip("modal_tertanam:Q", format=",.0f")]
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

    st.markdown('<div class="section-header"><h3>💰 Profit per Produk (Kredit + Cash)</h3></div>', unsafe_allow_html=True)
    df_profit = read_sql("""
        SELECT p.nama as produk, p.kategori,
               COALESCE(SUM(CASE WHEN x.sumber='cash' THEN x.laba ELSE 0 END), 0) as laba_cash,
               COALESCE(SUM(CASE WHEN x.sumber='kredit' THEN x.laba ELSE 0 END), 0) as laba_kredit,
               COALESCE(SUM(x.laba), 0) as total_laba
        FROM produk p
        LEFT JOIN (
            SELECT t.produk_id, 'cash' as sumber, t.laba as laba FROM transaksi_cash t
            UNION ALL
            SELECT k.produk_id, 'kredit' as sumber,
                   (k.dp + k.total_hutang) - (SELECT harga_modal FROM produk WHERE id=k.produk_id) as laba
            FROM kredit k
        ) x ON p.id = x.produk_id
        GROUP BY p.id, p.nama, p.kategori
        HAVING COALESCE(SUM(x.laba), 0) > 0
        ORDER BY total_laba DESC
        LIMIT 20
    """)

    if df_profit.empty:
        st.info("Belum ada penjualan.")
    else:
        df_v = df_profit.copy()
        for col in ['laba_cash', 'laba_kredit', 'total_laba']:
            df_v[col] = df_v[col].apply(format_rp)
        st.dataframe(df_v, use_container_width=True, hide_index=True)

        chart = alt.Chart(df_profit).mark_bar().encode(
            y=alt.Y("produk:N", sort='-x', title="Produk"),
            x=alt.X("total_laba:Q", title="Total Laba (Rp)"),
            color=alt.Color("kategori:N", scale=alt.Scale(scheme='tableau10'))
        ).properties(height=max(300, len(df_profit) * 25))
        st.altair_chart(chart, use_container_width=True)

# ==================== 15. BACKUP, CETAK & IMPOR ====================
elif pilihan == "💾 Backup, Cetak & Impor":
    st.markdown('<div class="main-header"><h1>💾 Backup, Cetak & Impor</h1><p>Cadangkan data & impor massal</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📥 Backup (JSON/CSV)", "📤 Impor Produk (CSV)", "🖨️ Cetak Laporan"])

    with tab1:
        st.markdown("**Backup JSON (semua tabel):**")
        if st.button("🔄 Generate Backup JSON"):
            try:
                tables = ["produk", "transaksi_in", "transaksi_cash", "customer", "kredit",
                          "pembayaran", "users", "log_aktivitas", "pengaturan", "serah_terima"]
                backup = {}
                for t in tables:
                    df = read_sql(f"SELECT * FROM {t}")
                    backup[t] = df.to_dict(orient="records")
                json_bytes = pd.io.json.dumps(backup, indent=2, default_handler=str).encode("utf-8")
                st.download_button("⬇️ Download JSON Backup", json_bytes,
                                   f"backup_grace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                   "application/json")
                st.success("✅ Backup berhasil dibuat! Klik tombol download.")
            except Exception as e:
                st.error(f"❌ Gagal backup: {e}")

        st.markdown("---")
        st.markdown("**Export CSV per tabel:**")
        tabel_pilihan = st.selectbox("Pilih tabel", ["produk", "transaksi_cash", "kredit", "pembayaran", "customer"])
        if st.button("📄 Generate CSV"):
            try:
                df = read_sql(f"SELECT * FROM {tabel_pilihan}")
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(f"⬇️ Download {tabel_pilihan}.csv", csv,
                                   f"{tabel_pilihan}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
                st.success(f"✅ {len(df)} baris siap diunduh.")
            except Exception as e:
                st.error(f"❌ Gagal: {e}")

    with tab2:
        st.markdown("**Format CSV yang diharapkan:** `nama,kategori,harga_modal,stok,markup_persen,harga_jual`")
        uploaded = st.file_uploader("Upload CSV Produk", type=["csv"])
        if uploaded:
            try:
                df_imp = pd.read_csv(uploaded)
                st.dataframe(df_imp.head(), use_container_width=True)
                if st.button("✅ Impor Sekarang"):
                    cols_wajib = ["nama", "kategori", "harga_modal", "stok"]
                    missing = [c for c in cols_wajib if c not in df_imp.columns]
                    if missing:
                        st.error(f"❌ Kolom wajib hilang: {missing}")
                    else:
                        count = 0
                        for _, r in df_imp.iterrows():
                            try:
                                c.execute("""INSERT INTO produk (nama, kategori, harga_modal, stok, markup_persen, harga_jual)
                                             VALUES (?,?,?,?,?,?)""",
                                          (str(r['nama']), str(r['kategori']), float(r['harga_modal']), int(r['stok']),
                                           float(r.get('markup_persen', 5.0)) if pd.notna(r.get('markup_persen')) else 5.0,
                                           float(r['harga_jual']) if 'harga_jual' in r and pd.notna(r.get('harga_jual')) else None))
                                count += 1
                            except Exception:
                                conn.rollback()
                        conn.commit()
                        st.success(f"✅ {count} produk berhasil diimpor!")
                        log_aksi(st.session_state.username, "IMPOR_PRODUK", f"{count} baris")
            except Exception as e:
                st.error(f"❌ Gagal baca CSV: {e}")

    with tab3:
        st.markdown("**Cetak Laporan Penjualan (HTML siap print):**")
        tgl_1 = st.date_input("Dari", value=(datetime.now() - timedelta(days=30)).date(), key="cetak1")
        tgl_2 = st.date_input("Sampai", value=datetime.now().date(), key="cetak2")

        if st.button("🖨️ Generate Laporan"):
            df_lap = read_sql("""
                SELECT t.tanggal, p.nama as produk, t.jumlah, t.total_harga, t.laba
                FROM transaksi_cash t JOIN produk p ON t.produk_id = p.id
                WHERE t.tanggal BETWEEN ? AND ?
                ORDER BY t.tanggal
            """, (tgl_1.strftime("%Y-%m-%d"), tgl_2.strftime("%Y-%m-%d") + " 23:59:59"))

            rows_html = "".join([
                f"<tr><td>{r['tanggal']}</td><td>{r['produk']}</td><td class='r'>{r['jumlah']}</td>"
                f"<td class='r'>{format_rp(r['total_harga'])}</td><td class='r'>{format_rp(r['laba'])}</td></tr>"
                for _, r in df_lap.iterrows()
            ]) if not df_lap.empty else "<tr><td colspan='5' style='text-align:center;'>Tidak ada data</td></tr>"

            html_lap = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <title>Laporan Penjualan</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ text-align: center; color: #1e3a8a; }}
                p.sub {{ text-align: center; color: #666; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
                th {{ background: #1e3a8a; color: white; padding: 8px; text-align: left; }}
                td {{ padding: 6px 8px; border-bottom: 1px solid #e5e7eb; }}
                .r {{ text-align: right; }}
                .total {{ font-weight: bold; background: #eff6ff; }}
                .btn {{ text-align: center; margin: 20px 0; }}
                button {{ padding: 10px 24px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }}
                @media print {{ .btn {{ display: none; }} }}
            </style></head><body>
            <h1>LAPORAN PENJUALAN</h1>
            <p class="sub">Periode: {tgl_1.strftime('%d-%m-%Y')} s/d {tgl_2.strftime('%d-%m-%Y')}</p>
            <table>
                <thead><tr><th>Tanggal</th><th>Produk</th><th class="r">Qty</th><th class="r">Total</th><th class="r">Laba</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <div class="btn"><button onclick="window.print()">🖨️ Cetak Laporan</button></div>
            </body></html>
            """
            components.html(html_lap, height=700, scrolling=True)

# ==================== 16. MANAJEMEN USER (ADMIN) ====================
elif pilihan == "👤 Manajemen User" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>👤 Manajemen User</h1><p>Kelola akun & hak akses</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Tambah User", "📋 Daftar User", "✏️ Edit / Hapus"])

    with tab1:
        with st.form("form_user_baru"):
            col1, col2 = st.columns(2)
            with col1:
                u = st.text_input("Username")
                nl = st.text_input("Nama Lengkap")
            with col2:
                p = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["admin", "kasir"])
            if st.form_submit_button("💾 Simpan User"):
                if not u or not p or not nl:
                    st.warning("Semua field wajib diisi.")
                else:
                    try:
                        c.execute("INSERT INTO users (username, password, nama_lengkap, role, aktif) VALUES (?,?,?,?,1)",
                                  (u, hash_password(p), nl, role))
                        conn.commit()
                        log_aksi(st.session_state.username, "TAMBAH_USER", u)
                        flash(f"✅ User {u} berhasil ditambahkan!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Gagal: {e} (mungkin username sudah dipakai)")

    with tab2:
        df_users = read_sql("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY id")
        if df_users.empty:
            st.info("Belum ada user.")
        else:
            df_view = df_users.copy()
            df_view['aktif'] = df_view['aktif'].apply(lambda v: "✅ Aktif" if int(v or 0) == 1 else "❌ Nonaktif")
            st.dataframe(df_view[['username', 'nama_lengkap', 'role', 'aktif']], use_container_width=True, hide_index=True)

    with tab3:
        df_users = read_sql("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY id")
        if df_users.empty:
            st.info("Belum ada user.")
        else:
            opsi = {f"{r['username']} ({r['nama_lengkap']})": r['id'] for _, r in df_users.iterrows()}
            pilih = st.selectbox("Pilih User", list(opsi.keys()))
            uid = opsi[pilih]
            detail = df_users[df_users['id'] == uid].iloc[0]

            with st.form("form_edit_user"):
                new_nama_l = st.text_input("Nama Lengkap", value=detail['nama_lengkap'] or "")
                new_role = st.selectbox("Role", ["admin", "kasir"],
                                        index=0 if detail['role'] == "admin" else 1)
                new_pwd = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
                new_aktif = st.checkbox("Aktif", value=int(detail['aktif'] or 0) == 1)

                colA, colB = st.columns(2)
                with colA:
                    if st.form_submit_button("💾 Update"):
                        try:
                            if new_pwd:
                                c.execute("UPDATE users SET nama_lengkap=?, role=?, password=?, aktif=? WHERE id=?",
                                          (new_nama_l, new_role, hash_password(new_pwd), 1 if new_aktif else 0, uid))
                            else:
                                c.execute("UPDATE users SET nama_lengkap=?, role=?, aktif=? WHERE id=?",
                                          (new_nama_l, new_role, 1 if new_aktif else 0, uid))
                            conn.commit()
                            log_aksi(st.session_state.username, "EDIT_USER", detail['username'])
                            flash("✅ User diupdate!", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal: {e}")
                with colB:
                    if st.form_submit_button("🗑️ Hapus"):
                        if detail['username'] == "admin":
                            st.error("❌ User admin utama tidak boleh dihapus.")
                        elif detail['username'] == st.session_state.username:
                            st.error("❌ Tidak bisa menghapus akun sendiri yang sedang login.")
                        else:
                            try:
                                c.execute("DELETE FROM users WHERE id=?", (uid,))
                                conn.commit()
                                log_aksi(st.session_state.username, "HAPUS_USER", detail['username'])
                                flash("🗑️ User dihapus!", "success")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"❌ Gagal: {e}")

# ==================== 17. LOG AKTIVITAS (ADMIN) ====================
elif pilihan == "📝 Log Aktivitas" and st.session_state.role == "admin":
    st.markdown('<div class="main-header"><h1>📝 Log Aktivitas</h1><p>Audit trail semua aksi user</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Tampilkan N terakhir", min_value=10, max_value=500, value=100, step=10)
    with col2:
        cari = st.text_input("🔍 Filter (username / aksi / detail)")

    if cari:
        df_log = read_sql("""
            SELECT waktu, username, aksi, detail FROM log_aktivitas
            WHERE username ILIKE ? OR aksi ILIKE ? OR detail ILIKE ?
            ORDER BY id DESC LIMIT ?
        """, (f"%{cari}%", f"%{cari}%", f"%{cari}%", int(limit)))
    else:
        df_log = read_sql("SELECT waktu, username, aksi, detail FROM log_aktivitas ORDER BY id DESC LIMIT ?", (int(limit),))

    if df_log.empty:
        st.info("Belum ada log.")
    else:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        csv = df_log.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Log CSV", csv,
                           f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

# ==================== FALLBACK (jika role non-admin pilih menu admin) ====================
elif pilihan in ["⚙️ Pengaturan Owner", "👤 Manajemen User", "📝 Log Aktivitas"]:
    st.error("🚫 Menu ini hanya untuk admin. Silakan login sebagai admin.")
    st.info(f"Anda login sebagai **{st.session_state.nama}** (role: **{st.session_state.role}**).")
