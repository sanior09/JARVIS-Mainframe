"""
jarvis_core/research_service.py
===============================
Modular Service for Autonomous Multi-Step Deep Web Research,
Page Content Scraping, and Structured Technical Report Synthesis.
"""

from __future__ import annotations

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("JarvisResearchService")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [RESEARCH-SERVICE] %(levelname)s - %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _clean_html_to_markdown(html_content: str, max_chars: int = 4000) -> str:
    """Strip unnecessary HTML elements and extract clean textual content."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
            tag.decompose()
            
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n...[เนื้อหาถูกตัดทอนตามขีดจำกัด]..."
        return cleaned
    except Exception as e:
        logger.warning(f"Failed to clean HTML: {e}")
        return ""


def fetch_and_clean_url(url: str, timeout: int = 8) -> Dict[str, Any]:
    """Fetch content from a single URL and return clean text summary."""
    headers = {"User-Agent": USER_AGENT}
    try:
        res = requests.get(url, headers=headers, timeout=timeout)
        res.raise_for_status()
        cleaned_text = _clean_html_to_markdown(res.text)
        domain = urlparse(url).netloc
        return {
            "status": "success",
            "url": url,
            "domain": domain,
            "content": cleaned_text
        }
    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "error": str(e)
        }


def autonomous_deep_research(query: str, max_sources: int = 3) -> Dict[str, Any]:
    """
    Perform deep autonomous research:
    1. Search query via DuckDuckGo
    2. Extract top URLs
    3. Scrape and clean page content
    4. Compile source summaries
    """
    logger.info(f"Initiating autonomous research for: '{query}'")
    search_results: List[Dict[str, str]] = []

    # 1. Search DuckDuckGo
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_sources * 2))
            for r in raw_results:
                search_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", ""))
                })
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")

    # Fallback to wikipedia if empty
    if not search_results:
        try:
            wiki_url = f"https://th.wikipedia.org/w/api.php?action=opensearch&search={requests.utils.quote(query)}&limit=3&namespace=0&format=json"
            w_res = requests.get(wiki_url, timeout=5).json()
            if len(w_res) >= 4 and w_res[1]:
                for title, link in zip(w_res[1], w_res[3]):
                    search_results.append({
                        "title": title,
                        "url": link,
                        "snippet": f"ข้อมูลจากวิกิพีเดียสำหรับหัวข้อ {title}"
                    })
        except Exception:
            pass

    # 2. Scrape top sources
    gathered_sources = []
    for item in search_results[:max_sources]:
        url = item.get("url")
        if not url:
            continue
        page_info = fetch_and_clean_url(url)
        if page_info["status"] == "success" and page_info.get("content"):
            gathered_sources.append({
                "title": item.get("title", "No Title"),
                "url": url,
                "domain": page_info.get("domain", ""),
                "snippet": item.get("snippet", ""),
                "full_text_extract": page_info.get("content", "")[:1500]
            })

    return {
        "status": "success",
        "query": query,
        "total_sources_found": len(search_results),
        "scraped_sources_count": len(gathered_sources),
        "sources": gathered_sources
    }


def synthesize_technical_report(topic: str, findings: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate a formatted technical Markdown report and persist it to `reports/`.
    """
    timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
    clean_topic_slug = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')[:30]
    filename = f"research_{clean_topic_slug}_{timestamp_str}.md"
    report_path = os.path.join(REPORTS_DIR, filename)

    content_lines = [
        f"# รายงานผลการสืบค้นและวิจัยเชิงลึก (J.A.R.V.I.S. Research Matrix)",
        f"**หัวข้อการสืบค้น:** {topic}",
        f"**วันที่บันทึก:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**สถานะ:** สังเคราะห์ข้อมูลเสร็จสมบูรณ์",
        "\n---\n",
        "## สาระสำคัญและข้อค้นพบหลัก (Executive Summary)",
        findings,
        "\n---\n",
        "## แหล่งข้อมูลอ้างอิง (Citations & Sources)"
    ]

    if sources:
        for s in sources:
            content_lines.append(f"- [{s}]({s})")
    else:
        content_lines.append("- บันทึกข้อมูลจากการประมวลผลภายในระบบและ Web Scraping")

    content_lines.append("\n---\n*จัดทำโดย: J.A.R.V.I.S. Autonomous Research Sub-Agent*")

    full_report_text = "\n".join(content_lines)

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report_text)

        logger.info(f"Saved research report to: {report_path}")
        return {
            "status": "success",
            "filename": filename,
            "filepath": report_path,
            "message": f"บันทึกรายงานวิจัยเรื่อง '{topic}' ลงในไฟล์ {filename} เรียบร้อยแล้วครับ",
            "report_preview": full_report_text[:600]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ไม่สามารถบันทึกรายงานได้: {str(e)}"
        }
