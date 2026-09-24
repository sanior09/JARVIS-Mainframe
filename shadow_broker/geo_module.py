"""
Geospatial Intelligence Module (Module 2).
Asynchronously fetches Telemetry (ADS-B / AIS) with In-Memory caching.
Formats data as GeoJSON FeatureCollection for Leaflet/Mapbox frontend.
"""
import time
import asyncio
from typing import Dict, Any
from .core import BaseGeoProvider, logger
from .config import GEO_ADSB_API_URL, GEO_AIS_API_URL, GEO_CACHE_TTL_SEC, GEO_FETCH_TIMEOUT_SEC

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    logger.warning("aiohttp is not installed. Geospatial Intelligence will run in fallback mode. Run 'pip install aiohttp' to enable.")

class GeoCache:
    """In-memory cache for geospatial data to prevent rate-limiting."""
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._cache = {}
        
    def get(self, key: str) -> dict:
        item = self._cache.get(key)
        if item and (time.time() - item['timestamp'] < self.ttl):
            return item['data']
        return None
        
    def set(self, key: str, data: dict):
        self._cache[key] = {
            'timestamp': time.time(),
            'data': data
        }


class ADSBProvider(BaseGeoProvider):
    """Fetches real-time flight data from OpenSky Network."""
    def __init__(self, cache: GeoCache):
        self.cache = cache
        
    async def fetch_data(self) -> Dict[str, Any]:
        cache_key = "adsb_data"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
            
        if not HAS_AIOHTTP:
            return self._mock_data()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GEO_ADSB_API_URL, timeout=GEO_FETCH_TIMEOUT_SEC) as response:
                    if response.status == 200:
                        data = await response.json()
                        geojson = self._to_geojson(data)
                        self.cache.set(cache_key, geojson)
                        return geojson
                    else:
                        logger.error(f"ADS-B API returned status {response.status}")
                        return self._mock_data()
        except Exception as e:
            logger.error(f"Error fetching ADS-B data: {e}")
            return self._mock_data()

    def _to_geojson(self, data: dict) -> dict:
        """Convert OpenSky state vectors to GeoJSON."""
        features = []
        states = data.get("states", [])
        if not states:
            return {"type": "FeatureCollection", "features": []}
            
        for state in states[:500]: # Limit to 500 for performance
            # state format: [icao24, callsign, origin_country, time_position, last_contact, longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
            try:
                lng, lat = state[5], state[6]
                if lng is None or lat is None:
                    continue
                    
                callsign = state[1].strip() if state[1] else "UNKNOWN"
                velocity = state[9]
                heading = state[10]
                altitude = state[7]
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat]
                    },
                    "properties": {
                        "type": "aircraft",
                        "callsign": callsign,
                        "velocity": velocity,
                        "heading": heading,
                        "altitude": altitude,
                        "country": state[2]
                    }
                })
            except (IndexError, TypeError):
                continue
                
        return {
            "type": "FeatureCollection",
            "features": features
        }

    def _mock_data(self) -> dict:
        """Fallback mock data if API fails or aiohttp is missing."""
        import random
        features = []
        for i in range(20):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [random.uniform(98.0, 105.0), random.uniform(10.0, 20.0)]
                },
                "properties": {
                    "type": "aircraft",
                    "callsign": f"MOCK{i:03d}",
                    "velocity": random.uniform(200, 900),
                    "heading": random.uniform(0, 360),
                    "altitude": random.uniform(1000, 40000),
                    "country": "Mockland"
                }
            })
        return {"type": "FeatureCollection", "features": features}


class AISProvider(BaseGeoProvider):
    """Fetches vessel tracking data."""
    def __init__(self, cache: GeoCache):
        self.cache = cache
        
    async def fetch_data(self) -> Dict[str, Any]:
        # Placeholder for AIS logic
        # Implementation is similar to ADSBProvider
        return {"type": "FeatureCollection", "features": []}


class GeospatialAggregator:
    """Aggregates data from multiple GeoProviders."""
    def __init__(self):
        self.cache = GeoCache(ttl=GEO_CACHE_TTL_SEC)
        self.adsb = ADSBProvider(self.cache)
        self.ais = AISProvider(self.cache)
        
    async def get_all_features(self) -> Dict[str, Any]:
        """Fetch all geo data concurrently."""
        adsb_task = asyncio.create_task(self.adsb.fetch_data())
        ais_task = asyncio.create_task(self.ais.fetch_data())
        
        results = await asyncio.gather(adsb_task, ais_task, return_exceptions=True)
        
        all_features = []
        for res in results:
            if isinstance(res, dict) and "features" in res:
                all_features.extend(res["features"])
                
        return {
            "type": "FeatureCollection",
            "features": all_features
        }
