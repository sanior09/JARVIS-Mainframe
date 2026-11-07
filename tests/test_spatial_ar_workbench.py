"""
tests/test_spatial_ar_workbench.py
──────────────────────────────────────────────────────────────────────────────
Pytest test suite for SpatialARWorkbench Subsystem.
Validates image optimization, bounding box clamping, card synthesis, and video lookup.
"""

import base64
import io
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from modules.spatial_ar_workbench import SpatialARWorkbench


@pytest.fixture
def workbench():
    wb = SpatialARWorkbench()
    wb.initialize()
    return wb


def test_workbench_initialization(workbench):
    assert workbench.is_active is True
    telemetry = workbench.get_telemetry()
    assert telemetry["name"] == "SpatialARWorkbench"
    assert telemetry["active"] is True


def test_optimize_image_payload(workbench):
    # Create small 16x16 image
    img = Image.new("RGB", (16, 16), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_raw = base64.b64encode(buf.getvalue()).decode()

    # Optimized image should upscale to at least 64x64
    optimized_b64 = workbench._optimize_image_payload(b64_raw)
    out_img = Image.open(io.BytesIO(base64.b64decode(optimized_b64)))
    assert out_img.size[0] >= 64
    assert out_img.size[1] >= 64


def test_analyze_desk_object_mocked(workbench):
    mock_llm_json = """{
      "target_name": "Flipper Zero Multi-Tool",
      "brand": "Flipper Devices",
      "category": "Penetration Testing Transceiver",
      "bbox": [32.5, 38.0, 68.0, 64.5],
      "specs_card": {
        "title": "SECURITY & ARCHITECTURE",
        "items": ["Sub-GHz Transceiver CC1101", "RFID 125kHz", "STM32WB55 Dual Core"]
      },
      "llm_card": {
        "title": "LLM & VOICE INTEGRATION",
        "items": ["Zero-shot command execution", "UART bridging"]
      },
      "pricing_card": {
        "price_usd": "$199",
        "price_thb": "฿7,200",
        "status": "OFFICIAL MSRP",
        "badge": "VERIFIED"
      },
      "display_card": {
        "title": "DISPLAY & INTERFACES",
        "items": ["Monochrome LCD 128x64", "5-Way Pad"]
      },
      "telemetry_card": {
        "score": 88,
        "score_label": "CAPABILITY INDEX",
        "metrics": [{"label": "RF", "value": 95}, {"label": "NFC", "value": 90}]
      },
      "video_query": "Flipper Zero review",
      "brief_summary_th": "อุปกรณ์มัลติทูลสำหรับทดสอบความปลอดภัยความถี่วิทยุและ RFID"
    }"""

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_llm_json
    mock_response.choices = [mock_choice]

    # Create dummy 100x100 image
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_input = base64.b64encode(buf.getvalue()).decode()

    with patch("os.getenv", return_value="fake_groq_key"):
        with patch("groq.Groq") as mock_groq_cls:
            mock_client = MagicMock()
            mock_groq_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            with patch.object(workbench, "_find_youtube_video_id", return_value="test_yt_id"):
                result = workbench.analyze_desk_object(b64_input, "สแกนวัตถุนี้ให้หน่อย")

                assert result["success"] is True
                assert result["target_name"] == "Flipper Zero Multi-Tool"
                assert result["bbox"] == [32.5, 38.0, 68.0, 64.5]
                assert result["pricing_card"]["price_usd"] == "$199"
                assert result["video_id"] == "test_yt_id"
                assert "ตรวจพบ Flipper Zero Multi-Tool เรียบร้อยครับเจ้านาย" in result["voice_text"]
