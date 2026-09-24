import asyncio
import os
import edge_tts
from jarvis_stt_local import transcribe_audio


async def main():
    print("1. Generating test audio...")
    text = "สวัสดีครับจาร์วิส นี่คือการทดสอบระบบหูฟัง"
    communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural")
    await communicate.save("test_audio.mp3")

    print("2. Transcribing with Faster-Whisper...")
    result = transcribe_audio("test_audio.mp3")
    print(f"Result: {result}")

    if os.path.exists("test_audio.mp3"):
        os.remove("test_audio.mp3")


if __name__ == "__main__":
    asyncio.run(main())
