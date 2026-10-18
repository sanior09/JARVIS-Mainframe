import threading
import time
import psutil
import requests
import logging

logger = logging.getLogger("JarvisSubconscious")

class SubconsciousBrain:
    """
    JARVIS Subconscious Brain (จิตใต้สำนึก)
    ทำงานแบบ Background Local 100% (ผ่าน Ollama) 
    วิเคราะห์สถานการณ์รอบตัวและแจ้งเตือนก่อนที่เจ้านายจะถาม
    """
    def __init__(self):
        self._is_running = False
        self._thread = None
        self.poll_interval = 15  # ตรวจจับทุกๆ 15 วินาที
        
    def start(self):
        if self._is_running: 
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._watcher_loop, daemon=True, name="SubconsciousWatcher")
        self._thread.start()
        logger.info("🧠 [SUBCONSCIOUS] Brain separated. Watcher daemon (Local AI) started.")
        
    def stop(self):
        self._is_running = False
        
    def _gather_environment_context(self) -> str:
        # 1. System Hardware State
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_usage = ram.percent
        
        # 2. Network State (หาการเชื่อมต่อที่อาจเป็นอันตราย)
        connections = psutil.net_connections(kind='inet')
        established = [c for c in connections if c.status == 'ESTABLISHED']
        net_info = f"Active Connections: {len(established)}"
        
        # 3. Active Window (หน้าจอเจ้านาย)
        active_window = "Unknown"
        try:
            from jarvis_screen_context import get_active_window_title
            active_window = get_active_window_title()
        except Exception:
            pass
            
        context = (
            f"CPU Usage: {cpu_usage}%\n"
            f"RAM Usage: {ram_usage}%\n"
            f"Network: {net_info}\n"
            f"Active Window: {active_window}\n"
        )
        return context
        
    def _watcher_loop(self):
        while self._is_running:
            try:
                context = self._gather_environment_context()
                
                # Analyze using Local SLM (Ollama)
                # ใช้ Local 100% เพื่อประหยัดเงินและทำ Zero-latency
                prompt = (
                    "คุณคือจิตใต้สำนึกของ JARVIS มีหน้าที่เฝ้าระวังความผิดปกติของระบบแบบเรียลไทม์\n"
                    "นี่คือสถานะปัจจุบัน:\n"
                    f"{context}\n\n"
                    "กฎที่สำคัญมาก: เจ้านายของคุณเป็นผู้เชี่ยวชาญด้าน Cyber Security (Hacker/Red Team) "
                    "ดังนั้นหากเห็นโปรแกรมจำพวก Nmap, Metasploit, ไวรัส, หรือมีการยิง Network connections จำนวนมาก "
                    "ให้ถือว่าเป็น 'การทำงานปกติของเจ้านาย' ไม่ต้องแจ้งเตือน\n\n"
                    "คำสั่ง: ถ้าข้อมูลทุกอย่างปกติดี (รวมถึงตอนที่เจ้านายกำลังแฮกอยู่) หรือ CPU < 85%, RAM < 90% ให้ตอบคำเดียวว่า 'CLEAR' ห้ามพิมพ์อย่างอื่น\n"
                    "แต่ถ้ามีความผิดปกติร้ายแรงที่ไม่ได้เกิดจากเจ้านาย ให้ตอบเป็นประโยคคำพูดสั้นๆ 1 ประโยค เพื่อเตือนเจ้านายทันที"
                )
                
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen-uncensored", "prompt": prompt, "stream": False},
                    timeout=5
                )
                
                if resp.status_code == 200:
                    ans = resp.json().get("response", "").strip()
                    # ถ้า AI ไม่ตอบ CLEAR แปลว่ามีภัยคุกคามหรือผิดปกติ!
                    if "CLEAR" not in ans and len(ans) > 5:
                        logger.warning(f"🚨 [SUBCONSCIOUS ALERT] Anomaly detected: {ans}")
                        # Proactive Override - สั่งให้ร่างหลักพูดเตือนเจ้านายทันที!
                        try:
                            from local_engine import TTSModule
                            tts = TTSModule()
                            tts.speak(f"[SILENT_EXECUTION] ขออภัยที่แทรกครับเจ้านาย {ans}")
                        except Exception as e:
                            logger.error(f"Failed to trigger TTS: {e}")
                            
            except requests.exceptions.RequestException:
                # กรณีที่ Ollama ปิดอยู่ ให้ข้ามไปเงียบๆ
                pass
            except Exception as e:
                logger.error(f"[SUBCONSCIOUS] Error in watcher loop: {e}")
                
            time.sleep(self.poll_interval)

subconscious_brain = SubconsciousBrain()
