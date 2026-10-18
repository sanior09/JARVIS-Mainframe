"""
[JARVIS LINE ADAPTER & OUTPUT SANITIZER]
โมดูลสำหรับจัดการปฏิสัมพันธ์กับ LINE Messaging API:
- ขัดเกลาข้อความให้กระชับ สะอาดตา และเหมาะสมกับการอ่านบนสมาร์ตโฟน
- ดึงและบันทึก URL รูปภาพจากคำตอบของ AI
- ส่ง Push Message (Text, Image, QuickReply) ไปยังผู้ใช้งาน
"""

import logging
import mimetypes
import os
import re
import shutil
import time
import uuid
from typing import Any, Optional

import requests

try:
    from jarvis_text_utils import normalize_thai_text
except (ImportError, ModuleNotFoundError):
    try:
        from modules.jarvis_text_utils import normalize_thai_text
    except (ImportError, ModuleNotFoundError):
        def normalize_thai_text(text: str) -> str:
            if not text:
                return ""
            text = text.replace("เเ", "แ").replace("ะา", "ำ").replace("ํา", "ำ").replace("ํ้า", "้ำ")
            text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
            return re.sub(r'([่้๊๋ิีึืุูัํ])\1+', r'\1', text)

logger = logging.getLogger("JARVIS_LINE")


def format_reply_for_line(text: str) -> str:
    """
    [LINE ADAPTER: OUTPUT SANITIZER & FORMATTER]
    ขัดเกลาและจัดรูปแบบข้อความสำหรับส่งเข้าแอป LINE บนสมาร์ตโฟนโดยเฉพาะ:
    1. จัดการคำสั่งเงียบ (Silent Execution) หรือคำสั่ง Action ให้มีคำตอบรับสุภาพ ไม่เงียบหาย
    2. ลบแท็กภายในระบบ เช่น [WINDOW:...], [END_WINDOW], [SILENT_EXECUTION]
    3. ถอด HTML tags (เช่น <img ...>) ที่มักทำให้ข้อความเละ
    4. แปลง Markdown จัดรูปเล่ม (เช่น **, ###, code blocks, tables) ให้เป็นข้อความสะอาดตา อ่านง่ายบนมือถือ
    5. ขจัดตัวอักขระแปลกปลอม (Zero-width space, control characters, JSON artifacts)
    6. คุมความกระชับ จัดวรรคตอนให้สบายตา ไม่ยาวเป็นพรืดตามที่เจ้านายต้องการ
    """
    if not text:
        return "ดำเนินการเรียบร้อยครับเจ้านาย"

    s = text

    # 1. จัดการกรณีคำสั่ง Silent Execution หรือ Action ที่ตอบสั้น
    if "[SILENT_EXECUTION]" in s:
        s = s.replace("[SILENT_EXECUTION]", "").strip()
        magic_triggers = ["lumos!", "lumos", "nox.", "nox", "incendio!", "incendio"]
        if not s or any(s.strip().lower() == m for m in magic_triggers):
            return "ดำเนินการเรียบร้อยแล้วครับเจ้านาย"

    # 2. ถอดแท็กหน้าต่างแสดงผล HUD / Window
    s = re.sub(r'\[WINDOW:[^\]]*\]', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\[END_WINDOW\]', '', s, flags=re.IGNORECASE)

    # 3. ถอดแท็กระบบและ directive ภายใน
    internal_tags = [
        r'\[ANTICIPATORY[^\]]*\]',
        r'\[คาดการณ์[^\]]*\]',
        r'\[วิธีข้อมูล[^\]]*\]',
        r'\[ค้นหาข้อมูล[^\]]*\]',
        r'\[DEEP THOUGHT[^\]]*\]',
        r'\[REJECTION EXECUTION[^\]]*\]',
        r'\[CRITICAL SAFETY[^\]]*\]',
        r'\[VOICE MODE[^\]]*\]',
        r'\[LINE MESSAGING[^\]]*\]',
        r'\[LINE MOBILE[^\]]*\]',
        r'\[INTERNAL[^\]]*\]',
        r'\[PROTOCOL[^\]]*\]',
        r'\[SENTINEL[^\]]*\]',
        r'\[NACHAPOL[^\]]*\]',
        r'\[Real-time[^\]]*\]',
        r'\[ENGINEERING[^\]]*\]',
        r'\[CONFIRMED_BY_LINE\]',
        r'\[IMAGE CACHE[^\]]*\]',
        r'\[TASK QUEUE[^\]]*\]',
        r'\[SYSTEM[^\]]*\]',
    ]
    for tag_pat in internal_tags:
        s = re.sub(tag_pat, '', s, flags=re.IGNORECASE)

    # ตัดแท็กตัวพิมพ์ใหญ่ในวงเล็บเหลี่ยมทั่วไป
    s = re.sub(r'\[[A-Z0-9_\s]{4,}\]', '', s)

    # 4. ลบ HTML tags เช่น <img ...>, <div>, <span>, <br>
    s = re.sub(r'<img[^>]*>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'</?(?:div|span|p|b|i|strong|em|hr)[^>]*>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', '', s)

    # 5. ลบ JSON หรือ Query fragments และเศษข้อความเรียกคำสั่งระบบ
    s = re.sub(r'\{["\'](?:query|action|status|tool_name|status_code)["\']:\s*[^}]+\}', '', s)
    s = re.sub(r'\{"[a-zA-Z0-9_]+"\s*:\s*"[^"]*"\}', '', s)
    s = re.sub(r'(?i)กำลังประมวลผล(?:คำสั่ง|งาน|โปรแกรม)?\s*[:\-]?\s*[\'"`]?[a-zA-Z0-9_()]+\s*[\'"`]?', '', s)
    s = re.sub(r'(?i)executing(?: command| tool)?\s*[:\-]?\s*[\'"`]?[a-zA-Z0-9_()]+\s*[\'"`]?', '', s)
    s = re.sub(r'[\'"`]?[a-zA-Z0-9_]+\(\)[\'"`]?', '', s)

    # 6. ปรับแต่ง Markdown:
    # 6.1 ลบ Headers: ### หรือ ## หรือ #
    s = re.sub(r'^[ \t]*#{1,6}[ \t]*(.*)$', r'\1', s, flags=re.MULTILINE)

    # 6.2 ลบ Bold / Italic asterisks (**คำ**, *คำ*, __คำ__, _คำ_)
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)
    s = re.sub(r'__(.*?)__', r'\1', s)
    s = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', s)
    s = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'\1', s)

    # 6.3 Code blocks: ```python ... ``` หรือ `code`
    s = re.sub(r'```(?:[a-zA-Z0-9_-]+)?\n?(.*?)```', r'\1', s, flags=re.DOTALL)
    s = re.sub(r'`([^`]+)`', r"'\1'", s)

    # 6.4 Blockquotes: >
    s = re.sub(r'^[ \t]*>[ \t]?', '', s, flags=re.MULTILINE)

    # 6.5 ปรับ Bullet points: ใช้ • แทน - หรือ *
    s = re.sub(r'^[ \t]*[\*\-][ \t]+', '• ', s, flags=re.MULTILINE)

    # 6.6 ปรับ Links: [Text](URL) -> Text (URL)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1 (\2)', s)

    # 6.7 ลบลิงก์ local path เช่น ลิงก์: /static/generatedimages/... หรือ /static/generated_images/...
    s = re.sub(r'(?:ลิงก์|ลิงค์|link|url)\s*[:：]?\s*/static/\S+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'!\[.*?\]\(/static/\S+\)', '', s, flags=re.IGNORECASE)
    s = re.sub(r'/static/(?:generated_images|generatedimages)/\S+', '', s, flags=re.IGNORECASE)

    # 6.8 จัดการตาราง Markdown ให้เป็นรายการ bullet ที่อ่านง่ายบนมือถือ
    table_lines = s.split('\n')
    formatted_t_lines = []
    for t_line in table_lines:
        striped_t = t_line.strip()
        if striped_t.startswith('|') and striped_t.endswith('|'):
            cells = [c.strip() for c in striped_t.split('|')[1:-1]]
            if all(set(c) <= {'-', ':', ' '} for c in cells if c):
                continue
            formatted_t_lines.append('• ' + ' : '.join([c for c in cells if c]))
        else:
            formatted_t_lines.append(t_line)
    s = '\n'.join(formatted_t_lines)

    # 6.9 เส้นแบ่ง markdown
    s = re.sub(r'^[ \t]*[\-\=\*\_]{3,}[ \t]*$', '──────────', s, flags=re.MULTILINE)

    # 7. ลบตัวอักขระแปลกปลอมและ Unicode ขยะ
    s = s.replace('\xa0', ' ')
    s = s.replace('\u200b', '')
    s = s.replace('\u200c', '')
    s = s.replace('\u200d', '')
    s = s.replace('\ufeff', '')

    # 8. ปรับแก้สระและวรรณยุกต์ภาษาไทยให้ถูกต้องตามมาตรฐาน Unicode
    s = normalize_thai_text(s)

    # 9. จัดระยะบรรทัดและการเว้นวรรค
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = s.strip()

    if not s:
        return "ดำเนินการเรียบร้อยแล้วครับเจ้านาย"

    return s


def extract_image_url_from_response(text: str) -> Optional[str]:
    """ดึง URL รูปภาพแรกที่พบใน AI response (จาก <img>, Markdown ![](url), หรือ URL ตรงๆ)"""
    if not text:
        return None
    # 1. HTML img tag
    match = re.search(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', text, re.IGNORECASE)
    if match:
        return match.group(1)
    # 2. Markdown image: ![alt](url)
    match = re.search(r'!\[.*?\]\((/static/\S+|/temp_images/\S+|https?://\S+)\)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    # 3. Pollinations AI direct URL
    match = re.search(r'https?://image\.pollinations\.ai/prompt/\S+', text)
    if match:
        return match.group(0)
    # 4. Direct web image URLs
    match = re.search(r'https?://\S+\.(?:jpg|jpeg|png|webp|gif|svg)(\?\S*)?', text, re.IGNORECASE)
    if match:
        return match.group(0)
    # 5. Relative static or temp image paths (including cases where LLM omits underscore)
    match = re.search(r'/(?:static/(?:generated_images|generatedimages)|temp_images)/\S+\.(?:jpg|jpeg|png|webp|gif)', text, re.IGNORECASE)
    if match:
        return match.group(0)
    # 6. Local generated image filenames (e.g. gen_img_123.jpg or genimg_123.jpg)
    match = re.search(r'(?:gen_?img_\d+|screenshot_\d+|line_img_\w+)\.(?:jpg|jpeg|png|webp)', text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None


def download_image_for_line(image_url: str, base_dir: str, temp_images_dir: str) -> Optional[str]:
    """ดาวน์โหลดรูปภาพหรือคัดลอกจาก local path และ save ลง temp_images/ คืน filename ที่บันทึก"""
    try:
        os.makedirs(temp_images_dir, exist_ok=True)
        local_name = os.path.basename(image_url)

        # 1. ตรวจสอบว่าไฟล์อยู่ใน temp_images_dir อยู่แล้วหรือไม่
        direct_temp = os.path.join(temp_images_dir, local_name)
        if os.path.exists(direct_temp):
            return local_name

        # 2. กรณีเป็นไฟล์รูปภาพที่เพิ่งสร้างจาก generate_image_operation
        gen_dir = os.path.join(base_dir, "static", "generated_images")
        candidate_paths = [
            os.path.join(gen_dir, local_name),
            os.path.join(gen_dir, local_name.replace("genimg_", "gen_img_")),
            os.path.join(gen_dir, local_name.replace("gen_img_", "genimg_")),
        ]
        
        # Fuzzy match หาไฟล์ที่ timestamp ตรงกันใน static/generated_images
        digits = re.findall(r'\d+', local_name)
        if digits and os.path.exists(gen_dir):
            for existing in os.listdir(gen_dir):
                if any(d in existing for d in digits):
                    candidate_paths.append(os.path.join(gen_dir, existing))
                    break

        for path in candidate_paths:
            if os.path.exists(path):
                ext = os.path.splitext(path)[1] or '.jpg'
                filename = f"line_img_{uuid.uuid4().hex[:12]}{ext}"
                filepath = os.path.join(temp_images_dir, filename)
                shutil.copy2(path, filepath)
                return filename

        # 3. ถ้าเป็น URL ภายนอก (HTTP/HTTPS) ให้ดาวน์โหลด
        if image_url.startswith(("http://", "https://")):
            headers = {"User-Agent": "Mozilla/5.0 (JarvisHUD/2.0)"}
            r = requests.get(image_url, headers=headers, timeout=15, stream=True)
            r.raise_for_status()
            content_type = r.headers.get('content-type', 'image/jpeg').split(';')[0].strip()
            ext = mimetypes.guess_extension(content_type) or '.jpg'
            if ext == '.jpe':
                ext = '.jpg'
            filename = f"line_img_{uuid.uuid4().hex[:12]}{ext}"
            filepath = os.path.join(temp_images_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return filename

        return None
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[LINE IMAGE] Download failed: {e}")
        return None
