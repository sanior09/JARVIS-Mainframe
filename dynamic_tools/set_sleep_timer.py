import subprocess

TOOL_SCHEMA = {
    "name": "set_sleep_timer",
    "description": "ตั้งเวลาปิดคอมพิวเตอร์ (Shutdown Timer) หรือยกเลิกการตั้งเวลา",
    "parameters": {
        "type": "object",
        "properties": {
            "minutes": {
                "type": "integer",
                "description": "เวลาหน่วยเป็นนาที (ใส่ 0 ถ้ายกเลิก)"
            }
        },
        "required": ["minutes"]
    }
}

def execute(minutes: int) -> str:
    if minutes <= 0:
        try:
            subprocess.run(["shutdown", "-a"], shell=False, check=True)
            return "ยกเลิกการตั้งเวลาปิดเครื่องเรียบร้อยแล้วครับ"
        except subprocess.CalledProcessError:
            return "ไม่มีการตั้งเวลาปิดเครื่องอยู่ก่อนแล้วครับ"
    else:
        seconds = int(minutes * 60)
        # -s (shutdown) -t (time) -f (force close apps)
        subprocess.run(["shutdown", "-s", "-f", "-t", str(seconds)], shell=False)
        
        # Calculate expected shutdown time
        import datetime
        now = datetime.datetime.now()
        shutdown_time = now + datetime.timedelta(seconds=seconds)
        time_str = shutdown_time.strftime("%H:%M")
        
        return f"ระบบตั้งเวลาปิดเครื่อง (Sleep Timer) ในอีก {minutes} นาทีให้แล้วครับ (เครื่องจะดับเวลาประมาณ {time_str})"
