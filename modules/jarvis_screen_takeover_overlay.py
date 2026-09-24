"""
jarvis_screen_takeover_overlay.py
===================================
J.A.R.V.I.S. Screen Takeover HUD Overlay (PyQt6)

Features:
1. Fullscreen transparent glowing neon blue border around the entire screen.
2. Bottom-center floating status pill showing what JARVIS is doing in real-time.
3. Interactive Red Stop (⏹️) button to immediately abort computer control.
4. User interruption detection: Flashes a red warning banner & red glowing border
   when the user clicks the mouse or presses keys while JARVIS is in control.
5. IPC Server (QLocalServer: jarvis_takeover_pipe) for lightning-fast control.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import time
from ctypes import wintypes

from PyQt6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRect,
                          QRectF, QSize, Qt, QTimer, pyqtSignal)
from PyQt6.QtGui import (QColor, QCursor, QFont, QLinearGradient, QPainter,
                          QPen, QRadialGradient)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QApplication, QGraphicsDropShadowEffect,
                             QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)

# Setup Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [TAKEOVER] %(message)s")
logger = logging.getLogger("ScreenTakeover")

PIPE_NAME = "jarvis_takeover_pipe"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATUS_FILE = os.path.join(BASE_DIR, "data", "takeover_status.json")


def update_status_file(active: bool, stopped: bool, action: str = "") -> None:
    """Writes the current takeover state atomically for instant polling by JARVIS."""
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        temp_file = STATUS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({
                "active": active,
                "stopped": stopped,
                "action": action,
                "timestamp": time.time()
            }, f, ensure_ascii=False)
        os.replace(temp_file, STATUS_FILE)
    except Exception as e:
        logger.debug(f"Status file write failed: {e}")


class BorderGlowOverlay(QWidget):
    """
    Fullscreen transparent overlay rendering a high-tech glowing neon border.
    Has WA_TransparentForMouseEvents enabled so it NEVER blocks desktop interaction.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.border_thickness = 32
        self.glow_color = QColor(14, 75, 185)       # Deep Electric Royal Blue (from reference image)
        self.normal_color = QColor(14, 75, 185)     # Deep Electric Blue
        self.alert_color = QColor(220, 38, 38)      # Crimson Red
        self.target_color = self.normal_color
        self.current_alpha = 150
        self.pulse_direction = 1

        # Smooth breathing pulse timer
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(50)
        self.pulse_timer.timeout.connect(self._on_pulse)
        self.pulse_timer.start()

    def set_alert_mode(self, is_alert: bool) -> None:
        """Transitions border glow between Deep Electric Blue and Crimson Red."""
        self.glow_color = self.alert_color if is_alert else self.normal_color
        self.current_alpha = 180 if is_alert else 150
        self.update()

    def _on_pulse(self) -> None:
        """Gentle breathing pulse for the outer glow."""
        if self.glow_color == self.normal_color:
            self.current_alpha += self.pulse_direction * 1
            if self.current_alpha >= 165:
                self.current_alpha = 165
                self.pulse_direction = -1
            elif self.current_alpha <= 135:
                self.current_alpha = 135
                self.pulse_direction = 1
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = self.border_thickness

        c = QColor(self.glow_color)
        c.setAlpha(self.current_alpha)

        c_fade = QColor(self.glow_color)
        c_fade.setAlpha(0)

        # 1. Top Border Gradient
        grad_top = QLinearGradient(0, 0, 0, t)
        grad_top.setColorAt(0, c)
        grad_top.setColorAt(1, c_fade)
        painter.fillRect(0, 0, w, t, grad_top)

        # 2. Bottom Border Gradient
        grad_bottom = QLinearGradient(0, h, 0, h - t)
        grad_bottom.setColorAt(0, c)
        grad_bottom.setColorAt(1, c_fade)
        painter.fillRect(0, h - t, w, t, grad_bottom)

        # 3. Left Border Gradient
        grad_left = QLinearGradient(0, 0, t, 0)
        grad_left.setColorAt(0, c)
        grad_left.setColorAt(1, c_fade)
        painter.fillRect(0, 0, t, h, grad_left)

        # 4. Right Border Gradient
        grad_right = QLinearGradient(w, 0, w - t, 0)
        grad_right.setColorAt(0, c)
        grad_right.setColorAt(1, c_fade)
        painter.fillRect(w - t, 0, t, h, grad_right)

        # 5. Crisp Perimeter Accent Line
        pen = QPen(QColor(self.glow_color.red() + 20, min(255, self.glow_color.green() + 30), min(255, self.glow_color.blue() + 40)), 1.0)
        painter.setPen(pen)
        painter.drawRect(0, 0, w - 1, h - 1)


class CircularStopButton(QPushButton):
    """
    Circular dark coin button with centered, vivid red stop square matching reference.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("หยุดการควบคุม (Stop Control - Esc)")
        self.setStyleSheet("border: none; background: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Circle disc background
        if self.isDown():
            bg_color = QColor(26, 26, 26)
        elif self.underMouse():
            bg_color = QColor(48, 48, 48)
        else:
            bg_color = QColor(36, 36, 36)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawEllipse(QRectF(0, 0, 28, 28))

        # 2. Inner Red Stop Square (vivid scarlet with subtle corner rounding)
        if self.isDown():
            square_color = QColor(179, 0, 11)
        elif self.underMouse():
            square_color = QColor(255, 31, 45)
        else:
            square_color = QColor(229, 9, 20)

        painter.setBrush(square_color)
        painter.drawRoundedRect(QRectF(8.5, 8.5, 11.0, 11.0), 2.0, 2.0)
        painter.end()


class StatusPillWidget(QWidget):
    """
    Bottom-center floating HUD pill matching the user reference screenshot.
    Compact, dark charcoal capsule (252x48) with clean muted status label and circular stop button.
    """

    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setFixedSize(252, 48)
        self._init_ui()

    def _init_ui(self) -> None:
        # Container with dark charcoal capsule styling
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: rgba(20, 20, 20, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 24px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(20, 4, 10, 4)
        layout.setSpacing(10)

        # Action / Status Label (Clean muted gray text, regular weight, no dot)
        self.label_status = QLabel("Taking screenshot...", self)
        self.label_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        self.label_status.setStyleSheet("color: #a6a6a6; background: transparent; border: none;")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label_status, 1)

        # Circular Stop Button with Red Square [■]
        self.btn_stop = CircularStopButton(self)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.btn_stop)

    def set_action_text(self, text: str) -> None:
        """Updates the action status text smoothly."""
        display_text = text if len(text) <= 32 else text[:29] + "..."
        self.label_status.setText(display_text)

    def set_alert_mode(self, is_alert: bool) -> None:
        """Toggles status styling between normal and alert mode."""
        if is_alert:
            self.container.setStyleSheet("""
                QWidget#container {
                    background-color: rgba(28, 12, 16, 0.96);
                    border: 1px solid rgba(239, 68, 68, 0.75);
                    border-radius: 24px;
                }
            """)
        else:
            self.container.setStyleSheet("""
                QWidget#container {
                    background-color: rgba(20, 20, 20, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 24px;
                }
            """)

    def _on_stop_clicked(self) -> None:
        logger.info("[STOP BUTTON] User clicked Stop button.")
        self.label_status.setText("Stopping computer control...")
        self.btn_stop.setEnabled(False)
        self.stop_requested.emit()


class InterruptionWarningToast(QWidget):
    """
    Floating Red Warning Toast displayed when the user clicks or types
    while JARVIS is actively in control of the screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setFixedSize(540, 48)
        self._init_ui()

    def _init_ui(self) -> None:
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(36, 10, 16, 0.95);
                border: 1.5px solid rgba(255, 51, 68, 0.85);
                border-radius: 24px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(255, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.container.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(18, 6, 18, 6)

        self.label = QLabel("⚠️ JARVIS กำลังคุมจออยู่! (กดปุ่มหยุด ■ หรือ ESC เพื่อยกเลิก)", self)
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.label.setStyleSheet("color: #ff4d5a; background: transparent; border: none;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)


class TakeoverOverlayController(QWidget):
    """
    Main Orchestrator for the Screen Takeover Overlay System.
    Manages the Fullscreen Glow, Status Pill, Warning Toast,
    Mouse Click Detector, and IPC Server.
    """

    def __init__(self):
        super().__init__()
        self.is_active = False
        self.is_stopped = False
        self.suppress_clicks_until = 0.0

        # Primary screen dimensions
        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()

        # 1. Fullscreen Border Glow
        self.glow_overlay = BorderGlowOverlay()
        self.glow_overlay.setGeometry(screen)

        # 2. Bottom Status Pill Widget
        self.pill_widget = StatusPillWidget()
        pill_x = (self.screen_w - self.pill_widget.width()) // 2
        pill_y = self.screen_h - 76
        self.pill_widget.move(pill_x, pill_y)
        self.pill_widget.stop_requested.connect(self.on_user_stop)

        # 3. Interruption Warning Toast
        self.warning_toast = InterruptionWarningToast()
        toast_x = (self.screen_w - self.warning_toast.width()) // 2
        toast_y = self.screen_h - 150
        self.warning_toast.move(toast_x, toast_y)

        # Auto-hide timer for warning toast
        self.warning_hide_timer = QTimer(self)
        self.warning_hide_timer.setSingleShot(True)
        self.warning_hide_timer.setInterval(2400)
        self.warning_hide_timer.timeout.connect(self._hide_warning)

        # Input activity monitor timer (checking left click & ESC)
        self.input_check_timer = QTimer(self)
        self.input_check_timer.setInterval(35)
        self.input_check_timer.timeout.connect(self._check_user_inputs)
        self.input_check_timer.start()

        # Setup IPC Server
        self._init_ipc_server()

        # Clean initial state
        update_status_file(active=False, stopped=False)

    def _init_ipc_server(self) -> None:
        """Initializes QLocalServer for high-speed IPC communication."""
        QLocalServer.removeServer(PIPE_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_ipc_connection)
        if self.server.listen(PIPE_NAME):
            logger.info(f"Takeover Overlay IPC Server listening on '{PIPE_NAME}'")
        else:
            logger.error(f"Failed to start IPC Server on '{PIPE_NAME}'")

    def _on_new_ipc_connection(self) -> None:
        client = self.server.nextPendingConnection()
        if not client:
            return

        def _handle_read():
            data = client.readAll().data().decode("utf-8", errors="ignore").strip()
            if not data:
                return

            parts = data.split("|", 1)
            cmd = parts[0]
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "START":
                self.start_takeover(arg or "Taking screenshot...")
                client.write(b"OK\n")
            elif cmd == "UPDATE":
                self.update_action(arg)
                client.write(b"OK\n")
            elif cmd == "AGENT_CLICK":
                # Suppress click detector for 400ms when JARVIS clicks
                self.suppress_clicks_until = time.time() + 0.40
                client.write(b"OK\n")
            elif cmd == "STOP":
                self.stop_takeover()
                client.write(b"OK\n")
            elif cmd == "STATUS":
                resp = "STOPPED" if self.is_stopped else ("ACTIVE" if self.is_active else "IDLE")
                client.write(f"{resp}\n".encode("utf-8"))

            client.flush()
            client.disconnectFromServer()

        client.readyRead.connect(_handle_read)

    def start_takeover(self, initial_action: str = "Taking screenshot...") -> None:
        """Activates the full takeover overlay."""
        self.is_active = True
        self.is_stopped = False
        self.suppress_clicks_until = time.time() + 1.20

        self.pill_widget.btn_stop.setEnabled(True)
        self.pill_widget.set_action_text(initial_action)
        self.pill_widget.set_alert_mode(False)
        self.glow_overlay.set_alert_mode(False)

        self.glow_overlay.show()
        self.glow_overlay.raise_()
        self.pill_widget.show()
        self.pill_widget.raise_()
        self.warning_toast.hide()

        try:
            hwnd_glow = int(self.glow_overlay.winId())
            hwnd_pill = int(self.pill_widget.winId())
            ctypes.windll.user32.SetWindowPos(hwnd_glow, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
            ctypes.windll.user32.SetWindowPos(hwnd_pill, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
        except Exception:
            pass

        update_status_file(active=True, stopped=False, action=initial_action)
        logger.info(f"Screen Takeover ACTIVE: '{initial_action}'")

    def update_action(self, action_text: str) -> None:
        """Updates the current action text shown on the pill."""
        if self.is_active:
            self.pill_widget.set_action_text(action_text)
            update_status_file(active=True, stopped=False, action=action_text)

    def stop_takeover(self) -> None:
        """Deactivates and hides all overlay components."""
        self.is_active = False
        self.is_stopped = False
        self.glow_overlay.hide()
        self.pill_widget.hide()
        self.warning_toast.hide()
        self.warning_hide_timer.stop()

        update_status_file(active=False, stopped=False, action="")
        logger.info("Screen Takeover DEACTIVATED.")

    def on_user_stop(self) -> None:
        """User pressed Stop button or hit ESC."""
        logger.warning("[ABORT] User commanded emergency stop of computer control!")
        self.is_stopped = True
        self.is_active = False
        update_status_file(active=False, stopped=True, action="Stopped by user")

        # Fade out smoothly without overwriting stopped state
        QTimer.singleShot(600, self._hide_all_windows)

    def _hide_all_windows(self) -> None:
        self.glow_overlay.hide()
        self.pill_widget.hide()
        self.warning_toast.hide()
        self.warning_hide_timer.stop()
        if "--test" in sys.argv:
            QApplication.instance().quit()

    def trigger_interruption_warning(self) -> None:
        """User clicked while JARVIS was controlling: flashes red warning & border."""
        if not self.is_active or self.is_stopped:
            return

        logger.info("[USER INTERRUPTION] User clicked while JARVIS is controlling! Triggering alert.")
        self.glow_overlay.set_alert_mode(True)
        self.pill_widget.set_alert_mode(True)
        self.warning_toast.show()

        # Restart 2.4s timer to revert back to normal cyan glow
        self.warning_hide_timer.start()

    def _hide_warning(self) -> None:
        """Restores normal cyan glow after warning interval."""
        if self.is_active:
            self.glow_overlay.set_alert_mode(False)
            self.pill_widget.set_alert_mode(False)
        self.warning_toast.hide()

    def _check_user_inputs(self) -> None:
        """Polls Windows API for left clicks and ESC key."""
        if not self.is_active or self.is_stopped:
            return

        # 1. Check ESC key (0x1B) for emergency instant abort
        if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
            self.on_user_stop()
            return

        # 2. Check Left Mouse Button (0x01)
        if ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
            # Check if this click was generated by JARVIS
            if time.time() < self.suppress_clicks_until:
                return

            cursor_pos = QCursor.pos()
            # Check if cursor is over the Stop button or pill
            pill_rect = self.pill_widget.geometry()
            if pill_rect.contains(cursor_pos):
                # User is clicking inside pill / on the Stop button
                return

            # In test preview mode, do NOT close on screen clicks! Only close on ESC or Stop [■] button
            if "--test" in sys.argv:
                return

            # User clicked somewhere on the screen! Instantly yield control back to the user
            logger.info("[USER OVERRIDE] User clicked on screen. Instantly yielding control back to user!")
            self.on_user_stop()
            return


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    controller = TakeoverOverlayController()

    if "--test" in sys.argv:
        controller.start_takeover("Taking screenshot...")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
