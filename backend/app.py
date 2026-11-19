import os
import cv2
import json
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime

from .config import Config
from .models import db, Admin, Dosen, Mahasiswa, KelasMataKuliah, Pertemuan, WajahMahasiswa, Presensi
from .ai_engine import get_face_embedding, get_average_embedding, process_frame

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize Database
db.init_app(app)

with app.app_context():
    db.create_all()
    # Auto-create default pertemuan jika belum ada (agar tidak FK error saat testing)
    if not Pertemuan.query.first():
        default_kelas = KelasMataKuliah.query.first()
        if not default_kelas:
            default_kelas = KelasMataKuliah(nama_kelas="IF-A", nama_matkul="Kecerdasan Buatan")
            db.session.add(default_kelas)
            db.session.commit()
        default_pertemuan = Pertemuan(
            kelas_matkul_id=default_kelas.id,
            tanggal=datetime.utcnow().date(),
            jam_mulai=datetime.strptime("08:00:00", "%H:%M:%S").time()
        )
        db.session.add(default_pertemuan)
        db.session.commit()
        print(f"[DB] Auto-created default Pertemuan ID={default_pertemuan.id}")

# Utility to decode base64 image
def decode_base64_image(base64_string: str):
    try:
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

# ==========================================
# 1. API: Register Face (Admin)
# ==========================================
@app.route('/api/admin/register-face', methods=['POST'])
def register_face():
    try:
        data = request.json
        nim = data.get('nim')
        nama = data.get('nama')
        kelas_id = data.get('kelas_id') 
        images_base64 = data.get('images_base64')
        
        if not all([nim, nama, images_base64]) or not isinstance(images_base64, list):
            return jsonify({"status": "error", "message": "NIM, Nama, dan gambar diperlukan"}), 400
            
        imgs = []
        for b64 in images_base64:
            img = decode_base64_image(b64)
            if img is not None:
                imgs.append(img)
                
        if not imgs:
            return jsonify({"status": "error", "message": "Format gambar tidak valid"}), 400
            
        embedding_list = get_average_embedding(imgs)
        if embedding_list is None:
            return jsonify({"status": "error", "message": "Wajah tidak terdeteksi pada salah satu gambar atau model gagal"}), 400
            
        mahasiswa = Mahasiswa.query.filter_by(nim=nim).first()
        if not mahasiswa:
            mahasiswa = Mahasiswa(nim=nim, nama=nama)
            db.session.add(mahasiswa)
            db.session.commit()
            
        wajah = WajahMahasiswa.query.filter_by(mahasiswa_id=mahasiswa.id).first()
        if wajah:
            wajah.face_embedding = embedding_list
        else:
            wajah = WajahMahasiswa(mahasiswa_id=mahasiswa.id, face_embedding=embedding_list)
            db.session.add(wajah)
            
        db.session.commit()
        return jsonify({"status": "success", "message": f"Wajah untuk {nama} ({nim}) berhasil didaftarkan dengan {len(imgs)} pose."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 2. API: Tambah Pertemuan (Dosen)
# ==========================================
@app.route('/api/dosen/pertemuan', methods=['POST'])
def tambah_pertemuan():
    try:
        data = request.json
        kelas_matkul_id = data.get('kelas_matkul_id')
        jam_mulai = data.get('jam_mulai')
        tanggal = data.get('tanggal')
        
        if not all([kelas_matkul_id, jam_mulai]):
            return jsonify({"status": "error", "message": "Kelas Matkul ID dan jam mulai diperlukan"}), 400
            
        jam_obj = datetime.strptime(jam_mulai, "%H:%M:%S").time()
        tgl_obj = datetime.strptime(tanggal, "%Y-%m-%d").date() if tanggal else datetime.utcnow().date()
            
        pertemuan = Pertemuan(kelas_matkul_id=kelas_matkul_id, tanggal=tgl_obj, jam_mulai=jam_obj)
        db.session.add(pertemuan)
        db.session.commit()
        
        return jsonify({"status": "success", "message": "Jadwal pertemuan berhasil ditambahkan.", "pertemuan_id": pertemuan.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 2.5 API: Statistik Presensi
# ==========================================
@app.route('/api/dosen/statistik-presensi', methods=['GET'])
def statistik_presensi():
    try:
        pertemuan_id = request.args.get('pertemuan_id')
        total_mahasiswa = Mahasiswa.query.count()
        
        if pertemuan_id:
            hadir = Presensi.query.filter_by(pertemuan_id=pertemuan_id).count()
        else:
            hadir = Presensi.query.count()
            
        alpha = max(0, total_mahasiswa - hadir)
            
        return jsonify({
            "status": "success",
            "data": {"total": total_mahasiswa, "hadir": hadir, "alpha": alpha}
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. WebSocket: Presensi Real-Time
# ==========================================
client_sessions = {}

# Embedding cache (refresh setiap 30 detik)
_embedding_cache = None
_embedding_cache_time = 0

def get_all_registered_embeddings():
    global _embedding_cache, _embedding_cache_time
    import time
    now = time.time()
    if _embedding_cache is not None and (now - _embedding_cache_time) < 30:
        return _embedding_cache
    records = WajahMahasiswa.query.all()
    results = []
    for r in records:
        try:
            results.append({'mahasiswa_id': r.mahasiswa_id, 'embedding': r.face_embedding})
        except:
            pass
    _embedding_cache = results
    _embedding_cache_time = now
    return results

@socketio.on('connect', namespace='/api/presensi/stream')
def on_connect():
    sid = request.sid
    client_sessions[sid] = {
        'blink_counter': 0,
        'eye_closed_frames': 0,
        'current_matched_id': None,
        'frame_count': 0,
        'pertemuan_id': request.args.get('pertemuan_id')
    }
    global _embedding_cache_time
    _embedding_cache_time = 0
    print(f"Client {sid} connected.")

@socketio.on('disconnect', namespace='/api/presensi/stream')
def on_disconnect():
    sid = request.sid
    if sid in client_sessions:
        del client_sessions[sid]
    print(f"Client {sid} disconnected.")

@socketio.on('stream_frame', namespace='/api/presensi/stream')
def handle_stream_frame(data):
    sid = request.sid
    session_data = client_sessions.get(sid)
    if not session_data:
        return
        
    pertemuan_id = session_data.get('pertemuan_id')
    
    try:
        base64_img = data.get('image', '')
        img = decode_base64_image(base64_img)
        
        if img is None:
            emit('presensi_result', {"status": "ERROR", "message": "Frame tidak valid"})
            return
        
        # Resize agar proses AI lebih cepat
        img_h, img_w = img.shape[:2]
        if img_w > 480:
            scale = 480.0 / img_w
            img = cv2.resize(img, (480, int(img_h * scale)))

        registered_embeddings = get_all_registered_embeddings()
        
        # Increment frame counter
        frame_count = session_data['frame_count']
        session_data['frame_count'] = frame_count + 1
        
        # Proses AI (YOLO hanya tiap 15 frame, MediaPipe tiap frame)
        status, m_id, bbox, blink_counter, eye_closed_frames, yolo_confirmed = process_frame(
            img, 
            session_data['blink_counter'], 
            session_data['eye_closed_frames'], 
            registered_embeddings,
            session_data['current_matched_id'],
            frame_count
        )
        
        # Update session
        session_data['blink_counter'] = blink_counter
        session_data['eye_closed_frames'] = eye_closed_frames
        if m_id is not None:
            session_data['current_matched_id'] = m_id
        
        response = {
            "status": status,
            "blink_counter": blink_counter,
            "bbox": bbox,
            "yolo_confirmed": yolo_confirmed
        }
        
        # Populate nama/NIM segera
        mahasiswa = None
        if m_id is not None:
            mahasiswa = db.session.get(Mahasiswa, m_id)
            if mahasiswa:
                response["name"] = mahasiswa.nama
                response["nim"] = mahasiswa.nim
        
        # Jika berhasil (kedipan 2x + wajah dikenali)
        if status == "SUCCESS" and m_id is not None and mahasiswa:
            cek_presensi = None
            pid = int(pertemuan_id) if pertemuan_id else 1
            
            cek_presensi = Presensi.query.filter_by(
                mahasiswa_id=m_id, 
                pertemuan_id=pid
            ).first()
                
            if not cek_presensi:
                presensi_baru = Presensi(
                    mahasiswa_id=m_id, 
                    pertemuan_id=pid, 
                    status="Hadir"
                )
                db.session.add(presensi_baru)
                db.session.commit()
                response["message"] = f"Presensi Sukses: {mahasiswa.nama}"
            else:
                response["status"] = "ALREADY_ATTENDED"
                response["message"] = f"{mahasiswa.nama} - sudah absen"
            
            session_data['blink_counter'] = 0
            session_data['eye_closed_frames'] = 0
                
        emit('presensi_result', response)
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        emit('presensi_result', {"status": "ERROR", "message": str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
