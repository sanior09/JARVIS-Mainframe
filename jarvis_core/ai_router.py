"""
jarvis_core/ai_router.py
─────────────────────────────────────────────────────
Centralized AI LLM Router for J.A.R.V.I.S.
Handles: Groq (primary) → Gemini (fallback) → Ollama (local fallback)
Includes: Reflex SLM fast-track, Deep Thought interception, Circuit Breaker integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("JARVIS")

import queue
ACTIVE_STREAM_QUEUE: Optional[queue.Queue] = None



# ──────────────────────────────────────────────────────────────────────────────
# Groq API caller
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_tool_calls(raw_tool_calls: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
    if not raw_tool_calls:
        return None
    normalized = []
    for tc in raw_tool_calls:
        if not isinstance(tc, dict):
            continue
        tc_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
        if "function" in tc and isinstance(tc["function"], dict):
            fn_name = tc["function"].get("name") or tc.get("name", "")
            raw_args = tc["function"].get("arguments", "{}")
        else:
            fn_name = tc.get("name", "")
            raw_args = tc.get("args", {})

        if isinstance(raw_args, (dict, list)):
            fn_args = json.dumps(raw_args, ensure_ascii=False)
        elif raw_args is None:
            fn_args = "{}"
        else:
            fn_args = str(raw_args)

        normalized.append({
            "id": str(tc_id),
            "type": "function",
            "function": {
                "name": str(fn_name),
                "arguments": fn_args
            }
        })
    return normalized or None


def call_groq_model(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call the Groq Cloud API (Whisper Large / Llama models).

    Args:
        messages: List of message dicts with 'role' and 'content'.
        tools:    Optional list of tool definitions for function calling.
        model:    Model override string. Defaults to env GROQ_MODEL.

    Returns:
        Dict with keys 'content' (str) and 'tool_calls' (list), or 'error_message'.
    """
    import re
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return {"error_message": "GROQ_API_KEY not configured"}

    selected_model = model or os.getenv("GROQ_MODEL") or os.getenv("GROQ_DEFAULT_MODEL") or "qwen/qwen3.8-27b"
    client = Groq(api_key=api_key)

    serialised = []
    has_image = False
    for m in messages:
        if isinstance(m, dict):
            raw_role = m.get("role", "user")
            content = m.get("content", "")
            raw_tool_calls = m.get("tool_calls")
            tool_call_id = m.get("tool_call_id")
        else:
            raw_role = getattr(m, "type", "user")
            content = getattr(m, "content", "")
            raw_tool_calls = getattr(m, "tool_calls", None)
            tool_call_id = getattr(m, "tool_call_id", None)

        raw_role = str(raw_role).lower()
        if raw_role in {"human", "user"}:
            role = "user"
        elif raw_role in {"ai", "assistant", "model"}:
            role = "assistant"
        elif raw_role == "system":
            role = "system"
        elif raw_role in {"tool", "function"}:
            role = "tool"
        else:
            role = "user"

        if isinstance(content, list):
            is_multimodal = any(isinstance(c, dict) and c.get("type") in ("image_url", "text") for c in content)
            if is_multimodal:
                has_image = True
                norm_content = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "image_url":
                            img_url_data = c.get("image_url", {}).get("url", "")
                            if "data:image" in img_url_data and ";base64," in img_url_data:
                                try:
                                    header, b64_data = img_url_data.split(";base64,", 1)
                                    if len(b64_data) > 200000:
                                        from PIL import Image
                                        import io
                                        import base64 as _b64
                                        raw_b = _b64.b64decode(b64_data)
                                        p_img = Image.open(io.BytesIO(raw_b))
                                        if p_img.mode in ("RGBA", "P"):
                                            p_img = p_img.convert("RGB")
                                        p_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                                        out_buf = io.BytesIO()
                                        p_img.save(out_buf, format="JPEG", quality=70, optimize=True)
                                        new_b64 = _b64.b64encode(out_buf.getvalue()).decode("utf-8")
                                        c = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{new_b64}"}}
                                except Exception as opt_e:
                                    logger.warning(f"[ROUTER] Image recompress failed: {opt_e}")
                        norm_content.append(c)
                    else:
                        norm_content.append({"type": "text", "text": str(c)})
                item = {"role": role, "content": norm_content}
            else:
                item = {"role": role, "content": str(content)}
        else:
            item = {"role": role, "content": str(content) if content is not None else ""}

        if role == "tool" and tool_call_id:
            item["tool_call_id"] = str(tool_call_id)
        if raw_tool_calls and role == "assistant":
            norm_tc = _normalize_tool_calls(raw_tool_calls)
            if norm_tc:
                item["tool_calls"] = norm_tc
        serialised.append(item)

    kwargs: Dict[str, Any] = {
        "messages": serialised,
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    if tools and not has_image:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    if has_image:
        candidate_list = ["qwen/qwen3.8-27b"]
    else:
        model_candidates = [
            selected_model,
            os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b"),
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ]
        seen: set[str] = set()
        candidate_list = [m for m in model_candidates if m and not (m in seen or seen.add(m))]

    last_err: Optional[Exception] = None
    for candidate_model in candidate_list:
        kwargs["model"] = candidate_model
        try:
            if ACTIVE_STREAM_QUEUE is not None and not kwargs.get("tools"):
                kwargs["stream"] = True
                response = client.chat.completions.create(**kwargs)
                message_content = ""
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        ACTIVE_STREAM_QUEUE.put(delta.content)
                        message_content += delta.content
                ACTIVE_STREAM_QUEUE.put("[DONE_LLM]")
                return {"content": message_content.strip(), "tool_calls": []}
            else:
                response = client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message_content = choice.message.content or ""
                message_content = re.sub(r"<think>.*?</think>", "", message_content, flags=re.DOTALL).strip()
    
                raw_tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        raw_tool_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        })
    
                return {"content": message_content, "tool_calls": raw_tool_calls}
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "overloaded" in err_str or "503" in err_str:
                logger.warning(f"[GROQ THROTTLE] 429 / busy on {candidate_model}. Auto fast-swapping to next model in pool...")
            else:
                logger.warning(f"[GROQ RETRY] Error on {candidate_model}: {e}. Trying next candidate model...")
            continue

    logger.error(f"Groq API Processing Error: All Groq models failed. Last error: {last_err}")
    return {"error_message": f"Groq Cloud Connection Error: {str(last_err)}"}


# ──────────────────────────────────────────────────────────────────────────────
# Gemini fallback
# ──────────────────────────────────────────────────────────────────────────────

def call_gemini_fallback(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Fallback to Google Gemini when Groq is unavailable.

    Args:
        messages: Conversation history.
        tools:    Tool definitions (ignored in this fallback – Gemini format differs).

    Returns:
        Dict with 'content' and empty 'tool_calls', or raises ValueError.
    """
    from dotenv import load_dotenv  # noqa: PLC0415
    load_dotenv(override=True)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or "YOUR_GEMINI" in gemini_key or gemini_key.startswith("YOUR_") or len(gemini_key) < 20:
        raise ValueError("GEMINI_API_KEY not configured or is placeholder")

    from google import genai
    from google.genai import types
    import base64 as _b64

    client = genai.Client(api_key=gemini_key)
    gemini_contents = []

    for m in messages:
        if isinstance(m, dict):
            raw_role = m.get("role", "user")
            content = m.get("content", "")
        else:
            raw_role = getattr(m, "type", "user")
            content = getattr(m, "content", "")

        role = "model" if raw_role in {"ai", "assistant", "model"} else "user"

        if raw_role == "system":
            if not gemini_contents:
                gemini_contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=f"System Context: {content}")])
                )
            continue

        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "image_url":
                        img_url = c.get("image_url", {}).get("url", "")
                        if ";base64," in img_url:
                            b64_part = img_url.split(";base64,", 1)[1]
                            parts.append(types.Part.from_bytes(data=_b64.b64decode(b64_part), mime_type="image/jpeg"))
                    elif c.get("type") == "text":
                        parts.append(types.Part.from_text(text=c.get("text", "")))
                else:
                    parts.append(types.Part.from_text(text=str(c)))
            if parts:
                gemini_contents.append(types.Content(role=role, parts=parts))
        else:
            gemini_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(content))]))

    if not gemini_contents:
        gemini_contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Hello")]))

    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=gemini_contents
            )
            response = future.result(timeout=25)
        return {"content": f"[GEMINI FALLBACK]\n{response.text.strip()}", "tool_calls": []}
    except concurrent.futures.TimeoutError as e:
        raise ValueError(f"Gemini API Timeout: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Gemini SDK Error: {e}") from e


# ──────────────────────────────────────────────────────────────────────────────
# Ollama local fallback
# ──────────────────────────────────────────────────────────────────────────────

def call_ollama_fallback(
    messages: List[Dict[str, Any]],
    model: str = "llama3",
) -> Dict[str, Any]:
    """
    Last-resort local Ollama fallback when cloud services are unavailable.

    Args:
        messages: Conversation history.
        model:    Ollama model to use.

    Returns:
        Dict with 'content' and empty 'tool_calls', or 'error_message'.
    """
    import requests  # noqa: PLC0415

    def _extract_str(m: Any) -> str:
        c = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if isinstance(c, list):
            return " ".join(item.get("text", "") for item in c if isinstance(item, dict) and item.get("type") == "text")
        return str(c) if c is not None else ""

    prompt = "\n".join(_extract_str(m) for m in messages)
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if res.status_code == 200:
            return {"content": res.json().get("response", "[OLLAMA] พร้อมรับใช้ครับเจ้านาย"), "tool_calls": []}
        return {"error_message": f"Ollama HTTP {res.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error_message": f"Ollama connection failed: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# Reflex SLM fast-track
# ──────────────────────────────────────────────────────────────────────────────

_REFLEX_HARDCODED: List[Dict[str, Any]] = [
    {
        "keywords": {"เปิดโหมดเฝ้าบ้าน", "เปิดระบบรักษาความปลอดภัย"},
        "content": "ระบบเฝ้าบ้าน ทำงานครับเจ้านาย 🛡️",
        "tool": "toggle_guard_mode",
        "args": '{"action":"start"}',
        "call_id": "call_fast_guard_on",
    },
    {
        "keywords": {"ปิดโหมดเฝ้าบ้าน", "ปิดระบบรักษาความปลอดภัย"},
        "content": "ปิดระบบเฝ้าบ้านเรียบร้อยครับ 🛑",
        "tool": "toggle_guard_mode",
        "args": '{"action":"stop"}',
        "call_id": "call_fast_guard_off",
    },
    {
        "keywords": {"เปิดไฟ", "เปิดแสง"},
        "content": "เปิดไฟให้แล้วครับเจ้านาย",
        "tool": "toggle_home_assistant_device",
        "args": '{"entity_id":"light.iwachi_wifi_smart_bulb","action":"turn_on"}',
        "call_id": "call_fast_light_on",
    },
    {
        "keywords": {"ปิดไฟ", "ปิดแสง"},
        "content": "ปิดไฟให้แล้วครับเจ้านาย",
        "tool": "toggle_home_assistant_device",
        "args": '{"entity_id":"light.iwachi_wifi_smart_bulb","action":"turn_off"}',
        "call_id": "call_fast_light_off",
    },
]


def _try_reflex_hardcoded(query: str) -> Optional[Dict[str, Any]]:
    """
    Match query against hardcoded reflex table (O(n) keyword scan).

    Args:
        query: Raw user query string.

    Returns:
        Pre-built response dict if matched, else None.
    """
    lower = query.lower()
    for rule in _REFLEX_HARDCODED:
        if any(kw in lower for kw in rule["keywords"]):
            logger.info(f"🧠 [REFLEX] Hardcoded action matched: {rule['tool']}")
            return {
                "content": rule["content"],
                "tool_calls": [{
                    "id": rule["call_id"],
                    "type": "function",
                    "function": {"name": rule["tool"], "arguments": rule["args"]},
                }],
            }
    return None


def _try_reflex_slm(query: str) -> Optional[Dict[str, Any]]:
    """
    Attempt ultra-fast local SLM response (Ollama qwen:4b, timeout 1.5s).

    Args:
        query: Short user query.

    Returns:
        Response dict if successful, else None.
    """
    import requests  # noqa: PLC0415

    SKIP_KEYWORDS = {"เปิด", "ปิด", "เช็ค", "รัน", "ค้นหา"}
    if len(query) > 25 or any(kw in query.lower() for kw in SKIP_KEYWORDS):
        return None

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen:4b", "prompt": f"You are JARVIS. ตอบสั้นๆ เป็นภาษาไทย 1 ประโยค: {query}", "stream": False},
            timeout=1.5,
        )
        if resp.status_code == 200:
            ans = resp.json().get("response", "")
            logger.info(f"🧠 [REFLEX SLM] Fast response: {ans}")
            return {"content": ans, "tool_calls": []}
    except requests.exceptions.RequestException:
        logger.debug("[REFLEX SLM] Skipped — Ollama unavailable or timed out")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Main router (call_nachapol_core)
# ──────────────────────────────────────────────────────────────────────────────

def call_nachapol_core(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict]] = None,
    model: Optional[str] = None,
    deep_thought=None,
) -> Dict[str, Any]:
    """
    Central LLM router for J.A.R.V.I.S. with multi-layer fallback strategy.

    Priority chain:
        1. Reflex hardcoded fast-track  (< 1 ms)
        2. Local SLM (qwen:4b / Ollama) (< 1.5 s)
        3. Deep Thought subsystem       (for complex reasoning queries)
        4. Groq Cloud (primary LLM)     via Circuit Breaker
        5. Gemini (cloud fallback)
        6. Ollama llama3 (local fallback)

    Args:
        messages:    Conversation history.
        tools:       Tool definitions for function-calling.
        model:       Model override.
        deep_thought: Deep-thought subsystem instance (optional, injected at runtime).

    Returns:
        Dict with 'content' and 'tool_calls', or 'error_message' on total failure.
    """
    try:
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "user":
            user_content = messages[-1].get("content", "")
            if isinstance(user_content, list):
                user_text = " ".join(c.get("text", "") for c in user_content if isinstance(c, dict) and c.get("type") == "text")
            else:
                user_text = str(user_content)

            actual_query = (
                user_text.split("โจทย์ที่ต้องวางแผน:")[-1]
                if "โจทย์ที่ต้องวางแผน:" in user_text
                else user_text
            )

            # Layer 1 – hardcoded reflex
            reflex = _try_reflex_hardcoded(actual_query)
            if reflex:
                return reflex

            # Layer 2 – local SLM fast-track
            slm = _try_reflex_slm(actual_query)
            if slm:
                return slm

            # Layer 3 – Deep Thought subsystem
            DEEP_THOUGHT_KEYWORDS = {"voltage", "circuit", "architecture", "loop", "deep thought", "คิดวิเคราะห์"}
            if deep_thought and any(kw in actual_query.lower() for kw in DEEP_THOUGHT_KEYWORDS):
                logger.info(f"🧠 [DEEP THOUGHT] Intercepting: '{actual_query.strip()[:80]}'")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    dt_response = loop.run_until_complete(deep_thought.process_with_reflection(user_text))
                finally:
                    loop.close()
                return {
                    "content": f"[DEEP THOUGHT CONFIDENCE: {dt_response.confidence_score:.2f}]\n{dt_response.final_answer}",
                    "tool_calls": [],
                }

        # Layer 4 – Groq (primary) via Circuit Breaker
        try:
            from jarvis_circuit_breaker import groq_breaker  # noqa: PLC0415
        except ImportError:
            try:
                from modules.jarvis_circuit_breaker import groq_breaker  # noqa: PLC0415
            except ImportError:
                groq_breaker = None

        def _call_groq() -> Dict[str, Any]:
            response = call_groq_model(messages, tools=tools, model=model)
            if not response or "error_message" in response:
                raise ConnectionError(response.get("error_message", "Empty Groq response") if response else "Empty response")
            return response

        if groq_breaker:
            return groq_breaker.call(_call_groq)
        return _call_groq()

    except Exception as e:  # noqa: BLE001
        logger.warning(f"[FALLBACK] Groq/Circuit Breaker failed ({e}). Trying Gemini...")

    # Layer 5 – Gemini fallback
    try:
        return call_gemini_fallback(messages, tools)
    except Exception as gemini_e:  # noqa: BLE001
        logger.warning(f"[FALLBACK] Gemini failed ({gemini_e}). Trying Ollama local...")

    # Layer 6 – Ollama local (last resort)
    result = call_ollama_fallback(messages)
    if "error_message" not in result:
        return result

    # Total failure
    return {"error_message": f"All LLM backends unavailable. Last Ollama error: {result.get('error_message')}"}
