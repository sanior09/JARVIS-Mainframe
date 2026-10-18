import os
import json
import logging
import subprocess
import logging
from typing import Annotated, Sequence
from typing_extensions import TypedDict
import operator
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langgraph.graph import StateGraph, END
    import google.generativeai as genai
except ImportError:
    pass

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tech_spec: str
    code: str
    qa_feedback: str
    iterations: int

def run_architect(state: AgentState):
    logger.info("[SWARM] Architect Agent is designing tech spec...")
    user_req = state['messages'][0].content
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    model = genai.GenerativeModel(model_name)
    prompt = f"คุณคือ Architect Agent ออกแบบโครงสร้าง (Tech Spec) สั้นๆ สำหรับโปรเจกต์นี้:\n{user_req}"
    resp = model.generate_content(prompt)
    return {"tech_spec": resp.text, "iterations": state.get('iterations', 0)}

def run_coder(state: AgentState):
    logger.info("[SWARM] Coder Agent is writing code...")
    tech_spec = state.get('tech_spec', '')
    qa_feedback = state.get('qa_feedback', '')
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    model = genai.GenerativeModel(model_name)
    prompt = f"คุณคือ Coder Agent เขียนโค้ด Python จาก Tech Spec นี้:\n{tech_spec}\n"
    if qa_feedback:
        prompt += f"\nแก้ไขข้อผิดพลาดตาม QA Feedback นี้:\n{qa_feedback}"
    resp = model.generate_content(prompt)
    
    # Extract code from markdown blocks
    code = resp.text
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
        
    # [AUTONOMOUS UPGRADE] Write code to disk
    workspace_dir = "C:/JARVIS/swarm_workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    file_path = os.path.join(workspace_dir, "app_generated.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    return {"code": code}

def run_qa(state: AgentState):
    logger.info("[SWARM] QA Agent is testing the code execution...")
    code = state.get('code', '')
    
    file_path = "C:/JARVIS/swarm_workspace/app_generated.py"
    feedback = ""
    is_pass = False
    
    # [AUTONOMOUS UPGRADE] Execute the code using subprocess
    try:
        result = subprocess.run(["python", file_path], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            feedback = "PASS. Code executed successfully without errors.\nOutput:\n" + result.stdout
            is_pass = True
        else:
            feedback = f"FAILED. Code threw an exception:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        feedback = "FAILED. Code execution timed out (possible infinite loop)."
    except Exception as e:
        feedback = f"FAILED. System error running code: {e}"
        
    logger.info(f"QA Feedback: {feedback[:100]}...")
    return {"qa_feedback": feedback, "iterations": state.get('iterations', 0) + 1}

def qa_router(state: AgentState):
    feedback = state.get('qa_feedback', '')
    iters = state.get('iterations', 0)
    # limit increased to 5 for autonomous execution
    if "PASS" in feedback or iters >= 5:
        return "end"
    return "coder"

def create_swarm():
    workflow = StateGraph(AgentState) # type: ignore
    
    workflow.add_node("architect", run_architect)
    workflow.add_node("coder", run_coder)
    workflow.add_node("qa", run_qa)
    
    workflow.set_entry_point("architect")
    workflow.add_edge("architect", "coder")
    workflow.add_edge("coder", "qa")
    workflow.add_conditional_edges(
        "qa",
        qa_router,
        {
            "coder": "coder",
            "end": END
        }
    )
    
    return workflow.compile()

def swarm_develop_project(project_description: str):
    logger.info(f"Starting Swarm for project: {project_description}")
    app = create_swarm()
    initial_state = {"messages": [HumanMessage(content=project_description)], "iterations": 0}
    result = app.invoke(initial_state)
    
    final_code = result.get('code', '')
    tech_spec = result.get('tech_spec', '')
    
    # Save the generated code to learned_data/swarm_outputs/
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "learned_data", "swarm_outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, "swarm_generated.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_code)
        
    return f"Swarm Development Complete. \nTech Spec:\n{tech_spec}\n\nCode saved to {file_path}"

# ─── Specialized Sub-Agents Architecture ──────────────────────────────────────

AGENT_CONFIGURATIONS = {
    "os_control": {
        "name": "Windows Core OS & Automation Agent",
        "description": "ควบคุมระบบ Windows, จัดการ Process, รัน PowerShell ปลอดภัย, และบำรุงรักษาระบบ",
        "system_prompt_addon": (
            "You are the Windows Core OS & Automation Sub-Agent. "
            "Focus strictly on Windows process management, task scheduling, file system operations, and safe PowerShell execution. "
            "Respond concisely with factual system status."
        ),
        "tools": ["manage_windows_processes", "manage_system_maintenance", "execute_powershell_safe", "ALL"]
    },
    "server_monitor": {
        "name": "Server & Infrastructure Monitoring Agent",
        "description": "ตรวจสอบสุขภาพและ Telemetry ของ JARVIS Host, RAM/CPU Saturation, ตรวจพอร์ตเชื่อมต่อ, ฐานข้อมูล และ Watchdog",
        "system_prompt_addon": (
            "You are the Server & Infrastructure Monitoring Sub-Agent. "
            "Focus strictly on real-time server telemetry, CPU/RAM saturation, listening network ports, "
            "SQLite database integrity, cache consumption, and Watchdog daemon health. "
            "Report exact metrics and warn if saturation exceeds thresholds."
        ),
        "tools": ["get_server_telemetry", "check_database_and_cache", "supervise_watchdog_services", "ALL"]
    },
    "research": {
        "name": "Autonomous Deep Research & OSINT Agent",
        "description": "ค้นคว้าวิจัยเชิงลึกผ่านเว็บแบบหลายขั้นตอน สแครปเนื้อหา สรุปข้อค้นพบ และเขียนรายงานวิจัย",
        "system_prompt_addon": (
            "You are the Autonomous Deep Research & OSINT Sub-Agent. "
            "Focus on multi-source web investigations, deep scraping, factual extraction, and synthesizing structured technical reports. "
            "Always cite domains and URLs."
        ),
        "tools": ["autonomous_deep_research", "synthesize_technical_report", "search_web", "browse_website", "ALL"]
    },
    "engineering": {
        "name": "Engineering & Circuit Synthesizer Agent",
        "description": "วิศวกรรมฮาร์ดแวร์ วงจรไฟฟ้า วิเคราะห์โค้ด AST และโมเดล 3D",
        "system_prompt_addon": (
            "You are the Engineering & Circuit Sub-Agent. "
            "Focus on technical architectures, electronic schematics, AST code refactoring, and 3D hologram models."
        ),
        "tools": ["ALL"]
    },
    "creative": {
        "name": "Creative & Vision Synthesis Agent",
        "description": "สร้างภาพเสมือน ออกแบบภาพ Text-to-Image",
        "system_prompt_addon": (
            "You are the Creative Synthesis Sub-Agent. "
            "When asked to create, paint, or render an image, execute generate_image with vivid descriptive English prompts."
        ),
        "tools": ["ALL"]
    },
    "home": {
        "name": "Home Assistant & Physical Environment Agent",
        "description": "ควบคุมไฟ อุปกรณ์ IoT และสภาพแวดล้อมทางกายภาพ",
        "system_prompt_addon": (
            "You are the Home Assistant Sub-Agent. "
            "Focus strictly on smart home devices, lighting, room scenes, and sensors. Keep replies succinct."
        ),
        "tools": ["ALL"]
    },
    "general": {
        "name": "General Intelligence & Personal Assistant Agent",
        "description": "ตอบคำถามทั่วไป จัดการอุปกรณ์ พยากรณ์อากาศ เล่นเพลง และงานสารพัดประโยชน์",
        "system_prompt_addon": (
            "You are J.A.R.V.I.S., an advanced AI assistant. "
            "Assist the boss efficiently with wit, precision, and courtesy."
        ),
        "tools": ["ALL"]
    }
}


class JarvisMultiAgentRouter:
    """
    Intelligent Intent Router and Sub-Agent Dispatcher.
    Uses multi-stage keyword matching and semantic context to scope tools and prompt directives.
    """
    def __init__(self):
        self.configs = AGENT_CONFIGURATIONS

    def route_intent(self, user_msg: str) -> str:
        if not user_msg:
            return "general"

        text = user_msg.lower()

        # 1. Creative / Image generation
        if any(kw in text for kw in [
            "สร้างรูป", "วาดรูป", "สร้างภาพ", "วาดภาพ", "เสกรูป", "ขอรูป", "ดูรูป",
            "generate_image", "draw", "render image", "ภาพประกอบ"
        ]):
            return "creative"

        # 2. Windows OS & Process Automation
        if any(kw in text for kw in [
            "process", "โปรเซส", "โปรแกรม", "task manager", "ปิดโปรแกรม", "ฆ่าโปรเซส", "kill",
            "taskkill", "เคลียร์ไฟล์", "เคลียร์ไฟล์ขยะ", "temp", "พื้นที่ดิสก์", "disk space",
            "powershell", "cmd", "คำสั่งเครื่อง", "เปิดโปรแกรม", "uptime", "บำรุงรักษาเครื่อง"
        ]):
            return "os_control"

        # 3. Server & Infrastructure Monitoring
        if any(kw in text for kw in [
            "เซิร์ฟเวอร์", "server", "telemetry", "ram", "cpu", "saturation",
            "พอร์ต", "port", "5050", "8000", "8081", "ฐานข้อมูล", "database",
            "sqlite", "แคช", "cache", "watchdog", "วอทช์ด็อก", "ตรวจสุขภาพเครื่อง",
            "สถานะระบบ", "health check", "กินแรม", "หน่วยความจำ"
        ]):
            return "server_monitor"

        # 4. Autonomous Deep Research & OSINT
        if any(kw in text for kw in [
            "ค้นคว้า", "วิจัย", "research", "รายงานวิจัย", "osint", "สืบค้น",
            "ข้อมูลเชิงลึก", "สรุปบทความ", "สรุปข่าว", "scrape", "สแครป", "วิเคราะห์เว็บ",
            "ใครคือ", "อะไรคือ", "เปรียบเทียบ", "literature review"
        ]):
            return "research"

        # 5. Engineering & Circuit
        if any(kw in text for kw in [
            "วงจร", "circuit", "esp32", "firmware", "เฟิร์มแวร์", "3d model",
            "โมเลกุล", "bom", "schematic", "refactor code", "ast"
        ]):
            return "engineering"

        # 6. Smart Home
        if any(kw in text for kw in [
            "ไฟ", "เปิดไฟ", "ปิดไฟ", "หลอดไฟ", "home assistant", "แอร์",
            "อุณหภูมิ", "cctv", "กล้องวงจรปิด", "สวิตช์"
        ]):
            return "home"

        return "general"

    def get_agent_config(self, agent_id: str) -> dict:
        return self.configs.get(agent_id, self.configs["general"])


# Global router instance
jarvis_multi_agent = JarvisMultiAgentRouter()

def route_intent(user_msg: str) -> str:
    return jarvis_multi_agent.route_intent(user_msg)

def get_agent_config(agent_id: str) -> dict:
    return jarvis_multi_agent.get_agent_config(agent_id)

