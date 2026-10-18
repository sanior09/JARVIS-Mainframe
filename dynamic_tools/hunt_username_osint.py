"""
[J.A.R.V.I.S. DYNAMIC TOOL: HUNT USERNAME OSINT]
Nachapol Industries Advanced Intelligence System

Invokes the Sherlock & Multi-Account OSINT Engine to track down
all social media, developer, and gaming accounts across platforms.
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure root directory is accessible for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tactical_command.sherlock_recon import run_sherlock_scan

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "hunt_username_osint",
        "description": "Perform OSINT reconnaissance to track down and list all online accounts across TikTok, Instagram, GitHub, Telegram, Reddit, Steam, YouTube, etc. for a person, individual, target, contact, or username. Use this whenever the user asks to investigate, stalk, look up social accounts, or find information about a specific person or name using natural language (e.g., 'ไปหาข้อมูลของโดนัทมาให้หน่อย', 'ช่วยสืบประวัติน้องโดนัท', 'ส่องไอจีกับติ๊กต็อกคนนี้', 'หาประวัติคนชื่อ...').",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Target person's name, nickname, or online handle to investigate (e.g., 'donut', 'nachapol'). If given in Thai (e.g., 'โดนัท', 'น้องโดนัท'), transliterate/convert to the Romanized handle ('donut') or pass directly."
                },
                "mode": {
                    "type": "string",
                    "enum": ["multi", "exact", "deep"],
                    "description": "Scan mode: 'multi' (Default: Sweep multiple accounts across all platforms ~8s), 'exact' (1:1 exact handle match on top 25 platforms), 'deep' (Full 480+ platforms exact match)."
                }
            },
            "required": ["username"]
        }
    }
}

def execute(args):
    """
    Entry point for JARVIS to execute OSINT investigation.
    """
    username = args.get("username", "") if isinstance(args, dict) else str(args)
    username = username.strip().replace("@", "")
    
    mode = "multi"
    if isinstance(args, dict):
        mode = args.get("mode", "multi") or "multi"
    if mode == "quick":
        mode = "exact"

    if not username:
        return "กรุณาระบุชื่อหรือ Username ของเป้าหมายที่ต้องการให้สืบค้นครับเจ้านาย"

    res = run_sherlock_scan(username=username, mode=mode)
    if res.get("status") == "success":
        return res.get("summary", "การสืบค้นข้อมูลเสร็จสมบูรณ์ครับ")
    elif res.get("status") == "timeout":
        return res.get("message", "การสืบค้นใช้เวลานานเกินกำหนดครับ")
    return f"ข้อขัดข้องในการสืบค้น: {res.get('message', 'ไม่สามารถเชื่อมต่อระบบได้')}"

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "donut"
    m = sys.argv[2] if len(sys.argv) > 2 else "multi"
    print(f"Testing OSINT for '{target}' (mode={m})...")
    output = execute({"username": target, "mode": m})
    print(output)
