import base64
import json
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .database import init_db, get_db, register_student, log_attendance, get_all_students
from .ai_engine import get_face_embedding, process_frame

app = FastAPI(title="Face Recognition Attendance System")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class RegisterRequest(BaseModel):
    nim: str
    name: str
    image_base64: str

def decode_base64_image(base64_string: str):
    try:
        # Remove header if exists e.g., data:image/jpeg;base64,
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        return None

# Caching embeddings in memory for fast lookup during websocket stream
cached_embeddings = {}

def update_embeddings_cache():
    global cached_embeddings
    students = get_all_students()
    for s in students:
        if s.face_embedding:
            try:
                emb = json.loads(s.face_embedding)
                cached_embeddings[s.nim] = (s.name, emb)
            except:
                pass

@app.on_event("startup")
def on_startup():
    init_db()
    update_embeddings_cache()

@app.post("/api/register")
def register_api(req: RegisterRequest):
    img = decode_base64_image(req.image_base64)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")
        
    embedding = get_face_embedding(img)
    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected or InsightFace not initialized")
        
    # Convert numpy array to list for JSON serialization
    emb_list = embedding.tolist()
    
    try:
        student = register_student(req.nim, req.name, emb_list)
        update_embeddings_cache()
        return {"status": "SUCCESS", "message": f"Student {student.name} registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/presensi")
async def presensi_websocket(websocket: WebSocket):
    await websocket.accept()
    
    blink_counter = 0
    ear_history = []
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Frontend should send JSON like {"image": "base64..."}
            try:
                payload = json.loads(data)
                base64_img = payload.get("image", "")
            except:
                base64_img = data
                
            img = decode_base64_image(base64_img)
            
            if img is None:
                await websocket.send_json({"status": "ERROR", "message": "Invalid frame"})
                continue
                
            status, nim, name, bbox, blink_counter, ear_history = process_frame(
                img, blink_counter, ear_history, cached_embeddings
            )
            
            response = {
                "status": status,
                "blink_counter": blink_counter,
                "bbox": bbox
            }
            
            if status == "SUCCESS":
                response["name"] = name
                response["nim"] = nim
                
                # Log to database
                students = get_all_students()
                student_id = None
                for s in students:
                    if s.nim == nim:
                        student_id = s.id
                        break
                        
                if student_id:
                    log_attendance(student_id=student_id, status="Hadir")
                    response["message"] = f"Presensi Sukses: {name}"
                    
                    # Reset session after success
                    blink_counter = 0
                    ear_history = []
            
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

# Mount static files at the root
import os
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
