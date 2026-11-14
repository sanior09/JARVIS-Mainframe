import speech_recognition as sr
import threading
import logging
import time

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from modules.audio_capture import (
        CHANNELS,
        DEFAULT_BLOCKSIZE,
        DTYPE,
        SAMPLE_RATE,
        SAMPLE_WIDTH,
        pcm16_rms,
        record_utterance_from_stream,
    )
except ImportError:
    from audio_capture import (
        CHANNELS,
        DEFAULT_BLOCKSIZE,
        DTYPE,
        SAMPLE_RATE,
        SAMPLE_WIDTH,
        pcm16_rms,
        record_utterance_from_stream,
    )

logger = logging.getLogger("JarvisWakeWord")

class WakeWordEngine:
    """
    1. Always-On Wake Word (ระบบเรียกชื่อโดยไม่ต้องกดปุ่ม)
    Listens in the background for the wake word "Jarvis" or "จาร์วิส"
    """
    def __init__(self, wake_words=None):
        if wake_words is None:
            wake_words = [
                "jarvis", "จาร์วิส", "จาวิส", "จราวิส", "จาหวิด",
                "ok google", "กูเกิล", "โอเค กูเกิล", "โอเคกูเกิล"
            ]
        self.wake_words = wake_words
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.is_paused = False
        self.stop_listening_func = None
        self.on_wake_callback = None
        self._listener_thread = None

    def pause(self):
        """Temporarily suspend wake word processing (e.g. while STT or TTS is active)."""
        self.is_paused = True
        logger.debug("[WAKE WORD] Paused.")

    def resume(self):
        """Resume wake word listening."""
        self.is_paused = False
        logger.debug("[WAKE WORD] Resumed.")

    def _audio_callback(self, recognizer, audio):
        if self.is_paused:
            return

        try:
            # We use Google's free API for lightweight background scanning 
            text = recognizer.recognize_google(audio, language="th-TH").lower()
            logger.debug(f"[WAKE WORD] Heard: {text}")
            
            if any(ww in text for ww in self.wake_words):
                logger.info(f"🎙️ [WAKE WORD DETECTED] J.A.R.V.I.S. heard: '{text}'")
                if self.on_wake_callback:
                    import re
                    # If Google STT heard "ok google" when user spoke fast "โอเค จราวิส เปิดกูเกิล..."
                    # Normalize leading "ok google" into "เปิดกูเกิล " so user's intent to open Google is preserved
                    raw_cmd = re.sub(r'^(?:โอเค|ok)\s*(?:google|กูเกิล)\s*', 'เปิดกูเกิล ', text, flags=re.IGNORECASE)

                    # Extract inline command if spoken in the same breath
                    cmd = re.sub(
                        r'^(?:โอเค|ok|เฮ้|hey|ฮัลโหล|hello)?\s*[\(\)\[\]\{\},\.]*\s*(?:jarvis|จาร์วิส|จาวิส|จราวิส|จาหวิด|j\.?a\.?r\.?v\.?i\.?s)\s*[\(\)\[\]\{\},\.]*',
                        ' ',
                        raw_cmd,
                        flags=re.IGNORECASE
                    ).strip()
                    # Also strip any trailing/isolated wake word remnants
                    cmd = re.sub(
                        r'[\(\)\[\]\{\},\.]*\s*(?:jarvis|จาร์วิส|จาวิส|จราวิส|จาหวิด|j\.?a\.?r\.?v\.?i\.?s)\s*[\(\)\[\]\{\},\.]*',
                        ' ',
                        cmd,
                        flags=re.IGNORECASE
                    ).strip()
                    cmd = re.sub(r'^[^\wก-๙]+', '', cmd).strip()
                    
                    try:
                        self.on_wake_callback(command=cmd, full_text=text)
                    except TypeError:
                        self.on_wake_callback()
                    
        except sr.UnknownValueError:
            pass # Ignore silence/unrecognized
        except sr.RequestError as e:
            logger.error(f"[WAKE WORD] API Error: {e}")

    def _listen_loop(self):
        """Continuously captures default-mic audio via sounddevice and feeds wake-word recognizer."""
        if sd is None:
            logger.error("❌ [WAKE WORD] sounddevice is not installed.")
            self.is_listening = False
            return

        stream = None
        try:
            stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=DEFAULT_BLOCKSIZE,
                channels=CHANNELS,
                dtype=DTYPE,
            )
            stream.start()

            # Quick ambient noise calibration (~0.5s) on default Windows microphone
            ambient_samples = []
            for _ in range(16):
                if not self.is_listening:
                    return
                raw_data, _ = stream.read(DEFAULT_BLOCKSIZE)
                ambient_samples.append(pcm16_rms(bytes(raw_data)))
            avg_ambient = sum(ambient_samples) / max(1, len(ambient_samples))
            energy_threshold = max(250.0, avg_ambient * 2.2)

            logger.info("🎙️ [SYSTEM] Always-On Wake Word Engine Started (sounddevice default mic). Say 'JARVIS' to wake me up.")

            min_utterance_bytes = int(SAMPLE_RATE * SAMPLE_WIDTH * 0.25)
            while self.is_listening:
                if self.is_paused:
                    time.sleep(0.05)
                    continue

                pcm_bytes = record_utterance_from_stream(
                    stream,
                    sample_rate=SAMPLE_RATE,
                    blocksize=DEFAULT_BLOCKSIZE,
                    energy_threshold=energy_threshold,
                    pause_threshold=0.6,
                    listen_timeout=0.5,
                    phrase_limit=6.0,
                    should_stop=lambda: (not self.is_listening) or self.is_paused,
                )
                if len(pcm_bytes) >= min_utterance_bytes:
                    audio_data = sr.AudioData(pcm_bytes, SAMPLE_RATE, SAMPLE_WIDTH)
                    self._audio_callback(self.recognizer, audio_data)
        except Exception as e:
            logger.error(f"❌ [WAKE WORD] Failed in sounddevice listener: {e}")
            self.is_listening = False
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

    def start(self, callback):
        """Starts the background listener"""
        if self.is_listening:
            return
        if sd is None:
            logger.error("❌ [WAKE WORD] Failed to start microphone: sounddevice is not installed.")
            return

        self.on_wake_callback = callback
        self.is_listening = True
        self.is_paused = False

        def _stop_listener(wait_for_stop=False):
            self.is_listening = False
            if wait_for_stop and self._listener_thread and self._listener_thread is not threading.current_thread():
                self._listener_thread.join(timeout=1.5)

        self.stop_listening_func = _stop_listener
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="WakeWordSounddeviceLoop",
        )
        self._listener_thread.start()

    def stop(self):
        self.is_listening = False
        self.is_paused = False
        if self.stop_listening_func:
            self.stop_listening_func(wait_for_stop=False)
        if self._listener_thread and self._listener_thread is not threading.current_thread():
            self._listener_thread.join(timeout=1.0)
        logger.info("[WAKE WORD] Stopped.")

wake_word_engine = WakeWordEngine()
