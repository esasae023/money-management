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
    if not client: return None, {}, {}, {}, "Google Account belum disetting."
    
    try:
        sheet = client.open_by_url(folder.spreadsheet_url)
        worksheet = sheet.worksheet(sheet_name)
        raw_data = worksheet.get_all_values()
        
        if not raw_data: return None, {}, {}, {}, "Sheet kosong."

        def clean_indo_number(val):
            try:
                s = str(val).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                return float(s) if s else 0
            except: return 0

        def get_cell_value(addr):
            try:
                if not addr: return 0
                row, col = a1_to_rowcol(addr)
                val = raw_data[row-1][col-1]
                return clean_indo_number(val)
            except: return 0

        # 1. KPI UTAMA
        summary = {
            'income': f"{get_cell_value(folder.cell_addr_income):,.0f}",
            'expense': f"{get_cell_value(folder.cell_addr_expense):,.0f}",
            'balance': f"{get_cell_value(folder.cell_addr_balance):,.0f}"
        }

        # 2. DATA PIE CHART (Dipisah Income & Expense)
        pie_income = {'labels': [], 'data': []}
        pie_expense = {'labels': [], 'data': []}

        for cat in folder.categories:
            val = get_cell_value(cat.cell_addr)
            if val > 0:
                if cat.type == 'income':
                    pie_income['labels'].append(cat.name)
                    pie_income['data'].append(val)
                else:
                    pie_expense['labels'].append(cat.name)
                    pie_expense['data'].append(val)

        # 3. DATA LINE CHART (Harian)
        df = pd.DataFrame()
        # Cari header
        header_index = 0
        found = False
        for i, row in enumerate(raw_data):
            if folder.col_date in row:
                header_index = i
                found = True
                break
        
        if found and len(raw_data) > header_index + 1:
            df = pd.DataFrame(raw_data[header_index+1:], columns=raw_data[header_index])
            
            # Bersihkan angka Pemasukan & Pengeluaran
            if folder.col_expense in df.columns:
                df[folder.col_expense] = df[folder.col_expense].apply(clean_indo_number)
            if folder.col_income in df.columns:
                df[folder.col_income] = df[folder.col_income].apply(clean_indo_number)
            
            df[folder.col_date] = pd.to_datetime(df[folder.col_date], errors='coerce')

        return df, summary, pie_income, pie_expense, None

    except Exception as e:
        return None, {}, {}, {}, str(e)

# --- ROUTES ---
@app.route('/')
def index(): return redirect(url_for('login')) if not current_user.is_authenticated else redirect(url_for('home'))

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
        creds = request.form['google_creds']
        enc = crypto.encrypt(creds)
        sett = GlobalSettings.query.filter_by(user_id=current_user.id).first()
        if not sett:
            sett = GlobalSettings(user_id=current_user.id, google_creds_encrypted=enc)
            db.session.add(sett)
        else:
            sett.google_creds_encrypted = enc
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('settings_global.html')

@app.route('/folder/create', methods=['POST'])
@login_required
def create_folder():
    new_folder = MonitorFolder(name=request.form['name'], spreadsheet_url=request.form['url'], user_id=current_user.id)
    db.session.add(new_folder)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/folder/<int:folder_id>/settings', methods=['GET', 'POST'])
@login_required
def folder_settings(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    if request.method == 'POST':
        folder.name = request.form['name']
        folder.spreadsheet_url = request.form['url']
        folder.sheet_list_str = request.form['sheet_list']
        folder.col_date = request.form['col_date']
        folder.col_income = request.form['col_income']
        folder.col_expense = request.form['col_expense']
        folder.cell_addr_income = request.form['cell_addr_income']
        folder.cell_addr_expense = request.form['cell_addr_expense']
        folder.cell_addr_balance = request.form['cell_addr_balance']
        db.session.commit()
        flash('Pengaturan tersimpan.', 'success')
        return redirect(url_for('folder_settings', folder_id=folder.id))
    
    # Pisahkan kategori untuk ditampilkan di 2 tabel berbeda
    cats_income = [c for c in folder.categories if c.type == 'income']
    cats_expense = [c for c in folder.categories if c.type == 'expense']
    return render_template('settings_folder.html', folder=folder, cats_income=cats_income, cats_expense=cats_expense)

@app.route('/folder/<int:folder_id>/category/add', methods=['POST'])
@login_required
def add_category(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    name = request.form.get('cat_name')
    addr = request.form.get('cat_addr')
    tipe = request.form.get('cat_type') # 'income' atau 'expense'
    
    if name and addr and tipe:
        new_cat = CategoryMap(folder_id=folder.id, name=name, cell_addr=addr, type=tipe)
        db.session.add(new_cat)
        db.session.commit()
        flash(f'Kategori {tipe} ditambahkan!', 'success')
    
    return redirect(url_for('folder_settings', folder_id=folder.id))

@app.route('/category/delete/<int:cat_id>')
@login_required
def delete_category(cat_id):
    cat = CategoryMap.query.get_or_404(cat_id)
    folder = MonitorFolder.query.get(cat.folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('folder_settings', folder_id=folder.id))

@app.route('/folder/<int:folder_id>/dashboard')
@login_required
def dashboard(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    sheet_list = folder.get_sheet_list()
    selected_month = request.args.get('month', sheet_list[0] if sheet_list else 'Sheet1')
    
    summary = {'income': '0', 'expense': '0', 'balance': '0'}
    pie_income = {'labels': [], 'data': []}
    pie_expense = {'labels': [], 'data': []}
    chart_trend = {'labels': [], 'income': [], 'expense': []}
    error_msg = None

    # Fetch Data (Sekarang return 5 variable)
    df, sum_data, p_inc, p_exp, err = fetch_sheet_data(folder, selected_month)
    
    if sum_data: summary = sum_data
    if p_inc: pie_income = p_inc
    if p_exp: pie_expense = p_exp
    if err: error_msg = err

    # Logic Line Chart (Gabungan Pemasukan & Pengeluaran)
    if df is not None and not df.empty:
        try:
            # Group by Tanggal
            grp = df.groupby(df[folder.col_date].dt.date).sum(numeric_only=True).reset_index()
            
            chart_trend['labels'] = grp[folder.col_date].astype(str).tolist()
            # Cek kolom ada atau tidak, kalau tidak isi 0
            if folder.col_income in grp.columns:
                chart_trend['income'] = grp[folder.col_income].tolist()
            else:
                chart_trend['income'] = [0] * len(chart_trend['labels'])
                
            if folder.col_expense in grp.columns:
                chart_trend['expense'] = grp[folder.col_expense].tolist()
            else:
                chart_trend['expense'] = [0] * len(chart_trend['labels'])
                
        except Exception as e:
            pass 

    return render_template('dashboard.html', 
                           folder=folder, sheet_list=sheet_list, selected_month=selected_month,
                           summary=summary, 
                           chart_trend=chart_trend,
                           pie_income=pie_income,
                           pie_expense=pie_expense,
                           error_msg=error_msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)