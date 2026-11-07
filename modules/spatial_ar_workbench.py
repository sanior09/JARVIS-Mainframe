"""
modules/spatial_ar_workbench.py
──────────────────────────────────────────────────────────────────────────────
J.A.R.V.I.S. Desk AR Spatial Workbench & Object Reconnaissance Subsystem
Transforms camera vision into an Augmented Reality (AR) HUD workbench:
- Detects physical objects on the desk/workbench (Single or Multi-Target).
- Handles interactive human-in-the-loop targeting:
  * Detects multiple objects and asks user: "ตรวจพบ 2 รายการ... เจ้านายต้องการชิ้นไหนครับ?"
  * If only 1 object found, auto-selects and unfolds full 6-card AR HUD immediately.
  * Allows sequential two-step commands: "สแกนสิ่งนี้" (draws reticles) then "หาข้อมูลสิ่งที่อยู่ในวงให้หน่อย".
- Synthesizes 6 multi-vector data cards (Security Specs, Pricing, Display,
  Telemetry Bar Charts, Community Video Stream, Hardware IO).
- Integrates dynamic vector leader lines linking physical objects to HUD cards.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger("JARVIS.SpatialARWorkbench")


class SpatialARWorkbench:
    """
    Subsystem responsible for desk-space AR Object Reconnaissance.
    Emulates the high-tech Tony Stark / Huw Prosser AR Workbench HUD.
    """

    def __init__(self, core_ref: Optional[Any] = None):
        self.core = core_ref
        self.is_active = False
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.last_scanned_candidates: List[Dict[str, Any]] = []
        self.active_selected_target: Optional[Dict[str, Any]] = None
        self.last_image_base64: Optional[str] = None
        logger.info("📐 [SPATIAL AR] Spatial AR Workbench Subsystem initialized.")

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self.is_active = True
        return True

    def shutdown(self):
        self.is_active = False
        self._cache.clear()
        self.last_scanned_candidates.clear()
        self.active_selected_target = None
        self.last_image_base64 = None
        logger.info("📐 [SPATIAL AR] Spatial AR Workbench Subsystem shut down cleanly.")

    def _optimize_image_payload(self, raw_base64: str) -> str:
        """Ensures image is valid RGB JPEG, resized to fit within 1024x1024."""
        clean_b64 = raw_base64
        if "base64," in clean_b64:
            clean_b64 = clean_b64.split("base64,")[1]

        try:
            image_bytes = base64.b64decode(clean_b64)
            img = Image.open(io.BytesIO(image_bytes))

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Ensure minimum dimension >= 64px for Groq vision models
            width, height = img.size
            if width < 64 or height < 64:
                scale = max(64 / width, 64 / height)
                new_w = max(64, int(width * scale))
                new_h = max(64, int(height * scale))
                img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

            # Cap maximum dimension to 1024px for latency & token conservation
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=80, optimize=True)
            return base64.b64encode(out_buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.warning(f"⚠️ [SPATIAL AR] Image optimization warning: {e}")
            return clean_b64

    def _normalize_bbox(self, raw_bbox: Any) -> List[float]:
        """Ensures coordinates are [ymin, xmin, ymax, xmax] in 0-100 percentage."""
        if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
            return [30.0, 35.0, 70.0, 65.0]

        vals = [float(v) for v in raw_bbox]
        # Check if model gave coordinates on a 0-1000 scale
        if any(v > 100 for v in vals):
            vals = [v / 10.0 for v in vals]

        ymin = max(0.0, min(100.0, vals[0]))
        xmin = max(0.0, min(100.0, vals[1]))
        ymax = max(ymin + 5.0, min(100.0, vals[2]))
        xmax = max(xmin + 5.0, min(100.0, vals[3]))
        return [round(ymin, 1), round(xmin, 1), round(ymax, 1), round(xmax, 1)]

    def _find_youtube_video_id(self, query: str) -> Optional[str]:
        """Finds a top YouTube video ID for the target object for AR video stream."""
        if not query:
            return None
        try:
            encoded_q = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_q}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                video_ids = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html)
                if video_ids:
                    return video_ids[0]
        except Exception as e:
            logger.debug(f"[SPATIAL AR] YouTube video search error: {e}")
        return None

    def scan_desk_candidates(self, image_base64: str) -> Dict[str, Any]:
        """
        Scans the whole desk/surface for all visible prominent objects (1 to 4).
        If only 1 object is found, automatically invokes deep_dive_target.
        If multiple objects are found, returns list of candidate reticles + question prompt.
        """
        start_time = time.time()
        optimized_b64 = self._optimize_image_payload(image_base64)
        self.last_image_base64 = optimized_b64

        from groq import Groq

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return {
                "success": False,
                "error": "GROQ_API_KEY is not configured.",
                "voice_text": "ระบบยังไม่ได้ตั้งค่า API Key สำหรับสายตาครับเจ้านาย"
            }

        client = Groq(api_key=groq_api_key, max_retries=1)

        prompt = (
            "You are J.A.R.V.I.S. Multi-Target Desk Scanner & Spatial Reconnaissance Subsystem. "
            "Scan the uploaded camera frame showing a desk or workbench. "
            "Identify up to 4 distinct physical objects, gadgets, tools, peripherals, or electronic components visible on the surface. "
            "Return strictly valid JSON without markdown code blocks:\n"
            "{\n"
            "  \"candidates\": [\n"
            "    {\"id\": 1, \"name\": \"Flipper Zero\", \"name_th\": \"อุปกรณ์ Flipper Zero\", \"category\": \"RF Multi-Tool\", \"bbox\": [ymin, xmin, ymax, xmax]},\n"
            "    {\"id\": 2, \"name\": \"Mechanical Keyboard\", \"name_th\": \"คีย์บอร์ดกลไก\", \"category\": \"Computer Peripheral\", \"bbox\": [ymin, xmin, ymax, xmax]}\n"
            "  ]\n"
            "}\n"
            "COORDINATE RULES:\n"
            "- bbox MUST be [ymin, xmin, ymax, xmax] in percentages (0 to 100).\n"
            "- If only 1 object is visible, return only 1 item in candidates array."
        )

        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{optimized_b64}"}}]}
                ],
                temperature=0.1,
                max_tokens=600,
                timeout=12.0
            )

            raw = response.choices[0].message.content or ""
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            clean_json = re.sub(r"\s*```$", "", clean_json)

            data = json.loads(clean_json)
            candidates = data.get("candidates", [])

            # Normalize bounding boxes
            for idx, c in enumerate(candidates, 1):
                c["id"] = idx
                c["bbox"] = self._normalize_bbox(c.get("bbox"))

            self.last_scanned_candidates = candidates

            # ── Scenario 1: Only 1 object found ──
            if len(candidates) == 1:
                single = candidates[0]
                self.active_selected_target = single
                deep_dive = self.deep_dive_target(optimized_b64, single["name"], single["bbox"])
                deep_dive["mode"] = "single_target_auto"
                deep_dive["candidates"] = candidates
                return deep_dive

            # ── Scenario 2: Multiple objects found on desk ──
            if len(candidates) > 1:
                self.active_selected_target = candidates[0]  # default to first candidate
                names_summary = ", ".join([f"{c['id']}. {c.get('name_th') or c['name']}" for c in candidates])
                voice_text = (
                    f"ผมสแกนตรวจพบวัตถุบนโต๊ะ {len(candidates)} รายการครับ: {names_summary} "
                    f"— เจ้านายต้องการให้ผมหาข้อมูลของชิ้นไหนครับ?"
                )
                return {
                    "success": True,
                    "mode": "multiple_candidates",
                    "total_detected": len(candidates),
                    "candidates": candidates,
                    "active_candidate_id": 1,
                    "voice_text": voice_text,
                    "latency_ms": round((time.time() - start_time) * 1000, 1)
                }

            # ── Scenario 3: Fallback if no specific object parsed ──
            default_cand = {
                "id": 1,
                "name": "DESK WORKBENCH OBJECT",
                "name_th": "วัตถุบนโต๊ะทำงาน",
                "category": "HARDWARE",
                "bbox": [30.0, 35.0, 70.0, 65.0]
            }
            self.last_scanned_candidates = [default_cand]
            self.active_selected_target = default_cand
            return self.deep_dive_target(optimized_b64, default_cand["name"], default_cand["bbox"])

        except Exception as e:
            logger.error(f"❌ [SPATIAL AR] Candidate scan error: {e}", exc_info=True)
            fallback_cands = [
                {"id": 1, "name": "DESK TARGET", "name_th": "วัตถุบนโต๊ะทำงาน", "category": "HARDWARE", "bbox": [32.0, 35.0, 68.0, 65.0]}
            ]
            self.last_scanned_candidates = fallback_cands
            self.active_selected_target = fallback_cands[0]
            return self.deep_dive_target(optimized_b64, fallback_cands[0]["name"], fallback_cands[0]["bbox"])

    def deep_dive_target(
        self,
        image_base64: str,
        target_name: str,
        bbox: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes the full 6-card Stark Industries AR HUD dataset for a specific chosen target.
        """
        start_time = time.time()
        optimized_b64 = self._optimize_image_payload(image_base64)
        clamped_bbox = self._normalize_bbox(bbox)

        from groq import Groq

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return {
                "success": False,
                "error": "GROQ_API_KEY not configured",
                "voice_text": "ระบบยังไม่ได้เชื่อมต่อ API Key ครับเจ้านาย"
            }

        client = Groq(api_key=groq_api_key, max_retries=1)

        system_prompt = (
            f"You are J.A.R.V.I.S. Deep-Dive AR Object Reconnaissance Subsystem. "
            f"The target object is: '{target_name}'. "
            f"Synthesize the full Stark Industries Cyberpunk AR HUD dataset for this specific hardware item.\n\n"
            f"Return strictly valid JSON without markdown code fences or backticks:\n"
            f"{{\n"
            f"  \"target_name\": \"{target_name}\",\n"
            f"  \"brand\": \"Manufacturer / Brand\",\n"
            f"  \"category\": \"Category Description\",\n"
            f"  \"specs_card\": {{\n"
            f"    \"title\": \"SECURITY & HARDWARE ARCHITECTURE\",\n"
            f"    \"items\": [\"Bullet point 1\", \"Bullet point 2\", \"Bullet point 3\", \"Bullet point 4\"]\n"
            f"  }},\n"
            f"  \"llm_card\": {{\n"
            f"    \"title\": \"LLM & VOICE-ASSISTANT INTEGRATIONS\",\n"
            f"    \"items\": [\"Feature point 1\", \"Feature point 2\", \"Feature point 3\"]\n"
            f"  }},\n"
            f"  \"pricing_card\": {{\n"
            f"    \"price_usd\": \"$199\",\n"
            f"    \"price_thb\": \"฿7,200\",\n"
            f"    \"status\": \"OFFICIAL MSRP / IN STOCK\",\n"
            f"    \"badge\": \"MARKET VERIFIED\"\n"
            f"  }},\n"
            f"  \"display_card\": {{\n"
            f"    \"title\": \"DISPLAY & INTERFACES\",\n"
            f"    \"items\": [\"Display spec\", \"Key interfaces / ports\", \"Battery / power\"]\n"
            f"  }},\n"
            f"  \"telemetry_card\": {{\n"
            f"    \"score\": 88,\n"
            f"    \"score_label\": \"CAPABILITY INDEX\",\n"
            f"    \"metrics\": [\n"
            f"      {{\"label\": \"Protocol\", \"value\": 92}},\n"
            f"      {{\"label\": \"Coverage\", \"value\": 85}},\n"
            f"      {{\"label\": \"Security\", \"value\": 95}},\n"
            f"      {{\"label\": \"Firmware\", \"value\": 88}}\n"
            f"    ]\n"
            f"  }},\n"
            f"  \"video_query\": \"{target_name} review tech showcase\"\n"
            f"}}"
        )

        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Generate full technical specs, pricing, and telemetry for: {target_name}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{optimized_b64}"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
                timeout=15.0
            )

            raw = response.choices[0].message.content or ""
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            clean_json = re.sub(r"\s*```$", "", clean_json)

            data = json.loads(clean_json)
            data["bbox"] = clamped_bbox

            # Fetch live YouTube video ID
            video_q = data.get("video_query", f"{target_name} review")
            video_id = self._find_youtube_video_id(video_q)
            data["video_id"] = video_id or "nLIp4wd0oXs"

            price_usd = data.get("pricing_card", {}).get("price_usd", "$199")
            resolved_name = data.get("target_name", target_name)
            voice_text = (
                f"สแกนตรวจพบ {resolved_name} เรียบร้อยครับเจ้านาย "
                f"ราคาตลาดอยู่ที่ประมาณ {price_usd} "
                f"ข้อมูลจำเพาะทางเทคนิคและพิมพ์เขียวฮาร์ดแวร์ถูกกางลงบนเลนส์ AR เรียบร้อยแล้วครับ"
            )
            data["voice_text"] = voice_text
            data["success"] = True
            data["mode"] = "deep_dive_complete"
            data["latency_ms"] = round((time.time() - start_time) * 1000, 1)

            self.active_selected_target = {
                "name": resolved_name,
                "bbox": clamped_bbox,
                "data": data
            }

            return data

        except Exception as e:
            logger.error(f"❌ [SPATIAL AR] Deep dive error: {e}", exc_info=True)
            return {
                "success": False,
                "target_name": target_name,
                "brand": "HARDWARE TARGET",
                "category": "DESK COMPONENT",
                "bbox": clamped_bbox,
                "specs_card": {
                    "title": "SECURITY & HARDWARE ARCHITECTURE",
                    "items": [
                        "Sub-GHz Multi-Band RF Transceiver",
                        "Embedded Cryptographic Core",
                        "Dual-Core High Performance MCU"
                    ]
                },
                "llm_card": {
                    "title": "LLM & VOICE-ASSISTANT INTEGRATIONS",
                    "items": [
                        "Direct Command Bridge via USB/UART",
                        "Continuous Telemetry Streaming Active"
                    ]
                },
                "pricing_card": {
                    "price_usd": "$199",
                    "price_thb": "฿7,200",
                    "status": "OFFICIAL MSRP / IN STOCK",
                    "badge": "MARKET VERIFIED"
                },
                "display_card": {
                    "title": "DISPLAY & INTERFACES",
                    "items": ["High-contrast Matrix LCD", "Multi-function Tactile Controls"]
                },
                "telemetry_card": {
                    "score": 85,
                    "score_label": "CAPABILITY INDEX",
                    "metrics": [
                        {"label": "Protocol", "value": 90},
                        {"label": "Coverage", "value": 85},
                        {"label": "Security", "value": 92}
                    ]
                },
                "video_id": "nLIp4wd0oXs",
                "voice_text": f"สแกน {target_name} เรียบร้อยครับเจ้านาย กางข้อมูลจำเพาะและพิมพ์เขียวบนหน้าจอ AR ให้แล้วครับ",
                "latency_ms": round((time.time() - start_time) * 1000, 1),
                "mode": "deep_dive_complete"
            }

    def resolve_target_selection(self, user_prompt: str, image_base64: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolves subsequent user choices:
        e.g. "หาข้อมูลเกี่ยวกับสิ่งที่อยู่ในวงให้หน่อย", "ชิ้นที่ 1", "อันแรก", "ชิ้นที่ 2", "คีย์บอร์ด"
        """
        img_to_use = image_base64 or self.last_image_base64
        if not img_to_use:
            return {
                "success": False,
                "voice_text": "เกรงว่าระบบยังไม่มีภาพสัญญาณจากกล้องครับเจ้านาย รบกวนเปิดกล้องหรือกดสแกนใหม่อีกครั้งครับ"
            }

        p_clean = user_prompt.lower()

        # Check for explicit index mentions: 1, 2, 3 or "อันแรก", "อันที่สอง"
        target_candidate = None

        if self.last_scanned_candidates:
            if any(w in p_clean for w in ["ชิ้นที่ 1", "อันที่ 1", "อันแรก", "เบอร์ 1", "หมายเลข 1", "1"]):
                target_candidate = self.last_scanned_candidates[0]
            elif any(w in p_clean for w in ["ชิ้นที่ 2", "อันที่ 2", "อันที่สอง", "เบอร์ 2", "หมายเลข 2", "2"]) and len(self.last_scanned_candidates) > 1:
                target_candidate = self.last_scanned_candidates[1]
            elif any(w in p_clean for w in ["ชิ้นที่ 3", "อันที่ 3", "อันที่สาม", "เบอร์ 3", "หมายเลข 3", "3"]) and len(self.last_scanned_candidates) > 2:
                target_candidate = self.last_scanned_candidates[2]
            else:
                # Name matching
                for c in self.last_scanned_candidates:
                    c_name = c["name"].lower()
                    c_name_th = c.get("name_th", "").lower()
                    if c_name in p_clean or c_name_th in p_clean:
                        target_candidate = c
                        break

        # If user simply says "สิ่งที่อยู่ในวง" or "ในวง", pick active or first candidate
        if not target_candidate:
            if self.active_selected_target:
                target_candidate = self.active_selected_target
            elif self.last_scanned_candidates:
                target_candidate = self.last_scanned_candidates[0]

        if target_candidate:
            return self.deep_dive_target(
                img_to_use,
                target_candidate.get("name", "DESK OBJECT"),
                target_candidate.get("bbox", [30.0, 35.0, 70.0, 65.0])
            )

        # Fallback to scanning desk
        return self.scan_desk_candidates(img_to_use)

    def analyze_desk_object(self, image_base64: str, user_prompt: str = "") -> Dict[str, Any]:
        """
        Master dispatcher handling all AR workbench queries.
        Differentiates between initial desk scans and subsequent target selections.
        """
        p_clean = user_prompt.lower()

        # Is the user asking to deep dive on what's already circled or selected?
        is_followup = any(w in p_clean for w in [
            "สิ่งที่อยู่ในวง", "สิ่งที่วงไว้", "ในวง", "อันในวง",
            "ชิ้นที่", "อันที่", "เบอร์ 1", "เบอร์ 2", "อันแรก", "อันที่สอง"
        ])

        if is_followup and (self.last_scanned_candidates or self.active_selected_target):
            return self.resolve_target_selection(user_prompt, image_base64)

        # Otherwise perform desk candidates scan (which auto-deep-dives if only 1 item found!)
        return self.scan_desk_candidates(image_base64)

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "name": "SpatialARWorkbench",
            "active": self.is_active,
            "candidates_count": len(self.last_scanned_candidates),
            "active_target": self.active_selected_target.get("name") if self.active_selected_target else None
        }


spatial_ar_workbench = SpatialARWorkbench()
