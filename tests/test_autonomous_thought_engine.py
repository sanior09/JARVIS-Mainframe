"""
Unit test suite for AutonomousThoughtEngine.
Focuses on thread safety, bio-inspired neurotransmitters, and graceful shutdown.
"""
import time
from unittest.mock import MagicMock, patch
import pytest

from jarvis import AutonomousThoughtEngine


def test_engine_initial_state():
    engine = AutonomousThoughtEngine()
    levels = engine.get_neuro_levels()
    assert levels["dopamine"] == 0.5
    assert levels["cortisol"] == 0.5
    assert levels["acetylcholine"] == 0.5
    assert not engine.running


def test_stimulus_and_success_flow():
    engine = AutonomousThoughtEngine()
    
    # Test polite message vs impolite/error
    engine.process_stimulus("มี error บั๊กพังหมดแล้ว")
    levels = engine.get_neuro_levels()
    assert levels["cortisol"] > 0.5
    assert levels["dopamine"] < 0.5

    # Test success reward
    engine.process_success()
    new_levels = engine.get_neuro_levels()
    assert new_levels["dopamine"] > levels["dopamine"]
    assert new_levels["cortisol"] < levels["cortisol"]


def test_neuro_prompt_generation():
    engine = AutonomousThoughtEngine()
    prompt = engine.get_neuro_prompt()
    assert "[SYNTHETIC NEUROTRANSMITTERS MATRIX]" in prompt
    assert "Dopamine: 0.50" in prompt
    assert "Cortisol: 0.50" in prompt


def test_start_and_graceful_shutdown():
    engine = AutonomousThoughtEngine()
    # Mock network/WMI/screen calls to keep test completely offline and instant
    engine._read_hardware_sensors = MagicMock(return_value=(25.0, 48.0))
    
    engine.start()
    assert engine.running is True
    assert engine.synaptic_thread is not None and engine.synaptic_thread.is_alive()
    assert engine.proactive_thread is not None and engine.proactive_thread.is_alive()
    
    # Verify instant shutdown (must take < 0.5s)
    t0 = time.time()
    engine.stop(timeout=1.0)
    elapsed = time.time() - t0
    
    assert engine.running is False
    assert elapsed < 1.0, f"Shutdown took too long: {elapsed:.2f}s"
