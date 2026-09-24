import sys, json
sys.path.append('c:\\JARVIS')
from jarvis import handle_chat_logic, app
with app.app_context():
    r = handle_chat_logic({'message':'เปิดโปรแกรม antigravity IDE', 'silent':False})
    print(json.dumps(r.get_json(force=True), ensure_ascii=False))

