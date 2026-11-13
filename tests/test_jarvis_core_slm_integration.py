"""
Integration tests for Step 4: C:\\JarvisCore (8 Forged BPE Personas) <-> C:\\JARVIS Mainframe Bridge.
"""

import pytest
from modules.jarvis_slm_bridge import get_jarviscore_bridge
from jarvis_core.cognitive.swarm import AgentCouncil
from jarvis_core.ai_router import call_nachapol_core


@pytest.fixture(scope="module", autouse=True)
def cleanup_bridge_worker():
    yield
    bridge = get_jarviscore_bridge()
    bridge.shutdown()


def test_bridge_discovers_all_eight_forged_personas():
    bridge = get_jarviscore_bridge()
    personas = bridge.list_forged_personas()
    expected = {"jarvis", "friday", "veronica", "edith", "u", "dume", "jocasta", "karen"}
    assert expected.issubset(set(personas)), f"Missing forged personas: {expected - set(personas)}"


def test_bridge_live_bpe_inference_multiple_personas():
    bridge = get_jarviscore_bridge()
    assert bridge.initialize() is True

    res_jocasta = bridge.generate_persona_response("jocasta", "สแกนช่องโหว่", max_new_tokens=16)
    assert res_jocasta.get("ok") is True
    assert res_jocasta.get("persona") == "jocasta"
    assert res_jocasta.get("tokenizer") == "bpe"
    assert res_jocasta.get("vocab_size", 0) >= 100290

    res_karen = bridge.generate_persona_response("karen", "เหนื่อยมากวันนี้", max_new_tokens=16)
    assert res_karen.get("ok") is True
    assert res_karen.get("persona") == "karen"


def test_ai_router_native_jarviscore_routing():
    res = call_nachapol_core(
        messages=[{"role": "user", "content": "รายงานสถานะ"}],
        model="jarviscore:jarvis",
    )
    assert "error_message" not in res
    assert isinstance(res.get("content"), str)
    assert len(res["content"]) > 0


def test_swarm_council_native_zero_cloud_debate():
    council = AgentCouncil()
    report = council.hold_council_debate(
        query="วิเคราะห์ความปลอดภัยและสุขภาพผู้ใช้",
        active_agents=["jocasta", "karen"],
        use_native_core=True,
    )
    assert "Native Core Synthesis" in report
    assert "J.O.C.A.S.T.A." in report
    assert "K.A.R.E.N." in report
    assert "jocasta_ckpt.pt" in report
    assert "karen_ckpt.pt" in report
