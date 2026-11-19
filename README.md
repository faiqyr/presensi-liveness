# Sistem Presensi Perkuliahan Mahasiswa Berbasis Face Recognition & Liveness Detection

Sistem presensi mahasiswa berbasis pengenalan wajah dan deteksi kehidupan (*liveness detection*) untuk mengatasi kecurangan absensi seperti **titip absen** dan **spoofing** menggunakan foto atau video rekaman.

Sistem menggabungkan tiga model AI: **YOLO** untuk deteksi wajah, **MediaPipe** untuk verifikasi kedipan mata, dan **InsightFace ArcFace** untuk pengenalan identitas berbasis *embedding* 512-dimensi.

---

## Daftar Isi

- [Fitur](#fitur)
- [Arsitektur Teknologi](#arsitektur-teknologi)
- [Cara Kerja Sistem](#cara-kerja-sistem)
- [Struktur Project](#struktur-project)
- [Prasyarat](#prasyarat)
- [Instalasi & Konfigurasi](#instalasi--konfigurasi)
- [Cara Menjalankan](#cara-menjalankan)
- [Endpoint API](#endpoint-api)
- [Skema Database](#skema-database)
- [Panduan Pengujian (Alpha Testing)](#panduan-pengujian-alpha-testing)
- [Catatan Keamanan](#catatan-keamanan)
- [Troubleshooting](#troubleshooting)

---

## Fitur

- **Registrasi Wajah Multi-Pose** — Pendaftaran wajah dengan 5 pose berbeda (depan, kiri, kanan, atas, bawah) untuk meningkatkan akurasi pengenalan.
- **Liveness Detection** — Deteksi kedipan mata menggunakan Eye Aspect Ratio (EAR) via MediaPipe Face Mesh. Wajib 2 kedipan untuk lulus verifikasi.
- **Face Recognition** — InsightFace ArcFace mengekstrak *embedding* 512-D dan mencocokkan dengan *Cosine Similarity* (threshold ≥ 0.50).
- **Real-time Streaming** — Presensi berlangsung real-time via Flask-SocketIO dengan ~5 FPS.
- **Anti-Spoofing 2D** — Foto cetak dan video rekaman ditolak karena tidak dapat mengedipkan mata.
- **Dashboard Statistik** — Menampilkan total, hadir, dan alpha secara real-time.
- **Auto-create Database** — Sistem otomatis membuat database PostgreSQL `presensi_db` jika belum ada.
- **SQLite Fallback** — Jika PostgreSQL tidak tersedia, sistem otomatis beralih ke SQLite.

---

## Arsitektur Teknologi

| Komponen | Teknologi |
|----------|-----------|
| **Backend** | Python 3.10+, Flask 3.0.3, Flask-SocketIO 5.3.6 |
| **Frontend** | React 19, Vite, Tailwind CSS 4 |
| **Database** | PostgreSQL (fallback: SQLite) |
| **AI - Deteksi Wajah** | YOLOv11 / YOLOv8 (Ultralytics) |
| **AI - Liveness** | MediaPipe Face Mesh (Google) |
| **AI - Pengenalan** | InsightFace ArcFace (buffalo_l model) |
| **Real-time** | Flask-SocketIO (polling transport) |

### Pipeline AI per Frame

```
Frame Kamera
    │
    ▼
┌──────────────────────────────────────────────┐
│  1. YOLO (setiap 15 frame)                    │
│     → Konfirmasi ada wajah/person            │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  2. MediaPipe Face Mesh (setiap frame)        │
│     → Bounding box wajah presisi             │
│     → Hitung EAR (Eye Aspect Ratio)           │
│     → State machine: closed → open = 1 blink  │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  3. InsightFace ArcFace (sekali per sesi)     │
│     → Ekstrak embedding 512-D                 │
│     → Cosine Similarity vs DB (≥ 0.50)        │
└──────────────────┬───────────────────────────┘
                   ▼
              Hasil: SUCCESS / UNKNOWN_FACE / NEED_BLINK
```

---

## Struktur Project

```
presensi-liveness/
├── run.py                    # Entry point - jalankan backend + frontend
├── requirements.txt          # Dependensi Python
├── .env.example              # Template environment variable
├── .gitignore
│
├── backend/
│   ├── app.py                # Server Flask + SocketIO + REST API (AKTIF)
│   ├── ai_engine.py          # Pipeline AI: YOLO + MediaPipe + InsightFace
│   ├── config.py             # Konfigurasi database (env-based)
│   ├── models.py             # Model database SQLAlchemy
│   ├── database.py           # (Legacy) versi FastAPI/SQLite - tidak digunakan
│   ├── main.py               # (Legacy) versi FastAPI - tidak digunakan
│   └── test_liveness.py       # Script testing liveness detection standalone
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx          # Entry point React
        ├── App.jsx          # Navigasi antar halaman
        ├── PresensiPage.jsx  # Halaman presensi real-time (WebSocket)
        ├── RegisterPage.jsx  # Halaman registrasi wajah 5-pose
        ├── App.css
        └── index.css
```

---

## Prasyarat

### Software

- **Python** 3.10 atau lebih baru
- **Node.js** 18+ dan npm
- **PostgreSQL** 14+ (opsional — ada fallback SQLite)
- **Git**

### Hardware (Disarankan)

- **Webcam** (internal atau eksternal)
- **RAM** 8 GB+ (InsightFace butuh memori cukup)
- **GPU** opsional (CUDA untuk ONNX Runtime GPU — mempercepat ekstraksi embedding)

---

## Instalasi & Konfigurasi

### 1. Clone repository

```bash
git clone https://github.com/faiqyr/presensi-liveness.git
cd presensi-liveness
```

### 2. Install dependensi Python (Backend)

```bash
pip install -r requirements.txt
```

InsightFace dan ONNX Runtime tidak ada di `requirements.txt` dan harus diinstall manual:

```bash
# Untuk CPU
pip install insightface onnxruntime

# Untuk GPU (CUDA)
pip install insightface onnxruntime-gpu
```

### 3. Install dependensi Node.js (Frontend)

```bash
cd frontend
npm install
cd ..
```

### 4. Konfigurasi Environment Variable

Copy template `.env.example` menjadi `.env`:

**Linux/Mac:**
```bash
cp .env.example .env
```

**Windows (cmd):**
```cmd
copy .env.example .env
```

Lalu edit file `.env` dan isi dengan kredensial PostgreSQL Anda:

```env
DB_USER=postgres
DB_PASSWORD=password_postgres_anda
DB_HOST=localhost
DB_PORT=5432
DB_NAME=presensi_db
SECRET_KEY=generate_random_key_disini
```

> Jika PostgreSQL tidak berjalan, sistem otomatis fallback ke SQLite (`presensi_fallback.db`). Anda tidak perlu melakukan konfigurasi apapun untuk mode SQLite.

> Generate secret key acak: `python -c "import secrets; print(secrets.token_hex(32))"`

### 5. Setup Database PostgreSQL (Opsional)

Sistem akan otomatis membuat database `presensi_db` jika belum ada. Pastikan:
- PostgreSQL service berjalan
- Kredensial di `.env` sudah benar
- User memiliki permission untuk CREATE DATABASE

---

## Cara Menjalankan

```bash
python run.py
```

Perintah ini akan:
1. Memulai backend Flask di **port 5000**
2. Menunggu 3 detik agar backend stabil
3. Memulai frontend Vite dev server di **port 5173**
4. Membuka browser: **http://localhost:5173**

Tekan `Ctrl+C` di terminal untuk menghentikan kedua service.

### Menjalankan secara terpisah (alternatif)

**Backend saja:**
```bash
python -m backend.app
```

**Frontend saja:**
```bash
cd frontend
npm run dev
```

---

## Endpoint API

### REST API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/admin/register-face` | Registrasi wajah mahasiswa (5 foto) |
| `POST` | `/api/dosen/pertemuan` | Tambah jadwal pertemuan baru |
| `GET` | `/api/dosen/statistik-presensi` | Statistik kehadiran (total, hadir, alpha) |

### Contoh Request

**Registrasi Wajah:**
```json
POST /api/admin/register-face
Content-Type: application/json

{
  "nim": "2021001",
  "nama": "John Doe",
  "kelas_id": 1,
  "images_base64": [
    "data:image/jpeg;base64,/9j/4AAQ...",
    "data:image/jpeg;base64,/9j/4AAQ...",
    "data:image/jpeg;base64,/9j/4AAQ...",
    "data:image/jpeg;base64,/9j/4AAQ...",
    "data:image/jpeg;base64,/9j/4AAQ..."
  ]
}
```

**Tambah Pertemuan:**
```json
POST /api/dosen/pertemuan
Content-Type: application/json

{
  "kelas_matkul_id": 1,
  "jam_mulai": "08:00:00",
  "tanggal": "2026-11-19"
}
```

**Statistik Presensi:**
```
GET /api/dosen/statistik-presensi?pertemuan_id=1
```

### WebSocket (Socket.IO)

| Event | Arah | Namespace | Deskripsi |
|-------|------|-----------|-----------|
| `connect` | Client → Server | `/api/presensi/stream` | Inisialisasi sesi presensi |
| `stream_frame` | Client → Server | `/api/presensi/stream` | Kirim frame kamera (base64 JPEG) |
| `presensi_result` | Server → Client | `/api/presensi/stream` | Hasil deteksi per frame |

**Response `presensi_result`:**
```json
{
  "status": "SUCCESS",
  "blink_counter": 2,
  "bbox": [120, 80, 280, 320],
  "yolo_confirmed": true,
  "name": "John Doe",
  "nim": "2021001",
  "message": "Presensi Sukses: John Doe"
}
```

**Status yang mungkin:**

| Status | Arti |
|--------|------|
| `MENUNGGU` | Menunggu deteksi dimulai |
| `NO_FACE_DETECTED` | Tidak ada wajah di frame |
| `LIVENESS_FAILED_NEED_BLINK` | Wajah terdeteksi tapi belum kedip 2x |
| `UNKNOWN_FACE` | Sudah kedip 2x tapi wajah tidak terdaftar |
| `SUCCESS` | Lulus liveness + wajah dikenali + presensi tercatat |
| `ALREADY_ATTENDED` | Sudah absen untuk pertemuan ini |
| `ERROR` | Error pemrosesan frame |

---

## Skema Database

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  mahasiswa  │     │ wajah_mahasiswa  │     │    presensi     │
├─────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)     │◄──┐ │ id (PK)          │     │ id (PK)         │
│ nim (uniq)  │   └─│ mahasiswa_id (FK)│  ┌─►│ mahasiswa_id(FK)│
│ nama        │     │ face_embedding   │  │  │ pertemuan_id(FK)│
└─────────────┘     │   (JSON 512-D)   │  │  │ waktu_hadir     │
                    └──────────────────┘  │  │ status         │
                                          │  └─────────────────┘
┌──────────────────┐                      │        ▲
│ kelas_mata_kuliah│                      │        │
├──────────────────┤     ┌──────────────┐ │        │
│ id (PK)          │◄──┐ │  pertemuan   │ │        │
│ nama_kelas       │   └─│ id (PK)      │ ├────────┘
│ nama_matkul      │     │ kelas_matkul │ │
└──────────────────┘     │   _id (FK)   │ │
                         │ tanggal      │ │
┌─────────────┐          │ jam_mulai    │ │
│   dosen     │          └──────────────┘ │
├─────────────┤                           │
│ id (PK)     │                           │
│ nidn (uniq) │                           │
│ nama        │                           │
│ email       │                           │
│ password    │                           │
└─────────────┘                           │
                                          │
┌─────────────┐                           │
│   admin     │                           │
├─────────────┤                           │
│ id (PK)     │                           │
│ username    │                           │
│ password    │                           │
└─────────────┘
```

**Tabel utama:**

| Tabel | Deskripsi |
|-------|-----------|
| `mahasiswa` | Data mahasiswa (NIM, nama) |
| `wajah_mahasiswa` | Embedding 512-D wajah (JSON) |
| `kelas_mata_kuliah` | Kelas & mata kuliah |
| `pertemuan` | Jadwal pertemuan per kelas |
| `presensi` | Catatan kehadiran mahasiswa per pertemuan |
| `admin` | Akun admin |
| `dosen` | Akun dosen |

---

## Panduan Pengujian (Alpha Testing)

Pengujian dilakukan dengan metode **Black Box Testing** yang difokuskan pada uji validitas skenario keamanan (*Anti-Spoofing*).

> Pastikan Anda sudah meregistrasikan wajah mahasiswa melalui halaman "Registrasi Wajah" atau via API `/api/admin/register-face` sebelum pengujian.

### Skenario 1: Presensi Normal (Harus Berhasil)

**Kondisi:** Mahasiswa berdiri di depan kamera secara langsung.

**Langkah:**
1. Klik tombol "Mulai Deteksi" di halaman presensi.
2. Saat wajah terdeteksi, lakukan kedipan mata secara natural minimal 2 kali.
3. Indikator kedipan akan bertambah hingga mencapai 2/2.

**Ekspektasi:** Jika vektor wajah cocok (Similarity ≥ 0.50), bounding box berubah hijau dengan status "Presensi Berhasil" dan kehadiran tercatat di statistik.

### Skenario 2: Spoofing Menggunakan Foto/Video (Harus Ditolak)

**Kondisi:** Mengelabui sistem menggunakan foto tercetak atau pemutaran video wajah di layar HP.

**Langkah:**
1. Arahkan foto cetak / layar HP berisi video wajah ke depan webcam.
2. Tunggu 10-15 detik.

**Ekspektasi:** Wajah mungkin dikenali YOLO (muncul bounding box), namun indikator kedipan tetap `0/2` dan status tertahan pada instruksi kedip. Sistem tidak akan melanjutkan ke pengenalan wajah. Aman dari bypass 2D.

### Skenario 3: Penggunaan Aksesoris (Harus Berhasil)

**Kondisi:** Mahasiswa presensi langsung dengan aksesoris seperti kacamata transparan, topi, atau jilbab (yang tidak menutupi area mata).

**Langkah:**
1. Kenakan kacamata (non-hitam) atau topi.
2. Lakukan presensi dan berkedip 2 kali.

**Ekspektasi:** Mata masih ter-track MediaPipe. Kedipan mencapai 2/2. InsightFace ArcFace mampu mengenali struktur wajah meskipun sebagian tertutup aksesoris. Status "Presensi Berhasil".

---

## Catatan Keamanan

- **Kredensial database** dibaca dari environment variable (`.env`), bukan hardcoded di source code.
- File `.env` sudah di-exclude oleh `.gitignore` dan tidak akan ter-push ke GitHub.
- **Secret key Flask** juga menggunakan environment variable.
- Model weight YOLO (`*.pt`) di-exclude dari git — diunduh otomatis oleh Ultralytics saat pertama kali dijalankan.
- File `.env.example` hanya berisi template tanpa kredensial nyata.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'insightface'` | Jalankan `pip install insightface onnxruntime` |
| Kamera tidak terbuka | Pastikan tidak ada aplikasi lain yang memakai webcam (Zoom, browser, dll) |
| `psycopg2.OperationalError: could not connect to server` | PostgreSQL belum berjalan. Sistem akan fallback ke SQLite otomatis |
| SocketIO error 400 di console | Normal — frontend sengaja pakai transport `polling` untuk stabilitas |
| Wajah tidak dikenali (UNKNOWN_FACE) | Pastikan sudah registrasi wajah terlebih dahulu dan cek pencahayaan |
| Kedipan tidak terdeteksi | Pastikan wajah terlihat jelas dan pencahayaan cukup. Jangan berkedip terlalu cepat |
| `yolov11n.pt not found` | Sistem otomatis fallback ke `yolov8n.pt` yang sudah ada |
| Port 5000/5173 sudah dipakai | Tutup aplikasi yang memakai port tersebut, atau ubah port di `app.py` / `vite.config.js` |

---

## Lisensi

Project ini dibuat untuk tujuan penelitian dan pengembangan akademik.
