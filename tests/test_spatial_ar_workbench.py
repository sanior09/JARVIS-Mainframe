"""
tests/test_spatial_ar_workbench.py
──────────────────────────────────────────────────────────────────────────────
Pytest test suite for SpatialARWorkbench Subsystem.
Validates image optimization, multi-candidate detection, interactive selection,
single-target auto-deep-dive, and card synthesis.
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


def test_scan_desk_candidates_multiple(workbench):
    mock_candidates_json = """{
      "candidates": [
        {"id": 1, "name": "Flipper Zero", "name_th": "อุปกรณ์ Flipper Zero", "category": "RF Tool", "bbox": [30, 35, 60, 60]},
        {"id": 2, "name": "Mechanical Keyboard", "name_th": "คีย์บอร์ดกลไก", "category": "Peripheral", "bbox": [65, 20, 85, 80]}
      ]
    }"""

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_candidates_json
    mock_response.choices = [mock_choice]

    img = Image.new("RGB", (100, 100), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    with patch("os.getenv", return_value="fake_groq_key"):
        with patch("groq.Groq") as mock_groq_cls:
            mock_client = MagicMock()
            mock_groq_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            result = workbench.scan_desk_candidates(b64)
            assert result["success"] is True
            assert result["mode"] == "multiple_candidates"
            assert result["total_detected"] == 2
            assert len(result["candidates"]) == 2
            assert "เจ้านายต้องการให้ผมหาข้อมูลของชิ้นไหนครับ" in result["voice_text"]


def test_scan_desk_candidates_single_auto_deep_dive(workbench):
    mock_single_json = """{
      "candidates": [
        {"id": 1, "name": "Flipper Zero", "name_th": "อุปกรณ์ Flipper Zero", "category": "RF Tool", "bbox": [30, 35, 60, 60]}
      ]
    }"""

    mock_deep_dive_data = {
        "success": True,
        "target_name": "Flipper Zero",
        "bbox": [30.0, 35.0, 60.0, 60.0],
        "pricing_card": {"price_usd": "$199"},
        "voice_text": "สแกนตรวจพบ Flipper Zero เรียบร้อยครับ"
    }

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_single_json
    mock_response.choices = [mock_choice]

    img = Image.new("RGB", (100, 100), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    with patch("os.getenv", return_value="fake_groq_key"):
        with patch("groq.Groq") as mock_groq_cls:
            mock_client = MagicMock()
            mock_groq_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            with patch.object(workbench, "deep_dive_target", return_value=mock_deep_dive_data):
                result = workbench.scan_desk_candidates(b64)
                assert result["success"] is True
                assert result["mode"] == "single_target_auto"
                assert result["target_name"] == "Flipper Zero"


def test_resolve_target_selection_by_index(workbench):
    workbench.last_scanned_candidates = [
        {"id": 1, "name": "Flipper Zero", "bbox": [30, 35, 60, 60]},
        {"id": 2, "name": "Mechanical Keyboard", "bbox": [65, 20, 85, 80]}
    ]
    workbench.last_image_base64 = "dummy_base64"

    mock_deep_dive_result = {
        "success": True,
        "target_name": "Mechanical Keyboard",
        "bbox": [65.0, 20.0, 85.0, 80.0],
        "voice_text": "สแกนคีย์บอร์ดเรียบร้อยครับ"
    }

    with patch.object(workbench, "deep_dive_target", return_value=mock_deep_dive_result) as mock_dive:
        res = workbench.resolve_target_selection("หาข้อมูลเกี่ยวกับชิ้นที่ 2 ให้หน่อย")
        assert res["target_name"] == "Mechanical Keyboard"
        mock_dive.assert_called_once_with("dummy_base64", "Mechanical Keyboard", [65, 20, 85, 80])


def test_analyze_desk_object_followup_detection(workbench):
    workbench.last_scanned_candidates = [
        {"id": 1, "name": "Flipper Zero", "bbox": [30, 35, 60, 60]}
    ]
    workbench.last_image_base64 = "dummy_base64"

    with patch.object(workbench, "resolve_target_selection") as mock_resolve:
        mock_resolve.return_value = {"success": True, "target_name": "Flipper Zero"}
        workbench.analyze_desk_object("dummy_base64", "หาข้อมูลเกี่ยวกับสิ่งที่อยู่ในวงให้หน่อย")
        mock_resolve.assert_called_once_with("หาข้อมูลเกี่ยวกับสิ่งที่อยู่ในวงให้หน่อย", "dummy_base64")
