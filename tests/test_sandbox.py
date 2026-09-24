import sys
sys.path.append('c:\\JARVIS')
from agent_windows_core import SandboxExecutor

sandbox = SandboxExecutor()
print("Executing sandbox test...")
try:
    sandbox.execute_sandbox_code("import pyautogui; pyautogui.moveTo(0, 0)")
    print("Test passed without FailSafeException!")
except Exception as e:
    print(f"Exception: {e}")
