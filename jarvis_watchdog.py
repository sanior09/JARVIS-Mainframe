import time
import subprocess
import os
import sys
import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODULES_DIR = os.path.join(BASE_DIR, "modules")
if _MODULES_DIR not in sys.path:
    sys.path.insert(0, _MODULES_DIR)

dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def send_line_alert(message: str):
    """ส่งแจ้งเตือนผ่าน LINE ทันทีโดยไม่ผ่าน jarvis.py (เผื่อ jarvis.py ตายอยู่)"""
    if not LINE_TOKEN or not LINE_USER_ID:
        return
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=5)
    except Exception as e:
        print(f"[Watchdog] Failed to send LINE alert: {e}")

def run_watchdog():
    script_to_monitor = "jarvis.py"
    
    print("==================================================")
    print("[!] JARVIS Watchdog Supervisor Initialized")
    print(f"Monitoring process: {script_to_monitor}")
    print("==================================================")
    
    restart_count = 0
    max_restarts_per_hour = 10
    start_time = time.time()
    
    while True:
        try:
            
            if time.time() - start_time > 3600:
                restart_count = 0
                start_time = time.time()
                
            print(f"\n[Watchdog] [*] Starting {script_to_monitor}...")
            
            process = subprocess.Popen(
                [sys.executable, script_to_monitor],
                cwd=BASE_DIR
            )
            
            while True:
                try:
                    process.wait(timeout=1.0)
                    break
                except subprocess.TimeoutExpired:
                    pass
            
            exit_code = process.returncode
            if exit_code == 0:
                print(f"[Watchdog] [i] {script_to_monitor} exited cleanly.")
                break 
            elif exit_code == 100:
                print("[Watchdog] [*] Autonomous Reboot Requested (Code 100). Restarting immediately...")
                continue
            else:
                restart_count += 1
                print(f"[Watchdog] [!] {script_to_monitor} crashed with exit code {exit_code}!")
                
                if restart_count > max_restarts_per_hour:
                    msg = f"[CRITICAL ALERT]\nJARVIS Mainframe Crash Loop Detected (>{max_restarts_per_hour} times/hr)\nระบบระงับการทำงานเพื่อป้องกันความเสียหาย โปรดตรวจสอบระบบด่วน"
                    print(msg)
                    send_line_alert(msg)
                    break
                    
                msg = f"[AUTO-HEALING TRIGGERED]\nJARVIS Mainframe Crash (Exit Code: {exit_code}). กำลังเรียกใช้งาน Auto-Healer..."
                print(msg)
                send_line_alert(msg)
                
                try:
                    healer_script = os.path.join(BASE_DIR, "modules", "jarvis_auto_healer.py")
                    if not os.path.exists(healer_script):
                        healer_script = os.path.join(BASE_DIR, "jarvis_auto_healer.py")
                    healer_process = subprocess.Popen([sys.executable, healer_script], cwd=BASE_DIR)
                    healer_process.wait(timeout=300) 
                except Exception as he:
                    print(f"[Watchdog] [x] Auto-Healer failed to run: {he}")
                
                print(f"[Watchdog] [*] Restarting Mainframe after healing attempt (Attempt {restart_count}/{max_restarts_per_hour})")
                continue
            
        except KeyboardInterrupt:
            print("\n[Watchdog] [!] Manual termination requested. Shutting down.")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
            break
        except Exception as e:
            print(f"[Watchdog] [x] Critical Watchdog Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_watchdog()
