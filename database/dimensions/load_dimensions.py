import mysql.connector

def isi_tabel_dimensi(cursor, df_clean):
    print("[DIMENSIONS] Mulai mengisi tabel-tabel dimensi...")
    
    # 1. Isi dim_semester
    for sem in df_clean['semester mk'].drop_duplicates():
        parts = sem.split(" ")
        nama_sem = parts[0] if len(parts) > 0 else "Ganjil"
        thn_akad = parts[1] if len(parts) > 1 else "2024/2025"
        cursor.execute(
            "INSERT INTO dim_semester (tahun_akademik, nama_semester) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE tahun_akademik=VALUES(tahun_akademik);", (thn_akad, nama_sem)
        )
        
    # 2. Isi dim_metode
    for met in df_clean['metode'].drop_duplicates():
        cursor.execute(
            "INSERT INTO dim_metode (nama_metode) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE nama_metode=VALUES(nama_metode);", (met,)
        )
        
    # 3. Isi dim_prodi
    for prd in df_clean['prodi'].drop_duplicates():
        fakultas_default = "Fakultas Teknologi Informasi"
        if prd in ["Psikologi", "Sociologi", "Sosiologi", "Administrasi Publik"]:
            fakultas_default = "Fakultas Ilmu Sosial dan Ilmu Politik"
        elif prd in ["Ekonomi Islam", "Manajemen Pemasaran"]:
            fakultas_default = "Fakultas Ekonomi dan Bisnis"
        elif prd in ["Biologi", "Kimia", "Matematika", "Fisika"]:
            fakultas_default = "Fakultas Matematika dan Ilmu Pengetahuan Alam"
        cursor.execute(
            "INSERT INTO dim_prodi (nama_prodi, fakultas) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE fakultas=VALUES(fakultas);", (prd, fakultas_default)
        )
        
    # 4. Isi dim_mata_kuliah
    for _, row in df_clean.drop_duplicates(subset=['kode_mk']).iterrows():
        cursor.execute(
            "INSERT INTO dim_mata_kuliah (kode_mk, nama_mk) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE nama_mk=VALUES(nama_mk);", (row['kode_mk'], row['nama mata kuliah'])
        )
    print("[DIMENSIONS SUCCESS] Seluruh komponen tabel dimensi terisi.")