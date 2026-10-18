"""
Root proxy to modules/dynamic_island.py
Allows seamless execution and imports from workspace root.
"""
import os
import sys

# Ensure UTF-8 output on Windows consoles (avoids cp874 emoji crash)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

# Import directly from modules.dynamic_island without circular import
from modules.dynamic_island import (
    DynamicIsland,
    BuddyWidget,
    AgentEventWidget,
    UsageGaugeWidget,
    LiveDiffWidget,
    MarqueeLabel,
    send_to_island,
    send_toast_to_island,
    send_buddy_mood,
    send_buddy_skin,
    send_agent_event,
    send_usage_gauge,
    send_live_diff
)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import argparse

    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. HUD")
    parser.add_argument("--jarvis-pid", type=int, default=None)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    island = DynamicIsland()

    if args.jarvis_pid is not None:
        import threading as _thr
        try:
            import psutil as _psutil
            _HAS_PSUTIL = True
        except ImportError:
            _HAS_PSUTIL = False

        def _pid_watchdog(jarvis_pid: int) -> None:
            import time as _t
            consecutive_dead = 0
            while True:
                _t.sleep(2)
                alive = False
                try:
                    if _HAS_PSUTIL:
                        alive = _psutil.pid_exists(jarvis_pid)
                    else:
                        import ctypes
                        handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, jarvis_pid)
                        alive = handle != 0
                        if handle: ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    alive = False

                if alive:
                    consecutive_dead = 0
                else:
                    consecutive_dead += 1
                    if consecutive_dead >= 5:
                        import os as _os
                        _os._exit(0)
                        break
        _thr.Thread(target=_pid_watchdog, args=(args.jarvis_pid,), daemon=True, name="PidWatchdogThread").start()

    sys.exit(app.exec())
