"""
tests/test_subtext_engine.py
──────────────────────────────────────────────────────────────────────────────
Unit tests for J.A.R.V.I.S. Cognitive Theory of Mind & Human Subtext Engine.
Verifies subtext extraction, literary & psychological framing, and prompt injection.
"""

import pytest
from unittest.mock import patch, MagicMock
from jarvis_core.cognitive.subtext_engine import SubtextCognitiveEngine, subtext_engine
from jarvis_core.ai_router import call_nachapol_core


def test_subtext_engine_bypass_operational_commands():
    """Verify that pure machine commands skip subtext analysis for zero-latency execution."""
    engine = SubtextCognitiveEngine()
    assert engine.should_analyze_subtext("เปิด chrome") is False
    assert engine.should_analyze_subtext("ปิด chrome") is False
    assert engine.should_analyze_subtext("เพิ่มเสียง") is False
    assert engine.should_analyze_subtext("กี่โมง") is False
    assert engine.should_analyze_subtext("cls") is False
    assert engine.should_analyze_subtext("แคปจอ") is False


def test_subtext_engine_triggers_on_reflective_queries():
    """Verify that personal, reflective, or complex queries trigger subtext analysis."""
    engine = SubtextCognitiveEngine()
    assert engine.should_analyze_subtext("วันนี้รู้สึกเหนื่อยจัง งานเยอะมากเลย") is True
    assert engine.should_analyze_subtext("นายคิดว่ามนุษย์กับ AI จะอยู่ร่วมกันอย่างไรในอนาคต") is True
    assert engine.should_analyze_subtext("ผมอยากสร้างโปรเจกต์ใหม่ที่ยิ่งใหญ่มาก") is True
    assert engine.should_analyze_subtext("ไม่แน่ใจว่าจะทำได้ไหม กลัวล้มเหลว") is True


def test_thematic_wisdom_mapping():
    """Verify that wisdom heuristics match appropriate literary and psychological archetypes."""
    engine = SubtextCognitiveEngine()

    fatigue_info = engine.extract_wisdom_heuristics("ช่วงนี้เหนื่อยมาก หมดไฟสุดๆ")
    assert fatigue_info is not None
    assert "Marcus Aurelius" in fatigue_info["literary_parallel"]
    assert "Cognitive Exhaustion" in fatigue_info["psychology"]

    ambition_info = engine.extract_wisdom_heuristics("ผมอยากสร้างและประดิษฐ์หุ่นยนต์ตัวใหม่")
    assert ambition_info is not None
    assert "Prometheus" in ambition_info["literary_parallel"]

    doubt_info = engine.extract_wisdom_heuristics("ลังเลมากเลย กลัวจะล้มเหลว")
    assert doubt_info is not None
    assert "Shakespeare" in doubt_info["literary_parallel"]


def test_subtext_prompt_injection_structure():
    """Verify prompt formatting for LLM injection."""
    engine = SubtextCognitiveEngine()
    injection = engine.get_subtext_prompt_injection("รู้สึกเหนื่อยและหมดไฟมากครับจาร์วิส")
    assert "[COGNITIVE SUBTEXT & THEORY OF MIND" in injection
    assert "จิตวิทยาและสภาวะอารมณ์แฝง:" in injection
    assert "มุมมองวรรณกรรมและปรัชญาสากล:" in injection
    assert "ทัศนคติการตอบสนองของ J.A.R.V.I.S.:" in injection


def test_ai_router_integration_with_subtext_engine():
    """Verify that call_nachapol_core enriches system prompt with subtext when appropriate."""
    messages = [
        {"role": "system", "content": "You are J.A.R.V.I.S."},
        {"role": "user", "content": "จาร์วิส ผมรู้สึกเหนื่อยและท้อกับงานวันนี้มาก"}
    ]

    with patch("jarvis_core.ai_router.call_groq_model") as mock_groq:
        mock_groq.return_value = {"content": "กระผมเข้าใจดีครับเจ้านาย พักผ่อนสักนิดเถิดครับ", "tool_calls": []}

        response = call_nachapol_core(messages=messages)
        assert "content" in response

        # Check that the system message was enriched with subtext
        system_content = messages[0]["content"]
        assert "COGNITIVE SUBTEXT & THEORY OF MIND" in system_content
        assert "Marcus Aurelius" in system_content
