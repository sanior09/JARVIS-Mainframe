import sys, sqlite3
sys.path.append('c:\\JARVIS')
from jarvis import JARVIS_DB_PATH
conn = sqlite3.connect(JARVIS_DB_PATH)
c = conn.cursor()
c.execute('SELECT content FROM memories WHERE action=''episodic_memory'' ORDER BY id DESC LIMIT 2')
print(c.fetchall())
