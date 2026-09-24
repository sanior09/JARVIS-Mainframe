"""
jarvis_core.state
=================
Thread-safe runtime state, singleton managers, queues,
and telemetry tracking for J.A.R.V.I.S.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("JarvisState")

# Global Subsystem References
voice_engine: Optional[Any] = None
NEURO_STATE: Optional[Any] = None
vad_manager: Optional[Any] = None
event_bus: Optional[Any] = None
thought_engine: Optional[Any] = None
jarvis_scheduler: Optional[Any] = None

# Queues
strategist_memory_queue: queue.Queue = queue.Queue(maxsize=5)
jarvis_task_queue: queue.Queue = queue.Queue()

# Thread-safe Telemetry Registry
_telemetry_lock = threading.Lock()
_system_telemetry: Dict[str, Any] = {
    "status": "Online",
    "boot_time": time.time(),
    "cores": {
        "core1": {"status": "Online", "detail": "Language & Cognitive Router"},
        "core2": {"status": "Online", "detail": "Temporal & Episodic Memory"},
        "core3": {"status": "Online", "detail": "Voice & Realtime VAD"},
        "core4": {"status": "Online", "detail": "Windows Automation Agent"},
    },
    "metrics": {
        "groq_requests": 0,
        "tools_executed": 0,
        "last_active": time.time(),
    }
}


def update_core_telemetry(core_name: str, status: str, detail: str = "") -> None:
    """Update status for a specific core subsystem in thread-safe manner."""
    with _telemetry_lock:
        if "cores" not in _system_telemetry:
            _system_telemetry["cores"] = {}
        _system_telemetry["cores"][core_name] = {
            "status": status,
            "detail": detail,
            "updated_at": time.time(),
        }


def get_telemetry_snapshot() -> Dict[str, Any]:
    """Returns a deepcopy-like snapshot of system telemetry."""
    with _telemetry_lock:
        return {
            "status": _system_telemetry.get("status", "Online"),
            "uptime_seconds": time.time() - _system_telemetry.get("boot_time", time.time()),
            "cores": dict(_system_telemetry.get("cores", {})),
            "metrics": dict(_system_telemetry.get("metrics", {})),
        }


def increment_metric(metric_name: str, count: int = 1) -> int:
    """Thread-safe metric incrementer."""
    with _telemetry_lock:
        if "metrics" not in _system_telemetry:
            _system_telemetry["metrics"] = {}
        current = _system_telemetry["metrics"].get(metric_name, 0) + count
        _system_telemetry["metrics"][metric_name] = current
        _system_telemetry["metrics"]["last_active"] = time.time()
        return current


def get_metric(metric_name: str, default: int = 0) -> int:
    """Thread-safe metric getter."""
    with _telemetry_lock:
        return _system_telemetry.get("metrics", {}).get(metric_name, default)
