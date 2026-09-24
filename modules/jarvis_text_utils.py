"""
[JARVIS TEXT UTILITIES & PATH SECURITY ENGINE]
โมดูลสำหรับปรับแต่งข้อความภาษาไทย, ล้างแท็กระบบ AI,
และตรวจสอบความปลอดภัยของ File Path สำหรับ J.A.R.V.I.S.
"""

import os
import re
from typing import Optional


def normalize_thai_text(text: str) -> str:
    """
    ปรับแต่งและสะกดคำภาษาไทยที่พบบ่อยให้ถูกต้องตามมาตรฐานตัวอักษร Unicode
    แก้ปัญหาการพิมพ์เบิ้ล สระซ้อน หรือการพิมพ์สระผิดโครงสร้าง พร้อมจัดวรรคตอน
    """
    if not text:
        return ""
    
    text = text.replace("เเ", "แ")
    text = text.replace("ะา", "ำ")
    text = text.replace("ํา", "ำ")
    text = text.replace("ํ้า", "้ำ")
    
    # ลบ zero-width spaces และ non-printing unicode
    text = (
        text.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )
    
    # แก้ไขสระหรือวรรณยุกต์ซ้อน
    text = re.sub(r'([่้๊๋ิีึืุูัํ])\1+', r'\1', text)
    
    # ปรับการตัดช่องว่างระหว่างคำลงท้ายภาษาไทยที่พบบ่อย (เช่น สวัสดี ครับ -> สวัสดีครับ)
    common_thai_particles = ["ครับ", "ค่ะ", "คะ", "จ้า", "จ๊ะ", "นะ", "คับ", "ฮะ"]
    for p in common_thai_particles:
        text = re.sub(rf'([\u0e00-\u0e7f])\s+{p}\b', rf'\1{p}', text)
        
    # แทนที่ newlines และ tabs ด้วยช่องว่างเดี่ยว
    text = re.sub(r'[\r\n\t]+', ' ', text)
    
    # ลบช่องว่างซ้ำ
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


def sanitize_ai_response(text: str) -> str:
    """
    [NACHAPOL PROTOCOL: OUTPUT SANITIZER]
    กรองแท็กภายในและ raw data ที่รั่วออกมาจาก AI response
    ก่อนส่งแสดงให้เจ้านายเห็นหรือแปลงเป็นเสียง
    """
    if not text:
        return text

    internal_tag_patterns = [
        r'\[ANTICIPATORY[^\]]*\]',
        r'\[คาดการณ์[^\]]*\]',
        r'\[วิธีข้อมูล[^\]]*\]',
        r'\[ค้นหาข้อมูล[^\]]*\]',
        r'\[DEEP THOUGHT[^\]]*\]',
        r'\[REJECTION EXECUTION[^\]]*\]',
        r'\[CRITICAL SAFETY[^\]]*\]',
        r'\[VOICE MODE[^\]]*\]',
        r'\[INTERNAL[^\]]*\]',
        r'\[PROTOCOL[^\]]*\]',
        r'\[SENTINEL[^\]]*\]',
        r'\[NACHAPOL[^\]]*\]',
        r'\[Real-time[^\]]*\]',
        r'\[ENGINEERING[^\]]*\]',
    ]
    for pattern in internal_tag_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    text = re.sub(r'\{["\']query["\']:\s*["\'][^"\']*["\']\}', '', text)
    text = re.sub(r'\(["\']query["\']:\s*["\'][^"\']*["\']\)', '', text)
    text = re.sub(r'\{"[a-zA-Z_]+"\s*:\s*"[^"]*"\}', '', text)
    text = re.sub(r'\[[A-Z_\s]{4,}\]', '', text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    text = text.strip()

    return text


def is_safe_path(base_path: str, target_path: str) -> bool:
    """ตรวจสอบความปลอดภัยของ Path และป้องกันการเข้าถึงไฟล์ระบบนอกโฟลเดอร์โปรเจ็ค"""
    try:
        forbidden_dirs = ['C:\\Windows', '/etc', '/root', '.git', '__pycache__']
        if any(forbidden in target_path for forbidden in forbidden_dirs):
            return False

        base_abs = os.path.abspath(base_path)
        target_abs = os.path.abspath(target_path)
        
        return target_abs.startswith(base_abs)
    except (IOError, OSError, FileNotFoundError, PermissionError):
        return False


def clean_thai_search_query(query: str, search_type: str = "general") -> str:
    """
    [QUERY NORMALIZER & FILLER STRIPPER]
    ทำความสะอาดข้อความค้นหาภาษาไทย ตัดคำสร้อย คำลงท้าย คำฟุ่มเฟือย (เช่น 'ให้หน่อย', 'หน่อยครับ', 'ขอรูป')
    และแปลงสระเบิ้ล (เเ -> แ) เพื่อให้ Search Engines ได้คีย์เวิร์ดที่แม่นยำที่สุด
    """
    if not query:
        return ""
    
    # 1. ปรับมาตรฐานอักขระไทย
    q = query.replace("\u0e40\u0e40", "\u0e41").replace("\u200b", "").replace("\ufeff", "").strip()
    
    # 2. รายการคำสร้อย / คำลงท้าย / คำสุภาพ ที่ติดท้ายประโยค
    suffix_patterns = [
        r'(?:ให้หน่อย(?:ครับ|ค่ะ|นะ|สิ|ซิ|ดิ|เถอะ|จ้า|จ๊ะ)?|หน่อย(?:ครับ|ค่ะ|นะ|สิ|ซิ|ดิ|เถอะ|จ้า|จ๊ะ)?)$',
        r'(?:ให้ที|ให้ด้วย|ให้ผมหน่อย|ให้เราหน่อย|ด้วย(?:ครับ|ค่ะ|จ้า)?)$',
        r'(?:ครับ(?:ผม|ท่าน)?|ค่ะ|คะ|จ้า|จ๊ะ|คับ|นะ(?:ครับ|ค่ะ|จ๊ะ|คับ)?)$',
        r'(?:สิ(?:ครับ|ค่ะ)?|ซิ|ดิ|เถอะ)$',
        r'(?:ได้ไหม(?:ครับ|ค่ะ)?|ได้มั้ย(?:ครับ|ค่ะ)?|ได้รึเปล่า)$',
        r'(?:ที(?:ครับ|ค่ะ)?)$'
    ]
    
    changed = True
    while changed:
        changed = False
        for pat in suffix_patterns:
            new_q = re.sub(pat, '', q).strip()
            if new_q != q and len(new_q) > 0:
                q = new_q
                changed = True
                
    is_chord = any(k in q.lower() for k in ["คอร์ด", "chord", "แท็บ", "tab", "ตารางคอร์ด"]) or search_type == "chord"
    
    if is_chord:
        prefix = r'^(?:ช่วย)?(?:ขอ|หา|ดู|อยากได้|ส่ง|ค้นหา|เสิร์ช)?\s*(?:รูปภาพ|รูป|ภาพ|ตาราง)?\s*(?:คอร์ดเพลง|คอร์ด|แท็บเพลง|แท็บกีตาร์|แท็บ)\s*(?:ของ)?\s*(?:เพลง)?\s*'
        m = re.search(prefix, q)
        if m and m.end() < len(q):
            song = q[m.end():].strip()
            changed = True
            while changed:
                changed = False
                for pat in suffix_patterns:
                    new_song = re.sub(pat, '', song).strip()
                    if new_song != song and len(new_song) > 0:
                        song = new_song
                        changed = True
            song = re.sub(r'^(?:ของ|เพลง)\s*', '', song).strip()
            if song:
                return f"คอร์ดเพลง {song}"
        elif not q.startswith("คอร์ด"):
            return f"คอร์ดเพลง {q}"
    elif search_type == "image" or any(k in q.lower() for k in ["รูป", "ภาพ", "image", "photo"]):
        img_prefix = r'^(?:ช่วย)?(?:ขอ|หา|ดู|อยากได้|ส่ง|ค้นหา|เสิร์ช)\s*(?:รูปภาพ|รูป|ภาพ)\s*(?:ของ)?\s*'
        q = re.sub(img_prefix, '', q).strip()
    else:
        general_prefix = r'^(?:ช่วย)?(?:ขอ|ค้นหา|เสิร์ช|หา|ดู|สืบค้น|เช็ค|เช็ก|อยากทราบ|อยากรู้|บอก)\s*(?:ข้อมูล|เรื่อง)?\s*(?:เกี่ยวกับ)?\s*'
        q = re.sub(general_prefix, '', q).strip()
        
    changed = True
    while changed:
        changed = False
        for pat in suffix_patterns:
            new_q = re.sub(pat, '', q).strip()
            if new_q != q and len(new_q) > 0:
                q = new_q
                changed = True
                
    return q


def extract_clean_song_title(text: str) -> str:
    """สกัดเฉพาะชื่อเพลงแบบสะอาดสะอ้าน ไร้คำสร้อย ไร้คำว่า คอร์ด/รูปคอร์ด เพื่อใช้ในการกล่าวตอบและแสดงผล"""
    cleaned = clean_thai_search_query(text, search_type="chord")
    return re.sub(r'^คอร์ดเพลง\s*', '', cleaned).strip()
