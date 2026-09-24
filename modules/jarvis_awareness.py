"""
J.A.R.V.I.S. Screen Awareness Module
=======================================
รันเป็น background thread ถ่ายภาพหน้าจอทุก 30 วินาที
เก็บ cache ล่าสุดไว้ใน RAM — เมื่อเจ้านายพูดถึงหน้าจอ
ระบบจะดึง cache มาส่ง Vision API โดยอัตโนมัติโดยไม่ต้องสั่ง
"""
from __future__ import annotations

import base64
import logging
import threading
import time
from io import BytesIO
from typing import Optional

logger = logging.getLogger("JarvisAwareness")

SCREEN_TRIGGER_KEYWORDS = [
    
    "หน้าจอ", "ตรงนี้", "บนจอ", "เห็นไหม", "ดูหน่อย", "มันพัง", "error ที่เห็น",
    "code ตรงนี้", "โค้ดตรงนี้", "ช่วยดู", "ตรงหน้า", "จอ", "บนหน้าจอ",
    "ที่เห็น", "ที่โชว์", "ที่แสดง",
    
    "on screen", "i see", "on my screen", "you see", "looking at", "this error",
]

_cached_screenshot_b64: Optional[str] = None
_last_capture_time: float = 0.0
_awareness_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_CAPTURE_INTERVAL = 30  

def _capture_screenshot() -> Optional[str]:
    """ถ่ายภาพหน้าจอและแปลงเป็น base64 JPEG string"""
    try:
        import mss
        import mss.tools
        from PIL import Image

        with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
            monitor = sct.monitors[1]  
            img = sct.grab(monitor)
            
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            
            pil_img.thumbnail((1280, 1280))
            buf = BytesIO()
            pil_img.save(buf, format="JPEG", quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return b64
    except ImportError:
        try:
            
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.thumbnail((1280, 1280))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.debug(f"[Awareness] Screenshot fallback failed: {e}")
            return None
    except Exception as e:
        logger.debug(f"[Awareness] Screenshot failed: {e}")
        return None

_last_ocr_alert_time: float = 0.0

def _awareness_loop() -> None:
    """Background thread ที่รันต่อเนื่อง"""
    global _cached_screenshot_b64, _last_capture_time, _last_ocr_alert_time
    logger.info("[Awareness] Screen awareness thread started (interval=30s)")
    
    ocr_enabled = True
    try:
        import pytesseract
    except ImportError:
        ocr_enabled = False
        logger.warning("[Awareness] pytesseract not installed. OCR Screen Awareness disabled.")

    while not _stop_event.is_set():
        screenshot = _capture_screenshot()
        if screenshot:
            _cached_screenshot_b64 = screenshot
            _last_capture_time = time.time()
            
            if ocr_enabled and time.time() - _last_ocr_alert_time > 300: 
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    import base64
                    
                    img_data = base64.b64decode(screenshot)
                    img = Image.open(io.BytesIO(img_data))
                    
                    img = img.convert('L')
                    text = pytesseract.image_to_string(img).lower()
                    
                    target_keywords = ['error', 'exception', 'failed', 'traceback', 'critical']
                    found = [kw for kw in target_keywords if kw in text]
                    
                    if found:
                        _last_ocr_alert_time = time.time()
                        logger.warning(f"[Awareness] Detected issue on screen: {found}")
                        try:
                            from jarvis_tts_edge import JarvisStreamingTTS
                            tts = JarvisStreamingTTS()
                            tts.speak("เจ้านายครับ ผมสังเกตเห็นหน้าจอมีการแจ้งเตือนข้อผิดพลาด ให้ผมช่วยวิเคราะห์ไหมครับ")
                        except Exception as e:
                            logger.error(f"[Awareness] Failed to trigger TTS: {e}")
                except Exception as e:
                    if "tesseract is not installed" in str(e).lower():
                        ocr_enabled = False
                        logger.warning("[Awareness] Tesseract not found in PATH. OCR disabled.")
                    else:
                        logger.debug(f"[Awareness] OCR scan failed: {e}")

        _stop_event.wait(timeout=_CAPTURE_INTERVAL)
    logger.info("[Awareness] Screen awareness thread stopped")

def start_awareness() -> None:
    """เริ่มต้น background thread — เรียกครั้งเดียวตอน startup"""
    global _awareness_thread
    if _awareness_thread and _awareness_thread.is_alive():
        return
    _stop_event.clear()
    _awareness_thread = threading.Thread(target=_awareness_loop, daemon=True, name="JarvisAwareness")
    _awareness_thread.start()

def stop_awareness() -> None:
    """หยุด background thread"""
    _stop_event.set()

def get_cached_screen_b64() -> Optional[str]:
    """ดึง screenshot ล่าสุด (base64) — None ถ้ายังไม่มี"""
    return _cached_screenshot_b64

def get_screen_age_seconds() -> float:
    """บอกว่า screenshot ล่าสุดถ่ายมากี่วินาทีแล้ว"""
    if _last_capture_time == 0:
        return float("inf")
    return time.time() - _last_capture_time

def is_screen_trigger(text: str) -> bool:
    """
    ตรวจว่าข้อความของเจ้านายมีความหมายว่ากำลังชี้ไปที่หน้าจอหรือไม่
    ใช้ตัดสินใจว่าจะแนบ screenshot ไปด้วยหรือเปล่า
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in SCREEN_TRIGGER_KEYWORDS)

def capture_now() -> Optional[str]:
    """ถ่าย screenshot ทันทีและอัปเดต cache — ใช้ตอนต้องการภาพสด"""
    global _cached_screenshot_b64, _last_capture_time
    screenshot = _capture_screenshot()
    if screenshot:
        _cached_screenshot_b64 = screenshot
        _last_capture_time = time.time()
    return screenshot
