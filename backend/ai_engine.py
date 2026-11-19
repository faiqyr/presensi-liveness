import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None

# ==========================================
# INITIALIZATION
# ==========================================

# 1. YOLOv11 untuk Face/Person Detection (dijalankan TIDAK setiap frame)
print("[AI Engine] Loading YOLO model...")
try:
    yolo_model = YOLO('yolov11n.pt')
except Exception:
    yolo_model = YOLO('yolov8n.pt')
print("[AI Engine] YOLO model loaded.")

# 2. MediaPipe Face Mesh: RINGAN, dijalankan SETIAP frame
#    Untuk blink detection (EAR) dan bounding box wajah yang presisi.
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 3. InsightFace untuk Face Recognition (dijalankan SEKALI per sesi)
if FaceAnalysis:
    insight_app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
    insight_app.prepare(ctx_id=0, det_size=(640, 640))
    print("[AI Engine] InsightFace loaded.")
else:
    print("[AI Engine] WARNING: InsightFace tidak terinstal.")
    insight_app = None

# ==========================================
# KONSTANTA
# ==========================================
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Landmark kontur wajah untuk bounding box presisi
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

EAR_THRESHOLD = 0.23

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def _dist(a, b):
    return np.linalg.norm(np.array(a, dtype=np.float64) - np.array(b, dtype=np.float64))

def calculate_ear(eye_points):
    p0, p1, p2, p3, p4, p5 = eye_points
    vertical_1 = _dist(p1, p5)
    vertical_2 = _dist(p2, p4)
    horizontal = _dist(p0, p3)
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)

def get_face_bbox_from_landmarks(landmarks, w, h):
    """Bounding box wajah dari MediaPipe landmarks (pas di wajah)."""
    xs = [int(landmarks[i].x * w) for i in FACE_OVAL]
    ys = [int(landmarks[i].y * h) for i in FACE_OVAL]
    x1, y1 = max(0, min(xs)), max(0, min(ys))
    x2, y2 = min(w, max(xs)), min(h, max(ys))
    return (x1, y1, x2, y2)

def run_yolo_detection(frame):
    """
    Jalankan YOLO untuk deteksi wajah/person.
    Return True jika terdeteksi, False jika tidak.
    """
    results = yolo_model(frame, verbose=False)
    for r in results:
        for box in r.boxes:
            if float(box.conf[0]) > 0.4:
                return True
    return False

def get_face_embedding(frame):
    if not insight_app:
        return None
    faces = insight_app.get(frame)
    if faces and len(faces) > 0:
        return faces[0].embedding
    return None

def get_average_embedding(frames):
    if not insight_app:
        return None
    embeddings = []
    for frame in frames:
        faces = insight_app.get(frame)
        if faces and len(faces) > 0:
            embeddings.append(faces[0].embedding)
    if not embeddings:
        return None
    avg_embedding = np.mean(embeddings, axis=0)
    return (avg_embedding / np.linalg.norm(avg_embedding)).tolist()

def cosine_similarity(emb1, emb2):
    emb1 = np.array(emb1, dtype=np.float64)
    emb2 = np.array(emb2, dtype=np.float64)
    norm = np.linalg.norm(emb1) * np.linalg.norm(emb2)
    if norm == 0:
        return 0.0
    return float(np.dot(emb1, emb2) / norm)

def verify_face(current_embedding, registered_embeddings):
    best_match_id = None
    best_sim = 0.0
    for record in registered_embeddings:
        m_id = record['mahasiswa_id']
        reg_emb = record['embedding']
        sim = cosine_similarity(current_embedding, reg_emb)
        if sim > best_sim:
            best_sim = sim
            best_match_id = m_id
    if best_sim >= 0.5:
        return best_match_id, best_sim
    return None, best_sim


# ==========================================
# FUNGSI UTAMA: process_frame
# ==========================================
def process_frame(frame, blink_counter, eye_closed_frames, registered_embeddings,
                  current_matched_id=None, frame_count=0):
    """
    Pipeline AI per frame:
    1. YOLO     → hanya di frame ke-0 dan setiap 15 frame (konfirmasi ada orang)
    2. MediaPipe → SETIAP frame (blink detection + bbox wajah)  [RINGAN]
    3. InsightFace → SEKALI saja per sesi (face recognition)    [BERAT, di-cache]

    Parameters:
        frame: numpy array BGR
        blink_counter: jumlah kedipan terdeteksi
        eye_closed_frames: jumlah frame berturut-turut mata tertutup
        registered_embeddings: list of dict
        current_matched_id: cache ID mahasiswa yg sudah dikenali
        frame_count: nomor frame saat ini (untuk mengatur kapan YOLO jalan)
    
    Returns:
        (status, matched_id, bbox, blink_counter, eye_closed_frames, yolo_confirmed)
    """
    h, w, _ = frame.shape

    # === STEP 1: YOLO Detection (hanya setiap 15 frame) ===
    yolo_confirmed = False
    if frame_count % 15 == 0:
        yolo_confirmed = run_yolo_detection(frame)

    # === STEP 2: MediaPipe Face Mesh (SETIAP frame, sangat ringan ~5ms) ===
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mesh_results = face_mesh.process(rgb_frame)

    if not mesh_results.multi_face_landmarks:
        return "NO_FACE_DETECTED", None, None, blink_counter, eye_closed_frames, yolo_confirmed

    face_landmarks = mesh_results.multi_face_landmarks[0]
    landmarks = face_landmarks.landmark

    # Bounding box dari MediaPipe (pas di wajah)
    bbox = get_face_bbox_from_landmarks(landmarks, w, h)

    # === STEP 3: EAR + Blink Detection ===
    def get_coords(indices):
        return [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices]

    left_ear = calculate_ear(get_coords(LEFT_EYE))
    right_ear = calculate_ear(get_coords(RIGHT_EYE))
    ear = (left_ear + right_ear) / 2.0

    # State machine blink: closed → open = 1 blink
    if ear < EAR_THRESHOLD:
        eye_closed_frames += 1
    else:
        if eye_closed_frames >= 1:
            blink_counter += 1
        eye_closed_frames = 0

    # === STEP 4: Face Recognition (InsightFace, hanya 1x) ===
    matched_id = current_matched_id
    if matched_id is None:
        current_embedding = get_face_embedding(frame)
        if current_embedding is not None:
            matched_id, _ = verify_face(current_embedding, registered_embeddings)

    # === STEP 5: Status ===
    if blink_counter < 2:
        return "LIVENESS_FAILED_NEED_BLINK", matched_id, bbox, blink_counter, eye_closed_frames, yolo_confirmed

    if matched_id is not None:
        return "SUCCESS", matched_id, bbox, blink_counter, eye_closed_frames, yolo_confirmed
    else:
        return "UNKNOWN_FACE", None, bbox, blink_counter, eye_closed_frames, yolo_confirmed
