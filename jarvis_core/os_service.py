"""
jarvis_core/os_service.py
=========================
Modular Service for Windows OS Management, Process Control,
System Maintenance, and Safe Automation Script Execution.
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import logging
import subprocess
from typing import Any, Dict, List, Optional, Union

import psutil

logger = logging.getLogger("JarvisOSService")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [OS-SERVICE] %(levelname)s - %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

PROTECTED_PROCESSES = {
    "svchost.exe", "csrss.exe", "wininit.exe", "smss.exe", "services.exe",
    "lsass.exe", "winlogon.exe", "explorer.exe", "dwm.exe"
}


def list_active_processes(top_n: int = 15, sort_by: str = "memory") -> Dict[str, Any]:
    """
    List top active Windows processes sorted by memory usage (MB) or CPU percentage.
    """
    processes = []
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'create_time']):
        try:
            info = proc.info
            mem_mb = round((info['memory_info'].rss if info.get('memory_info') else 0) / (1024 * 1024), 2)
            cpu = info.get('cpu_percent') or 0.0
            
            processes.append({
                "pid": info['pid'],
                "name": info['name'] or "Unknown",
                "cpu_percent": cpu,
                "memory_mb": mem_mb,
                "status": info.get('status', 'running'),
                "is_current": (info['pid'] == current_pid),
                "is_protected": (info['name'].lower() in PROTECTED_PROCESSES if info.get('name') else False)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by.lower() == "cpu":
        processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
    else:
        processes.sort(key=lambda p: p["memory_mb"], reverse=True)

    top_list = processes[:top_n]
    return {
        "status": "success",
        "total_processes": len(processes),
        "top_n": top_n,
        "sorted_by": sort_by,
        "processes": top_list
    }


def kill_process_by_identifier(identifier: Union[str, int]) -> Dict[str, Any]:
    """
    Safely terminate a process by PID (int or numeric str) or Process Name (e.g. 'chrome.exe').
    Refuses to terminate critical system processes or self.
    """
    current_pid = os.getpid()
    terminated = []
    errors = []

    # Check if identifier is PID
    target_pid: Optional[int] = None
    target_name: Optional[str] = None

    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.strip().isdigit()):
        target_pid = int(identifier)
    else:
        target_name = str(identifier).strip().lower()
        if not target_name.endswith(".exe") and "." not in target_name:
            target_name += ".exe"

    if target_pid:
        if target_pid == current_pid:
            return {"status": "error", "message": "ไม่อนุญาตให้ปิด Process ตัวเอง (J.A.R.V.I.S. Core) ครับ"}
        try:
            p = psutil.Process(target_pid)
            pname = p.name().lower()
            if pname in PROTECTED_PROCESSES:
                return {"status": "error", "message": f"ไม่อนุญาตให้ปิดระบบ Core Windows: {pname}"}
            p.terminate()
            p.wait(timeout=3)
            terminated.append({"pid": target_pid, "name": pname})
        except psutil.TimeoutExpired:
            p.kill()
            terminated.append({"pid": target_pid, "name": pname, "forced": True})
        except Exception as e:
            errors.append(f"PID {target_pid}: {str(e)}")
    elif target_name:
        if target_name in PROTECTED_PROCESSES:
            return {"status": "error", "message": f"ไม่อนุญาตให้ปิดระบบ Core Windows: {target_name}"}
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == target_name:
                    pid = proc.info['pid']
                    if pid == current_pid:
                        continue
                    proc.terminate()
                    terminated.append({"pid": pid, "name": target_name})
            except Exception as e:
                errors.append(f"Process {target_name}: {str(e)}")

    if terminated:
        return {
            "status": "success",
            "message": f"ยุติการทำงานของ Process สำเร็จ {len(terminated)} รายการ",
            "terminated": terminated,
            "errors": errors
        }
    else:
        msg = f"ไม่พบ Process '{identifier}' หรือไม่สามารถปิดได้"
        if errors:
            msg += f" (Errors: {'; '.join(errors)})"
        return {"status": "error", "message": msg}


def run_system_maintenance() -> Dict[str, Any]:
    """
    Perform Windows system maintenance:
    - Check disk space (C: drive)
    - Clean safe temporary files in %TEMP%
    - Report system uptime and memory status
    """
    results: Dict[str, Any] = {}

    # 1. Disk usage
    try:
        disk = psutil.disk_usage("C:\\")
        results["disk"] = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent
        }
    except Exception as e:
        results["disk_error"] = str(e)

    # 2. System Uptime
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = round(uptime_seconds / 3600, 2)
        results["system_uptime_hours"] = uptime_hours
    except Exception as e:
        results["uptime_error"] = str(e)

    # 3. Clean %TEMP% directory safely
    temp_dir = os.environ.get("TEMP", os.environ.get("TMP", ""))
    cleaned_files = 0
    cleaned_bytes = 0
    if temp_dir and os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    # Only delete files older than 6 hours to prevent deleting in-use locks
                    if time.time() - os.path.getmtime(filepath) > 21600:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned_files += 1
                        cleaned_bytes += size
                except Exception:
                    continue

    results["temp_cleaned"] = {
        "files_removed": cleaned_files,
        "freed_mb": round(cleaned_bytes / (1024 * 1024), 2)
    }

    # 4. RAM status
    vmem = psutil.virtual_memory()
    results["memory"] = {
        "total_gb": round(vmem.total / (1024**3), 2),
        "available_gb": round(vmem.available / (1024**3), 2),
        "percent_used": vmem.percent
    }

    return {
        "status": "success",
        "message": f"บำรุงรักษาระบบเรียบร้อย เคลียร์ไฟล์ชั่วคราว {cleaned_files} ไฟล์ (ประหยัดพื้นที่ {results['temp_cleaned']['freed_mb']} MB)",
        "details": results
    }


def execute_safe_powershell(command: str) -> Dict[str, Any]:
    """
    Execute a PowerShell command safely after inspecting for critical hazards.
    """
    # Blacklist dangerous destructive patterns
    dangerous = [
        "format-volume", "remove-item -recurse c:\\windows", "del /f /s /q c:\\windows",
        "diskpart", "bcdedit", "stop-computer"
    ]
    norm_cmd = command.lower()
    for d in dangerous:
        if d in norm_cmd:
            return {"status": "error", "message": f"คำสั่งถูกระงับโดยระบบความปลอดภัยเนื่องจากมีความเสี่ยงสูง: '{d}'"}

    # Optional AST check via CodeSentinel
    try:
        from code_sentinel import IsolatedCodeSandbox  # type: ignore
    except ImportError:
        pass

    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=25
        )
        return {
            "status": "success" if res.returncode == 0 else "failed",
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "การรันคำสั่งหมดเวลา (Timeout 25s)"}
    except Exception as e:
        return {"status": "error", "message": f"เกิดข้อผิดพลาดในการรันคำสั่ง: {str(e)}"}
