# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from cryptography.fernet import Fernet
import os

db = SQLAlchemy()

# Helper untuk Enkripsi/Dekripsi Data Sensitif (API Keys)
class EncryptionManager:
    def __init__(self):
        # Kunci ini HARUS diload dari environment variable di server
        self.key = os.getenv('SECRET_KEY_ENCRYPTION').encode() if os.getenv('SECRET_KEY_ENCRYPTION') else Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data):
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, token):
        return self.cipher.decrypt(token.encode()).decode()

crypto = EncryptionManager()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    # Relasi ke konfigurasi spreadsheet
    spreadsheets = db.relationship('SpreadsheetConfig', backref='owner', lazy=True)

class SpreadsheetConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    year_label = db.Column(db.String(10), nullable=False) # Contoh: "2025" (Folder)
    sheet_url = db.Column(db.String(500), nullable=False) # Link Google Sheet
    # Kredensial Google Service Account (JSON string) disimpan terenkripsi
    google_creds_encrypted = db.Column(db.Text, nullable=False)
    
    # Konfigurasi Mapping Kolom (Grafana style simple)
    col_date = db.Column(db.String(50), default="Timestamp")
    col_type = db.Column(db.String(50), default="Jenis") # Pemasukan/Pengeluaran
    col_category = db.Column(db.String(50), default="Sumber Pengeluaran")
    col_amount_in = db.Column(db.String(50), default="Nominal Pemasukan")
    col_amount_out = db.Column(db.String(50), default="Nominal Pengeluaran")