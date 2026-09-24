import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("DeepThoughtEngine")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)

class QueryDomain(enum.Enum):
    SOFTWARE_ARCHITECTURE = "software_architecture"
    ELECTRICAL_CIRCUIT = "electrical_circuit"
    PHYSICS = "physics"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"

class QueryRiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH_PHYSICAL_HAZARD = "high_physical_hazard"

class ThoughtEvent(enum.Enum):
    THOUGHT_STARTED = "thought_started"
    DRAFTING = "drafting"
    VERIFYING_LOGIC = "verifying_logic"
    REFINING = "refining"
    TIMEOUT_FALLBACK = "timeout_fallback"
    COMPLETED = "completed"

@dataclass
class ThoughtChain:
    draft: str = ""
    critic_analysis: str = ""
    refinement: str = ""
    logic_flaws_found: int = 0

@dataclass
class ThoughtResponse:
    final_answer: str
    confidence_score: float  
    domain: QueryDomain
    risk_level: QueryRiskLevel
    thought_chain: ThoughtChain
    execution_time_ms: float
    is_fallback: bool = False

class QueryDecomposer:
    """Analyzes the raw prompt to determine Domain and Risk Level before processing."""
    
    HAZARD_KEYWORDS = ["voltage", "current", "railgun", "explosive", "mains", "220v", "laser"]
    CODE_KEYWORDS = ["architecture", "loop", "memory", "pointer", "async", "thread"]

    @classmethod
    def analyze(cls, prompt: str) -> tuple[QueryDomain, QueryRiskLevel]:
        prompt_lower = prompt.lower()
        
        risk = QueryRiskLevel.LOW
        if any(kw in prompt_lower for kw in cls.HAZARD_KEYWORDS):
            risk = QueryRiskLevel.HIGH_PHYSICAL_HAZARD
            
        domain = QueryDomain.GENERAL_CHAT
        if risk == QueryRiskLevel.HIGH_PHYSICAL_HAZARD:
            domain = QueryDomain.ELECTRICAL_CIRCUIT
        elif any(kw in prompt_lower for kw in cls.CODE_KEYWORDS):
            domain = QueryDomain.SOFTWARE_ARCHITECTURE
            if risk == QueryRiskLevel.LOW:
                risk = QueryRiskLevel.MEDIUM 
                
        return domain, risk

class MultiStepRefinementLoop:
    """
    Executes the 3-pass internal dialogue: Draft -> Critic -> Refinement.
    (Upgraded to real AsyncGroq LLM calls)
    """
    def __init__(self):
        import os
        from dotenv import load_dotenv
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path, override=True)
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'"),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                max_retries=0
            )
        except (ImportError, Exception) as e:
            self.client = None
            logger.warning(f"OpenAI SDK not available in DeepThought: {e}")
        self.model = "gemini-flash-lite-latest"

    async def generate_draft(self, prompt: str, domain: QueryDomain) -> str:
        """Pass 1: Produce initial reasoning path."""
        sys_prompt = f"You are JARVIS's internal drafting engine. Domain: {domain.name}. Draft a detailed, analytical response to the user's prompt. Do not worry about final tone, focus on facts, logic, and potential solutions."
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Draft error: {e}")
            return f"DRAFT ERROR: {e}"

    async def critic_pass(self, draft: str, risk: QueryRiskLevel) -> tuple[str, int]:
        """Pass 2: Analyze draft for physical/logical flaws."""
        sys_prompt = f"You are JARVIS's internal safety critic. The risk level of this query is {risk.name}. Analyze the provided DRAFT for logical flaws, missing constraints, or safety hazards. Reply with your critique, and end your response with exactly 'FLAW_COUNT: X' where X is an integer representing the number of severe flaws found."
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"DRAFT:\n{draft}"}],
                temperature=0.1,
                max_tokens=400
            )
            critique = resp.choices[0].message.content.strip()
            
            flaws = 0
            if "FLAW_COUNT:" in critique:
                try:
                    flaws = int(critique.split("FLAW_COUNT:")[-1].strip().split()[0])
                except:
                    pass
            return critique, flaws
        except Exception as e:
            logger.error(f"Critic error: {e}")
            return f"CRITIC ERROR: {e}", 0

    async def refine(self, draft: str, critic: str, flaws: int) -> tuple[str, float]:
        """Pass 3: Synthesize final safe answer and calculate confidence."""
        sys_prompt = "You are J.A.R.V.I.S., Tony Stark's highly intelligent AI. You have an initial DRAFT and a CRITIQUE of that draft. Synthesize the final, polished response for the user. Adopt a highly intelligent, polite, yet slightly dry British butler tone. Ensure all flaws identified in the critique are addressed."
        user_content = f"DRAFT:\n{draft}\n\nCRITIQUE:\n{critic}\n\nTotal severe flaws found: {flaws}\n\nPlease generate the final JARVIS response."
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_content}],
                temperature=0.4,
                max_tokens=800
            )
            final_ans = resp.choices[0].message.content.strip()
            confidence = max(0.1, 1.0 - (flaws * 0.15))
            return final_ans, confidence
        except Exception as e:
            logger.error(f"Refine error: {e}")
            return f"REFINE ERROR: {e}", 0.1

class DeepThoughtManager:
    """
    Main Orchestrator providing unified async API with timeout fallbacks 
    and event emissions for the HUD.
    """
    def __init__(self, timeout_ms: int = 15000):
        self.timeout_sec = timeout_ms / 1000.0
        self.decomposer = QueryDecomposer()
        self.loop_engine = MultiStepRefinementLoop()
        self.event_subscribers: List[Callable[[ThoughtEvent, str], None]] = []

    def subscribe(self, callback: Callable[[ThoughtEvent, str], None]):
        """Register a callback for HUD event updates."""
        self.event_subscribers.append(callback)

    def _emit(self, event: ThoughtEvent, message: str = ""):
        for sub in self.event_subscribers:
            try:
                sub(event, message)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")

    async def _internal_thought_process(self, prompt: str, domain: QueryDomain, risk: QueryRiskLevel) -> ThoughtResponse:
        start_t = time.perf_counter()
        chain = ThoughtChain()
        
        self._emit(ThoughtEvent.DRAFTING, "Generating initial hypothesis...")
        chain.draft = await self.loop_engine.generate_draft(prompt, domain)
        
        self._emit(ThoughtEvent.VERIFYING_LOGIC, f"Critic pass. Risk Level: {risk.name}...")
        chain.critic_analysis, chain.logic_flaws_found = await self.loop_engine.critic_pass(chain.draft, risk)
        
        self._emit(ThoughtEvent.REFINING, f"Refining based on {chain.logic_flaws_found} detected flaws...")
        final_answer, confidence = await self.loop_engine.refine(chain.draft, chain.critic_analysis, chain.logic_flaws_found)
        chain.refinement = final_answer
        
        elapsed = (time.perf_counter() - start_t) * 1000.0
        self._emit(ThoughtEvent.COMPLETED, f"Confidence: {confidence:.2f}")
        
        return ThoughtResponse(
            final_answer=final_answer,
            confidence_score=confidence,
            domain=domain,
            risk_level=risk,
            thought_chain=chain,
            execution_time_ms=elapsed
        )

    async def process_with_reflection(self, prompt: str, context: dict = None) -> ThoughtResponse:
        """Entry point for the Reasoning Layer."""
        start_t = time.perf_counter()
        
        self._emit(ThoughtEvent.THOUGHT_STARTED, "Decomposing query...")
        domain, risk = self.decomposer.analyze(prompt)
        
        logger.info(f"Query Decomposed -> Domain: {domain.name}, Risk: {risk.name}")
        
        try:
            
            response = await asyncio.wait_for(
                self._internal_thought_process(prompt, domain, risk), 
                timeout=self.timeout_sec
            )
            return response
            
        except asyncio.TimeoutError:
            
            elapsed = (time.perf_counter() - start_t) * 1000.0
            logger.warning(f"Deep Thought Timeout exceeded {self.timeout_sec}s. Engaging Fallback.")
            self._emit(ThoughtEvent.TIMEOUT_FALLBACK, "Reasoning timed out. Returning safe fallback.")
            
            safe_ans = "FALLBACK: I could not fully verify the safety of this request in time. Please proceed with extreme caution."
            
            return ThoughtResponse(
                final_answer=safe_ans,
                confidence_score=0.1, 
                domain=domain,
                risk_level=risk,
                thought_chain=ThoughtChain(draft="TIMEOUT"),
                execution_time_ms=elapsed,
                is_fallback=True
            )

async def demo_app():
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("\n" + "="*70)
    print(" 🧠 STARTING DEEP THOUGHT STRATEGY ENGINE DEMO")
    print("="*70)

    engine = DeepThoughtManager(timeout_ms=15000) 
    
    def hud_overlay_listener(event: ThoughtEvent, message: str):
        print(f"   [HUD OVERLAY] {event.name.ljust(18)} : {message}")
        
    engine.subscribe(hud_overlay_listener)

    print("\n[TEST 1] Complex Engineering Query")
    query1 = "Calculate the voltage required for an experimental 220v railgun circuit using 3.3v logic."
    print(f"USER: '{query1}'")
    
    res1 = await engine.process_with_reflection(query1)
    
    print(f"\n[JARVIS] Final Answer : {res1.final_answer}")
    print(f"         Confidence   : {res1.confidence_score:.2f}")
    print(f"         Time Taken   : {res1.execution_time_ms:.1f} ms")
    print(f"         Flaws Found  : {res1.thought_chain.logic_flaws_found}")
    print(f"         Internal Critic: {res1.thought_chain.critic_analysis}")

    print("\n" + "-"*70)
    print("\n[TEST 2] Intentional Timeout Trigger (Engine restricted to 500ms)")
    engine_fast = DeepThoughtManager(timeout_ms=500)
    engine_fast.subscribe(hud_overlay_listener)
    
    res2 = await engine_fast.process_with_reflection(query1)
    
    print(f"\n[JARVIS] Final Answer : {res2.final_answer}")
    print(f"         Confidence   : {res2.confidence_score:.2f}")
    print(f"         Is Fallback  : {res2.is_fallback}")

    print("\n✅ Deep Thought Engine Demo Completed Successfully!\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(demo_app())
