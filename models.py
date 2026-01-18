import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from cryptography.fernet import Fernet

db = SQLAlchemy()

# Enkripsi Helper
class EncryptionManager:
    def __init__(self):
        # Gunakan key tetap untuk development agar tidak error saat restart
        # Di production, simpan ini di .env
        self.key = b'gAAAAABlz8wLcwjT0E4w1q5uV6tD5yZ8q3_uW9aQ7n0=' 
        self.cipher = Fernet(self.key)
    def encrypt(self, data): return self.cipher.encrypt(data.encode()).decode()
    def decrypt(self, token): return self.cipher.decrypt(token.encode()).decode()

crypto = EncryptionManager()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    folders = db.relationship('MonitorFolder', backref='owner', lazy=True)

class GlobalSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    google_creds_encrypted = db.Column(db.Text, nullable=False)

class MonitorFolder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    spreadsheet_url = db.Column(db.String(500), nullable=False)
    sheet_list_str = db.Column(db.Text, default="Januari,Februari,Maret")
    
    # --- KONFIGURASI PANEL 1 (KPI & GRAFIK HARIAN) ---
    col_date = db.Column(db.String(50), default="Timestamp")
    col_expense = db.Column(db.String(50), default="Nominal Pengeluaran") # Masih dipakai untuk Line Chart (Trend)
    
    # Mapping Cell KPI (Total Atas)
    cell_addr_income = db.Column(db.String(10), default="K1")
    cell_addr_expense = db.Column(db.String(10), default="K2")
    cell_addr_balance = db.Column(db.String(10), default="K3")
    
    # --- RELASI KE KATEGORI CUSTOM (PIE CHART) ---
    # Ini menggantikan kolom col_category lama
    categories = db.relationship('CategoryMap', backref='folder', lazy=True, cascade="all, delete-orphan")
    
    def get_sheet_list(self):
        return [x.strip() for x in self.sheet_list_str.split(',') if x.strip()]

# --- TABEL BARU: Mapping Kategori ---
class CategoryMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('monitor_folder.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)    # Contoh: "Makan"
    cell_addr = db.Column(db.String(10), nullable=False) # Contoh: "Z1"