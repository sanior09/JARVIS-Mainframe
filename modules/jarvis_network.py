import subprocess
import threading
import time
import logging
import re
import os
import json

logger = logging.getLogger("JarvisNetwork")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [NETWORK] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KNOWN_DEVICES_FILE = os.path.join(BASE_DIR, "system_cache", "known_mac_addresses.json")
MAC_ALIASES_FILE = os.path.join(BASE_DIR, "system_cache", "mac_aliases.json")

_network_thread = None
_stop_event = threading.Event()
_known_macs = set()
_mac_aliases = {}

def _load_known_devices():
    global _known_macs
    try:
        if os.path.exists(KNOWN_DEVICES_FILE):
            with open(KNOWN_DEVICES_FILE, "r", encoding="utf-8") as f:
                _known_macs = set(json.load(f))
    except Exception as e:
        logger.error(f"Failed to load known devices: {e}")

def _save_known_devices():
    try:
        os.makedirs(os.path.dirname(KNOWN_DEVICES_FILE), exist_ok=True)
        with open(KNOWN_DEVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(list(_known_macs), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save known devices: {e}")

def _load_aliases():
    global _mac_aliases
    try:
        if os.path.exists(MAC_ALIASES_FILE):
            with open(MAC_ALIASES_FILE, "r", encoding="utf-8") as f:
                _mac_aliases = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load MAC aliases: {e}")

def _save_aliases():
    try:
        os.makedirs(os.path.dirname(MAC_ALIASES_FILE), exist_ok=True)
        with open(MAC_ALIASES_FILE, "w", encoding="utf-8") as f:
            json.dump(_mac_aliases, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save MAC aliases: {e}")

def set_mac_alias(mac: str, alias: str):
    """Set a human-readable name for a MAC address"""
    _mac_aliases[mac.lower()] = alias
    _save_aliases()

def _scan_arp():
    """Scan ARP table for MAC addresses"""
    try:
        
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=True)
        
        mac_pattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
        
        current_macs = set()
        for line in result.stdout.splitlines():
            match = mac_pattern.search(line)
            if match:
                mac = match.group(0).replace('-', ':').lower()
                
                if not mac.startswith('ff:ff:ff') and not mac.startswith('01:00:5e'):
                    current_macs.add(mac)
        return current_macs
    except Exception as e:
        logger.error(f"ARP scan failed: {e}")
        return set()

def _network_radar_loop():
    logger.info("Local Network Radar started.")
    _load_known_devices()
    _load_aliases()
    
    first_run = True
    
    while not _stop_event.is_set():
        current_macs = _scan_arp()
        
        if first_run:
            
            new_macs = current_macs - _known_macs
            if new_macs:
                _known_macs.update(new_macs)
                _save_known_devices()
            first_run = False
        else:
            new_macs = current_macs - _known_macs
            if new_macs:
                for mac in new_macs:
                    logger.warning(f"⚠️ NEW DEVICE DETECTED: {mac}")
                    _trigger_network_alert(mac)
                
                _known_macs.update(new_macs)
                _save_known_devices()
                
        _stop_event.wait(timeout=60)  

def _trigger_network_alert(mac_address):
    """Trigger a TTS alert for a new device"""
    try:
        from jarvis_tts_edge import JarvisStreamingTTS
        tts = JarvisStreamingTTS()
        alert_msg = f"เจ้านายครับ ตรวจพบอุปกรณ์แปลกปลอม หมายเลขแมคแอดเดรส {mac_address.replace(':', ' ')} เชื่อมต่อเข้ามาในเครือข่ายครับ"
        tts.speak(alert_msg)
    except Exception as e:
        logger.error(f"Failed to trigger network alert TTS: {e}")

def start_network_radar():
    global _network_thread
    if _network_thread and _network_thread.is_alive():
        return
    _stop_event.clear()
    _network_thread = threading.Thread(target=_network_radar_loop, daemon=True, name="JarvisNetwork")
    _network_thread.start()

def stop_network_radar():
    _stop_event.set()

def get_radar_state():
    """Return the current radar state for the Web UI"""
    macs_with_aliases = []
    for mac in _known_macs:
        macs_with_aliases.append({
            "mac": mac,
            "alias": _mac_aliases.get(mac, None)
        })
    
    return {
        "devices": macs_with_aliases,
        "timestamp": time.time()
    }
