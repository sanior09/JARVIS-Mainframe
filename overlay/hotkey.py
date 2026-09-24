"""
hotkey.py -- Global Hotkey Listener Thread (Ctrl+Space)
Runs in QThread to avoid blocking the Qt event loop.
"""
from __future__ import annotations
import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class GlobalHotkeyThread(QThread):
    """Listens for Ctrl+Space globally and emits toggle_requested."""

    toggle_requested: Signal = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl_held: bool = False

    def run(self) -> None:
        try:
            from pynput import keyboard

            def on_press(key) -> None:
                try:
                    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                        self._ctrl_held = True
                    elif self._ctrl_held and key == keyboard.Key.space:
                        self.toggle_requested.emit()
                except Exception:
                    pass

            def on_release(key) -> None:
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    self._ctrl_held = False

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()

        except ImportError:
            logger.warning("[Hotkey] pynput not installed. Run: pip install pynput")
        except Exception as exc:
            logger.error("[Hotkey] Listener error: %s", exc)

    def stop(self) -> None:
        self.quit()
        self.wait(2000)