import sqlite3

def check_db(db_path):
    print(f"\n--- Checking {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for table in tables:
            t = table[0]
            print(f"Table: {t}")
            if t not in ['memories', 'user_profile', 'knowledge_graph', 'episodes', 'semantic_nodes']:
                continue
            try:
                rows = c.execute(f"SELECT * FROM {t}").fetchall()
                for row in rows:
                    print(row)
            except Exception as e:
                pass
                
    except Exception as e:
        print("DB Error:", e)

import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
check_db(os.path.join(base_dir, 'data', 'jarvis_memory.db'))
check_db(os.path.join(base_dir, 'data', 'memory_core.db'))
check_db(os.path.join(base_dir, 'data', 'jarvis_knowledge_graph.db'))
