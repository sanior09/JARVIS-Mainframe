"""
dynamic_tools/manage_gmail.py
───────────────────────────────────────────────────────────────────────────────
J.A.R.V.I.S. Gmail Management Dynamic Tool
Allows JARVIS to:
- Check and summarize unread emails in Gmail
- Search emails by keywords, sender, or subject
- Send emails to any recipient or to the user
───────────────────────────────────────────────────────────────────────────────
"""

import sys
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from modules.jarvis_gmail import check_unread_emails, search_emails, send_email

TOOL_SCHEMA = {
    "name": "manage_gmail",
    "description": "จัดการอีเมล Gmail สำหรับเจ้านาย — สามารถตรวจสอบอีเมลใหม่ที่ยังไม่ได้อ่าน, ค้นหาอีเมลสำคัญตามผู้ส่งหรือหัวข้อ, และส่งอีเมลหาผู้อื่นหรือส่งหาเจ้านายเอง",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_unread", "search", "send"],
                "description": "การทำงานที่ต้องการ: 'check_unread' (เช็คเมลใหม่), 'search' (ค้นหาเมล), 'send' (ส่งอีเมล)"
            },
            "query": {
                "type": "string",
                "description": "(สำหรับ action='search') คีย์เวิร์ด หรือชื่อคน หรือหัวข้อที่ต้องการค้นหา"
            },
            "to_email": {
                "type": "string",
                "description": "(สำหรับ action='send') ที่อยู่อีเมลผู้รับ เช่น 'client@example.com' (ถ้าเว้นว่างจะส่งเข้าอีเมลของเจ้านาย)"
            },
            "subject": {
                "type": "string",
                "description": "(สำหรับ action='send') หัวข้อของอีเมล"
            },
            "body": {
                "type": "string",
                "description": "(สำหรับ action='send') ข้อความเนื้อหาในอีเมล"
            },
            "limit": {
                "type": "integer",
                "description": "จำนวนอีเมลสูงสุดที่ต้องการดู (ค่าเริ่มต้น 5)"
            }
        },
        "required": ["action"]
    }
}


def execute(args=None, **kwargs) -> str:
    """Entry point for dynamic tool execution"""
    if isinstance(args, dict):
        params = args
    else:
        params = kwargs

    action = params.get("action", "check_unread")
    limit = int(params.get("limit", 5))

    if action == "check_unread":
        return check_unread_emails(limit=limit)
    elif action == "search":
        query = params.get("query", "")
        return search_emails(query=query, limit=limit)
    elif action == "send":
        to_email = params.get("to_email", "")
        subject = params.get("subject", "ข้อความแจ้งเตือนจาก J.A.R.V.I.S.")
        body = params.get("body", "")
        if not body:
            return "⚠️ กรุณาระบุเนื้อหาข้อความที่ต้องการส่งในพารามิเตอร์ 'body' ครับ"
        return send_email(to_email=to_email, subject=subject, body=body)
    else:
        return f"ไม่รู้จัก action: '{action}' กรุณาใช้ check_unread, search หรือ send ครับ"


if __name__ == "__main__":
    # Support CLI arguments if called directly
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS Gmail Tool")
    parser.add_argument("--action", default="check_unread")
    parser.add_argument("--query", default="")
    parser.add_argument("--to_email", default="")
    parser.add_argument("--subject", default="ข้อความจาก J.A.R.V.I.S.")
    parser.add_argument("--body", default="")
    parser.add_argument("--limit", type=int, default=5)
    cli_args = parser.parse_args()
    
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(execute(vars(cli_args)))
