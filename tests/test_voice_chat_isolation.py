import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from jarvis import app, handle_chat_logic, save_history_to_file

def test_voice_chat_isolation():
    dirty_history = [
        {"role": "user", "content": "[รูปภาพจากเจ้านาย] วิเคราะห์รูปนี้ให้หน่อย"},
        {"role": "assistant", "content": "ภาพนี้เป็นภาพอาหารและโต๊ะอาหารครับเจ้านาย"},
        {"role": "user", "content": "กินข้าวกัน"},
        {"role": "assistant", "content": "ยินดีด้วยครับ ขอให้อร่อยกับมื้ออาหารครับเจ้านาย"}
    ]
    save_history_to_file(dirty_history)
    
    with app.test_request_context():
        # Normal command: should NOT leak old chat
        res = handle_chat_logic({
            "message": "จาร์วิส นับประมวลผลตอนนี้เป็นยังไงบ้าง",
            "voice_mode": True,
            "silent": True
        })
        json_data = res.get_json()
        assert json_data is not None, "Response JSON is None"
        response_text = json_data.get("response", "")
        print(f"[TEST 1: ISOLATION] Voice Response: {response_text}")
        
        assert "กินข้าว" not in response_text, "Old chat history leaked into voice response!"
        assert "โต๊ะอาหาร" not in response_text, "Old image context leaked into voice response!"
        assert "[VOICE MODE OVERRIDE]" not in response_text, "Rogue meta-tag leaked into response!"
        print("SUCCESS: Voice isolation test PASSED!")

def test_voice_chat_recall_on_demand():
    sample_history = [
        {"role": "user", "content": "โปรเจกต์หุ่นยนต์ Arduino Uno เสร็จหรือยัง"},
        {"role": "assistant", "content": "วงจรเสร็จเรียบร้อยแล้วครับเจ้านาย กำลังรอทดสอบเฟิร์มแวร์"}
    ]
    save_history_to_file(sample_history)
    
    with app.test_request_context():
        # User explicitly asks for past chat
        res = handle_chat_logic({
            "message": "จาร์วิส สรุปที่คุยก่อนหน้านี้ให้ฟังหน่อย",
            "voice_mode": True,
            "silent": True
        })
        json_data = res.get_json()
        assert json_data is not None, "Response JSON is None"
        response_text = json_data.get("response", "")
        print(f"[TEST 2: RECALL ON DEMAND] Voice Recall: {response_text}")
        
        # Verify it recalled the requested topic
        assert any(term in response_text for term in ["หุ่นยนต์", "Arduino", "วงจร", "โปรเจกต์", "เฟิร์มแวร์"]), "Failed to recall requested chat history!"
        print("SUCCESS: Chat history on-demand recall test PASSED!")

if __name__ == "__main__":
    test_voice_chat_isolation()
    test_voice_chat_recall_on_demand()
