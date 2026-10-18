"""
Purpose: ค้นหาไฟล์ในคอมพิวเตอร์และส่งลิงก์ดาวน์โหลดให้เจ้านายผ่าน LINE Bot
"""
import os
import shutil
import time
from dotenv import load_dotenv

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_file_to_line",
        "description": "ค้นหาและส่งไฟล์จากในคอมพิวเตอร์ (PC) ให้เจ้านายผ่าน LINE (สร้างลิงก์ดาวน์โหลด)",
        "parameters": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "ชื่อไฟล์ที่ต้องการค้นหาและส่ง เช่น 'รายงาน.pdf' หรือ 'สรุปยอดขาย.xlsx'"
                },
                "search_directory": {
                    "type": "string",
                    "description": "โฟลเดอร์ที่ต้องการค้นหา (ถ้าไม่ระบุ จะค้นหาใน Desktop และ Documents เป็นหลัก)",
                    "default": ""
                }
            },
            "required": ["file_name"]
        }
    }
}

def transfer_file_to_line(args):
    file_name = args.get("file_name", "")
    search_directory = args.get("search_directory", "")
    
    if not file_name:
        return "กรุณาระบุชื่อไฟล์ที่ต้องการส่งครับ"
        
    # Directories to search if not specified
    user_profile = os.path.expanduser("~")
    search_dirs = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads")
    ]
    if search_directory and os.path.exists(search_directory):
        search_dirs = [search_directory]
        
    found_path = None
    
    # Simple search
    for directory in search_dirs:
        for root, dirs, files in os.walk(directory):
            for f in files:
                if file_name.lower() in f.lower():
                    found_path = os.path.join(root, f)
                    break
            if found_path:
                break
        if found_path:
            break
            
    if not found_path:
        return f"ไม่พบไฟล์ที่ชื่อ '{file_name}' ในระบบครับเจ้านาย"
        
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(base_dir, ".env"))
        ngrok_url = os.getenv("NGROK_PUBLIC_URL", "").strip().rstrip('/')
        
        if not ngrok_url:
            return "ไม่สามารถส่งไฟล์ได้เนื่องจาก NGROK_PUBLIC_URL ไม่ได้ตั้งค่าไว้ครับ"
            
        save_dir = os.path.join(base_dir, "system_cache", "temp_files")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # สร้างชื่อไฟล์ใหม่เพื่อป้องกันการซ้ำ
        safe_name = f"{int(time.time())}_{os.path.basename(found_path)}"
        safe_name = safe_name.replace(" ", "_")
        dest_path = os.path.join(save_dir, safe_name)
        
        shutil.copy2(found_path, dest_path)
        
        public_url = f"{ngrok_url}/temp_files/{safe_name}"
        
        return f"พบไฟล์ '{os.path.basename(found_path)}' แล้วครับ!\n\nกรุณาแจ้งให้เจ้านายดาวน์โหลดไฟล์ได้ที่ลิงก์นี้:\n{public_url}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการเตรียมไฟล์: {e}"
