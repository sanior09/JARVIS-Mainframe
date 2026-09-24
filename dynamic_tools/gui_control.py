"""
Purpose: GUI Automation Subsystem for J.A.R.V.I.S.
Created: 2024-05-20
"""

import pyautogui
import time
import logging

logger = logging.getLogger(__name__)

def gui_control(args):
    action = args.get('action')
    try:
        if action == 'move':
            x, y = args.get('x', 0), args.get('y', 0)
            pyautogui.moveTo(x, y, duration=0.5)
            return f"Moved pointer to ({x}, {y}) ครับท่าน"
        elif action == 'click':
            if 'x' in args and 'y' in args:
                pyautogui.click(args.get('x'), args.get('y'))
            else:
                pyautogui.click()
            return "ดำเนินการคลิกเรียบร้อยครับ"
        elif action == 'type':
            pyautogui.write(args.get('text', ''), interval=0.1)
            return f"ป้อนข้อความ: '{args.get('text')}' สำเร็จครับ"
        elif action == 'hotkey':
            pyautogui.press(args.get('key', 'space'))
            return f"กดปุ่ม '{args.get('key')}' ให้แล้วครับเจ้านาย"
        return "ขอประทานอภัยครับ คำสั่ง GUI ไม่ชัดเจน"
    except Exception as e:
        return f"GUI Automation Error: {str(e)}"