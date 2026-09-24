"""
J.A.R.V.I.S. Autonomous System Overdrive
========================================
Active Resource Manager Daemon
Manages Windows Process Priorities and CPU/RAM optimization.
"""
from __future__ import annotations

import logging
import threading
import time
import os
import psutil
import ctypes
from typing import Optional, Set

logger = logging.getLogger("JarvisOverdrive")

# Windows Priority Classes
IDLE_PRIORITY_CLASS = 0x00000040
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
NORMAL_PRIORITY_CLASS = 0x00000020
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
HIGH_PRIORITY_CLASS = 0x00000080

# Essential processes that should NEVER be touched
ESSENTIAL_PROCESSES: Set[str] = {
    'svchost.exe', 'explorer.exe', 'system', 'system idle process',
    'csrss.exe', 'smss.exe', 'wininit.exe', 'services.exe', 'lsass.exe',
    'taskmgr.exe', 'spoolsv.exe', 'dwm.exe', 'conhost.exe', 'cmd.exe',
    'python.exe', 'pythonw.exe', 'code.exe', 'antimalware service executable'
}

# Processes that naturally deserve HIGH priority (Games, Renderers, Compilers)
HEAVY_WEIGHT_PROCESSES: Set[str] = {
    'dota2.exe', 'csgo.exe', 'valorant.exe', 'cyberpunk2077.exe', 'witcher3.exe',
    'vray.exe', 'blender.exe', 'premiere.exe', 'aftereffects.exe', 'photoshop.exe',
    'unrealeditor.exe', 'unity.exe', 'msbuild.exe', 'cl.exe'
}

class SystemOverdrive:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cooldown = 120  # Run every 2 minutes

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True)
        self._thread.start()
        logger.info("[System Overdrive] Daemon initialized. Monitoring resources.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            
    def _get_foreground_pid(self) -> Optional[int]:
        """Gets the Process ID of the currently active/focused window."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                return pid.value
        except Exception as e:
            logger.debug(f"[Overdrive] Failed to get foreground PID: {e}")
        return None

    def _daemon_loop(self):
        # The daemon loop is now deprecated since the Cognitive Loop handles decision making.
        # This keeps the thread alive just in case, but does nothing.
        while self._running:
            time.sleep(60)

    def optimize_system(self, auto_mode: bool = False) -> str:
        """
        Scans processes and adjusts priorities.
        If auto_mode is True, it runs quietly. If False, it returns a summary report.
        """
        boosted = 0
        demoted = 0
        
        foreground_pid = self._get_foreground_pid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                pid = proc.info['pid']
                name = str(proc.info['name']).lower()
                
                if name in ESSENTIAL_PROCESSES or pid == os.getpid():
                    continue

                # Check if it's the foreground window
                if foreground_pid and pid == foreground_pid:
                    if proc.nice() not in [HIGH_PRIORITY_CLASS, ABOVE_NORMAL_PRIORITY_CLASS]:
                        proc.nice(ABOVE_NORMAL_PRIORITY_CLASS)
                        boosted += 1
                        logger.debug(f"[Overdrive] Boosted foreground process: {name}")
                    continue
                
                # Check known heavy weights
                if name in HEAVY_WEIGHT_PROCESSES:
                    if proc.nice() not in [HIGH_PRIORITY_CLASS, ABOVE_NORMAL_PRIORITY_CLASS]:
                        proc.nice(HIGH_PRIORITY_CLASS)
                        boosted += 1
                    continue
                    
                # If background and high CPU, lower it slightly to prevent freezing foreground
                # (Need process to be idle to get real CPU percent, skipping for now in basic loop)
                # Instead, set low-priority for known resource hogs when not in foreground
                if "updater" in name or "telemetry" in name or "crash" in name:
                    if proc.nice() != IDLE_PRIORITY_CLASS:
                        proc.nice(IDLE_PRIORITY_CLASS)
                        demoted += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        report = f"System Optimized. Boosted {boosted} processes, Demoted {demoted} background tasks."
        if not auto_mode:
            logger.info(f"[System Overdrive] {report}")
            
        return report

# Global Singleton
overdrive_manager = SystemOverdrive()

def start_overdrive_daemon():
    overdrive_manager.start()
