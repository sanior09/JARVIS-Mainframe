"""
API Controller for Tactical Command Modules.
Exposes Flask Blueprints for Valkyrie, Aegis, and Heimdall.
"""
from flask import Blueprint, Response, jsonify
import asyncio
from .valkyrie_soc import get_soc_report
from .aegis_space import AegisAggregator
from .heimdall_geo import HeimdallAggregator
from .heimdall_radar import get_airspace_radar

tactical_bp = Blueprint('tactical_command', __name__, url_prefix='/tactical')

# Global Integrations
aegis_aggregator = AegisAggregator()
heimdall_aggregator = HeimdallAggregator()

def _async_run(coro):
    """Helper to run async code inside a synchronous Flask view."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Project Valkyrie ---
@tactical_bp.route('/valkyrie/report', methods=['GET'])
def valkyrie_report():
    """API endpoint for Local Network SOC Report."""
    data = get_soc_report()
    return jsonify(data)

# --- Project Aegis ---
@tactical_bp.route('/aegis/space', methods=['GET'])
def aegis_space():
    """API endpoint for 3D Satellite Positions and Space Weather."""
    data = _async_run(aegis_aggregator.get_space_situational_awareness())
    return jsonify(data)

# --- Project Heimdall ---
@tactical_bp.route('/heimdall/disasters', methods=['GET'])
def heimdall_disasters():
    """API endpoint for Global Earthquakes and Hotspots (GeoJSON)."""
    data = _async_run(heimdall_aggregator.get_global_disasters())
    return jsonify(data)

@tactical_bp.route('/heimdall/radar', methods=['GET'])
def heimdall_radar_api():
    """API endpoint for live flight radar."""
    data = get_airspace_radar()
    return jsonify(data)

