"""
tests/test_web_app.py
Tests for Flask Web Application Factory and API endpoints.
Verifies health status, telemetry, voice status, and Computer Use REST APIs.
"""

import json
import pytest
from jarvis_core.web_app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.mark.unit
def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"


@pytest.mark.unit
def test_api_telemetry(client):
    res = client.get("/api/telemetry")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "Online"
    assert "cores" in data
    assert "metrics" in data


@pytest.mark.unit
def test_api_voice_status(client):
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "is_listening" in data
    assert "is_busy" in data


@pytest.mark.agent
def test_api_computer_windows(client):
    res = client.get("/api/computer/windows")
    assert res.status_code == 200
    data = res.get_json()
    assert "windows" in data
    assert "total_windows" in data


@pytest.mark.agent
def test_api_computer_screenshot(client):
    res = client.get("/api/computer/screenshot")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "image_base64" in data
    assert len(data["image_base64"]) > 50


@pytest.mark.agent
def test_api_computer_execute(client):
    res = client.post(
        "/api/computer/execute",
        data=json.dumps({"goal": "จับภาพหน้าจอคอมพิวเตอร์"}),
        content_type="application/json"
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] in ("success", "completed")


@pytest.mark.unit
def test_chat_empty_message(client):
    res = client.post(
        "/chat",
        data=json.dumps({"message": ""}),
        content_type="application/json"
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "ว่างเปล่า" in data["response"]
