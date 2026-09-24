"""
tests/test_automation_agent.py
Tests for Windows Computer Use & RPA Automation Agent.
Verifies safety guardrails, coordinate bounds, Thai-safe typing, perception, and goal planning.
"""

import pytest
from jarvis_core.automation_agent import (
    WindowsAutomationAgent,
    get_computer_agent,
    AutomationSafetyError,
)


@pytest.mark.agent
def test_agent_initialization_and_screen_bounds():
    agent = get_computer_agent()
    assert agent.screen_width > 0
    assert agent.screen_height > 0

    # Coordinate clamping
    cx, cy = agent._validate_coordinates(agent.screen_width + 500, -100)
    assert 0 <= cx < agent.screen_width
    assert cy == 0


@pytest.mark.agent
def test_dangerous_command_blacklist():
    agent = get_computer_agent()

    dangerous_commands = [
        "format C: /FS:NTFS",
        "rmdir /s /q c:\\",
        "del /f /s /q c:\\windows\\system32",
        "reg delete HKLM\\Software",
    ]

    for cmd in dangerous_commands:
        with pytest.raises(AutomationSafetyError):
            agent.execute_command_safely(cmd)


@pytest.mark.agent
def test_safe_command_execution():
    agent = get_computer_agent()
    result = agent.execute_command_safely("Write-Output 'JARVIS_AUTOMATION_READY'")
    assert result.success is True
    assert "JARVIS_AUTOMATION_READY" in result.message


@pytest.mark.agent
def test_thai_safe_text_typing():
    agent = get_computer_agent()
    # Test typing Thai characters via clipboard paste
    res = agent.type_text("สวัสดีครับ จาร์วิสกำลังทดสอบระบบ", use_clipboard=True)
    assert res.success is True
    assert "clipboard paste" in res.message


@pytest.mark.agent
def test_goal_decomposition_calc():
    agent = get_computer_agent()
    # Test planning a calculator goal
    res = agent.execute_goal("เปิดเครื่องคิดเลข")
    assert res["status"] == "success"
    assert "calc" in res["goal"].lower() or "เครื่องคิดเลข" in res["goal"]
    assert len(res["steps"]) >= 1


@pytest.mark.agent
def test_goal_decomposition_screenshot():
    agent = get_computer_agent()
    res = agent.execute_goal("จับภาพหน้าจอคอมพิวเตอร์ตอนนี้")
    assert res["status"] == "success"
    assert "screenshot" in res["message"].lower() or "บันทึก" in res["message"]


@pytest.mark.agent
def test_window_inspection():
    agent = get_computer_agent()
    windows = agent.list_open_windows()
    assert isinstance(windows, list)
    active = agent.get_active_window()
    if active:
        assert isinstance(active.title, str)
