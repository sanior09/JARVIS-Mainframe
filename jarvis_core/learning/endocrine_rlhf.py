"""
jarvis_core/learning/endocrine_rlhf.py
─────────────────────────────────────────────────────────────────────────────
Reinforcement Learning with Endocrine Simulation (Bio-Inspired RLHF Engine).
Simulates neurochemical hormones (Dopamine, Cortisol, Serotonin, Adrenaline)
to dynamically shape reward functions and modulate LLM generation policies.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, Optional

from jarvis_core.learning.interfaces import (
    EndocrineState,
    IEndocrineRewardEngine,
    SentimentPolarity,
    UserFeedbackSignal,
)

logger = logging.getLogger("JARVIS-EndocrineRLHF")
logger.setLevel(logging.INFO)


class EndocrineHomeostasis:
    """
    Simulates natural biological decay and recovery of hormones towards baseline.
    Prevents permanent hormone saturation or chronic panic states.
    """

    BASELINE_DOPAMINE = 0.50
    BASELINE_CORTISOL = 0.15
    BASELINE_SEROTONIN = 0.70
    BASELINE_ADRENALINE = 0.20

    # Half-life decay rates in seconds
    DECAY_RATE_DOPAMINE = 0.05    # Fast decay
    DECAY_RATE_CORTISOL = 0.02    # Slower decay (stress lingers longer)
    DECAY_RATE_SEROTONIN = 0.01   # Very slow baseline buffer
    DECAY_RATE_ADRENALINE = 0.10  # Very fast spike decay

    @classmethod
    def apply_decay(cls, state: EndocrineState) -> EndocrineState:
        now = time.time()
        dt_minutes = max(0.0, (now - state.last_updated) / 60.0)

        if dt_minutes <= 0.01:
            return state

        # Exponential decay towards baseline: H(t) = H_base + (H_0 - H_base) * e^(-k * t)
        state.dopamine = cls.BASELINE_DOPAMINE + (state.dopamine - cls.BASELINE_DOPAMINE) * math.exp(-cls.DECAY_RATE_DOPAMINE * dt_minutes)
        state.cortisol = cls.BASELINE_CORTISOL + (state.cortisol - cls.BASELINE_CORTISOL) * math.exp(-cls.DECAY_RATE_CORTISOL * dt_minutes)
        state.serotonin = cls.BASELINE_SEROTONIN + (state.serotonin - cls.BASELINE_SEROTONIN) * math.exp(-cls.DECAY_RATE_SEROTONIN * dt_minutes)
        state.adrenaline = cls.BASELINE_ADRENALINE + (state.adrenaline - cls.BASELINE_ADRENALINE) * math.exp(-cls.DECAY_RATE_ADRENALINE * dt_minutes)

        state.last_updated = now
        return state


class EndocrineRewardEngine(IEndocrineRewardEngine):
    """
    Reinforcement learning coordinator mapping user sentiment and performance
    into neurochemical hormone fluctuations and runtime generation hyperparameters.
    """

    def __init__(self, initial_state: Optional[EndocrineState] = None) -> None:
        self.state = initial_state or EndocrineState()

    def ingest_feedback(self, feedback: UserFeedbackSignal) -> float:
        """
        Updates hormone levels based on interaction feedback and computes the
        total modulated scalar reward.
        """
        # 1. Update homeostasis baseline
        EndocrineHomeostasis.apply_decay(self.state)

        # 2. Extract feedback signals
        raw_reward = 0.0
        d_dopamine = 0.0
        d_cortisol = 0.0
        d_serotonin = 0.0
        d_adrenaline = 0.0

        if feedback.explicit_rating is not None:
            raw_reward += feedback.explicit_rating

        # Implicit sentiment effects
        if feedback.implicit_sentiment == SentimentPolarity.POSITIVE:
            raw_reward += 0.5
            d_dopamine += 0.25
            d_serotonin += 0.15
            d_cortisol -= 0.10
        elif feedback.implicit_sentiment == SentimentPolarity.NEGATIVE:
            raw_reward -= 0.6
            d_cortisol += 0.35
            d_dopamine -= 0.20
            d_serotonin -= 0.15
        elif feedback.implicit_sentiment == SentimentPolarity.CRITICAL_ERROR:
            raw_reward -= 1.2
            d_cortisol += 0.60
            d_adrenaline += 0.50
            d_dopamine -= 0.40

        # Execution failure penalties
        if not feedback.execution_success:
            raw_reward -= 0.5
            d_cortisol += 0.25

        # Direct correction reward shaping (User teaching is a long-term win)
        if feedback.user_correction_text:
            d_serotonin += 0.10  # Appreciative learning stance
            d_dopamine += 0.05

        # 3. Apply hormone deltas with strict clamping [0.0, 1.0]
        self.state.dopamine = max(0.0, min(1.0, self.state.dopamine + d_dopamine))
        self.state.cortisol = max(0.0, min(1.0, self.state.cortisol + d_cortisol))
        self.state.serotonin = max(0.0, min(1.0, self.state.serotonin + d_serotonin))
        self.state.adrenaline = max(0.0, min(1.0, self.state.adrenaline + d_adrenaline))
        self.state.last_updated = time.time()

        # 4. Modulated bio-inspired reward calculation
        # High dopamine amplifies positive reinforcement; high cortisol amplifies penalty
        modulated_reward = (
            raw_reward
            + (0.3 * self.state.dopamine)
            - (0.4 * self.state.cortisol)
            + (0.1 * self.state.serotonin)
        )

        logger.info(
            f"[Endocrine RLHF] Feedback ingested. Modulated Reward={modulated_reward:.3f} | "
            f"Hormones: {self.state.to_dict()}"
        )
        return float(modulated_reward)

    def get_current_state(self) -> EndocrineState:
        return EndocrineHomeostasis.apply_decay(self.state)

    def get_behavioral_modifiers(self) -> Dict[str, Any]:
        """
        Translates endocrine balance into dynamic LLM sampling settings and persona traits.
        """
        state = self.get_current_state()

        # Dopamine increases creativity & exploration (temperature), Cortisol forces precision
        base_temp = 0.4
        temp_delta = (state.dopamine * 0.4) - (state.cortisol * 0.3)
        effective_temp = max(0.1, min(0.9, base_temp + temp_delta))

        # Cortisol raises strictness and safety checking
        safety_strictness = 0.5 + (state.cortisol * 0.4) - (state.serotonin * 0.1)
        safety_strictness = max(0.2, min(1.0, safety_strictness))

        # Adrenaline enforces brevity and speed
        verbosity_penalty = state.adrenaline > 0.6

        # Persona tone formulation
        persona_directive = ""
        if state.cortisol > 0.6:
            persona_directive = "คำสั่งพิเศษ: รักษาความระมัดระวังสูงสุด ตรวจสอบผลลัพธ์ซ้ำซ้อน และใช้สำนวนที่นอบน้อมสุขุม"
        elif state.dopamine > 0.75:
            persona_directive = "คำสั่งพิเศษ: มีความมั่นใจสูง นำเสนอไอเดียเชิงรุก และกระตือรือร้นในการปฏิบัติงาน"
        elif state.adrenaline > 0.7:
            persona_directive = "คำสั่งพิเศษ: โหมดฉุกเฉิน/เร่งด่วน กระชับคำตอบสูงสุด ตัดคำฟุ่มเฟือย รายงานเฉพาะประเด็นสำคัญ"
        else:
            persona_directive = "คำสั่งพิเศษ: บุคลิก J.A.R.V.I.S. สุภาพ สุขุม มีไหวพริบ เลือกใช้คำลงท้ายให้เหมาะสมตามบริบท (ใช้ 'ครับ/ครับเจ้านาย' เมื่อรายงานหรือรับคำสั่งสำคัญ, ตัดคำลงท้ายเมื่อสรุปสถิติ/เทคนิค/ฉุกเฉิน/มุกประชดประชัน, และใช้คำตอบรับเป็นกันเองในการประสานงานทั่วไป)"

        return {
            "temperature": round(effective_temp, 2),
            "top_p": round(0.85 + (0.1 * state.dopamine), 2),
            "safety_strictness": round(safety_strictness, 2),
            "verbosity_penalty": verbosity_penalty,
            "persona_directive": persona_directive,
            "endocrine_levels": state.to_dict(),
        }
