import ctypes
import os
import subprocess
import psutil

def main():
    print("=" * 56)
    print("      J.A.R.V.I.S. Memory & RAM Optimization Tool")
    print("=" * 56)
    
    before = psutil.virtual_memory()
    print(f"\n[สถานะก่อนเคลียร์] RAM: {before.percent}% (ว่าง: {before.available / 1e9:.2f} GB)")

    # 1. ปลดโมเดล Ollama ออกจาก RAM
    print("\n[1/3] กำลังปลดโมเดล Local AI (Ollama) ออกจากหน่วยความจำ...")
    models = ["qwen-uncensored", "qwen:4b", "dolphin-llama3", "qwen3.8:27b"]
    for m in models:
        try:
            subprocess.run(["ollama", "stop", m], capture_output=True, timeout=2)
        except Exception:
            pass

    # 2. เคลียร์ Working Set สำหรับโปรเซสทั้งหมด
    print("[2/3] กำลังเคลียร์แคชและ Working Set ของแอปพลิเคชัน...")
    freed_procs = 0
    for p in psutil.process_iter(['pid']):
        try:
            h = ctypes.windll.kernel32.OpenProcess(0x001F0FFF, False, p.info['pid'])
            if h:
                ctypes.windll.psapi.EmptyWorkingSet(h)
                ctypes.windll.kernel32.CloseHandle(h)
                freed_procs += 1
        except Exception:
            pass

    after = psutil.virtual_memory()
    freed_mb = max(0, int((after.available - before.available) / 1e6))
    print(f"\n[3/3] สรุปผลการเคลียร์ RAM ({freed_procs} โปรเซส):")
    print(f"  - คืนหน่วยความจำ: +{freed_mb} MB")
    print(f"  - สถานะ RAM ปัจจุบัน: {after.percent}% (ว่าง: {after.available / 1e9:.2f} GB จากทั้งหมด {after.total / 1e9:.2f} GB)")
    print("\n" + "=" * 56)
    print("      เคลียร์หน่วยความจำ RAM สำเร็จเรียบร้อยครับ!")
    print("=" * 56)

if __name__ == "__main__":
    main()
