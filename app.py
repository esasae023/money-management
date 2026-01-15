# app.py
import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import db, User, GlobalSettings, MonitorFolder, crypto
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'rahasia')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER: KONEKSI GOOGLE SHEET ---
def get_google_client():
    settings = GlobalSettings.query.first()
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
    """
    Mengambil data dengan error handling agar tidak Internal Server Error
    """
    client = get_google_client()
    if not client: return None, "Google Account belum disetting admin."
    
    try:
        sheet = client.open_by_url(folder.spreadsheet_url)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        
        # Cari header row (baris yang mengandung nama kolom tanggal)
        header_index = 0
        found = False
        for i, row in enumerate(data):
            if folder.col_date in row:
                header_index = i
                found = True
                break
        
        if not found: return None, f"Kolom '{folder.col_date}' tidak ditemukan di sheet."

        df = pd.DataFrame(data[header_index+1:], columns=data[header_index])
        
        # Bersihkan data numerik
        def clean_num(x):
            try: return float(str(x).replace('.','').replace(',','').replace('Rp','').strip())
            except: return 0
            
        df[folder.col_income] = df[folder.col_income].apply(clean_num)
        df[folder.col_expense] = df[folder.col_expense].apply(clean_num)
        df[folder.col_date] = pd.to_datetime(df[folder.col_date], errors='coerce')
        
        return df, None
    except gspread.exceptions.WorksheetNotFound:
        return None, f"Sheet '{sheet_name}' tidak ditemukan."
    except Exception as e:
        return None, str(e)

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
    # Halaman utama: List Folder
    folders = MonitorFolder.query.filter_by(user_id=current_user.id).all()
    global_set = GlobalSettings.query.first()
    return render_template('home.html', folders=folders, has_global=bool(global_set))

@app.route('/settings/global', methods=['GET', 'POST'])
@login_required
def settings_global():
    # Setting Google Credential (Global)
    if request.method == 'POST':
        creds_content = request.form['google_creds']
        encrypted = crypto.encrypt(creds_content)
        
        setting = GlobalSettings.query.first()
        if not setting:
            setting = GlobalSettings(google_creds_encrypted=encrypted)
            db.session.add(setting)
        else:
            setting.google_creds_encrypted = encrypted
        db.session.commit()
        flash('Global Google Credentials updated!', 'success')
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

@app.route('/folder/<int:folder_id>/settings', methods=['GET', 'POST'])
@login_required
def folder_settings(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    if request.method == 'POST':
        folder.name = request.form['name']
        folder.spreadsheet_url = request.form['url']
        folder.sheet_list_str = request.form['sheet_list']
        # Mapping Kolom
        folder.col_date = request.form['col_date']
        folder.col_income = request.form['col_income']
        folder.col_expense = request.form['col_expense']
        folder.col_category = request.form['col_category']
        db.session.commit()
        flash('Pengaturan Folder disimpan.', 'success')
        return redirect(url_for('dashboard', folder_id=folder.id))
        
    return render_template('settings_folder.html', folder=folder)

@app.route('/folder/<int:folder_id>/dashboard')
@login_required
def dashboard(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    sheet_list = folder.get_sheet_list()
    selected_month = request.args.get('month', sheet_list[0] if sheet_list else 'Sheet1')
    
    # Default Values (Agar tidak Internal Server Error)
    summary = {'income': '0', 'expense': '0', 'balance': '0'}
    chart_daily = {'labels': [], 'data': []}
    chart_cat = {'labels': [], 'data': []}
    error_msg = None

    # Fetch Data
    df, error = fetch_sheet_data(folder, selected_month)
    
    if error:
        error_msg = error
    elif df is not None and not df.empty:
        try:
            # 1. Summary logic
            inc = df[folder.col_income].sum()
            exp = df[folder.col_expense].sum()
            summary = {
                'income': f"{inc:,.0f}",
                'expense': f"{exp:,.0f}",
                'balance': f"{inc - exp:,.0f}"
            }
            
            # 2. Chart Harian logic
            daily = df.groupby(df[folder.col_date].dt.date)[folder.col_expense].sum().reset_index()
            chart_daily = {
                'labels': daily[folder.col_date].astype(str).tolist(),
                'data': daily[folder.col_expense].tolist()
            }
            
            # 3. Chart Kategori logic (Filter hanya 'Pengeluaran')
            # Cek apakah ada kolom filter 'Jenis' (optional)
            if folder.col_cat_type in df.columns:
                cat_df = df[df[folder.col_cat_type] == 'Pengeluaran']
            else:
                cat_df = df # Ambil semua jika tidak ada kolom jenis
                
            cat_grp = cat_df.groupby(folder.col_category)[folder.col_expense].sum().reset_index()
            chart_cat = {
                'labels': cat_grp[folder.col_category].tolist(),
                'data': cat_grp[folder.col_expense].tolist()
            }
        except Exception as e:
            error_msg = f"Error saat memproses data: {str(e)}. Cek setting kolom."

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