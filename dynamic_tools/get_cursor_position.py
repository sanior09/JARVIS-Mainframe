"""
Purpose: ดึงพิกัด X และ Y ของเมาส์ในระบบ Windows เพื่อใช้ในการวิเคราะห์ UI ที่ตำแหน่งนั้นๆ
Created: 2026-10-09 13:33:14.820099
"""

import pyautogui

def get_cursor_position(params):
    """
    ดึงพิกัดปัจจุบันของเคอร์เซอร์เมาส์ (X, Y)
    """
    try:
        x, y = pyautogui.position()
        return {"status": "success", "x": x, "y": y}
    except Exception as e:
        return {"status": "error", "message": str(e)}
