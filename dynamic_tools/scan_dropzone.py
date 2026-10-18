"""
Purpose: Expose scan_dropzone to the LLM
"""

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "scan_dropzone",
        "description": "คำสั่งสำหรับบังคับให้ J.A.R.V.I.S. สแกนและอ่านเอกสารใหม่ (PDF, Word, Excel) ที่ถูกวางไว้ในโฟลเดอร์ jarvis_library ทันที",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def scan_dropzone(args):
    # This won't be called directly by run_dynamic_tool because it's mapped in AVAILABLE_TOOLS
    # but just in case it falls through:
    import jarvis_doc_parser
    return jarvis_doc_parser.scan_and_parse_library()
