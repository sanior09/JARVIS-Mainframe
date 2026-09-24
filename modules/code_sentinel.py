"""
code_sentinel.py
Module 2: Isolated Sandbox & AST Architecture Sentinel

Responsible for safely executing untrusted code in a sandboxed environment
and statically analyzing/refactoring Python code using Abstract Syntax Trees (AST).
"""

import ast
import asyncio
import logging
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any, List, Optional

# Setup Module Logger
logger = logging.getLogger("CodeSentinel")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class SentinelException(Exception):
    """Base exception for the Sentinel module."""
    pass


class SandboxTimeoutError(SentinelException):
    """Raised when the sandbox execution exceeds the allowed time limit."""
    pass


class SecurityViolationError(SentinelException):
    """Raised when forbidden modules or operations are detected."""
    pass


class IsolatedCodeSandbox:
    """
    Executes Python code in an isolated subprocess.
    In a real production environment, this might use Docker or Windows Job Objects (psutil constraints).
    """
    
    def __init__(self, timeout_seconds: int = 5, max_memory_mb: int = 128):
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        # Note: True memory limiting on Windows via pure Python is complex.
        # We simulate limits and focus on Timeout and Subprocess isolation.

    async def execute(self, code: str) -> Dict[str, Any]:
        """
        Executes the provided code snippet asynchronously in a safe subprocess.
        """
        logger.info("Preparing isolated sandbox for code execution...")
        
        # Write code to a temporary file
        fd, tmp_path = tempfile.mkstemp(suffix=".py", text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Using asyncio.create_subprocess_exec to run it
            process = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                logger.warning("Code execution timed out!")
                raise SandboxTimeoutError(f"Execution exceeded the {self.timeout_seconds}s limit.")
            
            return {
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8').strip(),
                "stderr": stderr.decode('utf-8').strip(),
                "status": "SUCCESS" if process.returncode == 0 else "ERROR"
            }
            
        finally:
            # Cleanup temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class ASTStructuralReformer(ast.NodeVisitor):
    """
    Uses Python's abstract syntax tree to scan code for anti-patterns and code smells.
    Can be expanded to automatically refactor structures (e.g., separating logic/data).
    """
    
    def __init__(self):
        self.anti_patterns_found: List[str] = []
        
    def scan_code(self, code: str) -> List[str]:
        """Parses the code into an AST and visits the nodes."""
        self.anti_patterns_found.clear()
        try:
            tree = ast.parse(code)
            self.visit(tree)
            return self.anti_patterns_found
        except SyntaxError as e:
            logger.error(f"Syntax Error during AST scan: {e}")
            return [f"SyntaxError: {e}"]

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Detect bare 'except:' which is considered an anti-pattern."""
        if node.type is None:
            self.anti_patterns_found.append(f"Line {node.lineno}: Bare except detected. Use specific Exceptions.")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            # Although catching Exception is sometimes needed, it's a smell if not logged.
            self.anti_patterns_found.append(f"Line {node.lineno}: Catching broad Exception detected.")
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Detect functions that are too long (e.g., > 50 lines) or lack docstrings."""
        if not ast.get_docstring(node):
            self.anti_patterns_found.append(f"Line {node.lineno}: Function '{node.name}' lacks a docstring.")
            
        # Check function length (heuristic)
        if hasattr(node, 'end_lineno') and node.end_lineno and node.lineno:
            func_length = node.end_lineno - node.lineno
            if func_length > 50:
                self.anti_patterns_found.append(f"Line {node.lineno}: Function '{node.name}' is too long ({func_length} lines). Consider refactoring.")
                
        self.generic_visit(node)
        
    def visit_Global(self, node: ast.Global):
        """Detect the use of the 'global' keyword (often bad practice in clean architecture)."""
        self.anti_patterns_found.append(f"Line {node.lineno}: Usage of 'global' keyword detected ({', '.join(node.names)}). Violates pure function principles.")
        self.generic_visit(node)


if __name__ == "__main__":
    
    async def run_tests():
        logger.info("--- Testing ASTStructuralReformer ---")
        dirty_code = """
def process_data(data):
    global processed_count
    try:
        processed_count += 1
        return data * 2
    except:
        pass
"""
        reformer = ASTStructuralReformer()
        issues = reformer.scan_code(dirty_code)
        logger.info("Issues detected in dirty_code:")
        for issue in issues:
            logger.warning(f" - {issue}")
            
        logger.info("\n--- Testing IsolatedCodeSandbox ---")
        sandbox = IsolatedCodeSandbox(timeout_seconds=2)
        
        good_code = "print('Hello from isolated sandbox!')"
        infinite_loop_code = "while True: pass"
        
        try:
            result = await sandbox.execute(good_code)
            logger.info(f"Good Code Result: {result}")
        except Exception as e:
            logger.error(f"Sandbox failed: {e}")
            
        try:
            logger.info("Running infinite loop code to test timeout...")
            await sandbox.execute(infinite_loop_code)
        except SandboxTimeoutError as e:
            logger.info(f"Successfully caught timeout: {e}")

    asyncio.run(run_tests())
