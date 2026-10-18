import os
import ctypes
import base64
import logging
from PIL import ImageGrab

logger = logging.getLogger("JarvisScreenContext")

def get_active_window_title() -> str:
    """ดึงชื่อหน้าต่าง (Active Window) ที่ผู้ใช้กำลังเปิดใช้อยู่"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value if buf.value else "Unknown Desktop/Window"
    except Exception as e:
        logger.error(f"Failed to get active window title: {e}")
        return "Unknown Context"

def get_screen_context_image_b64() -> str:
    """แคปหน้าจอแล้วแปลงเป็น base64 ทันที"""
    try:
        img = ImageGrab.grab()
        # ย่อขนาดลงเพื่อให้ส่งผ่าน API ได้รวดเร็วที่สุด (Zero-latency focus)
        img.thumbnail((1280, 1280))
        
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=75)
        return base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return ""

def should_attach_screen(text: str) -> bool:
    """เช็คว่าในประโยคมีคีย์เวิร์ดที่อ้างอิงถึงหน้าจอ หรือคลิป/ไฟล์บนจอหรือไม่"""
    keywords = [
        "ตรงนี้", "หน้านี้", "อันนี้", "หน้าจอนี้", "โค้ดนี้", "หน้าต่างนี้",
        "เกิดอะไรขึ้น", "ดูนี่ให้หน่อย", "บนจอ", "อ่านนี่ให้หน่อย",
        "วิดีโอนี้", "คลิปนี้", "ไฟล์นี้", "ตัดต่อคลิปนี้", "ตัดต่อวิดีโอนี้",
        "ใส่ซับคลิปนี้", "ใส่ซับวิดีโอนี้", "คลิปบนจอ", "วิดีโอบนจอ",
        "คลิปบนหน้าจอ", "วิดีโอบนหน้าจอ", "ไฟล์บนจอ", "ไฟล์บนหน้าจอ",
        # คำถามเกี่ยวกับหน้าจอ / สิ่งที่เปิดอยู่ / แมพเกม
        "หน้าจอผม", "หน้าจอ", "เห็นหน้าจอ", "เห็นจอ", "เปิดอะไรอยู่",
        "ดูจอ", "ดูหน้าจอ", "แมพนี้", "ในจอ", "ในหน้าจอ", "จอคอม",
        "เกมนี้", "โปรแกรมนี้", "ภาพบนจอ", "รูปบนจอ", "ที่เปิดอยู่",
        "screen", "display", "active window"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

def enrich_messages_with_screen_context(messages: list) -> None:
    """
    Hook สำหรับดักจับว่าผู้ใช้กำลังพูดถึงหน้าจอหรือคลิปวิดีโอบนจออยู่หรือเปล่า
    ถ้าใช่ จะเพิ่ม Context ของหน้าต่าง ภาพหน้าจอ และตำแหน่งไฟล์วิดีโอส่งไปให้ AI
    """
    if not messages: 
        return
        
    last_msg = messages[-1]
    if last_msg.get("role") != "user": 
        return
    
    user_content = last_msg.get("content", "")
    
    # ถ้าส่งมาเป็น list อยู่แล้ว แปลว่ามีรูปภาพแนบมาแล้วข้ามไป
    if isinstance(user_content, list):
        return 
        
    if should_attach_screen(user_content):
        title = get_active_window_title()
        b64_img = get_screen_context_image_b64()
        
        # ตรวจสอบเพิ่มเติมหากเป็นคำสั่งเกี่ยวกับคลิป/วิดีโอ
        detected_video_info = ""
        if any(k in user_content.lower() for k in ["คลิป", "วิดีโอ", "video", "clip", "ตัดต่อ", "ใส่ซับ", "ซับ"]):
            try:
                from jarvis_video_automator import JarvisVideoAutomator
                automator = JarvisVideoAutomator()
                detected_path = automator.detect_video_from_screen()
                if detected_path:
                    detected_video_info = f"\n[JARVIS DETECTED VIDEO ON SCREEN: '{detected_path}']"
                    logger.info(f"🎥 [SCREEN CONTEXT] Auto-detected video on screen: {detected_path}")
            except Exception as e:
                logger.debug(f"Video screen auto-detection note: {e}")

        if b64_img:
            # เสริมข้อมูลชื่อหน้าต่างที่เจ้านายกำลังโฟกัสอยู่
            new_text = f"[JARVIS VISION: เจ้านายกำลังโฟกัสอยู่ที่หน้าต่าง '{title}']{detected_video_info}\nคำถาม: {user_content}"
            logger.info(f"👀 [SCREEN CONTEXT] Auto-attached screen vision (Active: {title})")
            
            # แปลงข้อความเป็นรูปแบบ Multimodal (รองรับ Vision Model)
            messages[-1]["content"] = [
                {"type": "text", "text": new_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]
        elif detected_video_info:
            messages[-1]["content"] = f"{detected_video_info}\nคำถาม: {user_content}"
