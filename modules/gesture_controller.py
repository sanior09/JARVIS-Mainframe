"""
gesture_controller.py
Module: Holographic Hand Gesture Controller

Utilizes MediaPipe and OpenCV to track hand movements and map them to 
commands for interacting with 3D Holograms/Wireframes (e.g., Pinch to Zoom, Pan).
"""

import math
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List

try:
    import cv2
    import mediapipe as mp
    _HAS_CV_DEPS = True
except (ImportError, Exception):
    _HAS_CV_DEPS = False

# Setup Module Logger
logger = logging.getLogger("GestureController")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class GestureControllerException(Exception):
    """Base exception for the Gesture Controller module."""
    pass


class AbstractGestureMapper(ABC):
    @abstractmethod
    def map_landmarks_to_command(self, landmarks: Any) -> Optional[str]:
        """Analyzes hand landmarks and returns an action command."""
        pass


class GestureCommandMapper(AbstractGestureMapper):
    """
    Analyzes mathematical distances between finger joints to detect gestures.
    """
    def __init__(self, pinch_threshold: float = 0.05):
        self.pinch_threshold = pinch_threshold

    def _calculate_distance(self, p1, p2) -> float:
        """Calculates 3D Euclidean distance between two landmarks."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def map_landmarks_to_command(self, landmarks) -> Optional[str]:
        """
        Takes MediaPipe NormalizedLandmarkList and maps to a string command.
        Uses simplistic heuristics for demonstration.
        """
        # In MediaPipe: 
        # 4 = Thumb tip, 8 = Index finger tip, 12 = Middle finger tip
        try:
            thumb_tip = landmarks.landmark[4]
            index_tip = landmarks.landmark[8]
            middle_tip = landmarks.landmark[12]
            
            # Pinch Gesture (Thumb and Index close together)
            distance_pinch = self._calculate_distance(thumb_tip, index_tip)
            if distance_pinch < self.pinch_threshold:
                return "PINCH_ZOOM"
                
            # Peace Sign / Pan Gesture (Index and Middle up, others down)
            # A simplified check: index and middle are far apart, but y-coord is higher than base
            distance_peace = self._calculate_distance(index_tip, middle_tip)
            if distance_peace > 0.08 and index_tip.y < landmarks.landmark[5].y and middle_tip.y < landmarks.landmark[9].y:
                 return "PAN_MOVE"
                 
            # Open Hand (All tips relatively far from wrist 0)
            wrist = landmarks.landmark[0]
            if self._calculate_distance(thumb_tip, wrist) > 0.3 and self._calculate_distance(index_tip, wrist) > 0.3:
                return "ROTATE"
                
        except (AttributeError, IndexError) as e:
            logger.debug(f"Landmark analysis error: {e}")
            
        return None


class HandTrackingEngine:
    """
    Interfaces with the Webcam and MediaPipe Hands solution.
    """
    def __init__(self, max_num_hands: int = 2, min_detection_confidence: float = 0.7):
        self.mapper = GestureCommandMapper()
        
        if _HAS_CV_DEPS:
            try:
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    max_num_hands=max_num_hands,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=0.5
                )
                self.mp_drawing = mp.solutions.drawing_utils
            except AttributeError as e:
                logger.warning(f"MediaPipe initialization failed ({e}). Running in MOCK mode.")
                self.hands = None
        else:
            logger.warning("MediaPipe or OpenCV not installed. Running in MOCK mode.")
            self.hands = None

    def start_tracking_loop(self):
        """
        Starts the OpenCV VideoCapture loop. Blocks the current thread.
        Press 'q' to exit.
        """
        if not _HAS_CV_DEPS:
            logger.error("Cannot start tracking loop. Missing cv2/mediapipe.")
            self._mock_tracking_loop()
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise GestureControllerException("Cannot open webcam.")

        logger.info("Started Holographic Gesture Tracking. Press 'q' to exit.")
        
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                logger.warning("Ignoring empty camera frame.")
                continue

            # To improve performance, optionally mark the image as not writeable to pass by reference.
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)

            # Draw the hand annotations on the image.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS)
                        
                    # Map to command
                    command = self.mapper.map_landmarks_to_command(hand_landmarks)
                    if command:
                        logger.info(f"Detected Gesture Command: {command}")
                        # In production, dispatch this command to the HologramVisualizer
                        
                        # Visual Feedback
                        cv2.putText(image, f"CMD: {command}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Show window
            cv2.imshow('J.A.R.V.I.S. Holographic Controller', image)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()

    def _mock_tracking_loop(self):
        """Simulates tracking for environments without a webcam."""
        import time
        logger.info("[MOCK] Simulating Gesture Tracking loop for 5 seconds...")
        time.sleep(1)
        logger.info("[MOCK] Detected Gesture Command: PINCH_ZOOM")
        time.sleep(2)
        logger.info("[MOCK] Detected Gesture Command: ROTATE")
        time.sleep(2)
        logger.info("[MOCK] Gesture Tracking loop closed.")


if __name__ == "__main__":
    logger.info("--- Testing Holographic Hand Gesture Controller ---")
    engine = HandTrackingEngine()
    try:
        engine.start_tracking_loop()
    except Exception as e:
        logger.error(f"Error during tracking: {e}")
