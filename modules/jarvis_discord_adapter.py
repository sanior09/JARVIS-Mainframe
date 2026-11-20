"""
Module: modules/jarvis_discord_adapter.py
Author: J.A.R.V.I.S. Systems Engineering
Description:
  Modular Discord Bot Adapter (Gateway v10 + REST API v10) for J.A.R.V.I.S.
  - Zero extra pip dependencies (uses `websockets` + `requests` already in C:\\JARVIS\\venv)
  - Implements J.A.R.V.I.S. Lifecycle Protocol (initialize, execute_intent, get_telemetry, shutdown)
  - Concurrency-safe: dedicated daemon thread + ThreadPoolExecutor + Event teardown + Lock telemetry
  - Auto-fallback from privileged MESSAGE_CONTENT intent (close code 4014) to basic mention/DM intents
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import requests

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

try:
    from jarvis_text_utils import normalize_thai_text
except (ImportError, ModuleNotFoundError):
    try:
        from modules.jarvis_text_utils import normalize_thai_text
    except (ImportError, ModuleNotFoundError):
        def normalize_thai_text(text: str, preserve_newlines: bool = False) -> str:
            if not text:
                return ""
            text = text.replace("เเ", "แ").replace("ะา", "ำ").replace("ํา", "ำ").replace("ํ้า", "้ำ")
            text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
            text = re.sub(r"([่้๊๋ิีึืุูัํ])\1+", r"\1", text)
            if preserve_newlines:
                return re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()
            return text

logger = logging.getLogger("JARVIS.DiscordAdapter")

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
DISCORD_USER_AGENT = "DiscordBot (https://nachapol.industries/jarvis, 1.0)"

# Discord Gateway Intents bitmasks
INTENT_GUILDS = 1 << 0
INTENT_GUILD_MEMBERS = 1 << 1
INTENT_GUILD_MESSAGES = 1 << 9
INTENT_DIRECT_MESSAGES = 1 << 12
INTENT_MESSAGE_CONTENT = 1 << 15

INTENTS_FULL = (
    INTENT_GUILDS
    | INTENT_GUILD_MEMBERS
    | INTENT_GUILD_MESSAGES
    | INTENT_DIRECT_MESSAGES
    | INTENT_MESSAGE_CONTENT
)  # 37379
INTENTS_BASIC = INTENT_GUILDS | INTENT_GUILD_MESSAGES | INTENT_DIRECT_MESSAGES  # 4609

# Fallback .env path shared with the Antigravity Discord plugin
ANTIGRAVITY_DISCORD_ENV = Path.home() / ".gemini" / "config" / "plugins" / "discord" / ".env"

LEVEL_COLORS = {
    "info": 0x38BDF8,      # Electric Cyan
    "success": 0x34D399,   # Emerald
    "warning": 0xFBBF24,   # Amber
    "error": 0xF43F5E,     # Rose Red
}


def load_discord_token(explicit_token: Optional[str] = None) -> str:
    """
    Loads DISCORD_TOKEN from:
      1. Explicit parameter
      2. Environment variable DISCORD_TOKEN (loaded from C:\\JARVIS\\.env)
      3. Fallback Antigravity Discord plugin .env
    Never logs or reveals the token value.
    """
    candidates = [explicit_token, os.getenv("DISCORD_TOKEN")]

    if ANTIGRAVITY_DISCORD_ENV.exists():
        try:
            for raw_line in ANTIGRAVITY_DISCORD_ENV.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                if key.strip() == "DISCORD_TOKEN":
                    candidates.append(val.strip().strip('"').strip("'"))
                    break
        except Exception as exc:
            logger.debug(f"[DISCORD] Could not read fallback plugin .env: {exc}")

    for cand in candidates:
        if not cand:
            continue
        token = cand.strip().strip('"').strip("'")
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        if token and token != "YOUR_DISCORD_BOT_TOKEN_HERE":
            return token

    return ""


def format_reply_for_discord(text: str) -> str:
    """
    Sanitizes J.A.R.V.I.S. AI responses for Discord while preserving Discord Markdown
    (bold, italic, code blocks, lists).
    """
    if not text:
        return "ดำเนินการเรียบร้อยครับเจ้านาย"

    s = text

    if "[SILENT_EXECUTION]" in s:
        s = s.replace("[SILENT_EXECUTION]", "").strip()
        if not s:
            return "ดำเนินการเรียบร้อยแล้วครับเจ้านาย"

    # Strip internal HUD / system directive tags
    s = re.sub(r"\[WINDOW:[^\]]*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\[END_WINDOW\]", "", s, flags=re.IGNORECASE)
    s = re.sub(
        r"\[(?:ANTICIPATORY|DEEP THOUGHT|INTERNAL|PROTOCOL|SENTINEL|SYSTEM|VOICE MODE|LINE [A-Z]+|TASK QUEUE|IMAGE CACHE)[^\]]*\]",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\[[A-Z0-9_\s]{5,}\]", "", s)

    # Strip HTML tags while keeping line breaks
    s = re.sub(r"<img[^>]*>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</?(?:div|span|p|hr)[^>]*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)

    # Clean zero-width artifacts and normalize Thai typography while keeping line breaks
    s = s.replace("\xa0", " ")
    s = normalize_thai_text(s, preserve_newlines=True)

    # Restore clean line breaks before inline Markdown headings (outside fenced code blocks)
    parts = re.split(r"(```[\s\S]*?```)", s)
    for idx in range(0, len(parts), 2):
        parts[idx] = re.sub(r"([^\n])[ \t]+(#{1,6}[ \t]+)", r"\1\n\n\2", parts[idx])
    s = "".join(parts)

    s = re.sub(r"\n{3,}", "\n\n", s).strip()

    return s or "ดำเนินการเรียบร้อยแล้วครับเจ้านาย"


def split_discord_message(text: str, max_len: int = 1950) -> List[str]:
    """Splits text safely into Discord-sized chunks (<= 2000 chars per message)."""
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_len:
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 3:
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at < max_len // 3:
            split_at = max_len
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _parse_id_set(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


class JarvisDiscordAdapter:
    """
    Encapsulated Discord Gateway + REST subsystem for J.A.R.V.I.S.
    Follows the J.A.R.V.I.S. Modular Subsystem Lifecycle Protocol.
    """

    def __init__(
        self,
        core_ref: Optional[Any] = None,
        chat_handler: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        token: Optional[str] = None,
        command_prefix: str = "!jarvis",
        max_workers: int = 2,
    ):
        self.core = core_ref
        self._chat_handler = chat_handler
        self._explicit_token = token
        self._token = ""
        self._command_prefix = command_prefix.lower()
        self._allowed_channels: Set[str] = set()
        self._owner_ids: Set[str] = set()
        self._notify_channel_id: str = ""
        self._auto_role_id: str = ""
        self._welcome_channel_id: str = ""
        self._clear_toast_delay: float = 4.0

        self.is_active = False
        self._connected = False
        self._bot_user_id: Optional[str] = None
        self._bot_username: Optional[str] = None
        self._intents_mode: str = "full"

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._gateway_thread: Optional[threading.Thread] = None
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="jarvis_discord_worker")

        self._metrics: Dict[str, Any] = {
            "messages_received": 0,
            "messages_replied": 0,
            "notifications_sent": 0,
            "auto_roles_assigned": 0,
            "errors": 0,
            "reconnects": 0,
            "last_heartbeat_ts": 0.0,
        }

    # ==================== LIFECYCLE PROTOCOL ====================

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initializes credentials, validates bot identity, and starts Gateway thread."""
        cfg = config or {}
        try:
            self._token = load_discord_token(cfg.get("token") or self._explicit_token)
            if not self._token:
                logger.warning("[DISCORD] DISCORD_TOKEN not configured; adapter remains inactive.")
                self.is_active = False
                return False

            self._allowed_channels = _parse_id_set(
                cfg["allowed_channels"] if "allowed_channels" in cfg else os.getenv("DISCORD_ALLOWED_CHANNELS", "")
            )
            self._owner_ids = _parse_id_set(
                cfg["owner_ids"] if "owner_ids" in cfg else os.getenv("DISCORD_OWNER_USER_ID", "")
            )
            self._notify_channel_id = (
                cfg["notify_channel_id"] if "notify_channel_id" in cfg else os.getenv("DISCORD_NOTIFY_CHANNEL_ID", "")
            ).strip()
            self._auto_role_id = (
                cfg["auto_role_id"] if "auto_role_id" in cfg else os.getenv("DISCORD_AUTO_ROLE_ID", "")
            ).strip()
            self._welcome_channel_id = (
                cfg["welcome_channel_id"] if "welcome_channel_id" in cfg else os.getenv("DISCORD_WELCOME_CHANNEL_ID", "")
            ).strip()

            if not cfg.get("skip_verify", False):
                me = self._rest_request("GET", "/users/@me")
                if not me or not me.get("id"):
                    logger.error("[DISCORD] Failed to verify bot identity via /users/@me.")
                    self.is_active = False
                    return False
                with self._lock:
                    self._bot_user_id = str(me["id"])
                    self._bot_username = str(me.get("username", "J.A.R.V.I.S."))

            self.is_active = True
            self._stop_event.clear()

            if cfg.get("start_gateway", True):
                if websockets is None:
                    logger.warning("[DISCORD] `websockets` not available; REST-only mode active.")
                else:
                    self._gateway_thread = threading.Thread(
                        target=self._gateway_thread_main,
                        daemon=True,
                        name="JARVIS-Discord-Gateway",
                    )
                    self._gateway_thread.start()

            logger.info(
                f"[DISCORD] Initialized successfully as '{self._bot_username or 'Bot'}' "
                f"(Gateway={'ON' if self._gateway_thread else 'REST-ONLY'})."
            )
            return True
        except Exception as exc:
            logger.error(f"[DISCORD] Initialization error: {exc}", exc_info=True)
            self.is_active = False
            return False

    def execute_intent(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handles dispatched actions from ai_router, voice commands, or agent_office."""
        if not self.is_active:
            return {"status": "error", "message": "Discord adapter is inactive"}

        action = (intent or "").lower().strip()
        try:
            if action == "send_message":
                channel_id = str(params.get("channel_id") or self._notify_channel_id)
                content = str(params.get("content") or "")
                if not channel_id or not content:
                    return {"status": "error", "message": "channel_id and content are required"}
                res = self.send_message(channel_id, content, reply_to_message_id=params.get("reply_to"))
                return {"status": "success" if res else "error", "result": res}

            if action == "send_embed":
                channel_id = str(params.get("channel_id") or self._notify_channel_id)
                if not channel_id:
                    return {"status": "error", "message": "channel_id is required"}
                res = self.send_embed(
                    channel_id=channel_id,
                    title=str(params.get("title", "J.A.R.V.I.S.")),
                    description=str(params.get("description", "")),
                    color=int(params.get("color", LEVEL_COLORS["info"])),
                    fields=params.get("fields"),
                )
                return {"status": "success" if res else "error", "result": res}

            if action == "notify":
                ok = self.send_notification(
                    message=str(params.get("message", "")),
                    title=str(params.get("title", "J.A.R.V.I.S. Notification")),
                    level=str(params.get("level", "info")),
                    channel_id=params.get("channel_id"),
                )
                return {"status": "success" if ok else "error"}

            if action == "status":
                return {"status": "success", "result": self.get_telemetry()}

            if action == "clear_channel":
                channel_id = str(params.get("channel_id") or "")
                if not channel_id:
                    return {"status": "error", "message": "channel_id is required"}
                deleted = self.clear_channel_messages(
                    channel_id=channel_id,
                    limit=int(params.get("limit", 100)),
                    keep_welcome_embeds=bool(params.get("keep_welcome_embeds", True)),
                )
                return {"status": "success", "deleted": deleted}

            return {"status": "error", "message": f"Unsupported intent: {intent}"}
        except Exception as exc:
            logger.error(f"[DISCORD] execute_intent({intent}) failed: {exc}", exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns thread-safe status snapshot for HUD / Web dashboard."""
        with self._lock:
            return {
                "name": "JarvisDiscordAdapter",
                "active": self.is_active,
                "connected": self._connected,
                "bot_username": self._bot_username,
                "bot_user_id": self._bot_user_id,
                "intents_mode": self._intents_mode,
                "metrics": dict(self._metrics),
            }

    def shutdown(self, timeout: float = 5.0) -> None:
        """Signals background Gateway loop to stop and cleans up threads."""
        self.is_active = False
        self._stop_event.set()

        loop = self._async_loop
        if loop and loop.is_running():
            try:
                for task in asyncio.all_tasks(loop):
                    loop.call_soon_threadsafe(task.cancel)
            except Exception:
                pass

        if self._gateway_thread and self._gateway_thread.is_alive():
            self._gateway_thread.join(timeout=timeout)
            if self._gateway_thread.is_alive():
                logger.warning(f"[DISCORD] Gateway thread did not stop within {timeout}s.")

        self._executor.shutdown(wait=False)
        with self._lock:
            self._connected = False
        logger.info("[DISCORD] Shut down cleanly.")

    # ==================== REST API HELPERS ====================

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bot {self._token}",
            "User-Agent": DISCORD_USER_AGENT,
            "Content-Type": "application/json",
        }

    def _rest_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> Optional[Any]:
        if not self._token:
            return None
        url = f"{DISCORD_API_BASE}{endpoint}"
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 204:
                return {"ok": True}
            if 200 <= resp.status_code < 300:
                return resp.json() if resp.content else {"ok": True}
            logger.error(f"[DISCORD REST] HTTP {resp.status_code} on {method} {endpoint}: {resp.text[:200]}")
            with self._lock:
                self._metrics["errors"] += 1
            return None
        except Exception as exc:
            logger.error(f"[DISCORD REST] Request failed ({method} {endpoint}): {exc}")
            with self._lock:
                self._metrics["errors"] += 1
            return None

    def trigger_typing(self, channel_id: str) -> None:
        self._rest_request("POST", f"/channels/{channel_id}/typing", timeout=5.0)

    def send_message(
        self,
        channel_id: str,
        content: str,
        reply_to_message_id: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        formatted = format_reply_for_discord(content) if content else ""
        chunks = split_discord_message(formatted) if formatted else [""]

        last_res: Optional[Dict[str, Any]] = None
        for idx, chunk in enumerate(chunks):
            payload: Dict[str, Any] = {}
            if chunk:
                payload["content"] = chunk
            if idx == 0 and reply_to_message_id:
                payload["message_reference"] = {"message_id": str(reply_to_message_id)}
            if idx == len(chunks) - 1 and embed:
                payload["embeds"] = [embed]
            if not payload:
                continue
            last_res = self._rest_request("POST", f"/channels/{channel_id}/messages", payload=payload)
        return last_res

    def send_embed(
        self,
        channel_id: str,
        title: str,
        description: str,
        color: int = 0x38BDF8,
        fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        embed: Dict[str, Any] = {
            "title": title[:256],
            "description": format_reply_for_discord(description)[:4000],
            "color": color,
            "footer": {"text": "J.A.R.V.I.S. • Nachapol Industries"},
        }
        if fields:
            embed["fields"] = fields[:25]
        return self._rest_request("POST", f"/channels/{channel_id}/messages", payload={"embeds": [embed]})

    def send_notification(
        self,
        message: str,
        title: str = "J.A.R.V.I.S. Alert",
        level: str = "info",
        channel_id: Optional[str] = None,
    ) -> bool:
        target = (channel_id or self._notify_channel_id or "").strip()
        if not target:
            logger.debug("[DISCORD] Notification skipped: DISCORD_NOTIFY_CHANNEL_ID not set.")
            return False
        color = LEVEL_COLORS.get(level.lower(), LEVEL_COLORS["info"])
        res = self.send_embed(target, title=title, description=message, color=color)
        if res:
            with self._lock:
                self._metrics["notifications_sent"] += 1
            return True
        return False

    def assign_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Assigns a role to a guild member via Discord REST API v10."""
        res = self._rest_request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")
        return res is not None

    def clear_channel_messages(
        self,
        channel_id: str,
        limit: int = 100,
        keep_welcome_embeds: bool = True,
    ) -> int:
        """
        Deletes recent chat messages in a channel while preserving pinned messages
        and bot Welcome/Command Center Embed cards.
        Uses Discord bulk-delete for messages < 14 days old and single-delete fallback otherwise.
        """
        fetch_limit = max(1, min(int(limit), 100))
        msgs = self._rest_request("GET", f"/channels/{channel_id}/messages?limit={fetch_limit}")
        if not isinstance(msgs, list):
            return 0

        now_sec = time.time()
        fourteen_days_sec = 14 * 86400 - 60
        recent_ids: List[str] = []
        older_ids: List[str] = []

        for m in msgs:
            mid = str(m.get("id") or "")
            if not mid:
                continue
            if m.get("pinned"):
                continue
            if keep_welcome_embeds:
                embeds = m.get("embeds") or []
                is_bot_msg = bool((m.get("author") or {}).get("bot"))
                if is_bot_msg and embeds:
                    continue

            # Determine age from Discord snowflake ID
            is_recent = True
            try:
                created_sec = ((int(mid) >> 22) + 1420070400000) / 1000.0
                if (now_sec - created_sec) >= fourteen_days_sec:
                    is_recent = False
            except (ValueError, TypeError):
                is_recent = True

            if is_recent:
                recent_ids.append(mid)
            else:
                older_ids.append(mid)

        deleted = 0
        if len(recent_ids) >= 2:
            res = self._rest_request(
                "POST",
                f"/channels/{channel_id}/messages/bulk-delete",
                payload={"messages": recent_ids[:100]},
            )
            if res is not None:
                deleted += len(recent_ids[:100])
        elif len(recent_ids) == 1:
            res = self._rest_request("DELETE", f"/channels/{channel_id}/messages/{recent_ids[0]}")
            if res is not None:
                deleted += 1

        for oid in older_ids:
            if self._stop_event.is_set():
                break
            res = self._rest_request("DELETE", f"/channels/{channel_id}/messages/{oid}")
            if res is not None:
                deleted += 1
            self._stop_event.wait(timeout=0.35)

        return deleted

    def _parse_clear_command(self, text: str) -> Optional[int]:
        """Returns message limit (1-100) if text is a !clear / ลบแชท command, else None."""
        cleaned = text.strip().lower()
        m = re.match(r"^(?:!clear|!ลบแชท|!ล้างแชท|ลบแชท|เคลียร์แชท|ล้างแชท)(?:\s+(\d+))?$", cleaned)
        if not m:
            return None
        if m.group(1):
            return max(1, min(int(m.group(1)), 100))
        return 100

    def _process_member_join(self, event_data: Dict[str, Any]) -> None:
        """Automatically assigns DISCORD_AUTO_ROLE_ID to newly joined non-bot members."""
        user = event_data.get("user") or {}
        if user.get("bot"):
            return

        guild_id = str(event_data.get("guild_id") or "")
        user_id = str(user.get("id") or "")
        username = str(user.get("global_name") or user.get("username") or "เพื่อนใหม่")

        if not guild_id or not user_id:
            return

        assigned = False
        if self._auto_role_id:
            assigned = self.assign_role(guild_id, user_id, self._auto_role_id)
            if assigned:
                with self._lock:
                    self._metrics["auto_roles_assigned"] += 1
                logger.info(f"[DISCORD] Auto-assigned role {self._auto_role_id} to new member '{username}' ({user_id}).")
            else:
                logger.warning(f"[DISCORD] Failed to auto-assign role {self._auto_role_id} to '{username}' ({user_id}).")

        if self._welcome_channel_id:
            desc = f"ยินดีต้อนรับคุณ <@{user_id}> เข้าสู่เซิร์ฟเวอร์ครับ!"
            if assigned:
                desc += f"\nระบบได้มอบยศ <@&{self._auto_role_id}> ให้เรียบร้อยแล้วครับ"
            self.send_embed(
                channel_id=self._welcome_channel_id,
                title="👋 ยินดีต้อนรับสมาชิกใหม่",
                description=desc,
                color=0x818CF8,
            )

    # ==================== MESSAGE ROUTING ====================

    def should_respond_to_message(self, msg: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determines whether J.A.R.V.I.S. should respond to an incoming MESSAGE_CREATE payload,
        and returns (should_respond, cleaned_user_text).
        """
        author = msg.get("author") or {}
        if author.get("bot"):
            return False, ""

        author_id = str(author.get("id", ""))
        if self._bot_user_id and author_id == self._bot_user_id:
            return False, ""

        # Optional owner restriction if DISCORD_OWNER_USER_ID is explicitly set
        if self._owner_ids and author_id not in self._owner_ids:
            return False, ""

        content = (msg.get("content") or "").strip()
        if not content:
            return False, ""

        is_dm = msg.get("guild_id") is None
        channel_id = str(msg.get("channel_id", ""))
        in_allowed_channel = channel_id in self._allowed_channels

        mention_hit = False
        if self._bot_user_id:
            mention_pat = rf"<@!?{re.escape(self._bot_user_id)}>"
            if re.search(mention_pat, content):
                mention_hit = True
                content = re.sub(mention_pat, "", content).strip()

        prefix_hit = False
        lower = content.lower()
        for pfx in (self._command_prefix, "jarvis ", "จาร์วิส "):
            if lower.startswith(pfx):
                prefix_hit = True
                content = content[len(pfx):].strip()
                break

        is_clear_cmd = self._parse_clear_command(content) is not None

        if not (is_dm or in_allowed_channel or mention_hit or prefix_hit or is_clear_cmd):
            return False, ""

        if not content:
            return True, "สวัสดีครับ มีอะไรให้ช่วยไหม"

        return True, content

    def _process_incoming_message(self, msg: Dict[str, Any]) -> None:
        """Runs inside ThreadPoolExecutor so LLM latency never blocks Gateway heartbeats."""
        should_reply, clean_text = self.should_respond_to_message(msg)
        if not should_reply:
            return

        channel_id = str(msg.get("channel_id", ""))
        message_id = str(msg.get("id", ""))
        author = msg.get("author") or {}
        meta = {
            "channel": "discord",
            "channel_id": channel_id,
            "guild_id": msg.get("guild_id"),
            "message_id": message_id,
            "author_id": str(author.get("id", "")),
            "author_name": str(author.get("username", "User")),
        }

        with self._lock:
            self._metrics["messages_received"] += 1

        # Built-in !clear command (intercepted before LLM)
        clear_limit = self._parse_clear_command(clean_text)
        if clear_limit is not None:
            try:
                deleted = self.clear_channel_messages(
                    channel_id=channel_id,
                    limit=clear_limit,
                    keep_welcome_embeds=True,
                )
                toast = self.send_message(
                    channel_id,
                    f"🧹 เคลียร์แชทเรียบร้อยแล้วครับเจ้านาย (ลบไป {deleted} ข้อความ • เก็บป้าย Welcome Embed ไว้ให้แล้ว)",
                )
                with self._lock:
                    self._metrics["messages_replied"] += 1
                if toast and toast.get("id") and self._clear_toast_delay > 0:
                    self._stop_event.wait(timeout=self._clear_toast_delay)
                    self._rest_request("DELETE", f"/channels/{channel_id}/messages/{toast['id']}")
            except Exception as exc:
                logger.error(f"[DISCORD] !clear failed in channel {channel_id}: {exc}", exc_info=True)
                with self._lock:
                    self._metrics["errors"] += 1
            return

        try:
            self.trigger_typing(channel_id)
            if self._chat_handler:
                reply_text = self._chat_handler(clean_text, meta)
            else:
                reply_text = f"รับทราบข้อความจากคุณ {meta['author_name']} ครับท่าน: {clean_text}"

            self.send_message(channel_id, reply_text, reply_to_message_id=message_id)
            with self._lock:
                self._metrics["messages_replied"] += 1
        except Exception as exc:
            logger.error(f"[DISCORD] Failed handling message {message_id}: {exc}", exc_info=True)
            with self._lock:
                self._metrics["errors"] += 1
            self.send_message(
                channel_id,
                f"ขออภัยครับท่าน ระบบประมวลผลขัดข้องชั่วคราว: {str(exc)[:180]}",
                reply_to_message_id=message_id,
            )

    # ==================== GATEWAY V10 LOOP ====================

    def _gateway_thread_main(self) -> None:
        """Dedicated background daemon thread hosting the asyncio Gateway loop."""
        logger.info("[DISCORD] Starting Gateway v10 background thread...")
        loop = asyncio.new_event_loop()
        self._async_loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._gateway_reconnect_loop())
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"[DISCORD] Unhandled Gateway loop error: {exc}", exc_info=True)
        finally:
            try:
                loop.close()
            except Exception:
                pass
            self._async_loop = None
            logger.info("[DISCORD] Gateway thread terminated cleanly.")

    async def _gateway_reconnect_loop(self) -> None:
        backoff = 2.0
        use_full_intents = True

        while self.is_active and not self._stop_event.is_set():
            try:
                await self._run_gateway_session(use_full_intents=use_full_intents)
                backoff = 2.0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                # Detect Discord Close Code 4014 (Disallowed Intents) -> downgrade cleanly
                close_code = getattr(exc, "code", None)
                if close_code == 4014 and use_full_intents:
                    logger.warning(
                        "[DISCORD] Privileged MESSAGE_CONTENT intent is not enabled in Discord Developer Portal "
                        "(close 4014). Falling back to basic intents (DMs & @mentions)."
                    )
                    use_full_intents = False
                    with self._lock:
                        self._intents_mode = "basic_fallback"
                    backoff = 2.0
                else:
                    logger.error(f"[DISCORD] Gateway session error: {exc}")
                    with self._lock:
                        self._metrics["errors"] += 1
                        self._metrics["reconnects"] += 1

            with self._lock:
                self._connected = False

            if self._stop_event.is_set() or not self.is_active:
                break

            logger.info(f"[DISCORD] Reconnecting Gateway in {backoff:.1f}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)

    async def _run_gateway_session(self, use_full_intents: bool = True) -> None:
        intents = INTENTS_FULL if use_full_intents else INTENTS_BASIC
        seq: Optional[int] = None
        heartbeat_task: Optional[asyncio.Task] = None

        async with websockets.connect(DISCORD_GATEWAY_URL, max_size=None) as ws:  # type: ignore
            # 1. Receive Hello (OP 10)
            hello_raw = await ws.recv()
            hello = json.loads(hello_raw)
            interval_sec = float(hello["d"]["heartbeat_interval"]) / 1000.0

            async def _heartbeat_loop():
                while not self._stop_event.is_set():
                    await asyncio.sleep(interval_sec)
                    await ws.send(json.dumps({"op": 1, "d": seq}))
                    with self._lock:
                        self._metrics["last_heartbeat_ts"] = time.time()

            heartbeat_task = asyncio.create_task(_heartbeat_loop())

            # 2. Send Identify (OP 2)
            identify_payload = {
                "op": 2,
                "d": {
                    "token": self._token,
                    "intents": intents,
                    "properties": {
                        "os": "windows",
                        "browser": "jarvis_mainframe",
                        "device": "jarvis_mainframe",
                    },
                    "presence": {
                        "status": "online",
                        "activities": [{"name": "J.A.R.V.I.S. Mainframe", "type": 3}],
                        "afk": False,
                    },
                },
            }
            await ws.send(json.dumps(identify_payload))

            try:
                async for raw_msg in ws:
                    if self._stop_event.is_set():
                        break
                    data = json.loads(raw_msg)
                    op = data.get("op")
                    if data.get("s") is not None:
                        seq = data["s"]

                    if op == 0:  # Dispatch
                        event_type = data.get("t")
                        event_data = data.get("d") or {}

                        if event_type == "READY":
                            user = event_data.get("user") or {}
                            with self._lock:
                                self._connected = True
                                self._bot_user_id = str(user.get("id", self._bot_user_id or ""))
                                self._bot_username = str(user.get("username", self._bot_username or "J.A.R.V.I.S."))
                            logger.info(
                                f"[DISCORD] ✅ Gateway READY — Online as '{self._bot_username}' "
                                f"(guilds={len(event_data.get('guilds', []))}, mode={self._intents_mode})"
                            )
                        elif event_type == "MESSAGE_CREATE":
                            self._executor.submit(self._process_incoming_message, event_data)
                        elif event_type == "GUILD_MEMBER_ADD":
                            self._executor.submit(self._process_member_join, event_data)

                    elif op == 1:  # Immediate heartbeat request
                        await ws.send(json.dumps({"op": 1, "d": seq}))
                    elif op == 7:  # Reconnect requested by Discord
                        logger.info("[DISCORD] Gateway requested reconnect (OP 7).")
                        break
                    elif op == 9:  # Invalid session
                        logger.warning("[DISCORD] Invalid Gateway session (OP 9); re-identifying.")
                        await asyncio.sleep(2.0)
                        break
            finally:
                if heartbeat_task:
                    heartbeat_task.cancel()


# Module-level singleton helper for easy registration
_discord_adapter_instance: Optional[JarvisDiscordAdapter] = None


def get_discord_adapter() -> Optional[JarvisDiscordAdapter]:
    return _discord_adapter_instance


def start_discord_adapter(
    chat_handler: Optional[Callable[[str, Dict[str, Any]], str]] = None,
    core_ref: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[JarvisDiscordAdapter]:
    """Creates, initializes, and registers the singleton JarvisDiscordAdapter."""
    global _discord_adapter_instance
    if _discord_adapter_instance and _discord_adapter_instance.is_active:
        return _discord_adapter_instance

    adapter = JarvisDiscordAdapter(core_ref=core_ref, chat_handler=chat_handler)
    if adapter.initialize(config=config):
        _discord_adapter_instance = adapter
        return adapter
    return None
