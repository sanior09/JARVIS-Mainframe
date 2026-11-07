"""
tests/test_system_anatomy.py
──────────────────────────────────────────────────────────────────────────────
Unit tests for J.A.R.V.I.S. Self-Introspection & System Anatomy Engine.
Verifies real-time hardware inspection, software organs manifest, and prompt injection.
"""

import pytest
from unittest.mock import patch, MagicMock
from jarvis_core.cognitive.system_anatomy import SystemAnatomyEngine, system_anatomy_engine
from jarvis_core.ai_router import call_nachapol_core


def test_system_inquiry_detection():
    """Verify detection of queries asking about JARVIS's internal anatomy and specs."""
    engine = SystemAnatomyEngine()
    assert engine.is_system_inquiry("คิดว่าระบบเราขาดอะไรไป") is True
    assert engine.is_system_inquiry("เเล้วระบบjarvisเรานี้เป็นไงว") is True
    assert engine.is_system_inquiry("เครื่องเราสเปกอะไรนะ") is True
    assert engine.is_system_inquiry("มีโมดูลอะไรทำงานอยู่บ้าง") is True
    assert engine.is_system_inquiry("แผนอัปเกรดตู้แร็คไปถึงไหนแล้ว") is True

    # Unrelated queries
    assert engine.is_system_inquiry("พรุ่งนี้ฝนจะตกไหม") is False
    assert engine.is_system_inquiry("เปิด Google Chrome ให้หน่อย") is False


def test_hardware_snapshot():
    """Verify hardware snapshot returns non-empty telemetry values."""
    engine = SystemAnatomyEngine()
    hw = engine.get_hardware_snapshot()
    assert "cpu" in hw
    assert "ram" in hw
    assert "gpu" in hw
    assert "disk" in hw
    assert "os" in hw


def test_software_organs_manifest():
    """Verify software organs include Proactive Intelligence and Swarm Council."""
    engine = SystemAnatomyEngine()
    organs = engine.get_software_organs_manifest()
    organs_str = " ".join(organs)
    assert "Proactive Intelligence" in organs_str
    assert "Swarm Council" in organs_str
    assert "Tool Dispatcher" in organs_str
    assert "ChromaDB" in organs_str


def test_anatomy_prompt_injection():
    """Verify formatting of the introspection injection block."""
    engine = SystemAnatomyEngine()
    injection = engine.get_anatomy_prompt_injection("คิดว่าระบบเราขาดอะไร")
    assert "[J.A.R.V.I.S. SELF-ANATOMY & SYSTEM INTROSPECTION" in injection
    assert "Proactive Intelligence" in injection
    assert "Swarm Council" in injection
    assert "Roadmap" in injection


def test_ai_router_integration_with_anatomy_engine():
    """Verify call_nachapol_core injects system anatomy when user asks about the system."""
    messages = [
        {"role": "system", "content": "You are J.A.R.V.I.S."},
        {"role": "user", "content": "จาร์วิส คิดว่าระบบเราขาดอะไรไป"}
    ]

    with patch("jarvis_core.ai_router.call_groq_model") as mock_groq:
        mock_groq.return_value = {"content": "ระบบกำลังรอตู้แร็ค 9U ครับ", "tool_calls": []}

        response = call_nachapol_core(messages=messages)
        assert "content" in response

        system_content = messages[0]["content"]
        assert "J.A.R.V.I.S. SELF-ANATOMY & SYSTEM INTROSPECTION" in system_content
        assert "Proactive Intelligence" in system_content
