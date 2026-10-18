# 🛠️ คู่มือประกอบชุดสแกนความร้อน DIY ด้วย MLX90640 (งบประหยัด)
**Project:** `STARK-DIY-THERMAL-MLX90640`  
**Location:** [`c:\JARVIS\hardware\mlx90640_diy_guide.md`](file:///c:/JARVIS/hardware/mlx90640_diy_guide.md)  
**Hardware Cost:** ~900 - 1,450 บาท

---

## 📌 1. รายการอุปกรณ์ที่ต้องสั่งซื้อ (Shopping Checklist)

1. **โมดูลเซ็นเซอร์ความร้อน MLX90640 Breakout Board**
   * *สเปก:* 32×24 พิกเซล I2C (มีตัวต้านทาน Pull-up บนบอร์ดแล้ว)
   * *คำแนะนำการเลือกเลนส์:*
     * **รุ่น D110 (มุมกว้าง FOV 110°):** แนะนำสำหรับติดแว่นหรือหมวกไอรอนแมน เพราะเก็บภาพได้กว้างรอบห้อง
     * **รุ่น D55 (มุมแคบ FOV 55°):** ส่องระยะไกลได้คมกว่าถ้าต้องการเล็งเฉพาะจุดของกำแพง
2. **บอร์ดไมโครคอนโทรลเลอร์ (เลือกอย่างใดอย่างหนึ่ง):**
   * **ตัวเลือก A (แนะนำที่สุด):** **Raspberry Pi Pico (RP2040)** (~120 - 160 บาท) — ทำงานเร็ว Flash CircuitPython ง่ายมาก
   * **ตัวเลือก B:** **ESP32-S3 Mini / ESP32 Type-C** (~140 - 220 บาท) — มี Wi-Fi/Bluetooth ในตัว
3. **สายเชื่อมต่อ:** สาย Jumper หรือสายแพร 4 เส้น (ความยาวตามต้องการ) + สาย Micro USB หรือ Type-C เสียบเข้าคอม

---

## 🔌 2. แผนภาพการต่อสาย (Wiring Diagram)

การเชื่อมต่อระหว่าง **MLX90640** กับ **Raspberry Pi Pico (RP2040)**:

```
  MLX90640 (Sensor)             Raspberry Pi Pico (RP2040)
 ┌─────────────────┐           ┌──────────────────────────┐
 │      VIN        ├───────────┤ 3V3 (Pin 36) หรือ VBUS   │ (ไฟเลี้ยง 3.3V)
 │      GND        ├───────────┤ GND (Pin 38)             │ (กราวด์)
 │      SDA        ├───────────┤ GP4 (Pin 6) [I2C0 SDA]   │ (ส่งข้อมูล)
 │      SCL        ├───────────┤ GP5 (Pin 7) [I2C0 SCL]   │ (สัญญาณนาฬิกา)
 └─────────────────┘           └─────────────┬────────────┘
                                             │ (สาย USB เสียบเข้าคอมพิวเตอร์)
                                             ▼
                                     [ J.A.R.V.I.S. Mainframe ]
```

*(หมายเหตุ: หากใช้บอร์ด **ESP32**: ต่อ SDA -> GPIO 21, SCL -> GPIO 22, VIN -> 3.3V, GND -> GND)*

---

## 💻 3. โค้ดเฟิร์มแวร์บนบอร์ด (Firmware: CircuitPython)

วิธีที่ง่ายที่สุด ไม่ต้องลงโปรแกรมคอมไพล์ให้ยุ่งยาก:
1. เสียบ Pico เข้าคอม กดปุ่ม `BOOTSEL` ค้างไว้ แล้วลากไฟล์ `CircuitPython .UF2` ลงในไดรฟ์ Pico
2. ดาวน์โหลดไลบรารี `adafruit_mlx90640.mpy` ใส่โฟลเดอร์ `lib/`
3. ก๊อปปี้โค้ดด้านล่างนี้บันทึกเป็นชื่อไฟล์ `code.py` บนไดรฟ์ Pico:

```python
import time
import board
import busio
import json
import adafruit_mlx90640

# ตั้งค่า I2C ความถี่สูง 400kHz หรือ 800kHz เพื่อให้ได้ 4-8 FPS
i2c = busio.I2C(board.GP5, board.GP4, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

frame = [0] * 768

while True:
    try:
        mlx.getFrame(frame)
        # ปัดเศษทศนิยม 1 ตำแหน่งเพื่อส่งข้อมูลผ่าน Serial ได้เร็วขึ้น
        compressed_frame = [round(t, 1) for t in frame]
        # พ่นข้อมูลออกทางพอร์ต Serial เป็น JSON ทีละเฟรม
        print(json.dumps(compressed_frame))
    except ValueError:
        pass
    time.sleep(0.1)
```

---

## 🧠 4. เวทมนตร์ฝั่ง J.A.R.V.I.S. : เทคนิคแปลงภาพ $32 \times 24$ ให้เนียนกริบ (Super-Resolution)

เซ็นเซอร์ $32 \times 24$ จุด (768 พิกเซล) อาจดูเหมือนเป็นสี่เหลี่ยมหยาบ ๆ แต่ใน [`modules/jarvis_thermal_scanner.py`](file:///c:/JARVIS/modules/jarvis_thermal_scanner.py) เราได้เตรียมอัลกอริทึม **Bicubic Interpolation & Gaussian Anti-Aliasing** ไว้แล้ว:

```
[ ข้อมูลดิบ 32x24 จุดจากเซ็นเซอร์ ]
             │
             ▼
[ ขยายสเกล 20 เท่าด้วย cv2.INTER_CUBIC (เป็น 640x480 พิกเซล) ]
             │
             ▼
[ ใส่ฟิลเตอร์ Gaussian Heat Dissipation (เนียนนุ่มเหมือนของจริง) ]
             │
             ▼
[ ใส่จานสีความร้อน COLORMAP_INFERNO หรือ COLORMAP_JET ]
             │
             ▼
[ ผลลัพธ์: ภาพความร้อนคล้ายกล้องราคาหลายหมื่นบาท พร้อมกรอบ HUD Stark ]
```

---

## 🚀 5. เมื่อต่อเข้าคอมแล้วต้องทำอย่างไรต่อ?

1. เสียบสาย USB เข้าพอร์ตคอมพิวเตอร์
2. คอมพิวเตอร์จะมองเห็นเป็นพอร์ต Serial เช่น `COM3`, `COM4` หรือ `/dev/ttyACM0`
3. สั่ง J.A.R.V.I.S. ทางเสียงหรือแชท:
   * *"จาร์วิส สแกนความร้อนจากเซ็นเซอร์ MLX บนพอร์ต COM3"*
4. J.A.R.V.I.S. จะดึงข้อมูลจุดอุณหภูมิ 768 จุดมาวิเคราะห์โครงสร้างเหล็ก (Thermal Bridge) และรอยลมรั่ว (Air Draft) พร้อมแสดงภาพบนหน้าจอทันทีครับ!
