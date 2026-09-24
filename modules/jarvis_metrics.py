"""
[JARVIS METRICS & TELEMETRY COLLECTOR]
เก็บบันทึกสถิติการใช้งาน Groq LLM แบบเรียลไทม์:
- จำนวน Token (Prompt, Completion, Total)
- Response Time (ms / s)
- อัตราความสำเร็จ (Success Rate %)
- ข้อมูลคำขอวันนี้ (Requests Today)
- Rolling window 100 requests ล่าสุดใน RAM
"""

import threading
import time
from collections import deque
from datetime import datetime
from typing import Callable, Optional


class JarvisMetricsCollector:
    """
    Real-time Performance & Telemetry Metrics Collector for JARVIS LLM & Subsystems.
    Tracks token usage, latency (ms), success/error rates, and rolling request history in RAM.
    """

    def __init__(
        self,
        max_history: int = 100,
        quota_fn: Optional[Callable[[], int]] = None,
        default_model: str = "qwen/qwen3.8-27b"
    ):
        self._lock = threading.Lock()
        self.max_history = max_history
        self._requests = deque(maxlen=max_history)
        self._tokens_today = {"prompt": 0, "completion": 0, "total": 0}
        self._errors_today = 0
        self._success_today = 0
        self._total_requests = 0
        self._start_date = datetime.now().strftime("%Y-%m-%d")
        self._model_usage: dict[str, int] = {}
        self._quota_fn = quota_fn
        self._default_model = default_model

    def set_quota_fn(self, fn: Callable[[], int]) -> None:
        """ตั้งค่า Callback ฟังก์ชันสำหรับดึงจำนวน quota จาก Database"""
        self._quota_fn = fn

    def set_default_model(self, model: str) -> None:
        self._default_model = model

    def record(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        response_time_ms: float = 0.0,
        model: str = "",
        success: bool = True
    ) -> None:
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != self._start_date:
                self._start_date = today
                self._tokens_today = {"prompt": 0, "completion": 0, "total": 0}
                self._errors_today = 0
                self._success_today = 0
                self._total_requests = 0
                self._model_usage.clear()

            self._total_requests += 1
            if success:
                self._success_today += 1
            else:
                self._errors_today += 1

            p_tok = int(prompt_tokens or 0)
            c_tok = int(completion_tokens or 0)
            tot_tok = p_tok + c_tok

            self._tokens_today["prompt"] += p_tok
            self._tokens_today["completion"] += c_tok
            self._tokens_today["total"] += tot_tok

            raw_model = model or self._default_model
            m_name = raw_model.split("/")[-1]
            self._model_usage[m_name] = self._model_usage.get(m_name, 0) + 1

            self._requests.append({
                "timestamp": time.time(),
                "response_time_ms": round(float(response_time_ms or 0.0), 1),
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": tot_tok,
                "model": m_name,
                "success": bool(success)
            })

    def get_stats(self) -> dict:
        with self._lock:
            recent = list(self._requests)
            if recent:
                success_times = [
                    r["response_time_ms"] for r in recent
                    if r.get("success") and r.get("response_time_ms", 0) > 0
                ]
                avg_response_ms = round(sum(success_times) / len(success_times), 1) if success_times else 0.0
            else:
                avg_response_ms = 0.0

            db_count = 0
            if self._quota_fn:
                try:
                    db_count = self._quota_fn()
                except Exception:
                    db_count = 0

            display_requests = max(self._total_requests, db_count)
            total_attempted = self._success_today + self._errors_today
            if total_attempted > 0:
                success_rate = round((self._success_today / total_attempted) * 100, 1)
            else:
                success_rate = 100.0

            trend = [
                {
                    "t": int(r["timestamp"]),
                    "tokens": r["total_tokens"],
                    "ms": r["response_time_ms"],
                    "ok": r["success"]
                }
                for r in recent[-15:]
            ]

            active_model = self._default_model.split("/")[-1]

            return {
                "status": "online",
                "avg_response_ms": avg_response_ms,
                "avg_response_s": round(avg_response_ms / 1000.0, 2),
                "success_rate": success_rate,
                "tokens_today": dict(self._tokens_today),
                "requests_today": display_requests,
                "success_today": self._success_today,
                "errors_today": self._errors_today,
                "active_model": active_model,
                "model_usage": dict(self._model_usage),
                "recent_trend": trend,
                "quota_limit": 14400,
                "quota_percent": round((display_requests / 14400.0) * 100, 2) if display_requests else 0.0
            }


# Global Singleton instance
METRICS = JarvisMetricsCollector()
