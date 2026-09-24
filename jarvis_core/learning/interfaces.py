"""
jarvis_core/learning/interfaces.py
─────────────────────────────────────────────────────────────────────────────
Architectural Interfaces & Data Transfer Objects (DTOs) for the
Advanced AI Learning and Evolution Subsystem (J.A.R.V.I.S. Cognitive Core).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple


# ===========================================================================
# ENUMS & STATUS CODES
# ===========================================================================

class MemoryTier(str, Enum):
    WORKING = "working"          # Immediate dialogue window
    EPISODIC = "episodic"        # Recent events and interaction turns
    SEMANTIC = "semantic"        # Long-term facts, rules, learned knowledge
    PROCEDURAL = "procedural"    # Skills, tools, and execution strategies


class LearningState(str, Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    CONSOLIDATING = "consolidating"
    BENCHMARKING = "benchmarking"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


class SentimentPolarity(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRITICAL_ERROR = "critical_error"


# ===========================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ===========================================================================

@dataclass
class MemoryRecord:
    """Represents a unified atomic unit in the Semantic Memory Graph."""
    memory_id: str
    content: str
    tier: MemoryTier = MemoryTier.SEMANTIC
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5            # Range [0.0, 1.0]
    emotional_valence: float = 0.0     # Range [-1.0 (Negative), 1.0 (Positive)]
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)


@dataclass
class EndocrineState:
    """
    Simulated Bio-Chemical / Neurotransmitter State for Behavioral Modulation.
    Normalized values range between 0.0 and 1.0 (baseline at 0.5).
    """
    dopamine: float = 0.5     # Reward, curiosity, exploration tendency
    cortisol: float = 0.2     # Stress, risk aversion, defensive rigor
    serotonin: float = 0.7    # Emotional stability, patient composure
    adrenaline: float = 0.3   # Response urgency, execution acceleration
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, float]:
        return {
            "dopamine": round(self.dopamine, 4),
            "cortisol": round(self.cortisol, 4),
            "serotonin": round(self.serotonin, 4),
            "adrenaline": round(self.adrenaline, 4),
        }


@dataclass
class UserFeedbackSignal:
    """User evaluation signal ingested into the RLHF reward stream."""
    interaction_id: str
    user_prompt: str
    model_response: str
    explicit_rating: Optional[float] = None  # e.g., +1.0 (thumb up), -1.0 (thumb down)
    implicit_sentiment: SentimentPolarity = SentimentPolarity.NEUTRAL
    user_correction_text: Optional[str] = None
    execution_success: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class CriticResult:
    """Evaluation output from the Self-Reflection & Critic Circuit."""
    is_safe: bool
    is_logically_sound: bool
    confidence_score: float             # Range [0.0, 1.0]
    hallucination_detected: bool
    critique_notes: List[str] = field(default_factory=list)
    suggested_revision: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class ConsolidationReport:
    """Summary report from a Nightly Sleep Consolidation / LoRA Fine-tuning session."""
    job_id: str
    sample_count: int
    duration_sec: float
    loss_initial: float
    loss_final: float
    regression_test_passed: bool
    status: LearningState
    weights_path: Optional[str] = None
    details: str = ""


# ===========================================================================
# ABSTRACT BASE CLASSES & PROTOCOLS
# ===========================================================================

class ISemanticMemoryStore(ABC):
    """Protocol for semantic long-term memory retrieval and storage (RAG)."""

    @abstractmethod
    def store_memory(self, record: MemoryRecord) -> bool:
        """Stores or updates a memory record in the local vector DB."""
        pass

    @abstractmethod
    def retrieve_relevant(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.65,
        tier: Optional[MemoryTier] = None,
    ) -> List[MemoryRecord]:
        """Performs hybrid semantic search with temporal recency weighting."""
        pass

    @abstractmethod
    def prune_or_consolidate(self, decay_threshold_days: int = 30) -> int:
        """Prunes stale memories or merges redundant cluster memories."""
        pass


class IEndocrineRewardEngine(ABC):
    """Protocol for Bio-inspired Endocrine RLHF modulation."""

    @abstractmethod
    def ingest_feedback(self, feedback: UserFeedbackSignal) -> float:
        """
        Processes human feedback, updates simulated hormone levels,
        and returns the modulated reward scalar.
        """
        pass

    @abstractmethod
    def get_current_state(self) -> EndocrineState:
        """Returns the current endocrine levels."""
        pass

    @abstractmethod
    def get_behavioral_modifiers(self) -> Dict[str, Any]:
        """
        Derives LLM generation hyperparameters (temperature, top_p,
        safety_strictness, verbosity) from endocrine states.
        """
        pass


class ICriticCircuit(ABC):
    """Protocol for internal self-reflection and multi-pass output vetting."""

    @abstractmethod
    def evaluate(
        self,
        prompt: str,
        candidate_response: str,
        context_memories: List[MemoryRecord],
    ) -> CriticResult:
        """Performs pre-emission evaluation of accuracy, safety, and logic."""
        pass

    @abstractmethod
    def refine_response(
        self,
        prompt: str,
        candidate_response: str,
        critic_result: CriticResult,
    ) -> str:
        """Refines the candidate response using critique guidance."""
        pass


class IContinuousLearner(ABC):
    """Protocol for idle-state model evolution and LoRA adapter fine-tuning."""

    @abstractmethod
    def register_interaction(self, record: UserFeedbackSignal) -> None:
        """Caches user interactions into the daytime experience replay pool."""
        pass

    @abstractmethod
    def can_consolidate(self) -> bool:
        """Checks if system is in a safe idle state for offline consolidation."""
        pass

    @abstractmethod
    def run_nightly_consolidation(self) -> ConsolidationReport:
        """Executes sleep consolidation, fine-tuning, and regression gating."""
        pass
