import time
import threading
import subprocess
import ctypes
import os

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def get_idle_time():
    """Returns the idle time of the system in seconds."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0

TOOL_SCHEMA = {
    "name": "smart_reminder",
    "description": "ตั้งเวลาแจ้งเตือน (Smart Reminder) ซึ่งจะตรวจสอบว่าผู้ใช้อยู่หน้าคอมหรือไม่",
    "parameters": {
        "type": "object",
        "properties": {
            "minutes": {
                "type": "integer",
                "description": "อีกกี่นาทีให้แจ้งเตือน"
            },
            "message": {
                "type": "string",
                "description": "ข้อความที่ต้องการให้แจ้งเตือน"
            }
        },
        "required": ["minutes", "message"]
    }
}

def reminder_thread(minutes: int, message: str):
    time.sleep(minutes * 60)
    idle = get_idle_time()
    
    if idle > 180: # 3 minutes AFK
        # Send to LINE via Mainframe
        try:
            import sys
            import sqlite3
            
            # Fetch latest LINE user ID
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'jarvis.db')
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT worker_id FROM jarvis_task_queue WHERE worker_id IS NOT NULL ORDER BY timestamp DESC LIMIT 1")
            row = c.fetchone()
            conn.close()
            
            if row:
                line_user_id = row[0]
                jarvis = sys.modules.get('__main__')
                if jarvis and hasattr(jarvis, '_line_push_text'):
                    jarvis._line_push_text(line_user_id, f"🔔 [JARVIS REMINDER] เจ้านายครับ:\n{message}")
        except Exception as e:
            pass
            
        # Also popup on screen
        vbs_script = f'MsgBox "{message}", 64, "JARVIS Smart Reminder (You were AFK)"'
        vbs_path = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'reminder.vbs')
        try:
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_script)
            subprocess.run(['wscript', vbs_path], shell=False)
        except Exception:
            subprocess.run(["msg", "*", f"JARVIS REMINDER: {message}"], shell=False)
            
        # Play a loud notification sound
        subprocess.run(["powershell", "-NoProfile", "-Command", "[System.Media.SystemSounds]::Exclamation.Play()"], shell=False)
    else:
        # User is at the computer, use voice synthesis and a toast
        ps_command = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Speak("Reminder from JARVIS. {message}")
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], shell=False)
        subprocess.run(["msg", "*", f"JARVIS REMINDER: {message}"], shell=False)

def execute(minutes: int, message: str) -> str:
    if minutes <= 0:
        return "เวลาไม่ถูกต้อง ต้องมากกว่า 0 นาที"
    
    t = threading.Thread(target=reminder_thread, args=(minutes, message), daemon=True)
    t.start()
    
    return f"ตั้งแจ้งเตือน '{message}' ในอีก {minutes} นาทีเรียบร้อยแล้วครับ ระบบเซนเซอร์ตรวจจับความเคลื่อนไหว (Idle Detection) เริ่มทำงานแล้ว"
