"""
J.A.R.V.I.S. Autonomous Background Diagnostics
================================================
เฝ้าดูสุขภาพระบบโดยไม่ต้องร้องขอ และแจ้งเตือนเจ้านายเองเมื่อมีความผิดปกติ
เหมือน JARVIS จริงๆ ที่จะทักว่า "ขออภัยที่ขัดจังหวะครับนาย แต่ CPU กำลังร้อนเกินครับ"
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("JarvisDiagnostics")

CPU_WARN_PERCENT = 85       
CPU_SUSTAINED_SECS = 30     
RAM_WARN_PERCENT = 90       
DISK_WARN_GB = 5.0          
ALERT_COOLDOWN_SECS = 300   
CHECK_INTERVAL_SECS = 60    

_diag_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_last_alert_time: dict[str, float] = {}
_cpu_high_since: Optional[float] = None

def _can_alert(key: str) -> bool:
    """ป้องกัน alert spam — แจ้งซ้ำได้ก็ต่อเมื่อผ่านไปแล้ว COOLDOWN วินาที"""
    now = time.time()
    if now - _last_alert_time.get(key, 0) > ALERT_COOLDOWN_SECS:
        _last_alert_time[key] = now
        return True
    return False

def _send_alert(msg: str) -> None:
    """ส่งแจ้งเตือนผ่าน Dynamic Island และ log"""
    logger.warning(f"[Diagnostics] ALERT: {msg}")
    try:
        from dynamic_island import send_to_island
        send_to_island("ALERT", msg)
    except Exception:
        pass
    
    try:
        from local_engine import get_tts_engine
        tts = get_tts_engine()
        if tts:
            import asyncio
            async def _say():
                async def _gen():
                    yield msg
                await tts.speak_stream(_gen())
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_say())
                else:
                    loop.run_until_complete(_say())
            except Exception:
                pass
    except Exception:
        pass

def _check_system() -> None:
    """ตรวจสอบสุขภาพระบบ 1 รอบ"""
    global _cpu_high_since
    try:
        import psutil
    except ImportError:
        return  

    try:
        cpu = psutil.cpu_percent(interval=1)
        if cpu > CPU_WARN_PERCENT:
            if _cpu_high_since is None:
                _cpu_high_since = time.time()
            elif time.time() - _cpu_high_since > CPU_SUSTAINED_SECS:
                if _can_alert("cpu"):
                    _send_alert(f"CPU ทำงานหนักที่ {cpu:.0f}% มานานกว่า {CPU_SUSTAINED_SECS} วินาทีแล้วครับนาย ควรตรวจสอบโปรแกรมที่รันอยู่")
        else:
            _cpu_high_since = None
    except Exception as e:
        logger.debug(f"[Diagnostics] CPU check error: {e}")

    try:
        ram = psutil.virtual_memory()
        if ram.percent > RAM_WARN_PERCENT:
            if _can_alert("ram"):
                used_gb = ram.used / 1e9
                total_gb = ram.total / 1e9
                _send_alert(f"RAM เหลือน้อยมากครับนาย ใช้ไปแล้ว {used_gb:.1f}/{total_gb:.1f} GB ({ram.percent:.0f}%)")
    except Exception as e:
        logger.debug(f"[Diagnostics] RAM check error: {e}")

    try:
        disk = psutil.disk_usage("C:\\")
        free_gb = disk.free / 1e9
        if free_gb < DISK_WARN_GB:
            if _can_alert("disk"):
                _send_alert(f"พื้นที่ดิสก์ C: เหลือแค่ {free_gb:.1f} GB แล้วครับนาย ควรเคลียร์พื้นที่ก่อนที่ระบบจะทำงานผิดพลาด")
    except Exception as e:
        logger.debug(f"[Diagnostics] Disk check error: {e}")

def _diagnostics_loop() -> None:
    """Main loop ของ background thread"""
    logger.info("[Diagnostics] Autonomous diagnostic thread started")
    
    _stop_event.wait(timeout=30)
    while not _stop_event.is_set():
        _check_system()
        _stop_event.wait(timeout=CHECK_INTERVAL_SECS)
    logger.info("[Diagnostics] Diagnostic thread stopped")

def start_diagnostics() -> None:
    """เริ่มต้น diagnostics thread — เรียกครั้งเดียวตอน startup"""
    global _diag_thread
    if _diag_thread and _diag_thread.is_alive():
        return
    _stop_event.clear()
    _diag_thread = threading.Thread(target=_diagnostics_loop, daemon=True, name="JarvisDiagnostics")
    _diag_thread.start()

def stop_diagnostics() -> None:
    """หยุด diagnostics thread"""
    _stop_event.set()

def get_system_snapshot() -> dict:
    """ดึงสถานะระบบแบบ on-demand สำหรับคำถามเช่น 'CPU ตอนนี้เป็นยังไง'"""
    snapshot = {"cpu_percent": None, "ram_percent": None, "ram_used_gb": None,
                "ram_total_gb": None, "disk_free_gb": None}
    try:
        import psutil
        snapshot["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        snapshot["ram_percent"] = ram.percent
        snapshot["ram_used_gb"] = round(ram.used / 1e9, 1)
        snapshot["ram_total_gb"] = round(ram.total / 1e9, 1)
        disk = psutil.disk_usage("C:\\")
        snapshot["disk_free_gb"] = round(disk.free / 1e9, 1)
    except Exception:
        pass
    return snapshot
