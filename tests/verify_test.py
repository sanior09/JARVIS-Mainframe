import requests
import time

def test_chat(prompt):
    print(f"Testing: {prompt}")
    resp = requests.post("http://localhost:5050/chat", json={"message": prompt})
    if resp.status_code == 200:
        data = resp.json()
        print("Response:", data.get('response'))
    else:
        print("Failed:", resp.status_code, resp.text)
    print("-" * 50)

test_chat("รันระบบสแกนหาบั๊กในโค้ดตัวเองและทำการซ่อมแซมตัวเอง (Self-Patch) ด่วน")
time.sleep(5)
test_chat("ช่วยจับภาพหน้าจอคอมพิวเตอร์ตอนนี้และเซฟให้หน่อย")
