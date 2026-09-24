"""
J.A.R.V.I.S. iOS Bridge
โมดูลสำหรับเชื่อมต่อและควบคุมอุปกรณ์ iOS (iPhone/iPad)
- Option 1: iCloud Core (pyicloud) สำหรับเช็กพิกัด, แบตเตอรี่, และส่งเสียงร้อง
- Option 2: Pushcut Webhook สำหรับสั่งรัน Shortcuts ระยะไกล
"""

import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("JarvisIOSBridge")

APPLE_ID = os.getenv("APPLE_ID", "")
APPLE_PASSWORD = os.getenv("APPLE_PASSWORD", "")
PUSHCUT_SECRET = os.getenv("PUSHCUT_SECRET", "")

def icloud_controller(action: str) -> str:
    """
    ควบคุม iPhone ผ่าน iCloud
    action: "play_sound", "get_battery", "get_location"
    """
    if not APPLE_ID or not APPLE_PASSWORD:
        return (
            "ข้อผิดพลาด: ยังไม่ได้ตั้งค่า APPLE_ID และ APPLE_PASSWORD ในไฟล์ .env ครับ\n"
            "กรุณาเพิ่มข้อมูลดังนี้ลงในไฟล์ .env ก่อนเรียกใช้งาน:\n"
            "APPLE_ID=your_email@apple.com\n"
            "APPLE_PASSWORD=your_password"
        )
    
    try:
        from pyicloud import PyiCloudService
        from pyicloud.exceptions import PyiCloudFailedLoginException
        
        logger.info(f"Connecting to iCloud for {APPLE_ID}...")
        api = PyiCloudService(APPLE_ID, APPLE_PASSWORD)
        
        if api.requires_2fa:
            return "ข้อผิดพลาด: ระบบ iCloud ของเจ้านายต้องการรหัส 2FA กรุณาเปิด Terminal และรัน 'icloud' เพื่อกรอกรหัสยืนยันตัวตนครั้งแรกครับ"
            
        if not api.devices:
            return "ข้อผิดพลาด: ไม่พบอุปกรณ์ Apple ในบัญชีนี้ครับ"
            
        iphone = None
        for device in api.devices:
            if "iPhone" in device.data.get("deviceClass", ""):
                iphone = device
                break
                
        if not iphone:
            iphone = api.devices[0] 
            
        device_name = iphone.data.get("name", "อุปกรณ์")
        
        if action == "play_sound":
            iphone.play_sound()
            return f"สั่งส่งเสียงเตือนไปยัง '{device_name}' เรียบร้อยแล้วครับ! รีบเดินตามเสียงไปเลยครับ"
            
        elif action == "get_battery":
            try:
                
                status_dict = iphone.status()
                battery_level_raw = status_dict.get("batteryLevel")
                if battery_level_raw is None:
                    battery_level_raw = iphone.data.get("batteryLevel", 0)
                    
                battery_status = status_dict.get("batteryStatus", iphone.data.get("batteryStatus", "Unknown"))
            except Exception as e:
                logger.warning(f"Could not refresh devices status: {e}")
                battery_level_raw = iphone.data.get("batteryLevel", 0)
                battery_status = iphone.data.get("batteryStatus", "Unknown")

            battery_level = round(float(battery_level_raw) * 100) if battery_level_raw is not None else 0
            is_charging = "กำลังชาร์จ" if battery_status == "Charging" else "ไม่ได้ชาร์จ"
                
            return f"แบตเตอรี่ของ '{device_name}' ตอนนี้อยู่ที่ {battery_level}% และ{is_charging}ครับ"
            
        elif action == "get_location":
            try:
                api.devices.refresh()
            except Exception as e:
                pass
            
            location = iphone.location if isinstance(iphone.location, dict) else (iphone.location() if callable(iphone.location) else None)
            
            if location:
                lat = location.get("latitude")
                lon = location.get("longitude")
                return f"พิกัดล่าสุดของ '{device_name}' คือ Latitude: {lat}, Longitude: {lon}\nดูแผนที่: https://maps.google.com/?q={lat},{lon}"
            else:
                return f"ไม่สามารถดึงพิกัดของ '{device_name}' ได้ในขณะนี้ครับ"
        else:
            return f"ไม่รู้จักคำสั่ง: {action}"
            
    except PyiCloudFailedLoginException:
        return "ข้อผิดพลาด: รหัสผ่าน Apple ID หรืออีเมลไม่ถูกต้องครับ"
    except ImportError:
        return "ข้อผิดพลาด: Library 'pyicloud' ยังไม่ได้ติดตั้งครับ รบกวนรอสักครู่ หรือรัน pip install pyicloud"
    except Exception as e:
        logger.error(f"iCloud error: {e}")
        return f"เกิดข้อผิดพลาดในการเชื่อมต่อ iCloud: {e}"

def pushcut_trigger(shortcut_name: str, input_text: str = "") -> str:
    """
    สั่งรัน Apple Shortcuts บน iPhone ผ่านแอป Pushcut
    """
    if not PUSHCUT_SECRET:
        return (
            "ข้อผิดพลาด: ยังไม่ได้ตั้งค่า PUSHCUT_SECRET ในไฟล์ .env ครับ\n"
            "เจ้านายต้องไปที่แอป Pushcut บน iPhone -> Account -> คัดลอก Secret URL มาใส่ใน .env ครับ\n"
            "PUSHCUT_SECRET=your_secret_code"
        )
        
    try:
        
        url = f"https://api.pushcut.io/{PUSHCUT_SECRET}/execute?shortcut={shortcut_name}"
        if input_text:
            url += f"&input={input_text}"
            
        logger.info(f"Triggering shortcut: {shortcut_name}")
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            return f"ส่งคำสั่งรัน Shortcut '{shortcut_name}' ไปยัง iPhone เรียบร้อยแล้วครับ!"
        else:
            return f"เกิดข้อผิดพลาดจาก Pushcut Server (Code: {response.status_code}): {response.text}"
            
    except Exception as e:
        logger.error(f"Pushcut error: {e}")
        return f"ไม่สามารถส่งคำสั่งไปที่ Pushcut ได้: {e}"

TOOL_IOS_ICLOUD = {
    "type": "function",
    "function": {
        "name": "icloud_controller",
        "description": "ควบคุมและเช็กสถานะ iPhone/iPad ผ่าน iCloud (ต้องใช้เครื่องมือนี้เมื่อเจ้านายถามคำถามเกี่ยวกับมือถือ เช่น 'แบตโทรศัพท์เหลือเท่าไหร่', 'แบตไอโฟน', 'โทรศัพท์อยู่ไหน')",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play_sound", "get_battery", "get_location"],
                    "description": "คำสั่งที่ต้องการทำ: 'play_sound' (ส่งเสียงร้องหาเครื่อง), 'get_battery' (เช็กแบต), 'get_location' (ดูพิกัด GPS)"
                }
            },
            "required": ["action"]
        }
    }
}

TOOL_IOS_PUSHCUT = {
    "type": "function",
    "function": {
        "name": "pushcut_trigger",
        "description": "สั่งรัน Apple Shortcuts บน iPhone ระยะไกล (เช่น เปิด/ปิดโหมดห้ามรบกวน, ส่งข้อความ, คุมบ้านอัจฉริยะ)",
        "parameters": {
            "type": "object",
            "properties": {
                "shortcut_name": {
                    "type": "string",
                    "description": "ชื่อของ Shortcut ในแอปคำสั่งลัดบน iPhone ที่ต้องการรัน (พิมพ์ชื่อให้ตรงเป๊ะ)"
                },
                "input_text": {
                    "type": "string",
                    "description": "(Optional) ข้อความหรือข้อมูลเสริมที่จะส่งไปให้ Shortcut นั้นๆ"
                }
            },
            "required": ["shortcut_name"]
        }
    }
}
