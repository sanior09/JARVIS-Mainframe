"""
get_trending_news.py
──────────────────────────────────────────────────────────────────────────────
Dynamic Tool for J.A.R.V.I.S.
Provides instant access to trending news, social buzz (IG/TikTok/FB), and Google Trends.
Consumes 0 LLM API tokens (reads from pre-harvested cache or crawls free RSS).
──────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import logging
import jarvis_trend_fetcher

logger = logging.getLogger("JarvisDynamicTool.TrendingNews")

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_trending_news",
        "description": "ดึงสรุปข่าวฮิตล่าสุด กระแสโซเชียลมีเดีย ไวรัลยอดนิยมจาก Google Trends, IG, TikTok, ข่าวบันเทิง และข่าวเด่นรอบวัน (กินโควต้า API 0%)",
        "parameters": {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "boolean",
                    "description": "ตั้งเป็น true หากต้องการสั่งดึงข่าวสดใหม่ทันที ณ วินาทีนี้ (ใช้เวลา ~1-2 วินาที)"
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "social", "entertainment", "news"],
                    "description": "หมวดหมู่ที่ต้องการ: all (ทั้งหมด), social (ไวรัลโซเชียล), entertainment (บันเทิงดารา), news (ข่าวเด่น)"
                }
            }
        }
    }
}

def execute(args: dict) -> str:
    """Execute trending news fetch."""
    try:
        should_refresh = args.get("refresh", False)
        category = args.get("category", "all")
        
        if should_refresh:
            logger.info("Forced refresh of trending news requested...")
            data = jarvis_trend_fetcher.TrendFetcher.harvest_all()
        else:
            latest_json = os.path.join(jarvis_trend_fetcher.DATA_DIR, "latest_trends.json")
            if not os.path.exists(latest_json):
                data = jarvis_trend_fetcher.TrendFetcher.harvest_all()
            else:
                with open(latest_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
        total = data.get("total_items", 0)
        timestamp = data.get("timestamp", "ล่าสุด")
        
        output_lines = [
            f"📰 [สรุปข่าวฮิตและกระแสโซเชียลล่าสุด - {timestamp}] (ทั้งหมด {total} เรื่อง)",
            "--------------------------------------------------"
        ]
        
        categories = data.get("categories", {})
        
        for key, cat_data in categories.items():
            cat_name = cat_data.get("name", key)
            cat_type = cat_data.get("category", "")
            
            # Category filtering
            if category == "social" and "Social" not in cat_type and "Trends" not in cat_name:
                continue
            if category == "entertainment" and "Entertainment" not in cat_type:
                continue
            if category == "news" and "News" not in cat_type and "Society" not in cat_type:
                continue
                
            output_lines.append(f"\n{cat_name}:")
            items = cat_data.get("items", [])[:5]
            for i, it in enumerate(items, 1):
                output_lines.append(f"{i}. {it.get('title')} ({it.get('source')})")
                
        output_lines.append("\n💡 ข้อมูลทั้งหมดถูกบันทึกไว้ในโฟลเดอร์ data/trending_news/ พร้อมลิงก์ฉบับเต็มครับ")
        return "\n".join(output_lines)
    except Exception as e:
        logger.error(f"Failed to execute get_trending_news: {e}")
        return f"เกิดข้อผิดพลาดในการดึงข่าวฮิต: {e}"
