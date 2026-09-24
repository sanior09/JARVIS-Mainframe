"""
tray.py -- JARVIS System Tray Manager
"""
from __future__ import annotations
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon
from state import CONFIG

logger = logging.getLogger(__name__)


def _build_icon(color: str = "#4fc3f7") -> QIcon:
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    px = QPixmap(32, 32)
    px.fill(QColor(0, 0, 0, 0))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(color))
    painter.drawEllipse(4, 4, 24, 24)
    painter.drawEllipse(10, 10, 12, 12)
    painter.end()
    return QIcon(px)


class SystemTrayManager(QObject):
    """System tray icon with context menu."""

    show_requested: Signal = Signal()
    quit_requested: Signal = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(_build_icon(), self)
        self._tray.setToolTip(CONFIG.tray_tooltip)
        self._tray.activated.connect(self._on_tray_activated)
        self._build_menu()
        self._tray.show()

    def set_online(self, online: bool) -> None:
        color = "#00e676" if online else "#ef5350"
        self._tray.setIcon(_build_icon(color))
        self._tray.setToolTip(f"{CONFIG.tray_tooltip} ? {'Online' if online else 'Offline'}")

    def show_message(self, title: str, msg: str) -> None:
        self._tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 3000)

    def cleanup(self) -> None:
        self._tray.hide()

    def _build_menu(self) -> None:
        menu = QMenu()
        show_act = menu.addAction("Show / Hide  (Ctrl+Space)")
        show_act.triggered.connect(self.show_requested.emit)
        menu.addSeparator()
        quit_act = menu.addAction("Quit J.A.R.V.I.S.")
        quit_act.triggered.connect(self.quit_requested.emit)
        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()