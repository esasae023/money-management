import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from cryptography.fernet import Fernet

db = SQLAlchemy()

# Class Enkripsi
class EncryptionManager:
    def __init__(self):
        self.key = b'gAAAAABlz8wLcwjT0E4w1q5uV6tD5yZ8q3_uW9aQ7n0=' 
        self.cipher = Fernet(self.key)
    def encrypt(self, data): return self.cipher.encrypt(data.encode()).decode()
    def decrypt(self, token): return self.cipher.decrypt(token.encode()).decode()

crypto = EncryptionManager()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    recovery_code = db.Column(db.String(20), nullable=True)
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
    
    # Config Budget Utama
    col_date = db.Column(db.String(50), default="Timestamp")
    col_income = db.Column(db.String(50), default="Nominal Pemasukan")
    col_expense = db.Column(db.String(50), default="Nominal Pengeluaran")
    col_source_income = db.Column(db.String(50), default="Sumber Pemasukan")
    col_source_expense = db.Column(db.String(50), default="Sumber Pengeluaran")
    debt_keywords = db.Column(db.String(200), default="Hutang,Piutang,Sahur hutang")
    cell_addr_income = db.Column(db.String(10), default="K1")
    cell_addr_expense = db.Column(db.String(10), default="K2")
    cell_addr_balance = db.Column(db.String(10), default="K3")
    clean_income_cells = db.Column(db.Text, default="") 
    clean_expense_cells = db.Column(db.Text, default="")
    
    # Config Hutang Piutang
    col_desc_inc = db.Column(db.String(50), default="E")
    col_desc_exp = db.Column(db.String(50), default="J")
    cell_hutang_kotor = db.Column(db.String(10), default="")
    cell_hutang_dibayar = db.Column(db.String(10), default="")
    cell_piutang_kotor = db.Column(db.String(10), default="")
    cell_piutang_dibayar = db.Column(db.String(10), default="")
    kw_hutang_masuk = db.Column(db.String(100), default="Hutang")
    kw_hutang_keluar = db.Column(db.String(100), default="Sahur Hutang")
    kw_piutang_keluar = db.Column(db.String(100), default="Hutang")
    kw_piutang_masuk = db.Column(db.String(100), default="Sahur Hutang")
    
    # ==========================================
    # [BARU] CONFIG PORTOFOLIO (DASHBOARD 1)
    # ==========================================
    # Mapping Cell KPI Portofolio Tahunan
    port_sheet_name = db.Column(db.String(100), default="Portofolio")
    port_cell_inc_kotor = db.Column(db.String(10), default="")
    port_cell_exp_kotor = db.Column(db.String(10), default="")
    port_cell_bal_kotor = db.Column(db.String(10), default="")
    port_cell_inc_bersih = db.Column(db.String(10), default="")
    port_cell_exp_bersih = db.Column(db.String(10), default="")
    port_cell_bal_bersih = db.Column(db.String(10), default="")
    
    # Mapping Huruf Kolom Chart Tren Portofolio Tahunan
    port_col_month = db.Column(db.String(5), default="A")
    port_col_inc_kotor = db.Column(db.String(5), default="B")
    port_col_exp_kotor = db.Column(db.String(5), default="C")
    port_col_bal_kotor = db.Column(db.String(5), default="D")
    port_col_inc_bersih = db.Column(db.String(5), default="E")
    port_col_exp_bersih = db.Column(db.String(5), default="F")
    port_col_bal_bersih = db.Column(db.String(5), default="G")
    port_start_row = db.Column(db.Integer, default=2) # Untuk menghindari baca header
    
    categories = db.relationship('CategoryMap', backref='folder', lazy=True, cascade="all, delete-orphan")
    def get_sheet_list(self): return [x.strip() for x in self.sheet_list_str.split(',') if x.strip()]

class CategoryMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('monitor_folder.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cell_addr = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(20), default='expense')
    is_clean = db.Column(db.Boolean, default=False)

class FormShortcut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# ==========================================
# [BARU] TABEL ASET & PORTOFOLIO OVERALL
# ==========================================

class AssetData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nama_aset = db.Column(db.String(100), nullable=False) # cth: Emas Antam 5g
    harga_beli = db.Column(db.Float, nullable=False)
    tanggal_beli = db.Column(db.String(50), nullable=False) # cth: 15 Agustus 2026
    tahun = db.Column(db.Integer, nullable=False) # Digunakan untuk filter di Dashboard 1

class OverallPortfolioConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spreadsheet_url = db.Column(db.String(500), nullable=False)
    sheet_name = db.Column(db.String(100), default="Overall")
    
    # Mapping Cell KPI Overall
    cell_inc_kotor = db.Column(db.String(10), default="")
    cell_exp_kotor = db.Column(db.String(10), default="")
    cell_bal_kotor = db.Column(db.String(10), default="")
    cell_inc_bersih = db.Column(db.String(10), default="")
    cell_exp_bersih = db.Column(db.String(10), default="")
    cell_bal_bersih = db.Column(db.String(10), default="")
    
    # Mapping Huruf Kolom Chart Tren Overall (Tahunan)
    col_year = db.Column(db.String(5), default="A")
    col_inc_kotor = db.Column(db.String(5), default="B")
    col_exp_kotor = db.Column(db.String(5), default="C")
    col_bal_kotor = db.Column(db.String(5), default="D")
    col_inc_bersih = db.Column(db.String(5), default="E")
    col_exp_bersih = db.Column(db.String(5), default="F")
    col_bal_bersih = db.Column(db.String(5), default="G")
    start_row = db.Column(db.Integer, default=2)

class PortfolioCategoryMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Jika folder_id ada, berarti milik portofolio dashboard 1. Jika kosong, milik Overall.
    folder_id = db.Column(db.Integer, db.ForeignKey('monitor_folder.id'), nullable=True) 
    is_overall = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=False)
    cell_addr = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(20), default='expense')
    is_clean = db.Column(db.Boolean, default=False)