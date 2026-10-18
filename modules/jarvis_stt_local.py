"""
jarvis_stt_local.py
Speech-to-Text Engine (Groq Cloud Whisper with Faster-Whisper Fallback)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from faster_whisper import WhisperModel
from groq import Groq

load_dotenv()

# Setup Module Logger
logger = logging.getLogger("JARVIS-STT")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class HybridSTTEngine:
    _instance: Optional[HybridSTTEngine] = None
    client: Optional[Groq] = None
    model_name: str = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")
    local_model: Optional[WhisperModel] = None
    local_model_size: str = "base"
    local_device: str = "cpu"
    local_compute_type: str = "int8"

    # Targeted domain vocabulary prompt for Thai speech (Keywords only to prevent Whisper prompt continuation hallucination)
    VOCABULARY_PROMPT: str = "จาร์วิส, Jarvis, AI, ระบบผู้ช่วย, เซิร์ฟเวอร์, โค้ด, บอร์ด, อะคริลิค, รีเลย์, Python, พลังงาน, วิเคราะห์, หน้าจอ"

    def __new__(cls) -> HybridSTTEngine:
        if cls._instance is None:
            cls._instance = super(HybridSTTEngine, cls).__new__(cls)

            # Cloud (Primary: whisper-large-v3 gives 100% Thai accuracy with 0.48s latency)
            cls._instance.client = None
            cls._instance.model_name = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")

            # Local (Fallback)
            cls._instance.local_model = None
            cls._instance.local_model_size = "base"
            cls._instance.local_device = "cpu"
            cls._instance.local_compute_type = "int8"
        return cls._instance

    def _initialize_cloud(self) -> None:
        if self.client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                logger.error("GROQ_API_KEY is not set in .env")
                return
            logger.info(
                f"Initializing Primary STT: Groq Cloud ({self.model_name})"
            )
            try:
                self.client = Groq(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq Client: {e}")
                self.client = None

    def _initialize_local(self) -> None:
        if self.local_model is None:
            logger.info(
                f"Initializing Backup STT: Local Faster-Whisper "
                f"({self.local_model_size})"
            )
            try:
                self.local_model = WhisperModel(
                    self.local_model_size,
                    device=self.local_device,
                    compute_type=self.local_compute_type
                )
            except Exception as e:
                logger.error(f"Failed to initialize Local Backup STT: {e}")
                self.local_model = None

    def warmup(self) -> None:
        """Initialize the primary client early."""
        self._initialize_cloud()

    def _apply_typo_fixes(self, text: str) -> str:
        typo_map = {
            "จาวิท": "จาร์วิส",
            "ชาวิด": "จาร์วิส",
            "จาร์วิต": "จาร์วิส",
            "ชาวิศ": "จาร์วิส",
            "จาวิศ": "จาร์วิส",
            "จาวิด": "จาร์วิส",
            "จาวิช": "จาร์วิส",
            "จาวิส": "จาร์วิส",
            "จารวิส": "จาร์วิส",
            "จาวิทย์": "จาร์วิส",
            "จาร์วิทย์": "จาร์วิส",
            "จาหวิด": "จาร์วิส",
            "จาวิก": "จาร์วิส",
            "จาวิต": "จาร์วิส",
            "ชาวิก": "จาร์วิส",
            "ชาวิส": "จาร์วิส",
            "จาวิสส": "จาร์วิส",
            "jarvis": "จาร์วิส",
            "Jarvis": "จาร์วิส",
            "JARVIS": "จาร์วิส",
            # Phonetic recovery for co-articulated status queries
            "ชิดท่านาควมพ่อ": "เช็คสถานะคอมให้หน่อย",
            "ชิดท่านาควม": "เช็คสถานะคอม",
            "ชิดทานาควม": "เช็คสถานะคอม",
            "ชิดทานา": "เช็คสถานะ",
            "เช็คสตาร์ดักคอม": "เช็คสถานะคอม",
            "เช็กสถานะ": "เช็คสถานะ",
            "เชคสถานะ": "เช็คสถานะ",
            "ไฟดับ": "ปิดไฟ",
            "เป็ดไฟ": "เปิดไฟ",
            "เซิฟเวอ": "เซิร์ฟเวอร์",
            "เซิพเวอ": "เซิร์ฟเวอร์",
            "พายธอน": "Python",
            "อคริลิค": "อะคริลิค",
        }
        corrected_text = text
        for wrong, right in typo_map.items():
            if wrong in corrected_text:
                corrected_text = corrected_text.replace(wrong, right)

        # Strip rogue brackets / acronym hallucinations like "),J.A.R.V.I.S)," or "), j.a.r.v.i.s),"
        import re
        corrected_text = re.sub(r'[\)\]\},]+\s*j\.?a\.?r\.?v\.?i\.?s\b[\)\]\},]*', '', corrected_text, flags=re.IGNORECASE)
        corrected_text = re.sub(r'จาร์วิส[\)\]\},]+', 'จาร์วิส ', corrected_text)
        corrected_text = re.sub(r'\s{2,}', ' ', corrected_text).strip()

        if corrected_text != text:
            logger.info(f"Typo corrected: '{text}' -> '{corrected_text}'")
        return corrected_text

    def _is_hallucination(self, text: str) -> bool:
        if not text:
            return True
        import re
        norm = re.sub(r'[\s\W_]+', '', text.lower())
        if len(norm) < 2:
            return True

        # Boilerplate subtitles / video outros that are NEVER valid user commands
        boilerplate_substrings = [
            "โปรดติดตามตอนต่อไป", "ติดตามตอนต่อไป", "ติดตามชมตอนต่อไป", "จบตอน",
            "ซับไทยโดย", "แปลโดย", "กดไลค์", "กดแชร์", "กดติดตาม", "subscribe",
            "ขอบคุณสำหรับการรับชม", "ขอบคุณที่รับชม", "สำหรับวันนี้ขอลาไปก่อน",
            "พบกันใหม่คลิปหน้า", "พบกันใหม่", "amaraorg", "subtitles", "สนับสนุนช่อง",
            "สั่งงานทั่วไปและถามตอบ", "บทสนทนาภาษาไทย", "กับผู้ช่วยจาร์วิสสั่งงาน",
            "รับชมคลิป", "วีดีโอนี้", "ช่องยูทูป", "youtube", "บรรยายไทย"
        ]
        for b in boilerplate_substrings:
            if b in norm:
                return True

        # Isolated single-token hallucinations on low audio / mic noise
        isolated_tokens = [
            "ที่ผม", "พิสดิ์", "ขอบคุณครับ", "ขอบคุณค่ะ", "อืม", "อือ", "อ้า", 
            "สวัสดี", "สวัสดีครับ", "สวัสดีค่ะ", "โอเค", "อ่า", "ฮัลโหล"
        ]
        if norm in isolated_tokens:
            return True

        return False

    def transcribe(self, audio_file_path: str) -> str:
        """Transcribe audio using Groq Cloud Whisper Large V3.

        If it fails, fall back to Local Faster-Whisper.
        """
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return ""

        self._initialize_cloud()

        # 1. Try Primary Cloud (Groq Whisper Large V3)
        if self.client:
            try:
                start_time = time.time()
                with open(audio_file_path, "rb") as file:
                    transcription = self.client.audio.transcriptions.create(
                        file=(os.path.basename(audio_file_path), file.read()),
                        model=self.model_name,
                        language="th",
                        prompt=self.VOCABULARY_PROMPT,
                        response_format="json",
                        temperature=0.0
                    )

                elapsed = time.time() - start_time
                text = transcription.text.strip()
                if self._is_hallucination(text):
                    logger.warning(f"☁️ [Cloud STT] Ignored Whisper hallucination ({elapsed:.2f}s): '{text}'")
                    return ""
                logger.info(f"☁️ [Cloud STT] ({elapsed:.2f}s): {text}")
                return self._apply_typo_fixes(text)

            except Exception as e:
                logger.warning(
                    f"⚠️ Groq Cloud STT failed ({e}). "
                    f"Falling back to Local Model..."
                )
        else:
            logger.warning(
                "⚠️ Groq Client not available. Falling back to Local Model..."
            )

        # 2. Try Backup Local (Faster-Whisper)
        self._initialize_local()
        if self.local_model:
            try:
                start_time = time.time()
                segments, _ = self.local_model.transcribe(
                    audio_file_path,
                    beam_size=1,
                    language="th",
                    condition_on_previous_text=False
                )

                text = " ".join([segment.text for segment in segments]).strip()
                elapsed = time.time() - start_time
                if self._is_hallucination(text):
                    logger.warning(f"💻 [Local STT] Ignored Whisper hallucination ({elapsed:.2f}s): '{text}'")
                    return ""
                logger.info(f"💻 [Local STT] ({elapsed:.2f}s): {text}")
                return self._apply_typo_fixes(text)

            except Exception as e:
                logger.error(f"❌ Local Transcription error: {e}")
                return ""

        return ""


# Expose a global instance
stt_engine = HybridSTTEngine()


def transcribe_audio(file_path: str) -> str:
    """Helper function to transcribe audio from a file path."""
    return stt_engine.transcribe(file_path)
