"""
tests/test_spatial_ar_api.py
──────────────────────────────────────────────────────────────────────────────
Pytest test suite for /api/spatial/ar_recon endpoint.
"""

import base64
import io
import json
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from jarvis_core.web_app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_spatial_ar_recon_no_image(client):
    response = client.post("/api/spatial/ar_recon", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_api_spatial_ar_recon_success(client):
    img = Image.new("RGB", (80, 80), color="cyan")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    mock_recon_data = {
        "success": True,
        "target_name": "Flipper Zero",
        "bbox": [30.0, 35.0, 68.0, 65.0],
        "specs_card": {"title": "SECURITY", "items": ["Sub-GHz", "NFC"]},
        "pricing_card": {"price_usd": "$199", "price_thb": "฿7,200"},
        "telemetry_card": {"score": 88, "score_label": "CAPABILITY", "metrics": []},
        "video_id": "test_id",
        "voice_text": "สแกนวัตถุบนโต๊ะเรียบร้อยครับ"
    }

    with patch("modules.spatial_ar_workbench.spatial_ar_workbench.analyze_desk_object", return_value=mock_recon_data):
        response = client.post(
            "/api/spatial/ar_recon",
            json={"image": b64, "prompt": "สแกนสิ่งนี้ให้หน่อย"}
        )
        assert response.status_code == 200
        res_json = response.get_json()
        assert res_json["success"] is True
        assert res_json["target_name"] == "Flipper Zero"
        assert res_json["pricing_card"]["price_usd"] == "$199"
        assert res_json["video_id"] == "test_id"
