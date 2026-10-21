"""
modules/jarvis_satellite_node.py
================================
J.A.R.V.I.S. Satellite Node Agent (Client Machine Controller)
--------------------------------------------------------------
Run this lightweight agent on any target PC (Gaming Rig / Laptop)
to allow J.A.R.V.I.S. Server (9U Rack Mainframe) to command it remotely.

Features:
- Screen Capture & Streaming back to Server Vision AI
- Agentic GUI Control (Mouse Click, Move, Keyboard Type, Hotkeys)
- Process & Game Launching (Steam, Roblox, Valorant, Chrome)
- OS Power Control (Lockdown, Volume, Sleep, Shutdown)
- Hardware Health Telemetry (CPU%, RAM%, Battery%)
"""

import os
import sys
import time
import json
import base64
import logging
import platform
import subprocess
import threading
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SATELLITE-NODE] %(levelname)s - %(message)s"
)
logger = logging.getLogger("JarvisSatelliteNode")

# Node Settings
DEFAULT_NODE_NAME = platform.node() or "Target-PC"
DEFAULT_HOST = os.getenv("NODE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("NODE_PORT", "5055"))
AUTH_TOKEN = os.getenv("JARVIS_NODE_TOKEN", "jarvis_secret_link_2026")


class SatelliteNodeController:
    """Core controller executing hardware, OS, and GUI automation on target PC."""

    def __init__(self, node_name: str = DEFAULT_NODE_NAME):
        self.node_name = node_name
        self._init_pyautogui()

    def _init_pyautogui(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            self.screen_width, self.screen_height = pyautogui.size()
            self.gui_available = True
        except Exception as e:
            logger.warning(f"PyAutoGUI not available or headless display: {e}")
            self.screen_width, self.screen_height = (1920, 1080)
            self.gui_available = False

    def get_telemetry(self) -> Dict[str, Any]:
        """Fetches live hardware telemetry of this target PC."""
        cpu_pct = 0.0
        ram_pct = 0.0
        battery_pct = None
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.1)
            ram_pct = psutil.virtual_memory().percent
            bat = psutil.sensors_battery()
            battery_pct = round(bat.percent) if bat else None
        except Exception:
            pass

        return {
            "node_name": self.node_name,
            "os": platform.system(),
            "os_release": platform.release(),
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "battery_percent": battery_pct,
            "resolution": f"{self.screen_width}x{self.screen_height}",
            "time": time.strftime("%H:%M:%S")
        }

    def capture_screen(self, max_dim: int = 1280) -> Optional[str]:
        """Captures full screen and returns JPEG base64 string for Server Vision AI."""
        try:
            import io
            from PIL import ImageGrab, Image

            screenshot = ImageGrab.grab()
            if max_dim and (screenshot.width > max_dim or screenshot.height > max_dim):
                screenshot.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            screenshot.save(buf, format="JPEG", quality=75, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def execute_os_command(self, cmd: str) -> Dict[str, Any]:
        """Executes a system shell command or launches an app."""
        try:
            p = subprocess.Popen(  # nosec B602
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return {"success": True, "pid": p.pid, "command": cmd}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def launch_uri(self, uri: str) -> Dict[str, Any]:
        """Launches a protocol URI (e.g. steam://, roblox://, chrome)."""
        try:
            if sys.platform == "win32":
                os.startfile(uri)
            else:
                subprocess.Popen(["xdg-open", uri])
            logger.info(f"Launched URI: {uri}")
            return {"success": True, "uri": uri}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Clicks at specified screen coordinates."""
        if not self.gui_available:
            return {"success": False, "error": "GUI automation unavailable"}
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return {"success": True, "x": x, "y": y, "button": button}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        """Moves mouse cursor to coordinate."""
        if not self.gui_available:
            return {"success": False, "error": "GUI automation unavailable"}
        try:
            import pyautogui
            pyautogui.moveTo(x=x, y=y, duration=0.2)
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str) -> Dict[str, Any]:
        """Types text (supports Thai via clipboard paste)."""
        if not self.gui_available:
            return {"success": False, "error": "GUI automation unavailable"}
        try:
            import pyautogui
            # For non-ascii (Thai), paste via clipboard
            if any(ord(c) > 127 for c in text):
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.write(text, interval=0.02)
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hotkey(self, keys: list) -> Dict[str, Any]:
        """Presses keyboard shortcut combinations (e.g. ['ctrl', 'c'])."""
        if not self.gui_available:
            return {"success": False, "error": "GUI automation unavailable"}
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def lock_workstation(self) -> Dict[str, Any]:
        """Locks the Windows workstation immediately."""
        try:
            if sys.platform == "win32":
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
                return {"success": True, "message": "Workstation locked"}
            return {"success": False, "error": "Not a Windows machine"}
        except Exception as e:
            return {"success": False, "error": str(e)}


controller = SatelliteNodeController()


class SatelliteHTTPHandler(BaseHTTPRequestHandler):
    """HTTP API handling incoming commands from J.A.R.V.I.S. Mainframe."""

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        # Health check & Telemetry
        if self.path in ("/", "/status", "/api/telemetry"):
            telemetry = controller.get_telemetry()
            self._send_json({"status": "online", "data": telemetry})
        elif self.path == "/api/screen":
            # Quick screen grab via GET
            b64_img = controller.capture_screen()
            if b64_img:
                self._send_json({"status": "success", "image_b64": b64_img})
            else:
                self._send_json({"status": "error", "message": "Capture failed"}, 500)
        else:
            self._send_json({"status": "error", "message": "Not Found"}, 404)

    def do_POST(self):
        # Verify Token header if configured
        client_token = self.headers.get("X-Jarvis-Token", "")
        if AUTH_TOKEN and client_token != AUTH_TOKEN:
            self._send_json({"status": "forbidden", "message": "Invalid auth token"}, 403)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(post_data)
        except Exception:
            payload = {}

        action = payload.get("action", "").lower().strip()
        logger.info(f"Received action: '{action}' from {self.client_address[0]}")

        if action == "screen":
            b64_img = controller.capture_screen(max_dim=payload.get("max_dim", 1280))
            self._send_json({"status": "success", "image_b64": b64_img})

        elif action == "launch_uri":
            res = controller.launch_uri(payload.get("uri", ""))
            self._send_json(res)

        elif action == "exec_command":
            res = controller.execute_os_command(payload.get("command", ""))
            self._send_json(res)

        elif action == "click":
            x = int(payload.get("x", 0))
            y = int(payload.get("y", 0))
            btn = payload.get("button", "left")
            clicks = int(payload.get("clicks", 1))
            res = controller.mouse_click(x, y, btn, clicks)
            self._send_json(res)

        elif action == "move":
            x = int(payload.get("x", 0))
            y = int(payload.get("y", 0))
            res = controller.mouse_move(x, y)
            self._send_json(res)

        elif action == "type":
            text = payload.get("text", "")
            res = controller.type_text(text)
            self._send_json(res)

        elif action == "hotkey":
            keys = payload.get("keys", [])
            res = controller.hotkey(keys)
            self._send_json(res)

        elif action == "lock":
            res = controller.lock_workstation()
            self._send_json(res)

        elif action == "telemetry":
            res = controller.get_telemetry()
            self._send_json({"status": "success", "data": res})

        else:
            self._send_json({"status": "error", "message": f"Unknown action: {action}"}, 400)


def run_node_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = HTTPServer((host, port), SatelliteHTTPHandler)
    logger.info(f"============================================================")
    logger.info(f"🤖 J.A.R.V.I.S. SATELLITE NODE ONLINE")
    logger.info(f"[*] Node Name: {DEFAULT_NODE_NAME}")
    logger.info(f"[*] Listening on: http://{host}:{port}")
    logger.info(f"[*] Ready for remote commands from J.A.R.V.I.S. Mainframe")
    logger.info(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Satellite node stopping...")
        server.server_close()


if __name__ == "__main__":
    run_node_server()
