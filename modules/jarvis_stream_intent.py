import logging
import asyncio
import json

logger = logging.getLogger("JarvisStreamIntent")

class StreamIntentAnalyzer:
    """
    วิเคราะห์ Partial Transcript ระหว่างที่ผู้ใช้กำลังพูดอยู่
    เพื่อทำ Speculative Execution (รันคำสั่งล่วงหน้าแบบ Zero-Latency)
    """
    def __init__(self):
        self.handled_signatures = set()

    def _get_signature(self, text: str) -> str:
        # Normalize text เพื่อตัดคำซ้ำซ้อน
        import re
        return re.sub(r'[\s\W_]+', '', text.lower())

    def was_handled_early(self, final_text: str) -> bool:
        """เช็คว่าประโยคนี้ถูกเดาและรันล่วงหน้าไปแล้วหรือยัง (ป้องกันรันซ้ำ)"""
        sig = self._get_signature(final_text)
        for handled in self.handled_signatures:
            if handled in sig or sig in handled:
                return True
        return False

    async def analyze_stream(self, partial_text: str):
        """วิเคราะห์ Partial Transcript (คำต่อคำ)"""
        text = partial_text.lower()
        if len(text) < 4:
            return

        from jarvis_core.ai_router import _try_reflex_hardcoded
        
        reflex_action = _try_reflex_hardcoded(text)
        if reflex_action and reflex_action.get("tool_calls"):
            tool_call = reflex_action["tool_calls"][0]
            
            sig = self._get_signature(text)
            if sig not in self.handled_signatures:
                self.handled_signatures.add(sig)
                logger.info(f"⚡ [SPECULATIVE EXECUTION] เดาใจเจ้านายออกแล้ว! แอบสั่งรันล่วงหน้าทันที: {tool_call['function']['name']}")
                
                # Execute in background thread instantly
                import threading
                def _run_speculative():
                    try:
                        from jarvis_core.tool_dispatcher import tool_dispatcher
                        args = json.loads(tool_call['function']['arguments'])
                        tool_dispatcher.execute(tool_call['function']['name'], **args)
                    except Exception as e:
                        logger.error(f"Speculative execution failed: {e}")
                
                threading.Thread(target=_run_speculative, daemon=True).start()
                
                # Zero-Latency TTS Feedback
                try:
                    from modules.local_engine import TTSModule
                    tts = TTSModule()
                    tts.speak(reflex_action["content"])
                except Exception as e:
                    logger.debug(f"Could not speak speculative response: {e}")

sys_stream_intent = StreamIntentAnalyzer()
