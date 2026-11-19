import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_database_uri():
    # Ambil kredensial dari environment variable (bukan hardcoded demi keamanan)
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'presensi_db')

    pg_uri = os.environ.get('DATABASE_URL',
                            f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
    
    # Try to connect to PostgreSQL to see if it's running
    try:
        # Koneksi WAJIB ke database default 'postgres' terlebih dahulu untuk mengecek/membuat database baru
        conn = psycopg2.connect(
            dbname='postgres', # Jangan diubah ke presensi_db, karena jika belum ada akan error
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Mengecek apakah database presensi_db sudah ada
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'presensi_db'")
        if not cursor.fetchone():
            cursor.execute('CREATE DATABASE presensi_db')
            print("[INFO] Database presensi_db berhasil dibuat di PostgreSQL.")
            
        cursor.close()
        conn.close()
        print("[INFO] Terhubung ke PostgreSQL server.")
        return pg_uri
    except Exception as e:
        print(f"[WARNING] Gagal terhubung ke PostgreSQL ({e}). Fallback ke SQLite.")
        # Fallback to SQLite
        return 'sqlite:///./presensi_fallback.db'

class Config:
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
