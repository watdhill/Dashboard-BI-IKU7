import os
import sys
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse
import pandas as pd
import mysql.connector
import plotly.express as px

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

def show_dashboard(df):
    # --- TAMPILAN JENDELA DASBOR ---
    st.title("📊 Dasbor Monitoring Capaian IKU 7 Universitas Andalas")
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


def show_data_browser(df):
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
    files = list_data_files()
    st.subheader('File Raw')
    st.write(files.get('raw', []))
    st.subheader('File Processed')
    st.write(files.get('processed', []))
    st.markdown('---')
    if not df.empty:
        st.subheader('Data Lengkap')
        st.dataframe(df.reset_index(drop=True), use_container_width=True)
    else:
        st.warning("Data tidak tersedia. Jalankan ETL atau cek koneksi database.")


def show_dimensions(df):
    st.markdown("<h2>📚 Dimensions</h2>", unsafe_allow_html=True)
    try:
        params = st.experimental_get_query_params()
        st.markdown("**DEBUG — Navigation values (temporary)**")
        st.write({'query_params': params})
        st.write({'session_current_menu': st.session_state.get('current_menu')})
        st.markdown("---")
    except Exception:
        pass
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


def show_reports(df):
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


def main():
    # Render custom HTML sidebar navigation (uses query param `menu`)
    menu_items = [
        ("Dashboard", "📊"),
        ("Data Browser", "🗂️"),
        ("ETL Control", "⚙️"),
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
        st.experimental_rerun()

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
            show_dashboard(df)
    elif choice == 'Data Browser':
        show_data_browser(df)
    elif choice == 'ETL Control':
        st.markdown("<h2>⚙️ ETL Control</h2>", unsafe_allow_html=True)
        st.markdown('Jalankan pipeline pembersihan dan muat ulang data.')
        if st.button('Run clean_data.py'):
            run_etl_script()
    elif choice == 'Dimensions':
        show_dimensions(df)
    elif choice == 'Reports':
        show_reports(df)
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