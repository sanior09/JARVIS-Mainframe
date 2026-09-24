"""
Abstract Base Classes and core interfaces for Shadow Broker modules.
Enforces SOLID principles and consistent structure across modules.
"""
from abc import ABC, abstractmethod
import queue
import threading
import logging

logger = logging.getLogger("ShadowBroker")
logger.setLevel(logging.INFO)
# Avoid adding multiple handlers if already configured elsewhere
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class BaseVideoWorker(ABC):
    """
    Abstract base class for reading video frames into a queue.
    Separates the I/O-bound stream reading from CPU-bound inference.
    """
    def __init__(self, stream_url: str, queue_size: int = 30):
        self.stream_url = stream_url
        self.frame_queue = queue.Queue(maxsize=queue_size)
        self.is_running = False
        self._thread = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()
            logger.info(f"BaseVideoWorker started for {self.stream_url}")

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"BaseVideoWorker stopped for {self.stream_url}")

    @abstractmethod
    def _worker_loop(self):
        """Implement the loop to capture frames and put them into self.frame_queue."""
        pass


class BaseGeoProvider(ABC):
    """
    Abstract base class for async Geospatial data fetching.
    """
    @abstractmethod
    async def fetch_data(self) -> dict:
        """Fetch and return data as a GeoJSON FeatureCollection dictionary."""
        pass
