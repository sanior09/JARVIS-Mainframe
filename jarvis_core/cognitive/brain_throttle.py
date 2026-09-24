"""
jarvis_core/cognitive/brain_throttle.py
─────────────────────────────────────────────────────
Adaptive Brain Throttle for J.A.R.V.I.S.
Manages Complexity Classification and Hardware limits (RAM/CPU).
"""

import psutil
import logging
from typing import Dict, Any

logger = logging.getLogger("JARVIS.BrainThrottle")

class ComplexityClassifier:
    @staticmethod
    def classify(query: str) -> int:
        """
        Classify the complexity of the query into Tiers.
        Tier 1: Fast/Reflex (Simple commands, greetings)
        Tier 2: Standard (Conversational, basic questions)
        Tier 3: Complex (Architecture, Deep Engineering, ToT needed)
        """
        tier_1_keywords = ["สวัสดี", "hello", "hi", "เปิดไฟ", "ปิดไฟ", "เปิดระบบ", "ปิดระบบ", "เวลา", "time", "ขอบคุณ", "สบายดีไหม"]
        tier_3_keywords = [
            "architecture", "สถาปัตยกรรม", "refactor", "optimize", "design system",
            "โครงสร้างระบบ", "วิศวกรรมระบบ", "ออกแบบระบบ", "เขียนโปรแกรมใหม่", "deep engineering"
        ]
        
        query_lower = query.lower().strip()
        
        # Fast-track simple queries or status checks (do NOT trigger heavy Tier 3 council)
        status_inquiries = ["เป็นไง", "เป็นอะไร", "สถานะ", "status", "สลับโมเดล", "เช็คระบบ", "ตรวจระบบ", "ทำอะไรอยู่", "ช่วยอะไรได้บ้าง"]
        if any(kw in query_lower for kw in status_inquiries) and len(query_lower) < 80:
            return 1

        if any(kw in query_lower for kw in tier_1_keywords) and len(query_lower) < 60:
            return 1
            
        if any(kw in query_lower for kw in tier_3_keywords) or len(query_lower) > 350:
            return 3
            
        return 2

class HardwareGovernor:
    def __init__(self, ram_limit_mb: int = 6000): # 6GB limit out of 8GB for Lenovo S340
        self.ram_limit_mb = ram_limit_mb

    def check_system_health(self) -> Dict[str, Any]:
        """
        Check CPU and RAM usage.
        """
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            
            used_mb = mem.used / (1024 * 1024)
            total_mb = mem.total / (1024 * 1024)
            
            is_critical = used_mb > self.ram_limit_mb or cpu > 95.0
            
            health = {
                "cpu_percent": cpu,
                "ram_used_mb": used_mb,
                "ram_total_mb": total_mb,
                "ram_percent": mem.percent,
                "is_critical": is_critical
            }
            return health
        except Exception as e:
            logger.error(f"[BrainThrottle] Hardware Check Failed: {e}")
            return {"is_critical": False, "error": str(e)}

    def should_offload_to_cloud(self) -> bool:
        """
        Determine if the local system is too stressed and should bypass local SLM.
        """
        health = self.check_system_health()
        if health.get("is_critical", False):
            logger.warning(f"⚡ [BrainThrottle] SYSTEM STRESSED (RAM: {health.get('ram_percent')}%, CPU: {health.get('cpu_percent')}%). Offloading to Cloud.")
            return True
        return False
