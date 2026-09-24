"""
Purpose: รับไฟล์เสียง (เช่น .wav, .mp3) แล้วใช้โมเดล Speech‑to‑Text เพื่อแปลงเป็นข้อความไทยหรืออังกฤษ ส่งผลลัพธ์เป็นสตริงพร้อมเวลาเริ่ม‑จบของแต่ละประโยค สามารถใช้เพื่อบันทึกการประชุมหรือสรุปเนื้อหาเสียงได้
Created: 2026-08-24 17:43:53.848567
"""

import os
import logging
from typing import List, Dict, Any

try:
    import whisper
except Exception:
    whisper = None

logger = logging.getLogger(__name__)

# Load model once at module import for efficiency
_MODEL = None
def _load_model() -> Any:
    """Load the base Whisper model (multilingual) if not already loaded."""
    global _MODEL
    if _MODEL is None:
        try:
            _MODEL = whisper.load_model("base")
            logger.info("Whisper model loaded successfully.")
        except Exception as exc:
            logger.exception("Failed to load Whisper model.")
            raise RuntimeError("Unable to load Whisper model.") from exc
    return _MODEL

def transcribe_audio(audio_path: str) -> List[Dict[str, Any]]:
    """
    Transcribe an audio file to Thai/English text and return segments with timestamps.

    Args:
        audio_path: Path to a .wav, .mp3, or other Whisper‑compatible audio file.

    Returns:
        A list of dictionaries, each containing:
            - "text": transcribed sentence.
            - "start": start time in seconds (float).
            - "end": end time in seconds (float).

    Raises:
        FileNotFoundError: If the audio file does not exist.
        RuntimeError: If transcription fails.
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _load_model()
    try:
        result = model.transcribe(audio_path, language="en", fp16=False)
    except Exception as exc:
        logger.exception("Whisper transcription error.")
        raise RuntimeError("Transcription failed.") from exc

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "text": seg.get("text", "").strip(),
            "start": float(seg.get("start", 0)),
            "end": float(seg.get("end", 0)),
        })
    return segments

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transcribe_audio",
        "description": "Transcribe a given audio file (wav, mp3, etc.) into Thai or English text, returning each sentence with start and end timestamps.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the audio file to be transcribed."
                }
            },
            "required": ["audio_path"]
        }
    }
}