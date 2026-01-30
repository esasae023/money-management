from app import app
from models import db, User, MonitorFolder, GlobalSettings, CategoryMap

def hapus_user_by_username(username_target):
    with app.app_context():
        # 1. Cari User
        user = User.query.filter_by(username=username_target).first()
        
        if not user:
            print(f"❌ User '{username_target}' tidak ditemukan!")
            return

        print(f"🔄 Sedang menghapus user: {user.username} (ID: {user.id})...")

        try:
            # 2. Hapus Data Terkait (Manual Cascade Delete)
            # Agar tidak error foreign key atau meninggalkan data sampah
            
            # Hapus Global Settings milik user
            GlobalSettings.query.filter_by(user_id=user.id).delete()
            
            # Cari semua folder milik user
            folders = MonitorFolder.query.filter_by(user_id=user.id).all()
            for f in folders:
                # Hapus category map di dalam folder tersebut
                CategoryMap.query.filter_by(folder_id=f.id).delete()
                # Hapus folder itu sendiri
                db.session.delete(f)
            
            # 3. Hapus User Utama
            db.session.delete(user)
            
            # 4. Simpan Perubahan
            db.session.commit()
            print(f"✅ SUKSES: User '{username_target}' dan seluruh datanya telah dihapus.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ GAGAL: Terjadi error - {str(e)}")

if __name__ == "__main__":
    target = input("Masukkan USERNAME yang ingin dihapus: ")
    confirmation = input(f"Yakin ingin menghapus '{target}' selamanya? (y/n): ")
    
    if confirmation.lower() == 'y':
        hapus_user_by_username(target)
    else:
        print("Dibatalkan.")