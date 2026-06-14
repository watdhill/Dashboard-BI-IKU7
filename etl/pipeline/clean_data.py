"""
Pipeline ETL Terpadu — Monitoring IKU 7 Universitas Andalas
============================================================
File tunggal yang menggabungkan seluruh proses ETL:
  1. STAGING  : Baca file mentah → bersihkan → simpan CSV bersih
  2. DIMENSI  : Isi tabel dim_semester, dim_metode, dim_prodi, dim_mata_kuliah
  3. FAKTA    : Petakan relasi → isi tabel fact_iku7
  4. ORKESTRASI: Jalankan semua tahap secara berurutan

Cara pakai:
  python etl/pipeline/clean_data.py
"""

import os
import sys
import csv
import pandas as pd
import mysql.connector

# ══════════════════════════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

DB_CONFIG = {
    "host": "localhost",
    "database": "db_monitoring_iku7",
    "user": "root",
    "password": ""  # Sesuaikan password MySQL kalian
}


# ══════════════════════════════════════════════════════════════
# TAHAP 1 — STAGING (Ekstraksi & Pembersihan Data)
# ══════════════════════════════════════════════════════════════
def ekstrak_dan_bersihkan_staging():
    """Membaca file mentah dari data/raw, membersihkan, lalu menyimpan ke data/processed."""
    folder_raw = os.path.join(ROOT_DIR, "data", "raw")
    file_bersih = os.path.join(ROOT_DIR, "data", "processed", "Data_Matakuliah_Bersih.csv")

    # Cari file mentah
    file_mentah = None
    target_nama_files = ["Data_Matakuliah_Gabungan.xlsx", "Data_Matakuliah_Gabungan.csv"]

    for nama_file in target_nama_files:
        path_test = os.path.join(folder_raw, nama_file)
        if os.path.exists(path_test):
            file_mentah = path_test
            break

    if not file_mentah:
        print(f"[STAGING ERROR] Berkas mentah tidak ditemukan di: {folder_raw}")
        return None

    print(f"[STAGING] Membaca data mentah dari: {os.path.basename(file_mentah)}")
    df = pd.read_excel(file_mentah) if file_mentah.endswith('.xlsx') else pd.read_csv(file_mentah)

    # Standardisasi kolom & teks
    df.columns = df.columns.str.strip().str.lower()
    if 'nama_mata_kuliah' in df.columns:
        df.rename(columns={'nama_mata_kuliah': 'nama mata kuliah'}, inplace=True)
    if 'semester_mk' in df.columns:
        df.rename(columns={'semester_mk': 'semester mk'}, inplace=True)

    df['prodi'] = df['prodi'].astype(str).str.strip().str.title()
    df['kode_mk'] = df['kode_mk'].astype(str).str.replace(" ", "", regex=False).str.upper()
    df['nama mata kuliah'] = df['nama mata kuliah'].astype(str).str.strip().str.title()
    df['semester mk'] = df['semester mk'].astype(str).str.strip()
    df['metode'] = df['metode'].astype(str).str.strip().replace({
        'PJBL': 'PjBL', 'pjbl': 'PjBL', 'BIASA': 'Biasa', 'biasa': 'Biasa', 'Cbm': 'CBM', 'cbm': 'CBM'
    })
    df['sks'] = pd.to_numeric(df['sks'], errors='coerce').fillna(2).astype(int)

    os.makedirs(os.path.dirname(file_bersih), exist_ok=True)
    df.to_csv(file_bersih, index=False)
    print("[STAGING SUCCESS] Data bersih siap di area processed.")
    return df


# ══════════════════════════════════════════════════════════════
# TAHAP 2 — DIMENSI (Pengisian Tabel-tabel Dimensi)
# ══════════════════════════════════════════════════════════════
def isi_tabel_dimensi(cursor, df_clean):
    """Mengisi dim_semester, dim_metode, dim_prodi, dim_mata_kuliah."""
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

    # 3. Isi dim_prodi (dengan mapping fakultas)
    mapping_path = os.path.join(ROOT_DIR, 'data', 'mappings', 'prodi_to_fakultas.csv')
    prodi_map_file = {}
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
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
        # 1) Gunakan mapping file jika tersedia
        if prd in prodi_map_file and prodi_map_file.get(prd):
            fakultas_default = prodi_map_file.get(prd)
        else:
            # 2) Heuristik keyword sebagai fallback
            p = prd.lower()
            if any(k in p for k in ['psikologi', 'sosiologi', 'sosiolog', 'administrasi publik',
                                     'ilmu politik', 'ilmu komunikasi', 'hubungan internasional']):
                fakultas_default = 'Fakultas Ilmu Sosial dan Ilmu Politik'
            elif any(k in p for k in ['ekonomi', 'manajemen', 'akuntansi', 'perbankan']):
                fakultas_default = 'Fakultas Ekonomi dan Bisnis'
            elif any(k in p for k in ['biologi', 'kimia', 'fisika', 'matematika', 'statistik']):
                fakultas_default = 'Fakultas Matematika dan Ilmu Pengetahuan Alam'
            elif any(k in p for k in ['kedokteran', 'farmasi', 'kebidanan', 'biomedis',
                                       'keperawatan', 'kesehatan']):
                fakultas_default = 'Fakultas Kedokteran dan Ilmu Kesehatan'
            elif any(k in p for k in ['hukum']):
                fakultas_default = 'Fakultas Hukum'
            else:
                fakultas_default = 'Fakultas Lainnya'
                unmatched.append(prd)

        cursor.execute(
            "INSERT INTO dim_prodi (nama_prodi, fakultas) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE fakultas=VALUES(fakultas);", (prd, fakultas_default)
        )

    if unmatched:
        print('[DIMENSIONS WARNING] Beberapa prodi tidak otomatis terpetakan '
              '(periksa data/mappings/prodi_to_fakultas.csv):')
        for u in unmatched[:20]:
            print(' -', u)

    # 4. Isi dim_mata_kuliah
    for _, row in df_clean.drop_duplicates(subset=['kode_mk']).iterrows():
        cursor.execute(
            "INSERT INTO dim_mata_kuliah (kode_mk, nama_mk) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE nama_mk=VALUES(nama_mk);", (row['kode_mk'], row['nama mata kuliah'])
        )
    print("[DIMENSIONS SUCCESS] Seluruh komponen tabel dimensi terisi.")


# ══════════════════════════════════════════════════════════════
# TAHAP 3 — FAKTA (Pengisian Tabel Fakta)
# ══════════════════════════════════════════════════════════════
def isi_tabel_fakta(cursor, df_clean):
    """Memetakan relasi bisnis dan mengisi tabel fact_iku7."""
    print("[FACTS] Memetakan relasi bisnis dan mengisi tabel fakta...")

    cursor.execute("TRUNCATE TABLE fact_iku7;")

    # Ambil map ID dari database
    cursor.execute("SELECT id_prodi, nama_prodi FROM dim_prodi;")
    prodi_map = {name: id_ for id_, name in cursor.fetchall()}

    cursor.execute("SELECT id_mk, kode_mk FROM dim_mata_kuliah;")
    mk_map = {code: id_ for id_, code in cursor.fetchall()}

    cursor.execute("SELECT id_semester, CONCAT(nama_semester, ' ', tahun_akademik) FROM dim_semester;")
    sem_map = {name: id_ for id_, name in cursor.fetchall()}

    cursor.execute("SELECT id_metode, nama_metode FROM dim_metode;")
    metode_map = {name: id_ for id_, name in cursor.fetchall()}

    fact_rows = []
    for _, row in df_clean.iterrows():
        id_prodi = prodi_map.get(row['prodi'])
        id_mk = mk_map.get(row['kode_mk'])
        id_semester = sem_map.get(row['semester mk'])
        id_metode = metode_map.get(row['metode'])

        if id_prodi and id_mk and id_semester and id_metode:
            fact_rows.append((id_prodi, id_mk, id_semester, id_metode, int(row['sks']), 1))

    cursor.executemany(
        "INSERT INTO fact_iku7 (id_prodi, id_mk, id_semester, id_metode, sks, jumlah_mk) "
        "VALUES (%s, %s, %s, %s, %s, %s);", fact_rows
    )
    print(f"[FACTS SUCCESS] Total {len(fact_rows)} baris termuat di Fact Table.")


# ══════════════════════════════════════════════════════════════
# ORKESTRASI — Eksekusi Pipeline Lengkap
# ══════════════════════════════════════════════════════════════
def eksekusi_orkestrasi_pipeline_lengkap():
    """Menjalankan seluruh tahap ETL secara berurutan."""
    print("=" * 60)
    print("[ORCHESTRATOR] Memulai Eksekusi Pipeline ETL Terpadu...")
    print("=" * 60)

    # TAHAP 1: Staging
    df_clean = ekstrak_dan_bersihkan_staging()
    if df_clean is None:
        print("[ERROR] Proses terhenti di tahap staging.")
        return

    # TAHAP 2 & 3: Koneksi DB → Dimensi → Fakta
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # Isi tabel dimensi
        isi_tabel_dimensi(cursor, df_clean)
        conn.commit()

        # Isi tabel fakta
        isi_tabel_fakta(cursor, df_clean)

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()

        print("=" * 60)
        print("[SUKSES] Seluruh pipeline ETL terpadu berhasil dieksekusi!")
        print("=" * 60)

    except mysql.connector.Error as err:
        print(f"[PIPELINE ERROR] Mengalami kendala: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    eksekusi_orkestrasi_pipeline_lengkap()