"""
jarvis_core/cognitive/grounding_engine.py
──────────────────────────────────────────────────────────────────────────────
Real-Time Temporal & World Intelligence Grounding Engine for J.A.R.V.I.S.
Prevents parametric hallucinations and temporal anachronisms by injecting
live RSS feeds, verified headlines, and current timestamp telemetry into
AI completions for time-sensitive inquiries.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.CognitiveGrounding")


class RealTimeGroundingEngine:
    """
    Subsystem responsible for grounding J.A.R.V.I.S. with real-time external facts,
    eliminating hallucinated "today" events and anchoring the LLM in the current date.
    """

    GENERAL_RSS_URL = "https://news.google.com/rss?hl=th&gl=TH&ceid=TH:th"
    TECH_RSS_URL = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=th&gl=TH&ceid=TH:th"
    SEARCH_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=th&gl=TH&ceid=TH:th"

    # Keywords indicating a real-time temporal intelligence request
    GROUNDING_PATTERNS = [
        r"(วันนี้มีอะไร|มีอะไรใหม่|มีอะไรน่าสนใจ|อัปเดตวันนี้|ข่าววันนี้|สถานการณ์วันนี้|สรุปข่าว|ข่าวล่าสุด|เหตุการณ์วันนี้)",
        r"(ข่าวเทค|ข่าวไอที|ข่าวเทคโนโลยี|อัปเดตเทค|tech\s*news|ai\s*update)",
        r"(what'?s\s*new|daily\s*briefing|today'?s\s*news|latest\s*news|happening\s*today)",
        r"(ราคาทอง|ราคาน้ำมัน|ดัชนีหุ้น|ตลาดหุ้น)"
    ]

    TECH_PATTERNS = [
        r"(เทคโนโลยี|ไอที|เทค|แกดเจ็ต|ai|ปัญญาประดิษฐ์|สมาร์ตโฟน|มือถือ|ชิป|ฮาร์ดแวร์|tech|gadget)"
    ]

    def __init__(self, core_ref: Optional[Any] = None):
        self.core = core_ref
        self.is_active = True
        self._cache: Dict[str, Tuple[float, List[str]]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        logger.info("📡 [GROUNDING ENGINE] Real-Time Grounding Engine initialized.")

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self.is_active = True
        return True

    def shutdown(self):
        self.is_active = False
        self._cache.clear()
        logger.info("📡 [GROUNDING ENGINE] Shut down cleanly.")

    def is_grounding_query(self, query: str) -> bool:
        """Determines if the query demands real-time temporal and news grounding."""
        if not query or len(query.strip()) < 3:
            return False

        q_clean = query.strip().lower()
        for pattern in self.GROUNDING_PATTERNS:
            if re.search(pattern, q_clean):
                return True
        return False

    def detect_category(self, query: str) -> str:
        """Categorizes whether the query is tech-focused or general world news."""
        q_clean = query.strip().lower()
        for pattern in self.TECH_PATTERNS:
            if re.search(pattern, q_clean):
                return "technology"
        return "general"

    def fetch_live_headlines(self, query_text: str = "", limit: int = 5) -> List[str]:
        """
        Fetches live headlines from Google News RSS with caching and timeout safety.
        Returns a list of headline strings.
        """
        category = self.detect_category(query_text)
        now = time.time()

        # Extract specific search topic if user specified (e.g. 'ข่าวเกี่ยวกับ AI')
        search_topic = None
        topic_match = re.search(r"(?:ข่าว|news)(?:\s*(?:เกี่ยวกับ|เรื่อง))?\s+([\w\s\-]+)", query_text, re.IGNORECASE)
        if topic_match:
            candidate = topic_match.group(1).strip()
            # Avoid using generic words as topic
            if candidate and candidate not in ["วันนี้", "ล่าสุด", "ใหม่", "ใหม่ๆ", "น่าสนใจ", "ด่วน"]:
                search_topic = candidate

        cache_key = search_topic if search_topic else category
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if now - cached_time < self._cache_ttl:
                return cached_data[:limit]

        # Determine target URL
        if search_topic:
            encoded_q = urllib.parse.quote(search_topic)
            url = self.SEARCH_RSS_URL.format(query=encoded_q)
        elif category == "technology":
            url = self.TECH_RSS_URL
        else:
            url = self.GENERAL_RSS_URL

        headlines: List[str] = []
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) J.A.R.V.I.S./Cognitive"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as response:
                content = response.read()
                root = ET.fromstring(content)
                for item in root.findall(".//item")[:limit]:
                    title_elem = item.find("title")
                    if title_elem is not None and title_elem.text:
                        headlines.append(title_elem.text.strip())

            if headlines:
                self._cache[cache_key] = (now, headlines)
                logger.info(f"📡 [GROUNDING ENGINE] Fetched {len(headlines)} live items for [{cache_key}].")
        except Exception as e:
            logger.warning(f"⚠️ [GROUNDING ENGINE] Failed to fetch live headlines for [{cache_key}]: {e}")
            if cache_key in self._cache:
                return self._cache[cache_key][1][:limit]

        return headlines[:limit]

    def get_grounding_prompt_injection(self, query: str) -> Optional[str]:
        """
        Generates prompt grounding injection containing current date/time and live verified
        headlines if the query requires temporal intelligence.
        """
        if not self.is_grounding_query(query):
            return None

        headlines = self.fetch_live_headlines(query, limit=5)
        now_dt = datetime.now()
        date_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Thai date formatting for precision
        thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
        thai_months = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
            "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
        ]
        day_name = thai_days[now_dt.weekday()]
        month_name = thai_months[now_dt.month - 1]
        thai_date_display = f"วัน{day_name}ที่ {now_dt.day} {month_name} ค.ศ. {now_dt.year}"

        category = self.detect_category(query)
        lines = [
            "\n\n==================================================",
            "⚡ [REAL-TIME TEMPORAL GROUNDING & LIVE WORLD INTEL]",
            f"📅 CURRENT REAL-WORLD TIME: {thai_date_display} ({date_str} Local Time)",
            f"🌐 LIVE VERIFIED FEED ({category.upper()} INTEL):"
        ]

        if headlines:
            for idx, h in enumerate(headlines, 1):
                lines.append(f"  {idx}. {h}")
        else:
            lines.append("  (ขณะนี้เครือข่าย RSS ภายนอกขัดข้อง โปรดระบุตามตรงว่าไม่สามารถดึงข้อมูลข่าวสดได้ในเสี้ยววินาทีนี้)")

        lines.extend([
            "",
            "CRITICAL INSTRUCTIONS FOR J.A.R.V.I.S.:",
            f"1. You are answering a question about TODAY ({thai_date_display}).",
            "2. Strictly base your world update/briefing on the verified live headlines listed above.",
            "3. NEVER fabricate or hallucinate product launches, events, or breakthroughs from 2024 or earlier and pretend they happened 'today'.",
            "4. Synthesize the briefing with J.A.R.V.I.S.'s signature British butler intellect, sharp wit, and concise poise.",
            "==================================================\n"
        ])

        return "\n".join(lines)

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "name": "RealTimeGroundingEngine",
            "active": self.is_active,
            "cached_feeds": list(self._cache.keys())
        }


grounding_engine = RealTimeGroundingEngine()
