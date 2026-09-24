"""
api_client.py -- JARVIS Flask Backend Health Check & Connection Manager
"""
from __future__ import annotations
import logging
import requests
from PySide6.QtCore import QObject, QTimer, Signal
from state import CONFIG

logger = logging.getLogger(__name__)


class JarvisApiClient(QObject):
    """Polls Flask backend and emits signals when state changes."""

    backend_online: Signal = Signal()
    backend_offline: Signal = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._is_online: bool = False
        self._timer: QTimer = QTimer(self)
        self._timer.setInterval(CONFIG.retry_interval_ms)
        self._timer.timeout.connect(self._check_health)

    def start_polling(self) -> None:
        self._check_health()
        self._timer.start()

    def stop_polling(self) -> None:
        self._timer.stop()

    @property
    def is_online(self) -> bool:
        return self._is_online

    def _check_health(self) -> None:
        url = CONFIG.backend_url + CONFIG.health_endpoint
        try:
            resp = requests.get(url, timeout=2)
            online = resp.status_code == 200
        except requests.exceptions.RequestException:
            online = False

        if online and not self._is_online:
            logger.info("[API Client] Backend ONLINE at %s", CONFIG.backend_url)
            self._is_online = True
            self.backend_online.emit()
        elif not online and self._is_online:
            logger.warning("[API Client] Backend OFFLINE")
            self._is_online = False
            self.backend_offline.emit()
        elif not online:
            logger.debug("[API Client] Backend still offline, retrying...")