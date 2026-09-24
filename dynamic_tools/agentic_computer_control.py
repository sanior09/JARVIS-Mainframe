from jarvis_computer_agent import AgenticComputerController

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "agentic_computer_control",
        "description": "ควบคุมคอมพิวเตอร์แบบมนุษย์ (Visual Agentic UI) ให้ AI ดูหน้าจอและขยับเมาส์/พิมพ์อัตโนมัติเพื่อทำงานที่ซับซ้อนให้สำเร็จ",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "เป้าหมายที่ต้องการให้ทำบนหน้าจอ เช่น 'เปิด Notepad พิมพ์ว่า Hello', 'ค้นหาสภาพอากาศในเว็บ'"
                }
            },
            "required": ["goal"]
        }
    }
}

def agentic_computer_control(args: dict) -> str:
    goal = args.get("goal", "")
    if not goal:
        return "ไม่มีเป้าหมาย (Goal) ส่งมาให้"
        
    try:
        agent = AgenticComputerController()
        result = agent.execute_goal(goal)
        return result
    except Exception as e:
        return f"เกิดข้อผิดพลาดในระบบ Agentic Control: {e}"
