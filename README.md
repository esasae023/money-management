# Money Manager
Aplikasi dashboard manajemen keuangan pribadi dan portofolio berbasis web, dibangun menggunakan Python (Flask).

Berbeda dengan aplikasi keuangan tradisional yang mengunci data Anda di dalam database yang tertutup, Money Manager memanfaatkan Google Sheets API sebagai mesin data dinamis utamanya. Arsitektur ini memastikan Anda tetap memiliki 100% kepemilikan, visibilitas, dan kendali penuh atas catatan keuangan mentah Anda, sementara aplikasi ini berfungsi sebagai lapisan presentasi analitik yang canggih dan indah.

## ✨ Fitur Utama
- 📊 Monitor Anggaran Komprehensif. 

    Pantau pemasukan, pengeluaran, dan sisa saldo bulanan serta tahunan Anda melalui grafik real-time yang menawan (didukung oleh Chart.js). Beralih dengan mudah antara mode "Bersih" (operasional murni) dan "Kotor" (total keseluruhan) untuk membedah arus kas Anda.
- 🤝 Manajemen Hutang Piutang Terpisah

    Pisahkan uang operasional aktual Anda dari dana titipan atau pinjaman. Modul "Hutang Piutang" secara khusus melacak dana yang dipinjam dan dipinjamkan sehingga metrik anggaran utama Anda tetap akurat dan tidak semu.
- 💼 Pelacakan Portofolio & Aset

    Catat kepemilikan aset nyata (misalnya: logam mulia, properti) dan pantau akumulasi kekayaan jangka panjang Anda. Dilengkapi dengan "Dashboard Overall" tingkat makro yang menggabungkan seluruh spreadsheet dari berbagai tahun menjadi satu ringkasan finansial raksasa (all-time).
- 🔐 Aman & Privat
    
    Dilengkapi sistem autentikasi bawaan dengan perlindungan hashing kata sandi tingkat tinggi (Bcrypt). Menggunakan penyimpanan SQLite lokal untuk mengamankan pengaturan pengguna dan mengenkripsi kunci Google Service Account (API) agar tidak terekspos.
- 🎨 Antarmuka (UI) Modern & Responsif

    Didesain dengan estetika glassmorphism premium. Tampilan layar sepenuhnya responsif untuk desktop maupun seluler (mobile), dilengkapi fitur transisi Mode Gelap / Mode Terang (Dark/Light Mode) yang sangat mulus layaknya aplikasi native.

- 📃 Integrasi Google Form

    Karena data ditarik dari google spreadsheet, sehingga dapat kita integrasikan dengan Google form yang nantinya hasil input form akan disimpan ke dalam spreadsheet kemudian digunakan oleh aplikasi Money Manager ini.

## 🛠️ Teknologi yang Digunakan
- Backend: Python 3, Flask, SQLAlchemy, Gunicorn
- Database: SQLite (Untuk Konfigurasi & Pengguna) + Google Sheets (Untuk Data Keuangan)
- Frontend: HTML5, CSS3, Bootstrap 5, Chart.js
- Integrasi: Google Drive & Google Sheets API (gspread, oauth2client)

## 🚀 Deployment Guide
1. Persiapan Lingkungan (Pre-requisites)

    Pastikan server Anda sudah terinstal Python 3, `pip`, dan `venv`.
    ```bash
    apt update
    apt install python3 python3-venv python3-pip git -y
    ```
2. Persiapan Direktori

    Pastikan Anda menempatkan (atau melakukan clone) repositori proyek ke dalam direktori `/data/money_manager_project` sesuai dengan path konfigurasi service Anda.
    ``` bash
    mkdir /data
    cd /data
    git clone https://github.com/esasae023/money-management.git money_manager_project
    cd money_manager_project
    ```
3. Membuat dan Mengaktifkan Virtual Environment (venv)

    Gunakan `venv` untuk mengisolasi dependensi aplikasi dari sistem utama.
    ```bash
    # Membuat virtual environment dengan nama 'venv'
    python3 -m venv venv

    # (Opsional) Sesuaikan kepemilikan folder agar mudah diakses tanpa terus-menerus
    chown -R $USER:$USER venv

    # Mengaktifkan virtual environment
    source venv/bin/activate
    ```
4. Instalasi Dependensi

    Setelah virtual environment aktif (biasanya ditandai dengan awalan `(venv)` di terminal Anda), instal semua package yang dibutuhkan melalui file `requirements.txt`.
    ```bash
    # Memastikan pip versi terbaru
    pip install --upgrade pip

    # Menginstal dependensi aplikasi
    pip install -r requirements.txt
    ```

5. Konfigurasi Environment Variables (`.env`)

    Layanan `systemd` yang Anda konfigurasi memanggil file `.env`. Buat file tersebut di dalam direktori utama proyek:

    ```bash
    nano .env
    ```

    Isi dengan variabel dasar berikut (pastikan untuk mengubah nilai `SECRET_KEY` dengan kombinasi yang kuat):

    ```bash
    FLASK_SECRET_KEY='ganti_dengan_kunci_rahasia_sesi_flask_anda'
    SECRET_KEY_ENCRYPTION='ganti_dengan_kunci_enkripsi_fernet_anda'
    ```

6. Inisialisasi Database

    Selagi masih berada di dalam `venv`, jalankan inisialisasi database SQLite. Karena struktur aplikasi menggunakan pemanggilan `db.create_all()`, eksekusi perintah ini:
    ```bash
    python -c "from app import app, db; app.app_context().push(); db.create_all()"
    ```

7. Setup Systemd Service

    Keluar dari virtual environment dengan mengetikkan `deactivate`, lalu buat file service agar Gunicorn dapat berjalan di latar belakang dan otomatis menyala saat server booting.
    ```bash
    nano /etc/systemd/system/money_manager.service
    ```
    Tempelkan blok konfigurasi berikut:
    ```bash
    [Unit]
    Description=Gunicorn instance to serve Money Manager
    After=network.target

    [Service]
    User=root
    Group=www-data
    WorkingDirectory=/data/money_manager_project
    Environment="PATH=/data/money_manager_project/venv/bin"
    EnvironmentFile=/data/money_manager_project/.env
    ExecStart=/data/money_manager_project/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 -m 007 app:app

    [Install]
    WantedBy=multi-user.target
    ```

8. Menjalankan Layanan

    Muat ulang daemon untuk membaca service baru, lalu jalankan aplikasinya:

    ```bash
    systemctl daemon-reload
    systemctl start money_manager
    systemctl enable money_manager
    ```
    Untuk memastikan aplikasi sudah berjalan dengan normal tanpa error, periksa status service:
    ```bash
    systemctl status money_manager
    ```
    > Karena konfigurasi bind Gunicorn Anda disetel ke `0.0.0.0:5000`, aplikasi akan terekspos langsung ke jaringan publik jika port `5000` dibuka di level firewall. Jika Anda berencana menggunakan Reverse Proxy (seperti Nginx) di level host, disarankan untuk mengubah parameter bind menjadi `127.0.0.1:5000` untuk membatasi akses langsung.
