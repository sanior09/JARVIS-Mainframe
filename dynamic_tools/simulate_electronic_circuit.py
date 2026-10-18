import json

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "simulate_electronic_circuit",
        "description": "จำลองการทำงานของวงจรไฟฟ้าตามกฎของ Ohm และคำนวณความร้อนสะสม/ความเสี่ยงต่อโครงสร้างวัสดุ",
        "parameters": {
            "type": "object",
            "properties": {
                "voltage": {"type": "number", "description": "แรงดันไฟฟ้า (V)"},
                "resistance": {"type": "number", "description": "ค่าความต้านทานรวม (Ohms)"},
                "resistors": {"type": "array", "items": {"type": "number"}, "description": "รายการตัวต้านทานต่ออนุกรม"},
                "current_load": {"type": "number", "description": "กระแสโหลด (A) ถ้ามี"},
                "material": {"type": "string", "description": "วัสดุโครงสร้าง เช่น PMMA หรือ Aluminum"}
            },
            "required": ["voltage"]
        }
    }
}

def simulate_electronic_circuit(args):
    """
    [VIRTUAL LAB SIMULATION ENGINE]
    จำลองการทำงานของวงจรไฟฟ้าตามกฎของ Ohm และคำนวณความร้อนสะสม
    - args ควรประกอบด้วย:
      - voltage (float): แรงดันไฟ (V)
      - resistance (float) หรือ resistors (list): ค่าความต้านทาน (Ohms)
      - current_load (float): กระแสโหลด ถ้ามี
      - material (str): วัสดุโครงสร้าง (เช่น "PMMA")
    """
    try:
        if isinstance(args, str):
            args = json.loads(args)
            
        voltage = float(args.get("voltage", 0))
        resistance = args.get("resistance")
        resistors = args.get("resistors")
        current_load = args.get("current_load")
        material = str(args.get("material", "PMMA")).upper()

        if resistance is None and resistors is not None:
            # สมมติวงจรอนุกรมง่ายๆ
            resistance = sum(float(r) for r in resistors)
        elif resistance is None:
            resistance = 1.0 # default to prevent division by zero
            
        resistance = float(resistance)
        if resistance <= 0:
            resistance = 0.001

        # Ohm's Law
        if current_load is None:
            current = voltage / resistance
        else:
            current = float(current_load)

        # Power dissipation P = I^2 * R
        power = (current ** 2) * resistance

        # Thermal Delta Approximation
        # สมมติ Thermal Resistance ของ PMMA สูง ทำให้สะสมความร้อนได้ง่าย
        thermal_coefficient = 2.5 if material == "PMMA" else 1.5
        temp_delta = power * thermal_coefficient
        
        base_temp = 25.0
        final_temp = base_temp + temp_delta
        
        if final_temp > 80.0 or current > 10.0:
            alert_msg = (
                f"[WINDOW: SIMULATION ALERT]\n"
                f"🚨 การจำลองเสร็จสิ้น: ตรวจพบความเสี่ยงระดับวิกฤต\n"
                f"----------------------------------------\n"
                f"- กระแสไฟไหลผ่าน: {current:.2f} A\n"
                f"- การสูญเสียพลังงานความร้อน: {power:.2f} W\n"
                f"- อุณหภูมิสะสมจำลอง: {final_temp:.2f}°C\n"
                f"----------------------------------------\n"
                f"วิเคราะห์ทางฟิสิกส์: ความร้อนสะสมพุ่งทะลุ 80°C ซึ่งจะทำให้บอดี้ {material} หลอมละลายและเสียรูปทรง โครงสร้างวงจรนี้กระแสไฟเกินพิกัด ขอแนะนำให้เจ้านายเพิ่มค่าตัวต้านทานหรือลด Voltage ด่วนครับ!\n"
                f"[END_WINDOW]"
            )
            return alert_msg
            
        return (
            f"[WINDOW: SIMULATION SAFE]\n"
            f"✅ การจำลองเสร็จสิ้น: วงจรปลอดภัย\n"
            f"- กระแสไฟ: {current:.2f} A\n"
            f"- อุณหภูมิสะสม: {final_temp:.2f}°C\n"
            f"สถานะบอดี้ {material} อยู่ในเกณฑ์ทนความร้อนได้ ไม่พบความเสี่ยงครับเจ้านาย\n"
            f"[END_WINDOW]"
        )

    except Exception as e:
        return f"[WINDOW: SIMULATION ERROR]\nเกิดข้อผิดพลาดในการประมวลผลโมเดลคณิตศาสตร์: {str(e)}\n[END_WINDOW]"
