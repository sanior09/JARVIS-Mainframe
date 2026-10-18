"""
profile_jarvis.py — วัด CPU ของ JARVIS ที่กำลังรันอยู่ (ใช้ psutil เท่านั้น ไม่ต้องติดตั้งเพิ่ม)

ใช้: venv\\Scripts\\python.exe scripts\\profile_jarvis.py [วินาที=20] [ชื่อสคริปต์=jarvis.py]
แสดง CPU% ของโปรเซส JARVIS + โปรเซสลูก + 10 thread ที่กิน CPU มากสุด
เพื่อตัดสินใจว่าจุดไหนคุ้มที่จะย้ายไป Rust/C++
"""
import sys
import time

import psutil


def find_targets(script):
    out = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmd = ' '.join(p.info['cmdline'] or [])
        if script in cmd and 'profile_jarvis' not in cmd and 'python' in (p.info['name'] or '').lower():
            out.append(p)
    return out


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 20
    script = sys.argv[2] if len(sys.argv) > 2 else 'jarvis.py'
    targets = find_targets(script)
    if not targets:
        print(f"ไม่พบโปรเซสที่รัน {script} — เปิด JARVIS ก่อนแล้วรันใหม่")
        return
    procs = {}
    for t in targets:
        procs[t.pid] = t
        for c in t.children(recursive=True):
            procs[c.pid] = c
    ncpu = psutil.cpu_count() or 1
    before = {}
    for pid, p in procs.items():
        try:
            p.cpu_percent(None)
            before[pid] = {th.id: th.user_time + th.system_time for th in p.threads()}
        except psutil.Error:
            pass
    print(f"กำลังวัด {len(procs)} โปรเซส เป็นเวลา {secs:.0f} วินาที ...")
    time.sleep(secs)

    rows, threads = [], []
    for pid, p in procs.items():
        try:
            cpu = p.cpu_percent(None) / ncpu
            rows.append((cpu, pid, p.name(), p.memory_info().rss / 1e6, p.num_threads()))
            for th in p.threads():
                d = (th.user_time + th.system_time) - before.get(pid, {}).get(th.id, 0)
                threads.append((d / secs * 100 / ncpu, pid, th.id))
        except psutil.Error:
            pass
    print(f"\n{'CPU%(รวมทุกคอร์)':<18}{'PID':<8}{'ชื่อ':<16}{'RAM MB':<9}Threads")
    for cpu, pid, name, mem, nth in sorted(rows, reverse=True):
        print(f"{cpu:<18.1f}{pid:<8}{name:<16}{mem:<9.0f}{nth}")
    print("\nTop 10 threads:")
    for cpu, pid, tid in sorted(threads, reverse=True)[:10]:
        print(f"  {cpu:5.1f}%  pid={pid} tid={tid}")


if __name__ == '__main__':
    main()
