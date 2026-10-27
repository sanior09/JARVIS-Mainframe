"""
jarvis_core/model_gateway.py
──────────────────────────────────────────────────────────────────────────────
High-Level Model Gateway & Dispatcher for J.A.R.V.I.S.
Provides unified model resolution, intent-based temperature tuning,
fallback dispatching, and streaming token generation hooks.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from jarvis_core.ai_router import (
    call_groq_model,
    call_gemini_fallback,
    call_nachapol_core,
)

def get_groq_client():
    """Retrieve Groq client if API key is present."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception:
        return None

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

logger = logging.getLogger("JARVIS.ModelGateway")


class ModelIntentConfig:
    """Configures model parameters based on task intent."""
    
    INTENT_TEMPERATURES: Dict[str, float] = {
        "CODING": 0.2,
        "DEBUGGING": 0.1,
        "ANALYTICS": 0.3,
        "CONVERSATIONAL": 0.6,
        "CREATIVE": 0.8,
        "TACTICAL": 0.3,
        "DEFAULT": 0.5,
    }

    @classmethod
    def get_temperature(cls, intent: Optional[str] = None) -> float:
        if not intent:
            return cls.INTENT_TEMPERATURES["DEFAULT"]
        return cls.INTENT_TEMPERATURES.get(intent.upper(), cls.INTENT_TEMPERATURES["DEFAULT"])


class ModelGateway:
    """Unified Gateway for all LLM interactions within JARVIS."""

    def __init__(self):
        self.default_model = os.getenv("GROQ_MODEL", GROQ_MODEL)
        self.fast_model = os.getenv("GROQ_FAST_MODEL", GROQ_FAST_MODEL)
        self.vision_model = os.getenv("GROQ_VISION_MODEL", GROQ_VISION_MODEL)

    def resolve_model(
        self,
        has_image: bool = False,
        fast_mode: bool = False,
        override_model: Optional[str] = None,
    ) -> str:
        """Resolve the optimal model based on input context."""
        if override_model:
            return override_model
        if has_image:
            return self.vision_model
        if fast_mode:
            return self.fast_model
        return self.default_model

    def dispatch(
        self,
        messages: List[Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        intent: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Dispatches request through the Nachapol Core / Groq pipeline with automated fallbacks.
        """
        chosen_temp = temperature if temperature is not None else ModelIntentConfig.get_temperature(intent)
        chosen_model = model or self.default_model

        try:
            return call_nachapol_core(
                messages=messages,
                tools=tools,
                model=chosen_model,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"[MODEL GATEWAY] Primary dispatch error: {e}. Attempting direct fallback.")
            return call_groq_model(
                messages=messages,
                tools=tools,
                model=chosen_model,
                **kwargs,
            )

    async def stream_tokens(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams token chunks asynchronously for ultra-low latency voice/chat processing.
        """
        target_model = model or self.fast_model
        client = get_groq_client()
        if not client:
            yield "ขออภัยครับเจ้านาย ระบบประมวลผลโมเดลภายนอกไม่พร้อมใช้งาน"
            return

        try:
            stream = client.chat.completions.create(
                messages=messages,
                model=target_model,
                stream=True,
                temperature=0.5,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"[MODEL GATEWAY STREAM ERROR]: {e}")
            yield f"[Stream Exception: {e}]"


# Global singleton instance for easy import
model_gateway = ModelGateway()


def dispatch_llm_request(
    messages: List[Any],
    tools: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
    intent: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Convenience functional interface for model dispatch."""
    return model_gateway.dispatch(messages=messages, tools=tools, model=model, intent=intent, **kwargs)
