"""
modules/jarvis_afk_keeper.py
===========================
J.A.R.V.I.S. Autonomous Anti-AFK & Anti-Disconnect Keeper Subsystem.
Prevents games (e.g., Roblox, Steam, MMOs) or apps from auto-disconnecting
or kicking the user due to inactivity/idle timeouts.
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("JarvisAFKKeeper")

class AFKKeeperService:
    _instance: Optional["AFKKeeperService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.interval_minutes = 15
        self.interval_seconds = 15 * 60
        self.last_action_time = time.time()
        self.last_mouse_pos = (0, 0)
        self.pulse_count = 0
        self.target_game = "general"

    @classmethod
    def get_instance(cls) -> "AFKKeeperService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = AFKKeeperService()
            return cls._instance

    def start(self, interval_minutes: int = 15, target_game: str = "Roblox") -> str:
        with self._lock:
            if interval_minutes < 1:
                interval_minutes = 1
            if interval_minutes > 120:
                interval_minutes = 120

            self.interval_minutes = interval_minutes
            self.interval_seconds = interval_minutes * 60
            self.target_game = target_game
            self.pulse_count = 0
            self.last_action_time = time.time()

            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                self.last_mouse_pos = pyautogui.position()
            except Exception:
                pass

            if self.is_running:
                return f"ระบบเฝ้าหน้าจอ AFK กำลังทำงานอยู่แล้วครับ (ปรับรอบเวลาเป็นทุกๆ {interval_minutes} นาที สำหรับ {target_game})"

            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True, name="JarvisAFKKeeper")
            self.thread.start()

            logger.info(f"[AFK KEEPER] Started with interval {interval_minutes} mins for {target_game}")
            return f"เปิดระบบเฝ้าหน้าจอ AFK ให้เรียบร้อยแล้วครับเจ้านาย ผมจะช่วยขยับเมาส์และป้องกันเกม {target_game} เด้งหลุดทุกๆ {interval_minutes} นาทีครับ"

    def stop(self) -> str:
        with self._lock:
            if not self.is_running:
                return "ระบบเฝ้าหน้าจอ AFK ไม่ได้เปิดทำงานอยู่ครับเจ้านาย"

            self.is_running = False
            logger.info("[AFK KEEPER] Stopped by user command.")
            return f"ปิดระบบเฝ้าหน้าจอ AFK เรียบร้อยแล้วครับเจ้านาย (ช่วยรักษาสถานะออนไลน์ไปทั้งหมด {self.pulse_count} ครั้ง)"

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "pulse_count": self.pulse_count,
            "target_game": self.target_game,
            "time_since_last_pulse": int(time.time() - self.last_action_time)
        }

    def _run_loop(self) -> None:
        import pyautogui
        pyautogui.FAILSAFE = False

        while self.is_running:
            # Sleep in short increments to support responsive cancellation
            time.sleep(1.0)
            if not self.is_running:
                break

            now = time.time()
            # If user actively moved mouse significantly, reset idle timer to avoid interfering
            try:
                cur_pos = pyautogui.position()
                if abs(cur_pos.x - self.last_mouse_pos.x) > 30 or abs(cur_pos.y - self.last_mouse_pos.y) > 30:
                    self.last_mouse_pos = cur_pos
                    self.last_action_time = now
                    continue
            except Exception:
                pass

            if now - self.last_action_time >= self.interval_seconds:
                self._perform_anti_kick_action()
                self.last_action_time = time.time()
                self.pulse_count += 1

    def _perform_anti_kick_action(self) -> None:
        try:
            import pyautogui
            logger.info(f"[AFK KEEPER] Executing anti-disconnect action #{self.pulse_count + 1}...")

            # 1. Subtle cursor wiggle (moves 6px right then back)
            cur_x, cur_y = pyautogui.position()
            pyautogui.moveRel(6, 0, duration=0.1)
            time.sleep(0.08)
            pyautogui.moveRel(-6, 0, duration=0.1)
            self.last_mouse_pos = pyautogui.position()

            # 2. Key tap for game responsiveness (e.g. Roblox jump or shift)
            time.sleep(0.1)
            # Tap 'space' or 'd'/'a' safely
            pyautogui.press('space')
            time.sleep(0.05)

            try:
                from modules.jarvis_screen_takeover import flash_screen_takeover
                flash_screen_takeover("🛡️ J.A.R.V.I.S.: Anti-AFK Pulse (Online)", duration_sec=1.5)
            except Exception:
                pass

            logger.info(f"[AFK KEEPER] Anti-disconnect pulse #{self.pulse_count + 1} completed.")
        except Exception as e:
            logger.error(f"[AFK KEEPER] Pulse execution failed: {e}")


def manage_afk_keeper_operation(action: str = "start", interval_minutes: int = 20, game_name: str = "Roblox") -> str:
    service = AFKKeeperService.get_instance()
    act = (action or "start").lower().strip()

    if act in ["stop", "cancel", "disable", "off", "ปิด"]:
        return service.stop()
    elif act in ["status", "check", "สถานะ"]:
        st = service.get_status()
        if st["running"]:
            return f"ระบบเฝ้าหน้าจอ AFK กำลังทำงานอยู่ครับ (รอบเวลาทุก {st['interval_minutes']} นาที, ดำเนินการไปแล้ว {st['pulse_count']} ครั้ง สำหรับ {st['target_game']})"
        else:
            return "ระบบเฝ้าหน้าจอ AFK ขณะนี้ปิดอยู่ครับเจ้านาย"
    else:
        return service.start(interval_minutes=interval_minutes, target_game=game_name)
