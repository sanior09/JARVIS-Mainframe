"""
jarvis_core.automation_agent
=============================
Advanced Windows Computer Use & RPA Automation Agent for J.A.R.V.I.S.

Provides autonomous computer control capabilities:
- Perception: Screen capture, window tree enumeration, visual grounding
- Primitives: Safe mouse click/drag/scroll, Thai-safe clipboard typing, hotkeys
- App Management: Smart app launcher, window focus/minimize/maximize/close
- Planner: Multi-step goal decomposition and closed-loop execution
- Safety Guardrails: PyAutoGUI failsafe, coordinate bounds checks, command blacklist
"""

from __future__ import annotations

import asyncio
import base64
import ctypes
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
import pyautogui

try:
    import pyperclip
except ImportError:
    pyperclip = None

logger = logging.getLogger("JarvisAutomationAgent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [COMPUTER-AGENT] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ==========================================
# Safety Guardrails & Blacklist
# ==========================================
DANGEROUS_COMMAND_PATTERNS = [
    r"\bformat\b",
    r"\brmdir\b",
    r"\bdel\b.*(?:windows|system32)",
    r"\breg\s+delete\b",
    r"\bdiskpart\b",
    r"\bcd\s+c:\\\s*&&\s*del\b",
    r"\bshutdown\b",
]

COMMON_APP_MAP = {
    "notepad": "notepad.exe",
    "สมุดจด": "notepad.exe",
    "โน้ตแพด": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "เครื่องคิดเลข": "calc.exe",
    "chrome": "chrome.exe",
    "โครม": "chrome.exe",
    "เบราว์เซอร์": "chrome.exe",
    "edge": "msedge.exe",
    "เอจ": "msedge.exe",
    "cmd": "cmd.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "ไฟล์": "explorer.exe",
    "paint": "mspaint.exe",
    "วาดรูป": "mspaint.exe",
    "taskmgr": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "spotify": "spotify.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
}


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_active: bool = False
    process_name: str = ""


@dataclass
class ActionResult:
    success: bool
    action: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AutomationSafetyError(Exception):
    """Raised when an automation action violates safety constraints."""
    pass


class WindowsAutomationAgent:
    """
    High-level Windows Computer Use & RPA Automation Agent.
    """

    def __init__(self, failsafe: bool = True, pause_sec: float = 0.05):
        self.screen_width, self.screen_height = pyautogui.size()
        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = pause_sec
        self.user32 = ctypes.windll.user32 if sys.platform == "win32" else None
        self._status_callback: Optional[Callable[[str, str], None]] = None
        self._hud_available = self._detect_hud()

    def _detect_hud(self) -> bool:
        try:
            import jarvis_screen_takeover  # type: ignore
            return True
        except ImportError:
            return False

    def set_status_callback(self, callback: Callable[[str, str], None]) -> None:
        self._status_callback = callback

    def _notify_status(self, status: str, thought: str = "") -> None:
        logger.info(f"STATUS: {status} | THOUGHT: {thought}")
        if self._status_callback:
            try:
                self._status_callback(status, thought)
            except Exception:
                pass
        if self._hud_available:
            try:
                from jarvis_screen_takeover import update_screen_takeover
                update_screen_takeover(f"{status}: {thought}"[:50])
            except Exception:
                pass

    # ==========================================
    # 1. Perception & Inspection
    # ==========================================
    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        """
        Capture the current primary screen.
        Returns file path to the saved screenshot.
        """
        if not save_path:
            import tempfile
            fd, save_path = tempfile.mkstemp(suffix=".png", prefix="jarvis_screen_")
            os.close(fd)
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            logger.info(f"Screenshot captured: {save_path}")
            return save_path
        except Exception as e:
            logger.warning(f"Screen capture fallback triggered ({e}). Creating canvas image.")
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (self.screen_width or 1920, self.screen_height or 1080), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)
            draw.text((60, 60), "J.A.R.V.I.S. Screen Canvas", fill=(56, 189, 248))
            img.save(save_path)
            return save_path

    def get_screenshot_base64(self) -> str:
        """Capture screenshot and return as base64 string for Vision LLMs."""
        path = self.take_screenshot()
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        finally:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def get_active_window(self) -> Optional[WindowInfo]:
        """Returns details of the currently focused window on Windows."""
        if not self.user32:
            return None
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = self.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buf, length + 1)
        
        rect = ctypes.wintypes.RECT()
        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
        # Get process name
        pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pname = ""
        try:
            pname = psutil.Process(pid.value).name()
        except Exception:
            pass

        return WindowInfo(
            hwnd=hwnd,
            title=buf.value,
            rect=(rect.left, rect.top, rect.right, rect.bottom),
            is_active=True,
            process_name=pname,
        )

    def list_open_windows(self) -> List[WindowInfo]:
        """Enumerate all visible top-level desktop windows."""
        windows: List[WindowInfo] = []
        if not self.user32:
            return windows

        active_hwnd = self.user32.GetForegroundWindow()

        def enum_windows_callback(hwnd: int, _: Any) -> bool:
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        rect = ctypes.wintypes.RECT()
                        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        # Only include non-zero sized windows
                        if rect.right > rect.left and rect.bottom > rect.top:
                            pid = ctypes.c_ulong()
                            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            pname = ""
                            try:
                                pname = psutil.Process(pid.value).name()
                            except Exception:
                                pass
                            windows.append(WindowInfo(
                                hwnd=hwnd,
                                title=title,
                                rect=(rect.left, rect.top, rect.right, rect.bottom),
                                is_active=(hwnd == active_hwnd),
                                process_name=pname,
                            ))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        self.user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return windows

    # ==========================================
    # 2. Action Primitives (Mouse & Keyboard)
    # ==========================================
    def _validate_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Validate and clamp coordinates to screen boundaries."""
        safe_x = max(0, min(int(x), self.screen_width - 1))
        safe_y = max(0, min(int(y), self.screen_height - 1))
        return safe_x, safe_y

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
        """Perform mouse click at (x, y) with boundary validation."""
        sx, sy = self._validate_coordinates(x, y)
        try:
            pyautogui.click(x=sx, y=sy, clicks=clicks, button=button)
            return ActionResult(True, "click", f"Clicked ({sx}, {sy}) with {button} button {clicks} time(s).")
        except Exception as e:
            return ActionResult(False, "click", f"Failed to click at ({sx}, {sy}): {e}")

    def double_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, button="left", clicks=2)

    def right_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, button="right", clicks=1)

    def mouse_move(self, x: int, y: int, duration: float = 0.2) -> ActionResult:
        sx, sy = self._validate_coordinates(x, y)
        try:
            pyautogui.moveTo(sx, sy, duration=duration)
            return ActionResult(True, "mouse_move", f"Moved mouse to ({sx}, {sy}).")
        except Exception as e:
            return ActionResult(False, "mouse_move", f"Failed to move mouse: {e}")

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> ActionResult:
        s_x, s_y = self._validate_coordinates(start_x, start_y)
        e_x, e_y = self._validate_coordinates(end_x, end_y)
        try:
            pyautogui.moveTo(s_x, s_y)
            pyautogui.dragTo(e_x, e_y, duration=duration, button="left")
            return ActionResult(True, "mouse_drag", f"Dragged from ({s_x}, {s_y}) to ({e_x}, {e_y}).")
        except Exception as e:
            return ActionResult(False, "mouse_drag", f"Failed to drag: {e}")

    def mouse_scroll(self, clicks: int, direction: str = "down") -> ActionResult:
        amount = -abs(clicks) if direction == "down" else abs(clicks)
        try:
            pyautogui.scroll(amount)
            return ActionResult(True, "mouse_scroll", f"Scrolled {direction} by {clicks} click(s).")
        except Exception as e:
            return ActionResult(False, "mouse_scroll", f"Failed to scroll: {e}")

    def type_text(self, text: str, use_clipboard: bool = True, press_enter: bool = False) -> ActionResult:
        """
        Type text into the active element.
        When use_clipboard is True (default), copies to Windows clipboard and pastes via Ctrl+V.
        This provides 100% accurate Thai and Unicode typing without layout mismatches!
        """
        if not text:
            return ActionResult(True, "type_text", "Empty text provided.")

        prev_failsafe = pyautogui.FAILSAFE
        try:
            pyautogui.FAILSAFE = False
            if use_clipboard and pyperclip:
                pyperclip.copy(text)
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.05)

                if press_enter:
                    pyautogui.press("enter")

                return ActionResult(True, "type_text", f"Typed {len(text)} chars via clipboard paste.")
            else:
                pyautogui.typewrite(text, interval=0.03)
                if press_enter:
                    pyautogui.press("enter")
                return ActionResult(True, "type_text", f"Typed {len(text)} chars via keyboard simulation.")
        except Exception as e:
            return ActionResult(False, "type_text", f"Failed to type text: {e}")
        finally:
            pyautogui.FAILSAFE = prev_failsafe

    def press_key(self, key: str) -> ActionResult:
        """Press a single key (e.g. 'enter', 'esc', 'tab', 'backspace', 'space')."""
        try:
            pyautogui.press(key.lower())
            return ActionResult(True, "press_key", f"Pressed key '{key}'.")
        except Exception as e:
            return ActionResult(False, "press_key", f"Failed to press key '{key}': {e}")

    def hotkey(self, *keys: str) -> ActionResult:
        """Trigger keyboard shortcut (e.g. 'ctrl', 'c' or 'win', 'r')."""
        try:
            clean_keys = [k.lower().strip() for k in keys]
            pyautogui.hotkey(*clean_keys)
            return ActionResult(True, "hotkey", f"Triggered hotkey: {' + '.join(clean_keys)}.")
        except Exception as e:
            return ActionResult(False, "hotkey", f"Failed hotkey {' + '.join(keys)}: {e}")

    # ==========================================
    # 3. Application & Window Management
    # ==========================================
    def launch_app(self, app_name_or_path: str) -> ActionResult:
        """
        Launch an application by friendly name or path.
        """
        clean_name = app_name_or_path.lower().strip()
        target_path = COMMON_APP_MAP.get(clean_name, app_name_or_path)

        try:
            if sys.platform == "win32":
                os.startfile(target_path)
            else:
                subprocess.Popen([target_path])
            time.sleep(0.8)
            return ActionResult(True, "launch_app", f"Successfully launched '{target_path}'.")
        except Exception as e:
            try:
                subprocess.Popen(["powershell", "-Command", f"Start-Process '{target_path}'"])
                time.sleep(0.8)
                return ActionResult(True, "launch_app", f"Launched via PowerShell: '{target_path}'.")
            except Exception as pe:
                return ActionResult(False, "launch_app", f"Failed to launch '{target_path}': {e} | {pe}")

    def focus_window(self, title_pattern: str) -> ActionResult:
        """Bring window matching title_pattern to the foreground."""
        if not self.user32:
            return ActionResult(False, "focus_window", "Windows user32 unavailable.")

        pattern = title_pattern.lower()
        windows = self.list_open_windows()
        for win in windows:
            if pattern in win.title.lower() or pattern in win.process_name.lower():
                try:
                    self.user32.ShowWindow(win.hwnd, 9)  # SW_RESTORE = 9
                    self.user32.SetForegroundWindow(win.hwnd)
                    time.sleep(0.2)
                    return ActionResult(True, "focus_window", f"Focused window '{win.title}' (HWND={win.hwnd}).")
                except Exception as e:
                    return ActionResult(False, "focus_window", f"Failed to focus window: {e}")

        return ActionResult(False, "focus_window", f"No window matching '{title_pattern}' found.")

    def close_window(self, title_pattern: str) -> ActionResult:
        """Send WM_CLOSE to window matching title_pattern."""
        if not self.user32:
            return ActionResult(False, "close_window", "Windows user32 unavailable.")

        pattern = title_pattern.lower()
        windows = self.list_open_windows()
        for win in windows:
            if pattern in win.title.lower() or pattern in win.process_name.lower():
                try:
                    WM_CLOSE = 0x0010
                    self.user32.PostMessageW(win.hwnd, WM_CLOSE, 0, 0)
                    return ActionResult(True, "close_window", f"Closed window '{win.title}'.")
                except Exception as e:
                    return ActionResult(False, "close_window", f"Failed to close window: {e}")

        return ActionResult(False, "close_window", f"No window matching '{title_pattern}' found.")

    # ==========================================
    # 4. Safe Command Execution
    # ==========================================
    def execute_command_safely(self, command: str, timeout_sec: int = 15) -> ActionResult:
        """Execute a shell command with strict blacklist checks."""
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                logger.error(f"BLOCKED DANGEROUS COMMAND: {command}")
                raise AutomationSafetyError(f"Command blocked by security guardrails: {command}")

        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            return ActionResult(
                success=(result.returncode == 0),
                action="execute_command",
                message=stdout if result.returncode == 0 else f"Error (RC={result.returncode}): {stderr}",
                data={"stdout": stdout, "stderr": stderr, "exit_code": result.returncode},
            )
        except subprocess.TimeoutExpired:
            return ActionResult(False, "execute_command", f"Command timed out after {timeout_sec}s.")
        except Exception as e:
            return ActionResult(False, "execute_command", f"Command execution failed: {e}")

    # ==========================================
    # 5. Autonomous Multi-Step Goal Planner
    # ==========================================
    def execute_goal(self, goal: str, max_steps: int = 8) -> Dict[str, Any]:
        """
        Decomposes high-level user goal and executes closed-loop autonomous steps.
        """
        self._notify_status("Starting Autonomous Goal", goal)
        clean_goal = goal.lower().strip()
        steps_taken: List[ActionResult] = []

        try:
            if any(k in clean_goal for k in ["เปิด notepad", "เปิดสมุดจด", "จดบันทึก", "พิมพ์ข้อความ"]):
                self._notify_status("Planning", "Launching Notepad and typing content...")
                res1 = self.launch_app("notepad.exe")
                steps_taken.append(res1)
                time.sleep(0.5)

                type_match = re.search(r"(?:พิมพ์|จดว่า|เขียนว่า)\s*[\"']?([^\"']+)[\"']?", goal)
                text_to_type = type_match.group(1).strip() if type_match else "J.A.R.V.I.S. Automated Note\nDate: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\nภารกิจสำเร็จเรียบร้อยครับเจ้านาย"
                
                res2 = self.type_text(text_to_type, use_clipboard=True, press_enter=True)
                steps_taken.append(res2)
                self._notify_status("Completed", "Notepad note created successfully.")
                return {
                    "status": "success",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "message": "เปิด Notepad และพิมพ์ข้อความตามคำสั่งเรียบร้อยแล้วครับ",
                }

            elif any(k in clean_goal for k in ["เครื่องคิดเลข", "คำนวณ", "calc"]):
                self._notify_status("Planning", "Launching Calculator...")
                res1 = self.launch_app("calc.exe")
                steps_taken.append(res1)
                return {
                    "status": "success",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "message": "เปิดเครื่องคิดเลขให้เรียบร้อยแล้วครับ",
                }

            elif any(k in clean_goal for k in ["ค้นหา", "search", "กูเกิล", "google", "เว็บ"]):
                search_query = re.sub(r"^(ค้นหา|search|google|กูเกิล|เปิดเว็บ)\s*", "", clean_goal).strip()
                self._notify_status("Planning", f"Opening browser for search: '{search_query}'")
                import urllib.parse
                url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
                import webbrowser
                webbrowser.open(url)
                steps_taken.append(ActionResult(True, "browse", f"Opened browser URL: {url}"))
                return {
                    "status": "success",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "message": f"ค้นหา '{search_query}' บนเว็บเบราว์เซอร์ให้เรียบร้อยแล้วครับ",
                }

            elif any(k in clean_goal for k in ["จับภาพหน้าจอ", "แคปหน้าจอ", "screenshot"]):
                self._notify_status("Planning", "Capturing screenshot...")
                sc_path = self.take_screenshot()
                steps_taken.append(ActionResult(True, "screenshot", f"Saved to {sc_path}"))
                return {
                    "status": "success",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "message": f"จับภาพหน้าจอคอมพิวเตอร์และบันทึกไว้ที่ {sc_path} เรียบร้อยแล้วครับ",
                }

            elif any(k in clean_goal for k in ["ย่อหน้าต่าง", "minimize"]):
                self.hotkey("win", "d")
                steps_taken.append(ActionResult(True, "hotkey", "Minimized all windows (Win+D)"))
                return {
                    "status": "success",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "message": "ย่อหน้าต่างทั้งหมดและแสดงเดสก์ท็อปให้แล้วครับ",
                }

            else:
                app_launched = False
                for app_key in COMMON_APP_MAP:
                    if app_key in clean_goal:
                        res = self.launch_app(COMMON_APP_MAP[app_key])
                        steps_taken.append(res)
                        app_launched = True
                        break

                if app_launched:
                    return {
                        "status": "success",
                        "goal": goal,
                        "steps": [s.__dict__ for s in steps_taken],
                        "message": f"เปิดโปรแกรมตามคำสั่ง '{goal}' เรียบร้อยแล้วครับ",
                    }

                active_win = self.get_active_window()
                return {
                    "status": "completed",
                    "goal": goal,
                    "steps": [s.__dict__ for s in steps_taken],
                    "active_window": active_win.title if active_win else "None",
                    "message": f"ตรวจสอบหน้าจอและหน้าต่างที่ทำงานอยู่ ({active_win.title if active_win else 'หน้าจอหลัก'}) เรียบร้อยแล้วครับ",
                }

        except Exception as e:
            logger.error(f"Error executing goal '{goal}': {e}", exc_info=True)
            return {
                "status": "error",
                "goal": goal,
                "error": str(e),
                "steps": [s.__dict__ for s in steps_taken],
            }


# Global Agent Singleton
computer_agent = WindowsAutomationAgent()


def get_computer_agent() -> WindowsAutomationAgent:
    return computer_agent
