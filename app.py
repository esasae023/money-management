import os
import json
import pandas as pd
import gspread
from datetime import timedelta
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import a1_to_rowcol
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError # Import untuk menangani error duplicate username
from models import db, User, GlobalSettings, MonitorFolder, CategoryMap, crypto
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia_banget_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session Timeout 30 Menit
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

db.init_app(app)
bcrypt = Bcrypt(app)

# --- KONFIGURASI FLASK LOGIN ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# [BARU] Terjemahkan pesan "Please log in..." ke Bahasa Indonesia
login_manager.login_message = "Silakan login untuk mengakses halaman ini."
login_manager.login_message_category = "danger"  # Agar alert berwarna merah

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def make_session_permanent():
    session.permanent = True

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
    if not client: return None, {}, {}, {}, {}, {}, {}, "Akun Google belum diatur."
    
    try:
        sheet = client.open_by_url(folder.spreadsheet_url)
        worksheet = sheet.worksheet(sheet_name)
        raw_data = worksheet.get_all_values()
        
        if not raw_data: return None, {}, {}, {}, {}, {}, {}, "Sheet kosong."

        def clean_indo_number(val):
            try:
                s = str(val).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                return float(s) if s else 0
            except: return 0

        def get_cell_value(addr):
            try:
                if not addr: return 0
                row, col = a1_to_rowcol(addr.strip())
                val = raw_data[row-1][col-1]
                return clean_indo_number(val)
            except: return 0
            
        def sum_cells(cell_list_str):
            if not cell_list_str: return 0
            total = 0
            cells = cell_list_str.split(',')
            for cell in cells:
                if cell.strip():
                    total += get_cell_value(cell)
            return total

        # Summary
        sum_kotor = {
            'income': f"{get_cell_value(folder.cell_addr_income):,.0f}",
            'expense': f"{get_cell_value(folder.cell_addr_expense):,.0f}",
            'balance': f"{get_cell_value(folder.cell_addr_balance):,.0f}"
        }
        
        clean_inc_val = sum_cells(folder.clean_income_cells)
        clean_exp_val = sum_cells(folder.clean_expense_cells)
        clean_bal_val = clean_inc_val - clean_exp_val
        sum_clean = {
            'income': f"{clean_inc_val:,.0f}",
            'expense': f"{clean_exp_val:,.0f}",
            'balance': f"{clean_bal_val:,.0f}"
        }

        # Pie Chart
        pie_data = {
            'clean_inc': {'labels': [], 'data': []},
            'clean_exp': {'labels': [], 'data': []},
            'dirty_inc': {'labels': [], 'data': []},
            'dirty_exp': {'labels': [], 'data': []}
        }

        for cat in folder.categories:
            val = get_cell_value(cat.cell_addr)
            if val > 0:
                if cat.type == 'income':
                    pie_data['dirty_inc']['labels'].append(cat.name)
                    pie_data['dirty_inc']['data'].append(val)
                else:
                    pie_data['dirty_exp']['labels'].append(cat.name)
                    pie_data['dirty_exp']['data'].append(val)
                
                if cat.is_clean:
                    if cat.type == 'income':
                        pie_data['clean_inc']['labels'].append(cat.name)
                        pie_data['clean_inc']['data'].append(val)
                    else:
                        pie_data['clean_exp']['labels'].append(cat.name)
                        pie_data['clean_exp']['data'].append(val)

        # Trend Chart
        df_dirty = pd.DataFrame()
        df_clean = pd.DataFrame()
        
        header_index = 0
        found = False
        for i, row in enumerate(raw_data):
            if folder.col_date in row:
                header_index = i
                found = True
                break
        
        if found and len(raw_data) > header_index + 1:
            df = pd.DataFrame(raw_data[header_index+1:], columns=raw_data[header_index])
            
            if folder.col_income in df.columns:
                df[folder.col_income] = df[folder.col_income].apply(clean_indo_number)
            if folder.col_expense in df.columns:
                df[folder.col_expense] = df[folder.col_expense].apply(clean_indo_number)
            
            df[folder.col_date] = pd.to_datetime(df[folder.col_date], errors='coerce')
            
            df_dirty = df.copy()
            df_clean = df.copy()
            keywords = [k.strip().lower() for k in folder.debt_keywords.split(',') if k.strip()]
            
            if folder.col_source_income in df_clean.columns:
                mask_debt_inc = df_clean[folder.col_source_income].astype(str).str.lower().apply(
                    lambda x: any(k in x for k in keywords)
                )
                df_clean.loc[mask_debt_inc, folder.col_income] = 0

            if folder.col_source_expense in df_clean.columns:
                mask_debt_exp = df_clean[folder.col_source_expense].astype(str).str.lower().apply(
                    lambda x: any(k in x for k in keywords)
                )
                df_clean.loc[mask_debt_exp, folder.col_expense] = 0

        return df_dirty, df_clean, sum_kotor, sum_clean, pie_data, None

    except Exception as e:
        return None, None, {}, {}, {}, str(e)

# --- ROUTES ---
@app.route('/')
def index(): return redirect(url_for('login')) if not current_user.is_authenticated else redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('home'))
        # FLASH MESSAGE BAHASA INDONESIA
        flash('Login gagal. Periksa username atau password Anda.', 'danger')
    return render_template('login.html')

# --- [BARU] ROUTE REGISTER ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validasi
        if password != confirm_password:
            flash('Password dan Konfirmasi Password tidak sama!', 'danger')
            return redirect(url_for('register'))
            
        try:
            # Hash password menggunakan Bcrypt (sama seperti di profile)
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Username sudah digunakan. Pilih username lain.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if len(new_password) < 6:
            # FLASH MESSAGE BAHASA INDONESIA
            flash('Gagal: Password minimal 6 karakter.', 'danger')
            return redirect(url_for('profile'))
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        # FLASH MESSAGE BAHASA INDONESIA
        flash('Berhasil: Password Anda telah diubah!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

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
        
        folder.col_source_income = request.form['col_source_income']
        folder.col_source_expense = request.form['col_source_expense']
        folder.debt_keywords = request.form['debt_keywords']
        
        folder.cell_addr_income = request.form['cell_addr_income']
        folder.cell_addr_expense = request.form['cell_addr_expense']
        folder.cell_addr_balance = request.form['cell_addr_balance']
        
        folder.clean_income_cells = request.form['clean_income_cells']
        folder.clean_expense_cells = request.form['clean_expense_cells']
        
        db.session.commit()
        # FLASH MESSAGE BAHASA INDONESIA
        flash('Pengaturan berhasil disimpan.', 'success')
        return redirect(url_for('folder_settings', folder_id=folder.id))
    
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
    tipe = request.form.get('cat_type')
    is_clean = True if request.form.get('is_clean') else False
    if name and addr and tipe:
        new_cat = CategoryMap(folder_id=folder.id, name=name, cell_addr=addr, type=tipe, is_clean=is_clean)
        db.session.add(new_cat)
        db.session.commit()
        # FLASH MESSAGE BAHASA INDONESIA
        label = "Pemasukan" if tipe == 'income' else "Pengeluaran"
        flash(f'Kategori {label} berhasil ditambahkan!', 'success')
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
    
    sum_kotor = {'income': 0, 'expense': 0, 'balance': 0}
    sum_clean = {'income': 0, 'expense': 0, 'balance': 0}
    
    chart_clean = {'labels': [], 'income': [], 'expense': []}
    chart_dirty = {'labels': [], 'income': [], 'expense': []}
    
    pie_data = {
        'clean_inc': {'labels': [], 'data': []},
        'clean_exp': {'labels': [], 'data': []},
        'dirty_inc': {'labels': [], 'data': []},
        'dirty_exp': {'labels': [], 'data': []}
    }
    error_msg = None

    df_dirty, df_clean, kotor, clean, pies, err = fetch_sheet_data(folder, selected_month)
    
    if kotor: sum_kotor = kotor
    if clean: sum_clean = clean
    
    if pies and isinstance(pies, dict):
        if 'clean_inc' in pies: pie_data['clean_inc'] = pies['clean_inc']
        if 'clean_exp' in pies: pie_data['clean_exp'] = pies['clean_exp']
        if 'dirty_inc' in pies: pie_data['dirty_inc'] = pies['dirty_inc']
        if 'dirty_exp' in pies: pie_data['dirty_exp'] = pies['dirty_exp']
        
    if err: error_msg = err

    if df_dirty is not None and not df_dirty.empty:
        try:
            grp = df_dirty.groupby(df_dirty[folder.col_date].dt.date).sum(numeric_only=True).reset_index()
            chart_dirty['labels'] = grp[folder.col_date].astype(str).tolist()
            chart_dirty['income'] = grp[folder.col_income].tolist() if folder.col_income in grp else []
            chart_dirty['expense'] = grp[folder.col_expense].tolist() if folder.col_expense in grp else []
        except: pass

    if df_clean is not None and not df_clean.empty:
        try:
            grp = df_clean.groupby(df_clean[folder.col_date].dt.date).sum(numeric_only=True).reset_index()
            chart_clean['labels'] = grp[folder.col_date].astype(str).tolist()
            chart_clean['income'] = grp[folder.col_income].tolist() if folder.col_income in grp else []
            chart_clean['expense'] = grp[folder.col_expense].tolist() if folder.col_expense in grp else []
        except: pass

    return render_template('dashboard.html', 
                           folder=folder, sheet_list=sheet_list, selected_month=selected_month,
                           sum_kotor=sum_kotor, sum_clean=sum_clean,
                           chart_dirty=chart_dirty, chart_clean=chart_clean,
                           pie_data=pie_data, error_msg=error_msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)