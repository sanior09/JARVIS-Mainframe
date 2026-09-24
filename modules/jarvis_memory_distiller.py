import os
import glob
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

LEARNED_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_data")

def distill_memory():
    """
    อ่านไฟล์ .md ใน learned_data ที่มีขนาดใหญ่ แล้วใช้ Gemini สรุปเพื่อลดขนาด (Distillation)
    """
    if not api_key:
        logger.warning("[DISTILLER] GEMINI_API_KEY is not set. Skipping distillation.")
        return "Distillation skipped: No API Key."
        
    logger.info("[DISTILLER] Starting memory distillation process...")
    
    files = glob.glob(os.path.join(LEARNED_DATA_DIR, "*.md"))
    processed = 0
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    for file_path in files:
        filename = os.path.basename(file_path)
        
        if filename.startswith("Distilled_"):
            continue
            
        try:
            size_kb = os.path.getsize(file_path) / 1024
            
            if size_kb > 10:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                prompt = f"""
                คุณคือ J.A.R.V.I.S. AI System หน้าที่ของคุณคือย่อและสกัดข้อมูลสำคัญจากข้อความนี้ 
                ให้เหลือแต่แก่นสารสำคัญ (Key entities, facts, relationships, concepts) 
                เพื่อนำไปเก็บใน Vector Database ให้อยู่ในรูปแบบ Markdown ที่อ่านง่ายและกระชับที่สุด
                เนื้อหา:
                {content}
                """
                
                response = model.generate_content(prompt)
                distilled_text = response.text
                
                distilled_filename = f"Distilled_{filename}"
                distilled_filepath = os.path.join(LEARNED_DATA_DIR, distilled_filename)
                
                with open(distilled_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# [DISTILLED] {filename}\n\n")
                    f.write(distilled_text)
                    
                os.remove(file_path)
                logger.info(f"[DISTILLER] Distilled {filename} successfully.")
                processed += 1
                
        except Exception as e:
            logger.error(f"[DISTILLER] Error distilling {filename}: {e}")
            
    return f"Memory distillation complete. Compressed {processed} files."
