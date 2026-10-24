"""
Unit tests for the upgraded Stark Industries Multi-Agent Swarm Council.
Verifies the full 5-AI canonical pantheon and concurrent ThreadPool debate execution.
"""
import pytest
from unittest.mock import patch, MagicMock
from jarvis_core.cognitive.swarm import (
    AgentCouncil,
    CANONICAL_SWARM,
    friday_agent,
    veronica_agent,
    edith_agent,
    u_agent,
    dume_agent
)


def test_canonical_swarm_pantheon_members():
    """Verify all 5 canonical Stark AI agents exist with their official specs."""
    council = AgentCouncil()
    assert "friday" in council.agents
    assert "veronica" in council.agents
    assert "edith" in council.agents
    assert "u" in council.agents
    assert "dume" in council.agents

    assert council.get_agent("FRIDAY").codename == "friday"
    assert council.get_agent("EDITH").codename == "edith"
    assert council.get_agent("U").codename == "u"
    assert council.get_agent("DUME").codename == "dume"
    assert council.get_agent("VERONICA").codename == "veronica"


def test_swarm_agent_roles():
    """Verify official roles matching Stark Industries specifications."""
    assert "Tactical Ops" in friday_agent.role_description
    assert "Sentinel" in veronica_agent.role_description
    assert "Game Theory" in edith_agent.role_description
    assert "Defragger" in u_agent.role_description
    assert "Fire Suppression" in dume_agent.role_description


def test_council_debate_parallel_execution():
    """Test parallel deliberation and J.A.R.V.I.S. synthesis."""
    council = AgentCouncil()

    with patch("jarvis_core.cognitive.swarm.call_nachapol_core") as mock_core:
        # Mock individual agent outputs and final synthesis
        def side_effect(messages, model=None):
            sys_msg = messages[0]["content"]
            if "President of the Stark Industries" in sys_msg or "J.A.R.V.I.S." in sys_msg:
                return {"content": "JARVIS: Master directive formulated successfully."}
            elif "F.R.I.D.A.Y." in sys_msg:
                return {"content": "Friday: Code is optimized."}
            elif "V.E.R.O.N.I.C.A." in sys_msg:
                return {"content": "Veronica: Resources within safe bounds."}
            elif "E.D.I.T.H." in sys_msg:
                return {"content": "EDITH: Optimal game theory payoff achieved."}
            elif "U." in sys_msg:
                return {"content": "U: System defragmented and clean."}
            elif "D.U.M.-E." in sys_msg:
                return {"content": "DUM-E: Servos calibrated, fire suppression ready."}
            else:
                return {"content": "Default response"}

        mock_core.side_effect = side_effect

        result = council.hold_council_debate(query="Optimize mission protocol", context="Project Alpha")
        assert "JARVIS: Master directive formulated successfully." in result


def test_council_selective_quorum():
    """Test consulting only a subset of agents (e.g., Friday + EDITH)."""
    council = AgentCouncil()

    with patch("jarvis_core.cognitive.swarm.call_nachapol_core") as mock_core:
        mock_core.return_value = {"content": "Synthesis complete"}
        result = council.hold_council_debate(
            query="Analyze code strategy",
            context="",
            active_agents=["friday", "edith"]
        )
        assert result == "Synthesis complete"
