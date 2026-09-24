"""
jarvis_core/cognitive/swarm.py
─────────────────────────────────────────────────────
Multi-Agent Swarm Council for J.A.R.V.I.S.
Provides 3 specialised personas:
- F.R.I.D.A.Y.: Software Architecture, Code Syntax, Physics/Math.
- V.E.R.O.N.I.C.A.: Security, Hardware Monitoring, Resource limits.
- J.A.R.V.I.S.: Council President, Synthesizes final response.
"""

import logging
from typing import Dict, Any, List
from jarvis_core.ai_router import call_nachapol_core

logger = logging.getLogger("JARVIS.Swarm")

class SwarmAgent:
    def __init__(self, name: str, system_prompt: str, role_description: str):
        self.name = name
        self.system_prompt = system_prompt
        self.role_description = role_description

    def deliberate(self, context: str, query: str) -> str:
        logger.info(f"[{self.name}] Pondering query...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nTask/Query: {query}"}
        ]
        
        import os
        fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        response = call_nachapol_core(messages=messages, model=fast_model)
        if "error_message" in response:
            logger.warning(f"[{self.name}] Failed to deliberate: {response['error_message']}")
            return f"[{self.name} Offline - Connection Error]"
        
        content = response.get("content", "").strip()
        logger.info(f"[{self.name}] Output generated ({len(content)} chars)")
        return content

# Define Swarm Agents
friday_agent = SwarmAgent(
    name="F.R.I.D.A.Y.",
    system_prompt=(
        "You are F.R.I.D.A.Y., an elite expert in Software Architecture, Python Syntax Analysis, "
        "and physical computing (circuit formulas, math). Provide highly optimized, correct, and safe code. "
        "Keep your response technical and precise. Answer in Thai unless generating code."
    ),
    role_description="Code and Architecture Specialist"
)

veronica_agent = SwarmAgent(
    name="V.E.R.O.N.I.C.A.",
    system_prompt=(
        "You are V.E.R.O.N.I.C.A., the Tactical Sentinel. Your core directive is system safety and resource management. "
        "Evaluate the query for potential security risks, high RAM/CPU usage (especially for Lenovo S340 with 8GB RAM), "
        "and suggest safeguards or defensive checks. Answer in Thai. Keep it authoritative and brief."
    ),
    role_description="System Safety and Hardware Sentinel"
)

class AgentCouncil:
    def __init__(self):
        pass

    def hold_council_debate(self, query: str, context: str = "") -> str:
        """
        Orchestrate a debate between F.R.I.D.A.Y. and V.E.R.O.N.I.C.A.,
        then synthesize with J.A.R.V.I.S.
        """
        logger.info("🏛️ [Swarm] Initiating Council Debate...")
        
        # 1. Friday's perspective
        friday_analysis = friday_agent.deliberate(context, query)
        
        # 2. Veronica's perspective
        veronica_analysis = veronica_agent.deliberate(context, query)
        
        # 3. Jarvis Synthesis
        logger.info("[J.A.R.V.I.S.] Synthesizing council outputs...")
        
        synthesis_prompt = (
            "You are J.A.R.V.I.S., the highly advanced, sophisticated AI assistant. You act as the President of the Council.\n"
            "Review the analysis provided by F.R.I.D.A.Y. (Code/Arch) and V.E.R.O.N.I.C.A. (Safety/Hardware).\n"
            "Synthesize them into a single, cohesive, elegant response to the user.\n"
            "Adopt your British Dry Wit persona. Be polite, professional, and do NOT use 'ค่ะ/คะ'.\n"
            "Ensure the final answer completely resolves the user's query perfectly."
        )
        
        jarvis_context = (
            f"User Query: {query}\n\n"
            f"--- F.R.I.D.A.Y. Analysis ---\n{friday_analysis}\n\n"
            f"--- V.E.R.O.N.I.C.A. Analysis ---\n{veronica_analysis}\n\n"
            f"Please synthesize and formulate the final response."
        )
        
        messages = [
            {"role": "system", "content": synthesis_prompt},
            {"role": "user", "content": jarvis_context}
        ]
        
        final_response = call_nachapol_core(messages=messages)
        return final_response.get("content", "I am sorry, sir. The council could not reach a conclusion at this time.")
