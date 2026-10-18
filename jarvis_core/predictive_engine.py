import os
import time
import threading
import logging

logger = logging.getLogger("JarvisPredictive")

class PredictiveActionEngine:
    """
    4. Predictive Action Engine (Proactive tasks)
    Monitors specific directories (like Downloads) and anticipates user needs.
    """
    def __init__(self):
        self.running = False
        self.watch_thread = None
        self.downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.known_files = set()
        
    def start(self):
        if not self.running:
            self.running = True
            if os.path.exists(self.downloads_dir):
                self.known_files = set(os.listdir(self.downloads_dir))
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()
            logger.info("[PREDICTIVE] Predictive Action Engine started in background.")

    def stop(self):
        self.running = False

    def _watch_loop(self):
        while self.running:
            try:
                if os.path.exists(self.downloads_dir):
                    current_files = set(os.listdir(self.downloads_dir))
                    new_files = current_files - self.known_files
                    
                    for f in new_files:
                        if f.endswith(".zip"):
                            # Proactive Action!
                            logger.info(f"💡 [PREDICTIVE ACTION] New ZIP detected: {f}. I can extract this automatically.")
                            # Example of proactive system alert injection:
                            self._trigger_system_alert(f"ผมเห็นเจ้านายเพิ่งโหลดไฟล์ '{f}' มา ให้ผมแตกไฟล์และตรวจสอบไวรัสให้เลยไหมครับ?")
                            
                    self.known_files = current_files
            except Exception as e:
                logger.error(f"[PREDICTIVE] Watch loop error: {e}")
            time.sleep(10) # Check every 10 seconds

    def _trigger_system_alert(self, msg: str):
        # We can append this to the global SYSTEM_ALERTS in jarvis.py
        # Or just log it. For now we use the logger so it shows up in the terminal.
        print(f"\n🔔 [J.A.R.V.I.S. PROACTIVE]: {msg}\n")

predictive_engine = PredictiveActionEngine()
