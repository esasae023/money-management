import sqlite3
import os

db_path = 'instance/money_manager.db' if os.path.exists('instance/money_manager.db') else 'money_manager.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Membuka database di: {db_path}")
    
    # Membuat tabel form_shortcut
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS form_shortcut (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month VARCHAR(20) NOT NULL,
            url VARCHAR(500) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🎉 UPGRADE DATABASE SELESAI! Tabel 'form_shortcut' berhasil ditambahkan.")

except Exception as e:
    print(f"❌ Terjadi kesalahan: {str(e)}")