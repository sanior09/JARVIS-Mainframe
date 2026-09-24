"""
Project Heimdall: Global Radar & Tracking (Module 5)
Tracks global flights in real-time using the OpenSky Network API.
"""
import time
import requests
from .core import BaseDataCollector, InMemoryCache, logger

# OpenSky Network API endpoint (No auth required for basic rate limit)
OPENSKY_URL = "https://opensky-network.org/api/states/all"

# Bounding box for Thailand (approximate)
# [lamin, lomin, lamax, lomax]
THAI_BBOX = {
    "lamin": 5.61,
    "lomin": 97.34,
    "lamax": 20.46,
    "lomax": 105.63
}

class HeimdallRadarCollector(BaseDataCollector):
    """Collects real-time flight data."""
    def __init__(self, cache: InMemoryCache):
        super().__init__(cache)
        
    def fetch_flight_data(self, bbox: dict = None) -> dict:
        """Fetch real-time flight data."""
        params = {}
        if bbox:
            params = bbox
            
        try:
            # 10s timeout to prevent locking up
            response = requests.get(OPENSKY_URL, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                states = data.get("states", [])
                
                flights = []
                # Process up to 20 flights to avoid massive payloads
                for state in (states or [])[:20]:
                    flights.append({
                        "callsign": state[1].strip() if state[1] else "UNKNOWN",
                        "country": state[2],
                        "longitude": state[5],
                        "latitude": state[6],
                        "velocity_ms": state[9],
                        "altitude_m": state[13]
                    })
                
                return {
                    "status": "success",
                    "timestamp": time.time(),
                    "total_flights_in_zone": len(states) if states else 0,
                    "sample_flights": flights
                }
            else:
                logger.error(f"[HEIMDALL RADAR] API Error: {response.status_code}")
                return {"status": "error", "error": f"API returned {response.status_code}"}
        except Exception as e:
            logger.error(f"[HEIMDALL RADAR] Fetch Error: {e}")
            return {"status": "error", "error": str(e)}

    def get_local_airspace(self) -> dict:
        """Returns flight data for Thailand airspace, using cache."""
        cache_key = "heimdall_radar_thailand"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        logger.info("[HEIMDALL RADAR] Scanning local airspace...")
        data = self.fetch_flight_data(THAI_BBOX)
        # Cache for 60 seconds (OpenSky updates every 10s, but 60s is safer for free tier)
        self.cache.set(cache_key, data, ttl=60) 
        return data

# Singleton instance
cache_store = InMemoryCache()
heimdall_collector = HeimdallRadarCollector(cache_store)

def get_airspace_radar():
    """Helper function to be called from main JARVIS logic."""
    return heimdall_collector.get_local_airspace()
