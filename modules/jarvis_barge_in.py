import time
import logging
import threading
import numpy as np
import math
from dataclasses import dataclass
from typing import List
logger = logging.getLogger("JARVIS-BARGE-IN")

@dataclass
class AcousticFeatures:
    rms_dbfs: float
    zero_crossing_rate: float
    spectral_centroid: float
    urgency_score: float

class AcousticAnalyzer:
    """
    DSP Engine for real-time audio feature extraction.
    Computes RMS, ZCR, Spectral Centroid, and an Urgency Score.
    """
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._volume_history: List[float] = []
        self._history_maxlen = 15  

    def analyze_frame(self, pcm_bytes: bytes) -> AcousticFeatures:
        audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)
        
        if len(audio_data) == 0:
            return AcousticFeatures(-100.0, 0.0, 0.0, 0.0)

        rms_val = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
        rms_dbfs = 20 * math.log10(rms_val + 1e-9) - 20 * math.log10(32768)

        zero_crossings = np.nonzero(np.diff(audio_data > 0))[0]
        zcr = len(zero_crossings) / len(audio_data)

        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), 1.0 / self.sample_rate)
        
        spectrum_sum = np.sum(spectrum)
        if spectrum_sum == 0:
            spectral_centroid = 0.0
        else:
            spectral_centroid = np.sum(freqs * spectrum) / spectrum_sum

        self._volume_history.append(rms_dbfs)
        if len(self._volume_history) > self._history_maxlen:
            self._volume_history.pop(0)

        avg_history_rms = np.mean(self._volume_history[:-1]) if len(self._volume_history) > 1 else rms_dbfs
        rms_delta = rms_dbfs - avg_history_rms
        
        urgency = 0.0
        if rms_dbfs > -35:  
            
            if rms_delta > 12:
                urgency += 0.5
            elif rms_delta > 6:
                urgency += 0.2
            
            if spectral_centroid > 3000:
                urgency += 0.3
            elif spectral_centroid > 1500:
                urgency += 0.1
                
            if zcr > 0.15:
                urgency += 0.2
                
        urgency = min(1.0, max(0.0, urgency))
        
        return AcousticFeatures(
            rms_dbfs=float(rms_dbfs),
            zero_crossing_rate=float(zcr),
            spectral_centroid=float(spectral_centroid),
            urgency_score=float(urgency)
        )

class BargeInController:
    def __init__(self):
        self.is_playing = False
        self.should_stop = False
        self.urgency_threshold = 0.7  
        self.stream = None
        self.p = None
        self.is_running = False
        self.analyzer = AcousticAnalyzer(sample_rate=16000, chunk_size=1024)

    def start_playback(self):
        self.is_playing = True
        self.should_stop = False

    def end_playback(self):
        self.is_playing = False
        self.should_stop = False

    def start_monitoring(self):
        if self.is_running: return
        try:
            import pyaudio
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=16000,
                                      input=True,
                                      frames_per_buffer=1024)
            self.is_running = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            logger.info("Barge-in DSP stream (Advanced Acoustic Protocol) started.")
        except Exception as e:
            logger.error(f"Failed to start Barge-in stream: {e}")

    def _monitor_loop(self):
        while self.is_running:
            if not self.is_playing:
                time.sleep(0.1)
                continue
                
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                features = self.analyzer.analyze_frame(data)
                
                if features.urgency_score >= self.urgency_threshold:
                    logger.info(f"🚨 Barge-in triggered! Urgency Score: {features.urgency_score:.2f} (RMS: {features.rms_dbfs:.1f}dB, ZCR: {features.zero_crossing_rate:.2f})")
                    self.should_stop = True
                    self.is_playing = False
                    
            except Exception as e:
                logger.error(f"Error in Barge-in loop: {e}")
                time.sleep(1)

    def check_should_stop(self) -> bool:
        return self.should_stop

barge_in_controller = BargeInController()
