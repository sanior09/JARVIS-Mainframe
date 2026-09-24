"""
gui_operator.py
Module 3: Autonomous GUI & OS Operator

Responsible for bridging the gap between Computer Vision and Robotic Process Automation (RPA).
Parses visual elements on the screen and accurately executes human-like interactions (mouse, keyboard).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

# Setup Module Logger
logger = logging.getLogger("GUIOperator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class GUIOperatorException(Exception):
    """Base exception for the GUI Operator module."""
    pass


@dataclass
class UIElement:
    """Represents a discovered UI element on the screen."""
    element_id: str
    label: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # xmin, ymin, xmax, ymax

    @property
    def center_coordinates(self) -> Tuple[int, int]:
        """Calculates the center (x, y) of the bounding box for clicking."""
        xmin, ymin, xmax, ymax = self.bounding_box
        return (xmin + xmax) // 2, (ymin + ymax) // 2


class ScreenContextParser:
    """
    Parses visual context from screen captures.
    In a real-world scenario, this would interface with an Object Detection model
    (e.g., YOLO, Llama Vision) or OCR (Tesseract).
    """
    
    def __init__(self):
        # Mocking an internal state representing the current screen
        self.last_parsed_elements: List[UIElement] = []

    async def parse_screen(self, image_data: Any) -> List[UIElement]:
        """
        Analyzes the image data and extracts UI elements.
        """
        logger.info("Parsing screen context for UI elements...")
        await asyncio.sleep(0.2) # Simulate model inference time
        
        # Mock detection results
        self.last_parsed_elements = [
            UIElement("btn_01", "Submit", 0.95, (100, 200, 150, 220)),
            UIElement("txt_01", "Search Bar", 0.88, (300, 50, 500, 80)),
            UIElement("icon_01", "Close", 0.99, (1800, 10, 1820, 30))
        ]
        
        logger.info(f"Found {len(self.last_parsed_elements)} interactive elements.")
        return self.last_parsed_elements

    def find_element_by_label(self, label: str) -> Optional[UIElement]:
        """Searches previously parsed elements for a specific label."""
        for el in self.last_parsed_elements:
            if label.lower() in el.label.lower():
                return el
        return None


class SystemActionExecutor:
    """
    Executes actions on the operating system, specifically targeting coordinates
    provided by the ScreenContextParser.
    """
    
    def __init__(self, use_human_delay: bool = True):
        self.use_human_delay = use_human_delay
        # In a real environment, we would import pyautogui or pynput here.
        # import pyautogui
        # self.mouse = pyautogui

    async def _human_delay(self):
        """Simulates natural human reaction time between actions."""
        if self.use_human_delay:
            import random
            await asyncio.sleep(random.uniform(0.1, 0.5))

    async def move_mouse_and_click(self, x: int, y: int, clicks: int = 1):
        """Moves the cursor to the coordinate and clicks."""
        logger.info(f"Moving mouse to ({x}, {y})")
        await self._human_delay()
        # Simulated action: pyautogui.moveTo(x, y, duration=0.2)
        
        logger.info(f"Clicking {clicks} time(s) at ({x}, {y})")
        await self._human_delay()
        # Simulated action: pyautogui.click(clicks=clicks)

    async def type_text(self, text: str, press_enter: bool = False):
        """Types out a string of text on the keyboard."""
        logger.info(f"Typing text: '{text}'")
        await self._human_delay()
        # Simulated action: pyautogui.write(text, interval=0.05)
        
        if press_enter:
            logger.info("Pressing 'Enter'")
            await self._human_delay()
            # Simulated action: pyautogui.press('enter')

    async def execute_element_interaction(self, element: UIElement, action: str, **kwargs):
        """High-level method to interact with a specific UI element."""
        cx, cy = element.center_coordinates
        
        if action == "click":
            await self.move_mouse_and_click(cx, cy)
        elif action == "type":
            await self.move_mouse_and_click(cx, cy)
            text = kwargs.get("text", "")
            await self.type_text(text, press_enter=kwargs.get("press_enter", False))
        else:
            raise GUIOperatorException(f"Unsupported action: {action}")


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing Autonomous GUI & OS Operator ---")
        
        parser = ScreenContextParser()
        executor = SystemActionExecutor()
        
        # 1. Parse the screen
        dummy_image = "binary_image_data"
        elements = await parser.parse_screen(dummy_image)
        
        # 2. Find target element
        target = parser.find_element_by_label("Search Bar")
        if target:
            logger.info(f"Target found: {target.label} at center {target.center_coordinates}")
            
            # 3. Execute interaction
            await executor.execute_element_interaction(
                element=target, 
                action="type", 
                text="How to build an arc reactor",
                press_enter=True
            )
        else:
            logger.warning("Target element not found on screen.")
            
    asyncio.run(run_tests())
