"""
jarvis_core/learning
─────────────────────────────────────────────────────────────────────────────
Advanced Autonomous Learning and Evolution Subsystem for J.A.R.V.I.S.
Components:
1. Continuous / Online Learning (Nightly Sleep Consolidation)
2. Reinforcement Learning with Endocrine Simulation (Bio-RLHF)
3. Semantic Long-Term Memory (Local Vector DB RAG)
4. Self-Reflection / Critic Circuit (Internal Review & Gating)
5. Unified Cognitive Evolution Orchestrator
─────────────────────────────────────────────────────────────────────────────
"""

from jarvis_core.learning.continuous_learning import (
    ContinuousLearningEngine,
    ExperienceReplayBuffer,
    GoldenRegressionBenchmark,
    IdleStateDetector,
)
from jarvis_core.learning.critic_circuit import (
    GroundingVerifier,
    LogicCoherenceEvaluator,
    SafetySentinel,
    SelfReflectionCriticCircuit,
)
from jarvis_core.learning.endocrine_rlhf import (
    EndocrineHomeostasis,
    EndocrineRewardEngine,
)
from jarvis_core.learning.interfaces import (
    ConsolidationReport,
    CriticResult,
    EndocrineState,
    IContinuousLearner,
    ICriticCircuit,
    IEndocrineRewardEngine,
    ISemanticMemoryStore,
    LearningState,
    MemoryRecord,
    MemoryTier,
    SentimentPolarity,
    UserFeedbackSignal,
)
from jarvis_core.learning.orchestrator import CognitiveEvolutionOrchestrator
from jarvis_core.learning.semantic_memory import (
    ChromaVectorAdapter,
    FallbackDenseEmbedding,
    SemanticLongTermMemory,
)

__all__ = [
    # Orchestrator
    "CognitiveEvolutionOrchestrator",
    # Continuous Learning
    "ContinuousLearningEngine",
    "ExperienceReplayBuffer",
    "IdleStateDetector",
    "GoldenRegressionBenchmark",
    # Endocrine RLHF
    "EndocrineRewardEngine",
    "EndocrineHomeostasis",
    # Semantic Memory
    "SemanticLongTermMemory",
    "ChromaVectorAdapter",
    "FallbackDenseEmbedding",
    # Critic Circuit
    "SelfReflectionCriticCircuit",
    "SafetySentinel",
    "GroundingVerifier",
    "LogicCoherenceEvaluator",
    # Interfaces & DTOs
    "MemoryRecord",
    "MemoryTier",
    "EndocrineState",
    "UserFeedbackSignal",
    "CriticResult",
    "ConsolidationReport",
    "LearningState",
    "SentimentPolarity",
    "ISemanticMemoryStore",
    "IEndocrineRewardEngine",
    "ICriticCircuit",
    "IContinuousLearner",
]
