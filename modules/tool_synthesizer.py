"""
tool_synthesizer.py
Module 1: Dynamic Tool Synthesizer

Responsible for Meta-Programming capabilities. Analyzes user intent,
detects missing capabilities, and autonomously generates and registers
new Python tools at runtime.
"""

import ast
import asyncio
import importlib.util
import logging
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

# Setup Module Logger
logger = logging.getLogger("ToolSynthesizer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class SynthesizerException(Exception):
    """Base exception for the Tool Synthesizer module."""
    pass


class CodeGenerationError(SynthesizerException):
    """Raised when generated code is invalid or unsafe."""
    pass


class IntentAnalyzer:
    """
    Analyzes user intent against the registry of currently available tools.
    """
    
    def __init__(self, available_tools: List[str]):
        self.available_tools = available_tools

    async def analyze_intent(self, user_command: str) -> Dict[str, Any]:
        """
        Determines if the system currently supports the requested command.
        """
        logger.info(f"Analyzing intent for command: '{user_command}'")
        
        # Simulated intent parsing logic
        # In a real system, this would use semantic search or an LLM
        needs_new_tool = False
        required_tool_name = ""
        
        if "เปิดพัดลม" in user_command and "fan_controller" not in self.available_tools:
            needs_new_tool = True
            required_tool_name = "fan_controller"
            
        if needs_new_tool:
            response_msg = "ตอนนี้ระบบของเรายังไม่มี Tool ครับ ผมกำลังเพิ่ม Tool ให้ครับท่าน"
            logger.warning(f"Missing Tool Detected: {required_tool_name}")
            return {
                "status": "MISSING_TOOL",
                "tool_name": required_tool_name,
                "reply_message": response_msg
            }
            
        return {
            "status": "TOOL_EXISTS",
            "reply_message": "ระบบมีเครื่องมือรองรับแล้วครับ"
        }


class DynamicCodeGenerator:
    """
    Autonomously generates Python code for new tools, verifies their safety using AST,
    and dynamically registers them into the runtime environment.
    """
    
    def __init__(self, tools_directory: str = "dynamic_tools"):
        self.tools_directory = tools_directory
        if not os.path.exists(self.tools_directory):
            os.makedirs(self.tools_directory)
            
    def _verify_code_safety(self, code: str) -> bool:
        """
        Statically analyzes the generated code to prevent malicious operations.
        (e.g., os.system, subprocess, open)
        """
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ['system', 'popen', 'remove', 'rmdir']:
                            logger.error(f"Unsafe attribute call detected: {node.func.attr}")
                            return False
                    elif isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec', 'open']:
                            logger.error(f"Unsafe function call detected: {node.func.id}")
                            return False
            return True
        except SyntaxError as e:
            logger.error(f"Generated code contains syntax errors: {e}")
            return False

    async def generate_and_register_tool(self, tool_name: str, objective: str) -> Callable:
        """
        Generates code and tests using Groq, runs Pytest in a loop, and registers upon success.
        """
        import re
        import subprocess
        from jarvis_core.ai_router import call_groq_model

        logger.info(f"🚀 [CI/CD] Initiating Autonomous Tool Synthesis for: {tool_name} (Objective: {objective})")
        
        system_prompt = (
            "You are JARVIS's internal Meta-Programmer. Your job is to write a Python tool and its Pytest. "
            "Output MUST contain exactly two code blocks:\n"
            "1. The tool code (must contain a function named exactly the requested tool_name)\n"
            "2. The pytest code (must test the function without needing external servers if possible, use mocks)\n"
            "Do NOT use markdown outside of the code blocks. Just provide the blocks."
        )
        
        history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write tool_name: '{tool_name}' for objective: '{objective}'. Also write a comprehensive pytest script for it."}
        ]
        
        max_retries = 3
        for attempt in range(max_retries):
            logger.info(f"🔄 [CI/CD] Synthesis Attempt {attempt + 1}/{max_retries}")
            
            # Use Groq to generate code
            response = call_groq_model(history, model="llama-3.3-70b-versatile")
            if "error_message" in response:
                raise CodeGenerationError(f"LLM API Error: {response['error_message']}")
                
            content = response.get("content", "")
            
            # Extract code blocks
            blocks = re.findall(r"```python\s*(.*?)\s*```", content, re.DOTALL)
            if len(blocks) < 2:
                # Fallback matching if they didn't specify 'python'
                blocks = re.findall(r"```(.*?)```", content, re.DOTALL)
                
            if len(blocks) < 2:
                history.append({"role": "assistant", "content": content})
                history.append({"role": "user", "content": "You must provide EXACTLY TWO Python code blocks (1: Tool, 2: Pytest). Try again."})
                continue
                
            tool_code = blocks[0].strip()
            if tool_code.startswith("python"): tool_code = tool_code[6:].strip()
            
            test_code = blocks[1].strip()
            if test_code.startswith("python"): test_code = test_code[6:].strip()
            
            if not self._verify_code_safety(tool_code):
                history.append({"role": "assistant", "content": content})
                history.append({"role": "user", "content": "The tool code failed AST safety checks (avoid os.system, exec, etc.). Try again safely."})
                continue

            # Write to Sandbox
            sandbox_dir = os.path.abspath(os.path.join(self.tools_directory, "sandbox"))
            os.makedirs(sandbox_dir, exist_ok=True)
            
            tool_path = os.path.join(sandbox_dir, f"{tool_name}.py")
            test_path = os.path.join(sandbox_dir, f"test_{tool_name}.py")
            
            with open(tool_path, 'w', encoding='utf-8') as f:
                f.write(tool_code)
            with open(test_path, 'w', encoding='utf-8') as f:
                # Inject sys.path so the test can import the tool
                f.write(f"import sys\nimport os\nsys.path.insert(0, r'{sandbox_dir}')\n\n" + test_code)
                
            # Run Pytest
            logger.info(f"🧪 [CI/CD] Running Pytest for {tool_name}...")
            result = subprocess.run([sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ [CI/CD] Pytest PASSED for {tool_name}! Deploying tool...")
                # Move to main dynamic tools
                final_tool_path = os.path.join(self.tools_directory, f"{tool_name}.py")
                # Handle Windows file replace by removing old one if exists
                if os.path.exists(final_tool_path): os.remove(final_tool_path)
                os.rename(tool_path, final_tool_path)
                
                # Cleanup Sandbox
                if os.path.exists(test_path): os.remove(test_path)
                
                # Load module
                spec = importlib.util.spec_from_file_location(tool_name, final_tool_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[tool_name] = module
                    spec.loader.exec_module(module)
                    tool_function = getattr(module, tool_name)
                    logger.info("🎉 การเพิ่ม Tool เสร็จสิ้น ระบบพร้อมใช้งานแล้วครับท่าน")
                    return tool_function
                else:
                    raise CodeGenerationError("Module load failed after tests passed.")
                    
            else:
                logger.warning(f"❌ [CI/CD] Pytest FAILED for {tool_name}. Feeding error back to AI for self-healing.")
                history.append({"role": "assistant", "content": content})
                error_feedback = f"The pytest failed with this output:\n{result.stdout}\n{result.stderr}\nAnalyze the error, fix the code, and try again."
                history.append({"role": "user", "content": error_feedback})
                
        raise CodeGenerationError("Tool generation failed after maximum CI/CD retries.")


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing Dynamic Tool Synthesizer ---")
        
        # 1. Intent Analysis
        analyzer = IntentAnalyzer(available_tools=["capture_screen", "toggle_guard_mode"])
        intent_result = await analyzer.analyze_intent("จาร์วิส ช่วยเปิดพัดลมหน่อย")
        
        logger.info(f"J.A.R.V.I.S. Reply: {intent_result.get('reply_message')}")
        
        if intent_result.get("status") == "MISSING_TOOL":
            tool_to_build = intent_result["tool_name"]
            
            # 2. Dynamic Generation
            generator = DynamicCodeGenerator(tools_directory="temp_tools")
            try:
                new_tool_func = await generator.generate_and_register_tool(
                    tool_name=tool_to_build,
                    objective="Control local fan hardware via GPIO"
                )
                
                # Execute the newly generated tool
                result = new_tool_func()
                logger.info(f"Test Execution Result: {result}")
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
                
            finally:
                # Cleanup
                import shutil
                if os.path.exists("temp_tools"):
                    shutil.rmtree("temp_tools")

    asyncio.run(run_tests())
