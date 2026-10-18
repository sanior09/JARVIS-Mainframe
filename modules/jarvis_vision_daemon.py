import cv2
import time
import os
import threading
import logging
import sys
import datetime
import requests
import subprocess
from deepface import DeepFace

logger = logging.getLogger("VisionDaemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data")
LATEST_FRAME_PATH = os.path.join(CACHE_DIR, "latest_vision.jpg")

class VisionDaemon(threading.Thread):
    def __init__(self, fps=1):
        super().__init__()
        self.daemon = True
        self.fps = fps
        self.running = True
        self.cap = None
        self.last_alert_time = 0
        self.cooldown = 60
        self.last_face_check = 0
        self.is_locked = False
        self.lockdown_proc = None

    def run(self):
        logger.info("Initializing Continuous Vision Daemon...")
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            logger.error("Failed to open webcam.")
            return

        # ลดความละเอียดเพื่อไม่ให้กิน CPU 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        prev_gray = None

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            motion_detected = False

            if prev_gray is not None:
                frame_delta = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_score = cv2.countNonZero(thresh)
                
                if motion_score > 5000:  
                    motion_detected = True

            prev_gray = gray

            # Save the frame 
            cv2.imwrite(LATEST_FRAME_PATH, frame)
            
            if motion_detected:
                now = time.time()
                # Run DeepFace check max once every 3 seconds to save CPU
                if now - self.last_face_check > 3:
                    self.last_face_check = now
                    known_face_path = os.path.join(CACHE_DIR, "known_faces", "owner.jpg")
                    if os.path.exists(known_face_path):
                        try:
                            # ใช้วิธีวิเคราะห์ใบหน้า (ถ้าไม่เจอหน้าคนในภาพ มันจะโยน ValueError)
                            result = DeepFace.verify(LATEST_FRAME_PATH, known_face_path, enforce_detection=True, model_name="VGG-Face")
                            
                            if result.get("verified", False):
                                # เจ้านายกลับมาแล้ว! ปลดล็อค!
                                if self.is_locked:
                                    logger.info("Owner detected! Unlocking system...")
                                    if self.lockdown_proc:
                                        try:
                                            self.lockdown_proc.stdin.write(b"UNLOCK\n")
                                            self.lockdown_proc.stdin.flush()
                                        except:
                                            self.lockdown_proc.terminate()
                                    self.is_locked = False
                            else:
                                # หน้าคนอื่น! ล็อคทันที!
                                if not self.is_locked:
                                    logger.warning("Intruder detected! Locking system...")
                                    self.is_locked = True
                                    overlay_script = os.path.join(BASE_DIR, "modules", "lockdown_overlay.py")
                                    if not os.path.exists(overlay_script):
                                        overlay_script = os.path.join(BASE_DIR, "lockdown_overlay.py")
                                    self.lockdown_proc = subprocess.Popen(
                                        [sys.executable, overlay_script],
                                        stdin=subprocess.PIPE
                                    )
                                    # ยิงแจ้งเตือน LINE
                                    if now - self.last_alert_time > self.cooldown:
                                        try:
                                            requests.post("http://127.0.0.1:5000/api/internal_alert", json={
                                                "message": "🚨 [PASSIVE SENTINEL] ล็อคหน้าจอ! ตรวจพบผู้บุกรุกมานั่งที่หน้าคอมพิวเตอร์!",
                                                "image_path": LATEST_FRAME_PATH
                                            }, timeout=2)
                                            self.last_alert_time = now
                                        except:
                                            pass
                        except ValueError:
                            # ขยับ แต่ไม่เห็นหน้าคน ก็ปล่อยผ่าน
                            pass
                        except Exception as e:
                            logger.error(f"Face check error: {e}")
            
            time.sleep(1.0 / self.fps)

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

if __name__ == "__main__":
    daemon = VisionDaemon(fps=2) # 2 เฟรมต่อวินาที
    daemon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
