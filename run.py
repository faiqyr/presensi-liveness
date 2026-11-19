import subprocess
import sys
import time
import os

def start_backend():
    print("[SERVER] Memulai Backend Flask di Port 5000...")
    # Menjalankan app.py sebagai modul agar import relative berfungsi
    return subprocess.Popen([sys.executable, "-m", "backend.app"], stdout=sys.stdout, stderr=sys.stderr)

def start_frontend():
    print("[CLIENT] Memulai Frontend ReactJS di Port 5173...")
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
    return subprocess.Popen(["npm", "run", "dev"], cwd=frontend_path, shell=True, stdout=sys.stdout, stderr=sys.stderr)

if __name__ == "__main__":
    print("==================================================")
    print("  SYSTEM PRESENSI FACE RECOGNITION & LIVENESS")
    print("==================================================")
    
    try:
        backend_proc = start_backend()
        time.sleep(3) # Tunggu backend stabil
        frontend_proc = start_frontend()
        
        print("\n[READY] Aplikasi berjalan. Akses frontend di: http://localhost:5173")
        print("[READY] Tekan CTRL+C untuk menghentikan.\n")
        
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Menghentikan seluruh service (Backend & Frontend)...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("[INFO] Service berhasil dihentikan.")
