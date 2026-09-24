import sys
import os

# Ensure tactical_command is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tactical_command.heimdall_radar import get_airspace_radar

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_airspace_radar",
        "description": "Scan and track live commercial flights in the local airspace (Thailand) using OpenSky ADS-B data.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute(args):
    """
    Entry point for JARVIS to fetch flight data.
    """
    data = get_airspace_radar()
    if data.get("status") == "success":
        flights = data.get("sample_flights", [])
        total = data.get("total_flights_in_zone", 0)
        report = f"Heimdall Radar: Detected {total} flights in the zone.\n\n"
        for f in flights[:10]: # limit to 10 for brevity
            report += f"- Flight {f['callsign']} ({f['country']}) | Alt: {f['altitude_m']}m | Vel: {f['velocity_ms']}m/s\n"
        return report
    return f"Radar scan failed: {data.get('error', 'Unknown Error')}"
