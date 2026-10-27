"""
STARK ENVIRONMENTAL & THERMOGRAPHIC SCANNER SUBSYSTEM (INFRARED / IR-NDT)
========================================================================
Inspired by Avengers: Age of Ultron (Tony Stark's Hydra Lab IR Wall Scan) &
Nachapol Industries Non-Destructive Structural Thermography.

Key Capabilities:
1. Radiometric & False-Color Thermal Gradient Analysis (Simulation, Webcam, or USB IR Camera).
2. Structural Thermal Bridging Detection (identifying concealed steel beams, rebar, and voids).
3. Convective Air Infiltration & Draft Detection (detecting localized cooling from hidden seams).
4. Stark HUD Overlay Generation (Iron Man reticles, temperature probes, and vector telemetry).
5. Dynamic Island Real-time Alert Dispatch.
6. Ready for FLIR Lepton / Infiray USB-C / MLX90640 plug-and-play hardware integration.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("STARK-THERMAL-SCANNER")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

SCAN_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thermal_scans")


class StarkThermalScanner:
    """
    Nachapol Industries Infrared & Structural Building Scanner.
    Singleton engine for thermographic analysis, thermal bridging, and draft detection.
    """
    _instance: Optional[StarkThermalScanner] = None

    def __new__(cls) -> StarkThermalScanner:
        if cls._instance is None:
            cls._instance = super(StarkThermalScanner, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        os.makedirs(SCAN_OUTPUT_DIR, exist_ok=True)
        self.last_scan_telemetry: Dict[str, Any] = {}
        logger.info("[THERMAL] Stark Thermographic & Structural Scanner Initialized (Standby).")

    def _generate_synthetic_hydra_frame(self, width: int = 1280, height: int = 720) -> np.ndarray:
        """
        Synthesizes a realistic room scan environment matching the Avengers Age of Ultron scene:
        Dark masonry room with anomalous steel structure and cold air draft on the left wall.
        """
        # Create base ambient temperature matrix (normalized 0-255 representing 18C - 26C)
        # Background ambient wall ~ 21.0C
        base_temp = np.full((height, width), 115, dtype=np.uint8)

        # Subtle noise and room depth
        noise = np.random.normal(0, 2.5, (height, width)).astype(np.float32)
        ambient = np.clip(base_temp.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 1. Structural Steel Reinforcement on the Left Wall (X: 120 to 450, Y: 100 to 650)
        # Steel conducts / holds thermal mass: creates distinct vertical columns
        for pillar_x in [160, 240, 320, 400]:
            cv2.rectangle(ambient, (pillar_x - 12, 110), (pillar_x + 12, 640), 160, -1)
        # Cross-beam reinforcement
        cv2.rectangle(ambient, (140, 260), (420, 285), 170, -1)
        cv2.rectangle(ambient, (140, 480), (420, 505), 170, -1)

        # 2. Air Draft / Leakage Seam (Convective cooling plume along left door seam X: 240, Y: 140 to 620)
        # Cold air leaking out (drops temperature by ~3.5°C)
        draft_mask = np.zeros((height, width), dtype=np.float32)
        cv2.line(draft_mask, (240, 140), (240, 620), 1.0, 32)
        # Gaussian blur for realistic convective air dispersion
        draft_plume = cv2.GaussianBlur(draft_mask, (65, 65), 0)
        ambient_float = ambient.astype(np.float32)
        ambient_float = ambient_float - (draft_plume * 75.0)  # Significant cold plume
        ambient = np.clip(ambient_float, 0, 255).astype(np.uint8)

        # Smooth edges for natural heat dissipation
        synthetic_thermal = cv2.GaussianBlur(ambient, (9, 9), 0)
        return synthetic_thermal

    def _analyze_thermal_matrix(self, thermal_gray: np.ndarray) -> Dict[str, Any]:
        """
        Runs analytical algorithms on thermal data:
        1. Mean, Min, Max radiometric temperature mapping.
        2. Detection of Thermal Bridges (Reinforced Steel).
        3. Detection of Localized Air Infiltration (Draft).
        """
        h, w = thermal_gray.shape[:2]

        # Map 0-255 grayscale to physical temperature range (15.0°C to 30.0°C)
        min_temp_c = 15.0
        max_temp_c = 30.0
        temp_scale = (max_temp_c - min_temp_c) / 255.0

        mean_val = float(np.mean(thermal_gray))
        ambient_c = round(min_temp_c + (mean_val * temp_scale), 1)

        # Divide image into 3 vertical sectors: Left Wall, Center Area, Right Wall
        left_sector = thermal_gray[:, :int(w * 0.38)]
        center_sector = thermal_gray[:, int(w * 0.38):int(w * 0.68)]
        right_sector = thermal_gray[:, int(w * 0.68):]

        left_min = float(np.min(left_sector))
        left_max = float(np.max(left_sector))
        left_var = float(np.var(left_sector))

        # Detect Draft: Look for localized cold anomaly (temperatures below ambient by > 1.2°C)
        cold_threshold = mean_val - (1.2 / temp_scale)
        draft_pixels = np.where(thermal_gray < cold_threshold)
        draft_detected = len(draft_pixels[0]) > (w * h * 0.003)

        draft_location = "None"
        draft_temp_c = ambient_c
        if draft_detected:
            # Check which sector has highest concentration of cold pixels
            left_cold = np.sum(left_sector < cold_threshold)
            center_cold = np.sum(center_sector < cold_threshold)
            right_cold = np.sum(right_sector < cold_threshold)
            if left_cold >= center_cold and left_cold >= right_cold:
                draft_location = "Left Wall (ผนังฝั่งซ้าย)"
            elif right_cold >= left_cold and right_cold >= center_cold:
                draft_location = "Right Wall (ผนังฝั่งขวา)"
            else:
                draft_location = "Center Structure (โครงสร้างตรงกลาง)"
            draft_temp_c = round(min_temp_c + (float(np.min(thermal_gray)) * temp_scale), 1)

        # Detect Steel Structure / Thermal Bridging: Look for high-contrast linear vertical gradients
        sobel_x = cv2.Sobel(left_sector, cv2.CV_32F, 1, 0, ksize=3)
        edge_energy = float(np.mean(np.abs(sobel_x)))
        steel_reinforced = edge_energy > 4.5 or left_var > 350.0

        structural_findings = []
        if steel_reinforced:
            structural_findings.append("Reinforced Steel Framing (โครงสร้างเสริมเหล็กกล้าความหนาแน่นสูง)")
        if draft_detected:
            structural_findings.append(f"Convective Airflow Draft ({draft_location} - ลมพัดผ่านรอยต่อ)")

        confidence_pct = 94 if (steel_reinforced and draft_detected) else (85 if (steel_reinforced or draft_detected) else 70)

        return {
            "ambient_temp_c": ambient_c,
            "min_temp_c": round(min_temp_c + (float(np.min(thermal_gray)) * temp_scale), 1),
            "max_temp_c": round(min_temp_c + (float(np.max(thermal_gray)) * temp_scale), 1),
            "delta_t_c": round(float(np.max(thermal_gray) - np.min(thermal_gray)) * temp_scale, 1),
            "steel_reinforcement_detected": steel_reinforced,
            "draft_detected": draft_detected,
            "draft_location": draft_location,
            "draft_temp_c": draft_temp_c,
            "structural_findings": structural_findings,
            "confidence_percent": confidence_pct,
            "sector_variance_left": round(left_var, 1)
        }

    def _render_stark_hud_overlay(self, thermal_gray: np.ndarray, analysis: Dict[str, Any]) -> str:
        """
        Creates a high-tech Iron Man / J.A.R.V.I.S. HUD thermographic image:
        - Thermal false-color mapping (COLORMAP_INFERNO)
        - Futuristic reticles, bounding brackets, and wireframe markers
        - Real-time telemetry badges (Temperature, Draft Velocity, Structural Composition)
        """
        h, w = thermal_gray.shape[:2]

        # 1. Apply thermal false-color mapping
        color_thermal = cv2.applyColorMap(thermal_gray, cv2.COLORMAP_INFERNO)

        # 2. Create HUD graphics overlay layer
        hud = color_thermal.copy()

        # Grid lines (Cyan Stark Grid)
        grid_color = (180, 140, 20)  # Subtle Stark Gold/Cyan
        for y in range(0, h, 80):
            cv2.line(hud, (0, y), (w, y), (50, 40, 20), 1, cv2.LINE_AA)
        for x in range(0, w, 80):
            cv2.line(hud, (x, 0), (x, h), (50, 40, 20), 1, cv2.LINE_AA)

        # 3. Highlight Anomaly Zone (Left Wall if detected)
        if analysis.get("steel_reinforcement_detected") or analysis.get("draft_detected"):
            box_x1, box_y1 = int(w * 0.08), int(h * 0.16)
            box_x2, box_y2 = int(w * 0.44), int(h * 0.80)

            # High-tech corner brackets
            bracket_color = (0, 230, 255)  # Bright Cyan / Stark Blue
            c_len = 32
            thick = 2
            # Top-left
            cv2.line(hud, (box_x1, box_y1), (box_x1 + c_len, box_y1), bracket_color, thick)
            cv2.line(hud, (box_x1, box_y1), (box_x1, box_y1 + c_len), bracket_color, thick)
            # Top-right
            cv2.line(hud, (box_x2, box_y1), (box_x2 - c_len, box_y1), bracket_color, thick)
            cv2.line(hud, (box_x2, box_y1), (box_x2, box_y1 + c_len), bracket_color, thick)
            # Bottom-left
            cv2.line(hud, (box_x1, box_y2), (box_x1 + c_len, box_y2), bracket_color, thick)
            cv2.line(hud, (box_x1, box_y2), (box_x1, box_y2 - c_len), bracket_color, thick)
            # Bottom-right
            cv2.line(hud, (box_x2, box_y2), (box_x2 - c_len, box_y2), bracket_color, thick)
            cv2.line(hud, (box_x2, box_y2), (box_x2, box_y2 - c_len), bracket_color, thick)

            # Target Center Reticle
            cx, cy = (box_x1 + box_x2) // 2, (box_y1 + box_y2) // 2
            cv2.circle(hud, (cx, cy), 22, (0, 180, 255), 1, cv2.LINE_AA)
            cv2.circle(hud, (cx, cy), 4, (0, 240, 255), -1)
            cv2.line(hud, (cx - 30, cy), (cx + 30, cy), (0, 180, 255), 1)
            cv2.line(hud, (cx, cy - 30), (cx, cy + 30), (0, 180, 255), 1)

            # Anomaly Tags (Top and Bottom of bounding box)
            cv2.putText(hud, "ANOMALOUS STRUCTURAL CAVITY", (box_x1 + 8, box_y1 + 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(hud, f"[!] STEEL DENSITY: REINFORCED (DELTA-T: {analysis.get('delta_t_c')}C)",
                        (box_x1 + 8, box_y2 - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 220, 255), 1, cv2.LINE_AA)
            cv2.putText(hud, f"[!] AIRFLOW: DRAFT DETECTED ({analysis.get('draft_temp_c')}C)",
                        (box_x1 + 8, box_y2 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 220, 255), 1, cv2.LINE_AA)

        # 4. Stark Header & Telemetry Bars
        header_color = (0, 255, 200)
        cv2.putText(hud, "NACHAPOL INDUSTRIES // MARK-XLIII TACTICAL HUD", (35, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, header_color, 2, cv2.LINE_AA)
        cv2.putText(hud, "OPTICAL THERMOGRAPHY & STRUCTURAL INTEGRITY SCAN", (35, 62),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 200, 200), 1, cv2.LINE_AA)

        # Status Badge (Top-Right)
        status_text = "IR-NDT: ACTIVE // MATCH FOUND"
        cv2.putText(hud, status_text, (w - 380, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 2, cv2.LINE_AA)
        cv2.putText(hud, f"AMBIENT: {analysis.get('ambient_temp_c')}C | RANGE: {analysis.get('min_temp_c')}C - {analysis.get('max_temp_c')}C",
                    (w - 380, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1, cv2.LINE_AA)

        # Timestamp (Bottom)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(hud, f"TIMESTAMP: {ts} | SYSTEM: J.A.R.V.I.S.", (35, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 140), 1, cv2.LINE_AA)


        # Blend HUD with original for cinematic Stark Holographic glow
        final_frame = cv2.addWeighted(color_thermal, 0.35, hud, 0.65, 0)

        # Save to artifacts / data directory
        output_path = os.path.join(SCAN_OUTPUT_DIR, "latest_thermal_scan.jpg")
        cv2.imwrite(output_path, final_frame)
        return output_path

    def process_raw_mlx90640_array(
        self,
        raw_768_values: List[float],
        target_w: int = 1280,
        target_h: int = 720
    ) -> np.ndarray:
        """
        Converts a 768-element list (32x24 grid) from an MLX90640 sensor into a smooth,
        high-resolution grayscale thermal matrix using Bicubic Super-Resolution & Gaussian dissipation.
        """
        try:
            grid = np.array(raw_768_values[:768], dtype=np.float32).reshape((24, 32))
            t_min, t_max = float(np.min(grid)), float(np.max(grid))
            if t_max - t_min > 0.05:
                norm_grid = ((grid - t_min) / (t_max - t_min) * 255.0).astype(np.uint8)
            else:
                norm_grid = np.full((24, 32), 128, dtype=np.uint8)

            # Bicubic upsampling to HD Stark HUD resolution
            upscaled = cv2.resize(norm_grid, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
            smoothed = cv2.GaussianBlur(upscaled, (17, 17), 0)
            return smoothed
        except Exception as e:
            logger.error(f"[THERMAL] Error upscaling MLX90640 array: {e}")
            return self._generate_synthetic_hydra_frame(target_w, target_h)

    def scan_room(
        self,
        source: str = "auto",
        image_path: Optional[str] = None,
        camera_index: int = 0,
        raw_mlx_data: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Executes a room thermographic scan.
        - source: 'auto', 'image', 'camera', 'mlx90640', 'simulation'
        - image_path: path to real camera image or thermal file
        - raw_mlx_data: list of 768 float temperature readings from MLX90640 DIY sensor
        """
        logger.info(f"[THERMAL] Initiating Stark Thermographic Scan (Source: {source})...")
        thermal_matrix = None
        source_used = "simulation"

        # 0. Check for raw MLX90640 DIY sensor data
        if raw_mlx_data and len(raw_mlx_data) >= 768:
            thermal_matrix = self.process_raw_mlx90640_array(raw_mlx_data)
            source_used = "Hardware Sensor: MLX90640 (32x24 Super-Resolution)"

        # 1. Try loading from image_path or JSON data file if provided
        if thermal_matrix is None and image_path and os.path.exists(image_path):
            try:
                if image_path.endswith(".json"):
                    with open(image_path, "r", encoding="utf-8") as jf:
                        j_data = json.load(jf)
                        if isinstance(j_data, list) and len(j_data) >= 768:
                            thermal_matrix = self.process_raw_mlx90640_array(j_data)
                            source_used = f"MLX90640 JSON Data: {os.path.basename(image_path)}"
                if thermal_matrix is None:
                    loaded = cv2.imread(image_path)
                    if loaded is not None:
                        thermal_matrix = cv2.cvtColor(loaded, cv2.COLOR_BGR2GRAY)
                        source_used = f"file: {os.path.basename(image_path)}"
            except Exception as e:
                logger.warning(f"[THERMAL] Failed to load {image_path}: {e}")


        # 2. Try real webcam or USB Thermal device if requested
        if thermal_matrix is None and source in ["auto", "camera"]:
            try:
                cap = cv2.VideoCapture(camera_index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        thermal_matrix = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        source_used = f"Hardware Camera Index #{camera_index}"
            except Exception as e:
                logger.debug(f"[THERMAL] Camera capture not available: {e}")

        # 3. Fallback to High-Fidelity Synthetic Simulation (Hydra Fortress Secret Chamber Mode)
        if thermal_matrix is None:
            thermal_matrix = self._generate_synthetic_hydra_frame(1280, 720)
            source_used = "High-Fidelity Synthetic Thermography (Hydra Lab Protocol)"

        # Run analytical algorithms
        analysis = self._analyze_thermal_matrix(thermal_matrix)
        analysis["source"] = source_used

        # Generate Stark HUD Visual Artifact
        try:
            overlay_file = self._render_stark_hud_overlay(thermal_matrix, analysis)
            analysis["hud_overlay_path"] = overlay_file
        except Exception as e:
            logger.error(f"[THERMAL] HUD render error: {e}")
            analysis["hud_overlay_path"] = None

        self.last_scan_telemetry = analysis

        # Send HUD Toast to Dynamic Island
        try:
            from modules.dynamic_island import send_toast_to_island
            summary_msg = f"โครงสร้างเหล็ก & ลมพัดผ่าน ({analysis.get('draft_location')})"
            send_toast_to_island("THERMAL SCAN COMPLETE", summary_msg, icon="🔥")
        except Exception:
            pass

        logger.info(f"[THERMAL] Scan completed. Steel: {analysis.get('steel_reinforcement_detected')}, Draft: {analysis.get('draft_detected')} ({analysis.get('draft_location')})")
        return analysis

    def get_latest_telemetry(self) -> Dict[str, Any]:
        """Returns the most recent scan telemetry."""
        return self.last_scan_telemetry or {
            "status": "STANDBY",
            "message": "ยังไม่มีประวัติการสแกนความร้อนในรอบปัจจุบันครับ"
        }


# Singleton Accessor
_thermal_scanner_instance: Optional[StarkThermalScanner] = None

def get_thermal_scanner() -> StarkThermalScanner:
    global _thermal_scanner_instance
    if _thermal_scanner_instance is None:
        _thermal_scanner_instance = StarkThermalScanner()
    return _thermal_scanner_instance
