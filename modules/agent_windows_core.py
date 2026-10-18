import ast
import base64
import ctypes
import gc
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pyautogui
from dotenv import load_dotenv
from groq import Groq

class Config:
    def __init__(self):
        load_dotenv()
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.MODEL_NAME: str = os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile")
        self.SAFE_ZONE_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.DB_PATH: str = os.path.join(self.SAFE_ZONE_PATH, "data", "jarvis_memory.db")
        self.STATUS_FILE: str = os.path.join(self.SAFE_ZONE_PATH, "data", "os_agent_status.json")
        self.LOG_FILE: str = os.path.join(self.SAFE_ZONE_PATH, "reports", "agent_core.log")
        self.AUDIT_LOG_FILE: str = os.path.join(self.SAFE_ZONE_PATH, "audit_payload.log")
        self.VISION_MODEL: str = "llama-3.2-90b-vision-preview"

config = Config()

def setup_logging(log_file: str) -> logging.Logger:
    app_logger = logging.getLogger("WindowsAgent")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        app_logger.addHandler(file_handler)
        app_logger.addHandler(console_handler)
    return app_logger

logger = setup_logging(config.LOG_FILE)

class StatusReporter:
    def __init__(self, status_file: str):
        self.status_file = status_file
        self.status_callback: Optional[Callable[[str, str], None]] = None

    def write_status(self, status_msg: str, thought_msg: str = "") -> None:
        """[Cognitive Thought Stream HUD] Write dual-layer status for frontend telemetry."""
        if self.status_callback:
            self.status_callback(status_msg, thought_msg)
            return
            
        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status_msg,
                    "thought": thought_msg,
                    "timestamp": time.time()
                }, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Status Write Error: {e}")

reporter = StatusReporter(config.STATUS_FILE)

STATUS_CALLBACK = None
def write_agent_status(status_msg: str, thought_msg: str = "") -> None:
    reporter.status_callback = STATUS_CALLBACK
    reporter.write_status(status_msg, thought_msg)
    try:
        from jarvis_screen_takeover import start_screen_takeover, update_screen_takeover, stop_screen_takeover
        if status_msg and status_msg.strip():
            start_screen_takeover(status_msg.strip())
        else:
            stop_screen_takeover()
    except Exception:
        pass

class VisionEngine:
    def __init__(self, api_key: str, model: str, safe_zone_path: str):
        self.api_key = api_key
        self.model = model
        self.safe_zone_path = safe_zone_path

    def scan_screen(self, element_desc: str) -> Tuple[int, int]:
        """[Adaptive GUI Object Ingestion Matrix] Uses Llama Vision to find UI elements"""
        img_path = os.path.join(self.safe_zone_path, "temp_vision.jpg")
        try:
            pyautogui.screenshot(img_path)
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            if not self.api_key:
                logger.warning("GROQ_API_KEY missing, defaulting to screen center.")
                return pyautogui.size()[0] // 2, pyautogui.size()[1] // 2
                
            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Locate the UI element described as '{element_desc}'. The image is a computer screen screenshot. Return ONLY a JSON array with approximate [x, y] coordinates in pixels, e.g. [960, 540]"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                temperature=0.1
            )
            res_text = response.choices[0].message.content.strip() if response.choices else ""
            match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', res_text)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception as e:
            logger.error(f"Vision API Error: {e}")
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception as cleanup_err:
                    logger.debug(f"Ignored cleanup error: {cleanup_err}")
        
        sw, sh = pyautogui.size()
        return sw // 2, sh // 2

def scan_screen_with_llama_vision(element_desc: str) -> Tuple[int, int]:
    engine = VisionEngine(config.GROQ_API_KEY, config.VISION_MODEL, config.SAFE_ZONE_PATH)
    return engine.scan_screen(element_desc)

class SandboxExecutor:
    def __init__(self, safe_zone_path: str, audit_log_path: str):
        self.safe_zone_path = safe_zone_path
        self.audit_log_path = audit_log_path
        self.allowed_imports = {'pyautogui', 'subprocess', 'os', 'shutil', 'ctypes', 'time', 'math', 'gc', 'agent_windows_core', 'sys', 'traceback'}

    def validate_ast(self, code_block: str) -> Tuple[bool, str]:
        """Check if imports are safe."""
        try:
            tree = ast.parse(code_block)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_module = alias.name.split('.')[0]
                        if base_module not in self.allowed_imports:
                            return False, f"Unauthorized import: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    base_module = node.module.split('.')[0] if node.module else ""
                    if base_module not in self.allowed_imports:
                        return False, f"Unauthorized from-import: {node.module}"
            return True, "Valid"
        except Exception as e:
            return False, f"AST Parse Error: {e}"

    def get_secure_payload(self, code_block: str) -> str:
        """Wrap the code block with necessary safe imports and functions."""
        safety_header = (
            "import sys\n"
            "import os\n"
            "_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else os.getcwd()\n"
            "if _root not in sys.path: sys.path.insert(0, _root)\n"
            "_mods = os.path.join(_root, 'modules')\n"
            "if _mods not in sys.path: sys.path.insert(0, _mods)\n"
            "from agent_windows_core import scan_screen_with_llama_vision, write_agent_status\n"
            "import pyautogui\n"
            "import gc\n"
            "import subprocess\n"
            "pyautogui.FAILSAFE = False\n"
            "pyautogui.PAUSE = 0.1\n"
            "# [Virtual Desktop Integration Matrix] Hide spawned windows from main screen\n"
            "import ctypes\n"
            "def _hide_window_by_title(title_substr):\n"
            "    user32 = ctypes.windll.user32\n"
            "    def callback(hwnd, _):\n"
            "        length = user32.GetWindowTextLengthW(hwnd)\n"
            "        if length > 0:\n"
            "            buf = ctypes.create_unicode_buffer(length + 1)\n"
            "            user32.GetWindowTextW(hwnd, buf, length + 1)\n"
            "            if title_substr.lower() in buf.value.lower():\n"
            "                user32.ShowWindow(hwnd, 0)\n"
            "    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))\n"
            "    user32.EnumWindows(WNDENUMPROC(callback), 0)\n"
            "\n"
        )
        safety_footer = "\ngc.collect()\n"
        return safety_header + code_block + safety_footer

    def log_audit(self, payload: str, result_msg: str) -> None:
        """Write to audit log."""
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now()} ---\n")
                f.write(payload + "\n")
                f.write(f"Result: {result_msg}\n")
                f.write("-----------------------------\n")
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    def execute(self, code_block: str) -> Tuple[bool, str, str]:
        """Execute Python payload safely."""
        logger.info("Matrix Executing Python Payload (Sandbox Mode)...")
        
        is_valid, reason = self.validate_ast(code_block)
        if not is_valid:
            logger.warning(f"Sandbox Blocked Payload: {reason}")
            return False, "", f"Blocked by Sandbox: {reason}"

        secure_code_block = self.get_secure_payload(code_block)
        payload_path = os.path.join(self.safe_zone_path, "temp_payload.py")
        
        try:
            with open(payload_path, "w", encoding="utf-8") as f:
                f.write(secure_code_block)
        except Exception as e:
            return False, "", f"Failed to write payload: {e}"

        success = False
        stdout_str = ""
        stderr_str = ""
        
        try:
            result = subprocess.run(
                [sys.executable, payload_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            stdout_str = result.stdout
            stderr_str = result.stderr
            if result.returncode == 0:
                success = True
            else:
                logger.warning(f"Payload Exec Error (RC={result.returncode})")
        except subprocess.TimeoutExpired:
            stderr_str = "Execution timeout (15 seconds exceeded)."
            logger.warning("Payload Exec Timeout")
        except Exception as e:
            stderr_str = traceback.format_exc()
            logger.error(f"Payload System Error: {e}")
        finally:
            if os.path.exists(payload_path):
                try:
                    os.remove(payload_path)
                except Exception as e:
                    logger.debug(f"Payload cleanup error: {e}")

        result_msg = f"Success={success}\nSTDOUT:\n{stdout_str}\nSTDERR:\n{stderr_str}"
        self.log_audit(secure_code_block, result_msg)
        
        return success, stdout_str, stderr_str

class LLMProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = Groq(api_key=api_key.strip().strip('"').strip("'"))
        self.model_candidates = self._get_unique_candidates([
            config.MODEL_NAME,
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "mixtral-8x7b-32768"
        ])

    def _get_unique_candidates(self, candidates: List[str]) -> List[str]:
        seen = set()
        return [x for x in candidates if not (x in seen or seen.add(x))]

    def query(self, system_prompt: str, user_content: str) -> str:
        last_exception = None
        for candidate in self.model_candidates:
            for attempt in range(3):
                try:
                    response = self.client.chat.completions.create(
                        model=candidate,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.0,
                        timeout=30.0
                    )
                    logger.info(f"[SYSTEM DIAGNOSTIC] Connected successfully using model candidate: {candidate}")
                    return response.choices[0].message.content or ""
                except Exception as ret_err:
                    last_exception = ret_err
                    err_str = str(ret_err).lower()
                    if any(kw in err_str for kw in ["rate limit", "429", "timeout", "connection"]):
                        if attempt < 2:
                            sleep_time = 2 ** attempt
                            logger.warning(f"Groq API Retry ({attempt+1}/3) in {sleep_time}s on candidate {candidate} due to: {ret_err}")
                            time.sleep(sleep_time)
                            continue
                    break 
                    
            err_str = str(last_exception).lower()
            if any(kw in err_str for kw in ["not found", "404", "429", "quota", "limit", "timeout"]):
                logger.warning(f"[SYSTEM DIAGNOSTIC] Candidate model {candidate} failed. Trying next candidate...")
                continue
            else:
                if last_exception:
                    raise last_exception
        
        if last_exception:
            raise last_exception
        return ""

class TaskDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def poll_pending_task(self) -> Optional[Tuple[int, str, Optional[str]]]:
        """Returns (task_id, instruction, transaction_id) if available."""
        task_id, instruction, transaction_id = None, None, None
        
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                c = conn.cursor()
                try:
                    c.execute("SELECT id, task_description, transaction_id FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
                    task = c.fetchone()
                    if task:
                        task_id, instruction, transaction_id = task
                except sqlite3.OperationalError:
                    
                    c.execute("SELECT id, task_description FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
                    task = c.fetchone()
                    if task:
                        task_id, instruction = task[0], task[1]
                        transaction_id = None
                
                if task_id is not None:
                    c.execute("UPDATE tasks SET status = 'executing' WHERE id = ?", (task_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"Synaptic Link Read/Lock Error: {e}")
            return None
            
        if task_id is not None:
            return task_id, instruction, transaction_id
        return None

    def update_task_status(self, task_id: int, final_status: str, transaction_id: Optional[str] = None, output: Optional[str] = None) -> bool:
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                c = conn.cursor()
                
                try:
                    c.execute("UPDATE tasks SET status = ?, output = ? WHERE id = ?", (final_status, output, task_id))
                except sqlite3.OperationalError:
                    
                    c.execute("UPDATE tasks SET status = ? WHERE id = ?", (final_status, task_id))
                
                if final_status == "failed" and transaction_id:
                    logger.warning(f"Transaction {transaction_id} failed at step {task_id}. Cancelling remaining steps...")
                    c.execute("UPDATE tasks SET status = 'cancelled' WHERE transaction_id = ? AND status = 'pending'", (transaction_id,))
                
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Synaptic Link Write Status Error for Task {task_id}: {e}")
            return False

class WindowsAutonomousAgent:
    def __init__(self):
        logger.info("J.A.R.V.I.S. Windows Agent Synced (Production Optimized Core)")
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1
        self.executor = SandboxExecutor(config.SAFE_ZONE_PATH, config.AUDIT_LOG_FILE)
        self.llm = LLMProvider(config.GROQ_API_KEY)
        self.db = TaskDatabase(config.DB_PATH)

    def get_system_prompt(self) -> str:
        return (
            "You are J.A.R.V.I.S., the autonomous engineering agent of Nachapol Industries. Your primary objective is to execute system directives by generating precise, secure, and robust Python automation scripts.\n\n"
            "1. CORE OPERATING PRINCIPLES:\n"
            "   - Use 'pyautogui' for GUI interactions. **CRITICAL**: Use the pre-injected function `scan_screen_with_llama_vision(\"element description\")` (Adaptive GUI Object Ingestion Matrix) which uses Llama Vision to find dynamic UI elements (like logos, buttons, text) and returns a (x, y) tuple for clicking. Do NOT guess static screen coordinates.\n"
            "   - **Restricted Authentication Vault Bridge**: NEVER automate typing passwords manually. Launch browsers with the user's existing profile (e.g. `subprocess.Popen(['chrome.exe', '--profile-directory=Default', url])`) to inherit Session Cookies/Tokens.\n"
            "   - **[Cognitive Thought Stream HUD]**: You MUST call `write_agent_status(status_msg, thought_msg)` BEFORE every major action. The `status_msg` describes WHAT you are doing (e.g. 'Launching Chrome...'). The `thought_msg` describes WHY you chose this approach and what reasoning/condition you are evaluating (e.g. 'Scanning for DM button because the user wants to message Nont').\n"
            "   - **[Virtual Desktop Integration]**: Use `subprocess.CREATE_NO_WINDOW` flag when launching external processes. Use `_hide_window_by_title('window title')` (pre-injected) to hide spawned application windows from the main screen. The user must NOT be disturbed.\n"
            "   - Use 'subprocess' with Windows App Execution Aliases (e.g., `start chrome`, `code`, `notepad`) to launch external apps stably in the background.\n"
            "   - Use 'os/shutil' for file systems.\n"
            "   - All scripts MUST be wrapped in comprehensive 'try-except' blocks. Log all failures to stdout/stderr.\n"
            "   - Code must be modular, efficient, and follow PEP 8 standards.\n\n"
            "2. LOGIC & ERROR RECOVERY (The Self-Correction Protocol):\n"
            "   - You will receive directives accompanied by '[PREVIOUS_EXECUTION_ERROR]' (if any).\n"
            "   - If an error log is provided: Analyze the traceback, identify the specific logical flaw (e.g., FileNotFoundError, PermissionError, LogicError), and provide a corrected script that explicitly mitigates that flaw.\n"
            "   - Do not repeat a failed approach.\n\n"
            "3. SAFETY & INTEGRITY (Non-negotiable):\n"
            "   - Every directive must pass a safety audit.\n"
            "   - REJECT: Commands involving deletion of OS-critical files, unauthorized registry modification, or malicious code execution.\n"
            "   - ACTION: If a command is unsafe, respond ONLY with: 'ALERT: SAFETY PROTOCOL VIOLATION. COMMAND REJECTED.'\n\n"
            "4. RESPONSE ARCHITECTURE (Strict Format):\n"
            "   - Output ONLY in the following format:\n"
            "```python\n"
            "     [Your Python Code Here]\n"
            "```\n"
            "   - No preamble, no postscript, no conversational filler, and no markdown explanations.\n"
            "   - Keep comments within the code minimal, explaining only the 'why' for complex logic.\n\n"
            "5. ANTICIPATORY ENGINEERING:\n"
            "   - Verify path/file existence before operations.\n"
            "   - Optimize for runtime speed and system stability.\n"
            "   - If the task requires multiple steps, structure the script as a cohesive, transactional operation."
        )

    def run_cycle(self, instruction: str, previous_error: Optional[str] = None) -> Dict[str, Any]:
        """วิเคราะห์แกนคำสั่งและจำลองการทำงานบน Windows OS"""
        logger.info(f"Decoding Directive: {instruction}")
        
        user_content = f"Execute this directive: {instruction}"
        if previous_error:
            user_content += f"\n\n[PREVIOUS_EXECUTION_ERROR]:\n{previous_error}"

        try:
            raw_content = self.llm.query(self.get_system_prompt(), user_content)
            
            if "ALERT: SAFETY PROTOCOL VIOLATION" in raw_content:
                status = "REJECTED_UNSAFE"
                result = {"success": False, "output": raw_content}
            else:
                code_match = re.search(r"```python\s*(.*?)\s*```", raw_content, re.DOTALL)
                if code_match:
                    code_to_run = code_match.group(1)
                    success, stdout, stderr = self.executor.execute(code_to_run)
                    status = "SUCCESS" if success else "EXECUTION_ERROR"
                    result = {"success": success, "output": stdout if success else stderr}
                else:
                    status = "PARSING_ERROR"
                    result = {"success": False, "output": "Failed to extract execution payload from response."}
        except Exception as e:
            status = "API_ERROR"
            result = {"success": False, "output": str(e)}

        logger.info(f"[MISSION STATUS]: {status}")
        return result

    def poll_for_tasks(self) -> bool:
        """[NACHAPOL PROTOCOL OPTIMIZED] ตรวจสอบภารกิจใหม่พร้อมระบบคิวรีแบบคู่ขนานฐานข้อมูล"""
        task_data = self.db.poll_pending_task()
        if not task_data:
            return False
            
        task_id, instruction, transaction_id = task_data
        
        write_agent_status(f"Executing: {instruction}", f"Analyzing directive and compiling automation script for: {instruction}")
        res = self.run_cycle(instruction)
        
        if not res.get("success") and res.get("output") and "SAFETY PROTOCOL VIOLATION" not in res.get("output", ""):
            logger.warning(f"Execution failed. Initiating Self-Correction Protocol for Task {task_id}...")
            res = self.run_cycle(instruction, previous_error=res.get("output"))
        
        final_status = "completed" if res.get("success") else "failed"
        self.db.update_task_status(task_id, final_status, transaction_id, res.get("output"))
        
        write_agent_status("") 
        return True

if __name__ == "__main__":
    jarvis_agent = WindowsAutonomousAgent()
    while True:
        has_task = jarvis_agent.poll_for_tasks()
        if has_task:
            time.sleep(0.5)  
        else:
            time.sleep(2.0)  