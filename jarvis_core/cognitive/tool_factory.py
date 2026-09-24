"""
jarvis_core/cognitive/tool_factory.py
─────────────────────────────────────────────────────
Autonomous Tool Factory for J.A.R.V.I.S.
Synthesizes, Sandbox-Tests, and Hot-Reloads new AI Tools.
"""

import ast
import logging
import os
import subprocess
from typing import Dict, Any

logger = logging.getLogger("JARVIS.ToolFactory")

class SandboxValidator:
    @staticmethod
    def validate_ast(code: str) -> bool:
        """
        Check if the code contains dangerous operations like os.remove
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.error(f"[ToolFactory] SyntaxError in generated code: {e}")
            return False
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['remove', 'rmdir', 'unlink']:
                        logger.error(f"[ToolFactory] Security violation: Found '{node.func.attr}' call.")
                        return False
        return True

    @staticmethod
    def run_unit_tests(code: str, test_code: str) -> bool:
        """
        Write the code and tests to a temporary file and run it in a subprocess.
        """
        test_file_path = "c:/JARVIS/scratch/temp_tool_test.py"
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        
        full_code = f"{code}\n\n{test_code}"
        
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(full_code)
            
        try:
            result = subprocess.run(
                ["python", test_file_path], 
                capture_output=True, 
                text=True, 
                timeout=5.0
            )
            if result.returncode == 0:
                logger.info("[ToolFactory] Sandbox testing passed.")
                return True
            else:
                logger.error(f"[ToolFactory] Sandbox testing failed:\n{result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("[ToolFactory] Sandbox testing timed out (5s).")
            return False
        except Exception as e:
            logger.error(f"[ToolFactory] Sandbox error: {e}")
            return False
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

class RuntimeHotReloader:
    def __init__(self, tools_dir="c:/JARVIS/dynamic_tools"):
        self.tools_dir = tools_dir
        os.makedirs(self.tools_dir, exist_ok=True)
        init_file = os.path.join(self.tools_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")

    def reload_tool(self, tool_name: str, code: str) -> bool:
        """
        Write the tool to the dynamic_tools directory.
        """
        file_path = os.path.join(self.tools_dir, f"{tool_name}.py")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"🧪 [ToolFactory] Hot-reloaded tool '{tool_name}' at {file_path}")
            return True
        except Exception as e:
            logger.error(f"[ToolFactory] Failed to write tool '{tool_name}': {e}")
            return False

class ToolSynthesizer:
    def __init__(self):
        self.sandbox = SandboxValidator()
        self.reloader = RuntimeHotReloader()

    def create_tool(self, tool_name: str, objective: str, code: str, test_code: str) -> bool:
        """
        Validate, test, and hot-reload a new tool.
        """
        logger.info(f"🧪 [ToolFactory] Synthesizing new tool: {tool_name}")
        
        if not self.sandbox.validate_ast(code):
            logger.error("[ToolFactory] Tool failed AST Security Validation.")
            return False
            
        if not self.sandbox.run_unit_tests(code, test_code):
            logger.error("[ToolFactory] Tool failed Sandbox Unit Testing.")
            return False
            
        if self.reloader.reload_tool(tool_name, code):
            logger.info(f"🧪 [ToolFactory] Tool '{tool_name}' successfully synthesized and deployed.")
            return True
            
        return False
