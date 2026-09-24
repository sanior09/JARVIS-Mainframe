"""
Purpose: ดึงรายการโปรแกรมที่กำลังทำงานอยู่ในระบบ Windows พร้อมข้อมูล PID, ชื่อโปรแกรม, การใช้ RAM และ CPU
Created: 2026-09-13 13:07:58.801755
"""

import psutil
import json

def list_running_processes(params):
    """
    ดึงรายการโปรแกรมที่กำลังทำงานอยู่ในระบบ Windows
    คืนค่า: รายการ process พร้อม pid, name, memory_percent, cpu_percent
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
        try:
            info = proc.info
            processes.append({
                "pid": info['pid'],
                "name": info['name'],
                "memory_percent": info['memory_percent'],
                "cpu_percent": info['cpu_percent']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # เรียงตามการใช้งบ RAM จากมากไปน้อย
    processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    
    return {
        "status": "success",
        "total_processes": len(processes),
        "processes": processes
    }