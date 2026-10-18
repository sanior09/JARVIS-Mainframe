# dynamic_tools/trigger_sleep_mode.py

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "trigger_sleep_mode",
        "description": "เปิดโหมดจำศีล (Sleep Mode) เพื่อตกผลึกความจำ (Memory Consolidation) สร้าง Core Beliefs ให้ JARVIS เรียนรู้นิสัยเจ้านาย",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def execute(args: dict) -> str:
    """Execute the sleep mode memory consolidation."""
    import logging
    import sys
    
    # Needs to import from parent directory
    sys.path.append("c:\\JARVIS")
    try:
        from jarvis import chroma_client
        import jarvis_memory_consolidation
        
        success = jarvis_memory_consolidation.start_sleep_mode_consolidation(chroma_client)
        if success:
            # Force reload core beliefs to JARVIS memory if needed
            return "✅ ทำการเข้าโหมดจำศีลและตกผลึกความจำ (Core Beliefs) เรียบร้อยแล้วครับเจ้านาย ความจำระยะยาวถูกอัปเดตแล้ว!"
        else:
            return "❌ เกิดข้อผิดพลาดในการรัน Memory Consolidation"
    except Exception as e:
        logging.error(f"Sleep mode tool error: {e}")
        return f"❌ ข้อผิดพลาดของระบบ: {str(e)}"
