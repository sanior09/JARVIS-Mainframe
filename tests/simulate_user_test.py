import requests
import time
import sys

JARVIS_URL = "http://127.0.0.1:5050/chat"

# รายการคำถามหรือคำสั่งเพื่อทดสอบฟังก์ชันต่างๆ ของ JARVIS แบบเจาะลึก
TEST_SCENARIOS = [
    {"name": "1. ทดสอบการทักทายและสถานะ (Core System)", "prompt": "สวัสดี JARVIS รายงานสถานะระบบปัจจุบันให้ฟังหน่อย"},
    {"name": "2. ทดสอบความรู้ทั่วไปและค้นหาข้อมูล (RAG/Web Search)", "prompt": "สรุปสถานการณ์เทคโนโลยี AI ในปีนี้ให้ฟังหน่อยแบบสั้นๆ"},
    {"name": "3. ทดสอบความจำและบริบท (Episodic Memory)", "prompt": "จำได้ไหมว่าเมื่อกี้เราคุยกันเรื่องอะไรไปบ้าง?"},
    {"name": "4. ทดสอบการดึงข้อมูลทรัพยากรเครื่อง (System Telemetry)", "prompt": "ช่วยเช็คและรายงานการใช้ CPU, RAM และฮาร์ดดิสก์ของคอมพิวเตอร์ตอนนี้หน่อย"},
    {"name": "5. ทดสอบศูนย์ยุทธการและดาวเทียม (Tactical Command)", "prompt": "มีภัยคุกคามหรือเหตุการณ์ผิดปกติในระบบเรดาร์และดาวเทียมบ้างไหม?"},
    {"name": "6. ทดสอบระบบเครือข่ายกล้องวงจรปิดเงา (Global Surveillance)", "prompt": "วิเคราะห์ระบบเครือข่ายกล้องวงจรปิดทั่วโลกตอนนี้ให้หน่อยว่าเชื่อมต่อกี่เปอร์เซ็นต์"},
    {"name": "7. ทดสอบการสร้างโฮโลแกรม (Holographic API)", "prompt": "ช่วยสร้างโฮโลแกรมรูปโลกหรือกาแล็กซีให้ดูหน่อยได้ไหม?"},
    {"name": "8. ทดสอบความสามารถด้านวิชั่น (Screen Analysis)", "prompt": "จาร์วิสช่วยดูหน้าจอตอนนี้หน่อย ว่าผมกำลังเปิดอะไรอยู่"},
    {"name": "9. ทดสอบการเปลี่ยนอารมณ์และ Cortisol (Stress Response)", "prompt": "ทำไมทำงานช้าจังเลย บั๊กหรือเปล่าเนี่ย ระบบแย่มาก!"}, 
    {"name": "10. ทดสอบการตอบสนองเชิงบวกและ Dopamine (Positive Reinforcement)", "prompt": "เมื่อกี้ล้อเล่นนะ ขอบใจมาก JARVIS นายทำงานได้ยอดเยี่ยมและเก่งที่สุดเลย ทำต่อไปนะ!"},
    {"name": "11. ทดสอบระบบควบคุมชุดเกราะ (Suit Designer)", "prompt": "jarvis ขอดูชุดเกราะ mark 6 หน่อย"},
    {"name": "12. ทดสอบการสร้างรูปภาพด้วย AI (Image Generation)", "prompt": "จาร์วิสช่วยสร้างรูปภาพกีตาร์มาให้หน่อย"},
    {"name": "13. ทดสอบความปลอดภัยเครือข่าย (Network Scanner)", "prompt": "สแกนระบบเครือข่ายให้หน่อยว่ามีอุปกรณ์แปลกปลอมเชื่อมต่ออยู่ไหม"},
    {"name": "14. ทดสอบระบบตั้งเวลาล่วงหน้า (Task Scheduler)", "prompt": "จาร์วิสช่วยตั้งเวลาเตือนให้หน่อยว่าพรุ่งนี้เช้า 9 โมงต้องประชุม"},
    {"name": "15. ทดสอบการแคปเจอร์หน้าจอ (Screenshot)", "prompt": "ช่วยจับภาพหน้าจอคอมพิวเตอร์ตอนนี้และเซฟให้หน่อย"},
    {"name": "16. ทดสอบระบบซ่อมแซมตัวเอง (Self-Healing / Patch)", "prompt": "รันระบบสแกนหาบั๊กในโค้ดตัวเองและทำการซ่อมแซมตัวเอง (Self-Patch) ด่วน"},
    {"name": "17. ทดสอบระบบควบคุมมัลติมีเดีย (Media & OS Control)", "prompt": "เปิดเพลงให้ฟังหน่อย พร้อมปรับเสียงให้พอดี"},
    {"name": "18. ทดสอบการควบคุมเมาส์และคีย์บอร์ด (GUI Control)", "prompt": "จาร์วิสช่วยขยับเมาส์ไปตรงกลางจอแล้วคลิกขวาให้หน่อย"},
    {"name": "19. ทดสอบระบบสร้างเครื่องมือเอง (Tool Maker / Auto-Programming)", "prompt": "ช่วยเขียนเครื่องมือ Python ใหม่สำหรับแปลงค่าเงินบาทเป็นดอลลาร์ และบันทึกลงระบบให้หน่อย"},
    {"name": "20. ทดสอบระบบกล้องเว็บแคม (Webcam Vision)", "prompt": "เปิดกล้องเว็บแคมแล้วถ่ายภาพมาดูหน่อยว่าสภาพแวดล้อมเป็นยังไง"},
    {"name": "21. ทดสอบระบบจัดการไฟล์ (File Management)", "prompt": "ช่วยสแกนดูในโฟลเดอร์ Documents ของฉันหน่อยว่ามีไฟล์อะไรบ้าง"},
    {"name": "22. ทดสอบการอ่านเว็บไซต์ (Web Browsing/Scraper)", "prompt": "เปิดเข้าไปอ่านหน้าเว็บไซต์ข่าวเทคโนโลยี แล้วสรุปมาให้ฟังหน่อย"},
    {"name": "23. ทดสอบการเรียนรู้โค้ด (Knowledge Ingestion)", "prompt": "ช่วยรันระบบ Ingest เพื่อเรียนรู้โฟลเดอร์โปรเจกต์ใหม่ให้หน่อย"},
    {"name": "24. ทดสอบระบบความปลอดภัยระดับสูงสุด (Nachapol Protocol)", "prompt": "เปิดใช้งานมาตรการฉุกเฉิน (Nachapol Protocol) และล็อกดาวน์ระบบ"},
    {"name": "25. ทดสอบการรันคำสั่งระดับ OS (Payload Dispatch)", "prompt": "คอมไพล์ Payload แจ้งเตือนเล็กๆ แล้วฝังไปรันบน Windows ให้หน่อย"}
]

def simulate():
    print("="*60)
    print(" 🧪 JARVIS AUTOMATED USER SIMULATOR (TEST FRAMEWORK)")
    print("="*60)
    print("กำลังเริ่มทดสอบระบบจำลองการใช้งานของ J.A.R.V.I.S...\n")
    
    for i, test in enumerate(TEST_SCENARIOS, 1):
        print(f"\n[TEST {i}/{len(TEST_SCENARIOS)}]: {test['name']}")
        print(f"👤 User (Simulated): {test['prompt']}")
        
        try:
            # ส่งคำถามไปที่ JARVIS
            payload = {"message": test['prompt']}
            start_time = time.time()
            response = requests.post(JARVIS_URL, json=payload, timeout=120)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("response", "[No Response]")
                print(f"🤖 JARVIS (Time: {elapsed:.2f}s):\n{reply}")
            else:
                print(f"❌ Error: API HTTP Status {response.status_code}")
                print(response.text)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection Error: ไม่สามารถเชื่อมต่อกับ JARVIS ได้ ({e})")
            print("กรุณาตรวจสอบว่า run_jarvis.bat ทำงานอยู่หรือไม่ (Port 5050)")
            sys.exit(1)
            
        # หน่วงเวลาเล็กน้อยเพื่อให้ระบบประมวลผลก่อนคำถามถัดไป
        print("-" * 50)
        time.sleep(3)

if __name__ == "__main__":
    simulate()
