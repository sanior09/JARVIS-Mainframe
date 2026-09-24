"""
tests/test_tool_dispatcher.py
Tests for centralized Tool Dispatcher.
Verifies tool routing, safety guardrails, response formatting, and computer action execution.
"""

import pytest
from jarvis_core.tool_dispatcher import (
    execute_tool_call,
    format_tool_response,
    guardrail_validation,
)


@pytest.mark.unit
def test_format_tool_response():
    assert format_tool_response("test", "simple_string") == "simple_string"
    dict_res = format_tool_response("test", {"key": "value"})
    assert '"key": "value"' in dict_res


@pytest.mark.unit
def test_guardrail_validation():
    # Safe tool
    assert guardrail_validation("search_web", {"query": "hello"}) is None

    # Dangerous shutdown without force flag
    warn = guardrail_validation("os_control", {"command": "shutdown"})
    assert warn is not None
    assert "ปลอดภัย" in warn


@pytest.mark.agent
def test_tool_dispatcher_computer_agent():
    # Goal-based tool call
    res = execute_tool_call({
        "name": "control_computer_agent",
        "args": {"goal": "จับภาพหน้าจอ"}
    })
    assert isinstance(res, dict)
    assert res.get("status") in ("success", "completed")


@pytest.mark.agent
def test_tool_dispatcher_screen_info():
    res = execute_tool_call({
        "name": "get_screen_info",
        "args": {}
    })
    assert isinstance(res, dict)
    assert "screen_width" in res
    assert "screen_height" in res
    assert res["screen_width"] > 0
