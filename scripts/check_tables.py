import sqlite3

def check(db_path):
    print(f"--- {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        print([x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
    except Exception as e:
        print("Error:", e)
        
check('C:\\JARVIS\\data\\memory_core.db')
check('C:\\JARVIS\\data\\jarvis_memory.db')
