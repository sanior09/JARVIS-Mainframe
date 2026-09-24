"""
Purpose: อ่านและทำความเข้าใจสิ่งที่อยู่บนหน้าจอคอมพิวเตอร์ปัจจุบัน (Context-Aware Screen Memory)
"""
import os
import pyautogui
import google.generativeai as genai
from PIL import ImageGrab
from dotenv import load_dotenv

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_screen_context",
        "description": "อ่านและทำความเข้าใจสิ่งที่อยู่บนหน้าจอคอมพิวเตอร์ปัจจุบันแบบทันที (ใช้เมื่อเจ้านายถามเกี่ยวกับสิ่งที่กำลังเห็นบนหน้าจอ หรือให้อ่าน/สรุปข้อมูลบนหน้าจอ)",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "คำถามหรือสิ่งที่ต้องการให้วิเคราะห์จากหน้าจอ (เช่น 'ฉันกำลังทำอะไรอยู่', 'สรุปโค้ดบนจอนี้หน่อย')"
                }
            },
            "required": ["question"]
        }
    }
}

def read_screen_context(args):
    question = args.get("question", "สรุปข้อมูลสำคัญทั้งหมดบนหน้าจอนี้")
    
    load_dotenv(r"c:\JARVIS\.env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "เกิดข้อผิดพลาด: ไม่พบ GEMINI_API_KEY ในไฟล์ .env"
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # ถ่ายภาพหน้าจอ
        screenshot = ImageGrab.grab()
        
        prompt = f"""
        คุณคือ J.A.R.V.I.S. ผู้ช่วย AI ที่สามารถมองเห็นหน้าจอคอมพิวเตอร์ของเจ้านายได้
        คำถามของเจ้านายคือ: {question}
        
        กรุณาวิเคราะห์ภาพหน้าจอนี้และตอบคำถามอย่างละเอียด เป็นธรรมชาติ และมีประโยชน์ที่สุด
        หากมีโค้ด ข้อความ หรือข้อมูลสำคัญ ให้ดึงออกมาด้วย
        """
        
        response = model.generate_content([prompt, screenshot])
        return f"[SCREEN CONTEXT VISION]\n{response.text}"
        
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการวิเคราะห์หน้าจอ: {e}"
