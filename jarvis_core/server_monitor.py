"""
jarvis_core/server_monitor.py
=============================
Modular Service for Real-Time Server Telemetry, Listening Ports Inspector,
Database Integrity Verification, and Watchdog Supervisor Status.
"""

from __future__ import annotations

import gc
import os
import sys
import time
import socket
import sqlite3
import logging
import threading
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger("JarvisServerMonitor")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [SERVER-MONITOR] %(levelname)s - %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "jarvis_memory.db")


_TELEMETRY_CACHE: Dict[str, Any] = {}
_TELEMETRY_CACHE_TIME: float = 0.0
_TELEMETRY_CACHE_LOCK = threading.Lock()
_CPU_INITIALIZED = False


def get_full_server_telemetry(force_refresh: bool = False, max_age: float = 1.0) -> Dict[str, Any]:
    """
    Returns comprehensive telemetry for J.A.R.V.I.S. host machine and core process:
    - CPU overall and per-core (Non-blocking sampling with TTL caching)
    - Virtual Memory and Swap
    - Disk I/O & Space
    - J.A.R.V.I.S. Core Process metrics
    - Thermal / Saturation indicators
    """
    global _TELEMETRY_CACHE, _TELEMETRY_CACHE_TIME, _CPU_INITIALIZED
    now = time.time()
    with _TELEMETRY_CACHE_LOCK:
        if not force_refresh and _TELEMETRY_CACHE and (now - _TELEMETRY_CACHE_TIME < max_age):
            return dict(_TELEMETRY_CACHE)

    if not _CPU_INITIALIZED:
        psutil.cpu_percent(interval=None)
        _CPU_INITIALIZED = True

    vmem = psutil.virtual_memory()
    try:
        swap = psutil.swap_memory()
        swap_pct = swap.percent
    except Exception:
        swap_pct = 0.0

    # Non-blocking CPU measurement prevents 100ms GIL / thread stall
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(percpu=True, interval=None)

    # Core process stats
    current_proc = psutil.Process(os.getpid())
    with current_proc.oneshot():
        proc_mem = round(current_proc.memory_info().rss / (1024 * 1024), 2)
        proc_threads = current_proc.num_threads()
        proc_uptime = round(time.time() - current_proc.create_time(), 1)

    # Disk summary
    disk = psutil.disk_usage(os.path.splitdrive(BASE_DIR)[0] or "C:\\")

    # Network counters
    net_io = psutil.net_io_counters()

    # Memory saturation alert
    is_saturated = (vmem.percent >= 85.0)

    payload = {
        "status": "success",
        "timestamp": time.time(),
        "cpu": {
            "total_percent": cpu_percent,
            "core_count": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "per_core_percent": cpu_cores
        },
        "memory": {
            "total_gb": round(vmem.total / (1024**3), 2),
            "used_gb": round(vmem.used / (1024**3), 2),
            "available_gb": round(vmem.available / (1024**3), 2),
            "percent": vmem.percent,
            "swap_percent": swap_pct,
            "is_saturated": is_saturated
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_percent": disk.percent
        },
        "network": {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2)
        },
        "core_process": {
            "pid": current_proc.pid,
            "memory_mb": proc_mem,
            "threads": proc_threads,
            "uptime_seconds": proc_uptime
        }
    }
    with _TELEMETRY_CACHE_LOCK:
        _TELEMETRY_CACHE = payload
        _TELEMETRY_CACHE_TIME = payload["timestamp"]
    return payload


def check_listening_ports(target_ports: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Check if essential network ports are currently listening:
    - 5050: JARVIS Mainframe Flask Web / Mobile API
    - 8000: Secondary service
    - 8081: Expo Metro Bundler
    - 19000: Expo Go Server
    - 11434: Local Ollama LLM Core
    """
    if target_ports is None:
        target_ports = [5050, 8000, 8081, 19000, 11434]

    port_status: Dict[int, Dict[str, Any]] = {}
    
    # Try finding via psutil connections
    listening_pids: Dict[int, int] = {}
    try:
        conns = psutil.net_connections(kind='tcp')
        for c in conns:
            if c.status == psutil.CONN_LISTEN and c.laddr:
                listening_pids[c.laddr.port] = c.pid or 0
    except Exception:
        pass

    for port in target_ports:
        is_open = False
        pid = listening_pids.get(port, 0)
        pname = ""
        
        if pid:
            is_open = True
            try:
                pname = psutil.Process(pid).name()
            except Exception:
                pname = "Unknown"
        else:
            # Fallback socket check
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                res = s.connect_ex(('127.0.0.1', port))
                if res == 0:
                    is_open = True

        port_status[port] = {
            "is_listening": is_open,
            "owning_pid": pid if pid else None,
            "process_name": pname if pname else None,
            "service_hint": {
                5050: "JARVIS Mainframe & Mobile API",
                8000: "Secondary Core",
                8081: "Expo Metro Bundler",
                19000: "Expo Go Server",
                11434: "Ollama Local LLM Core"
            }.get(port, "General Service")
        }

    return {
        "status": "success",
        "ports": port_status
    }


def check_database_and_cache(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """
    Verify SQLite database integrity and examine cache sizes.
    """
    db_results: Dict[str, Any] = {"db_exists": os.path.exists(db_path)}
    
    if os.path.exists(db_path):
        db_results["size_kb"] = round(os.path.getsize(db_path) / 1024, 2)
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check;")
            res = cursor.fetchone()
            db_results["integrity"] = res[0] if res else "unknown"
            
            # Count table records
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            db_results["tables"] = tables
            conn.close()
        except Exception as e:
            db_results["error"] = str(e)
            db_results["integrity"] = "failed"
    else:
        db_results["integrity"] = "not_found"

    # Check cache directory sizes
    caches = {}
    cache_dirs = [
        ("mobile_cache", os.path.join(BASE_DIR, "mobile_cache")),
        ("tts_cache", os.path.join(BASE_DIR, "tts_cache")),
        ("temp_images", os.path.join(BASE_DIR, "temp_images")),
        ("vector_db", os.path.join(BASE_DIR, "jarvis_vector_db")),
    ]

    for name, cpath in cache_dirs:
        if os.path.exists(cpath):
            total_size = 0
            file_count = 0
            for r, d, files in os.walk(cpath):
                for f in files:
                    file_count += 1
                    try:
                        total_size += os.path.getsize(os.path.join(r, f))
                    except Exception:
                        pass
            caches[name] = {
                "exists": True,
                "file_count": file_count,
                "size_mb": round(total_size / (1024 * 1024), 2)
            }
        else:
            caches[name] = {"exists": False, "file_count": 0, "size_mb": 0.0}

    return {
        "status": "success",
        "database": db_results,
        "caches": caches
    }


def supervise_watchdog_services() -> Dict[str, Any]:
    """
    Inspect the status of the JARVIS Watchdog supervisor and background agents.
    Performs memory compaction if needed.
    """
    watchdog_running = False
    watchdog_pid = None
    agent_windows_running = False

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline'] or []).lower()
            if "jarvis_watchdog.py" in cmdline:
                watchdog_running = True
                watchdog_pid = proc.info['pid']
            if "agent_windows_core.py" in cmdline:
                agent_windows_running = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Execute gc collect
    collected = gc.collect()

    return {
        "status": "success",
        "watchdog_active": watchdog_running,
        "watchdog_pid": watchdog_pid,
        "windows_background_agent_active": agent_windows_running,
        "gc_collected_objects": collected,
        "message": (
            "Watchdog กำลังคุ้มกันระบบอยู่ครับ" if watchdog_running 
            else "ไม่พบ Watchdog กำลังรันอยู่ แนะนำให้เริ่มระบบผ่าน run_jarvis.bat ครับ"
        )
    }
