import os
import zipfile
import datetime

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "backup_source_code",
        "description": "สำรองข้อมูล Source Code ทั้งหมดของ J.A.R.V.I.S. บีบอัดเป็นไฟล์ ZIP เก็บไว้ในโฟลเดอร์ backups",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute(args):
    """
    Creates a ZIP archive of the JARVIS source code.
    Excludes large folders like __pycache__, venv, node_modules, data, backups.
    """
    base_dir = r"c:\JARVIS"
    backup_dir = os.path.join(base_dir, "backups")
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(backup_dir, f"JARVIS_Backup_{timestamp}.zip")
    
    exclude_dirs = {
        '__pycache__', 'venv', 'node_modules', 'data', 'backups', 
        '.pytest_cache', '.git', 'screenshots', 'snapshots', 'models'
    }
    
    file_count = 0
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if file.endswith('.pyc') or file.endswith('.db') or file == "jarvis_backup.py":
                        continue
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
        return f"สำรองข้อมูลสำเร็จครับเจ้านาย! แพ็คไฟล์จำนวน {file_count} ไฟล์ ลงใน '{zip_filename}' เรียบร้อยแล้วครับ"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการสำรองข้อมูล: {e}"
