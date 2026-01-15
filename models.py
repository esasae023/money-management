# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from cryptography.fernet import Fernet
import os
import json

db = SQLAlchemy()

# Enkripsi Helper
class EncryptionManager:
    def __init__(self):
        self.key = os.getenv('SECRET_KEY_ENCRYPTION').encode() if os.getenv('SECRET_KEY_ENCRYPTION') else Fernet.generate_key()
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
    
    name = db.Column(db.String(100), nullable=False) # Nama Folder/Project
    spreadsheet_url = db.Column(db.String(500), nullable=False) # Link Sheet unik per folder
    
    # List Nama Sheet (Manual Input, dipisah koma. Contoh: "Januari,Februari,Maret")
    sheet_list_str = db.Column(db.Text, default="Januari,Februari,Maret,April,Mei,Juni,Juli,Agustus,September,Oktober,November,Desember")
    
    # --- KONFIGURASI PANEL (GRAFANA STYLE) ---
    # Kita simpan "Nama Kolom" excel yang akan dipakai oleh masing-masing panel
    
    # Panel 1: Summary & Grafik Harian
    col_date = db.Column(db.String(50), default="Timestamp")
    col_income = db.Column(db.String(50), default="Nominal Pemasukan")
    col_expense = db.Column(db.String(50), default="Nominal Pengeluaran")
    cell_addr_income = db.Column(db.String(10), default="K1")  # Posisi Total Pemasukan
    cell_addr_expense = db.Column(db.String(10), default="K2") # Posisi Total Pengeluaran
    cell_addr_balance = db.Column(db.String(10), default="K3") # Posisi Sisa Saldo
    
    # Panel 2: Grafik Kategori (Pie Chart)
    col_category = db.Column(db.String(50), default="Sumber Pengeluaran")
    col_cat_type = db.Column(db.String(50), default="Jenis") # Untuk filter "Pengeluaran"
    
    def get_sheet_list(self):
        return [x.strip() for x in self.sheet_list_str.split(',') if x.strip()]