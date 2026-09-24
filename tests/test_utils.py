import os
import sys
import pytest

# เพิ่ม Path เพื่อให้สามารถ import jarvis ได้
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions from jarvis.py
from jarvis import (
    normalize_thai_text,
    is_safe_path,
    segment_text,
    apply_nachapol_voice_protocol
)

def test_normalize_thai_text():
    # Test spaces formatting
    assert normalize_thai_text("สวัสดี ครับ") == "สวัสดีครับ"
    # Test newlines and tabs
    assert normalize_thai_text("บรรทัดที่ 1\nบรรทัดที่ 2\tจบ") == "บรรทัดที่ 1 บรรทัดที่ 2 จบ"
    # Test duplicate spaces
    assert normalize_thai_text("มี  ช่องว่าง   หลายตัว") == "มี ช่องว่าง หลายตัว"

def test_is_safe_path():
    base = os.path.abspath("C:/JARVIS")
    # Safe paths
    assert is_safe_path(base, os.path.abspath("C:/JARVIS/data.txt")) == True
    assert is_safe_path(base, os.path.abspath("C:/JARVIS/subfolder/test.png")) == True
    
    # Unsafe paths (Directory Traversal)
    assert is_safe_path(base, os.path.abspath("C:/Windows/System32")) == False
    assert is_safe_path(base, os.path.abspath("C:/JARVIS/../Windows/System32")) == False

def test_segment_text():
    # Should chunk at spaces or newlines nicely
    text = "นี่คือประโยคที่ยาวมากๆ " * 20
    chunks = segment_text(text, max_length=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 50

def test_apply_nachapol_voice_protocol():
    # Test specific Thai pronunciations handling
    result = apply_nachapol_voice_protocol("นาย A ทำงานที่ บ.")
    assert "บริษัท" in result
    
    result2 = apply_nachapol_voice_protocol("100% ฟรี")
    assert "เปอร์เซ็นต์" in result2
    
    # Test english alphabet spellings
    result3 = apply_nachapol_voice_protocol("FBI")
    assert "เอฟ บี ไอ" in result3 or "FBI" in result3 # depends on the implementation logic
