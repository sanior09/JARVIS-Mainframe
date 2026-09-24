import os
import subprocess
import tempfile
import base64
import logging

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger("JarvisHardware")

def flash_esp32_firmware(cpp_code: str, port: str = "AUTO") -> str:
    """
    Creates a temporary PlatformIO project, writes the cpp_code, and flashes it to the ESP32.
    """
    try:
        
        with tempfile.TemporaryDirectory() as pio_dir:
            
            init_cmd = ["pio", "project", "init", "--board", "esp32dev"]
            result = subprocess.run(init_cmd, cwd=pio_dir, capture_output=True, text=True)
            if result.returncode != 0:
                return f"[HARDWARE ERROR] ไม่สามารถสร้าง PlatformIO Project ได้: {result.stderr}"

            src_dir = os.path.join(pio_dir, "src")
            os.makedirs(src_dir, exist_ok=True)
            main_cpp_path = os.path.join(src_dir, "main.cpp")
            with open(main_cpp_path, "w", encoding="utf-8") as f:
                f.write(cpp_code)

            pio_ini_path = os.path.join(pio_dir, "platformio.ini")
            with open(pio_ini_path, "a", encoding="utf-8") as f:
                f.write("framework = arduino\n")
                if port != "AUTO":
                    f.write(f"upload_port = {port}\n")

            run_cmd = ["pio", "run", "--target", "upload"]
            logger.info("กำลังคอมไพล์และอัปโหลด Firmware ไปยัง ESP32...")
            upload_result = subprocess.run(run_cmd, cwd=pio_dir, capture_output=True, text=True)
            
            if upload_result.returncode == 0:
                return f"การอัปโหลดโค้ดลง ESP32 สำเร็จเรียบร้อยครับเจ้านาย! (Port: {port})"
            else:
                return f"[HARDWARE ERROR] อัปโหลดล้มเหลว: {upload_result.stderr[-500:]}"
    except Exception as e:
        return f"[HARDWARE EXCEPTION] {str(e)}"

def capture_webcam_image(camera_index: int = 0) -> str:
    """
    Captures an image from the specified webcam index, encodes it in base64,
    and returns a formatted string containing the base64 data.
    """
    if cv2 is None:
        return "[HARDWARE ERROR] ไม่พบไลบรารี OpenCV กรุณาติดตั้ง opencv-python"
        
    try:
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return "[HARDWARE ERROR] ไม่สามารถเชื่อมต่อกับกล้อง Webcam ได้ครับท่าน"

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return "[HARDWARE ERROR] ไม่สามารถอ่านภาพจากกล้องได้"

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return "[HARDWARE ERROR] ไม่สามารถประมวลผลภาพจากกล้องได้"
            
        b64_img = base64.b64encode(buffer).decode('utf-8')
        
        return f"[WEBCAM_IMAGE_BASE64:{b64_img}]"

    except Exception as e:
        return f"[HARDWARE EXCEPTION] {str(e)}"
