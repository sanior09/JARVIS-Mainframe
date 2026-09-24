import speech_recognition as sr
import audioop
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

mics = sr.Microphone.list_microphone_names()
print("=" * 60)
print(" 🎙️ เครื่องมือค้นหาไมโครโฟนอัตโนมัติ 🎙️")
print("=" * 60)
print(">>> โปรดส่งเสียงพูด (ฮัลโหลๆ) หรือเคาะไมค์ ระหว่างที่ระบบกำลังสแกน... <<<\n")

for i, name in enumerate(mics):
    if "Voicemeeter" not in name and "CABLE" not in name and "Steam Streaming" not in name:
        print(f"ทดสอบเบอร์ [{i:3d}] {name[:30]:<30} ... ", end="", flush=True)
        try:
            mic = sr.Microphone(device_index=i)
            with mic as source:
                max_rms = 0
                for _ in range(15):
                    buffer = source.stream.read(source.CHUNK)
                    rms = audioop.rms(buffer, source.SAMPLE_WIDTH)
                    if rms > max_rms:
                        max_rms = rms
                
                if max_rms > 10:
                    print(f"🟢 มีเสียง! (ความดัง: {max_rms}) => 🎉 เอาเบอร์นี้ไปใช้ได้เลย!")
                elif max_rms > 0:
                    print(f"🟡 เสียงเบามาก (ความดัง: {max_rms})")
                else:
                    print(f"🔴 เงียบกริบ (0) => ใช้ไม่ได้")
        except Exception as e:
            err_msg = str(e).split('\n')[0][:30]
            print(f"❌ เออเร่อ ({err_msg})")

print("\n" + "=" * 60)
input("สแกนเสร็จแล้ว! กด Enter เพื่อปิดหน้าต่างนี้...")
