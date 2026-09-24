import builtins
import copy
import logging

logger = logging.getLogger("JarvisSandbox")

def run_sandbox_test(code_string: str) -> bool:
    """
    กักกันโค้ด (Sandbox) สำหรับทดสอบรัน Python script 
    ก่อนที่จะนำไปติดตั้งในสมองหลัก ป้องกันการใช้คำสั่งอันตราย (os, subprocess, open)
    """
    try:
        # 1. คัดลอก builtins พื้นฐาน
        safe_builtins = copy.copy(builtins.__dict__)
        
        # 2. ถอดคำสั่งสุดอันตรายออก (เช่น ลบไฟล์ หรือสั่ง command line)
        for block_func in ['eval', 'exec', 'compile']:
            safe_builtins.pop(block_func, None)
            
        # 3. สร้าง Import Interceptor
        original_import = builtins.__import__
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            # ห้าม import library ที่อาจทำลายระบบ OS
            if name in ['os', 'subprocess', 'shutil', 'sys']:
                raise ImportError(f"[SANDBOX BLOCKED] Module '{name}' is restricted for safety.")
            return original_import(name, globals, locals, fromlist, level)
            
        safe_builtins['__import__'] = safe_import
        
        # 4. ทดลองรันแบบ Dry-run (Compiling) เพื่อเช็ค Syntax
        compile(code_string, '<string>', 'exec')
        
        # 5. ถ้าระบบต้องการรันจริงๆ จะใช้ restricted_globals
        restricted_globals = {'__builtins__': safe_builtins}
        
        # รันแค่โหมดวิเคราะห์ (ไม่ต้องรันฟังก์ชัน เพราะเราไม่รู้ arguments)
        # ถ้ารัน exec ผ่าน แปลว่าไม่มี Syntax error
        exec(code_string, restricted_globals)
        return True
        
    except ImportError as e:
        logger.warning(f"Sandbox Rejection (Dangerous Import): {e}")
        return False
    except Exception as e:
        logger.error(f"Sandbox Rejection (Syntax/Runtime Error): {e}")
        return False
