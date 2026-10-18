import sqlite3
import time
import json
from datetime import datetime

DB_PATH = 'C:/JARVIS/data/jarvis_memory.db'

# 1. Update user_profile table (directly injected into prompt context)
profile_items = [
    ("full_name", "นายทดสอบ ตัวอย่าง"),
    ("nickname", "เจ้านาย"),
    ("age", "20 ปี"),
    ("birthdate", "1 มกราคม 2548"),
    ("favorite_color", "สีน้ำเงิน"),
    ("favorite_movies", "Sci-Fi, AI"),
    ("past_relationship", "ไม่มี"),
    ("address", "กรุงเทพมหานคร"),
    ("hobby", "เขียนโค้ดและพัฒนา AI"),
    ("glasses", "ไม่มี"),
    ("phone", "สมาร์ทโฟน"),
    ("tablet", "แท็บเล็ต"),
    ("favorite_icecream", "วนิลลา"),
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Insert/replace into user_profile
for k, v in profile_items:
    c.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (k, v))
print("Updated user_profile successfully.")

# 2. Insert into memories table
raw_facts = [
    "เจ้านายชื่อเล่น: เจ้านาย",
    "เจ้านายชอบเขียนโค้ดและพัฒนา AI",
    "เจ้านายชอบหนังแนว Sci-Fi และระบบปัญญาประดิษฐ์",
    "ที่อยู่ของเจ้านาย: กรุงเทพมหานคร",
    "เจ้านายชอบสี: สีน้ำเงิน"
]

for fact in raw_facts:
    c.execute("INSERT INTO memories (timestamp, action, content, tag) VALUES (CURRENT_TIMESTAMP, ?, ?, ?)",
              ("manual_save", fact, "personal_profile"))
print("Added facts to memories table.")

# 3. Insert into knowledge_graph
kg_triples = [
    ("เจ้านาย", "ชื่อเล่น", "เจ้านาย"),
    ("เจ้านาย", "งานอดิเรก", "พัฒนา AI"),
    ("เจ้านาย", "ที่อยู่", "กรุงเทพมหานคร"),
    ("เจ้านาย", "สีโปรด", "สีน้ำเงิน"),
]

for sub, rel, obj in kg_triples:
    c.execute("""
        INSERT INTO knowledge_graph (entity_a, relation, entity_b, confidence, source)
        VALUES (?, ?, ?, 1.0, 'user_explicit')
    """, (sub, rel, obj))
print("Added triples to knowledge_graph.")

conn.commit()
conn.close()

# 4. Insert into ChromaDB
try:
    import chromadb
    client = chromadb.PersistentClient(path='C:/JARVIS/jarvis_vector_db')
    
    # In personal_memories
    p_col = client.get_or_create_collection('personal_memories')
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts = int(time.time())
    
    docs = raw_facts + [
        "ข้อมูลตัวอย่างของเจ้านาย: ชื่นชอบเทคโนโลยีและ AI"
    ]
    ids = [f"user_fact_{ts}_{i}" for i in range(len(docs))]
    metas = [{"timestamp": now_str, "type": "user_profile_verified"} for _ in docs]
    
    p_col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"Added {len(docs)} documents to personal_memories collection.")
    
    # In jarvis_longterm_memory
    lt_col = client.get_or_create_collection('jarvis_longterm_memory')
    lt_ids = [f"lt_fact_{ts}_{i}" for i in range(len(docs))]
    lt_col.add(documents=docs, metadatas=metas, ids=lt_ids)
    print(f"Added {len(docs)} documents to jarvis_longterm_memory collection.")

except Exception as err:
    print("ChromaDB update error:", err)

print("ALL MEMORIES STORED SUCCESSFULLY!")
