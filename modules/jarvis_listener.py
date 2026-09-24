

import json
import logging
import os
import time

import requests
import speech_recognition as sr
from dotenv import load_dotenv
import pygame

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
pygame.mixer.init()

load_dotenv()
logger = logging.getLogger("JarvisListener")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [LISTENER] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
JARVIS_URL = os.getenv("JARVIS_URL", "http://127.0.0.1:5050")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

def classify_utterance(text: str):
    """
    Returns (intent_class, cleaned_text)
    intent_class: DIRECTED_COMMAND | DIRECTED_QUESTION | NOT_DIRECTED
    """
    cleaned_text = text.strip()
    lowered_text = cleaned_text.lower()
    
    trigger_names = ["jarvis", "จาร์วิส", "จาหวิด", "จาวิส"]
    command_prefixes = ["เปิด", "ปิด", "ช่วย", "ขอดู", "แสดง", "รัน", "ค้นหา", "เล่น"]
    
    is_name_called = any(name in lowered_text for name in trigger_names)
    is_explicit_command = any(lowered_text.startswith(cmd) for cmd in command_prefixes)
    
    if is_name_called or is_explicit_command:
        
        if is_explicit_command or any(cmd in lowered_text for cmd in command_prefixes):
            logger.info("[HEURISTIC] Fast-tracked as DIRECTED_COMMAND")
            return "DIRECTED_COMMAND", cleaned_text
        else:
            logger.info("[HEURISTIC] Fast-tracked as DIRECTED_QUESTION")
            return "DIRECTED_QUESTION", cleaned_text

    if not GROQ_API_KEY:
        return "NOT_DIRECTED", cleaned_text
        
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        system_prompt = (
            "You are a speech intent classifier for J.A.R.V.I.S.\n"
            "Classify into EXACTLY ONE category:\n"
            "DIRECTED_COMMAND: command to JARVIS requiring action, minimal/no verbal reply.\n"
            "DIRECTED_QUESTION: question/chat directed at JARVIS requiring verbal answer.\n"
            "NOT_DIRECTED: speaker is NOT talking to JARVIS (talking to another person / self).\n"
            "You MUST reply ONLY in a valid JSON object format like exactly this: {\"class\": \"X\", \"cleaned\": \"text\"}\n"
            "IMPORTANT: For 'cleaned', YOU MUST KEEP THE EXACT ORIGINAL LANGUAGE AND WORDS. DO NOT TRANSLATE IT TO ENGLISH."
        )
        resp = client.chat.completions.create(
            model=GROQ_FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Speech: {cleaned_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=50
        )
        raw = resp.choices[0].message.content.strip()
        
        import re
        raw = re.sub(r'^```[a-zA-Z]*\n', '', raw)
        raw = re.sub(r'```$', '', raw).strip()
        
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {raw}")
            return "NOT_DIRECTED", cleaned_text
        
        intent = parsed.get("class", "NOT_DIRECTED")
        final_text = parsed.get("cleaned", cleaned_text)
            
        return intent, final_text
    except Exception as e:
        logger.error(f"Classifier error: {e}")
        return "NOT_DIRECTED", cleaned_text

import queue
import threading

class TTSWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.q = queue.Queue()
        self.is_running = True
        
    def clear_queue(self):
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
    def run(self):
        import tempfile
        import pygame
        import os
        from jarvis_barge_in import barge_in_controller

        while self.is_running:
            try:
                if barge_in_controller.check_should_stop():
                    self.clear_queue()
                    
                sentence = self.q.get(timeout=0.1)
                if sentence == "[STOP]":
                    break
                    
                if not sentence.strip():
                    continue
                    
                if barge_in_controller.check_should_stop():
                    continue

                # Generate TTS
                tts_resp = requests.post(f"{JARVIS_URL}/tts", json={"text": sentence}, timeout=15)
                if tts_resp.ok and tts_resp.content:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        f.write(tts_resp.content)
                        temp_path = f.name
                        
                    try:
                        if barge_in_controller.check_should_stop():
                            continue
                            
                        pygame.mixer.music.load(temp_path)
                        barge_in_controller.start_playback()
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy():
                            if barge_in_controller.check_should_stop():
                                pygame.mixer.music.stop()
                                logger.info("[BARGE-IN] Interrupted by user voice. Stopped TTS.")
                                self.clear_queue()
                                break
                            time.sleep(0.05)
                            
                        barge_in_controller.end_playback()
                    except Exception as e:
                        logger.error(f"TTS playback error: {e}")
                        barge_in_controller.end_playback()
                    finally:
                        try:
                            pygame.mixer.music.unload()
                        except:
                            pass
                            
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass
                                
            except queue.Empty:
                pass

tts_worker = TTSWorker()
tts_worker.start()

class ContinuousListener:
    """
    [PHASE 9] ฟังไมค์แบบต่อเนื่องใน Background Thread
    โทนี่ไม่ต้องพูดคำปลุก - JARVIS รับรู้บริบทเองโดยอัตโนมัติ
    """

    def __init__(self, energy_threshold: int = 400, pause_threshold: float = 0.8):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 600  
        self.recognizer.pause_threshold = 0.6   
        self.recognizer.dynamic_energy_threshold = False 
        self.is_running = False
        self._stop_fn = None
        self.last_processed = 0
        self.COOLDOWN = 1.5

    def _audio_callback(self, recognizer, audio):
        if time.time() - self.last_processed < self.COOLDOWN:
            return
        self.last_processed = time.time()
        try:
            
            text = self._transcribe_with_local_whisper(audio)
            
            if not text or len(text.strip()) < 2:
                return
            logger.info(f"Heard: \"{text}\"")
            intent_class, cleaned = classify_utterance(text)
            logger.info(f"Intent: {intent_class} | \"{cleaned}\"")
            if intent_class == "NOT_DIRECTED":
                return
            silent = (intent_class == "DIRECTED_COMMAND")
            self._dispatch(cleaned, silent=silent)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            logger.error(f"STT API error: {e}")
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def _transcribe_with_local_whisper(self, audio):
        """
        Transcribe audio using the Local Faster-Whisper model.
        """
        try:
            from jarvis_stt_local import transcribe_audio
            import tempfile
            import os
            
            # Save audio to a temporary file
            wav_data = audio.get_wav_data()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data)
                tmp_path = f.name
            
            try:
                text = transcribe_audio(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                    
            return text
        except Exception as e:
            logger.warning(f"Local Whisper failed, falling back to Google Web Speech: {e}")
            return self.recognizer.recognize_google(audio, language="th-TH,en-US")

    def _dispatch(self, text: str, silent: bool = False):
        try:
            if silent:
                resp = requests.post(
                    f"{JARVIS_URL}/chat",
                    json={"message": text, "silent": silent},
                    timeout=30
                )
                if resp.ok:
                    data = resp.json()
                    preview = data.get("response", "")[:80]
                    logger.info(f"JARVIS: {preview}")
                return

            resp = requests.post(
                f"{JARVIS_URL}/chat_stream",
                json={"message": text, "silent": False},
                stream=True,
                timeout=30
            )
            
            if resp.ok:
                current_sentence = ""
                for line in resp.iter_lines():
                    from jarvis_barge_in import barge_in_controller
                    if barge_in_controller.check_should_stop():
                        tts_worker.clear_queue()
                        break
                        
                    if not line:
                        continue
                        
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            status = data.get("status")
                            
                            if status == "streaming":
                                chunk = data.get("chunk", "")
                                current_sentence += chunk
                                
                                if any(p in chunk for p in ['.', '!', '?', '\n']) or (len(current_sentence) > 60 and ' ' in chunk):
                                    if current_sentence.strip():
                                        tts_worker.q.put(current_sentence.strip())
                                    current_sentence = ""
                                    
                            elif status == "interrupt":
                                tts_worker.clear_queue()
                                break
                                
                            elif status == "done":
                                if current_sentence.strip():
                                    tts_worker.q.put(current_sentence.strip())
                                break
                        except json.JSONDecodeError:
                            pass
            else:
                logger.warning(f"JARVIS returned {resp.status_code}")
        except Exception as e:
            logger.error(f"Dispatch error: {e}")

    def start(self):
        if self.is_running:
            logger.warning("Already running.")
            return
        try:
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 400
            
            mic = sr.Microphone()
            with mic as source:
                logger.info("Initializing microphone (Dynamic Threshold Active)...")
            self._stop_fn = self.recognizer.listen_in_background(
                mic, self._audio_callback, phrase_time_limit=8
            )
            self.is_running = True
            
            try:
                from jarvis_barge_in import barge_in_controller
                barge_in_controller.start_monitoring()
            except Exception as e:
                logger.error(f"Could not start Barge-in monitor: {e}")
                
            logger.info("[PHASE 9] AMBIENT INTELLIGENCE ARMED. Listening...")
        except Exception as e:
            logger.error(f"Failed to start: {e}")

    def stop(self):
        if self._stop_fn:
            self._stop_fn(wait_for_stop=False)
        self.is_running = False
        logger.info("Listener stopped.")

_instance = None

def get_listener():
    global _instance
    if _instance is None:
        _instance = ContinuousListener()
    return _instance

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    print("=" * 55)
    print("  PHASE 9: CONTINUOUS LISTENER — STANDALONE TEST")
    print("  พูดอะไรเข้าไมค์ — JARVIS จะวิเคราะห์บริบทเอง")
    print("  Ctrl+C เพื่อหยุด")
    print("=" * 55)
    listener = get_listener()
    listener.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        listener.stop()
