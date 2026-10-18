"""
Purpose: รันสคริปต์หรือโปรแกรมที่ผู้ใช้เขียนเองบนคอมพิวเตอร์โดยไม่ต้องผ่านแอปพลิเคชันหลักของ J.A.R.V.I.S. ใช้สำหรับการทำงานที่เฉพาะเจาะจงหรือการทำงานที่ไม่มีตัวเลือกในแอปพลิเคชันทั่วไป
Created: 2026-09-29 22:02:06.671321
"""

from typing import Dict, Any

TOOL_SCHEMA: Dict[str, Any] = {
    "name": "run_custom_script",
    "description": "Run a custom script or program on your computer without going through J.A.R.V.I.S.'s main application. Useful for specific tasks or tasks with no options in general applications.",
    "parameters": {
        "type": "object",
        "properties": {
            "script_path": {
                "type": "string",
                "description": "The file path to the script or program you want to run."
            },
            "arguments": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Optional arguments to pass to the script or program."
            }
        },
        "required": ["script_path"]
    }
}

def run_custom_script(script_path: str, arguments: list = []) -> str:
    """
    Run a custom script or program on your computer.

    Args:
        script_path (str): The file path to the script or program you want to run.
        arguments (list, optional): Optional arguments to pass to the script or program. Defaults to an empty list.

    Returns:
        str: The output of the script or program.
    """
    import subprocess
    try:
        result = subprocess.run([script_path] + arguments, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"