"""
system_resilience.py
Module 4: Local Offline Docs & System Snapshot Manager

Responsible for managing offline documentation access via vector search
and maintaining system resilience through state snapshots and rollbacks.
"""

import json
import logging
import math
import os
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

# Setup Module Logger
logger = logging.getLogger("SystemResilience")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class ResilienceException(Exception):
    """Base exception for the System Resilience module."""
    pass


class SnapshotRestoreError(ResilienceException):
    """Raised when a system rollback operation fails."""
    pass


class OfflineDocsIndexer:
    """
    A lightweight, offline vector search engine using basic TF-IDF principles.
    In a true production environment, this might wrap ChromaDB or FAISS.
    """
    
    def __init__(self, docs_directory: str):
        self.docs_directory = docs_directory
        self.documents: Dict[str, str] = {}
        self.vocabulary: set = set()
        self.tf_idf_vectors: Dict[str, Dict[str, float]] = {}

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer for document processing."""
        return [word.lower() for word in text.split() if word.isalnum()]

    async def index_documents(self, doc_data: Dict[str, str]):
        """
        Builds the TF-IDF index asynchronously for offline search.
        doc_data is a dictionary of {doc_id: document_content}
        """
        logger.info("Indexing local documents for offline access...")
        import asyncio
        await asyncio.sleep(0.1) # Simulate indexing latency
        
        self.documents = doc_data
        
        # Build vocabulary and Term Frequency (TF)
        doc_tfs = {}
        for doc_id, text in self.documents.items():
            tokens = self._tokenize(text)
            self.vocabulary.update(tokens)
            
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
                
            # Normalize TF
            total_tokens = len(tokens) if tokens else 1
            doc_tfs[doc_id] = {k: v / total_tokens for k, v in tf.items()}
            
        # Build Inverse Document Frequency (IDF)
        num_docs = len(self.documents)
        idfs = {}
        for term in self.vocabulary:
            docs_with_term = sum(1 for tf in doc_tfs.values() if term in tf)
            idfs[term] = math.log(num_docs / (1 + docs_with_term))
            
        # Calculate TF-IDF Vectors
        for doc_id, tf in doc_tfs.items():
            self.tf_idf_vectors[doc_id] = {term: tf_val * idfs.get(term, 0) for term, tf_val in tf.items()}
            
        logger.info(f"Successfully indexed {len(self.documents)} documents.")

    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Searches the indexed documents based on query terms."""
        if not self.tf_idf_vectors:
            raise ResilienceException("Documents must be indexed before searching.")
            
        query_tokens = self._tokenize(query)
        scores = {}
        
        # Very basic scoring based on term presence
        for doc_id, vector in self.tf_idf_vectors.items():
            score = sum(vector.get(token, 0) for token in query_tokens)
            if score > 0:
                scores[doc_id] = score
                
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for doc_id, score in sorted_docs:
            results.append({
                "doc_id": doc_id,
                "score": score,
                "snippet": self.documents[doc_id][:100] + "..."
            })
            
        return results


class SystemSnapshotManager:
    """
    Manages system state backups (Database, Configs) to allow 
    safe rollbacks in case of catastrophic failures or bad code execution.
    """
    
    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = snapshot_dir
        if not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

    async def create_snapshot(self, state_data: Dict[str, Any]) -> str:
        """
        Asynchronously creates a backup snapshot of the system state.
        Returns the snapshot_id.
        """
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(self.snapshot_dir, f"snapshot_{snapshot_id}.json")
        
        logger.info(f"Creating system snapshot: {snapshot_id}")
        import asyncio
        await asyncio.sleep(0.1) # Simulate file IO
        
        try:
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4)
            return snapshot_id
        except IOError as e:
            logger.error(f"Failed to write snapshot {snapshot_id}: {e}")
            raise ResilienceException(f"Snapshot creation failed: {e}")

    async def rollback_to_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Restores the system state from a given snapshot_id.
        """
        snapshot_path = os.path.join(self.snapshot_dir, f"snapshot_{snapshot_id}.json")
        logger.warning(f"INITIATING ROLLBACK TO SNAPSHOT: {snapshot_id}")
        
        import asyncio
        await asyncio.sleep(0.1)
        
        if not os.path.exists(snapshot_path):
            error_msg = f"Snapshot {snapshot_id} not found at {snapshot_path}"
            logger.error(error_msg)
            raise SnapshotRestoreError(error_msg)
            
        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            logger.info("Rollback successful. System state restored.")
            return state_data
        except (IOError, json.JSONDecodeError) as e:
            logger.critical(f"Catastrophic failure during rollback: {e}")
            raise SnapshotRestoreError(f"Failed to read snapshot data: {e}")


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        logger.info("--- Testing OfflineDocsIndexer ---")
        indexer = OfflineDocsIndexer("docs")
        docs = {
            "doc1": "Python is a high-level programming language.",
            "doc2": "C++ is often used for embedded systems.",
            "doc3": "Embedded systems require low latency and high reliability."
        }
        await indexer.index_documents(docs)
        
        results = await indexer.search("embedded systems")
        logger.info("Search Results for 'embedded systems':")
        for res in results:
            logger.info(f" - {res['doc_id']} (Score: {res['score']:.4f}): {res['snippet']}")
            
        logger.info("\\n--- Testing SystemSnapshotManager ---")
        manager = SystemSnapshotManager("test_snapshots")
        
        dummy_state = {
            "active_tasks": 5,
            "memory_usage_mb": 1024,
            "critical_flags": {"safe_mode": False}
        }
        
        snapshot_id = await manager.create_snapshot(dummy_state)
        logger.info(f"Snapshot created with ID: {snapshot_id}")
        
        # Test rollback
        restored_state = await manager.rollback_to_snapshot(snapshot_id)
        logger.info(f"Restored State: {restored_state}")
        
        # Cleanup
        shutil.rmtree("test_snapshots", ignore_errors=True)

    asyncio.run(run_tests())
