from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Dosen(db.Model):
    __tablename__ = 'dosen'
    id = db.Column(db.Integer, primary_key=True)
    nidn = db.Column(db.String(20), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class KelasMataKuliah(db.Model):
    __tablename__ = 'kelas_mata_kuliah'
    id = db.Column(db.Integer, primary_key=True)
    nama_kelas = db.Column(db.String(50), nullable=False)
    nama_matkul = db.Column(db.String(100), nullable=False)

class Mahasiswa(db.Model):
    __tablename__ = 'mahasiswa'
    id = db.Column(db.Integer, primary_key=True)
    nim = db.Column(db.String(20), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    
    # Relasi ke tabel wajah
    wajah = db.relationship('WajahMahasiswa', backref='mahasiswa', lazy=True, cascade="all, delete-orphan")

class WajahMahasiswa(db.Model):
    __tablename__ = 'wajah_mahasiswa'
    id = db.Column(db.Integer, primary_key=True)
    mahasiswa_id = db.Column(db.Integer, db.ForeignKey('mahasiswa.id'), nullable=False)
    # Menyimpan 512-D vector embedding dari InsightFace dalam format teks/JSON
    face_embedding = db.Column(db.JSON, nullable=False) 

class Pertemuan(db.Model):
    __tablename__ = 'pertemuan'
    id = db.Column(db.Integer, primary_key=True)
    kelas_matkul_id = db.Column(db.Integer, db.ForeignKey('kelas_mata_kuliah.id'), nullable=False)
    tanggal = db.Column(db.Date, default=datetime.utcnow().date)
    jam_mulai = db.Column(db.Time, nullable=False)

class Presensi(db.Model):
    __tablename__ = 'presensi'
    id = db.Column(db.Integer, primary_key=True)
    mahasiswa_id = db.Column(db.Integer, db.ForeignKey('mahasiswa.id'), nullable=False)
    pertemuan_id = db.Column(db.Integer, db.ForeignKey('pertemuan.id'), nullable=False)
    waktu_hadir = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Hadir") # Hadir, Izin, Alpa
