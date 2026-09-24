import subprocess
import tempfile
import os
import sys

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "code_interpreter",
        "description": "รันโค้ด Python แบบ Real-time (REPL) เพื่อแก้ปัญหา วิเคราะห์ข้อมูล โหลดไฟล์ หรือรันสคริปต์อัตโนมัติ ใช้เครื่องมือนี้เมื่อต้องการเขียนโค้ดแก้ปัญหาเฉพาะหน้า โดยสามารถใช้ pip install ได้ในสคริปต์ผ่าน subprocess",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "โค้ด Python ที่ต้องการให้ระบบรันแบบสมบูรณ์ (ตัวอย่างเช่น import x, data=x(), print(data)) กรุณาพิมพ์ผลลัพธ์ด้วย print() เสมอ"
                }
            },
            "required": ["code"]
        }
    }
}

def code_interpreter(args: dict) -> str:
    """
    Executes arbitrary Python code in a temporary file and returns stdout/stderr.
    This acts as a "Code Interpreter" / "Advanced Data Analysis" tool.
    """
    code = args.get("code", "")
    if not code:
        return "Error: No code provided."
    
    # We create a temporary python file
    fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="jarvis_code_")
    
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Execute the python script using the same environment Jarvis is running in
        # Timeout set to 120 seconds to prevent infinite loops
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = ""
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"
            
        if not output:
            output = "Code executed successfully with no output. (Did you forget to print()?)"
            
        return output
        
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out (exceeded 120 seconds)."
    except Exception as e:
        return f"Error executing code: {e}"
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
