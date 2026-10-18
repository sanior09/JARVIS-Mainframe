import sqlite3

conn = sqlite3.connect('C:\\JARVIS\\data\\memory_core.db')
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
    conn2 = sqlite3.connect('C:\\JARVIS\\data\\jarvis.db')
    rows2 = conn2.execute("SELECT * FROM knowledge_graph WHERE entity_a = 'เจ้านาย'").fetchall()
    for r in rows2:
        print(r)
except Exception as e:
    print("knowledge_graph error:", e)
