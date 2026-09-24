import os
from generative_3d import visualize_data_3d

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "render_3d_workspace",
        "description": "สร้างภาพจำลอง 3 มิติ (โฮโลแกรม) ของไฟล์และโฟลเดอร์ในโปรเจกต์ (Infinite 3D Workspace)",
        "parameters": {
            "type": "object",
            "properties": {
                "root_path": {
                    "type": "string",
                    "description": "เส้นทางโฟลเดอร์ที่ต้องการจำลอง เช่น 'c:/JARVIS'"
                }
            },
            "required": ["root_path"]
        }
    }
}

def render_3d_workspace(args: dict) -> str:
    root_path = args.get("root_path", "c:/JARVIS")
    
    if not os.path.exists(root_path):
        return f"ไม่พบเส้นทาง {root_path}"

    nodes = []
    links = []
    
    # Create root node
    nodes.append({"id": root_path, "group": 0, "val": 10})
    
    # Traverse directory
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Limit depth/number of files to prevent lag
            if len(nodes) > 300:
                break
                
            for d in dirnames:
                if d.startswith(".") or d == "__pycache__": continue
                full_path = os.path.join(dirpath, d).replace('\\', '/')
                nodes.append({"id": full_path, "group": 1, "val": 5})
                links.append({"source": dirpath.replace('\\', '/'), "target": full_path, "value": 2})
                
            for f in filenames:
                if f.startswith("."): continue
                full_path = os.path.join(dirpath, f).replace('\\', '/')
                nodes.append({"id": full_path, "group": 2, "val": 2})
                links.append({"source": dirpath.replace('\\', '/'), "target": full_path, "value": 1})
                
        data = {
            "nodes": nodes,
            "links": links
        }
        
        visualize_data_3d(data, data_type='workspace_nodes')
        return f"สร้างและเปิด Infinite 3D Workspace ของ {root_path} เรียบร้อยแล้วครับ"
        
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการสร้าง 3D Workspace: {e}"
