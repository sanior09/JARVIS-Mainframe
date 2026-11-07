"""
tests/test_grounding_engine.py
──────────────────────────────────────────────────────────────────────────────
Pytest test suite for RealTimeGroundingEngine and Temporal Grounding.
Validates intent classification, RSS extraction, anti-hallucination prompt injection,
and router integration.
"""

from unittest.mock import MagicMock, patch
import pytest

from jarvis_core.cognitive.grounding_engine import RealTimeGroundingEngine
from jarvis_core.cognitive.subtext_engine import subtext_engine


@pytest.fixture
def engine():
    return RealTimeGroundingEngine()


def test_is_grounding_query(engine):
    # Positive grounding queries
    assert engine.is_grounding_query("วันนี้มีอะไรใหม่ๆน่าสนใจบ้าง") is True
    assert engine.is_grounding_query("ข่าววันนี้มีอะไรบ้าง") is True
    assert engine.is_grounding_query("อัปเดตเทคโนโลยีล่าสุด") is True
    assert engine.is_grounding_query("What's new today?") is True
    assert engine.is_grounding_query("สรุปข่าวล่าสุดให้ฟังหน่อย") is True

    # Negative queries (operational or pure philosophical)
    assert engine.is_grounding_query("เปิด Google Chrome ให้หน่อย") is False
    assert engine.is_grounding_query("ทำไมมนุษย์ถึงมีความฝัน") is False
    assert engine.is_grounding_query("cls") is False


def test_detect_category(engine):
    assert engine.detect_category("วันนี้มีข่าวเทคโนโลยีอะไรบ้าง") == "technology"
    assert engine.detect_category("อัปเดตเรื่อง AI ล่าสุด") == "technology"
    assert engine.detect_category("วันนี้มีอะไรใหม่ๆน่าสนใจบ้าง") == "general"
    assert engine.detect_category("สถานการณ์บ้านเมืองวันนี้") == "general"


def test_fetch_live_headlines_mocked(engine):
    mock_rss = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Google News</title>
        <item><title>Mocked Headline 1 - Test News</title></item>
        <item><title>Mocked Headline 2 - Tech Update</title></item>
      </channel>
    </rss>
    """
    mock_response = MagicMock()
    mock_response.read.return_value = mock_rss
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        headlines = engine.fetch_live_headlines("วันนี้มีข่าวอะไรบ้าง", limit=2)
        assert len(headlines) == 2
        assert headlines[0] == "Mocked Headline 1 - Test News"
        assert headlines[1] == "Mocked Headline 2 - Tech Update"


def test_get_grounding_prompt_injection(engine):
    with patch.object(engine, "fetch_live_headlines", return_value=["Live Story A", "Live Story B"]):
        injection = engine.get_grounding_prompt_injection("วันนี้มีอะไรใหม่ๆน่าสนใจบ้าง")
        assert injection is not None
        assert "REAL-TIME TEMPORAL GROUNDING" in injection
        assert "CURRENT REAL-WORLD TIME:" in injection
        assert "Live Story A" in injection
        assert "NEVER fabricate or hallucinate" in injection


def test_subtext_engine_intent_triage():
    # Should classify into realtime_intel
    assert subtext_engine.classify_intent("วันนี้มีอะไรใหม่ๆน่าสนใจบ้าง") == "realtime_intel"
    assert subtext_engine.classify_intent("สรุปข่าววันนี้ให้หน่อย") == "realtime_intel"

    # Should classify into reflective
    assert subtext_engine.classify_intent("จาร์วิส วันนี้ผมรู้สึกเหนื่อยมาก งานกองเต็มไปหมด") == "reflective"
    assert subtext_engine.classify_intent("นายคิดว่าอนาคตความเป็นมนุษย์กับ AI จะเป็นอย่างไร") == "reflective"

    # Should classify into operational
    assert subtext_engine.classify_intent("เปิด Google Chrome ให้หน่อย") == "operational"
    assert subtext_engine.classify_intent("ปิดไฟ") == "operational"


def test_ai_router_grounding_integration():
    from jarvis_core.ai_router import call_nachapol_core

    with patch("jarvis_core.cognitive.grounding_engine.grounding_engine.fetch_live_headlines", return_value=["Verified Event Today"]):
        with patch("jarvis_core.ai_router.call_groq_model") as mock_groq:
            mock_groq.return_value = {"content": "รายงานข่าวสดครับ", "tool_calls": []}

            messages = [
                {"role": "system", "content": "You are J.A.R.V.I.S."},
                {"role": "user", "content": "วันนี้มีอะไรใหม่ๆน่าสนใจบ้าง"}
            ]

            response = call_nachapol_core(messages=messages)
            assert response is not None
            assert "Verified Event Today" in messages[0]["content"]
            assert "REAL-TIME TEMPORAL GROUNDING" in messages[0]["content"]
