# 🦾 J.A.R.V.I.S. Hardware Engineering & Procurement Hub
**Directory:** `hardware/`

คลังรวบรวมพิมพ์เขียว สเปกอุปกรณ์ ใบสั่งของ (Bill of Materials) และวงจรอิเล็กทรอนิกส์สำหรับขยายขีดความสามารถฮาร์ดแวร์จริงของ J.A.R.V.I.S. (หมวกไอรอนแมน, แว่นตาอัจฉริยะ, และเซ็นเซอร์ห้องแล็บ)

---

## 📂 รายการพิมพ์เขียวฮาร์ดแวร์ในปัจจุบัน (Hardware Projects)

### 1. 🎙️ [Laser Microphone & Optical Reconnaissance BOM](./laser_microphone_bom.md)
* **แรงบันดาลใจ:** Spider-Man: Homecoming (Karen AI Reconnaissance Mode ดักฟังเสียงทะลุกระจก)
* **งบประมาณ Prototype:** ~200 - 350 บาท
* **อุปกรณ์หลัก:** เลเซอร์ปรับโฟกัส 5V, Photodiode BPW34, บอร์ดขยายเสียง LM386/MAX9814, USB Sound Card
* **โมดูลซอฟต์แวร์ที่เชื่อมต่อ:** [`modules/jarvis_recon_audio.py`](../modules/jarvis_recon_audio.py)
* **คำสั่งเสียง:** *"จาร์วิส เปิดโหมดสอดแนม"*

---

### 2. 🔥 [Infrared Thermal & Structural Scanner BOM](./infrared_thermal_scanner_bom.md)
* **แรงบันดาลใจ:** Avengers: Age of Ultron (Tony Stark สแกนอินฟราเรดหาห้องลับและโครงสร้างเหล็กในปราสาท Hydra)
* **คู่มือประกอบชุด DIY งบประหยัด (~900 - 1,450 บ.):** [mlx90640_diy_guide.md](./mlx90640_diy_guide.md)
* **งบประมาณ:** 
  * ชุด DIY (MLX90640 + RP2040): ~900 - 1,450 บาท
  * ชุดจิ๋วระดับภาพยนตร์ (Infiray P2 Pro / Topdon TC001): ~4,600 - 7,600 บาท *(แนะนำสำหรับติดหมวก/แว่น)*
  * ชุดเกรดทหาร (FLIR Lepton 3.5 + PureThermal): ~8,500 - 12,000 บาท
* **โมดูลซอฟต์แวร์ที่เชื่อมต่อ:** [`modules/jarvis_thermal_scanner.py`](../modules/jarvis_thermal_scanner.py)
* **คำสั่งเสียง:** *"จาร์วิส สแกนอินฟราเรดห้องนี้หน่อย"*

---

### 3. 🕶️ [AR Smart Glasses (Meta Quest 3 Style) BOM](./ar_smart_glasses_bom.md)
* **แรงบันดาลใจ:** Meta Quest 3 & Apple Vision Pro (แว่น AR ตรวจจับมือเปล่า 21 จุด ลากหน้าจอ YouTube ลอยกลางอากาศ)
* **โครงสร้าง:** ออกแบบตามภาพสเก็ตช์ (บอร์ดประมวลผลขาซ้าย, แบตเตอรี่ขาขวา, กล้องคู่มุมกว้าง, หน้าจอโปร่งใส)
* **งบประมาณรวมทั้งชุด:** ~1,840 - 2,915 บาท
* **โมดูลซอฟต์แวร์ที่เชื่อมต่อ:** [`modules/holographic_gestures.py`](../modules/holographic_gestures.py) และ [`modules/gesture_controller.py`](../modules/gesture_controller.py)
* **การสั่งการ:** จีบนิ้ว (Pinch) ลากเลื่อนหน้าต่าง, สองมือขยายหน้าจอ (Two-Hand Zoom)
