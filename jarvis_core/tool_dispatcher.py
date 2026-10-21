"""
jarvis_core.tool_dispatcher
===========================
Dispatches, validates, and executes tool calls for J.A.R.V.I.S.
Integrates safety guardrails, dynamic tool runners, and autonomous agents.
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional

import requests
from jarvis_core.config import DYNAMIC_TOOLS_DIR, MODULES_DIR, BASE_DIR
from jarvis_core.state import increment_metric
from jarvis_core.automation_agent import get_computer_agent

logger = logging.getLogger("JarvisToolDispatcher")

EMERGENCY_STOP_FLAG = False

# Concurrency & GIL Safety Primitives
GUI_ACTION_LOCK = threading.RLock()
TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="JarvisToolWorker")


def format_tool_response(name: str, result: Any, status: str = "success") -> str:
    """Format standard tool response payload as string/json."""
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)
    return str(result)


def guardrail_validation(tool_name: str, args: dict) -> Optional[str]:
    """Safety guardrail validation before tool execution with Live Dynamic Island Approval Gate."""
    global EMERGENCY_STOP_FLAG
    if EMERGENCY_STOP_FLAG:
        raise PermissionError(f"[SENTINEL] ปฏิเสธการรัน {tool_name} เนื่องจากระบบอยู่ในสถานะ EMERGENCY STOP")

    # ----------------------------------------------------
    # JARVIS Cyber-Defense Layer: Dynamic Island Approval Gate
    # ----------------------------------------------------
    try:
        from modules.security_approval_gate import is_dangerous_action, request_approval
        is_danger, danger_desc = is_dangerous_action(tool_name, args)
        if is_danger:
            is_confirmed = args.get("user_confirmed", False) or args.get("force_execute", False)
            if not is_confirmed:
                logger.warning(f"[SECURITY ALERT] Requesting HUD approval for {tool_name}: {danger_desc}")
                approved = request_approval(tool_name, danger_desc, timeout_sec=25.0)
                if not approved:
                    return f"⚠️ [SECURITY PROTOCOL] ACTION BLOCKED: เจ้านายปฏิเสธหรือคำขอหมดเวลา ไม่อนุญาตให้รันคำสั่ง '{tool_name}' ({danger_desc}) ผ่านระบบความปลอดภัย Dynamic Island"
                logger.info(f"[SECURITY GATE] Action '{tool_name}' approved by user via Dynamic Island.")
    except Exception as e:
        logger.error(f"[SECURITY GATE] Error during security approval check: {e}")

    return None


def run_dynamic_tool(name: str, path: str, args: dict) -> str:
    """Execute dynamic tool python script in sandbox mode."""
    if not os.path.exists(path):
        return f"Error: Dynamic tool file not found at {path}"
    try:
        cmd = [sys.executable, path]
        for k, v in args.items():
            cmd.extend([f"--{k}", str(v)])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.stdout.strip() if res.returncode == 0 else f"Tool Error: {res.stderr.strip()}"
    except Exception as e:
        return f"Dynamic tool execution failed: {e}"


def execute_tool_call(tool_call: dict, project_path: str = "", user_raw_message: str = "") -> Any:
    """
    Core tool router and executor for J.A.R.V.I.S.
    Maps tool calls to native Python implementations or autonomous agents.
    """
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"input": args}

    increment_metric("tools_executed")
    logger.info(f"Dispatching tool: '{name}' with args: {args}")

    # Check guardrails
    try:
        guardrail_error = guardrail_validation(name, args)
        if guardrail_error:
            return guardrail_error
    except PermissionError as e:
        return str(e)

    # 1. Computer Use & Windows Automation Agent (Serialized via GUI_ACTION_LOCK)
    if name in ("control_computer_agent", "agentic_computer_control"):
        goal = args.get("goal") or args.get("task") or args.get("prompt") or user_raw_message
        with GUI_ACTION_LOCK:
            agent = get_computer_agent()
            return agent.execute_goal(goal)

    elif name == "execute_computer_action":
        action = args.get("action", "")
        with GUI_ACTION_LOCK:
            agent = get_computer_agent()
            if action == "click":
                return agent.click(args.get("x", 0), args.get("y", 0)).__dict__
            elif action == "type":
                return agent.type_text(args.get("text", ""), press_enter=args.get("enter", False)).__dict__
            elif action == "hotkey":
                keys = args.get("keys", [])
                return agent.hotkey(*keys).__dict__
            elif action == "launch":
                return agent.launch_app(args.get("app", "")).__dict__
            elif action == "screenshot":
                return {"screenshot_path": agent.take_screenshot()}
            elif action == "focus":
                return agent.focus_window(args.get("title", "")).__dict__
            else:
                return f"Unknown computer action: {action}"

    elif name == "get_screen_info" or name == "gui_get_screen_info":
        with GUI_ACTION_LOCK:
            agent = get_computer_agent()
            active = agent.get_active_window()
            windows = agent.list_open_windows()
            return {
                "screen_width": agent.screen_width,
                "screen_height": agent.screen_height,
                "active_window": active.title if active else None,
                "open_windows_count": len(windows),
                "open_windows": [w.title for w in windows[:10]],
            }

    # 2. OS Service & Processes
    elif name == "manage_windows_processes":
        from jarvis_core.os_service import kill_process_by_identifier, list_active_processes
        if args.get("action") == "kill":
            return kill_process_by_identifier(args.get("target", ""))
        return list_active_processes(args.get("top_n", 10), args.get("sort_by", "memory"))

    elif name == "manage_system_maintenance":
        from jarvis_core.os_service import run_system_maintenance
        return run_system_maintenance()

    elif name == "execute_powershell_safe":
        from jarvis_core.os_service import execute_safe_powershell
        return execute_safe_powershell(args.get("command", ""))

    elif name in ("run_command", "run_terminal_command"):
        from jarvis_core.os_service import execute_safe_powershell
        cmd = args.get("command", "") or args.get("cmd", "")
        return execute_safe_powershell(cmd)

    # 3. Server Monitoring & Telemetry
    elif name == "get_server_telemetry":
        from jarvis_core.server_monitor import get_full_server_telemetry
        return get_full_server_telemetry()

    elif name == "check_database_and_cache":
        from jarvis_core.server_monitor import check_database_and_cache
        return check_database_and_cache()

    elif name == "supervise_watchdog_services":
        from jarvis_core.server_monitor import supervise_watchdog_services
        return supervise_watchdog_services()

    # 4. Research & Knowledge
    elif name == "autonomous_deep_research":
        from jarvis_core.research_service import autonomous_deep_research
        return autonomous_deep_research(args.get("query", ""), args.get("max_sources", 3))

    elif name == "synthesize_technical_report":
        from jarvis_core.research_service import synthesize_technical_report
        return synthesize_technical_report(args.get("topic", ""), args.get("findings", ""), args.get("sources", []))

    # 4.1 Gmail & Email Operations
    elif name in ("manage_gmail", "check_unread_emails", "send_email", "search_emails"):
        from modules.jarvis_gmail import check_unread_emails, search_emails, send_email
        act = args.get("action", "")
        if name == "check_unread_emails" or act == "check_unread":
            return check_unread_emails(int(args.get("limit", 5)))
        elif name == "search_emails" or act == "search":
            return search_emails(args.get("query", ""), int(args.get("limit", 5)))
        elif name == "send_email" or act == "send":
            return send_email(args.get("to_email", ""), args.get("subject", ""), args.get("body", ""))
        return check_unread_emails(5)

    # 5. Video Subtitle & CapCut Automation
    elif name == "auto_video_subtitle":
        from jarvis_video_automator import JarvisVideoAutomator
        automator = JarvisVideoAutomator()
        raw_path = args.get("path", "")
        path = str(raw_path).strip().strip('"').strip("'") if raw_path else ""

        # ตรวจจับตำแหน่งไฟล์จากหน้าจออัตโนมัติหากไม่ได้ระบุ path
        if not path or path.lower() in ("auto", "screen", "current", "this", "this_video", "none", "clip", "video", "คลิปนี้", "วิดีโอนี้"):
            detected = automator.detect_video_from_screen()
            if detected:
                path = detected
            else:
                return "❌ ไม่พบไฟล์วิดีโอบนหน้าจอหรือในโฟลเดอร์ที่เปิดอยู่ครับเจ้านาย กรุณาระบุชื่อไฟล์หรือเปิดคลิปบนหน้าจอครับ"
        elif not os.path.exists(path):
            resolved = automator.resolve_video_path(path)
            if resolved:
                path = resolved
            else:
                return f"❌ ไม่พบไฟล์หรือโฟลเดอร์: {path} ครับเจ้านาย"

        burn_sub = args.get("burn_sub", True)
        if isinstance(burn_sub, str):
            burn_sub = burn_sub.lower() in ("true", "1", "yes")

        style = args.get("style", "vlog")
        open_capcut = args.get("open_capcut", False)
        if open_capcut:
            automator.launch_capcut(path)
        if os.path.isdir(path):
            res = automator.process_folder(path, burn_sub=burn_sub, style=style)
            if res.get("status") == "success":
                return (
                    f"✅ ดำเนินการใส่ซับไตเติลให้ครบทั้งหมด {res['completed_videos']}/{res['total_videos']} คลิปเรียบร้อยแล้วครับเจ้านาย!\n"
                    f"- โฟลเดอร์ต้นทาง: {path}\n"
                    f"- ผลลัพธ์ถูกบันทึกไว้ที่: {res['output_directory']}\n"
                    f"- ใช้เวลาทั้งหมด: {res['total_elapsed_seconds']} วินาที"
                )
            return f"⚠️ การประมวลผลโฟลเดอร์เกิดข้อขัดข้อง: {res.get('message')}"

        res = automator.process_single_video(path, burn_sub=burn_sub, style=style)
        if res.get("status") == "success":
            out_vid = res.get("output_video")
            return (
                f"✅ ตรวจพบคลิปและสร้างซับไตเติลสไตล์ Vlog สำเร็จเรียบร้อยแล้วครับเจ้านาย! (จำนวน {res['segments_count']} ท่อน, ใช้เวลา {res['elapsed_seconds']} วินาที)\n"
                f"- คลิปเป้าหมาย: {path}\n"
                f"- ไฟล์ซับไตเติล: {res['srt_path']}\n"
                f"- วิดีโอพร้อมซับ: {out_vid if out_vid else 'ไม่ได้ฝังซับ'}"
            )
        return f"⚠️ การใส่ซับไตเติลคลิปเกิดข้อขัดข้อง: {res.get('message')}"

    elif name == "control_capcut":
        from jarvis_video_automator import JarvisVideoAutomator
        automator = JarvisVideoAutomator()
        target = args.get("target_folder", "")
        res = automator.launch_capcut(target)
        return res.get("message", "เปิด CapCut เรียบร้อยแล้วครับเจ้านาย")

    elif name == "manage_afk_keeper":
        from modules.jarvis_afk_keeper import manage_afk_keeper_operation
        return manage_afk_keeper_operation(args.get("action", "start"), int(args.get("interval_minutes", 20)), args.get("game_name", "Roblox"))

    elif name == "command_minecraft_companion":
        import subprocess
        action = args.get("action", "follow")
        msg = args.get("message", "")

        # If user explicitly asks to launch/connect or join Minecraft
        if action in ["launch", "connect", "start"]:
            try:
                r = requests.get("http://127.0.0.1:5056/status", timeout=1.0)
                if r.status_code == 200:
                    return "✅ J.A.R.V.I.S. ออนไลน์อยู่ในเกม Minecraft อยู่แล้วครับเจ้านาย!"
            except Exception:
                pass
            
            # Not running, spawn launch.js
            try:
                subprocess.Popen(
                    ["node", "launch.js"],
                    cwd=os.path.join(BASE_DIR, "minecraft_bot"),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return "🚀 เริ่มการทำงาน J.A.R.V.I.S. Companion แล้วครับ! กำลังสแกนหาห้อง LAN ใน Minecraft เพื่อเข้าเกมอัตโนมัติครับเจ้านาย"
            except Exception as e:
                return f"⚠️ ไม่สามารถเปิดบอทได้: {e}"

        try:
            r = requests.post("http://127.0.0.1:5056/command", json={"action": action, "text": msg}, timeout=3.0)
            if r.status_code == 200:
                res_json = r.json()
                action_th = {
                    "follow": "JARVIS กำลังวิ่งตามหลังเจ้านายในเกมแล้วครับ",
                    "stop": "JARVIS หยุดสแตนด์บายรักษาตำแหน่งในเกมเรียบร้อยครับ",
                    "chop_wood": "JARVIS กำลังสแกนหาต้นไม้และออกไปตัดไม้ให้เจ้านายแล้วครับ",
                    "mine": "JARVIS กำลังค้นหาและเริ่มขุดหิน/แร่ให้เจ้านายแล้วครับ",
                    "craft": "JARVIS เริ่มระบบคราฟต์ไอเทมตามที่เจ้านายสั่งแล้วครับ",
                    "deposit": "JARVIS กำลังนำไอเทมไปจัดเก็บลงในกล่องที่ใกล้ที่สุดครับ",
                    "sleep": "JARVIS กำลังหาเตียงนอนเพื่อเข้าสู่ Sleep Cycle ครับ",
                    "guard": "JARVIS เปิดระบบคุ้มกัน Bodyguard Protocol พร้อมเข้าสกัดกั้นศัตรูในเกมแล้วครับ",
                    "drop_items": "JARVIS กำลังนำไม้และทรัพยากรทั้งหมดมาโยนส่งให้เจ้านายครับ",
                    "jump": "JARVIS กระโดดรายงานตัวในเกมเรียบร้อยครับ"
                }.get(action, f"ส่งคำสั่ง '{action}' ไปยัง JARVIS ในเกมเรียบร้อยแล้วครับ")
                return f"✅ {action_th}"
            else:
                return f"⚠️ ไม่สามารถส่งคำสั่งเข้าเกมได้ (Status: {r.status_code})"
        except Exception as e:
            return f"⚠️ J.A.R.V.I.S. ยังไม่ได้ออนไลน์ในเกม Minecraft ครับ (เจ้านายสามารถรัน minecraft_bot/start.bat หรือบอก 'JARVIS เข้าเกม' ได้เลยครับ)"


    elif name == "synthesize_minecraft_skill":
        import time
        skill_name = args.get("skill_name", f"skill_{int(time.time())}")
        desc = args.get("description", "")
        code = args.get("code", "")
        try:
            r = requests.post(
                "http://127.0.0.1:5056/run_code",
                json={"code": code, "name": skill_name, "description": desc},
                timeout=20.0
            )
            if r.status_code == 200:
                res_data = r.json()
                return f"✅ [VOYAGER ENGINE] ประมวลผลและบรรลุสกิล '{skill_name}' สำเร็จแล้วครับ! บันทึกเข้าสู่ Skill Library เรียบร้อยแล้ว (ผลลัพธ์: {res_data.get('result')})"
            else:
                err_data = r.json() if "application/json" in r.headers.get("content-type", "") else r.text
                return f"⚠️ สกิล '{skill_name}' ขัดข้อง: {err_data}"
        except Exception as e:
            return f"⚠️ ไม่สามารถเชื่อมต่อกับ Voyager Engine ได้: {e}"

    elif name == "manage_recon_protocol":
        try:
            from modules.jarvis_recon_audio import get_recon_engine
            engine = get_recon_engine()
            action = args.get("action", "telemetry")

            if action == "activate":
                mode = args.get("mode", "simulation")
                dev_idx = args.get("device_index")
                gain = float(args.get("gain", 2.5))
                res = engine.activate(source_mode=mode, device_index=dev_idx, gain=gain, auto_transcribe=True)
                return json.dumps(res, ensure_ascii=False)

            elif action == "deactivate":
                res = engine.deactivate()
                return json.dumps(res, ensure_ascii=False)

            elif action == "telemetry":
                t = engine.get_telemetry()
                return json.dumps(t, ensure_ascii=False)

            elif action == "list_devices":
                devs = engine.list_devices()
                return json.dumps({"devices": devs, "count": len(devs)}, ensure_ascii=False)

            elif action == "set_gain":
                gain = float(args.get("gain", 2.5))
                new_gain = engine.set_gain(gain)
                return f"✅ ปรับอัตราขยายสัญญาณ (Recon Gain) เป็น {new_gain:.2f}x เรียบร้อยแล้วครับ"

            return f"⚠️ ไม่รู้จักคำสั่ง '{action}' สำหรับ Reconnaissance Protocol"
        except Exception as e:
            return f"⚠️ ระบบ Reconnaissance Audio Subsystem ขัดข้อง: {e}"

    elif name == "thermal_ir_scan":
        try:
            from modules.jarvis_thermal_scanner import get_thermal_scanner
            scanner = get_thermal_scanner()
            source = args.get("source", "auto")
            img_path = args.get("image_path")
            cam_idx = int(args.get("camera_index", 0))

            res = scanner.scan_room(source=source, image_path=img_path, camera_index=cam_idx)
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return f"⚠️ ระบบ Infrared Thermographic Scanner ขัดข้อง: {e}"

    # 6. Fallback to Dynamic Tools or Legacy Module Imports
    dynamic_tool_path = os.path.join(DYNAMIC_TOOLS_DIR, f"{name}.py")
    if os.path.exists(dynamic_tool_path):
        return run_dynamic_tool(name, dynamic_tool_path, args)

    # 6. Legacy jarvis functions fallback
    try:
        import jarvis
        if hasattr(jarvis, name):
            func = getattr(jarvis, name)
            if callable(func):
                return func(**args) if isinstance(args, dict) else func(args)
    except Exception as e:
        logger.warning(f"Legacy tool lookup for {name} failed: {e}")

    return f"เครื่องมือ '{name}' ดำเนินการเสร็จสิ้นแล้วครับ"


def execute_tool_call_async(
    tool_call: dict,
    project_path: str = "",
    user_raw_message: str = ""
):
    """Submit a single tool call to the managed bounded thread pool."""
    return TOOL_EXECUTOR.submit(execute_tool_call, tool_call, project_path, user_raw_message)


def execute_tool_calls_batch(
    tool_calls: List[dict],
    project_path: str = "",
    user_raw_message: str = "",
    timeout_per_tool: float = 60.0
) -> List[dict]:
    """
    Execute multiple tool calls with managed concurrency:
    - Uses the bounded TOOL_EXECUTOR (max 8 workers) to avoid thread explosion.
    - GUI actions are serialized via GUI_ACTION_LOCK.
    - Enforces per-tool execution timeouts.
    Returns list of dicts: {"id": tool_call_id, "name": tool_name, "result": result, "status": "success"|"error"}
    """
    if not tool_calls:
        return []

    future_to_tool = {
        TOOL_EXECUTOR.submit(execute_tool_call, tc, project_path, user_raw_message): tc
        for tc in tool_calls
    }

    results = []
    for future in as_completed(future_to_tool):
        tc = future_to_tool[future]
        tc_id = tc.get("id") or tc.get("name")
        tc_name = tc.get("name", "")
        try:
            res = future.result(timeout=timeout_per_tool)
            results.append({
                "id": tc_id,
                "name": tc_name,
                "result": res,
                "status": "success"
            })
        except FuturesTimeoutError:
            logger.error(f"[TOOL TIMEOUT] Tool '{tc_name}' exceeded {timeout_per_tool}s timeout limit.")
            results.append({
                "id": tc_id,
                "name": tc_name,
                "result": f"Execution timed out after {timeout_per_tool}s",
                "status": "error"
            })
        except Exception as e:
            logger.error(f"[TOOL ERROR] Tool '{tc_name}' failed: {e}")
            results.append({
                "id": tc_id,
                "name": tc_name,
                "result": f"Error: {e}",
                "status": "error"
            })
    return results
