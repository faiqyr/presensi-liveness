import os
import cv2
import math
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
from scipy.spatial import distance as dist

# ==========================================
# 1. INITIALIZATION
# ==========================================
# Inisialisasi model YOLOv11 untuk deteksi wajah (Bounding Box)
# Catatan: Akan otomatis mendownload weights jika belum ada di direktori lokal.
print("Loading YOLOv11 Face model...")
try:
    yolo_model = YOLO('yolov11n-face.pt') 
except Exception:
    yolo_model = YOLO('yolov8n.pt') # Fallback ke YOLOv8 standar

# Inisialisasi MediaPipe Face Mesh untuk Facial Landmarks (mendapatkan titik mata)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Indeks landmarks untuk mata dari MediaPipe Face Mesh
# Mata Kiri (Left Eye) dan Mata Kanan (Right Eye) berdasarkan dokumentasi MediaPipe
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]

# Threshold & Parameter Liveness
EAR_THRESHOLD = 0.22  # Batas nilai EAR untuk mendeteksi mata tertutup (bisa disesuaikan)
CONSECUTIVE_FRAMES = 2 # Mata harus tertutup selama sekian frame untuk dihitung 1 kedipan
blink_counter = 0
total_blinks = 0

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def calculate_ear(eye_points):
    """
    Menghitung Eye Aspect Ratio (EAR) untuk satu mata.
    eye_points: List berisi 6 koordinat (x, y) dari landmark mata.
    """
    # Menghitung jarak vertikal antara kelopak mata atas dan bawah
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
    # Menghitung jarak horizontal antara sudut mata
    C = dist.euclidean(eye_points[0], eye_points[3])
    
    # Menghitung EAR
    ear = (A + B) / (2.0 * C)
    return ear

def get_landmarks_coords(landmarks, width, height, indices):
    """ Mengonversi koordinat landmark dari persentase menjadi piksel """
    return [(int(landmarks.landmark[i].x * width), int(landmarks.landmark[i].y * height)) for i in indices]


# ==========================================
# 3. MAIN LOOP (CAMERA)
# ==========================================
cap = None
# Coba buka kamera dari index 0 sampai 2, menggunakan CAP_DSHOW untuk Windows
for cam_idx in range(3):
    print(f"Mencoba membuka kamera index {cam_idx}...")
    temp_cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(cam_idx)
    if temp_cap.isOpened():
        ret, frame = temp_cap.read()
        if ret and frame is not None:
            cap = temp_cap
            print(f"✅ Berhasil terhubung ke kamera index {cam_idx}")
            break
    temp_cap.release()

if cap is None or not cap.isOpened():
    print("❌ ERROR: Gagal membaca frame kamera.")
    print("⚠️ PASTIKAN: 1. Kamera tidak sedang dipakai aplikasi lain (Browser/Zoom). 2. Kamera tersambung.")
    exit(1)

print("Starting Camera... Press 'q' to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Kamera terputus.")
        break
        
    frame = cv2.flip(frame, 1) # Flip horizontal agar seperti cermin
    h, w, _ = frame.shape
    
    # A. Face Detection menggunakan YOLO
    results = yolo_model(frame, verbose=False)
    
    # Flag untuk mengecek apakah ada wajah
    face_detected = False
    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            
            # Jika confidence cukup tinggi, gambar bounding box
            if conf > 0.5:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"Face {conf:.2f}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                face_detected = True

    # B. Liveness Detection menggunakan MediaPipe (EAR)
    # Kami menggunakan Mediapipe di atas seluruh frame karena lebih presisi 
    # menangkap landmark mata dibanding YOLO standard face model.
    if face_detected:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = face_mesh.process(rgb_frame)
        
        if mesh_results.multi_face_landmarks:
            for face_landmarks in mesh_results.multi_face_landmarks:
                # Dapatkan koordinat mata kiri dan kanan
                left_eye_coords = get_landmarks_coords(face_landmarks, w, h, LEFT_EYE_IDX)
                right_eye_coords = get_landmarks_coords(face_landmarks, w, h, RIGHT_EYE_IDX)
                
                # Hitung EAR masing-masing mata, lalu rata-ratakan
                left_ear = calculate_ear(left_eye_coords)
                right_ear = calculate_ear(right_eye_coords)
                ear = (left_ear + right_ear) / 2.0
                
                # Visualisasi titik mata
                for pt in left_eye_coords + right_eye_coords:
                    cv2.circle(frame, pt, 2, (0, 255, 0), -1)
                
                # Logika Penghitungan Kedipan (Blink Detection)
                if ear < EAR_THRESHOLD:
                    blink_counter += 1
                else:
                    if blink_counter >= CONSECUTIVE_FRAMES:
                        total_blinks += 1
                    blink_counter = 0 # Reset
                
                # Cek status liveness
                liveness_status = "LIVENESS VERIFIED" if total_blinks >= 1 else "BLINK YOUR EYES!"
                color = (0, 255, 0) if total_blinks >= 1 else (0, 0, 255)
                
                # Tampilkan info di layar
                cv2.putText(frame, f"EAR: {ear:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"Blinks: {total_blinks}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, liveness_status, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
    cv2.imshow("Presensi - Liveness Test", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
