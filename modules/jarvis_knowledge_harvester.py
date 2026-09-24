import os
import time
import logging
from bs4 import BeautifulSoup
import requests
try:
    import wikipedia
    from youtube_transcript_api import YouTubeTranscriptApi
    from duckduckgo_search import DDGS
except ImportError:
    pass  

logger = logging.getLogger(__name__)

LEARNED_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_data")

def save_to_learned_data(title: str, content: str):
    """
    บันทึกเนื้อหาลงโฟลเดอร์ learned_data เพื่อให้ jarvis_auto_ingest ดึงไปประมวลผลต่อ
    """
    if not os.path.exists(LEARNED_DATA_DIR):
        os.makedirs(LEARNED_DATA_DIR)
        
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_title}_{int(time.time())}.md"
    filepath = os.path.join(LEARNED_DATA_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(content)
        logger.info(f"[HARVESTER] Saved knowledge to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"[HARVESTER] Error saving {title}: {e}")
        return None

def fetch_wikipedia(query: str, lang: str = "th", auto_suggest: bool = False):
    """
    ค้นหาและดึงเนื้อหาจาก Wikipedia
    """
    try:
        wikipedia.set_lang(lang)
        logger.info(f"[HARVESTER] Searching Wikipedia for: {query} (lang: {lang})")
        
        page = wikipedia.page(query, auto_suggest=auto_suggest)
        title = page.title
        content = page.content
        
        filepath = save_to_learned_data(f"Wiki_{title}", content)
        return f"Successfully harvested Wikipedia data on '{title}' and saved to {filepath}"
    
    except wikipedia.exceptions.DisambiguationError as e:
        logger.warning(f"[HARVESTER] Disambiguation for '{query}': {e.options}")
        return f"Query '{query}' is too broad. Options: {e.options[:5]}..."
    except wikipedia.exceptions.PageError:
        logger.warning(f"[HARVESTER] Page not found for '{query}'")
        return f"No Wikipedia page found for '{query}' in language '{lang}'."
    except Exception as e:
        logger.error(f"[HARVESTER] Wikipedia API error: {e}")
        return f"Error fetching Wikipedia data: {e}"

def fetch_web_article(url: str):
    """
    ดึงเนื้อหาจาก URL ทั่วไป (Basic text extraction)
    """
    try:
        logger.info(f"[HARVESTER] Fetching web article from {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator='\n')
        
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        content = '\n'.join(chunk for chunk in chunks if chunk)
        
        title = soup.title.string if soup.title else "Web_Article"
        
        filepath = save_to_learned_data(title, content)
        return f"Successfully harvested web data '{title}' and saved to {filepath}"
        
    except Exception as e:
        logger.error(f"[HARVESTER] Error fetching web article {url}: {e}")
        return f"Error fetching web article: {e}"

def autonomous_research(topic: str, num_results: int = 3):
    """
    ใช้นักวิจัยอัตโนมัติ (DuckDuckGo) ค้นหาและดึงเนื้อหาจากเว็บที่เกี่ยวข้อง
    """
    logger.info(f"[HARVESTER] Autonomous research on '{topic}'")
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(topic, max_results=num_results):
                results.append(r)
        
        saved_files = []
        for res in results:
            url = res.get("href")
            if url:
                file_path = fetch_web_article(url)
                if file_path and not file_path.startswith("Error"):
                    saved_files.append(file_path)
        
        return f"Autonomous research completed for '{topic}'. Harvested {len(saved_files)} sources."
    except Exception as e:
        logger.error(f"[HARVESTER] Autonomous research error: {e}")
        return f"Error during autonomous research: {e}"

def fetch_youtube_transcript(video_url: str):
    """
    ดึง Transcript จากวิดีโอ YouTube
    """
    try:
        
        video_id = ""
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        
        if not video_id:
            return "Invalid YouTube URL."
            
        logger.info(f"[HARVESTER] Fetching transcript for YouTube ID: {video_id}")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['th', 'en'])
        
        full_text = " ".join([t['text'] for t in transcript_list])
        title = f"YouTube_Transcript_{video_id}"
        
        filepath = save_to_learned_data(title, full_text)
        return f"Successfully harvested YouTube transcript for {video_id} and saved to {filepath}"
        
    except Exception as e:
        logger.error(f"[HARVESTER] YouTube transcript error: {e}")
        return f"Error fetching YouTube transcript: {e}"
