import sqlite3, json, codecs

def dump():
    conn = sqlite3.connect('C:\\JARVIS\\data\\memory_core.db')
    rows = conn.execute("SELECT * FROM semantic_nodes").fetchall()
    with codecs.open('c:\\JARVIS\\semantic_dump.json', 'w', 'utf-8') as f:
        f.write(json.dumps(rows, ensure_ascii=False, indent=2))
        
dump()
