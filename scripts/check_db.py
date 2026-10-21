import os
import sqlite3

def check_db():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        conn = sqlite3.connect(os.path.join(base_dir, 'jarvis.db'))
        c = conn.cursor()
        
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print("TABLES:", tables)
        
        for table in tables:
            t = table[0]
            print(f"\n--- {t} ---")
            try:
                rows = c.execute(f"SELECT * FROM {t}").fetchall()  # nosec B608
                for row in rows:
                    print(row)
            except Exception as e:
                print(f"Error reading {t}: {e}")
                
    except Exception as e:
        print("DB Error:", e)

check_db()
