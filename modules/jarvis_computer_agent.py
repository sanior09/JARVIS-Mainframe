import os
import time
import json
import logging
import subprocess
import pyautogui
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [AGENTIC UI] %(message)s")
load_dotenv()

class AgenticComputerController:
    def __init__(self):
        import pyautogui
        
        pyautogui.FAILSAFE = False
        
        api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        if api_key and not api_key.startswith("YOUR_"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                gem_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                self.model = genai.GenerativeModel(gem_model)
            except Exception as e:
                logging.warning(f"Failed to initialize Gemini Vision for computer agent: {e}")
            
        self.screen_width, self.screen_height = pyautogui.size()
        self.max_steps = 10

    def get_screenshot(self):
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_ui_screenshot.png")
        screenshot.save(path)
        return path

    def normalize_to_pixels(self, ymin, xmin, ymax, xmax):
        """แปลงค่า 0-1000 จาก Gemini เป็นพิกัดหน้าจอจริง"""
        center_x_norm = (xmin + xmax) / 2
        center_y_norm = (ymin + ymax) / 2
        
        real_x = int((center_x_norm / 1000) * self.screen_width)
        real_y = int((center_y_norm / 1000) * self.screen_height)
        return real_x, real_y

    def _analyze_search_results(self, query: str) -> str:
        """Fetches live search context and synthesizes a concise, spoken answer via Groq."""
        try:
            import requests
            from bs4 import BeautifulSoup
            from groq import Groq

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            url = 'https://html.duckduckgo.com/html/?q=' + requests.utils.quote(query)
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                snippets = [s.get_text().strip() for s in soup.find_all('a', class_='result__snippet')[:4]]
                context = "\n".join(snippets).strip()
                if context:
                    groq_key = os.getenv("GROQ_API_KEY")
                    if groq_key:
                        client = Groq(api_key=groq_key)
                        model_name = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
                        resp = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'คุณคือ J.A.R.V.I.S. สรุปข้อมูลสำคัญจากหน้าจอที่ค้นหาให้เจ้านายฟังเป็นภาษาไทยอย่างกระชับ สุภาพ 1-2 ประโยคสำหรับอ่านออกเสียงตอบ หากมีตัวเลขสำคัญเช่นราคา ให้ระบุชัดเจน'
                                },
                                {
                                    'role': 'user',
                                    'content': f'ข้อมูลที่สืบค้นพบบนหน้าจอ:\n{context}\n\nคำสั่ง: สรุปคำตอบสั้นๆ ให้เจ้านาย'
                                }
                            ],
                            max_tokens=150,
                            temperature=0.3
                        )
                        return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"Failed to synthesize search analysis: {e}")
        return ""

    def execute_goal(self, goal: str) -> str:
        from jarvis_screen_takeover import (
            start_screen_takeover, update_screen_takeover,
            stop_screen_takeover, is_screen_takeover_stopped, notify_agent_click
        )
        import webbrowser
        import urllib.parse
        import pyperclip
        import pyautogui
        pyautogui.FAILSAFE = False

        clean_goal = goal.lower().strip()
        logging.info(f"Starting Agentic Computer Control for Goal: {goal}")

        # 1. Activate glowing blue neon border and HUD pill immediately
        start_screen_takeover(f"เริ่มต้นการควบคุมคอมพิวเตอร์: {goal[:35]}...")

        try:
            if is_screen_takeover_stopped():
                return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

            import re

            browser_keywords = [
                "เปิดเบราว์เซอร์", "เปิดเบราเซอร์", "เปิด browser", "เปิด chrome", "เปิดเว็บ",
                "ค้นหา", "เสิร์ช", "search", "google", "กูเกิล", "ราคาทอง", "url", "พิมurl",
                "พิมพ์url", "พิม url", "พิมพ์ url", "เว็บ", "เว็ป", "link", "ลิงก์", "ลิงค์",
                "เปิดgoogle", "เปิด google", "เข้าเว็บ"
            ]
            app_commands = {
                "notepad": ("notepad.exe", "Notepad"),
                "สมุดจด": ("notepad.exe", "Notepad"),
                "เครื่องคิดเลข": ("calc.exe", "Calculator"),
                "calculator": ("calc.exe", "Calculator"),
                "cmd": ("cmd.exe", "Command Prompt"),
                "terminal": ("powershell.exe", "Windows Terminal"),
                "explorer": ("explorer.exe", "File Explorer"),
                "ไฟล์": ("explorer.exe", "File Explorer")
            }

            control_mode = os.getenv("COMPUTER_CONTROL_MODE", "background").lower().strip()
            force_visual = any(kw in clean_goal for kw in ["คุมเมาส์", "ขยับเมาส์", "ลากเมาส์", "คลิกเมาส์", "visual control", "เลื่อนเมาส์", "เลื่อนเมา์", "เลื่อนเมาส", "คุมจอ", "ควบคุมจอ", "ขยับเมา"])

            # =================================================================
            # MODE 1: Background Automation (100% Mouse-Free & Non-Intrusive)
            # =================================================================
            if control_mode == "background" and not force_visual:
                logging.info(f"[BACKGROUND AGENT] Running Mode 1 (Mouse-Free Background Automation) for: '{goal}'")
                
                # 1. Search & Browser in Background
                if any(kw in clean_goal for kw in browser_keywords) or "http://" in goal or "https://" in goal:
                    search_query = ""
                    url_match = re.search(r'https?://[^\s<>"]+', goal)
                    if url_match:
                        search_query = url_match.group(0).strip()

                    if not search_query:
                        for trigger in ["ค้นหาข้อมูลเกี่ยวกับ", "ค้นหาข้อมูล", "ค้นหาเรื่อง", "ค้นหา", "search for", "search", "เสิร์ช", "หาข้อมูล", "พิมurl", "พิมพ์url", "พิมว่า", "พิมพ์ว่า"]:
                            if trigger in goal:
                                parts = goal.split(trigger, 1)
                                if len(parts) > 1 and parts[1].strip():
                                    candidate = parts[1].strip().strip(":").strip()
                                    if candidate.startswith("อันนี้"):
                                        candidate = candidate[len("อันนี้"):].strip()
                                    search_query = candidate
                                    break
                    if not search_query:
                        if "ราคาทอง" in clean_goal:
                            search_query = "ราคาทองคำวันนี้"
                        elif "youtube" in clean_goal:
                            search_query = "https://www.youtube.com"

                    if search_query:
                        update_screen_takeover(f"J.A.R.V.I.S. (พื้นหลัง): กำลังเปิด '{search_query}'...")
                        encoded_query = urllib.parse.quote_plus(search_query)
                        if search_query.startswith("http://") or search_query.startswith("https://"):
                            target_url = search_query
                        else:
                            target_url = f"https://www.google.com/search?q={encoded_query}"

                        # Open tab cleanly without hijacking mouse
                        webbrowser.open(target_url)

                        if search_query.startswith("http://") or search_query.startswith("https://"):
                            update_screen_takeover(f"สำเร็จ: เปิดเว็บไซต์ {target_url} เรียบร้อย")
                            time.sleep(0.8)
                            return f"เปิดเว็บไซต์ '{target_url}' บนเบราว์เซอร์ให้เรียบร้อยแล้วครับเจ้านาย โดยไม่รบกวนเมาส์ของเจ้านายครับ"

                        # Deep analyze the live results in background
                        update_screen_takeover("J.A.R.V.I.S. (พื้นหลัง): กำลังวิเคราะห์ข้อมูล...")
                        summary = self._analyze_search_results(search_query)

                        update_screen_takeover(f"สำเร็จ: วิเคราะห์ '{search_query}' เรียบร้อย")
                        time.sleep(0.8)
                        if summary:
                            return f"ผมเปิดหน้าค้นหา '{search_query}' บนเบราว์เซอร์ และวิเคราะห์ข้อมูลให้เรียบร้อยแล้วครับเจ้านาย: {summary}"
                        else:
                            return f"ผมเปิดหน้าต่างเบราว์เซอร์และสืบค้นข้อมูล '{search_query}' บนหน้าจอให้เรียบร้อยแล้วครับเจ้านาย โดยไม่รบกวนเมาส์ของเจ้านายครับ"
                    else:
                        webbrowser.open("https://www.google.com")
                        update_screen_takeover("สำเร็จ: เปิดหน้าต่างเบราว์เซอร์เรียบร้อย")
                        time.sleep(0.8)
                        return "เปิดหน้าต่างเบราว์เซอร์ให้เรียบร้อยแล้วครับเจ้านาย โดยไม่รบกวนเมาส์ของเจ้านายครับ"

                # 2. Launch Windows Apps in Background
                if any(kw in clean_goal for kw in ["steam", "สตีม", "สตรีม"]):
                    is_lib = any(kw in clean_goal for kw in ["คลัง", "library", "คลังเกม", "เกมในคลัง"])
                    if is_lib:
                        update_screen_takeover("กำลังเปิด Steam คลังเกม (Library)...")
                        try:
                            os.startfile("steam://open/games")
                        except Exception:
                            subprocess.Popen("start steam://open/games", shell=True)
                        time.sleep(1.0)
                        update_screen_takeover("สำเร็จ: เปิด Steam คลังเกมเรียบร้อย")
                        return ""
                    else:
                        update_screen_takeover("กำลังเปิดโปรแกรม Steam...")
                        try:
                            os.startfile("steam://open/main")
                        except Exception:
                            try:
                                os.startfile(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Steam\Steam.lnk")
                            except Exception:
                                subprocess.Popen("start steam://open/main", shell=True)
                        time.sleep(1.0)
                        update_screen_takeover("สำเร็จ: เปิดโปรแกรม Steam เรียบร้อย")
                        return "เปิดโปรแกรม Steam ให้เรียบร้อยแล้วครับเจ้านาย"

                for app_kw, (exe_name, app_display) in app_commands.items():
                    if f"เปิด {app_kw}" in clean_goal or f"เปิด{app_kw}" in clean_goal:
                        update_screen_takeover(f"J.A.R.V.I.S. (พื้นหลัง): กำลังเปิด {app_display}...")
                        subprocess.Popen([exe_name], shell=True)
                        time.sleep(0.8)
                        update_screen_takeover(f"สำเร็จ: เปิดโปรแกรม {app_display} แล้ว")
                        time.sleep(0.8)
                        return f"เปิดโปรแกรม {app_display} ให้เรียบร้อยแล้วครับเจ้านาย โดยไม่รบกวนเมาส์ของเจ้านายครับ"

            # =================================================================
            # MODE 2: Visual Takeover (เมื่อตั้งใจสั่งให้ลากเมาส์ หรือ force_visual)
            # =================================================================
            # -----------------------------------------------------------------
            # Step-by-Step Scenario 1: Open Browser and Search / URL (Visual Mouse & Keyboard)
            # -----------------------------------------------------------------
            if any(kw in clean_goal for kw in browser_keywords) or "http://" in goal or "https://" in goal:
                search_query = ""
                # ลำดับที่ 1: ดึง URL โดยตรงจากคำสั่ง (เช่น https://marvel-splendor-2.onrender.com/)
                url_match = re.search(r'https?://[^\s<>"]+', goal)
                if url_match:
                    search_query = url_match.group(0).strip()

                # ลำดับที่ 2: ตรวจจับคำค้นหาหรือการพิมพ์ข้อความ
                if not search_query:
                    try:
                        from jarvis_core.automation_agent import extract_search_query
                        search_query = extract_search_query(goal)
                    except Exception:
                        for trigger in [
                            "ค้นหาข้อมูลเกี่ยวกับ", "ค้นหาข้อมูล", "ค้นหาเรื่อง", "ค้นหา", "search for", "search",
                            "เสิร์ช", "หาข้อมูล", "พิมurl", "พิมพ์url", "พิม url", "พิมพ์ url", "พิมว่า", "พิมพ์ว่า",
                            "เปิดเว็บ", "เข้าเว็บ", "พิม", "พิมพ์"
                        ]:
                            if trigger in goal:
                                parts = goal.split(trigger, 1)
                                if len(parts) > 1 and parts[1].strip():
                                    candidate = parts[1].strip().strip(":").strip()
                                    if candidate.startswith("อันนี้"):
                                        candidate = candidate[len("อันนี้"):].strip()
                                    search_query = candidate
                                    break

                # ลำดับที่ 3: คำสั่งที่ไม่มี Keyword นำหน้า
                if not search_query:
                    if "ราคาทอง" in clean_goal:
                        search_query = "ราคาทองคำวันนี้"
                    elif "youtube" in clean_goal:
                        search_query = "https://www.youtube.com"

                scale_x = self.screen_width / 1920.0
                scale_y = self.screen_height / 1080.0

                # 1. Pinned Chrome icon on Windows Taskbar (1228, 1057 on 1920x1080)
                chrome_taskbar_x = int(1228 * scale_x)
                chrome_taskbar_y = int(1057 * scale_y)

                # 2. Address / Search Bar (960, 82 on 1920x1080)
                address_bar_x = int(960 * scale_x)
                address_bar_y = int(82 * scale_y)

                # ขั้นตอนที่ 1: เลื่อนเมาส์ไปยังไอคอน Google Chrome บน Taskbar แล้วคลิกเปิด
                update_screen_takeover("ขั้นตอนที่ 1: กำลังเลื่อนเมาส์ไปคลิกเปิด Google Chrome...")
                notify_agent_click()
                pyautogui.moveTo(chrome_taskbar_x, chrome_taskbar_y, duration=0.8)
                notify_agent_click()
                pyautogui.click(chrome_taskbar_x, chrome_taskbar_y)
                # เพื่อให้มั่นใจ 100% ว่าหน้าต่าง Chrome เปิดขึ้นมาบนหน้าจอ
                try:
                    subprocess.Popen("start chrome", shell=True)
                except Exception:
                    pass
                time.sleep(1.2)

                if is_screen_takeover_stopped():
                    return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

                # ขั้นตอนที่ 2: เลื่อนเมาส์ไปที่ช่องที่อยู่เว็บ / ช่องค้นหา (Address Bar)
                update_screen_takeover("ขั้นตอนที่ 2: เลื่อนเมาส์ไปที่แถบที่อยู่เว็บ (Address Bar)...")
                notify_agent_click()
                pyautogui.moveTo(address_bar_x, address_bar_y, duration=0.8)
                notify_agent_click()
                pyautogui.click(address_bar_x, address_bar_y)
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.4)

                if is_screen_takeover_stopped():
                    return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

                # ขั้นตอนที่ 3: พิมพ์ URL หรือคำค้นหาและกด Enter
                if search_query:
                    is_direct_url = search_query.startswith(("http://", "https://"))
                    if is_direct_url:
                        update_screen_takeover(f"ขั้นตอนที่ 3: กำลังพิมพ์ URL '{search_query}'...")
                    else:
                        update_screen_takeover(f"ขั้นตอนที่ 3: กำลังพิมพ์คำค้นหา '{search_query}'...")

                    pyperclip.copy(search_query)
                    time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.6)

                    if is_screen_takeover_stopped():
                        return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

                    # ขั้นตอนที่ 4: กด Enter เพื่อดำเนินการ
                    update_screen_takeover("ขั้นตอนที่ 4: กด Enter เพื่อนำทางไปยังเป้าหมาย...")
                    pyautogui.press('enter')
                    time.sleep(1.8)

                    if is_direct_url:
                        update_screen_takeover(f"สำเร็จ: นำทางไปยัง {search_query} เรียบร้อย")
                        time.sleep(1.0)
                        return f"ควบคุมเมาส์เปิด Google Chrome และพิมพ์ URL นำทางไปยัง '{search_query}' บนหน้าจอให้เรียบร้อยแล้วครับเจ้านาย"

                    # ขั้นตอนที่ 5: สแกนและวิเคราะห์ข้อมูลผลลัพธ์บนหน้าจอ (กรณีคำค้นหา)
                    update_screen_takeover("ขั้นตอนที่ 5: J.A.R.V.I.S. กำลังวิเคราะห์ผลลัพธ์บนหน้าจอ...")
                    summary = self._analyze_search_results(search_query)

                    update_screen_takeover(f"สำเร็จ: ค้นหาและวิเคราะห์ '{search_query}' เรียบร้อย")
                    time.sleep(1.0)
                    if summary:
                        return f"ผมเปิดเบราว์เซอร์และวิเคราะห์ข้อมูลบนหน้าจอให้เรียบร้อยแล้วครับเจ้านาย: {summary}"
                    else:
                        return f"ควบคุมเมาส์คลิกเปิด Chrome และพิมพ์ค้นหา '{search_query}' บนหน้าจอให้เรียบร้อยแล้วครับเจ้านาย"
                else:
                    update_screen_takeover("สำเร็จ: เปิดหน้าต่างเบราว์เซอร์เรียบร้อยแล้ว")
                    time.sleep(1.0)
                    return "ควบคุมเมาส์คลิกเปิด Google Chrome และเข้าสู่หน้าต่างเบราว์เซอร์ให้เรียบร้อยแล้วครับเจ้านาย"

            # -----------------------------------------------------------------
            # Step-by-Step Scenario 2: Launch Common Windows Applications
            # -----------------------------------------------------------------
            for app_kw, (exe_name, app_display) in app_commands.items():
                if f"เปิด {app_kw}" in clean_goal or f"เปิด{app_kw}" in clean_goal:
                    update_screen_takeover(f"ขั้นตอนที่ 1: กำลังค้นหาและเปิดโปรแกรม {app_display}...")
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyperclip.copy(exe_name.replace('.exe', ''))
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.4)
                    pyautogui.press('enter')
                    time.sleep(1.5)
                    update_screen_takeover(f"สำเร็จ: เปิดโปรแกรม {app_display} แล้ว")
                    time.sleep(1.0)
                    return f"เปิดโปรแกรม {app_display} บนคอมพิวเตอร์ให้เรียบร้อยแล้วครับเจ้านาย"

            # -----------------------------------------------------------------
            # Step-by-Step Scenario 3: Vision-Guided GUI Loop (for Arbitrary Goals)
            # -----------------------------------------------------------------
            if not self.model:
                logging.warning("[AGENTIC UI] Vision model is unavailable (GEMINI_API_KEY required for vision loops).")
                return f"รับทราบคำสั่ง '{goal}' ครับ (สำหรับงานที่ต้องคลิกวิเคราะห์ภาพหน้าจออัตโนมัติ ต้องการ GEMINI_API_KEY เพื่อเปิดใช้งานระบบ Vision เต็มรูปแบบครับ)"

            for step in range(self.max_steps):
                if is_screen_takeover_stopped():
                    logging.warning("[AGENTIC UI] Aborted by user via Stop button or ESC.")
                    return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

                logging.info(f"--- Step {step + 1}/{self.max_steps} ---")
                update_screen_takeover(f"ขั้นตอนที่ {step + 1}: กำลังถ่ายภาพหน้าจอ...")
                
                screenshot_path = self.get_screenshot()
                import PIL.Image
                img = PIL.Image.open(screenshot_path)
                
                prompt = f"""
                You are J.A.R.V.I.S., autonomously controlling a Windows computer.
                Your ultimate goal is: {goal}
                
                Analyze the provided screenshot of the current screen.
                Determine the single next action required to progress towards the goal.
                If the goal is already achieved or cannot be achieved, return 'done'.
                
                You MUST respond ONLY with a valid JSON block, NO OTHER TEXT.
                Format:
                {{
                    "action": "click" | "type" | "press" | "scroll_down" | "done",
                    "reasoning": "Briefly explain why this action is needed",
                    "box_2d": [ymin, xmin, ymax, xmax] (integers 0-1000 representing bounding box of the element to click, ONLY if action is 'click'),
                    "text": "Text to type or key to press (ONLY if action is 'type' or 'press')"
                }}
                """
                
                update_screen_takeover(f"ขั้นตอนที่ {step + 1}: กำลังวิเคราะห์หน้าจอ...")
                
                try:
                    response = self.model.generate_content([prompt, img])
                    
                    raw = response.text.strip()
                    if raw.startswith("```json"): raw = raw[7:-3].strip()
                    elif raw.startswith("```"): raw = raw[3:-3].strip()
                    
                    data = json.loads(raw)
                    action = data.get("action")
                    reasoning = data.get("reasoning", "")
                    logging.info(f"LLM Reasoning: {reasoning}")
                    
                    if is_screen_takeover_stopped():
                        return "ยกเลิกการควบคุมคอมพิวเตอร์ตามคำสั่งเจ้านายแล้วครับ"

                    if action == "done":
                        update_screen_takeover(f"สำเร็จ: {reasoning}")
                        time.sleep(1.0)
                        return f"สำเร็จแล้ว: {reasoning}"
                        
                    elif action == "click":
                        box = data.get("box_2d")
                        if box and len(box) == 4:
                            rx, ry = self.normalize_to_pixels(box[0], box[1], box[2], box[3])
                            logging.info(f"Clicking at {rx}, {ry}")
                            update_screen_takeover(f"Clicking: {reasoning}")
                            notify_agent_click()
                            pyautogui.moveTo(rx, ry, duration=0.8)
                            notify_agent_click()
                            pyautogui.click()
                        else:
                            logging.warning("No bounding box provided for click.")
                            
                    elif action == "type":
                        text = data.get("text", "")
                        logging.info(f"Typing: {text}")
                        update_screen_takeover(f"Typing: {text}")
                        try:
                            pyperclip.copy(text)
                            pyautogui.hotkey('ctrl', 'v')
                        except Exception:
                            pyautogui.write(text, interval=0.05)
                        
                    elif action == "press":
                        key = data.get("text", "enter")
                        logging.info(f"Pressing: {key}")
                        update_screen_takeover(f"Pressing: {key}")
                        pyautogui.press(key)
                        
                    elif action == "scroll_down":
                        logging.info("Scrolling down")
                        update_screen_takeover("Scrolling down...")
                        pyautogui.scroll(-500)
                        
                    time.sleep(1.5)
                    
                except Exception as e:
                    logging.error(f"Error in UI Loop: {e}")
                    return f"เกิดข้อผิดพลาดระหว่างทำงาน: {e}"
                    
            return f"ระบบหยุดทำงานเนื่องจากครบกำหนด {self.max_steps} ขั้นตอน (ป้องกันการวนลูป)"
        finally:
            stop_screen_takeover()

    def execute_social_workflow(self, platform: str, task: str, target: str = "", content: str = "") -> str:
        """
        Specialized Social Media Workflow Engine (Instagram Story/Post, LINE, Discord, Messenger).
        Opens the relevant platform and guides the autonomous vision agent.
        """
        import webbrowser
        plat = platform.lower().strip()
        task_clean = task.lower().strip()

        # Step 1: Open Target Platform
        if "ig" in plat or "instagram" in plat:
            webbrowser.open("https://www.instagram.com")
            time.sleep(2.0)
            if "story" in task_clean or "สตอรี่" in task_clean:
                goal = f"อยู่ในหน้า Instagram ให้คลิกสร้างสตอรี่ใหม่ (Create Story/Your Story) และเตรียมลงสตอรี่ {content}".strip()
            else:
                goal = f"อยู่ในหน้า Instagram ให้คลิกปุ่มสร้างโพสต์ใหม่ (+) และดำเนินการโพสต์ข้อความ: {content}".strip()

        elif "line" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'line:'"], shell=False)
            except Exception:
                pass
            time.sleep(2.0)
            goal = f"อยู่ในแอป LINE ให้ค้นหาชื่อเพื่อน '{target}' แล้วเปิดหน้าแชทเพื่อส่งข้อความ '{content}'"

        elif "discord" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'discord:'"], shell=False)
            except Exception:
                webbrowser.open("https://discord.com/app")
            time.sleep(2.0)
            goal = f"อยู่ใน Discord ให้ค้นหาห้องหรือเพื่อน '{target}' และพิมพ์ข้อความ '{content}'"

        elif "messenger" in plat or "facebook" in plat:
            webbrowser.open("https://www.messenger.com")
            time.sleep(2.0)
            goal = f"อยู่ใน Messenger ให้ค้นหาชื่อเพื่อน '{target}' แล้วพิมพ์ส่งข้อความ '{content}'"

        elif "telegram" in plat or "เทเลแกรม" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'tg:'"], shell=False)
            except Exception:
                webbrowser.open("https://web.telegram.org")
            time.sleep(2.0)
            goal = f"อยู่ใน Telegram ให้ค้นหาชื่อ '{target}' และพิมพ์ส่งข้อความ '{content}'"

        elif "whatsapp" in plat or "วอตส์แอป" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'whatsapp:'"], shell=False)
            except Exception:
                webbrowser.open("https://web.whatsapp.com")
            time.sleep(2.0)
            goal = f"อยู่ใน WhatsApp ให้ค้นหาแชทของ '{target}' และพิมพ์ส่งข้อความ '{content}'"

        elif "slack" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'slack:'"], shell=False)
            except Exception:
                webbrowser.open("https://app.slack.com")
            time.sleep(2.0)
            goal = f"อยู่ใน Slack ให้ค้นหาแชนแนลหรือเพื่อน '{target}' และพิมพ์ข้อความ '{content}'"

        elif "teams" in plat:
            try:
                subprocess.Popen(["powershell", "-Command", "Start-Process 'msteams:'"], shell=False)
            except Exception:
                webbrowser.open("https://teams.microsoft.com")
            time.sleep(2.0)
            goal = f"อยู่ใน Microsoft Teams ให้ค้นหาเพื่อนหรือกลุ่ม '{target}' และพิมพ์ข้อความ '{content}'"

        elif "twitter" in plat or " x " in f" {plat} " or plat == "x":
            webbrowser.open("https://x.com")
            time.sleep(2.0)
            goal = f"อยู่ใน X (Twitter) ให้โพสต์ข้อความ: '{content}' หรือส่ง DM ถึง '{target}'"

        else:
            # --- GENERAL APPLICATION FALLBACK ---
            # Try to launch via Windows Search / Start Menu if not running
            logging.info(f"Launching arbitrary application for platform: {platform}")
            try:
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(platform, interval=0.04)
                time.sleep(0.6)
                pyautogui.press('enter')
                time.sleep(2.5)
            except Exception as e:
                logging.warning(f"Failed to trigger start menu search for {platform}: {e}")

            if target:
                goal = f"ในโปรแกรม '{platform}' ให้ค้นหาหรือเลือกแชทของผู้รับ '{target}' แล้วพิมพ์ส่งข้อความ: '{content}'"
            else:
                goal = f"ในโปรแกรม '{platform}' ให้ดำเนินการ '{task}': '{content}'"

        return self.execute_goal(goal)


if __name__ == "__main__":
    agent = AgenticComputerController()
    print(agent.execute_goal("เปิด Notepad และพิมพ์คำว่า Hello J.A.R.V.I.S."))
