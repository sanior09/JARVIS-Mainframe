import ctypes
import time

TOOL_SCHEMA = {
    "name": "media_controller",
    "description": "ควบคุมสื่อบันเทิงและระดับเสียงของคอมพิวเตอร์ (Play, Pause, Next, Prev, VolUp, VolDown, Mute)",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "คำสั่ง: play_pause, next, prev, vol_up, vol_down, mute"
            }
        },
        "required": ["action"]
    }
}

def execute(action: str) -> str:
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3

    action_map = {
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "vol_up": VK_VOLUME_UP,
        "vol_down": VK_VOLUME_DOWN,
        "mute": VK_VOLUME_MUTE
    }

    vk_code = action_map.get(action.lower().replace(" ", "_").replace("-", "_"))
    
    # NLP fallback mappings
    if not vk_code:
        if action in ["เล่น", "หยุด", "play", "pause"]:
            vk_code = VK_MEDIA_PLAY_PAUSE
        elif action in ["เพิ่มเสียง", "ดังขึ้น", "up"]:
            vk_code = VK_VOLUME_UP
        elif action in ["ลดเสียง", "เบาลง", "down"]:
            vk_code = VK_VOLUME_DOWN
        elif action in ["ปิดเสียง", "mute"]:
            vk_code = VK_VOLUME_MUTE
        elif action in ["ข้าม", "เพลงต่อไป", "next"]:
            vk_code = VK_MEDIA_NEXT_TRACK
        elif action in ["ย้อนกลับ", "เพลงก่อนหน้า", "prev"]:
            vk_code = VK_MEDIA_PREV_TRACK

    if not vk_code:
        return f"ไม่รู้จักคำสั่ง Media Control: {action}"

    # Press the media key virtually
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

    return f"สั่งการ Media Control: {action} เรียบร้อยแล้วครับ"
