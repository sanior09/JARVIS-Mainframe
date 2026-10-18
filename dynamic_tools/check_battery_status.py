import psutil
import requests
import os
from dotenv import load_dotenv

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_battery_status",
        "description": "Check the system battery percentage and plugged-in status, and send the report directly to the user's LINE application.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def execute(args):
    """
    Check battery and send LINE alert.
    """
    battery = psutil.sensors_battery()
    if battery is None:
        return "System does not have a battery or cannot read battery status."
    
    percent = int(battery.percent)
    plugged = battery.power_plugged
    
    # Time left
    time_left = ""
    if not plugged and battery.secsleft != psutil.POWER_TIME_UNKNOWN:
        import datetime
        time_left = f" | ⏳ Time left: {datetime.timedelta(seconds=battery.secsleft)}"
    
    plugged_str = "🔌 Plugged In (Charging)" if plugged else "🔋 Not Plugged In (Discharging)"
    report = f"[SYSTEM DIAGNOSTIC]\n{plugged_str}\nBattery Level: {percent}%{time_left}"
    
    # Try to send LINE message
    try:
        # Load env to get token
        base_dir = os.path.dirname(os.path.dirname(__file__))
        load_dotenv(os.path.join(base_dir, ".env"))
        
        line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        line_user_id = os.getenv("LINE_USER_ID")
        
        if line_token and line_user_id:
            url = "https://api.line.me/v2/bot/message/push"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {line_token}"
            }
            data = {
                "to": line_user_id,
                "messages": [{"type": "text", "text": report}]
            }
            res = requests.post(url, headers=headers, json=data, timeout=5)
            if res.status_code == 200:
                return f"Battery is at {percent}%. Notified user via LINE successfully."
            else:
                return f"Battery is at {percent}%. Failed to send LINE message (Status {res.status_code})."
        else:
            return f"Battery is at {percent}%. Could not send LINE message: LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID not configured."
    except Exception as e:
        return f"Battery is at {percent}%. Error sending LINE message: {str(e)}"
