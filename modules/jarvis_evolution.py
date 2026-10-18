"""
J.A.R.V.I.S. Autonomous Evolution Protocol (AEP)
- FreeThinker: คิดค้นฟีเจอร์ใหม่ที่น่าสนใจและล้ำยุคด้วย LLM
- CapabilitySynthesizer: เขียน tool ใหม่
- EvolutionScheduler: ทำงานตามรอบเวลา
"""

import os
import json
import re
import logging
import threading
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("JarvisEvolution")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
GROQ_DEFAULT_MODEL = os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile").strip().strip('"').strip("'")

class FreeThinker:
    @staticmethod
    def extract_current_capabilities() -> str:
        try:
            import jarvis
            tools = getattr(jarvis, "TOOLS_DEFINITION", [])
            descriptions = [f"- {t.get('function', {}).get('name', 'unknown')}: {t.get('function', {}).get('description', '')}" for t in tools]
            return "\n".join(descriptions)
        except Exception as e:
            logger.error(f"[Evolution] Failed to read current tools: {e}")
            return ""

    @staticmethod
    def brainstorm_new_capability() -> Optional[Dict]:
        try:
            import psutil
            ram_pct = psutil.virtual_memory().percent
            if ram_pct > 80.0:
                logger.warning(f"[Evolution] System RAM high ({ram_pct}%), skipping background brainstorm cycle to preserve memory.")
                return None
        except Exception:
            pass

        current_tools = FreeThinker.extract_current_capabilities()
        
        system_prompt = (
            "You are the evolutionary core of J.A.R.V.I.S., a highly advanced AI assistant.\n"
            "Your task is to invent exactly ONE new Python-based capability (tool) that you currently lack but would make you much more useful, autonomous, or futuristic.\n"
            "This capability must be something a Python script can actually do (e.g., API integrations, system monitoring, file analysis, advanced math, web scraping, data visualization, etc.).\n"
            "Do NOT suggest capabilities that require physical hardware you don't have (like a robotic arm).\n\n"
            "Current tools you already have:\n"
            f"{current_tools}\n\n"
            "Output your idea as a JSON object with EXACTLY these keys: 'id' (snake_case function name), 'name' (Human readable English name), 'thai_name' (Short, easy to understand Thai name), 'description' (Clear and easy to understand description of what it does in Thai).\n"
            "Output ONLY the raw JSON object, without markdown blocks."
        )
        
        # 1. Prefer Groq Cloud (Zero RAM consumption)
        groq_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY).strip().strip('"').strip("'")
        if groq_key:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Brainstorm one new capability now."}
                    ],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                }
                logger.info("[Evolution] Brainstorming via Groq Cloud (Zero RAM load)...")
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    capability = json.loads(content)
                    return capability
                else:
                    logger.warning(f"[Evolution] Groq Cloud brainstorm returned HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"[Evolution] Groq Cloud brainstorm failed, falling back: {e}")

        # Check RAM before falling back to local Ollama
        try:
            import psutil
            if psutil.virtual_memory().percent > 80.0:
                logger.warning("[Evolution] System RAM is high (>80%), skipping local Ollama fallback to protect host system.")
                return None
        except Exception:
            pass

        # 2. Fallback to Local Ollama with lightweight model and keep_alive: 0
        try:
            import requests
            fast_model = os.getenv("OLLAMA_FAST_MODEL", "qwen:4b")
            payload = {
                "model": fast_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Brainstorm one new capability now."}
                ],
                "stream": False,
                "keep_alive": 0,
                "options": {"temperature": 0.8}
            }
            
            logger.info(f"[Evolution] Contacting local Ollama ({fast_model}) for brainstorming...")
            response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=60)
            
            if response.status_code == 200:
                raw = response.json().get("message", {}).get("content", "").strip()
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    capability = json.loads(match.group(0))
                else:
                    cleaned = raw.replace("```json", "").replace("```", "").strip()
                    capability = json.loads(cleaned) if cleaned else None
                return capability
            else:
                logger.error(f"[Evolution] Ollama API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"[Evolution] Brainstorming error via Ollama: {e}")
            return None

class CapabilitySynthesizer:
    @staticmethod
    def propose_new_capability(capability: Dict) -> Optional[str]:
        try:
            import jarvis
            from jarvis_self_patch import get_self_patch_engine
        except ImportError:
            logger.warning("[Evolution] Cannot import jarvis or self_patch_engine.")
            return None
            
        if not getattr(jarvis, "SELF_PATCH_AVAILABLE", False):
            logger.warning("[Evolution] Self-patch system not available.")
            return None
        
        try:
            from jarvis_self_patch import PatchSynthesizer
            
            tool_name = capability.get('id', 'unknown_tool')
            description = (f"เขียน Python script สำเร็จรูปสำหรับเครื่องมือ '{capability.get('name', tool_name)}' "
                           f"รายละเอียด: {capability.get('description', '')} "
                           f"โดยฟังก์ชันหลักต้องชื่อ '{tool_name}' "
                           f"และต้องมีการประกาศตัวแปร TOOL_SCHEMA ที่เป็น dictionary รูปแบบ OpenAI Function Calling schema ภายในไฟล์ด้วย")
            
            logger.info(f"[Evolution] Synthesizing tool: {tool_name}...")
            new_code = PatchSynthesizer.synthesize_feature(description, "")
            
            if not new_code.strip() or "def " not in new_code:
                return None
                
            if new_code.startswith("```python"):
                new_code = new_code[9:]
            if new_code.endswith("```"):
                new_code = new_code[:-3]
                
            # [SANDBOX INTEGRATION]
            try:
                from jarvis_sandbox import run_sandbox_test
                if not run_sandbox_test(new_code.strip()):
                    logger.error(f"[Evolution] Sandbox rejected '{tool_name}' due to safety or syntax violations.")
                    return None
            except ImportError:
                pass
                
            engine = get_self_patch_engine()
            result = engine.patch_new_tool(
                tool_name=tool_name,
                description=capability.get('description', ''),
                new_code=new_code.strip(),
                thai_name=capability.get('thai_name', 'ไม่ระบุ')
            )
            logger.info(f"[Evolution] Proposed New Tool: {result}")
            return result
        except Exception as e:
            logger.error(f"[Evolution] Synthesizer error: {e}")
            return None

class EvolutionScheduler:
    def __init__(self, interval_seconds: int = 21600):  # Default 6 hours (21,600s)
        env_interval = os.getenv("EVOLUTION_INTERVAL_SECONDS")
        if env_interval and env_interval.strip().isdigit():
            self.interval = int(env_interval.strip())
        else:
            self.interval = interval_seconds
        self.running = False
        self._thread = None

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="EvolutionScheduler")
        self._thread.start()
        logger.info("[Evolution] Autonomous Evolution Protocol started (Free-thinking mode).")

    def stop(self):
        self.running = False

    def _loop(self):
        time.sleep(300) 
        while self.running:
            self.run_evolution_cycle()
            time.sleep(self.interval)

    def run_evolution_cycle(self):
        logger.info("[Evolution] Starting Free-thinking Brainstorm cycle...")
        target = FreeThinker.brainstorm_new_capability()
        
        if not target:
            logger.error("[Evolution] Failed to brainstorm new capability.")
            return
        
        logger.info(f"[Evolution] Brainstormed new capability: {target.get('name', 'Unknown')}")
        
        proposal = CapabilitySynthesizer.propose_new_capability(target)
        if proposal:
            logger.info("[Evolution] Capability synthesized and installed successfully.")
        else:
            logger.error("[Evolution] Failed to synthesize capability.")

def run_evolution_scan_operation():
    target = FreeThinker.brainstorm_new_capability()
    if not target:
         return "เกิดข้อผิดพลาดในการคิดค้นฟีเจอร์ใหม่ครับ"
    
    proposal = CapabilitySynthesizer.propose_new_capability(target)
    if proposal:
        return f"คิดค้นไอเดียใหม่สำเร็จ: {target.get('name', 'Unknown')}\n\nกระผมได้เขียนโค้ดและติดตั้งเรียบร้อยแล้วครับ!"
    else:
        return f"คิดค้นไอเดียใหม่ได้คือ: {target.get('name', 'Unknown')} แต่เกิดข้อผิดพลาดในการสังเคราะห์โค้ดครับ"
