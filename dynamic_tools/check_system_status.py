import psutil
import requests
import os
import shutil
from dotenv import load_dotenv

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_system_status",
        "description": "Perform a comprehensive system diagnostic (CPU, RAM, Disk, Battery, Network) and send the complete report to the user's LINE application.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute(args):
    """
    Check full system status and send LINE alert.
    """
    try:
        # 1. CPU & RAM
        cpu = psutil.cpu_percent(interval=1.0)
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_gb = ram.used / (1024**3)
        ram_total = ram.total / (1024**3)
        
        # 2. Disk Space (C:)
        total, used, free = shutil.disk_usage("C:\\")
        disk_percent = (used / total) * 100
        free_gb = free / (1024**3)
        
        # 3. Battery
        battery_str = "No Battery / Desktop"
        battery = psutil.sensors_battery()
        if battery:
            percent = int(battery.percent)
            plugged = "🔌 Charging" if battery.power_plugged else "🔋 Discharging"
            battery_str = f"{percent}% ({plugged})"
            
        # Compile Report
        report = (
            "📊 [JARVIS SYSTEM DIAGNOSTIC]\n"
            "=======================\n"
            f"🧠 CPU Usage: {cpu}%\n"
            f"⚡ RAM Usage: {ram_percent}% ({ram_gb:.1f}/{ram_total:.1f} GB)\n"
            f"💾 C: Drive: {disk_percent:.1f}% used ({free_gb:.1f} GB free)\n"
            f"🔋 Battery: {battery_str}\n"
            "=======================\n"
            "✅ All Subsystems Online"
        )
        
        # Send via LINE
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
                return f"System check completed. Report sent to LINE.\nCPU: {cpu}%, RAM: {ram_percent}%, Battery: {battery_str}"
            else:
                return f"System checked but failed to send LINE message (Status {res.status_code})."
        else:
            return f"System checked locally. LINE credentials missing.\nCPU: {cpu}%, RAM: {ram_percent}%, Battery: {battery_str}"
            
    except Exception as e:
        return f"Error during system diagnostic: {str(e)}"

# Alias for direct invocation
check_system_status = execute
