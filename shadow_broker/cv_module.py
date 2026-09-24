"""
Computer Vision Module (Module 1).
Reads video stream into a Queue, performs YOLO Inference, and yields annotated frames.
"""
import time
import queue
import cv2
from typing import Generator
from .core import BaseVideoWorker, logger
from .config import CV_YOLO_MODEL_PATH, CV_FRAME_QUEUE_MAXSIZE, CV_TARGET_FPS

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning("ultralytics is not installed. AI Computer Vision will run in fallback mode (No inference). Run 'pip install ultralytics opencv-python' to enable.")

class CameraStreamer(BaseVideoWorker):
    """
    Reads frames from a video source (RTSP/Webcam) in a dedicated thread.
    Puts frames into a synchronized Queue to prevent blocking AI inference.
    """
    def __init__(self, stream_url: str):
        super().__init__(stream_url=stream_url, queue_size=CV_FRAME_QUEUE_MAXSIZE)
        
    def _worker_loop(self):
        # Allow integer stream_url for local webcam (e.g. "0")
        src = int(self.stream_url) if self.stream_url.isdigit() else self.stream_url
        cap = cv2.VideoCapture(src)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video stream: {self.stream_url}")
            self.is_running = False
            return

        fps_delay = 1.0 / CV_TARGET_FPS

        while self.is_running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Video stream disconnected: {self.stream_url}")
                # For demo purposes, if video ends, break. Real RTSP might need reconnect logic.
                break
                
            # Drop old frames if queue is full to keep real-time
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                    
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass
                
            # Enforce target FPS to prevent high CPU usage on fast sources
            elapsed = time.time() - start_time
            sleep_time = fps_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()
        logger.info(f"Video stream worker exited: {self.stream_url}")


class AIProcessor:
    """
    Consumes frames from CameraStreamer, runs YOLO inference,
    and formats output for Server-Sent Events (SSE) MJPEG stream.
    """
    def __init__(self, streamer: CameraStreamer):
        self.streamer = streamer
        if HAS_YOLO:
            try:
                self.model = YOLO(CV_YOLO_MODEL_PATH)
                logger.info(f"YOLO model loaded: {CV_YOLO_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
                self.model = None
        else:
            self.model = None

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """
        Generator yielding multipart JPEG frames.
        This blocks the calling thread (e.g. Flask request thread) until stream ends.
        """
        while self.streamer.is_running or not self.streamer.frame_queue.empty():
            try:
                # Use timeout to allow graceful shutdown checking
                frame = self.streamer.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # --- AI Inference ---
            if self.model:
                # Run YOLO inference (detect person, vehicle, etc.)
                # classes=[0,2,3,5,7] -> person, car, motorcycle, bus, truck in COCO
                results = self.model(frame, classes=[0,2,3,5,7], verbose=False)
                annotated_frame = results[0].plot()
            else:
                annotated_frame = frame
                # Add mock text if YOLO is missing
                cv2.putText(annotated_frame, "AI Module Offline (Missing ultralytics)", 
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(annotated_frame, "Run: pip install ultralytics opencv-python", 
                            (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # Yield as multipart/x-mixed-replace (standard for MJPEG streams)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
