"""
jarvis_screen_takeover.py
===========================
Client Library for J.A.R.V.I.S. Screen Takeover HUD Overlay.

Provides clean, fail-safe APIs to control the glowing blue border,
the action status pill, and check if the user clicked the red Stop button.
"""

import json
import logging
import os
import subprocess
import sys
import time
from typing import Optional

logger = logging.getLogger("ScreenTakeoverClient")

PIPE_NAME = "jarvis_takeover_pipe"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATUS_FILE = os.path.join(BASE_DIR, "data", "takeover_status.json")
OVERLAY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_screen_takeover_overlay.py")
if not os.path.exists(OVERLAY_SCRIPT):
    OVERLAY_SCRIPT = os.path.join(BASE_DIR, "modules", "jarvis_screen_takeover_overlay.py")
if not os.path.exists(OVERLAY_SCRIPT):
    OVERLAY_SCRIPT = os.path.join(BASE_DIR, "jarvis_screen_takeover_overlay.py")

_overlay_process: Optional[subprocess.Popen] = None


def _send_ipc_message(command: str, argument: str = "", timeout_ms: int = 400) -> bool:
    """Sends a message to the Takeover Overlay via QLocalSocket (PyQt6)."""
    try:
        from PyQt6.QtNetwork import QLocalSocket
        sock = QLocalSocket()
        sock.connectToServer(PIPE_NAME)
        if sock.waitForConnected(timeout_ms):
            msg = f"{command}|{argument}\n" if argument else f"{command}\n"
            sock.write(msg.encode("utf-8"))
            sock.waitForBytesWritten(timeout_ms)
            sock.disconnectFromServer()
            return True
        return False
    except Exception as e:
        logger.debug(f"[TAKEOVER IPC] Send failed: {e}")
        return False


def ensure_overlay_running() -> bool:
    """Checks if the overlay process is active; launches it in the background if not."""
    global _overlay_process

    # 1. Quick ping check
    if _send_ipc_message("STATUS", timeout_ms=200):
        return True

    # 2. Spawn overlay subprocess
    try:
        logger.info("[TAKEOVER] Spawning jarvis_screen_takeover_overlay.py in background...")
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable

        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0

        _overlay_process = subprocess.Popen(
            [pythonw, OVERLAY_SCRIPT],
            cwd=BASE_DIR,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait up to 1.5s for the pipe to become ready
        for _ in range(15):
            time.sleep(0.1)
            if _send_ipc_message("STATUS", timeout_ms=100):
                logger.info("[TAKEOVER] Overlay connected successfully.")
                return True
        return False
    except Exception as e:
        logger.error(f"[TAKEOVER] Failed to spawn overlay: {e}")
        return False


def start_screen_takeover(action_text: str = "Taking screenshot...") -> bool:
    """
    Activates the glowing blue screen border and bottom status pill.
    Displays what JARVIS is about to do.
    """
    ensure_overlay_running()
    # Reset status file stopped state
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"active": True, "stopped": False, "action": action_text, "timestamp": time.time()}, f)
    except Exception:
        pass

    return _send_ipc_message("START", action_text)


def update_screen_takeover(action_text: str) -> bool:
    """Updates the action text shown on the bottom status pill."""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["action"] = action_text
            data["timestamp"] = time.time()
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass
    return _send_ipc_message("UPDATE", action_text)


def notify_agent_click() -> bool:
    """
    Notifies overlay that JARVIS is about to click.
    Suppresses user interruption false-alarms for the next 400ms.
    """
    return _send_ipc_message("AGENT_CLICK")


def stop_screen_takeover() -> bool:
    """Hides the glowing border and bottom status pill."""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"active": False, "stopped": False, "action": "", "timestamp": time.time()}, f)
    except Exception:
        pass
    return _send_ipc_message("STOP")


def flash_screen_takeover(action_text: str = "J.A.R.V.I.S. Command", duration_sec: float = 2.5) -> None:
    """
    Activates the glowing cyan screen border for duration_sec, then stops it.
    Runs asynchronously in a background thread so commands execute with zero latency.
    """
    import threading
    def _worker():
        try:
            start_screen_takeover(action_text)
            time.sleep(duration_sec)
            stop_screen_takeover()
        except Exception as e:
            logger.debug(f"[TAKEOVER FLASH] Error: {e}")
    threading.Thread(target=_worker, daemon=True).start()


def is_screen_takeover_stopped() -> bool:
    """
    Returns True if the user clicked the red Stop (⏹️) button or pressed ESC.
    Allows automated agent loops to terminate immediately!
    """
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("stopped", False))
    except Exception:
        pass
    return False


class ScreenTakeover:
    """
    Python Context Manager for clean automated screen operations:
    
    with ScreenTakeover("Taking screenshot of Marvel Splendor..."):
        # Computer actions...
        update_screen_takeover("Clicking Assemble Heroes...")
        if is_screen_takeover_stopped():
            break
    """

    def __init__(self, initial_action: str = "Taking screenshot..."):
        self.initial_action = initial_action

    def __enter__(self):
        start_screen_takeover(self.initial_action)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        stop_screen_takeover()
