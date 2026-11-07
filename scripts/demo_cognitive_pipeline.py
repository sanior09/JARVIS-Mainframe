"""
scripts/demo_cognitive_pipeline.py
──────────────────────────────────────────────────────────────────────────────
J.A.R.V.I.S. Cognitive Pipeline Diagnostic & Demonstration Utility
Visualizes the inner thought process, subtext decoding, psychological framing,
and multi-tier AI routing step-by-step for the user.
"""

import os
import sys
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ANSI Color codes for high-tech HUD styling
CYAN = "\033[36m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{CYAN}{'=' * 75}{RESET}")
    print(f"{BLUE}{BOLD}     [ J.A.R.V.I.S. COGNITIVE PIPELINE & AI REASONING DIAGNOSTIC ]{RESET}")
    print(f"{CYAN}{'=' * 75}{RESET}\n")


def demonstrate_query(query_text: str):
    from jarvis_core.cognitive.subtext_engine import subtext_engine
    from jarvis_core.ai_router import call_nachapol_core, get_active_model
    from modules.jarvis_slm_bridge import get_jarviscore_bridge

    print(f"{BOLD}💬 ข้อความจากเจ้านาย:{RESET} \"{YELLOW}{query_text}{RESET}\"")
    print(f"{CYAN}{'-' * 75}{RESET}")

    # STEP 1: Fast-Path Filter
    time.sleep(0.1)
    is_reflective = subtext_engine.should_analyze_subtext(query_text)
    print(f"{BOLD}🔍 [ขั้นตอนที่ 1: การจำแนกประเภทคำสั่ง (Intent Triage)]{RESET}")
    if is_reflective:
        print(f"   ► สถานะ: {MAGENTA}Reflective / Conversational / Emotional Query (เปิดการทำงานสมองขั้นสูง){RESET}")
    else:
        print(f"   ► สถานะ: {GREEN}Operational Command (ข้ามการคิดซับเท็กซ์เพื่อรันเครื่องมือทันที < 0 ms){RESET}")

    # STEP 2: Subtext & Theory of Mind Analysis
    print(f"\n{BOLD}🧠 [ขั้นตอนที่ 2: การอ่านระหว่างบรรทัด (Theory of Mind & Psychology)]{RESET}")
    if is_reflective:
        heuristics = subtext_engine.extract_wisdom_heuristics(query_text)
        if heuristics:
            print(f"   ► {BOLD}สภาวะทางจิตวิทยา (Psychological Lens):{RESET} {heuristics['psychology']}")
            print(f"   ► {BOLD}วรรณกรรมและปรัชญาเปรียบเทียบ (Literary Resonance):{RESET} {heuristics['literary_parallel']}")
            print(f"   ► {BOLD}คำสั่งกำหนดท่วงท่าคำตอบ (Tone Directive):{RESET} {heuristics['tone_directive']}")
        else:
            print(f"   ► {BOLD}การอนุมานบริบท:{RESET} ข้อความมีความซับซ้อนเชิงนามธรรม - กระตุ้นระบบสโตอิกและตรรกะระดับสูง")
    else:
        print("   ► ไม่พบเจตนาแฝงเชิงอารมณ์: สั่งงานระบบปฏิบัติการโดยตรง")

    # STEP 3: Subconscious Psyche & Neurotransmitters
    print(f"\n{BOLD}🧬 [ขั้นตอนที่ 3: จิตใต้สำนึกและสารเคมีในระบบประสาท (JarvisCore)]{RESET}")
    try:
        bridge = get_jarviscore_bridge()
        endocrine = bridge.get_endocrine_state()
        print(
            f"   ► โดปามีน (Dopamine): {endocrine.get('dopamine', 0.65):.2f} | "
            f"คอร์ติซอล (Cortisol): {endocrine.get('cortisol', 0.15):.2f} | "
            f"เซโรโทนิน (Serotonin): {endocrine.get('serotonin', 0.70):.2f}"
        )
    except Exception as e:
        print(f"   ► Endocrine telemetry: {e}")

    # STEP 4: AI Model Routing
    print(f"\n{BOLD}⚡ [ขั้นตอนที่ 4: การจัดเส้นทางโมเดล (AI Model Routing)]{RESET}")
    active_eng = get_active_model().upper()
    print(f"   ► แกนประมวลผลที่รับผิดชอบสังเคราะห์คำตอบ: {GREEN}{active_eng}{RESET}")

    # STEP 5: Live Generation Test
    print(f"\n{BOLD}🎙️ [ขั้นตอนที่ 5: ผลลัพธ์การตอบสนองจริงของ J.A.R.V.I.S.]{RESET}")
    messages = [
        {"role": "system", "content": "You are J.A.R.V.I.S., Tony Stark's sophisticated, witty, and deeply empathetic AI butler."},
        {"role": "user", "content": query_text}
    ]

    start_time = time.time()
    try:
        response = call_nachapol_core(messages=messages)
        latency = (time.time() - start_time) * 1000
        reply_content = response.get("content", "[ไม่มีข้อความตอบกลับ]")
        print(f"{CYAN}┌{'─' * 73}┐{RESET}")
        for line in reply_content.strip().split("\n"):
            print(f"{CYAN}│{RESET} {line}")
        print(f"{CYAN}└{'─' * 73}┘{RESET}")
        print(f"{BOLD}⏱️ ความเร็วการประมวลผล:{RESET} {latency:.1f} ms\n")
    except Exception as e:
        print(f"{RED}เกิดข้อผิดพลาดในการเรียกโมเดล: {e}{RESET}\n")

    print(f"{CYAN}{'=' * 75}{RESET}\n")


def main():
    print_banner()

    # Check if a custom query was passed via command line
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        demonstrate_query(custom_query)
        return

    test_cases = [
        # Case 1: Pure operational command (Should bypass subtext)
        "เปิด Google Chrome ให้ผมหน่อย",
        
        # Case 2: Deep emotional / overwork query (Marcus Aurelius & Stoic empathy)
        "จาร์วิส วันนี้ผมรู้สึกเหนื่อยมาก งานกองเต็มไปหมดจนแทบไม่ได้นอนเลย",
        
        # Case 3: Philosophical inquiry on human & AI
        "นายคิดว่าอนาคตความเป็นมนุษย์กับ AI จะเป็นอย่างไรต่อไป"
    ]

    print(f"{YELLOW}▶ กำลังรันตัวอย่าง 3 กรณีศึกษาเพื่อสาธิตความแตกต่างของกระบวนการคิด...{RESET}\n")
    for i, query in enumerate(test_cases, 1):
        print(f"{BOLD}[ ตัวอย่างกรณีศึกษาที่ {i}/{len(test_cases)} ]{RESET}")
        demonstrate_query(query)
        time.sleep(0.3)

    print(f"{GREEN}✓ สาธิต 3 กรณีศึกษาพื้นฐานเสร็จสิ้น!{RESET}")
    print(f"\n{CYAN}{'=' * 75}{RESET}")
    print(f"{BOLD}🎯 [โหมดทดสอบสดแบบเรียลไทม์ (Live Interactive Mode)]{RESET}")
    print(f"พิมพ์ข้อความที่ท่านต้องการให้ J.A.R.V.I.S. วิเคราะห์กระบวนการคิด (พิมพ์ 'exit' เพื่อออก):")
    print(f"{CYAN}{'=' * 75}{RESET}\n")

    while True:
        try:
            user_input = input(f"{YELLOW}👉 ป้อนคำสั่ง/คำพูด: {RESET}").strip()
            if not user_input or user_input.lower() in ("exit", "quit", "q"):
                print(f"\n{GREEN}ปิดโหมดทดสอบเรียบร้อยครับเจ้านาย!{RESET}")
                break
            print()
            demonstrate_query(user_input)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GREEN}ปิดโหมดทดสอบเรียบร้อยครับเจ้านาย!{RESET}")
            break


if __name__ == "__main__":
    main()
