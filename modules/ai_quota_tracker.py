"""
modules/ai_quota_tracker.py
─────────────────────────────────────────────────────────────
Real-time AI API Quota & Usage Tracker for J.A.R.V.I.S.
Tracks daily requests and token quotas for:
- Groq Cloud (Free Tier limit: ~14,400 RPD / 30 RPM)
- Google Gemini (Free Tier limit: ~1,500 RPD / 15 RPM)
- Ollama Local (Unlimited local hardware processing)

Persists stats into system_cache/ai_quota_stats.json.
Automatically resets at midnight (00:00).
"""

from __future__ import annotations

import os
import time
import json
import logging
import threading
from typing import Dict, Any, Tuple

logger = logging.getLogger("JARVIS_QUOTA")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "system_cache")
STATS_FILE = os.path.join(CACHE_DIR, "ai_quota_stats.json")

_LOCK = threading.Lock()

# Daily Free Tier request caps
GROQ_DAILY_LIMIT = int(os.getenv("GROQ_DAILY_LIMIT", "14400"))
GEMINI_DAILY_LIMIT = int(os.getenv("GEMINI_DAILY_LIMIT", "1500"))


def _get_today_str() -> str:
    return time.strftime("%Y-%m-%d")


def _init_stats(today: str) -> Dict[str, Any]:
    return {
        "date": today,
        "groq_calls": 0,
        "gemini_calls": 0,
        "ollama_calls": 0,
        "groq_tokens": 0,
        "gemini_tokens": 0,
        "last_call_time": 0.0,
        "last_provider": "none",
        "created_at": time.time(),
    }


def _load_stats_unlocked() -> Dict[str, Any]:
    today = _get_today_str()
    if not os.path.exists(STATS_FILE):
        return _init_stats(today)

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("date") != today:
            logger.info(f"[QUOTA] Daily reset triggered for new date: {today}")
            return _init_stats(today)
        return data
    except Exception as e:
        logger.warning(f"[QUOTA] Error reading stats file: {e}. Reinitializing.")
        return _init_stats(today)


def _save_stats_unlocked(data: Dict[str, Any]) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        temp_file = STATS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(STATS_FILE):
            os.replace(temp_file, STATS_FILE)
        else:
            os.rename(temp_file, STATS_FILE)
    except Exception as e:
        logger.error(f"[QUOTA] Failed to persist stats: {e}")


def record_call(provider: str, tokens: int = 0) -> None:
    """Record a successful AI request call to Groq, Gemini, or Ollama"""
    prov = provider.lower().strip()
    with _LOCK:
        stats = _load_stats_unlocked()
        stats["last_call_time"] = time.time()
        stats["last_provider"] = prov

        if "groq" in prov:
            stats["groq_calls"] = stats.get("groq_calls", 0) + 1
            stats["groq_tokens"] = stats.get("groq_tokens", 0) + tokens
        elif "gemini" in prov:
            stats["gemini_calls"] = stats.get("gemini_calls", 0) + 1
            stats["gemini_tokens"] = stats.get("gemini_tokens", 0) + tokens
        elif "ollama" in prov or "local" in prov:
            stats["ollama_calls"] = stats.get("ollama_calls", 0) + 1

        _save_stats_unlocked(stats)
        logger.debug(f"[QUOTA] Recorded call for {prov}. Groq: {stats.get('groq_calls')}, Gemini: {stats.get('gemini_calls')}, Ollama: {stats.get('ollama_calls')}")


def get_quota_stats() -> Dict[str, Any]:
    """Retrieve formatted usage stats and percentage calculations"""
    with _LOCK:
        data = _load_stats_unlocked()

    groq_calls = data.get("groq_calls", 0)
    gemini_calls = data.get("gemini_calls", 0)
    ollama_calls = data.get("ollama_calls", 0)

    # Calculate percentages; if calls > 0, ensure at least 1% is visible for user feedback
    groq_pct = int((groq_calls / GROQ_DAILY_LIMIT) * 100) if GROQ_DAILY_LIMIT > 0 else 0
    if groq_calls > 0 and groq_pct == 0:
        groq_pct = 1

    gemini_pct = int((gemini_calls / GEMINI_DAILY_LIMIT) * 100) if GEMINI_DAILY_LIMIT > 0 else 0
    if gemini_calls > 0 and gemini_pct == 0:
        gemini_pct = 1

    ollama_pct = 0  # Local has no remote quota

    total_calls = groq_calls + gemini_calls + ollama_calls
    streak_badge = f"Calls: {total_calls} | Online" if total_calls > 0 else "Core Online | Standby"

    return {
        "date": data.get("date", _get_today_str()),
        "total_calls": total_calls,
        "groq": {
            "calls": groq_calls,
            "limit": GROQ_DAILY_LIMIT,
            "pct": min(100, groq_pct),
            "remaining": max(0, GROQ_DAILY_LIMIT - groq_calls)
        },
        "gemini": {
            "calls": gemini_calls,
            "limit": GEMINI_DAILY_LIMIT,
            "pct": min(100, gemini_pct),
            "remaining": max(0, GEMINI_DAILY_LIMIT - gemini_calls)
        },
        "ollama": {
            "calls": ollama_calls,
            "limit": 0,
            "pct": 0,
            "status": "Local Offline (Unlimited)"
        },
        "streak_badge": streak_badge
    }


def get_gauge_values() -> Tuple[int, int, int]:
    """Returns (groq_pct, gemini_pct, ollama_pct) for dynamic island gauges"""
    stats = get_quota_stats()
    return (
        stats["groq"]["pct"],
        stats["gemini"]["pct"],
        stats["ollama"]["pct"]
    )


def get_summary_text() -> str:
    """Thai summary message suitable for voice replies or chat prompts"""
    stats = get_quota_stats()
    g = stats["groq"]
    m = stats["gemini"]
    o = stats["ollama"]
    return (
        f"📊 รายงานโควต้า AI ประจำวันนี้ ({stats['date']}):\n"
        f"- ⚡ Groq (120B): ใช้ไป {g['calls']:,} / {g['limit']:,} ครั้ง ({g['pct']}%)\n"
        f"- 🌟 Google Gemini: ใช้ไป {m['calls']:,} / {m['limit']:,} ครั้ง ({m['pct']}%)\n"
        f"- 🔒 Ollama Local: เรียกใช้ {o['calls']:,} ครั้ง (ในเครื่อง ไม่จำกัดโควต้า)\n"
        f"รวมคำสั่ง AI วันนี้: {stats['total_calls']:,} ครั้งครับเจ้านาย"
    )
