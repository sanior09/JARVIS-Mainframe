import os
import shutil
import time
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Splits text into chunks, honoring word boundaries if possible."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
            next_newline = text.rfind('\n', start, end)
            if next_newline != -1 and next_newline > start + chunk_size // 2:
                end = next_newline + 1
            else:
                
                next_space = text.rfind(' ', start, end)
                if next_space != -1 and next_space > start + chunk_size // 2:
                    end = next_space + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return chunks

def run_ingestion(collection, base_dir: str):
    """
    Scans `learned_data` for .md and .txt files, chunks them,
    and inserts them into the given ChromaDB collection.
    """
    if not collection:
        logger.warning("[AUTO-INGEST] ChromaDB collection is None. Skipping.")
        return

    learned_data_dir = os.path.join(base_dir, "learned_data")
    processed_dir = os.path.join(learned_data_dir, "processed")

    if not os.path.exists(learned_data_dir):
        os.makedirs(learned_data_dir)
        
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

    files_processed = 0

    for filename in os.listdir(learned_data_dir):
        if filename.endswith(".md") or filename.endswith(".txt"):
            filepath = os.path.join(learned_data_dir, filename)
            if not os.path.isfile(filepath): continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    continue

                logger.info(f"[AUTO-INGEST] Processing file: {filename}")
                chunks = chunk_text(content)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                docs = []
                metas = []
                ids = []
                
                for i, chunk in enumerate(chunks):
                    
                    docs.append(f"[SOURCE: {filename}]\n{chunk}")
                    metas.append({
                        "timestamp": timestamp, 
                        "type": "knowledge_base",
                        "source": filename,
                        "chunk_idx": i
                    })
                    ids.append(f"kb_{uuid.uuid4().hex[:8]}_{i}")
                
                if docs:
                    collection.add(documents=docs, metadatas=metas, ids=ids)
                    
                dest_path = os.path.join(processed_dir, filename)
                
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    dest_path = os.path.join(processed_dir, f"{base}_{int(time.time())}{ext}")
                
                shutil.move(filepath, dest_path)
                files_processed += 1
                
            except Exception as e:
                logger.error(f"[AUTO-INGEST] Error processing {filename}: {e}")

    if files_processed > 0:
        logger.info(f"[AUTO-INGEST] Successfully ingested {files_processed} files into the cognitive core.")
