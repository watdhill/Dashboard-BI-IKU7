import os
import pandas as pd

def ekstrak_dan_bersihkan_staging():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
    folder_raw = os.path.join(root_dir, "data", "raw")
    file_bersih = os.path.join(root_dir, "data", "processed", "Data_Matakuliah_Bersih.csv")
    
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
    if 'nama_mata_kuliah' in df.columns: df.rename(columns={'nama_mata_kuliah': 'nama mata kuliah'}, inplace=True)
    if 'semester_mk' in df.columns: df.rename(columns={'semester_mk': 'semester mk'}, inplace=True)
        
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

if __name__ == "__main__":
    ekstrak_dan_bersihkan_staging()