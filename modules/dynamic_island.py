"""
J.A.R.V.I.S. DYNAMIC ISLAND — HUD Overlay (PyQt6)
Supercharged with:
- 🚨 Smart Alert / Toast Banner (Auto-expands & collapses)
- 🎵 Windows Media Now Playing Marquee Text
- 📁 Drag & Drop AI Ingestion (Direct desktop file analysis)
- Waveform, Media (Image/GIF), and Webcam support.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys
import threading
import time
import urllib.request

# pyrefly: ignore [missing-import]
import cv2
from PyQt6.QtCore import (QEasingCurve, QPropertyAnimation, QRect, QSize, Qt,
                          QTimer)
from PyQt6.QtGui import (QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent,
                          QFont, QImage, QMovie, QPainter, QPainterPath, QPen,
                          QPixmap)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QApplication, QLabel, QLineEdit, QMenu,
                             QProgressBar, QVBoxLayout, QWidget)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("DynamicIsland")

PIPE_NAME = "jarvis_island_pipe"

def send_to_island(status: str, detail: str = "") -> None:
    """Send IPC message to the Dynamic Island HUD"""
    def _send():
        try:
            sock = QLocalSocket()
            sock.connectToServer(PIPE_NAME)
            if sock.waitForConnected(500):
                msg = f"{status}|{detail}" if detail else status
                sock.write(msg.encode("utf-8"))
                sock.waitForBytesWritten(500)
                sock.disconnectFromServer()
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

def send_toast_to_island(title: str, message: str, icon: str = "🔔") -> None:
    """Send Toast notification banner to Dynamic Island"""
    send_to_island("TOAST", f"{icon} {title}:::{message}")


class MarqueeLabel(QLabel):
    """Smooth horizontal pixel-scrolling label for now-playing media and alert titles"""
    def __init__(self, text: str = "J.A.R.V.I.S.", parent=None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self._offset = 0
        self._is_scrolling = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll_step)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.setStyleSheet("color: #00BFFF;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_text_marquee(self, text: str, force_marquee: bool = False) -> None:
        self._full_text = text
        self._offset = 0
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        if force_marquee or (text_w > (self.width() - 20) and text_w > 90):
            self._is_scrolling = True
            if not self._timer.isActive():
                self._timer.start(35)
        else:
            self._is_scrolling = False
            self._timer.stop()
            self.setText(text)
        self.update()

    def _scroll_step(self) -> None:
        self._offset += 1
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore
        if not self._is_scrolling or not self._full_text:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        painter.setPen(QColor(0, 191, 255))
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        spacing = 45
        cycle = text_w + spacing
        offset = self._offset % cycle
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        painter.drawText(-offset + 10, y, self._full_text)
        painter.drawText(cycle - offset + 10, y, self._full_text)


class DynamicIsland(QWidget):
    DEFAULT_W = 180
    DEFAULT_H = 36
    EXPANDED_W = 320
    EXPANDED_H = 120
    CAMERA_W = 320
    CAMERA_H = 280
    TOAST_W = 380
    TOAST_H = 64
    DROP_W = 260
    DROP_H = 50

    def __init__(self) -> None:
        super().__init__()
        self.is_expanded: bool = False
        self._anim: QPropertyAnimation | None = None
        self._target_w = self.DEFAULT_W
        self._target_h = self.DEFAULT_H
        
        self.cam = None
        self.cam_timer = QTimer(self)
        self.cam_timer.timeout.connect(self._update_camera)
        
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._check_heartbeat)
        self.heartbeat_timer.start(5000)  
        self._last_heartbeat = time.time()
        
        self._is_hovered = False
        self._current_detail = ""
        self._current_status = "STANDBY"

        # ── Smart Alert / Toast Variables ──
        self._is_toast: bool = False
        self._toast_title: str = ""
        self._toast_message: str = ""
        self._toast_icon: str = "🔔"
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._dismiss_toast)

        # ── Media Now Playing Variables ──
        self._now_playing_track: str = ""
        self._media_probe_timer = QTimer(self)
        self._media_probe_timer.timeout.connect(self._probe_windows_media)
        self._media_probe_timer.start(3000)

        # ── Drag & Drop Variables ──
        self._is_drag_over: bool = False
        self.setAcceptDrops(True)

        self._setup_flags()
        self._setup_ui()
        self._setup_ipc()

        QTimer.singleShot(100, self._initial_show)

    def _setup_flags(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _setup_ui(self) -> None:
        self.resize(self.DEFAULT_W, self.DEFAULT_H)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(2)

        # ── Main Label (Marquee enabled) ──
        self.label = MarqueeLabel("J.A.R.V.I.S.", self)
        layout.addWidget(self.label)

        # ── Toast Banner Widget (Hidden by default) ──
        self.toast_widget = QWidget(self)
        self.toast_widget.setVisible(False)
        toast_layout = QVBoxLayout(self.toast_widget)
        toast_layout.setContentsMargins(4, 2, 4, 2)
        toast_layout.setSpacing(2)

        self.toast_title_label = QLabel("🔔 แจ้งเตือน", self.toast_widget)
        self.toast_title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.toast_title_label.setStyleSheet("color: #00E5FF;")
        toast_layout.addWidget(self.toast_title_label)

        self.toast_msg_label = QLabel("", self.toast_widget)
        self.toast_msg_label.setFont(QFont("Segoe UI", 8))
        self.toast_msg_label.setStyleSheet("color: #F0F0F0;")
        self.toast_msg_label.setWordWrap(True)
        toast_layout.addWidget(self.toast_msg_label)

        layout.addWidget(self.toast_widget)

        # ── Progress Bar ──
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00BFFF;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.media_controls_widget = QWidget(self)
        self.media_controls_widget.setVisible(False)
        self.media_controls_widget.setFixedHeight(0)
        layout.addWidget(self.media_controls_widget)
        
        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("พิมพ์คำสั่งให้ JARVIS...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 20);
                color: white;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 8px;
                padding: 4px 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 191, 255, 100);
                background-color: rgba(255, 255, 255, 30);
            }
        """)
        self.chat_input.setVisible(False)
        self.chat_input.returnPressed.connect(self._send_chat_message)
        layout.addWidget(self.chat_input)
        
        self.media_label = QLabel(self)
        self.media_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_label.hide()
        layout.addWidget(self.media_label)

    def _setup_ipc(self) -> None:
        QLocalServer.removeServer(PIPE_NAME)
        self._pipe_server = QLocalServer(self)
        self._pipe_server.setSocketOptions(QLocalServer.SocketOption.WorldAccessOption)
        if self._pipe_server.listen(PIPE_NAME):
            self._pipe_server.newConnection.connect(self._on_pipe_message)

    def _initial_show(self) -> None:
        self._position_top_center(self.DEFAULT_W, self.DEFAULT_H)
        self.show()
        self.raise_()

    def _position_top_center(self, width: int, height: int) -> None:
        screen = QApplication.primaryScreen()
        if not screen: return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - width) // 2
        y = geo.y() + 4
        self.setGeometry(x, y, width, height)

    def paintEvent(self, event) -> None:  # type: ignore
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 18.0 
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), r, r)

        # ── Dynamic Border & Background Styles ──
        if getattr(self, '_is_drag_over', False):
            # Glowing dashed border during file drag-over
            pen = QPen(QColor(0, 229, 255, 230), 2.0, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.fillPath(path, QColor(0, 40, 70, 210))
        elif getattr(self, '_is_toast', False):
            # Glowing cyan/blue border for notification toasts
            pen = QPen(QColor(0, 229, 255, 190), 1.5)
            painter.setPen(pen)
            painter.fillPath(path, QColor(10, 18, 30, 220))
        else:
            # Standard HUD glassmorphism
            painter.setPen(QColor(0, 120, 255, 70))
            painter.fillPath(path, QColor(10, 10, 15, 160))
        
        # ── Status Indicator Dot ──
        if hasattr(self, '_current_status') and not getattr(self, '_is_toast', False):
            dot_color = None
            if self._current_status == "LISTENING":
                dot_color = QColor(255, 140, 0, 150)  
            elif self._current_status == "THINKING":
                dot_color = QColor(0, 191, 255, 150)  
            elif self._current_status == "SPEAKING":
                dot_color = QColor(50, 205, 50, 150)  
            elif self._current_status in ["ERROR", "ALERT", "DISCONNECTED"]:
                dot_color = QColor(255, 50, 50, 150)  
                
            if dot_color:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot_color)
                dot_size = 8
                dot_y = int((self.DEFAULT_H - dot_size) / 2)
                dot_x = self.width() - 20
                painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

    def _resize_smooth(self, target_w, target_h):
        if self._target_w == target_w and self._target_h == target_h: return
        self._target_w = target_w
        self._target_h = target_h
        
        screen = QApplication.primaryScreen()
        if not screen: return
        geo = screen.availableGeometry()
        target_x = geo.x() + (geo.width() - target_w) // 2
        target_y = geo.y() + 4

        if self._anim: self._anim.stop()
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(QRect(target_x, target_y, target_w, target_h))
        self._anim.start()

    def enterEvent(self, event):
        self._is_hovered = True
        if self._is_toast:
            self._toast_timer.stop()  # Pause dismissal while reading
        self._update_size_based_on_state()
        super().enterEvent(event)

    def leaveEvent(self, event):  # type: ignore
        self._is_hovered = False
        if self._is_toast:
            self._toast_timer.start(2000)  # Auto-close 2s after cursor leaves
        self._update_size_based_on_state()
        super().leaveEvent(event)
        
    def _update_size_based_on_state(self):
        if not self.media_label.isHidden():
            return
        elif self._is_toast:
            self._resize_smooth(self.TOAST_W, self.TOAST_H)
            return
        elif self._is_hovered:
            self.toast_widget.setVisible(False)
            self.label.setVisible(True)
            self.media_controls_widget.setVisible(True)
            self.chat_input.setVisible(True)
            self.chat_input.setFocus()
            self._resize_smooth(self.EXPANDED_W, self.EXPANDED_H)
        else:
            self.chat_input.setVisible(False)
            self.chat_input.clearFocus()
            if self._current_status not in ["MEDIA", "MUSIC"]:
                self.media_controls_widget.setVisible(False)
            else:
                self.media_controls_widget.setVisible(True)
            
            # Width adjustments for Now Playing track
            if self._now_playing_track:
                music_w = min(280, max(self.DEFAULT_W, len(f"🎵 {self._now_playing_track}") * 8 + 40))
                self._resize_smooth(music_w, self.DEFAULT_H)
            else:
                self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)

    # ──────────────────────────────────────────────────────────────────────────
    # 🚨 Smart Alert / Toast Banner Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def show_toast(self, title: str, message: str, icon: str = "🔔", duration: int = 4500) -> None:
        """Display a dynamic animated toast notification on the island"""
        self._is_toast = True
        self._toast_title = title
        self._toast_message = message
        self._toast_icon = icon

        self.toast_title_label.setText(f"{icon} {title}")
        self.toast_msg_label.setText(message)

        self.toast_widget.setVisible(True)
        self.label.setVisible(False)
        self.chat_input.setVisible(False)
        self.media_controls_widget.setVisible(False)

        self._resize_smooth(self.TOAST_W, self.TOAST_H)
        self._toast_timer.start(duration)
        self.update()

    def _dismiss_toast(self) -> None:
        """Smoothly collapse toast back to normal state"""
        self._is_toast = False
        self.toast_widget.setVisible(False)
        self.label.setVisible(True)
        self._update_size_based_on_state()
        self.update()

    # ──────────────────────────────────────────────────────────────────────────
    # 🎵 Windows Media & Now Playing Marquee Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def set_now_playing(self, track_title: str) -> None:
        """Update Now Playing track with marquee animation"""
        clean_track = track_title.strip()
        self._now_playing_track = clean_track
        if clean_track:
            display_text = f"🎵 {clean_track}"
            self.label.set_text_marquee(display_text, force_marquee=True)
            if not self._is_toast and not self._is_hovered and not self._is_drag_over:
                music_w = min(280, max(self.DEFAULT_W, len(display_text) * 8 + 40))
                self._resize_smooth(music_w, self.DEFAULT_H)
        else:
            self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
            if not self._is_toast and not self._is_hovered and not self._is_drag_over:
                self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)
        self.update()

    def _probe_windows_media(self) -> None:
        """Probe Windows desktop for active Spotify or YouTube playing tracks"""
        def _probe():
            try:
                import ctypes
                from ctypes import wintypes
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                GetWindowText = ctypes.windll.user32.GetWindowTextW
                IsWindowVisible = ctypes.windll.user32.IsWindowVisible

                found_track = ""
                def callback(hwnd, extra):
                    nonlocal found_track
                    if IsWindowVisible(hwnd):
                        length = GetWindowTextLength(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            GetWindowText(hwnd, buff, length + 1)
                            title = buff.value
                            if " - YouTube" in title:
                                found_track = title.replace(" - YouTube", "").strip()
                                return False
                            elif "Spotify" in title and " - " in title:
                                found_track = title.replace(" - Spotify", "").strip()
                                return False
                    return True

                EnumWindows(EnumWindowsProc(callback), 0)
                if found_track != self._now_playing_track:
                    QTimer.singleShot(0, lambda: self.set_now_playing(found_track))
            except Exception:
                pass
        threading.Thread(target=_probe, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # 📁 Drag & Drop AI Ingestion Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore
        if event.mimeData().hasUrls() or event.mimeData().hasText():  # type: ignore
            event.acceptProposedAction()
            self._is_drag_over = True
            self.toast_widget.setVisible(False)
            self.label.setVisible(True)
            self.label.set_text_marquee("📥 วางไฟล์เพื่อให้ J.A.R.V.I.S. วิเคราะห์", force_marquee=False)
            self._resize_smooth(self.DROP_W, self.DROP_H)
            self.update()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # type: ignore
        self._is_drag_over = False
        if self._now_playing_track:
            self.label.set_text_marquee(f"🎵 {self._now_playing_track}", force_marquee=True)
        else:
            self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
        self._update_size_based_on_state()
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore
        self._is_drag_over = False
        urls = event.mimeData().urls()  # type: ignore
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        
        if file_paths:
            target_file = file_paths[0]
            filename = os.path.basename(target_file)
            self.show_toast("📥 ได้รับไฟล์", f"กำลังส่ง {filename} ให้ JARVIS วิเคราะห์...", icon="📄", duration=5000)
            threading.Thread(
                target=self._ingest_and_analyze_file,
                args=(target_file,),
                daemon=True
            ).start()
        elif event.mimeData().hasText():  # type: ignore
            text = event.mimeData().text().strip()  # type: ignore
            self.show_toast("📥 ได้รับข้อความ", f"ประมวลผล: {text[:35]}...", icon="📝", duration=5000)
            threading.Thread(
                target=self._send_text_to_jarvis,
                args=(f"ช่วยสรุปและวิเคราะห์ข้อความนี้ให้เจ้านายหน่อยครับ:\n{text}",),
                daemon=True
            ).start()
        
        event.acceptProposedAction()
        self.update()

    def _ingest_and_analyze_file(self, file_path: str) -> None:
        """Send dropped file to JARVIS backend for AI inspection"""
        try:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            payload = {}
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                with open(file_path, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode("utf-8")
                payload = {
                    "message": f"เจ้านายได้ส่งรูปภาพ '{filename}' มาให้ทาง Dynamic Island ช่วยตรวจสอบและวิเคราะห์รายละเอียดของภาพนี้ให้เจ้านายครับ",
                    "image": b64_img
                }
            else:
                content = ""
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(3000)
                except Exception:
                    pass
                prompt = (
                    f"เจ้านายได้ส่งไฟล์ '{filename}' มาให้ทาง Dynamic Island HUD เพื่อให้คุณช่วยวิเคราะห์ "
                    f"เนื้อหาเบื้องต้นของไฟล์:\n\n{content}\n\n"
                    f"กรุณาสรุปประเด็นสำคัญ หรือแจ้งผลการตรวจสอบให้เจ้านายทราบครับ"
                )
                payload = {"message": prompt}
            
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:5050/chat",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                reply = res_json.get("response", "")
                if reply:
                    clean_reply = reply[:110].replace("\n", " ")
                    QTimer.singleShot(0, lambda: self.show_toast("🤖 JARVIS วิเคราะห์เสร็จสิ้น", clean_reply, icon="✨", duration=6500))
        except Exception as e:
            e_str = str(e)
            logger.error(f"Failed to ingest file via Dynamic Island: {e_str}")
            QTimer.singleShot(0, lambda: self.show_toast("⚠️ ข้อขัดข้อง", f"ไม่สามารถส่งไฟล์ให้ JARVIS: {e_str}", icon="⚠️", duration=4000))

    def _send_text_to_jarvis(self, prompt: str) -> None:
        """Send dropped text to JARVIS backend"""
        try:
            data_bytes = json.dumps({"message": prompt}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:5050/chat",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                reply = res_json.get("response", "")
                if reply:
                    clean_reply = reply[:110].replace("\n", " ")
                    QTimer.singleShot(0, lambda: self.show_toast("🤖 JARVIS สรุปผล", clean_reply, icon="✨", duration=6500))
        except Exception as e:
            logger.error(f"Failed to send dropped text: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Existing Chat & Camera Methods
    # ──────────────────────────────────────────────────────────────────────────
    def _send_chat_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        
        self.chat_input.clear()
        self.update_status("THINKING", "Processing text command...")
        
        def _post_text():
            try:
                data = json.dumps({"text": text}).encode('utf-8')
                req = urllib.request.Request(
                    "http://127.0.0.1:5050/api/voice/text",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5):
                    pass 
            except Exception as e:
                logger.error(f"Failed to send chat: {e}")
                
        threading.Thread(target=_post_text, daemon=True).start()

    def update_status(self, status: str, detail: str = "") -> None:
        QTimer.singleShot(0, lambda: self._apply_status(status, detail))

    def _apply_status(self, status: str, detail: str) -> None:
        if status == "CAMERA":
            if detail == "ON":
                self._start_camera()
            elif detail == "OFF":
                self._stop_camera()
            elif detail == "CAPTURE":
                self._capture_camera_frame()
            return
            
        if status == "VISIBILITY":
            if detail == "HIDE":
                self.hide()
            elif detail == "SHOW":
                self.show()
            return
            
        if status == "IMAGE" or status == "GIF":
            self._show_media(status, detail)
            return
            
        if status == "MEDIA":
            if detail == "CLEAR":
                self.media_label.hide()
                if self.media_label.movie():
                    self.media_label.movie().stop()  # type: ignore
                self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)
            return

        if not self._now_playing_track:
            self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
        self._current_status = status
        
        if status == "PROGRESS":
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)
            
        if status in ["MEDIA", "MUSIC"] or self._is_hovered:
            self.media_controls_widget.setVisible(True)
        else:
            self.media_controls_widget.setVisible(False)
            
        self._update_size_based_on_state()
        self.update()  
                    
    def _start_camera(self):
        if self.cam is None:
            self.cam = cv2.VideoCapture(0)
        if self.cam.isOpened():
            self.media_label.show()
            self._resize_smooth(self.CAMERA_W, self.CAMERA_H)
            self.cam_timer.start(30)
            
    def _stop_camera(self):
        self.cam_timer.stop()
        if self.cam is not None:
            self.cam.release()
            self.cam = None
        self.media_label.hide()
        self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
        self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)
        
    def _capture_camera_frame(self):
        was_off = self.cam is None or not self.cam.isOpened()
        if was_off:
            temp_cam = cv2.VideoCapture(0)
            ret, frame = temp_cam.read()
            temp_cam.release()
        else:
            ret, frame = self.cam.read()  # type: ignore
            
        if ret:
            cv2.imwrite("c:/JARVIS/temp_cam_capture.jpg", frame)

    def _update_camera(self):
        if self.cam is not None and self.cam.isOpened():
            ret, frame = self.cam.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)  # type: ignore
                scaled_pixmap = QPixmap.fromImage(qt_img).scaled(
                    self.CAMERA_W - 20, self.CAMERA_H - 40, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                self.media_label.setPixmap(scaled_pixmap)
                
    def _show_media(self, m_type: str, path: str):
        if not os.path.exists(path): return
        self.media_label.show()
        self._resize_smooth(self.CAMERA_W, self.CAMERA_H)
        if m_type == "GIF":
            movie = QMovie(path)
            movie.setScaledSize(QSize(self.CAMERA_W - 20, self.CAMERA_H - 40))
            self.media_label.setMovie(movie)
            movie.start()
        else:
            pixmap = QPixmap(path).scaled(
                self.CAMERA_W - 20, self.CAMERA_H - 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.media_label.setPixmap(pixmap)

    def contextMenuEvent(self, event):  # type: ignore
        """Right-click context menu to Hide or Exit Dynamic Island"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(15, 23, 42, 0.95);
                color: #E2E8F0;
                border: 1px solid rgba(0, 191, 255, 0.5);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 191, 255, 0.25);
                color: #38BDF8;
            }
        """)
        hide_action = menu.addAction("👁️ ซ่อนแถบ HUD (Hide)")
        hide_action.triggered.connect(self.hide)  # type: ignore
        
        quit_action = menu.addAction("❌ ปิด Dynamic Island (Exit)")
        quit_action.triggered.connect(QApplication.instance().quit)  # type: ignore
        
        menu.exec(event.globalPos())

    def _on_pipe_message(self) -> None:
        conn = self._pipe_server.nextPendingConnection()
        conn.readyRead.connect(lambda: self._read_pipe(conn))  # type: ignore

    def _read_pipe(self, conn: QLocalSocket) -> None:
        data = conn.readAll().data().decode("utf-8", errors="ignore").strip()
        conn.disconnectFromServer()
        if not data: return
        parts = data.split("|", 1)
        status = parts[0].strip()
        detail = parts[1].strip() if len(parts) > 1 else ""
        
        if status in ["QUIT", "EXIT", "CLOSE", "SHUTDOWN"]:
            logger.info("[ISLAND] Received exit command, shutting down.")
            QApplication.instance().quit()  # type: ignore
            return

        if status == "HIDE":
            self.hide()
            return

        if status == "SHOW":
            self.show()
            self.raise_()
            return

        if status == "HEARTBEAT":
            self._last_heartbeat = time.time()
            if self.label.text() == "DISCONNECTED":
                self.update_status("STANDBY", "")
            return

        if status == "TOAST":
            title = "แจ้งเตือน"
            msg = detail
            icon = "🔔"
            if ":::" in detail:
                subparts = detail.split(":::", 1)
                title = subparts[0].strip()
                msg = subparts[1].strip()
            self.show_toast(title, msg, icon=icon)
            return

        if status == "ALERT":
            self.show_toast("ระบบเตือนภัย", detail, icon="🚨", duration=5000)
            return

        if status in ["NOW_PLAYING", "MEDIA_TRACK"]:
            self.set_now_playing(detail)
            return

        if status == "MEDIA_CLEAR":
            self.set_now_playing("")
            return
            
        self._last_heartbeat = time.time()
        self.update_status(status, detail)
        
    def _check_heartbeat(self) -> None:
        if time.time() - getattr(self, '_last_heartbeat', time.time()) > 30.0:
            if self.label.text() != "DISCONNECTED":
                self.update_status("DISCONNECTED", "Core process unresponsive")


if __name__ == "__main__":
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
            while True:
                _t.sleep(2)
                alive = False
                try:
                    if _HAS_PSUTIL:
                        alive = _psutil.pid_exists(jarvis_pid)  # type: ignore
                    else:
                        import ctypes
                        handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, jarvis_pid)
                        alive = handle != 0
                        if handle: ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    alive = False
                if not alive:
                    import os as _os
                    _os._exit(0)
                    break
        _thr.Thread(target=_pid_watchdog, args=(args.jarvis_pid,), daemon=True).start()

    sys.exit(app.exec())