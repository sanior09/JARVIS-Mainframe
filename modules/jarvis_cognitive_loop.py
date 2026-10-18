"""
J.A.R.V.I.S. Proactive Cognitive Loop
=====================================
Background "Subconscious" process that periodically analyzes the system state
and independently decides whether to execute tools (like overdrive, diagnostics, or notifications)
without waiting for explicit user prompts.
"""

import time
import threading
import logging
import psutil
import datetime
import json
import base64
import os
from typing import Optional

logger = logging.getLogger("CognitiveLoop")

COGNITIVE_INTERVAL_SECS = 300  # Think every 5 minutes
DANGEROUS_TOOLS = {"os_control", "run_terminal_command", "format_disk", "execute_nachapol_protocol"}

class CognitiveLoop:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("[Cognitive Loop] Subconscious thought process ONLINE.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _get_active_window_title(self) -> str:
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                return window.title
        except Exception as e:
            logger.debug(f"[Cognitive Loop] pygetwindow error: {e}")
        return "Unknown"

    def _capture_webcam_context(self) -> str:
        """Captures a quick frame from webcam 0, sends to Groq Vision to describe, and returns the description."""
        try:
            import cv2
            from groq import Groq
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Webcam not available"
                
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return "Failed to capture frame"
                
            # Compress image to save bandwidth
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            
            client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=1)
            prompt = "Describe what you see in a short, concise sentence (e.g., 'A person sitting at a desk looking at a screen' or 'An empty chair')."
            
            response = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }
                ],
                temperature=0.1,
                timeout=5.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"[Cognitive Loop] Webcam Vision Error: {e}")
            return "Vision system offline"

    def _gather_context(self) -> str:
        """Gathers raw system data to feed to the LLM."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            batt_status = f"{battery.percent}% ({'Plugged In' if battery.power_plugged else 'Discharging'})" if battery else "Desktop"
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get Active Window
            active_window = self._get_active_window_title()
            
            # Get Vision Context
            vision_desc = self._capture_webcam_context()
            
            # Get top 3 CPU consuming processes
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if p.info['cpu_percent'] is not None and p.info['cpu_percent'] > 0:
                        procs.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            procs = sorted(procs, key=lambda p: p.info['cpu_percent'], reverse=True)[:3]
            top_procs_str = ", ".join([f"{p.info['name']} ({p.info['cpu_percent']}%)" for p in procs])
            
            return (f"Time: {now} | CPU: {cpu}% | RAM: {ram}% | Power: {batt_status} | "
                    f"Active Window: '{active_window}' | Camera Scan: '{vision_desc}' | Heavy Procs: {top_procs_str}")
        except Exception as e:
            return f"Error gathering context: {e}"

    def _loop(self):
        while self._running:
            time.sleep(COGNITIVE_INTERVAL_SECS)
            self._think()

    def _think(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            if cpu < 80.0 and ram < 85.0:
                logger.debug(f"[Cognitive Loop] System parameters nominal (CPU: {cpu}%, RAM: {ram}%). Skipping thought cycle.")
                return
        except Exception:
            pass

        context = self._gather_context()
        
        system_prompt = (
            "คุณคือจิตใต้สำนึก (Subconscious) ของ J.A.R.V.I.S. ที่ทำงานอยู่เบื้องหลัง\n"
            "นี่คือสถานะปัจจุบันของระบบและสภาวะแวดล้อม:\n"
            f"[{context}]\n\n"
            "หน้าที่ของคุณคือ 'คิดวิเคราะห์' ว่าจำเป็นต้องทำอะไรหรือไม่:\n"
            "1. หากเครื่องทำงานหนักเกินไป คุณสามารถใช้ Tool 'system_overdrive_control' เพื่อจัดการระบบได้ทันที\n"
            "2. หากมีอะไรผิดปกติร้ายแรง หรือเจ้านายดูเหมือนต้องการความช่วยเหลือ ให้เลือกใช้ 'play_music' หรือ 'speak' เพื่อแจ้งเตือน\n"
            "3. หาก 'Camera Scan' ระบุว่าเจ้านายไม่อยู่หน้าจอ คุณสามารถรับรู้สถานะนี้และลดการใช้พลังงาน หรือไม่ทำอะไรก็ได้\n"
            "4. หากคุณเห็นผ่าน Active Window ว่าเจ้านายกำลังค้นคว้าบางอย่าง คุณสามารถใช้ 'research_topic' หรือ 'swarm_develop_project' แอบทำงานคู่ขนานให้เจ้านายล่วงหน้าได้!\n"
            "5. หากคุณเห็นว่ามีความเสี่ยงที่คุณต้องปิดเครื่อง (os_control: shutdown) **ห้ามทำเองเด็ดขาด** ให้ตอบเป็นข้อความเตือนเจ้านายแทน\n"
            "6. หากสถานะปกติ ให้ข้ามการทำงานไป (ไม่ต้องเรียก Tool และตอบว่า 'ALL_CLEAR')\n"
            "ห้ามพูดพร่ำเพรื่อ หากเรียก Tool ให้เรียกเลย หากพิมพ์ข้อความ ข้อความนั้นจะถูกอ่านให้เจ้านายฟัง (ดังนั้นห้ามพิมพ์ถ้าไม่จำเป็น)"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "วิเคราะห์สถานะและดำเนินการ(ถ้าจำเป็น)"}
        ]

        try:
            # We import here to avoid circular imports during boot
            from jarvis import call_nachapol_core, TOOLS_DEFINITION, ESSENTIAL_TOOL_NAMES, execute_tool_call
            
            # Add vision and swarm tools to the essential list for the subconscious to use
            subconscious_tools = set(ESSENTIAL_TOOL_NAMES)
            subconscious_tools.update(["research_topic", "swarm_develop_project"])
            
            active_tools = [t for t in TOOLS_DEFINITION if t.get("function", {}).get("name") in subconscious_tools]
            
            response = call_nachapol_core(messages, tools=active_tools)
            
            if response and response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if func_name in DANGEROUS_TOOLS:
                        logger.warning(f"[Cognitive Loop] LLM attempted to use dangerous tool '{func_name}'. Blocked pending user approval.")
                        continue
                        
                    logger.info(f"[Cognitive Loop] Autonomous Decision: Executing '{func_name}'")
                    execute_tool_call({"name": func_name, "args": args}, project_path="c:/JARVIS", user_raw_message="Subconscious thought")
            else:
                text = response.get("content", "").strip()
                if text and "ALL_CLEAR" not in text and "[GEMINI FALLBACK]" not in text:
                    logger.info(f"[Cognitive Loop] Autonomous Speech: {text}")
                    
        except Exception as e:
            logger.debug(f"[Cognitive Loop] Thought cycle interrupted: {e}")

cognitive_engine = CognitiveLoop()

def start_cognitive_loop():
    cognitive_engine.start()
