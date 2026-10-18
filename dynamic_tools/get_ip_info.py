"""
Purpose: ดึง IP ภายใน (Local) และ IP สาธารณะ (Public) ของเครื่องที่รัน JARVIS
Created: 2026-09-14 09:11:41.321410
"""

import socket, json, urllib.request

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_ip_info",
        "description": "ดึงข้อมูล IP ภายใน (Local LAN IP) และ IP สาธารณะ (Public IP) ของระบบ JARVIS",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def get_ip_info(params=None) -> dict:
    # Get local IP
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = 'ไม่สามารถดึงได้'
    # Get public IP
    try:
        with urllib.request.urlopen('https://api.ipify.org?format=json', timeout=5) as response:
            data = json.loads(response.read().decode())
            public_ip = data.get('ip', 'ไม่สามารถดึงได้')
    except Exception:
        public_ip = 'ไม่สามารถดึงได้'
    return {'local_ip': local_ip, 'public_ip': public_ip}
