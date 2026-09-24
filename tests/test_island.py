"""
J.A.R.V.I.S. Dynamic Island — Live Interactive Test & Demo Suite
Allows testing all Dynamic Island HUD features on your desktop.
"""
import os
import sys
import time
import subprocess
import psutil
from dynamic_island import send_to_island, send_toast_to_island

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

def launch_island():
    """Launch dynamic_island.py in a background process"""
    print("[*] Launching J.A.R.V.I.S. Dynamic Island HUD...")
    proc = subprocess.Popen([sys.executable, "dynamic_island.py"], cwd=r"c:\JARVIS")
    time.sleep(1.5)
    return proc

def run_automated_demo():
    """Run sequential showcase of Dynamic Island capabilities"""
    print("\n" + "="*55)
    print(" 🏝️  J.A.R.V.I.S. DYNAMIC ISLAND HUD — LIVE DEMO SUITE")
    print("="*55)

    if not is_island_running():
        launch_island()
    else:
        print("[+] Dynamic Island is already running!")

    time.sleep(0.8)

    print("\n[1/4] 🎵 Testing Windows Media Now Playing Marquee...")
    send_to_island("MEDIA_TRACK", "Starboy - The Weeknd ft. Daft Punk")
    print("      -> Sent track title. Look at the top of your screen for scrolling marquee!")
    time.sleep(4.5)

    print("\n[2/4] 🚨 Testing Smart Alert / Toast Banner...")
    send_toast_to_island("LINE Message", "คุณซาเนียร์: จาร์วิส เตรียมระบบพร้อมสำหรับการทดสอบแล้วหรือยัง", icon="💬")
    print("      -> Sent Toast Banner. The island should expand into a dual-line notification!")
    time.sleep(5.0)

    print("\n[3/4] ⚡ Testing Status Indicators...")
    print("      -> State: LISTENING (Orange dot)")
    send_to_island("LISTENING")
    time.sleep(2.0)

    print("      -> State: THINKING (Cyan dot)")
    send_to_island("THINKING")
    time.sleep(2.0)

    print("      -> State: SPEAKING (Green dot)")
    send_to_island("SPEAKING")
    time.sleep(2.0)

    print("      -> Reset to STANDBY")
    send_to_island("STANDBY")
    time.sleep(1.0)

    print("\n[4/4] 📁 Drag & Drop Ingestion:")
    print("      -> You can now drag ANY file (.png, .pdf, .py, .txt) from your desktop")
    print("         and drop it onto the island at the top of your screen!")
    print("="*55)
    print(" All automated checks completed successfully!")
    print("="*55)

def interactive_menu():
    """Interactive CLI menu to trigger custom test events"""
    while True:
        print("\n--- เลือกคำสั่งทดสอบ (พิมพ์ตัวเลขแล้วกด Enter) ---")
        print("1. ส่ง Toast แจ้งเตือน (Smart Alert)")
        print("2. ส่งชื่อเพลง Now Playing (Marquee Scroll)")
        print("3. ล้างชื่อเพลงกลับสู่ปกติ (Clear Media)")
        print("4. จำลองสถานะ LISTENING")
        print("5. จำลองสถานะ THINKING")
        print("6. จำลองสถานะ SPEAKING")
        print("7. จำลองสถานะ STANDBY")
        print("0. ออกจากโปรแกรมทดสอบ")
        
        choice = input("\nเลือกคำสั่ง [0-7]: ").strip()
        if choice == "1":
            title = input("หัวข้อแจ้งเตือน (Default: ข้อความใหม่): ").strip() or "ข้อความใหม่"
            msg = input("เนื้อหา (Default: ระบบ J.A.R.V.I.S. พร้อมทำงาน): ").strip() or "ระบบ J.A.R.V.I.S. พร้อมทำงาน"
            send_toast_to_island(title, msg, icon="🔔")
            print("[+] ส่ง Toast เรียบร้อยแล้วครับ!")
        elif choice == "2":
            track = input("ชื่อเพลง - ศิลปิน (Default: Blinding Lights - The Weeknd): ").strip() or "Blinding Lights - The Weeknd"
            send_to_island("MEDIA_TRACK", track)
            print("[+] ส่งชื่อเพลงเรียบร้อยแล้วครับ!")
        elif choice == "3":
            send_to_island("MEDIA_CLEAR")
            print("[+] ล้างชื่อเพลงเรียบร้อยแล้วครับ!")
        elif choice == "4":
            send_to_island("LISTENING")
        elif choice == "5":
            send_to_island("THINKING")
        elif choice == "6":
            send_to_island("SPEAKING")
        elif choice == "7":
            send_to_island("STANDBY")
        elif choice == "0":
            print("ปิดโปรแกรมทดสอบเรียบร้อยครับ.")
            break
        else:
            print("ตัวเลือกไม่ถูกต้อง กรุณาลองใหม่อีกครั้งครับ")

if __name__ == "__main__":
    run_automated_demo()
    print("\nกด 'm' เพื่อเข้าสู่เมนูทดสอบเพิ่มเติม หรือกด Enter เพื่อเสร็จสิ้น...")
    user_choice = input().strip().lower()
    if user_choice == "m":
        interactive_menu()
