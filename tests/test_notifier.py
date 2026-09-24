"""
Unit Tests for JarvisNotifier (Mocking network/LINE API)
"""

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch
import pytest

# Add project root and modules to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from modules.jarvis_notifier import JarvisNotifier


def test_notifier_configuration():
    notifier = JarvisNotifier(access_token="test_token", owner_id="U123456789")
    assert notifier.is_configured is True
    assert notifier._access_token == "test_token"
    assert notifier._owner_id == "U123456789"


def test_notifier_not_configured():
    notifier = JarvisNotifier(access_token="", owner_id="")
    assert notifier.is_configured is False
    assert notifier.send_push_sync("Hello") is False


def test_notifier_cooldown_suppression():
    notifier = JarvisNotifier(access_token="test_token", owner_id="U123456789")
    key = "test_alert_key"

    # First time should NOT suppress
    assert notifier._should_suppress(key, cooldown_sec=10) is False
    # Immediately after should suppress
    assert notifier._should_suppress(key, cooldown_sec=10) is True
    # Different key should NOT suppress
    assert notifier._should_suppress("different_key", cooldown_sec=10) is False


@patch("requests.post")
def test_notifier_send_push_sync_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    notifier = JarvisNotifier(access_token="token_xyz", owner_id="user_abc")
    success = notifier.send_push_sync("สวัสดีครับเจ้านาย งานสำเร็จแล้ว")

    assert success is True
    assert mock_post.called
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == JarvisNotifier.LINE_PUSH_URL
    assert call_kwargs["headers"]["Authorization"] == "Bearer token_xyz"
    assert call_kwargs["headers"]["Content-Type"] == "application/json"

    sent_data = json.loads(call_kwargs["data"].decode("utf-8"))
    assert sent_data["to"] == "user_abc"
    assert len(sent_data["messages"]) == 1
    assert "สวัสดีครับเจ้านาย งานสำเร็จแล้ว" in sent_data["messages"][0]["text"]


@patch("requests.post")
def test_notifier_send_push_sync_api_error(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid access token"
    mock_post.return_value = mock_resp

    notifier = JarvisNotifier(access_token="bad_token", owner_id="user_abc")
    success = notifier.send_push_sync("ทดสอบข้อผิดพลาด")

    assert success is False


@patch("requests.post")
def test_notifier_notify_methods(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    notifier = JarvisNotifier(access_token="token_xyz", owner_id="user_abc")

    # 1. notify_success
    notifier.notify_success(task="Computer Agent Task", detail="เปิดโปรแกรมเรียบร้อย")
    # Wait for background thread executor to complete task
    time.sleep(0.1)
    assert mock_post.called

    # 2. notify_error
    mock_post.reset_mock()
    notifier.notify_error(error="Timeout connecting to server", context="Cloud Sync")
    time.sleep(0.1)
    assert mock_post.called

    # 3. notify_alert
    mock_post.reset_mock()
    notifier.notify_alert(msg="CPU load is 98%", level="CRITICAL", alert_key="cpu_test")
    time.sleep(0.1)
    assert mock_post.called

    # 4. notify_info
    mock_post.reset_mock()
    notifier.notify_info(title="System Ready", body="All subsystems nominal")
    time.sleep(0.1)
    assert mock_post.called


def test_notifier_text_truncation():
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        notifier = JarvisNotifier(access_token="token_xyz", owner_id="user_abc")
        huge_message = "A" * 3000
        notifier.send_push_sync(huge_message)

        sent_data = json.loads(mock_post.call_args[1]["data"].decode("utf-8"))
        sent_text = sent_data["messages"][0]["text"]
        assert len(sent_text) <= 2000
        assert sent_text.endswith("...")
