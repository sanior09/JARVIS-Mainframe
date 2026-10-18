"""
╔══════════════════════════════════════════════════════════════════════╗
║         J.A.R.V.I.S. LOCAL ENGINE - VOICE INTERACTION MODULE        ║
║         Production-ready Voice Pipeline (Headless/Background)       ║
╚══════════════════════════════════════════════════════════════════════╝

สถาปัตยกรรม (Architecture):
  ┌─────────────────────────────────────────────────────────────┐
  │  LocalPipelineController (Main Orchestrator)                 │
  │  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
  │  │  STTModule   │ -> │ LLM Callback │ -> │  TTSModule    │  │
  │  │  (PyAudio +  │    │  (Groq API)  │    │  (edge-tts)   │  │
  │  │  SpeechRec.) │    │              │    │               │  │
  │  └──────────────┘    └──────────────┘    └───────┬───────┘  │
  │                                                   │          │
  │                                          ┌────────▼───────┐  │
  │                                          │  AudioPlayer   │  │
  │                                          │  (Queue-based) │  │
  │                                          └────────────────┘  │
  └─────────────────────────────────────────────────────────────┘

การเชื่อมต่อกับ jarvis.py (Integration):
    from local_engine import LocalPipelineController
    engine = LocalPipelineController(llm_callback=call_groq_model_sync)
    engine.start()
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
import traceback
import ctypes

try:
    from jarvis_stt_local import transcribe_audio, LocalSTTEngine
    stt_engine = LocalSTTEngine()
    # Warmup STT model in background thread so it doesn't block startup but is ready for first command
    import threading
    threading.Thread(target=stt_engine.warmup, daemon=True).start()
except ImportError:
    pass

def log_error(msg):
    logger.error(msg)

import os
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable, Optional, Tuple

try:
    from dynamic_island import send_to_island
except ImportError:
    def send_to_island(*args, **kwargs): pass

MIC_LOCK = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LocalEngine")

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
    logger.warning("[DEP] SpeechRecognition not installed. STT will be disabled.")

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    logger.warning("[DEP] edge-tts not installed. TTS will be disabled.")

PIPELINE_SHORT_WAKE_WORDS = [
    "jarvis", "จาร์วิส", "จาวิส", "จาร์วิสครับ", "จาร์วิสอยู่ไหม", "จาวิสครับ", "jarvis อยู่มั้ย", "จาร์วิสอยู่มั้ย"
]
PIPELINE_STOP_WORDS = [
    "หยุด", "หยุดพูด", "เงียบ", "เงียบหน่อย", "พอแล้ว", "พอได้แล้ว", "stop", "shut up", "พอละ", "หยุดก่อน", "ไม่พูดแล้ว"
]
PIPELINE_STANDBY_WORDS = [
    "jarvis กลับพักผ่อนได้", "jarvis กลับเข้าโหมด", "จาร์วิสพักผ่อนได้", "จาร์วิสเข้าโหมด", "กลับพักผ่อนได้", "เข้าโหมดสแตนบาย", "พักผ่อนได้"
]
# Backward-compatibility aliases
short_wake_words = PIPELINE_SHORT_WAKE_WORDS
stop_words = PIPELINE_STOP_WORDS
standby_words = PIPELINE_STANDBY_WORDS

class STTModule:
    """
    ระบบแปลงเสียงพูดเป็นข้อความ (Speech-to-Text) แบบ Offline-first
    
    Strategy:
        1. Google Speech Recognition (ต้องใช้เน็ต, ฟรี, ไม่ต้อง API Key)
        2. ออฟไลน์ Fallback: คืน string ว่าง เพื่อให้ระบบหลักจัดการต่อ
    
    Design Principle:
        - Blocking I/O ทั้งหมด → ต้องรันภายใน Thread เสมอ
        - ถ้า microphone ดับหรือ network ล่ม จะไม่ทำให้ process หลักแครช
    """

    def __init__(
        self,
        language: str = "th-TH",
        energy_threshold: int = 800,
        pause_threshold: float = 0.7,
        listen_timeout: float = 5.0,
        phrase_limit: float = 30.0,
    ) -> None:
        """
        Args:
            language: รหัสภาษาสำหรับ Google Speech Recognition (เช่น "th-TH", "en-US")
            energy_threshold: ค่า sensitivity ของ microphone (300-4000, ยิ่งต่ำยิ่งไวต่อเสียง)
            pause_threshold: วินาทีที่หยุดพูดแล้วถือว่าจบคำสั่ง (0.7s เพื่อการตอบสนองที่กระชับ ไม่ต้องรอนาน)
            listen_timeout: วินาทีที่รอก่อนจะยอมแพ้ถ้าไม่ยินเสียงใดๆ เลย
            phrase_limit: วินาทีสูงสุดที่ยอมรับเสียงพูดต่อครั้ง
        """
        self.language = language
        self.pause_threshold = pause_threshold
        self.listen_timeout = listen_timeout
        self.phrase_limit = phrase_limit
        self.is_listening: bool = False
        self._last_interaction_time: float = 0.0

        if HAS_SR:
            self._recognizer = sr.Recognizer()
            env_thresh = os.getenv("STT_ENERGY_THRESHOLD")
            if env_thresh and env_thresh.isdigit():
                energy_threshold = int(env_thresh)
            self._recognizer.energy_threshold = energy_threshold
            self._recognizer.pause_threshold = pause_threshold
            self._recognizer.non_speaking_duration = min(0.3, pause_threshold - 0.1)
            self._recognizer.dynamic_energy_threshold = False
            
            mic_idx_str = os.getenv("MIC_INDEX")
            self._device_index = int(mic_idx_str) if mic_idx_str and mic_idx_str.isdigit() else None
            
            logger.info(f"STT: Initialized (Language={language}, Threshold={energy_threshold}, MicIndex={self._device_index})")
        else:
            self._recognizer = None
            logger.error("STT: SpeechRecognition not available.")

    def listen_and_transcribe(self) -> str:
        """
        [Blocking I/O] เปิดไมโครโฟน รอเสียง และแปลงเป็นข้อความ
        
        Returns:
            str: ข้อความที่แปลงได้, หรือ "" หากฟังไม่ได้ยิน/เกิด Error
        """
        if not HAS_SR or self._recognizer is None:
            logger.error("STT: Module unavailable. Returning empty string.")
            return ""

        self.is_listening = True
        logger.info("STT: 🎤 Microphone active — waiting for speech...")
        send_to_island("LISTENING", "Waiting for command...")

        try:
            with MIC_LOCK:
                with sr.Microphone(device_index=self._device_index) as source:
                    
                    audio = self._recognizer.listen(
                        source,
                        timeout=self.listen_timeout,
                        phrase_time_limit=self.phrase_limit,
                    )
            
            send_to_island("THINKING", "Processing speech...")
            import os
            
            duration = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
            if duration < 0.5:
                logger.warning(f"STT: Audio too short ({duration:.2f}s). Skipping.")
                return ""

            wav_data = audio.get_wav_data()
            logger.info("STT: Audio captured — transcribing via Local Faster-Whisper...")
            
            import audioop
            rms = audioop.rms(audio.frame_data, audio.sample_width)
            emotion_tag = ""
            min_rms = int(os.getenv("STT_MIN_RMS", "700"))
            if rms < min_rms:
                logger.debug(f"STT: Audio RMS too low ({rms} < {min_rms}). Ignoring ambient noise/silence.")
                return ""
            
            if rms > 15000:
                emotion_tag = "[EMOTION: URGENT/LOUD] "
            elif rms < 800:
                emotion_tag = "[EMOTION: CALM/SOFT] "
            
            text = ""
            try:
                # [PRIMARY] Local Faster-Whisper
                import tempfile
                
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
                
                # Normalize STT phonetic misspellings (Comprehensive JARVIS Dictionary - MEGA EXPANSION)
                typo_map = {
                    # --- Jarvis Name Variations ---
                    "โอวิท": "จาร์วิส", "จ้าวิทย์": "จาร์วิส", "ชาวนี้": "จาร์วิส", "จาวิส": "จาร์วิส", 
                    "จาร์วิท": "จาร์วิส", "จาร์วิต": "จาร์วิส", "จาบิด": "จาร์วิส", "จาวิทย์": "จาร์วิส",
                    "จาวิต": "จาร์วิส", "จาบิส": "จาร์วิส", "ชาร์วิส": "จาร์วิส", "ชาร์วิต": "จาร์วิส",
                    "ตาวิทย์": "จาร์วิส", "ตาบิด": "จาร์วิส", "จาวิท": "จาร์วิส", "ดาวิส": "จาร์วิส",
                    "ทราวิส": "จาร์วิส", "จาหวิด": "จาร์วิส", "จาวิด": "จาร์วิส", "ชาริส": "จาร์วิส",
                    "จราวิส": "จาร์วิส", "จราวิด": "จาร์วิส", "จะระวิส": "จาร์วิส", "จารวิส": "จาร์วิส",
                    "จราวิต": "จาร์วิส", "โอเคจราวิส": "โอเค จาร์วิส", "โอเค จราวิส": "โอเค จาร์วิส",
                    "ok จราวิส": "ok จาร์วิส", "ok จาร์วิส": "ok จาร์วิส",
                    
                    # --- Camera & Vision ---
                    "ช่วยมือ": "ชูมือ", "ชู้มือ": "ชูมือ", "ชู่มือ": "ชูมือ", "ชูมื่อ": "ชูมือ",
                    "ชมมือ": "ชูมือ", "ชูมื้อ": "ชูมือ", "ดูกลอง": "ดูกล้อง", "ดุกรอง": "ดูกล้อง",
                    "สะแกนกล้อง": "สแกนกล้อง", "สแกรนกล้อง": "สแกนกล้อง", "เวบแคม": "เว็บแคม", "เวปแคม": "เว็บแคม",
                    
                    # --- Smart Home & Hardware ---
                    "เปิดไฟล์": "เปิดไฟ", "ปิดไฟล์": "ปิดไฟ", "เปิดไฟล": "เปิดไฟ", "แอ": "แอร์",
                    "แอร": "แอร์", "แอรื": "แอร์", "พัดล่ม": "พัดลม", "ฮ่องนอน": "ห้องนอน",
                    "สมาร์ทโฮมม์": "สมาร์ทโฮม", "สมาทโฮม": "สมาร์ทโฮม", "สะมาทโฮม": "สมาร์ทโฮม",
                    "ปลั๊กพ่วง": "ปลั๊กไฟ", "ปักไฟ": "ปลั๊กไฟ", "ปักพ่วง": "ปลั๊กไฟ", "ทีวี": "TV",
                    "หน้าจ้อ": "หน้าจอ", "พัดลมคอม": "พัดลม", "การ์ดจ้อ": "การ์ดจอ", "กาดจอ": "การ์ดจอ",
                    
                    # --- Tactical & System ---
                    "ชิดท่านาควมพ่อ": "เช็คสถานะคอมให้หน่อย", "ชิดท่านาควม": "เช็คสถานะคอม",
                    "ชิดทานาควม": "เช็คสถานะคอม", "ชิดทานา": "เช็คสถานะ", "เช็คสตาร์ดักคอม": "เช็คสถานะคอม",
                    "ศูนย์ยุทธกาล": "ศูนย์ยุทธการ", "สูนยุทธการ": "ศูนย์ยุทธการ",
                    "เรดาไซเบอร์": "เรดาร์ไซเบอร์", "เลด้าไซเบอร์": "เรดาร์ไซเบอร์", "เรด้าร์ไซเบอร์": "เรดาร์ไซเบอร์",
                    "แผนทีสามมิติ": "แผนที่ 3 มิติ", "สามมิติ": "3 มิติ",
                    "ประมวนผล": "ประมวลผล", "วิเคราะ": "วิเคราะห์", "วิเคาะ": "วิเคราะห์",
                    "อุณภูมิ": "อุณหภูมิ", "อุนหภูมิ": "อุณหภูมิ", "สภาพอากาส": "สภาพอากาศ",
                    
                    # --- General Terms ---
                    "คอมพิวเตอ": "คอมพิวเตอร์", "เจ้าน้าย": "เจ้านาย", "จ้านาย": "เจ้านาย",
                    "ขอบคุน": "ขอบคุณ", "คัฟ": "ครับ", "ครัช": "ครับ", "คาบ": "ครับ", "คับ": "ครับ",
                    "โอเคร": "โอเค", "โอก": "โอเค", "ยกเลิกคำสั้ง": "ยกเลิกคำสั่ง", "ยกเลิด": "ยกเลิก",
                    "ชั่งมัน": "ช่างมัน", "ม่ายเอา": "ไม่เอา", "ทามงาน": "ทำงาน", "ทามไม": "ทำไม",
                    
                    # --- Gaming & Entertainment ---
                    "ตีมอส": "ตีบอส", "ตีมอด": "ตีบอส", "หาเคส": "หาเควส", "เขวส": "เควส", "เคลวส": "เควส",
                    "ดิสคอด": "Discord", "ดิสคอร์ด": "Discord", "สตีม": "Steam", "สะตีม": "Steam",
                    "ยูทูป": "YouTube", "ยูทูบ": "YouTube", "เน็ตฟริก": "Netflix", "เน็ตฟลิก": "Netflix",
                    "สปอติฟาย": "Spotify", "สปอดิฟาย": "Spotify", "เล่นเพลง": "เปิดเพลง",
                    "เกมเพล": "Gameplay", "แบล็กมิด": "Black Myth", "หงอคง": "Wukong", "ไซเบอร์พัง": "Cyberpunk",
                    
                    # --- Hacking & Cyber Security ---
                    "ติดบัก": "ติดบั๊ก", "ติดบล็อก": "ติดบั๊ก", "แก้บัก": "แก้บั๊ก",
                    "โดนแทค": "โดนแฮก", "สั่งแพ็ค": "สั่งแฮก", "เพนเทสส": "Pentest", "เพนเทส": "Pentest",
                    "ไวรัส": "Virus", "ไวลัส": "Virus", "มัลแวร์": "Malware", "มัลแวร": "Malware",
                    "ทรอยแจน": "Trojan", "โทรจัน": "Trojan", "แบคดอ": "Backdoor", "แบคดอร์": "Backdoor",
                    "ช่องโหว่": "Vulnerability", "หาช่องโหว่": "Scan Vulnerability",
                    "ดีดอส": "DDoS", "สแกนพอด": "Scan Port", "เอ็นแมพ": "Nmap", "เอนแมบ": "Nmap",
                    
                    # --- Developer & Programming ---
                    "พายทอน": "Python", "ไพทอน": "Python", "ไพธอน": "Python", "แพทอน": "Python",
                    "จาวาสคิป": "JavaScript", "จาวาสคริป": "JavaScript", "จาว่า": "Java", "ซีพลัส": "C++",
                    "ซีชาร์ป": "C#", "โกแลง": "Golang", "รัสท": "Rust", "รัส": "Rust",
                    "รีแอค": "React", "รีแอด": "React", "โหนดเจเอส": "Node.js", "โนดเจเอส": "Node.js",
                    "กิทฮับ": "GitHub", "กิตฮับ": "GitHub", "กิตแลป": "GitLab",
                    "เทอมินอล": "Terminal", "เทอมินัล": "Terminal", "คอมมานไลน์": "Command Line",
                    "ดาต้าเบส": "Database", "ดาด้าเบด": "Database", "มายเอสคิวแอล": "MySQL", "โปสเกรส": "PostgreSQL",
                    "เจสัน": "JSON", "เจซัน": "JSON", "เจเอสโอเอ็น": "JSON", "เอกเอมเอล": "XML",
                    "เอพีไอ": "API", "เอยูพีไอ": "API", "เอนพอย": "Endpoint", "สคริป": "Script",
                    
                    # --- AI & Machine Learning ---
                    "พร็อม": "Prompt", "พอม": "Prompt", "พร้อมท": "Prompt", "พ้อม": "Prompt",
                    "โมเดว": "Model", "แอลแอลเอ็ม": "LLM", "เอจีไอ": "AGI", "แชทจีพีที": "ChatGPT",
                    "เจมินาย": "Gemini", "เจมินี่": "Gemini", "คลาวด์": "Claude", "คร้อด": "Claude",
                    "โอลาม่า": "Ollama", "โอราม่า": "Ollama", "แลนเชน": "LangChain", "เวกเตอ": "Vector",
                    
                    # --- Operating System & Files ---
                    "อัพเดท": "Update", "อัพเดต": "Update", "วินโดว": "Windows", "วินโดว์": "Windows",
                    "แมคโอเอส": "macOS", "ลินุก": "Linux", "ลีนุกซ์": "Linux", "อูบุนตู": "Ubuntu",
                    "รีบูท": "Reboot", "รีสตาด": "Restart", "ชัตดาว": "Shutdown", "ชัตดาวน์": "Shutdown",
                    "ไฟล์ซิบ": "Zip File", "ไดเรกทอรี": "Directory", "โฟลเดอ": "Folder", "โฟเดอร์": "Folder",
                    "ไฟวอล": "Firewall", "ไฟร์วอล": "Firewall", "แอนตี้ไวรัส": "Antivirus",
                    
                    # --- Advanced Developer Jargon (TITAN EXPANSION) ---
                    "เทลวิน": "Tailwind", "เทลวินด": "Tailwind", "ซีเอสเอส": "CSS", 
                    "เน็กเจเอส": "Next.js", "เนกเจเอส": "Next.js", "ไทป์สคริป": "TypeScript", 
                    "ไทปสคริป": "TypeScript", "แองกูล่า": "Angular", "วิวจีเอส": "Vue.js",
                    "ฟลัตเตอร์": "Flutter", "ฟัตเตอ": "Flutter", "ดาร์ท": "Dart",
                    "ดอกเกอร์": "Docker", "ด็อกเกอ": "Docker", "คูเบอเนตีส": "Kubernetes",
                    "คูเบอร์เนทีส": "Kubernetes", "เจดับบลิวที": "JWT", "เรสทีพีไอ": "REST API",
                    "วีพีเอน": "VPN", "วีพีเอ็น": "VPN", "เอสเอสเอช": "SSH", "เอสเอสแอล": "SSL",
                    "โอออธ": "OAuth", "โอสออธ": "OAuth", "กาดจอ": "GPU", "จีพียู": "GPU",
                    "ซีพียู": "CPU", "เมนบอด": "Mainboard", "มาเตอบอด": "Motherboard",
                    "แอดเดรส": "Address", "พอร์ต": "Port", "ไวไฟ": "Wi-Fi", "แลน": "LAN",
                    "ไอพี": "IP", "แมกแอดเดรส": "MAC Address", "บลูทูต": "Bluetooth",
                    "แพนด้า": "Pandas", "เทนเซอ": "TensorFlow", "ไซคิต": "Scikit-Learn",
                    "โอเพนเอไอ": "OpenAI", "โอเพ่นเอไอ": "OpenAI", "มีดเจอนี": "Midjourney",
                    "ดิฟฟิวชัน": "Stable Diffusion", "สเตเบิลดิฟฟิวชัน": "Stable Diffusion",
                    "คิวอาโค้ด": "QR Code", "บาร์โคด": "Barcode", "เอ็กเซล": "Excel", 
                    "พาวเวอพอย": "PowerPoint", "ไมโครซอฟ": "Microsoft", "กูเกิ้ล": "Google"
                }
                for typo, correct in typo_map.items():
                    text = text.replace(typo, correct)
                
                # Filter Whisper hallucinations with whitespace & punctuation normalization
                import re
                norm_text = re.sub(r'[\s\W_]+', '', text.lower())
                boilerplate_hallucinations = [
                    "โปรดติดตามตอนต่อไป", "โปรโย", "ซับไทยโดย", "แปลโดย", "รับชมต่อได้ที่", 
                    "ติดตามตอนต่อไป", "สําหรับวันนี้ขอลาไปก่อน",
                    "อย่าลืมกดไลค์กดแชร์", "อย่าลืมกดไลค์", "อย่าลืมกดติดตาม", "อย่าลืมกดsubscribe",
                    "ขอบคุณที่รับชมครับ", "ขอบคุณที่รับชมค่ะ", "ขอบคุณที่รับชม", "พบกันใหม่คลิปหน้า",
                    "สนับสนุนช่อง", "amaraorg", "ซับไทย", "โปรดติดตามตอนต่อไปครับ", "จบตอน",
                    "ติดตามชมตอนต่อไป", "ซับไทยโดยอารีฟีน", "ขอบคุณสำหรับการรับชม",
                    "สั่งงานทั่วไปและถามตอบ", "บทสนทนาภาษาไทย", "กับผู้ช่วยจาร์วิสสั่งงาน"
                ]
                isolated_tokens = ["ที่ผม", "พิสดิ์", "ขอบคุณครับ", "ขอบคุณค่ะ"]
                
                is_hallucination = False
                if len(norm_text) < 2:
                    is_hallucination = True
                elif norm_text in [re.sub(r'[\s\W_]+', '', t.lower()) for t in isolated_tokens]:
                    is_hallucination = True
                else:
                    for h in boilerplate_hallucinations:
                        norm_h = re.sub(r'[\s\W_]+', '', h.lower())
                        if norm_h and norm_h in norm_text:
                            is_hallucination = True
                            break

                if is_hallucination:
                    logger.warning(f"STT: Whisper Hallucination detected ('{text.strip()}'). Ignoring.")
                    return ""
            except Exception as e2:
                logger.error(f"STT: Groq API Error - {e2}. Falling back to Google...")
                # [FALLBACK] Google Speech Recognition
                text = self._recognizer.recognize_google(audio, language=self.language)
                if 'typo_map' in locals():
                    for typo, correct in typo_map.items():
                        text = text.replace(typo, correct)
            
            logger.info(f"STT: ✅ Transcribed → '{text.strip()}' (RMS: {rms})")
            return emotion_tag + text.strip()

        except sr.WaitTimeoutError:
            logger.warning("STT: No speech detected within timeout. Returning empty.")
            send_to_island("STANDBY", "")
            return ""
        except sr.UnknownValueError:
            logger.warning("STT: Speech was detected but could not be understood.")
            send_to_island("STANDBY", "")
            return ""
        except sr.RequestError as e:
            logger.error(f"STT: Google Speech API error — {e}")
            send_to_island("STANDBY", "")
            return ""
        except OSError as e:
            logger.error(f"STT: Microphone hardware error — {e}")
            send_to_island("STANDBY", "")
            return ""
        except (AssertionError, AttributeError) as e:
            logger.error(f"STT: ❌ ขัดข้อง! ระบบเข้าถึงไมโครโฟนไม่ได้ (Error: {e}, type: {type(e)}). โปรดตรวจสอบ PyAudio หรือ set_mic.bat")
            send_to_island("ERROR", "Mic error")
            import time
            time.sleep(5)  
            return ""
        except Exception as e:
            logger.error(f"STT: Unexpected error — {e}", exc_info=True)
            send_to_island("STANDBY", "")
            return ""
        finally:
            self.is_listening = False

class AudioPlayer:
    """
    จัดการคิวและเล่นไฟล์เสียง MP3 แบบ Thread-safe
    
    ป้องกัน Race Condition: เสียงพูดซ้อนทับกันไม่ได้ — ต้องรอเสียงก่อนหน้าจบก่อน
    Garbage Collection: ลบ Temp File ทันทีหลังเล่นเสร็จ ป้องกันขยะสะสมบนดิสก์
    
    Strategy (เล่นเสียง MP3):
        1. subprocess + ffplay (ถ้ามี ffmpeg)
        2. subprocess + mpg123 (ถ้ามี mpg123)
        3. Windows built-in: playsound / winsound fallback
    """

    def __init__(self) -> None:
        self._audio_queue: queue.Queue[Optional[Tuple[str, bool]]] = queue.Queue()
        self._is_running: bool = False
        self._is_playing: bool = False
        self._current_process: Optional[subprocess.Popen] = None
        self._stop_playback: bool = False
        self._worker_thread: Optional[threading.Thread] = None
        self._play_method: Optional[str] = self._detect_play_method()
        logger.info(f"AudioPlayer: Initialized (play_method={self._play_method})")

    def _notify_speaking_state(self, is_speaking: bool) -> None:
        """แจ้งสถานะให้ Silero VAD ทราบว่ากำลังพูดหรือหยุดพูด"""
        try:
            try:
                from jarvis_vad_bargein import get_vad_manager, InteractionState
            except ImportError:
                from modules.jarvis_vad_bargein import get_vad_manager, InteractionState
            vm = get_vad_manager()
            if vm:
                target_state = InteractionState.SPEAKING if is_speaking else InteractionState.LISTENING
                vm.set_state(target_state)
        except Exception:
            pass

    def _detect_play_method(self) -> Optional[str]:
        """ตรวจหาวิธีเล่นเสียงที่มีในระบบ โดยใช้ pygame เป็นลำดับแรกเพื่อ Zero-latency in-process playback"""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            logger.info("AudioPlayer: ✅ Selected 'pygame' as primary fast in-process audio engine.")
            return "pygame"
        except Exception as pe:
            logger.warning(f"AudioPlayer: pygame init failed ({pe}), falling back to external player.")

        try:
            result = subprocess.run(
                ["ffplay", "-version"], capture_output=True, timeout=3
            )
            if result.returncode == 0:
                return "ffplay"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            result = subprocess.run(
                ["mpg123", "--version"], capture_output=True, timeout=3
            )
            if result.returncode == 0:
                return "mpg123"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            import playsound  
            return "playsound"
        except ImportError:
            pass

        if sys.platform == "win32":
            return "powershell"

        logger.error("AudioPlayer: No audio playback method found!")
        return None

    def start(self) -> None:
        """เริ่ม Background Worker Thread สำหรับเล่นเสียง"""
        if self._is_running:
            return
        self._is_running = True
        self._stop_playback = False
        self._worker_thread = threading.Thread(
            target=self._playback_worker, daemon=True, name="AudioPlayer-Worker"
        )
        self._worker_thread.start()
        logger.info("AudioPlayer: Worker thread started.")

    def stop(self) -> None:
        """หยุดการทำงานอย่างปลอดภัย (Graceful Shutdown)"""
        self.interrupt()
        self._is_running = False
        self._audio_queue.put(None)  
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        logger.info("AudioPlayer: Stopped.")

    def interrupt(self) -> None:
        """[Instant Barge-in] สั่งตัดเสียงพูดปัจจุบันทันที และล้างคิวที่รออยู่ทั้งหมด"""
        self._stop_playback = True
        
        # 1. Stop pygame playback instantly if active
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                logger.info("AudioPlayer: 🛑 Pygame music stopped and unloaded.")
        except Exception:
            pass

        # 2. Kill running audio subprocess immediately if any
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                self._current_process.kill()
                logger.info("AudioPlayer: ⏹ Active playback process terminated.")
            except Exception as e:
                logger.warning(f"AudioPlayer: Failed to terminate process: {e}")
        self._current_process = None

        # 3. Clear all queued audio files and clean up
        while not self._audio_queue.empty():
            try:
                item = self._audio_queue.get_nowait()
                if item:
                    fpath, del_after = item
                    if del_after and os.path.exists(fpath):
                        try: os.remove(fpath)
                        except: pass
                self._audio_queue.task_done()
            except Exception:
                break

        self._is_playing = False
        self._notify_speaking_state(False)
        send_to_island("STANDBY", "")
        logger.info("AudioPlayer: 🛑 Playback interrupted and queue drained.")

    def enqueue(self, file_path: str, delete_after_play: bool = True) -> None:
        """
        เพิ่มไฟล์เสียงเข้าคิว

        Args:
            file_path: พาทไปยังไฟล์ MP3
            delete_after_play: True = ลบไฟล์หลังจากเล่นเสร็จ (Resource Cleanup)
        """
        self._audio_queue.put((file_path, delete_after_play))
        logger.debug(f"AudioPlayer: Enqueued '{file_path}' (Queue size={self._audio_queue.qsize()})")

    @property
    def is_busy(self) -> bool:
        """True ถ้ากำลังเล่นเสียงหรือมีงานในคิว"""
        return self._is_playing or not self._audio_queue.empty()

    def _play_file(self, file_path: str) -> None:
        """เล่นไฟล์เสียงโดยใช้วิธีที่ตรวจพบ รองรับการหยุดเล่นทันทีแบบ Zero-latency"""
        self._stop_playback = False
        self._notify_speaking_state(True)
        try:
            if self._play_method == "pygame":
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and not self._stop_playback and self._is_running:
                        time.sleep(0.02)
                    if self._stop_playback or not self._is_running:
                        pygame.mixer.music.stop()
                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass
                except Exception as pge:
                    logger.warning(f"AudioPlayer: pygame error ({pge}), trying fallback.")
            elif self._play_method == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path]
                self._current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while self._current_process and self._current_process.poll() is None:
                    if self._stop_playback or not self._is_running:
                        self._current_process.terminate()
                        try:
                            self._current_process.wait(timeout=0.2)
                        except subprocess.TimeoutExpired:
                            self._current_process.kill()
                        break
                    time.sleep(0.04)
            elif self._play_method == "mpg123":
                cmd = ["mpg123", "-q", file_path]
                self._current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while self._current_process and self._current_process.poll() is None:
                    if self._stop_playback or not self._is_running:
                        self._current_process.terminate()
                        try: self._current_process.wait(timeout=0.2)
                        except: self._current_process.kill()
                        break
                    time.sleep(0.04)
            elif self._play_method == "playsound":
                cmd = [sys.executable, "-c", f"import playsound; playsound.playsound(r'{file_path}', block=True)"]
                self._current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while self._current_process and self._current_process.poll() is None:
                    if self._stop_playback or not self._is_running:
                        self._current_process.terminate()
                        try: self._current_process.wait(timeout=0.2)
                        except: self._current_process.kill()
                        break
                    time.sleep(0.04)
            elif self._play_method == "powershell":
                ps_cmd = (
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"
                    if file_path.endswith(".wav")
                    else f"$player = New-Object System.Windows.Media.MediaPlayer; "
                    f"$player.Open([Uri]::new((Resolve-Path '{file_path}'))); "
                    f"$player.Play(); Start-Sleep -s 5; $player.Stop()"
                )
                self._current_process = subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while self._current_process and self._current_process.poll() is None:
                    if self._stop_playback or not self._is_running:
                        self._current_process.terminate()
                        try: self._current_process.kill()
                        except: pass
                        break
                    time.sleep(0.04)
            else:
                logger.error("AudioPlayer: No playback method available.")
        except Exception as e:
            logger.error(f"AudioPlayer: Playback error — {e}")
        finally:
            self._current_process = None
            self._notify_speaking_state(False)

    def _playback_worker(self) -> None:
        """Worker Loop: ดึงงานจาก Queue แล้วเล่นทีละไฟล์ตามลำดับ"""
        while self._is_running:
            try:
                item = self._audio_queue.get(timeout=0.5)

                if item is None:
                    break

                file_path, delete_after = item
                if self._stop_playback:
                    self._audio_queue.task_done()
                    continue

                self._is_playing = True
                send_to_island("SPEAKING", "")

                try:
                    if os.path.exists(file_path):
                        logger.info(f"AudioPlayer: ▶ Playing '{os.path.basename(file_path)}'")
                        self._play_file(file_path)
                    else:
                        logger.warning(f"AudioPlayer: File not found — '{file_path}'")
                finally:
                    self._is_playing = False
                    send_to_island("STANDBY", "")
                    
                    if delete_after and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.debug(f"AudioPlayer: 🗑 Cleaned up '{os.path.basename(file_path)}'")
                        except OSError as e:
                            logger.warning(f"AudioPlayer: Cleanup failed — {e}")

                self._audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"AudioPlayer: Worker error — {e}", exc_info=True)
                self._is_playing = False
                send_to_island("STANDBY", "")
                time.sleep(0.2)  

class TTSModule:
    """
    แปลงข้อความเป็นเสียงพูดผ่าน edge-tts (Microsoft Neural Voice)
    
    Voice Default: th-TH-NiwatNeural (เสียงชาย ภาษาไทย คุณภาพสูง)
    Alternative:   th-TH-PremwadeeNeural (เสียงหญิง ภาษาไทย)
    
    Design:
        - สร้างเสียงแบบ Async (edge-tts เป็น asyncio-based)
        - ส่ง file path ให้ AudioPlayer จัดคิวเล่นต่อ
        - ตัวเองไม่บล็อก Pipeline — เพียงแค่ generate และส่งต่อ
    """

    def __init__(
        self,
        voice: str = "th-TH-NiwatNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        audio_player: Optional[AudioPlayer] = None,
    ) -> None:
        """
        Args:
            voice: เสียงที่ใช้ (ดูรายการทั้งหมด: edge-tts --list-voices)
            rate: ความเร็วในการพูด เช่น "+10%" เร็วขึ้น 10%, "-10%" ช้าลง
            pitch: ระดับความทุ้ม/แหลม เช่น "-5Hz" ทุ้มลง, "+5Hz" แหลมขึ้น
            volume: ระดับเสียง เช่น "+50%" ดังขึ้น
            audio_player: instance ของ AudioPlayer (ถ้าไม่ส่งมา จะสร้างใหม่)
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self._player = audio_player or AudioPlayer()
        self._is_generating: bool = False
        logger.info(f"TTS: Initialized (Voice={voice}, Rate={rate}, Pitch={pitch})")

    @property
    def is_busy(self) -> bool:
        return self._is_generating or self._player.is_busy

    def interrupt(self) -> None:
        """Cancel speech generation and interrupt active playback."""
        self._is_generating = False
        self._player.interrupt()

    async def wait_until_played(self, guard_delay: float = 0.4) -> None:
        """Wait until generation completes and AudioPlayer finishes playing or gets interrupted."""
        while self._is_generating:
            if getattr(self._player, '_stop_playback', False):
                break
            await asyncio.sleep(0.04)
        while self._player.is_busy:
            if getattr(self._player, '_stop_playback', False):
                break
            await asyncio.sleep(0.04)
        if guard_delay > 0 and not getattr(self._player, '_stop_playback', False):
            await asyncio.sleep(guard_delay)

    def speak(self, text: str) -> None:
        """
        [Non-blocking] แปลงข้อความเป็น MP3 และส่งเข้าคิวเล่น
        
        ฟังก์ชันนี้รันได้จาก Thread ใดก็ได้ ไม่ block Process หลัก
        
        Args:
            text: ข้อความที่ต้องการพูด
        """
        if not text or not text.strip():
            return
        
        if "[SILENT_EXECUTION]" in text:
            text = text.replace("[SILENT_EXECUTION]", "").strip()
            if not text:
                return

        if not HAS_EDGE_TTS:
            logger.error("TTS: edge-tts not available. Cannot speak.")
            return

        self._is_generating = True
        t = threading.Thread(
            target=self._generate_and_enqueue,
            args=(text.strip(),),
            daemon=True,
            name="TTS-Generator",
        )
        t.start()

    def _generate_and_enqueue(self, text: str) -> None:
        """
        [Internal — runs in separate thread]
        สร้าง Temp MP3 file จาก edge-tts แล้วส่งเข้า AudioPlayer Queue
        """
        temp_path = ""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_tts_")
            os.close(fd)

            asyncio.run(self._async_generate(text, temp_path))

            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                logger.info(f"TTS: ✅ Generated audio ({os.path.getsize(temp_path)} bytes) → enqueuing...")
                self._player.enqueue(temp_path, delete_after_play=True)
            else:
                logger.error("TTS: Generated file is empty or missing.")
                self._cleanup(temp_path)

        except Exception as e:
            logger.error(f"TTS: Generation failed — {e}", exc_info=True)
            self._cleanup(temp_path)
        finally:
            self._is_generating = False

    def _apply_phonetic_dictionary(self, text: str) -> str:
        """
        แปลงคำศัพท์ภาษาอังกฤษที่เจอบ่อยเป็นคำอ่านภาษาไทย เพื่อให้เสียงไม่เพี้ยนและยังเป็นเสียงคนเดียวกัน
        ครอบคลุมศัพท์เทคโนโลยี, AI, Coding, Hardware, Gaming, Smart Home, และ J.A.R.V.I.S. Sci-Fi (กว่า 1,140+ คำ)
        """
        if not text:
            return ""
        import re

        replacements = {
            # --- Numbers & Symbols ---
            "144hz": "หนึ่งร้อยสี่สิบสี่เฮิรตซ์", "240hz": "สองร้อยสี่สิบเฮิรตซ์",

            # --- A ---
            "acceleration": "แอกเซลเลอเรชัน", "accept": "แอ็กเซปต์", "accepted": "แอ็กเซปเต็ด",
            "access": "แอ็กเซส", "access point": "แอคเซสพอยต์", "accordion": "แอคคอร์เดียน",
            "account": "แอคเคานต์", "ace": "เอซ", "action": "แอ็กชัน",
            "activate": "แอคติเวต", "activating": "แอคติเวตติ้ง", "activity": "แอกทิวิตี",
            "actuator": "แอกทูเอเตอร์", "ad": "แอด", "add": "แอด",
            "address": "แอดเดรส", "admin": "แอดมิน", "administrator": "แอดมินิสเตรเตอร์",
            "aether": "อีเทอร์", "afk": "เอเอฟเค", "agent": "เอเจนต์",
            "agentic": "เอเจนติก", "agents": "เอเจนต์", "agile": "เอไจล์", "agoda": "อโกด้า",
            "agree": "อะกรี", "ai": "เอไอ", "aim": "เอม",
            "airbnb": "แอร์บีเอ็นบี", "airpods": "แอร์พอดส์", "airtag": "แอร์แท็ก",
            "alarm": "อะลาร์ม", "alert": "อะเลิร์ต", "algorithm": "อัลกอริทึม",
            "allow": "อะลาว", "almond": "อะเมิ่น", "alpha": "อัลฟ่า", "alt": "อัลต์",
            "alter": "อัลเทอร์", "always": "ออลเวย์ส", "amazon": "แอมะซอน",
            "amazon alexa": "แอมะซอนอเล็กซ่า", "amd": "เอเอ็มดี", "analysis": "อะนาลิซิส",
            "analyzing": "อะนาไลซิง", "android": "แอนดรอยด์", "angular": "แองกูลาร์",
            "animation": "แอนิเมชัน", "ansible": "แอนซิเบิล", "apache": "อาปาเช่",
            "apex": "เอเปกส์", "apex legends": "เอเปกส์เลเจนดส์", "api": "เอพีไอ",
            "app": "แอป", "apple": "แอปเปิล", "apple homekit": "แอปเปิลโฮมคิต",
            "apple music": "แอปเปิลมิวสิก", "apple vision pro": "แอปเปิลวิชันโปร", "apple watch": "แอปเปิลวอตช์",
            "application": "แอปพลิเคชัน", "approve": "แอพพรูฟ", "ar": "เออาร์",
            "arc": "อาร์ค", "arc reactor": "อาร์ครีแอ็กเตอร์", "arc reactor core": "อาร์ครีแอ็กเตอร์คอร์",
            "architecture": "อาร์คิเทคเจอร์", "archive": "อาร์ไคฟ์", "arduino": "อาร์ดูอิโน",
            "argument": "อาร์กิวเมนต์", "arguments": "อาร์กิวเมนต์", "armor": "อาร์เมอร์",
            "array": "อาร์เรย์", "article": "อาร์ทิเคิล", "artificial intelligence": "อาร์ติฟิเชียลอินเทลลิเจนซ์",
            "ascii": "แอสกี", "aside": "อะไซด์", "ask": "อาสก์", "assert": "แอสเสิร์ต",
            "assign": "แอสไซน์", "async": "อะซิงก์", "asynchronous": "อะซิงโครนัส",
            "attribute": "แอตทริบิวต์", "attributes": "แอตทริบิวต์", "audio": "ออดิโอ",
            "auth0": "ออธซีโร่", "authentic": "ออเทนติค", "authenticate": "ออเทนทิเคต",
            "authentication": "ออเทนติเคชั่น", "authorization": "ออธอไรเซชัน", "authorize": "ออทอไรซ์",
            "auto": "ออโต้", "automatic": "ออโตเมติค", "automation": "ออโตเมชั่น",
            "autonomous agent": "ออโตโนมัสเอเจนต์", "avengers": "อเวนเจอร์ส", "avg": "แอฟเวอเรจ",
            "await": "อะเวต", "aws": "เอดับเบิลยูเอส", "azure": "อาชัวร์",

            # --- B ---
            "backend": "แบ็กเอนด์", "background": "แบ็คกราวด์", "backlog": "แบ็กล็อก",
            "backup": "แบ็คอัพ", "backward": "แบ็คเวิร์ด", "bad": "แบด",
            "bad gateway": "แบดเกตเวย์", "bad request": "แบดรีเควสต์", "badge": "แบดจ์",
            "ban": "แบน", "bandwidth": "แบนด์วิดท์", "banner": "แบนเนอร์",
            "barcode": "บาร์โค้ด", "barge-in": "บาร์จอิน", "barn door protocol": "บาร์นดอร์โปรโตคอล", "base64": "เบสซิกซ์ตี้โฟร์",
            "bash": "แบช", "battery": "แบตเตอรี่", "battle royale": "แบทเทิลรอยัล",
            "benchmark": "เบนช์มาร์ก", "best": "เบสต์", "beta": "เบต้า",
            "better": "เบ็ตเทอร์", "bias": "ไบแอส", "binary": "ไบนารี",
            "bios": "ไบออส", "bitbucket": "บิตบักเก็ต", "blend": "เบลนด์",
            "block": "บล็อก", "blocking": "บล็อกกิง", "blue screen": "บลูสกรีน",
            "blue team": "บลูทีม", "bluetooth": "บลูทูธ", "board": "บอร์ด",
            "body": "บอดี้", "boolean": "บูลีน", "boost": "บูสท์",
            "bootstrap": "บูตสแตรป", "border": "บอร์เดอร์", "bottom": "บอตทอม",
            "box": "บ็อกซ์", "branch": "แบรนช์", "break": "เบรก",
            "browser": "เบราว์เซอร์", "brute force": "บรูทฟอร์ซ", "bsod": "บีเอสโอดี",
            "bucket": "บักเก็ต", "buff": "บัฟ", "buffer overflow": "บัฟเฟอร์โอเวอร์โฟลว์",
            "bug": "บั๊ก", "build": "บิลด์", "bun": "บัน",
            "business": "บิสซิเนส", "button": "บัตทอน",

            # --- C ---
            "c": "ซี", "c#": "ซีชาร์ป", "c++": "ซีพลัสพลัส",
            "cable": "เคเบิล", "cache": "แคช", "caddy": "แคดดี",
            "calendar": "แคเลนดาร์", "call": "คอล", "call of duty": "คอลออฟดิวตี้",
            "callback": "คอลแบ็ก", "camera": "กล้อง", "cancel": "แคนเซิล",
            "canvas": "แคนวาส", "capacity": "คาพาซิตี", "carousel": "คารูเซล",
            "carry": "แครี่", "case": "เคส", "catch": "แคช",
            "category": "แคทิกอรี", "cause": "คอส", "center": "เซ็นเตอร์",
            "certificate": "เซอร์ทิฟิเคต", "championship": "แชมเปียนชิป", "charge": "ชาร์จ",
            "charging": "ชาร์จจิ้ง", "chat": "แชท", "chatbot": "แชตบอต",
            "chatgpt": "แชตจีพีที", "check": "เช็ค", "checkbox": "เช็กบ็อกซ์",
            "chipset": "ชิปเซ็ต", "chromadb": "โครมาดีบี", "chrome": "โครม",
            "ci/cd": "ซีไอซีดี", "class": "คลาส", "classes": "คลาส",
            "claude": "คล็อด", "claude 3": "คล็อดสาม", "claude 3 haiku": "คล็อดสามไฮกุ",
            "claude 3 opus": "คล็อดสามโอปุส", "claude 3.5 sonnet": "คล็อดสามจุดห้าซอนเนต", "clean slate protocol": "คลีนสเลตโปรโตคอล",
            "clear": "เคลียร์", "clerk": "เคลิร์ก", "click": "คลิก",
            "client": "ไคลเอนต์", "clock": "คล็อก", "close": "โคลส",
            "clothes": "โคลธส์", "closure": "โคลสเชอร์", "cloud": "คลาวด์", "cloudflare": "คลาวด์แฟลร์",
            "cluster": "คลัสเตอร์", "clutch": "คลัตช์", "cmd": "ซีเอ็มดี",
            "co-op": "โคออป", "code": "โค้ด", "color": "คัลเลอร์",
            "column": "คอลัมน์", "com port": "คอมพอร์ต", "command": "คอมมานด์",
            "command line": "คอมมานด์ไลน์", "command prompt": "คอมมานด์พรอมต์", "comment": "คอมเมนต์",
            "commit": "คอมมิต", "company": "คอมพานี", "compile": "คอมไพล์",
            "compile time": "คอมไพล์ไทม์", "compiler": "คอมไพเลอร์", "complete": "คอมพลีท",
            "component": "คอมโพเนนต์", "compose": "คอมโพส", "compress": "คอมเพรส",
            "compute": "คอมพิวต์", "computer": "คอมพิวเตอร์", "computer vision": "คอมพิวเตอร์วิชัน",
            "concept": "คอนเซปต์", "concurrency": "คอนเคอเรนซี", "conda": "คอนดา",
            "condition": "คอนดิชัน", "conference": "คอนเฟอเรนซ์", "config": "คอนฟิก",
            "configmap": "คอนฟิกแมป", "configuration": "คอนฟิกกิวเรชัน", "configure": "คอนฟิกเกอร์",
            "confirm": "คอนเฟิร์ม", "conflict": "คอนฟลิกต์", "connect": "คอนเนค",
            "connected": "คอนเนคเต็ด", "connection": "คอนเนคชั่น", "constants": "คอนสแตนต์",
            "container": "คอนเทนเนอร์", "context": "คอนเท็กซ์", "context window": "คอนเทกซ์วินโดว์",
            "continue": "คอนทินิว", "continuous deployment": "คอนทินิวอัสดีพลอยเมนต์", "continuous integration": "คอนทินิวอัสอินทิเกรชัน",
            "control": "คอนโทรล", "controller": "คอนโทรลเลอร์", "cookie": "คุกกี้",
            "cookies": "คุกกี้", "cooldown": "คูลดาวน์", "cooler": "คูลเลอร์",
            "cooling": "คูลลิง", "coordinate": "โคออร์ดิเนต", "copy": "ก็อปปี้",
            "cors": "คอร์ส", "count": "เคานต์", "counter strike": "เคาน์เตอร์สไตรก์",
            "cpu": "ซีพียู", "crash": "แครช", "create": "ครีเอต",
            "created": "ครีเอตเต็ด", "credential": "ครีเดนเชียล", "critical": "คริติคอล",
            "cross join": "ครอสจอยน์", "cross site scripting": "ครอสไซต์สคริปติง", "cryptography": "คริปโตกราฟี",
            "css": "ซีเอสเอส", "csv": "ซีเอสวี", "cupboard": "เคอะเบิด", "current": "เคอร์เรนต์",
            "cut": "คัต", "cyberpunk": "ไซเบอร์พังก์", "cyberpunk 2077": "ไซเบอร์พังก์สองศูนย์เจ็ดเจ็ด",
            "cybersecurity": "ไซเบอร์ซีเคียวริตี้",

            # --- D ---
            "dall-e": "ดอลลี่", "dall-e 3": "ดอลลี่ทรี", "danger": "แดนเจอร์",
            "dart": "ดาร์ต", "data": "เดต้า", "database": "ดาต้าเบส",
            "datadog": "ดาต้าด็อก", "dataset": "ดาต้าเซ็ต", "date": "เดต",
            "day": "เดย์", "deactivate": "ดีแอคติเวต", "deafen": "เดฟเฟน",
            "debt": "เด็ท", "debug": "ดีบัก", "debugger": "ดีบักเกอร์", "decline": "ดีไคลน์",
            "decode": "ดีโค้ด", "decoder": "ดีโค้ดเดอร์", "decrypt": "ดีคริปต์", "decryption": "ดีคริปชัน",
            "decryptor": "ดีคริปเตอร์", "deep": "ดีป", "deep learning": "ดีปเลิร์นนิง",
            "deepseek": "ดีพซีค", "deepseek r1": "ดีพซีคอาร์วัน", "deepseek v3": "ดีพซีควีสาม",
            "default": "ดีฟอลต์", "defense system": "ดีเฟนส์ซิสเต็ม", "delete": "ดีลีต",
            "deno": "ดีโน่", "deny": "ดีนาย", "dependency": "ดีเพนเดนซี่",
            "deploy": "ดีพลอย", "deployment": "ดีพลอยเมนต์", "desert": "เดสเสิร์ท",
            "deserialize": "ดีซีเรียลไลซ์", "design": "ดีไซน์", "dessert": "ดิสเซิร์ท",
            "desktop": "เดสก์ท็อป", "detect": "ดีเทค",
            "detected": "ดีเทคเต็ด", "developer": "ดีเวลลอปเปอร์", "development": "ดีเวลลอปเมนต์",
            "device": "ดีไวซ์", "diablo": "ดิอาโบล", "diagnostic": "ไดแอกนอสติก",
            "dialog": "ไดอะล็อก", "dictionary": "ดิกชันนารี", "dimension": "ไดเมนชัน",
            "directory": "ไดเรกทอรี", "disagree": "ดิสอะกรี", "disconnect": "ดิสคอนเนค",
            "discord": "ดิสคอร์ด", "disk": "ดิสก์", "dislike": "ดิสไลก์",
            "disney plus": "ดิสนีย์พลัส", "disney+": "ดิสนีย์พลัส", "display": "ดิสเพลย์",
            "displayport": "ดิสเพลย์พอร์ต", "django": "จังโก้", "dlss": "ดีแอลเอสเอส",
            "dlss 3": "ดีแอลเอสเอสทรี", "dns": "ดีเอ็นเอส", "docker": "ด็อกเกอร์",
            "dockerfile": "ด็อกเกอร์ไฟล์", "domain": "โดเมน", "done": "ดัน",
            "dota": "โดต้า", "dota 2": "โดต้าทู", "downgrade": "ดาวน์เกรด",
            "download": "ดาวน์โหลด", "downtime": "ดาวน์ไทม์", "dps": "ดีพีเอส",
            "drag": "แดรก", "driver": "ไดรเวอร์", "drivers": "ไดรเวอร์",
            "drone": "โดรน", "drop": "ดรอป", "dropdown": "ดรอปดาวน์",
            "dynamic": "ไดนามิก", "dynamic island": "ไดนามิกไอแลนด์", "dynamic island hud": "ไดนามิกไอแลนด์ฮัด",

            # --- E ---
            "e-sports": "อี-สปอร์ต", "earphone": "เอียร์โฟน", "ec2": "อีซีทู",
            "edge": "เอดจ์", "edit": "อีดิต", "editor": "เอดิเตอร์",
            "effect": "เอฟเฟกต์", "elasticsearch": "อีลาสติกเสิร์ช", "elden ring": "เอลเดนริง",
            "elevenlabs": "อิเลเวนแล็บส์", "else": "เอลส์", "email": "อีเมล",
            "embedding": "เอมเบดดิง", "escape": "อิสเคป", "embeddings": "เอมเบดดิงส์", "empty": "เอมป์ตี",
            "encode": "เอนโค้ด", "encoder": "เอนโค้ดเดอร์", "encrypt": "เอ็นคริปท์", "encryption": "เอ็นคริปชั่น",
            "endpoint": "เอนด์พอยต์", "energy": "เอนเนอร์จี", "enter": "เอนเทอร์",
            "enterprise": "เอนเทอร์ไพรซ์", "environment": "เอนไวรอนเมนต์", "environment variable": "เอนไวรอนเมนต์แวเรียเบิล",
            "epic": "อีปิก", "epoch": "เอพ็อก", "error": "เออ-เร่อ",
            "esp32": "อีเอสพีสามสอง", "esp8266": "อีเอสพีแปดสองหกหก", "esports": "อีสปอร์ต",
            "ethernet": "อีเธอร์เน็ต", "evaluate": "อีแวลูเอต", "event": "อีเวนต์",
            "event bus": "อีเวนต์บัส", "event-driven": "อีเวนต์ดริฟเวน", "exceeded": "เอ็กซีดเด็ด",
            "except": "เอ็กเซปต์", "exception": "เอ็กเซปชัน", "execute": "เอ็กซีคิวต์",
            "execution": "เอ็กซีคิวชัน", "exit": "เอ็กซิต", "export": "เอกซ์พอร์ต",
            "express": "เอ็กซ์เพรส", "expression": "เอกซ์เพรสชัน", "extension": "เอกซ์เทนชัน",
            "extract": "เอกซ์แทรกต์", "extranet": "เอกซ์ทราเน็ต", "eye of agamotto": "อายออฟอกาม็อตโต้",

            # --- F ---
            "face recognition": "เฟสเรกคอกนิชัน", "facebook": "เฟซบุ๊ก", "fact": "แฟกต์",
            "failed": "เฟล", "false": "ฟอลส์", "fastapi": "ฟาสต์เอพีไอ",
            "fatigue": "ฟาทีก", "favicon": "แฟฟวิคอน", "feature": "ฟีเจอร์",
            "fetch": "เฟตช์", "few-shot": "ฟิวช็อต", "fiber optic": "ไฟเบอร์ออปติก", "field": "ฟิลด์",
            "file": "ไฟล์", "filter": "ฟิลเตอร์", "final": "ไฟนอล",
            "final fantasy": "ไฟนอลแฟนตาซี", "finally": "ไฟนอลลี", "find": "ไฟนด์",
            "fine-tuning": "ไฟน์ทูนนิง", "finetuning": "ไฟน์ทูนนิ่ง", "finished": "ฟินิชด์",
            "firefox": "ไฟร์ฟอกซ์", "firewall": "ไฟร์วอลล์", "first": "เฟิสต์",
            "fix": "ฟิกซ์", "flag": "แฟล็ก", "flask": "ฟลาสค์",
            "flex": "เฟล็กซ์", "float": "โฟลต", "flow": "โฟลว์",
            "flux": "ฟลักซ์", "folder": "โฟลเดอร์", "follow": "ฟอลโลว์",
            "foodpanda": "ฟู้ดแพนด้า", "footer": "ฟุตเตอร์", "forbidden": "ฟอร์บิดเดน",
            "force": "ฟอร์ซ", "foreign key": "ฟอเรนคีย์", "form": "ฟอร์ม",
            "format": "ฟอร์แมต", "formatter": "ฟอร์แมตเตอร์", "fortnite": "ฟอร์ตไนต์",
            "forward": "ฟอร์เวิร์ด", "fps": "เอฟพีเอส", "fragile": "แฟรจไจล์", "frame generation": "เฟรมเจเนอเรชัน",
            "frame rate": "เฟรมเรต", "framework": "เฟรมเวิร์ก", "free fire": "ฟรีไฟร์",
            "freesync": "ฟรีซิงก์", "friday": "ฟรายเดย์", "frontend": "ฟรอนต์เอนด์",
            "fsr": "เอฟเอสอาร์", "full join": "ฟูลจอยน์", "fullstack": "ฟูลสแต็ก",
            "function": "ฟังก์ชัน", "functions": "ฟังก์ชัน", "future": "ฟิวเจอร์",

            # --- G ---
            "g-sync": "จีซิงก์", "galaxy": "กาแล็กซี", "galaxy watch": "กาแล็กซีวอตช์",
            "game": "เกม", "gamer": "เกมเมอร์", "garbage collection": "การ์เบจคอลเลกชัน",
            "gateway": "เกตเวย์", "gateway timeout": "เกตเวย์ไทม์เอาต์", "gcp": "จีซีพี",
            "geforce": "จีฟอร์ซ", "gemini": "เจมินาย", "gemini 1.5 flash": "เจมินายหนึ่งจุดห้าแฟลช",
            "gemini 1.5 pro": "เจมินายหนึ่งจุดห้าโปร", "gemini 2.0 flash": "เจมินายสองจุดศูนย์แฟลช", "gemini 3.1 pro": "เจมินายสามจุดหนึ่งโปร",
            "gemini 3.8 flash": "เจมินายสามจุดแปดแฟลช", "gemma": "เจมม่า", "gemma 2": "เจมม่าสอง",
            "generation": "เจเนอเรชัน", "generative ai": "เจเนอเรทีฟเอไอ", "generator": "เจนเนอเรเตอร์",
            "generics": "เจนเนอริกส์", "genshin impact": "เกนชินอิมแพกต์", "gesture": "เจสเจอร์",
            "get": "เก็ต", "gg": "จีจี", "git": "กิต",
            "github": "กิตฮับ", "github actions": "กิตฮับแอ็กชันส์", "gitlab": "กิตแล็บ",
            "global": "โกลบอล", "global offensive": "โกลบอลออฟเฟนซิฟ", "go": "โก",
            "goal": "โกล", "good": "กู๊ด", "google": "กูเกิล",
            "google home": "กูเกิลโฮม", "gpt": "จีพีที", "gpt-4": "จีพีทีโฟร์",
            "gpt-4o": "จีพีทีโฟร์โอ", "gpt-4o mini": "จีพีทีโฟร์โอมินิ", "gpu": "จีพียู",
            "grab": "แกร็บ", "grade": "เกรด", "gradient": "เกรเดียนต์",
            "gradient descent": "เกรเดียนต์ดีเซนต์", "grafana": "กราฟาน่า", "grammar": "แกรมมาร์",
            "grant": "แกรนต์", "graph": "กราฟ", "graphic": "กราฟิก",
            "graphql": "กราฟคิวแอล", "grep": "เกรป", "grid": "กริด",
            "groq": "โกร็อก", "group": "กรุ๊ป", "group by": "กรุ๊ปบาย",
            "grpc": "จีอาร์พีซี", "gta": "จีทีเอ", "gta 6": "จีทีเอซิกส์",
            "gta v": "จีทีเอไฟฟ์", "gtx": "จีทีเอ็กซ์", "guest": "เกสต์",
            "gz": "จีแซด",

            # --- H ---
            "hallucination": "ฮาลูซิเนชัน", "hallucinations": "ฮาลูซิเนชัน", "handler": "แฮนด์เลอร์",
            "hardware": "ฮาร์ดแวร์", "hash": "แฮช", "hashing": "แฮชชิง",
            "having": "แฮฟวิง", "hbo go": "เอชบีโอโก", "hdd": "เอชดีดี",
            "hdmi": "เอชดีเอ็มไอ", "head": "เฮด", "header": "เฮดเดอร์",
            "headphone": "เฮดโฟน", "headshot": "เฮดช็อต", "healer": "ฮีลเลอร์",
            "health check": "เฮลธ์เช็ก", "heap": "ฮีป", "heavy": "เฮฟวี",
            "hex": "เฮกซ์", "hierarchy": "ไฮเออราร์คี", "high": "ไฮ", "hitbox": "ฮิตบ็อกซ์",
            "hologram": "โฮโลแกรม", "holographic": "โฮโลกราฟิก", "home assistant": "โฮมแอสซิสแตนต์",
            "honkai star rail": "ฮงไกสตาร์เรล", "hono": "โฮโนะ", "host": "โฮสต์",
            "hotfix": "ฮอตฟิกซ์", "hotspot": "ฮอตสปอต", "house party protocol": "เฮาส์ปาร์ตี้โปรโตคอล",
            "html": "เอชทีเอ็มแอล", "http": "เอชทีทีพี", "https": "เอชทีทีพีเอส",
            "hub": "ฮับ", "huggingface": "ฮักกิ้งเฟซ", "hulkbuster": "ฮัลค์บัสเตอร์",
            "humidity": "ฮิวมิดิตี้", "hz": "เฮิรตซ์",

            # --- I ---
            "icon": "ไอคอน", "ide": "ไอดีอี", "idea": "ไอเดีย",
            "if": "อีฟ", "ig": "ไอจี", "image": "อิมเมจ",
            "impact": "อิมแพกต์", "import": "อิมพอร์ต", "index": "อินเด็กซ์",
            "indexeddb": "อินเด็กซ์ดีบี", "inference": "อินเฟอเรนซ์", "info": "อินโฟ",
            "infrastructure": "อินฟราสตรัคเจอร์", "ingress": "อินเกรส", "initialize": "อินิชิอลไลซ์",
            "initializing": "อินิชิอลไลซิ่ง", "inner join": "อินเนอร์จอยน์", "input": "อินพุต",
            "insert": "อินเสิร์ต", "insomnia": "อินซอมเนีย", "instability": "อินสเตบิลิตี้",
            "instagram": "อินสตาแกรม", "install": "อินสตอล", "instances": "อินสแตนซ์",
            "integer": "อินทีเจอร์", "integration": "อินทิเกรชัน", "intel": "อินเทล",
            "interface": "อินเทอร์เฟซ", "interfaces": "อินเทอร์เฟซ", "internal server error": "อินเทอร์นัลเซิร์ฟเวอร์เออร์เรอร์",
            "internet": "อินเทอร์เน็ต", "internet of things": "อินเทอร์เน็ตออฟทิงส์", "interpret": "อินเทอร์พรีต",
            "interpreter": "อินเทอร์พรีเตอร์", "intersect": "อินเทอร์เซกต์", "intranet": "อินทราเน็ต",
            "invalid": "อินแวลิด", "ios": "ไอ-โอ-เอส", "iot": "ไอโอที",
            "ip": "ไอพี", "ipad": "ไอแพด", "iphone": "ไอโฟน",
            "ips": "ไอพีเอส", "iron": "ไอเอิร์น", "iron man": "ไอรอนแมน", "iron spider": "ไอรอนสไปเดอร์",
            "island": "ไอแลนด์", "island hud": "ไอแลนด์ฮัด", "island overlay": "ไอแลนด์โอเวอร์เลย์",
            "issue": "อิชชิว", "iteration": "อิเทอเรชัน", "iterator": "อิตเทอเรเตอร์",

            # --- J ---
            "j.a.r.v.i.s.": "จาร์วิส", "jarvis": "จาร์วิส", "java": "จาวา",
            "javascript": "จาวาสคริปต์", "jenkins": "เจนกินส์", "jewellery": "จิวเวลรี",
            "jewelry": "จิวเวลรี", "jitter": "จิตเตอร์",
            "job": "จ๊อบ", "joox": "จูกซ์", "js": "เจเอส",
            "json": "เจสัน", "jupyter": "จูพيتر", "jwt": "เจดับเบิลยูที",

            # --- K ---
            "k plus": "เคพลัส", "k8s": "เคแปดเอส", "kafka": "คาฟกา",
            "kanban": "คัมบัง", "keras": "เคราส", "kernel": "เคอร์เนล",
            "key": "คีย์", "keyboard": "คีย์บอร์ด", "kibana": "คิบาน่า",
            "kick": "คิก", "kind": "ไคนด์", "knowledge graph": "โนวเลจกราฟ",
            "kotlin": "คอตลิน", "kubernetes": "คูเบอร์เนตีส",

            # --- L ---
            "lag": "แล็ก", "lambda": "แลมบ์ดา", "langchain": "แลงเชน",
            "langgraph": "แลงกราฟ", "language model": "แรงกวิจโมเดล", "laptop": "แล็ปท็อป",
            "large language model": "ลาร์จแรงกวิจโมเดล", "last": "ลาสต์", "latency": "เลเทนซี",
            "later": "เลเทอร์", "latest": "เลเทสต์", "launch": "ลอนช์",
            "layout": "เลย์เอาต์", "lazada": "ลาซาด้า", "league of legends": "ลีกออฟเลเจนดส์",
            "led": "แอลอีดี", "left": "เลฟต์", "left join": "เลฟต์จอยน์",
            "level": "เลเวล", "lexical": "เล็กซิเคิล", "library": "ไลบรารี",
            "light": "ไลท์", "like": "ไลค์", "limit": "ลิมิต",
            "line": "ไลน์", "lineman": "ไลน์แมน", "link": "ลิงก์",
            "linkedin": "ลิงก์อิน", "linter": "ลินเตอร์", "linux": "ลีนุกซ์",
            "liquid cooling": "ลิควิดคูลลิ่ง", "list": "ลิสต์", "listener": "ลิสเซนเนอร์",
            "llama": "ลามะ", "llama 3": "ลามะสาม", "llama 3.1": "ลามะสามจุดหนึ่ง",
            "llama 3.2": "ลามะสามจุดสอง", "llama 3.3": "ลามะสามจุดสาม", "llm": "แอลแอลเอ็ม",
            "load": "โหลด", "load balancer": "โหลดบาลานเซอร์", "loader": "โหลดเดอร์",
            "loading": "โหลดดิง", "local": "โลคอล", "local storage": "โลคอลสตอเรจ",
            "localstorage": "โลคอลสตอเรจ", "location": "โลเคชัน", "lock": "ล็อก",
            "log": "ล็อก", "logic": "ลอจิก", "login": "ล็อกอิน",
            "logo": "โลโก้", "logout": "ล็อกเอาต์", "long": "ลอง",
            "loop": "ลูป", "loss": "ลอส", "low": "โลว์",
            "lucide": "ลูไซด์",

            # --- M ---
            "mac": "แมค", "mac address": "แม็กแอดเดรส", "macbook": "แมคบุ๊ก",
            "machine learning": "แมชชีนเลิร์นนิ่ง", "machine translation": "แมชชีนทรานสเลชัน", "macos": "แมค-โอ-เอส",
            "magsafe": "แม็กเซฟ", "main": "เมน", "mainboard": "เมนบอร์ด",
            "mainframe": "เมนเฟรม", "maintenance": "เมนทิแนนซ์", "man in the middle": "แมนอินเดอะมิดเดิล",
            "manual": "แมนนวล", "map": "แมป", "margin": "มาร์จิน",
            "mark": "มาร์ก", "mark 42": "มาร์กสี่สิบสอง", "mark 50": "มาร์กห้าสิบ",
            "mark 85": "มาร์กแปดสิบห้า", "markdown": "มาร์กดาวน์", "master": "มาสเตอร์",
            "matchmaking": "แมตช์เมกกิ้ง", "material": "แมททีเรียล", "matrix": "เมทริกซ์", "matplotlib": "แมตพลอตลิบ",
            "matter": "แมทเทอร์", "matter protocol": "แมตเทอร์โปรโตคอล", "max": "แมกซ์",
            "mayonnaise": "เมเยอเนส",
            "mediapipe": "มีเดียไปป์", "meeting": "มีตติง", "member": "เมมเบอร์",
            "memcached": "เมมแคชดี", "memory": "เมมโมรี่", "memory leak": "เมมโมรีลีค",
            "menu": "เมนู", "merge": "เมิร์จ", "message": "เมสเสจ",
            "message queue": "เมสเสจคิว", "messenger": "เมสเซนเจอร์", "meta quest": "เมตาเควสต์",
            "method": "เมทอด", "method not allowed": "เมทอดนอตอะลาวด์", "methods": "เมทอด",
            "microcontroller": "ไมโครคอนโทรลเลอร์", "microphone": "ไมโครโฟน", "microsecond": "ไมโครวินาที",
            "microservices": "ไมโครเซอร์วิส", "microsoft": "ไมโครซอฟท์", "middle": "มิดเดิล",
            "middleware": "มิดเดิลแวร์", "midjourney": "มิดเจอร์นีย์", "millisecond": "มิลลิวินาที",
            "min": "มิน", "minecraft": "มายคราฟต์",
            "mission": "มิชชัน", "mistral": "มิสตราล", "mixtral": "มิกซ์สตราล",
            "mmorpg": "เอ็มเอ็มโออาร์พีจี", "mmr": "เอ็มเอ็มอาร์", "moba": "โมบ้า",
            "mobile": "โมบายล์", "modal": "โมดัล", "mode": "โหมด",
            "modem": "โมเด็ม", "module": "โมดูล", "mongodb": "มองโกดีบี",
            "monitor": "มอนิเตอร์", "monitoring": "มอนิเตอริ่ง", "monolithic": "โมโนลิธิก",
            "monster hunter": "มอนสเตอร์ฮันเตอร์", "month": "มันท์", "motherboard": "มาเธอร์บอร์ด",
            "motion": "โมชัน", "motor": "มอเตอร์", "mouse": "เมาส์",
            "move": "มูฟ", "movement": "มูฟเมนต์", "movie": "มูฟวี่",
            "mr": "เอ็มอาร์", "multi-agent": "มัลติเอเจนต์", "multimodal": "มัลติโมดอล",
            "multiplayer": "มัลติเพลเยอร์", "multithread": "มัลติเธรด", "multithreading": "มัลติเธรดดิง",
            "multiverse": "มัลติเวิร์ส", "music": "มิวสิค", "mute": "มิวต์",

            # --- N ---
            "namespace": "เนมสเปซ", "nano gauntlet": "นาโนกอนต์เล็ต", "nanoparticle": "นาโนพาร์ทิเคิล",
            "nanosecond": "นาโนวินาที", "nanotech": "นาโนเทค", "nanotechnology": "นาโนเทคโนโลยี",
            "narrow": "แนร์โรว์", "natural language processing": "เนเชอรัลแรงกวิจโพรเซสซิง", "nav": "แนฟ",
            "navigation": "เนวิเกชัน", "nerf": "เนิร์ฟ", "netflix": "เน็ตฟลิกซ์",
            "netlify": "เนตลิฟาย", "network": "เน็ตเวิร์ก", "network interface": "เน็ตเวิร์กอินเทอร์เฟซ",
            "neural": "นิวรัล", "neural network": "นิวรัลเน็ตเวิร์ก", "never": "เนเวอร์", "new": "นิว",
            "new relic": "นิวรีลิก", "next": "เน็กซ์", "next.js": "เน็กซ์เจเอส",
            "nextjs": "เน็กซ์เจเอส", "nfc": "เอ็นเอฟซี", "nginx": "เอนจินเอ็กซ์",
            "nintendo": "นินเทนโด", "nlp": "เอ็นแอลพี", "no": "โน",
            "no content": "โนคอนเทนต์", "node": "โหนด", "nominal": "โนมินอล",
            "non-blocking": "นอนบล็อกกิง", "none": "นัน", "noob": "นู้บ",
            "not found": "นอตฟาวนด์", "not implemented": "นอตอิมพลีเมนต์เต็ด", "notification": "โนติฟิเคชั่น",
            "now": "นาว", "npm": "เอ็นพีเอ็ม", "null": "นัล",
            "number": "นัมเบอร์", "numpy": "นัมพาย", "nuxt": "นุกซ์",
            "nvidia": "เอ็นวิเดีย",

            # --- O ---
            "o1 mini": "โอวันมินิ", "o1 preview": "โอวันพรีวิว", "o1-mini": "โอวันมินิ",
            "o1-preview": "โอวันพรีวิว", "o3 mini": "โอทรีมินิ", "o3-mini": "โอทรีมินิ",
            "oauth": "โอออธ", "object": "อ็อบเจกต์", "object detection": "ออบเจกต์ดีเทกชัน",
            "objective": "ออบเจกทิฟ", "objects": "ออบเจกต์", "ocr": "โอซีอาร์",
            "off": "ออฟ", "offline": "ออฟไลน์", "offset": "ออฟเซต",
            "often": "ออฟเฟน", "ok": "โอเค", "okay": "โอเค",
            "oil": "ออยล์", "old": "โอลด์", "oled": "โอเลด", "ollama": "โอลามา",
            "on": "ออน", "online": "ออนไลน์", "onion": "ออนเยิน", "opacity": "โอพาซิตี",
            "open": "โอเพ่น", "openapi": "โอเพนเอพีไอ", "opencv": "โอเพนซีวี",
            "operand": "โอเปอแรนด์", "operator": "โอเปอเรเตอร์", "optical character recognition": "ออปติคัลแคแร็กเตอร์เรกคอกนิชัน",
            "optimal": "ออปติมอล", "optimization": "ออปติไมเซชัน", "optimize": "ออปติไมซ์",
            "option": "ออปชัน", "options": "ออปชันส์",
            "order": "ออร์เดอร์", "order by": "ออร์เดอร์บาย", "organization": "ออร์แกไนเซชัน",
            "origin": "ออริจิน", "os": "โอ-เอส", "outcome": "เอาต์คัม",
            "output": "เอาต์พุต", "overclock": "โอเวอร์คล็อก", "overdrive": "โอเวอร์ไดรฟ์", "overheating": "โอเวอร์ฮีตติง",
            "overwatch": "โอเวอร์วอตช์", "overwatch 2": "โอเวอร์วอตช์ทู", "owner": "โอนเนอร์",

            # --- P ---
            "package": "แพ็กเกจ", "packet": "แพ็กเกต", "packet loss": "แพ็กเก็ตลอส",
            "padding": "แพดดิง", "page": "เพจ", "pagination": "พาจิเนชัน",
            "pan": "แพน", "pandas": "แพนดาส", "parallelism": "พาราเลลลิซึม",
            "parameter": "พารามิเตอร์", "parameters": "พารามิเตอร์", "parse": "พาร์ส",
            "password": "พาสเวิร์ด", "past": "พาสต์", "paste": "เพสต์",
            "patch": "แพตช์", "path": "พาท", "path parameter": "พาทพารามิเตอร์",
            "path tracing": "พาทเทรซซิ่ง", "patterns": "แพตเทิร์น", "pause": "พอส",
            "payload": "เพย์โหลด", "payload too large": "เพย์โหลดทูลาร์จ", "paypal": "เพย์พาล",
            "peer": "เพียร์", "penetration testing": "เพเนเทรชันเทสติง", "performance": "เพอร์ฟอร์แมนส์",
            "perimeter": "เพอริมิเตอร์", "permission": "เพอร์มิชชัน", "perplexity": "เพอร์เพล็กซิตี้",
            "phi-3": "ฟายทรี",
            "phishing": "ฟิชชิง", "phone": "โฟน", "photo": "โฟโต้",
            "php": "พีเอชพี", "picture": "พิกเจอร์", "ping": "ปิง",
            "pinterest": "พินเทอเรสต์", "pip": "พิป", "pipeline": "ไพป์ไลน์",
            "pitch": "พิตช์", "pixel": "พิกเซล", "placeholder": "เพลซโฮลเดอร์",
            "plan": "แพลน", "platform": "แพลตฟอร์ม", "play": "เพลย์",
            "playerunknown's battlegrounds": "เพลเยอร์อันโนนส์แบทเทิลกราวดส์", "playstation": "เพลย์สเตชัน", "plug": "ปลั๊ก",
            "plugin": "ปลั๊กอิน", "pnpm": "พีเอ็นพีเอ็ม", "pod": "พ็อด",
            "pods": "พ็อดส์", "poetry": "โพเอทรี", "point": "พอยต์",
            "pointer": "พอยเตอร์", "popup": "ป็อปอัป", "port": "พอร์ต",
            "position": "โพสิชัน", "post": "โพสต์", "postman": "โพสต์แมน",
            "power": "เพาเวอร์", "power supply": "พาวเวอร์ซัปพลาย", "powerbank": "พาวเวอร์แบงก์",
            "powershell": "พาวเวอร์เชลล์", "preferences": "พรีเฟอเรนเซส", "previous": "พรีเวียส",
            "primary key": "ไพรมารีคีย์", "prime video": "ไพรม์วิดีโอ", "print": "พรินต์",
            "probably": "พรอบเบอบลี่", "procedure": "โพรซีเจอร์", "process": "โพรเซส", "processing": "โพรเซสซิ่ง",
            "processor": "โพรเซสเซอร์", "product": "โปรดักต์", "production": "โปรดักชัน",
            "profile": "โปรไฟล์", "profiler": "โพรไฟเลอร์", "program": "โปรแกรม",
            "progress": "โพรเกรส", "prometheus": "โพรมีธีอุส", "promise": "พรอมิส",
            "prompt": "พรอมต์", "prompt engineering": "พรอมต์เอนจิเนียริง", "promptpay": "พร้อมเพย์",
            "prompts": "พรอมต์", "properties": "พร็อปเพอร์ตีส์", "property": "พร็อพเพอร์ตี้",
            "protobuf": "โปรโตบัฟ", "protocol": "โปรโตคอล", "protocols": "โปรโตคอล",
            "proxy": "พร็อกซี", "psu": "พีเอสยู", "pub/sub": "ผับซับ",
            "pubg": "พับจี", "publish": "พับลิช", "pubsub": "ผับซับ",
            "pull": "พูล", "pull request": "พูลรีเควสต์", "purpose": "เพอร์โพส",
            "push": "พุช", "put": "พุต", "python": "ไพทอน",
            "pytorch": "พายทอร์ช",

            # --- Q ---
            "qr code": "คิวอาร์โค้ด", "quantum": "ควอนตัม", "quantum computing": "ควอนตัมคอมพิวติ้ง",
            "quantum realm": "ควอนตัมเรล์ม", "qubit": "คิวบิต", "query": "คิวรี",
            "query string": "คิวรีสตริง", "queue": "คิว", "quick": "ควิก",
            "quit": "ควิท", "quota": "โควตา", "qwen": "คิวเหวิน",

            # --- R ---
            "rabbitmq": "แรบบิทเอ็มคิว", "radeon": "เรเดียน", "radio": "เรดิโอ",
            "radix": "เรดิกซ์", "rag": "แร็ก", "rainbow table": "เรนโบว์เทเบิล",
            "raise": "เรส", "ram": "แรม", "rank": "แรงก์",
            "ransomware": "แรนซัมแวร์", "rapid": "แรพิด", "rarely": "แรร์ลี",
            "raspberry pi": "ราสเบอร์รีพาย", "rate limit": "เรตลิมิต", "ray tracing": "เรย์เทรซซิ่ง",
            "react": "รีแอค", "reaction": "รีแอ็กชัน", "reactor": "รีแอคเตอร์",
            "read": "รี้ด", "ready": "เรดดี้", "reason": "รีซัน",
            "receipt": "รีซีท", "receive": "รีซีฟ", "recent": "รีเซนต์", "record": "เรคคอร์ด",
            "red team": "เรดทีม", "reddit": "เรดดิต", "redis": "เรดิส",
            "reference": "เรเฟอเรนซ์", "refresh rate": "รีเฟรชเรต", "register": "รีจิสเตอร์",
            "registry": "เรจิสทรี", "reinforcement learning": "รีอินฟอร์ซเมนต์เลิร์นนิง", "reject": "รีเจกต์",
            "relay": "รีเลย์", "release": "รีลีส", "reminder": "รีไมน์เดอร์",
            "remove": "รีมูฟ", "rename": "รีเนม", "repair": "รีแพร์",
            "report": "รีพอร์ท", "repository": "รีโพสิทอรี", "repulsor": "รีพัลเซอร์",
            "repulsor cannon": "รีพัลเซอร์แคนนอน", "request": "รีเควสต์", "rescue suit": "เรสคิวสูท",
            "reset": "รีเซ็ต", "resident evil": "เรสซิเดนต์อีวิล", "resonance": "เรโซแนนซ์", "resolve": "รีโซล์ฟ",
            "resource": "รีซอร์ส", "respawn": "รีสปอว์น", "response": "เรสปอนส์",
            "rest api": "เรสต์เอพีไอ", "restart": "รีสตาร์ท", "restful": "เรสต์ฟูล",
            "restore": "รีสโตร์", "result": "รีซัลต์", "resume": "รีซูม",
            "return": "รีเทิร์น", "reverse proxy": "รีเวิร์สพร็อกซี", "revoke": "รีโวก",
            "rgb": "อาร์จีบี", "right": "ไรต์", "right join": "ไรต์จอยน์",
            "robinhood": "โรบินฮู้ด", "roblox": "โรบล็อกซ์", "robotics": "โรโบติกส์",
            "role": "โรล", "rollback": "โรลแบ็ก", "root": "รูท",
            "rotate": "โรเทต", "route": "เราต์", "router": "เราเตอร์",
            "rov": "อาร์โอวี", "row": "โรว์", "rpg": "อาร์พีจี",
            "rtx": "อาร์ทีเอ็กซ์", "ruby": "รูบี", "run": "รัน",
            "runtime": "รันไทม์", "runway": "รันเวย์", "rust": "รัสต์",
            "ryzen": "ไรเซน",

            # --- S ---
            "s3": "เอสทรี", "safari": "ซาฟารี", "safe": "เซฟ",
            "salmon": "แซเมิ่น", "salt": "ซอลต์", "samsung": "ซัมซุง", "save": "เซฟ",
            "savepoint": "เซฟพอยต์", "scale": "สเกล", "scan": "สแกน",
            "scanning": "สแกนนิ่ง", "scb easy": "เอสซีบีอีซี่", "scene": "ซีน",
            "schedule": "สเกดจูล", "schema": "สกีมา", "scikit-learn": "ไซคิตเลิร์น",
            "scope": "สโคป", "score": "สกอร์", "screen": "สกรีน",
            "script": "สคริปต์", "scripting": "สคริปติง", "scroll": "สกรอล",
            "scrum": "สครัม", "sdk": "เอสดีเค", "seaborn": "ซีบอร์น",
            "search": "เสิร์ช", "secret": "ซีเครต", "section": "เซกชัน",
            "secure": "ซีเคียว", "security": "ซีคิวริตี้", "security group": "ซีเคียวริตีกรุ๊ป",
            "segmentation fault": "เซกเมนต์เทชันฟอลต์", "select": "ซีเลกต์", "semantic": "ซีแมนติก",
            "send": "เซนด์", "sensor": "เซ็นเซอร์", "sentiment analysis": "เซนติเมนต์อะนาลิซิส",
            "sequence": "ซีเควนซ์", "serialize": "ซีเรียลไลซ์", "server": "เซิร์ฟเวอร์",
            "serverless": "เซิร์ฟเวอร์เลส", "service": "เซอร์วิส", "service unavailable": "เซอร์วิสอันอะไวเลเบิล",
            "session": "เซสชัน", "set": "เซต", "setting": "เซตติ้ง",
            "settings": "เซตติ้งส์", "shadcn": "แชดซีเอ็น", "shadow": "แชโดว์",
            "shallow": "แชลโลว์", "shape": "เชป", "share": "แชร์",
            "shell": "เชลล์", "shift": "ชิฟต์", "shopee": "ช้อปปี้",
            "short": "ชอร์ต", "shutdown": "ชัทดาวน์", "signal": "ซิกแนล",
            "signature": "ซิกเนเจอร์", "signin": "ไซน์อิน", "signout": "ไซน์เอาต์",
            "signup": "ไซน์อัป", "silent hill": "ไซเลนต์ฮิลล์", "singularity": "ซิงกูลาริตี้",
            "sir": "เซอร์", "size": "ไซส์", "skeleton": "สเกเลตัน", "skip": "สคิป",
            "sla": "เอสแอลเอ", "slider": "สไลเดอร์", "smart": "สมาร์ท",
            "smart bulb": "สมาร์ตบัลบ์", "smart camera": "สมาร์ตคาเมร่า", "smart home": "สมาร์ท-โฮม",
            "smart lock": "สมาร์ตล็อก", "smart plug": "สมาร์ตปลั๊ก", "smart ring": "สมาร์ตริง",
            "smart switch": "สมาร์ตสวิตช์", "smartwatch": "สมาร์ทวอตช์", "smurf": "สเมิร์ฟ",
            "soldier": "โซลเจอร์",
            "socket": "ซ็อกเก็ต", "software": "ซอฟต์แวร์", "sometimes": "ซัมไทม์ส",
            "sony": "โซนี่", "soon": "ซูน", "sora": "โซระ",
            "sort": "ซอร์ต", "sound": "ซาวด์", "soundcloud": "ซาวด์คลาวด์",
            "source": "ซอร์ส", "space": "สเปซ", "spawn": "สปอว์น",
            "speaker": "สปีกเกอร์", "speech": "สปีช", "speech recognition": "สปีชเรกคอกนิชัน",
            "speech synthesis": "สปีชซินทีซิส", "speech to text": "สปีชทูเท็กซ์", "speed": "สปีด",
            "spectrum": "สเปกตรัม",
            "spinner": "สปินเนอร์", "splunk": "สพลังก์", "spotify": "สปอติฟาย",
            "spring": "สปริง", "sprint": "สปรินต์", "sqlite": "เอสคิวแอลไลต์",
            "ssd": "เอส-เอส-ดี", "ssl": "เอสเอสแอล", "stability": "สเตบิลิตี้",
            "stable diffusion": "สเตเบิลดิฟฟิวชัน", "stack": "สแต็ก", "staging": "สเตจจิง",
            "standby": "สแตนด์บาย", "star": "สตาร์", "stark": "สตาร์ค",
            "stark industries": "สตาร์กอินดัสตรีส์", "start": "สตาร์ท", "startup": "สตาร์ตอัป",
            "state": "สเตต", "statement": "สเตตเมนต์", "status": "สเตตัส",
            "status code": "สเตตัสโค้ด", "steam": "สตีม", "stomach": "สโทเมิค", "stop": "สต็อป",
            "stopwatch": "สต็อปวอตช์", "strategy": "สแตรทิจี", "stream": "สตรีม",
            "streaming": "สตรีมมิ่ง", "string": "สตริง", "stripe": "สไตรป์",
            "structure": "สตรักเจอร์", "stt": "เอสทีที", "style": "สไตล์",
            "subatomic": "ซับอะตอมิก", "submit": "ซับมิต", "subnet": "ซับเน็ต", "subscribe": "ซับสไครบ์",
            "substance": "ซับสแตนซ์", "success": "ซัคเซส", "sudo": "ซูโด",
            "sum": "ซัม", "summarization": "ซัมมะไรเซชัน", "suno": "ซูโน่",
            "supervised learning": "ซูเปอร์ไวส์เลิร์นนิง", "support": "ซัพพอร์ต", "svelte": "สเวลต์",
            "svg": "เอสวีจี", "swagger": "สแวกเกอร์", "swift": "สวิฟต์",
            "swipe": "สไวป์", "switch": "สวิตช์", "symlink": "ซิมลิงก์",
            "sync": "ซิงก์", "synchronous": "ซิงโครนัส", "synonym": "ซิโนนิม",
            "syntax": "ซินแทกซ์", "synthetic": "ซินเทติก", "system": "ซิส-เต็ม",
            "sword": "ซอร์ด",

            # --- T ---
            "tab": "แท็บ", "table": "เทเบิล", "tablet": "แท็บเล็ต",
            "tag": "แท็ก", "tailwind": "เทลวินด์", "tailwindcss": "เทลวินด์ซีเอสเอส",
            "tall": "ทอล", "tank": "แทงก์", "tar": "ทาร์",
            "target": "ทาร์เก็ต", "task": "แทสก์", "task manager": "ทาสก์เมเนเจอร์",
            "tcp": "ทีซีพี", "team": "ทีม", "telegram": "เทเลแกรม",
            "telemetry": "เทเลเมทรี", "temperature": "เทมเพอเรเจอร์", "temperatures": "เทมเพอเรเจอร์ส",
            "templates": "เทมเพลต", "tensorflow": "เทนเซอร์โฟลว์", "terminal": "เทอร์มินัล",
            "terraform": "เทอร์ราฟอร์ม", "tesseract": "เทสเซอแร็กต์", "test": "เทสต์",
            "testing": "เทสติง", "text classification": "เท็กซ์คลาสซิฟิเคชัน", "text to speech": "เท็กซ์ทูสปีช",
            "textarea": "เท็กซ์แอเรีย", "texture": "เท็กซ์เจอร์", "theory": "ทฤษฎี",
            "thermal paste": "ซิลิโคนระบายความร้อน", "thermostat": "เทอร์โมสแตต", "thick": "ทิก",
            "thin": "ทิน", "thought": "ธอท", "thread": "เทรด",
            "thread protocol": "เทรดโปรโตคอล", "threshold": "เทรชโฮลด์", "through": "ธรู",
            "throughput": "ทรูพุต", "throw": "โทรว์",
            "ticket": "ทิกเก็ต", "tiktok": "ติ๊กต็อก", "time": "ไทม์",
            "timeout": "ไทม์เอ้าท์", "timer": "ไทม์เมอร์", "timestamp": "ไทม์แสตมป์",
            "tls": "ทีแอลเอส", "toast": "โทสต์", "today": "ทูเดย์",
            "token": "โทเคน", "token limit": "โทเคนลิมิต", "tokenizer": "โทเคไนเซอร์", "tokens": "โทเคน",
            "tomorrow": "ทูมอโรว์", "too many requests": "ทูเมนีรีเควสต์", "tooltip": "ทูลทิป",
            "top": "ท็อป", "top k": "ท็อปเค", "top p": "ท็อปพี",
            "top-k": "ท็อปเค", "top-p": "ท็อปพี", "touch": "ทัช",
            "tournament": "ทัวร์นาเมนต์", "transaction": "ทรานแซกชัน", "transform": "ทรานส์ฟอร์ม",
            "transformer": "ทรานส์ฟอร์เมอร์", "transition": "ทรานสิชัน", "translate": "ทรานสเลต",
            "translation": "ทรานสเลชัน", "tree": "ทรี", "trigger": "ทริกเกอร์",
            "trpc": "ทีอาร์พีซี", "true": "ทรู", "true wallet": "ทรูวอลเล็ต",
            "truemoney": "ทรูมันนี่", "truncate": "ทรูนเคต", "truth": "ทรูท",
            "try": "ไทร", "ts": "ทีเอส", "tts": "ทีทีเอส",
            "tuition": "ทูเชิ่น", "tuple": "ทูเพิล", "turborepo": "เทอร์โบริโป", "tv": "ที-วี",
            "twitch": "ทวิตช์", "twitter": "ทวิตเตอร์", "types": "ไทป์",
            "typescript": "ไทป์สคริปต์",

            # --- U ---
            "ubuntu": "อูบุนตู", "udio": "ยูดีโอ", "udp": "ยูดีพี",
            "uefi": "ยูอีเอฟไอ", "unauthorized": "อันออทอไรซ์", "unblock": "อันบล็อก",
            "undeafen": "อันเดฟเฟน", "undefined": "อันดีไฟน์", "undervolt": "อันเดอร์โวลต์",
            "unfollow": "อันฟอลโลว์", "unibeam blast": "ยูนิบีมบลาสต์", "unicode": "ยูนิโค้ด",
            "uninstall": "อันอินสตอล", "union": "ยูเนียน", "unlock": "อันล็อก",
            "unmute": "อันมิวต์", "unsubscribe": "อันซับสไครบ์", "unsupervised learning": "อันซูเปอร์ไวส์เลิร์นนิง",
            "update": "อัปเดต", "upgrade": "อัปเกรด", "upload": "อัปโหลด",
            "uptime": "อัปไทม์", "uru": "อูรู", "usage": "ยูสเสจ",
            "usb": "ยูเอสบี", "user": "ยูสเซอร์", "username": "ยูสเซอร์เนม",
            "utf-8": "ยูทีเอฟเอต",

            # --- V ---
            "vad": "วีเอดี", "valid": "แวลิด", "valorant": "วาโลแรนต์", "value": "แวลู",
            "variable": "เวเรียเบิล", "variables": "เวเรียเบิลส์", "vector": "เวกเตอร์",
            "vector database": "เวกเตอร์ดาต้าเบส", "vectors": "เวกเตอร์", "velocity": "เวโลซิตี",
            "vercel": "เวอร์เซล", "verify": "เวอริไฟ", "veronica": "เวโรนิกา",
            "version": "เวอร์ชัน", "version control": "เวอร์ชันคอนโทรล", "vertex": "เวอร์เท็กซ์",
            "vibranium": "ไวเบรเนียม", "video": "วิดีโอ", "video call": "วิดีโอคอล",
            "view": "วิว", "virtual assistant": "เวอร์ชวลแอสซิสแตนต์", "virtual machine": "เวอร์ชวลแมชชีน",
            "vision": "วิชัน", "vision pro": "วิชันโปร", "vite": "ไวต์",
            "vm": "วีเอ็ม", "voice": "วอยซ์", "voice assistant": "วอยซ์แอสซิสแตนต์",
            "voice recognition": "วอยซ์เรกคอกนิชัน", "volume": "โวลุ่ม", "vpc": "วีพีซี",
            "vpn": "วีพีเอ็น", "vr": "วีอาร์", "vsync": "วีซิงก์",
            "vue": "วิว", "vuejs": "วิวเจเอส", "vulnerability": "วัลเนอราบิลิตี้",

            # --- W ---
            "waiting": "เวตติง", "war machine": "วอร์แมชชีน", "warning": "วอร์นนิ่ง",
            "warzone": "วอร์โซน", "watch": "วอตช์", "water cooling": "วอเตอร์คูลลิ่ง",
            "way": "เวย์", "web": "เว็บ", "webcam": "เว็บแคม",
            "webhook": "เว็บฮุก", "webrtc": "เว็บอาร์ทีซี", "websocket": "เว็บซ็อกเก็ต",
            "wake word": "เวกเวิร์ด", "wakeword": "เวกเวิร์ด",
            "week": "วีก", "weights": "เวตส์", "whatsapp": "วอตส์แอปป์",
            "whisper": "วิสเปอร์", "wi-fi": "ไว-ไฟ", "wide": "ไวด์",
            "wifi": "ไว-ไฟ", "windows": "วินโดวส์", "woman": "วูเมิ่น",
            "women": "วีมิ่น", "work": "เวิร์ก",
            "world of warcraft": "เวิลด์ออฟวอร์คราฟต์", "worse": "เวิร์ส", "worst": "เวิร์สต์",
            "wrapper": "แรปเปอร์", "write": "ไรต์", "wrong": "รอง",

            # --- X ---
            "x": "เอ็กซ์", "xbox": "เอ็กซ์บ็อกซ์", "xml": "เอ็กซ์เอ็มแอล",
            "xr": "เอ็กซ์อาร์",

            # --- Y ---
            "yaml": "แยมเมิล", "yarn": "ยาร์น", "year": "เยียร์",
            "yes": "เยส", "yesterday": "เยสเตอร์เดย์", "yield": "ยีลด์",
            "youtube": "ยูทูบ",

            # --- Z ---
            "z-wave": "ซีเวฟ", "zero day": "ซีโร่เดย์", "zero-shot": "ซีโร่ช็อต", "zigbee": "ซิกบี",
            "zip": "ซิป", "zone": "โซน", "zoom": "ซูม",
            "zsh": "ซีเชลล์",

            # --- Thai Music Artists, Bands & T-Pop (ศิลปินและวงดนตรีไทยยอดนิยม) ---
            # ศิลปินเดี่ยว / ป๊อป / อาร์แอนด์บี / อินดี้
            "nont tanont": "นนท์ ธนนท์", "nont": "นนท์",
            "bowkylion": "โบกี้ไลอ้อน", "bowky lion": "โบกี้ไลอ้อน", "bowky": "โบกี้",
            "ink waruntorn": "อิงค์ วรันธร", "waruntorn": "วรันธร",
            "jeff satur": "เจฟ ซาเตอร์", "satur": "ซาเตอร์",
            "billkin": "บิวกิ้น", "billkin putthipong": "บิวกิ้น พุฒิพงศ์",
            "pp krit": "พีพี กฤษฎ์",
            "pun": "ปัน", "pun sarunviphat": "ปัน สรณวรรธน์",
            "atom chanakan": "อะตอม ชนกันต์", "chanakan": "ชนกันต์", "atom": "อะตอม",
            "violette wautier": "วิโอเลต วอเทียร์", "violette": "วิโอเลต", "wautier": "วอเทียร์",
            "milli": "มิลลิ",
            "phum viphurit": "ภูมิ วิภูริศ", "phum": "ภูมิ", "viphurit": "วิภูริศ",

            # วงดนตรี / แบนด์ / วงร็อก / อัลเทอร์เนทีฟ
            "bodyslam": "บอดี้สแลม", "body slam": "บอดี้สแลม",
            "cocktail": "ค็อกเทล",
            "three man down": "ทรีแมนดาวน์",
            "tilly birds": "ทิลลี่เบิร์ดส", "tilly bird": "ทิลลี่เบิร์ด",
            "tattoo colour": "แทททูคัลเลอร์", "tattoo color": "แทททูคัลเลอร์",
            "big ass": "บิ๊กแอส", "bigass": "บิ๊กแอส",
            "silly fools": "ซิลลี่ฟูลส์", "silly fool": "ซิลลี่ฟูล",
            "loso": "โลโซ", "sek loso": "เสก โลโซ",
            "polycat": "โพลีแคต", "poly cat": "โพลีแคต",
            "purpeech": "เปอร์พีช",
            "paper planes": "เปเปอร์เพลนส์", "paper plane": "เปเปอร์เพลน",
            "fellow fellow": "เฟลโลว์ เฟลโลว์",

            # ฮิปฮอป / แร็พ / T-Pop
            "youngohm": "ยังโอม", "young ohm": "ยังโอม",
            "f.hero": "กอล์ฟ เอฟ.ฮีโร่", "f hero": "เอฟฮีโร่", "f-hero": "เอฟฮีโร่", "fhero": "เอฟฮีโร่",
            "saran": "ศรัณย์",
            "4eve": "โฟร์อีฟ",
            "bus": "บัส", "because of you i shine": "บีคอสออฟยูไอชายน์",
            "proxie": "พร็อกซี่",

            # --- Musical Chords & Theory (คอร์ดดนตรีและทฤษฎีดนตรี) ---
            # คำศัพท์หมวดคอร์ดและทฤษฎีดนตรี
            "major chord": "คอร์ดเมเจอร์", "major chords": "คอร์ดเมเจอร์",
            "minor chord": "คอร์ดไมเนอร์", "minor chords": "คอร์ดไมเนอร์",
            "sharp chord": "คอร์ดชาร์ป", "sharp chords": "คอร์ดชาร์ป",
            "flat chord": "คอร์ดแฟลต", "flat chords": "คอร์ดแฟลต",
            "chord progression": "คอร์ดโปรเกรสชัน", "chord sheet": "คอร์ดชีต",
            "chord": "คอร์ด", "chords": "คอร์ด",

            # คอร์ดเมเจอร์และไมเนอร์แบบสะกดคำเต็ม
            "c major": "ซีเมเจอร์", "d major": "ดีเมเจอร์", "e major": "อีเมเจอร์",
            "f major": "เอฟเมเจอร์", "g major": "จีเมเจอร์", "a major": "เอเมเจอร์", "b major": "บีเมเจอร์",
            "c minor": "ซีไมเนอร์", "d minor": "ดีไมเนอร์", "e minor": "อีไมเนอร์",
            "f minor": "เอฟไมเนอร์", "g minor": "จีไมเนอร์", "a minor": "เอไมเนอร์", "b minor": "บีไมเนอร์",
            "cmaj": "ซีเมเจอร์", "dmaj": "ดีเมเจอร์", "emaj": "อีเมเจอร์",
            "fmaj": "เอฟเมเจอร์", "gmaj": "จีเมเจอร์", "amaj": "เอเมเจอร์", "bmaj": "บีเมเจอร์",
            "cmin": "ซีไมเนอร์", "dmin": "ดีไมเนอร์", "emin": "อีไมเนอร์",
            "fmin": "เอฟไมเนอร์", "gmin": "จีไมเนอร์", "amin": "เอไมเนอร์", "bmin": "บีไมเนอร์",

            # คอร์ดเมเจอร์พื้นฐาน A-G (โน้ตเดี่ยว 7 ตัวในบริบทคอร์ด)
            "a": "เอ", "b": "บี", "c": "ซี", "d": "ดี", "e": "อี", "f": "เอฟ", "g": "จี",

            # คอร์ดไมเนอร์พื้นฐาน (Minor Chords: Cm - Bm)
            "cm": "ซีไมเนอร์", "dm": "ดีไมเนอร์", "em": "อีไมเนอร์",
            "fm": "เอฟไมเนอร์", "gm": "จีไมเนอร์", "am": "เอไมเนอร์", "bm": "บีไมเนอร์",

            # คอร์ดติดชาร์ป (# - Sharp) & แฟลต (b - Flat)
            "c#": "ซีชาร์ป", "d#": "ดีชาร์ป", "f#": "เอฟชาร์ป", "g#": "จีชาร์ป", "a#": "เอชาร์ป",
            "db": "ดีแฟลต", "eb": "อีแฟลต", "gb": "จีแฟลต", "ab": "เอแฟลต", "bb": "บีแฟลต",

            # คอร์ดไมเนอร์ติดชาร์ป & แฟลต
            "c#m": "ซีชาร์ปไมเนอร์", "d#m": "ดีชาร์ปไมเนอร์", "f#m": "เอฟชาร์ปไมเนอร์", "g#m": "จีชาร์ปไมเนอร์", "a#m": "เอชาร์ปไมเนอร์",
            "dbm": "ดีแฟลตไมเนอร์", "ebm": "อีแฟลตไมเนอร์", "gbm": "จีแฟลตไมเนอร์", "abm": "เอแฟลตไมเนอร์", "bbm": "บีแฟลตไมเนอร์",

            # คอร์ด 7 (Dominant 7th)
            "c7": "ซีเซเว่น", "d7": "ดีเซเว่น", "e7": "อีเซเว่น", "f7": "เอฟเซเว่น", "g7": "จีเซเว่น", "a7": "เอเซเว่น", "b7": "บีเซเว่น",
            "c#7": "ซีชาร์ปเซเว่น", "d#7": "ดีชาร์ปเซเว่น", "f#7": "เอฟชาร์ปเซเว่น", "g#7": "จีชาร์ปเซเว่น", "a#7": "เอชาร์ปเซเว่น",
            "db7": "ดีแฟลตเซเว่น", "eb7": "อีแฟลตเซเว่น", "gb7": "จีแฟลตเซเว่น", "ab7": "เอแฟลตเซเว่น", "bb7": "บีแฟลตเซเว่น",

            # คอร์ด maj7 (Major 7th)
            "cmaj7": "ซีเมเจอร์เซเว่น", "dmaj7": "ดีเมเจอร์เซเว่น", "emaj7": "อีเมเจอร์เซเว่น",
            "fmaj7": "เอฟเมเจอร์เซเว่น", "gmaj7": "จีเมเจอร์เซเว่น", "amaj7": "เอเมเจอร์เซเว่น", "bmaj7": "บีเมเจอร์เซเว่น",
            "c#maj7": "ซีชาร์ปเมเจอร์เซเว่น", "d#maj7": "ดีชาร์ปเมเจอร์เซเว่น", "f#maj7": "เอฟชาร์ปเมเจอร์เซเว่น", "g#maj7": "จีชาร์ปเมเจอร์เซเว่น", "a#maj7": "เอชาร์ปเมเจอร์เซเว่น",
            "dbmaj7": "ดีแฟลตเมเจอร์เซเว่น", "ebmaj7": "อีแฟลตเมเจอร์เซเว่น", "gbmaj7": "จีแฟลตเมเจอร์เซเว่น", "abmaj7": "เอแฟลตเมเจอร์เซเว่น", "bbmaj7": "บีแฟลตเมเจอร์เซเว่น",

            # คอร์ด m7 (Minor 7th)
            "cm7": "ซีไมเนอร์เซเว่น", "dm7": "ดีไมเนอร์เซเว่น", "em7": "อีไมเนอร์เซเว่น",
            "fm7": "เอฟไมเนอร์เซเว่น", "gm7": "จีไมเนอร์เซเว่น", "am7": "เอไมเนอร์เซเว่น", "bm7": "บีไมเนอร์เซเว่น",
            "c#m7": "ซีชาร์ปไมเนอร์เซเว่น", "d#m7": "ดีชาร์ปไมเนอร์เซเว่น", "f#m7": "เอฟชาร์ปไมเนอร์เซเว่น", "g#m7": "จีชาร์ปไมเนอร์เซเว่น", "a#m7": "เอชาร์ปไมเนอร์เซเว่น",
            "dbm7": "ดีแฟลตไมเนอร์เซเว่น", "ebm7": "อีแฟลตไมเนอร์เซเว่น", "gbm7": "จีแฟลตไมเนอร์เซเว่น", "abm7": "เอแฟลตไมเนอร์เซเว่น", "bbm7": "บีแฟลตไมเนอร์เซเว่น",

            # คอร์ด sus4, sus2, sus (Suspended Chords)
            "csus4": "ซีซัสโฟร์", "dsus4": "ดีซัสโฟร์", "esus4": "อีซัสโฟร์",
            "fsus4": "เอฟซัสโฟร์", "gsus4": "จีซัสโฟร์", "asus4": "เอซัสโฟร์", "bsus4": "บีซัสโฟร์",
            "csus2": "ซีซัสทู", "dsus2": "ดีซัสทู", "esus2": "อีซัสทู",
            "fsus2": "เอฟซัสทู", "gsus2": "จีซัสทู", "asus2": "เอซัสทู", "bsus2": "บีซัสทู",
            "csus": "ซีซัส", "dsus": "ดีซัส", "esus": "อีซัส",
            "fsus": "เอฟซัส", "gsus": "จีซัส", "asus": "เอซัส", "bsus": "บีซัส",
            "c#sus4": "ซีชาร์ปซัสโฟร์", "d#sus4": "ดีชาร์ปซัสโฟร์", "f#sus4": "เอฟชาร์ปซัสโฟร์", "g#sus4": "จีชาร์ปซัสโฟร์", "a#sus4": "เอชาร์ปซัสโฟร์",

            # คอร์ด dim & dim7 (Diminished Chords)
            "cdim": "ซีดิมินิช", "ddim": "ดีดิมินิช", "edim": "อีดิมินิช",
            "fdim": "เอฟดิมินิช", "gdim": "จีดิมินิช", "adim": "เอดิมินิช", "bdim": "บีดิมินิช",
            "cdim7": "ซีดิมินิชเซเว่น", "ddim7": "ดีดิมินิชเซเว่น", "edim7": "อีดิมินิชเซเว่น",
            "fdim7": "เอฟดิมินิชเซเว่น", "gdim7": "จีดิมินิชเซเว่น", "adim7": "เอดิมินิชเซเว่น", "bdim7": "บีดิมินิชเซเว่น",
            "c#dim": "ซีชาร์ปดิมินิช", "d#dim": "ดีชาร์ปดิมินิช", "f#dim": "เอฟชาร์ปดิมินิช", "g#dim": "จีชาร์ปดิมินิช", "a#dim": "เอชาร์ปดิมินิช",

            # คอร์ด add9
            "cadd9": "ซีแอดไนน์", "dadd9": "ดีแอดไนน์", "eadd9": "อีแอดไนน์",
            "fadd9": "เอฟแอดไนน์", "gadd9": "จีแอดไนน์", "aadd9": "เอแอดไนน์", "badd9": "บีแอดไนน์",

            # คอร์ด m9 (Minor 9th)
            "cm9": "ซีไมเนอร์ไนน์", "dm9": "ดีไมเนอร์ไนน์", "em9": "อีไมเนอร์ไนน์",
            "fm9": "เอฟไมเนอร์ไนน์", "gm9": "จีไมเนอร์ไนน์", "am9": "เอไมเนอร์ไนน์", "bm9": "บีไมเนอร์ไนน์",

            # คอร์ด 9, 6, aug
            "c9": "ซีไนน์", "d9": "ดีไนน์", "e9": "อีไนน์", "f9": "เอฟไนน์", "g9": "จีไนน์", "a9": "เอไนน์", "b9": "บีไนน์",
            "c6": "ซีซิกส์", "d6": "ดีซิกส์", "e6": "อีซิกส์", "f6": "เอฟซิกส์", "g6": "จีซิกส์", "a6": "เอซิกส์", "b6": "บีซิกส์",
            "caug": "ซีออกเมนต์", "daug": "ดีออกเมนต์", "eaug": "อีออกเมนต์",
            "faug": "เอฟออกเมนต์", "gaug": "จีออกเมนต์", "aaug": "เอออกเมนต์", "baug": "บีออกเมนต์",

            # การตั้งสายและคำศัพท์ดนตรี
            "tuning": "ทูนนิ่ง", "d tuning": "ดีทูนนิ่ง", "standard tuning": "สแตนดาร์ดทูนนิ่ง",
            "drop d": "ดรอปดี", "drop c": "ดรอปซี",

            # โครงสร้างพื้นฐานและเทคโนโลยี
            "postgresql": "โพสต์เกรสคิวแอล", "postgres": "โพสต์เกรส",
            "ssh": "เอสเอสเอช",
            "autonomous": "ออโตโนมัส", "autonomous pipeline": "ออโตโนมัสไพป์ไลน์",
            "worker threads": "เวิร์กเกอร์เธรด", "worker thread": "เวิร์กเกอร์เธรด",

            # คอร์ดเมื่อมีคำว่า คอร์ด / chord นำหน้า
            "คอร์ด c": "คอร์ด ซี", "คอร์ด d": "คอร์ด ดี", "คอร์ด e": "คอร์ด อี",
            "คอร์ด f": "คอร์ด เอฟ", "คอร์ด g": "คอร์ด จี", "คอร์ด a": "คอร์ด เอ", "คอร์ด b": "คอร์ด บี",
            "chord c": "คอร์ด ซี", "chord d": "คอร์ด ดี", "chord e": "คอร์ด อี",
            "chord f": "คอร์ด เอฟ", "chord g": "คอร์ด จี", "chord a": "คอร์ด เอ", "chord b": "คอร์ด บี",
        }

        if not hasattr(self, '_phonetic_pattern') or self._phonetic_pattern is None:
            sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
            self._phonetic_pattern = re.compile(
                r'(?<![a-zA-Z0-9])(' + '|'.join(re.escape(k) for k in sorted_keys) + r')(?![a-zA-Z0-9])',
                re.IGNORECASE
            )
            self._phonetic_lookup = {k.lower(): v for k, v in replacements.items()}

        return self._phonetic_pattern.sub(
            lambda m: self._phonetic_lookup.get(m.group(0).lower(), m.group(0)),
            text
        )

    def _clean_for_speech(self, text: str) -> str:
        """
        ทำความสะอาดข้อความก่อนส่งไปสังเคราะห์เสียง
        ลบ Markdown, Tags, วงเล็บ, สัญลักษณ์พิเศษ ที่ทำให้ Edge TTS สะดุดหรือเว้นจังหวะผิดธรรมชาติ
        """
        if not text:
            return ""
        import re
        # 1. ลบ Code blocks และ inline code
        text = re.sub(r'```[\s\S]*?```', ' โค้ดโปรแกรม ', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # 2. ลบ System tags เช่น [SILENT], [STATUS], [WINDOW: ...]
        text = re.sub(r'\[(?:WINDOW|VIDEO|SYSTEM|STATUS|STEP|END_WINDOW|SILENT)[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[.*?\]', '', text)
        
        # 3. ลบ Markdown formatting: #, *, _, ~, |, >, bullets (•, ●, ▪, ▫, -, +)
        text = re.sub(r'^[#*>\-•●▪▫+\d.]+\s*', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'[*_~|•●▪▫]+', ' ', text)
        
        # 4. ลบวงเล็บและเครื่องหมายคำพูด ไม่ให้อ่านชื่อเครื่องหมาย
        text = re.sub(r'[\(\)\[\]\{\}"\'“”‘’]+', ' ', text)
        
        # 5. แปลงสัญลักษณ์ทั่วไปเป็นคำพูด
        text = text.replace('%', ' เปอร์เซ็นต์ ')
        text = text.replace('°c', ' องศาเซลเซียส ').replace('°C', ' องศาเซลเซียส ')
        text = text.replace('&', ' และ ')
        text = text.replace('+', ' บวก ')
        text = text.replace('=', ' เท่ากับ ')
        text = text.replace('@', ' แอด ')
        text = text.replace(':', ' ')
        
        # 6. ลบเครื่องหมายวรรคตอนและจุดซ้ำซ้อนที่ทำให้ TTS สะดุด
        text = re.sub(r'[:;!?]+', ' ', text)
        text = re.sub(r'\.{2,}', ' ', text)
        text = re.sub(r'[\r\n]+', ' ', text)
        
        # 7. จัดการช่องว่าง
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _natural_prosody_enhancer(self, text: str) -> str:
        """
        ปรับปรุงจังหวะการหายใจและการเว้นวรรคให้เป็นธรรมชาติสำหรับภาษาไทย
        แทรกจังหวะพักสั้นๆ (comma) เฉพาะหลังคำลงท้ายประโยคหลักที่มีข้อความตามหลัง
        เพื่อให้อ่านลื่นไหลเหมือนมนุษย์พูดจริง ไม่เว้นจังหวะกระตุกพร่ำเพรื่อ
        """
        if not text:
            return ""
        import re
        # แทรก comma หลังคำลงท้ายวลีหลักเฉพาะเมื่อมีประโยคอื่นตามหลัง
        clause_break_patterns = [
            r'(ครับเจ้านาย|ครับท่าน|ครับผม|เรียบร้อยครับ)(?![,\.\?!…\s]*$)\s+',
        ]
        for p in clause_break_patterns:
            text = re.sub(p, r'\1, ', text)

        # ลบ comma ซ้ำซ้อน หรือ comma หัว/ท้ายประโยค
        text = re.sub(r'\s*,\s*(?:,\s*)+', ', ', text)
        text = re.sub(r'^\s*,\s*', '', text)
        text = re.sub(r'\s*,\s*$', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def _async_generate(self, text: str, output_path: str) -> None:
        """
        [Async Internal] เรียก edge-tts API จริงๆ และบันทึกเป็นไฟล์

        Args:
            text: ข้อความที่จะแปลงเป็นเสียง
            output_path: พาทที่จะบันทึก MP3
        """
        import re
        text = self._clean_for_speech(text)
        text = self._apply_phonetic_dictionary(text)
        text = self._natural_prosody_enhancer(text)
        if not text or not re.search(r'[\wก-๙]', text):
            return
        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume, pitch=self.pitch)
                await communicate.save(output_path)
                return
            except Exception as e:
                if attempt == 1:
                    raise
                await asyncio.sleep(0.5)

    def speak_stream(self, text_generator) -> None:
        """
        [Non-blocking] รับ Generator จาก LLM Stream แปลงเป็นเสียงทันทีแบบ Chunk-by-chunk
        """
        if not HAS_EDGE_TTS:
            return
            
        t = threading.Thread(
            target=self._generate_stream_and_enqueue,
            args=(text_generator,),
            daemon=True,
            name="TTS-Stream-Generator",
        )
        t.start()

    def _generate_stream_and_enqueue(self, text_generator) -> None:
        asyncio.run(self._async_generate_stream(text_generator))

    async def _async_generate_stream(self, text_generator) -> None:
        import inspect
        try:
            sem = asyncio.Semaphore(3)
            ordered: "asyncio.Queue" = asyncio.Queue()

            async def consumer():
                # เล่นตามลำดับเดิมเสมอ แม้ก้อนหลังจะสังเคราะห์เสร็จก่อน
                while True:
                    task = await ordered.get()
                    if task is None:
                        break
                    try:
                        temp_paths = await task
                    except Exception as e:
                        logger.error(f"TTS Stream chunk failed: {e}")
                        continue
                    for temp_path in temp_paths:
                        if temp_path and os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                            self._player.enqueue(temp_path, delete_after_play=True)
                        else:
                            self._cleanup(temp_path)

            consumer_task = asyncio.ensure_future(consumer())

            def submit(chunk):
                if chunk:
                    sentence = chunk.strip()
                    if sentence:
                        ordered.put_nowait(asyncio.ensure_future(
                            self._process_chunk_return_paths(sentence, sem)))

            try:
                if inspect.isasyncgen(text_generator):
                    async for chunk in text_generator:
                        submit(chunk)
                else:
                    for chunk in text_generator:
                        submit(chunk)
            finally:
                ordered.put_nowait(None)
            await consumer_task

        except Exception as e:
            logger.error(f"TTS Stream failed: {e}")

    async def _process_chunk_return_paths(self, text: str, sem: asyncio.Semaphore) -> list[str]:
        """สังเคราะห์เสียง 1 ก้อนข้อความ = 1 request (คงน้ำเสียงต่อเนื่อง ไม่แตกเป็นคลิปย่อยตามภาษา)"""
        import re

        text = self._clean_for_speech(text)
        if not text or not re.search(r'[\wก-๙]', text):
            return []

        text = self._apply_phonetic_dictionary(text)
        text = self._natural_prosody_enhancer(text)
        temp_path = None
        async with sem:
            try:
                fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_tts_")
                os.close(fd)
                communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume, pitch=self.pitch)
                await communicate.save(temp_path)
                return [temp_path]
            except Exception as e:
                logger.error(f"TTS Chunk error: {e} (text={text[:30]!r})")
                self._cleanup(temp_path)
                return []

    def _cleanup(self, path: str) -> None:
        """ลบไฟล์ชั่วคราวที่สร้างค้างไว้"""
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

_global_pipeline: Optional['LocalPipelineController'] = None

def get_pipeline() -> Optional['LocalPipelineController']:
    """ดึง instance ล่าสุดของ LocalPipelineController สำหรับระบบภายนอก (เช่น VAD Barge-in)"""
    global _global_pipeline
    return _global_pipeline

class LocalPipelineController:
    """
    ตัวควบคุมหลักที่ประสานงานทุก Module:
        STTModule → LLM Callback → TTSModule → AudioPlayer
    
    Architecture:
        - ทำงานผ่าน Background Worker Thread (Daemon)
        - รับงานผ่าน Thread-safe Queue
        - ป้องกัน Race Condition: ทำงานทีละ Task เสมอ
        - Graceful Shutdown: ทำงานที่ค้างอยู่ให้เสร็จก่อนหยุด
    
    Integration กับ jarvis.py:
        >>> from local_engine import LocalPipelineController
        >>> engine = LocalPipelineController(llm_callback=my_groq_function)
        >>> engine.start()
        >>> engine.trigger_voice_input()   # เรียกเมื่อต้องการรับเสียง
    """

    def __init__(
        self,
        llm_callback: Callable[[str], str],
        stt_language: str = "th-TH",
        tts_voice: str = "th-TH-NiwatNeural",
        on_transcribed: Optional[Callable[[str], None]] = None,
        on_response: Optional[Callable[[str], None]] = None,
        enable_wake_word: bool = True,
    ) -> None:
        """
        Args:
            llm_callback: ฟังก์ชันที่รับ text และคืน text ตอบกลับ (จาก Groq/OpenAI)
                          signature: (user_text: str) -> str
            stt_language: รหัสภาษาสำหรับ STT (default: "th-TH")
            tts_voice: ชื่อเสียง edge-tts (default: "th-TH-NiwatNeural")
            on_transcribed: Callback ที่ถูกเรียกเมื่อ STT แปลงเสร็จ (optional, สำหรับ logging/UI)
            on_response: Callback ที่ถูกเรียกเมื่อ LLM ตอบกลับ (optional, สำหรับ logging/UI)
            enable_wake_word: เปิดโหมดฟังตลอดเวลาเพื่อรอคำว่า 'jarvis' หรือไม่
        """
        global _global_pipeline
        _global_pipeline = self

        self._llm_callback = llm_callback
        self._on_transcribed = on_transcribed
        self._on_response = on_response
        self.enable_wake_word = enable_wake_word

        self._audio_player = AudioPlayer()
        self._fallback_stt = STTModule(language=stt_language, listen_timeout=10.0)
        try:
            from jarvis_stt_stream import StreamingSTTEngine
            self._stt = StreamingSTTEngine()
            logger.info("LocalPipelineController: 🚀 Using Deepgram Streaming STT (Predictive Intent Active).")
        except Exception as e:
            logger.error(f"Failed to load StreamingSTTEngine: {e}. Falling back to old STTModule.")
            self._stt = self._fallback_stt
        self._tts = TTSModule(voice=tts_voice, audio_player=self._audio_player)

        self._task_queue: queue.Queue = queue.Queue()
        self._is_running: bool = False
        self._worker_thread: Optional[threading.Thread] = None

        logger.info("LocalPipelineController: Initialized (Ready to start)")

    def interrupt(self) -> None:
        """[Instant Interruption] ตัดเสียงพูดปัจจุบันทันที และล้างคิว"""
        if hasattr(self, '_audio_player') and self._audio_player:
            self._audio_player.interrupt()
        if hasattr(self, '_tts') and self._tts:
            self._tts.interrupt()

    def start(self) -> None:
        """เริ่มระบบ — เปิด Worker Thread และ AudioPlayer"""
        if self._is_running:
            logger.warning("Pipeline: Already running. Ignoring start().")
            return

        self._is_running = True
        self._audio_player.start()
        
        def async_loop_thread():
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_until_complete(self._pipeline_worker_async())
            loop.close()

        self._worker_thread = threading.Thread(
            target=async_loop_thread,
            daemon=True,
            name="Pipeline-Async-Worker",
        )
        self._worker_thread.start()
        
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True,
            name="Heartbeat-Worker",
        )
        self._heartbeat_thread.start()

        self._bargein_thread = threading.Thread(
            target=self._bargein_worker,
            daemon=True,
            name="BargeIn-Worker",
        )
        self._bargein_thread.start()
        
        logger.info("Pipeline: ✅ Started (Background Worker + AudioPlayer + Heartbeat + BargeIn Active)")

    def stop(self) -> None:
        """หยุดระบบอย่างปลอดภัย — รอ Queue ว่างก่อน"""
        logger.info("Pipeline: Graceful shutdown initiated...")
        self._is_running = False
        self._task_queue.put(None)  
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        self._audio_player.stop()
        logger.info("Pipeline: ⛔ Stopped.")

    def _bargein_worker(self) -> None:
        """[VAD Barge-in] ตรวจจับเสียงพูดแทรกขณะกำลังเล่นเสียง TTS"""
        import struct
        import math
        import time
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            logger.info("Pipeline: 🛑 Barge-in Monitor Active")
            
            stream = None
            
            while self._is_running:
                is_playing = getattr(self._audio_player, '_is_playing', False)
                
                if not is_playing:
                    if stream is not None:
                        try:
                            stream.stop_stream()
                            stream.close()
                        except: pass
                        stream = None
                    time.sleep(0.1)
                    continue
                    
                if getattr(self._stt, 'is_listening', False):
                    time.sleep(0.1)
                    continue
                    
                if stream is None:
                    try:
                        with MIC_LOCK:
                            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                                            frames_per_buffer=CHUNK, input_device_index=self._stt._device_index)
                    except Exception as e:
                        
                        time.sleep(0.2)
                        continue
                        
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    samples = struct.unpack(f'<{CHUNK}h', data)
                    rms = math.sqrt(sum(s*s for s in samples) / max(1, CHUNK))
                    
                    if rms > 1500: 
                        logger.warning(f'Pipeline: 🛑 Barge-in Detected (RMS={int(rms)})! Stopping TTS...')
                        self._audio_player.interrupt()
                        
                        while not self._task_queue.empty():
                            try: self._task_queue.get_nowait()
                            except: pass
                            
                        time.sleep(0.5)
                except Exception:
                    time.sleep(0.1)
                    
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except: pass
            p.terminate()
        except Exception as e:
            logger.warning(f'Pipeline: Barge-in monitor unavailable: {e}')

    def trigger_voice_input(self) -> None:
        """
        [Non-blocking] เพิ่มงานฟังเสียงเข้าคิว
        
        ใช้เมื่อต้องการให้ระบบเริ่มฟังเสียงผู้ใช้
        ปลอดภัยเรียกจาก Thread ใดก็ได้ (Thread-safe)
        """
        
        if hasattr(self, '_audio_player') and getattr(self._audio_player, '_is_playing', False) or getattr(self._audio_player, 'is_playing', False):
            try:
                self._audio_player.stop()
            except Exception as e:
                logger.error(f"Failed to stop audio player: {e}")
                
        self._task_queue.put({'type': 'voice'})
        logger.info(f'Pipeline: Voice task queued (Queue size={self._task_queue.qsize()})')

    def trigger_text_input(self, text: str) -> None:
        """
        [Non-blocking] ส่งข้อความตรงไปยัง LLM โดยข้าม STT
        
        ใช้เมื่อต้องการส่งคำสั่งแบบ Text โดยไม่ต้องพูด
        เช่น integration กับ chat interface ของ jarvis.py
        
        Args:
            text: ข้อความที่จะส่งไป LLM
        """
        if text and text.strip():
            
            if hasattr(self, '_audio_player') and getattr(self._audio_player, '_is_playing', False) or getattr(self._audio_player, 'is_playing', False):
                try:
                    self._audio_player.stop()
                except Exception as e:
                    pass
                    
            logger.info(f"Pipeline: Text task queued → '{text[:40]}...'")
            if hasattr(self, '_loop') and getattr(self, '_loop', None) is not None:
                import asyncio
                fut = asyncio.run_coroutine_threadsafe(self._process_command_async(text.strip(), False), self._loop)
                def _handle_coro_result(f):
                    try:
                        f.result()
                    except Exception as err:
                        logger.error(f"Pipeline: Error in trigger_text_input coroutine: {err}", exc_info=True)
                fut.add_done_callback(_handle_coro_result)
            else:
                self._task_queue.put({"type": "text", "payload": text.strip()})

    def speak_direct(self, text: str) -> None:
        """
        [Non-blocking] พูดข้อความโดยตรง ไม่ผ่าน LLM
        
        ใช้สำหรับ System Messages หรือการตอบสนองแบบทันที
        
        Args:
            text: ข้อความที่ต้องการให้พูด
        """
        if text:
            self._tts.speak(text)

    async def _is_addressing_jarvis(self, text: str) -> bool:
        """
        """
        try:
            from groq import AsyncGroq
            import os
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return True # Fallback
                
            client = AsyncGroq(api_key=api_key)
            prompt = f"""You are an intent classifier for an AI assistant named JARVIS.
Does the following Thai sentence DIRECTLY ADDRESS or COMMAND JARVIS (like talking TO him), or does it just MENTION him in third person?
Examples:
"จาร์วิส เปิดไฟหน่อย" -> YES
"เมื่อกี้ฉันเรียกจาร์วิสแล้วเขาไม่ตอบ" -> NO
"ระบบจาร์วิสทำงานช้ามาก" -> NO
"จาร์วิสครับ ช่วยหาข้อมูลให้หน่อย" -> YES
"ถ้าเกิดจาร์วิสพังจะทำยังไง" -> NO
"เดี๋ยวให้จาร์วิสจัดการ" -> NO

Sentence: "{text}"
Reply only with YES or NO."""
            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=5
            )
            ans = response.choices[0].message.content.strip().upper()
            return "YES" in ans
        except Exception as e:
            logger.error(f"Intent check failed: {e}")
            return True

    @property
    def is_busy(self) -> bool:
        """True ถ้า Pipeline กำลังทำงานหรือมีงานในคิว"""
        return not self._task_queue.empty() or self._audio_player.is_busy

    async def _pipeline_worker_async(self) -> None:
        """
        [ULTRA-LOW LATENCY] Async Main Event Loop — ทำงานใน Background Event Loop
        
        ดึงงานจาก Queue ทีละชิ้น ทำตามลำดับ:
            1. STT (via asyncio.to_thread) หรือรับ Text โดยตรง
            2. ส่ง Text ไปยัง Async LLM Callback
            3. รับ Async Generator Response → ส่งให้ TTSModule พูดแบบ Stream
        """
        import inspect
        import time
        logger.info("Pipeline Worker: Async Loop started.")

        while self._is_running:
            try:
                task = None
                try:
                    
                    task = self._task_queue.get_nowait()
                except queue.Empty:
                    if self.enable_wake_word and not self._tts.is_busy and not self._audio_player.is_busy:
                        task = {"type": "voice", "is_wakeword": True}
                    else:
                        await asyncio.sleep(0.1)
                        continue

                if task is None:
                    break

                task_type = task.get("type")
                is_wakeword = task.get("is_wakeword", False)

                user_text = ""
                if task_type == "voice":
                    await self._tts.wait_until_played(guard_delay=0.3)
                    try:
                        user_text = await asyncio.to_thread(self._stt.listen_and_transcribe)
                    except Exception as e:
                        logger.error(f"Pipeline: Primary STT error — {e}")
                        user_text = ""

                    if not user_text and getattr(self, '_fallback_stt', None) and self._stt != self._fallback_stt:
                        logger.info("Pipeline: 🔄 Primary STT yielded empty result. Engaging fallback STT...")
                        try:
                            user_text = await asyncio.to_thread(self._fallback_stt.listen_and_transcribe)
                        except Exception as fe:
                            logger.error(f"Pipeline: Fallback STT error — {fe}")
                elif task_type == "text":
                    user_text = task.get("payload", "")

                if not user_text:
                    if not is_wakeword:
                        self._task_queue.task_done()
                    continue
                    
                if is_wakeword:
                    lower_text = user_text.lower()
                    has_wakeword = "jarvis" in lower_text or "จาร์วิส" in lower_text or "จาวิส" in lower_text
                    
                    if not has_wakeword:
                        continue
                        
                    # --- Context-Aware Wake Word Check (Pepper Potts Mode) ---
                    is_addressed = await self._is_addressing_jarvis(user_text)
                    if not is_addressed:
                        logger.info(f"Pipeline: 🛑 Wake word ignored (Mentioned only, not addressed): '{user_text}'")
                        if not is_wakeword:
                            self._task_queue.task_done()
                        continue
                    
                    if has_wakeword:
                        import re
                        command = re.sub(r'[\(\)\[\]\{\},\.]*\s*(jarvis|จาร์วิส|จาวิส|j\.?a\.?r\.?v\.?i\.?s)\s*[\(\)\[\]\{\},\.]*', ' ', lower_text, flags=re.IGNORECASE).strip()
                        command = re.sub(r'^[^\wก-๙]+', '', command).strip()
                    else:
                        command = lower_text.strip()
                    
                    if not command:
                        logger.info("Pipeline: Wake word detected! Prompting user...")
                        self._tts.speak("ครับเจ้านาย")
                        await self._tts.wait_until_played(guard_delay=0.4)
                        self.trigger_voice_input()
                        self._last_interaction_time = time.time()
                        continue
                        
                    user_text = command
                    logger.info(f"Pipeline: Wake word + command detected -> {user_text}")

                if self._on_transcribed:
                    try:
                        self._on_transcribed(user_text)
                    except Exception:
                        pass

                self._last_user_input = user_text
                logger.info(f"Pipeline: 🧠 Sending to Async LLM → '{user_text[:60]}'")

                clean_text = user_text.strip().lower()

                if any(w == clean_text or clean_text.startswith(w) or f" {w}" in clean_text for w in PIPELINE_STOP_WORDS):
                    logger.info(f"Pipeline: 🛑 Intercepted STOP command ('{clean_text}'). Silencing Jarvis immediately.")
                    self._audio_player.interrupt()
                    if not is_wakeword:
                        self._task_queue.task_done()
                    send_to_island("STANDBY", "")
                    continue



                ai_response = None
                try:
                    if inspect.iscoroutinefunction(self._llm_callback):
                        ai_response = await self._llm_callback(user_text)
                    else:
                        ai_response = await asyncio.to_thread(self._llm_callback, user_text)
                except Exception as e:
                    logger.error(f"Pipeline: LLM callback failed — {e}", exc_info=True)
                    ai_response = "ขออภัย ระบบสื่อสารกับ AI ขัดข้องชั่วคราวครับ"

                if not ai_response:
                    logger.warning("Pipeline: LLM returned empty response.")
                    self._task_queue.task_done()
                    continue

                import types
                if inspect.isasyncgen(ai_response):
                    logger.info("Pipeline: ✅ Async LLM Response Stream received")
                    await self._tts._async_generate_stream(ai_response)
                elif isinstance(ai_response, types.GeneratorType):
                    logger.info("Pipeline: ✅ Sync LLM Response Stream received")
                    self._tts.speak_stream(ai_response)
                else:
                    logger.info(f"Pipeline: ✅ LLM Response received ({len(str(ai_response))} chars)")
                    response_text = str(ai_response)
                    if self._on_response:
                        try:
                            self._on_response(response_text)
                        except Exception:
                            pass
                            
                    if "[SILENT]" in response_text.upper():
                        logger.info("Pipeline: 🤫 [SILENT] tag detected. Executing action without voice feedback.")
                    else:
                        self._tts.speak(response_text)
                        await self._tts.wait_until_played(guard_delay=0.6)
                
                self._last_interaction_time = time.time()

                if not is_wakeword:
                    self._task_queue.task_done()
                    send_to_island("STANDBY", "")

            except Exception as e:
                logger.error(f"Pipeline Worker: Unhandled error — {e}", exc_info=True)
                await asyncio.sleep(1.0)  

        logger.info("Pipeline Worker: Async Loop exited.")

    async def _process_command_async(self, user_text: str, is_wakeword: bool, from_queue: bool = False) -> None:
        import inspect
        import time
        import asyncio
        import random
        
        try:
            self._last_user_input = user_text
            logger.info(f"Pipeline: 🧠 Sending to Async LLM → '{user_text[:60]}'")

            clean_text = user_text.strip().lower()
            if any(w == clean_text or clean_text.startswith(w) or f" {w}" in clean_text for w in PIPELINE_STOP_WORDS):
                logger.info(f"Pipeline: 🛑 Intercepted STOP command ('{clean_text}'). Silencing Jarvis immediately.")
                self._audio_player.interrupt()
                if from_queue:
                    self._task_queue.task_done()
                send_to_island("STANDBY", "")
                return



            ai_response = None
            try:
                if inspect.iscoroutinefunction(self._llm_callback):
                    ai_response = await self._llm_callback(user_text)
                else:
                    ai_response = await asyncio.to_thread(self._llm_callback, user_text)
            except Exception as e:
                logger.error(f"Pipeline: LLM callback failed — {e}", exc_info=True)
                ai_response = "ขออภัย ระบบสื่อสารกับ AI ขัดข้องชั่วคราวครับ"

            if not ai_response:
                logger.warning("Pipeline: LLM returned empty response.")
                if from_queue:
                    self._task_queue.task_done()
                return

            import types
            if inspect.isasyncgen(ai_response):
                logger.info("Pipeline: ✅ Async LLM Response Stream received")
                await self._tts._async_generate_stream(ai_response)
            elif isinstance(ai_response, types.GeneratorType):
                logger.info("Pipeline: ✅ Sync LLM Response Stream received")
                self._tts.speak_stream(ai_response)
            else:
                logger.info(f"Pipeline: ✅ LLM Response received ({len(str(ai_response))} chars)")
                if self._on_response:
                    try:
                        self._on_response(str(ai_response))
                    except Exception:
                        pass
                self._tts.speak(str(ai_response))
                await self._tts.wait_until_played(guard_delay=0.6)
            
            self._last_interaction_time = time.time()

            if from_queue:
                self._task_queue.task_done()
            send_to_island("STANDBY", "")
        except Exception as e:
            logger.error(f"Pipeline: Unhandled error in _process_command_async: {e}", exc_info=True)
            if from_queue:
                try: self._task_queue.task_done()
                except: pass
            send_to_island("STANDBY", "")

    def _heartbeat_worker(self) -> None:
        """Thread สำหรับส่ง Heartbeat ไปที่ Dynamic Island ทุก 5 วินาที"""
        import time
        while self._is_running:
            try:
                send_to_island("HEARTBEAT", "")
            except Exception:
                pass
            time.sleep(5.0)

if __name__ == "__main__":
    """
    ทดสอบระบบ Voice Pipeline แบบ Standalone
    รันด้วย: python local_engine.py
    """

    def mock_llm(user_text: str) -> str:
        logger.info(f"[MOCK LLM] Received: '{user_text}'")
        time.sleep(1.0)  
        return f"กระผมรับทราบคำสั่ง '{user_text}' เรียบร้อยแล้วครับเจ้านาย"

    def on_user_spoke(text: str) -> None:
        print(f"\n👤 USER: {text}")

    def on_ai_responded(text: str) -> None:
        print(f"🤖 JARVIS: {text}\n")

    print("=" * 60)
    print("  J.A.R.V.I.S. LOCAL ENGINE — Voice Pipeline Test")
    print("=" * 60)

    engine = LocalPipelineController(
        llm_callback=mock_llm,
        stt_language="th-TH",
        tts_voice="th-TH-NiwatNeural",
        on_transcribed=on_user_spoke,
        on_response=on_ai_responded,
    )

    engine.start()

    print("\n[TEST 1] Sending text directly to LLM...")
    engine.trigger_text_input("สวัสดีครับ จาร์วิส")
    time.sleep(8)

    engine.stop()
    print("\n✅ Pipeline test complete.")
