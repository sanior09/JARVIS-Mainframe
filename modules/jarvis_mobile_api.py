"""
jarvis_mobile_api.py
========================
Mobile API Module for JARVIS Expo Go App
Handles Voice (STT), Vision, Chat, and Autonomous Hands-Free Telephony (Incoming Calls).
"""

import os
import re
import time
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any, List
from flask import Blueprint, request, jsonify, send_from_directory

logger = logging.getLogger("JarvisMobileAPI")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [MOBILE-API] %(levelname)s - %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

mobile_bp = Blueprint("mobile_api", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MOBILE_CACHE_DIR = os.path.join(BASE_DIR, "mobile_cache")
os.makedirs(MOBILE_CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Call State Management (Telephony & Hands-Free Loop)
# ---------------------------------------------------------------------------
CALL_STATE: Dict[str, Any] = {
    "call_id": None,
    "status": "idle",       # "idle", "ringing", "connected", "ended"
    "reason": "",
    "initial_message": "",
    "initial_audio_url": None,
    "created_at": 0.0,
    "last_activity": 0.0,
    "recent_bot_replies": [],
}

# ---------------------------------------------------------------------------
# Acoustic Self-Echo & Silence Suppression Helpers
# ---------------------------------------------------------------------------
def _estimate_tts_duration(text: str) -> float:
    """ประเมินระยะเวลาพูดของเสียง TTS ภาษาไทย (วินาที) เพื่อให้มือถือเว้นช่วง Guard Delay ได้ถูกต้อง"""
    if not text:
        return 1.5
    clean = re.sub(r'[^\w\s]', '', text).strip()
    return max(1.8, round(len(clean) * 0.08 + 0.8, 2))

def _remember_bot_reply(text: str) -> None:
    if not text:
        return
    replies = CALL_STATE.setdefault("recent_bot_replies", [])
    replies.append(text)
    if len(replies) > 8:
        CALL_STATE["recent_bot_replies"] = replies[-8:]

def _is_self_echo(user_text: str) -> bool:
    """
    Acoustic Self-Echo Suppression:
    ตรวจสอบว่าเสียงที่ STT จับได้ คือเสียงของ JARVIS เองที่เพิ่งดังออกจากลำโพงมือถือ
    แล้วไมค์มือถือดูดกลับเข้ามาวนลูปหรือไม่
    """
    if not user_text:
        return False

    norm_user = re.sub(r'[\s\W_]+', '', user_text.lower())
    if len(norm_user) < 3:
        return False

    # 1. ข้อความทักทายหรือตอบรับมาตรฐานของระบบ
    canned_echoes = [
        "ขออภัยครับท่านผมฟังไม่ค่อยถนัด",
        "มีอะไรให้ผมรับใช้ไหมครับ",
        "มีอะไรให้ผมช่วยไหมครับ",
        "พร้อมรับคำสั่งแล้วครับท่าน",
        "สวัสดีครับท่านเจ้านาย",
        "liveพร้อมสนทนาเสียงสดแล้ว",
        "สั่งการได้ทันทีครับ",
        "ระบบประมวลผลขัดข้องชั่วคราว",
        "รับทราบครับท่าน",
        "รับทราบครับเจ้านาย",
    ]
    for canned in canned_echoes:
        norm_canned = re.sub(r'[\s\W_]+', '', canned.lower())
        if norm_user in norm_canned or (len(norm_canned) >= 6 and norm_canned in norm_user):
            return True

    # 2. เปรียบเทียบกับคำตอบที่ JARVIS เพิ่งพูดไปในสาย
    recent_replies = CALL_STATE.get("recent_bot_replies", [])
    for past in recent_replies:
        norm_past = re.sub(r'[\s\W_]+', '', past.lower())
        if not norm_past:
            continue
        if norm_user in norm_past:
            return True
        if len(norm_past) >= 8 and norm_past in norm_user:
            return True
        # ตรวจสอบ Substring Overlap >= 65%
        if len(norm_user) >= 6 and len(norm_past) >= 6:
            for i in range(len(norm_user) - 5):
                gram = norm_user[i:i+6]
                if gram in norm_past:
                    match_len = 6
                    while i + match_len < len(norm_user) and norm_user[i:i+match_len+1] in norm_past:
                        match_len += 1
                    if (match_len / len(norm_user)) >= 0.65:
                        return True

    return False

# ---------------------------------------------------------------------------
# Helper: Whisper STT
# ---------------------------------------------------------------------------
def _transcribe_audio(audio_path: str) -> str:
    """ถอดเสียงจากไฟล์เสียงโดยใช้ Local STT"""
    try:
        from jarvis_stt_local import transcribe_audio
        text = transcribe_audio(audio_path)
        return text or ""
    except Exception as e:
        logger.error(f"Local STT error: {e}")
        return ""

# ---------------------------------------------------------------------------
# Helper: Edge-TTS Audio Generator
# ---------------------------------------------------------------------------
def _generate_tts_audio(text: str) -> Optional[str]:
    """
    สร้างไฟล์ .mp3 จากข้อความด้วย Edge-TTS (th-TH-NiwatNeural)
    และคืนค่าเป็น URL path เช่น /api/mobile/audio/tts_xxxx.mp3
    """
    if not text:
        return None
    try:
        # pyrefly: ignore [missing-import]
        import edge_tts
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
        if len(clean_text) > 400:
            clean_text = clean_text[:397] + "..."
            
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(MOBILE_CACHE_DIR, filename)
        
        async def _save():
            comm = edge_tts.Communicate(clean_text, "th-TH-NiwatNeural", rate="+0%")
            await comm.save(filepath)
            
        asyncio.run(_save())
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return f"/api/mobile/audio/{filename}"
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
    return None

# ---------------------------------------------------------------------------
# Telephony Service Functions
# ---------------------------------------------------------------------------
def trigger_call_to_boss(reason: str, message: str = "") -> dict:
    """
    สั่งให้ J.A.R.V.I.S. ยิงสายเรียกเข้าไปยังมือถือของเจ้านาย
    :param reason: เหตุผลที่โทรหา เช่น "รันสคริปต์เสร็จแล้วครับท่าน"
    :param message: ข้อความเปิดการสนทนา
    """
    call_id = uuid.uuid4().hex[:8]
    initial_msg = message or f"ขออภัยที่รบกวนครับท่านเจ้านาย {reason} มีคำสั่งให้ผมดำเนินการต่อเลยไหมครับ?"
    _remember_bot_reply(initial_msg)
    audio_url = _generate_tts_audio(initial_msg)
    
    CALL_STATE["call_id"] = call_id
    CALL_STATE["status"] = "ringing"
    CALL_STATE["reason"] = reason
    CALL_STATE["initial_message"] = initial_msg
    CALL_STATE["initial_audio_url"] = audio_url
    CALL_STATE["created_at"] = time.time()
    CALL_STATE["last_activity"] = time.time()
    
    logger.info(f"[CALL DISPATCHER] Initiated Outbound Call: call_id={call_id}, reason='{reason}'")
    return CALL_STATE

# ---------------------------------------------------------------------------
# Audio Serving Route
# ---------------------------------------------------------------------------
@mobile_bp.route("/api/mobile/audio/<filename>", methods=["GET"])
def get_mobile_audio(filename):
    """สตรีมไฟล์เสียง mp3 ไปยังมือถือ"""
    return send_from_directory(MOBILE_CACHE_DIR, filename, mimetype="audio/mpeg")

# ---------------------------------------------------------------------------
# Telephony Endpoints
# ---------------------------------------------------------------------------
@mobile_bp.route("/api/mobile/call_status", methods=["GET"])
def get_call_status():
    """
    มือถือดึงข้อมูลสถานะสายโทรศัพท์แบบ Real-time
    """
    # Auto-timeout ringing after 60s
    if CALL_STATE["status"] == "ringing" and (time.time() - CALL_STATE["created_at"] > 60):
        CALL_STATE["status"] = "idle"
        logger.info("[CALL DISPATCHER] Call timed out (missed call).")

    return jsonify({
        "status": "success",
        "call_id": CALL_STATE["call_id"],
        "call_status": CALL_STATE["status"],
        "reason": CALL_STATE["reason"],
        "initial_message": CALL_STATE["initial_message"],
        "initial_audio_url": CALL_STATE["initial_audio_url"],
    })

@mobile_bp.route("/api/mobile/call_trigger", methods=["POST"])
def api_call_trigger():
    """
    Endpoint ให้ระบบภายในสั่งโทรหามือถือ
    JSON: { "reason": "...", "message": "..." }
    """
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "มีรายงานสำคัญจากระบบครับ")
    msg = data.get("message", "")
    res = trigger_call_to_boss(reason, msg)
    return jsonify({"status": "success", "call": res})

@mobile_bp.route("/api/mobile/call_answer", methods=["POST"])
def api_call_answer():
    """
    เจ้านายกดปุ่มรับสายบนมือถือ
    """
    CALL_STATE["status"] = "connected"
    CALL_STATE["last_activity"] = time.time()
    logger.info(f"[CALL DISPATCHER] Boss answered call: {CALL_STATE['call_id']}")
    return jsonify({
        "status": "success",
        "call_status": "connected",
        "initial_message": CALL_STATE["initial_message"],
        "initial_audio_url": CALL_STATE["initial_audio_url"],
    })

@mobile_bp.route("/api/mobile/call_hangup", methods=["POST"])
def api_call_hangup():
    """
    เจ้านายกดวางสาย หรือระบบตัดสาย
    """
    logger.info(f"[CALL DISPATCHER] Call ended: {CALL_STATE['call_id']}")
    CALL_STATE["status"] = "idle"
    CALL_STATE["call_id"] = None
    CALL_STATE["reason"] = ""
    CALL_STATE["recent_bot_replies"] = []
    return jsonify({"status": "success", "call_status": "idle"})

@mobile_bp.route("/api/mobile/call_turn", methods=["POST"])
def api_call_turn():
    """
    รอบการสนทนาสดในสาย (Hands-Free Loop Turn):
    รับไฟล์เสียงพูดจากมือถือ -> ถอดเสียง STT -> ตรวจจับและระงับ Acoustic Self-Echo -> ส่ง LLM -> คืนค่าเสียงตอบกลับ
    """
    CALL_STATE["last_activity"] = time.time()
    audio_file = request.files.get("audio")
    json_data = request.get_json(silent=True) or {}
    text_input = (request.form.get("text", "") or json_data.get("text", "")).strip()

    if audio_file:
        audio_filename = f"call_voice_{uuid.uuid4().hex[:6]}.m4a"
        audio_path = os.path.join(MOBILE_CACHE_DIR, audio_filename)
        audio_file.save(audio_path)
        logger.info(f"[CALL TURN] Received voice: {audio_filename}")
        
        try:
            stt_text = _transcribe_audio(audio_path)
            if stt_text:
                text_input = stt_text.strip()
            else:
                text_input = ""
        finally:
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

    # 1. จัดการกรณีเงียบ หรือไม่มีเสียงพูด (Silence Handling)
    # คืนค่าเงียบเพื่อป้องกันการตอบซ้ำเอง (Anti-Infinite Loop)
    if not text_input:
        logger.info("[CALL TURN] Silent / Inaudible audio — listening continuously without speaking.")
        return jsonify({
            "status": "success",
            "call_status": "connected",
            "user_text": "",
            "reply": "",
            "audio_url": None,
            "estimated_duration": 0,
            "is_silent_turn": True,
            "is_hangup": False
        })

    # 2. ตรวจจับและระงับเสียงสะท้อนตัวเอง (Acoustic Self-Echo Suppression)
    if _is_self_echo(text_input):
        logger.warning(f"[CALL TURN] 🔇 Suppressed acoustic self-echo from speaker: '{text_input}' — ignored.")
        return jsonify({
            "status": "success",
            "call_status": "connected",
            "user_text": "",
            "reply": "",
            "audio_url": None,
            "estimated_duration": 0,
            "is_silent_turn": True,
            "is_hangup": False
        })

    logger.info(f"[CALL TURN] 👤 Boss said: '{text_input}'")

    # 3. ตรวจสอบเจตนาวางสาย
    hangup_keywords = ["วางสาย", "แค่นี้แหละ", "ขอบใจ", "ขอบคุณมาก", "พอแล้ว", "บาย", "ไม่มีอะไรแล้ว", "goodbye", "bye", "hang up", "เลิกคุย"]
    is_hangup = any(kw in text_input.lower() for kw in hangup_keywords)

    if is_hangup:
        farewell = "รับทราบครับเจ้านาย ขอให้มีความสุขกับกิจกรรมครับ แล้วผมจะดูแลระบบที่นี่ให้ครับ"
        _remember_bot_reply(farewell)
        audio_url = _generate_tts_audio(farewell)
        duration = _estimate_tts_duration(farewell)
        CALL_STATE["status"] = "ended"
        return jsonify({
            "status": "success",
            "call_status": "ended",
            "user_text": text_input,
            "reply": farewell,
            "audio_url": audio_url,
            "estimated_duration": duration,
            "is_silent_turn": False,
            "is_hangup": True
        })

    # 4. ประมวลผลคำสั่งผ่าน Core LLM
    try:
        from jarvis import handle_chat_logic
        raw_res = handle_chat_logic({"message": text_input})
        if hasattr(raw_res, "get_json"):
            res_data = raw_res.get_json() or {}
        elif isinstance(raw_res, tuple) and hasattr(raw_res[0], "get_json"):
            res_data = raw_res[0].get_json() or {}
        elif isinstance(raw_res, dict):
            res_data = raw_res
        else:
            res_data = {}

        reply = res_data.get("response") or res_data.get("reply") or res_data.get("message") or "รับทราบครับท่าน"
        _remember_bot_reply(reply)
        audio_url = _generate_tts_audio(reply)
        duration = _estimate_tts_duration(reply)

        return jsonify({
            "status": "success",
            "call_status": "connected",
            "user_text": text_input,
            "reply": reply,
            "audio_url": audio_url,
            "estimated_duration": duration,
            "is_silent_turn": False,
            "is_hangup": False
        })
    except Exception as e:
        logger.error(f"[CALL TURN ERROR]: {e}")
        err_reply = "ระบบประมวลผลขัดข้องชั่วคราวครับท่าน"
        _remember_bot_reply(err_reply)
        return jsonify({
            "status": "success",
            "call_status": "connected",
            "user_text": text_input,
            "reply": err_reply,
            "audio_url": _generate_tts_audio(err_reply),
            "estimated_duration": 2.2,
            "is_silent_turn": False,
            "is_hangup": False
        })

# ---------------------------------------------------------------------------
# Standard Mobile Chat / Vision API Endpoint
# ---------------------------------------------------------------------------
@mobile_bp.route("/api/mobile/converse", methods=["POST"])
def mobile_converse():
    """
    รับคำสั่งจากมือถือ (Voice, Vision, Text)
    รองรับพารามิเตอร์ speak เพื่อเลือกให้ส่งเสียงพูดกลับหรือไม่
    """
    logger.info("Received request from Mobile App.")
    
    json_data = request.get_json(silent=True) or {}
    text_input = (request.form.get("text", "") or json_data.get("text", "")).strip()
    audio_file = request.files.get("audio")
    image_file = request.files.get("image")

    # กำหนดว่าจะสังเคราะห์เสียงพูดตอบกลับหรือไม่ (Default: ถ้าส่งไฟล์เสียงมาให้ตอบเป็นเสียง ถ้าเป็นข้อความตัวหนังสือให้ตอบแบบเงียบ)
    raw_speak = request.form.get("speak", json_data.get("speak", None))
    if raw_speak is not None:
        should_speak = str(raw_speak).lower() in ["true", "1", "yes"]
    else:
        should_speak = bool(audio_file)
    
    if audio_file:
        audio_filename = f"mobile_voice_{uuid.uuid4().hex[:6]}.m4a"
        audio_path = os.path.join(MOBILE_CACHE_DIR, audio_filename)
        audio_file.save(audio_path)
        logger.info(f"Processing audio: {audio_filename}")
        
        stt_text = _transcribe_audio(audio_path)
        if not stt_text:
            return jsonify({"status": "error", "message": "ไม่สามารถถอดเสียงได้ครับ"}), 400
        text_input = stt_text
        
    doc_file = request.files.get("file")
    image_path = None
    
    if image_file:
        import base64
        image_bytes = image_file.read()
        try:
            from PIL import Image
            import io
            p_img = Image.open(io.BytesIO(image_bytes))
            if p_img.mode in ("RGBA", "P"):
                p_img = p_img.convert("RGB")
            p_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            p_img.save(out_buf, format="JPEG", quality=70, optimize=True)
            image_b64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")
        except Exception:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_filename = f"mobile_vision_{uuid.uuid4().hex[:6]}.jpg"
        image_path = os.path.join(MOBILE_CACHE_DIR, image_filename)
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Saved vision image: {image_filename}")
        
        prompt = text_input or "ช่วยวิเคราะห์ภาพนี้อย่างละเอียด และตอบเป็นภาษาไทยครับ"
        try:
            from jarvis import analyze_spatial_environment
            ai_response = analyze_spatial_environment(image_b64, prompt)
            audio_url = _generate_tts_audio(ai_response) if should_speak else None
            return jsonify({
                "status": "success",
                "user_text": text_input or "ส่งรูปภาพ",
                "reply": ai_response,
                "audio_url": audio_url,
                "has_image": True
            })
        except Exception as vision_err:
            logger.error(f"Vision analysis failed: {vision_err}")
            text_input = f"[รูปภาพ: {image_filename}] {prompt}"

    if doc_file:
        doc_filename = f"mobile_doc_{uuid.uuid4().hex[:6]}_{doc_file.filename}"
        doc_path = os.path.join(MOBILE_CACHE_DIR, doc_filename)
        doc_file.save(doc_path)
        logger.info(f"Saved doc file: {doc_filename}")
        
        doc_text = ""
        try:
            ext = os.path.splitext(doc_filename)[1].lower()
            if ext in ['.txt', '.md', '.py', '.json', '.csv', '.html', '.css', '.js', '.yaml', '.yml', '.xml']:
                with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
                    doc_text = f.read(6000)
            elif ext == '.pdf':
                try:
                    # pyrefly: ignore [missing-import]
                    import pymupdf as fitz
                except ImportError:
                    # pyrefly: ignore [missing-import]
                    import fitz
                pdf_doc = fitz.open(doc_path)
                doc_text = "\n".join([str(page.get_text()) for page in pdf_doc[:5]])
        except Exception as read_err:
            logger.warning(f"Could not extract doc text: {read_err}")
            
        doc_context = f"--- ข้อมูลจากไฟล์: {doc_file.filename} ---\n{doc_text}\n\n" if doc_text else f"[แนบไฟล์: {doc_file.filename}]\n\n"
        text_input = f"{doc_context}คำสั่งของเจ้านาย: {text_input or 'ช่วยสรุปหรือวิเคราะห์เนื้อหาในไฟล์นี้ให้หน่อยครับ'}"
            
    if not text_input and not image_path:
        return jsonify({"status": "error", "message": "No input provided."}), 400
        
    try:
        from jarvis import handle_chat_logic
        
        raw_res = handle_chat_logic({"message": text_input})
        if hasattr(raw_res, "get_json"):
            res_data = raw_res.get_json() or {}
        elif isinstance(raw_res, tuple) and hasattr(raw_res[0], "get_json"):
            res_data = raw_res[0].get_json() or {}
        elif isinstance(raw_res, dict):
            res_data = raw_res
        else:
            res_data = {}

        ai_response = res_data.get("response") or res_data.get("reply") or res_data.get("message") or "รับทราบครับท่าน"
        audio_url = _generate_tts_audio(ai_response) if should_speak else None
        
        return jsonify({
            "status": "success",
            "user_text": text_input,
            "reply": ai_response,
            "audio_url": audio_url,
            "has_image": bool(image_path)
        })
        
    except Exception as e:
        logger.error(f"Mobile API Core Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def register_mobile_routes(app):
    """ลงทะเบียน Blueprint เข้าสู่ Flask Server หลัก"""
    app.register_blueprint(mobile_bp)
    logger.info("[MOBILE API] Routes registered successfully with Telephony Engine.")
