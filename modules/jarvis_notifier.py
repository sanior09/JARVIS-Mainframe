"""
[JARVIS NOTIFICATION SYSTEM]
ระบบแจ้งเตือนอัจฉริยะสำหรับ J.A.R.V.I.S.
ส่งข้อความแจ้งเตือนผ่าน LINE Messaging API (Push Message) แบบ Non-blocking:
- ✅ แจ้งเตือนเมื่อ Task / Computer Control สำเร็จ
- ❌ แจ้งเตือนข้อผิดพลาดสำคัญ (Critical Error / Exception)
- ⚠️ แจ้งเตือนสถานะทรัพยากรเครื่อง (Resource Alert: CPU, RAM, GPU)
- 🧠 แจ้งเตือนกระบวนการเรียนรู้และความจำ (Memory Consolidation)
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests

try:
    from jarvis_line_adapter import format_reply_for_line
except (ImportError, ModuleNotFoundError):
    try:
        from modules.jarvis_line_adapter import format_reply_for_line
    except (ImportError, ModuleNotFoundError):
        def format_reply_for_line(text: str) -> str:
            return text.strip() if text else ""

logger = logging.getLogger("JARVIS_NOTIFIER")


class JarvisNotifier:
    """
    JARVIS Notification Manager
    จัดการการส่ง Push Notification ไปยัง LINE ของผู้ใช้งาน (Owner)
    ทำงานแบบ Asynchronous ผ่าน ThreadPoolExecutor เพื่อไม่ให้หน่วงระบบหลัก
    """

    LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

    def __init__(
        self,
        access_token: Optional[str] = None,
        owner_id: Optional[str] = None,
        max_workers: int = 2
    ):
        self._access_token = (
            access_token
            if access_token is not None
            else os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        ).strip().strip('"').strip("'")

        self._owner_id = (
            owner_id
            if owner_id is not None
            else os.getenv("LINE_OWNER_USER_ID", "")
        ).strip().strip('"').strip("'")

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="jarvis_notifier"
        )
        self._cooldowns: dict[str, float] = {}

    @property
    def is_configured(self) -> bool:
        """ตรวจสอบว่าระบบตั้งค่า LINE API Token และ Owner ID ครบถ้วนหรือไม่"""
        return bool(self._access_token and self._owner_id)

    def _should_suppress(self, alert_key: str, cooldown_sec: int) -> bool:
        """ป้องกันการส่งข้อความซ้ำๆ ถี่เกินไป (Alert Fatigue Prevention)"""
        now = time.time()
        last_time = self._cooldowns.get(alert_key, 0.0)
        if (now - last_time) < cooldown_sec:
            return True
        self._cooldowns[alert_key] = now
        return False

    def send_push_sync(
        self,
        message: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        ส่งข้อความ Push ไปยัง LINE แบบ Synchronous (บล็อกจนกว่าจะส่งเสร็จ)
        """
        target_id = (user_id or self._owner_id or "").strip()
        if not self._access_token:
            logger.debug("[NOTIFIER] Skipped: LINE_CHANNEL_ACCESS_TOKEN is not configured.")
            return False
        if not target_id:
            logger.debug("[NOTIFIER] Skipped: Target LINE User ID is not configured.")
            return False

        clean_text = format_reply_for_line(message)
        if not clean_text:
            return False

        # ตัดความยาวไม่ให้เกิน 2000 ตัวอักษรตามข้อกำหนดของ LINE Messaging API
        if len(clean_text) > 2000:
            clean_text = clean_text[:1990] + "..."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }
        payload = {
            "to": target_id,
            "messages": [
                {
                    "type": "text",
                    "text": clean_text
                }
            ]
        }

        try:
            resp = requests.post(
                self.LINE_PUSH_URL,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"[NOTIFIER] Push sent successfully to {target_id[:8]}***")
                return True
            else:
                logger.warning(
                    f"[NOTIFIER] LINE Push failed (HTTP {resp.status_code}): {resp.text}"
                )
                return False
        except Exception as e:
            logger.error(f"[NOTIFIER] Push exception: {e}")
            return False

    def send_push_async(
        self,
        message: str,
        user_id: Optional[str] = None
    ):
        """ส่งข้อความ Push แบบ Non-blocking ผ่าน Background Worker"""
        return self._executor.submit(self.send_push_sync, message, user_id)

    def notify_success(self, task: str, detail: str = "") -> None:
        """
        ✅ แจ้งเตือนเมื่องานเสร็จสมบูรณ์ (Task Completed)
        เช่น Computer Agent ทำงานอัตโนมัติสำเร็จ
        """
        msg = f"✅ [JARVIS TASK COMPLETE]\nงาน: {task}"
        if detail:
            msg += f"\nรายละเอียด: {detail}"
        self.send_push_async(msg)

    def notify_error(self, error: str, context: str = "") -> None:
        """
        ❌ แจ้งเตือนเมื่อเกิดข้อผิดพลาดสำคัญ (Error Alert)
        """
        alert_key = f"err_{context}_{str(error)[:50]}"
        if self._should_suppress(alert_key, cooldown_sec=120):
            return

        msg = f"❌ [JARVIS ALERT - ERROR]\nข้อผิดพลาด: {error}"
        if context:
            msg += f"\nตำแหน่ง/บริบท: {context}"
        self.send_push_async(msg)

    def notify_alert(
        self,
        msg: str,
        level: str = "WARNING",
        alert_key: Optional[str] = None,
        cooldown_sec: int = 300
    ) -> None:
        """
        ⚠️ แจ้งเตือนสถานะความปลอดภัย หรือ ทรัพยากรเครื่อง (Resource / Safety Alert)
        มี Cooldown ป้องกันการส่งซ้ำ
        """
        key = alert_key or f"alert_{level}_{msg[:30]}"
        if self._should_suppress(key, cooldown_sec=cooldown_sec):
            return

        formatted = f"⚠️ [JARVIS {level.upper()}]\n{msg}"
        self.send_push_async(formatted)

    def notify_info(self, title: str, body: str = "") -> None:
        """
        ℹ️ แจ้งเตือนข้อมูลทั่วไป (General Info)
        เช่น การสรุปความจำรอบดึก (Nightly Consolidation)
        """
        msg = f"ℹ️ [JARVIS INFO]\n{title}"
        if body:
            msg += f"\n{body}"
        self.send_push_async(msg)


# Global Singleton Notifier
NOTIFIER = JarvisNotifier()
