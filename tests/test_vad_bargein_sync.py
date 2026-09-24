import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from jarvis_vad_bargein import AudioInteractionManager, get_vad_manager, InteractionState
from local_engine import AudioPlayer, get_pipeline, LocalPipelineController

def run_sync_test():
    print("[TEST] Initializing AudioInteractionManager...")
    mgr = AudioInteractionManager()
    assert get_vad_manager() is mgr, "Manager singleton mismatch"
    
    print("[TEST] Initializing AudioPlayer...")
    player = AudioPlayer()
    
    # Check default state is LISTENING
    assert mgr.get_state().value == InteractionState.LISTENING.value, f"Expected LISTENING, got {mgr.get_state()}"
    
    # Test setting speaking state
    player._notify_speaking_state(True)
    assert mgr.get_state().value == InteractionState.SPEAKING.value, f"Expected SPEAKING, got {mgr.get_state()}"
    
    # Test setting listening state
    player._notify_speaking_state(False)
    assert mgr.get_state().value == InteractionState.LISTENING.value, f"Expected LISTENING, got {mgr.get_state()}"
    
    # Test barge-in interrupt
    player._notify_speaking_state(True)
    player.interrupt()
    assert mgr.get_state().value == InteractionState.LISTENING.value, f"Expected LISTENING after interrupt, got {mgr.get_state()}"
    
    # Test pipeline singleton registration
    pipeline = LocalPipelineController(llm_callback=lambda x: "hello")
    assert get_pipeline() is pipeline, "Pipeline singleton registration failed"
    
    # Test pipeline interrupt
    pipeline.interrupt()
    
    print("SUCCESS: AudioPlayer, LocalPipelineController & VAD Barge-in sync verified successfully!")

if __name__ == "__main__":
    run_sync_test()
