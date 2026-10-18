import speech_recognition as sr
import threading
import logging
import time

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

    def start(self, callback):
        """Starts the background listener"""
        if self.is_listening:
            return
            
        self.on_wake_callback = callback
        self.is_listening = True
        self.is_paused = False
        
        # Start listening in the background (non-blocking)
        try:
            mic = sr.Microphone()
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.stop_listening_func = self.recognizer.listen_in_background(mic, self._audio_callback)
            logger.info("🎙️ [SYSTEM] Always-On Wake Word Engine Started. Say 'JARVIS' to wake me up.")
        except Exception as e:
            logger.error(f"❌ [WAKE WORD] Failed to start microphone: {e}")
            self.is_listening = False

    def stop(self):
        if self.stop_listening_func:
            self.stop_listening_func(wait_for_stop=False)
        self.is_listening = False
        self.is_paused = False
        logger.info("[WAKE WORD] Stopped.")

wake_word_engine = WakeWordEngine()
