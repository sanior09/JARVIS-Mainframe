"""
jarvis_trend_fetcher.py
──────────────────────────────────────────────────────────────────────────────
Autonomous Trending News & Social Buzz Harvester for J.A.R.V.I.S.
Fetches trending topics, social buzz (IG/FB/TikTok/X trends), and top news
every 3 hours with ZERO LLM API token consumption (0% API quota used).
Saves structured markdown reports and JSON data to `data/trending_news/`.
──────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any
import requests
import feedparser

logger = logging.getLogger("JarvisTrendFetcher")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [TRENDS] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, "data", "trending_news")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_INTERVAL_HOURS = 3
DEFAULT_INTERVAL_SECONDS = DEFAULT_INTERVAL_HOURS * 3600

# High-yield feeds covering viral social buzz, search trends, entertainment & breaking news
TREND_FEEDS = {
    "google_trends": {
        "name": "🔥 Google Trends Thailand (ไวรัล/ค้นหายอดนิยม)",
        "url": "https://trends.google.com/trending/rss?geo=TH",
        "category": "Social & Search Buzz",
        "limit": 15
    },
    "google_top_news": {
        "name": "⚡ ข่าวเด่นกระแสหลัก (Top Headlines)",
        "url": "https://news.google.com/rss?hl=th&gl=TH&ceid=TH:th",
        "category": "Breaking News",
        "limit": 15
    },
    "entertainment_viral": {
        "name": "🎬 บันเทิง ดารา โซเชียลมีเดีย (IG/TikTok/Entertainment)",
        "url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=th&gl=TH&ceid=TH:th",
        "category": "Entertainment & Social",
        "limit": 15
    },
    "thairath_news": {
        "name": "📰 ไทยรัฐออนไลน์ (กระแสสังคม/ไวรัล)",
        "url": "https://www.thairath.co.th/rss/news",
        "category": "Society & Viral",
        "limit": 12
    },
    "khaosod_news": {
        "name": "📣 ข่าวสด (ข่าวฮิตรอบวัน)",
        "url": "https://www.khaosod.co.th/feed",
        "category": "General Viral",
        "limit": 12
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

_scheduler_running = False
_scheduler_thread = None

class TrendFetcher:
    """Zero-API-cost crawler for real-time trending news and social buzz."""

    @staticmethod
    def fetch_feed(feed_key: str, feed_info: Dict[str, Any]) -> List[Dict[str, str]]:
        items = []
        try:
            resp = requests.get(feed_info["url"], headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                parsed = feedparser.parse(resp.content)
                for entry in parsed.entries[:feed_info.get("limit", 15)]:
                    title = getattr(entry, "title", "").strip()
                    link = getattr(entry, "link", "").strip()
                    published = getattr(entry, "published", "") or getattr(entry, "updated", "")
                    
                    # Clean title if Google News appends publisher e.g. "Title - Source"
                    source = feed_info["name"]
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        source = parts[1].strip()
                    else:
                        clean_title = title
                    
                    if clean_title:
                        items.append({
                            "title": clean_title,
                            "source": source,
                            "link": link,
                            "published": published,
                            "category": feed_info.get("category", "General")
                        })
            else:
                logger.warning(f"Failed to fetch {feed_info['name']}: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"Error fetching {feed_info['name']}: {e}")
            
        return items

    @classmethod
    def harvest_all(cls) -> Dict[str, Any]:
        """Fetch all trending feeds, deduplicate, and compile report."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_stamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        logger.info(f"🚀 Starting autonomous trending news harvest at {timestamp_str}...")
        
        collected_data = {
            "timestamp": timestamp_str,
            "generated_at": date_stamp,
            "total_items": 0,
            "categories": {}
        }
        
        seen_titles = set()
        all_items_count = 0
        
        for key, info in TREND_FEEDS.items():
            items = cls.fetch_feed(key, info)
            unique_items = []
            for it in items:
                norm_title = it["title"][:50].lower()
                if norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    unique_items.append(it)
                    
            collected_data["categories"][key] = {
                "name": info["name"],
                "category": info["category"],
                "count": len(unique_items),
                "items": unique_items
            }
            all_items_count += len(unique_items)
            
        collected_data["total_items"] = all_items_count
        
        # Save to disk
        cls._save_to_disk(collected_data, date_stamp)
        logger.info(f"✅ Successfully harvested {all_items_count} trending items. Saved to {DATA_DIR}")
        return collected_data

    @classmethod
    def _save_to_disk(cls, data: Dict[str, Any], date_stamp: str):
        # 1. Save JSON (latest and timestamped)
        latest_json_path = os.path.join(DATA_DIR, "latest_trends.json")
        ts_json_path = os.path.join(DATA_DIR, f"trends_{date_stamp}.json")
        
        with open(latest_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        with open(ts_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 2. Save Markdown Report (human-readable & easy for JARVIS to reference)
        md_lines = [
            f"# 🌐 รายงานข่าวฮิตและกระแสโซเชียลประจำวัน (Trending News & Social Buzz)",
            f"**รอบเวลาบันทึก**: `{data['timestamp']}` | **จำนวนหัวข้อทั้งหมด**: `{data['total_items']}` เรื่อง",
            f"**การใช้ API Quota**: `0 Tokens (ฟรี 100% ผ่าน RSS Scraper)`\n",
            "---\n"
        ]
        
        for key, cat_data in data["categories"].items():
            md_lines.append(f"## {cat_data['name']} ({cat_data['count']} หัวข้อ)")
            for idx, item in enumerate(cat_data["items"], 1):
                md_lines.append(f"{idx}. **{item['title']}**")
                if item.get("source"):
                    md_lines.append(f"   - แหล่งที่มา: `{item['source']}`")
                if item.get("link"):
                    md_lines.append(f"   - ลิงก์: [{item['link'][:60]}...]({item['link']})")
            md_lines.append("")
            
        report_content = "\n".join(md_lines)
        
        latest_md_path = os.path.join(DATA_DIR, "latest_trends.md")
        ts_md_path = os.path.join(DATA_DIR, f"trends_{date_stamp}.md")
        
        with open(latest_md_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        with open(ts_md_path, "w", encoding="utf-8") as f:
            f.write(report_content)


def get_latest_trends_summary(top_n: int = 5) -> str:
    """
    Returns a quick text summary of the latest trends for JARVIS to recite.
    Does not make any network or LLM API calls.
    """
    latest_json_path = os.path.join(DATA_DIR, "latest_trends.json")
    if not os.path.exists(latest_json_path):
        # Trigger an immediate harvest if never run before
        TrendFetcher.harvest_all()
        
    try:
        with open(latest_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        summary_lines = [f"สรุปกระแสและข่าวฮิตล่าสุด ({data.get('timestamp', 'ล่าสุด')}):"]
        count = 0
        for cat_key, cat_info in data.get("categories", {}).items():
            items = cat_info.get("items", [])
            if items:
                summary_lines.append(f"\n[{cat_info.get('name', cat_key)}]:")
                for it in items[:3]:
                    count += 1
                    summary_lines.append(f"- {it['title']}")
                    if count >= top_n * 2:
                        break
        return "\n".join(summary_lines)
    except Exception as e:
        return f"ไม่สามารถโหลดข่าวฮิตล่าสุดได้: {e}"


def _background_loop(interval_seconds: int):
    global _scheduler_running
    logger.info(f"⏰ Trending News Scheduler active. Interval: {interval_seconds // 3600} ชั่วโมง ({interval_seconds} วินาที).")
    
    # Run first harvest immediately
    try:
        TrendFetcher.harvest_all()
    except Exception as e:
        logger.error(f"Initial trend harvest error: {e}")
        
    while _scheduler_running:
        try:
            time.sleep(interval_seconds)
            if _scheduler_running:
                TrendFetcher.harvest_all()
        except Exception as e:
            logger.error(f"Periodic trend harvest error: {e}")


def start_background_scheduler(interval_hours: int = DEFAULT_INTERVAL_HOURS):
    """Start recurring background thread that runs every N hours."""
    global _scheduler_running, _scheduler_thread
    if _scheduler_running:
        logger.info("Trending News Scheduler already running.")
        return
        
    _scheduler_running = True
    interval_seconds = interval_hours * 3600
    _scheduler_thread = threading.Thread(
        target=_background_loop,
        args=(interval_seconds,),
        daemon=True,
        name="JarvisTrendHarvester"
    )
    _scheduler_thread.start()
    logger.info(f"✅ Started JarvisTrendHarvester daemon thread (Every {interval_hours} hours).")


def stop_background_scheduler():
    global _scheduler_running
    _scheduler_running = False
    logger.info("Stopped Trending News Scheduler.")


if __name__ == "__main__":
    print("Testing J.A.R.V.I.S. Trending News Fetcher...")
    result = TrendFetcher.harvest_all()
    print(f"Total trends harvested: {result['total_items']}")
    print("\nSummary for J.A.R.V.I.S.:")
    print(get_latest_trends_summary(5))
