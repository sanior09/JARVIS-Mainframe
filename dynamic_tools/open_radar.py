import webbrowser

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_radar",
        "description": "เปิดหน้าจอ Heimdall Radar (Tactical Flight Tracking) บนเบราว์เซอร์ เพื่อดูเรดาร์เที่ยวบิน Use this when the user asks to open the radar, show the radar, or track flights on the screen.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute(args):
    """
    Entry point for JARVIS to open the radar dashboard.
    """
    url = "http://127.0.0.1:5000/radar"
    try:
        webbrowser.open(url)
        return "เปิดหน้าจอ Heimdall Radar บนเบราว์เซอร์เรียบร้อยแล้วครับ"
    except Exception as e:
        return f"ไม่สามารถเปิดหน้าจอเรดาร์ได้: {e}"
