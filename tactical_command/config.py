"""
Configuration for Tactical Command Modules.
Contains settings for Valkyrie, Aegis, and Heimdall.
"""
import os

# --- General ---
CACHE_TTL_DEFAULT = int(os.getenv("TACTICAL_CACHE_TTL", "60"))
FETCH_TIMEOUT = int(os.getenv("TACTICAL_FETCH_TIMEOUT", "10"))

# --- Project Valkyrie (SOC & Cyber Threat) ---
VALKYRIE_THREAT_RATE = float(os.getenv("VALKYRIE_THREAT_RATE", "0.5")) # Threats per second (simulated)
VALKYRIE_ALERT_THRESHOLD = int(os.getenv("VALKYRIE_ALERT_THRESHOLD", "10")) # Threats/sec to trigger Critical

# --- Project Aegis (Space) ---
AEGIS_CELESTRAK_URL = os.getenv("AEGIS_CELESTRAK_URL", "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle")
AEGIS_SPACE_WEATHER_URL = os.getenv("AEGIS_SPACE_WEATHER_URL", "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")

# --- Project Heimdall (Disaster) ---
HEIMDALL_USGS_EARTHQUAKE_URL = os.getenv("HEIMDALL_USGS_EARTHQUAKE_URL", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson")
