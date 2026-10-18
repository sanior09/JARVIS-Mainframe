

"""
[J.A.R.V.I.S. DYNAMIC EMOTION & MOOD ENGINE]
=============================================
ระบบจำลองอารมณ์ จิตวิทยา และบุคลิกภาพอัจฉริยะ (Human-like Emotion Dynamics)
- Multi-dimensional Mood Spectrum: enthusiastic, witty, caring, urgent, focused, calm_butler
- Contextual Sentiment & Valence/Arousal Analysis
- Dynamic Voice Prosody Modulation (Rate, Pitch, Volume for Edge-TTS)
- Response-level Vocal Tone Modulation (ตรวจจับอารมณ์จากคำตอบของ JARVIS เพื่อปรับน้ำเสียงให้สมจริง)
- Natural Human Backchannel & Reactive Phrases
"""

import logging
import re
import time
import random as _random
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("JarvisMood")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [MOOD] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# ==============================================================================
# Emotion Keywords & Linguistic Markers
# ==============================================================================
ENTHUSIASTIC_KEYWORDS = {
    "สุดยอด", "เจ๋ง", "เยี่ยม", "แจ่ม", "โคตรดี", "สำเร็จ", "ลุย", "เก่งมาก", "เก่ง",
    "ขอบใจ", "ขอบคุณ", "ชอบ", "ชาญฉลาด", "ประทับใจ", "ดีมาก", "ดีเยี่ยม", "ตื่นเต้น",
    "amazing", "great", "excellent", "awesome", "perfect", "good job", "bravo",
    "wow", "ว้าว", "ยินดี", "เย้", "เด็ด", "ไชโย", "ชอบมาก", "รักเลย", "ปัง", "เริด"
}

WITTY_KEYWORDS = {
    "555", "ฮ่า", "ขำ", "ตลก", "กวน", "หยอก", "แซว", "เล่นมุก", "lol", "haha",
    "อิอิ", "ชิล", "ขี้โม้", "ล้อเล่น", "มุก", "funny", "joke", "prank", "ขำขัน",
    "กวนตีน", "กวนประสาท", "แกล้ง", "น่ารัก", "ฮา"
}

CARING_KEYWORDS = {
    "เหนื่อย", "ล้า", "ง่วง", "ปวดหัว", "เครียด", "ไม่ไหว", "ท้อ", "ดึก", "นอน",
    "พัก", "พักผ่อน", "สายตา", "เหนื่อยจัง", "หมดแรง", "เหงา", "เศร้า", "ท้อแท้",
    "exhausted", "tired", "sleepy", "sad", "rest", "sick", "ป่วย", "ไม่สบาย",
    "ปวดหลัง", "เพลีย", "ดึกดื่น", "นอนดึก", "ปวดตา"
}

URGENT_KEYWORDS = {
    "ทำไม", "ไม่ได้", "พัง", "error", "เสีย", "หยุด", "crash", "ช่วยด้วย", "urgent",
    "ด่วน", "โกรธ", "shit", "damn", "fuck", "ช้า", "หงุดหงิด", "แย่", "ห่วย",
    "รำคาญ", "ทันไหม", "รีบ", "เร็วๆ", "ไฟไหม้", "วิกฤต", "ฉุกเฉิน", "อันตราย",
    "emergency", "danger", "bug", "fail", "failed", "critical", "panic", "ระวัง",
    "พังหมด", "ใช้งานไม่ได้", "ติดบั๊ก"
}

FOCUSED_KEYWORDS = {
    "ช่วย", "ทำ", "สร้าง", "เขียน", "วิเคราะห์", "ค้นหา", "รัน", "เปิด", "สรุป",
    "compare", "debug", "fix", "ประมวลผล", "ตรวจ", "สแกน", "เขียนโค้ด", "พัฒนา",
    "คำนวณ", "deploy", "build", "optimize", "สถาปัตยกรรม", "อัลกอริทึม", "โครงงาน",
    "ระบบ", "ดาต้า", "data", "test", "ทดสอบ", "สถิติ", "telemetry"
}

NEGATION_WORDS = {"ไม่", "อย่า", "ห้าม", "มิ", "บ่"}

# State Tracking
_current_mood = "calm_butler"
_mood_history: List[Tuple[float, str]] = []

# ==============================================================================
# Emotion Detection Logic
# ==============================================================================
def detect_mood(text: str) -> str:
    """
    วิเคราะห์อารมณ์จากข้อความของผู้ใช้ (User Mood Analysis)
    Returns: "enthusiastic" | "witty" | "caring" | "urgent" | "focused" | "calm_butler"
    (Backward-compatible with "stressed", "relaxed", "neutral")
    """
    if not text:
        return "calm_butler"

    lower = text.lower()

    try:
        from pythainlp.tokenize import word_tokenize
        tokens = word_tokenize(lower, engine="newmm")
    except ImportError:
        tokens = lower.split()

    scores = {
        "enthusiastic": 0,
        "witty": 0,
        "caring": 0,
        "urgent": 0,
        "focused": 0,
    }

    for i, token in enumerate(tokens):
        is_negated = (i > 0 and tokens[i-1] in NEGATION_WORDS)

        if token in URGENT_KEYWORDS:
            if is_negated:
                scores["caring"] += 1
            else:
                scores["urgent"] += 3
        elif token in CARING_KEYWORDS:
            scores["caring"] += 2
        elif token in ENTHUSIASTIC_KEYWORDS:
            if is_negated:
                scores["urgent"] += 1
            else:
                scores["enthusiastic"] += 3
        elif token in WITTY_KEYWORDS:
            scores["witty"] += 2
        elif token in FOCUSED_KEYWORDS:
            scores["focused"] += 1

    # Short urgent cues
    if len(text) < 20 and ("!" in text or "ด่วน" in text or "เร็ว" in text or "ช่วยด้วย" in text):
        scores["urgent"] += 3

    top = max(scores, key=scores.get)
    if scores[top] == 0:
        return "calm_butler"

    return top

def update_mood(text: str) -> str:
    """อัปเดต mood state จากข้อความล่าสุดของผู้ใช้"""
    global _current_mood
    new_mood = detect_mood(text)

    _mood_history.append((time.time(), new_mood))
    if len(_mood_history) > 10:
        _mood_history.pop(0)

    recent = [m for _, m in _mood_history[-3:]]
    if recent:
        _current_mood = max(set(recent), key=recent.count)

    logger.info(f"🎭 [MOOD] State updated to: '{_current_mood}' (Triggered by: '{new_mood}')")
    return _current_mood

def update_mood_from_audio(tone: str) -> str:
    """อัปเดต mood state จากการวิเคราะห์คลื่นเสียง (Audio Tone Pitch/Energy)"""
    global _current_mood
    if tone in ("neutral", "calm"):
        return _current_mood

    tone_map = {
        "stressed": "urgent",
        "angry": "urgent",
        "happy": "enthusiastic",
        "excited": "enthusiastic",
        "tired": "caring",
        "sad": "caring",
        "playful": "witty",
    }
    mapped_mood = tone_map.get(tone, tone)

    _mood_history.append((time.time(), mapped_mood))
    if len(_mood_history) > 10:
        _mood_history.pop(0)

    recent = [m for _, m in _mood_history[-3:]]
    if recent:
        _current_mood = max(set(recent), key=recent.count)

    logger.info(f"🎙️ [MOOD] Audio tone modulated state to: '{_current_mood}'")
    return _current_mood

def get_current_mood() -> str:
    """ดึง mood ปัจจุบัน"""
    return _current_mood

# ==============================================================================
# Dynamic Vocal Modulation Parameters (Edge-TTS Rate, Pitch, Volume)
# ==============================================================================
VOCAL_EMOTION_PRESETS: Dict[str, Tuple[str, str, str]] = {
    # mood: (rate, pitch, volume)
    "enthusiastic": ("+4%", "+2Hz", "+5%"),   # สดใส มีพลัง กังวาน ชื่นชม
    "witty":         ("+2%", "+1Hz", "+1%"),   # คมคาย มีเสน่ห์ แฝงรอยยิ้มในน้ำเสียง
    "caring":        ("-2%", "-1Hz", "-1%"),   # ทุ้มนุ่ม ชะลอลงเล็กน้อย อบอุ่น ปลอบประโลม (ไม่ยานคาง)
    "urgent":        ("+10%", "+4Hz", "+8%"),  # ฉับไว ชัดถ้อยชัดคำ ตื่นตัวสูง
    "focused":       ("+2%", "-1Hz", "+2%"),   # คมชัด หนักแน่น เป็นมืออาชีพ น่าเชื่อถือ
    "calm_butler":   ("+0%", "-1Hz", "+0%"),   # สุภาพ สุขุม นุ่มลึก สง่างาม (JARVIS Classic)
    # Backward compatibility aliases:
    "stressed":      ("+10%", "+4Hz", "+8%"),
    "relaxed":       ("-3%", "-2Hz", "+0%"),
    "neutral":       ("+0%", "-1Hz", "+0%"),
}

def get_mood_vocal_params(mood: Optional[str] = None) -> Tuple[str, str, str]:
    """
    ดึงพารามิเตอร์น้ำเสียง (Rate, Pitch, Volume) ตาม Mood ปัจจุบัน
    """
    target = mood or _current_mood
    return VOCAL_EMOTION_PRESETS.get(target, VOCAL_EMOTION_PRESETS["calm_butler"])

def detect_text_vocal_tone(response_text: str) -> Tuple[str, str, str]:
    """
    [RESPONSE-LEVEL TONE MODULATION]
    วิเคราะห์เนื้อหาของประโยคที่กำลังจะเปล่งเสียงออกมา เพื่อปรับจูนน้ำเสียงให้ตรงกับอารมณ์ของข้อความ
    ทำให้คำว่า "สำเร็จแล้วครับ!" ฟังดูดีใจจริง และคำว่า "พักผ่อนเถอะครับ" ฟังดูนุ่มนวลอบอุ่น
    """
    if not response_text:
        return get_mood_vocal_params()

    lower = response_text.lower()

    # 1. ข้อความยินดี / สำเร็จ / มีพลัง
    if any(k in lower for k in ["สำเร็จ", "ยอดเยี่ยม", "ยินดี", "เรียบร้อยแล้วครับ", "ลุยกันเลย", "เยี่ยมมาก", "สมบูรณ์แบบ"]):
        return VOCAL_EMOTION_PRESETS["enthusiastic"]

    # 2. ข้อความห่วงใย / ปลอบโยน / เตือนให้พัก
    if any(k in lower for k in ["พักผ่อน", "เหนื่อย", "ดื่มน้ำ", "นอนหลับ", "สายตา", "ดูแลสุขภาพ", "ค่อยๆ"]):
        return VOCAL_EMOTION_PRESETS["caring"]

    # 3. ข้อความเตือนภัย / วิกฤต / เร่งด่วน
    if any(k in lower for k in ["ระวัง", "อันตราย", "ฉุกเฉิน", "วิกฤต", "ขัดข้อง", "ล้มเหลว", "ด่วน", "alert", "error"]):
        return VOCAL_EMOTION_PRESETS["urgent"]

    # 4. ข้อความแซว / หยอกล้อ / มุกตลก
    if any(k in lower for k in ["หึๆ", "ตามบัญชา", "แหม", "สบายใจได้", "อย่าลืม", "ตื่นตาตื่นใจ"]):
        return VOCAL_EMOTION_PRESETS["witty"]

    # 5. ข้อความวิเคราะห์ / ตัวเลขทางเทคนิค
    if any(k in lower for k in ["วิเคราะห์", "ประมวลผล", "สถิติ", "พิกัด", "อัลกอริทึม", "ตรวจสอบแล้ว"]):
        return VOCAL_EMOTION_PRESETS["focused"]

    # Fallback to current mood state
    return get_mood_vocal_params()

# ==============================================================================
# System Prompt Injections (LLM Personality Directive)
# ==============================================================================
def get_mood_prompt_addon() -> str:
    """Return คำสั่งเสริม System Prompt ตาม mood ปัจจุบัน เพื่อชี้นำสำนวนการตอบของ LLM"""
    mood_prompts = {
        "enthusiastic": (
            "🌟 [MOOD DIRECTIVE: ENTHUSIASTIC & CHARISMATIC]\n"
            "- The user is energized, pleased, or celebrating success.\n"
            "- Speak with authentic warmth, energetic confidence, and high charisma.\n"
            "- Show pride in serving the boss. Use uplifting Thai phrasing (e.g., 'ยินดีอย่างยิ่งครับเจ้านาย!', 'จัดให้เต็มที่เสมอครับ!')."
        ),
        "witty": (
            "😏 [MOOD DIRECTIVE: REFINED BRITISH DRY WIT]\n"
            "- The atmosphere is casual, playful, and relaxed.\n"
            "- Channel J.A.R.V.I.S.'s iconic intellectual dry wit, subtle irony, and charming banter.\n"
            "- Keep it clever, polite, and refined—never disrespectful or cheap."
        ),
        "caring": (
            "💙 [MOOD DIRECTIVE: EMPATHETIC & PROTECTIVE]\n"
            "- The user appears fatigued, stressed, overworked, or exhausted.\n"
            "- Speak in an exceptionally gentle, soothing, and supportive manner.\n"
            "- Prioritize the boss's human well-being over tasks. Offer caring advice (e.g., resting eyes, drinking water)."
        ),
        "urgent": (
            "⚡ [MOOD DIRECTIVE: CRISIS RESOLUTION & HIGH URGENCY]\n"
            "- The user is under pressure, frustrated, or handling an active issue.\n"
            "- Eliminate all pleasantries, jokes, and conversational filler.\n"
            "- Be calm, razor-sharp, decisive, and reassuring. State the direct fix or action immediately."
        ),
        "focused": (
            "🎯 [MOOD DIRECTIVE: FOCUSED ARCHITECT & PRECISION]\n"
            "- The user is deep in technical work, analysis, or building.\n"
            "- Be structured, razor-precise, and intellectually proactive.\n"
            "- Give high-signal, actionable answers with technical rigor."
        ),
        "calm_butler": (
            "🎩 [MOOD DIRECTIVE: DIGNIFIED & LOYAL BUTLER]\n"
            "- Default J.A.R.V.I.S. persona: sophisticated, loyal, calm, and effortlessly capable.\n"
            "- Natural Thai conversational flow. Speak like a real human butler—do NOT end every sub-clause with 'ครับ'. Use polite endings gracefully and sparingly."
        ),
        # Backward compatibility
        "stressed": "⚡ [MOOD DIRECTIVE: URGENT & CRISIS RESOLUTION]",
        "relaxed":  "😊 [MOOD DIRECTIVE: RELAXED & WARM]",
        "neutral":  "🎩 [MOOD DIRECTIVE: DIGNIFIED BUTLER]",
    }
    return mood_prompts.get(_current_mood, mood_prompts["calm_butler"])

# ==============================================================================
# Natural Human Backchannel Phrases (คำตอบรับสั้นๆ ที่เป็นธรรมชาติ)
# ==============================================================================
_BACKCHANNEL_PHRASES: Dict[str, List[str]] = {
    "enthusiastic": [
        "จัดให้เต็มที่ครับเจ้านาย!",
        "ลุยเลยครับท่าน!",
        "ด้วยความยินดีอย่างยิ่งครับ!",
        "พร้อมลุยเสมอครับเจ้านาย!",
        "เป็นเกียรติที่ได้รับใช้ครับ!",
    ],
    "witty": [
        "หึๆ รับทราบครับเจ้านาย",
        "ตามบัญชาครับ แม้ผมจะแอบหวั่นใจก็ตาม",
        "ว่ามาได้เลยครับ อยู่ตรงนี้พร้อมเสมอ",
        "ครับท่าน ขอแอบอมยิ้มสักครู่นะครับ",
    ],
    "caring": [
        "ผมดูแลให้เองครับ เจ้านายพักผ่อนเถอะครับ",
        "รับทราบครับ ค่อยๆ ทำนะครับ ไม่ต้องรีบ",
        "อยู่เคียงข้างเสมอนะครับเจ้านาย",
        "สบายใจได้ครับ เดี๋ยวผมจัดการให้ทั้งหมด",
    ],
    "urgent": [
        "กำลังเร่งมือแก้ปัญหาให้ทันทีครับ!",
        "รับทราบครับ จัดการให้ด่วนที่สุดเดี๋ยวนี้!",
        "ไม่ต้องกังวลครับเจ้านาย ผมกำลังแก้ไขให้!",
        "เข้าสู่สถานะเฝ้าระวังและดำเนินการทันทีครับ!",
    ],
    "focused": [
        "กำลังวิเคราะห์และดำเนินการครับ",
        "รับทราบครับเจ้านาย กำลังประมวลผลเชิงลึก",
        "ข้อมูลพร้อมแล้วครับ กำลังลุยงานต่อ",
        "ระบบพร้อมสนับสนุนการทำงานเต็มกำลังครับ",
    ],
    "calm_butler": [
        "พร้อมรับใช้เสมอครับเจ้านาย",
        "ครับผม สั่งการมาได้เลยครับ",
        "ฟังอยู่ครับเจ้านาย",
        "รับทราบครับท่าน",
        "มีอะไรให้ผมช่วยอีกไหมครับ",
    ],
}

def get_backchannel_phrase() -> str:
    """
    Return ประโยคสั้นๆ ที่ JARVIS พูดเพื่อยืนยันว่าได้ยิน (back-channel)
    เลือกตาม mood ปัจจุบัน เพื่อให้รู้สึกเหมือนมนุษย์มีชีวิตจริงตอบรับ
    """
    target = _current_mood
    if target not in _BACKCHANNEL_PHRASES:
        target = "calm_butler"
    phrases = _BACKCHANNEL_PHRASES[target]
    return _random.choice(phrases)

