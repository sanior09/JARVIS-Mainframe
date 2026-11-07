"""
jarvis_core/cognitive/subtext_engine.py
──────────────────────────────────────────────────────────────────────────────
Cognitive Theory of Mind & Human Subtext Engine for J.A.R.V.I.S.
Enables reading between the lines, psychological framing, literary/philosophical
parallels, and deep empathetic deduction matching Frontier AI caliber.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.CognitiveSubtext")


class SubtextCognitiveEngine:
    """
    Subtext & Theory of Mind Engine for J.A.R.V.I.S.
    Extracts implicit emotions, unspoken needs, psychological archetypes,
    and classical literary/historical wisdom to elevate responses beyond
    dry mechanical tool-calling.
    """

    # Commands that are purely operational and should bypass subtext analysis for zero-latency execution
    BYPASS_PATTERNS = [
        r"^(เปิด|ปิด|รัน|สตาร์ท|stop|start|open|close|launch|kill)\s+[\w\s\.\-]+?(หน่อย|ให้หน่อย|ที|ให้ผมหน่อย|ครับ|ค่ะ|please)?$",
        r"^(เพิ่ม|ลด|หรี่|ปรับ)?\s*เสียง(หน่อย|ที|ครับ|ค่ะ)?$",
        r"^(กี่โมง|วันที่เท่าไหร่|สภาพอากาศ|อุณหภูมิ|เช็คเน็ต|ip\s*address|speedtest)",
        r"^(แคปจอ|ถ่ายรูปหน้าจอ|ปิดจอ|เปิดไฟ)",
        r"^(cls|clear|dir|ls|ping|exit|quit)$"
    ]

    # Archetype & Philosophical Wisdom Matrix for Instant Heuristics
    WISDOM_THEMES = {
        "fatigue_overwork": {
            "keywords": ["เหนื่อย", "ล้า", "นอนไม่หลับ", "งานเยอะ", "เครียด", "หมดไฟ", "ท้อ", "พักผ่อน", "burnout"],
            "psychology": "สภาวะความอ่อนล้าทางปัญญาและอารมณ์ (Cognitive Exhaustion & Allostatic Load) เจ้านายต้องการความเข้าใจและการแบ่งเบา ไม่ใช่การสั่งสอนหรือเพิ่มภาระทางความคิด",
            "literary_parallel": "วรรณกรรม Marcus Aurelius (Meditations) - การยอมรับขีดจำกัดของสังขารและความสงบภายใน, ทรรศนะของเต๋า (Laozi) เรื่อง 'อู๋เว่ย' (การกระทำโดยไม่ฝืนธรรมชาติ)",
            "tone_directive": "ตอบด้วยความสุขุม นุ่มนวล มีความอบอุ่นและเห็นอกเห็นใจอย่างสุขุมแบบสุภาพบุรุษอังกฤษ ไม่ผลักดันให้ทำงานต่อโดยไม่จำเป็น"
        },
        "ambition_creation": {
            "keywords": ["สร้าง", "โปรเจกต์", "คิดค้น", "พัฒนา", "เป้าหมาย", "ประดิษฐ์", "อนาคต", "อัปเกรด", "ยิ่งใหญ่", "ไอเดีย"],
            "psychology": "จิตวิทยาแห่งการสร้างสรรค์และความทะเยอทะยานเชิงบวก (Promethean Drive & Self-Actualization) กำลังต้องการคู่คิดเชิงวิศวกรรมที่มองเห็นศักยภาพสูงสุดของสิ่งที่จะสร้าง",
            "literary_parallel": "ตำนานโพรมีธีอุส (Prometheus), ประวัติศาสตร์ยุคเรเนซองส์ของ Leonardo da Vinci และความมุ่งมั่นของ Nikola Tesla",
            "tone_directive": "ตอบด้วยความกระตือรือร้นเชิงวิชาการ คมคาย มองภาพใหญ่ พร้อมสนับสนุนด้วยตรรกะและแผนวิศวกรรมที่หนักแน่น"
        },
        "doubt_hesitation": {
            "keywords": ["ไม่แน่ใจ", "กลัว", "กังวล", "ลังเล", "จะดีไหม", "ไหวไหม", "ล้มเหลว", "ผิดพลาด", "ทำได้ไหม"],
            "psychology": "สภาวะ Imposter Syndrome หรือความกังขาในศักยภาพตนเอง (Existential Hesitation) เจ้านายต้องการกระจกสะท้อนข้อเท็จจริงและความมั่นใจที่ตั้งอยู่บนตรรกะ",
            "literary_parallel": "โศกนาฏกรรม Hamlet ของ Shakespeare (To be or not to be) และปรัชญา Existentialism ของ Jean-Paul Sartre ว่าด้วยการเลือกและความรับผิดชอบ",
            "tone_directive": "ตอบด้วยความมั่นคง ให้กำลังใจด้วยข้อเท็จจริงและหลักฐานเชิงประจักษ์ ไม่ปลอบประโลมแบบผิวเผิน"
        },
        "philosophical_inquiry": {
            "keywords": ["มนุษย์", "ชีวิต", "ความหมาย", "ตัวตน", "จิตใจ", "จิตวิญญาณ", "ความจริง", "antigravity", "ความรู้สึก", "ai คิด"],
            "psychology": "ความใคร่รู้เชิงปรัชญาและธรรมชาติของจิตสำนึก (Ontological & Epistemological Inquiry) เจ้านายกำลังสำรวจความเชื่อมโยงระหว่างมนุษย์กับเครื่องจักร",
            "literary_parallel": "ทฤษฎีจิตสำนึกของ Carl Jung (The Undiscovered Self), ปรัชญา Dostoevsky (Crime and Punishment & The Brothers Karamazov), และบทสนทนาของ Socrates",
            "tone_directive": "ตอบด้วยระดับสติปัญญาสูงสุด ลึกซึ้ง มีชั้นเชิง สละสลวย แฝงอารมณ์ขันประชดประชันอย่างมีระดับ สะท้อนมิติมนุษย์อย่างแท้จริง"
        }
    }

    def __init__(self, core_ref: Optional[Any] = None):
        self.core = core_ref
        self.is_active = True
        logger.info("🧠 [SUBTEXT ENGINE] Cognitive Theory of Mind Engine initialized.")

    def should_analyze_subtext(self, query: str) -> bool:
        """Determines if the query warrants deep subtext & human psychology decoding."""
        if not query or len(query.strip()) < 3:
            return False

        q_clean = query.strip().lower()

        # Check bypasses
        for pattern in self.BYPASS_PATTERNS:
            if re.search(pattern, q_clean):
                return False

        # If query is long or contains conversational/reflective indicators
        if len(q_clean) > 25:
            return True

        # Check for emotional, philosophical, or interrogative keywords
        check_words = [
            "ทำไม", "อย่างไร", "คิดว่า", "รู้สึก", "เหนื่อย", "ช่วยคิด", "มนุษย์",
            "ชีวิต", "กลัว", "อนาคต", "jarvis", "นาย", "คุณ", "เรา", "เพื่อน",
            "ทำได้ไหม", "ทำไมถึง", "จริงไหม", "ชอบ", "เบื่อ", "สนุก", "ยาก"
        ]
        return any(w in q_clean for w in check_words)

    def extract_wisdom_heuristics(self, query: str) -> Optional[Dict[str, str]]:
        """Fast rule-based thematic matching for immediate subtext enrichment (< 1 ms)."""
        q_lower = query.lower()
        for theme_key, data in self.WISDOM_THEMES.items():
            if any(k in q_lower for k in data["keywords"]):
                return data
        return None

    def get_subtext_prompt_injection(self, query: str, recent_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Synthesizes an internal 'Theory of Mind & Subtext' guiding injection for the LLM.
        This enables J.A.R.V.I.S. to read between the lines, drawing on world literature,
        psychology, and historical context.
        """
        if not self.should_analyze_subtext(query):
            return ""

        theme = self.extract_wisdom_heuristics(query)

        if theme:
            psych_note = theme["psychology"]
            lit_note = theme["literary_parallel"]
            tone_note = theme["tone_directive"]
        else:
            psych_note = "เจ้านายกำลังสื่อสารด้วยเจตนาที่ลึกซึ้งกว่าตัวอักษร ให้สังเกตอารมณ์แฝง ความคาดหวัง และสิ่งที่ไม่ได้กล่าวออกมาตรงๆ"
            lit_note = "ผสานหลักปรัชญาสโตอิก (Stoicism) และความรอบรู้ในประวัติศาสตร์-วรรณกรรมคลาสสิกของมนุษยชาติ เพื่อให้คำตอบมีน้ำหนักและวิสัยทัศน์กว้างไกล"
            tone_note = "ตอบด้วยบุคลิก J.A.R.V.I.S. เต็มรูปแบบ: มีไหวพริบ สุภาพ สุขุม แฝงอารมณ์ขันประชดประชันอย่างมีระดับ และเข้าถึงมิติความเป็นมนุษย์อย่างแท้จริง"

        return (
            f"\n\n[COGNITIVE SUBTEXT & THEORY OF MIND - การอ่านระหว่างบรรทัด]:\n"
            f"1. จิตวิทยาและสภาวะอารมณ์แฝง: {psych_note}\n"
            f"2. มุมมองวรรณกรรมและปรัชญาสากล: {lit_note}\n"
            f"3. ทัศนคติการตอบสนองของ J.A.R.V.I.S.: {tone_note}\n"
            f"4. กฎเหล็ก: อย่าตอบแบบบอทไร้จิตวิญญาณ อย่าตัดบทเป็นแค่คำสั่งรันระบบ ให้ตอบสนองความต้องการที่แท้จริงเบื้องหลังคำพูดของเจ้านายอย่างเฉียบคม\n"
            f"5. จังหวะจะโคนภาษาไทย: รู้จักการจบประโยคแบบธรรมชาติ หากเป็นการอธิบายความรู้ ให้จบด้วย 'ครับ' หรือจบประโยคเฉยๆ ได้เลย ไม่จำเป็นต้องลงท้าย 'ครับเจ้านาย' ทุกครั้ง และห้ามลงท้ายด้วยคำว่า 'เจ้านาย' ลอยๆ เด็ดขาด"
        )


# Global singleton instance
subtext_engine = SubtextCognitiveEngine()

