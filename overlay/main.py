"""
main.py -- J.A.R.V.I.S. Floating Overlay HUD Entry Point
Wires together: HudWindow, JarvisApiClient, SystemTrayManager, GlobalHotkeyThread
"""
from __future__ import annotations
import logging
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from api_client import JarvisApiClient
from hotkey import GlobalHotkeyThread
from state import CONFIG
from tray import SystemTrayManager
from window import HudWindow

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("jarvis.overlay")


class OverlayController:
    """
    Thin orchestrator. Owns all subsystem references and connects signals.
    No business logic lives here -- each module handles its own concerns.
    """

    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._window = HudWindow()
        self._api = JarvisApiClient()
        self._tray = SystemTrayManager()
        self._hotkey = GlobalHotkeyThread()

        # Wire signals
        self._api.backend_online.connect(self._on_backend_online)
        self._api.backend_offline.connect(self._on_backend_offline)
        self._tray.show_requested.connect(self._window.toggle)
        self._tray.quit_requested.connect(self._shutdown)
        self._hotkey.toggle_requested.connect(self._window.toggle)

        # Start subsystems
        self._api.start_polling()
        self._hotkey.start()
        logger.info("[Controller] Overlay started. Hotkey: Ctrl+Space | Hover top edge")

    def _on_backend_online(self) -> None:
        self._window.load_backend()
        self._tray.set_online(True)
        self._tray.show_message(CONFIG.app_name, "Mainframe online.")

    def _on_backend_offline(self) -> None:
        self._window.show_offline()
        self._tray.set_online(False)

    def _shutdown(self) -> None:
        logger.info("[Controller] Graceful shutdown")
        self._hotkey.stop()
        self._api.stop_polling()
        self._tray.cleanup()
        self._app.quit()


def main() -> None:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName(CONFIG.app_name)
    app.setQuitOnLastWindowClosed(False)
    controller = OverlayController(app)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()