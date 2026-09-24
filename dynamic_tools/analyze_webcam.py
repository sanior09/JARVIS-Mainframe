"""
Purpose: Expose webcam vision to the main LLM using the Continuous Vision Daemon cache.
"""
import os
import shutil
import time
import base64
import logging
from dotenv import load_dotenv
from groq import Groq

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_webcam",
        "description": "ถ่ายภาพจากกล้อง Webcam (ดวงตาของจาร์วิส) เพื่อวิเคราะห์ภาพและตอบคำถามที่เจ้านายสงสัย เช่น 'ฉันชูมือกี่นิ้ว', 'ฉันใส่เสื้อสีอะไร'",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "คำถามหรือสิ่งที่ต้องการให้ AI มองหาจากกล้อง เช่น 'ผู้ชายคนนี้ชูมือกี่นิ้ว'"
                }
            },
            "required": ["question"]
        }
    }
}

def analyze_webcam(args):
    question = args.get("question", "อธิบายสิ่งที่คุณเห็นในภาพนี้เป็นภาษาไทย")
    try:
        latest_frame_path = r"c:\JARVIS\data\latest_vision.jpg"
        if not os.path.exists(latest_frame_path):
            return "ไม่พบข้อมูลภาพจากระบบ Continuous Vision ครับเจ้านาย (กรุณาตรวจสอบว่า Vision Daemon ทำงานอยู่หรือไม่)"
            
        with open(latest_frame_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=1)
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question + " (ตอบเป็นภาษาไทยอย่างสั้นและกระชับ)"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }
            ],
            temperature=0.1,
            timeout=10.0
        )
        result_msg = response.choices[0].message.content.strip()
        
        # Prepare image for LINE Bot
        load_dotenv(r"c:\JARVIS\.env")
        ngrok_url = os.getenv("NGROK_PUBLIC_URL", "").strip().rstrip('/')
        
        if ngrok_url:
            save_dir = r"c:\JARVIS\system_cache\temp_images"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            filename = f"webcam_{int(time.time())}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            # Copy to temp_images
            shutil.copy2(latest_frame_path, filepath)
            
            public_url = f"{ngrok_url}/temp_images/{filename}"
            result_msg += f"\n\n(หากต้องการส่งภาพนี้ให้เจ้านายดู กรุณาแนบข้อความนี้ไปด้วย: <img src='{public_url}'>)"
            
        return result_msg
    except Exception as e:
        return f"เกิดข้อผิดพลาดที่ระบบตาข่ายประสาทตา: {e}"
