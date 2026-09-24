"""
Purpose: เปิด/ปิดโหมดรักษาความปลอดภัย (Vision Daemon) แบบเบื้องหลัง
"""
import os
import psutil
import subprocess

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "toggle_guard_mode",
        "description": "เปิดหรือปิดโหมดเฝ้าระวังความปลอดภัย (Passive Sentinel / Vision Daemon)",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop"],
                    "description": "ระบุว่าต้องการ start หรือ stop"
                }
            },
            "required": ["action"]
        }
    }
}

def toggle_guard_mode(args):
    action = args.get("action", "").lower()
    
    daemon_script = "jarvis_vision_daemon.py"
    
    def get_daemon_pid():
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if 'python' in proc.info.get('name', '').lower() or 'python.exe' in proc.info.get('name', '').lower():
                    for cmd in cmdline:
                        if daemon_script in cmd:
                            return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None

    pid = get_daemon_pid()
    
    if action == "start":
        if pid:
            return "ระบบเฝ้าบ้านกำลังทำงานอยู่แล้วครับ"
            
        script_path = os.path.join(r"c:\JARVIS", "modules", daemon_script)
        if not os.path.exists(script_path):
            script_path = os.path.join(r"c:\JARVIS", daemon_script)
        if not os.path.exists(script_path):
            return "เปิดระบบไม่ได้ครับ ไม่พบไฟล์หลัก"
            
        subprocess.Popen(["python", script_path], cwd=r"c:\JARVIS")
        return "ระบบเฝ้าบ้าน ทำงานครับเจ้านาย 🛡️"
        
    elif action == "stop":
        if not pid:
            return "ระบบเฝ้าบ้านปิดอยู่แล้วครับ"
            
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=3)
            return "ปิดระบบเฝ้าบ้านเรียบร้อยครับ 🛑"
        except Exception as e:
            return f"Error: {e}"
            
    return "ไม่เข้าใจคำสั่ง กรุณาระบุ action ให้ถูกต้อง (start / stop)"
