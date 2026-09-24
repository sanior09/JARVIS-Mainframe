"""
cognitive_tuner.py
Module 4: Cognitive Meta-Learner & Tuner

Responsible for evaluating system performance and mimicking biological neurotransmitters
to dynamically adjust J.A.R.V.I.S.'s cognitive state (e.g., Dopamine for confidence, Cortisol for stress).
Uses the Observer Pattern.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any

# Setup Module Logger
logger = logging.getLogger("CognitiveTuner")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class CognitiveException(Exception):
    """Base exception for the Cognitive Meta-Learner module."""
    pass


@dataclass
class NeuroState:
    """Represents the current levels of simulated neurotransmitters (0.0 to 1.0)."""
    dopamine: float = 0.5       # Reward, Motivation, Confidence
    cortisol: float = 0.5       # Stress, Alertness, Risk-aversion
    acetylcholine: float = 0.5  # Learning rate, Focus, Attention to detail

    def clamp(self):
        """Ensures all levels remain within biological bounds [0.0, 1.0]."""
        self.dopamine = max(0.0, min(1.0, self.dopamine))
        self.cortisol = max(0.0, min(1.0, self.cortisol))
        self.acetylcholine = max(0.0, min(1.0, self.acetylcholine))


class INeuroObserver(ABC):
    """Observer Interface that modules must implement to react to cognitive changes."""
    @abstractmethod
    def on_neuro_state_changed(self, new_state: NeuroState):
        pass


class PerformanceEvaluator:
    """Evaluates task execution to determine success and error rates."""
    
    def __init__(self):
        self.total_tasks = 0
        self.successful_tasks = 0
        self.total_execution_time = 0.0

    def record_task_result(self, success: bool, execution_time_sec: float):
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        self.total_execution_time += execution_time_sec

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks

    @property
    def average_execution_time(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_execution_time / self.total_tasks


class NeurotransmitterTuner:
    """
    Maintains the cognitive state and notifies observers when levels change.
    Uses Dependency Injection to accept a PerformanceEvaluator.
    """
    
    def __init__(self, evaluator: PerformanceEvaluator):
        self.evaluator = evaluator
        self.state = NeuroState()
        self.observers: List[INeuroObserver] = []

    def attach(self, observer: INeuroObserver):
        if observer not in self.observers:
            self.observers.append(observer)

    def detach(self, observer: INeuroObserver):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.on_neuro_state_changed(self.state)

    def tune_based_on_performance(self):
        """
        Adjusts neurotransmitters based on recent performance metrics.
        High success -> High Dopamine, Low Cortisol.
        Low success -> High Cortisol, High Acetylcholine (forces learning).
        """
        success_rate = self.evaluator.success_rate
        
        logger.info(f"Tuning cognition based on Success Rate: {success_rate:.2f}")

        if success_rate > 0.8:
            # Doing well: Boost confidence, lower stress
            self.state.dopamine += 0.1
            self.state.cortisol -= 0.1
            self.state.acetylcholine -= 0.05
        elif success_rate < 0.5:
            # Failing frequently: Spike stress, boost learning focus
            self.state.dopamine -= 0.2
            self.state.cortisol += 0.2
            self.state.acetylcholine += 0.2
        else:
            # Mediocre: Slight homeostasis shift towards baseline
            self.state.dopamine = (self.state.dopamine + 0.5) / 2
            self.state.cortisol = (self.state.cortisol + 0.5) / 2

        self.state.clamp()
        logger.info(f"New Cognitive State - DOP: {self.state.dopamine:.2f} | COR: {self.state.cortisol:.2f} | ACH: {self.state.acetylcholine:.2f}")
        
        self.notify_observers()


# --- Example Observer for Testing ---
class SystemPromptGenerator(INeuroObserver):
    """Example system that adjusts the LLM's system prompt based on stress and confidence."""
    
    def on_neuro_state_changed(self, new_state: NeuroState):
        logger.info("[Observer Triggered] Updating System Prompt Generator...")
        if new_state.cortisol > 0.7:
            logger.warning("-> System Prompt set to: HIGH CAUTION, DOUBLE-CHECK ALL CODE.")
        elif new_state.dopamine > 0.7:
            logger.info("-> System Prompt set to: CREATIVE, BOLD, FAST EXECUTION.")
        else:
            logger.info("-> System Prompt set to: BALANCED STANDARD MODE.")


if __name__ == "__main__":
    logger.info("--- Testing Cognitive Meta-Learner ---")
    
    evaluator = PerformanceEvaluator()
    tuner = NeurotransmitterTuner(evaluator)
    
    # Attach a sub-system to listen for cognitive changes
    prompt_gen = SystemPromptGenerator()
    tuner.attach(prompt_gen)
    
    # Simulate a series of successful tasks
    logger.info("Simulating 3 successful tasks...")
    for _ in range(3):
        evaluator.record_task_result(success=True, execution_time_sec=1.2)
    tuner.tune_based_on_performance()
    
    # Simulate a sudden failure cascade
    logger.info("\\nSimulating 5 consecutive failed tasks (e.g. API outage)...")
    for _ in range(5):
        evaluator.record_task_result(success=False, execution_time_sec=5.0)
    tuner.tune_based_on_performance()
