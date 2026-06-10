import mysql.connector

def isi_tabel_fakta(cursor, df_clean):
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