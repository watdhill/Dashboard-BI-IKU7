import sys
import os
import mysql.connector

# Menambahkan root project ke path sistem agar Python bisa mendeteksi modul folder lain
base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
sys.path.append(root_dir)

# Import modul fungsi dari folder dimensi, fakta, dan staging kalian
from database.staging.load_staging import ekstrak_dan_bersihkan_staging
from database.dimensions.load_dimensions import isi_tabel_dimensi
from database.facts.load_facts import isi_tabel_fakta

db_config = {
    "host": "localhost",
    "database": "db_monitoring_iku7",
    "user": "root",
    "password": ""  # Sesuaikan password MySQL kalian
}

def eksekusi_orkestrasi_pipeline_lengkap():
    print("=" * 60)
    print("[ORCHESTRATOR] Memulai Eksekusi Pipeline ETL Modular...")
    print("=" * 60)
    
    # 1. Jalankan komponen Staging
    df_clean = ekstrak_dan_bersihkan_staging()
    if df_clean is None:
        print("[ERROR] Proses terhenti di tahap staging.")
        return
        
    # 2. Jalankan Koneksi Database untuk Dimensi dan Fakta
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # Panggil fungsi dari folder dimensions/
        isi_tabel_dimensi(cursor, df_clean)
        conn.commit()
        
        # Panggil fungsi dari folder facts/
        isi_tabel_fakta(cursor, df_clean)
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        
        print("=" * 60)
        print("[SUKSES MASAL] Seluruh file folder modular bekerja dengan sempurna!")
        print("=" * 60)
        
    except mysql.connector.Error as err:
        print(f"[PIPELINE ERROR] Mengalami kendala: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    eksekusi_orkestrasi_pipeline_lengkap()