import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger("JarvisCrypto")

class JarvisCryptoManager:
    """
    JARVIS Cyber-Defense Layer: Data Encryption
    Handles AES encryption for chat history, logs, and sensitive data.
    """
    def __init__(self, key_path: str = "c:/JARVIS/data/.jarvis_crypto.key"):
        self.key_path = key_path
        self.fernet = self._load_or_generate_key()

    def _load_or_generate_key(self) -> Fernet:
        if not os.path.exists(os.path.dirname(self.key_path)):
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as key_file:
                key_file.write(key)
            logger.info("[SECURITY] Generated new AES Encryption Key for JARVIS Data.")
        return Fernet(key)

    def encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        if not data: return ""
        try:
            return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"[CRYPTO ERROR] Encryption failed: {e}")
            return data

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not encrypted_data: return ""
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"[CRYPTO ERROR] Decryption failed: {e}")
            return encrypted_data

crypto_manager = JarvisCryptoManager()
