import mysql.connector
import os
import csv

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
    # Attempt to load explicit mapping file: data/mappings/prodi_to_fakultas.csv
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    mapping_path = os.path.join(root_dir, 'data', 'mappings', 'prodi_to_fakultas.csv')
    prodi_map_file = {}
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row: continue
                    key = row[0].strip()
                    val = row[1].strip() if len(row) > 1 else ''
                    if key:
                        prodi_map_file[key] = val
            print(f"[DIMENSIONS] Loaded prodi->fakultas mapping from {mapping_path}")
        except Exception as e:
            print(f"[DIMENSIONS] Gagal membaca mapping file: {e}")

    unmatched = []
    for prd in df_clean['prodi'].drop_duplicates():
        fakultas_default = None
        # 1) use mapping file if available
        if prd in prodi_map_file and prodi_map_file.get(prd):
            fakultas_default = prodi_map_file.get(prd)
        else:
            # 2) conservative keyword heuristics (fallback)
            p = prd.lower()
            if any(k in p for k in ['psikologi', 'sosiologi', 'sosiolog', 'administrasi publik', 'ilmu politik', 'ilmu komunikasi', 'hubungan internasional', 'ilmu politik', 'ilmu komunikasi', 'ilmu komunikasi']):
                fakultas_default = 'Fakultas Ilmu Sosial dan Ilmu Politik'
            elif any(k in p for k in ['ekonomi', 'manajemen', 'akuntansi', 'perbankan']):
                fakultas_default = 'Fakultas Ekonomi dan Bisnis'
            elif any(k in p for k in ['biologi', 'kimia', 'fisika', 'matematika', 'statistik']):
                fakultas_default = 'Fakultas Matematika dan Ilmu Pengetahuan Alam'
            elif any(k in p for k in ['kedokteran', 'farmasi', 'kebidanan', 'biomedis', 'keperawatan', 'kesehatan']):
                fakultas_default = 'Fakultas Kedokteran dan Ilmu Kesehatan'
            elif any(k in p for k in ['hukum']):
                fakultas_default = 'Fakultas Hukum'
            else:
                # leave as unknown for manual review
                fakultas_default = 'Fakultas Lainnya'
                unmatched.append(prd)

        cursor.execute(
            "INSERT INTO dim_prodi (nama_prodi, fakultas) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE fakultas=VALUES(fakultas);", (prd, fakultas_default)
        )

    if unmatched:
        print('[DIMENSIONS WARNING] Beberapa prodi tidak otomatis terpetakan (periksa data/mappings/prodi_to_fakultas.csv):')
        for u in unmatched[:20]:
            print(' -', u)
        
    # 4. Isi dim_mata_kuliah
    for _, row in df_clean.drop_duplicates(subset=['kode_mk']).iterrows():
        cursor.execute(
            "INSERT INTO dim_mata_kuliah (kode_mk, nama_mk) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE nama_mk=VALUES(nama_mk);", (row['kode_mk'], row['nama mata kuliah'])
        )
    print("[DIMENSIONS SUCCESS] Seluruh komponen tabel dimensi terisi.")