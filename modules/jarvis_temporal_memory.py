"""
jarvis_temporal_memory.py
========================
J.A.R.V.I.S. 20-Year Temporal Cognitive Memory System
Nachapol Industries — Advanced Intelligence Division

สถาปัตยกรรม 4 Layer:
  Layer 2: Episodic Memory   — ChromaDB (เหตุการณ์รายวัน, มี Time-decay)
  Layer 3: Semantic Memory   — SQLite Knowledge Graph (Fact ที่ตกผลึก, มี valid_from/valid_until)
  Layer 4: Identity Memory   — JSON Profile (ตัวตนเจ้านาย, ไม่เปลี่ยน)
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("TemporalMemory")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [TEMPORAL-MEM] %(levelname)s - %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JARVIS_DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")
IDENTITY_FILE = os.path.join(BASE_DIR, "data", "jarvis_identity.json")

# Time-decay half-life
EPISODIC_HALF_LIFE_DAYS = 90    # ความจำรายวัน ลดครึ่งหนึ่งทุก 90 วัน
SEMANTIC_HALF_LIFE_DAYS = 3650  # Fact ที่ตกผลึก คงอยู่นาน ~10 ปี


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class OwnerProfile:
    """Layer 4: ตัวตนที่ไม่เปลี่ยนแปลงของเจ้านาย"""
    name: str = "เจ้านาย"
    preferred_language: str = "th"
    response_style: str = "concise"
    known_projects: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Database Schema Bootstrap
# ---------------------------------------------------------------------------
_EPISODIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text   TEXT NOT NULL,
    jarvis_resp TEXT NOT NULL,
    timestamp   REAL NOT NULL,
    tags        TEXT DEFAULT '[]',
    importance  REAL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_ep_timestamp ON episodic_memory(timestamp);
"""

_KG_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_graph (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_a    TEXT NOT NULL,
    relation    TEXT NOT NULL,
    entity_b    TEXT NOT NULL,
    valid_from  REAL NOT NULL,
    valid_until REAL,
    confidence  REAL DEFAULT 1.0,
    source      TEXT DEFAULT 'conversation',
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kg_entity_a ON knowledge_graph(entity_a);
CREATE INDEX IF NOT EXISTS idx_kg_entity_b ON knowledge_graph(entity_b);
CREATE INDEX IF NOT EXISTS idx_kg_valid    ON knowledge_graph(valid_until);
"""


def _migrate_knowledge_graph(conn: sqlite3.Connection):
    """อัปเกรด schema เดิม เพิ่มคอลัมน์ temporal — idempotent"""
    c = conn.cursor()
    c.execute("PRAGMA table_info(knowledge_graph)")
    existing = {row[1] for row in c.fetchall()}
    migrations = {
        "valid_from":  "ALTER TABLE knowledge_graph ADD COLUMN valid_from REAL",
        "valid_until": "ALTER TABLE knowledge_graph ADD COLUMN valid_until REAL",
        "confidence":  "ALTER TABLE knowledge_graph ADD COLUMN confidence REAL DEFAULT 1.0",
        "source":      "ALTER TABLE knowledge_graph ADD COLUMN source TEXT DEFAULT 'conversation'",
        "created_at":  "ALTER TABLE knowledge_graph ADD COLUMN created_at REAL",
    }
    for col, sql in migrations.items():
        if col not in existing:
            try:
                c.execute(sql)
                logger.info(f"[SCHEMA] Added column: knowledge_graph.{col}")
            except sqlite3.OperationalError as e:
                logger.warning(f"[SCHEMA] Migration skipped ({col}): {e}")
    conn.commit()


def _bootstrap_db():
    """สร้าง/อัปเกรด DB Schema ที่จำเป็น"""
    try:
        with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
            conn.executescript(_EPISODIC_SCHEMA)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_graph'")
            if c.fetchone():
                _migrate_knowledge_graph(conn)
            else:
                conn.executescript(_KG_SCHEMA)
            conn.commit()
        logger.info("[BOOT] Temporal Memory DB ready.")
    except Exception as e:
        logger.error(f"[BOOT] DB bootstrap failed: {e}")


# ---------------------------------------------------------------------------
# Time-Decay
# ---------------------------------------------------------------------------
def _temporal_weight(timestamp: float, half_life_days: float) -> float:
    """weight = 0.5^(age_days / half_life_days)"""
    age_days = (time.time() - timestamp) / 86400.0
    if age_days <= 0:
        return 1.0
    return max(math.pow(0.5, age_days / half_life_days), 0.001)


# ---------------------------------------------------------------------------
# TemporalMemoryManager
# ---------------------------------------------------------------------------
class TemporalMemoryManager:
    """ศูนย์กลางจัดการความจำ 20 ปีของ J.A.R.V.I.S."""

    def __init__(self, chroma_collection=None):
        self._col = chroma_collection
        self._profile: Optional[OwnerProfile] = None
        _bootstrap_db()
        self._load_identity()
        logger.info("[INIT] TemporalMemoryManager ready.")

    # --- Layer 4: Identity ---

    def _load_identity(self):
        try:
            os.makedirs(os.path.dirname(IDENTITY_FILE), exist_ok=True)
            if os.path.exists(IDENTITY_FILE):
                with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._profile = OwnerProfile(**{k: v for k, v in data.items()
                                                if k in OwnerProfile.__dataclass_fields__})
                logger.info(f"[IDENTITY] Loaded profile for '{self._profile.name}'.")
            else:
                self._profile = OwnerProfile()
                self._save_identity()
        except Exception as e:
            logger.warning(f"[IDENTITY] Load failed: {e} — using default.")
            self._profile = OwnerProfile()

    def _save_identity(self):
        try:
            os.makedirs(os.path.dirname(IDENTITY_FILE), exist_ok=True)
            with open(IDENTITY_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._profile), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[IDENTITY] Save failed: {e}")

    def get_identity_context(self) -> str:
        if not self._profile:
            return ""
        lines = [f"[IDENTITY] ชื่อเจ้านาย: {self._profile.name}"]
        if self._profile.known_projects:
            lines.append(f"[IDENTITY] โปรเจกต์: {', '.join(self._profile.known_projects)}")
        for note in self._profile.notes[-5:]:
            lines.append(f"[IDENTITY NOTE] {note}")
        return "\n".join(lines)

    def update_identity(self, key: str, value: Any):
        if self._profile and hasattr(self._profile, key):
            setattr(self._profile, key, value)
            self._profile.last_updated = time.time()
            self._save_identity()

    # --- Layer 2: Episodic Memory ---

    def save_interaction(self, user_text: str, jarvis_response: str,
                         tags: Optional[List[str]] = None, importance: float = 1.0):
        """บันทึกบทสนทนาพร้อม timestamp"""
        now = time.time()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                conn.execute(
                    "INSERT INTO episodic_memory (user_text, jarvis_resp, timestamp, tags, importance) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_text[:2000], jarvis_response[:2000], now, tags_json, importance)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"[EPISODIC] SQLite save failed: {e}")

        if self._col:
            try:
                self._col.add(
                    documents=[f"User: {user_text}\nJARVIS: {jarvis_response}"],
                    metadatas=[{"timestamp": now, "type": "episodic", "tags": tags_json}],
                    ids=[f"ep_{int(now * 1000)}"]
                )
            except Exception as e:
                logger.warning(f"[EPISODIC] ChromaDB save failed: {e}")

    # --- Layer 3: Semantic Memory (Knowledge Graph) ---

    def save_fact(self, entity_a: str, relation: str, entity_b: str,
                  confidence: float = 1.0, source: str = "conversation"):
        """
        บันทึก Fact พร้อม Conflict Resolution
        ถ้า entity_a + relation เดิม entity_b ต่างกัน → ปิด valid_until ของของเก่า
        """
        now = time.time()
        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                existing = conn.execute(
                    "SELECT id, entity_b FROM knowledge_graph "
                    "WHERE entity_a=? AND relation=? AND valid_until IS NULL",
                    (entity_a, relation)
                ).fetchall()

                for row_id, old_val in existing:
                    if old_val != entity_b:
                        conn.execute(
                            "UPDATE knowledge_graph SET valid_until=? WHERE id=?",
                            (now, row_id)
                        )
                        logger.info(
                            f"[CONFLICT] '{entity_a} {relation}' "
                            f"'{old_val}' -> '{entity_b}'"
                        )

                conn.execute(
                    "INSERT INTO knowledge_graph "
                    "(entity_a, relation, entity_b, valid_from, valid_until, confidence, source, created_at) "
                    "VALUES (?, ?, ?, ?, NULL, ?, ?, ?)",
                    (entity_a, relation, entity_b, now, confidence, source, now)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"[SEMANTIC] save_fact failed: {e}")

    # --- Retrieval ---

    def retrieve_memories(self, query: str, top_k: int = 6) -> str:
        """ดึงความจำแบบ Time-aware จากทุก Layer คืน context string"""
        chunks: List[str] = []

        identity = self.get_identity_context()
        if identity:
            chunks.append(identity)

        try:
            semantic = self._retrieve_semantic(query)
            if semantic:
                chunks.append("[SEMANTIC MEMORY (Verified Facts)]:")
                chunks.extend(semantic)
        except Exception as e:
            logger.warning(f"[RETRIEVE] Semantic failed: {e}")

        try:
            episodic = self._retrieve_episodic(query, top_k)
            if episodic:
                chunks.append("[EPISODIC MEMORY (Recent Events)]:")
                chunks.extend(episodic)
        except Exception as e:
            logger.warning(f"[RETRIEVE] Episodic failed: {e}")

        return "\n".join(chunks)

    def _retrieve_semantic(self, query: str) -> List[str]:
        results = []
        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                rows = conn.execute(
                    "SELECT entity_a, relation, entity_b, valid_from, confidence "
                    "FROM knowledge_graph WHERE valid_until IS NULL "
                    "AND (? LIKE '%' || entity_a || '%' OR ? LIKE '%' || entity_b || '%' "
                    "OR entity_a LIKE '%' || ? || '%' OR entity_b LIKE '%' || ? || '%') "
                    "ORDER BY confidence DESC, valid_from DESC LIMIT 8",
                    (query, query, query, query)
                ).fetchall()
                for ea, rel, eb, vf, conf in rows:
                    age = round((time.time() - (vf or time.time())) / 86400)
                    results.append(f"  - {ea} [{rel}] {eb} (อายุ {age} วัน, มั่นใจ {conf:.0%})")
        except Exception as e:
            logger.warning(f"[SEMANTIC RETRIEVE] {e}")
        return results

    def _retrieve_episodic(self, query: str, top_k: int) -> List[str]:
        scored: List[tuple] = []

        if self._col:
            try:
                res = self._col.query(
                    query_texts=[query], n_results=min(top_k * 2, 20),
                    where={"type": "episodic"}
                )
                if res and res.get("documents") and res["documents"][0]:
                    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
                        ts = meta.get("timestamp", time.time())
                        w = _temporal_weight(ts, EPISODIC_HALF_LIFE_DAYS)
                        scored.append((w, doc[:200]))
            except Exception:
                pass

        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                rows = conn.execute(
                    "SELECT user_text, jarvis_resp, timestamp, importance "
                    "FROM episodic_memory ORDER BY timestamp DESC LIMIT 30"
                ).fetchall()
                words = set(query.split())
                for ut, jr, ts, imp in rows:
                    rel = sum(1 for w in words if w in ut) / max(len(words), 1)
                    if rel > 0:
                        w = _temporal_weight(ts, EPISODIC_HALF_LIFE_DAYS) * (imp or 1.0) * rel
                        scored.append((w, f"User: {ut[:100]} -> {jr[:100]}"))
        except Exception as e:
            logger.warning(f"[EPISODIC RETRIEVE] {e}")

        scored.sort(key=lambda x: x[0], reverse=True)
        return [f"  - {t}" for _, t in scored[:top_k]]

    # --- Maintenance ---

    def prune_old_episodic(self, older_than_days: int = 180):
        """ลบ Episodic Memory เก่าที่ไม่สำคัญ"""
        cutoff = time.time() - (older_than_days * 86400)
        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                res = conn.execute(
                    "DELETE FROM episodic_memory WHERE timestamp < ? AND importance < 0.3",
                    (cutoff,)
                )
                conn.commit()
                logger.info(f"[PRUNE] Removed {res.rowcount} old memories.")
        except Exception as e:
            logger.error(f"[PRUNE] {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        try:
            with sqlite3.connect(JARVIS_DB_PATH, timeout=10) as conn:
                stats["episodic_count"] = conn.execute(
                    "SELECT COUNT(*) FROM episodic_memory").fetchone()[0]
                stats["semantic_active"] = conn.execute(
                    "SELECT COUNT(*) FROM knowledge_graph WHERE valid_until IS NULL").fetchone()[0]
                stats["semantic_archived"] = conn.execute(
                    "SELECT COUNT(*) FROM knowledge_graph WHERE valid_until IS NOT NULL").fetchone()[0]
                oldest = conn.execute("SELECT MIN(timestamp) FROM episodic_memory").fetchone()[0]
                if oldest:
                    stats["oldest_memory_days"] = round((time.time() - oldest) / 86400, 1)
        except Exception as e:
            stats["error"] = str(e)
        return stats


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[TemporalMemoryManager] = None


def get_temporal_memory(chroma_collection=None) -> TemporalMemoryManager:
    """Singleton accessor"""
    global _instance
    if _instance is None:
        _instance = TemporalMemoryManager(chroma_collection)
    return _instance
