import os, sqlite3, json, codecs

def dump():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    conn = sqlite3.connect(os.path.join(base_dir, 'data', 'memory_core.db'))
    rows = conn.execute("SELECT * FROM semantic_nodes").fetchall()
    with codecs.open(os.path.join(base_dir, 'semantic_dump.json'), 'w', 'utf-8') as f:
        f.write(json.dumps(rows, ensure_ascii=False, indent=2))
        
dump()
