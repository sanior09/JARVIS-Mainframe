"""
Purpose: จับภาพหน้าจอคอมพิวเตอร์และเซฟลงเครื่อง
Created: 2026-08-15 20:25:07.281723
"""

import os
import pyautogui
from PIL import Image

def capture_screen(params: dict) -> str:
    """จับภาพหน้าจอคอมพิวเตอร์และบันทึกเป็นไฟล์"""
    try:
        screenshot = pyautogui.screenshot()
        filename = params.get("file_name", "screenshot_lab.png") if params else "screenshot_lab.png"
        screenshot.save(filename)
        return f"บันทึกภาพหน้าจอเรียบร้อยแล้วที่ {filename} ครับ"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการจับภาพหน้าจอ: {str(e)}"

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "capture_screen",
        "description": "จับภาพหน้าจอคอมพิวเตอร์และบันทึกเป็นไฟล์ภาพ",
        "parameters": {
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "ชื่อไฟล์ภาพ"}
            }
        }
    }
}
