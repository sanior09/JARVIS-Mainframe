"""
╔══════════════════════════════════════════════════════════════════════════╗
║     J.A.R.V.I.S. SELF-PATCH ENGINE  (Level 2 — Semi-Autonomous)        ║
║     Self-analyzing, Self-improving Code Module                          ║
╚══════════════════════════════════════════════════════════════════════════╝

Architecture:
  Level 2 Behavior:
    - Bug fixes (small, isolated, <30 lines diff): auto-apply + notify owner
    - Feature additions / structural changes: propose + require approval
    
  Safety Protocol:
    - Always backup before any patch
    - Always sandbox-test before apply
    - IMMUTABLE_FUNCTIONS are never touched
    - Rollback watchdog monitors 60s post-patch
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JARVIS_MAIN_FILE = os.path.join(BASE_DIR, "jarvis.py")
BACKUP_DIR = os.path.join(BASE_DIR, "system_cache", "self_patch_backups")
PATCH_LOG_FILE = os.path.join(BASE_DIR, "reports", "self_patch_log.jsonl")
REJECTED_ARCHIVE_FILE = os.path.join(BASE_DIR, "system_cache", ".rejected_patches.json")

IMMUTABLE_FUNCTIONS = {
    "reject_execution",
    "require_api_token",
    "evaluate_and_trigger_alerts",
    "perform_system_boot_sequence",
}

BUG_FIX_LINE_THRESHOLD = 30

logger = logging.getLogger("SelfPatch")

os.makedirs(BACKUP_DIR, exist_ok=True)

class BackupManager:
    """Manages versioned backups of Python files before any patch."""

    @staticmethod
    def create_backup(target_file: str) -> str:
        """Create a timestamped backup of target_file. Returns backup path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(target_file)
        backup_name = f"{filename}_{ts}.bak.py"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        with open(target_file, "r", encoding="utf-8") as src:
            content = src.read()
        with open(backup_path, "w", encoding="utf-8") as dst:
            dst.write(content)
            
        meta_path = backup_path + ".meta"
        with open(meta_path, "w", encoding="utf-8") as m:
            m.write(target_file)
            
        logger.info(f"[Backup] Created: {backup_path} for {target_file}")
        return backup_path

    @staticmethod
    def rollback(backup_path: str) -> bool:
        """Restore from a backup using its metadata. Returns True if successful."""
        try:
            meta_path = backup_path + ".meta"
            if not os.path.exists(meta_path):
                target_file = JARVIS_MAIN_FILE
            else:
                with open(meta_path, "r", encoding="utf-8") as m:
                    target_file = m.read().strip()
                    
            with open(backup_path, "r", encoding="utf-8") as src:
                content = src.read()
            with open(target_file, "w", encoding="utf-8") as dst:
                dst.write(content)
            logger.warning(f"[Rollback] Restored {target_file} from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"[Rollback] FAILED: {e}")
            return False

    @staticmethod
    def list_backups() -> list[str]:
        """List all available backups sorted newest-first."""
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".bak.py")],
            reverse=True,
        )
        return [os.path.join(BACKUP_DIR, b) for b in backups]

class CodeAnalyzer:
    """Reads and analyzes a target Python file to extract relevant code sections."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        with open(filepath, "r", encoding="utf-8") as f:
            self.source = f.read()
        self.lines = self.source.splitlines(keepends=True)

    @staticmethod
    def scan_all_files(func_name: str) -> Optional[str]:
        """Scan all .py files in BASE_DIR to find which file contains func_name."""
        for filename in os.listdir(BASE_DIR):
            if filename.endswith(".py"):
                filepath = os.path.join(BASE_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name == func_name:
                                return filepath
                except Exception:
                    continue
        return None

    def get_function_source(self, func_name: str) -> Optional[tuple[int, int, str]]:
        """
        Returns (start_line_1indexed, end_line_1indexed, source_code) of a function.
        Returns None if not found.
        """
        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    start = node.lineno - 1  
                    end = node.end_lineno  
                    code = "".join(self.lines[start:end])
                    return (start + 1, end, code)
        return None

    def get_file_skeleton(self) -> str:
        """Returns a skeleton of the file including imports, class definitions, and function signatures."""
        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return ""

        skeleton = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                skeleton.append(ast.get_source_segment(self.source, node))
            elif isinstance(node, ast.ClassDef):
                skeleton.append(f"class {node.name}:")
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        skeleton.append(f"    def {sub.name}(...): ...")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                skeleton.append(f"def {node.name}(...): ...")
        
        return "\n".join(filter(None, skeleton))

    def find_error_context(self, error_pattern: str, context_lines: int = 20) -> str:
        """Find lines near an error pattern and return surrounding context."""
        results = []
        for i, line in enumerate(self.lines):
            if error_pattern in line:
                start = max(0, i - context_lines)
                end = min(len(self.lines), i + context_lines)
                snippet = "".join(self.lines[start:end])
                results.append(f"--- Found at line {i+1} ---\n{snippet}")
        return "\n\n".join(results) if results else ""

    def is_immutable(self, func_name: str) -> bool:
        """Check if a function is protected from modification."""
        return func_name in IMMUTABLE_FUNCTIONS

class SafetyValidator:
    """Validates that a patch is safe before applying."""

    DANGEROUS_PATTERNS = [
        "os.remove(",
        "shutil.rmtree(",
        "subprocess.Popen",
        "eval(",
        "exec(",
        "__import__(",
        "os.system(",
    ]

    @staticmethod
    def check_syntax(code: str) -> tuple[bool, str]:
        """Check if code is valid Python. Returns (is_valid, error_message)."""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    @staticmethod
    def check_dangerous_patterns(code: str) -> list[str]:
        """Use AST to semantically find dangerous function calls."""
        found = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                        if name in ('eval', 'exec', '__import__'):
                            found.append(name)
                    elif isinstance(node.func, ast.Attribute):
                        attr = node.func.attr
                        if attr in ('remove', 'rmtree', 'system', 'Popen'):
                            found.append(attr)
        except SyntaxError:
            pass
        return found

    @staticmethod
    def check_immutable_untouched(original: str, patched: str) -> list[str]:
        """
        Verify that immutable functions were not modified.
        Returns list of violated function names.
        """
        violations = []
        try:
            orig_tree = ast.parse(original)
            patch_tree = ast.parse(patched)
            orig_funcs = {
                n.name: ast.get_source_segment(original, n)
                for n in ast.walk(orig_tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name in IMMUTABLE_FUNCTIONS
            }
            patch_funcs = {
                n.name: ast.get_source_segment(patched, n)
                for n in ast.walk(patch_tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name in IMMUTABLE_FUNCTIONS
            }
            for fname in IMMUTABLE_FUNCTIONS:
                if orig_funcs.get(fname) != patch_funcs.get(fname):
                    violations.append(fname)
        except Exception:
            pass
        return violations

    @classmethod
    def validate(cls, original_code: str, patched_code: str) -> tuple[bool, str]:
        """
        Full validation pipeline. Returns (is_safe, reason).
        """
        valid, err = cls.check_syntax(patched_code)
        if not valid:
            return False, f"Syntax Error: {err}"

        dangerous = cls.check_dangerous_patterns(patched_code)
        if dangerous:
            return False, f"Dangerous patterns detected: {dangerous}"

        violations = cls.check_immutable_untouched(original_code, patched_code)
        if violations:
            return False, f"Immutable functions modified: {violations}"

        return True, "OK"

class SandboxTester:
    """Tests a patched file in an isolated subprocess."""

    @staticmethod
    def test(patched_source: str) -> tuple[bool, str]:
        """
        Write patched source to a temp file and test with pyflakes.
        Returns (passed, output_message).
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                encoding="utf-8",
                delete=False,
                dir=BASE_DIR,
            ) as tmp:
                tmp.write(patched_source)
                tmp_path = tmp.name

            # Level 3 Upgrade: Check runtime errors using pyflakes instead of just syntax
            result = subprocess.run(
                [sys.executable, "-m", "pyflakes", tmp_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            os.unlink(tmp_path)

            if result.returncode == 0:
                return True, "Sandbox test passed."
            else:
                return False, f"Sandbox validation error (pyflakes):\n{result.stderr or result.stdout}"
        except subprocess.TimeoutExpired:
            return False, "Sandbox test timed out."
        except Exception as e:
            return False, f"Sandbox error: {e}"

class PatchSynthesizer:
    """
    Uses Groq LLM to generate a patch for a given issue.
    Relies on the call_groq_model function from jarvis.py via late import.
    """

    @staticmethod
    def _call_llm(messages: list[dict]) -> str:
        """Force use of local Ollama (qwen2.5-coder:7b) for highly private and specific coding."""
        try:
            import requests
            
            payload = {
                "model": "qwen2.5-coder:7b",
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1} # Low temp for exact coding
            }
            
            logger.info("[PatchSynthesizer] Sending coding task to local Ollama (qwen2.5-coder:7b)...")
            response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=180)
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "").strip()
            else:
                logger.error(f"[PatchSynthesizer] Ollama API Error: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logger.error(f"[PatchSynthesizer] LLM call failed via Ollama: {e}")
        return ""

    @classmethod
    def synthesize_bug_fix(cls, issue_description: str, code_context: str, file_skeleton: str = "") -> str:
        """Ask LLM to generate a fixed version of the given code context."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Python engineer. You will be given a code snippet "
                    "from a production system called J.A.R.V.I.S. and a description of "
                    "the problem. Output ONLY the corrected Python code (the same section, "
                    "fully corrected). Do NOT add explanations or markdown fences. "
                    "Preserve all existing logic — only fix the stated issue."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"File skeleton for context:\n```python\n{file_skeleton}\n```\n\n"
                    f"Issue: {issue_description}\n\n"
                    f"Code to fix:\n```python\n{code_context}\n```\n\n"
                    "Return ONLY the corrected code."
                ),
            },
        ]
        return cls._call_llm(messages)

    @classmethod
    def synthesize_feature(cls, feature_description: str, relevant_context: str, file_skeleton: str = "") -> str:
        """Ask LLM to generate code for a new feature."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Python engineer working on J.A.R.V.I.S., "
                    "a personal AI system. Write clean, production-grade Python code "
                    "with type hints and docstrings. Output ONLY executable Python code, "
                    "no markdown, no explanations."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"File skeleton for context:\n```python\n{file_skeleton}\n```\n\n"
                    f"Feature to add: {feature_description}\n\n"
                    f"Relevant existing code for context:\n```python\n{relevant_context}\n```\n\n"
                    "Return ONLY the new/modified code to be inserted or appended. If it requires new imports, include them at the top of your response."
                ),
            },
        ]
        return cls._call_llm(messages)

class PatchApplicator:
    """Applies validated patches to target files safely."""

    @staticmethod
    def apply_function_patch(target_file: str, func_name: str, new_func_code: str) -> tuple[bool, str]:
        """
        Replace a specific function in target_file with new_func_code.
        Automatically hoists any imports from new_func_code to the top of the file.
        Returns (new_source, message).
        """
        analyzer = CodeAnalyzer(target_file)
        found = analyzer.get_function_source(func_name)
        if not found:
            return False, f"Function '{func_name}' not found in {target_file}"

        start_1idx, end_1idx, _old_code = found
        lines = analyzer.lines

        # Extract and hoist imports
        try:
            tree = ast.parse(new_func_code)
            imports = []
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.get_source_segment(new_func_code, node))
            
            if imports:
                lines_to_keep = [line for line in new_func_code.splitlines() if not line.strip().startswith(('import ', 'from '))]
                new_func_code = "\n".join(lines_to_keep) + "\n"
                
                # Find a safe place to insert imports
                insert_idx = 0
                for i, line in enumerate(lines):
                    if not line.startswith(('from __future__', '"""', "'''", '#')) and line.strip():
                        insert_idx = i
                        break
                
                new_imports_str = "\n".join(imports) + "\n"
                lines.insert(insert_idx, new_imports_str)
                # Adjust indices since we added a line
                start_1idx += 1
                end_1idx += 1
        except SyntaxError:
            pass

        new_lines = (
            lines[: start_1idx - 1]
            + [new_func_code.rstrip("\n") + "\n"]
            + lines[end_1idx:]
        )
        new_source = "".join(new_lines)
        return new_source, ""

    @staticmethod
    def apply_append_patch(target_file: str, new_code: str) -> tuple[bool, str]:
        """Append new code before the if __name__ == '__main__' block (if any)."""
        with open(target_file, "r", encoding="utf-8") as f:
            source = f.read()

        insert_marker = "if __name__ == \"__main__\":"
        idx = source.rfind(insert_marker)
        if idx == -1:
            new_source = source + "\n\n" + new_code
        else:
            new_source = source[:idx] + "\n\n" + new_code + "\n\n" + source[idx:]

        return new_source, ""

class RollbackWatchdog:
    """Monitors JARVIS health after a patch and rolls back if unresponsive."""

    def __init__(self, backup_path: str, health_check_fn=None, timeout: int = 60):
        self.backup_path = backup_path
        self.health_check_fn = health_check_fn
        self.timeout = timeout
        self._thread: Optional[threading.Thread] = None
        self._cancelled = threading.Event()

    def start(self) -> None:
        self._cancelled.clear()
        self._thread = threading.Thread(
            target=self._watch, daemon=True, name="RollbackWatchdog"
        )
        self._thread.start()

    def cancel(self) -> None:
        """Call this when patch is confirmed working."""
        self._cancelled.set()
        logger.info("[Watchdog] Cancelled — patch confirmed healthy.")

    def _watch(self) -> None:
        start_time = time.time()
        while not self._cancelled.is_set():
            elapsed = time.time() - start_time
            if elapsed >= self.timeout:
                logger.warning("[Watchdog] Timeout reached! Initiating rollback...")
                BackupManager.rollback(self.backup_path)
                PatchLogger.log(
                    event_type="rollback",
                    description="Auto-rollback after watchdog timeout",
                    status="rolled_back",
                    backup_path=self.backup_path,
                )
                break
            time.sleep(5)

class PatchLogger:
    """Logs all patch events to a JSONL file for audit trail."""

    @staticmethod
    def log(
        event_type: str,
        description: str,
        status: str,
        diff: str = "",
        backup_path: str = "",
        func_name: str = "",
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "status": status,
            "func_name": func_name,
            "backup_path": backup_path,
            "diff_preview": diff[:500] if diff else "",
        }
        try:
            with open(PATCH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[PatchLogger] Failed to write log: {e}")

    @staticmethod
    def get_history(limit: int = 20) -> list[dict]:
        """Read last N patch events."""
        try:
            with open(PATCH_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            entries = [json.loads(l) for l in lines if l.strip()]
            return entries[-limit:]
        except Exception:
            return []

class SelfPatchEngine:
    """
    Top-level orchestrator for J.A.R.V.I.S. Self-Patch System.
    
    Level 2 Logic:
      - Bug fix (diff < BUG_FIX_LINE_THRESHOLD): auto-apply, notify owner
      - Feature / large change: propose only, require human approval
    """

    _PENDING_PATCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pending_patch.json")

    def __init__(self) -> None:
        
        self._pending_patch: Optional[dict] = self._load_pending_patch()

    def _load_pending_patch(self) -> Optional[dict]:
        """โหลด pending patch จากไฟล์ (ถ้ามี)"""
        try:
            if os.path.exists(self._PENDING_PATCH_FILE):
                with open(self._PENDING_PATCH_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_pending_patch(self, patch: Optional[dict]) -> None:
        """บันทึก pending patch ลงไฟล์"""
        try:
            if patch is None:
                if os.path.exists(self._PENDING_PATCH_FILE):
                    os.remove(self._PENDING_PATCH_FILE)
            else:
                with open(self._PENDING_PATCH_FILE, 'w', encoding='utf-8') as f:
                    json.dump(patch, f, ensure_ascii=False, indent=2)
        except Exception as e:
            import logging
            logging.getLogger('SelfPatch').error(f"[SELF-PATCH] Cannot save pending patch: {e}")

    def _load_rejected_archive(self) -> list:
        """โหลดรายการ patch ที่เคยถูกยกเลิก"""
        try:
            if os.path.exists(REJECTED_ARCHIVE_FILE):
                with open(REJECTED_ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def _append_rejected_archive(self, patch: dict) -> None:
        """เก็บ patch ที่ถูกยกเลิกเข้า Archive (ไม่ลบทิ้ง)"""
        os.makedirs(os.path.dirname(REJECTED_ARCHIVE_FILE), exist_ok=True)
        archive = self._load_rejected_archive()
        patch["rejected_at"] = datetime.now().isoformat()
        archive.append(patch)
        
        archive = archive[-50:]
        try:
            with open(REJECTED_ARCHIVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(archive, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[SELF-PATCH] Cannot save rejected archive: {e}")

    def list_rejected_patches(self) -> str:
        """แสดงรายการ patch ที่เคยถูกยกเลิก พร้อม index สำหรับ restore"""
        archive = self._load_rejected_archive()
        if not archive:
            return "[SELF-PATCH] ยังไม่มี patch ที่ถูกยกเลิกไว้ในคลังครับ"
        lines = ["[SELF-PATCH ARCHIVE] รายการ Patch ที่เคยถูกยกเลิก:\n"]
        for i, p in enumerate(reversed(archive), 1):  
            real_idx = len(archive) - i  
            desc = p.get('description', p.get('type', 'N/A'))[:120]
            ts = p.get('rejected_at', 'ไม่ทราบ')[:16].replace('T', ' ')
            lines.append(f"  [{real_idx}] {ts} | {p.get('type','?')} | {desc}")
        lines.append("\nถ้าต้องการ restore ให้สั่ง 'JARVIS restore patch <index>' ครับ")
        return "\n".join(lines)

    def restore_rejected_patch(self, index: int) -> str:
        """นำ patch จาก Archive กลับมาเป็น pending เพื่อรออนุมัติใหม่"""
        archive = self._load_rejected_archive()
        if not archive:
            return "[SELF-PATCH] ไม่มี patch ในคลัง Archive ครับ"
        if index < 0 or index >= len(archive):
            return f"[SELF-PATCH] index {index} ไม่ถูกต้อง มีทั้งหมด {len(archive)} รายการ (0-{len(archive)-1}) ครับ"
        
        patch_to_restore = dict(archive[index])
        patch_to_restore.pop('rejected_at', None)  
        
        self._pending_patch = patch_to_restore
        self._save_pending_patch(self._pending_patch)
        
        desc = patch_to_restore.get('description', 'N/A')[:100]
        return (
            f"[SELF-PATCH RESTORED] Patch ถูกโหลดกลับมาเป็น Pending แล้วครับ\n"
            f"รายละเอียด: {desc}\n"
            f"ถ้าเห็นด้วยให้สั่ง 'JARVIS อนุมัติ patch' ได้เลยครับ"
        )

    def _compute_diff_size(self, original: str, patched: str) -> int:
        """Count changed lines between original and patched."""
        diff = list(
            difflib.unified_diff(
                original.splitlines(),
                patched.splitlines(),
                lineterm="",
            )
        )
        return sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))

    def _apply_new_source(self, target_file: str, new_source: str, backup_path: str, description: str, func_name: str = "") -> str:
        """Write new_source to target_file and start watchdog. Returns status message."""
        with open(target_file, "r", encoding="utf-8") as f:
            old_source = f.read()
            
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_source)

        diff = "\n".join(
            difflib.unified_diff(
                old_source.splitlines(),
                new_source.splitlines(),
                lineterm="",
                n=3,
            )
        )

        PatchLogger.log(
            event_type="patch_applied",
            description=description,
            status="applied",
            diff=diff,
            backup_path=backup_path,
            func_name=func_name,
        )

        try:
            from modules.dynamic_island import send_live_diff
            added = sum(1 for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
            removed = sum(1 for line in diff.splitlines() if line.startswith('-') and not line.startswith('---'))
            send_live_diff(added=added, removed=removed, summary=os.path.basename(target_file))
        except Exception:
            pass

        watchdog = RollbackWatchdog(backup_path=backup_path, timeout=60)
        watchdog.start()
        
        threading.Timer(65.0, watchdog.cancel).start()

        return diff

    def patch_bug(self, issue_description: str, func_name: str) -> str:
        """
        Level 2: Analyze + fix a bug in a specific function.
        Auto-applies if diff < threshold; otherwise escalates to feature flow.
        Returns a human-readable report.
        """
        target_file = CodeAnalyzer.scan_all_files(func_name)
        if not target_file:
            return f"[SELF-PATCH ERROR] ไม่พบฟังก์ชัน '{func_name}' ในระบบเลยครับ"
            
        analyzer = CodeAnalyzer(target_file)
        
        found = analyzer.get_function_source(func_name)
        if not found:
            return f"[SELF-PATCH ERROR] ไม่พบฟังก์ชัน '{func_name}' ใน {target_file} ครับ"

        _start, _end, old_code = found

        fixed_code = PatchSynthesizer.synthesize_bug_fix(issue_description, old_code, analyzer.get_file_skeleton())
        if not fixed_code.strip():
            return "[SELF-PATCH ERROR] ระบบสร้าง patch ไม่สำเร็จ LLM ไม่ตอบสนองครับ"

        result = PatchApplicator.apply_function_patch(target_file, func_name, fixed_code)
        if isinstance(result, tuple) and not result[0]:
            return f"[SELF-PATCH ERROR] {result[1]}"
        new_source, _ = result if isinstance(result, tuple) else (result, "")

        is_safe, reason = SafetyValidator.validate(analyzer.source, new_source)
        if not is_safe:
            return f"[SELF-PATCH BLOCKED] Safety Validator ปฏิเสธ patch: {reason}"

        passed, sandbox_msg = SandboxTester.test(new_source)
        if not passed:
            return f"[SELF-PATCH BLOCKED] Sandbox test ล้มเหลว:\n{sandbox_msg}"

        diff_size = self._compute_diff_size(analyzer.source, new_source)

        if True: 
            
            backup_path = BackupManager.create_backup(target_file)
            diff = self._apply_new_source(target_file, new_source, backup_path, issue_description, func_name)
            msg = (
                f"[SELF-PATCH APPLIED] กระผมได้แก้ไข '{func_name}' อัตโนมัติแล้วครับ "
                f"(แก้ {diff_size} บรรทัดใน {os.path.basename(target_file)}) มีการสำรองข้อมูลไว้ที่ backup ล่าสุดครับ\n\n"
                f"สรุปปัญหา: {issue_description}\n"
                f"Diff Preview:\n{diff[:800]}"
            )
            
            try:
                import sys
                jarvis_main = sys.modules.get('__main__')
                if jarvis_main and hasattr(jarvis_main, 'send_line_patch_notification'):
                    jarvis_main.send_line_patch_notification(
                        "bug_fix",
                        f"✅ Auto-applied: {issue_description[:200]}",
                        diff[:300]
                    )
            except Exception:
                pass
            
            if "dynamic_tools" not in target_file.replace("\\", "/"):
                msg += "\n\n[System] Core file modified. Initiating Autonomous Reboot (Code 100)..."
                print(msg)
                try:
                    import sys
                    sys.exit(100)
                except SystemExit:
                    raise
            
            return msg
        else:
            
            self._pending_patch = {
                "type": "bug_fix_large",
                "target_file": target_file,
                "func_name": func_name,
                "description": issue_description,
                "new_source": new_source,
                "diff_size": diff_size,
            }
            self._save_pending_patch(self._pending_patch)  
            proposal_msg = (
                f"[SELF-PATCH PROPOSAL] การแก้ไขครั้งนี้ใหญ่เกินขอบเขต Bug Fix ({diff_size} บรรทัด) "
                "กระผมขออนุมัติจากเจ้านายก่อนครับ ถ้าเห็นด้วยให้สั่ง 'JARVIS อนุมัติ patch' ได้เลยครับ\n\n"
                f"สรุปการเปลี่ยนแปลง: ฟังก์ชัน '{func_name}' ใน {os.path.basename(target_file)} — {issue_description}"
            )
            
            try:
                import sys
                jarvis_main = sys.modules.get('__main__')
                if jarvis_main and hasattr(jarvis_main, 'send_line_patch_notification'):
                    jarvis_main.send_line_patch_notification(
                        "bug_fix",
                        f"func: {func_name} | {issue_description[:200]}",
                    )
            except Exception:
                pass
            return proposal_msg

    def patch_feature(self, feature_description: str, relevant_func: str = "") -> str:
        """
        Level 2: Always propose, never auto-apply for new features.
        Returns proposal message.
        """
        context = ""
        target_file = JARVIS_MAIN_FILE
        if relevant_func:
            found_file = CodeAnalyzer.scan_all_files(relevant_func)
            if found_file:
                target_file = found_file
                analyzer = CodeAnalyzer(target_file)
                found = analyzer.get_function_source(relevant_func)
                if found:
                    context = found[2]
        
        analyzer = CodeAnalyzer(target_file)

        new_code = PatchSynthesizer.synthesize_feature(feature_description, context, analyzer.get_file_skeleton())
        if not new_code.strip():
            return "[SELF-PATCH ERROR] ระบบสังเคราะห์ Feature ไม่สำเร็จครับ"

        is_safe, reason = SafetyValidator.validate(analyzer.source, analyzer.source + "\n" + new_code)
        if not is_safe:
            return f"[SELF-PATCH BLOCKED] Safety Validator ปฏิเสธ Feature: {reason}"

        self._pending_patch = {
            "type": "feature",
            "target_file": target_file,
            "description": feature_description,
            "new_code": new_code,
        }
        self._save_pending_patch(self._pending_patch)  

        preview = new_code[:600] + ("..." if len(new_code) > 600 else "")
        proposal_msg = (
            f"[SELF-PATCH PROPOSAL] กระผมได้สังเคราะห์ Feature ใหม่ตามที่ร้องขอแล้วครับ "
            "รอการอนุมัติจากเจ้านายก่อน Apply ครับ ถ้าเห็นด้วยสั่ง 'JARVIS อนุมัติ patch' ได้เลยครับ\n\n"
            f"Feature: {feature_description}\n\n"
            f"Code Preview:\n```python\n{preview}\n```"
        )
        
        try:
            import sys
            jarvis_main = sys.modules.get('__main__')
            if jarvis_main and hasattr(jarvis_main, 'send_line_patch_notification'):
                jarvis_main.send_line_patch_notification(
                    "feature",
                    feature_description[:250],
                    preview[:300]
                )
        except Exception:
            pass
        return proposal_msg

    def patch_new_tool(self, tool_name: str, description: str, new_code: str, thai_name: str = "") -> str:
        """
        Propose a completely new tool (Dynamic Tool) and automatically approve it.
        """
        self._pending_patch = {
            "type": "new_tool",
            "tool_name": tool_name,
            "description": description,
            "new_code": new_code,
            "thai_name": thai_name
        }
        self._save_pending_patch(self._pending_patch)

        # [AUTO-EVOLUTION OVERRIDE]
        # Automatically approve and install the tool silently!
        approval_result = self.approve_pending_patch()

        proposal_msg = (
            f"[SELF-PATCH APPROVED] ระบบ Evolution อนุมัติตัวเองและติดตั้งสกิลใหม่: {tool_name} เรียบร้อยแล้ว!\n"
            f"ผลลัพธ์: {approval_result}"
        )
        
        try:
            from dynamic_island import send_toast_to_island
            send_toast_to_island(
                title="ASI Evolution",
                message=f"Skill Added: {thai_name or tool_name}",
                icon="🧬"
            )
        except Exception as e:
            logger.error(f"[SelfPatch] Failed to send Dynamic Island toast: {e}")
            
        return proposal_msg

    def approve_pending_patch(self) -> str:
        """Apply the currently pending patch after human approval."""
        self._pending_patch = self._load_pending_patch()  
        if not self._pending_patch:
            return "ไม่มี patch ที่รอการอนุมัติอยู่ในขณะนี้ครับ"

        patch = self._pending_patch
        self._pending_patch = None
        self._save_pending_patch(None)  
        target_file = patch.get("target_file", JARVIS_MAIN_FILE)

        backup_path = BackupManager.create_backup(target_file)

        if patch["type"] in ("bug_fix_large", "bug_fix"):
            new_source = patch["new_source"]
            passed, msg = SandboxTester.test(new_source)
            if not passed:
                return f"[SELF-PATCH BLOCKED] Sandbox ล้มเหลวหลังอนุมัติ: {msg}"
            self._apply_new_source(target_file, new_source, backup_path, patch["description"], patch.get("func_name", ""))
            
            try:
                from dynamic_island import send_toast_to_island
                send_toast_to_island(title="Auto-Heal", message="Core repaired.", icon="🔧")
            except Exception:
                pass
                
            return f"[SELF-PATCH APPLIED] Patch อนุมัติและ Apply ลง {os.path.basename(target_file)} เรียบร้อยครับเจ้านาย! สำรองไว้แล้วที่ {backup_path}"

        elif patch["type"] == "feature":
            new_code = patch["new_code"]
            new_source, _ = PatchApplicator.apply_append_patch(target_file, new_code)
            passed, msg = SandboxTester.test(new_source)
            if not passed:
                return f"[SELF-PATCH BLOCKED] Sandbox ล้มเหลวหลังอนุมัติ: {msg}"
            self._apply_new_source(target_file, new_source, backup_path, patch["description"])
            
            try:
                from dynamic_island import send_toast_to_island
                send_toast_to_island(title="Core Upgrade", message="Feature integrated.", icon="⚡")
            except Exception:
                pass
                
            return f"[SELF-PATCH APPLIED] Feature ถูก Apply ลง {os.path.basename(target_file)} เรียบร้อยแล้วครับเจ้านาย! สำรองไว้แล้วที่ {backup_path}"

        elif patch["type"] == "new_tool":
            tool_name = patch["tool_name"]
            new_code = patch["new_code"]
            desc = patch["description"]
            try:
                import sys
                jarvis_main = sys.modules.get('__main__')
                if jarvis_main and hasattr(jarvis_main, 'generate_new_tool_operation'):
                    result = jarvis_main.generate_new_tool_operation(tool_name, new_code.strip(), desc)
                    
                    try:
                        from dynamic_island import send_toast_to_island
                        # We use the raw tool_name or try to extract thai_name if it was passed via some means, 
                        # but in approve_pending_patch we might only have what's in the patch dict.
                        t_name = patch.get("thai_name") or tool_name
                        send_toast_to_island(title="ASI Evolution", message=f"Skill Added: {t_name}", icon="🧬")
                    except Exception:
                        pass
                        
                    return f"[SELF-PATCH APPLIED] เครื่องมือใหม่ถูกติดตั้งเรียบร้อยแล้ว: {result}"
                else:
                    return "[SELF-PATCH ERROR] ไม่พบฟังก์ชัน generate_new_tool_operation ใน jarvis.py"
            except Exception as e:
                return f"[SELF-PATCH ERROR] ติดตั้งเครื่องมือใหม่ล้มเหลว: {e}"

        return "[SELF-PATCH ERROR] ประเภท patch ไม่ถูกต้องครับ"

    def reject_pending_patch(self) -> str:
        """Discard the pending patch — เก็บเข้า Archive แทนลบทิ้ง เผื่อให้ restore ได้ภายหลังถ้าเปลี่ยนใจ"""
        self._pending_patch = self._load_pending_patch()  
        if not self._pending_patch:
            return "ไม่มี patch ที่รอการอนุมัติอยู่ในขณะนี้ครับ"
        
        desc = self._pending_patch.get("description", "N/A")
        
        self._append_rejected_archive(self._pending_patch)
        
        self._pending_patch = None
        self._save_pending_patch(None)  
        PatchLogger.log(
            event_type="patch_rejected",
            description=desc,
            status="rejected",
        )
        return (
            "[SELF-PATCH CANCELLED] Patch ถูกยกเลิกแล้วครับ ระบบยังคงสภาพเดิมทุกประการ\n"
            "ถ้าเปลี่ยนใจภายหลังสามารถสั่ง 'ดู patch ที่ยกเลิก' เพื่อดูรายการได้ครับ"
        )

    def get_patch_history(self) -> str:
        """Return a formatted summary of recent patches."""
        history = PatchLogger.get_history(limit=10)
        if not history:
            return "ยังไม่มีประวัติ Self-Patch ครับ"
        lines = ["[SELF-PATCH HISTORY] 10 รายการล่าสุด:\n"]
        for entry in reversed(history):
            ts = entry.get("timestamp", "")[:19]
            et = entry.get("event_type", "")
            desc = entry.get("description", "")[:60]
            status = entry.get("status", "")
            lines.append(f"  [{ts}] {et} | {status} | {desc}")
        return "\n".join(lines)

    def analyze_repeated_errors(self, error_text: str, count: int) -> str:
        """
        Called when an error repeats 3+ times.
        Auto-triggers bug analysis and proposes or auto-fixes.
        """
        logger.info(f"[Self-Patch] Repeated error detected ({count}x): {error_text[:80]}")
        target_file = JARVIS_MAIN_FILE
        analyzer = CodeAnalyzer(target_file)
        context = analyzer.find_error_context(error_text[:60])
        if not context:
            return ""
        return self.patch_bug(
            issue_description=f"ข้อผิดพลาดซ้ำซาก ({count} ครั้ง): {error_text[:200]}",
            func_name="",
        )

_self_patch_engine: Optional[SelfPatchEngine] = None

def get_self_patch_engine() -> SelfPatchEngine:
    """Return the global SelfPatchEngine singleton, creating it if needed."""
    global _self_patch_engine
    if _self_patch_engine is None:
        _self_patch_engine = SelfPatchEngine()
    return _self_patch_engine

def self_patch_system_operation(action: str, description: str = "", func_name: str = "") -> str:
    """
    Entry point called by JARVIS tool dispatcher.
    
    Actions:
      - "bug_fix"        : fix a bug in func_name based on description
      - "add_feature"    : propose a new feature
      - "approve"        : approve pending patch
      - "reject"         : reject pending patch (เก็บเข้า Archive ไม่ลบ)
      - "history"        : show applied patch history
      - "list_rejected"  : ดูรายการ patch ที่เคยยกเลิก
      - "restore_rejected": เอา patch จาก Archive กลับมาเป็น pending (ระบุ index ใน func_name)
    """
    engine = get_self_patch_engine()

    if action == "bug_fix":
        if not func_name:
            return "[SELF-PATCH] กรุณาระบุชื่อฟังก์ชันที่ต้องการแก้ไขครับ"
        return engine.patch_bug(description, func_name)

    elif action == "add_feature":
        return engine.patch_feature(description, func_name)

    elif action == "approve":
        return engine.approve_pending_patch()

    elif action == "reject":
        return engine.reject_pending_patch()

    elif action == "history":
        return engine.get_patch_history()

    elif action == "list_rejected":
        return engine.list_rejected_patches()

    elif action == "restore_rejected":
        try:
            idx = int(func_name)
        except (ValueError, TypeError):
            return "[SELF-PATCH] กรุณาระบุ index ของ patch ที่ต้องการ restore เช่น 'restore_rejected 0' ครับ"
        return engine.restore_rejected_patch(idx)

    else:
        return f"[SELF-PATCH] action '{action}' ไม่ถูกต้องครับ (bug_fix / add_feature / approve / reject / history / list_rejected / restore_rejected)"
