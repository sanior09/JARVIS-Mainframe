"""
intent_predictor.py
Module 1: Streaming Intent Predictor

Analyzes streaming input (text or tokenized speech) in real-time to predict 
the user's intent before they finish speaking, allowing for preemptive task execution.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable

# Setup Module Logger
logger = logging.getLogger("IntentPredictor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class PredictorException(Exception):
    """Base exception for the Intent Predictor module."""
    pass


@dataclass
class IntentPrediction:
    """Represents a predicted intent and its confidence score."""
    predicted_action: str
    confidence: float
    trigger_threshold: float = 0.8


class StreamIntentAnalyzer:
    """
    Analyzes a stream of text characters/words to predict intent early.
    In production, this could use a fast, lightweight n-gram model or local LLM.
    """
    
    def __init__(self):
        # Heuristic vocabulary mapping partial phrases to intended actions
        self._knowledge_base = {
            "เปิดไฟใ": "turn_on_room_lights",
            "ปิดไฟ": "turn_off_lights",
            "เปิดพัด": "turn_on_fan",
            "รันโค้ด": "execute_code_sandbox",
            "ลบไฟ": "delete_file_warning",
            "สแกนไวร": "run_antivirus_scan"
        }

    async def analyze_stream(self, text_buffer: str) -> Optional[IntentPrediction]:
        """
        Evaluates the current text buffer to predict an intent.
        Returns an IntentPrediction if a pattern is matched.
        """
        logger.debug(f"Analyzing buffer: '{text_buffer}'")
        # Simulate minor processing delay
        await asyncio.sleep(0.01)
        
        # Simple heuristic matching
        for pattern, action in self._knowledge_base.items():
            if pattern in text_buffer:
                # Calculate confidence based on how much of the pattern is matched vs buffer length
                # For this stub, if it exactly matches our trigger substring, confidence is high
                confidence = 0.85
                if text_buffer.endswith(pattern):
                    confidence = 0.95
                    
                return IntentPrediction(predicted_action=action, confidence=confidence)
                
        return None


class PreemptiveTaskTrigger:
    """
    Acts upon predictions by waking up target modules or preparing resources
    in the background before the final confirmation is received.
    """
    
    def __init__(self):
        self._active_preemptive_tasks: Dict[str, asyncio.Task] = {}
        
    async def _mock_resource_wakeup(self, action: str):
        """Simulates waking up a hardware resource or loading a large model into VRAM."""
        logger.info(f"[{action}] Waking up resources in background...")
        await asyncio.sleep(2.0)  # Simulate slow resource initialization
        logger.info(f"[{action}] Resources fully initialized and standing by.")

    def trigger(self, prediction: IntentPrediction):
        """
        Triggers a preemptive background task if confidence exceeds the threshold.
        """
        if prediction.confidence >= prediction.trigger_threshold:
            action = prediction.predicted_action
            if action not in self._active_preemptive_tasks:
                logger.warning(f"HIGH CONFIDENCE ({prediction.confidence:.2f}) -> Preemptively triggering: {action}")
                task = asyncio.create_task(self._mock_resource_wakeup(action))
                self._active_preemptive_tasks[action] = task
            else:
                logger.debug(f"Action {action} is already being preemptively prepared.")
        else:
            logger.debug(f"Confidence ({prediction.confidence:.2f}) too low to trigger {prediction.predicted_action}.")

    def clear_tasks(self):
        """Cancels and clears all preemptive tasks (e.g., if user changes their mind)."""
        for action, task in self._active_preemptive_tasks.items():
            task.cancel()
        self._active_preemptive_tasks.clear()
        logger.info("Cleared all preemptive tasks.")


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing Streaming Intent Predictor ---")
        
        analyzer = StreamIntentAnalyzer()
        trigger = PreemptiveTaskTrigger()
        
        # Simulate a user typing or speaking slowly
        simulated_input_stream = ["เปิ", "เปิด", "เปิดไ", "เปิดไฟใ", "เปิดไฟในห้อง"]
        
        buffer = ""
        for chunk in simulated_input_stream:
            buffer = chunk
            logger.info(f"Stream received: {buffer}")
            
            prediction = await analyzer.analyze_stream(buffer)
            if prediction:
                logger.info(f"Predicted Action: {prediction.predicted_action} | Confidence: {prediction.confidence:.2f}")
                trigger.trigger(prediction)
            
            await asyncio.sleep(0.5) # Time between keystrokes/words
            
        # Wait a bit to see background tasks complete
        await asyncio.sleep(3.0)

    asyncio.run(run_tests())
