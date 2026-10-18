"""
modules/jarvis_gmail.py
───────────────────────────────────────────────────────────────────────────────
J.A.R.V.I.S. Gmail & Email Integration Subsystem
Provides autonomous email operations:
  - check_unread_emails(limit): สรุปอีเมลที่ยังไม่ได้อ่านล่าสุด
  - search_emails(query, limit): ค้นหาอีเมลตามคำค้นหา / ผู้ส่ง
  - read_email_detail(email_id): อ่านเนื้อหาฉบับเต็มของอีเมล
  - send_email(to_email, subject, body): ส่งอีเมลผ่าน Gmail SMTP
───────────────────────────────────────────────────────────────────────────────
"""

import os
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import smtplib
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("JARVIS.Gmail")

GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


from dotenv import load_dotenv
load_dotenv(override=True)


def _get_email_credentials():
    """ดึงและทำความสะอาด Email User & App Password จาก environment"""
    user = os.getenv("EMAIL_USER") or os.getenv("GMAIL_USER") or ""
    passwd = os.getenv("EMAIL_PASS") or os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASS") or ""
    
    # ทำความสะอาดช่องว่างและ quotes ที่อาจติดมาใน .env
    user = user.strip().strip('"').strip("'")
    passwd = passwd.replace(" ", "").strip().strip('"').strip("'")
    return user, passwd


def _decode_header_str(header_val: str) -> str:
    """ถอดรหัสหัวข้ออีเมลหรือชื่อผู้ส่งที่ถูกเข้ารหัส MIME (RFC 2047)"""
    if not header_val:
        return ""
    try:
        decoded_fragments = decode_header(header_val)
        result = []
        for frag, enc in decoded_fragments:
            if isinstance(frag, bytes):
                enc = enc or "utf-8"
                try:
                    result.append(frag.decode(enc, errors="replace"))
                except Exception:
                    result.append(frag.decode("utf-8", errors="replace"))
            else:
                result.append(str(frag))
        return "".join(result).strip()
    except Exception:
        return header_val


def _extract_body_snippet(msg: email.message.Message, max_len: int = 500) -> str:
    """สกัดเนื้อหาข้อความแบบ Text ออกมาจาก email message"""
    body_text = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = part.get("Content-Disposition", "")
                if ctype == "text/plain" and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="replace")
                        break
            if not body_text:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            raw_html = payload.decode(charset, errors="replace")
                            # strip basic html tags
                            import re
                            body_text = re.sub(r'<[^>]+>', ' ', raw_html)
                            break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")
    except Exception as e:
        logger.warning(f"Failed to extract email body: {e}")

    clean = " ".join(body_text.split())
    if len(clean) > max_len:
        clean = clean[:max_len] + "..."
    return clean or "[ไม่มีเนื้อหาข้อความ หรือเป็นไฟล์แนบ]"


def check_unread_emails(limit: int = 5) -> str:
    """
    ตรวจสอบอีเมลที่ยังไม่ได้อ่านในกล่องข้อความ Gmail (Inbox)
    
    Args:
        limit: จำนวนอีเมลสูงสุดที่ต้องการดึงมาสรุป (ค่าเริ่มต้น 5)
        
    Returns:
        ข้อความสรุปรายการอีเมลที่ยังไม่ได้อ่าน หรือคำแนะนำหากเชื่อมต่อไม่สำเร็จ
    """
    user, passwd = _get_email_credentials()
    if not user or not passwd:
        return (
            "⚠️ [GMAIL SYSTEM]: ยังไม่ได้ตั้งค่าบัญชี Gmail ในไฟล์ .env ครับ\n"
            "กรุณาระบุ:\n"
            "EMAIL_USER=your_email@gmail.com\n"
            "EMAIL_PASS=xxxx xxxx xxxx xxxx (Google App Password 16 หลัก)"
        )

    try:
        imap = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
        imap.login(user, passwd)
        imap.select("INBOX")

        status, messages = imap.search(None, "UNSEEN")
        if status != "OK" or not messages or not messages[0]:
            # ถ้าไม่มี unseen ลองดึง 3 ฉบับล่าสุดมาให้ดูแทน
            status_all, all_msgs = imap.search(None, "ALL")
            if status_all == "OK" and all_msgs and all_msgs[0]:
                id_list = all_msgs[0].split()
                recent_ids = id_list[-limit:]
                recent_ids.reverse()
                
                summaries = []
                for num in recent_ids:
                    _, data = imap.fetch(num, "(RFC822)")
                    if not data or not data[0] or not isinstance(data[0], tuple):
                        continue
                    msg = email.message_from_bytes(data[0][1])
                    sub = _decode_header_str(msg.get("Subject", "(ไม่มีหัวข้อ)"))
                    sender = _decode_header_str(msg.get("From", "(ไม่ระบุผู้ส่ง)"))
                    date_str = msg.get("Date", "")
                    snippet = _extract_body_snippet(msg, max_len=180)
                    summaries.append(f"📧 **[{sub}]**\n   - จาก: {sender}\n   - วันที่: {date_str}\n   - ตัวอย่าง: {snippet}")
                
                imap.logout()
                output = f"📭 ใน Inbox ไม่มีอีเมลใหม่ที่ยังไม่ได้อ่านครับเจ้านาย\nนี่คืออีเมลล่าสุด {len(summaries)} ฉบับที่ได้รับ:\n\n" + "\n\n".join(summaries)
                return output

            imap.logout()
            return "📭 ไม่มีอีเมลใหม่ในกล่องข้อความครับเจ้านาย กล่องจดหมายว่างและเรียบร้อยดีครับ"

        mail_ids = messages[0].split()
        total_unread = len(mail_ids)
        target_ids = mail_ids[-limit:]
        target_ids.reverse()

        summaries = []
        for num in target_ids:
            _, data = imap.fetch(num, "(RFC822)")
            if not data or not data[0] or not isinstance(data[0], tuple):
                continue
            msg = email.message_from_bytes(data[0][1])
            sub = _decode_header_str(msg.get("Subject", "(ไม่มีหัวข้อ)"))
            sender = _decode_header_str(msg.get("From", "(ไม่ระบุผู้ส่ง)"))
            date_str = msg.get("Date", "")
            snippet = _extract_body_snippet(msg, max_len=200)
            summaries.append(f"📩 **[{sub}]**\n   - จาก: {sender}\n   - วันที่: {date_str}\n   - เนื้อหาโดยย่อ: {snippet}")

        imap.logout()
        res = (
            f"📬 เจ้านายครับ มีอีเมลที่ยังไม่ได้อ่านทั้งหมด **{total_unread}** ฉบับครับ\n"
            f"รายละเอียด {len(summaries)} ฉบับล่าสุด:\n\n" + "\n\n".join(summaries)
        )
        return res

    except imaplib.IMAP4.error as e:
        logger.error(f"[GMAIL IMAP AUTH ERROR]: {e}")
        return (
            f"⚠️ ไม่สามารถเข้าถึง Gmail ได้ (Authentication Failed): {e}\n\n"
            f"คำแนะนำสำหรับเจ้านาย:\n"
            f"1. บัญชี Google ต้องการ **รหัสผ่านสำหรับแอป (App Password)** 16 หลัก ไม่ใช่รหัสผ่านบัญชีทั่วไป\n"
            f"2. เข้าไปที่: https://myaccount.google.com/apppasswords\n"
            f"3. สร้างรหัสผ่านสำหรับแอปชื่อ 'JARVIS' แล้วคัดลอกรหัส 16 ตัวมาใส่ใน EMAIL_PASS ในไฟล์ .env ครับ"
        )
    except Exception as e:
        logger.error(f"[GMAIL IMAP ERROR]: {e}")
        return f"เกิดข้อผิดพลาดในการตรวจสอบอีเมล: {e}"


def search_emails(query: str, limit: int = 5) -> str:
    """
    ค้นหาอีเมลในกล่องจดหมาย Gmail ตามคำค้นหา หรือชื่อผู้ส่ง
    
    Args:
        query: คีย์เวิร์ดที่ต้องการค้นหา เช่น ชื่อคน, หัวข้อ, หรือข้อความ
        limit: จำนวนผลลัพธ์สูงสุด (ค่าเริ่มต้น 5)
    """
    user, passwd = _get_email_credentials()
    if not user or not passwd:
        return "⚠️ กรุณาตั้งค่า EMAIL_USER และ EMAIL_PASS ใน .env ก่อนใช้งานครับ"

    if not query:
        return check_unread_emails(limit)

    try:
        imap = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
        imap.login(user, passwd)
        imap.select("INBOX")

        # ค้นหาทั้ง SUBJECT, FROM, หรือ TEXT
        # IMAP search format
        status, messages = imap.search(None, f'(OR (OR (SUBJECT "{query}") (FROM "{query}")) (TEXT "{query}"))')
        if status != "OK" or not messages or not messages[0]:
            # ลองค้นหาแบบกว้าง (TEXT)
            status, messages = imap.search(None, f'TEXT "{query}"')

        if status != "OK" or not messages or not messages[0]:
            imap.logout()
            return f"🔍 ไม่พบอีเมลที่เกี่ยวข้องกับ '{query}' ในกล่องจดหมายครับเจ้านาย"

        mail_ids = messages[0].split()
        target_ids = mail_ids[-limit:]
        target_ids.reverse()

        summaries = []
        for num in target_ids:
            _, data = imap.fetch(num, "(RFC822)")
            if not data or not data[0] or not isinstance(data[0], tuple):
                continue
            msg = email.message_from_bytes(data[0][1])
            sub = _decode_header_str(msg.get("Subject", "(ไม่มีหัวข้อ)"))
            sender = _decode_header_str(msg.get("From", "(ไม่ระบุผู้ส่ง)"))
            date_str = msg.get("Date", "")
            snippet = _extract_body_snippet(msg, max_len=180)
            summaries.append(f"📧 **[{sub}]**\n   - จาก: {sender}\n   - วันที่: {date_str}\n   - ตัวอย่าง: {snippet}")

        imap.logout()
        return f"🔎 ผลการค้นหาอีเมลสำหรับ '{query}' (พบ {len(mail_ids)} ฉบับ แสดง {len(summaries)} ฉบับล่าสุด):\n\n" + "\n\n".join(summaries)

    except Exception as e:
        logger.error(f"[GMAIL SEARCH ERROR]: {e}")
        return f"พบข้อขัดข้องในการค้นหาอีเมล: {e}"


def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> str:
    """
    ส่งอีเมลผ่าน Gmail SMTP Service
    
    Args:
        to_email: อีเมลผู้รับปลายทาง
        subject: หัวข้ออีเมล
        body: เนื้อหาข้อความในอีเมล
        is_html: True หากเนื้อหาเป็น HTML (ค่าเริ่มต้น False)
    """
    user, passwd = _get_email_credentials()
    if not user or not passwd:
        return "⚠️ ไม่สามารถส่งอีเมลได้เนื่องจากขาดการตั้งค่า EMAIL_USER หรือ EMAIL_PASS ใน .env ครับ"

    if not to_email or "@" not in to_email:
        # Default to USER_EMAIL if not provided
        to_email = os.getenv("USER_EMAIL") or user

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"J.A.R.V.I.S. Personal AI <{user}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        subtype = "html" if is_html else "plain"
        msg.attach(MIMEText(body, subtype, "utf-8"))

        sent = False
        try:
            with smtplib.SMTP_SSL(GMAIL_SMTP_SERVER, 465, timeout=15) as server:
                server.login(user, passwd)
                server.send_message(msg)
                sent = True
        except Exception as ssl_err:
            logger.debug(f"[GMAIL] Port 465 attempt failed: {ssl_err}, falling back to port 587")

        if not sent:
            with smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(user, passwd)
                server.send_message(msg)

        logger.info(f"[GMAIL] Email sent successfully to {to_email} (Subject: {subject})")
        return f"✅ ส่งอีเมลไปยัง '{to_email}' เรียบร้อยแล้วครับเจ้านาย (หัวข้อ: {subject})"

    except Exception as e:
        logger.error(f"[GMAIL SEND ERROR]: {e}")
        return f"⚠️ ไม่สามารถส่งอีเมลได้: {e}"
