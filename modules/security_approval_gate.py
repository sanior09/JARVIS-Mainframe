"""
modules/security_approval_gate.py
─────────────────────────────────────────────────────────────
Real-time Security Approval Gate for J.A.R.V.I.S.
Intercepts dangerous tools and terminal commands, triggering
an interactive [Allow] / [Deny] approval banner on Dynamic Island.

Blocks execution until the user explicitly clicks [Allow] on the HUD.
"""

from __future__ import annotations

import os
import time
import json
import uuid
import logging
from typing import Tuple, Optional, Any, Dict

logger = logging.getLogger("JARVIS_SECURITY_GATE")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "system_cache")
APPROVAL_FILE = os.path.join(CACHE_DIR, "security_approval.json")

DANGEROUS_TOOLS = {
    "run_command",
    "execute_powershell_safe",
    "run_terminal_command",
    "os_control",
    "format_disk",
    "delete_custom_tool",
    "flash_esp32_firmware",
    "manage_windows_processes",
}

CRITICAL_CMD_PATTERNS = [
    "rmdir", "del ", "del /", "format", "shutdown", "taskkill",
    "reg delete", "net user", "drop database", "drop table", "powershell -enc",
    "stop-service", "remove-item", "cmd.exe /c del"
]


def is_dangerous_action(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Evaluate if the incoming tool or command requires explicit user confirmation.
    Returns (is_dangerous: bool, description: str).
    """
    name = tool_name.lower().strip()
    
    # 1. Direct dangerous tool match
    if name in DANGEROUS_TOOLS:
        if name in ("run_command", "run_terminal_command", "execute_powershell_safe"):
            cmd = str(args.get("command", "") or args.get("cmd", "")).strip()
            return True, f"Terminal: {cmd}"
        elif name == "manage_windows_processes":
            action = args.get("action", "").lower()
            if action in ("kill", "terminate"):
                target = args.get("target", "unknown")
                return True, f"Taskkill: {target}"
            return False, ""
        elif name == "os_control":
            cmd = args.get("command", "system action")
            return True, f"System Control: {cmd}"
        elif name == "delete_custom_tool":
            tool = args.get("tool_name", "")
            return True, f"Delete Tool: {tool}"
        return True, f"Execute: {name}"

    # 2. General command check inside args
    for val in args.values():
        if isinstance(val, str):
            val_lower = val.lower()
            for pattern in CRITICAL_CMD_PATTERNS:
                if pattern in val_lower:
                    return True, f"Critical Command: {val[:50]}"

    return False, ""


def request_approval(action: str, detail: str, timeout_sec: float = 25.0) -> bool:
    """
    Request interactive approval from user via Dynamic Island HUD.
    Blocks thread until user clicks [Allow] / [Deny] or timeout expires.
    Returns True if ALLOWED, False if DENIED or TIMED OUT.
    """
    req_id = f"req_{uuid.uuid4().hex[:6]}"
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Clean up single-line detail for HUD display
    clean_detail = detail.replace("\n", " ").strip()
    if len(clean_detail) > 48:
        clean_detail = clean_detail[:45] + "..."

    # Write initial pending state
    payload = {
        "request_id": req_id,
        "action": action,
        "detail": detail,
        "status": "PENDING",
        "created_at": time.time(),
        "timeout_at": time.time() + timeout_sec
    }
    _write_state(payload)

    # Trigger Dynamic Island HUD event banner
    try:
        from modules.dynamic_island import send_agent_event
        display_agent = "Security Gate"
        send_agent_event(
            agent=display_agent,
            status="request",
            detail=f"{clean_detail}",
            buttons="allow_deny"
        )
        logger.info(f"[SECURITY GATE] Sent approval request '{req_id}' for '{action}' to Dynamic Island HUD")
    except Exception as e:
        logger.error(f"[SECURITY GATE] Failed to dispatch HUD event: {e}")

    # Polling wait loop for user's click on HUD
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        time.sleep(0.15)
        current = _read_state()
        if current.get("request_id") == req_id:
            status = current.get("status", "PENDING")
            if status == "ALLOWED":
                logger.info(f"[SECURITY GATE] Request '{req_id}' was APPROVED by user!")
                return True
            elif status == "DENIED":
                logger.warning(f"[SECURITY GATE] Request '{req_id}' was REJECTED by user!")
                return False

    logger.warning(f"[SECURITY GATE] Request '{req_id}' TIMED OUT after {timeout_sec}s. Denying by default.")
    payload["status"] = "TIMED_OUT"
    _write_state(payload)
    return False


def resolve_approval(allowed: bool) -> None:
    """
    Called by Dynamic Island when user clicks [Allow] or [Deny] button.
    Updates approval state file to unblock waiting thread.
    """
    current = _read_state()
    if not current or current.get("status") != "PENDING":
        return

    current["status"] = "ALLOWED" if allowed else "DENIED"
    current["resolved_at"] = time.time()
    _write_state(current)
    logger.info(f"[SECURITY GATE] Resolved approval request '{current.get('request_id')}' as {current['status']}")


def _write_state(data: Dict[str, Any]) -> None:
    try:
        temp_file = APPROVAL_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(APPROVAL_FILE):
            os.replace(temp_file, APPROVAL_FILE)
        else:
            os.rename(temp_file, APPROVAL_FILE)
    except Exception as e:
        logger.error(f"[SECURITY GATE] Error writing approval state: {e}")


def _read_state() -> Dict[str, Any]:
    if not os.path.exists(APPROVAL_FILE):
        return {}
    try:
        with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
