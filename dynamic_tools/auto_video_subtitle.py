import os
import sys
import json
import argparse

# Add project root and modules to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "modules"))

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "auto_video_subtitle",
        "description": "ตัดต่อและใส่ซับไตเติล (Auto-Captions) วิดีโออัตโนมัติด้วย AI (Whisper-Large-v3 + FFmpeg) รองรับทั้งคลิปเดี่ยวและทั้งโฟลเดอร์ หรือเปิด CapCut (หากไม่ได้ระบุ path หรือสั่งว่า 'วิดีโอนี้/คลิปนี้' ระบบจะสแกนหน้าจอและโฟลเดอร์ที่เปิดอยู่เพื่อหาตำแหน่งไฟล์ให้อัตโนมัติ)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "(Optional) ที่อยู่ไฟล์วิดีโอ (.mp4, .mov ฯลฯ) หรือโฟลเดอร์ เช่น 'C:\\Users\\User\\Videos' (หากผู้ใช้สั่ง 'คลิปนี้' หรือไม่ได้ระบุตำแหน่งไฟล์ ให้เว้นว่างไว้ หรือใส่ '' / 'auto' ระบบจะสแกนหน้าจอเพื่อดึงไฟล์วิดีโอที่กำลังเปิดอยู่ให้เองโดยอัตโนมัติ)"
                },
                "burn_sub": {
                    "type": "boolean",
                    "description": "ฝังซับไตเติลลงในเนื้อวิดีโอทันที (Hardsub สไตล์ Vlog) ค่าเริ่มต้นคือ true",
                    "default": True
                },
                "style": {
                    "type": "string",
                    "enum": ["vlog", "white_clean"],
                    "description": "รูปแบบสไตล์ซับไตเติล: 'vlog' (เหลืองสดใส ขอบดำหนา) หรือ 'white_clean' (ขาวเรียบหรู)",
                    "default": "vlog"
                },
                "open_capcut": {
                    "type": "boolean",
                    "description": "เปิดโปรแกรม CapCut (Desktop/Web) ควบคู่ไปด้วยหรือไม่",
                    "default": False
                }
            },
            "required": []
        }
    }
}

def execute(args: dict) -> str:
    from jarvis_video_automator import JarvisVideoAutomator
    automator = JarvisVideoAutomator()

    raw_path = args.get("path", "")
    path = str(raw_path).strip().strip('"').strip("'") if raw_path else ""

    # ตรวจจับจากหน้าจอและโฟลเดอร์อัตโนมัติหากไม่มีการระบุ path หรือระบุคำอ้างอิง
    if not path or path.lower() in ("auto", "screen", "current", "this", "this_video", "none", "clip", "video", "คลิปนี้", "วิดีโอนี้"):
        detected = automator.detect_video_from_screen()
        if detected:
            path = detected
        else:
            return "❌ ไม่พบไฟล์วิดีโอบนหน้าจอหรือในโฟลเดอร์ที่เปิดอยู่ครับเจ้านาย กรุณาเปิดคลิปหรือระบุพาธไฟล์ครับ"
    elif not os.path.exists(path):
        resolved = automator.resolve_video_path(path)
        if resolved:
            path = resolved
        else:
            return f"❌ ไม่พบไฟล์หรือโฟลเดอร์: {path} ครับเจ้านาย"

    burn_sub = args.get("burn_sub", True)
    if isinstance(burn_sub, str):
        burn_sub = burn_sub.lower() in ("true", "1", "yes")

    style = args.get("style", "vlog")
    open_capcut = args.get("open_capcut", False)

    if open_capcut:
        automator.launch_capcut(path)

    if os.path.isdir(path):
        res = automator.process_folder(path, burn_sub=burn_sub, style=style)
        if res.get("status") == "success":
            return (
                f"✅ ดำเนินการใส่ซับไตเติลให้ครบทั้งหมด {res['completed_videos']}/{res['total_videos']} คลิปเรียบร้อยแล้วครับเจ้านาย!\n"
                f"- โฟลเดอร์ต้นทาง: {path}\n"
                f"- ผลลัพธ์ถูกบันทึกไว้ที่: {res['output_directory']}\n"
                f"- ใช้เวลาทั้งหมดเพียง: {res['total_elapsed_seconds']} วินาที"
            )
        else:
            return f"⚠️ การประมวลผลโฟลเดอร์เกิดข้อขัดข้อง: {res.get('message')}"
    else:
        res = automator.process_single_video(path, burn_sub=burn_sub, style=style)
        if res.get("status") == "success":
            out_vid = res.get("output_video")
            return (
                f"✅ ตรวจพบคลิปและสร้างซับไตเติลสไตล์ Vlog สำเร็จเรียบร้อยแล้วครับเจ้านาย! (จำนวน {res['segments_count']} ท่อน, ใช้เวลา {res['elapsed_seconds']} วินาที)\n"
                f"- คลิปเป้าหมาย: {path}\n"
                f"- ไฟล์ซับไตเติล: {res['srt_path']}\n"
                f"- วิดีโอพร้อมซับ: {out_vid if out_vid else 'ไม่ได้ฝังซับ'}"
            )
        else:
            return f"⚠️ การใส่ซับไตเติลคลิปเกิดข้อขัดข้อง: {res.get('message')}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="")
    parser.add_argument("--burn_sub", default=True)
    parser.add_argument("--style", default="vlog")
    parser.add_argument("--open_capcut", default=False)
    cli_args = parser.parse_args()

    result = execute(vars(cli_args))
    sys.stdout.reconfigure(encoding="utf-8")
    print(result)
