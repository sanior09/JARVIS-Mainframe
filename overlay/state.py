"""
state.py -- Window State Management & Global Configuration
JARVIS Floating Overlay HUD
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final


class WindowState(Enum):
    """Finite-state machine states for the HUD window lifecycle."""
    HIDDEN = auto()
    SHOWING = auto()
    VISIBLE = auto()
    HIDING = auto()


@dataclass(frozen=True)
class OverlayConfig:
    backend_url: str = "http://127.0.0.1:5050"
    health_endpoint: str = "/api/quota"
    retry_interval_ms: int = 3000
    hud_height: int = 680
    trigger_zone_height: int = 5
    animation_duration_ms: int = 350
    hotkey_key: str = "space"
    app_name: str = "J.A.R.V.I.S. HUD"
    tray_tooltip: str = "J.A.R.V.I.S. Overlay"
    window_title: str = "JARVIS HUD"


CONFIG: Final[OverlayConfig] = OverlayConfig()