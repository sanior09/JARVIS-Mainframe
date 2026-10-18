"""
Purpose: To get the current X and Y coordinates of the mouse cursor on the screen.
Created: 2026-10-09 14:15:25.105996
"""

import pyautogui

def get_mouse_position(params):
    """
    Returns the current mouse cursor position (x, y).
    """
    try:
        x, y = pyautogui.position()
        return {"x": x, "y": y, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}
