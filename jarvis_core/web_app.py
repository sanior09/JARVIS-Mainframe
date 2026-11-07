"""
jarvis_core.web_app
===================
Flask Web Application Factory and API route registry for J.A.R.V.I.S.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context
from flask_cors import CORS

from jarvis_core.config import STATIC_DIR, TEMPLATES_DIR, BASE_DIR
from jarvis_core.state import get_telemetry_snapshot, update_core_telemetry
from jarvis_core.automation_agent import get_computer_agent

logger = logging.getLogger("JarvisWebApp")


def create_app() -> Flask:
    """Factory creating and configuring the central Flask app."""
    app = Flask(
        __name__,
        static_folder=STATIC_DIR,
        template_folder=TEMPLATES_DIR,
    )
    CORS(app)

    # ----------------------------------------------------
    # JARVIS Cyber-Defense Layer: Network & API Security
    # ----------------------------------------------------
    @app.before_request
    def enforce_security_protocols():
        # 1. Localhost Lockdown
        allowed_ips = ["127.0.0.1", "::1"]
        if request.remote_addr not in allowed_ips:
            logger.warning(f"[SECURITY ALERT] Blocked external access from IP: {request.remote_addr}")
            return jsonify({
                "status": "error", 
                "message": "ACCESS DENIED: External connections are blocked by JARVIS Security Protocol."
            }), 403

        # 2. API Token Authentication (if JARVIS_SECURE_MODE is enabled)
        if os.environ.get("JARVIS_SECURE_MODE", "False").lower() == "true":
            # Skip check for basic frontend routes
            if request.path in ["/", "/favicon.ico"] or request.path.startswith("/temp_images/"):
                return
            
            token = request.headers.get("X-Jarvis-Security-Token")
            expected_token = os.environ.get("JARVIS_SECURITY_TOKEN", "strict-jarvis-auth-token")
            if token != expected_token:
                logger.warning(f"[SECURITY ALERT] Unauthorized API attempt on {request.path}")
                return jsonify({
                    "status": "error", 
                    "message": "ACCESS DENIED: Invalid or missing Security Token."
                }), 401

    # ----------------------------------------------------
    # Index & Static File Routes
    # ----------------------------------------------------
    @app.route("/")
    def index():
        try:
            return render_template("tactical.html")
        except Exception:
            return jsonify({
                "system": "J.A.R.V.I.S. Core Operating System",
                "status": "Online",
                "version": "3.0.0",
                "endpoints": ["/chat", "/api/voice/status", "/api/telemetry", "/api/status", "/api/computer/execute"]
            })

    @app.route("/favicon.ico")
    def favicon():
        fav_path = os.path.join(STATIC_DIR, "favicon.ico")
        if os.path.exists(fav_path):
            return send_from_directory(STATIC_DIR, "favicon.ico")
        return "", 204

    @app.route("/temp_images/<path:filename>")
    def serve_temp_images(filename):
        temp_dir = os.path.join(BASE_DIR, "temp_images")
        return send_from_directory(temp_dir, filename)

    # ----------------------------------------------------
    # System Status & Telemetry
    # ----------------------------------------------------
    @app.route("/api/status", methods=["GET"])
    def api_status():
        return jsonify({
            "status": "online",
            "message": "J.A.R.V.I.S. Core Engine is operating at peak efficiency.",
            "timestamp": time.time(),
        })

    @app.route("/api/telemetry", methods=["GET"])
    def api_telemetry():
        return jsonify(get_telemetry_snapshot())

    @app.route("/api/neuro_status", methods=["GET"])
    def api_neuro_status():
        telemetry = get_telemetry_snapshot()
        return jsonify({
            "neuro_state": "Synchronized",
            "active_cores": telemetry.get("cores", {}),
            "status": "Optimal",
        })

    # ----------------------------------------------------
    # Voice Subsystem API
    # ----------------------------------------------------
    @app.route("/api/voice/status", methods=["GET"])
    def api_voice_status():
        import jarvis_core.state as state
        ve = state.voice_engine
        if ve is None:
            return jsonify({
                "initialized": False,
                "is_listening": False,
                "is_busy": False,
                "tts_voice": "th-TH-NiwatNeural",
            })
        
        is_listening = getattr(getattr(ve, "_stt", None), "is_listening", False)
        is_busy = getattr(ve, "is_busy", False)
        tts_voice = getattr(getattr(ve, "_tts", None), "voice", "th-TH-NiwatNeural")
        
        return jsonify({
            "initialized": True,
            "is_listening": is_listening,
            "is_busy": is_busy,
            "tts_voice": tts_voice,
        })

    @app.route("/api/voice/trigger", methods=["POST"])
    def api_voice_trigger():
        import jarvis_core.state as state
        ve = state.voice_engine
        if ve and hasattr(ve, "trigger_voice_input"):
            ve.trigger_voice_input()
            return jsonify({"status": "success", "message": "Voice input triggered."})
        return jsonify({"status": "error", "message": "Voice engine not ready."}), 503

    @app.route("/api/voice/say", methods=["POST"])
    def api_voice_say():
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"status": "error", "message": "Missing text parameter."}), 400

        import jarvis_core.state as state
        ve = state.voice_engine
        if ve and hasattr(ve, "speak_direct"):
            ve.speak_direct(text)
            return jsonify({"status": "success", "message": f"Speaking: {text[:40]}"})
        return jsonify({"status": "error", "message": "Voice engine not ready."}), 503

    @app.route("/api/voice/text", methods=["POST"])
    def api_voice_text():
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"status": "error", "message": "Missing text parameter."}), 400

        import jarvis_core.state as state
        ve = state.voice_engine
        if ve and hasattr(ve, "trigger_text_input"):
            ve.trigger_text_input(text)
            return jsonify({"status": "success", "message": f"Text input queued: {text[:40]}"})
        return jsonify({"status": "error", "message": "Voice engine not ready."}), 503

    # ----------------------------------------------------
    # Computer Use / Automation Agent API
    # ----------------------------------------------------
    @app.route("/api/computer/execute", methods=["POST"])
    def api_computer_execute():
        data = request.get_json(silent=True) or {}
        goal = data.get("goal") or data.get("command") or data.get("task")
        if not goal:
            return jsonify({"status": "error", "message": "Missing 'goal' or 'command' in request."}), 400

        agent = get_computer_agent()
        result = agent.execute_goal(goal)
        return jsonify(result)

    @app.route("/api/computer/windows", methods=["GET"])
    def api_computer_windows():
        agent = get_computer_agent()
        active = agent.get_active_window()
        windows = agent.list_open_windows()
        return jsonify({
            "active_window": active.__dict__ if active else None,
            "total_windows": len(windows),
            "windows": [w.__dict__ for w in windows],
        })

    @app.route("/api/computer/screenshot", methods=["GET"])
    def api_computer_screenshot():
        agent = get_computer_agent()
        b64_img = agent.get_screenshot_base64()
        return jsonify({
            "status": "success",
            "image_base64": b64_img,
            "width": agent.screen_width,
            "height": agent.screen_height,
        })

    # ----------------------------------------------------
    # Chat & Cognitive Router
    # ----------------------------------------------------
    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "")
        if not user_message:
            return jsonify({"response": "ขออภัยครับเจ้านาย ข้อความว่างเปล่าครับ"})

        # Route through cognitive engine
        try:
            req_model = (data.get("model") or "").lower()
            from jarvis_core.ai_router import call_groq_model, call_gemini_fallback, call_ollama_fallback
            if "gemini" in req_model:
                response = call_gemini_fallback([{"role": "user", "content": user_message}])
            elif "ollama" in req_model or "local" in req_model:
                response = call_ollama_fallback([{"role": "user", "content": user_message}])
            else:
                response = call_groq_model([{"role": "user", "content": user_message}])

            reply_text = response.get("content") or response.get("error_message") or "รับทราบครับ กำลังประมวลผลคำสั่ง"
            return jsonify({"response": reply_text})
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return jsonify({"response": f"ขออภัยครับเจ้านาย เกิดข้อขัดข้อง: {e}"})

    @app.route("/api/feedback", methods=["POST"])
    def api_feedback():
        data = request.get_json(silent=True) or {}
        logger.info(f"Received user feedback: {data}")
        return jsonify({"status": "success", "message": "Feedback recorded."})

    @app.route("/api/ai_quota", methods=["GET"])
    def api_ai_quota():
        try:
            from modules.ai_quota_tracker import get_quota_stats
            return jsonify(get_quota_stats())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/spatial/ar_recon", methods=["POST"])
    def api_spatial_ar_recon():
        """[SPATIAL AR WORKBENCH] Endpoint สแกนวิเคราะห์วัตถุบนโต๊ะและกาง HUD เลนส์ AR เต็มรูปแบบ"""
        try:
            data = request.get_json(silent=True) or {}
            img_b64 = data.get("image") or data.get("image_base64", "")
            user_prompt = data.get("prompt") or data.get("query", "หาข้อมูลเกี่ยวกับสิ่งนี้ให้หน่อย")
            if not img_b64:
                return jsonify({"success": False, "error": "No image payload provided"}), 400

            from modules.spatial_ar_workbench import spatial_ar_workbench
            result = spatial_ar_workbench.analyze_desk_object(img_b64, user_prompt)
            return jsonify(result)
        except Exception as e:
            logger.error(f"[SPATIAL AR] API error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

    return app
