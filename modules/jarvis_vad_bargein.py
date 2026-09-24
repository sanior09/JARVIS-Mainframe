import os
import threading
import queue
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any
import numpy as np

try:
    import torch
except ImportError:
    torch = None
    logging.warning("[JARVIS VAD] Torch is not installed. Silero VAD requires 'torch' and 'torchaudio'.")

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logging.warning("[JARVIS VAD] PyAudio is not installed. Required for microphone input.")

class InteractionState(Enum):
    """สถานะการโต้ตอบของ J.A.R.V.I.S."""
    LISTENING = 1   
    PROCESSING = 2  
    SPEAKING = 3    

_global_vad_manager: Optional['AudioInteractionManager'] = None

def get_vad_manager() -> Optional['AudioInteractionManager']:
    global _global_vad_manager
    if _global_vad_manager is not None:
        return _global_vad_manager
    import sys
    for mod_name in ("jarvis_vad_bargein", "modules.jarvis_vad_bargein"):
        mod = sys.modules.get(mod_name)
        if mod and getattr(mod, "_global_vad_manager", None) is not None:
            _global_vad_manager = mod._global_vad_manager
            return _global_vad_manager
    return None

class AudioInteractionManager:
    """
    คลาสสำหรับจัดการ VAD (Voice Activity Detection) และระบบ Barge-in
    ด้วย Silero VAD (Real-time, High-accuracy)
    """

    def __init__(self, 
                 confidence_threshold: float = 0.65,
                 silence_duration: float = 1.3):
        """
        :param confidence_threshold: ระดับความมั่นใจว่าเสียงที่เข้ามาคือเสียงพูด (0.0 ถึง 1.0)
        :param silence_duration: ระยะเวลา(วินาที)ที่ต้องเงียบติดกัน ถึงจะถือว่า "พูดจบ"
        """
        global _global_vad_manager
        _global_vad_manager = self
        import sys
        for mod_name in ("jarvis_vad_bargein", "modules.jarvis_vad_bargein"):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "_global_vad_manager"):
                mod._global_vad_manager = self

        self.confidence_threshold = confidence_threshold
        self.silence_duration = silence_duration
        
        self.sample_rate = 16000
        self.chunk_size = 512
        
        self._state_lock = threading.Lock()
        self._current_state = InteractionState.LISTENING
        self._is_running = False
        
        self._is_user_speaking = False
        self._last_speech_time = time.time()
        
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None
        self.on_barge_in: Optional[Callable[[], None]] = None
        
        self.pa = pyaudio.PyAudio() if pyaudio else None
        self.vad_model = None
        
        self._init_silero_vad()

    def _init_silero_vad(self) -> None:
        """ดาวน์โหลด/โหลดโมเดล Silero VAD จาก PyTorch Hub"""
        if not torch:
            return
            
        logging.info("[JARVIS VAD] Loading Silero VAD model (Local/Hub)...")
        try:
            
            self.device = torch.device('cpu')
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self.vad_model = model.to(self.device)
            self.get_speech_timestamps = utils[0]
            logging.info("[JARVIS VAD] Silero VAD model loaded successfully.")
        except Exception as e:
            logging.error(f"[JARVIS VAD] Failed to load Silero VAD: {e}")

    def set_state(self, new_state: Any) -> None:
        """ปรับสถานะของระบบ (Thread-safe) รองรับทั้ง Enum และข้ามโมดูล"""
        with self._state_lock:
            state_val = getattr(new_state, "value", new_state)
            cur_val = getattr(self._current_state, "value", self._current_state)
            if cur_val != state_val:
                try:
                    target = InteractionState(state_val) if isinstance(state_val, int) else new_state
                except (ValueError, TypeError):
                    target = new_state
                old_name = getattr(self._current_state, "name", str(self._current_state))
                new_name = getattr(target, "name", str(target))
                logging.info(f"[JARVIS VAD] State changed: {old_name} -> {new_name}")
                self._current_state = target

    def get_state(self) -> InteractionState:
        """ดึงสถานะปัจจุบันของระบบ"""
        with self._state_lock:
            return self._current_state

    def _audio_processing_worker(self) -> None:
        """เธรดสำหรับอัดเสียงและป้อนเข้า Silero VAD แบบ Real-time"""
        if not self.pa or not self.vad_model:
            logging.error("[JARVIS VAD] Missing dependencies (PyAudio or VAD Model). VAD stopped.")
            self._is_running = False
            return

        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logging.info("[JARVIS VAD] Microphone listening thread started.")
            
            torch.set_num_threads(1)
            
            while self._is_running:
                
                raw_data = stream.read(self.chunk_size, exception_on_overflow=False)
                
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_np)
                
                with torch.no_grad():
                    speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
                
                current_time = time.time()
                state = self.get_state()
                state_val = getattr(state, "value", state)
                is_jarvis_speaking = (state_val == InteractionState.SPEAKING.value)
                # Use higher threshold while speaking to prevent self-trigger from speaker output
                effective_threshold = 0.75 if is_jarvis_speaking else self.confidence_threshold
                
                if speech_prob > effective_threshold:
                    self._last_speech_time = current_time
                    
                    if not self._is_user_speaking:
                        
                        self._is_user_speaking = True
                        
                        if is_jarvis_speaking:
                            logging.warning("[JARVIS VAD] 🛑 BARGE-IN DETECTED! User interrupted Jarvis.")
                            if self.on_barge_in:
                                try:
                                    self.on_barge_in()
                                except Exception as be:
                                    logging.error(f"[JARVIS VAD] Barge-in callback error: {be}")
                            self._current_state = InteractionState.LISTENING
                        else:
                            logging.info("[JARVIS VAD] Speech Started.")
                            if self.on_speech_start:
                                try:
                                    self.on_speech_start()
                                except Exception as se:
                                    logging.error(f"[JARVIS VAD] Speech start callback error: {se}")
                else:
                    
                    if self._is_user_speaking:
                        
                        if (current_time - self._last_speech_time) > self.silence_duration:
                            self._is_user_speaking = False
                            logging.info("[JARVIS VAD] Speech Ended (Silence detected).")
                            if self.on_speech_end:
                                self.on_speech_end()
                                
        except Exception as e:
            logging.error(f"[JARVIS VAD] Audio processing error: {e}")
        finally:
            if 'stream' in locals() and stream.is_active():
                stream.stop_stream()
                stream.close()
            logging.info("[JARVIS VAD] Microphone thread stopped.")

    def start(self) -> None:
        """เริ่มระบบ VAD ในเบื้องหลัง"""
        if self._is_running:
            return
        
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._audio_processing_worker, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        """หยุดระบบ VAD"""
        self._is_running = False
        if hasattr(self, '_worker_thread') and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def __del__(self):
        self.stop()
        if self.pa:
            self.pa.terminate()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = AudioInteractionManager(confidence_threshold=0.6, silence_duration=1.5)
    
    manager.on_speech_start = lambda: print("\n[Event] 🟢 User started speaking...")
    manager.on_speech_end = lambda: print("\n[Event] 🔴 User stopped speaking.")
    manager.on_barge_in = lambda: print("\n[Event] 💥 BARGE-IN! Stopping Jarvis TTS...")
    
    manager.start()
    
    print("\n--- Test Scenario ---")
    print("1. Speak into microphone -> Should trigger Speech Start")
    print("2. Stop speaking for 1.5s -> Should trigger Speech End")
    
    time.sleep(10)
    
    print("\n--- Testing Barge-in ---")
    manager.set_state(InteractionState.SPEAKING)
    print("Jarvis is 'SPEAKING' now. Try talking to interrupt him!")
    
    time.sleep(10)
    manager.stop()
    print("Test Completed.")
