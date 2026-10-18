import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "modules"))

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "control_capcut",
        "description": "เปิดและสั่งการโปรแกรม CapCut (Desktop หรือ Web) สำหรับตัดต่อคลิปและสร้าง Auto-Captions",
        "parameters": {
            "type": "object",
            "properties": {
                "target_folder": {
                    "type": "string",
                    "description": "(Optional) โฟลเดอร์วิดีโอที่ต้องการเปิดใช้งานคู่กับ CapCut เช่น 'C:\\Users\\sanio\\Videos\\JARVIS'"
                }
            }
        }
    }
}

def execute(args: dict) -> str:
    from jarvis_video_automator import JarvisVideoAutomator
    automator = JarvisVideoAutomator()
    target = args.get("target_folder", "")
    res = automator.launch_capcut(target)
    return res.get("message", "เปิด CapCut เรียบร้อยแล้วครับเจ้านาย")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_folder", default="")
    cli_args = parser.parse_args()

    result = execute(vars(cli_args))
    sys.stdout.reconfigure(encoding="utf-8")
    print(result)
