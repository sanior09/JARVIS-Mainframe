"""
jarvis_core/learning/semantic_memory.py
─────────────────────────────────────────────────────────────────────────────
Semantic Long-Term Memory (RAG Architecture with Local Vector DB).
Replaces legacy relational tables with vector-embedded episodic & semantic memory,
featuring temporal decay, hybrid scoring, and intelligent memory consolidation.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

from jarvis_core.learning.interfaces import (
    ISemanticMemoryStore,
    MemoryRecord,
    MemoryTier,
)

logger = logging.getLogger("JARVIS-SemanticMemory")
logger.setLevel(logging.INFO)


class FallbackDenseEmbedding:
    """Lightweight deterministic pseudo-semantic vector generator for offline fallback."""

    EMBEDDING_DIM = 64

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Extract tokens using PyThaiNLP if available, supplemented by character n-grams."""
        tokens = []
        try:
            import pythainlp
            thai_tokens = pythainlp.word_tokenize(text, keep_whitespace=False)
            tokens.extend([t.lower() for t in thai_tokens if len(t.strip()) > 0])
        except Exception:
            pass

        words = text.lower().split()
        tokens.extend(words)

        # Add 3-character n-grams for fuzzy sub-word matching across all languages
        clean = "".join(c for c in text.lower() if not c.isspace())
        if len(clean) >= 3:
            for i in range(len(clean) - 2):
                tokens.append(clean[i : i + 3])

        return tokens or [text.lower()]

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        # Generates a normalized 64-dimensional float vector from tokens and n-grams
        tokens = cls.tokenize(text)
        vec = [0.0] * cls.EMBEDDING_DIM
        for idx, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            slot = h % cls.EMBEDDING_DIM
            vec[slot] += 1.0 / (math.log(idx + 2))

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 5) for x in vec]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        return max(0.0, min(1.0, dot))


class ChromaVectorAdapter:
    """Encapsulates persistent ChromaDB collection interactions with graceful fallback."""

    def __init__(self, collection_name: str = "jarvis_longterm_memory", db_path: str = "./jarvis_vector_db") -> None:
        self.collection_name = collection_name
        self.db_path = db_path
        self.client = None
        self.collection = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import chromadb
            os.makedirs(self.db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.info(f"ChromaDB collection '{self.collection_name}' initialized at {self.db_path}")
        except Exception as err:
            logger.warning(f"ChromaDB not available ({err}). Operating with InMemory Vector fallback.")
            self.client = None
            self.collection = None

    def upsert(self, record_id: str, document: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        if self.collection:
            try:
                # Sanitize metadata for Chroma (strings, ints, floats, bools only)
                clean_meta = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
                self.collection.upsert(
                    ids=[record_id],
                    embeddings=[embedding],
                    documents=[document],
                    metadatas=[clean_meta],
                )
                return True
            except Exception as err:
                logger.error(f"ChromaDB upsert failed: {err}")
        return False

    def query(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if self.collection:
            try:
                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                )
                hits = []
                if results and "ids" in results and results["ids"]:
                    ids = results["ids"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    dists = results.get("distances", [[0.0] * len(ids)])[0]
                    for rid, doc, meta, dist in zip(ids, docs, metas, dists):
                        sim = max(0.0, 1.0 - (dist / 2.0))
                        hits.append({"id": rid, "document": doc, "metadata": meta, "similarity": sim})
                return hits
            except Exception as err:
                logger.error(f"ChromaDB query failed: {err}")
        return []


class SemanticLongTermMemory(ISemanticMemoryStore):
    """
    Production-ready Vector Memory Manager with Recency Decay, Importance Scoring,
    and Memory Consolidation.
    """

    def __init__(self, chroma_adapter: Optional[ChromaVectorAdapter] = None) -> None:
        self.chroma = chroma_adapter or ChromaVectorAdapter()
        # In-memory mirror for fast retrieval and offline resilience
        self._memory_cache: Dict[str, MemoryRecord] = {}

    def store_memory(self, record: MemoryRecord) -> bool:
        """Embeds and indexes a memory record into both ChromaDB and the fast cache."""
        if not record.vector:
            record.vector = FallbackDenseEmbedding.embed_text(record.content)

        record.last_accessed_at = time.time()
        self._memory_cache[record.memory_id] = record

        # Persist to ChromaDB
        meta = {
            "tier": record.tier.value,
            "importance": record.importance,
            "emotional_valence": record.emotional_valence,
            "created_at": record.created_at,
            "access_count": record.access_count,
            **record.metadata,
        }
        self.chroma.upsert(
            record_id=record.memory_id,
            document=record.content,
            embedding=record.vector,
            metadata=meta,
        )
        logger.debug(f"[Semantic Memory] Stored memory: {record.memory_id[:8]}... (Tier: {record.tier.value})")
        return True

    def retrieve_relevant(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.40,
        tier: Optional[MemoryTier] = None,
    ) -> List[MemoryRecord]:
        """
        Hybrid Semantic Retrieval combining:
        1. Cosine Vector Similarity (60% weight)
        2. Exponential Recency Decay (25% weight)
        3. Memory Importance Factor (15% weight)
        """
        query_vec = FallbackDenseEmbedding.embed_text(query)
        scored_candidates: List[tuple[float, MemoryRecord]] = []
        now = time.time()

        for record in self._memory_cache.values():
            if tier and record.tier != tier:
                continue

            # 1. Cosine similarity
            cosine_sim = FallbackDenseEmbedding.cosine_similarity(query_vec, record.vector or [])
            if cosine_sim < min_similarity:
                continue

            # 2. Recency factor: e^(-lambda * dt_hours)
            dt_hours = (now - record.last_accessed_at) / 3600.0
            recency = math.exp(-0.01 * dt_hours)

            # 3. Importance score
            importance = record.importance

            # Composite hybrid score
            composite_score = (0.60 * cosine_sim) + (0.25 * recency) + (0.15 * importance)
            scored_candidates.append((composite_score, record))

        # Sort descending by composite relevance
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_records = [rec for _, rec in scored_candidates[:limit]]

        # Update access telemetry
        for rec in top_records:
            rec.access_count += 1
            rec.last_accessed_at = now

        return top_records

    def prune_or_consolidate(self, decay_threshold_days: int = 30) -> int:
        """
        Prunes memories that have low importance and have not been accessed
        within the decay threshold window.
        """
        now = time.time()
        max_age_sec = decay_threshold_days * 86400.0
        pruned_count = 0

        for mid in list(self._memory_cache.keys()):
            rec = self._memory_cache[mid]
            # Permanent knowledge is immune to pruning
            if rec.tier == MemoryTier.SEMANTIC and rec.importance >= 0.8:
                continue

            age = now - rec.last_accessed_at
            if age > max_age_sec and rec.access_count <= 1 and rec.importance < 0.3:
                del self._memory_cache[mid]
                pruned_count += 1

        logger.info(f"[Semantic Memory] Consolidation complete: {pruned_count} stale items pruned.")
        return pruned_count

    @property
    def records(self) -> Dict[str, MemoryRecord]:
        """Provides access to cached memory records."""
        return self._memory_cache

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics of memories across tiers."""
        total = len(self._memory_cache)
        episodic = sum(1 for r in self._memory_cache.values() if r.tier == MemoryTier.EPISODIC)
        semantic = sum(1 for r in self._memory_cache.values() if r.tier == MemoryTier.SEMANTIC)
        procedural = sum(1 for r in self._memory_cache.values() if r.tier == MemoryTier.PROCEDURAL)
        working = sum(1 for r in self._memory_cache.values() if r.tier == MemoryTier.WORKING)
        return {
            "total_records": total,
            "episodic_count": episodic,
            "semantic_count": semantic,
            "procedural_count": procedural,
            "working_count": working,
        }

