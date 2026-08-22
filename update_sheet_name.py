import sqlite3

def update_db():
    conn = sqlite3.connect('instance/money_manager.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE monitor_folder ADD COLUMN port_sheet_name VARCHAR(100) DEFAULT 'Portofolio'")
        print("[OK] Kolom port_sheet_name berhasil ditambahkan!")
    except Exception as e:
        print(f"Error (mungkin kolom sudah ada): {e}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_db()