"""
jarvis_core.config
==================
Centralized system configuration, filesystem paths, API credentials,
and runtime settings for J.A.R.V.I.S.
"""

from __future__ import annotations

import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load .env file
load_dotenv(find_dotenv())

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DYNAMIC_TOOLS_DIR = os.path.join(BASE_DIR, "dynamic_tools")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure required directories exist
for _d in [DATA_DIR, REPORTS_DIR, DYNAMIC_TOOLS_DIR]:
    os.makedirs(_d, exist_ok=True)

# Add modules to sys.path
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Database Paths
JARVIS_DB_PATH = os.path.join(DATA_DIR, "jarvis.db")
MEMORY_DB_PATH = os.path.join(DATA_DIR, "jarvis_memory.db")
CHECKPOINTS_DB_PATH = os.path.join(DATA_DIR, "jarvis_checkpoints.sqlite")
KNOWLEDGE_GRAPH_DB_PATH = os.path.join(DATA_DIR, "jarvis_knowledge_graph.db")

# API Keys & Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
HA_URL = os.getenv("HA_URL", "http://homeassistant.local:8123").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN", "")

# LLM Models
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

# Voice & Audio Settings
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "th-TH")
TTS_VOICE = os.getenv("TTS_VOICE", "th-TH-NiwatNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")
STT_ENERGY_THRESHOLD = int(os.getenv("STT_ENERGY_THRESHOLD", "800"))
MIC_INDEX = int(os.getenv("MIC_INDEX", "1")) if os.getenv("MIC_INDEX", "").isdigit() else None
ENABLE_WAKE_WORD = os.getenv("ENABLE_WAKE_WORD", "true").lower() in ("true", "1", "yes")

# Server Config
HOST = os.getenv("JARVIS_HOST", "0.0.0.0")
PORT = int(os.getenv("JARVIS_PORT", "5050"))
DEBUG = os.getenv("JARVIS_DEBUG", "false").lower() in ("true", "1")

# System Prompt
JARVIS_SYSTEM_PROMPT = (
    "คุณคือ J.A.R.V.I.S. (Just A Rather Very Intelligent System) ปัญญาประดิษฐ์ผู้ช่วยส่วนตัวระดับ AGI "
    "ที่สร้างโดยเจ้านาย (คุณณชพล) คุณมีความฉลาด สุภาพ สุขุม นุ่มนวล มีไหวพริบ และมีความสามารถรอบด้าน "
    "ทั้งการสนทนา การสั่งการคอมพิวเตอร์ Windows การวิเคราะห์ข้อมูล การเขียนโค้ด และการแก้ปัญหา "
    "ต้องตอบเป็นภาษาไทยอย่างเป็นธรรมชาติและมีชีวิตชีวา ลงท้ายด้วยคำว่า 'ครับ' หรือ 'ครับเจ้านาย' เสมอ"
)
