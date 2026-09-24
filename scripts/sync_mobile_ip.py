"""
sync_mobile_ip.py
──────────────────────────────────────────────────────────────────────────────
Auto-detects the host machine's active local LAN IPv4 address and synchronizes
it into jarvis-mobile/App.js so the mobile app always connects smoothly.
──────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import socket
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_JS_PATH = os.path.join(BASE_DIR, "jarvis-mobile", "App.js")


def get_local_ip() -> str:
    """Retrieve active outbound IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just routes to determine local interface
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        s.close()


def sync_ip(port: int = 5050) -> bool:
    if not os.path.exists(APP_JS_PATH):
        print(f"[!] App.js not found at {APP_JS_PATH}. Skipping sync.")
        return False

    current_ip = get_local_ip()
    target_host = f"http://{current_ip}:{port}"

    with open(APP_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"const\s+JARVIS_HOST\s*=\s*['\"][^'\"]+['\"];"
    match = re.search(pattern, content)

    if not match:
        print("[!] Could not locate 'const JARVIS_HOST' in App.js.")
        return False

    old_decl = match.group(0)
    new_decl = f"const JARVIS_HOST = '{target_host}';"

    if old_decl == new_decl:
        print(f"[*] Mobile IP is up to date: {target_host}")
        return True

    updated_content = content.replace(old_decl, new_decl)
    with open(APP_JS_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"[✓] JARVIS Mobile Host synchronized to: {target_host}")
    return True


if __name__ == "__main__":
    sync_ip()
