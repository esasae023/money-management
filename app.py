import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import a1_to_rowcol
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import db, User, GlobalSettings, MonitorFolder, CategoryMap, crypto
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia_banget_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER: KONEKSI GOOGLE SHEET ---
def get_google_client():
    if not current_user.is_authenticated: return None
    settings = GlobalSettings.query.filter_by(user_id=current_user.id).first()
    if not settings: return None
    try:
        creds_json = crypto.decrypt(settings.google_creds_encrypted)
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def fetch_sheet_data(folder, sheet_name):
    client = get_google_client()
    if not client: return None, {}, {}, "Google Account belum disetting."
    
    try:
        sheet = client.open_by_url(folder.spreadsheet_url)
        worksheet = sheet.worksheet(sheet_name)
        raw_data = worksheet.get_all_values()
        
        if not raw_data: return None, {}, {}, "Sheet kosong."

        # Helper: Bersihkan Format Rupiah (Rp 1.000,00 -> 1000.0)
        def clean_indo_number(val):
            try:
                s = str(val).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                return float(s) if s else 0
            except: return 0

        # Helper: Ambil Nilai Cell (Z1, K5)
        def get_cell_value(addr):
            try:
                if not addr: return 0
                row, col = a1_to_rowcol(addr)
                val = raw_data[row-1][col-1]
                return clean_indo_number(val)
            except: return 0

        # 1. AMBIL DATA KPI (Income, Expense, Balance)
        summary = {
            'income': f"{get_cell_value(folder.cell_addr_income):,.0f}",
            'expense': f"{get_cell_value(folder.cell_addr_expense):,.0f}",
            'balance': f"{get_cell_value(folder.cell_addr_balance):,.0f}"
        }

        # 2. AMBIL DATA PIE CHART (Dari Mapping Kategori Custom)
        cat_labels = []
        cat_data = []
        for cat in folder.categories:
            val = get_cell_value(cat.cell_addr)
            if val > 0:
                cat_labels.append(cat.name)
                cat_data.append(val)
        
        chart_cat = {
            'labels': cat_labels,
            'data': cat_data
        }

        # 3. AMBIL DATA LINE CHART (Harian) - Masih butuh Pandas untuk tanggal
        header_index = 0
        found = False
        for i, row in enumerate(raw_data):
            if folder.col_date in row:
                header_index = i
                found = True
                break
        
        df = pd.DataFrame()
        if found and len(raw_data) > header_index + 1:
            df = pd.DataFrame(raw_data[header_index+1:], columns=raw_data[header_index])
            # Bersihkan kolom expense agar bisa dijumlah per hari
            if folder.col_expense in df.columns:
                df[folder.col_expense] = df[folder.col_expense].apply(clean_indo_number)
            df[folder.col_date] = pd.to_datetime(df[folder.col_date], errors='coerce')

        return df, summary, chart_cat, None

    except Exception as e:
        return None, {}, {}, str(e)

# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('home'))
        flash('Login gagal', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    folders = MonitorFolder.query.filter_by(user_id=current_user.id).all()
    global_set = GlobalSettings.query.filter_by(user_id=current_user.id).first()
    return render_template('home.html', folders=folders, has_global=bool(global_set))

@app.route('/settings/global', methods=['GET', 'POST'])
@login_required
def settings_global():
    if request.method == 'POST':
        creds_content = request.form['google_creds']
        encrypted = crypto.encrypt(creds_content)
        
        setting = GlobalSettings.query.filter_by(user_id=current_user.id).first()
        if not setting:
            setting = GlobalSettings(user_id=current_user.id, google_creds_encrypted=encrypted)
            db.session.add(setting)
        else:
            setting.google_creds_encrypted = encrypted
            
        db.session.commit()
        flash('API Key berhasil disimpan!', 'success')
        return redirect(url_for('home'))
    return render_template('settings_global.html')

@app.route('/folder/create', methods=['POST'])
@login_required
def create_folder():
    name = request.form['name']
    url = request.form['url']
    new_folder = MonitorFolder(name=name, spreadsheet_url=url, user_id=current_user.id)
    db.session.add(new_folder)
    db.session.commit()
    return redirect(url_for('home'))

# --- ROUTE SETTING FOLDER (UPDATED) ---
@app.route('/folder/<int:folder_id>/settings', methods=['GET', 'POST'])
@login_required
def folder_settings(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Simpan General & KPI
        folder.name = request.form['name']
        folder.spreadsheet_url = request.form['url']
        folder.sheet_list_str = request.form['sheet_list']
        
        folder.col_date = request.form['col_date']
        folder.col_expense = request.form['col_expense']
        
        folder.cell_addr_income = request.form['cell_addr_income']
        folder.cell_addr_expense = request.form['cell_addr_expense']
        folder.cell_addr_balance = request.form['cell_addr_balance']
        
        db.session.commit()
        flash('Pengaturan berhasil disimpan.', 'success')
        return redirect(url_for('folder_settings', folder_id=folder.id))
        
    return render_template('settings_folder.html', folder=folder)

# --- ROUTE TAMBAH KATEGORI (NEW) ---
@app.route('/folder/<int:folder_id>/category/add', methods=['POST'])
@login_required
def add_category(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    name = request.form.get('cat_name')
    addr = request.form.get('cat_addr')
    
    if name and addr:
        new_cat = CategoryMap(folder_id=folder.id, name=name, cell_addr=addr)
        db.session.add(new_cat)
        db.session.commit()
        flash('Kategori ditambahkan!', 'success')
    
    return redirect(url_for('folder_settings', folder_id=folder.id))

# --- ROUTE HAPUS KATEGORI (NEW) ---
@app.route('/category/delete/<int:cat_id>')
@login_required
def delete_category(cat_id):
    cat = CategoryMap.query.get_or_404(cat_id)
    folder = MonitorFolder.query.get(cat.folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    db.session.delete(cat)
    db.session.commit()
    flash('Kategori dihapus.', 'warning')
    return redirect(url_for('folder_settings', folder_id=folder.id))

@app.route('/folder/<int:folder_id>/dashboard')
@login_required
def dashboard(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    sheet_list = folder.get_sheet_list()
    selected_month = request.args.get('month', sheet_list[0] if sheet_list else 'Sheet1')
    
    summary = {'income': '0', 'expense': '0', 'balance': '0'}
    chart_cat = {'labels': [], 'data': []}
    chart_daily = {'labels': [], 'data': []}
    error_msg = None

    # Fetch Data Baru (Return 4 variabel)
    df, summary_data, chart_data, error = fetch_sheet_data(folder, selected_month)
    
    if summary_data: summary = summary_data
    if chart_data: chart_cat = chart_data # Chart Pie diambil dari hasil cell mapping
    if error: error_msg = error

    # Logic Line Chart (Harian) tetap pakai Pandas
    if df is not None and not df.empty:
        try:
            if folder.col_date in df.columns and folder.col_expense in df.columns:
                daily = df.groupby(df[folder.col_date].dt.date)[folder.col_expense].sum().reset_index()
                chart_daily = {
                    'labels': daily[folder.col_date].astype(str).tolist(),
                    'data': daily[folder.col_expense].tolist()
                }
        except Exception as e:
            pass # Ignore chart error if summary is fine

    return render_template('dashboard.html', 
                           folder=folder, 
                           sheet_list=sheet_list, 
                           selected_month=selected_month,
                           summary=summary, 
                           chart_daily=chart_daily, 
                           chart_cat=chart_cat,
                           error_msg=error_msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)