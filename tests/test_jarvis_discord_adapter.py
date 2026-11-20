"""
Unit tests for modules/jarvis_discord_adapter.py
Follows pytest-mock-master: zero real network calls, zero sleeping loops, clean teardown.
"""

from unittest.mock import MagicMock, patch

import pytest

from modules.jarvis_discord_adapter import (
    JarvisDiscordAdapter,
    format_reply_for_discord,
    split_discord_message,
)


@pytest.fixture(autouse=True)
def _isolate_discord_env(monkeypatch):
    monkeypatch.delenv("DISCORD_OWNER_USER_ID", raising=False)
    monkeypatch.delenv("DISCORD_ALLOWED_CHANNELS", raising=False)


def test_format_reply_preserves_markdown_and_strips_internal_tags():
    raw = (
        "[WINDOW:HUD][SYSTEM_NOTE] สวัสดีครับ**เจ้านาย**<br>"
        "โค้ดคือ `print(1)`<img src='/static/a.png'> [END_WINDOW]"
    )
    cleaned = format_reply_for_discord(raw)
    assert "**เจ้านาย**" in cleaned
    assert "`print(1)`" in cleaned
    assert "\n" in cleaned
    assert "[WINDOW:HUD]" not in cleaned
    assert "[END_WINDOW]" not in cleaned
    assert "<img" not in cleaned


def test_format_reply_preserves_multiline_lists_and_headings():
    raw = (
        "รับทราบครับ ### 1. ตรวจสอบสถานี S340\n"
        "- **ตรวจวัดอุณหภูมิ**: ปกติ ≈48°C\n"
        "- **Full Diagnostic**: ตรวจเช็ก RAM\n\n"
        "### 2. งานประกอบ\n"
        "1. ตัดแผ่นอะคริลิค\n"
        "2. วัดค่าตัวต้านทาน"
    )
    cleaned = format_reply_for_discord(raw)
    lines = cleaned.splitlines()
    assert lines[0] == "รับทราบครับ"
    assert "### 1. ตรวจสอบสถานี S340" in lines
    assert "- **ตรวจวัดอุณหภูมิ**: ปกติ ≈48°C" in lines
    assert "- **Full Diagnostic**: ตรวจเช็ก RAM" in lines
    assert "### 2. งานประกอบ" in lines
    assert "1. ตัดแผ่นอะคริลิค" in lines
    assert "2. วัดค่าตัวต้านทาน" in lines


def test_router_cadence_and_screen_context_guards():
    from jarvis_core.ai_router import sanitize_thai_cadence
    from modules.jarvis_screen_context import enrich_messages_with_screen_context

    sample = (
        "รับทราบครับ\n"
        "### 1. ตรวจสอบระบบ\n"
        "- **CPU**: ปกติ\n"
        "  - **RAM**: 78%\n\n"
        "### 2. ขั้นตอนถัดไป\n"
        "- ดำเนินการต่อ"
    )
    cleaned = sanitize_thai_cadence(sample)
    assert "\n### 1. ตรวจสอบระบบ\n- **CPU**: ปกติ" in cleaned
    assert "\n\n### 2. ขั้นตอนถัดไป\n- ดำเนินการต่อ" in cleaned

    internal_msgs = [
        {
            "role": "user",
            "content": "ข้อมูลบริบทและระบบปัจจุบัน:\nหน้าจอที่เปิดอยู่\n\nโจทย์ที่ต้องวางแผน: มีอะไรแนะนำผมมั้ยทำไรดี",
        }
    ]
    enrich_messages_with_screen_context(internal_msgs)
    assert isinstance(internal_msgs[-1]["content"], str)


def test_split_discord_message_respects_limit():
    long_text = ("บรรทัดทดสอบระบบ J.A.R.V.I.S.\n" * 120).strip()
    chunks = split_discord_message(long_text, max_len=500)
    assert len(chunks) >= 3
    assert all(len(c) <= 500 for c in chunks)


def test_should_respond_routing_rules():
    adapter = JarvisDiscordAdapter(token="fake-token")
    adapter._bot_user_id = "999999"
    adapter._allowed_channels = {"chan_allowed"}

    # Ignore bot messages
    ok, _ = adapter.should_respond_to_message({"author": {"id": "1", "bot": True}, "content": "!jarvis hi"})
    assert not ok

    # Respond in DM
    ok, text = adapter.should_respond_to_message({"author": {"id": "123", "bot": False}, "guild_id": None, "channel_id": "dm1", "content": "สวัสดี"})
    assert ok and text == "สวัสดี"

    # Respond on @mention and strip mention
    ok, text = adapter.should_respond_to_message({"author": {"id": "123", "bot": False}, "guild_id": "g1", "channel_id": "c1", "content": "<@999999> เช็กสถานะ"})
    assert ok and text == "เช็กสถานะ"

    # Respond on !jarvis prefix
    ok, text = adapter.should_respond_to_message({"author": {"id": "123", "bot": False}, "guild_id": "g1", "channel_id": "c1", "content": "!jarvis รายงานระบบ"})
    assert ok and text == "รายงานระบบ"

    # Ignore unmentioned chatter in non-allowed channel
    ok, _ = adapter.should_respond_to_message({"author": {"id": "123", "bot": False}, "guild_id": "g1", "channel_id": "c_other", "content": "คุยเล่นทั่วไป"})
    assert not ok

    # Respond in explicitly allowed channel
    ok, text = adapter.should_respond_to_message({"author": {"id": "123", "bot": False}, "guild_id": "g1", "channel_id": "chan_allowed", "content": "เปิดไฟ"})
    assert ok and text == "เปิดไฟ"


def test_lifecycle_and_execute_intent_mocked(monkeypatch):
    monkeypatch.delenv("DISCORD_OWNER_USER_ID", raising=False)
    monkeypatch.delenv("DISCORD_ALLOWED_CHANNELS", raising=False)
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = b'{"id": "1573284364500865075", "username": "J.A.R.V.I.S."}'
    fake_resp.json.return_value = {"id": "1573284364500865075", "username": "J.A.R.V.I.S."}

    chat_mock = MagicMock(return_value="รับทราบครับเจ้านาย")
    adapter = JarvisDiscordAdapter(chat_handler=chat_mock, token="fake-token-for-test")

    with patch("modules.jarvis_discord_adapter.requests.request", return_value=fake_resp) as mock_req:
        assert adapter.initialize(config={"start_gateway": False, "notify_channel_id": "ch_1"}) is True
        telemetry = adapter.get_telemetry()
        assert telemetry["active"] is True
        assert telemetry["bot_username"] == "J.A.R.V.I.S."

        res = adapter.execute_intent("notify", {"title": "Test", "message": "System online", "level": "success"})
        assert res["status"] == "success"

        adapter._process_incoming_message({
            "id": "m_1",
            "channel_id": "ch_1",
            "guild_id": None,
            "author": {"id": "u_1", "username": "Nachapol", "bot": False},
            "content": "สถานะระบบ",
        })
        chat_mock.assert_called_once()
        assert adapter.get_telemetry()["metrics"]["messages_replied"] == 1
        assert mock_req.call_count >= 3

    adapter.shutdown(timeout=1.0)
    assert adapter.get_telemetry()["active"] is False


def test_auto_role_on_member_join():
    fake_resp = MagicMock()
    fake_resp.status_code = 204
    fake_resp.content = b""

    adapter = JarvisDiscordAdapter(token="fake-token-for-test")
    with patch("modules.jarvis_discord_adapter.requests.request", return_value=fake_resp) as mock_req:
        assert adapter.initialize(
            config={
                "start_gateway": False,
                "skip_verify": True,
                "auto_role_id": "role_friend_123",
                "welcome_channel_id": "chan_welcome_456",
            }
        ) is True

        # Bots must be ignored
        adapter._process_member_join({"guild_id": "g1", "user": {"id": "b1", "username": "OtherBot", "bot": True}})
        assert mock_req.call_count == 0

        # Human join assigns role + sends welcome embed
        adapter._process_member_join({"guild_id": "g1", "user": {"id": "u_new", "username": "NewFriend", "bot": False}})
        assert adapter.get_telemetry()["metrics"]["auto_roles_assigned"] == 1
        assert mock_req.call_count == 2
        put_call = mock_req.call_args_list[0].kwargs
        assert put_call["method"] == "PUT"
        assert "/guilds/g1/members/u_new/roles/role_friend_123" in put_call["url"]

    adapter.shutdown(timeout=1.0)


def test_clear_command_preserves_welcome_embed_and_bypasses_llm():
    chat_mock = MagicMock(return_value="should not be called")
    adapter = JarvisDiscordAdapter(chat_handler=chat_mock, token="fake-token-for-test")
    adapter._clear_toast_delay = 0.0

    # Mock GET messages, POST bulk-delete, POST toast
    fake_messages = [
        {"id": "1573298987933372477", "author": {"id": "b1", "bot": True}, "content": "hi", "embeds": [], "pinned": False},
        {"id": "1573298575465779323", "author": {"id": "u1", "bot": False}, "content": "!clear", "embeds": [], "pinned": False},
        {"id": "1573292071094325259", "author": {"id": "b1", "bot": True}, "content": "", "embeds": [{"title": "WELCOME"}], "pinned": False},
    ]

    def fake_request(method, url, headers=None, json=None, timeout=15.0):
        resp = MagicMock()
        if method == "GET" and "/messages" in url:
            resp.status_code = 200
            resp.content = b"[...]"
            resp.json.return_value = fake_messages
        elif method == "POST" and "/bulk-delete" in url:
            resp.status_code = 204
            resp.content = b""
        else:
            resp.status_code = 200
            resp.content = b'{"id": "toast_1"}'
            resp.json.return_value = {"id": "toast_1"}
        return resp

    with patch("modules.jarvis_discord_adapter.requests.request", side_effect=fake_request) as mock_req:
        assert adapter.initialize(config={"start_gateway": False, "skip_verify": True}) is True
        adapter._process_incoming_message({
            "id": "1573298575465779323",
            "channel_id": "ch_cmd",
            "guild_id": "g1",
            "author": {"id": "u1", "username": "neon63445654", "bot": False},
            "content": "!clear",
        })
        chat_mock.assert_not_called()
        bulk_calls = [c for c in mock_req.call_args_list if "/bulk-delete" in c.kwargs["url"]]
        assert len(bulk_calls) == 1
        deleted_ids = bulk_calls[0].kwargs["json"]["messages"]
        assert "1573292071094325259" not in deleted_ids  # Welcome Embed preserved!
        assert set(deleted_ids) == {"1573298987933372477", "1573298575465779323"}

    adapter.shutdown(timeout=1.0)
