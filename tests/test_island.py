"""
J.A.R.V.I.S. Dynamic Island — Live Interactive Test & Demo Suite
Allows testing ALL Dynamic Island HUD features inspired by Coucou & modern desktop islands:
1. 🐾 Notch Mascot Buddy & Expressions (idle, happy, thinking, alert, success)
2. 🎭 Mascot Character Skins (mochi, antigravity, codex, cursor, jarvis, gemini)
3. 🤖 AI Agent Watcher & Notifications (Codex finished · 48 tests passed)
4. 🛡️ AI Agent Permission Request (Allow / Deny Action Buttons)
5. 📊 API Plan Usage & Telemetry Gauges (Groq 35%, Gemini 12%, Ollama 0%)
6. 📝 Live Diff Inspector Badge (+48 -12 lines changed)
7. 🚨 Smart Alert / Toast Banners
8. ⚡ Voice State Indicators (LISTENING, THINKING, SPEAKING, STANDBY)
9. 📁 Desktop File Drag & Drop AI Ingestion
"""
import os
import sys
import time
import subprocess
import psutil

# Ensure UTF-8 output on Windows consoles to prevent cp874 emoji encoding crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = r"c:\JARVIS"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from modules.dynamic_island import (
    send_to_island,
    send_toast_to_island,
    send_buddy_mood,
    send_buddy_skin,
    send_agent_event,
    send_usage_gauge,
    send_live_diff,
    send_attach_file
)

def is_island_running() -> bool:
    """Check if dynamic_island.py process is currently running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('dynamic_island.py' in str(arg) for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def terminate_existing_island():
    """Kill any running dynamic_island.py instance to ensure newest code runs"""
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('dynamic_island.py' in str(arg) for arg in cmdline):
                proc.terminate()
                proc.wait(timeout=2)
                killed += 1
        except Exception:
            pass
    if killed > 0:
        time.sleep(1.0)
    return killed

def launch_island(force_restart: bool = False):
    """Launch dynamic_island.py in a background process"""
    if force_restart:
        terminate_existing_island()
    elif is_island_running():
        print("[+] Dynamic Island กำลังทำงานอยู่แล้ว!")
        return None

    print("[*] กำลังเปิด J.A.R.V.I.S. Dynamic Island HUD...")
    creationflags = 0x08000000 if os.name == "nt" else 0

    proc = subprocess.Popen(
        [sys.executable, os.path.join(MODULES_DIR, "dynamic_island.py")],
        cwd=BASE_DIR,
        creationflags=creationflags
    )
    time.sleep(2.0)
    return proc

def run_automated_demo():
    """Run sequential showcase of all Dynamic Island capabilities"""
    print("\n" + "="*62)
    print(" 🏝️  J.A.R.V.I.S. DYNAMIC ISLAND HUD — ALL FEATURES DEMO")
    print("="*62)

    launch_island(force_restart=False)
    time.sleep(1.0)

    # 1. Mascot Expressions
    print("\n[1/10] 🐾 Notch Buddy Mascot: ทดสอบสีหน้า & อาการกะพริบตา...")
    for mood, desc in [
        ("thinking", "🤔 ครุ่นคิด (เหลียวมองด้านบน)"),
        ("happy", "😊 ดีใจ / ยิ้มตาหยี (^ ^)"),
        ("alert", "😲 ตื่นตัว / ตกใจตาโต (O O)"),
        ("success", "😉 ทำงานสำเร็จ / ขยิบตา (^ •)"),
        ("idle", "😴 ปกติ (กระพริบตาเป็นระยะ)")
    ]:
        print(f"      -> Mood: {mood.upper()} - {desc}")
        send_buddy_mood(mood)
        time.sleep(1.8)

    # 2. Wardrobe Character Skins
    print("\n[2/10] 🎭 Notch Buddy Skins: ทดสอบเปลี่ยนสกินตัวละคร (6 แบบ)...")
    skins = [
        ("antigravity", "🟣 Antigravity (ม่วงนีออนล้ำอนาคต)"),
        ("codex", "🟢 OpenAI Codex (เขียวมรกต Dev)"),
        ("cursor", "⚪ Cursor IDE (Slate Dark & Minimal)"),
        ("jarvis", "🔷 JARVIS Arc Reactor (ฟ้าเรืองแสง)"),
        ("gemini", "🔵 Google Gemini (น้ำเงินมิติใหม่)"),
        ("mochi", "🟡 Mochi Coucou (ครีมอบอุ่น Mascot)")
    ]
    for s_name, desc in skins:
        print(f"      -> Skin: {s_name.upper()} - {desc}")
        send_buddy_skin(s_name)
        time.sleep(1.8)

    # 3. AI Coding Agent Event
    print("\n[3/10] 🤖 AI Agent Watcher: แจ้งเตือน Codex ทำงานเสร็จ...")
    print("      -> แสดงหัวข้อ '🟢 Codex finished' พร้อมปุ่ม [Open terminal] และ [OK]")
    send_agent_event(
        agent="Codex",
        status="finished",
        detail="Pushed to main · 48 tests passed · 0 failed",
        buttons="terminal_ok"
    )
    time.sleep(5.0)

    # 4. Agent Permission Request
    print("\n[4/10] 🛡️ Agent Permission: คำขอสิทธิ์จาก Antigravity...")
    print("      -> แสดงหัวข้อ '🟣 Antigravity request' พร้อมปุ่ม [Allow] และ [Deny]")
    send_agent_event(
        agent="Antigravity",
        status="request",
        detail="Execute: pytest -v tests/test_island.py",
        buttons="allow_deny"
    )
    time.sleep(5.0)

    # 5. JARVIS AI Brain Quota & Telemetry Gauges
    print("\n[5/10] 📊 Telemetry Plan Usage Gauges: เกจแสดงการใช้งานโควต้า API...")
    print("      -> Groq Cloud 35% | Google Gemini 12% | Ollama Local 0% | Core Online")
    send_usage_gauge(groq=35, gemini=12, ollama=0)
    time.sleep(5.0)

    # 6. Live Diff Inspector Badge
    print("\n[6/9] 📝 Live Diff Inspector: การเปลี่ยนแปลงโค้ดล่าสุด...")
    print("      -> +48 -12 lines changed (modules/dynamic_island.py)")
    send_live_diff(added=48, removed=12, summary="modules/dynamic_island.py")
    time.sleep(4.5)

    # 7. Smart Alert Toast Banners
    print("\n[7/9] 🚨 Smart Alert / Toast Banner: การแจ้งเตือนสองบรรทัด...")
    send_toast_to_island("LINE Message", "คุณซาเนียร์: จาร์วิส รันระบบ Dynamic Island เรียบร้อยหรือยังครับ", icon="💬")
    time.sleep(5.0)

    # 8. Status Indicators
    print("\n[8/9] ⚡ Status Indicators: จำลองสถานะ JARVIS Core...")
    states = [
        ("LISTENING", "🎙️ LISTENING (กำลังฟังเสียงสั่งการ)"),
        ("THINKING", "🧠 THINKING (AI กำลังประมวลผล)"),
        ("SPEAKING", "🔊 SPEAKING (กำลังพูดตอบกลับ)"),
        ("STANDBY", "✨ STANDBY (พร้อมรับคำสั่ง)")
    ]
    for st, desc in states:
        print(f"      -> {desc}")
        send_to_island(st)
        time.sleep(1.8)

    # 9. Status Indicators
    # 10. File & Image Attachment (+ Button & Drag & Drop)
    print("\n[10/10] 📎 File & Image Attachment (+ Button & Drag & Drop):")
    sample_img = os.path.join(BASE_DIR, "tests", "test_sample.png")
    if os.path.exists(sample_img):
        print(f"      -> จำลองการแนบไฟล์รูปภาพเข้ากล่องแชท: {sample_img}")
        send_attach_file(sample_img)
        send_toast_to_island("📎 แนบไฟล์ตัวอย่างสำเร็จ", "แนบ 'test_sample.png' เข้ากล่องแชทแล้ว (สังเกต Badge ด้านบน)", icon="🖼️")
        time.sleep(4.5)
    else:
        print("      -> คุณสามารถกดปุ่ม '+' หรือลากไฟล์ภาพ/โค้ดมาวางบน Dynamic Island ได้ทันที!")
    print("="*62)
    print(" 🎉 การทดสอบอัตโนมัติครบถ้วนสมบูรณ์ 10/10 รายการ!")
    print("="*62)

def interactive_menu():
    """Interactive CLI menu to trigger custom test events individually"""
    # Ensure island is active before menu starts
    if not is_island_running():
        launch_island()
    else:
        print("[+] Dynamic Island กำลังทำงานอยู่แล้ว!")

    while True:
        print("\n" + "="*50)
        print("   🎮 J.A.R.V.I.S. DYNAMIC ISLAND — เมนูเลือกทดสอบ")
        print("="*50)
        print(" [1]  🐾 เปลี่ยนสีหน้า Notch Buddy (Expressions)")
        print(" [2]  🎭 เปลี่ยนสกินตัวละคร (Default: 🔷 JARVIS Arc Reactor ฟ้าเรืองแสง)")
        print(" [3]  🤖 แจ้งเตือน AI Agent เสร็จสิ้น (Codex / Antigravity)")
        print(" [4]  🛡️ แจ้งเตือนขออนุมัติคำสั่ง (Allow / Deny Action - Live Gate)")
        print(" [5]  📊 แสดงเกจโควต้า API & Streak (Usage Gauges)")
        print(" [6]  📝 แสดง Badge สรุป Live Diff (+48 -12 lines)")
        print(" [7]  🚨 ส่ง Toast แจ้งเตือน (Smart Alert Banner)")
        print(" [8]  ⚡ จำลองสถานะ (LISTENING / THINKING / SPEAKING)")
        print(" [9]  📎 ทดสอบแนบไฟล์ / รูปภาพ (+ Button & Drag-Drop Simulator)")
        print(" [10] 🔄 Restart Dynamic Island HUD")
        print(" [0]  ❌ ออกจากโปรแกรมทดสอบ")
        print("="*50)
        
        choice = input("\nพิมพ์หมายเลขคำสั่ง [0-10]: ").strip()
        
        if choice == "1":
            print("\nเลือกสีหน้า: 1.idle  2.happy  3.thinking  4.alert  5.success")
            m_choice = input("เลือก [1-5]: ").strip()
            mood_map = {"1": "idle", "2": "happy", "3": "thinking", "4": "alert", "5": "success"}
            m = mood_map.get(m_choice, "happy")
            send_buddy_mood(m)
            print(f"[+] เปลี่ยนสีหน้าเป็น {m.upper()} เรียบร้อยแล้ว!")

        elif choice == "2":
            print("\nเลือกสกิน: 1.jarvis (Default)  2.antigravity  3.codex  4.cursor  5.gemini  6.mochi")
            s_choice = input("เลือก [1-6, Enter = jarvis]: ").strip()
            skin_map = {"1": "jarvis", "2": "antigravity", "3": "codex", "4": "cursor", "5": "gemini", "6": "mochi"}
            s = skin_map.get(s_choice, "jarvis")
            send_buddy_skin(s)
            print(f"[+] เปลี่ยนสกินเป็น {s.upper()} เรียบร้อยแล้ว!")

        elif choice == "3":
            ag = input("ชื่อ Agent (Default: Codex): ").strip() or "Codex"
            st = input("สถานะ (Default: finished): ").strip() or "finished"
            dt = input("รายละเอียด (Default: Pushed to main · 48 tests passed): ").strip() or "Pushed to main · 48 tests passed"
            send_agent_event(agent=ag, status=st, detail=dt, buttons="terminal_ok")
            print("[+] ส่งการแจ้งเตือน Agent Watcher เรียบร้อย!")

        elif choice == "4":
            print("\n[🛡️ ทดสอบระบบขออนุมัติความปลอดภัย (Security Approval Gate)]")
            print(" 1. ทดสอบ Gate ดักจับคำสั่งจริง (Live Interception: กด [Allow] / [Deny] บน Island)")
            print(" 2. ส่งจำลองกล่องคำขอบน HUD อย่างเดียว (Visual Test)")
            sub_c = input("เลือกรูปแบบ [1 หรือ 2, Enter = 1]: ").strip() or "1"
            if sub_c == "1":
                cmd_test = input("คำสั่ง Terminal จำลอง (Default: dir): ").strip() or "dir"
                print(f"[*] กำลังรันคำสั่ง '{cmd_test}' เข้าสู่ระบบ J.A.R.V.I.S....")
                print("    👉 กรุณากดปุ่ม [Allow] หรือ [Deny] บน Dynamic Island ด้านบนจอของคุณ!")
                try:
                    from jarvis_core.tool_dispatcher import execute_tool_call
                    result = execute_tool_call({"name": "run_command", "args": {"command": cmd_test}})
                    print(f"\n[+] ผลลัพธ์การประมวลผลคำสั่ง:\n{result}\n")
                except Exception as ex:
                    print(f"[-] เกิดข้อผิดพลาด: {ex}")
            else:
                ag = input("ชื่อ Agent (Default: Security Gate): ").strip() or "Security Gate"
                dt = input("คำสั่งที่ขอรัน (Default: powershell.exe -Command 'dir'): ").strip() or "powershell.exe -Command 'dir'"
                send_agent_event(agent=ag, status="request", detail=dt, buttons="allow_deny")
                print("[+] ส่งกล่องขออนุมัติ [Allow] [Deny] ไปที่ Dynamic Island เรียบร้อย!")

        elif choice == "5":
            print("\n[📊 โควต้า AI Brain Quota]")
            print(" (กด Enter โดยไม่กรอก เพื่อดึงค่าสถิติการใช้งานจริงของวันนี้ หรือกรอก % เอง)")
            g = input("Groq Cloud % (Enter = Live Real Data): ").strip()
            m = input("Google Gemini % (Enter = Live Real Data): ").strip()
            o = input("Ollama Local % (Enter = Live Real Data): ").strip()
            try:
                g_val = int(g) if g else -1
                m_val = int(m) if m else -1
                o_val = int(o) if o else -1
                send_usage_gauge(g_val, m_val, o_val)
                print("[+] ส่งแถบเกจวัดโควต้า JARVIS เรียบร้อยแล้ว!")
            except ValueError:
                print("[-] กรุณากรอกเป็นตัวเลขจำนวนเต็มครับ")

        elif choice == "6":
            add = input("Lines added (Default: 48): ").strip() or "48"
            rem = input("Lines removed (Default: 12): ").strip() or "12"
            note = input("File/Note (Default: modules/dynamic_island.py): ").strip() or "modules/dynamic_island.py"
            try:
                send_live_diff(int(add), int(rem), note)
                print("[+] ส่ง Live Diff Badge เรียบร้อย!")
            except ValueError:
                print("[-] กรุณากรอกจำนวนบรรทัดเป็นตัวเลขครับ")

        elif choice == "7":
            title = input("หัวข้อแจ้งเตือน (Default: ข้อความใหม่): ").strip() or "ข้อความใหม่"
            msg = input("เนื้อหา (Default: ระบบ J.A.R.V.I.S. พร้อมทำงาน): ").strip() or "ระบบ J.A.R.V.I.S. พร้อมทำงาน"
            icon = input("Icon Emoji (Default: 🔔): ").strip() or "🔔"
            send_toast_to_island(title, msg, icon=icon)
            print("[+] ส่ง Toast เรียบร้อยแล้วครับ!")

        elif choice == "8":
            print("\nเลือกสถานะ: 1.LISTENING  2.THINKING  3.SPEAKING  4.STANDBY")
            st_choice = input("เลือก [1-4]: ").strip()
            st_map = {"1": "LISTENING", "2": "THINKING", "3": "SPEAKING", "4": "STANDBY"}
            send_to_island(st_map.get(st_choice, "STANDBY"))
            print("[+] อัปเดตสถานะเรียบร้อย!")

        elif choice == "9":
            print("\n" + "-"*50)
            print(" [📎 เมนูทดสอบแนบไฟล์และรูปภาพ]")
            print(" 1. แนบรูปภาพตัวอย่างเข้ากล่องแชททันที (test_sample.png)")
            print(" 2. แนบไฟล์เอกสารในโปรเจกต์ (requirements.txt)")
            print(" 3. เปิดโฟลเดอร์ไฟล์ตัวอย่างบน Windows Explorer (ลองใช้เมาส์ลากวาง)")
            print(" 4. ระบุที่อยู่ไฟล์เอง (Custom File Path)")
            print("-"*50)
            sub_c = input("เลือก [1-4, Enter = 1]: ").strip() or "1"
            
            img_path = os.path.join(BASE_DIR, "tests", "test_sample.png")
            doc_path = os.path.join(BASE_DIR, "requirements.txt")
            
            if sub_c == "1":
                if os.path.exists(img_path):
                    send_attach_file(img_path)
                    print(f"[+] แนบรูปภาพ {img_path} เข้ากล่องแชทเรียบร้อยแล้ว!")
                    print("    👉 สังเกตแถบ Badge ด้านบนจอ: จะมี [🖼️ test_sample.png ✕] แสดงขึ้นมา")
                else:
                    print("[-] ไม่พบไฟล์รูปภาพตัวอย่าง")
            elif sub_c == "2":
                if os.path.exists(doc_path):
                    send_attach_file(doc_path)
                    print(f"[+] แนบไฟล์เอกสาร {doc_path} เข้ากล่องแชทเรียบร้อยแล้ว!")
                    print("    👉 สังเกตแถบ Badge ด้านบนจอ: จะมี [📄 requirements.txt ✕] แสดงขึ้นมา")
                else:
                    print("[-] ไม่พบไฟล์ requirements.txt")
            elif sub_c == "3":
                tests_dir = os.path.join(BASE_DIR, "tests")
                print(f"[*] กำลังเปิดโฟลเดอร์ {tests_dir}...")
                subprocess.Popen(f'explorer.exe /select,"{img_path}"')
                print("[+] เปิดโฟลเดอร์เรียบร้อย! คุณสามารถใช้เมาส์ลาก 'test_sample.png' หรือไฟล์อื่นๆ ไปวางบน Dynamic Island ได้เลยครับ")
            elif sub_c == "4":
                custom_p = input("ใส่ Full Path ของไฟล์: ").strip().strip('"').strip("'")
                if os.path.exists(custom_p):
                    send_attach_file(custom_p)
                    print(f"[+] แนบไฟล์ {custom_p} เข้ากล่องแชทเรียบร้อย!")
                else:
                    print(f"[-] ไม่พบไฟล์ที่ระบุ: {custom_p}")

        elif choice == "10":
            print("[*] กำลังรีสตาร์ต Dynamic Island...")
            launch_island(force_restart=True)
            print("[+] รีสตาร์ตเรียบร้อยแล้วครับ!")

        elif choice == "0":
            print("ปิดโปรแกรมทดสอบเรียบร้อยครับ.")
            break
        else:
            print("ตัวเลือกไม่ถูกต้อง กรุณาลองใหม่อีกครั้งครับ")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--menu":
        interactive_menu()
    else:
        run_automated_demo()
        print("\nพิมพ์ 'm' แล้วกด Enter เพื่อเข้าสู่เมนูทดสอบเพิ่มเติม (หรือกด Enter เพื่อออก): ", end="")
        try:
            choice = input().strip().lower()
            if choice == "m":
                interactive_menu()
        except (KeyboardInterrupt, EOFError):
            pass
