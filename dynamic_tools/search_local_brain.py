"""
Purpose: Search the JARVIS Local RAG Brain
"""

import sys
import os
import logging

logger = logging.getLogger(__name__)

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_local_brain",
        "description": "ค้นหาและวิเคราะห์ข้อมูลจากเอกสาร PDF, Word, Excel ใน jarvis_library (Local RAG Brain) เมื่อเจ้านายถามเกี่ยวกับเอกสารหรือให้สรุปเอกสาร",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "คำถามหรือข้อความที่ต้องการค้นหาในเอกสารอ้างอิง"
                }
            },
            "required": ["query"]
        }
    }
}

def search_local_brain(args):
    query = args.get('query', '')
    if not query:
        return "ท่านเจ้านายยังไม่ได้ระบุคำถามในการค้นหาเอกสารครับ"
        
    try:
        from jarvis_rag_engine import JarvisRAGEngine
        rag = JarvisRAGEngine()
        response = rag.answer_question(query)
        return response
    except Exception as e:
        logger.error(f"[RAG TOOL ERROR] {e}")
        return f"พบข้อผิดพลาดในการดึงข้อมูลจากสมองส่วนเอกสารครับ: {e}"
