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
seen_names = set()

import pyaudio
p = pyaudio.PyAudio()

for i, name in enumerate(mics):
    # กรองพวก Virtual Audio ออกบางส่วนเพื่อให้ดูง่ายขึ้น
    if "Voicemeeter" not in name and "CABLE" not in name and "Steam Streaming" not in name:
        try:
            dev_info = p.get_device_info_by_index(i)
            # เช็คว่าเป็น input device จริงๆ (มีช่องรับเสียง) ไม่ใช่ลำโพง
            if dev_info.get('maxInputChannels', 0) > 0:
                clean_name = name.strip()
                # Windows API มักจะตัดชื่อไมค์เหลือ 31 ตัวอักษร ทำให้เกิดชื่อซ้ำ เราจึงเช็คแค่ 25 ตัวแรก
                base_name = clean_name[:25].lower()
                if base_name not in seen_names:
                    seen_names.add(base_name)
                    display_idx = len(valid_mics)
                    valid_mics.append((i, clean_name))
                    print(f"[{display_idx}] {clean_name}")
        except Exception:
            pass

p.terminate()

print("\n(หมายเหตุ: กรองอุปกรณ์ Output (ลำโพง) และซ่อนไมค์ที่ชื่อซ้ำกัน เพื่อให้เลือกง่ายขึ้น)")
print("=" * 60)

try:
    choice = input("👉 โปรดพิมพ์ตัวเลขหน้าไมโครโฟนที่คุณต้องการใช้ (เช่น 0, 1 หรือ 2) แล้วกด Enter: ")
    display_idx = int(choice.strip())
    
    if display_idx < 0 or display_idx >= len(valid_mics):
        print("\n❌ ตัวเลขไม่ถูกต้อง! โปรดรันสคริปต์นี้ใหม่")
        sys.exit(1)
        
    idx, selected_name = valid_mics[display_idx]
    print(f"\n✅ คุณเลือก: [{display_idx}] {selected_name}")
    
    # อัปเดตไฟล์ .env ในโฟลเดอร์ Root ของโปรเจกต์
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(project_root, ".env")
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
