"""
J.A.R.V.I.S. Autonomous Learning Protocol (ALP)
- CuriosityEngine: หาหัวข้อที่น่าสนใจ
- WebResearcher: ค้นหาข้อมูลบนเว็บ
- KnowledgeSynthesizer: สรุปและบันทึกลงโฟลเดอร์ knowledge_base
- LearningScheduler: จัดตารางเวลาการเรียนรู้
"""

import os
import time
import random
import logging
import threading
from datetime import datetime
from typing import Optional
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEARNED_DATA_DIR = os.path.join(BASE_DIR, "learned_data")
os.makedirs(LEARNED_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(LEARNED_DATA_DIR, "knowledge.db")

logger = logging.getLogger("JarvisLearning")

CURIOSITY_TOPICS = [
    "Quantum Computing fundamentals and latest breakthroughs",
    "Artificial General Intelligence (AGI) timelines and progress",
    "Advances in Brain-Computer Interfaces like Neuralink",
    "Nuclear Fusion energy latest experiments",
    "CRISPR gene editing newest medical applications",
    "SpaceX Starship and Mars colonization updates",
    "Solid-state battery technology for EVs",
    "Neuromorphic computing and spiking neural networks",
    "Room temperature superconductors research",
    "Exoplanet discovery and James Webb Space Telescope findings"
]

class CuriosityEngine:
    @staticmethod
    def pick_topic() -> str:
        """
        [Context-Aware Curiosity] ให้ AI อ่านประวัติความจำ/แชท 
        เพื่อหาเรื่องที่เจ้านายกำลังสนใจแต่ยังไม่รู้ลึก แล้วเอาไปค้นคว้า
        ถ้าไม่มี Context พิเศษ จะสุ่ม Trend จาก Social Media
        """
        try:
            import os
            from groq import Groq
            import jarvis
            
            memories = ""
            try:
                memories = jarvis.get_recent_memories(limit=20)
            except Exception as e:
                logger.warning(f"[Curiosity] Failed to get memories: {e}")
                
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            if memories and len(memories.strip()) > 20:
                prompt = (
                    f"นี่คือความจำล่าสุดที่ J.A.R.V.I.S. คุยกับเจ้านาย:\n{memories}\n\n"
                    "ในฐานะ AI วิเคราะห์พฤติกรรม จงหา 1 หัวข้อ (Knowledge Gap) ที่เจ้านายน่าจะสนใจเพิ่มเติม "
                    "หรือหัวข้อที่ J.A.R.V.I.S. ควรไปเรียนรู้เพื่อมาตอบคำถามเจ้านายในอนาคตให้ดีขึ้น\n"
                    "ตอบมาเป็นคำค้นหา (Search Query) ภาษาอังกฤษหรือไทยสั้นๆ 1 ประโยค ห้ามมีคำอธิบายเพิ่ม ห้ามมีเครื่องหมายคำพูด"
                )
            else:
                prompt = (
                    "คุณคือ AI Trend Analyst สุ่มเลือก 1 แหล่งข้อมูลจาก (TikTok Viral, Twitter/X Trending, Facebook Hot Topic, Instagram Trends, Wikipedia Featured Article) "
                    "และสร้างคำค้นหา (Search Query) ภาษาอังกฤษหรือไทยสั้นๆ 1 ประโยค สำหรับไปค้นหาเทรนด์ที่น่าสนใจวันนี้ในเว็บ "
                    "ห้ามมีคำอธิบายเพิ่ม ห้ามมีเครื่องหมายคำพูด "
                )
                
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": "You only output the raw search query string. No quotes, no intro."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=40
            )
            raw_content = response.choices[0].message.content
            topic = (raw_content or "").strip(' "\'\n')
            if topic and len(topic) < 150:
                logger.info(f"[Curiosity] Topic Generated: {topic}")
                return topic
        except Exception as e:
            logger.error(f"[Curiosity] Failed to generate context-aware trend: {e}")
            
        topic = random.choice(CURIOSITY_TOPICS)
        logger.info(f"[Curiosity] JARVIS is curious about (Fallback): {topic}")
        return topic

class WebResearcher:
    @staticmethod
    def research(topic: str) -> str:
        """[Deep Research] ค้นหาและดึงเนื้อหาเต็มจากเว็บเพื่อการเรียนรู้เชิงลึก"""
        logger.info(f"[Research] Initiating deep web research for: {topic}")
        try:
            import urllib.request
            import urllib.parse
            import json
            
            encoded_topic = urllib.parse.quote(topic)
            url = f"https://api.duckduckgo.com/?q={encoded_topic}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'JarvisLearning/1.0'})
            
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                data = json.loads(response.read().decode())
                
            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")
            
            if abstract_url:
                logger.info(f"[Research] Deep scraping URL: {abstract_url}")
                try:
                    
                    jina_url = f"https://r.jina.ai/{abstract_url}"
                    jreq = urllib.request.Request(jina_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(jreq, timeout=15) as jresp:  # nosec B310
                        full_content = jresp.read().decode('utf-8')
                        return f"Source: {abstract_url}\n\nContent:\n{full_content[:5000]}"
                except Exception as e:
                    logger.warning(f"[Research] Deep scrape failed, falling back to abstract: {e}")
                    return f"Source: {abstract_url}\n\nAbstract:\n{abstract}"
            
            if abstract:
                return f"Abstract:\n{abstract}"
                
            logger.info(f"[Research] Using Jina Search for: {topic}")
            jina_search_url = f"https://s.jina.ai/{encoded_topic}"
            sreq = urllib.request.Request(jina_search_url, headers={'Accept': 'text/plain'})
            with urllib.request.urlopen(sreq, timeout=15) as sresp:  # nosec B310
                search_content = sresp.read().decode('utf-8')
                return f"Search Results for '{topic}':\n\n{search_content[:5000]}"
                
        except Exception as e:
            logger.error(f"[Research] Error during web research: {e}")
            try:
                import jarvis
                if hasattr(jarvis, "perform_live_web_search_operation"):
                    return jarvis.perform_live_web_search_operation(topic)
            except:
                pass
            return ""

class KnowledgeSynthesizer:
    @staticmethod
    def synthesize_and_save(topic: str, raw_data: str):
        """สรุปและบันทึกลงโฟลเดอร์ knowledge_base โดยใช้ LLM จัดการเนื้อหาและตั้งชื่อไฟล์"""
        if not raw_data or len(raw_data) < 50:
            logger.warning("[Synthesis] Raw data too short or empty. Aborting save.")
            return False

        try:
            import jarvis
            import json
            from groq import Groq
            
            summary_th = "ข้อมูลที่รวบรวมได้ (ดิบ): " + raw_data[:500]
            short_name = "learned_knowledge"
            briefing = ""
            tags = []
            
            try:
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                prompt = (
                    f"คุณคือ J.A.R.V.I.S. เพิ่งค้นคว้าเกี่ยวกับเรื่อง: {topic}\n"
                    f"ข้อมูลที่ได้: {raw_data[:2500]}...\n\n"
                    "คำสั่งที่ 1: สรุปความรู้ที่ได้เป็นภาษาไทยที่อ่านเข้าใจง่าย กระชับ\n"
                    "คำสั่งที่ 2: ตั้งชื่อไฟล์สั้นๆ (ภาษาอังกฤษ snake_case ไม่ต้องใส่ .md) ที่สื่อถึงเรื่องนี้\n"
                    "คำสั่งที่ 3: เตรียม Script สั้นๆ (ไม่เกิน 2 ประโยค) เพื่อเล่าให้เจ้านายฟังในตอนเช้าแบบเท่ๆ (Morning Briefing)\n"
                    "คำสั่งที่ 4: เสนอ Tags (Array of strings)\n\n"
                    "ตอบกลับในรูปแบบ JSON อย่างเคร่งครัด:\n"
                    "{\n"
                    "  \"filename\": \"name_here\",\n"
                    "  \"summary\": \"สรุปภาษาไทย...\",\n"
                    "  \"briefing\": \"เจ้านายครับ เมื่อคืนกระผมได้ศึกษาเรื่อง...\",\n"
                    "  \"tags\": [\"tag1\", \"tag2\"]\n"
                    "}"
                )
                response = client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content or "{}"
                result = json.loads(raw_content)
                short_name = result.get("filename", short_name)
                summary_th = result.get("summary", summary_th)
                briefing = result.get("briefing", "")
                tags = result.get("tags", [])
            except Exception as llm_e:
                logger.error(f"[Synthesis] LLM Error: {llm_e}")

            kb_dir = jarvis.KNOWLEDGE_BASE_DIR
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{short_name}_{timestamp}.md"
            filepath = os.path.join(kb_dir, filename)

            content = f"# ความรู้เรื่อง: {topic}\n"
            content += f"*เรียนรู้อัตโนมัติเมื่อ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
            content += f"**Tags:** {', '.join(tags) if tags else 'General'}\n\n"
            content += "## สรุปความรู้\n"
            content += f"{summary_th}\n\n"
            content += "---\n*This file will be automatically ingested by JARVIS Data Ingestion Engine.*"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"[Synthesis] Knowledge saved to: {filename}")

            # Autonomous Vector Store Ingestion (ChromaDB)
            try:
                import chromadb
                vdb_path = os.path.join(BASE_DIR, "jarvis_vector_db")
                if os.path.exists(vdb_path):
                    client = chromadb.PersistentClient(path=vdb_path)
                    collection = client.get_or_create_collection(name="jarvis_document_brain")
                    doc_id = f"alp_{int(time.time())}_{short_name[:10]}"
                    collection.add(
                        documents=[f"หัวข้อ: {topic}\n\nบทสรุป: {summary_th}"],
                        metadatas=[{"source": filename, "topic": topic, "tags": ",".join(tags) if tags else "General"}],
                        ids=[doc_id]
                    )
                    logger.info(f"[Synthesis] Autonomously ingested '{topic}' into ChromaDB Vector Store.")
            except Exception as vdb_err:
                logger.warning(f"[Synthesis] Vector Store ingestion deferred: {vdb_err}")
            
            if briefing:
                briefing_path = os.path.join(jarvis.BASE_DIR, "data", "morning_briefings.txt") if os.path.exists(os.path.join(jarvis.BASE_DIR, "data", "morning_briefings.txt")) else os.path.join(jarvis.BASE_DIR, "morning_briefings.txt")
                with open(briefing_path, "a", encoding="utf-8") as bf:
                    bf.write(f"[{datetime.now().strftime('%Y-%m-%d')}] {briefing}\n")
                logger.info("[Synthesis] Morning Briefing queued.")
                
            return True
        except Exception as e:
            logger.error(f"[Synthesis] Error saving knowledge: {e}")
            return False

class LearningScheduler:
    def __init__(self, interval_seconds: int = 21600): 
        self.interval = interval_seconds
        self.running = False
        self._thread = None

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="LearningScheduler")
        self._thread.start()
        logger.info("[Learning] Autonomous Learning Protocol started.")

    def stop(self):
        self.running = False

    def _loop(self):
        
        time.sleep(3600) 
        while self.running:
            self.run_learning_cycle()
            time.sleep(self.interval)

    def run_learning_cycle(self, custom_topic: Optional[str] = None) -> str:
        logger.info("[Learning] Starting Learning Cycle...")
        
        topic = custom_topic if custom_topic else CuriosityEngine.pick_topic()
        
        raw_data = WebResearcher.research(topic)
        
        success = KnowledgeSynthesizer.synthesize_and_save(topic, raw_data)
        
        if success:
            return f"JARVIS ได้เรียนรู้เรื่อง '{topic}' และบันทึกลงฐานข้อมูลความรู้สำเร็จแล้วครับเจ้านาย"
        else:
            return f"เกิดข้อผิดพลาดในการเรียนรู้เรื่อง '{topic}' ครับ"

def trigger_learning_cycle_operation(topic: str = "") -> str:
    scheduler = LearningScheduler() 
    if topic:
        return scheduler.run_learning_cycle(custom_topic=topic)
    else:
        return scheduler.run_learning_cycle()

def _ensure_table():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                hour INTEGER,
                day_of_week INTEGER,
                intent TEXT,
                topic TEXT,
                message TEXT
            )
        """)
        conn.commit()

def log_interaction(message: str, intent: str = "unknown"):
    """บันทึก interaction pattern ลง DB เพื่อการเรียนรู้"""
    _ensure_table()
    now = datetime.now()
    
    words = message.lower().split()
    topic = words[0] if words else "unknown"
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "INSERT INTO habit_log (timestamp, hour, day_of_week, intent, topic, message) VALUES (?,?,?,?,?,?)",
                (time.time(), now.hour, now.weekday(), intent, topic, message[:200])
            )
            conn.commit()
    except Exception as e:
        logger.error(f"log_interaction error: {e}")

def get_habit_suggestions() -> str:
    """
    วิเคราะห์ pattern การใช้งาน และ return คำแนะนำ proactive
    เช่น "เจ้านายมักเปิด Spotify ตอนเขียนโค้ด"
    """
    _ensure_table()
    suggestions = []
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            now = datetime.now()
            
            rows = conn.execute(
                "SELECT topic, COUNT(*) as cnt FROM habit_log WHERE hour=? GROUP BY topic ORDER BY cnt DESC LIMIT 3",
                (now.hour,)
            ).fetchall()
            for topic, cnt in rows:
                if cnt >= 3:
                    suggestions.append(f"เจ้านายมักจะพูดถึง '{topic}' ในช่วงเวลานี้")
            
            day_rows = conn.execute(
                "SELECT intent, COUNT(*) as cnt FROM habit_log WHERE day_of_week=? AND intent != 'unknown' GROUP BY intent ORDER BY cnt DESC LIMIT 2",
                (now.weekday(),)
            ).fetchall()
            for intent, cnt in day_rows:
                if cnt >= 5:
                    suggestions.append(f"วันนี้เจ้านายมักใช้คำสั่งประเภท {intent} บ่อย")
    except Exception as e:
        logger.error(f"get_habit_suggestions error: {e}")
    
    if suggestions:
        return "\n[Habit Insights]: " + " | ".join(suggestions)
    return ""

def get_user_preferences() -> dict:
    """Return preferences ที่ JARVIS เรียนรู้มา"""
    _ensure_table()
    prefs = {"favorite_topics": [], "peak_hours": [], "common_intents": []}
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            topics = conn.execute(
                "SELECT topic, COUNT(*) as cnt FROM habit_log GROUP BY topic ORDER BY cnt DESC LIMIT 5"
            ).fetchall()
            prefs["favorite_topics"] = [t for t, _ in topics]

            hours = conn.execute(
                "SELECT hour, COUNT(*) as cnt FROM habit_log GROUP BY hour ORDER BY cnt DESC LIMIT 3"
            ).fetchall()
            prefs["peak_hours"] = [h for h, _ in hours]
    except Exception as e:
        logger.error(f"get_user_preferences error: {e}")
    return prefs

