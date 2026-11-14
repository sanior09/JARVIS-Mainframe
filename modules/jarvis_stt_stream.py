"""
jarvis_stt_stream.py
Real-time Streaming STT using Deepgram API (WebSocket) for Word-by-Word Intent Prediction
"""

import os
import threading
import time
import logging
from dotenv import load_dotenv
from deepgram import DeepgramClient
from deepgram.core.events import EventType

try:
    import sounddevice as sd
except ImportError:
    sd = None

load_dotenv()

# Setup Module Logger
logger = logging.getLogger("JARVIS-STT-STREAM")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class StreamingSTTEngine:
    """
    ระบบฟังเสียงและแปลผลแบบ Real-time ทีละคำ 
    เพื่อใช้ร่วมกับ Predictive Intent (เดาใจก่อนพูดจบ)
    """
    def __init__(self, on_partial=None, on_final=None):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            logger.error("DEEPGRAM_API_KEY not found in .env! กรุณาใส่ API Key")
            return
            
        self.deepgram = DeepgramClient(api_key=self.api_key)
        self.on_partial = on_partial  # Callback เมื่อได้คำที่กำลังพูด (ทีละคำ)
        self.on_final = on_final      # Callback เมื่อพูดจบประโยค (มีช่องว่างเสียง)
        self.is_listening = False
        self.dg_connection = None
        self._dg_context = None
        self.microphone = None
        self.audio_stream = None
        self._final_text = ""
        self._listen_done_event = None

    def _send_audio_chunk(self, payload: bytes) -> None:
        if self.dg_connection is None:
            return
        if hasattr(self.dg_connection, "send_media"):
            self.dg_connection.send_media(payload)
        else:
            self.dg_connection.send(payload)

    def _handle_transcript_message(self, message, **kwargs) -> None:
        channel = getattr(message, "channel", None)
        alternatives = getattr(channel, "alternatives", None) if channel else None
        if not alternatives:
            return
        sentence = getattr(alternatives[0], "transcript", "") or ""
        if not sentence:
            return

        if getattr(message, "is_final", False):
            logger.info(f"🟢 [FINAL]: {sentence}")
            try:
                from jarvis_stream_intent import sys_stream_intent
                if sys_stream_intent.was_handled_early(sentence):
                    logger.info("⏭️ [SPECULATIVE SKIP] คำสั่งนี้ถูกรันล่วงหน้าไปแล้ว ข้ามการรันซ้ำ")
                    self._final_text = "[SILENT_EXECUTION]"
                    if self.on_final:
                        self.on_final("[SILENT_EXECUTION]")
                    self._listen_done_event.set()
                    return
            except ImportError:
                pass

            self._final_text = sentence
            if self.on_final:
                self.on_final(sentence)
            self._listen_done_event.set()
        else:
            logger.info(f"🟡 [PARTIAL]: {sentence}")
            if self.on_partial:
                self.on_partial(sentence)
            try:
                import asyncio
                from jarvis_stream_intent import sys_stream_intent

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(sys_stream_intent.analyze_stream(sentence))
                else:
                    asyncio.run(sys_stream_intent.analyze_stream(sentence))
            except Exception:
                pass

    def _handle_error(self, error, **kwargs) -> None:
        logger.error(f"Deepgram Error: {error}")
        if self._listen_done_event is not None:
            self._listen_done_event.set()

    def listen_and_transcribe(self) -> str:
        """
        Drop-in replacement สำหรับระบบเก่า (Blocking)
        แต่ภายในทำงานแบบ Streaming และยิง Partial/Predictive Intent ไปด้วย
        """
        if not self.api_key:
            return ""
        if sd is None:
            logger.error("sounddevice is not installed. Cannot stream microphone audio.")
            return ""

        self._final_text = ""
        self._listen_done_event = threading.Event()

        try:
            self._dg_context = self.deepgram.listen.v1.connect(
                model="nova-2",
                language="th",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                endpointing=400,
            )
            self.dg_connection = self._dg_context.__enter__()
            self.dg_connection.on(EventType.MESSAGE, lambda msg, **kw: self._handle_transcript_message(msg, **kw))
            self.dg_connection.on(EventType.ERROR, lambda err, **kw: self._handle_error(err, **kw))

            listener_thread = threading.Thread(
                target=self.dg_connection.start_listening,
                daemon=True,
                name="DeepgramStreamListener",
            )
            listener_thread.start()

            def _on_audio(indata, frames, time_info, status):
                if self.is_listening and self.dg_connection is not None:
                    try:
                        self._send_audio_chunk(bytes(indata))
                    except Exception:
                        pass

            self.audio_stream = sd.RawInputStream(
                samplerate=16000,
                blocksize=1024,
                channels=1,
                dtype="int16",
                callback=_on_audio,
            )
            self.is_listening = True
            self.audio_stream.start()
            
            logger.info("🎙️ [STREAMING STT] รอรับคำสั่งผ่าน sounddevice default mic (พูดได้เลย)...")
            
            # รอจนกว่าจะได้ is_final
            self._listen_done_event.wait(timeout=10.0)
            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
        finally:
            self.stop_listening()
            
        return self._final_text

    def stop_listening(self):
        """หยุดฟังและตัดการเชื่อมต่อ"""
        self.is_listening = False
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None
        if self.microphone:
            self.microphone.finish()
        if self.dg_connection is not None:
            try:
                if hasattr(self.dg_connection, "send_close_stream"):
                    self.dg_connection.send_close_stream()
                elif hasattr(self.dg_connection, "finish"):
                    self.dg_connection.finish()
            except Exception:
                pass
            self.dg_connection = None
        if self._dg_context is not None:
            try:
                self._dg_context.__exit__(None, None, None)
            except Exception:
                pass
            self._dg_context = None
        logger.info("🛑 [STREAMING STT] ปิดระบบฟังเสียงเรียบร้อยแล้ว")
