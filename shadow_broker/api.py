"""
API Controller Module (Module 3).
Flask Blueprint connecting backend processors to Frontend Dashboard.
"""
from flask import Blueprint, Response, jsonify, request
from .cv_module import CameraStreamer, AIProcessor
from .geo_module import GeospatialAggregator
import asyncio

shadow_bp = Blueprint('shadow_broker', __name__, url_prefix='/shadow')

# Global instances for the blueprint
cv_streamers = {}  # Stream URL/ID -> CameraStreamer
cv_processors = {} # Stream URL/ID -> AIProcessor
geo_aggregator = GeospatialAggregator()


@shadow_bp.route('/stream/cv', methods=['GET'])
def cv_stream():
    """
    Server-Sent Events (SSE) / MJPEG stream endpoint for CV output.
    Query params: `src` (default "0" for webcam).
    """
    src = request.args.get('src', '0')
    
    if src not in cv_streamers:
        streamer = CameraStreamer(stream_url=src)
        streamer.start()
        cv_streamers[src] = streamer
        cv_processors[src] = AIProcessor(streamer)
        
    processor = cv_processors[src]
    
    return Response(
        processor.generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def _async_run(coro):
    """Helper to run async code inside a synchronous Flask view."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@shadow_bp.route('/api/geo', methods=['GET'])
def geo_data():
    """
    Returns aggregated Telemetry (ADS-B/AIS) as GeoJSON.
    Uses asyncio to fetch from multiple providers concurrently.
    """
    data = _async_run(geo_aggregator.get_all_features())
    return jsonify(data)


@shadow_bp.route('/system/cleanup', methods=['POST'])
def cleanup_resources():
    """Stops all running streamers to free memory/GPU."""
    count = 0
    for src, streamer in cv_streamers.items():
        streamer.stop()
        count += 1
        
    cv_streamers.clear()
    cv_processors.clear()
    
    return jsonify({"status": "success", "message": f"Stopped {count} streams."})
