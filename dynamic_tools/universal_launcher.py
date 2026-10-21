"""
Purpose: Universal App Launcher for JARVIS
Dynamically searches for Windows Shortcuts (.lnk) and launches them.
"""

import os
import subprocess
import difflib
import logging

logger = logging.getLogger(__name__)

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "universal_app_launcher",
        "description": "เปิดโปรแกรม เกม หรือแอปพลิเคชันทุกชนิดในเครื่องคอมพิวเตอร์ โดยค้นหาจากชื่อโปรแกรม",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "ชื่อโปรแกรมหรือเกมที่เจ้านายต้องการเปิด เช่น 'chrome', 'valorant', 'word', 'line'"
                }
            },
            "required": ["app_name"]
        }
    }
}

def get_all_shortcuts():
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    public_desktop = os.environ.get("PUBLIC", "C:\\Users\\Public") + "\\Desktop"
    
    search_paths = [
        os.path.join(user_profile, "Desktop"),
        public_desktop,
        os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
    ]
    
    shortcuts = {}
    for path in search_paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith('.lnk') or file.lower().endswith('.url'):
                    name = os.path.splitext(file)[0]
                    # Save the full path keyed by the display name
                    shortcuts[name] = os.path.join(root, file)
                    
    return shortcuts

def universal_app_launcher(args):
    app_name = args.get('app_name', '').strip()
    if not app_name:
        return "ไม่พบชื่อโปรแกรมที่ต้องการเปิดครับ"
        
    shortcuts = get_all_shortcuts()
    if not shortcuts:
        return "ไม่พบข้อมูลโปรแกรมในระบบเลยครับเจ้านาย"
        
    names = list(shortcuts.keys())
    best_match = None
    
    # 1. Exact Substring Match (Case-Insensitive)
    for name in names:
        if app_name.lower() in name.lower():
            best_match = name
            break
            
    # 2. Fuzzy Match (If substring fails)
    if not best_match:
        matches = difflib.get_close_matches(app_name, names, n=1, cutoff=0.4)
        if matches:
            best_match = matches[0]
            
    if best_match:
        target_path = shortcuts[best_match]
        try:
            # Use cmd /c start so Windows resolves the .lnk properly
            subprocess.Popen(["cmd.exe", "/c", "start", "", target_path], shell=False)
            return f"เปิดโปรแกรม {best_match} ให้เรียบร้อยแล้วครับเจ้านาย"
        except Exception as e:
            logger.error(f"Launcher Error: {e}")
            return f"พบข้อผิดพลาดในการรัน {best_match} ครับ: {str(e)}"
    else:
        return f"ขออภัยครับเจ้านาย ผมหาโปรแกรมที่ชื่อคล้ายๆ '{app_name}' ไม่เจอในระบบเลยครับ รบกวนตรวจสอบชื่ออีกครั้งครับ"
