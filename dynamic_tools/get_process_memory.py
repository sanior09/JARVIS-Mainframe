"""
Purpose: Return top memory-consuming processes on the Windows system.
Created: 2026-09-25 16:53:37.758680
"""

import psutil, json, sys

def get_process_memory(params):
    # params can include 'top' number of processes
    top_n = int(params.get('top', 5))
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            mem = proc.info['memory_info'].rss / (1024 * 1024)  # MB
            processes.append({'pid': proc.info['pid'], 'name': proc.info['name'], 'memory_mb': round(mem, 2)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    # sort by memory usage descending
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    return json.dumps(processes[:top_n])
