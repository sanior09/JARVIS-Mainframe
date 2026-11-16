"""
Tests for Nachapol AI Office backend, Flask REST endpoints, multi-agent @mention routing,
and frontend asset cleanliness.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from jarvis_core.web_app import create_app
from jarvis_agents.jarvis_multi_agent import route_intent
from modules.agent_office import (
    AgentOfficeManager,
    agent_office_manager,
    classify_task_room,
    parse_direct_prompt,
    resolve_agent_id,
)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    agent_office_manager.reset_office()
    with app.test_client() as c:
        yield c


def test_agent_office_aliases_and_handoff_parsing():
    assert resolve_agent_id("@code") == "friday"
    assert resolve_agent_id("@web") == "edith"
    assert resolve_agent_id("@os") == "dume"
    assert resolve_agent_id("@cli") == "jocasta"

    parsed = parse_direct_prompt("@friday -> @veronica ตรวจสอบโมดูลเสียง")
    assert parsed["agent_id"] == "friday"
    assert parsed["handoff_to"] == "veronica"
    assert parsed["clean_prompt"] == "ตรวจสอบโมดูลเสียง"


def test_situational_shared_room_routing():
    assert classify_task_room("ช่วยเขียน code python api และแก้ bug", "dume") == "dev_lab"
    assert classify_task_room("ตรวจสอบ sensor esp32 และสั่ง 3d print เคส", "friday") == "maker_iot"
    assert classify_task_room("สแกนช่องโหว่ network และตรวจ chromadb", "u") == "data_net"
    assert classify_task_room("ตรวจสอบภาพ screenshot และเสียง tts", "jocasta") == "media_qa"
    assert classify_task_room("ค้นหาข่าวล่าสุดบน web", "veronica") == "intel_lab"
    assert classify_task_room("เช็คการใช้ ram cpu และไฟล์ log บน windows", "edith") == "sys_ops"


def test_multi_agent_router_supports_explicit_mentions():
    assert route_intent("@friday ช่วยตรวจโค้ดหน่อย") == "friday"
    assert route_intent("@code รีแฟกเตอร์ฟังก์ชันนี้") == "friday"
    assert route_intent("@veronica เช็คโหลด RAM") == "veronica"
    assert route_intent("@edith ประเมินความเสี่ยง") == "edith"
    assert route_intent("@u ล้างแคชระบบ") == "u"
    assert route_intent("@dume กดปุ่มยืนยัน") == "dume"
    assert route_intent("@jocasta สแกนช่องโหว่") == "jocasta"
    assert route_intent("@karen สรุปงานวันนี้") == "karen"
    assert route_intent("@web ค้นข่าวล่าสุด") == "research"
    assert route_intent("@os เปิด task manager") == "os_control"


def test_api_office_state_and_command_with_handoff(client):
    res = client.get("/api/office/state")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"
    assert len(data["agents"]) == 8
    assert all(a["state"] == "IDLE" for a in data["agents"])

    with patch.object(
        agent_office_manager,
        "_invoke_specialist",
        side_effect=lambda aid, prompt, context="": f"[{aid.upper()}] ok: {prompt[:30]}",
    ) as mock_exec:
        cmd_res = client.post(
            "/api/office/command",
            data=json.dumps({
                "prompt": "@friday -> @veronica ตรวจความปลอดภัยระบบเสียง",
                "async": False,
            }),
            content_type="application/json",
        )
        assert cmd_res.status_code == 200
        cmd_data = cmd_res.get_json()
        assert cmd_data["agent_id"] == "friday"
        assert cmd_data["handoff_to"] == "veronica"
        assert mock_exec.call_count == 2

    after = client.get("/api/office/state").get_json()
    assert after["summary"]["done_tasks"] == 2
    by_id = {a["agent_id"]: a for a in after["agents"]}
    assert by_id["friday"]["completed_count"] >= 1
    assert by_id["veronica"]["completed_count"] >= 1
    assert by_id["friday"]["state"] == "IDLE"
    assert by_id["veronica"]["state"] == "IDLE"


def test_api_office_meeting_mission_pipeline(client):
    mgr_states_seen = []
    orig_set = agent_office_manager._set_agent_state

    def _spy_set(agent_id, **kwargs):
        if kwargs.get("state"):
            mgr_states_seen.append((agent_id, kwargs["state"]))
        return orig_set(agent_id, **kwargs)

    with (
        patch.object(agent_office_manager, "_set_agent_state", side_effect=_spy_set),
        patch.object(
            agent_office_manager,
            "_decompose_mission",
            return_value={
                "friday": "วางสถาปัตยกรรมโค้ด",
                "veronica": "ประเมินความปลอดภัยฮาร์ดแวร์",
            },
        ),
        patch.object(
            agent_office_manager,
            "_invoke_specialist",
            side_effect=lambda aid, prompt, context="": f"ผลลัพธ์จาก {aid}: เรียบร้อย",
        ),
    ):
        res = client.post(
            "/api/office/mission",
            data=json.dumps({
                "mission": "สร้างระบบแดชบอร์ดมอนิเตอร์เซิร์ฟเวอร์",
                "agents": ["friday", "veronica"],
                "async": False,
            }),
            content_type="application/json",
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["status"] == "accepted"
        assert body["quorum"] == ["friday", "veronica"]

    # Confirm Meeting phase + Desk Working phase occurred before returning to IDLE
    assert ("friday", "MEETING") in mgr_states_seen
    assert ("veronica", "MEETING") in mgr_states_seen
    assert ("friday", "CODING") in mgr_states_seen
    assert ("veronica", "SEARCHING") in mgr_states_seen

    snap = client.get("/api/office/state").get_json()
    assert snap["summary"]["done_tasks"] == 3  # 1 mission + 2 subtasks
    assert snap["feed"][0]["kind"] == "synthesis"


def test_api_office_chat_and_reset(client):
    with patch.object(
        agent_office_manager,
        "_invoke_specialist",
        return_value="รับทราบครับ F.R.I.D.A.Y. แรมเครื่องยังเหลือเฟือครับ",
    ):
        chat_res = client.post(
            "/api/office/chat",
            data=json.dumps({
                "from_agent": "friday",
                "to_agent": "veronica",
                "message": "RAM พอสำหรับ build ไหม?",
                "async": False,
            }),
            content_type="application/json",
        )
        assert chat_res.status_code == 200

    snap = client.get("/api/office/state").get_json()
    assert any(f["from_agent"] == "veronica" and f["to_agent"] == "friday" for f in snap["feed"])

    reset_res = client.post("/api/office/reset")
    assert reset_res.status_code == 200
    reset_snap = reset_res.get_json()
    assert reset_snap["summary"]["done_tasks"] == 0


def test_old_office_files_removed_and_new_assets_wired():
    legacy_paths = [
        "empty_office.jpg",
        "pixel_office.jpg",
        "friday.png",
        "veronica.png",
        "web.png",
        "cli.png",
        "os.png",
        "code.png",
    ]
    for fname in legacy_paths:
        assert not os.path.exists(os.path.join(BASE_DIR, "web", fname))

    for new_file in ("agent_office.css", "agent_office.js", "mindspace_studio_3d.jpg"):
        assert os.path.exists(os.path.join(BASE_DIR, "web", new_file))

    with open(os.path.join(BASE_DIR, "web", "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    assert "agent_office.css" in html
    assert "agent_office.js" in html


def test_real_system_live_telemetry_hooks_and_core_executor():
    mgr = AgentOfficeManager()

    # 1. Live turn start/end from HUD chat moves specialist to situational room and resets cleanly
    t_ctx = mgr.notify_live_turn_start("ช่วยค้นหาข่าวเทคโนโลยีวันนี้บนเว็บ", routed_intent="research", channel="hud")
    assert t_ctx is not None
    assert t_ctx["agent_id"] == "edith"
    assert t_ctx["zone"] == "intel_lab"

    snap = mgr.get_state_snapshot()
    by_id = {a["agent_id"]: a for a in snap["agents"]}
    assert by_id["edith"]["state"] == "SEARCHING"
    assert by_id["edith"]["zone"] == "intel_lab"

    # Overlapping real tool call refcount stays busy until BOTH end
    tool_ctx = mgr.notify_live_tool_start("search_web", {"query": "AI news"}, "ค้นหาข่าว")
    assert tool_ctx["agent_id"] == "edith"
    tool_hw = mgr.notify_live_tool_start("flash_esp32_firmware", {"port": "COM3"})
    assert tool_hw["agent_id"] == "dume"
    assert tool_hw["zone"] == "maker_iot"

    mgr.notify_live_turn_end(t_ctx, "สรุปข่าวเรียบร้อย")
    # Tool is still open on edith, so refcount keeps edith active until tool ends
    snap_mid = {a["agent_id"]: a for a in mgr.get_state_snapshot()["agents"]}
    assert snap_mid["edith"]["state"] != "IDLE"
    assert snap_mid["dume"]["state"] == "EXECUTING"

    mgr.notify_live_tool_end(tool_ctx, "พบ 5 ข่าว")
    mgr.notify_live_tool_end(tool_hw, "Flash complete")
    snap_end = {a["agent_id"]: a for a in mgr.get_state_snapshot()["agents"]}
    assert snap_end["edith"]["state"] == "IDLE"
    assert snap_end["dume"]["state"] == "IDLE"

    # 2. Core executor hook runs real pipeline and suppresses duplicate turn hook
    called = []

    def fake_core(aid, prompt, ctx):
        called.append((aid, prompt))
        # Simulate recursive call_model_node check while flag is suppressed
        assert mgr.notify_live_turn_start(prompt, routed_intent="general", channel="hud") is None
        return "คำตอบจากระบบจริง"

    mgr.attach_core_executor(fake_core)
    reply = mgr._invoke_specialist("friday", "เช็คสถานะ", "")
    assert reply == "คำตอบจากระบบจริง"
    assert called == [("friday", "เช็คสถานะ")]
