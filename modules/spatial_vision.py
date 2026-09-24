"""
spatial_vision.py
Module 2: Advanced Spatial Vision & Defect Inspector

Responsible for processing images to detect engineering defects (like PCB burns or short circuits)
and mapping 2D image coordinates to 3D spatial references.
"""

import logging
import math
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

# Setup Module Logger
logger = logging.getLogger("SpatialVision")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class VisionException(Exception):
    """Base exception for the Spatial Vision module."""
    pass


class ImageProcessingError(VisionException):
    """Raised when an image cannot be processed or is corrupted."""
    pass


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Point3D:
    x: float
    y: float
    z: float


# --- Strategy Pattern for Inspection Algorithms ---
class BaseInspectionStrategy(ABC):
    """Abstract Strategy for defect inspection algorithms."""
    
    @abstractmethod
    def inspect(self, image_data: Any) -> Dict[str, Any]:
        """Runs the inspection algorithm on the provided image data."""
        pass


class BurnMarkDetector(BaseInspectionStrategy):
    """Strategy to detect burn marks on a PCB surface."""
    
    def inspect(self, image_data: Any) -> Dict[str, Any]:
        logger.info("Running BurnMarkDetector strategy...")
        # Simulated logic: In reality, we'd use cv2 to threshold dark/carbon regions
        has_burn = True if image_data == "simulated_burned_image" else False
        return {
            "defect_type": "BURN_MARK",
            "detected": has_burn,
            "confidence": 0.85 if has_burn else 0.0
        }


class ShortCircuitDetector(BaseInspectionStrategy):
    """Strategy to detect solder bridges causing short circuits."""
    
    def inspect(self, image_data: Any) -> Dict[str, Any]:
        logger.info("Running ShortCircuitDetector strategy...")
        # Simulated logic
        has_short = False
        return {
            "defect_type": "SHORT_CIRCUIT",
            "detected": has_short,
            "confidence": 0.0
        }


class PCBDefectInspector:
    """
    Main class that orchestrates different inspection strategies to analyze a PCB image.
    Uses Dependency Injection to accept specific inspection strategies.
    """
    
    def __init__(self, strategies: List[BaseInspectionStrategy] = None):
        self.strategies = strategies or []
        
    def add_strategy(self, strategy: BaseInspectionStrategy):
        self.strategies.append(strategy)
        
    def analyze_image(self, image_path: str) -> List[Dict[str, Any]]:
        logger.info(f"Analyzing image: {image_path}")
        
        # Simulate image loading
        simulated_image_data = "simulated_burned_image" if "burn" in image_path.lower() else "clean_image"
        
        results = []
        for strategy in self.strategies:
            res = strategy.inspect(simulated_image_data)
            results.append(res)
            
        return results


class SpatialCoordinateMapper:
    """
    Calculates and maps 2D camera coordinates (pixels) into real-world 3D spatial coordinates.
    """
    
    def __init__(self, focal_length_mm: float, sensor_width_mm: float, image_width_px: int, camera_height_mm: float):
        self.focal_length = focal_length_mm
        self.sensor_width = sensor_width_mm
        self.image_width = image_width_px
        self.camera_height = camera_height_mm  # Distance from camera to object plane (Z axis)
        
    def map_2d_to_3d(self, pixel: Point2D) -> Point3D:
        """
        Converts a 2D pixel coordinate to a 3D coordinate on a flat plane.
        Uses simple pinhole camera model mapping.
        """
        logger.debug(f"Mapping pixel ({pixel.x}, {pixel.y}) to 3D space...")
        
        # Calculate real-world width covered by the camera
        real_world_width_mm = (self.sensor_width * self.camera_height) / self.focal_length
        mm_per_pixel = real_world_width_mm / self.image_width
        
        # Assuming the camera is centered directly above (0, 0)
        center_x_px = self.image_width / 2.0
        # For simplicity, assuming a square aspect ratio or just 1D center offset
        center_y_px = self.image_width / 2.0 
        
        real_x = (pixel.x - center_x_px) * mm_per_pixel
        real_y = (pixel.y - center_y_px) * mm_per_pixel
        
        return Point3D(real_x, real_y, 0.0)


if __name__ == "__main__":
    logger.info("--- Testing PCBDefectInspector ---")
    inspector = PCBDefectInspector()
    inspector.add_strategy(BurnMarkDetector())
    inspector.add_strategy(ShortCircuitDetector())
    
    # Test with a dirty image
    report = inspector.analyze_image("pcb_burn_sample_01.jpg")
    for r in report:
        logger.info(f"Defect Result: {r}")
        
    logger.info("\\n--- Testing SpatialCoordinateMapper ---")
    # Camera spec: 50mm lens, 36mm sensor width, 1920px image width, 1000mm height
    mapper = SpatialCoordinateMapper(focal_length_mm=50.0, sensor_width_mm=36.0, image_width_px=1920, camera_height_mm=1000.0)
    
    # Map a pixel near the edge
    pixel_coord = Point2D(x=1920, y=960)
    spatial_coord = mapper.map_2d_to_3d(pixel_coord)
    
    logger.info(f"Pixel {pixel_coord} maps to 3D Coordinates: ({spatial_coord.x:.2f}mm, {spatial_coord.y:.2f}mm, {spatial_coord.z}mm)")
