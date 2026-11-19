# Sistem Presensi Perkuliahan Mahasiswa Berbasis Face Recognition & Liveness Detection

Sistem ini dikembangkan berdasarkan pendekatan dari jurnal penelitian untuk mengatasi kecurangan absensi (*titip absen*) dan *spoofing* menggunakan foto/video.

## Arsitektur Teknologi
1. **Backend:** Python + Flask + Flask-SocketIO (Real-time Stream)
2. **Frontend:** ReactJS + Vite + Tailwind CSS
3. **Database:** MySQL via Flask-SQLAlchemy
4. **AI Core:**
   - **YOLOv11**: Pendeteksian wajah akurat & cepat.
   - **MediaPipe**: Liveness detection (EAR) via deteksi 2 kedipan mata.
   - **InsightFace**: Fitur ekstrasi 512-D embedding dan *Cosine Similarity*.

---

## Panduan Pengujian Sistem (Alpha Testing)

Pengujian sistem dilakukan dengan menggunakan metode **Black Box Testing** yang difokuskan pada uji validitas skenario keamanan (*Anti-Spoofing*). 

Pastikan Anda sudah meregistrasikan wajah Anda (menggunakan Postman ke `/api/admin/register-face` atau menambahkannya secara manual) sebelum melakukan pengujian ini.

### 1. Skenario 1: Presensi Normal (Harus Berhasil)
* **Kondisi:** Mahasiswa berdiri di depan kamera secara langsung.
* **Langkah Uji:** 
  1. Klik tombol "Mulai Presensi" di frontend ReactJS.
  2. Saat wajah terdeteksi, perhatikan instruksi "Silakan Berkedip" berwarna kuning.
  3. Lakukan kedipan mata secara natural minimal 2 kali.
* **Ekspektasi Hasil:** Indikator kedipan bertambah hingga mencapai 2/2. Jika vektor wajah cocok (Similarity >= 0.65), maka kotak akan berubah menjadi warna hijau dengan status "**Akses Diterima**" dan riwayat tercatat di log tabel.

### 2. Skenario 2: Spoofing Menggunakan Foto/Video Rekaman (Harus Ditolak)
* **Kondisi:** Mengelabui sistem menggunakan foto tercetak wajah mahasiswa atau pemutaran video wajah mahasiswa di layar HP.
* **Langkah Uji:**
  1. Arahkan foto cetak / layar HP berisi video wajah ke depan webcam laptop.
  2. Tunggu selama beberapa detik (10-15 detik).
* **Ekspektasi Hasil:** Wajah *mungkin* dikenali oleh YOLOv11 (muncul Bounding Box), namun sistem **tidak akan pernah** melanjutkan ke proses pengenalan wajah. Indikator kedipan tetap `0/2` dan status akan tertahan pada "**Silakan Berkedip**". Sistem aman dari *bypass* 2D.

### 3. Skenario 3: Penggunaan Aksesoris (Harus Berhasil)
* **Kondisi:** Mahasiswa melakukan presensi secara langsung dengan menggunakan aksesoris tambahan seperti kacamata transparan, topi, atau jilbab (yang tidak menutupi area mata).
* **Langkah Uji:**
  1. Kenakan kacamata (non-hitam) atau topi.
  2. Lakukan presensi dan berkedip 2 kali di depan kamera.
* **Ekspektasi Hasil:** Mata masih dapat di-*track* oleh MediaPipe. Indikator kedipan berhasil mencapai 2/2. Fitur ArcFace dari InsightFace mampu mengenali struktur dasar wajah meskipun sebagian kecil tertutup aksesoris pinggir. Status menjadi "**Akses Diterima**".

---

## Cara Menjalankan Aplikasi
1. Pastikan database PostgreSQL sudah berjalan.
2. Copy `.env.example` menjadi `.env` lalu isi kredensial database Anda:
   ```bash
   cp .env.example .env
   ```
   Edit file `.env` dan sesuaikan `DB_PASSWORD`, `DB_USER`, dll. (Jika PostgreSQL tidak berjalan, sistem otomatis fallback ke SQLite.)
3. Install dependensi Python: `pip install -r requirements.txt` (serta `pip install insightface onnxruntime`).
4. Install dependensi frontend: `cd frontend && npm install && cd ..`
5. Jalankan perintah:
   ```bash
   python run.py
   ```
6. Akses antarmuka sistem di browser Anda melalui alamat: `http://localhost:5173`
