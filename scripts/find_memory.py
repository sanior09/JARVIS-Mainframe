import os
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
conn = sqlite3.connect(os.path.join(base_dir, 'data', 'memory_core.db'))
c = conn.cursor()

try:
    print("--- semantic_nodes ---")
    rows = c.execute("SELECT * FROM semantic_nodes WHERE subject = 'เจ้านาย'").fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print("semantic_nodes error:", e)
    
try:
    print("--- knowledge_graph ---")
    conn2 = sqlite3.connect(os.path.join(base_dir, 'data', 'jarvis.db'))
    rows2 = conn2.execute("SELECT * FROM knowledge_graph WHERE entity_a = 'เจ้านาย'").fetchall()
    for r in rows2:
        print(r)
except Exception as e:
    print("knowledge_graph error:", e)
