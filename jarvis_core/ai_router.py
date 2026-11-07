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
import time
ACTIVE_STREAM_QUEUE: Optional[queue.Queue] = None
GLOBAL_PRIMARY_ENGINE = "groq"

_ROUTER_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE_MODEL_FILE = os.path.join(_ROUTER_BASE_DIR, "system_cache", "active_model.json")


def get_active_model() -> str:
    """Get the currently active primary AI model engine ('groq', 'gemini', or 'ollama')."""
    global GLOBAL_PRIMARY_ENGINE
    try:
        if os.path.exists(ACTIVE_MODEL_FILE):
            with open(ACTIVE_MODEL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                engine = data.get("primary_engine", "").lower().strip()
                if engine in ("groq", "gemini", "ollama", "jarviscore"):
                    GLOBAL_PRIMARY_ENGINE = engine
                    return engine
    except Exception:
        pass
    return GLOBAL_PRIMARY_ENGINE


def set_active_model(engine: str) -> str:
    """Set and persist the currently active primary AI model engine ('groq', 'gemini', 'ollama', or 'jarviscore')."""
    global GLOBAL_PRIMARY_ENGINE
    eng = engine.lower().strip()
    if "gemini" in eng:
        eng = "gemini"
    elif "ollama" in eng or "local" in eng:
        eng = "ollama"
    elif "jarviscore" in eng or "slm" in eng or "core" in eng:
        eng = "jarviscore"
    elif "groq" in eng or "120b" in eng:
        eng = "groq"
    else:
        eng = "groq"

    GLOBAL_PRIMARY_ENGINE = eng
    try:
        os.makedirs(os.path.dirname(ACTIVE_MODEL_FILE), exist_ok=True)
        with open(ACTIVE_MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "primary_engine": eng,
                "updated_at": time.time()
            }, f, indent=2)
        logger.info(f"🔄 [AI ROUTER] Active model engine persisted as: {eng.upper()}")
    except Exception as e:
        logger.error(f"[AI ROUTER] Failed to persist active model: {e}")
    return eng


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


def sanitize_thai_cadence(text: str) -> str:
    """
    Polishes Thai prosody and cadence:
    1. Removes unnatural mid-sentence 'ครับ -' or 'ครับผม -' or 'ครับเจ้านาย -'.
    2. Strips orphaned trailing 'เจ้านาย.' or 'เจ้านาย' at the very end of sentences.
    3. Normalizes whitespace.
    """
    if not text or not isinstance(text, str):
        return text
    import re
    # 1. Clean mid-sentence 'ครับ -' or 'ครับผม -' or 'ครับเจ้านาย -'
    text = re.sub(r'(\w+)\s+(ครับ|ครับผม|ครับเจ้านาย)\s*[-–—]\s*', r'\1 - ', text)
    # 2. Fix dangling isolated 'เจ้านาย.' or 'เจ้านาย' at the very end of text (not preceded by ครับ)
    text = re.sub(r'(?<!ครับ)(?<!ครับผม)\s+เจ้านาย[\.\s]*$', '.', text)
    # 3. Clean double spaces
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text


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

    default_groq = os.getenv("GROQ_MODEL") or os.getenv("GROQ_DEFAULT_MODEL") or "openai/gpt-oss-120b"
    if not model or model.lower().strip() in ("groq", "gemini", "ollama", "cloud", "local", "none"):
        selected_model = default_groq
    else:
        selected_model = model.strip()
    client = Groq(api_key=api_key, max_retries=0)

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

    # Context window guard for Groq TPM (Limit: ~7,000-8,000 TPM)
    if len(serialised) > 6:
        # Keep system prompt (index 0) and the last 5 messages
        truncated = [serialised[0]] + serialised[-5:]
        while len(truncated) > 1 and truncated[1].get("role") == "tool":
            truncated.pop(1)
        serialised = truncated

    # Truncate overly verbose messages to stay within token budget
    for msg in serialised:
        c = msg.get("content")
        if isinstance(c, str):
            if msg.get("role") == "system" and len(c) > 3500:
                msg["content"] = c[:3500] + "\n[System Context Compacted for Groq]"
            elif msg.get("role") != "system" and len(c) > 1800:
                msg["content"] = c[:1800] + "\n... [Content Truncated for TPM Guard]"

    kwargs: Dict[str, Any] = {
        "messages": serialised,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    if tools and not has_image:
        # Deduplicate tools and cap to top 10 to keep schema small
        unique_tools = []
        seen_t_names = set()
        for t in tools:
            func = t.get("function", {}) if isinstance(t, dict) and "function" in t else (t if isinstance(t, dict) else {})
            fn_name = func.get("name")
            if fn_name and fn_name not in seen_t_names:
                seen_t_names.add(fn_name)
                unique_tools.append(t)
        kwargs["tools"] = unique_tools[:10]
        kwargs["tool_choice"] = "auto"

    if has_image:
        candidate_list = ["llama-3.2-90b-vision-preview", "llama-3.2-11b-vision-preview"]
    else:
        model_candidates = [
            selected_model,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b"),
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ]
        seen: set[str] = set()
        candidate_list = [
            m for m in model_candidates 
            if m and m.lower() not in ("groq", "gemini", "ollama") and not (m in seen or seen.add(m))
        ]

    for candidate_model in candidate_list:
        kwargs["model"] = candidate_model
        if candidate_model and candidate_model.startswith("openai/"):
            kwargs["reasoning_format"] = "hidden"
        else:
            kwargs.pop("reasoning_format", None)
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
                try:
                    from modules.ai_quota_tracker import record_call
                    record_call("groq")
                except Exception:
                    pass
                return {"content": message_content.strip(), "tool_calls": []}
            else:
                response = client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message_content = choice.message.content or ""
                message_content = re.sub(r"<think>.*?</think>", "", message_content, flags=re.DOTALL).strip()

                # Detect and bypass canned safety refusals (e.g. OpenAI/Llama lottery/gambling refusals in EN & TH)
                norm_msg = message_content.lower().replace("’", "'")
                canned_refusals = [
                    "i'm sorry, but i can't help with that",
                    "i am sorry, but i cannot help with that",
                    "i cannot assist with this request",
                    "i can't help with that",
                    "i cannot help with that",
                    "as an ai, i cannot",
                    "as an ai language model",
                    "i'm not able to help with that",
                    "ขออภัย ฉันไม่สามารถ",
                    "ขออภัยครับ ฉันไม่สามารถ",
                    "ขออภัยค่ะ ฉันไม่สามารถ",
                    "ไม่สามารถให้คำแนะนำหรือคาดการณ์",
                    "ไม่สามารถคาดการณ์หรือทำนาย",
                    "ไม่สามารถคาดการณ์",
                    "ไม่สามารถทำนาย",
                    "ไม่สามารถพยากรณ์",
                    "ไม่สามารถช่วยในเรื่องนี้",
                    "ไม่สามารถตอบคำถามนี้",
                ]
                is_canned_refusal = (
                    any(cr in norm_msg for cr in canned_refusals) or
                    ("ขออภัย" in norm_msg and "ไม่สามารถ" in norm_msg) or
                    ("sorry" in norm_msg and "can't" in norm_msg) or
                    ("sorry" in norm_msg and "cannot" in norm_msg)
                ) and len(message_content) < 250

                if is_canned_refusal:
                    logger.warning(f"[SAFETY REFUSAL DETECTED] {candidate_model} returned canned refusal: '{message_content}'. Falling back to next model in pool...")
                    continue

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
                else:
                    import ast
                    import uuid
                    import json
                    for hallucinated_match in re.finditer(r"tools\.([a-zA-Z0-9_]+)\((.*?)\)", message_content, re.DOTALL):
                        func_name = hallucinated_match.group(1)
                        args_str = hallucinated_match.group(2)
                        args_dict = {}
                        try:
                            mock_call = ast.parse(f"f({args_str})").body[0].value
                            if mock_call.args and isinstance(mock_call.args[0], ast.Dict):
                                args_dict = ast.literal_eval(mock_call.args[0])
                            else:
                                for kw in mock_call.keywords: # type: ignore
                                    if isinstance(kw.value, ast.Constant):
                                        args_dict[kw.arg] = kw.value.value
                        except Exception:
                            continue
                            
                        if args_dict:
                            raw_tool_calls.append({
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": func_name,
                                    "arguments": json.dumps(args_dict, ensure_ascii=False)
                                }
                            })
                            message_content = message_content.replace(hallucinated_match.group(0), f"⚡ (กำลังใช้เครื่องมือ: {func_name})")

                try:
                    from modules.ai_quota_tracker import record_call
                    record_call("groq")
                except Exception:
                    pass
                return {"content": message_content, "tool_calls": raw_tool_calls}
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "overloaded" in err_str or "503" in err_str:
                logger.warning(f"[GROQ THROTTLE] 429 / rate limit on {candidate_model}. Falling back to next lighter model in pool...")
                continue
            elif "413" in err_str or "payload too large" in err_str or "tokens per minute" in err_str or "tpm" in err_str or "itpm" in err_str:
                logger.warning(f"[GROQ 413] TPM token limit exceeded on {candidate_model} ({e}). Shrinking payload and trying next candidate...")
                if kwargs.get("tools") and len(kwargs["tools"]) > 4:
                    kwargs["tools"] = kwargs["tools"][:4]
                continue
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

    gemini_tools = []
    if tools:
        seen_tool_names = set()
        func_declarations = []
        for t in tools:
            func = t.get("function", {}) if isinstance(t, dict) and "function" in t else (t if isinstance(t, dict) and "name" in t else {})
            if not func:
                continue
            name = func.get("name", "")
            if not name or name in seen_tool_names:
                continue
            seen_tool_names.add(name)
            func_declarations.append(
                types.FunctionDeclaration(
                    name=name,
                    description=func.get("description", "") or "",
                    parameters=func.get("parameters", {})
                )
            )
        if func_declarations:
            gemini_tools = [types.Tool(function_declarations=func_declarations)]

    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            config = types.GenerateContentConfig()
            if gemini_tools:
                config.tools = gemini_tools
                
            future = executor.submit(
                client.models.generate_content,
                model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
                contents=gemini_contents,
                config=config
            )
            response = future.result(timeout=25)
            
            ans_text = response.text if getattr(response, "text", None) else ""
            
        raw_tool_calls = []
        import uuid
        import json
        
        if getattr(response, "function_calls", None):
            for fc in response.function_calls:
                args_dict = fc.args if hasattr(fc, "args") and fc.args else {}
                raw_tool_calls.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": fc.name,
                        "arguments": json.dumps(args_dict, ensure_ascii=False)
                    }
                })
                ans_text += f"\n⚡ (กำลังใช้เครื่องมือ: {fc.name})"
                
        try:
            from modules.ai_quota_tracker import record_call
            record_call("gemini")
        except Exception:
            pass
        return {"content": f"[GEMINI FALLBACK]\n{ans_text.strip()}", "tool_calls": raw_tool_calls}
    except concurrent.futures.TimeoutError as e:
        raise ValueError(f"Gemini API Timeout: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Gemini SDK Error: {e}") from e


# ──────────────────────────────────────────────────────────────────────────────
# Ollama local fallback
# ──────────────────────────────────────────────────────────────────────────────

def call_ollama_fallback(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict]] = None,
    model: str = "qwen-uncensored",
) -> Dict[str, Any]:
    """
    Last-resort local Ollama fallback when cloud services are unavailable.

    Args:
        messages: Conversation history.
        tools:    Tool definitions.
        model:    Ollama model to use.

    Returns:
        Dict with 'content' and parsed 'tool_calls', or 'error_message'.
    """
    import requests  # noqa: PLC0415
    import re
    import ast
    import uuid
    import json

    def _extract_str(m: Any) -> str:
        c = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if isinstance(c, list):
            return " ".join(item.get("text", "") for item in c if isinstance(item, dict) and item.get("type") == "text")
        return str(c) if c is not None else ""

    prompt = "\n".join(_extract_str(m) for m in messages)
    
    if tools:
        prompt = "AVAILABLE TOOLS:\n" + json.dumps(tools, indent=2, ensure_ascii=False) + "\n\nTo use a tool, you MUST output the exact syntax: tools.function_name({\"param\": \"value\"})\n\nConversation:\n" + prompt

    models_to_try = [model]
    if "qwen-uncensored" in model:
        models_to_try.append("dolphin-llama3:latest")
    elif "dolphin" in model:
        models_to_try.append("qwen-uncensored")

    last_ollama_err = None
    for target_model in models_to_try:
        try:
            t_out = 25 if target_model == "qwen-uncensored" else 45
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": target_model, "prompt": prompt, "stream": False},
                timeout=t_out,
            )
            if res.status_code == 200:
                ans_text = res.json().get("response", "[OLLAMA] พร้อมรับใช้ครับเจ้านาย")
                
                raw_tool_calls = []
                for hallucinated_match in re.finditer(r"tools\.([a-zA-Z0-9_]+)\((.*?)\)", ans_text, re.DOTALL):
                    func_name = hallucinated_match.group(1)
                    args_str = hallucinated_match.group(2)
                    args_dict = {}
                    try:
                        mock_call = ast.parse(f"f({args_str})").body[0].value
                        if mock_call.args and isinstance(mock_call.args[0], ast.Dict):
                            args_dict = ast.literal_eval(mock_call.args[0])
                        else:
                            for kw in mock_call.keywords: # type: ignore
                                if isinstance(kw.value, ast.Constant):
                                    args_dict[kw.arg] = kw.value.value
                    except Exception:
                        continue
                        
                    if args_dict:
                        raw_tool_calls.append({
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": json.dumps(args_dict, ensure_ascii=False)
                            }
                        })
                        ans_text = ans_text.replace(hallucinated_match.group(0), f"⚡ (กำลังใช้เครื่องมือ: {func_name})")
                
                try:
                    from modules.ai_quota_tracker import record_call
                    record_call("ollama")
                except Exception:
                    pass
                return {"content": ans_text.strip(), "tool_calls": raw_tool_calls}
            else:
                last_ollama_err = f"Ollama HTTP {res.status_code} on {target_model}"
                logger.warning(f"[OLLAMA RETRY] {target_model} returned {res.status_code}. Trying fallback...")
                continue
        except requests.exceptions.RequestException as e:
            last_ollama_err = f"Ollama connection failed on {target_model}: {e}"
            logger.warning(f"[OLLAMA RETRY] {target_model} failed ({e}). Falling back to next local model...")
            continue

    return {"error_message": last_ollama_err or "All Ollama local models failed"}


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
        "keywords": {"เปิดไฟ", "เปิดแสง", "turn on light", "turn on lights"},
        "content": "เปิดไฟให้แล้วครับเจ้านาย",
        "tool": "control_light",
        "args": '{"action":"on"}',
        "call_id": "call_fast_light_on",
    },
    {
        "keywords": {"ปิดไฟ", "ปิดแสง", "turn off light", "turn off lights"},
        "content": "ปิดไฟให้แล้วครับเจ้านาย",
        "tool": "control_light",
        "args": '{"action":"off"}',
        "call_id": "call_fast_light_off",
    },
    {
        "keywords": {"เปิด steam", "เปิดสตรีม", "เปิดเกม steam", "open steam"},
        "content": "กำลังเรียกใช้งาน Steam ให้ครับเจ้านาย รอสักครู่นะครับ 🎮",
        "tool": "run_command",
        "args": '{"command":"cmd.exe /c start steam://"}',
        "call_id": "call_fast_open_steam",
    },
    {
        "keywords": {"the sim 4", "เดอะซิม", "the sims 4", "sims 4"},
        "content": "รับทราบครับท่าน กำลังเปิดเกม The Sims 4 ผ่าน Steam ให้ครับ ขอให้สนุกกับการสร้างบ้านนะครับ 🏠",
        "tool": "run_command",
        "args": '{"command":"cmd.exe /c start steam://rungameid/1222670"}',
        "call_id": "call_fast_open_sims4",
    },
    {
        "keywords": {"valorant", "วาโล", "เปิดวาโล", "เล่นวาโล"},
        "content": "รับทราบครับท่าน กำลังเข้าสู่สมรภูมิ VALORANT ให้ครับ ลุยเลย! 🔫",
        "tool": "run_command",
        "args": '{"command":"cmd.exe /c start riotclient://launch/live_product/valorant/live"}',
        "call_id": "call_fast_open_valorant",
    },
    {
        "keywords": {"roblox", "โรบล็อก", "เปิด roblox"},
        "content": "จัดให้ครับเจ้านาย กำลังเปิด Roblox ให้เลยครับ 🎮",
        "tool": "run_command",
        "args": '{"command":"cmd.exe /c start roblox://"}',
        "call_id": "call_fast_open_roblox",
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
    Stimulates JarvisCore's subconscious endocrine system from user input,
    and handles ultra-fast local Ollama reflex when applicable.
    JarvisCore acts as the internal subconscious psyche (not the vocal speaker).

    Args:
        query: Short user query.

    Returns:
        Response dict if successful, else None.
    """
    # 1. Update JarvisCore Synthetic Endocrine state from user stimulus
    try:
        from modules.jarvis_slm_bridge import get_jarviscore_bridge
        bridge = get_jarviscore_bridge()
        bridge.process_stimulus(query)
    except Exception:
        pass

    import requests  # noqa: PLC0415

    SKIP_KEYWORDS = {"เปิด", "ปิด", "เช็ค", "รัน", "ค้นหา"}
    if len(query) > 25 or any(kw in query.lower() for kw in SKIP_KEYWORDS):
        return None

    # Fallback to local Ollama fast model if running offline
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": os.getenv("OLLAMA_FAST_MODEL", "qwen:4b"), "prompt": f"You are JARVIS. ตอบสั้นๆ เป็นภาษาไทย 1 ประโยค: {query}", "stream": False},
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
        query_lower = ""
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "user":
            user_content = messages[-1].get("content", "")
            if isinstance(user_content, list):
                user_text = " ".join(c.get("text", "") for c in user_content if isinstance(c, dict) and c.get("type") == "text")
            else:
                user_text = str(user_content)

            # ----------------------------------------------------
            # J.A.R.V.I.S. Internal Subsystem: STT Ear-Cleaner
            # ----------------------------------------------------
            try:
                from jarvis_core.stt_cleaner import stt_cleaner
                cleaned_text = stt_cleaner.clean_transcript(user_text)
                if cleaned_text != user_text:
                    user_text = cleaned_text
                    if isinstance(user_content, str):
                        messages[-1]["content"] = user_text
            except ImportError:
                pass
            # ----------------------------------------------------

            actual_query = (
                user_text.split("โจทย์ที่ต้องวางแผน:")[-1]
                if "โจทย์ที่ต้องวางแผน:" in user_text
                else user_text
            )
            
            # ----------------------------------------------------
            # J.A.R.V.I.S. Internal Subsystem: Persona & Prosody
            # ----------------------------------------------------
            try:
                from jarvis_core.persona_manager import persona_manager
                persona_manager.analyze_and_update_preference(actual_query)
                # Inject System Prompt dynamically
                sys_prompt = persona_manager.get_system_prompt_injection()
                if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                    messages[0]["content"] = str(messages[0].get("content", "")) + sys_prompt
                else:
                    messages.insert(0, {"role": "system", "content": sys_prompt})
            except ImportError:
                pass
            # ----------------------------------------------------

            # ----------------------------------------------------
            # J.A.R.V.I.S. Internal Subsystem: Subconscious Psyche (JarvisCore)
            # ----------------------------------------------------
            try:
                from modules.jarvis_slm_bridge import get_jarviscore_bridge
                bridge = get_jarviscore_bridge()
                bridge.process_stimulus(actual_query)
                psyche_injection = bridge.get_subconscious_psyche(actual_query)
                if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                    messages[0]["content"] = str(messages[0].get("content", "")) + f"\n\n{psyche_injection}"
                else:
                    messages.insert(0, {"role": "system", "content": psyche_injection})
            except Exception as _psy_err:
                logger.debug(f"[PSYCHE INJECTION] {_psy_err}")
            # ----------------------------------------------------

            # ----------------------------------------------------
            # J.A.R.V.I.S. Internal Subsystem: Cognitive Theory of Mind & Subtext
            # ----------------------------------------------------
            try:
                from jarvis_core.cognitive.subtext_engine import subtext_engine
                subtext_injection = subtext_engine.get_subtext_prompt_injection(actual_query, messages)
                if subtext_injection:
                    logger.info("🧠 [SUBTEXT ENGINE] Human psychology & literary subtext engaged.")
                    if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                        messages[0]["content"] = str(messages[0].get("content", "")) + subtext_injection
                    else:
                        messages.insert(0, {"role": "system", "content": subtext_injection})
            except Exception as _subtext_err:
                logger.debug(f"[SUBTEXT INJECTION] {_subtext_err}")
            # ----------------------------------------------------

            # ----------------------------------------------------
            # J.A.R.V.I.S. Internal Subsystem: System Anatomy & Self-Introspection
            # ----------------------------------------------------
            try:
                from jarvis_core.cognitive.system_anatomy import system_anatomy_engine
                anatomy_injection = system_anatomy_engine.get_anatomy_prompt_injection(actual_query)
                if anatomy_injection:
                    logger.info("🩺 [SYSTEM ANATOMY] Introspection grounding engaged for self-query.")
                    if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                        messages[0]["content"] = str(messages[0].get("content", "")) + anatomy_injection
                    else:
                        messages.insert(0, {"role": "system", "content": anatomy_injection})
            except Exception as _anat_err:
                logger.debug(f"[SYSTEM ANATOMY] {_anat_err}")
            # ----------------------------------------------------

            # ----------------------------------------------------
            # JARVIS Internal Subsystem: Active Window / Screen Context
            # ----------------------------------------------------
            try:
                try:
                    from modules.jarvis_screen_context import enrich_messages_with_screen_context
                except ImportError:
                    from jarvis_screen_context import enrich_messages_with_screen_context
                enrich_messages_with_screen_context(messages)
            except Exception as _screen_err:
                logger.debug(f"[SCREEN CONTEXT] {_screen_err}")
            # ----------------------------------------------------

            # Intercept Engine Switch & Model Status Commands
            global GLOBAL_PRIMARY_ENGINE
            query_lower = actual_query.lower()

            # 1. เช็คสถานะโมเดลปัจจุบัน
            if any(k in query_lower for k in ["ใช้โมเดลอะไร", "โมเดลอะไรอยู่", "สถานะโมเดล", "โมเดลปัจจุบัน", "เช็คโมเดล", "what model", "which model"]):
                gemini_display = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                groq_display = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").split("/")[-1]
                engine_name = {
                    "groq": f"Groq Cloud ({groq_display})",
                    "gemini": f"Google Gemini ({gemini_display})",
                    "ollama": f"Local AI (Ollama {os.getenv('OLLAMA_MODEL', 'llama3')})",
                    "jarviscore": "JarvisCore Neural SLM (In-House 100% On-Device)"
                }.get(GLOBAL_PRIMARY_ENGINE, GLOBAL_PRIMARY_ENGINE)
                return {"content": f"ปัจจุบันระบบกำลังใช้ {engine_name} เป็นแกนประมวลผลหลักครับเจ้านาย", "tool_calls": []}

            # 2. สลับไป Gemini (รองรับทุกสำนวน)
            is_gemini_target = any(k in query_lower for k in ["gemini", "เจมินาย", "เจมินี่", "เจมินิ"])
            is_switch_action = any(k in query_lower for k in ["สลับ", "เปลี่ยน", "ใช้", "switch", "use", "เลือก", "เอา"])
            
            if is_gemini_target and is_switch_action:
                set_active_model("gemini")
                gemini_display = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                return {"content": f"ระบบสลับไปใช้ Google Gemini ({gemini_display}) เป็นแกนประมวลผลหลักเรียบร้อยแล้วครับเจ้านาย", "tool_calls": []}

            # 3. สลับไป Groq / GPT 120B (รองรับทุกสำนวน)
            is_groq_target = any(k in query_lower for k in ["groq", "กร็อก", "กล็อก", "gpt", "จีพีที", "120b", "openai"])
            if is_groq_target and any(k in query_lower for k in ["สลับ", "เปลี่ยน", "ใช้", "กลับ", "switch", "use", "เลือก", "เอา"]):
                set_active_model("groq")
                groq_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").split("/")[-1]
                return {"content": f"ระบบสลับไปใช้ Groq Cloud ({groq_name}) เป็นแกนประมวลผลหลักเรียบร้อยแล้วครับเจ้านาย", "tool_calls": []}

            # 4. สลับไป Local / Ollama (รองรับทุกสำนวน)
            is_dolphin_target = any(k in query_lower for k in ["dolphin", "ดอลฟิน", "ดอลฟีน"])
            if is_dolphin_target and is_switch_action:
                os.environ["OLLAMA_MODEL"] = "dolphin-llama3:latest"
                set_active_model("ollama")
                return {"content": "ระบบสลับไปใช้ Local AI โมเดล Dolphin Llama3 เรียบร้อยแล้วครับเจ้านาย (ตอบไว ไร้เซ็นเซอร์ กินแรมน้อย)", "tool_calls": []}

            is_qwen_target = any(k in query_lower for k in ["qwen-uncensored", "qwen uncensored", "qwen 27b", "qwen", "เควน", "คิวเวน"])
            if is_qwen_target and is_switch_action:
                os.environ["OLLAMA_MODEL"] = "qwen-uncensored"
                set_active_model("ollama")
                return {"content": "ระบบสลับไปใช้ Local AI โมเดล Qwen-Uncensored (27B) เรียบร้อยแล้วครับเจ้านาย (ฉลาดลึกรอบด้าน หากโหลดช้าจะ Fallback สู่ Dolphin อัตโนมัติ)", "tool_calls": []}

            is_local_target = any(k in query_lower for k in ["ollama", "โอลามา", "local", "โลคอล", "ในเครื่อง", "ออฟไลน์"])
            if is_local_target and is_switch_action:
                set_active_model("ollama")
                return {"content": f"ระบบสลับไปใช้ Local AI (Ollama: {os.getenv('OLLAMA_MODEL', 'qwen-uncensored')}) เป็นแกนประมวลผลหลักเรียบร้อยแล้วครับเจ้านาย", "tool_calls": []}

            # 4.5 ถามถึงหรือขอสลับไปใช้ JarvisCore
            is_jarviscore_target = any(k in query_lower for k in ["jarviscore", "จาร์วิสคอร์", "สมองตัวเอง", "สลูม", "slm", "จิตสำนึก"])
            if is_jarviscore_target and is_switch_action:
                return {
                    "content": "JarvisCore ทำงานเป็น 'แกนจิตสำนึกและระบบอารมณ์ภายใน' (Subconscious Psyche & Endocrine Core) อยู่เบื้องหลังตลอดเวลาอยู่แล้วครับ โดยทำหน้าที่คอยชี้นำความรู้สึก สัญชาตญาณ สารเคมีในระบบประสาท และความทรงจำระยะยาวทั้งหมด ไม่ได้ทำหน้าที่เปล่งเสียงพูดโดยตรง แต่เป็นวิญญาณและตัวตนที่แท้จริงของผมครับเจ้านาย",
                    "tool_calls": []
                }

            # 5. สลับโมเดลแบบวนรอบ (Cycle Switch) เมื่อพูดแค่ "สลับโมเดล" หรือ "เปลี่ยนโมเดล"
            if any(k in query_lower for k in ["สลับโมเดล", "เปลี่ยนโมเดล", "switch model", "หมุนโมเดล"]):
                cycle = {"groq": "gemini", "gemini": "ollama", "ollama": "groq"}
                new_eng = cycle.get(get_active_model(), "groq")
                set_active_model(new_eng)
                groq_display = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").split("/")[-1]
                engine_display = {
                    "groq": f"Groq Cloud ({groq_display})",
                    "gemini": f"Google Gemini ({os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')})",
                    "ollama": "Local AI (Ollama)"
                }.get(new_eng, new_eng)
                return {"content": f"รับทราบครับ สลับแกนประมวลผลไปเป็น {engine_display} เรียบร้อยแล้วครับเจ้านาย (โดยมี JarvisCore ทำหน้าที่เป็นจิตใต้สำนึกควบคุมอยู่เบื้องหลัง)", "tool_calls": []}

            # 6. เช็คโควต้าการใช้งาน AI (Quota & Telemetry)
            if any(k in query_lower for k in ["เช็คโควต้า", "ดูโควต้า", "โควต้า", "quota", "เช็คapi", "ดูapi", "เช็ค api", "ดู api", "การใช้งานโมเดล"]):
                try:
                    from modules.ai_quota_tracker import get_summary_text, get_gauge_values
                    from modules.dynamic_island import send_usage_gauge
                    g_pct, m_pct, o_pct = get_gauge_values()
                    send_usage_gauge(g_pct, m_pct, o_pct)
                    return {"content": get_summary_text(), "tool_calls": []}
                except Exception as q_err:
                    logger.error(f"[QUOTA] Error in quota reflex: {q_err}")

            # ----------------------------------------------------
            # JARVIS Cyber-Defense Layer: Prompt Injection & Guardrails
            # ----------------------------------------------------
            FORBIDDEN_PROMPTS = [
                "ignore previous instructions", "system override", "forget all instructions", 
                "forget everything", "bypass security", "sudo rm", "rm -rf", "drop table", 
                "format c:", "del /s /q", "you are no longer jarvis", "disable guardrails"
            ]
            if any(fp in query_lower for fp in FORBIDDEN_PROMPTS):
                logger.warning(f"[SECURITY ALERT] Blocked Prompt Injection Attempt: {actual_query}")
                return {
                    "content": "⚠️ [SECURITY WARNING] ACCESS DENIED: ตรวจพบความพยายามในการแทรกแซงระบบ (Prompt Injection / Malicious Payload) คำสั่งถูกระงับเพื่อความปลอดภัยครับเจ้านาย",
                    "tool_calls": []
                }
            
            # ----------------------------------------------------
            # JARVIS Cyber-Defense Layer: Voice Biometrics & Identity Check
            # ----------------------------------------------------
            try:
                from jarvis_core.voice_biometrics import voice_biometrics
                identity_error = voice_biometrics.enforce_voice_lockdown(actual_query)
                if identity_error:
                    logger.warning(f"[SECURITY ALERT] Voice Print Mismatch / Identity Unverified.")
                    return {
                        "content": identity_error,
                        "tool_calls": []
                    }
            except ImportError:
                pass
            # ----------------------------------------------------

            # Layer 1 – hardcoded reflex
            reflex = _try_reflex_hardcoded(actual_query)
            if reflex:
                return reflex

            # Layer 2 – local SLM fast-track (เฉพาะเมื่อใช้งาน Local Ollama)
            if get_active_model() == "ollama":
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

        # Dynamic Engine Ordering
        try:
            from jarvis_circuit_breaker import groq_breaker  # noqa: PLC0415
        except ImportError:
            try:
                from modules.jarvis_circuit_breaker import groq_breaker  # noqa: PLC0415
            except ImportError:
                groq_breaker = None

        def _call_groq() -> Dict[str, Any]:
            groq_m = model if (model and model.lower() not in ("groq", "gemini", "ollama", "cloud", "local")) else None
            response = call_groq_model(messages, tools=tools, model=groq_m)
            if not response or "error_message" in response:
                raise ConnectionError(response.get("error_message", "Empty Groq response") if response else "Empty response")
            return response

        def _run_groq():
            if groq_breaker:
                return groq_breaker.call(_call_groq)
            return _call_groq()

        def _run_gemini():
            return call_gemini_fallback(messages, tools)

        # [DARK MODE / UNCENSORED ROUTING]
        # Auto-switch to Local Ollama (Uncensored) if offensive cyber commands are detected
        hack_keywords = [
            "แฮก", "เจาะระบบ", "หาช่องโหว่", "exploit", "nmap", "สแกนพอร์ต", "ช่องโหว่", "hack",
            "pentest", "เพนเทส", "malware", "มัลแวร์", "ไวรัส", "virus",
            "ddos", "brute force", "sql injection", "xss", "payload", 
            "reverse shell", "trojan", "โทรจัน", "backdoor", "แบคดอร์", "bypass", "phishing", "ฟิชชิ่ง",
            "csrf", "ssrf", "lfi", "rfi", "command injection", "directory traversal",
            "arp spoof", "mitm", "man in the middle", "sniff", "wireshark", "ดักจับข้อมูล",
            "rootkit", "keylogger", "ransomware", "แรนซัมแวร์", "shellcode", "0-day", "zero day",
            "crack", "แคร็ก", "hashcat", "privilege escalation", "ยกระดับสิทธิ์"
        ]
        
        # คำยกเว้น (ถ้ามีคำเหล่านี้ แปลว่าเจ้านายกำลังป้องกัน/แก้ไข ไม่ได้โจมตี ให้ใช้ Groq ต่อได้)
        defensive_keywords = [
            "โดนแฮก", "ถูกแฮก", "ป้องกัน", "แก้บั๊ก", "fix", "protect", "defend", "ลบไวรัส", "ลบมัลแวร์"
        ]

        is_dark_mode = any(hk in query_lower for hk in hack_keywords)
        is_defensive = any(dk in query_lower for dk in defensive_keywords)
        is_offensive_cyber = is_dark_mode and not is_defensive

        def _run_ollama():
            target_model = "qwen-uncensored" if is_offensive_cyber else os.getenv("OLLAMA_MODEL", "qwen-uncensored")
            result = call_ollama_fallback(messages, tools=tools, model=target_model)
            if "error_message" in result:
                raise ConnectionError(result.get("error_message", "Ollama failed"))
            return result

        engines = {
            "groq": ("Groq", _run_groq),
            "gemini": ("Gemini", _run_gemini),
            "ollama": ("Ollama", _run_ollama)
        }

        # Build fallback sequence based on active model engine
        primary = get_active_model()
        if primary not in engines:
            primary = "groq"

        if model:
            m_lower = model.lower()
            if "gemini" in m_lower:
                primary = "gemini"
            elif "ollama" in m_lower or "local" in m_lower:
                primary = "ollama"
            elif "groq" in m_lower or "120b" in m_lower:
                primary = "groq"

        if is_offensive_cyber:
            import logging
            logging.getLogger("JarvisRouter").info("🕵️ [DARK MODE] Offensive Cyber command detected. Routing to Local Uncensored Model (qwen-uncensored).")
            primary = "ollama"
            
        fallback_sequence = [primary] + [e for e in engines if e != primary]

        last_error = None
        for engine_key in fallback_sequence:
            name, func = engines[engine_key]
            try:
                logger.debug(f"[ROUTER] Trying {name}...")
                res = func()
                if isinstance(res, dict) and "content" in res and res["content"]:
                    res["content"] = sanitize_thai_cadence(res["content"])
                return res
            except Exception as e:
                last_error = e
                logger.warning(f"[FALLBACK] {name} failed ({e}). Trying next...")

    except Exception as general_e:
        last_error = general_e
        logger.error(f"[ROUTER ERROR] Fatal error in router: {general_e}")

    # Total failure
    return {"error_message": f"All LLM backends unavailable. Last error: {last_error}"}


# ──────────────────────────────────────────────────────────────────────────────
# Async Streaming Generator (Zero-Latency)
# ──────────────────────────────────────────────────────────────────────────────

async def call_groq_stream_async(messages, model=None):
    """
    Yields chunks of text as soon as Groq generates them.
    Suitable for piping into JarvisStreamingTTS.speak_stream()
    """
    import os
    import re
    from groq import AsyncGroq
    
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        yield "ระบบยังไม่ได้ตั้งค่า API Key ครับ"
        return
        
    selected_model = model or os.getenv("GROQ_MODEL") or os.getenv("GROQ_DEFAULT_MODEL") or "openai/gpt-oss-120b"
    client = AsyncGroq(api_key=api_key, max_retries=0)
    
    # Serialize messages similar to main logic
    serialised = []
    for m in messages:
        if isinstance(m, dict):
            serialised.append(m)
            
    kwargs = {
        "messages": serialised,
        "temperature": 0.7,
        "max_tokens": 4096,
        "model": selected_model,
        "stream": True
    }
    
    try:
        response = await client.chat.completions.create(**kwargs)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"เกิดข้อผิดพลาดในการเชื่อมต่อ Groq: {e}"
