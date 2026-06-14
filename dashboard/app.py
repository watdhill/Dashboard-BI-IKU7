import os
import sys
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import time

# 1. Konfigurasi Utama Layar Web Dasbor
st.set_page_config(
    page_title="Monitoring IKU 7 - UNAND",
    page_icon="📊",
    layout="wide"
)


def inject_css():
    css = """
    <style>
    /* Layout container */
    .block-container{max-width:1400px; padding:1.5rem 2.5rem}
    h1 {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size:34px; margin-bottom:6px}
    h2 {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#e6eef7}

    /* Buttons and download */
    .stButton>button {background-color: #036; color: white}
    .download-button button {background-color:#006d77}

    /* Sidebar container tweak */
    .stSidebar .sidebar-content {padding: 1rem 0.75rem}
    .sidebar {background:#243447}

    /* Sidebar nav styles (custom) */
    .sidebar-nav {padding:8px 6px; margin:8px 0}
    .sidebar-nav a {display:flex; align-items:center; gap:10px; padding:12px 14px; color:#dbe7ef; text-decoration:none; border-radius:8px; margin-bottom:6px}
    .sidebar-nav a .icon {display:inline-flex; width:30px; height:30px; align-items:center; justify-content:center; font-size:18px}
    .sidebar-nav a:hover {background:#16364f; color:#fff}
    .sidebar-nav a.active {background: linear-gradient(90deg,#0b84ff,#0366d6); color:white; font-weight:600; box-shadow: 0 4px 14px rgba(3,102,214,0.12)}

    /* Enhanced Sidebar visual theme (radio-driven navigation compatible) */
    .stSidebar {
        background: linear-gradient(180deg,#0f1724,#111827);
        color: #dbe7ef;
        padding-top: 8px;
    }
    .stSidebar .sidebar-content {padding: 1.25rem 0.75rem;}
    .stSidebar .stRadio > div {display:flex; flex-direction:column; gap:6px}
    .stSidebar .stRadio label {
        display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:10px;
        color:#dbe7ef; font-weight:600; cursor:pointer; transition: all .12s ease-in-out; margin:4px 6px;
    }
    .stSidebar .stRadio label:hover {background:#162a3a; transform: translateY(-1px)}
    .stSidebar .stRadio input[type="radio"] {accent-color:#0b84ff; width:18px; height:18px}
    /* Attempt to style the checked/active option (Streamlit may expose aria-checked)
       Fallback: maintain high-contrast on hover and rely on accent-color for selection */
    .stSidebar .stRadio label[aria-checked="true"] {background: linear-gradient(90deg,#0b84ff,#0366d6); color:#fff}

    /* Make the sidebar icons spacing consistent */
    .sidebar .icon {width:34px; height:34px; display:inline-flex; align-items:center; justify-content:center; font-size:18px}

    /* Improve headings/filters spacing */
    .block-container h2 {margin-top: 0.6rem}
    .stMarkdown h3 {margin-top:0.6rem}

    /* Make tables and charts breathe */
    .stDataFrame, .stPlotlyChart {margin-top: 1rem}

    @media (max-width: 900px) {
        .block-container{padding:1rem}
        .sidebar-nav a {padding:10px}
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


inject_css()


def safe_rerun():
    """Attempt to trigger a Streamlit rerun using multiple strategies.
    Some Streamlit versions expose different APIs; try them in order and
    fallback to nudging query params or session_state so the app refreshes.
    """
    try:
        if hasattr(st, 'experimental_rerun'):
            try:
                st.experimental_rerun()
                return
            except Exception:
                pass
        if hasattr(st, 'rerun'):
            try:
                st.rerun()
                return
            except Exception:
                pass
        # Fallback: toggle a query param to force a rerun
        try:
            params = st.experimental_get_query_params()
            params['_refresh'] = [str(int(time.time()))]
            st.experimental_set_query_params(**params)
            return
        except Exception:
            pass
        # Final fallback: set a session flag (will change app state and usually rerun)
        try:
            st.session_state['_refresh'] = int(time.time())
        except Exception:
            pass
    except Exception:
        pass

# 2. Fungsi Mengambil Data Menggunakan JOIN Relasional Star Schema MySQL
def get_data_from_mysql(host="localhost", database="db_monitoring_iku7", user="root", password=""):
    conn = mysql.connector.connect(
        host=host,
        database=database,  # Sinkron dengan nama database penampungan baru kalian
        user=user,
        password=password  # !!! SAMAKAN PASSWORD MYSQL DENGAN FILE ETL !!!
    )

    # Kueri mengambil relasi data antar dimensi melalui jembatan tabel fakta
    query = """
        SELECT 
            p.nama_prodi AS prodi,
            p.fakultas AS fakultas,
            m.id_mk AS id_mk,
            m.kode_mk AS kode_mk,
            m.nama_mk AS `nama mata kuliah`,
            CONCAT(s.nama_semester, ' ', s.tahun_akademik) AS `semester mk`,
            f.sks AS sks,
            mt.nama_metode AS metode
        FROM fact_iku7 f
        JOIN dim_prodi p ON f.id_prodi = p.id_prodi
        JOIN dim_mata_kuliah m ON f.id_mk = m.id_mk
        JOIN dim_semester s ON f.id_semester = s.id_semester
        JOIN dim_metode mt ON f.id_metode = mt.id_metode;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def show_dashboard(df, etl_status):
    # --- TAMPILAN JENDELA DASBOR ---
    st.title("📊 Dasbor Monitoring Capaian IKU 7 Universitas Andalas")
    # If no processed data, show a prominent note and stop
    if not etl_status.get('processed_file_exists'):
        st.warning("Tidak ada data terproses: jalankan ETL atau unggah file terlebih dahulu. Visualisasi dan tabel tidak tersedia sampai data diproses.")
        return
    # debug block will be injected under the main title for visibility
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass

    st.markdown("Evaluasi Real-Time Kurikulum Terintegrasi Berbasis Sistem Pangkalan Data *Star Schema* MySQL")
    st.markdown("---")

    # --- PANEL FILTER DI ATAS HALAMAN ---
    st.markdown('### Filters')
    col_fak, col_prodi = st.columns([1, 3])

    # Filter Fakultas (atas)
    all_fakultas = ["Semua Fakultas"] + list(df['fakultas'].unique())
    selected_fakultas = col_fak.selectbox("Pilih Fakultas:", all_fakultas)

    # Kondisi filter dinamis berjenjang
    if selected_fakultas != "Semua Fakultas":
        df_filtered_fak = df[df['fakultas'] == selected_fakultas]
        all_prodis = sorted(df_filtered_fak['prodi'].unique())
        pilihan_list = ["-- Semua Program Studi --"] + all_prodis
        pilihan = col_prodi.selectbox('Pilih Program Studi:', pilihan_list, index=0, disabled=False)
        if pilihan == "-- Semua Program Studi --":
            selected_prodi = all_prodis
        else:
            selected_prodi = [pilihan]
    else:
        df_filtered_fak = df
        all_prodis = sorted(df['prodi'].unique())
        pilihan_list = ["-- Semua Program Studi --"] + all_prodis
        # tetap tampil tapi dinonaktifkan saat Semua Fakultas
        pilihan = col_prodi.selectbox('Pilih Program Studi:', pilihan_list, index=0, disabled=True)
        selected_prodi = all_prodis

    # Mengaplikasikan filter akhir ke dataset kerja
    df_filtered = df_filtered_fak[df_filtered_fak['prodi'].isin(selected_prodi)]

    # --- KOMPUTASI FORMULA METRIK (DAX LOGIC DI STREAMLIT) ---
    total_mk = len(df_filtered)
    mk_iku7 = len(df_filtered[df_filtered['metode'].isin(['PjBL', 'CBM'])])
    persen_iku7 = (mk_iku7 / total_mk * 100) if total_mk > 0 else 0

    # --- LAYOUT KARTU INFORMASI KPI ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Mata Kuliah Terdaftar", value=f"{total_mk} MK")
    with col2:
        st.metric(label="Mata Kuliah IKU 7 (PjBL + CBM)", value=f"{mk_iku7} MK")
    with col3:
        st.metric(label="Persentase Capaian Target IKU 7", value=f"{persen_iku7:.2f}%", delta=f"{persen_iku7 - 15.93:.2f}% vs Baseline Unand")

    st.markdown("---")

    # --- LAYOUT GRAFIK VISUALISASI ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📌 Distribusi Metode Pembelajaran")
        fig_donut = px.pie(
            df_filtered,
            names='metode',
            hole=0.4,
            color='metode',
            color_discrete_map={'Biasa': '#EF553B', 'PjBL': '#636EFA', 'CBM': '#00CC96'}
        )
        st.plotly_chart(fig_donut, width='stretch')

    with col_right:
        st.subheader("🏆 Peringkat Capaian IKU 7 per Program Studi")
        # Compute per-prodi percentages without using GroupBy.apply on grouping columns
        total = df_filtered.groupby('prodi').size().rename('total')
        iku7_counts = df_filtered[df_filtered['metode'].isin(['PjBL', 'CBM'])].groupby('prodi').size().rename('iku7')
        prodi_stats = pd.concat([total, iku7_counts], axis=1).fillna(0)
        prodi_stats['percent'] = (prodi_stats['iku7'] / prodi_stats['total'] * 100).fillna(0)
        prodi_stats = prodi_stats.reset_index()[['prodi', 'percent']].sort_values(by='percent', ascending=True)

        fig_bar = px.bar(
            prodi_stats,
            x='percent',
            y='prodi',
            orientation='h',
            labels={'percent': 'Capaian (%)', 'prodi': 'Program Studi'},
            color='percent',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, width='stretch')

    st.markdown("---")

    st.subheader("📋 Daftar Prioritas Konversi Mata Kuliah Konvensional")
    st.markdown("Tabel interaktif di bawah ini menyaring daftar kelas berstatus **Biasa** sebagai acuan taktis Ketua Prodi untuk dikonversi menjadi metode pengajaran aktif di semester depan.")

    df_biasa = df_filtered[df_filtered['metode'] == 'Biasa'][['prodi', 'kode_mk', 'nama mata kuliah', 'sks', 'metode']]
    st.dataframe(df_biasa, width='stretch')

    # ══════════════════════════════════════════════════════════════
    # INSIGHT & REKOMENDASI STRATEGIS BERBASIS STAKEHOLDER
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("""<h2 style='text-align:center;margin-bottom:4px'>💡 Analisis Insight & Rekomendasi Strategis</h2>
    <p style='text-align:center;color:#94a3b8;font-size:15px;margin-top:0'>Berbasis Stakeholder — Semester Ganjil 2024/2025</p>""", unsafe_allow_html=True)
    st.markdown("""<p style='text-align:center;color:#cbd5e1;font-size:14px;max-width:900px;margin:0 auto 24px auto'>
    Temuan analitik dari dasbor IKU 7 telah diekstraksi dan dipetakan menjadi rekomendasi <em>actionable</em>
    bagi tiga tingkatan pemangku kebijakan.</p>""", unsafe_allow_html=True)

    # --- Compute dynamic values for insight text ---
    _total_all = len(df)
    _mk_iku7_all = len(df[df['metode'].isin(['PjBL', 'CBM'])])
    _persen_all = (_mk_iku7_all / _total_all * 100) if _total_all > 0 else 0
    _mk_biasa_all = len(df[df['metode'] == 'Biasa'])

    _total_prodi = df.groupby('prodi').size().rename('total')
    _iku7_prodi = df[df['metode'].isin(['PjBL', 'CBM'])].groupby('prodi').size().rename('iku7')
    _ps = pd.concat([_total_prodi, _iku7_prodi], axis=1).fillna(0)
    _ps['percent'] = (_ps['iku7'] / _ps['total'] * 100).fillna(0)
    _ps = _ps.reset_index()

    _prodi_100_list = _ps[_ps['percent'] == 100]['prodi'].tolist()
    _prodi_0_count = len(_ps[_ps['percent'] == 0])
    _prodi_100_names = ', '.join(_prodi_100_list[:5]) + ('...' if len(_prodi_100_list) > 5 else '') if _prodi_100_list else '-'

    # Top 5 prodi with most 'Biasa' MK
    _biasa_all = df[df['metode'] == 'Biasa']
    _biasa_top5 = _biasa_all.groupby('prodi').size().reset_index(name='cnt').sort_values('cnt', ascending=False).head(5)
    _top5_names = ', '.join(_biasa_top5['prodi'].tolist()) if not _biasa_top5.empty else '-'

    # Health prodi at 0%
    _health_keywords = ['Biomedis', 'Kedokteran', 'Farmasi', 'Keperawatan']
    _health_zero = _ps[(_ps['percent'] == 0) & (_ps['prodi'].str.contains('|'.join(_health_keywords), case=False, na=False))]['prodi'].tolist()
    _health_zero_names = ', '.join(_health_zero) if _health_zero else 'tidak terdeteksi'

    # Shared CSS for insight cards
    insight_css = """
    <style>
    .insight-section-title {
        display:flex; align-items:center; gap:12px;
        padding:16px 20px; border-radius:14px;
        margin:28px 0 16px 0;
        font-size:20px; font-weight:700; color:#fff;
    }
    .insight-section-title .title-icon {
        font-size:28px; width:48px; height:48px;
        display:flex; align-items:center; justify-content:center;
        border-radius:12px; background:rgba(255,255,255,0.15);
    }
    .insight-section-title .title-sub {
        font-size:13px; font-weight:400; color:rgba(255,255,255,0.8);
        margin-top:2px;
    }
    .insight-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius:14px; padding:22px 24px;
        margin-bottom:16px;
        border-left:5px solid;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .insight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.35);
    }
    .insight-card .card-label {
        display:inline-block; font-size:10px; font-weight:700;
        letter-spacing:1.5px; text-transform:uppercase;
        padding:4px 10px; border-radius:6px;
        margin-bottom:10px;
    }
    .insight-card .card-label.insight { background:rgba(99,110,250,0.2); color:#818cf8; }
    .insight-card .card-label.rekom { background:rgba(0,204,150,0.2); color:#34d399; }
    .insight-card .card-title {
        font-size:17px; font-weight:700; color:#f1f5f9;
        margin-bottom:10px; line-height:1.35;
    }
    .insight-card .card-body {
        font-size:14px; color:#cbd5e1; line-height:1.7;
    }
    .insight-card .card-body strong { color:#e2e8f0; }
    .insight-card .card-body em { color:#94a3b8; }
    .highlight-num {
        display:inline-block; background:rgba(99,110,250,0.15);
        color:#a5b4fc; font-weight:700; padding:1px 8px;
        border-radius:6px; font-size:15px;
    }
    </style>
    """
    st.markdown(insight_css, unsafe_allow_html=True)

    # ── SECTION 1: Rektorat ──────────────────────────────────────
    st.markdown("""<div class='insight-section-title' style='background:linear-gradient(90deg,#1e3a5f,#0f2440)'>
        <div class='title-icon'>🏛️</div>
        <div><div>Pimpinan Universitas (Rektorat / WR I Bidang Akademik)</div>
        <div class='title-sub'>Pandangan makro-strategis untuk kebijakan institusional dan alokasi resource</div></div>
    </div>""", unsafe_allow_html=True)

    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        st.markdown(f"""
        <div class='insight-card' style='border-color:#636EFA'>
            <div class='card-label insight'>📊 Insight 1</div>
            <div class='card-title'>Kesenjangan Kesiapan Rumpun Keilmuan (Polarisasi Performa)</div>
            <div class='card-body'>
                Data menunjukkan polarisasi yang ekstrem. Baseline capaian universitas berada di angka
                <span class='highlight-num'>{_persen_all:.2f}%</span>. Prodi dari rumpun Vokasional dan Agrokompleks
                (<strong>{_prodi_100_names}</strong>) telah menyentuh angka konversi
                <span class='highlight-num'>100%</span>. Di sisi lain,
                <span class='highlight-num'>{_prodi_0_count} prodi</span> masih berada di angka <strong>0%</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r1_col2:
        st.markdown(f"""
        <div class='insight-card' style='border-color:#00CC96'>
            <div class='card-label rekom'>✅ Rekomendasi 1</div>
            <div class='card-title'>Tetapkan "Center of Excellence" dari Prodi 100%</div>
            <div class='card-body'>
                Universitas tidak perlu memulai pembinaan dari nol. Prodi dengan capaian 100% harus ditetapkan sebagai
                <strong>Pusat Percontohan</strong>. Dokumen <em>Rencana Pembelajaran Semester</em> (RPS) dan rubrik penilaian
                PjBL/CBM dari prodi-prodi ini harus ditarik dan dijadikan <strong>template rujukan resmi</strong>
                bagi fakultas lain yang masih kesulitan melakukan transisi.
            </div>
        </div>
        """, unsafe_allow_html=True)

    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        st.markdown(f"""
        <div class='insight-card' style='border-color:#636EFA'>
            <div class='card-label insight'>📊 Insight 2</div>
            <div class='card-title'>Implementasi Hukum Pareto (Aturan 80/20) untuk Akselerasi</div>
            <div class='card-body'>
                Dari <span class='highlight-num'>{_mk_biasa_all} MK</span> yang belum memenuhi IKU 7
                (status "Biasa"), lebih dari separuhnya berasal hanya dari <strong>5 Program Studi</strong> dengan
                beban kelas terpadat: <strong>{_top5_names}</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r2_col2:
        st.markdown(f"""
        <div class='insight-card' style='border-color:#00CC96'>
            <div class='card-label rekom'>✅ Rekomendasi 2</div>
            <div class='card-title'>Konsentrasi Intervensi pada "5 Prodi Raksasa"</div>
            <div class='card-body'>
                Hindari kebijakan pemaksaan serentak. Strategi intervensi harus dikonsentrasikan secara eksklusif
                pada <strong>5 Prodi</strong> tersebut. Dengan menetapkan target konversi parsial
                (misalnya <strong>30%</strong> dari total kelas), grafik baseline universitas akan melonjak
                secara <strong>efisien dan signifikan</strong> pada semester berikutnya.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── SECTION 2: Dekanat ───────────────────────────────────────
    st.markdown("""<div class='insight-section-title' style='background:linear-gradient(90deg,#1e3a5f,#1a365d)'>
        <div class='title-icon'>🎓</div>
        <div><div>Pimpinan Fakultas (Dekanat / WD I Bidang Akademik)</div>
        <div class='title-sub'>Jembatan kebijakan — pengawasan pelaporan dan penyelesaian kendala struktural tingkat fakultas</div></div>
    </div>""", unsafe_allow_html=True)

    d1_col1, d1_col2 = st.columns(2)
    with d1_col1:
        st.markdown(f"""
        <div class='insight-card' style='border-color:#f59e0b'>
            <div class='card-label insight'>📊 Insight 1</div>
            <div class='card-title'>Potensi "False-Negative" — Kegagalan Pelaporan Administratif (Rumpun Kesehatan)</div>
            <div class='card-body'>
                Dasbor mendeteksi anomali <em>zero-performance</em> (0%) pada prodi:
                <strong>{_health_zero_names}</strong>.
                Secara standar pendidikan medis klinis, metode <em>Problem-Based Learning</em> (PBL) dan bedah kasus
                sejatinya sudah menjadi rutinitas. Angka 0% ini sangat kuat diindikasi sebagai
                <strong>kegagalan pelaporan metadata</strong>, bukan kegagalan pedagogis dosen.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with d1_col2:
        st.markdown("""
        <div class='insight-card' style='border-color:#00CC96'>
            <div class='card-label rekom'>✅ Rekomendasi 1</div>
            <div class='card-title'>Audit & Revisi Tagging SIAKAD untuk Kelas Tutorial Klinis</div>
            <div class='card-body'>
                Dekan di Fakultas Kedokteran, Farmasi, dan Kedokteran Gigi harus segera menerbitkan
                <strong>edaran instruksi teknis</strong> kepada operator SIAKAD tingkat prodi.
                Operator harus melakukan audit dan merevisi tagging (label) pada kelas-kelas tutorial klinis
                menjadi <strong>"CBM"</strong> di dalam sistem. Perbaikan administrasi sederhana ini akan langsung
                mengoreksi warna merah pada dasbor <strong>tanpa merombak cara mengajar</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    d2_col1, d2_col2 = st.columns(2)
    with d2_col1:
        st.markdown("""
        <div class='insight-card' style='border-color:#f59e0b'>
            <div class='card-label insight'>📊 Insight 2</div>
            <div class='card-title'>Transisi Bertahap (Low-Hanging Fruit) untuk Rumpun Sosio-Humaniora</div>
            <div class='card-body'>
                Fakultas seperti Hukum dan ISIP mencatatkan beban kelas "Biasa" yang masif.
                Hal ini menunjukkan resistensi karena dosen ilmu teori/sosial mungkin merasa metode
                "Proyek" (PjBL) <strong>tidak relevan</strong> atau terlalu memberatkan.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with d2_col2:
        st.markdown("""
        <div class='insight-card' style='border-color:#00CC96'>
            <div class='card-label rekom'>✅ Rekomendasi 2</div>
            <div class='card-title'>Fasilitasi Lokakarya CBM sebagai Low-Hanging Fruit</div>
            <div class='card-body'>
                Dekan terkait harus memfasilitasi <strong>Bimtek</strong> yang difokuskan pada transisi menuju
                metode <strong>CBM</strong> (<em>Case-Based Method</em>) terlebih dahulu, bukan PjBL.
                Mendorong dosen Hukum menggunakan <strong>analisis putusan pengadilan riil</strong>, atau dosen
                Psikologi dengan <strong>studi kasus klinis</strong>, jauh lebih mudah dieksekusi daripada
                merancang proyek fisik berskala besar.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── SECTION 3: Kaprodi ───────────────────────────────────────
    st.markdown("""<div class='insight-section-title' style='background:linear-gradient(90deg,#1e3a5f,#0d2137)'>
        <div class='title-icon'>👤</div>
        <div><div>Ketua Program Studi (Kaprodi)</div>
        <div class='title-sub'>Eksekutor langsung — kendali jadwal, ploting dosen, dan validasi RPS</div></div>
    </div>""", unsafe_allow_html=True)

    k_col1, k_col2 = st.columns(2)
    with k_col1:
        st.markdown("""
        <div class='insight-card' style='border-color:#8b5cf6'>
            <div class='card-label insight'>📊 Insight</div>
            <div class='card-title'>Identifikasi Target Mata Kuliah Konversi</div>
            <div class='card-body'>
                Kaprodi seringkali kebingungan menentukan <strong>mata kuliah mana</strong> yang harus diubah
                terlebih dahulu agar memenuhi standar MBKM. Tanpa panduan data, keputusan menjadi subjektif
                dan tidak efisien.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k_col2:
        st.markdown("""
        <div class='insight-card' style='border-color:#00CC96'>
            <div class='card-label rekom'>✅ Rekomendasi</div>
            <div class='card-title'>Gunakan Tabel "Daftar Prioritas" di Atas untuk Seleksi MK</div>
            <div class='card-body'>
                Kaprodi wajib menggunakan fitur tabel interaktif <strong>"Daftar Prioritas Konversi"</strong>
                di atas. Seleksi <strong>2–4 mata kuliah</strong> di semester menengah (Semester 3 atau 5)
                yang paling fleksibel, lalu instruksikan Dosen Pengampu untuk <strong>merevisi RPS</strong>
                dan menugaskan minimal <strong>satu pemecahan kasus nyata</strong> di semester mendatang.
            </div>
        </div>
        """, unsafe_allow_html=True)


def list_data_files():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_dirs = {
        'raw': os.path.join(root, 'data', 'raw'),
        'processed': os.path.join(root, 'data', 'processed')
    }
    files = {}
    for k, p in data_dirs.items():
        try:
            files[k] = os.listdir(p)
        except Exception:
            files[k] = []
    return files


def run_etl_script():
    etl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'etl', 'pipeline', 'clean_data.py'))
    if not os.path.exists(etl_path):
        st.error(f"ETL script tidak ditemukan: {etl_path}")
        return
    with st.spinner('Menjalankan ETL...'):
        try:
            proc = subprocess.run([sys.executable, etl_path], capture_output=True, text=True, timeout=300)
            st.code(proc.stdout[:10000])
            if proc.stderr:
                st.error(proc.stderr[:10000])
        except Exception as e:
            st.error(f"Gagal menjalankan ETL: {e}")


def show_data_browser(df, etl_status):
    st.markdown("<h2>🗂️ Data Browser</h2>", unsafe_allow_html=True)
    # debug block under page heading
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass

    st.markdown('Lihat dataset yang dimuat dan file-data sumber di folder `data`.')
    # --- Upload form (quick ETL trigger - asynchronous background run) ---
    st.markdown('#### Upload file untuk diproses (Excel/CSV)')
    uploaded = st.file_uploader('Unggah file .xlsx atau .csv lalu tekan `Upload & Run ETL` (admin)', type=['xlsx', 'csv'])
    if uploaded is not None:
        col1, col2 = st.columns([3,1])
        with col1:
            st.info(f'File siap diupload: {uploaded.name} ({uploaded.type})')
        with col2:
            if st.button('Upload & Run ETL'):
                root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                raw_dir = os.path.join(root, 'data', 'raw')
                os.makedirs(raw_dir, exist_ok=True)
                safe_name = f"{int(time.time())}_{uploaded.name.replace(' ', '_')}"
                dest_path = os.path.join(raw_dir, safe_name)
                try:
                    data_bytes = uploaded.getbuffer()
                    with open(dest_path, 'wb') as f:
                        f.write(data_bytes)
                    st.success(f'File tersimpan: {safe_name}')

                    # Also create a copy with the expected pipeline filename so staging finds it
                    _, ext = os.path.splitext(uploaded.name)
                    ext = ext.lower() if ext else '.csv'
                    expected_name = f"Data_Matakuliah_Gabungan{ext}"
                    expected_path = os.path.join(raw_dir, expected_name)
                    try:
                        with open(expected_path, 'wb') as ef:
                            ef.write(data_bytes)
                        st.info(f'Copied to expected pipeline filename: {expected_name}')
                    except Exception as e:
                        st.warning(f'Gagal membuat salinan expected file: {e}')

                except Exception as e:
                    st.error(f'Gagal menyimpan file: {e}')
                    return

                # start ETL in background and write logs
                etl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'etl', 'pipeline', 'clean_data.py'))
                logs_dir = os.path.join(root, '.logs')
                os.makedirs(logs_dir, exist_ok=True)
                log_file = os.path.join(logs_dir, f'etl_{int(time.time())}.log')
                try:
                    with open(log_file, 'w') as lf:
                        proc = subprocess.Popen([sys.executable, etl_path], stdout=lf, stderr=subprocess.STDOUT)
                    st.info('ETL started in background. This may take a few moments.')
                    st.write(f'PID: {proc.pid}')
                    st.write(f'Log: {log_file}')
                    # Instead of blocking here, set session state so the next rerun
                    # will start the ETL-polling loop. This lets the UI refresh immediately.
                    st.session_state['etl_log_file'] = log_file
                    st.session_state['etl_started'] = False
                    st.session_state['etl_requested_at'] = int(time.time())
                    # trigger a rerun so sidebar and file lists update immediately
                    try:
                        safe_rerun()
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f'Gagal memulai ETL: {e}')

    # Recalculate file lists now that upload may have occurred
    # If an ETL run was requested and we have a log file recorded in session_state,
    # start a polling loop here (this is after a rerun triggered by the upload handler).
    etl_log = st.session_state.get('etl_log_file')
    if etl_log and not st.session_state.get('etl_started'):
        st.session_state['etl_started'] = True
        processed_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'data', 'processed', 'Data_Matakuliah_Bersih.csv')
        tail_placeholder = st.empty()
        tail_placeholder.markdown(f'Log: {etl_log}')
        start_wait = time.time()
        wait_timeout = 300
        try:
            while time.time() - start_wait < wait_timeout:
                # show recent log content if available
                if os.path.exists(etl_log):
                    try:
                        with open(etl_log, 'r', encoding='utf-8', errors='ignore') as lf:
                            lf.seek(0, 2)
                            size = lf.tell()
                            seek = max(0, size - 8192)
                            lf.seek(seek)
                            lines = lf.read().splitlines()[-20:]
                            tail_placeholder.code('\n'.join(lines))
                    except Exception:
                        tail_placeholder.text('Menunggu log...')

                # check for processed file presence
                if os.path.exists(processed_path):
                    # If processed file exists, check DB has been updated (fact rows > 0)
                    try:
                        host = st.session_state.get('db_host', 'localhost')
                        database = st.session_state.get('db_name', 'db_monitoring_iku7')
                        user = st.session_state.get('db_user', 'root')
                        password = st.session_state.get('db_password', '')
                        try:
                            conn = mysql.connector.connect(host=host, database=database, user=user, password=password)
                            cur = conn.cursor()
                            cur.execute('SELECT COUNT(*) FROM fact_iku7;')
                            cnt = cur.fetchone()[0]
                            cur.close()
                            conn.close()
                        except Exception:
                            cnt = 0

                        if cnt and cnt > 0:
                            tail_placeholder.success('ETL selesai — DB terisi.')
                            # clear session flags and rerun to refresh sidebar/status
                            try:
                                del st.session_state['etl_log_file']
                            except Exception:
                                pass
                            try:
                                del st.session_state['etl_started']
                            except Exception:
                                pass
                            time.sleep(1)
                            safe_rerun()
                        else:
                            tail_placeholder.info('File processed ditemukan, menunggu pemuatan ke DB...')
                    except Exception as e:
                        # non-fatal: show the error message in the placeholder and continue polling
                        tail_placeholder.text(f'Error memeriksa DB: {str(e)} — menunggu...')
                time.sleep(2)
            tail_placeholder.warning('Waktu tunggu ETL habis. Periksa log di folder .logs.')
        except Exception as e:
            tail_placeholder.text(f'Polling log dihentikan karena kesalahan: {e}')

    files = list_data_files()
    st.subheader('File Raw')
    raw_files = files.get('raw', [])
    processed_files = files.get('processed', [])

    def _human_size(n):
        try:
            n = int(n)
        except Exception:
            return '-'
        for unit in ['B','KB','MB','GB']:
            if n < 1024.0:
                return f"{n:3.1f} {unit}"
            n /= 1024.0
        return f"{n:.1f} TB"

    def render_cards(folder_key, file_list):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        folder_map = {'raw': os.path.join(root, 'data', 'raw'), 'processed': os.path.join(root, 'data', 'processed')}
        folder_path = folder_map.get(folder_key, root)
        if not file_list:
            st.info('Tidak ada file di ' + folder_key)
            return
        cols_per_row = 3
        for i in range(0, len(file_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, fname in enumerate(file_list[i:i+cols_per_row]):
                col = cols[j]
                full = os.path.join(folder_path, fname)
                mtime = '-'
                size = '-'
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
                try:
                    size = _human_size(os.path.getsize(full))
                except Exception:
                    pass
                card_html = f"""
                <div style='padding:10px;border-radius:8px;border:1px solid #e6eef7;background:linear-gradient(180deg,#fff,#f7fafc);'>
                  <div style='font-weight:700;color:#0b3b5b'>{fname}</div>
                  <div style='font-size:12px;color:#354250;margin-top:6px'>Modified: {mtime}</div>
                  <div style='font-size:12px;color:#354250'>Size: {size}</div>
                </div>
                """
                col.markdown(card_html, unsafe_allow_html=True)
                # delete button
                del_key = f"del__{folder_key}__{i+j}__{fname}"
                if col.button('Delete', key=del_key):
                    try:
                        if os.path.exists(full):
                            os.remove(full)
                        # if raw folder and expected pipeline filename exists, remove it too
                        if folder_key == 'raw':
                            expected_csv = os.path.join(folder_path, 'Data_Matakuliah_Gabungan.csv')
                            expected_xlsx = os.path.join(folder_path, 'Data_Matakuliah_Gabungan.xlsx')
                            for p in (expected_csv, expected_xlsx):
                                try:
                                    if os.path.exists(p):
                                        os.remove(p)
                                except Exception:
                                    pass
                        st.success(f"Deleted: {fname}")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus {fname}: {e}")

    render_cards('raw', raw_files)

    st.markdown('---')
    st.subheader('File Processed')
    render_cards('processed', processed_files)
    st.markdown('---')
    # Only show the full dataset view if a processed file exists and DB returned rows
    if not etl_status.get('processed_file_exists'):
        st.info('Tidak ada data terproses. Bagian "Data Lengkap" disembunyikan sampai ETL selesai.')
    else:
        if not df.empty:
            st.subheader('Data Lengkap')
            st.dataframe(df.reset_index(drop=True), use_container_width=True)
        else:
            st.warning("Data tidak tersedia. Jalankan ETL atau cek koneksi database.")


def show_dimensions(df, etl_status):
    st.markdown("<h2>📚 Dimensions</h2>", unsafe_allow_html=True)
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass
    if not etl_status.get('processed_file_exists'):
        st.info('Tidak ada data terproses. Tabel dimensi tidak tersedia.')
        return
    if df.empty:
        st.warning('Tidak ada data untuk menampilkan dimensi.')
        return
    st.subheader('Dimensi Program Studi')
    st.dataframe(df[['prodi', 'fakultas']].drop_duplicates().reset_index(drop=True))
    st.subheader('Dimensi Mata Kuliah')
    st.dataframe(df[['id_mk', 'kode_mk', 'nama mata kuliah', 'sks']].drop_duplicates().reset_index(drop=True))
    st.subheader('Dimensi Semester')
    st.dataframe(df[['semester mk']].drop_duplicates().reset_index(drop=True))
    st.subheader('Dimensi Metode')
    st.dataframe(df[['metode']].drop_duplicates().reset_index(drop=True))


def show_reports(df, etl_status):
    st.markdown("<h2>📈 Reports</h2>", unsafe_allow_html=True)
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass

    st.markdown('Ekspor data saat ini menjadi CSV untuk keperluan laporan.')
    if not etl_status.get('processed_file_exists'):
        st.info('Tidak ada data terproses. Laporan tidak tersedia.')
        return
    if df.empty:
        st.warning('Tidak ada data untuk diekspor.')
        return
    csv = df.to_csv(index=False)
    st.download_button('Download CSV', csv, file_name='iku7_export.csv', mime='text/csv')








def show_settings():
    st.markdown("<h2>🔧 Settings</h2>", unsafe_allow_html=True)
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass

    st.markdown('Atur koneksi database sementara (tidak disimpan persist).')
    host = st.text_input('DB Host', value='localhost')
    database = st.text_input('Database', value='db_monitoring_iku7')
    user = st.text_input('User', value='root')
    password = st.text_input('Password', value='', type='password')
    st.info('Perubahan hanya berlaku saat reload halaman.')
    return host, database, user, password


def show_about():
    st.markdown("<h2>ℹ️ About</h2>", unsafe_allow_html=True)
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass

    st.markdown('Aplikasi Dasbor Monitoring IKU 7 — Universitas Andalas')
    st.markdown('- Developer: Tim Internal')
    st.markdown('- Data Source: MySQL star-schema (fact_iku7 + dim_*)')
    st.markdown('')
    st.markdown('**Data Diri Pengembang:**')
    st.markdown('- Revin Pahlevi — NIM 2311522024')
    st.markdown('- Rahil Akram Hammad — NIM 2311523012')
    st.markdown('- Abdul Hakim Aziz — NIM 2311523020')


def main():
    # Render custom HTML sidebar navigation (uses query param `menu`)
    menu_items = [
        ("Dashboard", "📊"),

        ("Data Browser", "🗂️"),
        ("Dimensions", "📚"),
        ("Reports", "📈"),
        ("Settings", "🔧"),
        ("About", "ℹ️"),
    ]

    # Read query param and prepare sync
    try:
        params = st.experimental_get_query_params()
        qmenu_raw = params.get('menu', [None])[0]
        qmenu = urllib.parse.unquote_plus(qmenu_raw) if qmenu_raw else None
    except Exception:
        params = {}
        qmenu = None

    # Ensure session key exists
    if 'current_menu' not in st.session_state:
        st.session_state['current_menu'] = 'Dashboard'

    # If URL requests a different menu, honor it and rerun once to sync UI
    if qmenu and st.session_state.get('current_menu') != qmenu:
        st.session_state['current_menu'] = qmenu
        try:
            safe_rerun()
        except Exception:
            pass

    # Use a stateful radio widget keyed so Streamlit remembers the selection
    menu_names = [name for name, _ in menu_items]
    current = st.session_state.get('current_menu', 'Dashboard')

    # Initialize a sidebar widget state to the current menu if not present
    if 'sidebar_menu' not in st.session_state:
        st.session_state['sidebar_menu'] = current

    choice = st.sidebar.radio("Menu", menu_names, key='sidebar_menu')

    # When user selects a different menu, update session; avoid forcing rerun
    if choice != st.session_state.get('current_menu'):
        st.session_state['current_menu'] = choice
        try:
            st.experimental_set_query_params(menu=urllib.parse.quote_plus(choice))
        except Exception:
            # Older Streamlit: skip URL sync
            pass

    # Quick sidebar debug so values are always visible even if main content is styled
    try:
        params = st.experimental_get_query_params()
        st.sidebar.markdown('---')
        st.sidebar.markdown('**DEBUG (sidebar)**')
        st.sidebar.write(params)
        st.sidebar.write({'session_current_menu': st.session_state.get('current_menu')})
    except Exception:
        pass

    # Persistent, highly-visible debug box (contrasting color so it's obvious)
    try:
        params = st.experimental_get_query_params()
        sess = st.session_state.get('current_menu')
        debug_html = f"""
        <div style="background:#fffbcc;border-left:6px solid #f59e0b;padding:12px;border-radius:6px;color:#000;margin-bottom:10px">
          <strong>DEBUG — Global navigation (persistent, temporary)</strong>
          <pre style="white-space:pre-wrap;margin-top:8px">query_params: {params}\nsession_current_menu: {sess}</pre>
        </div>
        """
        st.markdown(debug_html, unsafe_allow_html=True)
    except Exception:
        pass

    # (removed debug messages)

    # Load settings from Settings page defaults or session_state
    host = st.session_state.get('db_host', 'localhost')
    database = st.session_state.get('db_name', 'db_monitoring_iku7')
    user = st.session_state.get('db_user', 'root')
    password = st.session_state.get('db_password', '')

    # Show simple ETL status in the sidebar (processed file timestamp + fact row count)
    def get_etl_status(host, database, user, password):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        processed_file = os.path.join(root, 'data', 'processed', 'Data_Matakuliah_Bersih.csv')
        status = {'processed_file_exists': False, 'processed_file_mtime': None, 'fact_rows': None}
        try:
            if os.path.exists(processed_file):
                status['processed_file_exists'] = True
                status['processed_file_mtime'] = datetime.fromtimestamp(os.path.getmtime(processed_file)).isoformat(sep=' ', timespec='seconds')
        except Exception:
            pass

        try:
            conn = mysql.connector.connect(host=host, database=database, user=user, password=password)
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM fact_iku7;')
            status['fact_rows'] = cur.fetchone()[0]
            cur.close()
            conn.close()
        except Exception:
            status['fact_rows'] = None

        return status

    etl_status = get_etl_status(host, database, user, password)
    st.sidebar.markdown('---')
    st.sidebar.markdown('**ETL Status**')
    if etl_status.get('processed_file_exists'):
        st.sidebar.write('Processed file: ✅')
        st.sidebar.write(f"Last processed: {etl_status.get('processed_file_mtime')}")
    else:
        st.sidebar.write('Processed file: ❌ (not found)')

    if etl_status.get('fact_rows') is None:
        st.sidebar.write('Fact table: ❓ (DB unreachable)')
    else:
        st.sidebar.write(f"Fact rows: {etl_status.get('fact_rows')}")

    # Memuat data dengan proteksi
    try:
        df = get_data_from_mysql(host=host, database=database, user=user, password=password)
    except Exception as e:
        st.sidebar.error('Tidak terhubung ke MySQL. Beberapa fitur mungkin tidak tersedia.')
        df = pd.DataFrame()

    if choice == 'Dashboard':
        if df.empty:
            st.warning("Silakan jalankan pipa pemrograman data 'clean_data.py' terlebih dahulu untuk memigrasikan data ke MySQL!")
        else:
            show_dashboard(df, etl_status)
    elif choice == 'Data Browser':
        show_data_browser(df, etl_status)

    elif choice == 'ETL Control':
        st.markdown("<h2>⚙️ ETL Control</h2>", unsafe_allow_html=True)
        st.markdown('Jalankan pipeline pembersihan dan muat ulang data.')
        if st.button('Run clean_data.py'):
            run_etl_script()
    elif choice == 'Dimensions':
        show_dimensions(df, etl_status)
    elif choice == 'Reports':
        show_reports(df, etl_status)
    elif choice == 'Settings':
        h, db, u, p = show_settings()
        if st.button('Apply (session only)'):
            st.session_state['db_host'] = h
            st.session_state['db_name'] = db
            st.session_state['db_user'] = u
            st.session_state['db_password'] = p
            st.success('Pengaturan diterapkan ke sesi. Reload halaman untuk memuat ulang koneksi.')
    elif choice == 'About':
        show_about()


if __name__ == '__main__':
    main()