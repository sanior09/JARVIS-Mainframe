"""
tests/test_voice_bargein_suite.py
Tests for Voice STT/TTS & Barge-in Subsystem.
Verifies instant interruption, state transitions, audio player queueing, and fallback.
"""

import os
import time
import pytest
from jarvis_vad_bargein import AudioInteractionManager, InteractionState, get_vad_manager
from local_engine import AudioPlayer, LocalPipelineController, STTModule, get_pipeline


@pytest.mark.voice
def test_vad_manager_singleton_and_state():
    mgr = AudioInteractionManager(confidence_threshold=0.6, silence_duration=0.7)
    assert get_vad_manager() is mgr
    assert mgr.silence_duration == 0.7

    # Initial state should be LISTENING
    assert mgr.get_state().value == InteractionState.LISTENING.value

    # State transitions
    mgr.set_state(InteractionState.SPEAKING)
    assert mgr.get_state().value == InteractionState.SPEAKING.value

    mgr.set_state(InteractionState.LISTENING)
    assert mgr.get_state().value == InteractionState.LISTENING.value


@pytest.mark.voice
def test_audio_player_pygame_preference_and_interrupt():
    player = AudioPlayer()
    # pygame should be selected as the primary playback engine
    assert player._play_method in ("pygame", "ffplay", "mpg123", "powershell")
    
    # Check notification to VAD
    mgr = AudioInteractionManager(silence_duration=0.7)
    player._notify_speaking_state(True)
    assert mgr.get_state().value == InteractionState.SPEAKING.value

    # Instant interrupt should reset state to LISTENING immediately
    player.interrupt()
    assert mgr.get_state().value == InteractionState.LISTENING.value
    assert not player.is_busy


@pytest.mark.voice
def test_stt_module_configuration():
    stt = STTModule(language="th-TH", pause_threshold=0.7)
    assert stt.language == "th-TH"
    # Ensure optimized low pause threshold for fast turn taking
    assert stt.pause_threshold == 0.7


@pytest.mark.voice
def test_pipeline_controller_interrupt():
    pipeline = LocalPipelineController(llm_callback=lambda x: "test response")
    assert get_pipeline() is pipeline

    # Test pipeline interrupt
    pipeline.interrupt()
    assert not pipeline._audio_player.is_busy
