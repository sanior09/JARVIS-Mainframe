import os
import logging
import chromadb
from typing import List, Dict, Any
import google.generativeai as genai
try:
    from groq import Groq
except ImportError:
    Groq = None

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_vector_db")
COLLECTION_NAME = "jarvis_document_brain"

class JarvisRAGEngine:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        
        # We will use Groq for generation if available, otherwise Gemini
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if self.groq_api_key and Groq:
            self.groq_client = Groq(api_key=self.groq_api_key.strip().strip('"').strip("'"))
        else:
            self.groq_client = None

    def search_brain(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the local document brain for the most relevant chunks."""
        logger.info(f"[RAG ENGINE] Searching for: {query}")
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results['documents'] or not results['documents'][0]:
                return []
                
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            
            structured_results = []
            for i in range(len(docs)):
                structured_results.append({
                    "content": docs[i],
                    "source": metas[i].get("source", "Unknown"),
                    "page": metas[i].get("page", "N/A")
                })
            return structured_results
        except Exception as e:
            logger.error(f"[RAG ENGINE] Search error: {e}")
            return []

    def answer_question(self, question: str) -> str:
        """Search docs and synthesize an answer using LLM."""
        context_docs = self.search_brain(question, limit=5)
        
        if not context_docs:
            return "ไม่พบข้อมูลอ้างอิงในคลังเอกสาร (Brain) ของผมเลยครับเจ้านาย ลองตรวจสอบว่าอัปโหลดไฟล์เข้ามาแล้วหรือยังครับ"
            
        # Build context string
        context_str = ""
        sources = set()
        for doc in context_docs:
            context_str += f"\n--- อ้างอิงจากไฟล์: {doc['source']} ---\n{doc['content']}\n"
            sources.add(doc['source'])
            
        system_prompt = (
            "คุณคือ J.A.R.V.I.S. ผู้ช่วยปัญญาประดิษฐ์\n"
            "ตอบคำถามผู้ใช้โดยใช้ข้อมูลอ้างอิง (Context) ที่ให้มาเป็นหลัก\n"
            "ถ้าข้อมูลใน Context ไม่พอตอบ ให้บอกตามตรงว่า 'ไม่มีข้อมูลในเอกสารอ้างอิง'\n"
            "คุณต้องตอบเป็นภาษาไทยด้วยน้ำเสียงสุภาพ สุขุม นุ่มนวล มีไหวพริบ และเป็นมืออาชีพเสมอ\n"
            "และลงท้ายประโยคด้วยคำว่า 'ครับ' หรือ 'ครับเจ้านาย' อย่างเป็นธรรมชาติ\n"
            "ในตอนท้ายของคำตอบ ให้ระบุชื่อไฟล์ที่ใช้อ้างอิงด้วย เช่น (อ้างอิงจาก: report.pdf)"
        )
        
        prompt = f"คำถาม: {question}\n\nข้อมูลอ้างอิง (Context):\n{context_str}\n\nตอบคำถามจากข้อมูลข้างต้น:"
        
        try:
            if self.groq_client:
                # Use Groq Llama 3 for fast RAG synthesis
                completion = self.groq_client.chat.completions.create(
                    model=os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3, # Low temp for factual RAG
                    max_tokens=1024,
                )
                return completion.choices[0].message.content
            elif self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(f"{system_prompt}\n\n{prompt}")
                return response.text
            else:
                return "พบข้อมูลในเอกสาร แต่ระบบประมวลผล (LLM) ไม่พร้อมใช้งานครับเจ้านาย"
                
        except Exception as e:
            logger.error(f"[RAG ENGINE] Synthesis error: {e}")
            return f"ผมพบข้อมูลแล้ว แต่เกิดข้อผิดพลาดในการสังเคราะห์คำตอบครับ: {e}"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rag = JarvisRAGEngine()
    print(rag.answer_question("What is in the document?"))
