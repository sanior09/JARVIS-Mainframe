"""
Abstract Base Classes and Core Utilities for Tactical Command Modules.
Provides In-Memory Cache and Base Collectors.
"""
import time
import logging
from abc import ABC


logger = logging.getLogger("TacticalCommand")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class InMemoryCache:
    """Simple TTL-based In-Memory Cache to prevent rate limiting."""
    def __init__(self, ttl: int = 60):
        self.default_ttl = ttl
        self._cache = {}
        
    def get(self, key: str):
        item = self._cache.get(key)
        if item and (time.time() - item['timestamp'] < item['ttl']):
            return item['data']
        return None
        
    def set(self, key: str, data: any, ttl: int = None):
        self._cache[key] = {
            'timestamp': time.time(),
            'data': data,
            'ttl': ttl if ttl is not None else self.default_ttl
        }

class BaseDataCollector:
    """Base class for all data collectors."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache

    def fetch_data(self) -> dict:
        """Fetch and return data, using cache if applicable."""
        pass

class BaseDataNormalizer:
    """Base class for normalizing raw API data into standard formats (e.g. GeoJSON)."""
    
    def normalize(self, raw_data: dict) -> dict:
        """Process raw data and return normalized structure."""
        pass
