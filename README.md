# J.A.R.V.I.S. Neural Matrix (Super AGI Edition)
**Nachapol Industries Advanced Intelligence System**

ระบบผู้ช่วยอัจฉริยะแบบ AGI (Artificial General Intelligence) ที่ออกแบบมาเพื่อการทำงานที่ครอบคลุมตั้งแต่วิศวกรรมซอฟต์แวร์ ฮาร์ดแวร์ ไปจนถึง 3D Holographic และ Generative AI

## 🚀 Quick Start (Nachapol Protocol)

### 1. เตรียม Mainframe
ติดตั้ง [Ollama](https://ollama.ai/) และรันคำสั่งเพื่อติดตั้งคอร์ประมวลผล:
```bash
ollama pull qwen2.5:1.5b
```

### 2. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
# ติดตั้งไลบรารีสำหรับ Super AGI Modules
pip install mediapipe opencv-python aiohttp websockets
```

### 3. ตั้งค่าระบบ
แก้ไขไฟล์ `.env` และใส่ API Keys ของท่าน:
- `OLLAMA_MODEL`: หรือเปลี่ยนเป็น `GROQ_MODEL` หากต้องการขุมพลังสูงสุด
- `HOME_ASSISTANT_TOKEN`: สำหรับควบคุมอุปกรณ์ใน Lab
- `ELEVENLABS_API_KEY`: สำหรับระบบสังเคราะห์เสียงอัจฉริยะ

### 4. เริ่มปฏิบัติการ
```bash
python jarvis.py
```
เปิดเบราว์เซอร์ไปที่ `http://localhost:5050` เพื่อเริ่มระบบรับฟัง (Speech Recognition)

---

## 🛠 16 Core Super AGI Modules (Features)
ระบบล่าสุดได้รับการอัปเกรดแบบ **Phase 1-7 Expansion** ครอบคลุม:

**🔒 Safety & Resilience Pipeline:**
- **Code Sentinel:** ประเมินความปลอดภัยโค้ดระดับ AST ป้องกัน Infinite Loop (`code_sentinel.py`)
- **Predictive Simulator:** คาดการณ์ความเสี่ยงและจำลองผลลัพธ์ก่อนสั่งรัน OS (`predictive_simulator.py`)
- **System Resilience:** สำรองโครงสร้างโค้ดอัตโนมัติขณะ Boot เครื่อง (`system_resilience.py`)

**👁️ Computer Vision & 3D Hologram:**
- **Holographic Gesture Controller:** ควบคุมระบบด้วยภาษามือผ่าน Webcam (`gesture_controller.py`)
- **Hologram Visualizer:** สร้างและเรนเดอร์กราฟิก Wireframe 3D กลางอากาศ (`hologram_visualizer.py`)
- **Spatial Vision:** ตรวจจับความเสียหายบนแผ่นวงจร PCB (`spatial_vision.py`)

**⚡ Real-Time Processing & Automation:**
- **Stream Intent Predictor:** เดาใจล่วงหน้าขณะพูดด้วย Zero-latency (`intent_predictor.py`)
- **ComfyUI Automation Bridge:** สั่งการ ComfyUI เพื่อสร้างภาพ Generative AI ด้วยเสียง (`comfyui_bridge.py`)
- **Tool Synthesizer:** เขียนและเรียนรู้เครื่องมือใหม่ๆ เองแบบ Meta-Programming (`tool_synthesizer.py`)

**⚙️ Engineering & Architecture:**
- **Engineering Analyzer:** สแกน 3D CAD และคลื่นสัญญาณ (`engineering_analyzer.py`)
- **Research Synthesizer:** สรุป Datasheet และวาด Architecture Graph อัตโนมัติ (`research_synthesizer.py`)
- **Lab Workflow FSM:** ควบคุมและติดตาม State การทำงานในห้องแล็บ (`lab_workflow_fsm.py`)
- **Cluster Offloader:** กระจายงานไปยังบอร์ดอื่นๆ หรือ Raspberry Pi ภายในวง LAN (`cluster_offloader.py`)

---
*Status: SUPER AGI MATRIX NOMINAL*  
*Mainframe Integrity: 100.0%*  
*Developed by Nachapol Industries*