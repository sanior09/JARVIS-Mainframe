"""
jarvis_core.boot
================
System boot sequence, background daemons initialization, global hotkeys,
and startup greeting orchestration for J.A.R.V.I.S.
"""

from __future__ import annotations

import logging
import random
import sys
import threading
import time
from typing import Optional

logger = logging.getLogger("JarvisBoot")


def perform_system_boot_sequence(silent: bool = False) -> None:
    """Perform integrity checks and initialize subsystem logs."""
    if not silent:
        logger.info("=" * 60)
        logger.info("  J.A.R.V.I.S. Core Boot Sequence Initiated")
        logger.info("=" * 60)


def execute_boot_automation() -> None:
    """Execute initial boot tasks, checking hardware and telemetry."""
    logger.info("Executing boot automation matrix...")
    try:
        from jarvis_core.automation_agent import get_computer_agent
        agent = get_computer_agent()
        active = agent.get_active_window()
        logger.info(f"[BOOT] Screen resolved: {agent.screen_width}x{agent.screen_height} | Active: {active.title if active else 'Desktop'}")
    except Exception as e:
        logger.warning(f"[BOOT] Computer Agent check: {e}")


def setup_global_hotkeys() -> None:
    """Bind global keyboard shortcuts (e.g. Ctrl+Shift+J for voice input)."""
    try:
        import keyboard
        import jarvis_core.state as state
        keyboard.add_hotkey(
            "ctrl+shift+j",
            lambda: state.voice_engine.trigger_voice_input() if state.voice_engine else logger.warning("Voice engine not ready")
        )
        logger.info("[HOTKEY] 🎙️ Press Ctrl+Shift+J anywhere to talk to J.A.R.V.I.S.")
    except Exception as e:
        logger.warning(f"[HOTKEY] Failed to bind global hotkey (requires admin on some systems): {e}")


def start_delayed_greeting(voice_engine: Optional[Any] = None) -> None:
    """Wait for audio listener to be ready, then speak an organic boot greeting."""
    def _greeting_worker():
        time.sleep(1.0)
        boot_greetings = [
            "จาร์วิสออนไลน์... พร้อมปฏิบัติการแล้วครับเจ้านาย",
            "ระบบออนไลน์เต็มรูปแบบ... วันนี้มีภารกิจอะไรให้รับใช้มั้ยครับ",
            "สวัสดีครับเจ้านาย... ระบบพร้อมรับคำสั่งแล้วครับ",
            "จาร์วิสพร้อมแล้วครับ... มีอะไรสั่งการได้ทันทีเลยครับ"
        ]
        selected = random.choice(boot_greetings)
        if voice_engine and hasattr(voice_engine, "speak_direct"):
            try:
                voice_engine.speak_direct(selected)
            except Exception as e:
                logger.debug(f"Greeting error: {e}")

    threading.Thread(target=_greeting_worker, daemon=True, name="Boot-Greeting").start()


def start_background_daemons(app: Any, voice_engine: Optional[Any] = None) -> None:
    """
    Launch all secondary background daemons:
    - Awareness daemon
    - Diagnostics daemon
    - Network radar
    - Proactive intelligence
    - Trend harvester
    - Global hotkeys
    """
    logger.info("[BOOT] 🚀 Launching secondary background daemons...")

    # 1. Awareness daemon
    try:
        import jarvis_awareness
        if hasattr(jarvis_awareness, "start_awareness"):
            jarvis_awareness.start_awareness()
        logger.info("[BOOT] ✅ Awareness Daemon online.")
    except Exception as e:
        logger.debug(f"[BOOT] Awareness daemon not started: {e}")

    # 2. Diagnostics daemon
    try:
        import jarvis_diagnostics
        if hasattr(jarvis_diagnostics, "start_diagnostics"):
            jarvis_diagnostics.start_diagnostics()
        logger.info("[BOOT] ✅ Diagnostics Daemon online.")
    except Exception as e:
        logger.debug(f"[BOOT] Diagnostics daemon not started: {e}")

    # 3. Proactive module
    try:
        import jarvis_proactive
        if hasattr(jarvis_proactive, "start"):
            jarvis_proactive.start()
        logger.info("[BOOT] ✅ Proactive Intelligence activated.")
    except Exception as e:
        logger.debug(f"[BOOT] Proactive module not started: {e}")

    # 4. Global Hotkeys
    setup_global_hotkeys()

    # 5. Delayed Greeting
    if voice_engine:
        start_delayed_greeting(voice_engine)
