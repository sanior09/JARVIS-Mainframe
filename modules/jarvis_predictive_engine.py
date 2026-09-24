import os
import json
import re
import logging
from dotenv import load_dotenv
from jarvis_core.ai_router import call_groq_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [PREDICTIVE] %(message)s")
load_dotenv(override=True)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_data", "predictive_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class PredictiveEngine:
    def __init__(self):
        self.fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        self.cache_file = os.path.join(CACHE_DIR, "precomputed_answers.json")

    def analyze_and_predict(self, recent_context: str):
        """
        วิเคราะห์บริบทล่าสุด (เช่น คำสั่งล่าสุดที่ผู้ใช้เรียก) 
        และสร้างคำตอบเตรียมไว้ล่วงหน้าสำหรับ 3 คำถามที่คิดว่าผู้ใช้จะถามถัดไป
        """
        logging.info("Analyzing context for predictive pre-computation...")
        
        prompt = f"""
คุณคือ J.A.R.V.I.S. Predictive Engine
ข้อมูลบริบทล่าสุดที่เจ้านายกำลังทำอยู่: "{recent_context}"

จงคาดเดา 3 คำถามที่เจ้านายน่าจะถามถัดไป พร้อมกับเตรียมคำตอบสั้นๆ ไว้ให้

ตอบกลับในรูปแบบ JSON Array ที่มีโครงสร้างดังนี้:
[
  {{"question": "คำถามที่คาดเดา", "answer": "คำตอบที่เตรียมไว้"}}
]
ตอบแค่ JSON Array เท่านั้น ห้ามมีข้อความอื่น
"""
        
        try:
            # Use Groq fast model (high quota, 0.3s) instead of burning Gemini 20 req/day quota
            messages = [{"role": "user", "content": prompt}]
            res = call_groq_model(messages, model=self.fast_model)
            raw_text = res.get("content", "").strip() if res else ""
            
            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if match:
                predictions = json.loads(match.group(0))
            else:
                cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                predictions = json.loads(cleaned) if cleaned else []
                
            if predictions and isinstance(predictions, list):
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(predictions, f, ensure_ascii=False, indent=2)
                logging.info(f"Successfully pre-computed {len(predictions)} potential queries.")
            
        except Exception as e:
            logging.error(f"Error during predictive generation: {e}")

    def get_cached_answer(self, user_query: str) -> str:
        """
        ตรวจสอบว่าคำถามของผู้ใช้ตรงกับที่เดาไว้หรือไม่ 
        (ใช้ logic จับ keyword ง่ายๆ)
        """
        if not os.path.exists(self.cache_file):
            return None
            
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                predictions = json.load(f)
                
            for p in predictions:
                
                query_words = set(user_query.lower().split())
                cache_words = set(p['question'].lower().split())
                if query_words and len(query_words.intersection(cache_words)) / len(query_words) > 0.5:
                    logging.info(f"Predictive Cache HIT for query: {user_query}")
                    return p['answer']
                    
            return None
        except Exception:
            return None

if __name__ == "__main__":
    
    engine = PredictiveEngine()
    engine.analyze_and_predict("ผู้ใช้เพิ่งเปิดโค้ด jarvis_predictive_engine.py ขึ้นมาแก้บั๊ก")
