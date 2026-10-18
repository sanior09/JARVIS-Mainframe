"""
jarvis_stt_stream.py
Real-time Streaming STT using Deepgram API (WebSocket) for Word-by-Word Intent Prediction
"""

import os
import time
import logging
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

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
            
        self.deepgram = DeepgramClient(self.api_key)
        self.on_partial = on_partial  # Callback เมื่อได้คำที่กำลังพูด (ทีละคำ)
        self.on_final = on_final      # Callback เมื่อพูดจบประโยค (มีช่องว่างเสียง)
        self.is_listening = False
        self.dg_connection = None
        self.microphone = None
        self._final_text = ""
        self._listen_done_event = None

    def listen_and_transcribe(self) -> str:
        """
        Drop-in replacement สำหรับระบบเก่า (Blocking)
        แต่ภายในทำงานแบบ Streaming และยิง Partial/Predictive Intent ไปด้วย
        """
        if not self.api_key:
            return ""
            
        import threading
        self._final_text = ""
        self._listen_done_event = threading.Event()
        
        try:
            self.dg_connection = self.deepgram.listen.live.v("1")
            
            def on_message(self, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) == 0:
                    return
                
                if result.is_final:
                    logger.info(f"🟢 [FINAL]: {sentence}")
                    
                    # ตรวจสอบว่าคำสั่งนี้ถูกรันล่วงหน้า (Speculative) ไปแล้วหรือยัง
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
                    self._listen_done_event.set()  # ปลดล็อค
                else:
                    logger.info(f"🟡 [PARTIAL]: {sentence}")
                    if self.on_partial:
                        self.on_partial(sentence)
                        
                    # แอบยิง Predictive Intent แบบเบื้องหลัง
                    try:
                        import asyncio
                        from jarvis_stream_intent import sys_stream_intent
                        
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(sys_stream_intent.analyze_stream(sentence))
                        else:
                            asyncio.run(sys_stream_intent.analyze_stream(sentence))
                    except Exception as ex:
                        pass

            def on_error(self, error, **kwargs):
                logger.error(f"Deepgram Error: {error}")
                self._listen_done_event.set()

            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

            options = LiveOptions(
                model="nova-2",
                language="th",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                endpointing=400
            )
            
            self.dg_connection.start(options)
            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()
            self.is_listening = True
            
            logger.info("🎙️ [STREAMING STT] รอรับคำสั่ง (พูดได้เลย)...")
            
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
        if self.microphone:
            self.microphone.finish()
        if self.dg_connection:
            self.dg_connection.finish()
        logger.info("🛑 [STREAMING STT] ปิดระบบฟังเสียงเรียบร้อยแล้ว")
