"""
Project Aegis: Satellite & Space Situational Awareness (Module 2).
Fetches TLE data and calculates real-time 3D orbital positions using SGP4.
Also fetches Space Weather data.
"""
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from .core import BaseDataCollector, InMemoryCache, logger
from .config import AEGIS_CELESTRAK_URL, AEGIS_SPACE_WEATHER_URL, FETCH_TIMEOUT, CACHE_TTL_DEFAULT

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    
try:
    from sgp4.api import Satrec, jday
    HAS_SGP4 = True
except ImportError:
    HAS_SGP4 = False
    logger.warning("sgp4 is not installed. Project Aegis will run in fallback mode. Run 'pip install sgp4' to enable 3D tracking.")

class TLECollector(BaseDataCollector):
    """Fetches Two-Line Element (TLE) sets from Space-Track or Celestrak."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        
    async def fetch_data(self) -> dict:
        cache_key = "aegis_tle_data"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        if not HAS_AIOHTTP:
            return self._mock_tle()
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(AEGIS_CELESTRAK_URL, timeout=FETCH_TIMEOUT) as response:
                    if response.status == 200:
                        text_data = await response.text()
                        parsed = self._parse_tle(text_data)
                        self.cache.set(cache_key, parsed)
                        return parsed
                    else:
                        logger.error(f"TLE API error: {response.status}")
                        return self._mock_tle()
        except Exception as e:
            logger.error(f"Failed to fetch TLE: {e}")
            return self._mock_tle()
            
    def _parse_tle(self, text: str) -> dict:
        lines = text.strip().split('\n')
        satellites = {}
        for i in range(0, len(lines)-2, 3):
            name = lines[i].strip()
            line1 = lines[i+1].strip()
            line2 = lines[i+2].strip()
            satellites[name] = {"line1": line1, "line2": line2}
        return satellites
        
    def _mock_tle(self) -> dict:
        return {
            "ISS (ZARYA)": {
                "line1": "1 25544U 98067A   23275.52627315  .00016717  00000+0  30164-3 0  9997",
                "line2": "2 25544  51.6416 112.5516 0004546  14.2818 107.0306 15.49845356418659"
            }
        }


class SatelliteTracker:
    """Uses SGP4 to calculate real-time Latitude, Longitude, Altitude."""
    def __init__(self, tle_data: dict):
        self.sats = {}
        if HAS_SGP4:
            for name, data in tle_data.items():
                try:
                    self.sats[name] = Satrec.twoline2rv(data["line1"], data["line2"])
                except Exception as e:
                    logger.warning(f"Failed to parse TLE for {name}: {e}")
    
    def get_positions(self) -> List[dict]:
        """Calculates current positions for all loaded satellites."""
        if not HAS_SGP4:
            return [{"name": "ISS (MOCK)", "lat": 0.0, "lon": 0.0, "alt": 400.0}]
            
        now = datetime.utcnow()
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
        
        positions = []
        for name, sat in self.sats.items():
            e, r, v = sat.sgp4(jd, fr)
            if e == 0:
                import math
                # Simple approximation from TEME to LLA (True conversion requires rigorous math, using basic sphere for demo)
                x, y, z = r
                r_norm = math.sqrt(x**2 + y**2 + z**2)
                lat = math.asin(z / r_norm)
                lon = math.atan2(y, x)
                # Earth radius ~ 6371 km
                alt = r_norm - 6371.0 
                
                positions.append({
                    "name": name,
                    "lat": math.degrees(lat),
                    "lon": math.degrees(lon),
                    "alt": alt, # km
                    "velocity_km_s": math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
                })
        return positions


class SpaceWeatherCollector(BaseDataCollector):
    """Fetches Solar Wind / Solar Flare parameters."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        
    async def fetch_data(self) -> dict:
        cache_key = "aegis_space_weather"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        if not HAS_AIOHTTP:
            return {"kp_index": 2.0, "status": "MOCK_NORMAL"}
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(AEGIS_SPACE_WEATHER_URL, timeout=FETCH_TIMEOUT) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Process NOAA JSON
                        try:
                            latest = data[-1]
                            kp = float(latest[1])
                            status = "STORM" if kp > 4 else "NORMAL"
                        except:
                            kp, status = 0.0, "UNKNOWN"
                            
                        res = {"kp_index": kp, "status": status, "timestamp": time.time()}
                        self.cache.set(cache_key, res)
                        return res
                    return {"kp_index": 0.0, "status": "ERROR"}
        except Exception:
            return {"kp_index": 1.5, "status": "MOCK_NORMAL"}


class AegisAggregator:
    """Aggregates Space Data."""
    def __init__(self):
        self.cache = InMemoryCache(ttl=CACHE_TTL_DEFAULT)
        self.tle_collector = TLECollector(self.cache)
        self.weather_collector = SpaceWeatherCollector(self.cache)
        
    async def get_space_situational_awareness(self) -> dict:
        tle_data = await self.tle_collector.fetch_data()
        weather = await self.weather_collector.fetch_data()
        
        tracker = SatelliteTracker(tle_data)
        positions = tracker.get_positions()
        
        return {
            "timestamp": time.time(),
            "space_weather": weather,
            "satellites": positions[:50] # Limit to top 50 for payload size
        }
