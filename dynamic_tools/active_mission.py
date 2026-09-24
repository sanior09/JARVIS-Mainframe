"""
J.A.R.V.I.S. Deep Autonomous Mission Loop (The Limitless Engine)
================================================================
This module allows JARVIS to take a high-level goal and run continuously
in an autonomous loop (Plan -> Execute -> Evaluate -> Re-plan) until the
goal is completed or max iterations are reached.
"""

import time
import json
import logging
from typing import List, Dict

logger = logging.getLogger("ActiveMission")

# This is a simplified representation of the Autonomous Agent loop.
class AutonomousAgent:
    def __init__(self, core_engine_callback, max_iterations=20):
        """
        core_engine_callback: A function that takes (messages, tools) and returns the LLM response.
        """
        self.core_engine = core_engine_callback
        self.max_iterations = max_iterations
        self.memory: List[Dict] = []
        
    def execute_mission(self, goal: str, available_tools: list) -> str:
        logger.info(f"[MISSION START] Goal: {goal}")
        
        system_prompt = (
            "คุณอยู่ในโหมด 100% Autonomous (Limitless Mode) ของ J.A.R.V.I.S.\n"
            f"เป้าหมายหลักของคุณคือ: '{goal}'\n\n"
            "กฎเหล็ก:\n"
            "1. คุณต้องลงมือทำผ่าน Tools ที่มีให้ทีละขั้นตอน (เช่น code_interpreter, universal_browser_agent, etc.)\n"
            "2. หลังจากการทำงานของ Tool เสร็จสิ้น คุณจะต้องประเมินว่างานเสร็จหรือยัง\n"
            "3. หากยังไม่เสร็จ ให้ใช้ Tool ทำขั้นตอนต่อไป\n"
            "4. หากเสร็จสมบูรณ์ 100% ให้ตอบกลับพร้อมคำว่า 'MISSION_ACCOMPLISHED' และสรุปผลลัพธ์\n"
            "5. หากเจอทางตันที่ไม่สามารถแก้ได้ ให้ตอบว่า 'MISSION_FAILED' พร้อมเหตุผล\n"
        )
        
        self.memory = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "เริ่มต้นทำงานได้เลย วิเคราะห์สถานการณ์และเรียกใช้ Tool แรกที่จำเป็น"}
        ]
        
        # We need to import the tool executor
        from jarvis import execute_tool_call
        
        for iteration in range(self.max_iterations):
            logger.info(f"[MISSION ITERATION {iteration + 1}/{self.max_iterations}]")
            
            try:
                response = self.core_engine(self.memory, tools=available_tools)
                
                # Check if there's a tool call
                if response and response.get("tool_calls"):
                    # Append the assistant's request to memory
                    self.memory.append({"role": "assistant", "tool_calls": response["tool_calls"]})
                    
                    for tool_call in response["tool_calls"]:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        logger.info(f"-> Agent invokes: {func_name}")
                        
                        tool_result = execute_tool_call({"name": func_name, "args": args}, project_path="c:/JARVIS", user_raw_message=goal)
                        
                        # Add tool result to memory
                        self.memory.append({
                            "role": "tool",
                            "name": func_name,
                            "content": str(tool_result),
                            "tool_call_id": tool_call.id if hasattr(tool_call, "id") else "unknown"
                        })
                else:
                    text_response = response.get("content", "").strip()
                    logger.info(f"-> Agent says: {text_response}")
                    self.memory.append({"role": "assistant", "content": text_response})
                    
                    if "MISSION_ACCOMPLISHED" in text_response:
                        return f"ภารกิจเสร็จสิ้น (สำเร็จ): {text_response}"
                    elif "MISSION_FAILED" in text_response:
                        return f"ภารกิจล้มเหลว: {text_response}"
                    
                    # If the agent didn't use a tool and didn't conclude, push it to continue
                    self.memory.append({"role": "user", "content": "คุณยังทำงานไม่เสร็จและไม่ได้เรียก Tool กรุณาดำเนินการต่อ หรือตอบ MISSION_ACCOMPLISHED ถ้าเสร็จแล้ว"})
                    
            except Exception as e:
                logger.error(f"Mission loop error: {e}")
                return f"เกิดข้อผิดพลาดระหว่างปฏิบัติภารกิจ: {e}"
                
        return "ภารกิจถูกยกเลิก (เกินโควต้าการทำงาน Max Iterations)"

# We expose a dynamic tool so the orchestrator can trigger this mission loop.
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "start_autonomous_mission",
        "description": "เริ่มต้นโหมดปฏิบัติการแบบ 100% Autonomous (AutoGPT) ให้ Jarvis ทำงานที่ซับซ้อนและมีหลายขั้นตอนโดยอัตโนมัติข้ามคืน ใช้คำสั่งนี้เมื่อผู้ใช้สั่งให้ทำงานสเกลใหญ่ เช่น 'สร้างแอป', 'วิจัยเรื่อง X และเขียนรายงาน', 'จัดการอีเมลทั้งหมด'",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "เป้าหมายหลักที่ต้องทำให้สำเร็จ อธิบายให้ละเอียดที่สุด"
                }
            },
            "required": ["goal"]
        }
    }
}

def start_autonomous_mission(args: dict) -> str:
    goal = args.get("goal")
    if not goal:
        return "ไม่มีเป้าหมาย"
        
    from jarvis import call_nachapol_core, TOOLS_DEFINITION
    
    agent = AutonomousAgent(core_engine_callback=call_nachapol_core, max_iterations=15)
    
    # Run synchronously for now. In a full system, this could be dispatched to a background thread
    # and return "Mission started in background" to the user.
    result = agent.execute_mission(goal, available_tools=TOOLS_DEFINITION)
    return result
