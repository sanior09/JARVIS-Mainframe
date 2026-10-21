"""
J.A.R.V.I.S. DYNAMIC ISLAND — HUD Overlay (PyQt6)
Supercharged with:
- 🚨 Smart Alert / Toast Banner (Auto-expands & collapses)
- 🤖 Coucou / Notch Buddy Animated Mascot & Agent Watcher
- 📁 Drag & Drop AI Ingestion (Direct desktop file analysis)
- Waveform, Image/GIF Preview, and Webcam support.
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import sys
import threading
import time
import urllib.request

try:
    import cv2
except ImportError:
    cv2 = None
from PyQt6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt,
                          QTimer)
from PyQt6.QtGui import (QBrush, QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent,
                          QFont, QImage, QLinearGradient, QMovie, QPainter, QPainterPath, QPen,
                          QPixmap, QRadialGradient)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu,
                             QProgressBar, QPushButton, QVBoxLayout, QWidget, QWidgetAction)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("DynamicIsland")

def _global_exception_handler(exctype, value, tb):
    logger.critical("UNCAUGHT EXCEPTION in Dynamic Island", exc_info=(exctype, value, tb))

sys.excepthook = _global_exception_handler

PIPE_NAME = "jarvis_island_pipe"
HUD_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hud_config.json")

def load_hud_config() -> dict:
    """Load persistent HUD configuration (such as selected mascot skin)"""
    try:
        if os.path.exists(HUD_CONFIG_PATH):
            with open(HUD_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"[HUD_CONFIG] Load error: {e}")
    return {}

def save_hud_config(data: dict) -> None:
    """Save persistent HUD configuration to data/hud_config.json"""
    try:
        os.makedirs(os.path.dirname(HUD_CONFIG_PATH), exist_ok=True)
        cur = load_hud_config()
        cur.update(data)
        with open(HUD_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cur, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[HUD_CONFIG] Save error: {e}")

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

def send_buddy_mood(mood: str) -> None:
    """Change Notch Buddy mood: idle, happy, thinking, alert, success"""
    send_to_island("BUDDY_MOOD", mood)

def send_buddy_skin(skin: str) -> None:
    """Change Notch Buddy skin: mochi, antigravity, codex, cursor, jarvis, gemini"""
    send_to_island("BUDDY_SKIN", skin)

def send_agent_event(agent: str, status: str, detail: str, buttons: str = "terminal_ok") -> None:
    """Send Agent Watcher event: e.g. Codex, finished, 48 tests passed, terminal_ok or allow_deny"""
    send_to_island("AGENT_EVENT", f"{agent}:::{status}:::{detail}:::{buttons}")

def send_usage_gauge(groq: int = -1, gemini: int = -1, ollama: int = -1, streak_badge: str = "") -> None:
    """Send API usage percentage gauges for JARVIS models (Groq, Gemini, Ollama)"""
    if groq < 0 or gemini < 0 or ollama < 0:
        try:
            from modules.ai_quota_tracker import get_gauge_values, get_quota_stats
            groq, gemini, ollama = get_gauge_values()
            if not streak_badge:
                streak_badge = get_quota_stats().get("streak_badge", "")
        except Exception:
            groq, gemini, ollama = (0, 0, 0)
    detail = f"{groq}:::{gemini}:::{ollama}"
    if streak_badge:
        detail += f":::{streak_badge}"
    send_to_island("USAGE_GAUGE", detail)

def send_live_diff(added: int = 48, removed: int = 12, summary: str = "") -> None:
    """Send live diff statistics: +48 -12 lines"""
    send_to_island("LIVE_DIFF", f"{added}:::{removed}:::{summary}")

def send_attach_file(file_path: str) -> None:
    """Send IPC command to attach a file to Dynamic Island chat input"""
    send_to_island("ATTACH_FILE", file_path)



class BuddyWidget(QWidget):
    """
    Animated Notch Buddy (Coucou / Mochi style):
    - Smooth vector rendering with QPainter
    - Blinking eyes animation timer
    - Expression moods: idle, happy, thinking, alert, success
    - Character skins: mochi, antigravity, codex, cursor, jarvis, gemini
    """
    SKINS = {
        "mochi": {
            "body_top": QColor("#FFFDF5"),
            "body_bot": QColor("#FFE4B5"),
            "border": QColor("#F6D8A8"),
            "eyes": QColor("#2D2B2A"),
            "cheeks": QColor(255, 182, 193, 170),
            "glow": QColor(255, 235, 180, 80),
            "name": "Mochi"
        },
        "antigravity": {
            "body_top": QColor("#C084FC"),
            "body_bot": QColor("#7E22CE"),
            "border": QColor("#A855F7"),
            "eyes": QColor("#FFFFFF"),
            "cheeks": QColor(244, 114, 182, 190),
            "glow": QColor(168, 85, 247, 140),
            "name": "Antigravity"
        },
        "codex": {
            "body_top": QColor("#34D399"),
            "body_bot": QColor("#059669"),
            "border": QColor("#10B981"),
            "eyes": QColor("#064E3B"),
            "cheeks": QColor(110, 231, 183, 140),
            "glow": QColor(16, 185, 129, 130),
            "name": "Codex"
        },
        "cursor": {
            "body_top": QColor("#F8FAFC"),
            "body_bot": QColor("#94A3B8"),
            "border": QColor("#CBD5E1"),
            "eyes": QColor("#0F172A"),
            "cheeks": QColor(203, 213, 225, 120),
            "glow": QColor(255, 255, 255, 90),
            "name": "Cursor"
        },
        "jarvis": {
            "body_top": QColor("#0EA5E9"),
            "body_bot": QColor("#0369A1"),
            "border": QColor("#00E5FF"),
            "eyes": QColor("#F0FDFA"),
            "cheeks": QColor(0, 229, 255, 120),
            "glow": QColor(0, 229, 255, 180),
            "name": "JARVIS Arc"
        },
        "gemini": {
            "body_top": QColor("#60A5FA"),
            "body_bot": QColor("#818CF8"),
            "border": QColor("#3B82F6"),
            "eyes": QColor("#1E3A8A"),
            "cheeks": QColor(192, 132, 252, 150),
            "glow": QColor(96, 165, 250, 130),
            "name": "Gemini"
        },
        "mark6": {
            "body_top": QColor("#DC2626"),        # Metallic Hot-rod Red
            "body_bot": QColor("#7F1D1D"),        # Deep Crimson Titanium
            "border": QColor("#F59E0B"),          # Gold-Titanium alloy border
            "eyes": QColor("#E0F2FE"),            # Arc-reactor luminous visor
            "cheeks": QColor(245, 158, 11, 220),  # Polished Gold cheek accents
            "glow": QColor(220, 38, 38, 160),     # Stark repulsor crimson energy halo
            "name": "Iron Man Mark VI"
        }
    }

    def __init__(self, parent=None, size: int = 24):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.buddy_size = size
        self.skin = "jarvis"  # Default fallback
        self.mood = "idle"
        self._is_blinking = False
        self.on_skin_changed = None
        self.on_buddy_clicked = None
        
        # Blink timers
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._trigger_blink)
        self._blink_timer.start(3500)
        
        self._unblink_timer = QTimer(self)
        self._unblink_timer.setSingleShot(True)
        self._unblink_timer.timeout.connect(self._unblink)

    def mousePressEvent(self, event):
        """Ignore click events so left-clicking does not change skin"""
        event.ignore()

    def cycle_skin(self) -> str:
        """Cycle to the next skin in SKINS catalog"""
        skins_list = list(self.SKINS.keys())
        try:
            curr_idx = skins_list.index(self.skin)
            next_skin = skins_list[(curr_idx + 1) % len(skins_list)]
        except ValueError:
            next_skin = skins_list[0]
        self.set_skin(next_skin, save=True)
        return next_skin

    def set_mood(self, mood: str):
        self.mood = mood.lower().strip()
        self.update()

    def set_skin(self, skin: str, save: bool = True):
        s_key = skin.lower().strip()
        if s_key in self.SKINS:
            self.skin = s_key
            self.update()
            if save:
                save_hud_config({"buddy_skin": s_key})
            if callable(self.on_skin_changed):
                self.on_skin_changed(s_key)

    def _trigger_blink(self):
        if self.mood in ["idle", "thinking"]:
            self._is_blinking = True
            self.update()
            self._unblink_timer.start(180)

    def _unblink(self):
        self._is_blinking = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        skin_cfg = self.SKINS.get(self.skin, self.SKINS["mochi"])
        w = float(self.width())
        h = float(self.height())
        
        # ─────────────────────────────────────────────────────────────
        # 1. MOCHI: Kawaii Japanese Cat Mascot (Cat Ears & Kitty Mouth)
        # ─────────────────────────────────────────────────────────────
        if self.skin == "mochi":
            # Glow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)
            
            # Cat Ears (Left & Right 3D ears on top)
            ear_pen = QPen(skin_cfg["border"], 1.0)
            ear_brush = skin_cfg["body_top"]
            
            p_ear_l = QPainterPath()
            p_ear_l.moveTo(w * 0.16, h * 0.28)
            p_ear_l.lineTo(w * 0.12, 1.0)
            p_ear_l.lineTo(w * 0.38, h * 0.12)
            p_ear_l.closeSubpath()
            painter.setPen(ear_pen)
            painter.setBrush(ear_brush)
            painter.drawPath(p_ear_l)
            
            p_in_l = QPainterPath()
            p_in_l.moveTo(w * 0.18, h * 0.24)
            p_in_l.lineTo(w * 0.16, h * 0.08)
            p_in_l.lineTo(w * 0.32, h * 0.15)
            p_in_l.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 182, 193, 200))
            painter.drawPath(p_in_l)
            
            p_ear_r = QPainterPath()
            p_ear_r.moveTo(w * 0.84, h * 0.28)
            p_ear_r.lineTo(w * 0.88, 1.0)
            p_ear_r.lineTo(w * 0.62, h * 0.12)
            p_ear_r.closeSubpath()
            painter.setPen(ear_pen)
            painter.setBrush(ear_brush)
            painter.drawPath(p_ear_r)
            
            p_in_r = QPainterPath()
            p_in_r.moveTo(w * 0.82, h * 0.24)
            p_in_r.lineTo(w * 0.84, h * 0.08)
            p_in_r.lineTo(w * 0.68, h * 0.15)
            p_in_r.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 182, 193, 200))
            painter.drawPath(p_in_r)

            # Body Gradient
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, skin_cfg["body_top"])
            grad.setColorAt(1.0, skin_cfg["body_bot"])
            painter.setPen(QPen(skin_cfg["border"], 1.0))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, h * 0.10, w - 4, h * 0.88), 7, 7)

            # Rosy Cheeks
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["cheeks"])
            painter.drawEllipse(QRectF(w * 0.12, h * 0.58, w * 0.18, h * 0.12))
            painter.drawEllipse(QRectF(w * 0.70, h * 0.58, w * 0.18, h * 0.12))

            # Kitty Mouth 'ω'
            p_mouth = QPainterPath()
            p_mouth.moveTo(w * 0.42, h * 0.62)
            p_mouth.quadTo(w * 0.46, h * 0.68, w * 0.50, h * 0.63)
            p_mouth.quadTo(w * 0.54, h * 0.68, w * 0.58, h * 0.62)
            painter.setPen(QPen(QColor("#5C4033"), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(p_mouth)

        # ─────────────────────────────────────────────────────────────
        # 2. ANTIGRAVITY: Cosmic Nebula Space Mage (Orbital Halo & Star Eyes)
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "antigravity":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 7, 7)

            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#9333EA"))
            grad.setColorAt(0.5, QColor("#581C87"))
            grad.setColorAt(1.0, QColor("#2E1065"))
            painter.setPen(QPen(skin_cfg["border"], 1.1))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 7, 7)

            # Orbital Planetary Ring across head
            painter.setPen(QPen(QColor(232, 121, 249, 210), 1.1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(-w * 0.1, -h * 0.05, w * 1.2, h * 0.45), 30 * 16, 120 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 250))
            painter.drawEllipse(QRectF(w * 0.76, h * 0.10, 3.0, 3.0))

            # Cosmic Core Energy in chest
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(232, 121, 249, 180))
            painter.drawEllipse(QRectF(w * 0.44, h * 0.68, w * 0.12, w * 0.12))
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawEllipse(QRectF(w * 0.47, h * 0.71, w * 0.06, w * 0.06))

        # ─────────────────────────────────────────────────────────────
        # 3. CODEX: Cyber Matrix Hacker (Terminal Window & `>_` Prompt)
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "codex":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor("#022C22"))
            grad.setColorAt(1.0, QColor("#064E3B"))
            painter.setPen(QPen(skin_cfg["border"], 1.1))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 6, 6)

            # Terminal Title Bar Dots
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#EF4444"))
            painter.drawEllipse(QRectF(w * 0.16, 4.0, 2.5, 2.5))
            painter.setBrush(QColor("#F59E0B"))
            painter.drawEllipse(QRectF(w * 0.28, 4.0, 2.5, 2.5))
            painter.setBrush(QColor("#10B981"))
            painter.drawEllipse(QRectF(w * 0.40, 4.0, 2.5, 2.5))
            
            painter.setPen(QPen(QColor(16, 185, 129, 90), 0.8))
            painter.drawLine(int(w * 0.12), int(8.0), int(w * 0.88), int(8.0))

            # Bottom terminal data tick
            painter.setPen(QPen(QColor(52, 211, 153, 140), 1.0))
            painter.drawLine(int(w * 0.35), int(h * 0.75), int(w * 0.65), int(h * 0.75))

        # ─────────────────────────────────────────────────────────────
        # 4. CURSOR: Minimalist Developer Monolith (3D Cursor Pointer Arrow)
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "cursor":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor("#1E293B"))
            grad.setColorAt(1.0, QColor("#0F172A"))
            painter.setPen(QPen(skin_cfg["border"], 1.1))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 6, 6)

            # Iconic 3D Cursor Arrow Badge on forehead
            arrow = QPainterPath()
            ax = w * 0.50
            ay = h * 0.16
            arrow.moveTo(ax, ay)
            arrow.lineTo(ax - w * 0.14, ay + h * 0.20)
            arrow.lineTo(ax - w * 0.04, ay + h * 0.18)
            arrow.lineTo(ax - w * 0.08, ay + h * 0.28)
            arrow.lineTo(ax - w * 0.02, ay + h * 0.29)
            arrow.lineTo(ax + w * 0.04, ay + h * 0.19)
            arrow.lineTo(ax + w * 0.12, ay + h * 0.21)
            arrow.closeSubpath()
            painter.setPen(QPen(QColor("#0F172A"), 0.8))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawPath(arrow)

        # ─────────────────────────────────────────────────────────────
        # 5. JARVIS: Stark Hologram AI Interface Ring (Official Marvel UI)
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "jarvis":
            cx = w / 2.0
            cy = h / 2.0
            r_max = min(w, h) / 2.0
            
            # Subtle Outer Glow
            painter.setPen(Qt.PenStyle.NoPen)
            glow_grad = QRadialGradient(cx, cy, r_max)
            glow_grad.setColorAt(0.0, QColor(0, 229, 255, 60))
            glow_grad.setColorAt(0.7, QColor(0, 229, 255, 25))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(glow_grad)
            painter.drawEllipse(QRectF(1, 1, w - 2, h - 2))
            
            # Dark Cybernetic Monolith Base
            bg_grad = QLinearGradient(0, 0, 0, h)
            bg_grad.setColorAt(0.0, QColor("#031024"))
            bg_grad.setColorAt(0.5, QColor("#051B38"))
            bg_grad.setColorAt(1.0, QColor("#020B18"))
            painter.setPen(QPen(QColor(0, 229, 255, 120), 1.0))
            painter.setBrush(bg_grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 7, 7)
            
            # Outer Segmented Collar Arc (Cyan)
            r_outer = r_max * 0.82
            box_outer = QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
            pen_outer = QPen(QColor("#00E5FF"), max(1.2, w * 0.045))
            pen_outer.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_outer)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw segmented arc sections with gaps (Stark HUD collar)
            painter.drawArc(box_outer, 45 * 16, 75 * 16)    # Top-right
            painter.drawArc(box_outer, 135 * 16, 75 * 16)   # Top-left
            painter.drawArc(box_outer, 230 * 16, 60 * 16)   # Bottom-left
            painter.drawArc(box_outer, 305 * 16, 75 * 16)   # Bottom-right
            
            # Outer Tech Bracket Tabs at 4 cardinal points
            tab_len = max(1.5, w * 0.05)
            painter.setPen(QPen(QColor(0, 229, 255, 200), max(1.0, w * 0.035)))
            painter.drawLine(QPointF(cx, cy - r_outer - tab_len), QPointF(cx, cy - r_outer + tab_len * 0.5))
            painter.drawLine(QPointF(cx, cy + r_outer - tab_len * 0.5), QPointF(cx, cy + r_outer + tab_len))
            painter.drawLine(QPointF(cx - r_outer - tab_len, cy), QPointF(cx - r_outer + tab_len * 0.5, cy))
            painter.drawLine(QPointF(cx + r_outer - tab_len * 0.5, cy), QPointF(cx + r_outer + tab_len, cy))

            # Dial Gauge Tick Marks (Middle Telemetry Track)
            r_ticks = r_max * 0.68
            num_ticks = 16
            pen_tick = QPen(QColor(56, 189, 248, 140), max(0.8, w * 0.025))
            painter.setPen(pen_tick)
            for i in range(num_ticks):
                angle = i * (2 * math.pi / num_ticks)
                x1 = cx + (r_ticks - w * 0.03) * math.cos(angle)
                y1 = cy + (r_ticks - w * 0.03) * math.sin(angle)
                x2 = cx + (r_ticks + w * 0.03) * math.cos(angle)
                y2 = cy + (r_ticks + w * 0.03) * math.sin(angle)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                
            # Middle Ring Track
            r_mid = r_max * 0.54
            box_mid = QRectF(cx - r_mid, cy - r_mid, r_mid * 2, r_mid * 2)
            painter.setPen(QPen(QColor(2, 132, 199, 130), max(0.9, w * 0.028)))
            painter.drawEllipse(box_mid)
            
            # SIGNATURE AMBER/GOLDEN ARC on the Left flank (Iconic Stark J.A.R.V.I.S. visual)
            pen_amber = QPen(QColor("#F59E0B"), max(1.5, w * 0.05))
            pen_amber.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_amber)
            painter.drawArc(box_mid, 135 * 16, 100 * 16)
            
            # Amber Telemetry Dots on Top rim
            dot_r = max(1.0, w * 0.03)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FBBF24"))
            for deg in [70, 90, 110]:
                rad = math.radians(deg)
                dx = cx + r_mid * math.cos(rad)
                dy = cy - r_mid * math.sin(rad)
                painter.drawEllipse(QPointF(dx, dy), dot_r, dot_r)
                
            # Inner Cyan Ring
            r_in = r_max * 0.38
            box_in = QRectF(cx - r_in, cy - r_in, r_in * 2, r_in * 2)
            painter.setPen(QPen(QColor("#38BDF8"), max(1.0, w * 0.03)))
            painter.setBrush(QColor(3, 105, 161, 90))
            painter.drawEllipse(box_in)

            # Reticle Crosshair Lines (Subtle)
            painter.setPen(QPen(QColor(0, 229, 255, 150), max(0.8, w * 0.02)))
            painter.drawLine(QPointF(cx - r_in, cy), QPointF(cx - r_in * 0.4, cy))
            painter.drawLine(QPointF(cx + r_in * 0.4, cy), QPointF(cx + r_in, cy))
            painter.drawLine(QPointF(cx, cy - r_in), QPointF(cx, cy - r_in * 0.4))
            painter.drawLine(QPointF(cx, cy + r_in * 0.4), QPointF(cx, cy + r_in))

            # Center Luminous Reactor Core (Interacts with blinking & moods)
            if self._is_blinking:
                painter.setPen(QPen(QColor(0, 229, 255, 240), max(1.2, w * 0.04)))
                painter.drawLine(QPointF(cx - r_in * 0.5, cy), QPointF(cx + r_in * 0.5, cy))
            elif self.mood == "alert":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(239, 68, 68, 220))
                painter.drawEllipse(QPointF(cx, cy), r_in * 0.6, r_in * 0.6)
                painter.setBrush(QColor(255, 255, 255, 255))
                painter.drawEllipse(QPointF(cx, cy), r_in * 0.3, r_in * 0.3)
            elif self.mood == "happy":
                p_hap = QPainterPath()
                p_hap.moveTo(cx - r_in * 0.4, cy + r_in * 0.2)
                p_hap.quadTo(cx, cy - r_in * 0.4, cx + r_in * 0.4, cy + r_in * 0.2)
                painter.setPen(QPen(QColor("#00E5FF"), max(1.2, w * 0.04)))
                painter.drawPath(p_hap)
            else: # idle radiant reactor core
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 229, 255, 200))
                painter.drawEllipse(QPointF(cx, cy), r_in * 0.45, r_in * 0.45)
                painter.setBrush(QColor(255, 255, 255, 255))
                painter.drawEllipse(QPointF(cx, cy), r_in * 0.22, r_in * 0.22)

        # ─────────────────────────────────────────────────────────────
        # 6. GEMINI: Google AI Twin Star (Iconic ✦ Sparkle Star)
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "gemini":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 7, 7)

            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#2563EB"))
            grad.setColorAt(1.0, QColor("#7C3AED"))
            painter.setPen(QPen(skin_cfg["border"], 1.1))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 7, 7)

            # Iconic Google Gemini 4-Point Sparkle Star on forehead
            sw = w * 0.14
            sh = h * 0.16
            cx = w * 0.50
            cy = h * 0.22
            spark_path = QPainterPath()
            spark_path.moveTo(cx, cy - sh)
            spark_path.quadTo(cx, cy, cx + sw, cy)
            spark_path.quadTo(cx, cy, cx, cy + sh)
            spark_path.quadTo(cx, cy, cx - sw, cy)
            spark_path.quadTo(cx, cy, cx, cy - sh)
            spark_path.closeSubpath()
            painter.setPen(QPen(QColor(192, 132, 252, 200), 0.8))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawPath(spark_path)

            # Twin constellation dots in chest
            painter.setPen(QPen(QColor(255, 255, 255, 180), 0.8))
            painter.drawLine(int(w * 0.38), int(h * 0.74), int(w * 0.62), int(h * 0.74))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QRectF(w * 0.38 - 1.5, h * 0.74 - 1.5, 3.0, 3.0))
            painter.drawEllipse(QRectF(w * 0.62 - 1.5, h * 0.74 - 1.5, 3.0, 3.0))

        # ─────────────────────────────────────────────────────────────
        # 7. MARK6: Iron Man Mark VI Armor (KEPT AS REQUESTED "อันนี้เท่ละ")
        # ─────────────────────────────────────────────────────────────
        elif self.skin == "mark6":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(skin_cfg["glow"])
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 7, 7)

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor('#DC2626'))
            grad.setColorAt(1.0, QColor('#7F1D1D'))
            painter.setPen(QPen(skin_cfg["border"], 1.2))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 7, 7)

            # Golden Faceplate Forehead Brow Plate
            face_plate = QPainterPath()
            face_plate.moveTo(w * 0.22, 2.0)
            face_plate.lineTo(w * 0.78, 2.0)
            face_plate.lineTo(w * 0.72, h * 0.28)
            face_plate.lineTo(w * 0.50, h * 0.35)
            face_plate.lineTo(w * 0.28, h * 0.28)
            face_plate.closeSubpath()
            face_grad = QLinearGradient(0, 0, 0, h * 0.35)
            face_grad.setColorAt(0.0, QColor(251, 191, 36, 240))
            face_grad.setColorAt(1.0, QColor(217, 119, 6, 230))
            painter.setPen(QPen(QColor(245, 158, 11, 230), max(1.0, w * 0.03)))
            painter.setBrush(face_grad)
            painter.drawPath(face_plate)

            # Cheeks / Cheekplates
            cheek_w = max(3.5, w * 0.12)
            cheek_h = max(2.5, h * 0.14)
            painter.setPen(QPen(QColor(245, 158, 11, 230), 1.0))
            painter.setBrush(QColor(217, 119, 6, 190))
            painter.drawRoundedRect(QRectF(2.5, h * 0.52, cheek_w, cheek_h), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(w - 2.5 - cheek_w, h * 0.52, cheek_w, cheek_h), 1.5, 1.5)

            # Triangular Arc Reactor
            tri_cx = w / 2.0
            tri_cy = h * 0.70
            tri_w = w * 0.34
            tri_h = h * 0.28

            tri_outer = QPainterPath()
            tri_outer.moveTo(tri_cx - tri_w / 2.0, tri_cy - tri_h / 2.0)
            tri_outer.lineTo(tri_cx + tri_w / 2.0, tri_cy - tri_h / 2.0)
            tri_outer.lineTo(tri_cx, tri_cy + tri_h / 2.0)
            tri_outer.closeSubpath()

            painter.setPen(QPen(QColor(245, 158, 11, 250), max(1.0, w * 0.04)))
            painter.setBrush(QColor(146, 64, 14, 230))
            painter.drawPath(tri_outer)

            core_w = tri_w * 0.65
            core_h = tri_h * 0.65
            tri_core = QPainterPath()
            tri_core.moveTo(tri_cx - core_w / 2.0, tri_cy - core_h / 2.0 + (tri_h * 0.08))
            tri_core.lineTo(tri_cx + core_w / 2.0, tri_cy - core_h / 2.0 + (tri_h * 0.08))
            tri_core.lineTo(tri_cx, tri_cy + core_h / 2.0)
            tri_core.closeSubpath()

            painter.setPen(QPen(QColor(56, 189, 248, 255), max(0.8, w * 0.025)))
            painter.setBrush(QColor(240, 253, 250, 255))
            painter.drawPath(tri_core)

        # ─────────────────────────────────────────────────────────────
        # EYES & EMOTIONAL EXPRESSIONS
        # ─────────────────────────────────────────────────────────────
        if self.skin == "jarvis":
            # Handled internally as holographic Stark AI Ring Core
            return

        eye_color = skin_cfg["eyes"]
        painter.setBrush(eye_color)
        painter.setPen(QPen(eye_color, 1.2))
        
        eye_y = h * 0.44 if self.skin == "mark6" else (h * 0.48 if self.skin == "gemini" else h * 0.44)
        eye_left_x = w * 0.32
        eye_right_x = w * 0.68
        
        if self._is_blinking:
            # Closed eyes (horizontal curves)
            painter.drawLine(int(eye_left_x - 2.5), int(eye_y), int(eye_left_x + 2.5), int(eye_y))
            painter.drawLine(int(eye_right_x - 2.5), int(eye_y), int(eye_right_x + 2.5), int(eye_y))
        elif self.mood == "happy":
            # Upward curves ^ ^
            p = QPainterPath()
            p.moveTo(eye_left_x - 2.5, eye_y + 1)
            p.quadTo(eye_left_x, eye_y - 2.5, eye_left_x + 2.5, eye_y + 1)
            painter.drawPath(p)
            
            p2 = QPainterPath()
            p2.moveTo(eye_right_x - 2.5, eye_y + 1)
            p2.quadTo(eye_right_x, eye_y - 2.5, eye_right_x + 2.5, eye_y + 1)
            painter.drawPath(p2)
        elif self.mood == "thinking":
            # Looking up & sideways
            painter.drawEllipse(QRectF(eye_left_x - 1.5, eye_y - 2.0, 3.2, 3.2))
            painter.drawEllipse(QRectF(eye_right_x - 1.5, eye_y - 2.0, 3.2, 3.2))
        elif self.mood == "alert":
            # Big surprised eyes O O
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(eye_color, 1.5))
            painter.drawEllipse(QRectF(eye_left_x - 2.2, eye_y - 2.5, 4.4, 5.0))
            painter.drawEllipse(QRectF(eye_right_x - 2.2, eye_y - 2.5, 4.4, 5.0))
            painter.setBrush(eye_color)
            painter.drawEllipse(QRectF(eye_left_x - 1.0, eye_y - 1.0, 2.0, 2.0))
            painter.drawEllipse(QRectF(eye_right_x - 1.0, eye_y - 1.0, 2.0, 2.0))
        elif self.mood == "success":
            # Wink (left wink ^, right normal •)
            p = QPainterPath()
            p.moveTo(eye_left_x - 2.5, eye_y + 1)
            p.quadTo(eye_left_x, eye_y - 2.5, eye_left_x + 2.5, eye_y + 1)
            painter.drawPath(p)
            
            painter.drawEllipse(QRectF(eye_right_x - 1.5, eye_y - 1.5, 3.0, 3.0))
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.drawEllipse(QRectF(eye_right_x - 0.5, eye_y - 1.2, 1.2, 1.2))
        else: # idle signature eyes per character
            if self.skin == "mark6":
                # Razor-sharp Iron Man Visor Eyes
                slit_w = max(2.5, w * 0.11)
                slit_h = max(1.2, h * 0.05)
                aura_thick = max(1.8, w * 0.07)
                core_thick = max(1.0, w * 0.035)

                painter.setPen(QPen(QColor(56, 189, 248, 190), aura_thick))
                painter.drawLine(int(eye_left_x - slit_w), int(eye_y - slit_h * 0.6), int(eye_left_x + slit_w), int(eye_y + slit_h))
                painter.drawLine(int(eye_right_x - slit_w), int(eye_y + slit_h), int(eye_right_x + slit_w), int(eye_y - slit_h * 0.6))
                
                painter.setPen(QPen(QColor(255, 255, 255, 255), core_thick))
                painter.drawLine(int(eye_left_x - slit_w * 0.9), int(eye_y - slit_h * 0.6), int(eye_left_x + slit_w * 0.9), int(eye_y + slit_h))
                painter.drawLine(int(eye_right_x - slit_w * 0.9), int(eye_y + slit_h), int(eye_right_x + slit_w * 0.9), int(eye_y - slit_h * 0.6))
            elif self.skin == "codex":
                # Terminal Prompt `>` and `_`
                painter.setPen(QPen(QColor("#34D399"), 1.8))
                p_caret = QPainterPath()
                p_caret.moveTo(w * 0.24, h * 0.38)
                p_caret.lineTo(w * 0.36, h * 0.46)
                p_caret.lineTo(w * 0.24, h * 0.54)
                painter.drawPath(p_caret)
                painter.drawLine(int(w * 0.62), int(h * 0.54), int(w * 0.78), int(h * 0.54))
            elif self.skin == "cursor":
                # OLED Horizontal Dual Slit Eyes
                painter.setPen(QPen(QColor("#38BDF8"), 2.2))
                painter.drawLine(int(w * 0.24), int(h * 0.56), int(w * 0.40), int(h * 0.56))
                painter.drawLine(int(w * 0.60), int(h * 0.56), int(w * 0.76), int(h * 0.56))
                painter.setPen(QPen(QColor("#FFFFFF"), 1.2))
                painter.drawLine(int(w * 0.26), int(h * 0.56), int(w * 0.38), int(h * 0.56))
                painter.drawLine(int(w * 0.62), int(h * 0.56), int(w * 0.74), int(h * 0.56))
            elif self.skin == "antigravity":
                # Star Sparkle Eyes (✦ ✦)
                def draw_star(scx, scy, sr):
                    p = QPainterPath()
                    p.moveTo(scx, scy - sr)
                    p.quadTo(scx, scy, scx + sr, scy)
                    p.quadTo(scx, scy, scx, scy + sr)
                    p.quadTo(scx, scy, scx - sr, scy)
                    p.quadTo(scx, scy, scx, scy - sr)
                    p.closeSubpath()
                    return p
                star_r = w * 0.13
                painter.setPen(QPen(QColor(244, 114, 182, 190), 0.8))
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawPath(draw_star(eye_left_x, eye_y, star_r))
                painter.drawPath(draw_star(eye_right_x, eye_y, star_r))
            elif self.skin == "gemini":
                # Luminous Twin AI Sparks
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#F0FDFA"))
                painter.drawEllipse(QRectF(eye_left_x - 3.0, eye_y - 3.0, 6.0, 6.0))
                painter.drawEllipse(QRectF(eye_right_x - 3.0, eye_y - 3.0, 6.0, 6.0))
                painter.setBrush(QColor(96, 165, 250, 220))
                painter.drawEllipse(QRectF(eye_left_x - 1.2, eye_y - 1.2, 2.4, 2.4))
                painter.drawEllipse(QRectF(eye_right_x - 1.2, eye_y - 1.2, 2.4, 2.4))
            elif self.skin == "mochi":
                # Large Anime Cat Catchlight Eyes
                eye_r = w * 0.10
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#241C1A"))
                painter.drawEllipse(QRectF(eye_left_x - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2))
                painter.drawEllipse(QRectF(eye_right_x - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2))
                painter.setBrush(QColor(255, 255, 255, 240))
                painter.drawEllipse(QRectF(eye_left_x - eye_r * 0.5, eye_y - eye_r * 0.6, eye_r * 0.8, eye_r * 0.8))
                painter.drawEllipse(QRectF(eye_right_x - eye_r * 0.5, eye_y - eye_r * 0.6, eye_r * 0.8, eye_r * 0.8))
            else:
                painter.drawEllipse(QRectF(eye_left_x - 1.5, eye_y - 1.5, 3.0, 3.0))
                painter.drawEllipse(QRectF(eye_right_x - 1.5, eye_y - 1.5, 3.0, 3.0))
                painter.setBrush(QColor(255, 255, 255, 220))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(eye_left_x - 0.8, eye_y - 1.2, 1.2, 1.2))
                painter.drawEllipse(QRectF(eye_right_x - 0.8, eye_y - 1.2, 1.2, 1.2))


class SkinButton(QPushButton):
    """Visual mascot character tile for interactive skin palette"""
    def __init__(self, skin_key: str, is_active: bool = False, on_click=None, parent=None):
        super().__init__(parent)
        self.skin_key = skin_key
        self.is_active = is_active
        self.setFixedSize(38, 38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(BuddyWidget.SKINS.get(skin_key, {}).get("name", skin_key.capitalize()))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buddy = BuddyWidget(self, size=24)
        self.buddy.set_skin(skin_key, save=False)
        self.buddy.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.buddy)
        
        self._update_style()
        if on_click:
            self.clicked.connect(lambda: on_click(self.skin_key))

    def set_active(self, active: bool):
        self.is_active = active
        self._update_style()

    def _update_style(self):
        if self.is_active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 229, 255, 0.22);
                    border: 2px solid #00E5FF;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 229, 255, 0.35);
                    border: 2px solid #38BDF8;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.16);
                    border: 1.5px solid rgba(0, 229, 255, 0.7);
                }
            """)


class SkinPaletteWidget(QWidget):
    """Visual character palette shelf showing all mascot skins as live avatars"""
    def __init__(self, current_skin: str, on_select, parent=None):
        super().__init__(parent)
        self.on_select = on_select
        self.buttons = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 8)
        main_layout.setSpacing(6)
        
        title_label = QLabel("🎨 เลือกสกินมาสคอต (Select Mascot)", self)
        title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #38BDF8; background: transparent; padding: 0px;")
        main_layout.addWidget(title_label)
        
        row_widget = QWidget(self)
        row_widget.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(6)
        
        for s_key in BuddyWidget.SKINS.keys():
            is_active = (s_key == current_skin)
            btn = SkinButton(s_key, is_active=is_active, on_click=self._handle_click, parent=row_widget)
            self.buttons[s_key] = btn
            row_layout.addWidget(btn)
            
        main_layout.addWidget(row_widget)
        self.setStyleSheet("background: transparent;")

    def _handle_click(self, skin_key: str):
        for k, b in self.buttons.items():
            b.set_active(k == skin_key)
        if callable(self.on_select):
            self.on_select(skin_key)


class AgentEventWidget(QWidget):
    """
    Card for Agent Watcher & Allow/Deny Actions:
    - Agent Badge (e.g. 🟢 Codex finished, 🟣 Antigravity request)
    - Description: 'Pushed to main · 48 tests passed'
    - Buttons: [Open terminal] [OK] or [Allow] [Deny]
    """
    def __init__(self, on_action_callback=None, parent=None):
        super().__init__(parent)
        self.on_action = on_action_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        # Header Row
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.agent_badge = QLabel("🟢 Codex finished")
        self.agent_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.agent_badge.setStyleSheet("color: #34D399;")
        header_row.addWidget(self.agent_badge)
        header_row.addStretch()
        layout.addLayout(header_row)
        
        # Message text
        self.msg_label = QLabel("Pushed to main · 48 tests passed")
        self.msg_label.setFont(QFont("Segoe UI", 8))
        self.msg_label.setStyleSheet("color: #E2E8F0;")
        self.msg_label.setWordWrap(True)
        layout.addWidget(self.msg_label)
        
        # Button Row
        self.btn_row = QHBoxLayout()
        self.btn_row.setSpacing(8)
        
        self.btn_primary = QPushButton("Open terminal")
        self.btn_primary.setFixedHeight(24)
        self.btn_primary.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.25);
                color: #A7F3D0;
                border: 1px solid rgba(16, 185, 129, 0.6);
                border-radius: 5px;
                padding: 2px 10px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.45);
                color: #FFFFFF;
                border: 1px solid #10B981;
            }
        """)
        self.btn_primary.clicked.connect(lambda: self._handle_click("primary"))
        
        self.btn_secondary = QPushButton("OK")
        self.btn_secondary.setFixedHeight(24)
        self.btn_secondary.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: #F1F5F9;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 5px;
                padding: 2px 10px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                color: #FFFFFF;
            }
        """)
        self.btn_secondary.clicked.connect(lambda: self._handle_click("secondary"))
        
        self.btn_row.addWidget(self.btn_primary)
        self.btn_row.addWidget(self.btn_secondary)
        layout.addLayout(self.btn_row)

    def _handle_click(self, btn_type: str):
        if callable(self.on_action):
            self.on_action(btn_type)

    def set_event(self, agent: str, status: str, detail: str, buttons: str = "terminal_ok"):
        agent_clean = agent.strip()
        if "security" in agent_clean.lower() or "gate" in agent_clean.lower():
            color = "#00E5FF"
            icon = "🛡️"
        elif "antigravity" in agent_clean.lower():
            color = "#A855F7"
            icon = "🟣"
        elif "codex" in agent_clean.lower():
            color = "#10B981"
            icon = "🟢"
        else:
            color = "#38BDF8"
            icon = "⚡"
        
        self.agent_badge.setText(f"{icon} {agent_clean} {status}")
        self.agent_badge.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.msg_label.setText(detail)
        
        if buttons == "allow_deny":
            self.btn_primary.setText("Allow")
            self.btn_primary.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.35);
                    color: #A7F3D0;
                    border: 1px solid #10B981;
                    border-radius: 5px;
                    padding: 2px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #10B981;
                    color: white;
                }
            """)
            self.btn_secondary.setText("Deny")
            self.btn_secondary.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.25);
                    color: #FCA5A5;
                    border: 1px solid rgba(239, 68, 68, 0.6);
                    border-radius: 5px;
                    padding: 2px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #EF4444;
                    color: white;
                }
            """)
        else:
            self.btn_primary.setText("Open terminal")
            self.btn_primary.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.25);
                    color: #A7F3D0;
                    border: 1px solid rgba(16, 185, 129, 0.6);
                    border-radius: 5px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.45);
                    color: #FFFFFF;
                }
            """)
            self.btn_secondary.setText("OK")
            self.btn_secondary.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.12);
                    color: #F1F5F9;
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 5px;
                    padding: 2px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.25);
                }
            """)


class UsageGaugeWidget(QWidget):
    """Telemetry Gauges for Claude / Codex Plan Usage and GitHub Streak"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        # Header Row
        title_row = QHBoxLayout()
        title_lbl = QLabel("📊 JARVIS AI Brain Quota")
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38BDF8;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        self.streak_badge = QLabel("Core Online · Standby")
        self.streak_badge.setFont(QFont("Segoe UI", 8))
        self.streak_badge.setStyleSheet("color: #A7F3D0; background: rgba(16, 185, 129, 0.2); border-radius: 4px; padding: 1px 6px;")
        title_row.addWidget(self.streak_badge)
        layout.addLayout(title_row)
        
        # Bars
        self.groq_bar, self.groq_lbl = self._create_bar_row("Groq (120B)", "#F59E0B", 35)
        self.gemini_bar, self.gemini_lbl = self._create_bar_row("Google Gemini", "#38BDF8", 12)
        self.ollama_bar, self.ollama_lbl = self._create_bar_row("Ollama (Offline)", "#10B981", 0)
        
        layout.addLayout(self.groq_bar)
        layout.addLayout(self.gemini_bar)
        layout.addLayout(self.ollama_bar)

    def _create_bar_row(self, name: str, color: str, initial_val: int):
        row = QHBoxLayout()
        row.setSpacing(6)
        
        lbl = QLabel(name)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color: #94A3B8;")
        lbl.setFixedWidth(115)
        
        bar = QProgressBar()
        bar.setFixedHeight(5)
        bar.setTextVisible(False)
        bar.setRange(0, 100)
        bar.setValue(initial_val)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 20);
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        
        val_lbl = QLabel(f"{initial_val}%")
        val_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color: {color};")
        val_lbl.setFixedWidth(35)
        
        row.addWidget(lbl)
        row.addWidget(bar)
        row.addWidget(val_lbl)
        return row, (bar, val_lbl)

    def mousePressEvent(self, event):
        # Click directly on quota gauge to dismiss
        if hasattr(self.parent(), '_dismiss_gauge'):
            self.parent()._dismiss_gauge()
        super().mousePressEvent(event)

    def update_values(self, groq: int, gemini: int, ollama: int, streak_badge: str = ""):
        self.groq_lbl[0].setValue(groq)
        self.groq_lbl[1].setText(f"{groq}%")
        self.gemini_lbl[0].setValue(gemini)
        self.gemini_lbl[1].setText(f"{gemini}%")
        self.ollama_lbl[0].setValue(ollama)
        self.ollama_lbl[1].setText(f"{ollama}%")
        if streak_badge:
            self.streak_badge.setText(streak_badge)


class LiveDiffWidget(QWidget):
    """Badge for Live Diff (+48 -12 lines)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)
        
        self.add_lbl = QLabel("+48")
        self.add_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.add_lbl.setStyleSheet("color: #34D399;")
        
        self.sub_lbl = QLabel("-12")
        self.sub_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.sub_lbl.setStyleSheet("color: #F87171;")
        
        self.info_lbl = QLabel("lines changed")
        self.info_lbl.setFont(QFont("Segoe UI", 8))
        self.info_lbl.setStyleSheet("color: #94A3B8;")
        
        layout.addWidget(self.add_lbl)
        layout.addWidget(self.sub_lbl)
        layout.addWidget(self.info_lbl)
        layout.addStretch()

    def set_diff(self, added: int, removed: int, note: str = ""):
        self.add_lbl.setText(f"+{added}")
        self.sub_lbl.setText(f"-{removed}")
        self.info_lbl.setText(note if note else "lines changed")


class MarqueeLabel(QLabel):
    """Smooth horizontal pixel-scrolling label for status and alert titles"""
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


class ChatInputField(QLineEdit):
    """
    Sleek droppable QLineEdit that supports:
    - Direct file drag-and-drop onto the text input
    - Visual hover/drag feedback
    - Clean glassmorphism text styling
    """
    def __init__(self, on_file_dropped=None, parent=None):
        super().__init__(parent)
        self.on_file_dropped = on_file_dropped
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(0, 229, 255, 30);
                    color: white;
                    border: 1.5px dashed #00E5FF;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-family: 'Segoe UI';
                    font-size: 12px;
                }
            """)
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._reset_style()
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._reset_style()
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if paths and callable(self.on_file_dropped):
                self.on_file_dropped(paths[0])
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _reset_style(self):
        self.setStyleSheet("""
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
                border: 1px solid rgba(0, 191, 255, 120);
                background-color: rgba(255, 255, 255, 30);
            }
        """)


class CircularIconButton(QPushButton):
    """
    Precision vector-rendered circular button for pixel-perfect centering.
    Eliminates all font metric / glyph ascent/descent misalignments.
    Supports 'plus' and 'send' vector icons.
    """
    def __init__(self, icon_type: str = "plus", parent=None):
        super().__init__(parent)
        self.icon_type = icon_type  # "plus" or "send"
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_hovered = False
        self._is_pressed = False

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        r = (min(w, h) - 2.0) / 2.0

        # Colors based on state
        if self.icon_type == "send" and self._is_hovered:
            bg_color = QColor(0, 229, 255, 235)
            border_color = QColor(0, 229, 255)
            icon_color = QColor(10, 15, 26) # Dark sleek icon on cyan glow
        elif self._is_pressed:
            bg_color = QColor(0, 229, 255, 140)
            border_color = QColor(0, 229, 255)
            icon_color = QColor(255, 255, 255)
        elif self._is_hovered:
            bg_color = QColor(0, 229, 255, 80)
            border_color = QColor(0, 229, 255, 240)
            icon_color = QColor(255, 255, 255)
        else:
            bg_color = QColor(0, 229, 255, 35)
            border_color = QColor(0, 229, 255, 120)
            icon_color = QColor(0, 229, 255)

        # Draw circle background
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2.0, r * 2.0))

        # Precision Vector Icons (100% Mathematically Centered)
        if self.icon_type == "plus":
            pen = QPen(icon_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            line_len = 5.0
            # Horizontal bar
            painter.drawLine(QPointF(cx - line_len, cy), QPointF(cx + line_len, cy))
            # Vertical bar
            painter.drawLine(QPointF(cx, cy - line_len), QPointF(cx, cy + line_len))

        elif self.icon_type == "send":
            # Right-pointing sleek stealth arrow/dart
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(icon_color)
            
            tip = QPointF(cx + 4.5, cy)
            top = QPointF(cx - 4.5, cy - 4.8)
            crease = QPointF(cx - 1.8, cy)
            bot = QPointF(cx - 4.5, cy + 4.8)

            path = QPainterPath()
            path.moveTo(tip)
            path.lineTo(top)
            path.lineTo(crease)
            path.closeSubpath()

            path2 = QPainterPath()
            path2.moveTo(tip)
            path2.lineTo(crease)
            path2.lineTo(bot)
            path2.closeSubpath()

            painter.drawPath(path)
            painter.drawPath(path2)


class DynamicIsland(QWidget):
    DEFAULT_W = 210
    DEFAULT_H = 38
    EXPANDED_W = 365
    EXPANDED_H = 130
    CAMERA_W = 320
    CAMERA_H = 280
    TOAST_W = 380
    TOAST_H = 68
    AGENT_W = 410
    AGENT_H = 96
    GAUGE_W = 390
    GAUGE_H = 108
    DIFF_W = 280
    DIFF_H = 42
    DROP_W = 260
    DROP_H = 50

    def __init__(self) -> None:
        super().__init__()
        self.is_expanded: bool = False
        self._anim: QPropertyAnimation | None = None
        self._target_w = self.DEFAULT_W
        self._target_h = self.DEFAULT_H
        self._attached_file_path: str | None = None
        
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

        # ── Coucou Agent Watcher & Gauges Variables ──
        self._is_agent_event: bool = False
        self._is_gauge: bool = False
        self._is_diff: bool = False

        self._agent_timer = QTimer(self)
        self._agent_timer.setSingleShot(True)
        self._agent_timer.timeout.connect(self._dismiss_agent_event)

        self._gauge_timer = QTimer(self)
        self._gauge_timer.setSingleShot(True)
        self._gauge_timer.timeout.connect(self._dismiss_gauge)

        self._diff_timer = QTimer(self)
        self._diff_timer.setSingleShot(True)
        self._diff_timer.timeout.connect(self._dismiss_diff)

        # ── Media Display Auto-Dismiss Timer ──
        self._media_timer = QTimer(self)
        self._media_timer.setSingleShot(True)
        self._media_timer.timeout.connect(self._dismiss_media)


        # ── Drag & Drop Variables ──
        self._is_drag_over: bool = False
        self.setAcceptDrops(True)
        
        # ── Push-To-Talk Variables ──
        self._is_recording = False
        self._audio_frames = []

        self._setup_flags()
        self._setup_ui()
        self._setup_ipc()
        self._initial_show()

    def _setup_flags(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _setup_ui(self) -> None:
        self.resize(self.DEFAULT_W, self.DEFAULT_H)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(3)

        # ── Top Bar (Notch Buddy + Marquee Label) ──
        self.top_bar_widget = QWidget(self)
        top_bar_layout = QHBoxLayout(self.top_bar_widget)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(6)

        self.buddy_widget = BuddyWidget(self.top_bar_widget, size=22)
        # Load saved persistent skin from config
        saved_skin = load_hud_config().get("buddy_skin", "jarvis")
        if saved_skin in self.buddy_widget.SKINS:
            self.buddy_widget.set_skin(saved_skin, save=False)
        self.buddy_widget.on_skin_changed = self._on_buddy_skin_changed
        top_bar_layout.addWidget(self.buddy_widget)

        self.label = MarqueeLabel("J.A.R.V.I.S.", self.top_bar_widget)
        top_bar_layout.addWidget(self.label, 1)

        layout.addWidget(self.top_bar_widget)

        # ── Agent Event Widget (Coucou Agent Watcher) ──
        self.agent_event_widget = AgentEventWidget(on_action_callback=self._handle_agent_action, parent=self)
        self.agent_event_widget.setVisible(False)
        layout.addWidget(self.agent_event_widget)

        # ── Plan Usage & CI Streak Gauge Widget ──
        self.usage_gauge_widget = UsageGaugeWidget(self)
        self.usage_gauge_widget.setVisible(False)
        layout.addWidget(self.usage_gauge_widget)

        # ── Live Diff Badge Widget ──
        self.live_diff_widget = LiveDiffWidget(self)
        self.live_diff_widget.setVisible(False)
        layout.addWidget(self.live_diff_widget)

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
        
        # ── Quick AI Model Pills (Coucou Style) ──
        self.model_pills_widget = QWidget(self)
        pills_layout = QHBoxLayout(self.model_pills_widget)
        pills_layout.setContentsMargins(0, 2, 0, 2)
        pills_layout.setSpacing(6)
        pills_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pills_layout.addStretch()
        
        self.model_buttons = {}
        self.models_data = [
            ("Groq 120B", "#F59E0B", "groq"),
            ("Gemini", "#38BDF8", "gemini"),
            ("Ollama Local", "#10B981", "ollama")
        ]
        for m_name, m_col, m_key in self.models_data:
            btn = QPushButton(m_name, self.model_pills_widget)
            btn.setFixedHeight(20)
            btn.clicked.connect(lambda checked, mk=m_key, mn=m_name: self._on_select_model(mn, mk))
            self.model_buttons[m_key] = (btn, m_name, m_col)
            pills_layout.addWidget(btn)

        # ── Quota HUD Trigger Button ──
        self.btn_quota = QPushButton("📊 Quota", self.model_pills_widget)
        self.btn_quota.setFixedHeight(20)
        self.btn_quota.setToolTip("คลิกเพื่อดูโควต้าและสถิติการใช้งาน AI วันนี้")
        self.btn_quota.setStyleSheet("""
            QPushButton {
                background: rgba(0, 229, 255, 0.12);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 0 6px;
            }
            QPushButton:hover {
                background: rgba(0, 229, 255, 0.3);
                border: 1px solid #38BDF8;
                color: #FFFFFF;
            }
        """)
        self.btn_quota.clicked.connect(self._toggle_quota_gauge)
        pills_layout.addWidget(self.btn_quota)
        pills_layout.addStretch()

        # Initialize pills active UI state from persistent config
        initial_eng = "groq"
        try:
            from jarvis_core.ai_router import get_active_model
            initial_eng = get_active_model()
        except Exception:
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cache_file = os.path.join(base_dir, "system_cache", "active_model.json")
                if os.path.exists(cache_file):
                    with open(cache_file, "r", encoding="utf-8") as f:
                        initial_eng = json.load(f).get("primary_engine", "groq")
            except Exception:
                pass
        self._active_engine = initial_eng
        self._update_model_pills_ui(initial_eng)

        self.model_pills_widget.setVisible(False)
        layout.addWidget(self.model_pills_widget)

        # ── Attachment Badge (Hidden by default) ──
        self.attachment_badge_widget = QWidget(self)
        self.attachment_badge_widget.setFixedHeight(22)
        self.attachment_badge_widget.setVisible(False)
        self.attachment_badge_widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 229, 255, 0.12);
                border: 1px solid rgba(0, 229, 255, 0.35);
                border-radius: 6px;
            }
        """)
        attach_badge_layout = QHBoxLayout(self.attachment_badge_widget)
        attach_badge_layout.setContentsMargins(8, 0, 6, 0)
        attach_badge_layout.setSpacing(6)

        self.attachment_file_label = QLabel("📎 ไม่มีไฟล์", self.attachment_badge_widget)
        self.attachment_file_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.attachment_file_label.setStyleSheet("color: #00E5FF; border: none; background: transparent;")
        attach_badge_layout.addWidget(self.attachment_file_label, 1)

        self.btn_remove_attach = QPushButton("✕", self.attachment_badge_widget)
        self.btn_remove_attach.setFixedSize(16, 16)
        self.btn_remove_attach.setToolTip("ยกเลิกไฟล์แนบ")
        self.btn_remove_attach.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.15);
                color: #CBD5E1;
                border: none;
                border-radius: 8px;
                font-size: 9px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background: #EF4444;
                color: white;
            }
        """)
        self.btn_remove_attach.clicked.connect(self._remove_attachment)
        attach_badge_layout.addWidget(self.btn_remove_attach)

        layout.addWidget(self.attachment_badge_widget)

        # ── Chat Input Row (+ Button, Chat Input, Send Button) ──
        self.chat_input_row = QWidget(self)
        chat_row_layout = QHBoxLayout(self.chat_input_row)
        chat_row_layout.setContentsMargins(0, 0, 0, 0)
        chat_row_layout.setSpacing(6)

        # 1. Plus (+) Attach Button (Precision Vector Centered)
        self.btn_attach = CircularIconButton(icon_type="plus", parent=self.chat_input_row)
        self.btn_attach.setToolTip("แนบไฟล์หรือรูปภาพ (คลิกเพื่อเลือก หรือลากไฟล์มาวาง)")
        self.btn_attach.clicked.connect(self._select_file_dialog)
        chat_row_layout.addWidget(self.btn_attach)

        # 2. Droppable Chat Input
        self.chat_input = ChatInputField(on_file_dropped=self._attach_file, parent=self.chat_input_row)
        self.chat_input.setPlaceholderText("พิมพ์คำสั่งให้ JARVIS...")
        self.chat_input._reset_style()
        self.chat_input.returnPressed.connect(self._send_chat_message)
        chat_row_layout.addWidget(self.chat_input, 1)

        # 3. Send Button (➤) (Precision Vector Centered)
        self.btn_send = CircularIconButton(icon_type="send", parent=self.chat_input_row)
        self.btn_send.setToolTip("ส่งคำสั่ง (Enter)")
        self.btn_send.clicked.connect(self._send_chat_message)
        chat_row_layout.addWidget(self.btn_send)

        self.chat_input_row.setVisible(False)
        layout.addWidget(self.chat_input_row)
        
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
        elif getattr(self, '_current_status', '') in ['TOOL_RUNNING', 'PROGRESS']:
            # Pulsating border while working
            import math
            import time
            pulse = int((math.sin(time.time() * 6) + 1) * 75) + 50 # 50 to 200
            pen = QPen(QColor(0, 229, 255, pulse), 1.5)
            painter.setPen(pen)
            painter.fillPath(path, QColor(10, 18, 30, 220))
            # Keep repainting to animate the pulse
            QTimer.singleShot(50, self.update)
        else:
            # Standard HUD glassmorphism (Crisp luminous cyan border + sleek dark glass)
            pen = QPen(QColor(0, 229, 255, 200), 1.5)
            painter.setPen(pen)
            painter.fillPath(path, QColor(10, 15, 26, 245))
        
        # ── Status Indicator Dot Removed by User Request ──

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
        if self._is_agent_event:
            self._agent_timer.stop()
        if self._is_gauge:
            self._gauge_timer.stop()
        if self._is_diff:
            self._diff_timer.stop()
        if not self.media_label.isHidden():
            self._media_timer.stop()  # Pause media dismissal while inspecting
        self._update_size_based_on_state()
        if self._current_status in ["TOOL_RUNNING", "PROGRESS"] and self._current_detail:
            self.label.set_text_marquee(self._current_detail, force_marquee=True)
        super().enterEvent(event)

    def leaveEvent(self, event):  # type: ignore
        self._is_hovered = False
        if self._is_toast:
            self._toast_timer.start(2000)  # Auto-close 2s after cursor leaves
        if self._is_agent_event:
            self._agent_timer.start(2500)
        if self._is_gauge:
            self._gauge_timer.start(2500)
        if self._is_diff:
            self._diff_timer.start(2000)
        if not self.media_label.isHidden():
            self._media_timer.start(3000)  # Auto-close media 3s after cursor leaves
        self._update_size_based_on_state()
        self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
        super().leaveEvent(event)
        
    def _update_size_based_on_state(self):
        if not self.media_label.isHidden():
            return
        elif self._is_agent_event:
            self.top_bar_widget.setVisible(False)
            self.toast_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(False)
            self.live_diff_widget.setVisible(False)
            self.agent_event_widget.setVisible(True)
            self._resize_smooth(self.AGENT_W, self.AGENT_H)
            return
        elif self._is_gauge:
            self.top_bar_widget.setVisible(False)
            self.toast_widget.setVisible(False)
            self.agent_event_widget.setVisible(False)
            self.live_diff_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(True)
            self._resize_smooth(self.GAUGE_W, self.GAUGE_H)
            return
        elif self._is_diff:
            self.top_bar_widget.setVisible(False)
            self.toast_widget.setVisible(False)
            self.agent_event_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(False)
            self.live_diff_widget.setVisible(True)
            self._resize_smooth(self.DIFF_W, self.DIFF_H)
            return
        elif self._is_toast:
            self.top_bar_widget.setVisible(False)
            self.agent_event_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(False)
            self.live_diff_widget.setVisible(False)
            self.toast_widget.setVisible(True)
            self._resize_smooth(self.TOAST_W, self.TOAST_H)
            return
        elif self._is_hovered:
            self.top_bar_widget.setVisible(True)
            self.toast_widget.setVisible(False)
            self.agent_event_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(False)
            self.live_diff_widget.setVisible(False)
            if hasattr(self, 'model_pills_widget'):
                self.model_pills_widget.setVisible(True)
            if hasattr(self, 'attachment_badge_widget'):
                self.attachment_badge_widget.setVisible(bool(getattr(self, '_attached_file_path', None)))
            if hasattr(self, 'chat_input_row'):
                self.chat_input_row.setVisible(True)
            self.chat_input.setVisible(True)
            self.chat_input.setFocus()
            target_h = self.EXPANDED_H + 25
            if getattr(self, '_attached_file_path', None):
                target_h += 24
            self._resize_smooth(self.EXPANDED_W, target_h)
        else:
            self.top_bar_widget.setVisible(True)
            self.toast_widget.setVisible(False)
            self.agent_event_widget.setVisible(False)
            self.usage_gauge_widget.setVisible(False)
            self.live_diff_widget.setVisible(False)
            if hasattr(self, 'model_pills_widget'):
                self.model_pills_widget.setVisible(False)
            if hasattr(self, 'attachment_badge_widget'):
                self.attachment_badge_widget.setVisible(False)
            if hasattr(self, 'chat_input_row'):
                self.chat_input_row.setVisible(False)
            self.chat_input.setVisible(False)
            self.chat_input.clearFocus()
            self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)

    # ──────────────────────────────────────────────────────────────────────────
    # 🤖 Coucou Agent Watcher & Gauges Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def show_agent_event(self, agent: str, status: str, detail: str, buttons: str = "terminal_ok", duration: int = 7000):
        self._is_agent_event = True
        self._is_toast = False
        self._is_gauge = False
        self._is_diff = False
        
        self.top_bar_widget.setVisible(False)
        self.toast_widget.setVisible(False)
        self.usage_gauge_widget.setVisible(False)
        self.live_diff_widget.setVisible(False)
        if hasattr(self, 'attachment_badge_widget'):
            self.attachment_badge_widget.setVisible(False)
        if hasattr(self, 'chat_input_row'):
            self.chat_input_row.setVisible(False)
        
        self.agent_event_widget.set_event(agent, status, detail, buttons)
        self.agent_event_widget.setVisible(True)
        
        if "antigravity" in agent.lower():
            self.buddy_widget.set_skin("antigravity")
            self.buddy_widget.set_mood("alert")
        elif "codex" in agent.lower():
            self.buddy_widget.set_skin("codex")
            self.buddy_widget.set_mood("success")
        elif "cursor" in agent.lower():
            self.buddy_widget.set_skin("cursor")
            self.buddy_widget.set_mood("happy")
        else:
            self.buddy_widget.set_skin("jarvis")
            self.buddy_widget.set_mood("alert" if (buttons == "allow_deny" or status == "request") else "idle")

        if buttons == "allow_deny" or status == "request":
            duration = max(duration, 25000)
        elif status == "finished":
            duration = min(duration, 4000)

        self._play_chime("ACK")
        self._resize_smooth(self.AGENT_W, self.AGENT_H)
        self._agent_timer.start(duration)
        self.update()

    def _dismiss_agent_event(self):
        try:
            from modules.security_approval_gate import resolve_approval
            resolve_approval(allowed=False)
        except Exception:
            pass
        self._is_agent_event = False
        self.agent_event_widget.setVisible(False)
        self.top_bar_widget.setVisible(True)
        self.buddy_widget.set_skin("jarvis")
        self.buddy_widget.set_mood("idle")
        self._update_size_based_on_state()
        self.update()

    def _handle_agent_action(self, action_type: str):
        self._agent_timer.stop()
        self._play_chime("ACK")
        if action_type == "primary":
            btn_text = self.agent_event_widget.btn_primary.text()
            if "allow" in btn_text.lower():
                try:
                    from modules.security_approval_gate import resolve_approval
                    resolve_approval(allowed=True)
                except Exception as e:
                    logger.error(f"[GATE] resolve_approval error: {e}")
                self.show_toast("Security Approved", "อนุมัติคำสั่งเรียบร้อยแล้ว ✅", icon="✅", duration=3000)
            elif "terminal" in btn_text.lower():
                try:
                    import subprocess
                    subprocess.Popen(["cmd.exe", "/c", "start", "powershell.exe"])
                except Exception:
                    pass
                self.show_toast("Terminal Opened", "เปิดเทอร์มินัลเรียบร้อยแล้วครับ", icon="💻", duration=3000)
        else:
            btn_text = self.agent_event_widget.btn_secondary.text()
            if "deny" in btn_text.lower():
                try:
                    from modules.security_approval_gate import resolve_approval
                    resolve_approval(allowed=False)
                except Exception as e:
                    logger.error(f"[GATE] resolve_approval error: {e}")
                self.show_toast("Security Denied", "ปฏิเสธคำสั่งเพื่อความปลอดภัย ❌", icon="❌", duration=3000)
            else:
                self._dismiss_agent_event()

    def _toggle_quota_gauge(self):
        if getattr(self, '_is_gauge', False):
            self._dismiss_gauge()
        else:
            self.show_usage_gauge()

    def show_usage_gauge(self, groq: int = -1, gemini: int = -1, ollama: int = -1, streak_badge: str = "", duration: int = 6500):
        # Auto-fetch live usage stats if not explicitly passed
        if groq < 0 or gemini < 0 or ollama < 0:
            try:
                from modules.ai_quota_tracker import get_gauge_values, get_quota_stats
                groq, gemini, ollama = get_gauge_values()
                if not streak_badge:
                    stats = get_quota_stats()
                    streak_badge = stats.get("streak_badge", "Core Online")
            except Exception as e:
                logger.error(f"[QUOTA] Failed to fetch live stats: {e}")
                groq, gemini, ollama = (0, 0, 0)

        self._is_gauge = True
        self._is_agent_event = False
        self._is_toast = False
        self._is_diff = False
        
        self.top_bar_widget.setVisible(False)
        self.toast_widget.setVisible(False)
        self.agent_event_widget.setVisible(False)
        self.live_diff_widget.setVisible(False)
        if hasattr(self, 'attachment_badge_widget'):
            self.attachment_badge_widget.setVisible(False)
        if hasattr(self, 'chat_input_row'):
            self.chat_input_row.setVisible(False)
        
        self.usage_gauge_widget.update_values(groq, gemini, ollama, streak_badge)
        self.usage_gauge_widget.setVisible(True)
        
        self._resize_smooth(self.GAUGE_W, self.GAUGE_H)
        self._gauge_timer.start(duration)
        self.update()

    def _dismiss_gauge(self):
        self._is_gauge = False
        self.usage_gauge_widget.setVisible(False)
        self.top_bar_widget.setVisible(True)
        self._update_size_based_on_state()
        self.update()

    def show_live_diff(self, added: int = 48, removed: int = 12, note: str = "", duration: int = 5000):
        self._is_diff = True
        self._is_gauge = False
        self._is_agent_event = False
        self._is_toast = False
        
        self.top_bar_widget.setVisible(False)
        self.toast_widget.setVisible(False)
        self.agent_event_widget.setVisible(False)
        self.usage_gauge_widget.setVisible(False)
        if hasattr(self, 'attachment_badge_widget'):
            self.attachment_badge_widget.setVisible(False)
        if hasattr(self, 'chat_input_row'):
            self.chat_input_row.setVisible(False)
        
        self.live_diff_widget.set_diff(added, removed, note)
        self.live_diff_widget.setVisible(True)
        
        self._resize_smooth(self.DIFF_W, self.DIFF_H)
        self._diff_timer.start(duration)
        self.update()

    def _dismiss_diff(self):
        self._is_diff = False
        self.live_diff_widget.setVisible(False)
        self.top_bar_widget.setVisible(True)
        self._update_size_based_on_state()
        self.update()

    def _update_model_pills_ui(self, active_engine: str):
        for m_key, (btn, m_name, m_col) in getattr(self, 'model_buttons', {}).items():
            if m_key == active_engine:
                btn.setText(f"● {m_name}")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {m_col};
                        color: #0F172A;
                        border: 1px solid {m_col};
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 0 6px;
                    }}
                """)
            else:
                btn.setText(m_name)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(255, 255, 255, 0.08);
                        color: {m_col};
                        border: 1px solid rgba(255, 255, 255, 0.18);
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 0 6px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255, 255, 255, 0.22);
                        border: 1px solid {m_col};
                    }}
                """)

    def _on_select_model(self, model_name: str, engine_key: str = ""):
        if not engine_key:
            if "gemini" in model_name.lower():
                engine_key = "gemini"
            elif "ollama" in model_name.lower() or "local" in model_name.lower():
                engine_key = "ollama"
            else:
                engine_key = "groq"

        self._selected_model = model_name
        self._active_engine = engine_key
        self._update_model_pills_ui(engine_key)
        self.chat_input.setPlaceholderText(f"สั่งงาน {model_name}...")

        # 1. Persist to active_model.json
        try:
            from jarvis_core.ai_router import set_active_model
            set_active_model(engine_key)
        except Exception:
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cache_file = os.path.join(base_dir, "system_cache", "active_model.json")
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"primary_engine": engine_key, "updated_at": time.time()}, f, indent=2)
            except Exception:
                pass

        # 2. Notify JARVIS backend via HTTP in background
        def _notify():
            try:
                import urllib.request
                req = urllib.request.Request(
                    "http://127.0.0.1:5050/api/switch_model",
                    data=json.dumps({"model": engine_key}).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=2) as resp:  # nosec B310
                    pass
            except Exception:
                pass
        threading.Thread(target=_notify, daemon=True).start()

        self.show_toast("AI Model Active", f"สลับโมเดลเป็น {model_name} เรียบร้อยแล้ว (ใช้งานจริง)", icon="⚡", duration=2500)

    # ──────────────────────────────────────────────────────────────────────────
    # 🎙️ Push-To-Talk Subsystem
    # ──────────────────────────────────────────────────────────────────────────

    def _start_recording(self):
        self._is_recording = True
        self._audio_frames = []
        self._accumulated_text = ""
        self._current_partial = ""
        self.dg_connection = None
        island_self = self
        
        # 1. Update UI IMMEDIATELY
        self.label.set_text_marquee("🎙️ PTT: กำลังเตรียมไมค์...")
        self._resize_smooth(self.EXPANDED_W, self.DEFAULT_H + 40)
        
        def _init_heavy():
            try:
                import os
                
                # --- PyAudio Init ---
                if not getattr(island_self, '_pyaudio_instance', None):
                    island_self._pyaudio_instance = pyaudio.PyAudio()
                    
                mic_index = None
                from dotenv import load_dotenv
                load_dotenv()
                env_mic = os.getenv("MIC_INDEX")
                if env_mic is not None and env_mic.strip() != "":
                    try: mic_index = int(env_mic)
                    except ValueError: pass
                        
                stream_kwargs = {
                    'format': pyaudio.paInt16,
                    'channels': 1,
                    'rate': 16000,
                    'input': True,
                    'frames_per_buffer': 1024,
                    'stream_callback': island_self._audio_callback
                }
                if mic_index is not None:
                    stream_kwargs['input_device_index'] = mic_index
                    
                island_self._audio_stream = island_self._pyaudio_instance.open(**stream_kwargs)
                island_self._audio_stream.start_stream()
                
                # Notify UI that Mic is ready
                QTimer.singleShot(0, lambda: island_self.label.set_text_marquee("🎙️ PTT: กำลังฟัง... (พูดได้เลย)"))

                # --- Deepgram Init (Background) ---
                from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
                api_key = os.getenv("DEEPGRAM_API_KEY")
                if api_key:
                    island_self.deepgram = DeepgramClient(api_key)
                    dg_conn = island_self.deepgram.listen.live.v("1")
                    
                    def _on_message(dg_self, result, **kwargs):
                        sentence = result.channel.alternatives[0].transcript
                        if len(sentence) == 0: return
                        
                        # [EMERGENCY CANCEL]
                        cancel_words = ["ยกเลิกคำสั่ง", "ช่างมัน", "ไม่เอาแล้ว", "หยุดทำงาน", "cancel command"]
                        if any(cw in sentence.lower() for cw in cancel_words) or any(cw in island_self._accumulated_text.lower() for cw in cancel_words):
                            island_self._accumulated_text = ""
                            island_self._current_partial = ""
                            QTimer.singleShot(0, lambda: island_self.label.set_text_marquee("🚫 ยกเลิกคำสั่งแล้ว", force_marquee=False))
                            return

                        if result.is_final:
                            island_self._accumulated_text += " " + sentence
                            island_self._current_partial = ""
                            
                            # [OPEN MIC MODE] Check if user stopped talking
                            if getattr(result, 'speech_final', False):
                                final_text = island_self._accumulated_text.strip()
                                if final_text:
                                    import requests
                                    try:
                                        payload = {"message": final_text, "channel": "voice"}
                                        requests.post("http://127.0.0.1:5050/chat", json=payload, timeout=10)
                                    except Exception as e:
                                        pass
                                island_self._accumulated_text = "" # Reset for next sentence
                                QTimer.singleShot(0, lambda: island_self.label.set_text_marquee(f"⚡ สั่งงาน: {final_text}", force_marquee=False))
                                return
                        else:
                            island_self._current_partial = sentence
                            
                        display = (island_self._accumulated_text + " " + island_self._current_partial).strip()
                        if display:
                            QTimer.singleShot(0, lambda: island_self.label.set_text_marquee(f"🎙️ {display}", force_marquee=False))

                    def _on_error(dg_self, error, **kwargs):
                        pass

                    dg_conn.on(LiveTranscriptionEvents.Transcript, _on_message)
                    dg_conn.on(LiveTranscriptionEvents.Error, _on_error)

                    options = LiveOptions(
                        model="nova-2",
                        language="th",
                        smart_format=True,
                        encoding="linear16",
                        channels=1,
                        sample_rate=16000,
                        endpointing=500, # Triggers speech_final after 500ms of silence
                    )
                    dg_conn.start(options)
                    island_self.dg_connection = dg_conn
                    
                    # Flush buffered frames
                    if island_self._is_recording and island_self._audio_frames:
                        for frame in list(island_self._audio_frames):
                            try: dg_conn.send(frame)
                            except: pass
                            
            except Exception as e:
                QTimer.singleShot(0, lambda: island_self.label.set_text_marquee(f"⚠️ ไมค์มีปัญหา: {e}"))
                island_self._is_recording = False
                
        import threading
        threading.Thread(target=_init_heavy, daemon=True).start()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self._is_recording:
            self._audio_frames.append(in_data)
            if getattr(self, 'dg_connection', None):
                try:
                    self.dg_connection.send(in_data)
                except:
                    pass

        return (in_data, 0)

    def _stop_recording(self):
        self._is_recording = False
        self.label.set_text_marquee("⚡ กำลังส่งข้อความเสียง...")
        self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)
        
        if getattr(self, '_audio_stream', None):
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except:
                pass
            
        if getattr(self, 'dg_connection', None):
            try:
                self.dg_connection.finish()
            except:
                pass
                
        def _send():
            try:
                import requests
                final_text = (getattr(self, '_accumulated_text', "") + " " + getattr(self, '_current_partial', "")).strip()
                if getattr(self, 'dg_connection', None):
                    if final_text:
                        payload = {"message": final_text, "channel": "voice"}
                        requests.post("http://127.0.0.1:5050/chat", json=payload, timeout=10)
                    QTimer.singleShot(0, lambda: self.label.set_text_marquee("J.A.R.V.I.S."))
                else:
                    import wave
                    import tempfile
                    import os
                    
                    path = os.path.join(tempfile.gettempdir(), "ptt_jarvis.wav")
                    wf = wave.open(path, 'wb')
                    wf.setnchannels(1)
                    wf.setsampwidth(self._pyaudio_instance.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(self._audio_frames))
                    wf.close()
                    
                    with open(path, 'rb') as f:
                        files = {'audio': ('ptt.wav', f, 'audio/wav')}
                        requests.post("http://127.0.0.1:5050/voice", files=files, timeout=10)
                    QTimer.singleShot(0, lambda: self.label.set_text_marquee("J.A.R.V.I.S."))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.label.set_text_marquee(f"⚠️ ส่งเสียงไม่สำเร็จ: {e}"))
                
        import threading
        threading.Thread(target=_send, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # 🚨 Smart Alert / Toast Banner Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def show_toast(self, title: str, message: str, icon: str = "🔔", duration: int = 4500) -> None:
        """Display a dynamic animated toast notification on the island"""
        self._is_toast = True
        self._is_agent_event = False
        self._is_gauge = False
        self._is_diff = False
        self._toast_title = title
        self._toast_message = message
        self._toast_icon = icon

        self.toast_title_label.setText(f"{icon} {title}")
        self.toast_msg_label.setText(message)

        self.top_bar_widget.setVisible(False)
        self.toast_widget.setVisible(True)
        self.agent_event_widget.setVisible(False)
        self.usage_gauge_widget.setVisible(False)
        self.live_diff_widget.setVisible(False)
        if hasattr(self, 'attachment_badge_widget'):
            self.attachment_badge_widget.setVisible(False)
        if hasattr(self, 'chat_input_row'):
            self.chat_input_row.setVisible(False)
        self.chat_input.setVisible(False)
        if hasattr(self, 'model_pills_widget'):
            self.model_pills_widget.setVisible(False)

        self._resize_smooth(self.TOAST_W, self.TOAST_H)
        self._toast_timer.start(duration)
        self.update()

    def _dismiss_toast(self) -> None:
        """Smoothly collapse toast back to normal state"""
        self._is_toast = False
        self.toast_widget.setVisible(False)
        self.top_bar_widget.setVisible(True)
        self._update_size_based_on_state()
        self.update()

    # ──────────────────────────────────────────────────────────────────────────
    # 📎 File Selection & Attachment Methods
    # ──────────────────────────────────────────────────────────────────────────
    def _select_file_dialog(self) -> None:
        """Open native file dialog to pick an image, code or document"""
        file_filter = (
            "All Supported (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.txt *.py *.md *.pdf *.json *.csv *.log);;"
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;"
            "Documents & Code (*.txt *.py *.md *.pdf *.json *.csv *.log);;"
            "All Files (*.*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "เลือกไฟล์หรือรูปภาพสำหรับ J.A.R.V.I.S.",
            "",
            file_filter
        )
        if file_path:
            self._attach_file(file_path)

    def _attach_file(self, file_path: str) -> None:
        """Attach file to chat input, show floating badge and update placeholder"""
        if not file_path or not os.path.exists(file_path):
            return
            
        self._attached_file_path = file_path
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            size_str = ""

        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
            icon = "🖼️"
        elif ext in [".py", ".js", ".ts", ".html", ".css", ".json"]:
            icon = "💻"
        elif ext in [".pdf", ".doc", ".docx", ".txt", ".md"]:
            icon = "📄"
        else:
            icon = "📎"

        badge_text = f"{icon} {filename} ({size_str})" if size_str else f"{icon} {filename}"
        self.attachment_file_label.setText(badge_text)
        self.attachment_badge_widget.setVisible(True)
        self.chat_input.setPlaceholderText(f"พิมพ์คำสั่งเกี่ยวกับ {filename} หรือกด Enter...")
        self.chat_input.setFocus()
        
        # Ensure island expands to accommodate attachment
        self._is_hovered = True
        self._update_size_based_on_state()
        self.update()
        self._play_chime("ACK")

    def _remove_attachment(self) -> None:
        """Remove currently attached file"""
        self._attached_file_path = None
        self.attachment_badge_widget.setVisible(False)
        selected_model = getattr(self, '_selected_model', 'Groq 120B')
        self.chat_input.setPlaceholderText(f"สั่งงาน {selected_model}...")
        self._update_size_based_on_state()
        self.update()

    # ──────────────────────────────────────────────────────────────────────────
    # 📁 Drag & Drop AI Ingestion Subsystem
    # ──────────────────────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore
        if event.mimeData().hasUrls() or event.mimeData().hasText():  # type: ignore
            event.acceptProposedAction()
            self._is_drag_over = True
            self.toast_widget.setVisible(False)
            self.label.setVisible(True)
            self.label.set_text_marquee("📥 วางไฟล์ลงในกล่องแชทเพื่อแนบไฟล์", force_marquee=False)
            self._is_hovered = True
            self._update_size_based_on_state()
            self.update()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # type: ignore
        self._is_drag_over = False
        self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore
        self._is_drag_over = False
        urls = event.mimeData().urls()  # type: ignore
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        
        if file_paths:
            target_file = file_paths[0]
            self._attach_file(target_file)
        elif event.mimeData().hasText():  # type: ignore
            text = event.mimeData().text().strip()  # type: ignore
            clean_path = text.strip('"').strip("'")
            if os.path.exists(clean_path):
                self._attach_file(clean_path)
            elif text:
                self.chat_input.setText(text)
                self.chat_input.setFocus()
                self._is_hovered = True
                self._update_size_based_on_state()
        
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
            
            payload["model"] = getattr(self, '_selected_model', 'Groq 120B')
            payload["channel"] = "dynamic_island"
            
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:5050/chat",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                res_json = json.loads(resp.read().decode("utf-8"))
                reply = res_json.get("response", "")
                if reply:
                    clean_reply = reply[:110].replace("\n", " ")
                    QTimer.singleShot(0, self, lambda: self.show_toast("🤖 JARVIS วิเคราะห์เสร็จสิ้น", clean_reply, icon="✨", duration=6500))
        except Exception as e:
            e_str = str(e)
            logger.error(f"Failed to ingest file via Dynamic Island: {e_str}")
            QTimer.singleShot(0, self, lambda: self.show_toast("⚠️ ข้อขัดข้อง", f"ไม่สามารถส่งไฟล์ให้ JARVIS: {e_str}", icon="⚠️", duration=4000))

    def _send_text_to_jarvis(self, prompt: str) -> None:
        """Send dropped text to JARVIS backend"""
        try:
            data_bytes = json.dumps({"message": prompt}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:5050/chat",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:  # nosec B310
                res_json = json.loads(resp.read().decode("utf-8"))
                reply = res_json.get("response", "")
                if reply:
                    clean_reply = reply[:110].replace("\n", " ")
                    QTimer.singleShot(0, self, lambda: self.show_toast("🤖 JARVIS สรุปผล", clean_reply, icon="✨", duration=6500))
        except Exception as e:
            logger.error(f"Failed to send dropped text: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Existing Chat & Camera Methods
    # ──────────────────────────────────────────────────────────────────────────
    def _send_chat_message(self):
        text = self.chat_input.text().strip()
        attached_file = getattr(self, '_attached_file_path', None)
        
        # Check if user typed or pasted a raw file path as text
        if not attached_file and text and os.path.exists(text.strip('"').strip("'")):
            potential_path = text.strip('"').strip("'")
            if os.path.isfile(potential_path):
                attached_file = potential_path
                text = ""

        if not text and not attached_file:
            return
        
        self.chat_input.clear()
        selected_model = getattr(self, '_selected_model', 'Groq 120B')
        self.label.set_text_marquee(f"⚡ {selected_model}: กำลังวิเคราะห์...")
        self.buddy_widget.set_mood("thinking")
        
        # Save attached file to send and reset attachment state on UI
        file_to_send = attached_file
        self._attached_file_path = None
        if hasattr(self, 'attachment_badge_widget'):
            self.attachment_badge_widget.setVisible(False)
        self.chat_input.setPlaceholderText(f"สั่งงาน {selected_model}...")
        self._update_size_based_on_state()
        self.update()
        
        def _post_data():
            try:
                payload = {
                    "model": selected_model,
                    "channel": "dynamic_island"
                }
                
                if file_to_send and os.path.exists(file_to_send):
                    filename = os.path.basename(file_to_send)
                    ext = os.path.splitext(file_to_send)[1].lower()
                    
                    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
                        try:
                            from PIL import Image
                            import io
                            _pimg = Image.open(file_to_send)
                            if _pimg.mode in ("RGBA", "P"):
                                _pimg = _pimg.convert("RGB")
                            _pw, _ph = _pimg.size
                            if _pw < 32 or _ph < 32:
                                _pimg = _pimg.resize((max(32, _pw), max(32, _ph)), Image.Resampling.LANCZOS)
                            elif _pw > 1024 or _ph > 1024:
                                _pimg.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                            _buf = io.BytesIO()
                            _pimg.save(_buf, format="JPEG", quality=80, optimize=True)
                            b64_img = base64.b64encode(_buf.getvalue()).decode("utf-8")
                        except Exception:
                            with open(file_to_send, "rb") as f:
                                b64_img = base64.b64encode(f.read()).decode("utf-8")
                        payload["image"] = b64_img
                        if text:
                            payload["message"] = f"เจ้านายส่งรูปภาพ '{filename}' พร้อมคำสั่ง: {text}"
                        else:
                            payload["message"] = f"เจ้านายได้ส่งรูปภาพ '{filename}' มาให้ทาง Dynamic Island ช่วยตรวจสอบและวิเคราะห์รายละเอียดของภาพนี้ให้เจ้านายครับ"
                    else:
                        file_content = ""
                        try:
                            with open(file_to_send, "r", encoding="utf-8", errors="ignore") as f:
                                file_content = f.read(5000)
                        except Exception:
                            pass
                        prompt_header = f"คำสั่งจากเจ้านาย: {text}\n\n" if text else ""
                        payload["message"] = (
                            f"{prompt_header}"
                            f"เจ้านายได้ส่งไฟล์ '{filename}' มาให้ทาง Dynamic Island เพื่อให้คุณช่วยวิเคราะห์ "
                            f"เนื้อหาของไฟล์:\n```\n{file_content}\n```\n"
                            f"กรุณาวิเคราะห์และตอบคำถามหรือสรุปผลให้เจ้านายทราบครับ"
                        )
                else:
                    payload["message"] = text

                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    "http://127.0.0.1:5050/chat",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=35) as resp:  # nosec B310
                    res_json = json.loads(resp.read().decode('utf-8'))
                    reply = res_json.get("response", "")
                    if reply:
                        clean_reply = reply[:140].replace("\n", " ").strip()
                        QTimer.singleShot(0, self, lambda: self.show_toast(f"🤖 {selected_model}", clean_reply, icon="💬", duration=7000))
                        QTimer.singleShot(0, self, lambda: self.buddy_widget.set_mood("happy"))
                    else:
                        QTimer.singleShot(0, self, lambda: self.buddy_widget.set_mood("idle"))
            except Exception as e:
                logger.error(f"Failed to send chat: {e}")
                QTimer.singleShot(0, self, lambda: self.show_toast("⚠️ Error", f"ส่งคำสั่งไม่สำเร็จ: {e}", icon="⚠️", duration=3500))
                QTimer.singleShot(0, self, lambda: self.buddy_widget.set_mood("idle"))
                
        threading.Thread(target=_post_data, daemon=True).start()

    def update_status(self, status: str, detail: str = "") -> None:
        QTimer.singleShot(0, lambda: self._apply_status(status, detail))

    def _play_chime(self, chime_type: str) -> None:
        def play():
            try:
                import winsound
                if chime_type == "ACK":
                    winsound.Beep(1200, 60)
                    winsound.Beep(1800, 80)
                elif chime_type == "FINISH":
                    winsound.Beep(1800, 60)
                    winsound.Beep(1200, 80)
                elif chime_type == "ALERT":
                    winsound.Beep(600, 150)
                    winsound.Beep(600, 150)
            except:
                pass
        threading.Thread(target=play, daemon=True).start()

    def _apply_status(self, status: str, detail: str) -> None:
        if status == "TOOL_RUNNING":
            self._play_chime("ACK")
        elif status == "STANDBY" and getattr(self, '_current_status', '') == "TOOL_RUNNING":
            self._play_chime("FINISH")
        elif status == "ALERT":
            self._play_chime("ALERT")
        elif status in ["IMAGE", "GIF", "MEDIA"]:
            self._play_chime("ACK")
            
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
                self._dismiss_media()
            return

        self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False)
            
        self._current_status = status
        self._current_detail = detail
        
        if status in ["PROGRESS", "TOOL_RUNNING"]:
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)
            
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
                frame = cv2.flip(frame, 1)  # Mirror horizontal
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
                
    def _show_media(self, m_type: str, path: str, duration: int = 8000):
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
        # Automatically collapse media display after duration (default 8s)
        self._media_timer.start(duration)

    def _dismiss_media(self):
        """Smoothly collapse media preview back to normal HUD pill state"""
        self._media_timer.stop()
        self.media_label.hide()
        if self.media_label.movie():
            self.media_label.movie().stop()  # type: ignore
        self._update_size_based_on_state()
        self._resize_smooth(self.DEFAULT_W, self.DEFAULT_H)
        self.update()

    def mousePressEvent(self, event):  # type: ignore
        """Clicking on media preview dismisses it immediately"""
        if not self.media_label.isHidden() and self.cam is None:
            self._dismiss_media()
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_buddy_skin_changed(self, skin_key: str) -> None:
        """Briefly notify user of the skin switch on the HUD marquee"""
        skin_info = self.buddy_widget.SKINS.get(skin_key, {})
        skin_name = skin_info.get("name", skin_key.capitalize())
        self.label.set_text_marquee(f"🎨 Skin: {skin_name}", force_marquee=False)
        QTimer.singleShot(2500, lambda: self.label.set_text_marquee("J.A.R.V.I.S.", force_marquee=False))

    def contextMenuEvent(self, event):  # type: ignore
        """Right-click context menu to change skins, hide, or exit Dynamic Island"""
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

    def _show_visual_skin_picker(self, pos=None):
        """Display floating visual mascot picker shelf directly under the mascot"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(15, 23, 42, 0.95);
                color: #E2E8F0;
                border: 1px solid rgba(0, 191, 255, 0.5);
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
        """)
        palette_action = QWidgetAction(menu)
        palette_widget = SkinPaletteWidget(
            current_skin=self.buddy_widget.skin,
            on_select=lambda sk: (self.buddy_widget.set_skin(sk, save=True), menu.close()),
            parent=menu
        )
        palette_action.setDefaultWidget(palette_widget)
        menu.addAction(palette_action)

        if pos is None:
            global_pt = self.buddy_widget.mapToGlobal(QPoint(0, self.buddy_widget.height() + 6))
        else:
            global_pt = pos
        menu.exec(global_pt)

    def contextMenuEvent(self, event):  # type: ignore
        """Right-click context menu with visual mascot skin picker card"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(15, 23, 42, 0.95);
                color: #E2E8F0;
                border: 1px solid rgba(0, 191, 255, 0.5);
                border-radius: 10px;
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

        # ── Visual Mascot Skin Palette Card (Characters instead of text list) ──
        palette_action = QWidgetAction(menu)
        palette_widget = SkinPaletteWidget(
            current_skin=self.buddy_widget.skin,
            on_select=lambda sk: (self.buddy_widget.set_skin(sk, save=True), menu.close()),
            parent=menu
        )
        palette_action.setDefaultWidget(palette_widget)
        menu.addAction(palette_action)

        menu.exec(event.globalPos())

    def _on_pipe_message(self) -> None:
        try:
            conn = self._pipe_server.nextPendingConnection()
            if conn:
                conn.readyRead.connect(lambda: self._read_pipe(conn))  # type: ignore
        except Exception as e:
            logger.error(f"[ISLAND] IPC connection error: {e}")

    def _read_pipe(self, conn: QLocalSocket) -> None:
        try:
            if not conn or not conn.isValid():
                return
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


            if status == "BUDDY_MOOD":
                self.buddy_widget.set_mood(detail)
                return

            if status == "BUDDY_SKIN":
                self.buddy_widget.set_skin(detail, save=True)
                return

            if status == "AGENT_EVENT":
                # detail: agent:::status:::detail:::buttons
                parts_ev = detail.split(":::")
                ag = parts_ev[0] if len(parts_ev) > 0 else "Codex"
                st = parts_ev[1] if len(parts_ev) > 1 else "finished"
                dt = parts_ev[2] if len(parts_ev) > 2 else ""
                btn = parts_ev[3] if len(parts_ev) > 3 else "terminal_ok"
                self.show_agent_event(ag, st, dt, btn)
                return

            if status == "AGENT_DISMISS":
                self._dismiss_agent_event()
                return

            if status == "USAGE_GAUGE":
                # detail: groq:::gemini:::ollama:::streak_badge
                parts_g = detail.split(":::")
                g = int(parts_g[0]) if len(parts_g) > 0 and (parts_g[0].isdigit() or parts_g[0] == "-1") else -1
                m = int(parts_g[1]) if len(parts_g) > 1 and (parts_g[1].isdigit() or parts_g[1] == "-1") else -1
                o = int(parts_g[2]) if len(parts_g) > 2 and (parts_g[2].isdigit() or parts_g[2] == "-1") else -1
                badge = parts_g[3] if len(parts_g) > 3 else ""
                self.show_usage_gauge(g, m, o, streak_badge=badge)
                return

            if status == "LIVE_DIFF":
                # detail: added:::removed:::summary
                parts_d = detail.split(":::")
                a = int(parts_d[0]) if len(parts_d) > 0 and parts_d[0].isdigit() else 48
                r = int(parts_d[1]) if len(parts_d) > 1 and parts_d[1].isdigit() else 12
                note = parts_d[2] if len(parts_d) > 2 else "lines changed"
                self.show_live_diff(a, r, note)
                return

            if status in ["ATTACH_FILE", "ATTACH"]:
                self._attach_file(detail)
                return
                
            self._last_heartbeat = time.time()
            self.update_status(status, detail)
        except Exception as e:
            logger.error(f"[ISLAND] Error reading pipe: {e}")
        
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
            consecutive_dead = 0
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

                if alive:
                    consecutive_dead = 0
                else:
                    consecutive_dead += 1
                    if consecutive_dead >= 5:  # Require 5 consecutive failed checks (10s)
                        import os as _os
                        logger.info(f"[ISLAND] JARVIS PID {jarvis_pid} terminated. Dynamic Island closing.")
                        _os._exit(0)
                        break
        _thr.Thread(target=_pid_watchdog, args=(args.jarvis_pid,), daemon=True, name="PidWatchdogThread").start()

    sys.exit(app.exec())