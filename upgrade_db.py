import sqlite3
import os

# Mencari lokasi file database (biasanya di root atau di dalam folder 'instance')
db_path = 'instance/money_manager.db' if os.path.exists('instance/money_manager.db') else 'money_manager.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
# Daftar kolom baru untuk fitur Hutang Piutang
    kolom_baru = [
        "col_desc_inc VARCHAR(50) DEFAULT 'E'",
        "col_desc_exp VARCHAR(50) DEFAULT 'J'",
        "cell_hutang_kotor VARCHAR(10) DEFAULT ''",
        "cell_hutang_dibayar VARCHAR(10) DEFAULT ''",
        "cell_piutang_kotor VARCHAR(10) DEFAULT ''",
        "cell_piutang_dibayar VARCHAR(10) DEFAULT ''",
        "kw_hutang_masuk VARCHAR(100) DEFAULT 'Hutang'",
        "kw_hutang_keluar VARCHAR(100) DEFAULT 'Sahur Hutang'",
        "kw_piutang_keluar VARCHAR(100) DEFAULT 'Hutang'",
        "kw_piutang_masuk VARCHAR(100) DEFAULT 'Sahur Hutang'"
    ]
    
    print(f"Membuka database di: {db_path}")
    for kolom in kolom_baru:
        try:
            cursor.execute(f"ALTER TABLE monitor_folder ADD COLUMN {kolom};")
            print(f"✅ Berhasil menambahkan kolom: {kolom.split()[0]}")
        except Exception as e:
            # Jika error (biasanya karena kolom sudah ada), lewati saja
            print(f"⚠️ Melewati {kolom.split()[0]} (Info: {str(e)})")
            
    conn.commit()
    conn.close()
    print("\n🎉 UPGRADE DATABASE SELESAI! Semua data lama Anda AMAN.")

except Exception as e:
    print(f"❌ Terjadi kesalahan saat membuka database: {str(e)}")