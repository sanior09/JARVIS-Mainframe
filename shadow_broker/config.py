"""
Configuration for Shadow Broker Modules.
Contains settings for Computer Vision, Geospatial APIs, and general limits.
"""
import os

# --- Computer Vision Module Settings ---
CV_YOLO_MODEL_PATH = os.getenv("CV_YOLO_MODEL_PATH", "yolov8n.pt")
CV_FRAME_QUEUE_MAXSIZE = int(os.getenv("CV_FRAME_QUEUE_MAXSIZE", "30"))
CV_RTSP_TIMEOUT = int(os.getenv("CV_RTSP_TIMEOUT", "10"))
CV_TARGET_FPS = int(os.getenv("CV_TARGET_FPS", "15"))
CV_RECONNECT_DELAY = int(os.getenv("CV_RECONNECT_DELAY", "5"))

# --- Geospatial Intelligence Module Settings ---
GEO_ADSB_API_URL = os.getenv("GEO_ADSB_API_URL", "https://opensky-network.org/api/states/all")
GEO_AIS_API_URL = os.getenv("GEO_AIS_API_URL", "https://dummy-ais-api.local/v1/vessels")  # Placeholder for AIS
GEO_CACHE_TTL_SEC = int(os.getenv("GEO_CACHE_TTL_SEC", "10"))
GEO_FETCH_TIMEOUT_SEC = int(os.getenv("GEO_FETCH_TIMEOUT_SEC", "5"))
