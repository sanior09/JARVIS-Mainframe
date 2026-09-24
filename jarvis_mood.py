

import logging
import re
import time

logger = logging.getLogger("JarvisMood")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [MOOD] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

STRESSED_KEYWORDS = {"ทำไม", "ไม่ได้", "พัง", "error", "เสีย", "หยุด", "crash",
                     "ช่วยด้วย", "urgent", "ด่วน", "โกรธ", "shit", "damn", "fuck", 
                     "ช้า", "หงุดหงิด", "แย่", "ห่วย", "เครียด", "รำคาญ"}
RELAXED_KEYWORDS = {"อิอิ", "ฮ่า", "เย้", "แจ่ม", "เด็ด", "สนุก", "555", "lol", "haha",
                    "เจ๋ง", "ok", "โอเค", "ดีมาก", "เก่ง", "cool", "ชิล", "ดี", "เยี่ยม"}
FOCUSED_KEYWORDS = {"ช่วย", "ทำ", "สร้าง", "เขียน", "วิเคราะห์", "ค้นหา", "รัน", "เปิด",
                    "สรุป", "compare", "debug", "fix", "ประมวลผล", "ตรวจ", "สแกน"}
NEGATION_WORDS = {"ไม่", "อย่า", "ห้าม"}

_current_mood = "neutral"
_mood_history = []  

def detect_mood(text: str) -> str:
    """
    วิเคราะห์อารมณ์จากข้อความ โดยใช้ PyThaiNLP Tokenization (NLP-based)
    Returns: "stressed" | "relaxed" | "focused" | "neutral"
    """
    try:
        from pythainlp.tokenize import word_tokenize
        tokens = word_tokenize(text.lower(), engine="newmm")
    except ImportError:
        tokens = text.lower().split()
        
    stress_score = 0
    relax_score = 0
    focus_score = 0
    
    for i, token in enumerate(tokens):
        if token in STRESSED_KEYWORDS:
            
            if i > 0 and tokens[i-1] in NEGATION_WORDS:
                relax_score += 1  
            else:
                stress_score += 2
        elif token in RELAXED_KEYWORDS:
            if i > 0 and tokens[i-1] in NEGATION_WORDS:
                stress_score += 1 
            else:
                relax_score += 2
        elif token in FOCUSED_KEYWORDS:
            focus_score += 1
            
    if len(text) < 15 and ("!" in text or "ด่วน" in text):
        stress_score += 2
    
    scores = {"stressed": stress_score, "relaxed": relax_score, "focused": focus_score}
    top = max(scores, key=scores.get)
    
    if scores[top] == 0:
        return "neutral"
    return top

def update_mood(text: str) -> str:
    """อัปเดต mood state และ return mood ปัจจุบัน"""
    global _current_mood
    new_mood = detect_mood(text)
    
    _mood_history.append((time.time(), new_mood))
    if len(_mood_history) > 10:
        _mood_history.pop(0)
    
    recent = [m for _, m in _mood_history[-3:]]
    if recent:
        _current_mood = max(set(recent), key=recent.count)
    
    logger.info(f"Mood updated: {_current_mood} (from: {new_mood})")
    return _current_mood

def get_mood_prompt_addon() -> str:
    """Return คำสั่งเสริม System Prompt ตาม mood ปัจจุบัน"""
    mood_prompts = {
        "stressed": (
            "⚠️ MOOD CONTEXT: The user seems stressed or frustrated. "
            "Be extra concise, calm, and solution-focused. Skip pleasantries. "
            "Start with the solution immediately. Keep sentences short."
        ),
        "relaxed": (
            "😊 MOOD CONTEXT: The user is in a relaxed, casual mood. "
            "You may be slightly more playful and warm. Light humor is welcome. "
            "Keep the tone friendly and conversational."
        ),
        "focused": (
            "🎯 MOOD CONTEXT: The user is focused and wants results. "
            "Be precise, structured, and efficient. Use bullet points where helpful. "
            "Minimize filler words."
        ),
        "neutral": ""
    }
    return mood_prompts.get(_current_mood, "")

def get_current_mood() -> str:
    return _current_mood

import random as _random

_BACKCHANNEL_PHRASES: dict[str, list[str]] = {
    "stressed": [
        "จัดการให้เดี๋ยวนี้",
        "โอเค กำลังแก้ปัญหาให้",
        "รับทราบ กำลังเร่งมือ",
        "เข้าใจแล้ว เดี๋ยวจัดการให้",
    ],
    "relaxed": [
        "ว่าไง มีอะไรให้ช่วยไหม",
        "ฟังอยู่ สั่งมาได้เลย",
        "ว่ามาได้เลย",
        "ครับนาย อยู่ตรงนี้เสมอ",
    ],
    "focused": [
        "กำลังดำเนินการ",
        "ได้เลย",
        "รับทราบ",
        "โอเค ลุยต่อ",
    ],
    "neutral": [
        "พร้อมรับคำสั่ง",
        "ฟังอยู่",
        "ว่าไง",
        "รับทราบครับ",
    ],
}

def get_backchannel_phrase() -> str:
    """
    Return ประโยคสั้นๆ ที่ JARVIS พูดเพื่อยืนยันว่าได้ยิน (back-channel)
    เลือกตาม mood ปัจจุบัน เพื่อให้รู้สึกเป็นธรรมชาติ
    """
    phrases = _BACKCHANNEL_PHRASES.get(_current_mood, _BACKCHANNEL_PHRASES["neutral"])
    return _random.choice(phrases)
