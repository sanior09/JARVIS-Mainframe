

import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import psutil
import win32gui
import json
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("JarvisProactive")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [PROACTIVE] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

JARVIS_URL = os.getenv("JARVIS_URL", "http://127.0.0.1:5050")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis_memory.db")

_proactive_running = False
_last_break_reminder = 0.0
_session_start = time.time()
_morning_brief_done_date = None

def _speak(text: str):
    """ส่ง TTS ให้ JARVIS พูดออกมา"""
    try:
        requests.post(f"{JARVIS_URL}/tts", json={"text": text}, timeout=10)
    except Exception:
        pass

def _notify(text: str):
    """ส่ง notification ไปแสดงบน HUD + พูด + ส่ง LINE"""
    logger.info(f"[PROACTIVE] {text}")
    threading.Thread(target=_speak, args=(text,), daemon=True).start()
    
    try:
        line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        line_user_id = os.getenv("LINE_USER_ID")
        if line_token and line_user_id:
            url = "https://api.line.me/v2/bot/message/push"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {line_token}"
            }
            data = {
                "to": line_user_id,
                "messages": [{"type": "text", "text": f"🤖 [JARVIS Proactive]\n{text}"}]
            }
            requests.post(url, headers=headers, json=data, timeout=5)
    except Exception as e:
        logger.error(f"LINE notification error: {e}")

def _check_work_timer():
    """แจ้งเตือนพักทุก 2 ชั่วโมง"""
    global _last_break_reminder
    elapsed = time.time() - _session_start
    if elapsed > 2 * 3600 and (time.time() - _last_break_reminder) > 3600:
        hours = int(elapsed // 3600)
        _last_break_reminder = time.time()
        _notify(f"เจ้านาย ทำงานต่อเนื่องมา {hours} ชั่วโมงแล้ว พักสายตาสักครู่ไหมครับ")

def _check_morning_briefing():
    """Morning Briefing อัตโนมัติตอน 8:00 - 9:00 น."""
    global _morning_brief_done_date
    now = datetime.now()
    today = now.date()
    if today == _morning_brief_done_date:
        return
    if 8 <= now.hour < 9:
        _morning_brief_done_date = today
        brief = (
            f"สวัสดีตอนเช้าครับเจ้านาย ขณะนี้เวลา {now.strftime('%H:%M')} น. "
            f"วัน{now.strftime('%A')} "
            "ระบบพร้อมทำงานเต็มรูปแบบแล้ว มีแผนอะไรสำหรับวันนี้ไหมครับ"
        )
        _notify(brief)

_last_ram_warning = 0.0
_last_cpu_warning = 0.0

def get_active_window_title() -> str:
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd).lower()
    except:
        return ""

def is_smart_silence_active() -> bool:
    title = get_active_window_title()
    silence_keywords = ["youtube", "netflix", "prime video", "disney", "hbo", "spotify", "vlc", "potplayer", "movie", "หนัง", "ภาพยนตร์"]
    for kw in silence_keywords:
        if kw in title:
            return True
    return False

_last_screen_scan = 0.0
def _check_screen_anomaly():
    global _last_screen_scan
    now = time.time()
    if now - _last_screen_scan < 180:  # Scan at most every 3 minutes
        return
        
    title = get_active_window_title()
    
    is_coding = any(kw in title for kw in ["visual studio", "cursor", "pycharm", "intellij", "code", "terminal", "cmd", "powershell"])
    is_gaming = any(kw in title for kw in ["valorant", "elden ring", "genshin", "dota", "game", "steam"])
    
    if not (is_coding or is_gaming):
        return
        
    try:
        from jarvis_awareness import _cached_screenshot_b64
        if not _cached_screenshot_b64:
            return
            
        _last_screen_scan = now
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return
            
        context = "Programming IDE / Terminal" if is_coding else "Video Game"
        prompt = f"Analyze this screen of a {context}. If there are NO errors, NO exceptions, and NO 'Defeat/You Died/Game Over' screens, reply EXACTLY with the word 'CLEAR'. If you see a clear red error, exception, or game over, reply in THAI with a short 1-sentence witty and helpful comment (e.g. 'โค้ดตรงนั้นน่าจะมีปัญหาเรื่อง syntax นะครับเจ้านาย ให้ผมช่วยไหม'). DO NOT output anything else."
        
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.2-11b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_cached_screenshot_b64}"}}
                    ]
                }
            ],
            "temperature": 0.2,
            "max_tokens": 100
        }
        
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=12)
        if r.status_code == 200:
            msg = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if msg and "CLEAR" not in msg and len(msg) > 10:
                _notify(msg)
    except Exception as e:
        logger.error(f"Screen anomaly scan error: {e}")

def _check_system_health():
    """แจ้งเตือนเมื่อ CPU/RAM สูงผิดปกติ พร้อม Cooldown 15 นาที ป้องกันการพูดเตือนรัวทุกนาที"""
    global _last_ram_warning, _last_cpu_warning
    now = time.time()
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        if cpu > 92 and (now - _last_cpu_warning > 900):
            _last_cpu_warning = now
            _notify(f"เจ้านาย CPU กำลังทำงานหนักถึง {cpu:.0f}% ควรปิดโปรแกรมที่ไม่ได้ใช้งานไหมครับ")
        elif ram > 94 and (now - _last_ram_warning > 900):
            _last_ram_warning = now
            _notify(f"เจ้านาย มีการใช้งาน RAM สูงถึง {ram:.0f}% ครับ")
    except Exception:
        pass

def _proactive_loop():
    """Main loop: รัน checks ทุก 60 วินาที"""
    global _proactive_running
    logger.info("[PHASE 10A] Proactive Intelligence started.")
    while _proactive_running:
        try:
            if is_smart_silence_active():
                logger.info("[PROACTIVE] Smart Silence is ACTIVE (User is watching media). Suppressing alerts.")
            else:
                _check_work_timer()
                _check_morning_briefing()
                _check_system_health()
                _check_screen_anomaly()
        except Exception as e:
            logger.error(f"Proactive loop error: {e}")
        time.sleep(60)

def start():
    global _proactive_running, _session_start
    if _proactive_running:
        return
    _proactive_running = True
    _session_start = time.time()
    threading.Thread(target=_proactive_loop, daemon=True).start()

def stop():
    global _proactive_running
    _proactive_running = False
