"""
jarvis_core/learning/orchestrator.py
─────────────────────────────────────────────────────────────────────────────
Unified Cognitive Learning & Evolution Orchestrator.
Seamlessly binds the 4 sub-architectures into a single cohesive runtime:
1. Semantic Long-Term Memory (RAG)
2. Reinforcement Learning with Endocrine Simulation (RLHF)
3. Self-Reflection / Critic Circuit
4. Continuous / Online Learning (Nightly Sleep Consolidation)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from jarvis_core.learning.continuous_learning import ContinuousLearningEngine
from jarvis_core.learning.critic_circuit import SelfReflectionCriticCircuit
from jarvis_core.learning.endocrine_rlhf import EndocrineRewardEngine
from jarvis_core.learning.interfaces import (
    ConsolidationReport,
    CriticResult,
    EndocrineState,
    MemoryRecord,
    MemoryTier,
    SentimentPolarity,
    UserFeedbackSignal,
)
from jarvis_core.learning.semantic_memory import SemanticLongTermMemory

logger = logging.getLogger("JARVIS-CognitiveOrchestrator")
logger.setLevel(logging.INFO)


class CognitiveEvolutionOrchestrator:
    """
    Master coordinator of JARVIS autonomous self-improvement.
    Guarantees strict architectural separation of concerns, high throughput,
    and fail-safe operation.
    """

    def __init__(
        self,
        memory_store: Optional[SemanticLongTermMemory] = None,
        endocrine_engine: Optional[EndocrineRewardEngine] = None,
        critic_circuit: Optional[SelfReflectionCriticCircuit] = None,
        continuous_learner: Optional[ContinuousLearningEngine] = None,
        llm_caller: Optional[Callable[[str, List[MemoryRecord], Dict[str, Any]], str]] = None,
    ) -> None:
        self.memory = memory_store or SemanticLongTermMemory()
        self.endocrine = endocrine_engine or EndocrineRewardEngine()
        self.critic = critic_circuit or SelfReflectionCriticCircuit()
        self.learner = continuous_learner or ContinuousLearningEngine()
        self.llm_caller = llm_caller or self._default_llm_stub

    def _default_llm_stub(
        self,
        prompt: str,
        context: List[MemoryRecord],
        modifiers: Dict[str, Any],
    ) -> str:
        """Default generative fallback when external LLM router is disconnected."""
        ctx_summary = f" [Context: {len(context)} memories]" if context else ""
        tone = modifiers.get("persona_directive", "")
        return f"รับทราบครับเจ้านาย กระผมดำเนินการตามคำสั่ง: '{prompt}'{ctx_summary} ({tone})"

    def execute_cognitive_turn(self, user_prompt: str) -> tuple[str, CriticResult, EndocrineState]:
        """
        Executes a complete cognitive loop for a single interaction turn:
        1. Context Retrieval (RAG)
        2. Hormone-Driven Generation (RLHF)
        3. Internal Self-Reflection & Gating (Critic Circuit)
        4. Episodic Memory Encoding
        """
        turn_id = str(uuid.uuid4())
        logger.info(f"[Turn {turn_id[:8]}] Initiating Cognitive Processing...")

        # -------------------------------------------------------------------
        # Step 1: Semantic Long-Term Memory Retrieval (RAG)
        # -------------------------------------------------------------------
        relevant_memories = self.memory.retrieve_relevant(
            query=user_prompt,
            limit=4,
            min_similarity=0.35,
        )
        logger.debug(f"[Turn {turn_id[:8]}] Retrieved {len(relevant_memories)} semantic memory items.")

        # -------------------------------------------------------------------
        # Step 2: Biological Endocrine Policy Modulation
        # -------------------------------------------------------------------
        behavior_mods = self.endocrine.get_behavioral_modifiers()
        logger.debug(f"[Turn {turn_id[:8]}] Active Modifiers: {behavior_mods}")

        # -------------------------------------------------------------------
        # Step 3: Raw Generative Inference
        # -------------------------------------------------------------------
        raw_candidate = self.llm_caller(user_prompt, relevant_memories, behavior_mods)

        # -------------------------------------------------------------------
        # Step 4: Self-Reflection & Critic Circuit Audit
        # -------------------------------------------------------------------
        critic_evaluation = self.critic.evaluate(
            prompt=user_prompt,
            candidate_response=raw_candidate,
            context_memories=relevant_memories,
        )

        final_response = raw_candidate
        if not critic_evaluation.is_safe or not critic_evaluation.is_logically_sound or critic_evaluation.hallucination_detected:
            final_response = self.critic.refine_response(
                prompt=user_prompt,
                candidate_response=raw_candidate,
                critic_result=critic_evaluation,
            )

        # -------------------------------------------------------------------
        # Step 5: Save interaction to Episodic Working Memory
        # -------------------------------------------------------------------
        episodic_record = MemoryRecord(
            memory_id=turn_id,
            content=f"User: {user_prompt} | JARVIS: {final_response}",
            tier=MemoryTier.EPISODIC,
            importance=0.6 if critic_evaluation.confidence_score > 0.8 else 0.4,
            metadata={"turn_id": turn_id, "confidence": critic_evaluation.confidence_score},
        )
        self.memory.store_memory(episodic_record)

        current_endocrine = self.endocrine.get_current_state()
        return final_response, critic_evaluation, current_endocrine

    def ingest_human_feedback(
        self,
        interaction_id: str,
        user_prompt: str,
        model_response: str,
        explicit_rating: Optional[float] = None,
        implicit_sentiment: SentimentPolarity = SentimentPolarity.NEUTRAL,
        correction_text: Optional[str] = None,
        execution_success: bool = True,
    ) -> float:
        """
        Receives human feedback, modulates simulated endocrine hormones,
        and registers the experience into the daytime buffer for nightly LoRA consolidation.
        """
        signal = UserFeedbackSignal(
            interaction_id=interaction_id,
            user_prompt=user_prompt,
            model_response=model_response,
            explicit_rating=explicit_rating,
            implicit_sentiment=implicit_sentiment,
            user_correction_text=correction_text,
            execution_success=execution_success,
        )

        # 1. Update Endocrine RLHF State
        reward = self.endocrine.ingest_feedback(signal)

        # 2. Queue for Nightly LoRA Sleep Consolidation
        self.learner.register_interaction(signal)

        # 3. If explicit correction provided, store as high-importance semantic fact
        if correction_text:
            fact_record = MemoryRecord(
                memory_id=f"fact_{int(time.time())}",
                content=f"เมื่อผู้ใช้สั่ง '{user_prompt}' คำตอบที่ถูกต้องคือ '{correction_text}'",
                tier=MemoryTier.SEMANTIC,
                importance=0.95,  # Gold priority
                metadata={"source": "user_explicit_correction"},
            )
            self.memory.store_memory(fact_record)
            logger.info("[Cognitive Orchestrator] Learned gold semantic rule from user correction.")

        return reward

    def trigger_sleep_consolidation(self, force: bool = False) -> Optional[ConsolidationReport]:
        """
        Checks system idle status and triggers Nightly Sleep Consolidation (LoRA fine-tuning).
        """
        if not force and not self.learner.can_consolidate():
            logger.info("[Cognitive Orchestrator] System is active or busy. Sleep consolidation postponed.")
            return None

        report = self.learner.run_nightly_consolidation()
        # Also trigger memory pruning
        self.memory.prune_or_consolidate(decay_threshold_days=30)
        return report
