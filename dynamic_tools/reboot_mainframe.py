import sys
import time

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "reboot_mainframe",
        "description": "สั่งรีบูตระบบ J.A.R.V.I.S. Mainframe ทันที (Autonomous Reboot) เมื่อระบบเริ่มทำงานผิดปกติ หรือต้องการเคลียร์แคชระบบ",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def execute(args):
    """
    Triggers an autonomous reboot.
    Exits the process with code 100. The jarvis_watchdog.py supervisor 
    will catch this and immediately restart the jarvis.py process.
    """
    print("[SYSTEM] Autonomous Reboot Initiated...")
    
    # Wait slightly to allow the agent to finish its response
    import threading
    def delay_exit():
        time.sleep(2.0)
        sys.exit(100)
        
    t = threading.Thread(target=delay_exit)
    t.start()
    
    return "เริ่มกระบวนการรีบูตระบบ... ระบบจะกลับมาทำงานในอีกสักครู่ครับ"
