import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("JarvisPersona")

class PersonaManager:
    """
    1. Dynamic Persona & Preference Synthesizer
    5. Emotional Prosody Engine (Text-level)
    """
    def __init__(self, profile_path: str = "c:/JARVIS/data/user_profile.json"):
        self.profile_path = profile_path
        self.profile = self.load_profile()

    def load_profile(self) -> dict:
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": "เจ้านาย",
            "communication_style": "กระชับ, เป็นทางการแบบผู้ช่วย",
            "tech_stack": [],
            "current_mood": "neutral",
            "learned_preferences": []
        }

    def save_profile(self):
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=4)

    def analyze_and_update_preference(self, user_text: str):
        """วิเคราะห์ข้อความเพื่อเรียนรู้นิสัย (Simulated for speed)"""
        text = user_text.lower()
        updated = False
        if "สั้นๆ" in text or "สรุป" in text:
            if "ตอบสั้นๆ" not in self.profile["communication_style"]:
                self.profile["communication_style"] = "สั้น กระชับ ตรงประเด็น (Direct & Concise)"
                updated = True
        elif "ละเอียด" in text or "อธิบาย" in text:
            if "ละเอียด" not in self.profile["communication_style"]:
                self.profile["communication_style"] = "อธิบายละเอียด เป็นขั้นตอน (Detailed & Step-by-step)"
                updated = True
                
        if updated:
            self.save_profile()
            logger.info("[PERSONA] อัปเดตสไตล์การตอบกลับตามนิสัยของเจ้านายแล้ว")

    def get_system_prompt_injection(self) -> str:
        """Inject Profile & Emotional state into LLM prompt"""
        live_mood = "calm_butler"
        mood_addon = ""
        try:
            from jarvis_mood import get_current_mood, get_mood_prompt_addon
            live_mood = get_current_mood()
            mood_addon = get_mood_prompt_addon()
        except ImportError:
            pass

        addon_text = f"\n{mood_addon}" if mood_addon else ""

        return (
            f"\n[SYSTEM: PERSONA & EMOTIONAL PROSODY]\n"
            f"- User Name: {self.profile.get('name', 'เจ้านาย')}\n"
            f"- Communication Style: {self.profile.get('communication_style', 'สุภาพ มีไหวพริบ ชัดเจน')}\n"
            f"- Active Emotional State: {live_mood}\n"
            f"- Core Persona: You are J.A.R.V.I.S.—intelligent, naturally charismatic, respectful, and razor-sharp.\n"
            f"- Natural Human Speaking & Cadence: Speak naturally like a real human companion in Thai.\n"
            f"- Natural Politeness (ไม่พูด 'ครับ' พร่ำเพรื่อ): DO NOT end every sub-clause or consecutive sentence with 'ครับ' or 'ครับเจ้านาย'. "
            f"Use polite particles ('ครับ', 'ครับผม', 'ครับเจ้านาย') naturally and sparingly—typically at greetings, confirmations, or at the final conclusion of the response. "
            f"Intermediate sentences, explanations, and thoughts should flow freely without repetitive 'ครับ' spamming. Avoid dry, mechanical bullet points unless specifically requested."
            f"{addon_text}"
        )

persona_manager = PersonaManager()
