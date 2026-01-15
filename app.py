# app.py
import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import db, User, SpreadsheetConfig, crypto
from datetime import datetime

# Load env variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'rahasia-banget')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPERS ---
def get_google_data(config, month_sheet_name):
    """
    Mengambil data dari Google Sheet berdasarkan config user.
    Mendekripsi kredensial on-the-fly.
    """
    try:
        creds_json = crypto.decrypt(config.google_creds_encrypted)
        creds_dict = json.loads(creds_json)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(config.sheet_url)
        worksheet = sheet.worksheet(month_sheet_name)
        
        # Ambil semua data
        data = worksheet.get_all_values()
        
        # LOGIC PARSING KHUSUS (Berdasarkan file yang Anda upload)
        # File Anda memiliki header summary di atas. Header asli tabel ada di baris yang mengandung 'Timestamp'
        header_row_index = 0
        for i, row in enumerate(data):
            if config.col_date in row: # Mencari row header "Timestamp"
                header_row_index = i
                break
        
        # Buat dataframe mulai dari header yang benar
        df = pd.DataFrame(data[header_row_index+1:], columns=data[header_row_index])
        
        # Konversi tipe data
        # Hapus 'Rp', koma, titik jika ada format currency string
        def clean_currency(x):
            if not x or x == '': return 0
            return float(str(x).replace('.','').replace(',','').replace('Rp','').strip())

        df[config.col_amount_in] = df[config.col_amount_in].apply(clean_currency)
        df[config.col_amount_out] = df[config.col_amount_out].apply(clean_currency)
        
        # Konversi Date
        df[config.col_date] = pd.to_datetime(df[config.col_date], errors='coerce')
        df = df.dropna(subset=[config.col_date]) # Hapus baris kosong/summary bawah
        
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# --- ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login gagal. Periksa username dan password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    # Ambil filter dari URL
    selected_year_id = request.args.get('year_id')
    selected_month = request.args.get('month', 'Januari') # Default
    
    # Ambil daftar Tahun (Folder) milik user ini saja
    configs = SpreadsheetConfig.query.filter_by(user_id=current_user.id).all()
    
    current_config = None
    df = None
    summary = {}
    
    if configs:
        # Tentukan config mana yang dipakai
        if selected_year_id:
            current_config = SpreadsheetConfig.query.get(selected_year_id)
            if current_config.user_id != current_user.id: current_config = configs[0] # Security check
        else:
            current_config = configs[0]
            
        # Fetch Data
        df = get_google_data(current_config, selected_month)
        
        if df is not None:
            # --- AGGREGATION LOGIC (Mirip Grafana Query) ---
            
            # 1. Total Summary
            total_income = df[current_config.col_amount_in].sum()
            total_expense = df[current_config.col_amount_out].sum()
            balance = total_income - total_expense
            
            summary = {
                'income': f"{total_income:,.0f}",
                'expense': f"{total_expense:,.0f}",
                'balance': f"{balance:,.0f}"
            }
            
            # 2. Daily Trend (Line Chart)
            daily_grp = df.groupby(df[current_config.col_date].dt.date)[[current_config.col_amount_out]].sum().reset_index()
            chart_daily_labels = daily_grp[current_config.col_date].astype(str).tolist()
            chart_daily_values = daily_grp[current_config.col_amount_out].tolist()
            
            # 3. Category Pie Chart (Pengeluaran)
            cat_grp = df[df[current_config.col_type] == 'Pengeluaran'].groupby(current_config.col_category)[current_config.col_amount_out].sum().reset_index()
            chart_cat_labels = cat_grp[current_config.col_category].tolist()
            chart_cat_values = cat_grp[current_config.col_amount_out].tolist()
            
        else:
            flash(f'Gagal memuat data sheet "{selected_month}". Pastikan nama sheet benar.', 'warning')
            chart_daily_labels, chart_daily_values = [], []
            chart_cat_labels, chart_cat_values = [], []

    return render_template('dashboard.html', 
                           configs=configs, 
                           current_config=current_config,
                           selected_month=selected_month,
                           summary=summary,
                           chart_daily={'labels': chart_daily_labels, 'data': chart_daily_values},
                           chart_cat={'labels': chart_cat_labels, 'data': chart_cat_values})

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Logic untuk menyimpan Config baru
        # User menginput JSON content dari file Service Account Google di sini
        year_label = request.form['year_label']
        sheet_url = request.form['sheet_url']
        creds_content = request.form['google_creds'] # Isi JSON text
        
        encrypted_creds = crypto.encrypt(creds_content)
        
        new_config = SpreadsheetConfig(
            user_id=current_user.id,
            year_label=year_label,
            sheet_url=sheet_url,
            google_creds_encrypted=encrypted_creds,
            # Bisa tambahkan input form untuk mapping kolom jika ingin custom
            col_date=request.form.get('col_date', 'Timestamp'),
            col_amount_in=request.form.get('col_in', 'Nominal Pemasukan'),
            col_amount_out=request.form.get('col_out', 'Nominal Pengeluaran')
        )
        db.session.add(new_config)
        db.session.commit()
        flash('Konfigurasi Tahun berhasil ditambahkan!', 'success')
        
    return render_template('settings.html')

# --- INITIAL SETUP ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)