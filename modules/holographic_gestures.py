from __future__ import annotations
import asyncio
import enum
import logging
import math
import os
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.components import containers as mp_containers
    _MP_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"\n[WARNING] HolographicGestureEngine mediapipe dependency issue: {e}")
    mp = None
    _MP_AVAILABLE = False

logger = logging.getLogger("HolographicGestureEngine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)

class GestureType(enum.Enum):
    IDLE = "IDLE"
    AIR_CLICK = "AIR_CLICK"      
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    ZOOM_IN = "ZOOM_IN"          
    ZOOM_OUT = "ZOOM_OUT"        
    PALM_HALT = "PALM_HALT"      

@dataclass
class GestureEvent:
    gesture: GestureType
    confidence: float
    timestamp: float
    spatial_data: Optional[Dict[str, float]] = None

class SpatialFilter:
    """
    Implements a vectorized Exponential Moving Average (EMA) filter 
    to smooth 3D landmark coordinates and reduce hand jitter.
    """
    def __init__(self, alpha: float = 0.5):
        """
        Args:
            alpha: Smoothing factor (0.0 < alpha <= 1.0). 
                   Lower = smoother but more lag. Higher = faster but more jitter.
        """
        self.alpha = alpha
        self.state: Optional[np.ndarray] = None

    def filter(self, current_landmarks: np.ndarray) -> np.ndarray:
        """
        Applies EMA to a (21, 3) numpy array of landmarks.
        """
        if self.state is None:
            self.state = current_landmarks
            return self.state
        
        self.state = self.alpha * current_landmarks + (1 - self.alpha) * self.state
        return self.state

    def reset(self):
        self.state = None

class GestureClassifier:
    """
    Analyzes normalized 3D Hand Landmarks to classify complex gesture patterns.
    """
    def __init__(self):
        
        self.WRIST = 0
        self.THUMB_TIP = 4
        self.INDEX_TIP = 8
        self.MIDDLE_TIP = 12
        self.RING_TIP = 16
        self.PINKY_TIP = 20
        
        self.PINCH_THRESHOLD = 0.05
        self.SWIPE_THRESHOLD = 0.15  
        
        self.palm_history = deque(maxlen=10)
        self.last_gesture_time = 0.0
        self.cooldown = 0.5  

    def _is_finger_extended(self, landmarks: np.ndarray, tip_idx: int, pip_idx: int) -> bool:
        """Heuristic to check if a finger is extended (Tip is further from wrist than PIP joint)"""
        wrist = landmarks[self.WRIST]
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        
        dist_tip = np.linalg.norm(tip[:2] - wrist[:2])
        dist_pip = np.linalg.norm(pip[:2] - wrist[:2])
        return dist_tip > dist_pip

    def classify_single_hand(self, landmarks: np.ndarray) -> GestureType:
        """
        Classifies gestures for a single hand (21x3 numpy array).
        """
        
        thumb_tip = landmarks[self.THUMB_TIP]
        index_tip = landmarks[self.INDEX_TIP]
        pinch_dist = np.linalg.norm(thumb_tip - index_tip)
        
        if pinch_dist < self.PINCH_THRESHOLD:
            return GestureType.AIR_CLICK

        thumb_ext = self._is_finger_extended(landmarks, self.THUMB_TIP, self.THUMB_TIP - 2)
        index_ext = self._is_finger_extended(landmarks, self.INDEX_TIP, self.INDEX_TIP - 2)
        middle_ext = self._is_finger_extended(landmarks, self.MIDDLE_TIP, self.MIDDLE_TIP - 2)
        ring_ext = self._is_finger_extended(landmarks, self.RING_TIP, self.RING_TIP - 2)
        pinky_ext = self._is_finger_extended(landmarks, self.PINKY_TIP, self.PINKY_TIP - 2)
        
        if thumb_ext and index_ext and middle_ext and ring_ext and pinky_ext:
            
            return GestureType.PALM_HALT

        palm_center = landmarks[self.WRIST]
        self.palm_history.append(palm_center)
        
        if len(self.palm_history) == self.palm_history.maxlen:
            dx = self.palm_history[-1][0] - self.palm_history[0][0]
            
            if dx > self.SWIPE_THRESHOLD:
                self.palm_history.clear()
                return GestureType.SWIPE_RIGHT
            elif dx < -self.SWIPE_THRESHOLD:
                self.palm_history.clear()
                return GestureType.SWIPE_LEFT

        return GestureType.IDLE

    def classify_dual_hands(self, hand1: np.ndarray, hand2: np.ndarray) -> GestureType:
        """
        Classifies gestures involving two hands (e.g., ZOOM).
        """
        
        dist = np.linalg.norm(hand1[self.INDEX_TIP] - hand2[self.INDEX_TIP])
        
        return GestureType.IDLE

class HolographicGestureManager:
    """
    High-level Async Orchestrator running the Vision Pipeline on a background thread.
    """
    def __init__(self, camera_index: int = 0):
        self.available = True
        self.camera_index = camera_index
        self.hands_detector = None
        self._latest_detection = None

        if not _MP_AVAILABLE:
            self.available = False
            print("[WARNING] Holographic Gestures disabled due to missing 'mediapipe' module.")
        else:
            try:
                
                _model_path = os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task")
                base_options = mp_python.BaseOptions(
                    model_asset_path=_model_path,
                    delegate=mp_python.BaseOptions.Delegate.CPU
                )
                options = mp_vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=2,
                    min_hand_detection_confidence=0.7,
                    min_hand_presence_confidence=0.7,
                    min_tracking_confidence=0.5,
                )
                self.hands_detector = mp_vision.HandLandmarker.create_from_options(options)
                logger.info("[HolographicGestureEngine] MediaPipe 1.0 HandLandmarker initialized.")
            except Exception as e:
                print(f"[WARNING] Holographic Gestures disabled: {e}")
                self.available = False
        
        self.classifier = GestureClassifier()
        
        self.filters = [SpatialFilter(alpha=0.6), SpatialFilter(alpha=0.6)]
        
        self.callbacks: Dict[GestureType, List[Callable]] = {gt: [] for gt in GestureType}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def register_callback(self, gesture: GestureType, coro_fn: Callable[[GestureEvent], None]):
        """Register an async callback for a specific gesture."""
        self.callbacks[gesture].append(coro_fn)

    def _dispatch_event(self, gesture: GestureType, data: Optional[Dict[str, float]] = None):
        """Dispatches event to registered callbacks safely across threads."""
        if gesture == GestureType.IDLE:
            return
            
        current_time = time.time()
        
        if current_time - self.classifier.last_gesture_time < self.classifier.cooldown:
            return
            
        self.classifier.last_gesture_time = current_time
        event = GestureEvent(gesture=gesture, confidence=1.0, timestamp=current_time, spatial_data=data)
        
        logger.info(f"👉 DISPATCH EVENT: {gesture.value}")
        
        if self.loop is not None and self.loop.is_running():
            for cb in self.callbacks[gesture]:
                asyncio.run_coroutine_threadsafe(cb(event), self.loop)

    def start_background_task(self, render_debug: bool = False):
        """Starts the computer vision pipeline in a dedicated daemon thread."""
        self.loop = asyncio.get_running_loop()
        self._is_running = True
        
        self.thread = threading.Thread(target=self._vision_loop, args=(render_debug,), daemon=True, name="CV-Worker")
        self.thread.start()
        logger.info("HolographicGestureManager Started on CV-Worker Thread.")

    def _vision_loop(self, render_debug: bool):
        cap = cv2.VideoCapture(self.camera_index)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 60)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

        while self._is_running:
            start_t = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                logger.warning("Camera read failed. Retrying...")
                time.sleep(0.1)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            detection_result = self.hands_detector.detect(mp_image)

            parsed_hands = []

            if detection_result.hand_landmarks:
                for idx, hand_lms in enumerate(detection_result.hand_landmarks):
                    
                    lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_lms])

                    if idx < len(self.filters):
                        smoothed_lm = self.filters[idx].filter(lm_array)
                    else:
                        smoothed_lm = lm_array

                    parsed_hands.append(smoothed_lm)

                    gesture = self.classifier.classify_single_hand(smoothed_lm)
                    if gesture != GestureType.IDLE:
                        self._dispatch_event(gesture, data={"hand_id": idx})

                    if render_debug:
                        
                        h, w, _ = frame.shape
                        for lm in hand_lms:
                            cx, cy = int(lm.x * w), int(lm.y * h)
                            cv2.circle(frame, (cx, cy), 4, (0, 200, 255), -1)
            else:
                
                for f in self.filters:
                    f.reset()

            if len(parsed_hands) == 2:
                gesture_dual = self.classifier.classify_dual_hands(parsed_hands[0], parsed_hands[1])
                if gesture_dual != GestureType.IDLE:
                    self._dispatch_event(gesture_dual)

            process_time = (time.perf_counter() - start_t) * 1000

            if render_debug:
                cv2.putText(frame, f"Latency: {process_time:.1f}ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Holographic Gesture Engine [DEBUG]", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self._is_running = False
                    break

        cap.release()
        if self.hands_detector:
            self.hands_detector.close()
        cv2.destroyAllWindows()
        logger.info("CV-Worker Terminated. Resources freed.")

    def stop(self):
        self._is_running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2.0)

async def demo_app():
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("\n" + "="*50)
    print(" 🚀 STARTING HOLOGRAPHIC GESTURE ENGINE DEMO")
    print("="*50)
    print("[INFO] Press 'q' in the OpenCV window to exit the demo.")

    manager = HolographicGestureManager(camera_index=0)
    
    async def on_click(event: GestureEvent):
        print(f"\n[EVENT] 🤏 AIR CLICK Detected! (Time: {event.timestamp:.2f})")
        
    async def on_swipe_left(event: GestureEvent):
        print(f"\n[EVENT] ⏪ SWIPE LEFT Detected! (Time: {event.timestamp:.2f})")
        
    async def on_swipe_right(event: GestureEvent):
        print(f"\n[EVENT] ⏩ SWIPE RIGHT Detected! (Time: {event.timestamp:.2f})")
        
    async def on_halt(event: GestureEvent):
        print(f"\n[EVENT] 🛑 PALM HALT Detected! (EMERGENCY STOP) (Time: {event.timestamp:.2f})")

    manager.register_callback(GestureType.AIR_CLICK, on_click)
    manager.register_callback(GestureType.SWIPE_LEFT, on_swipe_left)
    manager.register_callback(GestureType.SWIPE_RIGHT, on_swipe_right)
    manager.register_callback(GestureType.PALM_HALT, on_halt)
    
    manager.start_background_task(render_debug=True)
    
    try:
        while manager._is_running:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        manager.stop()
        
    print("Demo Finished Cleanly.")

if __name__ == "__main__":
    asyncio.run(demo_app())
