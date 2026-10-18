import os
import chromadb
import sys
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, 'jarvis_vector_db')
client = chromadb.PersistentClient(path=db_path)

try:
    col = client.get_collection('jarvis_longterm_memory')
    res = col.get()
    
    docs = res['documents']
    ids = res['ids']
    
    target_ids = []
    
    for i, doc in zip(ids, docs):
        if doc and 'ชาเขียว' in doc:
            target_ids.append(i)
            print("Found target to delete in jarvis_longterm_memory:", i)
            
    if target_ids:
        col.delete(ids=target_ids)
        print("Deleted from jarvis_longterm_memory!")
    else:
        print("Not found in jarvis_longterm_memory")
        
except Exception as e:
    print("Error with jarvis_longterm_memory:", e)

try:
    col2 = client.get_collection('personal_memories')
    res2 = col2.get()
    docs2 = res2['documents']
    ids2 = res2['ids']
    
    target_ids2 = []
    for i, doc in zip(ids2, docs2):
        if doc and 'ชาเขียว' in doc:
            target_ids2.append(i)
            print("Found target to delete in personal_memories:", i)
            
    if target_ids2:
        col2.delete(ids=target_ids2)
        print("Deleted from personal_memories!")
    else:
        print("Not found in personal_memories")

except Exception as e:
    print("Error with personal_memories:", e)
