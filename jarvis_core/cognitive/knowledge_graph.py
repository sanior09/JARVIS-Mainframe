"""
jarvis_core/cognitive/knowledge_graph.py
─────────────────────────────────────────────────────
Knowledge Graph RAG for J.A.R.V.I.S.
Stores and retrieves Entity-Relation Triplets via SQLite.
"""

import sqlite3
import logging
import threading
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("JARVIS.KnowledgeGraph")

class KnowledgeTriplet:
    def __init__(self, subject: str, predicate: str, object_: str, confidence: float = 1.0, timestamp: str = None):
        self.subject = subject.lower()
        self.predicate = predicate.lower()
        self.object = object_.lower()
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now().isoformat()

class KnowledgeGraphEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="c:/JARVIS/data/jarvis_knowledge_graph.db"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KnowledgeGraphEngine, cls).__new__(cls)
                cls._instance._init_db(db_path)
            return cls._instance

    def _init_db(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triplets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL,
                timestamp TEXT,
                UNIQUE(subject, predicate, object)
            )
        ''')
        self.conn.commit()
        logger.info(f"🕸️ [KnowledgeGraph] Initialized at {db_path}")

    def insert_triplet(self, subject: str, predicate: str, object_: str, confidence: float = 1.0):
        with self._lock:
            try:
                timestamp = datetime.now().isoformat()
                self.cursor.execute('''
                    INSERT OR REPLACE INTO triplets (subject, predicate, object, confidence, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (subject.lower(), predicate.lower(), object_.lower(), confidence, timestamp))
                self.conn.commit()
                logger.info(f"🕸️ [KnowledgeGraph] Added Triplet: ({subject}) -[{predicate}]-> ({object_})")
            except Exception as e:
                logger.error(f"[KnowledgeGraph] Error inserting triplet: {e}")

    def search_by_entity(self, entity: str) -> List[KnowledgeTriplet]:
        with self._lock:
            self.cursor.execute('''
                SELECT subject, predicate, object, confidence, timestamp
                FROM triplets
                WHERE subject = ? OR object = ?
            ''', (entity.lower(), entity.lower()))
            rows = self.cursor.fetchall()
            return [KnowledgeTriplet(*row) for row in rows]

    def multi_hop_traversal(self, start_entity: str, max_hops: int = 2) -> List[KnowledgeTriplet]:
        """
        Traverse the graph from a starting entity up to max_hops.
        Returns a list of triplets.
        """
        start_entity = start_entity.lower()
        visited = set()
        queue = [(start_entity, 0)]
        results = []
        
        while queue:
            current_entity, depth = queue.pop(0)
            if depth >= max_hops or current_entity in visited:
                continue
                
            visited.add(current_entity)
            triplets = self.search_by_entity(current_entity)
            
            for t in triplets:
                if t not in results:
                    results.append(t)
                next_entity = t.object if t.subject == current_entity else t.subject
                if next_entity not in visited:
                    queue.append((next_entity, depth + 1))
                    
        return results

    def get_context_for_query(self, query: str) -> str:
        """
        Extract relevant keywords from the query and pull graph context.
        """
        # Very simple keyword extraction for demonstration
        ignore_words = {"what", "is", "the", "who", "where", "when", "why", "how", "a", "an", "and", "ของ", "คือ", "อะไร", "ใคร"}
        words = [w.strip("?.,!\"'()") for w in query.lower().split() if w not in ignore_words and len(w) > 2]
        
        context_lines = []
        for word in words:
            triplets = self.multi_hop_traversal(word, max_hops=1)
            for t in triplets:
                line = f"- {t.subject} {t.predicate} {t.object} (conf: {t.confidence})"
                if line not in context_lines:
                    context_lines.append(line)
                    
        if not context_lines:
            return ""
        return "Knowledge Graph Context:\n" + "\n".join(context_lines)

    def extract_and_store(self, user_msg: str, ai_response: str = ""):
        """
        Auto-extract factual entity-relation triplets from conversation dialogue and persist into SQLite.
        """
        if not user_msg or len(user_msg.strip()) < 3:
            return

        import re
        text = user_msg.strip()
        extracted = []

        # Thai Semantic Patterns
        thai_patterns = [
            (r"(?:ฉัน|ผม|เรา|เจ้านาย)\s*(?:มี|ซื้อ|ใช้|ชอบ|ถือ)\s*([a-zA-Z0-9_\u0E00-\u0E7F ]+)", "เจ้านาย", "ครอบครอง/ใช้งาน"),
            (r"([a-zA-Z0-9_\u0E00-\u0E7F ]+)\s*(?:คือ|เป็น)\s*([a-zA-Z0-9_\u0E00-\u0E7F ]+)", None, "คือ/เป็น"),
            (r"([a-zA-Z0-9_\u0E00-\u0E7F ]+)\s*(?:อยู่ที่|ตั้งอยู่ที่|อยู่ใน)\s*([a-zA-Z0-9_\u0E00-\u0E7F ]+)", None, "ตำแหน่งที่ตั้ง"),
            (r"([a-zA-Z0-9_\u0E00-\u0E7F ]+)\s*(?:เชื่อมต่อกับ|ทำงานกับ|สั่งการ)\s*([a-zA-Z0-9_\u0E00-\u0E7F ]+)", None, "เชื่อมต่อกับ"),
        ]

        # English Semantic Patterns
        eng_patterns = [
            (r"\b(?:i|user|boss)\s+(?:have|own|use|bought|like|prefer)\s+([a-zA-Z0-9_\- ]+)", "user", "owns/uses"),
            (r"\b([a-zA-Z0-9_\-]+)\s+(?:is|are)\s+([a-zA-Z0-9_\- ]+)", None, "is"),
            (r"\b([a-zA-Z0-9_\-]+)\s+(?:runs on|connected to|operates on)\s+([a-zA-Z0-9_\- ]+)", None, "connected_to"),
        ]

        for pat, fixed_subj, pred in thai_patterns + eng_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                if fixed_subj:
                    obj = m.strip() if isinstance(m, str) else m[0].strip()
                    if 1 < len(obj) < 60:
                        extracted.append((fixed_subj, pred, obj, 0.85))
                elif isinstance(m, tuple) and len(m) == 2:
                    subj, obj = m[0].strip(), m[1].strip()
                    if 1 < len(subj) < 40 and 1 < len(obj) < 60 and subj != obj:
                        extracted.append((subj, pred, obj, 0.8))

        for s, p, o, conf in extracted:
            self.insert_triplet(s, p, o, conf)
