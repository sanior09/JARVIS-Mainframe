"""
window.py -- JARVIS HUD Frameless Always-On-Top Notch Window
State machine: HIDDEN -> SHOWING -> VISIBLE -> HIDING -> HIDDEN
Triggers: mouse hover on top 5px + Ctrl+Space hotkey
"""
from __future__ import annotations
import logging
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMainWindow
from state import CONFIG, WindowState
from webview import JarvisWebView

logger = logging.getLogger(__name__)


class HudWindow(QMainWindow):
    """
    Floating Overlay HUD window.
    HIDDEN y = -(hud_height), VISIBLE y = 0, width = full screen.
    """

    def __init__(self) -> None:
        super().__init__()
        self._state: WindowState = WindowState.HIDDEN
        self._screen = QApplication.primaryScreen()
        self._setup_window()
        self._setup_webview()
        self._setup_animation()
        self._setup_trigger_zone()

    def _setup_window(self) -> None:
        self.setWindowTitle(CONFIG.window_title)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        geo: QRect = self._screen.geometry()
        self.setGeometry(0, -CONFIG.hud_height, geo.width(), CONFIG.hud_height)

    def _setup_webview(self) -> None:
        self._webview = JarvisWebView(self)
        self.setCentralWidget(self._webview)

    def _setup_animation(self) -> None:
        self._animation = QPropertyAnimation(self, b"pos")
        self._animation.setDuration(CONFIG.animation_duration_ms)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_animation_finished)

    def _setup_trigger_zone(self) -> None:
        self._trigger_timer = QTimer(self)
        self._trigger_timer.setInterval(100)
        self._trigger_timer.timeout.connect(self._check_mouse_trigger)
        self._trigger_timer.start()

    # Public API
    def toggle(self) -> None:
        if self._state in (WindowState.HIDDEN, WindowState.HIDING):
            self.slide_down()
        else:
            self.slide_up()

    def slide_down(self) -> None:
        if self._state in (WindowState.VISIBLE, WindowState.SHOWING):
            return
        self._state = WindowState.SHOWING
        self.show()
        self._animate_to(0)

    def slide_up(self) -> None:
        if self._state in (WindowState.HIDDEN, WindowState.HIDING):
            return
        self._state = WindowState.HIDING
        self._animate_to(-CONFIG.hud_height)

    def load_backend(self) -> None:
        self._webview.load_backend()

    def show_offline(self) -> None:
        self._webview.show_offline()

    # Internal
    def _animate_to(self, y: int) -> None:
        geo = self.geometry()
        self._animation.stop()
        self._animation.setStartValue(QPoint(geo.x(), geo.y()))
        self._animation.setEndValue(QPoint(geo.x(), y))
        self._animation.start()

    def _on_animation_finished(self) -> None:
        if self._state == WindowState.SHOWING:
            self._state = WindowState.VISIBLE
        elif self._state == WindowState.HIDING:
            self._state = WindowState.HIDDEN
            self.hide()

    def _check_mouse_trigger(self) -> None:
        cursor_y: int = QCursor.pos().y()
        if cursor_y <= CONFIG.trigger_zone_height and self._state == WindowState.HIDDEN:
            self.slide_down()
        elif cursor_y >= CONFIG.hud_height + 40 and self._state == WindowState.VISIBLE:
            self.slide_up()

    def resizeEvent(self, event) -> None:
        geo = self._screen.geometry()
        if self.width() != geo.width():
            r = self.geometry()
            r.setWidth(geo.width())
            self.setGeometry(r)
        super().resizeEvent(event)