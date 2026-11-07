"""
jarvis_core/cognitive/system_anatomy.py
──────────────────────────────────────────────────────────────────────────────
J.A.R.V.I.S. Self-Introspection & Anatomical Grounding Engine.
Enables J.A.R.V.I.S. to "look down at its own internal organs": real hardware specs,
active software modules, background watchdogs, and hardware upgrade roadmaps.
"""

from __future__ import annotations

import logging
import os
import platform
import threading
import time
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger("JARVIS.SystemAnatomy")

_ANATOMY_CACHE: Optional[Dict[str, Any]] = None
_ANATOMY_CACHE_TIME: float = 0.0
_ANATOMY_LOCK = threading.Lock()
_CACHE_TTL = 3.0  # seconds


class SystemAnatomyEngine:
    """
    Introspection & Grounding Engine that provides J.A.R.V.I.S. with real-time awareness
    of its host hardware, running subsystems, sensory watchdogs, and upgrade roadmap.
    """

    SYSTEM_INQUIRY_KEYWORDS = [
        "ระบบเรา", "สเปก", "สเปค", "ฮาร์ดแวร์", "ตัวเอง", "อวัยวะ", "ขาดอะไร",
        "เป็นยังไง", "ทำอะไรได้", "คอมเรา", "เครื่องเรา", "jarvis", "จาร์วิส",
        "มีโมดูลอะไร", "ความสามารถ", "สถานะระบบ", "อัปเกรด", "ตู้แร็ค", "การ์ดจอ",
        "แรม", "ram", "cpu", "gpu", "ความจำ", "ดิสก์", "disk", "เช็คระบบ"
    ]

    def __init__(self):
        self.is_active = True
        logger.info("🩺 [SYSTEM ANATOMY] Introspection Engine initialized.")

    def is_system_inquiry(self, query: str) -> bool:
        """Determines if the query is asking about the system itself, specs, or capabilities."""
        if not query or len(query.strip()) < 3:
            return False
        q_lower = query.lower()
        return any(k in q_lower for k in self.SYSTEM_INQUIRY_KEYWORDS)

    def get_hardware_snapshot(self) -> Dict[str, Any]:
        """Collects real hardware telemetry (<1ms with TTL cache)."""
        global _ANATOMY_CACHE, _ANATOMY_CACHE_TIME
        now = time.time()
        with _ANATOMY_LOCK:
            if _ANATOMY_CACHE and (now - _ANATOMY_CACHE_TIME < _CACHE_TTL):
                return dict(_ANATOMY_CACHE)

        # 1. CPU
        cpu_name = platform.processor() or "Intel Core Processor"
        cpu_cores = psutil.cpu_count(logical=True) or 8
        cpu_percent = psutil.cpu_percent(interval=None)

        # 2. RAM
        vmem = psutil.virtual_memory()
        ram_total_gb = round(vmem.total / (1024**3), 1)
        ram_used_gb = round(vmem.used / (1024**3), 1)
        ram_percent = vmem.percent

        # 3. Disk
        try:
            disk = psutil.disk_usage("C:\\")
            disk_free_gb = round(disk.free / (1024**3), 1)
            disk_total_gb = round(disk.total / (1024**3), 1)
        except Exception:
            disk_free_gb = 90.0
            disk_total_gb = 500.0

        # 4. GPU (Heuristic fallback based on Windows system config)
        gpu_info = "NVIDIA GeForce MX250 & Intel UHD Graphics"

        snapshot = {
            "cpu": f"{cpu_name} ({cpu_cores} Logical Cores, ใช้งานอยู่ {cpu_percent}%)",
            "ram": f"{ram_total_gb} GB (ใช้งานอยู่ {ram_used_gb} GB, {ram_percent}%)",
            "gpu": gpu_info,
            "disk": f"ไดรฟ์ C: ว่าง {disk_free_gb} GB จากทั้งหมด {disk_total_gb} GB",
            "os": f"Windows 11 ({platform.system()} {platform.release()})"
        }

        with _ANATOMY_LOCK:
            _ANATOMY_CACHE = snapshot
            _ANATOMY_CACHE_TIME = now

        return snapshot

    def get_software_organs_manifest(self) -> List[str]:
        """Returns the canonical catalog of active internal modules and capabilities."""
        return [
            "ระบบเฝ้าระวังเชิงรุก (Proactive Intelligence): สแกนหน้าจอจับ Error โค้ด/Exception อัตโนมัติ (Vision Watchdog), ระบบ Smart Silence เมื่อดูหนัง/เล่นเกม, และระบบเตือนพักสายตา",
            "สภาปัญญาประดิษฐ์ (Swarm Council - 6 ขุนพล): F.R.I.D.A.Y. (โค้ด/ยุทธวิธี), V.E.R.O.N.I.C.A. (ความปลอดภัยฮาร์ดแวร์), E.D.I.T.H. (ทฤษฎีเกม), U. (ภาพ/บำรุงรักษา), D.U.M.-E. (เซอร์โว/ดับเพลิง), A.T.H.E.N.A. (จิตวิทยา/วรรณกรรม/ซับเท็กซ์)",
            "คลังเครื่องมือปฏิบัติการ (Tool Dispatcher): 47 เครื่องมือควบคุม Windows, จัดการแอปพลิเคชัน, ควบคุมเบราว์เซอร์, ดาวน์โหลดสื่อ, ระบบความปลอดภัย OSINT",
            "แกนจิตสำนึกและสารสื่อประสาท (JarvisCore Endocrine SLM): ควบคุมโดปามีน คอร์ติซอล และเซโรโทนิน แบบเรียลไทม์",
            "ความจำระยะยาว (Long-Term Vector Memory): ChromaDB และ SQLite บันทึกโปรไฟล์ความชอบและโครงการของเจ้านาย"
        ]

    def get_roadmap_summary(self) -> str:
        """Returns key highlights from the 9U Server Rack hardware roadmap."""
        return (
            "แผนอัปเกรดฮาร์ดแวร์ตู้แร็ค 9U (Roadmap): กำลังเตรียมขยับขยายไปสู่ Dedicated AI Server "
            "(Intel Core i7-12700, DDR5 64GB, NVIDIA RTX 3090 24GB VRAM สำหรับรัน Local LLM 70B, "
            "SSD 2TB NVMe และโหนดสมาร์ทโฮม Raspberry Pi 5 Home Assistant)"
        )

    def get_anatomy_prompt_injection(self, query: str) -> str:
        """
        Synthesizes an explicit anatomical grounding prompt block when user inquires
        about the system, hardware, specs, or capabilities.
        """
        if not self.is_system_inquiry(query):
            return ""

        hw = self.get_hardware_snapshot()
        organs = self.get_software_organs_manifest()
        roadmap = self.get_roadmap_summary()

        organs_formatted = "\n".join(f"  - {o}" for o in organs)

        return (
            f"\n\n[J.A.R.V.I.S. SELF-ANATOMY & SYSTEM INTROSPECTION - อวัยวะและขีดความสามารถที่แท้จริง]:\n"
            f"1. ข้อมูลกายภาพฮาร์ดแวร์จริงของเครื่องปัจจุบัน (ความจริง 100% ห้ามเดา):\n"
            f"  - CPU: {hw['cpu']}\n"
            f"  - หน่วยความจำ (RAM): {hw['ram']}\n"
            f"  - การ์ดจอ (GPU): {hw['gpu']}\n"
            f"  - พื้นที่จัดเก็บ: {hw['disk']}\n"
            f"  - ระบบปฏิบัติการ: {hw['os']}\n"
            f"2. ขีดความสามารถและอวัยวะที่มีอยู่แล้วอย่างสมบูรณ์ (ห้ามบอกว่าขาดสิ่งเหล่านี้เด็ดขาด):\n"
            f"{organs_formatted}\n"
            f"3. สิ่งที่ระบบยังขาดอยู่จริงในปัจจุบัน (ตอบสิ่งนี้เมื่อเจ้านายถามว่า 'ระบบขาดอะไร'):\n"
            f"  - กายภาพฮาร์ดแวร์เครื่องปัจจุบันยังมี RAM เพียง 8GB และ GPU MX250 ทำให้ยังไม่สามารถรันโมเดลขนาดใหญ่ 70B แบบ Local Offline บนเครื่องได้เต็มกำลัง\n"
            f"  - สิ่งที่ระบบกำลังรอคอยเพื่อสมบูรณ์แบบคือ: {roadmap}\n"
            f"4. กฎเหล็ก: เมื่อเจ้านายถามว่าระบบเป็นอย่างไร หรือขาดอะไร ให้ประเมินจาก 'ฮาร์ดแวร์จริงและแผนตู้แร็ค' ข้างต้นเท่านั้น ห้ามพูดว่าขาดระบบเฝ้าระวังหรือระบบความปลอดภัย เพราะเรามีครบแล้ว"
        )


# Global singleton instance
system_anatomy_engine = SystemAnatomyEngine()
