import os
import sys

import speech_recognition as sr

# บังคับใช้ UTF-8 เพื่อให้แสดงภาษาไทยบน Windows CMD ได้
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("  J.A.R.V.I.S. Microphone Setup")
print("=" * 60)
print("กำลังค้นหาไมโครโฟนทั้งหมดในระบบของคุณ...\n")

mics = sr.Microphone.list_microphone_names()
valid_mics = []

for i, name in enumerate(mics):
    # กรองพวก Virtual Audio ออกบางส่วนเพื่อให้ดูง่ายขึ้น
    if "Voicemeeter" not in name and "CABLE" not in name and "Steam Streaming" not in name:
        valid_mics.append((i, name))
        print(f"[{i}] {name}")

print("\n(หมายเหตุ: ซ่อนไมค์จำลอง Voicemeeter และ Steam Streaming เพื่อให้เลือกง่ายขึ้น)")
print("=" * 60)

try:
    choice = input("👉 โปรดพิมพ์ตัวเลขหน้าไมโครโฟนที่คุณต้องการใช้ (เช่น 12 หรือ 42) แล้วกด Enter: ")
    idx = int(choice.strip())
    
    if idx < 0 or idx >= len(mics):
        print("\n❌ ตัวเลขไม่ถูกต้อง! โปรดรันสคริปต์นี้ใหม่")
        sys.exit(1)
        
    print(f"\n✅ คุณเลือก: [{idx}] {mics[idx]}")
    
    # อัปเดตไฟล์ .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env_content = ""
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # ลบ MIC_INDEX เดิมถ้ามี
            env_content = "".join([line for line in lines if not line.startswith("MIC_INDEX=")])
            
    if not env_content.endswith("\n") and env_content != "":
        env_content += "\n"
        
    env_content += f"MIC_INDEX={idx}\n"
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    print(f"\n🎉 บันทึกการตั้งค่าลงในไฟล์ .env สำเร็จ! (MIC_INDEX={idx})")
    print("ระบบ JARVIS จะใช้ไมโครโฟนตัวนี้ในครั้งต่อไปที่คุณรัน run_jarvis.bat")
    
except ValueError:
    print("\n❌ โปรดใส่เป็นตัวเลขเท่านั้น!")
except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาด: {e}")

input("\nกด Enter เพื่อออก...")
