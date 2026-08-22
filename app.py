import os
import json
import pandas as pd
import gspread
import random
import string
import re
from datetime import timedelta
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import a1_to_rowcol
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from models import db, User, GlobalSettings, MonitorFolder, CategoryMap, crypto, FormShortcut, OverallPortfolioConfig, PortfolioCategoryMap, AssetData
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
login_manager.login_message = "Silakan login untuk mengakses halaman ini."
login_manager.login_message_category = "danger"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def make_session_permanent():
    session.permanent = True

# --- [HELPER] GENERATE RECOVERY CODE ---
def generate_recovery_code(length=8):
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=length//2))
    part2 = ''.join(random.choices(chars, k=length//2))
    return f"{part1}-{part2}"

# --- HELPER: GOOGLE CLIENT ---
def get_google_client():
    if not current_user.is_authenticated: return None
    settings = GlobalSettings.query.filter_by(user_id=current_user.id).first()
    if not settings or not settings.google_creds_encrypted: return None
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

# --- HELPER: FETCH DATA ---
def fetch_sheet_data(folder, sheet_name):
    client = get_google_client()
    if not client: return None, None, {}, {}, {}, "Akun Google belum diatur."
    
    try:
        sheet = client.open_by_url(folder.spreadsheet_url)
        worksheet = sheet.worksheet(sheet_name)
        raw_data = worksheet.get_all_values()
        
        if not raw_data: return None, None, {}, {}, {}, "Sheet kosong."

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

        # Trend Chart Logic
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

# --- ROUTES AUTH ---

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
        flash('Login gagal. Periksa username atau password Anda.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Password dan Konfirmasi Password tidak sama!', 'danger')
            return redirect(url_for('register'))
            
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            rec_code = generate_recovery_code()
            new_user = User(username=username, password=hashed_password, recovery_code=rec_code)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Akun berhasil dibuat! Simpan KODE PEMULIHAN ini baik-baik.|{rec_code}', 'show_modal')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username sudah digunakan.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        rec_code = request.form.get('recovery_code')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Username tidak ditemukan.', 'danger')
            return redirect(url_for('forgot_password'))
        if user.recovery_code != rec_code:
            flash('Kode Pemulihan salah!', 'danger')
            return redirect(url_for('forgot_password'))
        if new_pass != confirm_pass:
            flash('Password baru tidak sama.', 'warning')
            return redirect(url_for('forgot_password'))

        user.password = bcrypt.generate_password_hash(new_pass).decode('utf-8')
        new_rec_code = generate_recovery_code()
        user.recovery_code = new_rec_code
        db.session.commit()
        flash(f'Password berhasil direset! Ini Kode Pemulihan BARU Anda.|{new_rec_code}', 'show_modal')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    # Tangkap state navigasi
    origin = request.args.get('origin', 'home')
    folder_id = request.args.get('folder_id')

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if len(new_password) < 6:
            flash('Gagal: Password minimal 6 karakter.', 'danger')
            return redirect(url_for('profile', origin=origin, folder_id=folder_id))
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        flash('Berhasil: Password Anda telah diubah!', 'success')
        return redirect(url_for('profile', origin=origin, folder_id=folder_id))
    return render_template('profile.html', origin=origin, folder_id=folder_id)
    
# --- ROUTES FITUR UTAMA (UPDATED) ---

@app.route('/home')
@login_required
def home():
    # Halaman ini sekarang adalah HUB UTAMA (Pilih Tipe Dashboard)
    # Kita hanya perlu cek apakah API Key ada untuk mengaktifkan tombol
    global_set = GlobalSettings.query.filter_by(user_id=current_user.id).first()
    has_creds = False
    if global_set and global_set.google_creds_encrypted:
        has_creds = True
    return render_template('home.html', has_global=has_creds)

@app.route('/dashboard/select-year')
@login_required
def select_year():
    # Ini adalah logika Home yang LAMA (Menampilkan daftar Tahun)
    folders = MonitorFolder.query.filter_by(user_id=current_user.id).all()
    return render_template('select_year.html', folders=folders)

@app.route('/settings/global', methods=['GET', 'POST'])
@login_required
def settings_global():
    sett = GlobalSettings.query.filter_by(user_id=current_user.id).first()

    # Tangkap state navigasi
    origin = request.args.get('origin', 'home')
    folder_id = request.args.get('folder_id')

    # -- 1. LOGIC HAPUS CREDENTIAL --
    if request.method == 'POST' and request.form.get('action') == 'delete':
        if sett:
            sett.google_creds_encrypted = None
            db.session.commit()
            flash('Service Account berhasil dihapus.', 'warning')
        return redirect(url_for('settings_global', origin=origin, folder_id=folder_id))

    # -- 2. LOGIC SIMPAN CREDENTIAL --
    if request.method == 'POST' and request.form.get('action') == 'save':
        try:
            name_sa = request.form['service_name']
            creds_str = request.form['google_creds']
            
            # Validasi JSON
            creds_json = json.loads(creds_str)
            
            # [TRIK] Sisipkan Nama Identitas ke dalam JSON sebelum dienkripsi
            # Agar tidak perlu ubah struktur tabel database
            creds_json['_custom_name'] = name_sa 
            
            final_json_str = json.dumps(creds_json)
            enc = crypto.encrypt(final_json_str)
            
            if not sett:
                sett = GlobalSettings(user_id=current_user.id, google_creds_encrypted=enc)
                db.session.add(sett)
            else:
                sett.google_creds_encrypted = enc
            
            db.session.commit()
            flash('Service Account berhasil ditambahkan!', 'success')
            return redirect(url_for('settings_global', origin=origin, folder_id=folder_id))
            
        except json.JSONDecodeError:
            flash('Format JSON tidak valid.', 'danger')
        except Exception as e:
            flash(f'Gagal menyimpan: {str(e)}', 'danger')

    # -- 3. LOGIC TAMPILKAN DATA SAAT INI --
    existing_data = None
    if sett and sett.google_creds_encrypted:
        try:
            decrypted = crypto.decrypt(sett.google_creds_encrypted)
            data = json.loads(decrypted)
            existing_data = {
                'name': data.get('_custom_name', 'My Service Account'),
                'email': data.get('client_email', 'Unknown Email'),
                'project_id': data.get('project_id', 'Unknown Project')
            }
        except:
            pass

    return render_template('settings_global.html', current_sa=existing_data, origin=origin, folder_id=folder_id)

@app.route('/folder/create', methods=['POST'])
@login_required
def create_folder():
    new_folder = MonitorFolder(name=request.form['name'], spreadsheet_url=request.form['url'], user_id=current_user.id)
    db.session.add(new_folder)
    db.session.commit()
    # Redirect kembali ke halaman pilih tahun, bukan home utama
    return redirect(url_for('select_year'))

@app.route('/folder/<int:folder_id>/settings', methods=['GET', 'POST'])
@login_required
def folder_settings(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))

    origin = request.args.get('origin', 'dash')
    tipe = request.args.get('tipe')
    
    if request.method == 'POST':
        # Simpan Config
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

        # Simpan Konfigurasi Hutang Piutang
        folder.col_desc_inc = request.form.get('col_desc_inc', folder.col_desc_inc)
        folder.col_desc_exp = request.form.get('col_desc_exp', folder.col_desc_exp)
        folder.cell_hutang_kotor = request.form.get('cell_hutang_kotor', folder.cell_hutang_kotor)
        folder.cell_hutang_dibayar = request.form.get('cell_hutang_dibayar', folder.cell_hutang_dibayar)
        folder.cell_piutang_kotor = request.form.get('cell_piutang_kotor', folder.cell_piutang_kotor)
        folder.cell_piutang_dibayar = request.form.get('cell_piutang_dibayar', folder.cell_piutang_dibayar)
        
        folder.kw_hutang_masuk = request.form.get('kw_hutang_masuk', folder.kw_hutang_masuk)
        folder.kw_hutang_keluar = request.form.get('kw_hutang_keluar', folder.kw_hutang_keluar)
        folder.kw_piutang_keluar = request.form.get('kw_piutang_keluar', folder.kw_piutang_keluar)
        folder.kw_piutang_masuk = request.form.get('kw_piutang_masuk', folder.kw_piutang_masuk)
        
        db.session.commit()
        flash('Konfigurasi Tahun berhasil disimpan.', 'success') 
        return redirect(url_for('folder_settings', folder_id=folder.id, origin=origin, tipe=tipe))
    
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
    
    # ... logic dashboard sama ...
    sum_kotor = {'income': 0, 'expense': 0, 'balance': 0}
    sum_clean = {'income': 0, 'expense': 0, 'balance': 0}
    chart_clean = {'labels': [], 'income': [], 'expense': []}
    chart_dirty = {'labels': [], 'income': [], 'expense': []}
    pie_data = {
        'clean_inc': {'labels': [], 'data': []}, 'clean_exp': {'labels': [], 'data': []},
        'dirty_inc': {'labels': [], 'data': []}, 'dirty_exp': {'labels': [], 'data': []}
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

@app.route('/folder/<int:folder_id>/hutang-piutang')
@login_required
def dashboard_hutang(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    sheet_list = folder.get_sheet_list()
    selected_month = request.args.get('month', sheet_list[0] if sheet_list else 'Sheet1')
    
    # Ambil data kotor saja dari helper lama
    df_dirty, _, _, _, _, err = fetch_sheet_data(folder, selected_month)
    error_msg = err

    # Variabel penampung
    hutang_kotor = 0; hutang_dibayar = 0; hutang_sisa = 0
    piutang_kotor = 0; piutang_dibayar = 0; piutang_sisa = 0
    list_hutang = []; list_piutang = []

    try:
        # 1. Ambil nilai KPI langsung dari Spreadsheet
        client = get_google_client()
        if client:
            sheet = client.open_by_url(folder.spreadsheet_url)
            worksheet = sheet.worksheet(selected_month)
            raw = worksheet.get_all_values()
            
            def get_val(addr):
                if not addr: return 0
                try:
                    row, col = a1_to_rowcol(addr.strip())
                    v = raw[row-1][col-1]
                    s = str(v).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                    return float(s) if s else 0
                except: return 0

            hutang_kotor = get_val(folder.cell_hutang_kotor)
            hutang_dibayar = get_val(folder.cell_hutang_dibayar)
            hutang_sisa = hutang_kotor - hutang_dibayar

            piutang_kotor = get_val(folder.cell_piutang_kotor)
            piutang_dibayar = get_val(folder.cell_piutang_dibayar)
            piutang_sisa = piutang_kotor - piutang_dibayar
            
        # 2. Proses Tabel Data List dari df_dirty
        if df_dirty is not None and not df_dirty.empty:
            # [PERBAIKAN] Ubah logika dari 'in' menjadi '==' (sama persis)
            def check_kw(val, kw):
                if not kw: 
                    return False
                return str(kw).lower().strip() == str(val).lower().strip()
               
            # Fungsi konversi huruf kolom (A, B, C) menjadi indeks angka (0, 1, 2)
            def get_col_idx(letter):
                if not letter: return -1
                try:
                    return a1_to_rowcol(f"{letter.strip()}1")[1] - 1
                except:
                    return -1

            # Ubah huruf dari database menjadi indeks
            idx_inc = get_col_idx(folder.col_desc_inc)
            idx_exp = get_col_idx(folder.col_desc_exp)

            for _, row in df_dirty.iterrows():
                tanggal = row.get(folder.col_date, '')
                
                # [BARU] Ambil deskripsi secara mutlak menggunakan urutan posisi kolom (indeks)
                desc_inc = row.iloc[idx_inc] if 0 <= idx_inc < len(row) else ''
                desc_exp = row.iloc[idx_exp] if 0 <= idx_exp < len(row) else ''
                
                src_inc = row.get(folder.col_source_income, '')
                src_exp = row.get(folder.col_source_expense, '')
                nom_inc = row.get(folder.col_income, 0)
                nom_exp = row.get(folder.col_expense, 0)

                # TABEL HUTANG
                if check_kw(src_inc, folder.kw_hutang_masuk):
                    list_hutang.append({'tanggal': tanggal, 'desc': desc_inc, 'jenis': 'Terima Pinjaman', 'nominal': nom_inc, 'tipe': 'danger'})
                if check_kw(src_exp, folder.kw_hutang_keluar):
                    list_hutang.append({'tanggal': tanggal, 'desc': desc_exp, 'jenis': 'Sahur Hutang', 'nominal': nom_exp, 'tipe': 'success'})

                # TABEL PIUTANG
                if check_kw(src_exp, folder.kw_piutang_keluar):
                    list_piutang.append({'tanggal': tanggal, 'desc': desc_exp, 'jenis': 'Beri Pinjaman', 'nominal': nom_exp, 'tipe': 'warning'})
                if check_kw(src_inc, folder.kw_piutang_masuk):
                    list_piutang.append({'tanggal': tanggal, 'desc': desc_inc, 'jenis': 'Sahur Piutang', 'nominal': nom_inc, 'tipe': 'primary'})

    except Exception as e:
        error_msg = str(e)

    kpi = {
        'hk': f"{hutang_kotor:,.0f}", 'hd': f"{hutang_dibayar:,.0f}", 'hs': f"{hutang_sisa:,.0f}",
        'pk': f"{piutang_kotor:,.0f}", 'pd': f"{piutang_dibayar:,.0f}", 'ps': f"{piutang_sisa:,.0f}"
    }

    return render_template('dashboard_hutang.html', 
                           folder=folder, sheet_list=sheet_list, selected_month=selected_month,
                           kpi=kpi, list_hutang=list_hutang, list_piutang=list_piutang, error_msg=error_msg)

@app.route('/form-shortcuts', methods=['GET', 'POST'])
@login_required
def form_shortcuts():
    if request.method == 'POST':
        year = request.form.get('year')
        month = request.form.get('month')
        url = request.form.get('url')
        
        if year and month and url:
            new_shortcut = FormShortcut(user_id=current_user.id, year=int(year), month=month, url=url)
            db.session.add(new_shortcut)
            db.session.commit()
            flash('Shortcut Form berhasil ditambahkan!', 'success')
        return redirect(url_for('form_shortcuts'))
    
    # Ambil data dan urutkan tahun dari yang terbaru
    shortcuts = FormShortcut.query.filter_by(user_id=current_user.id).order_by(FormShortcut.year.desc()).all()
    
    # Kelompokkan berdasarkan tahun
    grouped_shortcuts = {}
    for s in shortcuts:
        if s.year not in grouped_shortcuts:
            grouped_shortcuts[s.year] = []
        grouped_shortcuts[s.year].append(s)
        
    # Logika Cerdas Tombol Kembali (Menangkap asal halaman)
    back_url = request.referrer if request.referrer and request.url not in request.referrer else url_for('home')
        
    return render_template('form_shortcuts.html', grouped=grouped_shortcuts, back_url=back_url)

@app.route('/form-shortcuts/delete/<int:id>')
@login_required
def delete_form_shortcut(id):
    shortcut = FormShortcut.query.get_or_404(id)
    if shortcut.user_id == current_user.id:
        db.session.delete(shortcut)
        db.session.commit()
        flash('Shortcut Form berhasil dihapus.', 'success')
    return redirect(url_for('form_shortcuts'))

# ==============================================================
# [BARU] ROUTES FITUR PORTOFOLIO & ASET
# ==============================================================

@app.route('/folder/<int:folder_id>/portofolio/settings', methods=['GET', 'POST'])
@login_required
def settings_portofolio(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    origin = request.args.get('origin', 'list')
    
    if request.method == 'POST':
        # Simpan Config KPI Portofolio
        folder.port_sheet_name = request.form.get('port_sheet_name', 'Portofolio')
        folder.port_cell_inc_kotor = request.form.get('port_cell_inc_kotor', '')
        folder.port_cell_exp_kotor = request.form.get('port_cell_exp_kotor', '')
        folder.port_cell_bal_kotor = request.form.get('port_cell_bal_kotor', '')
        folder.port_cell_inc_bersih = request.form.get('port_cell_inc_bersih', '')
        folder.port_cell_exp_bersih = request.form.get('port_cell_exp_bersih', '')
        folder.port_cell_bal_bersih = request.form.get('port_cell_bal_bersih', '')
        
        # Simpan Config Chart Tren Portofolio
        folder.port_col_month = request.form.get('port_col_month', 'A')
        folder.port_col_inc_kotor = request.form.get('port_col_inc_kotor', 'B')
        folder.port_col_exp_kotor = request.form.get('port_col_exp_kotor', 'C')
        folder.port_col_bal_kotor = request.form.get('port_col_bal_kotor', 'D')
        folder.port_col_inc_bersih = request.form.get('port_col_inc_bersih', 'E')
        folder.port_col_exp_bersih = request.form.get('port_col_exp_bersih', 'F')
        folder.port_col_bal_bersih = request.form.get('port_col_bal_bersih', 'G')
        try:
            folder.port_start_row = int(request.form.get('port_start_row', 2))
        except:
            folder.port_start_row = 2
            
        db.session.commit()
        flash('Konfigurasi Portofolio Tahunan berhasil disimpan.', 'success')
        return redirect(url_for('settings_portofolio', folder_id=folder.id, origin=origin))
        
    # Ambil Kategori Khusus Portofolio Tahun Ini
    cats_income = PortfolioCategoryMap.query.filter_by(folder_id=folder.id, type='income').all()
    cats_expense = PortfolioCategoryMap.query.filter_by(folder_id=folder.id, type='expense').all()
    
    return render_template('settings_portofolio.html', folder=folder, origin=origin, 
                           cats_income=cats_income, cats_expense=cats_expense)

@app.route('/portofolio/overall/settings', methods=['GET', 'POST'])
@login_required
def settings_portofolio_overall():
    config = OverallPortfolioConfig.query.filter_by(user_id=current_user.id).first()
    origin = request.args.get('origin', 'list')
    
    if request.method == 'POST':
        if not config:
            config = OverallPortfolioConfig(user_id=current_user.id)
            db.session.add(config)
            
        config.spreadsheet_url = request.form.get('url', '')
        config.sheet_name = request.form.get('sheet_name', 'Overall')
        
        # Mapping Cell
        config.cell_inc_kotor = request.form.get('cell_inc_kotor', '')
        config.cell_exp_kotor = request.form.get('cell_exp_kotor', '')
        config.cell_bal_kotor = request.form.get('cell_bal_kotor', '')
        config.cell_inc_bersih = request.form.get('cell_inc_bersih', '')
        config.cell_exp_bersih = request.form.get('cell_exp_bersih', '')
        config.cell_bal_bersih = request.form.get('cell_bal_bersih', '')
        
        # Mapping Chart
        config.col_year = request.form.get('col_year', 'A')
        config.col_inc_kotor = request.form.get('col_inc_kotor', 'B')
        config.col_exp_kotor = request.form.get('col_exp_kotor', 'C')
        config.col_bal_kotor = request.form.get('col_bal_kotor', 'D')
        config.col_inc_bersih = request.form.get('col_inc_bersih', 'E')
        config.col_exp_bersih = request.form.get('col_exp_bersih', 'F')
        config.col_bal_bersih = request.form.get('col_bal_bersih', 'G')
        try:
            config.start_row = int(request.form.get('start_row', 2))
        except:
            config.start_row = 2
            
        db.session.commit()
        flash('Konfigurasi Portofolio Overall berhasil disimpan.', 'success')
        return redirect(url_for('settings_portofolio_overall', origin=origin))
        
    cats_income = PortfolioCategoryMap.query.filter_by(user_id=current_user.id, is_overall=True, type='income').all()
    cats_expense = PortfolioCategoryMap.query.filter_by(user_id=current_user.id, is_overall=True, type='expense').all()
    
    return render_template('settings_portofolio_overall.html', config=config, origin=origin,
                           cats_income=cats_income, cats_expense=cats_expense)

@app.route('/portofolio/category/add', methods=['POST'])
@login_required
def add_portofolio_category():
    folder_id = request.form.get('folder_id')
    is_overall = request.form.get('is_overall') == 'true'
    name = request.form.get('cat_name')
    addr = request.form.get('cat_addr')
    tipe = request.form.get('cat_type')
    is_clean = True if request.form.get('is_clean') else False
    
    if name and addr and tipe:
        new_cat = PortfolioCategoryMap(
            user_id=current_user.id,
            folder_id=folder_id if folder_id else None,
            is_overall=is_overall,
            name=name, cell_addr=addr, type=tipe, is_clean=is_clean
        )
        db.session.add(new_cat)
        db.session.commit()
        flash('Kategori Portofolio berhasil ditambahkan.', 'success')
        
    if is_overall:
        return redirect(url_for('settings_portofolio_overall'))
    return redirect(url_for('settings_portofolio', folder_id=folder_id))

@app.route('/portofolio/category/delete/<int:cat_id>')
@login_required
def delete_portofolio_category(cat_id):
    cat = PortfolioCategoryMap.query.get_or_404(cat_id)
    if cat.user_id == current_user.id:
        db.session.delete(cat)
        db.session.commit()
    if cat.is_overall:
        return redirect(url_for('settings_portofolio_overall'))
    return redirect(url_for('settings_portofolio', folder_id=cat.folder_id))

@app.route('/asset/add/<int:folder_id>', methods=['POST'])
@login_required
def add_asset(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))
    
    nama_aset = request.form.get('nama_aset')
    harga_beli = request.form.get('harga_beli')
    tanggal_beli = request.form.get('tanggal_beli') # Format bebas, misal: "15 Agustus"
    
    # Otomatis cari angka tahun dari nama folder (misal: "Keuangan 2026" -> 2026)
    tahun_match = re.search(r'\d{4}', folder.name)
    tahun = int(tahun_match.group()) if tahun_match else 0
    
    if nama_aset and harga_beli and tanggal_beli:
        try:
            harga_float = float(harga_beli.replace('Rp', '').replace('.', '').replace(',', '').strip())
            new_asset = AssetData(
                user_id=current_user.id,
                nama_aset=nama_aset,
                harga_beli=harga_float,
                tanggal_beli=tanggal_beli,
                tahun=tahun
            )
            db.session.add(new_asset)
            db.session.commit()
            flash('Aset berhasil ditambahkan!', 'success')
        except ValueError:
            flash('Format harga tidak valid.', 'danger')
            
    # Nanti ini akan redirect ke Dashboard Portofolio, tapi sementara kita arahkan ke settings dulu
    # return redirect(url_for('dashboard_portofolio', folder_id=folder.id))
    return redirect(url_for('select_year', tipe='portofolio'))

@app.route('/asset/delete/<int:asset_id>')
@login_required
def delete_asset(asset_id):
    asset = AssetData.query.get_or_404(asset_id)
    if asset.user_id == current_user.id:
        db.session.delete(asset)
        db.session.commit()
        flash('Aset berhasil dihapus.', 'success')
    return redirect(request.referrer or url_for('select_year', tipe='portofolio'))

# ==============================================================
# LOGIKA BACKEND DASHBOARD PORTOFOLIO
# ==============================================================

@app.route('/folder/<int:folder_id>/portofolio/dashboard')
@login_required
def dashboard_portofolio(folder_id):
    folder = MonitorFolder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id: return redirect(url_for('home'))

    client = get_google_client()
    error_msg = None
    kpi = {}
    chart_trend = {'labels': [], 'inc_kotor': [], 'exp_kotor': [], 'bal_kotor': [], 'inc_bersih': [], 'exp_bersih': [], 'bal_bersih': []}
    pie_data = {'clean_inc': {'labels': [], 'data': []}, 'clean_exp': {'labels': [], 'data': []}, 'dirty_inc': {'labels': [], 'data': []}, 'dirty_exp': {'labels': [], 'data': []}}
    
    # Cari tahun dari nama folder (Otomatis filter aset untuk tahun ini)
    tahun_match = re.search(r'\d{4}', folder.name)
    tahun = int(tahun_match.group()) if tahun_match else 0
    assets = AssetData.query.filter_by(user_id=current_user.id, tahun=tahun).all()

    try:
        if not client: raise Exception("Akun Google belum diatur.")
        sheet = client.open_by_url(folder.spreadsheet_url)
        # Asumsi rekap tahunan ada di sheet pertama
        sheet_name = folder.port_sheet_name if folder.port_sheet_name else 'Portofolio'
        worksheet = sheet.worksheet(sheet_name)
        raw_data = worksheet.get_all_values()

        def clean_val(val):
            try:
                s = str(val).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                return float(s) if s else 0
            except: return 0

        def get_val(addr):
            if not addr: return 0
            try:
                r, c = a1_to_rowcol(addr.strip())
                return clean_val(raw_data[r-1][c-1])
            except: return 0
            
        def get_col_idx(letter):
            if not letter: return -1
            try: return a1_to_rowcol(f"{letter.strip()}1")[1] - 1
            except: return -1

        # Tarik KPI Matang
        kpi['inc_kotor'] = f"{get_val(folder.port_cell_inc_kotor):,.0f}"
        kpi['exp_kotor'] = f"{get_val(folder.port_cell_exp_kotor):,.0f}"
        kpi['bal_kotor'] = f"{get_val(folder.port_cell_bal_kotor):,.0f}"
        kpi['inc_bersih'] = f"{get_val(folder.port_cell_inc_bersih):,.0f}"
        kpi['exp_bersih'] = f"{get_val(folder.port_cell_exp_bersih):,.0f}"
        kpi['bal_bersih'] = f"{get_val(folder.port_cell_bal_bersih):,.0f}"

        # Tarik Pie Kategori
        cats = PortfolioCategoryMap.query.filter_by(folder_id=folder.id).all()
        for cat in cats:
            val = get_val(cat.cell_addr)
            if val > 0:
                prefix = 'clean_' if cat.is_clean else 'dirty_'
                tipe_str = 'inc' if cat.type == 'income' else 'exp'
                pie_data[f"{prefix}{tipe_str}"]['labels'].append(cat.name)
                pie_data[f"{prefix}{tipe_str}"]['data'].append(val)

        # Proses Tabel Tren Berdasarkan Huruf Kolom
        start_idx = max(0, folder.port_start_row - 1)
        idx_month = get_col_idx(folder.port_col_month)
        idx_ik = get_col_idx(folder.port_col_inc_kotor)
        idx_ek = get_col_idx(folder.port_col_exp_kotor)
        idx_bk = get_col_idx(folder.port_col_bal_kotor)
        idx_ib = get_col_idx(folder.port_col_inc_bersih)
        idx_eb = get_col_idx(folder.port_col_exp_bersih)
        idx_bb = get_col_idx(folder.port_col_bal_bersih)

        for i in range(start_idx, len(raw_data)):
            row = raw_data[i]
            if idx_month >= 0 and idx_month < len(row) and str(row[idx_month]).strip():
                chart_trend['labels'].append(str(row[idx_month]))
                chart_trend['inc_kotor'].append(clean_val(row[idx_ik]) if 0 <= idx_ik < len(row) else 0)
                chart_trend['exp_kotor'].append(clean_val(row[idx_ek]) if 0 <= idx_ek < len(row) else 0)
                chart_trend['bal_kotor'].append(clean_val(row[idx_bk]) if 0 <= idx_bk < len(row) else 0)
                chart_trend['inc_bersih'].append(clean_val(row[idx_ib]) if 0 <= idx_ib < len(row) else 0)
                chart_trend['exp_bersih'].append(clean_val(row[idx_eb]) if 0 <= idx_eb < len(row) else 0)
                chart_trend['bal_bersih'].append(clean_val(row[idx_bb]) if 0 <= idx_bb < len(row) else 0)

    except Exception as e:
        error_msg = str(e)

    return render_template('dashboard_portofolio.html', folder=folder, kpi=kpi, 
                           chart_trend=chart_trend, pie_data=pie_data, assets=assets, error_msg=error_msg)

@app.route('/portofolio/overall/dashboard')
@login_required
def dashboard_portofolio_overall():
    config = OverallPortfolioConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        flash('Silakan atur konfigurasi Portofolio Overall terlebih dahulu.', 'warning')
        return redirect(url_for('select_year', tipe='portofolio'))

    client = get_google_client()
    error_msg = None
    kpi = {}
    chart_trend = {'labels': [], 'inc_kotor': [], 'exp_kotor': [], 'bal_kotor': [], 'inc_bersih': [], 'exp_bersih': [], 'bal_bersih': []}
    pie_data = {'clean_inc': {'labels': [], 'data': []}, 'clean_exp': {'labels': [], 'data': []}, 'dirty_inc': {'labels': [], 'data': []}, 'dirty_exp': {'labels': [], 'data': []}}
    
    # Ambil SEMUA ASET dari seluruh tahun milik pengguna ini
    assets = AssetData.query.filter_by(user_id=current_user.id).order_by(AssetData.tahun.desc()).all()

    try:
        if not client: raise Exception("Akun Google belum diatur.")
        sheet = client.open_by_url(config.spreadsheet_url)
        worksheet = sheet.worksheet(config.sheet_name)
        raw_data = worksheet.get_all_values()

        def clean_val(val):
            try:
                s = str(val).replace('Rp', '').strip().replace('.', '').replace(',', '.')
                return float(s) if s else 0
            except: return 0

        def get_val(addr):
            if not addr: return 0
            try:
                r, c = a1_to_rowcol(addr.strip())
                return clean_val(raw_data[r-1][c-1])
            except: return 0
            
        def get_col_idx(letter):
            if not letter: return -1
            try: return a1_to_rowcol(f"{letter.strip()}1")[1] - 1
            except: return -1

        kpi['inc_kotor'] = f"{get_val(config.cell_inc_kotor):,.0f}"
        kpi['exp_kotor'] = f"{get_val(config.cell_exp_kotor):,.0f}"
        kpi['bal_kotor'] = f"{get_val(config.cell_bal_kotor):,.0f}"
        kpi['inc_bersih'] = f"{get_val(config.cell_inc_bersih):,.0f}"
        kpi['exp_bersih'] = f"{get_val(config.cell_exp_bersih):,.0f}"
        kpi['bal_bersih'] = f"{get_val(config.cell_bal_bersih):,.0f}"

        cats = PortfolioCategoryMap.query.filter_by(user_id=current_user.id, is_overall=True).all()
        for cat in cats:
            val = get_val(cat.cell_addr)
            if val > 0:
                prefix = 'clean_' if cat.is_clean else 'dirty_'
                tipe_str = 'inc' if cat.type == 'income' else 'exp'
                pie_data[f"{prefix}{tipe_str}"]['labels'].append(cat.name)
                pie_data[f"{prefix}{tipe_str}"]['data'].append(val)

        start_idx = max(0, config.start_row - 1)
        idx_year = get_col_idx(config.col_year)
        idx_ik = get_col_idx(config.col_inc_kotor)
        idx_ek = get_col_idx(config.col_exp_kotor)
        idx_bk = get_col_idx(config.col_bal_kotor)
        idx_ib = get_col_idx(config.col_inc_bersih)
        idx_eb = get_col_idx(config.col_exp_bersih)
        idx_bb = get_col_idx(config.col_bal_bersih)

        for i in range(start_idx, len(raw_data)):
            row = raw_data[i]
            if idx_year >= 0 and idx_year < len(row) and str(row[idx_year]).strip():
                chart_trend['labels'].append(str(row[idx_year]))
                chart_trend['inc_kotor'].append(clean_val(row[idx_ik]) if 0 <= idx_ik < len(row) else 0)
                chart_trend['exp_kotor'].append(clean_val(row[idx_ek]) if 0 <= idx_ek < len(row) else 0)
                chart_trend['bal_kotor'].append(clean_val(row[idx_bk]) if 0 <= idx_bk < len(row) else 0)
                chart_trend['inc_bersih'].append(clean_val(row[idx_ib]) if 0 <= idx_ib < len(row) else 0)
                chart_trend['exp_bersih'].append(clean_val(row[idx_eb]) if 0 <= idx_eb < len(row) else 0)
                chart_trend['bal_bersih'].append(clean_val(row[idx_bb]) if 0 <= idx_bb < len(row) else 0)

    except Exception as e:
        error_msg = str(e)

    return render_template('dashboard_portofolio_overall.html', config=config, kpi=kpi, 
                           chart_trend=chart_trend, pie_data=pie_data, assets=assets, error_msg=error_msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)