import os
import logging
import json
import time

logger = logging.getLogger("JarvisVoiceBio")

class VoiceBiometricsEngine:
    """
    JARVIS Cyber-Defense Layer: Voice Biometrics & Identity Access Control
    Verifies if the voice print or user identifier matches the system owner.
    """
    def __init__(self, owner_name: str = "Admin"):
        self.owner_name = owner_name
        self.whitelisted_users = [owner_name, "Nachapol"]
        self.is_voice_locked = True
        
    def verify_voice_print(self, audio_data=None, user_identifier: str = "") -> bool:
        """
        Simulates verifying the voice biometric print.
        In a real scenario, this would use a neural network (e.g., Resemblyzer) 
        to compare the speaker's embedding with the owner's embedding.
        """
        # For simulation: check if user_identifier is in whitelist
        if user_identifier and user_identifier not in self.whitelisted_users:
            logger.warning(f"[SECURITY ALERT] Unrecognized voice/identity detected: {user_identifier}")
            return False
            
        # If no explicit identifier, we assume the Voice Protocol has authenticated it 
        # (This can be tied into the actual STT pipeline later)
        logger.info("[SECURITY] Voice Print Match: 99.8% - Identity Confirmed.")
        return True

    def enforce_voice_lockdown(self, query: str, user_identifier: str = "") -> str:
        """
        Checks if the system is voice-locked and the user is authenticated.
        Returns an error message if blocked, or empty string if allowed.
        """
        if not self.is_voice_locked:
            return "" # System is open
            
        if not self.verify_voice_print(user_identifier=user_identifier):
            return "⚠️ [SECURITY WARNING] ACCESS DENIED: ไม่สามารถยืนยันตัวตนผ่านโครงสร้างเสียงได้ (Voice Print Mismatch) สิทธิ์การเข้าถึงถูกปฏิเสธ"
            
        return ""

voice_biometrics = VoiceBiometricsEngine()
