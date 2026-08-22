import sqlite3
from app import app, db

def update_database():
    print("Menambahkan kolom Portofolio ke tabel monitor_folder...")
    conn = sqlite3.connect('instance/money_manager.db') # Sesuaikan path jika tidak di dalam folder instance
    cursor = conn.cursor()
    
    columns_to_add = [
        ("port_cell_inc_kotor", "VARCHAR(10) DEFAULT ''"),
        ("port_cell_exp_kotor", "VARCHAR(10) DEFAULT ''"),
        ("port_cell_bal_kotor", "VARCHAR(10) DEFAULT ''"),
        ("port_cell_inc_bersih", "VARCHAR(10) DEFAULT ''"),
        ("port_cell_exp_bersih", "VARCHAR(10) DEFAULT ''"),
        ("port_cell_bal_bersih", "VARCHAR(10) DEFAULT ''"),
        ("port_col_month", "VARCHAR(5) DEFAULT 'A'"),
        ("port_col_inc_kotor", "VARCHAR(5) DEFAULT 'B'"),
        ("port_col_exp_kotor", "VARCHAR(5) DEFAULT 'C'"),
        ("port_col_bal_kotor", "VARCHAR(5) DEFAULT 'D'"),
        ("port_col_inc_bersih", "VARCHAR(5) DEFAULT 'E'"),
        ("port_col_exp_bersih", "VARCHAR(5) DEFAULT 'F'"),
        ("port_col_bal_bersih", "VARCHAR(5) DEFAULT 'G'"),
        ("port_start_row", "INTEGER DEFAULT 2")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE monitor_folder ADD COLUMN {col_name} {col_type}")
            print(f"[OK] Kolom {col_name} berhasil ditambahkan.")
        except sqlite3.OperationalError as e:
            # Mengabaikan error jika kolom sudah ada
            print(f"[-] Kolom {col_name} sudah ada atau error: {e}")
            
    conn.commit()
    conn.close()

    print("\nMembangun tabel baru (AssetData, OverallPortfolioConfig, PortfolioCategoryMap)...")
    with app.app_context():
        db.create_all()
    print("[SELESAI] Database berhasil diperbarui tanpa menghapus data lama!")

if __name__ == '__main__':
    update_database()