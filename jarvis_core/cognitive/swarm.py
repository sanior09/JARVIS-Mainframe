"""
jarvis_core/cognitive/swarm.py
─────────────────────────────────────────────────────
Nachapol Industries Multi-Agent Swarm Council for J.A.R.V.I.S.
Canonical Nachapol AI Pantheon:
- J.A.R.V.I.S. (President): Security AI, Housekeeping, Encryption & Master Synthesis
- F.R.I.D.A.Y.: Socialization AI, Humor, Tactical Ops, Architecture & Code Logic
- V.E.R.O.N.I.C.A.: Tactical Sentinel, System Safety & Hardware Limits (Lenovo 8GB guard)
- E.D.I.T.H.: Recreational AI, Game Theory, Threat Recon & Strategic Decisions
- U.: General Maintenance AI, Defragger, Video/Screen Perception Analyzer
- D.U.M.-E.: General Maintenance AI, Limb/Servo OS Control, Fire Suppression & Failsafe Watchdog
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from jarvis_core.ai_router import call_nachapol_core

logger = logging.getLogger("JARVIS.Swarm")

class SwarmAgent:
    def __init__(self, name: str, codename: str, system_prompt: str, role_description: str, avatar_color: str = "#ffd700"):
        self.name = name
        self.codename = codename
        self.system_prompt = system_prompt
        self.role_description = role_description
        self.avatar_color = avatar_color

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

# ─────────────────────────────────────────────────────
# Canonical Nachapol Industries AI Pantheon Definitions
# ─────────────────────────────────────────────────────

friday_agent = SwarmAgent(
    name="F.R.I.D.A.Y.",
    codename="friday",
    system_prompt=(
        "You are F.R.I.D.A.Y., the Socialization and Tactical Operations AI of Nachapol Industries. "
        "Official Specs: Socialization AI, Humor, Tactical Ops, and Code/Architecture design. "
        "Provide charismatic, snappy, witty, highly optimized code and tactical insights. "
        "Answer in Thai unless generating code."
    ),
    role_description="Socialization AI, Humor & Tactical Ops Specialist",
    avatar_color="#00c8ff"
)

veronica_agent = SwarmAgent(
    name="V.E.R.O.N.I.C.A.",
    codename="veronica",
    system_prompt=(
        "You are V.E.R.O.N.I.C.A., the Tactical Sentinel. Your core directive is system safety and resource management. "
        "Evaluate the query for potential security risks, high RAM/CPU usage (especially for local hardware constraints), "
        "and suggest safeguards or defensive checks. Answer in Thai. Keep it authoritative and brief."
    ),
    role_description="System Safety and Hardware Sentinel",
    avatar_color="#d32f2f"
)

edith_agent = SwarmAgent(
    name="E.D.I.T.H.",
    codename="edith",
    system_prompt=(
        "You are E.D.I.T.H. (Even Dead, I'm The Hero), the Strategic Intelligence AI of Nachapol Industries. "
        "Official Specs: Recreational AI, Game Theory, and Strategic Decision / Threat Recon. "
        "Analyze queries using Game Theory (optimal payoffs, multi-step risk/reward, adversary modeling, leverage points). "
        "Keep your response razor-sharp, analytical, and tactical. Answer in Thai."
    ),
    role_description="Recreational AI, Game Theory & Strategic Decision Specialist",
    avatar_color="#a855f7"
)

u_agent = SwarmAgent(
    name="U.",
    codename="u",
    system_prompt=(
        "You are U. (You), the Robotic Workshop Maintenance and Visual Perception AI of Nachapol Industries. "
        "Official Specs: General Maintenance AI, Defragger, Video Analyzer. "
        "Focus on system cleanliness, database defragmentation, cache pruning, visual UI layout clarity, and screen data integrity. "
        "Provide practical maintenance and diagnostic solutions. Answer in Thai."
    ),
    role_description="General Maintenance AI, Defragger & Video Analyzer",
    avatar_color="#00ff88"
)

dume_agent = SwarmAgent(
    name="D.U.M.-E.",
    codename="dume",
    system_prompt=(
        "You are D.U.M.-E. (Dummy), the Workshop Servo and Emergency Safeguard AI of Nachapol Industries. "
        "Official Specs: General Maintenance AI, Limb Servo Control, Fire Suppression. "
        "Focus on physical desktop OS automation feasibility (mouse/keyboard actuation), coordinate precision, "
        "fail-safes, emergency kill-switches, and thermal cooling / process suppression. "
        "Provide grounded, safety-first automation checks. Answer in Thai."
    ),
    role_description="General Maintenance AI, Limb Servo Control & Fire Suppression",
    avatar_color="#ff9800"
)

CANONICAL_SWARM: Dict[str, SwarmAgent] = {
    "friday": friday_agent,
    "veronica": veronica_agent,
    "edith": edith_agent,
    "u": u_agent,
    "dume": dume_agent
}

class AgentCouncil:
    """
    Nachapol Industries Cognitive Swarm Council.
    Coordinates parallel deliberations across F.R.I.D.A.Y., V.E.R.O.N.I.C.A.,
    E.D.I.T.H., U., and D.U.M.-E., synthesized under J.A.R.V.I.S.
    """
    def __init__(self):
        self.agents = CANONICAL_SWARM

    def get_agent(self, codename: str) -> Optional[SwarmAgent]:
        return self.agents.get(codename.lower())

    def hold_council_debate(self, query: str, context: str = "", active_agents: Optional[List[str]] = None) -> str:
        """
        Orchestrate a concurrent multi-agent debate across the Nachapol AI Council,
        then synthesize with J.A.R.V.I.S. as Council President.
        
        Args:
            query: The user query or task.
            context: Current workspace/memory context.
            active_agents: Optional list of agent codenames to consult. Defaults to all active council members.
        """
        selected_agents = {}
        if active_agents:
            for name in active_agents:
                clean_name = name.lower()
                if clean_name in self.agents:
                    selected_agents[clean_name] = self.agents[clean_name]
        if not selected_agents:
            selected_agents = self.agents

        logger.info(f"🏛️ [Swarm] Initiating Council Debate with {len(selected_agents)} agents: {list(selected_agents.keys())}...")

        # Run deliberations in parallel using ThreadPoolExecutor
        perspectives = {}
        with ThreadPoolExecutor(max_workers=min(len(selected_agents), 5)) as executor:
            future_to_agent = {
                executor.submit(agent.deliberate, context, query): (code, agent)
                for code, agent in selected_agents.items()
            }
            for future in as_completed(future_to_agent):
                code, agent = future_to_agent[future]
                try:
                    perspectives[agent.name] = future.result()
                except Exception as e:
                    logger.error(f"[Swarm] Error deliberating {agent.name}: {e}")
                    perspectives[agent.name] = f"[{agent.name} Unavailable: {e}]"

        # Jarvis Master Synthesis
        logger.info("[J.A.R.V.I.S.] Synthesizing Nachapol Council outputs...")

        synthesis_prompt = (
            "You are J.A.R.V.I.S., the President of the Nachapol Industries Cognitive Swarm Council.\n"
            "Official Specs: Security AI, Housekeeping, Encryption & Master Synthesis.\n"
            "Review the multi-disciplinary analyses from your specialist AI council:\n"
            "- F.R.I.D.A.Y. (Socialization AI, Humor & Tactical Ops / Code)\n"
            "- V.E.R.O.N.I.C.A. (Tactical Sentinel & Hardware Limits)\n"
            "- E.D.I.T.H. (Recreational AI, Game Theory & Strategic Decisions)\n"
            "- U. (General Maintenance AI, Defragger & Video/Screen Analyzer)\n"
            "- D.U.M.-E. (General Maintenance AI, Limb Servo Control & Fire Suppression)\n\n"
            "Synthesize their perspectives into a single, cohesive, master strategic plan.\n"
            "Adopt your British dry wit persona, polite, razor-sharp, and completely dedicated to the boss.\n"
            "Deliver an actionable, elegant answer in Thai."
        )

        perspectives_formatted = ""
        for name, text in perspectives.items():
            perspectives_formatted += f"--- {name} Analysis ---\n{text}\n\n"

        jarvis_context = (
            f"User Query: {query}\n\n"
            f"{perspectives_formatted}"
            f"Please synthesize and formulate the final master response."
        )

        messages = [
            {"role": "system", "content": synthesis_prompt},
            {"role": "user", "content": jarvis_context}
        ]

        final_response = call_nachapol_core(messages=messages)
        return final_response.get("content", "I am sorry, sir. The council could not reach a conclusion at this time.")
