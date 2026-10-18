"""
[J.A.R.V.I.S. TACTICAL OSINT MATRIX - SHERLOCK & MULTI-ACCOUNT RECON ENGINE]
Nachapol Industries Advanced Cyber Intelligence System

Empowered with:
1. Exact Handle Scan: Direct 1:1 match across 400+ platforms.
2. Multi-Account Sweep (Entity Discovery): Scans multiple variations & platform APIs
   to surface all accounts across Instagram, TikTok, GitHub, Telegram, Reddit, etc.
"""

import os
import sys
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger("JARVIS_OSINT")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "osint")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_sherlock_python() -> str:
    """
    Locates the Python interpreter with sherlock_project available.
    Prefers sys.executable, then checks the project's venv.
    """
    try:
        import sherlock_project  # noqa: F401
        return sys.executable
    except ImportError:
        pass

    venv_py = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_py):
        return venv_py
    return sys.executable


# Curated High-Priority Targets for Fast Sweeps
TOP_SITES = [
    # Developer & Tech
    "GitHub", "GitLab", "Docker Hub", "Kaggle", "HackerNews", "CodeSandbox", "HackTheBox", "Medium",
    # Social & Messaging
    "Twitter", "threads", "Reddit", "Telegram", "TikTok", "Instagram", "Pinterest", "Linktree",
    # Gaming & Media
    "Steam Community (User)", "Twitch", "YouTube", "Spotify", "Roblox", "Patreon"
]

CATEGORY_MAPPING = {
    "Developer & Code": ["GitHub", "GitLab", "Docker Hub", "Kaggle", "HackerNews", "CodeSandbox", "HackTheBox", "Dev.to", "Codeforces", "PyPi"],
    "Social & Messaging": ["Twitter", "threads", "Reddit", "Telegram", "TikTok", "Instagram", "Pinterest", "Linktree", "Facebook", "Mastodon"],
    "Gaming & Entertainment": ["Steam Community (User)", "Twitch", "YouTube", "Spotify", "Roblox", "Discord", "Patreon", "SoundCloud"],
}

BRAND_MAP = {
    "github.com": "GitHub", "gitlab.com": "GitLab", "hub.docker.com": "Docker Hub",
    "kaggle.com": "Kaggle", "news.ycombinator.com": "HackerNews", "codesandbox.io": "CodeSandbox",
    "hackthebox.com": "HackTheBox", "medium.com": "Medium", "twitter.com": "Twitter/X",
    "x.com": "Twitter/X", "threads.net": "Threads", "reddit.com": "Reddit",
    "t.me": "Telegram", "tiktok.com": "TikTok", "instagram.com": "Instagram",
    "pinterest.com": "Pinterest", "linktr.ee": "Linktree", "steamcommunity.com": "Steam",
    "twitch.tv": "Twitch", "youtube.com": "YouTube", "open.spotify.com": "Spotify",
    "spotify.com": "Spotify", "roblox.com": "Roblox", "patreon.com": "Patreon"
}

try:
    from pythainlp.transliterate import romanize as pythai_romanize
except ImportError:
    pythai_romanize = None

# Comprehensive Colloquial Thai Nickname & Loanword Lexicon
THAI_COLLOQUIAL_MAP = {
    # Food & Dessert
    "โดนัท": ["donut", "donuts"], "โดนัทท์": ["donut"], "แพนเค้ก": ["pancake"], "เค้ก": ["cake"],
    "คุ้กกี้": ["cookie"], "คุกกี้": ["cookie"], "โมจิ": ["moji"], "ข้าวปั้น": ["khaopan"],
    "ข้าวตัง": ["khaotang"], "ข้าวกล้อง": ["khaoklong"], "มะนาว": ["manao", "lime"],
    "ส้ม": ["som", "orange"], "แอปเปิ้ล": ["apple"], "เชอรี่": ["cherry"], "องุ่น": ["angoon", "grape"],
    "แตงโม": ["tangmo"], "ชมพู่": ["chompoo"], "ขนุน": ["khanun"], "ปุยฝ้าย": ["puifai"],
    # English Loanwords & Objects
    "ดรีม": ["dream"], "พัตเตอร์": ["putter"], "กอล์ฟ": ["golf"], "บอล": ["ball"],
    "ไอซ์": ["ice"], "แบงค์": ["bank"], "บอส": ["boss"], "เบียร์": ["beer"],
    "เบส": ["best"], "เบสท์": ["best"], "บิ๊ก": ["big"], "บูม": ["boom"],
    "โบว์": ["bow"], "กาย": ["guy"], "แชมป์": ["champ"], "ดอลลาร์": ["dollar"],
    "เอิร์ธ": ["earth"], "ฟิล์ม": ["film"], "ฟิวส์": ["fuse"], "ฟลุ๊ค": ["fluke"],
    "ฟลุค": ["fluke"], "เจล": ["gel"], "เกรซ": ["grace"], "แจ็ค": ["jack"],
    "เจมส์": ["james"], "เจ": ["jay"], "จีน": ["jean", "jeen"], "จูน": ["june"],
    "จัสติน": ["justin"], "ลีโอ": ["leo"], "ไมค์": ["mike"], "แมน": ["man"],
    "มาร์ช": ["march"], "มาร์ค": ["mark"], "มาร์ก": ["mark"], "แม็กซ์": ["max"],
    "แมกซ์": ["max"], "มินนี่": ["minnie"], "มิกกี้": ["mickey"], "มิ้น": ["mint"],
    "มิ้นท์": ["mint"], "นิว": ["new"], "นิก": ["nick"], "นิค": ["nick"],
    "ออฟ": ["off"], "ออย": ["oil"], "พีท": ["pete"], "พรีม": ["preme", "preem"],
    "แซม": ["sam"], "เท็น": ["ten"], "ไทเกอร์": ["tiger"], "ทอม": ["tom"],
    "ท็อป": ["top"], "วินเนอร์": ["winner"], "ชาลี": ["charlie"], "อลิส": ["alice"],
    "บิลลี่": ["billy"],
    # Popular Thai Nicknames (Multi-variant Romanization)
    "นัท": ["nat", "nut"], "ณัฐ": ["nat", "nut"], "มายด์": ["mild", "mind"],
    "มาย": ["mai", "mild"], "พลอย": ["ploy"], "ฟ้า": ["fah"], "นนท์": ["non", "nont"],
    "นน": ["non"], "เบนซ์": ["benz"], "เนย": ["noey", "butter"], "พิม": ["pim"],
    "พิมพ์": ["pim"], "น้ำ": ["nam"], "เต้ย": ["toey"], "นุ่น": ["noon"],
    "แป้ง": ["pang"], "แพรว": ["praew"], "แพร": ["prae"], "แพรวา": ["praewa"],
    "ใบเฟิร์น": ["baifern"], "เฟิร์น": ["fern"], "วิว": ["view"], "บิว": ["view", "biw"],
    "อาย": ["eye"], "ตาล": ["tarn", "tan"], "ตูน": ["toon"], "อาร์ม": ["arm"],
    "แอม": ["aum", "am"], "อั้ม": ["aum"], "ปาย": ["pai"], "ปอย": ["poy"],
    "หวาน": ["warn", "wan"], "ฝน": ["fon"], "จ๋า": ["ja"], "จ๊ะจ๋า": ["jaja"],
    "แนน": ["nan"], "ต้น": ["ton"], "ปอนด์": ["pond"], "มุก": ["mook"],
    "วิน": ["win"], "เต้": ["tae"], "เติ้ล": ["title"], "กันต์": ["gun", "kant"],
    "กัน": ["gun"], "อาร์ต": ["art"], "บาส": ["bas"], "เก้า": ["kao"],
    "ปอ": ["por"], "ป่าน": ["parn"], "แก้ม": ["gam", "kaem"], "เบลล์": ["bell"],
    "ดิว": ["dew"], "ตอง": ["tong"], "พราว": ["proud", "prao"], "เพชร": ["petch", "diamond"],
    "ยุ้ย": ["yui"], "โย": ["yo"], "ริน": ["rin"], "ว่าน": ["wan"],
    "อ้อม": ["aom"], "แอน": ["ann"], "ภูมิ": ["poom", "phum", "bhoom"],
    "ภัทร": ["pat", "phat"], "กานต์": ["karn", "kan"], "ก้อง": ["kong"],
    "เป้": ["pae", "pe"], "ปิง": ["ping"], "ป๊อป": ["pop"], "โอ๊ต": ["oat"],
    "อาร์ท": ["art"], "แบ๋ม": ["bam"], "จิ๊บ": ["jib"], "ตั๊ก": ["tak"],
    "แดน": ["dan"], "นิกกี้": ["nicky"], "นีน่า": ["nina"], "พล": ["pol", "phon"],
    "เมย์": ["may"], "เม": ["may"], "มด": ["mod"], "นก": ["nok"],
    "ไก่": ["kai"], "เป็ด": ["ped"], "หมู": ["moo"], "อ้น": ["ohn"],
    "เอ้": ["ae"], "อั๋น": ["un"], "นัทตี้": ["nutty"], "โบวี่": ["bowie"],
    "ปราง": ["prang"], "ปิ่น": ["pin"], "ก้อย": ["koy"], "แต้ว": ["taew"],
    "ใหม่": ["mai"], "ณเดชน์": ["nadech"], "ญาญ่า": ["yaya", "urassaya"],
    "เจนนี่": ["jennie"], "ลิซ่า": ["lisa"]
}

def resolve_target_handles(target: str) -> List[str]:
    """
    Quad-Layer Thai-to-English Handle Resolver:
    Layer 1: Non-Thai handle passed directly (e.g. 'johndoe' -> ['johndoe']).
    Layer 2: Strip Thai honorifics (น้อง, พี่, คุณ, ไอ้, อี, หมอ, ช่าง, จ่า, สารวัตร).
    Layer 3: Colloquial Thai & English-loan dictionary matching (returns list of spellings).
    Layer 4: Algorithmic RTGS phonetic transliteration via PyThaiNLP with phonetic suffix extensions.
    """
    clean = target.strip().replace("@", "")
    if not re.search(r'[\u0E00-\u0E7F]', clean):
        return [clean.lower()]

    # Strip Thai honorific prefixes
    stripped = re.sub(r'^(น้อง|พี่|คุณ|ไอ้|อี|หมอ|ช่าง|จ่า|ผู้กอง|สารวัตร)', '', clean).strip()

    candidates: List[str] = []

    # 1. Check Colloquial & Nickname Lexicon
    if stripped in THAI_COLLOQUIAL_MAP:
        candidates.extend(THAI_COLLOQUIAL_MAP[stripped])
    elif clean in THAI_COLLOQUIAL_MAP:
        candidates.extend(THAI_COLLOQUIAL_MAP[clean])

    # 2. Algorithmic RTGS Transliteration fallback (handles ANY Thai word/name)
    if pythai_romanize:
        try:
            r = pythai_romanize(stripped, engine='royin').lower()
            if r and r not in candidates:
                candidates.append(r)
            # Handle common Thai suffix spelling patterns
            if r.endswith('phon'):
                candidates.append(r[:-4] + 'pol')
            elif r.endswith('thon'):
                candidates.append(r[:-4] + 'thorn')
            elif r.endswith('chat'):
                candidates.append(r[:-4] + 'chart')
            elif r.endswith('sak'):
                candidates.append(r[:-3] + 'sakdi')
        except Exception as e:
            logger.debug(f"[OSINT-RESOLVER] PyThaiNLP romanization note: {e}")

    # Fallback to stripped original if nothing else
    return list(dict.fromkeys(candidates)) if candidates else [clean.lower()]

def normalize_target_entity(target: str) -> str:
    """
    Returns the primary canonical handle for a target.
    """
    handles = resolve_target_handles(target)
    return handles[0] if handles else target.strip().lower().replace("@", "")

def generate_handle_permutations(base_name: str, depth: str = "sweep") -> List[str]:
    """
    [ADVANCED HEURISTIC HANDLE PERMUTATION MATRIX]
    Generates high-probability handle permutations across Thai & international naming habits:
    1. Base canonical spellings & double symbols (_donut, donut_, __donut__, donut.)
    2. Thai & Regional identifiers (_th, .th, th, th_)
    3. Social & Aesthetic prefixes (iam, its, the, just, hey, hi, real, callme, oh)
    4. Aesthetic & Content suffixes (.official, _official, .diary, _diary, .jpg, .space, _studio, _vibes, _ch, channel)
    5. Aesthetic character elongation (donutt, donuttt, noeyy)
    6. Leetspeak & Slang conversions (o -> 0, s -> z, etc.)
    7. Birth Years & Numeric Anchors (00-06, 98-99, 2000-2004, 888, 999, 123)
    8. Gamer & Tag variations (x_..., ..._x, x_..._x)
    """
    candidates = resolve_target_handles(base_name)
    variations = []

    for cand in candidates:
        cand_clean = cand.strip().lower()
        if not cand_clean:
            continue

        # 1. Base & Direct Symbol Patterns
        variations.extend([
            cand_clean,
            f"{cand_clean}_",
            f"_{cand_clean}",
            f"{cand_clean}__",
            f"__{cand_clean}__",
            f"{cand_clean}.",
            f"_{cand_clean}_",
        ])

        # 2. Thai & Regional Identifiers
        variations.extend([
            f"{cand_clean}_th",
            f"{cand_clean}.th",
            f"{cand_clean}th",
            f"th_{cand_clean}",
        ])

        # 3. Social & Aesthetic Prefixes
        variations.extend([
            f"iam{cand_clean}",
            f"its{cand_clean}",
            f"the{cand_clean}",
            f"just{cand_clean}",
            f"hey{cand_clean}",
            f"hi{cand_clean}",
            f"real_{cand_clean}",
            f"callme_{cand_clean}",
            f"oh_{cand_clean}",
        ])

        # 4. Social & Content Suffixes
        variations.extend([
            f"{cand_clean}.official",
            f"{cand_clean}_official",
            f"{cand_clean}.diary",
            f"{cand_clean}_diary",
            f"{cand_clean}.jpg",
            f"{cand_clean}.space",
            f"{cand_clean}_studio",
            f"{cand_clean}_vibes",
            f"{cand_clean}_ch",
            f"{cand_clean}channel",
        ])

        # 5. Aesthetic Letter Elongation (e.g. donutt, donuttt, noeyy)
        last_char = cand_clean[-1]
        if last_char.isalpha():
            variations.append(f"{cand_clean}{last_char}")
            variations.append(f"{cand_clean}{last_char}{last_char}")
            variations.append(f"{cand_clean}{last_char}_")

        # 6. Leetspeak & Slang replacements
        if "s" in cand_clean:
            variations.append(cand_clean.replace("s", "z"))
        if cand_clean.endswith("t") or cand_clean.endswith("s"):
            variations.append(f"{cand_clean}z")
        if "o" in cand_clean:
            variations.append(cand_clean.replace("o", "0"))
        if "i" in cand_clean:
            variations.append(cand_clean.replace("i", "1"))

        # 7. Year & Numeric Anchors (Gen-Z / 90s Birth Years + Lucky digits)
        years = ["00", "01", "02", "03", "04", "05", "98", "99", "2000", "2002", "2004"]
        for yr in years:
            variations.append(f"{cand_clean}{yr}")
            variations.append(f"{cand_clean}_{yr}")

        # Lucky & standard numeric suffixes
        variations.extend([
            f"{cand_clean}123",
            f"{cand_clean}01",
            f"{cand_clean}888",
            f"{cand_clean}999",
            f"{cand_clean}69",
        ])

        # 8. Gamer & Tag variations
        variations.extend([
            f"x_{cand_clean}",
            f"{cand_clean}_x",
            f"x_{cand_clean}_x",
            f"xx_{cand_clean}_xx",
        ])

    deduped = list(dict.fromkeys(variations))
    if depth == "quick":
        return deduped[:16]
    elif depth == "sweep":
        return deduped[:32]
    return deduped

def probe_instagram_handles(handles: List[str]) -> List[Dict[str, str]]:
    """
    Direct ultra-reliable Instagram profile probe.
    Bypasses broken third-party proxies (like imginn) by using social crawler headers.
    """
    results = []
    headers = {'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'}

    def _check(h):
        clean_h = h.strip().replace("@", "")
        if not clean_h:
            return None
        try:
            r = requests.get(f"https://www.instagram.com/{clean_h}/", headers=headers, timeout=3.5)
            if 'property="og:title"' in r.text:
                title = re.search(r'<title>([^<]+)</title>', r.text)
                t_str = title.group(1).replace("&#064;", "@") if title else ""
                clean_name = t_str.split("•")[0].strip() if "•" in t_str else t_str.strip()
                return {
                    "handle": f"@{clean_h}",
                    "name": clean_name or f"@{clean_h}",
                    "url": f"https://www.instagram.com/{clean_h}/"
                }
        except Exception:
            pass
        return None

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=16) as ex:
        for it in ex.map(_check, handles):
            if it:
                results.append(it)
    return results

def run_multi_account_sweep(target_name: str, timeout: int = 5) -> Dict[str, Any]:
    """
    [MULTI-ACCOUNT ENTITY DISCOVERY]
    Find multiple matching accounts across all major social networks for a target person/handle.
    e.g. TikTok (8 accounts), IG (10 accounts), GitHub (6 accounts)...
    """
    clean_target = normalize_target_entity(target_name)
    if not clean_target:
        return {"status": "error", "message": "Invalid or empty target provided."}

    logger.info(f"[OSINT-SWEEP] Starting Multi-Account Sweep for entity: '{clean_target}'")
    start_time = time.time()
    results_by_platform: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    seen_urls = set()

    # 1. Query GitHub Users API for multiple accounts matching the keyword
    try:
        gh_url = f"https://api.github.com/search/users?q={clean_target}&per_page=8"
        gh_res = requests.get(gh_url, headers={"User-Agent": "JARVIS-OSINT"}, timeout=4)
        if gh_res.status_code == 200:
            for u in gh_res.json().get("items", []):
                u_url = u.get("html_url")
                if u_url and u_url not in seen_urls:
                    seen_urls.add(u_url)
                    results_by_platform["GitHub"].append({
                        "handle": f"@{u.get('login')}",
                        "url": u_url
                    })
    except Exception as e:
        logger.debug(f"[OSINT-SWEEP] GitHub API error: {e}")

    perms = generate_handle_permutations(target_name, depth="sweep")

    # 2. Instagram Direct Probe (bypasses broken imginn 403 issue)
    try:
        ig_accounts = probe_instagram_handles(perms)
        for ig in ig_accounts:
            if ig["url"] not in seen_urls:
                seen_urls.add(ig["url"])
                results_by_platform["Instagram"].append({
                    "handle": ig["handle"],
                    "url": ig["url"]
                })
    except Exception as e:
        logger.debug(f"[OSINT-SWEEP] Instagram probe error: {e}")
    python_exe = _get_sherlock_python()
    sherlock_perms = perms[:16]
    cmd = [python_exe, "-m", "sherlock_project"] + sherlock_perms + ["--timeout", str(timeout), "--print-found", "--no-color"]
    
    # Priority social platforms for multi-account scan
    sweep_sites = [
        "Instagram", "TikTok", "Twitter", "threads", "Telegram", "Reddit",
        "Steam Community (User)", "Twitch", "YouTube", "Spotify", "Pinterest", "Linktree"
    ]
    for site in sweep_sites:
        cmd.extend(["--site", site])

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=40
        )
        if proc.stdout:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line.startswith("[+]"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        raw_site = parts[0].replace("[+]", "").strip()
                        url = parts[1].strip()
                        if not url.startswith("http") or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        
                        # Normalize platform name
                        norm_platform = raw_site.replace(" Community (User)", "")
                        for b_dom, b_brand in BRAND_MAP.items():
                            if b_dom in url:
                                norm_platform = b_brand
                                break

                        # Extract clean handle from URL
                        handle = url.rstrip("/").split("/")[-1]
                        if not handle.startswith("@"):
                            handle = "@" + handle

                        results_by_platform[norm_platform].append({
                            "handle": handle,
                            "url": url
                        })
    except Exception as e:
        logger.error(f"[OSINT-SWEEP] Sherlock sweep error: {e}")

    elapsed_sec = round(time.time() - start_time, 2)
    total_found = sum(len(accs) for accs in results_by_platform.values())

    # Generate Markdown Dossier
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(REPORTS_DIR, f"dossier_{clean_target}_multi_{timestamp_str}.md")
    _write_multi_account_markdown(clean_target, elapsed_sec, results_by_platform, total_found, md_path)

    # Format output summary
    summary_text = _format_multi_account_summary(clean_target, elapsed_sec, results_by_platform, total_found, md_path)

    return {
        "status": "success",
        "target": clean_target,
        "mode": "multi",
        "elapsed_seconds": elapsed_sec,
        "total_found": total_found,
        "platforms_count": len(results_by_platform),
        "results_by_platform": dict(results_by_platform),
        "report_file": md_path,
        "summary": summary_text
    }

def _write_multi_account_markdown(target: str, elapsed: float, results: Dict[str, List[Dict[str, str]]], total: int, path: str) -> None:
    """Generate Markdown report for multi-account sweep."""
    lines = [
        f"# 🎯 J.A.R.V.I.S. MULTI-ACCOUNT OSINT DOSSIER: '{target}'",
        f"**Security Clearance:** NACHAPOL CLASSIFIED LEVEL-4",
        f"**Discovery Mode:** MULTI-ACCOUNT ENTITY SWEEP | **Execution Time:** {elapsed}s | **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Identities Discovered:** {total} Accounts across {len(results)} Platforms\n",
        "---",
        "## 📡 Accounts Discovered by Platform\n"
    ]

    for platform, accounts in results.items():
        lines.append(f"### 📂 {platform} ({len(accounts)} บัญชี)")
        for a in accounts:
            lines.append(f"- **{a['handle']}:** [{a['url']}]({a['url']})")
        lines.append("")

    if not total:
        lines.append("*ไม่พบบัญชีที่สอดคล้องกับคีย์เวิร์ดนี้ในเครือข่ายที่ตรวจสอบครับ*")

    lines.append("\n---\n*Generated by J.A.R.V.I.S. Tactical OSINT System (Nachapol Industries)*")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        logger.error(f"[OSINT-SWEEP] Failed writing markdown: {e}")

def _format_multi_account_summary(target: str, elapsed: float, results: Dict[str, List[Dict[str, str]]], total: int, report_path: str) -> str:
    """Format human & LINE-friendly summary grouped by platform."""
    if not total:
        return f"🎯 ผลการสืบค้นแบบ Multi-Account สำหรับเป้าหมาย **'{target}'**:\nไม่พบบัญชีที่สอดคล้องกันบนแพลตฟอร์มหลักครับ (ใช้เวลา {elapsed}s)"

    msg_lines = [
        f"🎯 [MULTI-ACCOUNT OSINT REPORT] เป้าหมาย: '{target}'",
        f"⏱️ เวลาที่ใช้: {elapsed} วินาที | พบบัญชีทั้งหมด: {total} บัญชี ใน {len(results)} แพลตฟอร์ม",
        "─────────────────────────"
    ]

    for platform, accounts in results.items():
        msg_lines.append(f"📂 {platform} ({len(accounts)} บัญชี):")
        for a in accounts[:4]:
            msg_lines.append(f" • {a['handle']}: {a['url']}")
        if len(accounts) > 4:
            msg_lines.append(f"   (และอีก {len(accounts) - 4} บัญชี...)")

    msg_lines.append("─────────────────────────")
    msg_lines.append(f"📄 บันทึกแฟ้มฉบับเต็มไว้ที่: reports/osint/{os.path.basename(report_path)}")
    return "\n".join(msg_lines)

def run_sherlock_scan(username: str, mode: str = "multi", timeout: int = 8) -> Dict[str, Any]:
    """
    Unified entry point for Sherlock & OSINT Reconnaissance.
    
    Args:
        username (str): The target username or keyword.
        mode (str): 'multi' (Sweep multiple accounts per platform),
                    'quick' (Exact handle across top 25 platforms),
                    'deep' (Exact handle across all 400+ platforms).
    """
    if mode == "multi":
        return run_multi_account_sweep(target_name=username, timeout=5)

    clean_user = normalize_target_entity(username)
    if not clean_user:
        return {"status": "error", "message": "Invalid or empty username provided."}

    logger.info(f"[OSINT] Starting {mode.upper()} Sherlock scan for target: @{clean_user}")
    
    python_exe = _get_sherlock_python()
    cmd = [python_exe, "-m", "sherlock_project", clean_user, "--no-color", "--print-found", "--timeout", str(timeout)]

    if mode in ("quick", "exact"):
        for site in TOP_SITES:
            cmd.extend(["--site", site])

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"dossier_{clean_user}_{timestamp_str}.txt"
    output_path = os.path.join(REPORTS_DIR, output_filename)
    cmd.extend(["--output", output_path])

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180 if mode == "deep" else 35
        )
        elapsed_sec = round(time.time() - start_time, 2)
    except subprocess.TimeoutExpired:
        logger.warning(f"[OSINT] Sherlock scan timed out for @{clean_user}")
        return {
            "status": "timeout",
            "username": clean_user,
            "message": f"การสืบค้นใช้เวลานานเกินกำหนด ({timeout}s)",
            "accounts": []
        }
    except Exception as e:
        logger.error(f"[OSINT] Execution failed: {e}")
        return {"status": "error", "message": f"เกิดข้อผิดพลาดในการรัน Sherlock: {str(e)}"}

    found_accounts = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("http://") or line.startswith("https://"):
                        found_accounts.append(line)
        except Exception:
            pass

    if not found_accounts and proc.stdout:
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("[+]"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    url_candidate = parts[1].strip()
                    if url_candidate.startswith("http"):
                        found_accounts.append(url_candidate)

    # Direct Instagram probe fallback (bypasses Sherlock's broken imginn 403 probe)
    try:
        ig_single = probe_instagram_handles([clean_user])
        for ig in ig_single:
            if ig["url"] not in found_accounts:
                found_accounts.append(ig["url"])
    except Exception:
        pass

    unique_urls = list(dict.fromkeys(found_accounts))

    categorized: Dict[str, List[Dict[str, str]]] = {
        "Developer & Code": [],
        "Social & Messaging": [],
        "Gaming & Entertainment": [],
        "Web & Community": []
    }

    for url in unique_urls:
        matched_cat = "Web & Community"
        domain = url.split("/")[2].lower().replace("www.", "")
        site_name = BRAND_MAP.get(domain)
        if not site_name:
            for b_domain, b_name in BRAND_MAP.items():
                if b_domain in domain:
                    site_name = b_brand
                    break
        if not site_name:
            site_name = domain.split(".")[0].capitalize()

        for cat, sites in CATEGORY_MAPPING.items():
            if any(s.lower() in site_name.lower() or s.lower() in url.lower() for s in sites):
                matched_cat = cat
                break
        categorized[matched_cat].append({
            "site": site_name,
            "url": url
        })

    md_dossier_path = os.path.join(REPORTS_DIR, f"dossier_{clean_user}_{timestamp_str}.md")
    _write_markdown_dossier(clean_user, mode, elapsed_sec, unique_urls, categorized, md_dossier_path)
    summary_text = _format_dossier_summary(clean_user, mode, elapsed_sec, unique_urls, categorized, md_dossier_path)

    return {
        "status": "success",
        "username": clean_user,
        "mode": mode,
        "elapsed_seconds": elapsed_sec,
        "total_found": len(unique_urls),
        "categorized": categorized,
        "accounts": unique_urls,
        "report_file": md_dossier_path,
        "summary": summary_text
    }

def _write_markdown_dossier(username: str, mode: str, elapsed: float, urls: List[str], categorized: Dict[str, List[Dict[str, str]]], path: str) -> None:
    lines = [
        f"# 🎯 J.A.R.V.I.S. TACTICAL OSINT DOSSIER: @{username}",
        f"**Security Clearance:** NACHAPOL CLASSIFIED LEVEL-4",
        f"**Scan Mode:** {mode.upper()} SCAN | **Execution Time:** {elapsed}s | **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Identities Discovered:** {len(urls)} Profiles\n",
        "---",
        "## 📡 Discovered Digital Footprints\n"
    ]
    for cat_name, items in categorized.items():
        if items:
            lines.append(f"### 📂 {cat_name} ({len(items)})")
            for item in items:
                lines.append(f"- **{item['site']}:** [{item['url']}]({item['url']})")
            lines.append("")
    if not urls:
        lines.append("*ไม่พบบัญชีที่ตรงกับชื่อผู้ใช้นี้ในฐานข้อมูลของโหมดนี้ครับ*")
    lines.append("\n---\n*Generated by J.A.R.V.I.S. Tactical OSINT System (Nachapol Industries)*")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        logger.error(f"[OSINT] Failed to save markdown dossier: {e}")

def _format_dossier_summary(username: str, mode: str, elapsed: float, urls: List[str], categorized: Dict[str, List[Dict[str, str]]], report_path: str) -> str:
    if not urls:
        return f"🎯 ผลการสืบค้น OSINT สำหรับเป้าหมาย **@{username}**:\nไม่พบบัญชีโซเชียลที่ตรงกันใน {mode.upper()} Scan ครับเจ้านาย (ใช้เวลา {elapsed}s)"

    msg_lines = [
        f"🎯 [TACTICAL OSINT REPORT] เป้าหมาย: @{username}",
        f"⏱️ เวลาที่ใช้: {elapsed} วินาที | พบบัญชีทั้งหมด: {len(urls)} รายการ",
        "─────────────────────────"
    ]
    for cat_name, items in categorized.items():
        if items:
            msg_lines.append(f"📂 {cat_name}:")
            for it in items[:4]:
                msg_lines.append(f" • {it['site']}: {it['url']}")
            if len(items) > 4:
                msg_lines.append(f"   (และอีก {len(items) - 4} บัญชี...)")
    msg_lines.append("─────────────────────────")
    msg_lines.append(f"📄 บันทึกแฟ้มประวัติฉบับเต็มไว้ที่: reports/osint/{os.path.basename(report_path)}")
    return "\n".join(msg_lines)
