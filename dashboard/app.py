import os
import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px

# 1. Konfigurasi Utama Layar Web Dasbor
st.set_page_config(
    page_title="Monitoring IKU 7 - UNAND", 
    page_icon="📊", 
    layout="wide"
)

# 2. Fungsi Mengambil Data Menggunakan JOIN Relasional Star Schema MySQL
def get_data_from_mysql():
    conn = mysql.connector.connect(
        host="localhost",
        database="db_monitoring_iku7",  # Sinkron dengan nama database penampungan baru kalian
        user="root",           
        password=""  # !!! SAMAKAN PASSWORD MYSQL DENGAN FILE ETL !!!
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

# Memuat data secara aman dengan proteksi try-except
try:
    df = get_data_from_mysql()
except Exception as e:
    st.error(f"Gagal memuat visualisasi karena tidak terhubung ke MySQL Data Warehouse! Detail: {e}")
    df = pd.DataFrame()

if not df.empty:
    # --- TAMPILAN JENDELA DASBOR ---
    st.title("📊 Dasbor Monitoring Capaian IKU 7 Universitas Andalas")
    st.markdown("Evaluasi Real-Time Kurikulum Terintegrasi Berbasis Sistem Pangkalan Data *Star Schema* MySQL")
    st.markdown("---")

    # --- PANEL FILTER SIDEBAR ---
    st.sidebar.header("Panel Filter Analisis")
    
    # Filter Fakultas
    all_fakultas = ["Semua Fakultas"] + list(df['fakultas'].unique())
    selected_fakultas = st.sidebar.selectbox("Pilih Fakultas:", all_fakultas)
    
    # Kondisi filter dinamis berjenjang
    if selected_fakultas != "Semua Fakultas":
        df_filtered_fak = df[df['fakultas'] == selected_fakultas]
    else:
        df_filtered_fak = df
        
    # Filter Program Studi
    all_prodis = sorted(df_filtered_fak['prodi'].unique())
    selected_prodi = st.sidebar.multiselect("Pilih Program Studi:", all_prodis, default=all_prodis)

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
        # Menghitung delta perbandingan terhadap rata-rata baseline makro universitas (15.93%)
        st.metric(label="Persentase Capaian Target IKU 7", value=f"{persen_iku7:.2f}%", delta=f"{persen_iku7 - 15.93:.2f}% vs Baseline Unand")

    st.markdown("---")
    
    # --- LAYOUT GRAFIK VISUALISASI ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📌 Distribusi Metode Pembelajaran")
        # Grafik Donut untuk melihat proporsi kelas konvensional vs kelas aktif
        fig_donut = px.pie(
            df_filtered, 
            names='metode', 
            hole=0.4, 
            color='metode',
            color_discrete_map={'Biasa': '#EF553B', 'PjBL': '#636EFA', 'CBM': '#00CC96'}
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.subheader("🏆 Peringkat Capaian IKU 7 per Program Studi")
        # Hitung agregasi persentase capaian per prodi secara dinamis untuk bar chart peringkat
        prodi_stats = df_filtered.groupby('prodi').apply(
            lambda x: (len(x[x['metode'].isin(['PjBL', 'CBM'])]) / len(x)) * 100
        ).reset_index(name='percent')
        prodi_stats = prodi_stats.sort_values(by='percent', ascending=True)
        
        fig_bar = px.bar(
            prodi_stats, 
            x='percent', 
            y='prodi', 
            orientation='h', 
            labels={'percent': 'Capaian (%)', 'prodi': 'Program Studi'},
            color='percent', 
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # --- LAYOUT TABEL DETAIL REKOMENDASI TINDAKAN ---
    st.subheader("📋 Daftar Prioritas Konversi Mata Kuliah Konvensional")
    st.markdown("Tabel interaktif di bawah ini menyaring daftar kelas berstatus **Biasa** sebagai acuan taktis Ketua Prodi untuk dikonversi menjadi metode pengajaran aktif di semester depan.")
    
    df_biasa = df_filtered[df_filtered['metode'] == 'Biasa'][['prodi', 'kode_mk', 'nama mata kuliah', 'sks', 'metode']]
    st.dataframe(df_biasa, use_container_width=True)

else:
    st.warning("Silakan jalankan pipa pemrograman data 'clean_data.py' terlebih dahulu untuk memigrasikan data ke MySQL!")