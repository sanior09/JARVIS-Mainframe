import sys
import os

# Ensure tactical_command is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tactical_command.aegis_osint import get_threat_intel

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_threat_intel",
        "description": "Fetch the latest Cyber Threat Intelligence (OSINT) from security feeds like The Hacker News and CISA.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute(args):
    """
    Entry point for JARVIS to fetch OSINT.
    """
    data = get_threat_intel()
    if data.get("status") == "success":
        report = "OSINT Threat Intelligence Report:\n"
        for item in data.get("threat_intel", []):
            report += f"- [{item['source']}] {item['title']}\n"
        return report
    return "Failed to fetch threat intelligence."
