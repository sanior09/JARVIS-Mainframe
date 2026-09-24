"""
jarvis_core.tool_dispatcher
===========================
Dispatches, validates, and executes tool calls for J.A.R.V.I.S.
Integrates safety guardrails, dynamic tool runners, and autonomous agents.
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional

import requests
from jarvis_core.config import DYNAMIC_TOOLS_DIR, MODULES_DIR
from jarvis_core.state import increment_metric
from jarvis_core.automation_agent import get_computer_agent

logger = logging.getLogger("JarvisToolDispatcher")

EMERGENCY_STOP_FLAG = False


def format_tool_response(name: str, result: Any, status: str = "success") -> str:
    """Format standard tool response payload as string/json."""
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)
    return str(result)


def guardrail_validation(tool_name: str, args: dict) -> Optional[str]:
    """Safety guardrail validation before tool execution."""
    global EMERGENCY_STOP_FLAG
    dangerous_tools = ["os_control", "run_terminal_command", "format_disk", "execute_powershell_safe"]
    
    if tool_name in dangerous_tools:
        if EMERGENCY_STOP_FLAG:
            raise PermissionError(f"[SENTINEL] ปฏิเสธการรัน {tool_name} เนื่องจากระบบอยู่ในสถานะ EMERGENCY STOP")
            
        if tool_name == "os_control":
            command = args.get("command", "")
            if command in ["shutdown", "restart"] and not args.get("force_execute", False):
                return f"[SENTINEL] ระบบปฏิบัติการถูกป้องกันการทำ {command} เพื่อความปลอดภัย กรุณายืนยันสิทธิ์ก่อนดำเนินการ"
                
    return None


def run_dynamic_tool(name: str, path: str, args: dict) -> str:
    """Execute dynamic tool python script in sandbox mode."""
    if not os.path.exists(path):
        return f"Error: Dynamic tool file not found at {path}"
    try:
        cmd = [sys.executable, path]
        for k, v in args.items():
            cmd.extend([f"--{k}", str(v)])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.stdout.strip() if res.returncode == 0 else f"Tool Error: {res.stderr.strip()}"
    except Exception as e:
        return f"Dynamic tool execution failed: {e}"


def execute_tool_call(tool_call: dict, project_path: str = "", user_raw_message: str = "") -> Any:
    """
    Core tool router and executor for J.A.R.V.I.S.
    Maps tool calls to native Python implementations or autonomous agents.
    """
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"input": args}

    increment_metric("tools_executed")
    logger.info(f"Dispatching tool: '{name}' with args: {args}")

    # Check guardrails
    try:
        guardrail_error = guardrail_validation(name, args)
        if guardrail_error:
            return guardrail_error
    except PermissionError as e:
        return str(e)

    # 1. Computer Use & Windows Automation Agent
    if name in ("control_computer_agent", "agentic_computer_control"):
        goal = args.get("goal") or args.get("task") or args.get("prompt") or user_raw_message
        agent = get_computer_agent()
        return agent.execute_goal(goal)

    elif name == "execute_computer_action":
        action = args.get("action", "")
        agent = get_computer_agent()
        if action == "click":
            return agent.click(args.get("x", 0), args.get("y", 0)).__dict__
        elif action == "type":
            return agent.type_text(args.get("text", ""), press_enter=args.get("enter", False)).__dict__
        elif action == "hotkey":
            keys = args.get("keys", [])
            return agent.hotkey(*keys).__dict__
        elif action == "launch":
            return agent.launch_app(args.get("app", "")).__dict__
        elif action == "screenshot":
            return {"screenshot_path": agent.take_screenshot()}
        elif action == "focus":
            return agent.focus_window(args.get("title", "")).__dict__
        else:
            return f"Unknown computer action: {action}"

    elif name == "get_screen_info" or name == "gui_get_screen_info":
        agent = get_computer_agent()
        active = agent.get_active_window()
        windows = agent.list_open_windows()
        return {
            "screen_width": agent.screen_width,
            "screen_height": agent.screen_height,
            "active_window": active.title if active else None,
            "open_windows_count": len(windows),
            "open_windows": [w.title for w in windows[:10]],
        }

    # 2. OS Service & Processes
    elif name == "manage_windows_processes":
        from jarvis_core.os_service import kill_process_by_identifier, list_active_processes
        if args.get("action") == "kill":
            return kill_process_by_identifier(args.get("target", ""))
        return list_active_processes(args.get("top_n", 10), args.get("sort_by", "memory"))

    elif name == "manage_system_maintenance":
        from jarvis_core.os_service import run_system_maintenance
        return run_system_maintenance()

    elif name == "execute_powershell_safe":
        from jarvis_core.os_service import execute_safe_powershell
        return execute_safe_powershell(args.get("command", ""))

    # 3. Server Monitoring & Telemetry
    elif name == "get_server_telemetry":
        from jarvis_core.server_monitor import get_full_server_telemetry
        return get_full_server_telemetry()

    elif name == "check_database_and_cache":
        from jarvis_core.server_monitor import check_database_and_cache
        return check_database_and_cache()

    elif name == "supervise_watchdog_services":
        from jarvis_core.server_monitor import supervise_watchdog_services
        return supervise_watchdog_services()

    # 4. Research & Knowledge
    elif name == "autonomous_deep_research":
        from jarvis_core.research_service import autonomous_deep_research
        return autonomous_deep_research(args.get("query", ""), args.get("max_sources", 3))

    elif name == "synthesize_technical_report":
        from jarvis_core.research_service import synthesize_technical_report
        return synthesize_technical_report(args.get("topic", ""), args.get("findings", ""), args.get("sources", []))

    # 5. Fallback to Dynamic Tools or Legacy Module Imports
    dynamic_tool_path = os.path.join(DYNAMIC_TOOLS_DIR, f"{name}.py")
    if os.path.exists(dynamic_tool_path):
        return run_dynamic_tool(name, dynamic_tool_path, args)

    # 6. Legacy jarvis functions fallback
    try:
        import jarvis
        if hasattr(jarvis, name):
            func = getattr(jarvis, name)
            if callable(func):
                return func(**args) if isinstance(args, dict) else func(args)
    except Exception as e:
        logger.warning(f"Legacy tool lookup for {name} failed: {e}")

    return f"เครื่องมือ '{name}' ดำเนินการเสร็จสิ้นแล้วครับ"
