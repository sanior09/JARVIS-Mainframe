"""
jarvis_memory_consolidation.py  (Upgraded — Temporal Edition)
=============================================================
Nightly Sleep-Mode Memory Consolidation พร้อม Conflict Resolution
Nachapol Industries
"""

import logging
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("JarvisMemory")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [MEMORY-SLEEP] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Public: Sleep-Mode Consolidation
# ---------------------------------------------------------------------------
def start_sleep_mode_consolidation(chroma_client, llm_engine=None):
    """
    1. ดึง Episodic Memory ล่าสุดจาก SQLite
    2. ให้ LLM สกัด Core Beliefs + Structured Facts
    3. บันทึก Fact ลง Knowledge Graph ผ่าน TemporalMemoryManager (Conflict-safe)
    4. Prune Episodic ที่เก่าและไม่สำคัญ
    """
    logger.info("Initiating Sleep Mode (Temporal Memory Consolidation)...")

    try:
        from jarvis_temporal_memory import get_temporal_memory
        tmem = get_temporal_memory(
            chroma_collection=_safe_get_collection(chroma_client)
        )
    except Exception as e:
        logger.error(f"[SLEEP] Cannot init TemporalMemoryManager: {e}")
        return False

    # --- ดึง Episodic Memory ล่าสุด ---
    try:
        import sqlite3
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_path = os.path.join(BASE_DIR, "data", "jarvis.db")

        with sqlite3.connect(db_path, timeout=10) as conn:
            rows = conn.execute(
                "SELECT user_text, jarvis_resp FROM episodic_memory "
                "ORDER BY timestamp DESC LIMIT 60"
            ).fetchall()

        if len(rows) < 3:
            logger.info(f"[SLEEP] Not enough events ({len(rows)}) to consolidate.")
            return True

        combined = "\n".join([f"User: {r[0]}\nJARVIS: {r[1]}" for r in rows[-30:]])
    except Exception as e:
        logger.error(f"[SLEEP] DB read failed: {e}")
        return False

    # --- ให้ LLM สกัด Facts + Beliefs ---
    try:
        llm = llm_engine or _build_default_llm()
        if not llm:
            logger.warning("[SLEEP] No LLM available. Skipping extraction.")
            return False

        from langchain_core.messages import HumanMessage, SystemMessage
        system_prompt = (
            "You are the Subconscious Module of J.A.R.V.I.S.\n"
            "Analyze the conversation history and extract structured facts.\n\n"
            "Return ONLY a JSON array. Each item must be:\n"
            '{"entity_a": "subject", "relation": "verb", "entity_b": "object", "confidence": 0.0-1.0}\n\n'
            "Examples:\n"
            '[{"entity_a":"เจ้านาย","relation":"ชอบดื่ม","entity_b":"ชาเขียว","confidence":0.9},\n'
            ' {"entity_a":"เจ้านาย","relation":"กำลังพัฒนา","entity_b":"JARVIS","confidence":1.0}]\n\n'
            "Extract only high-confidence facts. Return [] if nothing clear."
        )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation:\n{combined}")
        ])
        raw = response.content.strip()

        # Parse JSON safely
        facts = _parse_json_facts(raw)
        logger.info(f"[SLEEP] Extracted {len(facts)} facts.")

        for fact in facts:
            tmem.save_fact(
                entity_a=fact.get("entity_a", ""),
                relation=fact.get("relation", ""),
                entity_b=fact.get("entity_b", ""),
                confidence=float(fact.get("confidence", 0.8)),
                source="nightly_consolidation"
            )

    except Exception as e:
        logger.error(f"[SLEEP] LLM extraction failed: {e}")
        # ไม่ return False — ทำ Prune ต่อได้

    # --- Prune Episodic เก่า ---
    try:
        tmem.prune_old_episodic(older_than_days=180)
    except Exception as e:
        logger.warning(f"[SLEEP] Prune failed: {e}")

    stats = tmem.get_memory_stats()
    logger.info(
        f"[SLEEP] Consolidation complete. "
        f"Episodic: {stats.get('episodic_count','?')}, "
        f"Semantic active: {stats.get('semantic_active','?')}, "
        f"Archived: {stats.get('semantic_archived','?')}"
    )
    return True


# ---------------------------------------------------------------------------
# Public: get_core_beliefs (backward compat)
# ---------------------------------------------------------------------------
def get_core_beliefs(chroma_client) -> str:
    """
    คืน context string จาก TemporalMemoryManager
    สำหรับ inject เข้า JARVIS_PLANNING_PROMPT ตามเดิม
    """
    try:
        from jarvis_temporal_memory import get_temporal_memory
        col = _safe_get_collection(chroma_client)
        tmem = get_temporal_memory(col)
        # ดึง Semantic Facts ทั่วไป (ไม่ต้อง query เฉพาะ)
        return tmem.retrieve_memories("เจ้านาย preferences beliefs", top_k=4)
    except Exception as e:
        logger.warning(f"[BELIEFS] Fallback to legacy ChromaDB: {e}")
        return _legacy_get_core_beliefs(chroma_client)


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------
def _safe_get_collection(chroma_client):
    try:
        return chroma_client.get_or_create_collection(name="personal_memories")
    except Exception:
        return None


def _build_default_llm():
    try:
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        return ChatGroq(
            model_name=os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            api_key=api_key,
            temperature=0.1
        )
    except Exception as e:
        logger.warning(f"[LLM] Build failed: {e}")
        return None


def _parse_json_facts(raw: str) -> list:
    """Parse JSON array from LLM output ที่อาจมี markdown wrapping"""
    try:
        import json
        # ลองหา JSON array โดยตรง
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(raw)
    except Exception:
        return []


def _legacy_get_core_beliefs(chroma_client) -> str:
    """Legacy fallback สำหรับ ChromaDB โดยตรง"""
    try:
        col = chroma_client.get_collection(name="personal_memories")
        results = col.get(where={"type": "core_belief"})
        if results and results.get("documents"):
            return "\n".join(results["documents"][-3:])
    except Exception:
        pass
    return ""
