import os
import threading
import asyncio
import logging
import tempfile
import queue
from typing import AsyncGenerator, Optional

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
    "ต้องตอบเป็นภาษาไทยเท่านั้น และลงท้ายประโยคด้วยคำว่า 'ครับ', 'ครับท่าน' หรือ 'ครับเจ้านาย' อย่างเป็นธรรมชาติ"
)

class JarvisStreamingTTS:
    """
    โมดูลจัดการ Text-to-Speech โดยใช้ Microsoft Edge TTS (Cloud)
    เสียงภาษาไทยเนียนระดับมนุษย์ พร้อมระบบ Queue เล่นเสียงต่อกันแบบไร้รอยต่อ
    """

    def __init__(self, voice_name: str = "th-TH-NiwatNeural"):
        """
        :param voice_name: รหัสเสียง (th-TH-NiwatNeural เสียงผู้ชายสุภาพ, th-TH-PremwadeeNeural เสียงผู้หญิง)
        """
        self.voice_name = voice_name
        self.is_playing = False
        self._playback_thread: Optional[threading.Thread] = None
        
        self._audio_queue = queue.Queue()
        
        if pygame:
            pygame.mixer.init()
            
        self._verify_dependencies()

    @staticmethod
    def _get_mood_rate() -> str:
        """
        ดึง mood ปัจจุบันจาก jarvis_mood แล้วแปลงเป็น edge-tts rate string
        stressed  → +15% (พูดเร็ว กระชับ ไม่เยิ่นเย้อ)
        relaxed   → -8%  (พูดช้าลงนิด นุ่มนวล)
        focused   → +5%  (ปกติแต่ชัดเจน)
        neutral   → +0%  (ไม่เปลี่ยน)
        """
        try:
            from jarvis_mood import get_current_mood
            mood = get_current_mood()
            rate_map = {
                "stressed": "+15%",
                "relaxed":  "-8%",
                "focused":  "+5%",
                "neutral":  "+0%",
            }
            return rate_map.get(mood, "+0%")
        except Exception:
            return "+0%"

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
                    pygame.time.Clock().tick(10)
                
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
        แปลงเป็นเสียงทีละประโยค แล้วส่งเข้าคิวเล่นเสียงทันที
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
                
            async for chunk in text_generator:
                if not self.is_playing:
                    break
                    
                chunk = chunk.strip()
                if not chunk:
                    continue
                
                import re
                
                # --- Custom Phonetic Dictionary for Edge-TTS ---
                chunk = re.sub(r'(?i)arc reactor', 'อาร์ค รีแอคเตอร์', chunk)
                chunk = re.sub(r'(?i)jarvis', 'จาร์วิส', chunk)
                chunk = re.sub(r'(?i)j\.a\.r\.v\.i\.s\.?', 'จาร์วิส', chunk)
                
                chunk = chunk.replace('\n', ' , ').replace('...', ' , ')
                
                chunk = re.sub(r'([ก-๙]+)\s+([ก-๙]+)', r'\1, \2', chunk)
                
                chunk = re.sub(r'([,])\s*[,]+', r'\1', chunk)
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp_path = temp_file.name
                temp_file.close()
                
                rate = self._get_mood_rate()
                communicate = edge_tts.Communicate(chunk, self.voice_name, rate=rate)
                await communicate.save(temp_path)
                
                if self.is_playing:
                    self._audio_queue.put(temp_path)
                else:
                    
                    os.remove(temp_path)
                    
        except Exception as e:
            logging.error(f"[JARVIS TTS] ข้อผิดพลาดการแปลงเสียงจาก Edge TTS: {e}")
        finally:
            
            pass

    def stop(self) -> None:
        """หยุดการทำงานทั้งหมดทันที (Barge-in / Interrupt)"""
        self.is_playing = False
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        
        self._audio_queue.put("STOP")
        
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)

    def speak(self, text: str) -> None:
        """
        ฟังก์ชันเรียกใช้แบบ Synchronous สำหรับให้โมดูลเบื้องหลัง (เช่น Network, Awareness) เรียกใช้ได้ง่ายๆ
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
            "สวัสดีครับเจ้านาย ",
            "วันนี้อากาศแจ่มใสมากเลยครับ ",
            "มีอะไรให้ผมรับใช้อีกไหมครับท่าน"
        ]
        for s in sentences:
            yield s
            await asyncio.sleep(1.0) 

    tts_engine = JarvisStreamingTTS(voice_name="th-TH-NiwatNeural")
    
    print("✅ JarvisStreamingTTS (Edge TTS) Initialized Successfully.")
    print("🤖 SYSTEM PROMPT:", JARVIS_SYSTEM_PROMPT)
