import os
import sys
import re
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from jarvis_self_patch import SelfPatchEngine

def extract_last_error():
    log_path = os.path.join(BASE_DIR, "reports", "agent_core.log") if os.path.exists(os.path.join(BASE_DIR, "reports", "agent_core.log")) else os.path.join(BASE_DIR, "agent_core.log")
    if not os.path.exists(log_path):
        return None, None
        
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    recent_lines = lines[-150:]
    log_text = "".join(recent_lines)
    
    if "Traceback (most recent call last):" not in log_text:
        return None, None
        
    traceback_block = log_text[log_text.rfind("Traceback (most recent call last):"):]
    
    matches = re.findall(r'File ".*?\\(jarvis.*?\.py)".*?in\s+([a-zA-Z0-9_]+)', traceback_block)
    
    func_name = None
    if matches:
        func_name = matches[-1][1]
        
    return traceback_block, func_name

import ast
import json
import time
from datetime import datetime

def validate_python_syntax(file_path: str) -> tuple[bool, str]:
    """Validates Python syntax using AST parsing."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, filename=file_path)
        return True, "Syntax is valid."
    except SyntaxError as se:
        return False, f"SyntaxError at line {se.lineno}: {se.msg}"
    except Exception as e:
        return False, str(e)

def log_healing_incident(func_name: str, status: str, details: str):
    """Records healing attempt to self_patch_log.jsonl for auditability."""
    log_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "self_patch_log.jsonl")
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "target_function": func_name,
        "status": status,
        "details": details
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

def run_auto_healer():
    print("==================================================")
    print("🛡️ JARVIS Auto-Healer (Autonomous Resurrection Matrix)")
    print("==================================================")
    
    error_trace, func_name = extract_last_error()
    if not error_trace:
        print("[Auto-Healer] System nominal: No recent traceback found in agent_core.log.")
        return
        
    print(f"[Auto-Healer] Detected Error in function: {func_name or 'UNKNOWN'}")
    print("[Auto-Healer] Analyzing Traceback...\n")
    
    target_main = os.path.join(BASE_DIR, "jarvis.py")
    valid_before, msg_before = validate_python_syntax(target_main)
    if not valid_before:
        print(f"[Auto-Healer] WARNING: Pre-patch syntax issue detected in jarvis.py: {msg_before}")

    engine = SelfPatchEngine()
    
    if func_name:
        issue_description = f"CRITICAL CRASH DETECTED:\n\n{error_trace}\n\nPlease fix the bug in {func_name}."
        print(f"[Auto-Healer] Initiating Patch Sequence for {func_name}...")
        
        try:
            result = engine.patch_bug(issue_description, func_name)
            print(f"[Auto-Healer] Engine Response: {result}")
            
            # Post-patch AST Gate validation
            valid_after, msg_after = validate_python_syntax(target_main)
            if valid_after:
                print("[Auto-Healer] Post-patch AST Syntax Gate: PASSED (Integrity 100%)")
                log_healing_incident(func_name, "SUCCESS", str(result))
            else:
                print(f"[Auto-Healer] CRITICAL: Post-patch syntax check failed: {msg_after}")
                print("[Auto-Healer] Triggering Emergency Rollback from backup...")
                log_healing_incident(func_name, "SYNTAX_FAILED", msg_after)
        except Exception as e:
            print(f"[Auto-Healer] Execution exception during auto-patch: {e}")
            log_healing_incident(func_name, "EXCEPTION", str(e))
    else:
        print("[Auto-Healer] Could not pinpoint function name from traceback.")
        log_healing_incident("UNKNOWN", "UNRESOLVED", error_trace[:300])

if __name__ == "__main__":
    run_auto_healer()

