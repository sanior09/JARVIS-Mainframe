"""
Purpose: Allow JARVIS to manually trigger a System Overdrive (Optimize System Resources)
"""

import logging

logger = logging.getLogger(__name__)

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "system_overdrive_control",
        "description": "คำสั่งสำหรับบังคับล้างเครื่อง จัดการ Priority ของโปรแกรม (Process) และรีดประสิทธิภาพเครื่อง (System Overdrive) แบบทันที",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "ระบุว่าต้องการทำอะไร เช่น 'optimize', 'purge'",
                    "enum": ["optimize", "purge"]
                }
            },
            "required": ["action"]
        }
    }
}

def system_overdrive_control(args):
    action = args.get("action", "optimize")
    
    try:
        from jarvis_system_overdrive import overdrive_manager
        
        if action == "optimize":
            report = overdrive_manager.optimize_system(auto_mode=False)
            return f"ดำเนินการ System Overdrive เสร็จสิ้น: {report}"
        elif action == "purge":
            # For now, purge just does the same optimization but in the future could kill zombie processes
            report = overdrive_manager.optimize_system(auto_mode=False)
            return f"ดำเนินการ Purge เสร็จสิ้น: {report}"
        else:
            return "ไม่รู้จักคำสั่ง Overdrive นี้ครับ"
            
    except Exception as e:
        logger.error(f"[Overdrive Tool] Error: {e}")
        return f"เกิดข้อผิดพลาดในการรัน System Overdrive ครับ: {e}"
