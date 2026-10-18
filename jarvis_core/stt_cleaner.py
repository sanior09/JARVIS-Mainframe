import os
import logging
from groq import Groq

logger = logging.getLogger("JarvisSTTCleaner")

class STTCleanerEngine:
    """
    AI Ear-Cleaner: Fixes inaccurate speech-to-text transcripts 
    using a fast LLM (Groq) to guess technical context and correct Thai-English mixups.
    """
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        # Using a very fast model for near-instant correction
        self.model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        if self.api_key:
            self.client = Groq(api_key=self.api_key, max_retries=1)
        else:
            self.client = None

    def clean_transcript(self, raw_text: str) -> str:
        """Pass the raw STT text through the LLM to fix errors."""
        if not self.client or not raw_text.strip():
            return raw_text
            
        sys_prompt = (
            "You are an STT (Speech-to-Text) auto-correction engine. "
            "The user spoke Thai mixed with English tech jargon, but the STT might have misheard it. "
            "Fix the spelling, spacing, and guess the English tech words correctly. "
            "Do NOT answer the prompt. Do NOT add any conversational filler. "
            "Return ONLY the corrected sentence. "
            "Example: 'รันสคริปพายทอน' -> 'รันสคริปต์ Python' "
            "Example: 'ลงเอ็นพีเอ็มอินตอ' -> 'ลง npm install'"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": raw_text}
                ],
                temperature=0.1, # Low temp for factual correction
                max_tokens=256
            )
            corrected_text = response.choices[0].message.content.strip() # type: ignore
            
            if corrected_text and corrected_text != raw_text:
                logger.info(f"✨ [EAR-CLEANER] Fixed STT: '{raw_text}' -> '{corrected_text}'")
                return corrected_text
                
        except Exception as e:
            logger.error(f"[EAR-CLEANER] Failed to process: {e}")
            
        return raw_text

stt_cleaner = STTCleanerEngine()
