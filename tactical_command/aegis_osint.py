"""
Project Aegis: Open Source Intelligence (OSINT) Miner (Module 4)
Gathers threat intelligence and latest cyber news from public RSS feeds.
"""
import time
import feedparser
from .core import BaseDataCollector, InMemoryCache, logger

# Known Cyber Threat Intelligence Feeds
FEEDS = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "CISA Alerts": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
}

class AegisOSINTCollector(BaseDataCollector):
    """Collects OSINT data from RSS feeds."""
    def __init__(self, cache: InMemoryCache):
        super().__init__(cache)
    
    def fetch_threat_intel(self) -> dict:
        """Fetch the latest threat intel from RSS feeds."""
        intel_data = []
        for source, url in FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]: # Top 3 recent per feed
                    intel_data.append({
                        "source": source,
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published", ""),
                    })
            except Exception as e:
                logger.error(f"[AEGIS OSINT] Error fetching from {source}: {e}")
        
        return {
            "status": "success",
            "timestamp": time.time(),
            "threat_intel": intel_data
        }
    
    def get_latest_intel(self) -> dict:
        """Returns intel data, using cache if fresh."""
        cache_key = "aegis_osint"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        logger.info("[AEGIS OSINT] Fetching fresh threat intel...")
        data = self.fetch_threat_intel()
        self.cache.set(cache_key, data, ttl=1800) # 30 min cache
        return data

# Singleton instance
cache_store = InMemoryCache()
aegis_collector = AegisOSINTCollector(cache_store)

def get_threat_intel():
    """Helper function to be called from main JARVIS logic."""
    return aegis_collector.get_latest_intel()
