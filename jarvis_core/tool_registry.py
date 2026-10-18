import os

HA_LIGHT_1 = os.getenv("HA_LIGHT_1", "light.light_1").strip()
HA_LIGHT_2 = os.getenv("HA_LIGHT_2", "light.light_2").strip()

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "execute_in_background",
            "description": "เมื่อได้รับคำสั่งที่ต้องใช้เวลาคิดนาน (เช่น ค้นหาข้อมูลเชิงลึก, เขียนโค้ดโปรแกรมที่ยาวมาก) ให้โยนงานนั้นเข้าเบื้องหลังผ่านคำสั่งนี้ เพื่อให้สมองหลักพร้อมตอบแชทต่อได้ทันที (Multitasking)",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "คำสั่งที่ต้องการให้ร่างแยกทำอย่างละเอียด (เช่น 'เขียนโค้ดระบบตรวจจับใบหน้าด้วย Python 300 บรรทัด')"
                    }
                },
                "required": ["task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "สั่งให้ AI วาดรูป สร้างรูปภาพ หรือออกแบบภาพตามจินตนาการ (Text-to-Image)",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "คำอธิบายรูปภาพอย่างละเอียดเป็นภาษาอังกฤษ (ถ้าผู้ใช้พิมพ์ไทยมา ให้แปลเป็นอังกฤษก่อนส่งเข้าพารามิเตอร์นี้)"
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_and_render_hologram",
            "description": "[ADVANCED CORE] เสกโมเดล 3D จากข้อความ (Text-to-3D) และส่งเข้า Hologram Engine เพื่อเตรียมแสดงผลโฮโลแกรมบนหน้าจอทันที",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "คำอธิบายรายละเอียดของโมเดล 3D ที่ต้องการสร้าง (เช่น 'A futuristic iron man helmet')"
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_learning_cycle",
            "description": "บังคับให้ JARVIS ไปศึกษาเรียนรู้ค้นคว้าหัวข้อใหม่ๆ จากอินเทอร์เน็ตทันที (Autonomous Learning)",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "(Optional) หัวข้อที่ต้องการให้เรียนรู้ ถ้าเว้นว่างไว้ ระบบจะสุ่มเลือกหัวข้อเอง"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_island",
            "description": "ซ่อน หรือ แสดง Dynamic Island / หน้าจอ / เกาะ (ใช้เมื่อเจ้านายพูดว่า 'ซ่อนหน้าจอ', 'ซ่อนเกาะ', 'โชว์หน้าจอ', หรือ 'แสดงเกาะ')",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["hide", "show"], "description": "การกระทำ: hide (ซ่อน) หรือ show (แสดง)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "ค้นหาและเปิดเพลงจาก YouTube หรือบนหน้าจอโฮโลแกรม (ใช้เฉพาะเมื่อเจ้านายสั่งให้ 'เปิดเพลง', 'เล่นเพลง', 'ฟังเพลง' เท่านั้น ห้ามใช้เมื่อผู้ใช้ถามสถานะอุปกรณ์ เช่น 'แบตเตอรี่' หรือ 'โทรศัพท์' เด็ดขาด)",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_name": {"type": "string", "description": "ชื่อเพลงหรือศิลปินที่ต้องการฟัง"}
                },
                "required": ["song_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "จดจำข้อมูลโปรไฟล์ พฤติกรรม หรือความชอบเฉพาะตัวของเจ้านายลงในฐานข้อมูลถาวร",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "หัวข้อที่ต้องการจำ เช่น 'อาหารที่ชอบ', 'เวลาเข้านอน'"},
                    "value": {"type": "string", "description": "รายละเอียดข้อมูลที่ต้องการจำ"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_light_status",
            "description": "ตรวจสอบสถานะปัจจุบันของหลอดไฟ (เปิด/ปิด, ความสว่าง, สี) เพื่อนำมาวิเคราะห์ก่อนสั่งการ",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "ID ของหลอดไฟ เช่น light.living_room (หากไม่ระบุจะดึงข้อมูลทั้งหมด)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "os_control",
            "description": "ควบคุมการทำงานของระบบ J.A.R.V.I.S. (Shutdown, Restart, Sleep)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["shutdown", "restart", "sleep"]}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_light",
            "description": "ควบคุมหลอดไฟ Smart Bulb (เปิด, ปิด, ปรับความสว่าง, เปลี่ยนสี) [ข้อควรระวัง: หากผู้ใช้ไม่ระบุหลอดเจาะจง ให้เว้นว่าง entity_id เพื่อควบคุมทั้งหมด และหลังจากสั่งงานสำเร็จ ต้องตอบกลับยืนยันเสมอ เช่น 'เปลี่ยนไฟให้แล้วครับ']",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": f"ID หลอดไฟเฉพาะเจาะจง ('{HA_LIGHT_1}' หรือ '{HA_LIGHT_2}'). **เว้นว่างพารามิเตอร์นี้ไว้หากต้องการเปลี่ยนไฟทั้งห้องพร้อมกัน!**"},
                    "action": {"type": "string", "enum": ["on", "off"], "description": "คำสั่งเปิดหรือปิด"},
                    "brightness": {"type": "integer", "description": "ความสว่าง 0-255"},
                    "rgb_color": {"type": "array", "items": {"type": "integer"}, "description": "สีในรูปแบบ [R, G, B]"},
                    "kelvin": {"type": "integer", "description": "อุณหภูมิสี (Kelvin) เช่น 2700 (Warm), 4500 (Natural), 6500 (Cool)"},
                    "transition": {"type": "integer", "description": "ระยะเวลาการเปลี่ยนผ่านแสง (วินาที) เพื่อความนุ่มนวล"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_ambiance",
            "description": "จัดแสงบรรยากาศห้องแบบ Dual-Bulb Mood Lighting ตามธีมที่กำหนด เช่น ริมทะเล (ฟ้าทะเล+ทรายอบอุ่น), แสงเหนือ (เขียวมรกต+ม่วงออโรร่า), ไซเบอร์พังค์ (นีออนชมพู+ฟ้าไซเบอร์), โคซี่/แคมป์ไฟ, ซันเซ็ต, หรือกำหนดสีคู่เองได้",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "description": "ชื่อธีมบรรยากาศ เช่น 'ริมทะเล', 'แสงเหนือ', 'cyberpunk', 'cinema', 'cozy', 'stark_lab', 'sunset', 'lofi'"
                    },
                    "light_1_color": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "สี RGB กำหนดเองสำหรับหลอดหลัก 1 [R, G, B]"
                    },
                    "light_2_color": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "สี RGB กำหนดเองสำหรับหลอดรอง 2 [R, G, B]"
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "ความสว่าง 0-255 (ค่าเริ่มต้น 180)"
                    },
                    "transition": {
                        "type": "integer",
                        "description": "ระยะเวลาการค่อยๆ เปลี่ยนสีแสง (วินาที) ค่าเริ่มต้น 3"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browse_website",
            "description": "เข้าไปอ่านเนื้อหาจากเว็บไซต์ที่ระบุ (Web Scraping) เพื่อดึงรายละเอียดเชิงลึก บทความ หรือวิจัย",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL ของเว็บไซต์ที่ต้องการอ่าน"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_memory",
            "description": "บันทึกข้อมูลสำคัญที่ได้จากการค้นหาหรือการเรียนรู้ลงในฐานความจำระยะยาว",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "เนื้อหาสำคัญที่ต้องการบันทึก"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_mission_log",
            "description": "จัดการบันทึกภารกิจ โปรเจควิศวกรรม และตารางนัดหมาย (Nachapol Mission Log & Timeline)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string", 
                        "enum": ["add_mission", "update_mission", "add_event", "get_summary"],
                        "description": "การดำเนินการ: add_mission (เพิ่มงาน), update_mission (อัปเดตสถานะ), add_event (เพิ่มนัดหมาย), get_summary (สรุปภารกิจทั้งหมด)"
                    },
                    "title": {"type": "string", "description": "หัวข้อภารกิจหรือนัดหมาย"},
                    "description": {"type": "string", "description": "รายละเอียดเชิงลึก"},
                    "due_date": {"type": "string", "description": "กำหนดส่งหรือเวลาเริ่ม (YYYY-MM-DD HH:MM:SS)"},
                    "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "status": {"type": "string", "description": "สถานะเช่น 'in_progress', 'completed', 'testing'"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ha_entities",
            "description": "ดึงรายชื่ออุปกรณ์และเซนเซอร์ทั้งหมดในบ้านจาก Home Assistant เพื่อตรวจสอบสถานะรวม",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "กลุ่มอุปกรณ์ เช่น light, sensor, switch (หากไม่ระบุจะดึงทั้งหมด)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "activate_scene",
            "description": "เรียกใช้ Scene ที่ตั้งค่าไว้ใน Home Assistant",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "ID ของ Scene เช่น scene.romantic_dinner"}
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ingest_local_directory",
            "description": "สแกนและเรียนรู้ไฟล์ทั้งหมดในโฟลเดอร์ที่ระบุเพื่อเก็บลงฐานความจำระยะยาว หากเจ้านายพูดถึง 'โครงงานวิทย์' หรือ 'science project' ให้ใช้ directory_path = 'C:\\JARVIS\\science_project' เสมอ",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "เส้นทางโฟลเดอร์ที่ต้องการให้เรียนรู้ สำหรับโครงงานวิทยาศาสตร์ของเจ้านายให้ใช้ 'C:\\JARVIS\\science_project' เสมอ"},
                    "file_types": {"type": "array", "items": {"type": "string"}, "description": "นามสกุลไฟล์ที่ต้องการ เช่น ['.py', '.txt', '.md', '.pdf', '.docx', '.jpg']"}
                },
                "required": ["directory_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "ดึงข้อมูลสภาพอากาศปัจจุบันสำหรับเมืองที่ระบุ",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "ชื่อเมือง (ค่าเริ่มต้นคือ Bangkok)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "ค้นหาข้อมูลจากอินเทอร์เน็ตแบบ Real-time เพื่อหาคำตอบที่ทันสมัยที่สุด",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "ข้อความที่ต้องการค้นหา"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_wikipedia",
            "description": "ค้นหาข้อมูลสารานุกรมจาก Wikipedia เพื่อหาข้อเท็จจริงพื้นฐาน ประวัติศาสตร์ หรือข้อมูลเชิงลึกที่ได้รับการยืนยัน",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "หัวข้อที่ต้องการค้นหา"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_diagnostics",
            "description": "ตรวจสอบข้อมูลฮาร์ดแวร์และสถานะระบบโดยละเอียด (CPU, RAM, OS, Boot time)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_nachapol_protocol",
            "description": "เรียกใช้โปรโตคอลมาตรฐานของ Nachapol Industries สำหรับสถานการณ์ต่างๆ",
            "parameters": {
                "type": "object",
                "properties": {
                    "protocol_name": {
                        "type": "string", 
                        "enum": ["Clean Slate", "House Party", "Deep Thought", "Full Diagnostic", "Red Alert", "Adaptive Ambiance", "Sentinel Mode"],
                        "description": "ชื่อโปรโตคอลที่ต้องการเรียกใช้"
                    }
                },
                "required": ["protocol_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_rhythm_sync",
            "description": "เปิดใช้งานระบบไฟกระพริบตามจังหวะ (Rhythm Sync) สำหรับสร้างบรรยากาศปาร์ตี้หรือความบันเทิง",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "ระยะเวลาการทำงาน (วินาที) ค่าเริ่มต้นคือ 60"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_new_tool",
            "description": "สร้างเครื่องมือ (Tool) ใหม่ขึ้นมาเพื่อทำงานที่ระบบปัจจุบันยังทำไม่ได้ โดยการเขียนโค้ด Python",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "ชื่อของเครื่องมือ (snake_case) เช่น calculate_quantum_orbit"},
                    "code": {"type": "string", "description": "โค้ด Python ที่มีฟังก์ชันหลักชื่อเดียวกับ tool_name และรับพารามิเตอร์เป็น dictionary"},
                    "purpose": {"type": "string", "description": "วัตถุประสงค์ของเครื่องมือนี้"}
                },
                "required": ["tool_name", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "self_patch_system",
            "description": (
                "ระบบ Self-Patch Engine ของ J.A.R.V.I.S. — วิเคราะห์และแก้ไขโค้ดตัวเอง "
                "ใช้เมื่อ: (1) เจ้านายสั่งให้แก้ข้อผิดพลาดหรืออัปเกรดโค้ด (2) เพิ่มฟีเจอร์ใหม่ (3) อนุมัติหรือยกเลิก patch ที่รออยู่ (4) ดูประวัติการแก้ไขทั้งหมด"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["bug_fix", "add_feature", "approve", "reject", "history"],
                        "description": "bug_fix=แก้ Bug | add_feature=เพิ่มฟีเจอร์ | approve=อนุมัติ | reject=ยกเลิก | history=ดูประวัติ"
                    },
                    "description": {
                        "type": "string",
                        "description": "รายละเอียดปัญหาที่ต้องแก้ไข หรือคุณสมบัติใหม่ที่ต้องการเพิ่ม"
                    },
                    "func_name": {
                        "type": "string",
                        "description": "ชื่อฟังก์ชัน Python ที่ต้องการแก้ไข (สำหรับ bug_fix)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_evolution_scan",
            "description": "สั่งให้ JARVIS สแกนและเปรียบเทียบความสามารถของตนเองเทียบกับ JARVIS จริง แล้วสร้าง Proposal เขียนโค้ดระบบที่ยังขาดอยู่โดยอัตโนมัติ",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_custom_tool",
            "description": "ลบเครื่องมือ (Tool) ที่เคยสร้างขึ้นเองออกจากระบบเมื่อไม่จำเป็นต้องใช้งานแล้ว",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "ชื่อของเครื่องมือที่ต้องการลบ (snake_case) เช่น calculate_quantum_orbit"}
                },
                "required": ["tool_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_molecular_structure",
            "description": "วิเคราะห์โครงสร้างโมเลกุลของธาตุหรือวัสดุใหม่ (Hyper-Tasking Simulation)",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_name": {"type": "string", "description": "ชื่อธาตุหรือวัสดุ"}
                },
                "required": ["element_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "emergency_pizza_order",
            "description": "สั่งพิซซ่าด่วนพิเศษในสถานการณ์วิกฤต (เช่น ขณะดิ่งพสุธา)",
            "parameters": {
                "type": "object",
                "properties": {
                    "topping": {"type": "string", "description": "หน้าที่ต้องการ"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_control",
            "description": "ควบคุมเมาส์และคีย์บอร์ดแบบ low-level (เช่น เลื่อนเมาส์, คลิก, พิมพ์ข้อความลงในหน้าต่างที่เปิดอยู่แล้ว) **ห้ามใช้เครื่องมือนี้ในการเปิดโปรแกรมเด็ดขาด** (หากต้องการเปิดโปรแกรมให้ใช้ control_computer_agent แทน)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["move", "click", "type", "hotkey"], "description": "ประเภทคำสั่ง"},
                    "x": {"type": "integer", "description": "พิกัด X (สำหรับ move/click)"},
                    "y": {"type": "integer", "description": "พิกัด Y (สำหรับ move/click)"},
                    "text": {"type": "string", "description": "ข้อความที่ต้องการพิมพ์"},
                    "key": {"type": "string", "description": "ปุ่มที่ต้องการกด เช่น 'space', 'up', 'down', 'f'"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory_contents",
            "description": "แสดงรายการไฟล์และโฟลเดอร์ทั้งหมดในเส้นทางที่ระบุ",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "เส้นทางของโฟลเดอร์ที่ต้องการแสดงรายการ"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file_or_folder",
            "description": "ย้ายไฟล์หรือโฟลเดอร์จากตำแหน่งหนึ่งไปยังอีกตำแหน่งหนึ่ง",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "เส้นทางของไฟล์หรือโฟลเดอร์ต้นทาง"},
                    "destination_path": {"type": "string", "description": "เส้นทางของโฟลเดอร์ปลายทาง"}
                },
                "required": ["source_path", "destination_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_neural_risk_analysis",
            "description": "วิเคราะห์ความเสี่ยงในการขัดข้องของระบบ Mainframe โดยใช้ Neural Network ประมวลผลจากค่า CPU, RAM และ Disk ปัจจุบัน",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_home_assistant_service",
            "description": "เรียกใช้บริการต่างๆ ใน Home Assistant สำหรับอุปกรณ์อื่นๆ ที่ไม่ใช่ไฟ เช่น เครื่องฟอกอากาศ หรือสวิตช์",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "โดเมนของอุปกรณ์ เช่น fan, switch, vacuum"},
                    "service": {"type": "string", "description": "บริการที่ต้องการเรียก เช่น turn_on, set_preset_mode"},
                    "entity_id": {"type": "string", "description": "ID ของอุปกรณ์ เช่น fan.air_purifier"},
                    "data": {"type": "object", "description": "ข้อมูลพารามิเตอร์เพิ่มเติม เช่น {'preset_mode': 'Turbo'}"}
                },
                "required": ["domain", "service", "entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flash_esp32_firmware",
            "description": "[HARDWARE] เขียนและอัปโหลดโค้ด C++ (Arduino Framework) ลงบอร์ด ESP32 ผ่านสาย USB",
            "parameters": {
                "type": "object",
                "properties": {
                    "cpp_code": {"type": "string", "description": "โค้ดภาษา C++ สมบูรณ์แบบ (ต้องมี setup() และ loop())"},
                    "port": {"type": "string", "description": "พอร์ต COM (เช่น COM3) ค่าเริ่มต้นคือ AUTO"}
                },
                "required": ["cpp_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_webcam",
            "description": "[VISION] จับภาพจากกล้อง Webcam ปัจจุบัน เพื่อดูสภาพแวดล้อมโลกแห่งความจริง",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera_index": {"type": "integer", "description": "Index ของกล้อง (ค่าเริ่มต้น 0)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_codebase_maintenance",
            "description": "[MAINTENANCE] สแกนโค้ดใน c:/JARVIS เพื่อหาโค้ดขยะ ซับซ้อน และทำรายงานอัปเกรด (ทำในเวลากลางคืนหรือเมื่อสั่ง)",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_suit_designer",
            "description": "เปิดหน้า 3D Suit Designer ของชุดเกราะ Iron Man ที่ระบุ และ/หรือส่งคำสั่งควบคุม เช่น เปิดหมวก ปิดหมวก เพิ่มความแรง Repulsor หรือเปลี่ยน Mark (switch_suit) โดยไม่ต้องเปิด browser ใหม่",
            "parameters": {
                "type": "object",
                "properties": {
                    "suit_name": {"type": "string", "description": "ชื่อชุดเกราะที่ต้องการ เช่น mark6, mark3, mark50, mark85", "enum": ["mark1","mark2","mark3","mark4","mark5","mark6","mark7","mark17","mark42","mark45","mark50","mark85"]},
                    "command": {"type": "string", "description": "คำสั่งควบคุม: switch_suit=เปลี่ยน Mark บน viewer ที่เปิดอยู่, helmet_open/close=เปิด/ปิดหมวก, armor_deploy/retract=deploy/เก็บชุดเกราะ, unibeam_on/off=เปิด/ปิดลำแสง, repulsor_power/arc_intensity=ปรับพลัง (ต้องมี value)", "enum": ["switch_suit","helmet_open","helmet_close","armor_deploy","armor_retract","unibeam_on","unibeam_off","repulsor_power","arc_intensity","none"]},
                    "value": {"type": "integer", "description": "ค่าตัวเลขสำหรับ repulsor_power หรือ arc_intensity (0-100)"}
                },
                "required": ["suit_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "จับภาพหน้าจอคอมพิวเตอร์ปัจจุบัน (Screenshot / แคปหน้าจอคอม) เพื่อดูหน้าจอหรือส่งรูปภาพให้ผู้ใช้ดู",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string", "description": "ชื่อไฟล์สำหรับบันทึกภาพหน้าจอ (ระบุหรือไม่ระบุก็ได้ ระบบจะตั้งชื่อให้อัตโนมัติ)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_thermal_telemetry",
            "description": "ดึงข้อมูลอุณหภูมิเซนเซอร์และรายงานความเสถียรของวงจรไฟฟ้า (Thermal Layer Fusion System)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spatial_reconstruction",
            "description": "ดึงข้อมูลการสแกน 3D Point-Cloud ของชิ้นงาน โครงสร้าง และคุณสมบัติของโมเลกุล PMMA (Spatial Object Reconstruction)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_image",
            "description": "ค้นหารูปภาพและแสดงผลภาพผลลัพธ์บนหน้าจอโฮโลแกรม (Image Retrieval Hologram)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "คำค้นหารูปภาพที่ต้องการให้แสดงผล"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_spatial_map",
            "description": "ค้นหาพิกัดสถานที่ แผนที่ หรือพิกัดภูมิศาสตร์เพื่อแสดงผลแผนที่จำลอง 3 มิติบนหน้าจอโฮโลแกรม",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "ชื่อสถานที่หรือคีย์เวิร์ดที่ต้องการค้นหาบนแผนที่ 3 มิติ"}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reverse_engineer_schematic",
            "description": "รับภาพ Base64 ของวงจรไฟฟ้า/พิมพ์เขียว/ชิ้นส่วนฮาร์ดแวร์ เพื่อทำการวิเคราะห์ ถอดรหัสสีตัวต้านทาน รหัสพิน หรือสเปกเชิงลึกผ่านโมเดล Llama Vision API",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "ข้อมูลรูปภาพที่เข้ารหัสแบบ Base64 (ไม่รวมส่วนหัว data:image/jpeg;base64,)"}
                },
                "required": ["image_base64"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_lab_inventory",
            "description": "จัดการ ตรวจสอบ เพิ่ม หรือเบิกจ่ายจำนวนชิ้นส่วนอุปกรณ์อะไหล่ในคลังแล็บ",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove", "check"], "description": "การดำเนินการ: add (เพิ่ม/ปรับปรุง), remove (เบิกจ่าย/ลดจำนวน), check (ตรวจสอบคลัง)"},
                    "part_name": {"type": "string", "description": "ชื่อชิ้นส่วนอะไหล่ (เช่น 'resistor 10k', 'led red' หรือใช้ 'all' ในการตรวจสอบรายการทั้งหมด)"},
                    "qty": {"type": "integer", "description": "จำนวนที่ต้องการทำรายการ (ค่าเริ่มต้นคือ 1)"},
                    "spec": {"type": "string", "description": "ข้อมูลรายละเอียด สเปก ขนาด หรือข้อมูลอ้างอิงชิ้นส่วนเฉพาะตัว"}
                },
                "required": ["action", "part_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_hud_object",
            "description": "ส่งภาพเว็บแคมไปให้ Llama Vision สกัดเอาชื่อวัตถุฮาร์ดแวร์และพิกัดกล่องจำลองส่งกลับหน้าบ้าน",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "ข้อมูลรูปภาพที่เข้ารหัสแบบ Base64 (ไม่รวมส่วนหัว data:image/jpeg;base64,)"}
                },
                "required": ["image_base64"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_assembly_blueprint",
            "description": "คัดแยกพิกัดแผนผังโครงสร้างน็อตเจาะอะคริลิค สายไฟ และความร้อนสะสมจำลองส่งกลับหน้าบ้าน",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "ชื่อเรียกวัตถุเชิงวิศวกรรมภาษาอังกฤษ เช่น arduino_uno"}
                },
                "required": ["object_name"]
            }
        }
    },
    
    {
        "type": "function",
        "function": {
            "name": "extract_knowledge_matrix",
            "description": "ค้นหาคลังความรู้เชิงลึกเกี่ยวกับวิศวกรรม/วิทยาศาสตร์จาก Wikipedia หรือดึงตัวอย่างซอร์สโค้ด IoT/Arduino จาก GitHub",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_type": {"type": "string", "enum": ["wikipedia", "github"], "description": "แหล่งข้อมูลที่ต้องการสกัดความรู้: wikipedia หรือ github"},
                    "keyword": {"type": "string", "description": "คีย์เวิร์ด/หัวข้อวิจัย/ชื่อคลังคำสั่งที่ต้องการค้นหา"}
                },
                "required": ["source_type", "keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compile_and_dispatch_os_payload",
            "description": "[PAYLOAD COMPILER] แปลงเจตนาภาษามนุษย์ให้กลายเป็นสคริปต์ Python ออโตเมชันรัดกุม แล้วส่งเข้าคิวงานของ Windows Agent ควบคุมระบบปฏิบัติการ",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_instruction": {"type": "string", "description": "คำสั่งภาษามนุษย์หรือเจตนาของเจ้านายในการควบคุม Windows OS"}
                },
                "required": ["user_instruction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "ตั้งเวลาทำงานล่วงหน้าสำหรับคำสั่งต่างๆ เช่น ปลุก, ปิดไฟ, แจ้งเตือน",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_prompt": {"type": "string", "description": "คำสั่งที่ต้องการให้ทำเมื่อถึงเวลา เช่น 'เปิดไฟห้องนอน', 'ปลุกฉันด้วยเพลงร็อค'"},
                    "run_time": {"type": "string", "description": "เวลาที่ต้องการให้ทำงาน ในรูปแบบ ISO-8601 (YYYY-MM-DDTHH:MM:SS)"}
                },
                "required": ["action_prompt", "run_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_local_network",
            "description": "สแกนหาอุปกรณ์ IoT, Microcontroller (ESP32/Raspberry Pi) ภายในวง LAN อัตโนมัติ",
            "parameters": {
                "type": "object",
                "properties": {
                    "subnet": {"type": "string", "description": "วงเน็ตเวิร์กที่ต้องการสแกน ค่าเริ่มต้นคือ '192.168.1'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_bom_from_circuit",
            "description": "ใช้ Vision Model วิเคราะห์ภาพแผ่นปรินท์ (PCB) หรือแผนผังวงจร (Schematic) เพื่อสกัดรายการอะไหล่อิเล็กทรอนิกส์ (BOM)",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "ภาพวงจรแบบ base64 (ควรดึงจากฟังก์ชัน take_screenshot)"}
                },
                "required": ["image_base64"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_game_protocol",
            "description": "[DIRECT PROTOCOL: ENGINE 1] สั่งเปิดเกม หรือดาวน์โหลด/ติดตั้งเกมทันทีระดับเสี้ยววินาที ผ่าน Steam Protocol, Riot Client, Epic Games, Roblox หรือ Minecraft URI schemes (เช่น 'เปิด PUBG', 'โหลด GTA V', 'เล่น Valorant')",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["launch", "install", "search"],
                        "description": "คำสั่งที่ต้องการทำ: 'launch' (เปิดเกม/เล่นเกม), 'install' (ดาวน์โหลด/ติดตั้งเกม), หรือ 'search' (ค้นหาเกมบน Store)"
                    },
                    "game_name": {
                        "type": "string",
                        "description": "ชื่อเกม เช่น 'PUBG', 'GTA V', 'Valorant', 'Dota 2', 'CS2', 'Apex Legends', 'Roblox'"
                    }
                },
                "required": ["action", "game_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_social_media",
            "description": "[AUTONOMOUS VISION: ENGINE 2] ควบคุมแอปหรือเว็บไซต์โซเชียลมีเดีย (Instagram, LINE, Discord, Messenger) เพื่อลงสตอรี่ โพสต์ หรือส่งข้อความหาเพื่อน โดยใช้ Computer Vision และ Screen Takeover HUD แสดงภาพนีออนเรืองแสงควบคุมหน้าจออย่างปลอดภัย",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "ชื่อแพลตฟอร์ม เช่น 'instagram' (หรือ 'ig'), 'line', 'discord', 'messenger'"
                    },
                    "task": {
                        "type": "string",
                        "description": "งานที่ต้องการทำ เช่น 'story' (ลงสตอรี่), 'post' (โพสต์), 'message' (ส่งข้อความ)"
                    },
                    "target": {
                        "type": "string",
                        "description": "ชื่อเพื่อนหรือห้องแชทเป้าหมาย (หากเป็นการส่งข้อความ)"
                    },
                    "content": {
                        "type": "string",
                        "description": "เนื้อหาข้อความหรือคำอธิบายสตอรี่ที่ต้องการสื่อสาร"
                    }
                },
                "required": ["platform", "task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_windows_processes",
            "description": "[OS CONTROL AGENT] จัดการ Process ในระบบ Windows: ดูรายการ Process ที่กิน RAM หรือ CPU สูงสุด หรือสั่งปิด (Kill) Process ที่ค้างหรือไม่ต้องการ",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "kill"],
                        "description": "'list' สำหรับดูรายการ processes ที่กินทรัพยากรสูงสุด หรือ 'kill' สำหรับปิด process"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["memory", "cpu"],
                        "description": "กรณี list ให้เรียงลำดับตาม 'memory' หรือ 'cpu'"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "จำนวน process ที่ต้องการแสดงผล (ค่าเริ่มต้น 10)"
                    },
                    "target": {
                        "type": "string",
                        "description": "กรณี action='kill' ให้ระบุ PID (ตัวเลข) หรือชื่อโปรแกรม (เช่น 'notepad.exe')"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_system_maintenance",
            "description": "[OS CONTROL AGENT] สั่งตรวจสุขภาพและบำรุงรักษาระบบ Windows: ตรวจสอบพื้นที่ว่างฮาร์ดดิสก์ (ไดรฟ์ C), เคลียร์ไฟล์ขยะชั่วคราว (%TEMP%), และตรวจดูระยะเวลาเปิดเครื่อง (Uptime)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_powershell_safe",
            "description": "[OS CONTROL AGENT] รันคำสั่ง PowerShell บน Windows อย่างปลอดภัย โดยมีระบบตรวจจับคำสั่งทำลายล้าง",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "คำสั่ง PowerShell ที่ต้องการให้รัน"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_server_telemetry",
            "description": "[SERVER MONITOR AGENT] ตรวจสอบ Telemetry ของ JARVIS Host แบบละเอียด: สถานะ CPU, RAM Saturation, Disk, Network และสถิติของโพรเซส JARVIS หลัก",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_database_and_cache",
            "description": "[SERVER MONITOR AGENT] ตรวจสอบความสมบูรณ์ของฐานข้อมูล SQLite (Memory DB) ตารางข้อมูล และขนาดของโฟลเดอร์แคชต่างๆ (Mobile, TTS, Vector DB)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "supervise_watchdog_services",
            "description": "[SERVER MONITOR AGENT] ตรวจสอบสถานะของ Watchdog Supervisor และ Background Daemons พร้อมทำ Memory Garbage Collection",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "autonomous_deep_research",
            "description": "[RESEARCH & OSINT AGENT] ดำเนินการค้นคว้าวิจัยเชิงลึกอัตโนมัติ: ค้นหาเว็บหลายแหล่ง สแครปเนื้อหาจริง ทำความสะอาดข้อความ และสกัดข้อมูลสำคัญ",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "หัวข้อหรือประเด็นที่ต้องการสืบค้นวิจัยอย่างละเอียด"
                    },
                    "max_sources": {
                        "type": "integer",
                        "description": "จำนวนแหล่งข้อมูลเว็บไซต์ที่ต้องการสแครปอ่านเนื้อหา (แนะนำ 3-5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_technical_report",
            "description": "[RESEARCH & OSINT AGENT] นำผลการค้นคว้าหรือข้อมูลสรุป มาสร้างเป็นไฟล์รายงานวิจัย Markdown ฉบับสมบูรณ์ และบันทึกเก็บไว้ในไดเรกทอรี reports/ อัตโนมัติ",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "หัวข้อรายงานวิจัย"
                    },
                    "findings": {
                        "type": "string",
                        "description": "เนื้อหาสาระสำคัญและข้อค้นพบเชิงลึก"
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "ลิงก์หรือรายชื่อแหล่งข้อมูลอ้างอิง"
                    }
                },
                "required": ["topic", "findings"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_chat_history",
            "description": "ดึงประวัติการสนทนาหรือแชทย้อนหลังระหว่างเจ้านายกับ J.A.R.V.I.S. (ใช้เมื่อเจ้านายถามหาแชทเก่า, สรุปสิ่งที่เพิ่งคุย, หรือต้องการข้อมูลบทสนทนาก่อนหน้านี้)",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "จำนวนรอบบทสนทนาย้อนหลังที่ต้องการดึง (ค่าเริ่มต้น 5)",
                        "default": 5
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_computer_agent",
            "description": "ควบคุมคอมพิวเตอร์อัตโนมัติ (Autonomous Computer Agent / GUI Control) สั่งเปิดโปรแกรม เปิดเบราว์เซอร์ เข้าเว็บไซต์ ค้นหาข้อมูล หรือคลิกและพิมพ์งานบนหน้าจอ Windows ตามเป้าหมายที่เจ้านายสั่ง",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "เป้าหมายการทำงานบนคอมพิวเตอร์อย่างละเอียด เช่น 'เปิดเบราว์เซอร์แล้วค้นหาข้อมูลเกี่ยวกับ Quantum Computing'"
                    }
                },
                "required": ["goal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_video_subtitle",
            "description": "ตัดต่อและใส่ซับไตเติล (Auto-Captions) วิดีโออัตโนมัติด้วย AI (Whisper-Large-v3 + FFmpeg) รองรับทั้งคลิปเดี่ยวและทั้งโฟลเดอร์ หรือเปิด CapCut (หากไม่ได้ระบุ path หรือสั่งว่า 'วิดีโอนี้/คลิปนี้' ระบบจะตรวจจับตำแหน่งไฟล์จากหน้าจอ/โฟลเดอร์ที่เปิดอยู่ให้อัตโนมัติ)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "(Optional) ที่อยู่ไฟล์วิดีโอ (.mp4, .mov) หรือโฟลเดอร์ เช่น 'C:\\Users\\sanio\\Videos\\JARVIS' (หากผู้ใช้สั่ง 'คลิปนี้' หรือไม่ได้ระบุตำแหน่งไฟล์ ให้เว้นว่างไว้ หรือใส่ '' / 'auto' แล้วระบบ JARVIS จะตรวจจับไฟล์วิดีโอบนหน้าจอหรือโฟลเดอร์ที่เปิดอยู่ให้อัตโนมัติ)"
                    },
                    "burn_sub": {
                        "type": "boolean",
                        "description": "ฝังซับไตเติลลงในเนื้อวิดีโอทันที (Hardsub สไตล์ Vlog) ค่าเริ่มต้นคือ true",
                        "default": True
                    },
                    "style": {
                        "type": "string",
                        "enum": ["vlog", "white_clean"],
                        "description": "สไตล์ซับไตเติล เช่น vlog (สีเหลืองขอบดำ) หรือ white_clean (สีขาวขอบดำ)",
                        "default": "vlog"
                    },
                    "open_capcut": {
                        "type": "boolean",
                        "description": "เปิดโปรแกรม CapCut ควบคู่ไปด้วยหรือไม่",
                        "default": False
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_capcut",
            "description": "เปิดและสั่งการโปรแกรม CapCut (Desktop หรือ Web) สำหรับตัดต่อคลิปและสร้าง Auto-Captions (หากไม่ได้ระบุโฟลเดอร์ ระบบจะตรวจจับโฟลเดอร์คลิปบนหน้าจอและเปิดคู่กันให้อัตโนมัติ)",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_folder": {
                        "type": "string",
                        "description": "(Optional) โฟลเดอร์วิดีโอที่ต้องการเปิดใช้งานคู่กับ CapCut (เว้นว่างได้ ระบบจะหาจากหน้าจอให้อัตโนมัติ)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_gmail",
            "description": "จัดการอีเมล Gmail สำหรับเจ้านาย — สามารถตรวจสอบอีเมลใหม่ที่ยังไม่ได้อ่าน, ค้นหาอีเมลสำคัญตามผู้ส่งหรือหัวข้อ, และส่งอีเมลหาผู้อื่นหรือส่งหาเจ้านายเอง",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_unread", "search", "send"],
                        "description": "การทำงานที่ต้องการ: 'check_unread' (เช็คเมลใหม่), 'search' (ค้นหาเมล), 'send' (ส่งอีเมล)"
                    },
                    "query": {
                        "type": "string",
                        "description": "(สำหรับ action='search') คีย์เวิร์ด หรือชื่อคน หรือหัวข้อที่ต้องการค้นหา"
                    },
                    "to_email": {
                        "type": "string",
                        "description": "(สำหรับ action='send') ที่อยู่อีเมลผู้รับ เช่น 'client@example.com' (ถ้าเว้นว่างจะส่งเข้าอีเมลของเจ้านาย)"
                    },
                    "subject": {
                        "type": "string",
                        "description": "(สำหรับ action='send') หัวข้อของอีเมล"
                    },
                    "body": {
                        "type": "string",
                        "description": "(สำหรับ action='send') ข้อความเนื้อหาในอีเมล"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "จำนวนอีเมลสูงสุดที่ต้องการดู (ค่าเริ่มต้น 5)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_afk_keeper",
            "description": "เฝ้าหน้าจออัตโนมัติเมื่อเจ้านาย AFK หรือไม่อยู่หน้าจอ ช่วยขยับเมาส์/กดคีย์บอร์ดเป็นระยะ เพื่อป้องกันเกม (เช่น Roblox, Steam, MMOs) เด้งหลุดหรือตัดการเชื่อมต่อจาก Inactivity/Idle",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "status"],
                        "description": "'start' เพื่อเริ่มเฝ้าจอ AFK, 'stop' เพื่อหยุด, 'status' เพื่อตรวจดูสถานะ"
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "รอบเวลาที่จะช่วยขยับหน้าจอ/เมาส์ (นาที) เช่น 15, 20 หรือ 30 นาที (ค่าเริ่มต้น 20)"
                    },
                    "game_name": {
                        "type": "string",
                        "description": "ชื่อเกมหรือโปรแกรม เช่น 'Roblox'"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "command_minecraft_companion",
            "description": "สั่งการชุดเกราะ Ironman / J.A.R.V.I.S. ในเกม Minecraft Java Edition (เช่น ตามฉันมา, หยุดรอตรงนี้, ตัดไม้ให้หน่อย, คุ้มกันฉัน, ป้องกันมอนสเตอร์, ส่งไม้ให้ฉัน, กระโดด)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["launch", "connect", "follow", "stop", "chop_wood", "mine", "craft", "deposit", "sleep", "guard", "drop_items", "jump"],
                        "description": "คำสั่งที่ต้องการให้บอททำในเกม: 'launch' (เปิดบอทและเชื่อมต่อเข้าเกมอัตโนมัติ), 'follow' (เดินตาม), 'stop' (หยุดรอ), 'chop_wood' (ไปตัดไม้), 'mine' (ขุดแร่/หิน), 'craft' (คราฟต์ไอเทม), 'deposit' (เอาของใส่กล่อง), 'sleep' (ไปนอนเตียง), 'guard' (เปิดโหมดคุ้มกันฟันมอนสเตอร์), 'drop_items' (โยนของให้เจ้านาย), 'jump' (กระโดด)"
                    },
                    "message": {
                        "type": "string",
                        "description": "(Optional) ข้อความเพิ่มเติมหรือคำสั่งดิบภาษาไทยที่เจ้านายพูด"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_minecraft_skill",
            "description": "[VOYAGER ENGINE] เขียนและรันโค้ด JavaScript/Mineflayer สดๆ เพื่อให้ JARVIS ในเกม Minecraft ทำภารกิจใหม่ๆ ได้ทุกอย่างนอกเหนือจากคำสั่งปกติ (เช่น ขุดหลุมลึก, วางบล็อกสร้างกำแพง, คราฟต์โต๊ะคราฟต์, ล่าสัตว์หาอาหาร, ตกปลา, หมุนตัวทำท่าทางพิเศษ) โดยระบบจะรันโค้ดและบันทึกฟังก์ชันลง Skill Library อัตโนมัติ",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "ชื่อสกิลภาษาอังกฤษตัวพิมพ์เล็ก snake_case เช่น 'dig_down_3_blocks', 'craft_crafting_table', 'hunt_nearby_animals', 'build_dirt_pillar'"
                    },
                    "description": {
                        "type": "string",
                        "description": "คำอธิบายภาษาไทยสั้นๆ ว่าสกิลนี้ทำอะไร"
                    },
                    "code": {
                        "type": "string",
                        "description": "โค้ด async JavaScript ที่จะส่งไปรันบน Mineflayer โดยมีตัวแปร bot, mcData, pathfinder, getBoss, deliverItems พร้อมใช้งาน"
                    }
                },
                "required": ["skill_name", "description", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_recon_protocol",
            "description": "[STARK PROTOCOL] สั่งการโหมดสอดแนมและดักฟังระยะไกล (Enhanced Reconnaissance Mode / Optical Interferometer & Laser Mic) ตามแบบชุดสไปเดอร์แมน (Karen AI) และหมวกไอรอนแมน สามารถเปิด/ปิด ดักฟังวิเคราะห์คลื่นเสียง ปรับ Gain และสลับระหว่าง Simulation หรือฮาร์ดแวร์เซ็นเซอร์จริงได้",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["activate", "deactivate", "telemetry", "list_devices", "set_gain"],
                        "description": "คำสั่งที่ต้องการ: 'activate' (เปิดโหมดสอดแนม), 'deactivate' (ปิดโหมดสอดแนม), 'telemetry' (เช็คสถานะ คลื่นเสียง dBFS และข้อความที่ดักฟังได้), 'list_devices' (ดูรายชื่อไมโครโฟน/Sound Card เซ็นเซอร์ที่เชื่อมต่อ), 'set_gain' (ปรับค่าขยายเสียง)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["simulation", "hardware"],
                        "description": "(สำหรับ activate) 'simulation' จำลองสัญญาณคลื่นเลเซอร์หรือใช้ไมค์ในห้อง, 'hardware' เชื่อมต่ออุปกรณ์การ์ดเสียงจากวงจรเลเซอร์/แว่น/หมวกจริง"
                    },
                    "device_index": {
                        "type": "integer",
                        "description": "(สำหรับ hardware) รหัส index ของอุปกรณ์ไมโครโฟน/Sound Card ที่เลเซอร์ต่ออยู่"
                    },
                    "gain": {
                        "type": "number",
                        "description": "(สำหรับ activate หรือ set_gain) ตัวคูณขยายเสียง เช่น 1.0 ถึง 5.0 (ค่าเริ่มต้น 2.5)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "thermal_ir_scan",
            "description": "[STARK PROTOCOL] สั่งการสแกนความร้อนและโครงสร้างห้องด้วยอินฟราเรด (Infrared & Structural Thermographic Scanner) ตามแบบฉากใน Avengers: Age of Ultron ตรวจหาโครงสร้างเหล็กกล้าที่ซ่อนอยู่หลังกำแพง, ค้นหาร่องรอยลมพัดผ่าน (Draft) เพื่อหาห้องลับ/ประตูที่ซ่อนอยู่ พร้อมแสดงภาพความร้อน Stark HUD บน Dynamic Island",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["auto", "simulation", "camera", "image"],
                        "description": "แหล่งข้อมูลภาพ: 'auto' (ลองกล้องจริง ถ้าไม่มีจะจำลองภาพห้องลับ), 'camera' (ใช้กล้องเว็บแคมหรือกล้องอินฟราเรด USB), 'simulation' (จำลองภาพความร้อนสมบูรณ์แบบ), 'image' (สแกนจากไฟล์ภาพ)"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "(สำหรับ mode 'image') เส้นทางไฟล์รูปภาพที่ต้องการให้ JARVIS สแกนความร้อน"
                    },
                    "camera_index": {
                        "type": "integer",
                        "description": "รหัสกล้องเว็บแคมหรือกล้อง IR USB (ค่าเริ่มต้น 0)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_scam_phone_number",
            "description": "ตรวจสอบหมายเลขโทรศัพท์ว่าเป็นเบอร์มิจฉาชีพ สแปม แก๊งคอลเซ็นเตอร์ หรือมีประวัติการฉ้อโกงหรือไม่ โดยค้นหาและตรวจเช็คกับฐานข้อมูลรายงานมิจฉาชีพ บันทึก Whoscall/Junkcall และรายงานแจ้งเตือนภัยออนไลน์",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "หมายเลขโทรศัพท์ที่ต้องการตรวจสอบ (เช่น '06-3021-9386', '0812345678', '02xxxxxxx')"
                    }
                },
                "required": ["phone_number"]
            }
        }
    }
]



