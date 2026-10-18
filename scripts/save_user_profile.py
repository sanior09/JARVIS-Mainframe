import sqlite3
import time
import json
from datetime import datetime

DB_PATH = 'C:/JARVIS/data/jarvis_memory.db'

# 1. Update user_profile table (directly injected into prompt context)
profile_items = [
    ("full_name", "นาย ณชพล ศิริพรทุม"),
    ("nickname", "ซาเนียร์"),
    ("age", "17 ปี"),
    ("birthdate", "วันจันทร์ ที่ 1 มิถุนายน 2552"),
    ("favorite_color", "สีฟ้า"),
    ("favorite_movies", "Harry Potter และ จักรวาล Marvel"),
    ("past_relationship", "คนคุยเก่าชื่อโดนัท (เกิดวันที่ 14 กันยายน 2552) ยังคิดถึงอยู่"),
    ("address", "8/204 หมู่บ้านกลางเมืองลาดพร้าว-เสรีไทย เสรีไทย52 แขวงคันนายาว เขตคันนายาว กรุงเทพมหานคร"),
    ("hobby", "ชอบเล่นกีตาร์"),
    ("glasses", "แว่นกรองแสง OWNDAYS × STRANGER THINGS HELLFIRE CLUB Model"),
    ("phone", "iPhone 13"),
    ("tablet", "iPad Air 6"),
    ("favorite_icecream", "ไอศกรีมรสมิ้นท์"),
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Insert/replace into user_profile
for k, v in profile_items:
    c.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (k, v))
print("Updated user_profile successfully.")

# 2. Insert into memories table
raw_facts = [
    "เจ้านายชื่อจริง: นาย ณชพล ศิริพรทุม",
    "เจ้านายชื่อเล่น: ซาเนียร์",
    "เจ้านายอายุ: 17 ปี",
    "เจ้านายเกิดวันจันทร์ ที่ 1 มิถุนายน 2552",
    "เจ้านายชอบสี: สีฟ้า",
    "เจ้านายชอบดูหนัง: Harry Potter กับ จักรวาล Marvel",
    "เจ้านายมีคนคุยเก่าชื่อโดนัท (เกิดวันที่ 14 กันยายน 2552) และยังคิดถึงเค้าอยู่",
    "ที่อยู่ของเจ้านาย: 8/204 หมู่บ้านกลางเมืองลาดพร้าว-เสรีไทย เสรีไทย52 แขวงคันนายาว เขตคันนายาว กรุงเทพฯ",
    "เจ้านายชอบเล่นกีตาร์",
    "เจ้านายใส่แว่นกรองแสง OWNDAYS × STRANGER THINGS HELLFIRE CLUB Model",
    "เจ้านายใช้โทรศัพท์: iPhone 13",
    "เจ้านายมีแท็บเล็ต: iPad Air 6",
    "เจ้านายชอบของหวาน/ไอศกรีม: ไอศกรีมรสมิ้นท์"
]

for fact in raw_facts:
    c.execute("INSERT INTO memories (timestamp, action, content, tag) VALUES (CURRENT_TIMESTAMP, ?, ?, ?)",
              ("manual_save", fact, "personal_profile"))
print("Added facts to memories table.")

# 3. Insert into knowledge_graph
kg_triples = [
    ("เจ้านาย", "ชื่อจริง", "นาย ณชพล ศิริพรทุม"),
    ("เจ้านาย", "ชื่อเล่น", "ซาเนียร์"),
    ("เจ้านาย", "วันเกิด", "1 มิถุนายน 2552 (วันจันทร์)"),
    ("เจ้านาย", "อายุ", "17 ปี"),
    ("เจ้านาย", "สีโปรด", "สีฟ้า"),
    ("เจ้านาย", "ภาพยนตร์โปรด", "Harry Potter"),
    ("เจ้านาย", "ภาพยนตร์โปรด", "จักรวาล Marvel"),
    ("เจ้านาย", "คนคุยเก่า", "โดนัท (เกิด 14 กันยายน 2552)"),
    ("เจ้านาย", "ที่อยู่", "8/204 หมู่บ้านกลางเมืองลาดพร้าว-เสรีไทย เสรีไทย52 แขวงคันนายาว เขตคันนายาว กรุงเทพฯ"),
    ("เจ้านาย", "งานอดิเรก", "เล่นกีตาร์"),
    ("เจ้านาย", "แว่นตา", "OWNDAYS × STRANGER THINGS HELLFIRE CLUB Model"),
    ("เจ้านาย", "โทรศัพท์", "iPhone 13"),
    ("เจ้านาย", "แท็บเล็ต", "iPad Air 6"),
    ("เจ้านาย", "ของกินที่ชอบ", "ไอศกรีมรสมิ้นท์"),
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
        "ข้อมูลส่วนตัวของเจ้านาย: ชื่อ นาย ณชพล ศิริพรทุม (ซาเนียร์) อายุ 17 เกิด 1 มิถุนายน 2552 ชอบสีฟ้า ชอบ Harry Potter และ Marvel มีคนคุยเก่าชื่อโดนัท (14 ก.ย. 2552) ยังคิดถึงอยู่ ที่อยู่ลาดพร้าว-เสรีไทย ชอบเล่นกีตาร์ แว่นตา OWNDAYS Hellfire Club ใช้ iPhone 13, iPad Air 6 ชอบไอศกรีมรสมิ้นท์"
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
