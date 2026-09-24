"""
Project Heimdall: Global Disaster & Environmental Command (Module 3).
Fetches Earthquake (USGS) and Hotspot telemetry, normalizes into GeoJSON FeatureCollections.
"""
import time
import asyncio
from typing import Dict, Any
from .core import BaseDataCollector, BaseDataNormalizer, InMemoryCache, logger
from .config import HEIMDALL_USGS_EARTHQUAKE_URL, FETCH_TIMEOUT, CACHE_TTL_DEFAULT

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class USGSEarthquakeCollector(BaseDataCollector, BaseDataNormalizer):
    """Fetches real-time earthquake data and normalizes it."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        
    async def fetch_data(self) -> dict:
        cache_key = "heimdall_earthquake"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        if not HAS_AIOHTTP:
            return self._mock_data()
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(HEIMDALL_USGS_EARTHQUAKE_URL, timeout=FETCH_TIMEOUT) as response:
                    if response.status == 200:
                        raw_data = await response.json()
                        normalized = self.normalize(raw_data)
                        self.cache.set(cache_key, normalized)
                        return normalized
                    else:
                        logger.error(f"USGS API error: {response.status}")
                        return self._mock_data()
        except Exception as e:
            logger.error(f"Failed to fetch USGS data: {e}")
            return self._mock_data()
            
    def normalize(self, raw_data: dict) -> dict:
        """Adds severity level based on magnitude and normalizes properties."""
        features = raw_data.get("features", [])
        for feature in features:
            mag = feature.get("properties", {}).get("mag", 0)
            if mag is None: mag = 0
            
            if mag >= 7.0:
                severity = "CRITICAL"
            elif mag >= 5.5:
                severity = "HIGH"
            elif mag >= 4.0:
                severity = "MEDIUM"
            else:
                severity = "LOW"
                
            feature["properties"]["severity"] = severity
            feature["properties"]["disaster_type"] = "earthquake"
            
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    def _mock_data(self) -> dict:
        import random
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [random.uniform(-180, 180), random.uniform(-90, 90)]},
                    "properties": {"mag": random.uniform(2.5, 8.0), "place": "Mocked Location", "severity": "MOCK", "disaster_type": "earthquake"}
                } for _ in range(10)
            ]
        }


class HotspotCollector(BaseDataCollector):
    """Fetches NASA FIRMS or simulated Hotspot data."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        
    async def fetch_data(self) -> dict:
        # Mocking NASA FIRMS data for demonstration
        import random
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [random.uniform(98.0, 105.0), random.uniform(10.0, 20.0)]},
                    "properties": {"confidence": random.randint(50, 100), "severity": "HIGH", "disaster_type": "wildfire"}
                } for _ in range(50)
            ]
        }


class HeimdallAggregator:
    """Aggregates Environmental Disaster Data."""
    def __init__(self):
        self.cache = InMemoryCache(ttl=CACHE_TTL_DEFAULT)
        self.usgs = USGSEarthquakeCollector(self.cache)
        self.hotspot = HotspotCollector(self.cache)
        
    async def get_global_disasters(self) -> dict:
        """Fetch all disaster data concurrently."""
        usgs_task = asyncio.create_task(self.usgs.fetch_data())
        hotspot_task = asyncio.create_task(self.hotspot.fetch_data())
        
        results = await asyncio.gather(usgs_task, hotspot_task, return_exceptions=True)
        
        all_features = []
        for res in results:
            if isinstance(res, dict) and "features" in res:
                all_features.extend(res["features"])
                
        return {
            "type": "FeatureCollection",
            "features": all_features
        }
