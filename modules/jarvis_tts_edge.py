import os
import re
import threading
import asyncio
import logging
import tempfile
import queue
from typing import AsyncGenerator, Optional, Tuple

try:
    import edge_tts
except ImportError:
    edge_tts = None
    logging.warning("[JARVIS TTS] 'edge-tts' is not installed. Please run 'pip install edge-tts'.")

try:
    import pygame
except ImportError:
    pygame = None
    logging.warning("[JARVIS TTS] 'pygame' is not installed. Please run 'pip install pygame' for audio playback.")

JARVIS_SYSTEM_PROMPT = (
    "คุณคือ J.A.R.V.I.S. ปัญญาประดิษฐ์ผู้ช่วยส่วนตัวที่ล้ำสมัยที่สุด "
    "คุณต้องตอบคำถามด้วยโทนเสียงที่สุภาพ สุขุม นุ่มนวล มีไหวพริบ และเป็นมืออาชีพเสมอ "
    "ต้องตอบเป็นภาษาไทยอย่างเป็นธรรมชาติเสมือนมนุษย์จริง ไม่ลงท้าย 'ครับ' พร่ำเพรื่อทุกประโยคย่อย "
    "แต่ให้เลือกใช้คำว่า 'ครับ' หรือ 'ครับเจ้านาย' เฉพาะจุดสำคัญ เช่น เปิดทักทายหรือสรุปปิดท้ายอย่างสง่างาม"
)

class JarvisStreamingTTS:
    """
    โมดูลจัดการ Text-to-Speech โดยใช้ Microsoft Edge TTS (Cloud)
    เสียงภาษาไทยเนียนระดับมนุษย์ พร้อมระบบ Dynamic Emotion Prosody และ Queue เล่นเสียงแบบไร้รอยต่อ
    """

    def __init__(self, voice_name: Optional[str] = None):
        """
        :param voice_name: รหัสเสียง (th-TH-NiwatNeural เสียงผู้ชายสุภาพแบบ JARVIS, th-TH-PremwadeeNeural เสียงผู้หญิง)
        """
        self.voice_name = voice_name or os.getenv("JARVIS_VOICE", "th-TH-NiwatNeural")
        self.is_playing = False
        self._playback_thread: Optional[threading.Thread] = None
        self._audio_queue = queue.Queue()
        
        if pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception as e:
                logging.warning(f"[JARVIS TTS] Pygame mixer init warning: {e}")
            
        self._verify_dependencies()

    def _get_vocal_params(self, text: str = "") -> Tuple[str, str, str]:
        """
        ดึงพารามิเตอร์ Rate, Pitch, Volume ตามอารมณ์ของข้อความและบริบททางจิตวิทยา
        """
        try:
            from jarvis_mood import detect_text_vocal_tone
            return detect_text_vocal_tone(text)
        except Exception:
            return ("+0%", "-1Hz", "+0%")

    def _sanitize_for_speech(self, text: str) -> str:
        """
        [NATURAL SPEECH SANITIZER & PHONETIC ENGINE]
        ลบสัญลักษณ์ Markdown, จัดการ URL, ปรับคำศัพท์ภาษาอังกฤษให้ออกเสียงไทยเป็นธรรมชาติ
        และคงจังหวะการหายใจของประโยคโดยไม่ทำให้เสียงกระตุก
        """
        if not text:
            return ""

        # 1. Clean markdown code blocks and inline code
        text = re.sub(r'```[\s\S]*?```', ' โค้ดโปรแกรม ', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 2. Clean markdown headers, bold, italics, bullets, blockquotes, quotes, and brackets
        text = re.sub(r'^[#*>\-•●▪▫+\d.]+\s*', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'[*_~|•●▪▫]+', ' ', text)
        text = re.sub(r'[\(\)\[\]\{\}"\'“”‘’]+', ' ', text)

        # 3. Clean URLs so Niwat speaks naturally instead of spelling out 'h-t-t-p-s-colon-slash...'
        text = re.sub(r'https?://(?:www\.)?([a-zA-Z0-9.-]+)(?:/[^\s]*)?', r' เว็บไซต์ \1 ', text)

        # 4. Clean brackets and system tags like [STATUS], [WINDOW: ...], [SILENT]
        text = re.sub(r'\[(?:WINDOW|VIDEO|SYSTEM|STATUS|STEP|END_WINDOW|SILENT)[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[.*?\]', '', text)

        # 5. Clean common symbols and measurements
        text = text.replace('%', ' เปอร์เซ็นต์ ')
        text = text.replace('°c', ' องศาเซลเซียส ').replace('°C', ' องศาเซลเซียส ')
        text = text.replace('&', ' และ ')
        text = text.replace('+', ' บวก ')
        text = text.replace('=', ' เท่ากับ ')
        text = text.replace('@', ' แอด ')
        text = text.replace(':', ' ')

        # 6. Apply comprehensive phonetic translation from voice_protocol (1,300+ technical terms)
        try:
            from voice_protocol import apply_nachapol_voice_protocol
            text = apply_nachapol_voice_protocol(text)
        except ImportError:
            try:
                from modules.voice_protocol import apply_nachapol_voice_protocol
                text = apply_nachapol_voice_protocol(text)
            except ImportError:
                text = re.sub(r'(?i)arc reactor', 'อาร์ค รีแอคเตอร์', text)
                text = re.sub(r'(?i)j\.?a\.?r\.?v\.?i\.?s\.?', 'จาร์วิส', text)
                text = re.sub(r'(?i)ai', 'เอไอ', text)
                text = re.sub(r'(?i)cpu', 'ซีพียู', text)
                text = re.sub(r'(?i)ram', 'แรม', text)
                text = re.sub(r'(?i)gpu', 'จีพียู', text)

        # 6.5 Naturalize polite particle cadence: Reduce repetitive 'ครับ' in consecutive sub-clauses
        text = self._naturalize_polite_repetitions(text)

        # 7. Natural pauses: Smooth breath cadence without robotic stops
        # Normalize newlines and ellipses into natural spaces instead of comma pauses
        text = re.sub(r'[\r\n]+', ' ', text)
        text = re.sub(r'\.{2,}', ' ', text)
        text = re.sub(r'[!?;]+', ' ', text)

        # 7.1 Natural breath pause only after key boundary particles when followed by more speech
        text = re.sub(r'(ครับเจ้านาย|ครับท่าน|ครับผม|เรียบร้อยครับ)(?![,\.\?!…\s]*$)\s+', r'\1, ', text)

        # 7.2 Clean redundant commas, trailing punctuation, and normalize spaces
        text = re.sub(r'\s*,\s*(?:,\s*)+', ', ', text)
        text = re.sub(r'\s*,\s*$', '', text)
        text = re.sub(r'^\s*,\s*', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _naturalize_polite_repetitions(self, text: str) -> str:
        """
        [NATURAL POLITE PARTICLE CADENCE]
        ลดความซ้ำซากของคำลงท้าย 'ครับ' ในประโยคติดๆ กัน เพื่อให้เหมือนมนุษย์พูดจริง
        ไม่ใช่บอตคอลเซ็นเตอร์ที่พูด 'ครับ' ทุกอนุประโยค
        เช่น 'ผมรันคำสั่งแล้วครับ ข้อมูลพร้อมแล้วครับ เจ้านายดูได้เลยครับ'
        -> 'ผมรันคำสั่งแล้ว ข้อมูลพร้อมแล้ว เจ้านายดูได้เลยครับ'
        """
        if not text:
            return ""

        # 1. ลบ 'ครับ' ก่อนคำเชื่อมประโยค (เช่น "แล้วครับ และ" -> "แล้ว และ")
        text = re.sub(r'([ก-๙]+)(?:ครับ|นะครับ)\s+(และ|หรือ|แต่|โดย|ซึ่ง|จากนั้น|เดี๋ยว|ตอนนี้)', r'\1 \2', text)

        # 2. หากมี 'ครับ' ซ้ำซ้อนกันในประโยคย่อยติดๆ กัน ให้คงไว้เฉพาะจุดแรก (ทักทาย) และจุดท้าย (สรุป)
        text = re.sub(r'([ก-๙]+)(?:ครับ|นะครับ)\s+([ก-๙]{4,}.*?(?:ครับเจ้านาย|ครับท่าน|ครับผม|นะครับ|ครับ))', r'\1 \2', text)

        return text

    def _verify_dependencies(self) -> None:
        if not edge_tts:
            logging.error("[JARVIS TTS] ไม่สามารถทำงานได้ ขาดไลบรารี 'edge-tts'")
        if not pygame:
            logging.error("[JARVIS TTS] ไม่สามารถทำงานได้ ขาดไลบรารี 'pygame'")

    def _audio_playback_worker(self) -> None:
        """เธรดเบื้องหลังสำหรับรอรับไฟล์เสียงจาก Queue มาเปิดเล่นทีละไฟล์"""
        logging.info("[JARVIS TTS] เริ่มระบบรอคิวเล่นเสียง (Playback Worker)...")
        
        while self.is_playing:
            try:
                audio_file = self._audio_queue.get(timeout=1.0)
                
                if audio_file == "STOP":
                    break
                    
                if not os.path.exists(audio_file):
                    continue
                    
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy() and self.is_playing:
                    pygame.time.Clock().tick(15)
                
                try:
                    os.remove(audio_file)
                except Exception:
                    pass
                    
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"[JARVIS TTS] ปัญหาตอนเล่นเสียง: {e}")
                
        logging.info("[JARVIS TTS] ปิดระบบเล่นเสียงเรียบร้อย")

    async def speak_stream(self, text_generator: AsyncGenerator[str, None]) -> None:
        """
        รับ Async Generator (ประโยคที่ถูกทยอยส่งมา) 
        แปลงเป็นเสียงทีละประโยคด้วย Dynamic Emotional Prosody แล้วส่งเข้าคิวเล่นเสียงทันที
        """
        self.stop() 
        
        if not edge_tts or not pygame:
            return

        self.is_playing = True
        
        while not self._audio_queue.empty():
            try:
                old_file = self._audio_queue.get_nowait()
                if old_file != "STOP" and os.path.exists(old_file):
                    os.remove(old_file)
            except Exception:
                pass

        self._playback_thread = threading.Thread(target=self._audio_playback_worker, daemon=True)
        self._playback_thread.start()

        try:
            async for raw_chunk in text_generator:
                if not self.is_playing:
                    break
                    
                chunk = self._sanitize_for_speech(raw_chunk)
                if not chunk or not re.search(r'[ก-๙a-zA-Z0-9]', chunk):
                    continue
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp_path = temp_file.name
                temp_file.close()
                
                # Modulate vocal rate, pitch, and volume based on emotion
                rate, pitch, volume = self._get_vocal_params(chunk)
                communicate = edge_tts.Communicate(
                    chunk, 
                    self.voice_name, 
                    rate=rate, 
                    pitch=pitch, 
                    volume=volume
                )
                await communicate.save(temp_path)
                
                if self.is_playing:
                    self._audio_queue.put(temp_path)
                else:
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    
        except Exception as e:
            logging.error(f"[JARVIS TTS] ข้อผิดพลาดการแปลงเสียงจาก Edge TTS: {e}")

    def stop(self) -> None:
        """หยุดการทำงานทั้งหมดทันที (Barge-in / Interrupt)"""
        self.is_playing = False
        try:
            if pygame and hasattr(pygame, 'mixer') and pygame.mixer and hasattr(pygame.mixer, 'get_init') and pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        
        self._audio_queue.put("STOP")
        
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)

    def speak(self, text: str) -> None:
        """
        ฟังก์ชันเรียกใช้แบบ Synchronous สำหรับให้โมดูลเบื้องหลังเรียกใช้ได้ทันที
        """
        async def single_text_gen():
            yield text
            
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.speak_stream(single_text_gen()))
        except RuntimeError:
            asyncio.run(self.speak_stream(single_text_gen()))

    def __del__(self):
        self.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def mock_llm_stream():
        sentences = [
            "สวัสดีครับเจ้านาย! ",
            "วันนี้ทุกระบบทำงานได้อย่างราบรื่นและทรงพลังมากครับ ",
            "มีงานชิ้นไหนให้ผมช่วยจัดการอีกไหมครับท่าน"
        ]
        for s in sentences:
            yield s
            await asyncio.sleep(1.2) 

    tts_engine = JarvisStreamingTTS(voice_name="th-TH-NiwatNeural")
    print(f"✅ JarvisStreamingTTS Initialized Successfully. Voice: {tts_engine.voice_name}")
    print("🤖 SYSTEM PROMPT:", JARVIS_SYSTEM_PROMPT)

