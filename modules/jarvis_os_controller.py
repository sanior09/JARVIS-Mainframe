import asyncio
import logging
import psutil
import pyautogui
import pygetwindow as gw
from typing import Tuple, Optional, Dict

# Configure module-level logger
logger = logging.getLogger("JarvisOSController")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)


# ==========================================
# Custom Exceptions
# ==========================================
class JarvisOSError(Exception):
    """Base exception for JarvisOSController."""
    pass

class CommandExecutionError(JarvisOSError):
    """Raised when a system command execution fails or times out."""
    pass

class SystemResourceExceededError(JarvisOSError):
    """Raised when CPU or RAM usage exceeds safety thresholds."""
    pass

class ApplicationManagementError(JarvisOSError):
    """Raised when starting or killing an application fails."""
    pass

class InputAutomationError(JarvisOSError):
    """Raised when input simulation violates safety boundaries."""
    pass


# ==========================================
# Core Controller Class
# ==========================================
class JarvisOSController:
    """
    OS Control Module for JARVIS.
    Provides safe, asynchronous OS interactions including process management,
    telemetry checks, command execution, and GUI automation with guardrails.
    """

    def __init__(self, max_cpu: float = 90.0, max_ram: float = 90.0):
        self.max_cpu = max_cpu
        self.max_ram = max_ram
        # PyAutoGUI safety features
        pyautogui.FAILSAFE = True  # Moving mouse to screen corner raises FailSafeException

    # ------------------------------------------
    # 1. System Telemetry & Focus Control
    # ------------------------------------------
    def check_system_resources(self) -> Dict[str, float]:
        """
        Check CPU and Memory usage. Raises SystemResourceExceededError if above thresholds.
        """
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_usage = ram.percent

        logger.debug(f"Telemetry Check - CPU: {cpu_usage}%, RAM: {ram_usage}%")

        if cpu_usage > self.max_cpu:
            logger.error(f"CPU usage ({cpu_usage}%) exceeds safety threshold ({self.max_cpu}%).")
            raise SystemResourceExceededError(f"CPU usage at {cpu_usage}%, limit {self.max_cpu}%")
        
        if ram_usage > self.max_ram:
            logger.error(f"RAM usage ({ram_usage}%) exceeds safety threshold ({self.max_ram}%).")
            raise SystemResourceExceededError(f"RAM usage at {ram_usage}%, limit {self.max_ram}%")

        return {"cpu_percent": cpu_usage, "ram_percent": ram_usage}

    def get_active_window_title(self) -> Optional[str]:
        """Returns the title of the currently focused window."""
        try:
            window = gw.getActiveWindow()
            if window is not None:
                return window.title
            return None
        except Exception as e:
            logger.warning(f"Failed to get active window title: {e}")
            return None

    # ------------------------------------------
    # 2. Application Management
    # ------------------------------------------
    def is_process_running(self, process_name: str) -> bool:
        """Check if there is any running process that contains the given name."""
        process_name = process_name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                p_name = proc.info['name']
                if p_name and process_name in p_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def launch_application(self, executable_path: str, process_name: Optional[str] = None) -> bool:
        """
        Starts an application if it is not already running.
        Returns True if newly launched, False if already running.
        """
        if process_name and self.is_process_running(process_name):
            logger.info(f"Application '{process_name}' is already running. Launch aborted.")
            return False

        # Pre-flight resource check
        self.check_system_resources()

        try:
            # We use psutil.Popen for detached launching
            psutil.Popen([executable_path])
            logger.info(f"Launched application at: {executable_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to launch application '{executable_path}': {e}")
            raise ApplicationManagementError(f"Launch failed: {e}")

    def terminate_application(self, process_name: str) -> int:
        """
        Gracefully attempts to kill all processes matching process_name.
        Returns the number of terminated processes.
        """
        process_name = process_name.lower()
        terminated_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = proc.info['name']
                if p_name and process_name in p_name.lower():
                    proc.terminate()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.debug(f"Could not terminate process: {e}")
        
        logger.info(f"Terminated {terminated_count} instance(s) of '{process_name}'.")
        return terminated_count

    # ------------------------------------------
    # 3. Command Execution Engine
    # ------------------------------------------
    async def run_command_async(self, command: str, timeout_sec: float = 10.0) -> Tuple[int, str, str]:
        """
        Asynchronously executes a shell command with a strict timeout.
        Returns (exit_code, stdout_text, stderr_text).
        Raises CommandExecutionError if the command fails to launch or times out.
        """
        self.check_system_resources()
        logger.info(f"Executing command: '{command}' (Timeout: {timeout_sec}s)")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Subprocess creation failed for command '{command}': {e}")
            raise CommandExecutionError(f"Failed to create subprocess: {e}")

        try:
            stdout_data, stderr_data = await asyncio.wait_for(process.communicate(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            logger.error(f"Command '{command}' timed out after {timeout_sec}s. Terminating process.")
            try:
                process.kill()
                await process.communicate() # Ensure resources are cleaned up
            except ProcessLookupError:
                pass
            raise CommandExecutionError(f"Command execution timed out after {timeout_sec}s.")

        stdout_str = stdout_data.decode(errors='replace').strip()
        stderr_str = stderr_data.decode(errors='replace').strip()
        exit_code = process.returncode

        if exit_code != 0:
            logger.warning(f"Command '{command}' exited with code {exit_code}. Stderr: {stderr_str}")

        return (exit_code, stdout_str, stderr_str)

    # ------------------------------------------
    # 4. Input Automation Guard
    # ------------------------------------------
    def safe_click(self, x: int, y: int) -> None:
        """
        Clicks at a specific coordinate only if it falls within the current screen boundaries.
        """
        screen_width, screen_height = pyautogui.size()
        if not (0 <= x < screen_width and 0 <= y < screen_height):
            error_msg = f"Click coordinates ({x}, {y}) are out of bounds ({screen_width}x{screen_height})."
            logger.error(error_msg)
            raise InputAutomationError(error_msg)

        try:
            pyautogui.click(x, y)
            logger.debug(f"Clicked at ({x}, {y}).")
        except pyautogui.FailSafeException:
            logger.error("PyAutoGUI FailSafe triggered during click.")
            raise InputAutomationError("Failsafe triggered.")

    def safe_typewrite(self, text: str, interval: float = 0.05) -> None:
        """
        Types the given text with a default interval, safely.
        """
        try:
            active_window = self.get_active_window_title()
            logger.debug(f"Typing into active window: '{active_window}'")
            pyautogui.typewrite(text, interval=interval)
        except pyautogui.FailSafeException:
            logger.error("PyAutoGUI FailSafe triggered during typewrite.")
            raise InputAutomationError("Failsafe triggered.")
