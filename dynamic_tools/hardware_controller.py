import json
try:
    from jarvis_hardware_bridge import bridge_instance
except (ImportError, ModuleNotFoundError):
    bridge_instance = None

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "hardware_controller",
        "description": "ส่งคำสั่งควบคุมฮาร์ดแวร์ บอร์ดทดลอง Arduino หรือ ESP32 ผ่าน Serial หรือ MQTT",
        "parameters": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string",
                    "enum": ["serial", "mqtt"],
                    "description": "โปรโตคอลที่จะใช้เชื่อมต่อ"
                },
                "target": {
                    "type": "string",
                    "description": "Topic สำหรับ MQTT หรือ 'COMx' สำหรับ Serial"
                },
                "action": {
                    "type": "string",
                    "description": "คำสั่งที่จะส่ง เช่น 'turn_on_led', 'rotate_motor'"
                },
                "value": {
                    "type": "integer",
                    "description": "ค่าตัวเลขที่แนบไป เช่น องศามอเตอร์ 0-180"
                }
            },
            "required": ["protocol", "target", "action"]
        }
    }
}

def hardware_controller(args: dict) -> str:
    protocol = args.get("protocol")
    target = args.get("target")
    payload = {
        "action": args.get("action"),
        "value": args.get("value", 0)
    }
    
    return bridge_instance.send_command(protocol, target, payload)
