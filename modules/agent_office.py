"""
Module: modules/agent_office.py
Description: Real-time Multi-Agent AI Office state engine, Meeting Room orchestrator,
             and Flask API Blueprint for the Nachapol Industries 2.5D Pixel AI Office HUD.
"""

from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
import json
import logging
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

logger = logging.getLogger("JARVIS.Subsystems.AgentOffice")

AGENT_ALIASES: Dict[str, str] = {
    "jarvis": "jarvis",
    "code": "friday",
    "friday": "friday",
    "veronica": "veronica",
    "web": "edith",
    "edith": "edith",
    "u": "u",
    "os": "dume",
    "dume": "dume",
    "dum-e": "dume",
    "cli": "jocasta",
    "jocasta": "jocasta",
    "karen": "karen",
}

VALID_STATES = ("IDLE", "MEETING", "THINKING", "CODING", "SEARCHING", "EXECUTING", "ERROR")

SHARED_ROOMS = (
    "intel_lab",     # Web Recon, Research, Planning
    "command_deck",  # Executive Briefing & Synthesis
    "dev_lab",       # Coding, UI/Design, Debug, AI Architecture
    "data_net",      # Memory/ChromaDB, Cyber Defense, Network & Threat Map
    "maker_iot",     # 3D Printers, Sensors, TV/ADB, Electronics, Hardware
    "sys_ops",       # OS Automation, Files, Logs, Backups, Schedules
    "media_qa",      # Camera/Vision, Voice/TTS/Audio, Visual Inspection
    "meeting",       # Central Lounge Sofa & Bistro Table
    "lounge",        # Espresso Bar, Lobby & Free-roam Atrium
)

# Any agent can enter ANY functional room dynamically depending on the task/situation
ROOM_KEYWORDS: Dict[str, tuple] = {
    "dev_lab": (
        "code", "python", "js", "html", "css", "react", "ui", "ux", "design",
        "figma", "vercel", "api", "bug", "debug", "refactor", "test", "pytest",
        "โค้ด", "เขียนโปรแกรม", "หน้าเว็บ", "ดีไซน์", "แก้บั๊ก", "สคริปต์",
    ),
    "intel_lab": (
        "search", "web", "recon", "research", "news", "url", "browse", "doc",
        "ค้นหา", "เว็บ", "ข่าว", "วิจัย", "สืบ", "ข้อมูล", "วิเคราะห์ตลาด",
    ),
    "data_net": (
        "chroma", "vector", "memory", "db", "sql", "security", "vuln", "cyber",
        "wifi", "network", "ssh", "scan", "port", "firewall", "ความจำ", "ฐานข้อมูล",
        "ความปลอดภัย", "ช่องโหว่", "เครือข่าย", "สแกน",
    ),
    "maker_iot": (
        "hardware", "iot", "sensor", "arduino", "esp32", "circuit", "pcb", "tv",
        "adb", "3d", "print", "gpu", "temp", "thermal", "robot", "วงจร", "ฮาร์ดแวร์",
        "อุปกรณ์", "เซ็นเซอร์", "ปริ้น", "ทีวี", "อุณหภูมิ",
    ),
    "sys_ops": (
        "os", "windows", "file", "folder", "ram", "cpu", "disk", "process",
        "restart", "backup", "schedule", "cron", "log", "เปิดโปรแกรม", "ไฟล์",
        "แรม", "ซีพียู", "ดิสก์", "ระบบ", "ล้างแคช",
    ),
    "media_qa": (
        "screenshot", "image", "photo", "camera", "voice", "audio", "tts",
        "mic", "speech", "video", "visual", "qa", "รูป", "ภาพ", "เสียง", "กล้อง",
        "หน้าจอ", "ตรวจสอบภาพ",
    ),
    "command_deck": (
        "status", "overview", "plan", "brief", "strategy", "report", "summary",
        "ภาพรวม", "สรุป", "วางแผน", "รายงาน", "สถานะ", "ประสานงาน",
    ),
}

DEFAULT_ROOM_BY_AGENT: Dict[str, str] = {
    "jarvis": "command_deck",
    "friday": "dev_lab",
    "edith": "intel_lab",
    "veronica": "dev_lab",
    "jocasta": "data_net",
    "dume": "maker_iot",
    "u": "media_qa",
    "karen": "sys_ops",
}


def classify_task_room(text: str, agent_id: Optional[str] = None) -> str:
    """Route any agent to the right shared room for the current task/situation."""
    low = (text or "").lower()
    best_room = None
    best_hits = 0
    for room, keywords in ROOM_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in low)
        if hits > best_hits:
            best_hits = hits
            best_room = room
    if best_room:
        return best_room
    return DEFAULT_ROOM_BY_AGENT.get(agent_id or "jarvis", "command_deck")


ROUTE_INTENT_TO_AGENT: Dict[str, str] = {
    "general": "jarvis",
    "research": "edith",
    "os_control": "dume",
    "server_monitor": "veronica",
    "engineering": "friday",
    "creative": "u",
    "home": "karen",
    "cyber": "jocasta",
    "friday": "friday",
    "veronica": "veronica",
    "edith": "edith",
    "u": "u",
    "dume": "dume",
    "jocasta": "jocasta",
    "karen": "karen",
    "jarvis": "jarvis",
}

TOOL_ROUTE_MAP: Dict[str, tuple] = {
    # INTEL LAB (Web, OSINT, Wikipedia, News, Scam Recon)
    "search_web": ("edith", "intel_lab", "SEARCHING"),
    "browse_website": ("edith", "intel_lab", "SEARCHING"),
    "perform_live_web_search": ("edith", "intel_lab", "SEARCHING"),
    "autonomous_deep_research": ("edith", "intel_lab", "SEARCHING"),
    "research_topic": ("edith", "intel_lab", "SEARCHING"),
    "synthesize_technical_report": ("edith", "intel_lab", "THINKING"),
    "harvest_knowledge": ("edith", "intel_lab", "SEARCHING"),
    "extract_knowledge_matrix": ("edith", "intel_lab", "SEARCHING"),
    "check_scam_phone_number": ("edith", "intel_lab", "SEARCHING"),
    "search_wikipedia": ("edith", "intel_lab", "SEARCHING"),
    "ingest_youtube": ("edith", "intel_lab", "SEARCHING"),
    # IOT & MAKER (Hardware, ESP32, Circuits, Smart Home, Thermal)
    "flash_esp32_firmware": ("dume", "maker_iot", "EXECUTING"),
    "hardware_controller": ("dume", "maker_iot", "EXECUTING"),
    "simulate_electronic_circuit": ("dume", "maker_iot", "EXECUTING"),
    "reverse_engineer_schematic": ("veronica", "maker_iot", "SEARCHING"),
    "generate_bom_from_circuit": ("veronica", "maker_iot", "THINKING"),
    "get_thermal_telemetry": ("veronica", "maker_iot", "SEARCHING"),
    "manage_lab_inventory": ("karen", "maker_iot", "EXECUTING"),
    "open_suit_designer": ("friday", "maker_iot", "CODING"),
    "control_light": ("karen", "maker_iot", "EXECUTING"),
    "toggle_home_assistant_device": ("karen", "maker_iot", "EXECUTING"),
    "get_light_status": ("karen", "maker_iot", "SEARCHING"),
    "activate_scene": ("karen", "maker_iot", "EXECUTING"),
    "set_ambiance": ("karen", "maker_iot", "EXECUTING"),
    "call_home_assistant_service": ("karen", "maker_iot", "EXECUTING"),
    # DATA / NET (Memory, ChromaDB, Cyber Security, Telemetry, Network)
    "get_server_telemetry": ("veronica", "data_net", "SEARCHING"),
    "check_database_and_cache": ("veronica", "data_net", "SEARCHING"),
    "supervise_watchdog_services": ("veronica", "data_net", "EXECUTING"),
    "scan_local_network": ("jocasta", "data_net", "SEARCHING"),
    "get_neural_risk_analysis": ("jocasta", "data_net", "THINKING"),
    "search_local_brain": ("jocasta", "data_net", "SEARCHING"),
    "save_to_memory": ("jocasta", "data_net", "CODING"),
    "distill_memory": ("jocasta", "data_net", "THINKING"),
    "build_knowledge_graph_relation": ("jocasta", "data_net", "CODING"),
    "trigger_learning_cycle": ("jocasta", "data_net", "THINKING"),
    "scan_dropzone": ("jocasta", "data_net", "SEARCHING"),
    # DEV LAB (Code, Self-Patch, Dynamic Tool Creation, Evolution)
    "generate_new_tool": ("friday", "dev_lab", "CODING"),
    "delete_custom_tool": ("friday", "dev_lab", "CODING"),
    "self_patch_system": ("friday", "dev_lab", "CODING"),
    "run_codebase_maintenance": ("friday", "dev_lab", "CODING"),
    "run_evolution_scan": ("friday", "dev_lab", "THINKING"),
    "swarm_develop_project": ("friday", "dev_lab", "CODING"),
    "analyze_molecular_structure": ("friday", "dev_lab", "THINKING"),
    # SYS OPS (Windows Processes, PowerShell, Files, Email, Schedules)
    "manage_windows_processes": ("dume", "sys_ops", "EXECUTING"),
    "manage_system_maintenance": ("u", "sys_ops", "EXECUTING"),
    "execute_powershell_safe": ("dume", "sys_ops", "EXECUTING"),
    "run_command": ("dume", "sys_ops", "EXECUTING"),
    "run_terminal_command": ("dume", "sys_ops", "EXECUTING"),
    "execute_in_background": ("karen", "sys_ops", "EXECUTING"),
    "list_directory_contents": ("dume", "sys_ops", "SEARCHING"),
    "move_file_or_folder": ("dume", "sys_ops", "EXECUTING"),
    "schedule_task": ("karen", "sys_ops", "THINKING"),
    "manage_gmail": ("karen", "sys_ops", "EXECUTING"),
    "check_unread_emails": ("karen", "sys_ops", "SEARCHING"),
    "send_email": ("karen", "sys_ops", "EXECUTING"),
    "search_emails": ("karen", "sys_ops", "SEARCHING"),
    # MEDIA & QA (Vision, Camera, Screenshots, Video, GUI Control, Music)
    "capture_webcam": ("u", "media_qa", "EXECUTING"),
    "take_screenshot": ("u", "media_qa", "EXECUTING"),
    "generate_image": ("u", "media_qa", "EXECUTING"),
    "search_image": ("u", "media_qa", "SEARCHING"),
    "visualize_data_3d": ("u", "media_qa", "CODING"),
    "render_3d_workspace": ("u", "media_qa", "CODING"),
    "generate_and_render_hologram": ("u", "media_qa", "EXECUTING"),
    "extract_spatial_cad_mesh": ("u", "media_qa", "THINKING"),
    "get_spatial_reconstruction": ("u", "media_qa", "SEARCHING"),
    "search_spatial_map": ("u", "media_qa", "SEARCHING"),
    "analyze_hud_object": ("u", "media_qa", "SEARCHING"),
    "archive_schematic_snapshot": ("u", "media_qa", "EXECUTING"),
    "auto_video_subtitle": ("u", "media_qa", "EXECUTING"),
    "control_capcut": ("u", "media_qa", "EXECUTING"),
    "control_computer_agent": ("dume", "media_qa", "EXECUTING"),
    "agentic_computer_control": ("dume", "media_qa", "EXECUTING"),
    "execute_computer_action": ("dume", "media_qa", "EXECUTING"),
    "control_social_media": ("karen", "media_qa", "EXECUTING"),
    "manage_game_protocol": ("edith", "media_qa", "EXECUTING"),
    "play_music": ("karen", "media_qa", "EXECUTING"),
    # COMMAND DECK (Executive Meta, Status, History)
    "manage_mission_log": ("jarvis", "command_deck", "THINKING"),
    "get_recent_chat_history": ("jarvis", "command_deck", "SEARCHING"),
    "call_boss": ("jarvis", "command_deck", "EXECUTING"),
    "get_weather": ("jarvis", "command_deck", "SEARCHING"),
    "update_user_profile": ("jarvis", "command_deck", "THINKING"),
    "toggle_island": ("jarvis", "command_deck", "EXECUTING"),
    "set_island_skin": ("jarvis", "command_deck", "EXECUTING"),
}


def classify_tool_route(tool_name: str, args: Optional[Dict[str, Any]] = None, user_msg: str = "") -> tuple:
    """Resolve (agent_id, room_id, state) for any live J.A.R.V.I.S. tool call."""
    key = (tool_name or "").strip().lower()
    if key in TOOL_ROUTE_MAP:
        return TOOL_ROUTE_MAP[key]
    if "gui_" in key or "screen" in key or "camera" in key or "video" in key:
        return ("u", "media_qa", "EXECUTING")
    if "search" in key or "web" in key or "wiki" in key:
        return ("edith", "intel_lab", "SEARCHING")
    if "esp32" in key or "circuit" in key or "light" in key or "hardware" in key:
        return ("dume", "maker_iot", "EXECUTING")
    if "server" in key or "network" in key or "db" in key or "memory" in key:
        return ("jocasta", "data_net", "SEARCHING")
    if "file" in key or "process" in key or "powershell" in key or "mail" in key:
        return ("dume", "sys_ops", "EXECUTING")
    room = classify_task_room(f"{tool_name} {user_msg}", "friday")
    return ("friday", room, "CODING")


@dataclass
class OfficeAgentMeta:
    agent_id: str
    name: str
    title: str
    color: str
    work_state: str
    desk_zone: str
    state: str = "IDLE"
    zone: str = "lounge"
    task: str = ""
    bubble: str = ""
    bubble_at: float = 0.0
    last_updated: float = field(default_factory=time.time)
    completed_count: int = 0


def _default_roster() -> Dict[str, OfficeAgentMeta]:
    specs = [
        ("jarvis", "J.A.R.V.I.S.", "Executive Orchestrator & Synthesis", "#ffd700", "THINKING", "command_deck"),
        ("friday", "F.R.I.D.A.Y.", "Tactical Ops & Code Engine (@code)", "#00c8ff", "CODING", "dev_lab"),
        ("veronica", "V.E.R.O.N.I.C.A.", "Hardware & Safety Sentinel", "#ef4444", "SEARCHING", "dev_lab"),
        ("edith", "E.D.I.T.H.", "Game Theory & Web Recon (@web)", "#a855f7", "SEARCHING", "intel_lab"),
        ("u", "U.", "Visual QA & System Maintenance", "#22c55e", "THINKING", "media_qa"),
        ("dume", "D.U.M.-E.", "OS Automation & Actuators (@os)", "#f59e0b", "EXECUTING", "maker_iot"),
        ("jocasta", "J.O.C.A.S.T.A.", "Cyber-Defense & CLI Crypto (@cli)", "#94a3b8", "CODING", "data_net"),
        ("karen", "K.A.R.E.N.", "Situational Support & Comms", "#2dd4bf", "THINKING", "sys_ops"),
    ]
    now = time.time()
    return {
        aid: OfficeAgentMeta(
            agent_id=aid,
            name=name,
            title=title,
            color=color,
            work_state=work_state,
            desk_zone=desk_zone,
            state="IDLE",
            zone="lounge",
            bubble="",
            bubble_at=now,
            last_updated=now,
        )
        for aid, name, title, color, work_state, desk_zone in specs
    }


def resolve_agent_id(raw_id: Optional[str]) -> str:
    """Resolve explicit codename or @role alias to a canonical office agent_id."""
    if not raw_id:
        return "jarvis"
    cleaned = raw_id.strip().lstrip("@").lower()
    return AGENT_ALIASES.get(cleaned, "jarvis")


def parse_direct_prompt(prompt: str, fallback_agent: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Parse optional '@agent' and '@from -> @to' handoff syntax from prompt text."""
    text = (prompt or "").strip()
    handoff_match = re.match(
        r"^@([a-zA-Z0-9_-]+)\s*(?:->|→)\s*@([a-zA-Z0-9_-]+)\s*[:\-]?\s*(.+)$",
        text,
        flags=re.DOTALL,
    )
    if handoff_match:
        return {
            "agent_id": resolve_agent_id(handoff_match.group(1)),
            "handoff_to": resolve_agent_id(handoff_match.group(2)),
            "clean_prompt": handoff_match.group(3).strip(),
        }

    single_match = re.match(r"^@([a-zA-Z0-9_-]+)\s*[:\-]?\s*(.+)$", text, flags=re.DOTALL)
    if single_match:
        candidate = single_match.group(1).lower()
        if candidate in AGENT_ALIASES:
            return {
                "agent_id": AGENT_ALIASES[candidate],
                "handoff_to": None,
                "clean_prompt": single_match.group(2).strip(),
            }

    return {
        "agent_id": resolve_agent_id(fallback_agent) if fallback_agent else "jarvis",
        "handoff_to": None,
        "clean_prompt": text,
    }


class AgentOfficeManager:
    """Thread-safe real-time AI Office state & multi-agent collaboration orchestrator."""

    def __init__(self, core_ref: Optional[Any] = None):
        self.core = core_ref
        self.is_active = True
        self._lock = threading.RLock()
        self._agents: Dict[str, OfficeAgentMeta] = _default_roster()
        self._tasks: deque[Dict[str, Any]] = deque(maxlen=40)
        self._feed: deque[Dict[str, Any]] = deque(maxlen=80)
        self._active_mission_id: Optional[str] = None
        self._live_depth: Dict[str, int] = {aid: 0 for aid in self._agents}
        self._core_executor = None
        self._local_flags = threading.local()
        self._append_feed(
            from_agent="jarvis",
            to_agent="all",
            message="Nachapol AI Office online. Synced with real J.A.R.V.I.S. core.",
            kind="system",
        )

    def attach_core_executor(self, fn: Any) -> None:
        """Attach a callable (agent_id, prompt, context) -> Optional[str] for real J.A.R.V.I.S. tool-backed execution."""
        with self._lock:
            self._core_executor = fn

    # ── Lifecycle Protocol (jarvis-module-scaffolder) ───────────────────────
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            self.is_active = True
            return True

    def get_telemetry(self) -> Dict[str, Any]:
        return self.get_state_snapshot()

    def shutdown(self) -> None:
        with self._lock:
            self.is_active = False
            for agent in self._agents.values():
                agent.state = "IDLE"
                agent.zone = "lounge"
                agent.task = ""

    # ── State Mutators ──────────────────────────────────────────────────────
    def _set_agent_state(
        self,
        agent_id: str,
        *,
        state: Optional[str] = None,
        zone: Optional[str] = None,
        task: Optional[str] = None,
        bubble: Optional[str] = None,
        increment_done: bool = False,
    ) -> None:
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return
            now = time.time()
            if state in VALID_STATES:
                agent.state = state
            if zone is not None:
                agent.zone = zone
            if task is not None:
                agent.task = task
            if bubble is not None:
                agent.bubble = bubble[:110]
                agent.bubble_at = now
            if increment_done:
                agent.completed_count += 1
            agent.last_updated = now

    def _append_feed(
        self,
        *,
        from_agent: str,
        to_agent: str,
        message: str,
        kind: str = "chat",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry = {
            "id": uuid.uuid4().hex[:8],
            "timestamp": time.time(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "kind": kind,
            "task_id": task_id,
        }
        with self._lock:
            self._feed.appendleft(entry)
        return entry

    def _create_task(
        self,
        *,
        title: str,
        assigned_to: str,
        status: str = "queued",
        parent_id: Optional[str] = None,
        kind: str = "command",
    ) -> Dict[str, Any]:
        task = {
            "id": uuid.uuid4().hex[:8],
            "title": title,
            "assigned_to": assigned_to,
            "status": status,
            "parent_id": parent_id,
            "kind": kind,
            "result": "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        with self._lock:
            self._tasks.appendleft(task)
        return task

    def _update_task(self, task_id: str, *, status: Optional[str] = None, result: Optional[str] = None) -> None:
        with self._lock:
            for t in self._tasks:
                if t["id"] == task_id:
                    if status is not None:
                        t["status"] = status
                    if result is not None:
                        t["result"] = result
                    t["updated_at"] = time.time()
                    return

    def get_state_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            agents_list = []
            busy_count = 0
            for agent in self._agents.values():
                d = asdict(agent)
                if agent.state != "IDLE":
                    busy_count += 1
                # Expire stale speech bubbles cleanly after 18s when idle
                if agent.state == "IDLE" and (now - agent.bubble_at) > 18.0:
                    d["bubble"] = ""
                agents_list.append(d)

            tasks_list = list(self._tasks)
            return {
                "status": "online" if self.is_active else "offline",
                "timestamp": now,
                "active_mission_id": self._active_mission_id,
                "agents": agents_list,
                "tasks": tasks_list,
                "feed": list(self._feed),
                "summary": {
                    "total_agents": len(agents_list),
                    "busy_agents": busy_count,
                    "queued_tasks": sum(1 for t in tasks_list if t["status"] in ("queued", "meeting")),
                    "in_progress_tasks": sum(1 for t in tasks_list if t["status"] == "in_progress"),
                    "done_tasks": sum(1 for t in tasks_list if t["status"] == "done"),
                },
            }

    def reset_office(self) -> Dict[str, Any]:
        with self._lock:
            self._active_mission_id = None
            for aid in list(self._live_depth.keys()):
                self._live_depth[aid] = 0
            for agent in self._agents.values():
                agent.state = "IDLE"
                agent.zone = "lounge"
                agent.task = ""
                agent.bubble = ""
                agent.last_updated = time.time()
            self._tasks.clear()
            self._feed.clear()
            self._append_feed(
                from_agent="jarvis",
                to_agent="all",
                message="Office workspace reset. All desks cleared.",
                kind="system",
            )
            return self.get_state_snapshot()

    # ── Live Real-System Telemetry Hooks (Chat, Tools, Swarm) ───────────────
    def _push_live_work(
        self,
        agent_id: str,
        *,
        state: str,
        zone: str,
        task_title: str,
        bubble: str,
        kind: str = "live",
        from_actor: str = "boss",
    ) -> Dict[str, str]:
        aid = resolve_agent_id(agent_id)
        task_rec = self._create_task(title=task_title[:120], assigned_to=aid, status="in_progress", kind=kind)
        with self._lock:
            self._live_depth[aid] = self._live_depth.get(aid, 0) + 1
        self._set_agent_state(aid, state=state, zone=zone, task=task_title[:90], bubble=bubble[:95])
        self._append_feed(
            from_agent=from_actor,
            to_agent=aid,
            message=f"[{zone}] {task_title[:140]}",
            kind=kind,
            task_id=task_rec["id"],
        )
        return {"agent_id": aid, "task_id": task_rec["id"], "zone": zone}

    def _pop_live_work(
        self,
        ctx: Optional[Dict[str, str]],
        *,
        summary: str = "",
        is_error: bool = False,
        kind: str = "live",
    ) -> None:
        if not ctx or not ctx.get("agent_id"):
            return
        aid = ctx["agent_id"]
        task_id = ctx.get("task_id", "")
        clean_summary = (summary or ("เกิดข้อผิดพลาด" if is_error else "ดำเนินการเรียบร้อย")).strip()
        if task_id:
            self._update_task(task_id, status="failed" if is_error else "done", result=clean_summary[:500])
        if clean_summary:
            self._append_feed(
                from_agent=aid,
                to_agent="boss",
                message=clean_summary[:260],
                kind=kind,
                task_id=task_id or None,
            )
        with self._lock:
            depth = max(0, self._live_depth.get(aid, 1) - 1)
            self._live_depth[aid] = depth
        if depth == 0:
            self._set_agent_state(
                aid,
                state="IDLE",
                zone="lounge",
                task="",
                bubble=clean_summary[:70],
                increment_done=not is_error,
            )

    def notify_live_turn_start(
        self,
        user_msg: str,
        *,
        routed_intent: str = "general",
        channel: str = "hud",
    ) -> Optional[Dict[str, str]]:
        """Mirror a real user chat/voice/LINE command into the Office canvas & feed."""
        if getattr(self._local_flags, "suppress_turn_hook", False):
            return None
        clean = (user_msg or "").strip()
        if not clean:
            return None
        parsed = parse_direct_prompt(clean, fallback_agent=ROUTE_INTENT_TO_AGENT.get(routed_intent, "jarvis"))
        aid = parsed["agent_id"] or "jarvis"
        clean_title = parsed["clean_prompt"] or clean
        room = classify_task_room(clean_title, aid)
        return self._push_live_work(
            aid,
            state=self._agents[aid].work_state if aid != "jarvis" else "THINKING",
            zone=room,
            task_title=f"[{channel.upper()}] {clean_title[:100]}",
            bubble=clean_title[:55],
            kind="live_chat",
            from_actor=f"boss({channel})",
        )

    def notify_live_turn_end(
        self,
        turn_ctx: Optional[Dict[str, str]],
        reply_text: str = "",
        *,
        is_error: bool = False,
    ) -> None:
        self._pop_live_work(turn_ctx, summary=reply_text, is_error=is_error, kind="live_reply")

    def notify_live_tool_start(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        user_msg: str = "",
    ) -> Optional[Dict[str, str]]:
        """Dispatch the appropriate specialist into the matching functional lab while a real tool executes."""
        if not tool_name:
            return None
        aid, room, st = classify_tool_route(tool_name, args, user_msg)
        arg_hint = ""
        if isinstance(args, dict):
            for k in ("query", "topic", "command", "cmd", "task", "goal", "url", "phone_number", "location", "entity_id", "project_description"):
                if args.get(k):
                    arg_hint = f": {str(args[k])[:45]}"
                    break
        title = f"⚡ {tool_name}{arg_hint}"
        return self._push_live_work(
            aid,
            state=st,
            zone=room,
            task_title=title,
            bubble=title[:55],
            kind="tool",
            from_actor="jarvis",
        )

    def notify_live_tool_end(
        self,
        tool_ctx: Optional[Dict[str, str]],
        result_text: str = "",
        *,
        is_error: bool = False,
    ) -> None:
        self._pop_live_work(tool_ctx, summary=result_text, is_error=is_error, kind="tool_result")

    def notify_live_council_start(self, query: str, active_codes: List[str]) -> Dict[str, Any]:
        """Gather Swarm Council members into Meeting/Situational Labs for real council debate."""
        task = self._create_task(title=f"Council Debate: {query[:90]}", assigned_to="jarvis", status="in_progress", kind="council")
        members = [resolve_agent_id(c) for c in active_codes if resolve_agent_id(c) in self._agents]
        self._set_agent_state("jarvis", state="MEETING", zone="meeting", task=f"Council: {query[:55]}", bubble="เปิดประชุมสภา AI Swarm")
        for aid in members:
            if aid != "jarvis":
                with self._lock:
                    self._live_depth[aid] = self._live_depth.get(aid, 0) + 1
                self._set_agent_state(aid, state="MEETING", zone="meeting", task=f"Council: {query[:55]}", bubble="กำลังระดมสมอง...")
        self._append_feed(from_agent="jarvis", to_agent="all", message=f"Council Debate: {query[:140]}", kind="council", task_id=task["id"])
        return {"task_id": task["id"], "members": members}

    def notify_live_council_member(self, code: str, query: str, output: str) -> None:
        aid = resolve_agent_id(code)
        room = classify_task_room(query, aid)
        self._set_agent_state(aid, state=self._agents[aid].work_state, zone=room, task="", bubble=output[:60])
        self._append_feed(from_agent=aid, to_agent="jarvis", message=output[:240], kind="council")

    def notify_live_council_end(self, council_ctx: Optional[Dict[str, Any]], summary: str = "") -> None:
        if not council_ctx:
            return
        if council_ctx.get("task_id"):
            self._update_task(council_ctx["task_id"], status="done", result=summary[:500])
        for aid in council_ctx.get("members", []):
            with self._lock:
                depth = max(0, self._live_depth.get(aid, 1) - 1)
                self._live_depth[aid] = depth
            if depth == 0:
                self._set_agent_state(aid, state="IDLE", zone="lounge", task="", bubble="", increment_done=True)
        self._set_agent_state("jarvis", state="IDLE", zone="lounge", task="", bubble=summary[:65], increment_done=True)
        if summary:
            self._append_feed(from_agent="jarvis", to_agent="boss", message=summary[:260], kind="synthesis", task_id=council_ctx.get("task_id"))

    # ── AI Execution Helpers ────────────────────────────────────────────────
    def _invoke_specialist(self, agent_id: str, prompt: str, context: str = "") -> str:
        """Execute a specialist response via wired real J.A.R.V.I.S. core, CANONICAL_SWARM, or core router."""
        with self._lock:
            core_exec = self._core_executor
        if core_exec is not None:
            try:
                self._local_flags.suppress_turn_hook = True
                res = core_exec(agent_id, prompt, context)
                if isinstance(res, str) and res.strip():
                    return res.strip()
            except Exception as core_err:
                logger.warning(f"[AgentOffice] Core executor failed for '{agent_id}', using fallback: {core_err}")
            finally:
                self._local_flags.suppress_turn_hook = False
        try:
            from jarvis_core.cognitive.swarm import CANONICAL_SWARM
            from jarvis_core.ai_router import call_nachapol_core

            if agent_id in CANONICAL_SWARM:
                reply = CANONICAL_SWARM[agent_id].deliberate(context=context, query=prompt)
                if reply and reply.strip():
                    return reply.strip()

            sys_prompt = (
                "You are J.A.R.V.I.S., Executive Orchestrator of Nachapol Industries AI Office. "
                "Respond concisely in Thai with engineering precision and polite address (ครับท่าน / เจ้านาย)."
            )
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"{f'[Context: {context}] ' if context else ''}{prompt}"},
            ]
            fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
            resp = call_nachapol_core(messages=messages, model=fast_model)
            content = (resp or {}).get("content", "").strip()
            if content:
                return content
            err = (resp or {}).get("error_message")
            if err:
                return f"[{self._agents[agent_id].name} Notice] {err}"
        except Exception as e:
            logger.warning(f"[AgentOffice] Specialist '{agent_id}' fallback: {e}")
            return f"[{self._agents[agent_id].name} Offline Fallback] รับทราบภารกิจ: {prompt[:80]}"

        return f"[{self._agents[agent_id].name}] ดำเนินการวิเคราะห์คำสั่งเสร็จสิ้นครับท่าน"

    def _decompose_mission(self, mission: str, quorum: List[str]) -> Dict[str, str]:
        """Split a mission into per-agent subtasks via fast LLM with deterministic fallback."""
        fallback = {
            aid: f"วิเคราะห์และดำเนินส่วนของ {self._agents[aid].title} สำหรับภารกิจ: {mission}"
            for aid in quorum
        }
        try:
            from jarvis_core.ai_router import call_nachapol_core

            roster_desc = "\n".join(
                f"- {aid}: {self._agents[aid].name} ({self._agents[aid].title})"
                for aid in quorum
            )
            prompt = (
                f"Break down this mission cleanly for these AI specialists. Return ONLY valid JSON mapping agent_id -> concise Thai subtask.\n"
                f"Mission: {mission}\nSpecialists:\n{roster_desc}"
            )
            fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
            resp = call_nachapol_core(
                messages=[{"role": "user", "content": prompt}],
                model=fast_model,
            )
            raw = (resp or {}).get("content", "").strip()
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    for aid in quorum:
                        if isinstance(parsed.get(aid), str) and parsed[aid].strip():
                            fallback[aid] = parsed[aid].strip()
        except Exception as e:
            logger.debug(f"[AgentOffice] Mission decomposition used fallback: {e}")
        return fallback

    # ── Public Orchestration Actions ────────────────────────────────────────
    def dispatch_command(
        self,
        *,
        prompt: str,
        agent_id: Optional[str] = None,
        handoff_to: Optional[str] = None,
        run_async: bool = True,
    ) -> Dict[str, Any]:
        parsed = parse_direct_prompt(prompt, fallback_agent=agent_id)
        target_id = parsed["agent_id"] or "jarvis"
        clean_prompt = parsed["clean_prompt"] or prompt.strip()
        next_id = resolve_agent_id(handoff_to) if handoff_to else parsed["handoff_to"]

        meta = self._agents[target_id]
        target_room = classify_task_room(clean_prompt, target_id)
        task = self._create_task(title=clean_prompt, assigned_to=target_id, status="in_progress", kind="command")

        self._set_agent_state(
            target_id,
            state=meta.work_state,
            zone=target_room,
            task=clean_prompt[:90],
            bubble=f"[{target_room}] {clean_prompt[:45]}",
        )
        self._append_feed(
            from_agent="user",
            to_agent=target_id,
            message=f"@{target_id} {clean_prompt}",
            kind="directive",
            task_id=task["id"],
        )

        def _worker():
            try:
                reply = self._invoke_specialist(target_id, clean_prompt)
                self._update_task(task["id"], status="done", result=reply)
                self._append_feed(
                    from_agent=target_id,
                    to_agent=next_id or "user",
                    message=reply,
                    kind="reply",
                    task_id=task["id"],
                )
                self._set_agent_state(
                    target_id,
                    state="IDLE",
                    zone="lounge",
                    task="",
                    bubble=reply[:70],
                    increment_done=True,
                )

                if next_id and next_id != target_id and next_id in self._agents:
                    next_meta = self._agents[next_id]
                    handoff_room = classify_task_room(clean_prompt, next_id)
                    handoff_task = self._create_task(
                        title=f"Handoff from {meta.name}: {clean_prompt[:60]}",
                        assigned_to=next_id,
                        status="in_progress",
                        parent_id=task["id"],
                        kind="handoff",
                    )
                    self._set_agent_state(
                        next_id,
                        state=next_meta.work_state,
                        zone=handoff_room,
                        task=f"รับต่อจาก {meta.name}",
                        bubble=f"รับต่อที่ {handoff_room}...",
                    )
                    self._append_feed(
                        from_agent=target_id,
                        to_agent=next_id,
                        message=f"ส่งต่อให้ @{next_id} ตรวจ/ดำเนินการต่อ",
                        kind="handoff",
                        task_id=handoff_task["id"],
                    )
                    reply2 = self._invoke_specialist(
                        next_id,
                        f"ต่อยอด/ตรวจสอบผลลัพธ์จาก {meta.name} สำหรับงาน '{clean_prompt}'",
                        context=reply[:500],
                    )
                    self._update_task(handoff_task["id"], status="done", result=reply2)
                    self._append_feed(
                        from_agent=next_id,
                        to_agent="user",
                        message=reply2,
                        kind="reply",
                        task_id=handoff_task["id"],
                    )
                    self._set_agent_state(
                        next_id,
                        state="IDLE",
                        zone="lounge",
                        task="",
                        bubble=reply2[:70],
                        increment_done=True,
                    )
            except Exception as e:
                logger.error(f"[AgentOffice] Command worker failed: {e}", exc_info=True)
                self._update_task(task["id"], status="failed", result=str(e))
                self._set_agent_state(target_id, state="ERROR", bubble=f"Error: {e}"[:60])

        if run_async:
            threading.Thread(target=_worker, daemon=True, name=f"OfficeCmd-{target_id}").start()
        else:
            _worker()

        return {"status": "accepted", "task_id": task["id"], "agent_id": target_id, "handoff_to": next_id}

    def start_mission(
        self,
        *,
        mission: str,
        agents: Optional[List[str]] = None,
        run_async: bool = True,
    ) -> Dict[str, Any]:
        clean_mission = (mission or "").strip()
        if not clean_mission:
            return {"status": "error", "message": "Mission text is empty."}

        quorum = []
        for a in (agents or ["friday", "veronica", "edith", "u"]):
            aid = resolve_agent_id(a)
            if aid != "jarvis" and aid not in quorum:
                quorum.append(aid)
        if not quorum:
            quorum = ["friday", "veronica", "edith"]

        mission_task = self._create_task(
            title=clean_mission,
            assigned_to="jarvis",
            status="meeting",
            kind="mission",
        )
        with self._lock:
            self._active_mission_id = mission_task["id"]

        # Phase 1: Convene in Meeting Room
        meeting_team = ["jarvis"] + quorum
        for aid in meeting_team:
            self._set_agent_state(
                aid,
                state="MEETING",
                zone="meeting",
                task=f"Meeting: {clean_mission[:50]}",
                bubble="กำลังประชุมวางแผนภารกิจ...",
            )
        self._append_feed(
            from_agent="jarvis",
            to_agent="all",
            message=f"เรียกประชุมห้อง Meeting: \"{clean_mission}\" ({', '.join('@' + a for a in quorum)})",
            kind="meeting",
            task_id=mission_task["id"],
        )

        def _mission_runner():
            try:
                subtasks = self._decompose_mission(clean_mission, quorum)
                self._update_task(mission_task["id"], status="in_progress")

                subtask_records: Dict[str, Dict[str, Any]] = {}
                for aid in quorum:
                    st_text = subtasks[aid]
                    rec = self._create_task(
                        title=st_text,
                        assigned_to=aid,
                        status="in_progress",
                        parent_id=mission_task["id"],
                        kind="subtask",
                    )
                    subtask_records[aid] = rec
                    meta = self._agents[aid]
                    sub_room = classify_task_room(f"{clean_mission} {st_text}", aid)
                    self._set_agent_state(
                        aid,
                        state=meta.work_state,
                        zone=sub_room,
                        task=st_text[:80],
                        bubble=f"[{sub_room}] {st_text[:40]}",
                    )
                    self._append_feed(
                        from_agent="jarvis",
                        to_agent=aid,
                        message=f"@{aid} รับผิดชอบ: {st_text}",
                        kind="delegation",
                        task_id=rec["id"],
                    )

                self._set_agent_state(
                    "jarvis",
                    state="THINKING",
                    zone="command_deck",
                    task="กำลังประสานงานทีมและรอผลลัพธ์...",
                    bubble="กำลังติดตามความคืบหน้าทุกแผนก",
                )

                results: Dict[str, str] = {}
                with ThreadPoolExecutor(max_workers=min(len(quorum), 4)) as pool:
                    fut_map = {
                        pool.submit(self._invoke_specialist, aid, subtasks[aid], clean_mission): aid
                        for aid in quorum
                    }
                    for fut, aid in fut_map.items():
                        try:
                            out = fut.result(timeout=45)
                        except Exception as ex:
                            out = f"[{self._agents[aid].name} Error] {ex}"
                        results[aid] = out
                        self._update_task(subtask_records[aid]["id"], status="done", result=out)
                        self._append_feed(
                            from_agent=aid,
                            to_agent="jarvis",
                            message=out,
                            kind="reply",
                            task_id=subtask_records[aid]["id"],
                        )
                        self._set_agent_state(
                            aid,
                            state="IDLE",
                            zone="lounge",
                            task="",
                            bubble=out[:70],
                            increment_done=True,
                        )

                # Phase 3: Executive synthesis by J.A.R.V.I.S.
                compiled = "\n\n".join(f"[{self._agents[aid].name}]\n{txt}" for aid, txt in results.items())
                synthesis = self._invoke_specialist(
                    "jarvis",
                    f"สรุปแผนปฏิบัติการและผลลัพธ์จากทุกแผนกสำหรับภารกิจ '{clean_mission}' ให้กระชับชัดเจน",
                    context=compiled[:2000],
                )
                self._update_task(mission_task["id"], status="done", result=synthesis)
                self._append_feed(
                    from_agent="jarvis",
                    to_agent="user",
                    message=synthesis,
                    kind="synthesis",
                    task_id=mission_task["id"],
                )
                self._set_agent_state(
                    "jarvis",
                    state="IDLE",
                    zone="lounge",
                    task="",
                    bubble="ภารกิจทีมเสร็จสมบูรณ์ครับท่าน",
                    increment_done=True,
                )
            except Exception as e:
                logger.error(f"[AgentOffice] Mission runner failed: {e}", exc_info=True)
                self._update_task(mission_task["id"], status="failed", result=str(e))
                for aid in meeting_team:
                    self._set_agent_state(aid, state="IDLE", zone="lounge", task="", bubble="")
            finally:
                with self._lock:
                    if self._active_mission_id == mission_task["id"]:
                        self._active_mission_id = None

        if run_async:
            threading.Thread(target=_mission_runner, daemon=True, name="OfficeMissionRunner").start()
        else:
            _mission_runner()

        return {"status": "accepted", "mission_id": mission_task["id"], "quorum": quorum}

    def post_inter_agent_chat(
        self,
        *,
        from_agent: str,
        to_agent: str,
        message: str,
        auto_reply: bool = True,
        run_async: bool = True,
    ) -> Dict[str, Any]:
        src = resolve_agent_id(from_agent)
        dst = resolve_agent_id(to_agent)
        msg = (message or "").strip()
        if not msg:
            return {"status": "error", "message": "Empty message."}

        entry = self._append_feed(from_agent=src, to_agent=dst, message=msg, kind="chat")
        self._set_agent_state(src, bubble=f"-> @{dst}: {msg[:45]}")

        if auto_reply and dst != src:
            dst_meta = self._agents[dst]

            def _reply_worker():
                reply_room = classify_task_room(msg, dst)
                self._set_agent_state(
                    dst,
                    state=dst_meta.work_state,
                    zone=reply_room,
                    task=f"ตอบกลับ @{src}",
                    bubble=f"กำลังตอบ @{src}...",
                )
                reply = self._invoke_specialist(dst, f"เพื่อนร่วมทีม {self._agents[src].name} ส่งข้อความหาคุณว่า: {msg}")
                self._append_feed(from_agent=dst, to_agent=src, message=reply, kind="reply")
                self._set_agent_state(dst, state="IDLE", zone="lounge", task="", bubble=reply[:70])

            if run_async:
                threading.Thread(target=_reply_worker, daemon=True, name=f"OfficeChat-{dst}").start()
            else:
                _reply_worker()

        return {"status": "ok", "entry": entry}


agent_office_manager = AgentOfficeManager()
agent_office_bp = Blueprint("agent_office", __name__)


@agent_office_bp.route("/api/office/state", methods=["GET"])
def api_office_state():
    return jsonify(agent_office_manager.get_state_snapshot())


@agent_office_bp.route("/api/office/command", methods=["POST"])
def api_office_command():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt") or data.get("command") or data.get("message") or ""
    if not str(prompt).strip():
        return jsonify({"status": "error", "message": "Missing 'prompt' in request."}), 400
    res = agent_office_manager.dispatch_command(
        prompt=str(prompt),
        agent_id=data.get("agent_id"),
        handoff_to=data.get("handoff_to"),
        run_async=bool(data.get("async", True)),
    )
    return jsonify(res)


@agent_office_bp.route("/api/office/mission", methods=["POST"])
def api_office_mission():
    data = request.get_json(silent=True) or {}
    mission = data.get("mission") or data.get("goal") or data.get("prompt") or ""
    if not str(mission).strip():
        return jsonify({"status": "error", "message": "Missing 'mission' in request."}), 400
    agents = data.get("agents")
    res = agent_office_manager.start_mission(
        mission=str(mission),
        agents=agents if isinstance(agents, list) else None,
        run_async=bool(data.get("async", True)),
    )
    return jsonify(res)


@agent_office_bp.route("/api/office/chat", methods=["POST"])
def api_office_chat():
    data = request.get_json(silent=True) or {}
    res = agent_office_manager.post_inter_agent_chat(
        from_agent=data.get("from_agent") or "jarvis",
        to_agent=data.get("to_agent") or "friday",
        message=data.get("message") or "",
        auto_reply=bool(data.get("auto_reply", True)),
        run_async=bool(data.get("async", True)),
    )
    code = 200 if res.get("status") == "ok" else 400
    return jsonify(res), code


@agent_office_bp.route("/api/office/reset", methods=["POST"])
def api_office_reset():
    return jsonify(agent_office_manager.reset_office())


def register_agent_office_routes(app) -> bool:
    """Safely register the Agent Office Flask Blueprint once per Flask app."""
    if "agent_office" not in app.blueprints:
        app.register_blueprint(agent_office_bp)
        logger.info("[AGENT_OFFICE] Blueprint routes registered cleanly.")
    return True
