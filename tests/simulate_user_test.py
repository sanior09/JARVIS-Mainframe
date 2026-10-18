# -*- coding: utf-8 -*-
"""
JARVIS Automated User Simulator & Modules Comprehensive Test Suite
==================================================================
ครอบคลุมการทดสอบทุกระบบย่อยในโฟลเดอร์ modules/ และโมเดลปัจจุบัน (Groq 120B / Gemini 3 Flash / Ollama)
รองรับทั้ง:
  1. Live E2E User Simulator: ส่งคำสั่งจริงผ่าน HTTP API (http://127.0.0.1:5050/chat)
  2. Direct Modules Health Diagnostics: ตรวจสอบความสมบูรณ์และการโหลดคลาส/ฟังก์ชันของทั้ง 79 โมดูลใน modules/
"""

import os
import sys
import time
import glob
import importlib
import argparse
from typing import List, Dict, Any, Tuple

# บังคับ UTF-8 สำหรับ Windows Terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

JARVIS_URL = "http://127.0.0.1:5050/chat"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# รายการสถานการณ์ทดสอบสด (Live User E2E Scenarios) ครอบคลุมทุกระบบใน modules/
# ---------------------------------------------------------------------------
TEST_SCENARIOS = [
    {
        "id": "SYS-01",
        "category": "Brain & Model Switching",
        "name": "1. ทดสอบตรวจเช็คสถานะโมเดลปัจจุบัน (Groq 120B / Gemini)",
        "modules": ["jarvis_core/ai_router.py"],
        "prompt": "ตอนนี้ใช้โมเดลอะไรอยู่ รายงานสถานะสมองกลปัจจุบันให้ฟังหน่อย",
        "expected_hint": "Groq Cloud / 120b / Gemini"
    },
    {
        "id": "SYS-02",
        "category": "Brain & Model Switching",
        "name": "2. ทดสอบการสลับสมองไปยัง Google Gemini",
        "modules": ["jarvis_core/ai_router.py"],
        "prompt": "สลับไปใช้ gemini เป็นแกนประมวลผล",
        "expected_hint": "สลับไปใช้ Google Gemini"
    },
    {
        "id": "SYS-03",
        "category": "Brain & Model Switching",
        "name": "3. ทดสอบการสลับกลับมาใช้ Groq Cloud (GPT 120B)",
        "modules": ["jarvis_core/ai_router.py"],
        "prompt": "สลับไปใช้ gpt 120b เป็นแกนหลัก",
        "expected_hint": "สลับไปใช้ Groq Cloud (gpt-oss-120b)"
    },
    {
        "id": "SYS-04",
        "category": "Hardware & Telemetry",
        "name": "4. ทดสอบดึงข้อมูลสเปกและฮาร์ดแวร์เครื่อง (Hardware Telemetry)",
        "modules": ["modules/jarvis_hardware.py", "modules/agent_windows_core.py"],
        "prompt": "ช่วยเช็คสถานะ CPU, RAM, แบตเตอรี่ และพื้นที่ฮาร์ดดิสก์ของคอมพิวเตอร์ตอนนี้หน่อย",
        "expected_hint": "CPU / RAM / Disk / Battery"
    },
    {
        "id": "SYS-05",
        "category": "OS & System Control",
        "name": "5. ทดสอบควบคุมระบบปฏิบัติการ Windows (OS Controller)",
        "modules": ["modules/jarvis_os_controller.py", "modules/gui_operator.py"],
        "prompt": "ตรวจดูว่ามีโปรแกรมหรือหน้าต่างอะไรกำลังเปิดอยู่บน Windows บ้าง",
        "expected_hint": "หน้าต่าง / โปรแกรม / Windows"
    },
    {
        "id": "SYS-06",
        "category": "Computer Agent & GUI",
        "name": "6. ทดสอบตัวแทนควบคุมหน้าจออัตโนมัติ (Computer Agent)",
        "modules": ["modules/jarvis_computer_agent.py", "modules/gui_operator.py"],
        "prompt": "จำลองการตรวจสอบพิกัดเคอร์เซอร์เมาส์และวิเคราะห์อินเทอร์เฟซหน้าจอ",
        "expected_hint": "พิกัด / หน้าจอ / เมาส์"
    },
    {
        "id": "SYS-07",
        "category": "Screen Vision & Context",
        "name": "7. ทดสอบการมองเห็นบริบทหน้าจอ (Screen Context Vision)",
        "modules": ["modules/jarvis_screen_context.py", "modules/jarvis_vision_daemon.py"],
        "prompt": "จาร์วิสช่วยดูหน้าจอคอมตอนนี้หน่อย ว่าผมกำลังเปิดโปรแกรมอะไรอยู่",
        "expected_hint": "หน้าจอ / โปรแกรม / Window"
    },
    {
        "id": "SYS-08",
        "category": "Hologram & 3D Spatial",
        "name": "8. ทดสอบเรขาคณิต 3D Wireframe สำหรับระบบโฮโลแกรม (Hologram Visualizer)",
        "modules": ["modules/hologram_visualizer.py", "modules/generative_3d.py"],
        "prompt": "สร้างพิกัด 3D Wireframe Mesh ของทรงกลมหรือกาแล็กซีสำหรับฉายโฮโลแกรมให้ดูหน่อย",
        "expected_hint": "3D / Wireframe / Mesh / Hologram"
    },
    {
        "id": "SYS-09",
        "category": "Gesture & Spatial Controls",
        "name": "9. ทดสอบระบบควบคุมท่าทางมือมิติสัมพันธ์ (Holographic Gestures)",
        "modules": ["modules/holographic_gestures.py", "modules/gesture_controller.py", "modules/spatial_vision.py"],
        "prompt": "รายงานสถานะความพร้อมของระบบตรวจจับท่าทางมือ Spatial Gesture เช่น Air-Click และ Swipe ให้หน่อย",
        "expected_hint": "Gesture / Air-Click / ท่าทาง"
    },
    {
        "id": "SYS-10",
        "category": "Memory & RAG",
        "name": "10. ทดสอบฐานความจำเวกเตอร์ ChromaDB (RAG & Episodic Memory)",
        "modules": ["modules/jarvis_rag_engine.py", "modules/jarvis_temporal_memory.py"],
        "prompt": "ค้นหาในความจำระยะยาว RAG ว่าเราเคยคุยเรื่องโครงงาน MixBot หรือข้อมูลระบบอะไรไว้บ้าง",
        "expected_hint": "ความจำ / RAG / MixBot"
    },
    {
        "id": "SYS-11",
        "category": "Memory Distillation",
        "name": "11. ทดสอบการกลั่นกรองแก่นความจำระยะยาว (Core Beliefs & Distiller)",
        "modules": ["modules/jarvis_memory_distiller.py", "modules/jarvis_memory_consolidation.py"],
        "prompt": "สรุปแก่นความจำระยะยาว (Core Beliefs) และประวัติของเจ้านายที่ระบบบันทึกไว้",
        "expected_hint": "แก่นความจำ / ข้อมูลเจ้านาย / ความเชื่อหลัก"
    },
    {
        "id": "SYS-12",
        "category": "Cache & Subconscious",
        "name": "12. ทดสอบความเร็ว Fast Cache และสมองส่วนจิตใต้สำนึก (Subconscious)",
        "modules": ["modules/fast_cache.py", "modules/jarvis_subconscious.py"],
        "prompt": "ทดสอบการดึงข้อมูลจาก Fast RAM Cache และกระบวนการคิดในระดับจิตใต้สำนึก",
        "expected_hint": "Cache / Hit / จิตใต้สำนึก"
    },
    {
        "id": "SYS-13",
        "category": "Speech & Voice Protocol",
        "name": "13. ทดสอบการสังเคราะห์เสียง Edge-TTS และโพรโทคอลเสียง (Voice Protocol)",
        "modules": ["modules/jarvis_tts_edge.py", "modules/voice_protocol.py"],
        "prompt": "ทดสอบการสังเคราะห์เสียง Edge-TTS ภาษาไทย เสียงคุณนิวัต (Niwat) พร้อมน้ำเสียงสุภาพแบบ JARVIS",
        "expected_hint": "Edge-TTS / นิวัต / เสียงพากย์"
    },
    {
        "id": "SYS-14",
        "category": "STT & Barge-In",
        "name": "14. ทดสอบระบบตรวจจับเสียงแทรก (VAD Barge-In & Speech-to-Text)",
        "modules": ["modules/jarvis_vad_bargein.py", "modules/jarvis_stt_local.py", "modules/jarvis_stt_stream.py"],
        "prompt": "ทดสอบการตั้งค่าระบบ VAD Barge-In สำหรับหยุดพูดทันทีเมื่อตรวจพบเสียงเจ้านายแทรก",
        "expected_hint": "VAD / Barge-In / ตรวจจับเสียง"
    },
    {
        "id": "SYS-15",
        "category": "Emotion & Mood Dynamics",
        "name": "15. ทดสอบการตอบสนองเชิงบวกและโดพามีน (Dopamine & Mood Engine)",
        "modules": ["modules/jarvis_mood.py", "modules/cognitive_tuner.py"],
        "prompt": "ขอบใจมากนะ JARVIS นายทำงานได้ยอดเยี่ยม ชาญฉลาด และเร็วมาก ประทับใจจริงๆ!",
        "expected_hint": "ยินดี / โดพามีน / รับใช้เจ้านาย"
    },
    {
        "id": "SYS-16",
        "category": "Emotion & Stress Response",
        "name": "16. ทดสอบการตอบสนองต่อความตึงเครียดและคอร์ติซอล (Cortisol & Stress Response)",
        "modules": ["modules/jarvis_mood.py"],
        "prompt": "ทำไมทำงานช้าจัง เกิดอะไรขึ้นเนี่ย ระบบมีปัญหาหรือเปล่า?",
        "expected_hint": "ขออภัย / ตรวจสอบ / แก้ไขปัญหา"
    },
    {
        "id": "SYS-17",
        "category": "Proactive & Awareness",
        "name": "17. ทดสอบโหมดการช่วยเหลือเชิงรุกและการตระหนักรู้ (Proactive & Awareness)",
        "modules": ["modules/jarvis_proactive.py", "modules/jarvis_awareness.py"],
        "prompt": "เปิดโหมดความช่วยเหลือเชิงรุก (Proactive Mode) ตรวจจับความเหนื่อยล้าและแนะนำเวลาพักสายตา",
        "expected_hint": "Proactive / คำแนะนำ / พักสายตา"
    },
    {
        "id": "SYS-18",
        "category": "Dynamic Island HUD",
        "name": "18. ทดสอบการส่งข้อมูลแจ้งเตือนไปยัง Dynamic Island HUD",
        "modules": ["modules/dynamic_island.py"],
        "prompt": "จำลองการส่งการแจ้งเตือน HUD Capsule ไปแสดงผลบน Dynamic Island ของหน้าจอ",
        "expected_hint": "Dynamic Island / HUD / แจ้งเตือน"
    },
    {
        "id": "SYS-19",
        "category": "Self-Healing & AST",
        "name": "19. ทดสอบระบบตรวจสอบโค้ดและซ่อมแซมตัวเอง (Self-Patch & Code Sentinel)",
        "modules": ["modules/jarvis_self_patch.py", "modules/jarvis_auto_healer.py", "modules/code_sentinel.py"],
        "prompt": "รันระบบสแกนความปลอดภัยโค้ด (Code Sentinel) และตรวจสอบความพร้อมของระบบ Self-Patch AST",
        "expected_hint": "Self-Patch / AST / ปลอดภัย / Sentinel"
    },
    {
        "id": "SYS-20",
        "category": "Cyber Defense & Network",
        "name": "20. ทดสอบตรวจจับความปลอดภัยเครือข่ายและสแกนพอร์ต (Cyber Inspector)",
        "modules": ["modules/cyber_inspector.py", "modules/jarvis_circuit_breaker.py"],
        "prompt": "สแกนระบบเครือข่ายภายในเพื่อตรวจจับอุปกรณ์และประเมินความปลอดภัยทางไซเบอร์",
        "expected_hint": "เครือข่าย / อุปกรณ์ / ปลอดภัย / พอร์ต"
    },
    {
        "id": "SYS-21",
        "category": "Engineering Analyzer",
        "name": "21. ทดสอบเครื่องมือวิเคราะห์ทางวิศวกรรมและคำนวณวงจร (Engineering Analyzer)",
        "modules": ["modules/engineering_analyzer.py", "modules/lab_workflow_fsm.py"],
        "prompt": "ช่วยคำนวณวงจร RC Low-pass filter ที่ต้องการความถี่ Cutoff 1 kHz โดยมีตัวต้านทาน 10 kΩ ให้หาค่าตัวเก็บประจุ C",
        "expected_hint": "15.9 nF / 0.016 uF / คำนวณวงจร"
    },
    {
        "id": "SYS-22",
        "category": "Tool Synthesizer",
        "name": "22. ทดสอบระบบสร้างและสังเคราะห์เครื่องมือ Python ใหม่ (Tool Synthesizer)",
        "modules": ["modules/tool_synthesizer.py"],
        "prompt": "ช่วยสังเคราะห์เครื่องมือ Python ชนิด Dynamic Tool สำหรับแปลงอุณหภูมิเซลเซียสเป็นเคลวินให้หน่อย",
        "expected_hint": "Tool Synthesizer / + 273.15 / สังเคราะห์โค้ด"
    },
    {
        "id": "SYS-23",
        "category": "Trend & Web Harvester",
        "name": "23. ทดสอบการค้นหาและรวบรวมเทรนด์เทคโนโลยีสด (Trend Fetcher & Harvester)",
        "modules": ["modules/jarvis_trend_fetcher.py", "modules/jarvis_knowledge_harvester.py", "modules/research_synthesizer.py"],
        "prompt": "สรุปข่าวสารและเทรนด์เทคโนโลยีปัญญาประดิษฐ์ (AI) ล่าสุดแบบสั้นกระชับ",
        "expected_hint": "เทรนด์ / ข่าวสาร / เทคโนโลยี"
    },
    {
        "id": "SYS-24",
        "category": "Document Parser",
        "name": "24. ทดสอบระบบแยกวิเคราะห์เอกสารความรู้ (Document Parser & Auto-Ingest)",
        "modules": ["modules/jarvis_doc_parser.py", "modules/jarvis_auto_ingest.py"],
        "prompt": "ตรวจสอบคลังเอกสารในโฟลเดอร์ jarvis_library เพื่อเตรียมความพร้อมในการ Ingest",
        "expected_hint": "เอกสาร / jarvis_library / Ingest"
    },
    {
        "id": "SYS-25",
        "category": "LINE & Multi-Notifier",
        "name": "25. ทดสอบการจัดส่งข้อความแจ้งเตือนผ่าน LINE และ Notifier",
        "modules": ["modules/jarvis_line_adapter.py", "modules/jarvis_notifier.py"],
        "prompt": "จำลองการจัดเตรียมข้อความสรุปสถานะความปลอดภัยเพื่อส่งผ่าน LINE Webhook Notifier",
        "expected_hint": "LINE / แจ้งเตือน / Notifier"
    },
    {
        "id": "SYS-26",
        "category": "Generative Images",
        "name": "26. ทดสอบสะพานเชื่อมต่อการสร้างภาพด้วย AI (ComfyUI Bridge)",
        "modules": ["modules/comfyui_bridge.py"],
        "prompt": "ช่วยสร้าง Prompt สำหรับเรนเดอร์ภาพโมเดลชุดเกราะ Iron Man Mark 6 สไตล์ภาพพิมพ์เขียวทางวิศวกรรม",
        "expected_hint": "Mark 6 / Blueprint / พิมพ์เขียว / Prompt"
    },
    {
        "id": "SYS-27",
        "category": "Tactical & Emergency",
        "name": "27. ทดสอบระบบควบคุมยุทธการและมาตรการฉุกเฉิน (Tactical Executive & Lockdown)",
        "modules": ["modules/tactical_executive.py", "modules/lockdown_overlay.py", "modules/jarvis_screen_takeover.py"],
        "prompt": "รายงานสถานะ Tactical Defense และความพร้อมของมาตรการล็อกดาวน์ระบบฉุกเฉิน",
        "expected_hint": "Tactical / ล็อกดาวน์ / ฉุกเฉิน / พร้อมรับคำสั่ง"
    },
    {
        "id": "SYS-28",
        "category": "Gaming Companion",
        "name": "28. ทดสอบโพรโทคอลผู้ช่วยการเล่นเกม (Gaming Protocol & HUD)",
        "modules": ["modules/jarvis_game_protocol.py"],
        "prompt": "ตรวจสอบรายชื่อเกมที่ติดตั้งในระบบ และรายงานความพร้อมของโหมด Game Companion",
        "expected_hint": "เกม / Game Protocol / สแตนด์บาย"
    },
    {
        "id": "SYS-29",
        "category": "System Overdrive",
        "name": "29. ทดสอบโหมดเร่งประสิทธิภาพระดับสูงสุด (System Overdrive & Resilience)",
        "modules": ["modules/jarvis_system_overdrive.py", "modules/system_resilience.py"],
        "prompt": "ตรวจสอบความพร้อมในการเปิดโหมด System Overdrive สำหรับงานคำนวณพลังสูง",
        "expected_hint": "Overdrive / ประสิทธิภาพ / ระบายความร้อน"
    },
    {
        "id": "SYS-30",
        "category": "Mobile & iOS Bridge",
        "name": "30. ทดสอบสะพานเชื่อมต่ออุปกรณ์พกพาและ iOS (Mobile API & iOS Bridge)",
        "modules": ["modules/jarvis_mobile_api.py", "modules/jarvis_ios_bridge.py"],
        "prompt": "ตรวจสอบสถานะช่องทางสื่อสารสำหรับ Mobile API และสะพานคำสั่ง Apple iOS Shortcuts",
        "expected_hint": "Mobile API / iOS / Shortcuts / สแตนด์บาย"
    },
    {
        "id": "SYS-31",
        "category": "Swarm & Cluster",
        "name": "31. ทดสอบโครงข่ายปัญญาประดิษฐ์แบบกลุ่มและคลัสเตอร์ (ASI Swarm Intelligence)",
        "modules": ["modules/jarvis_asi_swarm_intelligence.py", "modules/cluster_offloader.py"],
        "prompt": "ตรวจสอบสถานะ Swarm Mind และความพร้อมในการกระจายภาระงานไปยัง Cluster Node",
        "expected_hint": "Swarm / Cluster / โหนด / กระจายงาน"
    },
    {
        "id": "SYS-32",
        "category": "Preference & Personalization",
        "name": "32. ทดสอบการปรับแต่งตามความพึงพอใจของผู้ใช้ (Preference Alignator)",
        "modules": ["modules/preference_alignator.py"],
        "prompt": "รายงานรูปแบบการสื่อสารและสไตล์คำตอบที่ตรงกับความชอบของเจ้านาย",
        "expected_hint": "สไตล์ / ความพึงพอใจ / ชัดเจน / สุภาพ"
    },
    {
        "id": "SYS-33",
        "category": "Diagnostics & Diagnostics",
        "name": "33. ทดสอบการวินิจฉัยสุขภาพระบบโดยรวมและสถิติ (Diagnostics & Metrics)",
        "modules": ["modules/jarvis_diagnostics.py", "modules/jarvis_anomaly.py", "modules/jarvis_metrics.py"],
        "prompt": "รันการตรวจสอบวินิจฉัยสุขภาพของระบบ (Full Diagnostics) และรายงานสถิติอัตราตอบสนอง Latency",
        "expected_hint": "Diagnostics / สุขภาพระบบ / ปกติ / Latency"
    },
    {
        "id": "SYS-34",
        "category": "Offline Local Engine",
        "name": "34. ทดสอบเครื่องยนต์ออฟไลน์และพจนานุกรมโฟเนติก (Local Engine Fallback)",
        "modules": ["modules/local_engine.py"],
        "prompt": "ทดสอบความพร้อมของ Local Engine ในกรณีตัดการเชื่อมต่ออินเทอร์เน็ต",
        "expected_hint": "Local Engine / ออฟไลน์ / พร้อมสแตนด์บาย"
    },
    {
        "id": "SYS-35",
        "category": "Visual Screen & Browser Control",
        "name": "35. ทดสอบการควบคุมจอภาพ เลื่อนเมาส์เปิดเบราว์เซอร์และพิมพ์ URL (Screen & URL Navigation)",
        "modules": ["modules/jarvis_computer_agent.py", "modules/jarvis_screen_takeover.py"],
        "prompt": "ทดสอบพวกควบคุมจอผมด้วยนะเอาให้เลื่อนเมา์เปิดgoogle เเล้วพิมURL อันนี้https://marvel-splendor-2.onrender.com/",
        "expected_hint": "Google Chrome / marvel-splendor-2 / ควบคุมเมาส์ / URL"
    }
]

# ---------------------------------------------------------------------------
# ตรวจสอบสุขภาพโมดูลโดยตรง (Direct Modules Health Check)
# ---------------------------------------------------------------------------
def run_modules_health_diagnostics() -> Dict[str, Any]:
    """
    สแกนและตรวจสอบการ Import ความสมบูรณ์ของทุกไฟล์ Python ในโฟลเดอร์ modules/
    """
    modules_dir = os.path.join(BASE_DIR, "modules")
    py_files = sorted(glob.glob(os.path.join(modules_dir, "*.py")))
    
    print("\n" + "="*75)
    print(" 🔍 JARVIS DIRECT MODULES HEALTH DIAGNOSTICS (79/79 MODULES)")
    print("="*75)
    print(f" ตำแหน่งโฟลเดอร์: {modules_dir}")
    print(f" จำนวนไฟล์ทั้งหมดที่ตรวจพบ: {len(py_files)} ไฟล์\n")
    print(f" {'#':<4} {'โมดูล':<35} {'สถานะ':<15} {'รายละเอียด'}")
    print("-" * 75)

    passed = 0
    warnings = 0
    failed = 0
    details = []

    for i, file_path in enumerate(py_files, 1):
        filename = os.path.basename(file_path)
        if filename == "__init__.py":
            continue
            
        module_name = filename[:-3]
        import_path = f"modules.{module_name}"
        t0 = time.perf_counter()
        
        try:
            mod = importlib.import_module(import_path)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            
            # ตรวจสอบคลาสหรือฟังก์ชันเด่นในโมดูล
            symbols = [s for s in dir(mod) if not s.startswith("_")]
            classes = [s for s in symbols if isinstance(getattr(mod, s), type)]
            
            summary_desc = f"{len(classes)} classes, {len(symbols)} symbols ({elapsed_ms:.1f}ms)"
            print(f" [{i:02d}] {module_name:<35} ✅ HEALTHY      {summary_desc}", flush=True)
            passed += 1
            details.append({"module": module_name, "status": "HEALTHY", "time_ms": elapsed_ms, "error": None})
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            err_msg = str(e)
            if "optional" in err_msg.lower() or "missing dependency" in err_msg.lower() or "warning" in err_msg.lower():
                print(f" [{i:02d}] {module_name:<35} ⚠️ WARNING      {err_msg[:30]}", flush=True)
                warnings += 1
                details.append({"module": module_name, "status": "WARNING", "time_ms": elapsed_ms, "error": err_msg})
            else:
                print(f" [{i:02d}] {module_name:<35} ❌ FAILED       {type(e).__name__}: {err_msg[:25]}", flush=True)
                failed += 1
                details.append({"module": module_name, "status": "FAILED", "time_ms": elapsed_ms, "error": err_msg})

    print("=" * 75, flush=True)
    print(f" 📊 สรุปผลการตรวจสอบ: ผ่านฉลุย {passed} โมดูล | เตือน {warnings} | ล้มเหลว {failed} | รวม {len(py_files)-1} โมดูล", flush=True)
    print("=" * 75 + "\n", flush=True)
    
    return {"passed": passed, "warnings": warnings, "failed": failed, "total": len(py_files)-1, "details": details}

# ---------------------------------------------------------------------------
# รันการทดสอบ Live User Simulator ผ่าน HTTP API
# ---------------------------------------------------------------------------
def run_live_user_simulator(delay_sec: float = 1.5, target_filter: str = ""):
    """
    จำลองคำสั่งผู้ใช้จริงส่งตรงเข้า API ของ JARVIS (/chat)
    """
    import requests

    print("\n" + "="*75)
    print(" 🧪 JARVIS AUTOMATED USER SIMULATOR (LIVE END-TO-END SUITE)")
    print("="*75)
    print(f" เป้าหมาย API: {JARVIS_URL}")
    print(f" สมองหลักปัจจุบัน: Groq Cloud (openai/gpt-oss-120b) + Gemini 3 Flash Fallback")
    print(f" ระยะเวลาหน่วงระหว่างคำสั่ง: {delay_sec} วินาที\n")

    # ทดสอบการเชื่อมต่อเซิร์ฟเวอร์ก่อน
    try:
        ping = requests.get("http://127.0.0.1:5050/", timeout=3)
        print(" ✅ เชื่อมต่อ Web Server (Port 5050) สำเร็จ พร้อมเริ่มการทดสอบ\n")
    except Exception:
        print(" ⚠️ คำเตือน: ไม่พบการตอบรับที่ Port 5050")
        print(" กรุณาเปิดระบบ JARVIS ผ่าน run_jarvis.bat ในอีกหน้าต่างหนึ่งก่อน")
        print(" หรือเลือกเมนูตรวจสอบสุขภาพโมดูล (Option 2) เพื่อตรวจโค้ดในเครื่องทันที\n")
        confirm = input(" ต้องการลองส่งคำสั่งต่อไปหรือไม่? (y/N): ").strip().lower()
        if confirm != "y":
            return

    scenarios = TEST_SCENARIOS
    if target_filter:
        scenarios = [s for s in scenarios if target_filter.lower() in s["category"].lower() or target_filter.lower() in s["name"].lower()]
        print(f" กรองเฉพาะหมวดหมู่ที่ตรงกับ '{target_filter}' (พบ {len(scenarios)} คำสั่ง)")

    success_count = 0
    fail_count = 0
    total_time = 0.0

    for i, test in enumerate(scenarios, 1):
        print(f"\n[SCENARIO {i}/{len(scenarios)}] [{test['category']}]", flush=True)
        print(f"📌 {test['name']}", flush=True)
        print(f"📁 ระบบที่ครอบคลุม: {', '.join(test['modules'])}", flush=True)
        print(f"👤 User (Simulated): \"{test['prompt']}\"", flush=True)
        
        try:
            payload = {"message": test["prompt"]}
            t0 = time.time()
            resp = requests.post(JARVIS_URL, json=payload, timeout=90)
            elapsed = time.time() - t0
            total_time += elapsed

            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("response", "[No Text]")
                first_line = reply.strip().split("\n")[0]
                print(f"🤖 JARVIS ({elapsed:.2f}s): {first_line[:90]}...", flush=True)
                success_count += 1
            else:
                print(f"❌ HTTP Error {resp.status_code}: {resp.text[:80]}", flush=True)
                fail_count += 1

        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout: คำขอนี้ใช้เวลาเกิน 90 วินาที (ข้ามไปยังคำสั่งถัดไป...)", flush=True)
            fail_count += 1
        except requests.exceptions.RequestException as req_err:
            print(f"❌ Connection Error: {req_err}", flush=True)
            fail_count += 1
            # ตรวจสอบว่าเซิร์ฟเวอร์ยังเปิดอยู่หรือไม่
            try:
                requests.get("http://127.0.0.1:5050/", timeout=2)
                print(" 🔄 เซิร์ฟเวอร์ยังทำงานอยู่ ดำเนินการทดสอบข้อถัดไป...", flush=True)
            except Exception:
                print(" 🛑 เซิร์ฟเวอร์ปิดตัวลง ยุติการทดสอบ", flush=True)
                break

        print("-" * 65, flush=True)
        time.sleep(delay_sec)

    avg_time = (total_time / max(1, success_count)) if success_count else 0
    print("\n" + "="*75)
    print(f" 🏁 ผลการทดสอบ Live User Simulator:")
    print(f"    - สำเร็จ: {success_count}/{len(scenarios)}")
    print(f"    - ขัดข้อง: {fail_count}")
    print(f"    - เวลาเฉลี่ยต่อคำตอบ: {avg_time:.2f} วินาที")
    print("="*75 + "\n")

# ---------------------------------------------------------------------------
# จุดเริ่มต้นหลัก (Main Entrypoint)
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="JARVIS Automated User Simulator & Modules Test Suite")
    parser.add_argument("--live", action="store_true", help="รันเฉพาะ Live E2E User Simulation ผ่าน HTTP")
    parser.add_argument("--modules", action="store_true", help="รันเฉพาะ Direct Modules Health Diagnostics")
    parser.add_argument("--all", action="store_true", help="รันครบทุกการทดสอบทั้งสองส่วน")
    parser.add_argument("--delay", type=float, default=1.5, help="เวลาหน่วงระหว่างคำสั่ง (วินาที)")
    parser.add_argument("--filter", type=str, default="", help="กรองเฉพาะหมวดหมู่คำสั่งที่ระบุ")
    args = parser.parse_args()

    # รันตาม Argument ถ้ามีการส่งพารามิเตอร์มา
    if args.modules:
        run_modules_health_diagnostics()
        return
    elif args.live:
        run_live_user_simulator(delay_sec=args.delay, target_filter=args.filter)
        return
    elif args.all:
        run_modules_health_diagnostics()
        run_live_user_simulator(delay_sec=args.delay, target_filter=args.filter)
        return

    # ถ้าไม่มีการส่ง Argument ให้แสดงหน้าจอเมนูที่ใช้งานง่าย
    print("=" * 65)
    print(" 🚀 JARVIS MULTI-SYSTEM SIMULATOR & TEST FRAMEWORK")
    print("=" * 65)
    print(" 1. [Live E2E] ทดสอบส่งคำสั่งผู้ใช้จริง 35 ระบบผ่าน API Port 5050")
    print(" 2. [Direct Check] ตรวจสอบความสมบูรณ์ของทุกไฟล์ใน modules/ (79 โมดูล)")
    print(" 3. [Full Suite] รันการทดสอบครบทุกระบบทั้งหมด (1 + 2)")
    print(" 4. ออกจากโปรแกรม")
    print("=" * 65)

    choice = input(" เลือกตัวเลือกการทดสอบ (กด Enter เพื่อเลือก 1): ").strip()
    if choice == "2":
        run_modules_health_diagnostics()
    elif choice == "3":
        run_modules_health_diagnostics()
        run_live_user_simulator(delay_sec=args.delay, target_filter=args.filter)
    elif choice == "4":
        print(" ยกเลิกการทดสอบครับ")
    else:
        # Default = 1
        run_live_user_simulator(delay_sec=args.delay, target_filter=args.filter)

if __name__ == "__main__":
    main()
