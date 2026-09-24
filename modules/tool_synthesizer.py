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
        Generates code for the requested tool and loads it into the runtime.
        """
        logger.info(f"Generating code for tool: {tool_name} (Objective: {objective})")
        
        # Simulated LLM code generation
        await asyncio.sleep(0.2)
        generated_code = f"""
def {tool_name}(*args, **kwargs):
    \"\"\"Autonomously generated tool for: {objective}\"\"\"
    return f"Executed {tool_name} successfully!"
"""
        
        if not self._verify_code_safety(generated_code):
            raise CodeGenerationError("Generated code failed safety verification.")
            
        file_path = os.path.join(self.tools_directory, f"{tool_name}.py")
        
        # Write code to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(generated_code)
            
        # Dynamically load the module
        logger.info(f"Registering module from {file_path}")
        spec = importlib.util.spec_from_file_location(tool_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[tool_name] = module
            spec.loader.exec_module(module)
            
            tool_function = getattr(module, tool_name)
            logger.info("การเพิ่ม Tool เสร็จสิ้น ระบบพร้อมใช้งานแล้วครับท่าน")
            return tool_function
        else:
            raise CodeGenerationError(f"Failed to load dynamically generated module: {tool_name}")


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
