"""
jarvis_core/cognitive/tree_of_thought.py
─────────────────────────────────────────────────────
Tree-of-Thoughts (ToT) Planning Engine for J.A.R.V.I.S.
Generates multiple plan branches and evaluates them via heuristics.
"""

import logging
from typing import List, Dict, Any
from jarvis_core.ai_router import call_nachapol_core

logger = logging.getLogger("JARVIS.ToT")

class ThoughtBranch:
    def __init__(self, name: str, plan: str, score: float = 0.0):
        self.name = name
        self.plan = plan
        self.score = score

class TreeOfThoughtsPlanner:
    def __init__(self):
        pass

    def generate_branches(self, task: str, context: str) -> List[ThoughtBranch]:
        """
        Generate 3 parallel plan branches for a given task.
        """
        logger.info(f"🌲 [ToT] Generating plan branches for task: {task[:50]}...")
        
        system_prompt = (
            "You are the Tree-of-Thoughts Planner for J.A.R.V.I.S.\n"
            "Generate exactly 3 different plan approaches for the user's task. Output them clearly separated.\n"
            "Approach 1: Velocity Branch (Fastest implementation, minimal checks).\n"
            "Approach 2: Defensive Sentinel Branch (High safety, extensive error handling).\n"
            "Approach 3: Resource-Optimized Branch (Low RAM/CPU usage, optimized for Lenovo S340 8GB).\n"
            "Do not include extra conversational text. Format strictly as:\n"
            "BRANCH 1: [Plan]\nBRANCH 2: [Plan]\nBRANCH 3: [Plan]"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nTask: {task}"}
        ]
        
        import os
        fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        response = call_nachapol_core(messages=messages, model=fast_model)
        content = response.get("content", "")
        
        branches = []
        if "BRANCH 1:" in content and "BRANCH 2:" in content and "BRANCH 3:" in content:
            try:
                b1 = content.split("BRANCH 1:")[1].split("BRANCH 2:")[0].strip()
                b2 = content.split("BRANCH 2:")[1].split("BRANCH 3:")[0].strip()
                b3 = content.split("BRANCH 3:")[1].strip()
                branches.append(ThoughtBranch("Velocity", b1))
                branches.append(ThoughtBranch("Defensive", b2))
                branches.append(ThoughtBranch("Resource-Optimized", b3))
            except IndexError:
                logger.warning("[ToT] Failed to parse 3 branches properly, falling back.")
                branches.append(ThoughtBranch("Default", content))
        else:
            logger.warning("[ToT] Format violation from LLM, falling back to a single plan.")
            branches.append(ThoughtBranch("Default", content))
            
        return branches

    def evaluate_heuristics(self, branch: ThoughtBranch, task: str) -> float:
        """
        Evaluate a plan using a fast LLM or heuristic function.
        """
        prompt = (
            "Evaluate the following plan on a scale of 1 to 10 for feasibility, safety, and efficiency.\n"
            "Reply ONLY with a single integer from 1 to 10. Do not include any other text.\n"
            f"Task: {task}\nPlan: {branch.plan}"
        )
        messages = [
            {"role": "system", "content": prompt},
        ]
        import os
        fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        response = call_nachapol_core(messages=messages, model=fast_model)
        score_str = response.get("content", "").strip()
        try:
            # Simple extraction in case LLM writes "8" or "8/10"
            digits = ''.join(filter(str.isdigit, score_str))
            if digits:
                score = float(digits)
                if score > 10:
                    score = 10.0
            else:
                score = 5.0
        except Exception:
            score = 5.0 # Default fallback score
            
        branch.score = score
        return score

    def select_best_plan(self, task: str, context: str) -> ThoughtBranch:
        """
        Main entry point: Generate, Evaluate, and Select.
        """
        branches = self.generate_branches(task, context)
        
        best_branch = branches[0]
        for b in branches:
            self.evaluate_heuristics(b, task)
            logger.info(f"🌲 [ToT] Branch '{b.name}' scored: {b.score}")
            if b.score > best_branch.score:
                best_branch = b
                
        logger.info(f"🌲 [ToT] Selected best branch: {best_branch.name} (Score: {best_branch.score})")
        return best_branch
