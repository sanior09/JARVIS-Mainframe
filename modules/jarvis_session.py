"""
J.A.R.V.I.S. Session Context Manager
=======================================
จดจำ context ข้ามวัน — บันทึกสิ่งที่คุยกันไว้ใน JSON
ตอน startup ถ้ามี session เก่า จะ greet เจ้านายว่ากำลังทำอะไรค้างไว้
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("JarvisSession")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SESSION_FILE = os.path.join(BASE_DIR, "data", "jarvis_session.json")

_session: dict = {}

def _load() -> dict:
    """โหลด session จากดิสก์"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[Session] Could not load session file: {e}")
    return {}

def _save(data: dict) -> None:
    """บันทึก session ลงดิสก์"""
    try:
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[Session] Could not save session: {e}")

def init_session() -> Optional[str]:
    """
    โหลด session เก่าและสร้างประโยค greeting ถ้ามี context เก่า
    Returns: greeting string หรือ None ถ้าไม่มี context น่าสนใจ
    """
    global _session
    _session = _load()

    if not _session:
        
        _session = {
            "session_start": datetime.now().isoformat(),
            "last_topic": None,
            "last_intent": None,
            "turn_count": 0,
        }
        return None

    last_shutdown_str = _session.get("last_shutdown", "")
    hours_ago = None
    if last_shutdown_str:
        try:
            last_dt = datetime.fromisoformat(last_shutdown_str)
            diff = datetime.now() - last_dt
            hours_ago = diff.total_seconds() / 3600
        except Exception:
            pass

    last_topic = _session.get("last_topic")
    last_intent = _session.get("last_intent")

    _session["session_start"] = datetime.now().isoformat()
    _session["turn_count"] = 0

    greeting = None
    if last_topic and hours_ago is not None:
        if hours_ago < 24:
            time_desc = f"{int(hours_ago)} ชั่วโมงที่แล้ว" if hours_ago >= 1 else "ไม่กี่นาทีที่ผ่านมา"
            greeting = (
                f"ยินดีต้อนรับกลับมาครับเจ้านาย เมื่อ{time_desc}เราค้างเรื่อง '{last_topic}' ไว้"
            )
            if last_intent:
                greeting += f" — {last_intent}"
            greeting += " ต้องการให้ผมสานต่อจากตรงนั้นเลยไหมครับ?"
        elif hours_ago < 72:
            greeting = f"กลับมาแล้วครับเจ้านาย ช่วงก่อนเราทำเรื่อง '{last_topic}' ค้างไว้ ยังสนใจต่อยอดไหมครับ?"

    return greeting

def update_session(topic: str = "", intent: str = "") -> None:
    """อัปเดต context ล่าสุด — เรียกหลังแต่ละ response"""
    global _session
    if topic:
        _session["last_topic"] = topic
    if intent:
        _session["last_intent"] = intent
    _session["turn_count"] = _session.get("turn_count", 0) + 1
    _session["last_active"] = datetime.now().isoformat()
    _save(_session)

def save_shutdown() -> None:
    """บันทึก shutdown timestamp — เรียกตอนปิดระบบ"""
    global _session
    _session["last_shutdown"] = datetime.now().isoformat()
    _save(_session)
    logger.info("[Session] Session saved on shutdown")

def extract_topic(user_text: str, assistant_response: str = "") -> str:
    """
    ดึง 'หัวข้อ' หลักจากบทสนทนา อย่างง่ายๆ
    ใช้ heuristic ดึงคำสำคัญจาก user_text
    """
    
    import re
    
    py_files = re.findall(r'[\w_]+\.py', user_text + " " + assistant_response)
    if py_files:
        return py_files[-1]
    
    keywords = ["JARVIS", "suit viewer", "dynamic island", "iOS bridge", "3D model",
                "arc reactor", "TTS", "voice", "backend", "API"]
    for kw in keywords:
        if kw.lower() in (user_text + assistant_response).lower():
            return kw
    
    words = user_text.strip().split()
    if words:
        return " ".join(words[:4])
    return "งานที่กำลังทำ"
