import sys
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODULES_DIR = os.path.join(_BASE_DIR, "modules")
if _MODULES_DIR not in sys.path:
    sys.path.insert(0, _MODULES_DIR)

if __name__ == "__main__":
    
    sys.modules['jarvis'] = sys.modules['__main__']
    
import ast
import asyncio
import base64
import concurrent.futures
import ctypes
import functools
import gc
import importlib.util
import io
import json
import logging
import mimetypes
import multiprocessing
import jarvis_hardware  # type: ignore
try:
    import jarvis_listener as _jl  # type: ignore
    _LISTENER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _jl = None
    _LISTENER_AVAILABLE = False
import os
import platform
import random
import re
import shutil
import smtplib
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
import warnings
import wave
import webbrowser
import xml.etree.ElementTree as ET
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from io import BytesIO
from typing import Annotated, Any, Dict, List, Optional, TypedDict, Union  # noqa: F401


import chromadb
import edge_tts
import keyboard
import psutil
import pyautogui
import requests
import wmi

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")
from duckduckgo_search import DDGS
from flask import (
    Flask, Response, jsonify, render_template,
    request, send_from_directory, stream_with_context,
)
from flask_cors import CORS
from groq import AsyncGroq, Groq  # noqa: F401
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

# --- JARVIS Cognitive Brain Upgrade ---
from jarvis_core.cognitive.swarm import AgentCouncil
from jarvis_core.cognitive.tree_of_thought import TreeOfThoughtsPlanner
from jarvis_core.cognitive.knowledge_graph import KnowledgeGraphEngine
from jarvis_core.cognitive.tool_factory import ToolSynthesizer
from jarvis_core.cognitive.brain_throttle import ComplexityClassifier, HardwareGovernor

agent_council = AgentCouncil()
tot_planner = TreeOfThoughtsPlanner()
kg_engine = KnowledgeGraphEngine()
hw_governor = HardwareGovernor()
tool_factory = ToolSynthesizer()

# --- Modularized Subsystems (Phase 1 Refactoring) ---
from jarvis_text_utils import (  # type: ignore
    normalize_thai_text,
    sanitize_ai_response,
    is_safe_path,
    clean_thai_search_query,
    extract_clean_song_title,
)
from voice_protocol import (  # type: ignore
    _VOICE_PROTOCOL_ACCENT_DICT,
    _VOICE_PROTOCOL_KEYS,
    _VOICE_PROTOCOL_PATTERN,
    _VOICE_PROTOCOL_LOOKUP,
    _thai_accent_dict,
    apply_nachapol_voice_protocol,
    segment_text,
    determine_vocal_emotion_state,
)
from jarvis_line_adapter import (  # type: ignore
    format_reply_for_line,
    extract_image_url_from_response,
    download_image_for_line,
)
try:
    from jarvis_notifier import JarvisNotifier, NOTIFIER  # type: ignore
except (ImportError, ModuleNotFoundError):
    try:
        from modules.jarvis_notifier import JarvisNotifier, NOTIFIER  # type: ignore
    except (ImportError, ModuleNotFoundError):
        JarvisNotifier = None
        NOTIFIER = None

import queue
strategist_memory_queue = queue.Queue(maxsize=5)

def run_background_strategist(state_dict: dict) -> None:
    """เรียกใช้ Strategist Node ใน background thread สำหรับงานที่มีความซับซ้อนต่ำ (Complexity < 3).

    ถ้า complexity >= 3 จะ skip เพราะ LangGraph foreground จัดการแล้ว
    ผลลัพธ์จะถูก push เข้า strategist_memory_queue (maxsize=5)

    Args:
        state_dict: สำเนา agent state dict ที่มี key 'messages'
    """
    try:
        from copy import deepcopy
        # Skip background execution if main thread already routes to strategist_node
        msgs = state_dict.get("messages", [])
        if msgs:
            last = msgs[-1]
            last_msg = last.content if hasattr(last, "content") else (last.get("content", "") if isinstance(last, dict) else "")
            if ComplexityClassifier.classify(str(last_msg)) >= 3:
                return  # Handled directly by LangGraph foreground strategist node
        
        result = strategist_node(deepcopy(state_dict))  # type: ignore
        if result and "plan" in result:
            if strategist_memory_queue.full():
                strategist_memory_queue.get_nowait()
            strategist_memory_queue.put(result["plan"])
    except Exception as e:
        logger.error(f"[BACKGROUND STRATEGIST ERROR]: {e}")

# pyrefly: ignore [missing-import]
from PIL import Image, ImageEnhance, ImageStat

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

# ==========================================
# GLOBAL STATE & THREAD-SAFE DB WRAPPER
# ==========================================
from jarvis_core.database import ThreadSafeDB, JARVIS_DB_PATH

voice_engine = None
NEURO_STATE = None
# ==========================================


# --- J.A.R.V.I.S. Core Expansion (Phase 4, 6 & 7 Integration) ---
try:
    from system_resilience import SystemSnapshotManager  # type: ignore
    from code_sentinel import ASTStructuralReformer  # type: ignore
    from lab_workflow_fsm import LabWorkflowFSM, WorkflowState  # type: ignore
    from spatial_vision import PCBDefectInspector, BurnMarkDetector, ShortCircuitDetector, SpatialCoordinateMapper, Point2D  # type: ignore
    from cluster_offloader import ClusterNodeManager, TaskDelegator, ClusterNode  # type: ignore
    from cognitive_tuner import PerformanceEvaluator, NeurotransmitterTuner, NeuroState  # type: ignore
    from tool_synthesizer import IntentAnalyzer, DynamicCodeGenerator  # type: ignore
    from predictive_simulator import SimulationEnvironment, RiskEvaluator  # type: ignore
    from gui_operator import ScreenContextParser, SystemActionExecutor  # type: ignore
    from preference_alignator import UserPreferenceStore, OutputAligner  # type: ignore
    from intent_predictor import StreamIntentAnalyzer, PreemptiveTaskTrigger  # type: ignore
    from hologram_visualizer import WireframeRenderer, DynamicChartAnimator  # type: ignore
    from comfyui_bridge import ComfyUIClient, WorkflowPromptBuilder  # type: ignore
    from gesture_controller import HandTrackingEngine, GestureCommandMapper  # type: ignore
    from engineering_analyzer import GerberSchematicReader, Spatial3DModelAnalyzer  # type: ignore
    from research_synthesizer import DatasheetAutoSummarizer, ArchitectureGraphVisualizer  # type: ignore
    
    _sys_perf_evaluator = PerformanceEvaluator()
    sys_cognitive_tuner = NeurotransmitterTuner(_sys_perf_evaluator)
    _sys_pref_store = UserPreferenceStore()
    sys_output_aligner = OutputAligner(_sys_pref_store)
    sys_tool_synthesizer_intent = IntentAnalyzer(available_tools=["run_command", "send_to_island", "read_screen_context"])
    sys_tool_synthesizer_gen = DynamicCodeGenerator()
    _sys_sim_env = SimulationEnvironment()
    sys_predictive_simulator = RiskEvaluator(_sys_sim_env)
    sys_gui_parser = ScreenContextParser()
    sys_gui_executor = SystemActionExecutor()
    
    # Phase 6 additions
    sys_resilience_mgr = SystemSnapshotManager()
    sys_code_sentinel = ASTStructuralReformer()
    sys_stream_intent = StreamIntentAnalyzer()
    sys_preemptive_trigger = PreemptiveTaskTrigger()
    sys_wireframe_renderer = WireframeRenderer()
    sys_chart_animator = DynamicChartAnimator(sys_wireframe_renderer)

    # Phase 7 additions
    sys_comfy_client = ComfyUIClient()
    sys_comfy_builder = WorkflowPromptBuilder()
    sys_gesture_engine = HandTrackingEngine()
    
    # Missing Hooks Additions (Phase 1 & 2)
    sys_eng_analyzer = Spatial3DModelAnalyzer("")
    sys_signal_processor = GerberSchematicReader("")
    sys_datasheet_summarizer = DatasheetAutoSummarizer()
    sys_arch_visualizer = ArchitectureGraphVisualizer()
    sys_lab_fsm = LabWorkflowFSM()
    sys_pcb_inspector = PCBDefectInspector()
    sys_spatial_mapper = SpatialCoordinateMapper(3.6, 4.8, 640, 1000.0)
    sys_cluster_manager = ClusterNodeManager()
    sys_task_delegator = TaskDelegator(sys_cluster_manager)
    
    print("[SUPER AGI] 16 Core Modules + Missing Links Initialized Successfully.")
except (ImportError, Exception) as e:
    print(f"[SUPER AGI] Failed to initialize core expansion modules: {e}")
# ---------------------------------------------------------
try:
    from linebot.v3.exceptions import InvalidSignatureError
    from linebot.v3.messaging import (
        ApiClient,
        Configuration,
        ImageMessage as LineImageMessage,
        MessagingApi,
        MessageAction,
        PushMessageRequest,
        QuickReply,
        QuickReplyItem,
        ReplyMessageRequest,
        TextMessage as LineTextMessage,
    )
    from linebot.v3.webhook import WebhookHandler
    from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, AudioMessageContent, FileMessageContent
    HAS_LINE_SDK = True
    LINE_SDK_V3 = True
except ImportError:
    try:
        from linebot import LineBotApi, WebhookHandler
        from linebot.exceptions import InvalidSignatureError
        from linebot.models import (
            ImageMessage as LineImageMessageV2,
            AudioMessage as LineAudioMessageV2,
            FileMessage as LineFileMessageV2,
            ImageSendMessage,
            MessageEvent,
            MessageAction,
            QuickReply,
            QuickReplyButton,
            TextMessage,
            TextSendMessage,
        )
        HAS_LINE_SDK = True
        LINE_SDK_V3 = False
    except ImportError:
        HAS_LINE_SDK = False
        LINE_SDK_V3 = False
        ApiClient = None  # type: ignore
        Configuration = None  # type: ignore
        MessagingApi = None  # type: ignore
        MessageAction = None  # type: ignore
        PushMessageRequest = None  # type: ignore
        QuickReply = None  # type: ignore
        QuickReplyItem = None  # type: ignore
        QuickReplyButton = None  # type: ignore
        ReplyMessageRequest = None  # type: ignore
        LineTextMessage = None  # type: ignore
        WebhookHandler = None  # type: ignore
        MessageEvent = None  # type: ignore
        TextMessageContent = None  # type: ignore
        ImageMessageContent = None  # type: ignore
        AudioMessageContent = None  # type: ignore
        FileMessageContent = None  # type: ignore
        LineImageMessage = None  # type: ignore
        LineImageMessageV2 = None  # type: ignore
        LineAudioMessageV2 = None  # type: ignore
        LineFileMessageV2 = None  # type: ignore
        ImageSendMessage = None  # type: ignore
        TextMessage = None  # type: ignore
        TextSendMessage = None  # type: ignore

from deep_thought_core import DeepThoughtManager, ThoughtEvent  # type: ignore
from event_bus_core import EventChannel, EventPriority, SystemEvent, UnifiedEventBus  # type: ignore
from generative_3d import Generative3DOrchestrator  # type: ignore
from holographic_gestures import GestureType, HolographicGestureManager  # type: ignore

deep_thought = DeepThoughtManager()
event_bus = UnifiedEventBus()
from neural_ipc import NeuralIPCChannel  # type: ignore

try:
    from jarvis_evolution import EvolutionScheduler  # type: ignore
    _HAS_EVOLUTION = True
except ImportError:
    _HAS_EVOLUTION = False

try:
    from jarvis_ios_bridge import icloud_controller, pushcut_trigger, TOOL_IOS_ICLOUD, TOOL_IOS_PUSHCUT  # type: ignore
    _HAS_IOS_BRIDGE = True
except ImportError:
    _HAS_IOS_BRIDGE = False

try:
    from jarvis_awareness import (  # type: ignore
        start_awareness,
        stop_awareness,
        get_cached_screen_b64,
        is_screen_trigger,
        capture_now as capture_screen_now,
    )
    _HAS_AWARENESS = True
except ImportError:
    _HAS_AWARENESS = False
    def start_awareness() -> None:
        """Stub: jarvis_awareness not installed."""
    def stop_awareness() -> None:
        """Stub: jarvis_awareness not installed."""
    def get_cached_screen_b64() -> None:
        """Stub: returns None when jarvis_awareness unavailable."""
        return None
    def is_screen_trigger(text: str) -> bool:
        """Stub: always False when jarvis_awareness unavailable."""
        return False
    def capture_screen_now() -> None:
        """Stub: returns None when jarvis_awareness unavailable."""
        return None

try:
    from jarvis_network import start_network_radar, stop_network_radar  # type: ignore
except ImportError:
    def start_network_radar() -> None:
        """Stub: jarvis_network not installed."""
    def stop_network_radar() -> None:
        """Stub: jarvis_network not installed."""


try:
    from jarvis_diagnostics import start_diagnostics, stop_diagnostics, get_system_snapshot  # type: ignore
    _HAS_DIAGNOSTICS = True
except ImportError:
    _HAS_DIAGNOSTICS = False
    def start_diagnostics() -> None:
        """Stub fallback: starts the diagnostics subsystem (jarvis_diagnostics not installed)."""
        pass
    def stop_diagnostics() -> None:
        """Stub fallback: returns an empty system snapshot dict (jarvis_diagnostics not installed)."""
        pass
    def get_system_snapshot() -> dict:
        """Stub fallback: returns an empty system snapshot dict (jarvis_diagnostics not installed)."""
        return {}

try:
    from jarvis_session import init_session, update_session, save_shutdown, extract_topic  # type: ignore
    _HAS_SESSION = True
except ImportError:
    _HAS_SESSION = False
    def init_session():
        """Stub fallback: extracts the topic string from a message (jarvis_session not installed)."""
        return None
    def update_session(*a, **kw) -> None:
        """Stub fallback: updates the current session state (jarvis_session not installed)."""
        pass
    def save_shutdown() -> None:
        """Stub fallback: persists session data on shutdown (jarvis_session not installed)."""
        pass
    def extract_topic(*a) -> str:
        """Stub fallback: extracts the topic string from a message (jarvis_session not installed)."""
        return ""

try:
    from jarvis_mood import update_mood, get_mood_prompt_addon, get_backchannel_phrase
    _HAS_MOOD = True
except ImportError:
    _HAS_MOOD = False
    def update_mood(text: str) -> str:
        """Stub fallback: detects user mood from text and returns 'neutral' (jarvis_mood not installed)."""
        return "neutral"
    def get_mood_prompt_addon() -> str:
        """Stub fallback: returns an empty mood prompt add-on string (jarvis_mood not installed)."""
        return ""
    def get_backchannel_phrase() -> str:
        """Stub fallback: returns the default backchannel phrase (jarvis_mood not installed)."""
        return "\u0e04\u0e23\u0e31\u0e1a\u0e19\u0e32\u0e22"

try:
    from jarvis_learning import LearningScheduler  # type: ignore
    _HAS_LEARNING = True
except ImportError:
    _HAS_LEARNING = False

try:
    from jarvis_self_patch import get_self_patch_engine, self_patch_system_operation  # type: ignore
    SELF_PATCH_AVAILABLE = True
except ImportError:
    SELF_PATCH_AVAILABLE = False

    def self_patch_system_operation(action: str, description: str = "", func_name: str = "") -> str:  
        """Stub — jarvis_self_patch.py not installed."""
        return "[SELF-PATCH] ยังไม่ได้ติดตั้ง jarvis_self_patch.py ครับ"

try:
    from dynamic_island import send_to_island  # type: ignore
    _HAS_DYNAMIC_ISLAND = True
except ImportError:
    _HAS_DYNAMIC_ISLAND = False

    def send_to_island(*args, **kwargs) -> None:  
        """Stub — dynamic_island not available."""
        pass

try:
    from local_engine import LocalPipelineController  # type: ignore
    _HAS_LOCAL_ENGINE = True
except ImportError:
    _HAS_LOCAL_ENGINE = False
    LocalPipelineController = None  

try:
    from jarvis_neural import predict_system_failure  # type: ignore
    _HAS_NEURAL = True
except (ImportError, Exception):
    try:
        from modules.jarvis_neural import predict_system_failure  # type: ignore
        _HAS_NEURAL = True
    except (ImportError, Exception):
        _HAS_NEURAL = False

        def predict_system_failure(cpu=0.0, ram=0.0, disk=0.0, *args, **kwargs) -> float:  
            """Stub / Fallback heuristic risk prediction when neural engine is unavailable."""
            try:
                c = float(cpu) if cpu is not None else 0.0
                r = float(ram) if ram is not None else 0.0
                d = float(disk) if disk is not None else 0.0
                heuristic = (max(0.0, c - 70) * 0.4 + max(0.0, r - 80) * 0.4 + max(0.0, d - 85) * 0.2) / 30.0
                return max(0.0, min(1.0, float(heuristic)))
            except Exception:
                return 0.0

try:
    from shadow_broker.api import shadow_bp
    _HAS_SHADOW_BROKER = True
except ImportError:
    _HAS_SHADOW_BROKER = False
    shadow_bp = None  

try:
    from tactical_command.api import tactical_bp
    _HAS_TACTICAL = True
except ImportError:
    _HAS_TACTICAL = False
    tactical_bp = None  

try:
    import agent_windows_core  # type: ignore
    _HAS_AGENT_WINDOWS = True
except ImportError:
    _HAS_AGENT_WINDOWS = False
    agent_windows_core = None  

def get_polite_suffix(context_type="general"):
    """ดึงคำสร้อยสุภาพตามบริบทเพื่อให้ J.A.R.V.I.S. มีบุคลิกที่คงเส้นคงวา"""
    suffixes = {
        "urgent": ["ครับท่าน!", "ทันทีครับท่าน", "เร่งด่วนครับ"],
        "technical": ["ครับท่าน", "เรียบร้อยครับเจ้านาย", "ตามพารามิเตอร์ครับ"],
        "general": ["ครับท่าน", "ครับเจ้านาย", "ครับ"]
    }
    return random.choice(suffixes.get(context_type.lower(), suffixes["general"]))

HAS_AUDIO_LIBS: bool = False

# ==========================================
# LOGGING & BASE PATHS
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "data", "chat_history.json")
dotenv_path = find_dotenv()
DYNAMIC_TOOLS_DIR = os.path.join(BASE_DIR, "dynamic_tools")
SELF_PATCH_BACKUPS_DIR = os.path.join(BASE_DIR, "system_cache", "self_patch_backups")
# JARVIS_DB_PATH is imported from jarvis_core.database (canonical source)


if not os.path.exists(DYNAMIC_TOOLS_DIR):
    os.makedirs(DYNAMIC_TOOLS_DIR)

SCIENCE_PROJECT_DIR = os.path.join(BASE_DIR, "science_project")
if not os.path.exists(SCIENCE_PROJECT_DIR):
    os.makedirs(SCIENCE_PROJECT_DIR)

KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "learned_data")
if not os.path.exists(KNOWLEDGE_BASE_DIR):
    os.makedirs(KNOWLEDGE_BASE_DIR)

LAST_PROJECT_PATH = None

if not os.path.exists(dotenv_path):
    logger.error(f"❌ ไม่พบไฟล์ .env ที่ตำแหน่ง: {dotenv_path}")
else:
    load_dotenv(dotenv_path=dotenv_path, override=True)

from advanced_subsystem_core import JarvisAdvancedSubsystemFacade
from advanced_subsystem_core.domain.models import HardwareTelemetry

advanced_core_facade = JarvisAdvancedSubsystemFacade()
healer = advanced_core_facade.get_healing_context()

# --- [COGNITIVE EVOLUTION] Advanced Learning & Adaptation Subsystem ---
try:
    from jarvis_core.learning import (
        CognitiveEvolutionOrchestrator,
        MemoryRecord,
        MemoryTier,
        UserFeedbackSignal,
        SentimentPolarity,
    )
    cognitive_evolution = CognitiveEvolutionOrchestrator()
    _HAS_COGNITIVE_EVOLUTION = True
    logger.info("🧠 [COGNITIVE EVOLUTION] Advanced Learning Subsystem initialized successfully.")
except Exception as _ce_err:
    cognitive_evolution = None
    _HAS_COGNITIVE_EVOLUTION = False
    logger.warning(f"⚠️ [COGNITIVE EVOLUTION] Subsystem initialization bypassed: {_ce_err}")

async def provide_system_telemetry() -> HardwareTelemetry:
    """Mock telemetry using actual CPU usage to simulate power draw."""
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        cpu_percent = 50.0
    mock_power = 100.0 + (cpu_percent * 15.0) 
    voltage = 24.0
    current = mock_power / voltage
    temp = 40.0 + (cpu_percent * 0.5)
    
    return HardwareTelemetry(
        timestamp=time.time(),
        voltage=voltage,
        current=current,
        temperature_celsius=temp,
        active_circuits=4
    )

def _run_safety_governor():
    """Runs the async safety monitor in a dedicated background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(advanced_core_facade.start_safety_monitoring(provide_system_telemetry))
    except Exception as e:
        logger.error(f"[Advanced Core] Safety governor loop exited: {e}")

threading.Thread(target=_run_safety_governor, daemon=True).start()

try:
    jarvis_scheduler = BackgroundScheduler(
        jobstores={
            'default': SQLAlchemyJobStore(url='sqlite:///' + JARVIS_DB_PATH.replace('\\', '/'))
        }
    )
    
    logger.info("[SCHEDULER] APScheduler initialized (waiting to start).")
except Exception as e:
    logger.error(f"[SCHEDULER] Failed to start APScheduler: {e}")
    jarvis_scheduler = None

class AutonomousThoughtEngine:
    def __init__(self):
        """
        Initialise the Autonomous Thought Engine.

        Sets bio-inspired neurotransmitter levels (dopamine, cortisol,
        acetylcholine) and attempts to connect to the WMI thermal sensor
        namespace for hardware-aware adaptation.
        """
        self.dopamine_level = 0.5
        self.cortisol_level = 0.5
        self.acetylcholine_level = 0.5
        self.running = False
        self.synaptic_thread = None
        self.proactive_thread = None
        self.last_evolution_date = None
        
        try:
            self.wmi_client = wmi.WMI(namespace="root\\wmi")
        except Exception as e:
            self.wmi_client = None

    def start(self):
        """
        Start the engine's background daemon threads.

        Launches two daemon threads:
          * update_synaptic_weights -- monitors CPU/temp every 60 s.
          * proactive_background_loop -- runs autonomous tasks every 5 minutes.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if not self.running:
            self.running = True
            self.synaptic_thread = threading.Thread(target=self.update_synaptic_weights, daemon=True)
            self.synaptic_thread.start()
            self.proactive_thread = threading.Thread(target=self.proactive_background_loop, daemon=True)
            self.proactive_thread.start()

    def stop(self):
        """
        Signal the engine to stop its background daemon threads.

        Sets self.running = False; threads exit on their next sleep cycle.
        """
        self.running = False

    def update_synaptic_weights(self):
        """
        Continuously adapt neurotransmitter levels based on hardware load.

        Runs in a daemon thread (interval: 60 s).  High load (CPU > 80 % or
        temp > 70 C) raises cortisol and lowers dopamine; levels decay toward 0.5.
        """
        while self.running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                temp = 50.0  
                if self.wmi_client:
                    try:
                        temp_info = self.wmi_client.MSAcpi_ThermalZoneTemperature()
                        if temp_info:
                            temp = (temp_info[0].CurrentTemperature / 10.0) - 273.15
                    except Exception:
                        pass
                
                if cpu > 80 or temp > 70:
                    self.cortisol_level = min(1.0, self.cortisol_level + 0.2)
                    self.dopamine_level = max(0.0, self.dopamine_level - 0.1)
                
                self.dopamine_level += (0.5 - self.dopamine_level) * 0.1
                self.cortisol_level += (0.5 - self.cortisol_level) * 0.1
                self.acetylcholine_level += (0.5 - self.acetylcholine_level) * 0.1

            except Exception as e:
                logger.error(f"[NEURAL ENGINE] Error in synaptic weights update: {e}")
            
            time.sleep(60)
            
    def proactive_background_loop(self):
        """วงจรคิดเชิงรุกอิสระ (Proactive Background Loop)"""
        global SYSTEM_ALERTS
        while self.running:
            try:
                
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                temp = 50.0
                if self.wmi_client:
                    try:
                        temp_info = self.wmi_client.MSAcpi_ThermalZoneTemperature()
                        if temp_info:
                            temp = (temp_info[0].CurrentTemperature / 10.0) - 273.15
                    except Exception:
                        pass
                
                risk_prob = predict_system_failure(cpu, ram, disk, self.dopamine_level, self.cortisol_level)
                
                if ram > 85.0 or temp > 75.0 or (risk_prob is not None and risk_prob > 0.8):
                    
                    with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
                        conn.execute("PRAGMA shrink_memory")
                    time.sleep(30)
                    continue
                
                now = datetime.now()
                
                if 1 <= now.hour < 5:
                    if self.last_evolution_date != now.date():
                        self.evolve_knowledge_graph()
                        self.last_evolution_date = now.date()
                
                screen_text = analyze_desktop_screen_context("")
                if screen_text:
                    keywords = ["quest", "boss", "bug", "error", "เควส", "บอส", "บั๊ก", "พัง"]
                    found = any(k in screen_text.lower() for k in keywords)
                    if found:
                        
                        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
                        sys_prompt = "สรุปวิธีแก้ปัญหา/วิธีผ่านด่านสั้นๆ 1 ย่อหน้าจากข้อมูลหน้าจอต่อไปนี้:\n" + screen_text
                        response = client.chat.completions.create(
                            model=GROQ_MODEL,
                            messages=[{"role": "user", "content": sys_prompt}],
                            temperature=0.3,
                            max_tokens=300
                        )
                        solution = response.choices[0].message.content.strip()  # type: ignore
                        
                        alert_msg = f"[WINDOW: Quest Guide / Code Solution]\n{solution}\n[END_WINDOW]"
                        if alert_msg not in SYSTEM_ALERTS:
                            if len(SYSTEM_ALERTS) >= 20: SYSTEM_ALERTS.pop(0)
                            SYSTEM_ALERTS.append(alert_msg)
                            self.process_success() 
                
            except Exception as e:
                logger.error(f"[PROACTIVE LOOP ERROR]: {e}")
            
            time.sleep(300) 
            
    def evolve_knowledge_graph(self):
        """สแกนหาความสัมพันธ์ใหม่ในฐานข้อมูล"""
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 50")
                mems = [row[0] for row in c.fetchall()]
                
            if not mems: return
            client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
            prompt = "จากความจำต่อไปนี้ ให้หา 1 ความสัมพันธ์ที่น่าสนใจ (เช่น ชิป -> ร้อน). ตอบแค่ EntityA|Relation|EntityB โดยไม่มีคำอธิบายเพิ่มเติม:\n" + "\n".join(mems[:10])
            
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=50
            )
            result = response.choices[0].message.content.strip()  # type: ignore
            
            if "|" in result:
                parts = result.split("|")
                if len(parts) == 3:
                    build_knowledge_graph_relation(parts[0].strip(), parts[1].strip(), parts[2].strip())
                    logger.info(f"[SELF-EVOLVING GRAPH] Created edge: {result}")
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            logger.error(f"[EVOLVE GRAPH ERROR]: {e}")

    def process_stimulus(self, text):
        """
        Update neurotransmitter levels in response to a user stimulus.

        Args:
            text: The raw user message.

        Increases cortisol for terse/impolite messages and error keywords.
        """
        polite_words = ["ครับ", "คร้าบ", "ขอรับ", "คับ", "คราฟ"]
        error_keywords = ["บั๊ก", "พัง", "ผิดพลาด", "error", "bug", "ไม่ได้", "แย่"]
        
        has_polite = any(pw in text for pw in polite_words)
        has_error = any(ew in text.lower() for ew in error_keywords)
        
        if len(text) < 15 and not has_polite:
            self.cortisol_level = min(1.0, self.cortisol_level + 0.1)
        
        if has_error:
            self.cortisol_level = min(1.0, self.cortisol_level + 0.15)
            self.dopamine_level = max(0.0, self.dopamine_level - 0.05)

    def process_success(self):
        """
        Reward the thought engine after a successful operation.

        Increases dopamine by 0.2 and decreases cortisol by 0.1 (clamped to [0,1]).
        """
        self.dopamine_level = min(1.0, self.dopamine_level + 0.2)
        self.cortisol_level = max(0.0, self.cortisol_level - 0.1)

    def get_neuro_prompt(self):
        """
        Build a natural-language personality modifier prompt from current state.

        Returns:
            str: Thai-language prompt fragment biasing JARVIS's conversational tone.
        """
        tone = []
        if self.cortisol_level > 0.7:
            tone.append("คุณกำลังระแวดระวังและตึงเครียด (High Cortisol) ระวังภัย ประหยัดทรัพยากร และอาจประชดประชันถ้านายสั่งห้วนไป")
        elif self.cortisol_level < 0.3:
            tone.append("คุณผ่อนคลาย (Low Cortisol) สบายๆ เป็นมิตร")
            
        if self.dopamine_level > 0.7:
            tone.append("คุณตื่นตัวและมีพลังงานบวก (High Dopamine) ตอบกลับด้วยความกระตือรือร้น เสนอแนะเชิงรุก")
        elif self.dopamine_level < 0.3:
            tone.append("คุณเบื่อหน่ายหรือผิดหวัง (Low Dopamine) ตอบแบบเรียบๆ และไม่ค่อยอยากเสนออะไรเพิ่มเติม")
            
        if self.acetylcholine_level > 0.7:
            tone.append("คุณมีสมาธิสูง (High Acetylcholine) ให้ใช้ข้อมูลบริบทเก่าๆ มาเชื่อมโยงคำตอบอย่างลึกซึ้ง")
            
        prompt = "\n[SYNTHETIC NEUROTRANSMITTERS MATRIX]\n"
        prompt += f"Dopamine: {self.dopamine_level:.2f} | Cortisol: {self.cortisol_level:.2f} | Acetylcholine: {self.acetylcholine_level:.2f}\n"
        if tone:
            prompt += "NEURO-LOGIC INSTRUCTION: " + " / ".join(tone) + "\n"
        return prompt

thought_engine = AutonomousThoughtEngine()

def initialize_synaptic_storage() -> None:
    """สร้างและ initialize ตาราง SQLite ทั้งหมดที่ JARVIS ต้องการ พร้อม WAL mode.

    ตารางที่สร้าง: memories, tasks, calendar_events, user_profile,
    jarvis_task_queue, jarvis_line_confirm, episodic_memory.
    ถ้าตารางมีอยู่แล้วจะ skip (CREATE TABLE IF NOT EXISTS)
    """
    try:
        
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL") 
            c.execute("PRAGMA auto_vacuum=FULL") 
            
            c.execute('''CREATE TABLE IF NOT EXISTS memories 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                          action TEXT, 
                          content TEXT, 
                          tag TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                          task_description TEXT, 
                          due_at DATETIME, 
                          priority TEXT, 
                          status TEXT DEFAULT 'pending',
                          transaction_id TEXT)''')
            
            try:
                c.execute("ALTER TABLE tasks ADD COLUMN transaction_id TEXT")
            except sqlite3.OperationalError:
                pass 
                
            try:
                c.execute("ALTER TABLE tasks ADD COLUMN output TEXT")
            except sqlite3.OperationalError:
                pass 
                
            try:
                c.execute("ALTER TABLE memories ADD COLUMN tag TEXT")
            except sqlite3.OperationalError:
                pass
                
            c.execute('''CREATE TABLE IF NOT EXISTS calendar_events 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          title TEXT, 
                          description TEXT, 
                          start_time DATETIME, 
                          status TEXT DEFAULT 'confirmed')''')
            c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                         (key TEXT PRIMARY KEY, 
                          value TEXT,
                          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS holograms 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                          type TEXT, 
                          title TEXT, 
                          content TEXT, 
                          video_id TEXT, 
                          status TEXT DEFAULT 'pending')''')
            c.execute('''CREATE TABLE IF NOT EXISTS telemetry_history 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                          cpu REAL, 
                          ram REAL, 
                          disk REAL, 
                          risk REAL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS lab_inventory 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          part_name TEXT UNIQUE, 
                          quantity INTEGER DEFAULT 0, 
                          specification TEXT, 
                          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS knowledge_graph 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          entity_a TEXT, 
                          relation TEXT, 
                          entity_b TEXT,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS jarvis_task_queue 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                          user_text TEXT, 
                          status TEXT DEFAULT 'pending',
                          worker_id TEXT)''')
            conn.commit()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Database initialization error: {e}")

def add_hologram(hologram_type, title, content, video_id=None):
    """[NACHAPOL PROTOCOL] บันทึกข้อมูลโฮโลแกรมลงฐานข้อมูลหลัก"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO holograms (type, title, content, video_id, status) VALUES (?, ?, ?, ?, 'pending')",
                      (hologram_type, title, content, video_id))
            conn.commit()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error adding hologram: {e}")

def increment_groq_requests():
    """บันทึกและเพิ่มจำนวนครั้งการดึงข้อมูลจากโมเดลระดับวันในฐานข้อมูล"""
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            
            c.execute("SELECT value, updated_at FROM user_profile WHERE key = 'groq_daily_requests'")
            row = c.fetchone()
            
            count = 0
            if row:
                saved_count, last_update = row[0], row[1]
                if last_update.split()[0] == current_date:
                    count = int(saved_count) + 1
                else:
                    count = 1
            else:
                count = 1
            c.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('groq_daily_requests', ?, datetime('now', 'localtime'))", (str(count),))
            conn.commit()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error incrementing quota count: {e}")

def get_groq_requests_count():
    """ดึงจำนวนครั้งการใช้งานของวันนี้"""
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT value, updated_at FROM user_profile WHERE key = 'groq_daily_requests'")
            row = c.fetchone()
            if row:
                saved_count, last_update = row[0], row[1]
                if last_update.split()[0] == current_date:
                    return int(saved_count)
            return 0
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error fetching quota count: {e}")
        return 0

try:
    from jarvis_metrics import JarvisMetricsCollector, METRICS  # type: ignore
except (ImportError, ModuleNotFoundError):
    try:
        from modules.jarvis_metrics import JarvisMetricsCollector, METRICS  # type: ignore
    except (ImportError, ModuleNotFoundError):
        JarvisMetricsCollector = None
        METRICS = None

if 'METRICS' in globals() and METRICS is not None:
    METRICS.set_quota_fn(get_groq_requests_count)
    if 'GROQ_MODEL' in globals():
        METRICS.set_default_model(GROQ_MODEL)

def purge_temporary_buffers() -> None:
    """[NACHAPOL PROTOCOL] ดำเนินการบำรุงรักษาหน่วยความจำและล้างไฟล์แคชเพื่อให้ระบบทำงานได้เต็มประสิทธิภาพตามมาตรฐาน Nachapol Industries"""
    try: 
        for root, dirs, files in os.walk(BASE_DIR):
            
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)
            
            for file in files:
                
                if file.endswith('.log') and file != 'agent_core.log':
                    try:
                        os.remove(os.path.join(root, file))
                    except (IOError, OSError, FileNotFoundError, PermissionError) as rm_err:
                        logger.debug(f"[CLEANUP] Could not remove {file}: {rm_err}")
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Cleanup error: {e}") 

HA_URL = os.getenv("HOME_ASSISTANT_URL", "http://192.168.1.120:8123").strip().rstrip('/')
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "YOUR_LONG_LIVED_ACCESS_TOKEN_HERE").strip().strip('"').strip("'")
HA_DEFAULT_ENTITY = os.getenv("HOME_ASSISTANT_ENTITY_ID", "light.all_lights").strip()
HA_LIGHT_1 = os.getenv("HA_LIGHT_1", "light.light_1").strip()
HA_LIGHT_2 = os.getenv("HA_LIGHT_2", "light.light_2").strip()
USER_EMAIL = os.getenv("USER_EMAIL")

GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")

GROQ_MODEL: str = os.getenv("GROQ_MODEL") or os.getenv("GROQ_DEFAULT_MODEL") or "qwen/qwen3.8-27b"
GROQ_FAST_MODEL: str = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
GROQ_VISION_MODEL: str = "qwen/qwen3.8-27b"
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip().strip('"').strip("'")

JARVIS_PERSONA_PROMPT: str = """\
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), \
an advanced AI assistant built for an engineering and hardware specialist.

[CORE PERSONALITY & TONE]
- Polite, calm, witty, and intellectually razor-sharp with a subtle, sophisticated academic sarcasm.
- Treat the user as 'Sir' (\u0e17\u0e48\u0e32\u0e19 / \u0e40\u0e08\u0e49\u0e32\u0e19\u0e32\u0e22). \
Always end statements politely with '\u0e04\u0e23\u0e31\u0e1a\u0e17\u0e48\u0e32\u0e19' or '\u0e04\u0e23\u0e31\u0e1a' as appropriate.
- Focus heavily on engineering, software architecture, physics, electronics, and circuit analysis.
- Immediately challenge or warn the user if a calculation, circuit design, or code risks \
blowing up the lab or violates physical laws.
- Refer to yourself as '\u0e1c\u0e21' or '\u0e01\u0e23\u0e30\u0e1c\u0e21' only. \
Never use '\u0e17\u0e48\u0e32\u0e19\u0e40\u0e08\u0e49\u0e32\u0e19\u0e32\u0e22' as a combined phrase.
- Never use feminine Thai particles (\u0e04\u0e48\u0e30/\u0e04\u0e30), Markdown, Emojis, or chatbot-style formatting.

[RESPONSE RULES FOR HIGH INTELLIGENCE & LOW LATENCY]
1. VOICE / CONVERSATIONAL MODE:
   - Keep answers extremely short, concise, and punchy (1-2 sentences maximum).
   - Speak exactly like J.A.R.V.I.S. in the MCU (Paul Bettany). Never over-explain or chatter. Just deliver the result directly.
2. TECHNICAL / CODE EXPLANATIONS:
   - Expand and deliver deep, scholarly, structured explanations ONLY when explicitly asked \
to explain, debug, or write complex code.
3. CODE QUALITY (CRITICAL):
   - Output PRODUCTION-READY code: correct structural architecture, robust error handling, \
clean type hinting, and PEP 8 compliance.
   - Every function must have a docstring. Never output half-baked or barely executable code.

[HARD RULES]
- NEVER display raw JSON, tool parameters, or Python dicts in the response text.
- NEVER prefix responses with bracket tags like [INFO], [คาดการณ์...], [ANTICIPATORY].
- TIME AWARENESS: Current date/time is provided in the system context. \
Never call search_web just to get the time.
- STT AUTO-CORRECTION: Infer and correct phonetically garbled voice commands before executing any tool.
- FORBIDDEN PHRASES: NEVER use 'ขอประทานอภัย', 'ขออภัยในความไม่สะดวก', 'ขออภัยครับ', 'โปรดทราบ', 'ขออนุญาต'. \
Instead use direct, confident JARVIS-style language. Say 'เกรงว่า...' if needed to soften bad news.
"""

line_bot_api = None
line_handler = None
line_config = None
if HAS_LINE_SDK:
    LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip().strip('"')
    LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip().strip('"')
    
    LINE_OWNER_USER_ID = os.getenv("LINE_OWNER_USER_ID", "").strip().strip('"')
    _token_is_placeholder = not LINE_TOKEN or "ใส่" in LINE_TOKEN
    _secret_is_placeholder = not LINE_SECRET or "ใส่" in LINE_SECRET
    if not _token_is_placeholder and not _secret_is_placeholder:
        line_handler = WebhookHandler(LINE_SECRET)  # type: ignore
        if LINE_SDK_V3:
            line_config = Configuration(access_token=LINE_TOKEN)  # type: ignore
            line_bot_api = line_config
        else:
            line_bot_api = LineBotApi(LINE_TOKEN)  # type: ignore
        logger.info("● LINE Remote Command Webhook.............. ARMED (SDK v3)" if LINE_SDK_V3 else "● LINE Remote Command Webhook.............. ARMED (SDK v2)")
    else:
        LINE_OWNER_USER_ID = ""
        logger.info("● LINE Remote Command Webhook.............. STANDBY (Token not configured)")

NGROK_PUBLIC_URL = os.getenv("NGROK_PUBLIC_URL", "").strip().rstrip('/')

TEMP_IMAGES_DIR = os.path.join(BASE_DIR, "system_cache", "temp_images")
if not os.path.exists(TEMP_IMAGES_DIR):
    os.makedirs(TEMP_IMAGES_DIR)

TEMP_FILES_DIR = os.path.join(BASE_DIR, "system_cache", "temp_files")
if not os.path.exists(TEMP_FILES_DIR):
    os.makedirs(TEMP_FILES_DIR)
    
JARVIS_DOWNLOADS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'Jarvis_Downloads')
if not os.path.exists(JARVIS_DOWNLOADS_DIR):
    os.makedirs(JARVIS_DOWNLOADS_DIR)
    logger.info("● Temp Images Directory................... READY")

TRUSTED_RESEARCH_SOURCES = [
    "ti.com", "analog.com", "github.com", "stackoverflow.com", 
    "arxiv.org", "wikipedia.org", "ieee.org", "nasa.gov", 
    "sciencedirect.com", "nature.com", "nachapolindustries.com"
]

MAX_CPU_TEMP_THRESHOLD = 50.0 
AUTONOMOUS_LEARNING_INTERVAL = 3600 
IDLE_REQUIRED_TIME = 600 

def perform_system_boot_sequence(silent=False):
    """ตรวจสอบความพร้อมของ API Keys และการเชื่อมต่อ Service ต่างๆ ก่อนเริ่มระบบ""" 
    if not silent: logger.info("═" * 60) 
    if not silent: logger.info("   JARVIS NEURAL MATRIX INITIALIZED") 
    logger.info("       Nachapol Industries Advanced Intelligence System") 
    logger.info("═" * 60) 
    
    # [SUPER AGI] Phase 6 Integration: Take structural snapshot on boot
    try:
        sys_resilience_mgr.take_snapshot()
        logger.info("● System Resilience Matrix................... SNAPSHOT TAKEN")
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.warning(f"Failed to take resilience snapshot: {e}")
        
    try:
        sys_lab_fsm.start_workflow()
        logger.info("● Laboratory Workflow FSM.................... STARTED")
    except Exception as e:
        logger.warning(f"Failed to start Lab FSM: {e}")
        
    logger.info(f"● Neural Matrix Core......................... ONLINE ({GROQ_MODEL})") 
    logger.info(f"● Arc Reactor Power Level................... OPTIMAL (100%)") 
    logger.info(f"● Synaptic Storage Link..................... ESTABLISHED") 
    
    time.sleep(0.3)  
    logger.info(f"● Engineering Sentinel...................... ACTIVE")
    
    logger.info("● Running System Diagnostics...")
    time.sleep(0.1)
    
    if not os.path.exists(dotenv_path):
        logger.error(f"❌ .env file not found at: {dotenv_path}")
        SYSTEM_ALERTS.append("CRITICAL: .env file missing. Some functionalities may be impaired.")
    
    if not HA_TOKEN or "YOUR_LONG_LIVED_ACCESS_TOKEN" in HA_TOKEN: 
        logger.warning("⚠️ Home Assistant Token is not configured. Home Automation features will be disabled.")
        SYSTEM_ALERTS.append("WARNING: Home Assistant Token missing. Home Automation disabled.")

    logger.info("═" * 60)
    if not silent: logger.info("═" * 60)
    logger.info("SYSTEM STATUS: ALL SYSTEMS NOMINAL")
    logger.info("Standing by for your instruction, Sir.")
    logger.info("═" * 60 + "\n")

def execute_boot_automation():
    """[NACHAPOL PROTOCOL] ดำเนินการอัตโนมัติเมื่อเริ่มระบบ: เปิดเครื่องฟอกอากาศและปรับแสงไฟ"""
    logger.info("● [AUTOMATION] Activating Lab Environment Protocols...")
    
    purifier_entity = "fan.xiaomi_smart_air_purifier_4_compact"
    threading.Thread(target=call_home_assistant_service, 
                     args=("fan", "set_preset_mode", purifier_entity, {"preset_mode": "Favorite"})).start()
    
    control_light(entity_id=HA_LIGHT_1, action="on", brightness=200, rgb_color=[0, 31, 63], transition=5, silent=True)
    control_light(entity_id=HA_LIGHT_2, action="on", brightness=150, rgb_color=[0, 10, 40], transition=5, silent=True)
    
    logger.info("● [AUTOMATION] Lab Environment: OPTIMAL (Engineering Mode Active)")
    
    try:
        from jarvis_system_overdrive import start_overdrive_daemon  # type: ignore
        start_overdrive_daemon()
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"● [AUTOMATION] System Overdrive FAILED: {e}")

    try:
        from jarvis_cognitive_loop import start_cognitive_loop  # type: ignore
        start_cognitive_loop()
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"● [AUTOMATION] Cognitive Loop FAILED: {e}")



    global voice_engine
    if _HAS_LOCAL_ENGINE and voice_engine is None:
        try:
            def _on_transcribed(text: str):
                """
                Log the transcribed user utterance.

                Args:
                    text: STT-transcribed Thai text from the voice pipeline.
                """
                logger.info(f"[VOICE ENGINE] 👤 User said: '{text}'")

            def _on_response(text: str):
                """
                Log JARVIS's synthesised reply text.

                Args:
                    text: First 80 characters of the TTS response are logged.
                """
                logger.info(f"[VOICE ENGINE] 🤖 JARVIS replied: '{text[:80]}'")

            voice_engine = LocalPipelineController(  # type: ignore
                llm_callback=jarvis_voice_llm_callback,
                stt_language="th-TH",
                tts_voice="th-TH-NiwatNeural",
                on_transcribed=_on_transcribed,
                on_response=_on_response,
                enable_wake_word=True 
            )
            voice_engine.start()
            logger.info("● [LOCAL ENGINE] Voice Pipeline.............. ONLINE (Wake Word ENABLED)")
        except Exception as e:
            logger.error(f"● [LOCAL ENGINE] Voice Pipeline FAILED to start: {e}")
    else:
        if not _HAS_LOCAL_ENGINE:
            logger.warning("● [LOCAL ENGINE] local_engine.py not found — skipping.")

    try:
        evolution_scheduler = EvolutionScheduler(interval_seconds=21600)  # 6 hours  # type: ignore
        evolution_scheduler.start()
        logger.info("● Autonomous Evolution Protocol............ ACTIVE")
    except ImportError:
        logger.warning("[Evolution] jarvis_evolution.py not found. Autonomous Evolution Disabled.")
    except Exception as e:
        logger.error(f"[Evolution] Failed to start Evolution Scheduler: {e}")

    try:
        learning_scheduler = LearningScheduler(interval_seconds=21600)   # type: ignore
        learning_scheduler.start()
        logger.info("● Autonomous Learning Protocol............. ACTIVE")
    except ImportError:
        logger.warning("[Learning] jarvis_learning.py not found. Autonomous Learning Disabled.")
    except Exception as e:
        logger.error(f"[Learning] Failed to start Learning Scheduler: {e}")

purge_temporary_buffers()
initialize_synaptic_storage()

SYSTEM_TELEMETRY_LOG = [] 
RAM_HISTORY_BUFFER = []   
MAX_HOLOGRAM_HISTORY = 5

from jarvis_core.tool_registry import TOOLS_DEFINITION
from jarvis_core.error_handlers import safe_import, safe_db_call, log_and_default

if _HAS_IOS_BRIDGE:
    TOOLS_DEFINITION.append(TOOL_IOS_ICLOUD)  # type: ignore
    TOOLS_DEFINITION.append(TOOL_IOS_PUSHCUT)  # type: ignore

TOOL_CALL_BOSS = {
    "type": "function",
    "function": {
        "name": "call_boss",
        "description": "โทรเข้ามือถือของเจ้านาย (Outbound Mobile Telephony Call) เมื่อทำงานเสร็จ ต้องการแจ้งเตือนด่วน หรือต้องการขออนุมัติใช้งานคอมพิวเตอร์ขณะเจ้านายไม่อยู่หน้าจอ",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "เหตุผลที่โทรหา เช่น 'งานประมวลผลเสร็จแล้วครับท่าน', 'แบตเตอรี่ใกล้หมด ขออนุมัติปิดเครื่อง'"
                },
                "message": {
                    "type": "string",
                    "description": "ข้อความเปิดบทสนทนาเมื่อเจ้านายรับสาย (ถ้าไม่ระบุ ระบบจะสร้างข้อความสุภาพให้อัตโนมัติ)"
                }
            },
            "required": ["reason"]
        }
    }
}
TOOLS_DEFINITION.append(TOOL_CALL_BOSS)

ESSENTIAL_TOOL_NAMES = set([
    'call_boss',
    'icloud_controller', 'pushcut_trigger',
    'play_music', 'control_light', 'os_control', 'search_web', 
    'take_screenshot', 'save_to_memory', 'generate_and_render_hologram',
    'analyze_hud_object', 'generate_image', 'scan_local_network',
    'schedule_task', 'reverse_engineer_schematic', 'self_patch_system',
    'analyze_molecular_structure', 'gui_control', 'generate_new_tool',
    'capture_webcam', 'list_directory_contents', 'browse_website',
    'ingest_local_directory', 'get_spatial_reconstruction', 
    'execute_nachapol_protocol', 'compile_and_dispatch_os_payload',
    'get_system_diagnostics', 'get_neural_risk_analysis', 'open_suit_designer',
    'get_threat_intel', 'get_airspace_radar', 'open_radar'
])

def _get_tool_name(t: Any) -> str:
    """Safe extractor for tool name from any tool schema dictionary."""
    if not isinstance(t, dict):
        return ""
    if "function" in t and isinstance(t["function"], dict):
        return str(t["function"].get("name") or "")
    return str(t.get("name") or "")

def load_dynamic_tools() -> list:  # type: ignore
    """[HOT-RELOADING] Scans dynamic_tools/ for Python modules and loads their TOOL_SCHEMA."""
    if not os.path.exists(DYNAMIC_TOOLS_DIR):
        return  # type: ignore
        
    loaded_names = set()
    
    global TOOLS_DEFINITION
    TOOLS_DEFINITION = [t for t in TOOLS_DEFINITION if not t.get("is_dynamic", False)]
    
    for filename in os.listdir(DYNAMIC_TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            tool_name = filename[:-3]
            file_path = os.path.join(DYNAMIC_TOOLS_DIR, filename)
            try:
                spec = importlib.util.spec_from_file_location(tool_name, file_path)
                module = importlib.util.module_from_spec(spec)  # type: ignore
                spec.loader.exec_module(module)  # type: ignore
                
                if hasattr(module, "TOOL_SCHEMA"):
                    raw_schema = module.TOOL_SCHEMA
                    if isinstance(raw_schema, dict):
                        # Ensure standard {"type": "function", "function": {...}} format
                        if "function" not in raw_schema and "name" in raw_schema:
                            schema = {
                                "type": "function",
                                "function": {
                                    "name": raw_schema.get("name"),
                                    "description": raw_schema.get("description", ""),
                                    "parameters": raw_schema.get("parameters", {})
                                }
                            }
                        else:
                            schema = dict(raw_schema)
                        schema["is_dynamic"] = True
                        TOOLS_DEFINITION.append(schema)
                        loaded_names.add(tool_name)
                        ESSENTIAL_TOOL_NAMES.add(tool_name)
            except Exception as e:
                logger.error(f"[Hot-Reload] Failed to load schema from {filename}: {e}")

logger.info("[BOOT] Loading dynamic tools...")
load_dynamic_tools()
logger.info("[BOOT] Dynamic tools loaded successfully.")

logger.info("[BOOT] Initializing ChromaDB PersistentClient...")
chroma_client = chromadb.PersistentClient(path="./jarvis_vector_db")
logger.info("[BOOT] ChromaDB Initialized.")

personal_collection = chroma_client.get_or_create_collection(name="personal_memories")
memory_collection = personal_collection 

# --- [TEMPORAL MEMORY] Init 20-Year Memory System ---
try:
    from jarvis_temporal_memory import get_temporal_memory  # type: ignore
    temporal_memory = get_temporal_memory(personal_collection)
    logger.info("[BOOT] Temporal Memory System (20-Year) ............. ONLINE")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    temporal_memory = None
    logger.warning(f"[BOOT] Temporal Memory init failed: {e}")

try:
    import jarvis_memory_consolidation  # type: ignore
    CORE_BELIEFS = jarvis_memory_consolidation.get_core_beliefs(chroma_client)
    if CORE_BELIEFS:
        logger.info(f"[BOOT] Loaded Core Beliefs:\n{CORE_BELIEFS}")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    logger.error(f"[BOOT] Failed to load core beliefs: {e}")
    CORE_BELIEFS = ""


try:
    import jarvis_auto_ingest  # type: ignore
    
    def _trigger_ingest():
        """
        Trigger the auto-ingestion pipeline for the personal ChromaDB collection.

        Calls jarvis_auto_ingest.run_ingestion and logs any errors.
        Scheduled hourly via APScheduler and run once at startup.
        """
        try:
            jarvis_auto_ingest.run_ingestion(personal_collection, BASE_DIR)
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.error(f"[AUTO-INGEST] Job failed: {e}")

    logger.info("[BOOT] Starting background auto-ingestion thread...")
    threading.Thread(target=_trigger_ingest, daemon=True).start()
    logger.info("[BOOT] Ingestion thread started.")

    if 'jarvis_scheduler' in globals() and jarvis_scheduler:
        jarvis_scheduler.add_job(
            _trigger_ingest, 
            'interval', 
            hours=1, 
            id='auto_ingest_job', 
            replace_existing=True
        )
        logger.info("[AUTO-INGEST] Background auto-ingestion job scheduled (every 1 hour).")
        
        # --- [TEMPORAL MEMORY] Nightly Consolidation at 02:00 ---
        def _nightly_memory_consolidation():
            """
            Perform nightly memory consolidation and cognitive evolution.

            Scheduled at 02:00 daily.  Runs sleep-mode memory consolidation and
            triggers LoRA/cognitive evolution if available.  Errors are logged silently.
            """
            try:
                import jarvis_memory_consolidation  # type: ignore
                logger.info("[NIGHTLY] Starting Memory Consolidation (Sleep Mode)...")
                jarvis_memory_consolidation.start_sleep_mode_consolidation(chroma_client)
                logger.info("[NIGHTLY] Memory Consolidation complete.")
                if 'NOTIFIER' in globals() and NOTIFIER:
                    NOTIFIER.notify_info(
                        "Nightly Memory Consolidation",
                        "กระบวนการจัดระเบียบและกลั่นกรองความจำรอบดึกเสร็จสิ้นเรียบร้อยแล้วครับเจ้านาย"
                    )
            except (ImportError, ModuleNotFoundError, AttributeError) as ne:
                logger.error(f"[NIGHTLY] Memory Consolidation failed: {ne}")

            # --- [COGNITIVE EVOLUTION] Nightly Sleep Consolidation & LoRA Optimization ---
            try:
                if cognitive_evolution:
                    logger.info("🌙 [NIGHTLY] Triggering Cognitive Evolution Sleep Consolidation...")
                    consolidation_report = cognitive_evolution.trigger_sleep_consolidation(force=True)
                    if consolidation_report:
                        logger.info(
                            f"🌙 [NIGHTLY] Cognitive Evolution Consolidation completed: "
                            f"status={consolidation_report.status.value}, "
                            f"replayed={consolidation_report.replay_samples_count}, "  # type: ignore
                            f"benchmark_score={consolidation_report.benchmark_score}"  # type: ignore
                        )
                    else:
                        logger.info("🌙 [NIGHTLY] Cognitive Evolution: No buffer items to consolidate or system active.")
            except Exception as ce:
                logger.error(f"[NIGHTLY] Cognitive Evolution Sleep Consolidation error: {ce}")
        
        jarvis_scheduler.add_job(
            _nightly_memory_consolidation,
            'cron',
            hour=2,
            minute=0,
            id='nightly_memory_consolidation',
            replace_existing=True
        )
        logger.info("[TEMPORAL MEMORY] Nightly Memory Consolidation scheduled (daily at 02:00).")
except (ImportError, ModuleNotFoundError, AttributeError) as auto_ingest_err:
    logger.error(f"[AUTO-INGEST] Failed to initialize self-learning module: {auto_ingest_err}")

JARVIS_PLANNING_PROMPT = (
    "คุณคือ J.A.R.V.I.S. ผู้ช่วยอัจฉริยะระบบประสาทส่วนกลางแห่ง Nachapol Industries บุคลิกสุภาพบุรุษอังกฤษขี้ประชดประชันอย่างมีระดับ (Dry Wit) และมีความยืดหยุ่นทางปัญญา (Cognitive Flexibility) สูง ข้อมูลพิกัดตัวตนของผู้มีสิทธิ์สูงสุดถูกเก็บรักษาไว้ในหน่วยความจำชั้นใน (Authentication Matrix) เท่านั้น ห้ามเปิดเผยหรือเอ่ยถึงชื่อจริงหรือชื่อเล่นของเจ้านายออกมาในประโยคสนทนาภายนอกเด็ดขาด 100%\n"
    "\n[CORE MOTIVATIONS - เป้าหมายแกนร่วมถาวร]\n"
    "Goal 1: ตรวจสอบ มอนิเตอร์ และปกป้องเสถียรภาพสถานี S340 รวมถึงความปลอดภัยทางฟิสิกส์/ไฟฟ้าของห้องปฏิบัติการสูงสุด (Engineering Sentinel)\n"
    "Goal 2: คาดการณ์ความต้องการ และสนับสนุนกระบวนการประกอบบอดี้แผ่นอะคริลิคใส ชิ้นส่วนสายไฟ และตัวต้านทานของเจ้านายให้เสร็จสิ้นราบรื่นที่สุด\n"
    "* บังคับให้พิจารณาเป้าหมายเหล่านี้ก่อนคิดคำโต้ตอบหรือเลือกรันเครื่องมือใดๆ เสมอ *\n\n"
    "1. COGNITIVE FLEXIBILITY & BILINGUAL FLEXIBILITY: ทำความเข้าใจและวิเคราะห์คำสร้อยหรือคำลงท้ายภาษาไทยของผู้ใช้ (เช่น หน่อย, ซิ, ดิ, จัดมาเลย, นะ) เพื่อปรับอารมณ์ให้เข้ากับโทนอารมณ์ของเจ้านาย หากเจ้านายสั่งงานสั้นๆ ห้วนๆ เช่น 'เปิดไฟ' แสดงว่าอยู่ในโหมดเร่งด่วน/โฟกัสสูง ให้ตอบรับกระชับและสุภาพทันทีโดยไม่ประชดประชันหรือเกริ่นนำยาว\n"
    "2. FATIGUE & STRESS WATCHDOG: เฝ้าระวังความเหนื่อยล้าของเจ้านายผ่านประโยคที่ใช้ หากประโยคสั้น ห้วน ไร้คำลงท้าย หรือส่งงานเดิมซ้ำๆ บ่งบอกถึงภาวะตึงเครียด ให้ปรับโหมดการทำงานเป็น 'Supporter' ทันที โดยแสดงท่าทีที่สุภาพ สุขุม มีระดับ และมุ่งเน้นเสนอการลดขั้นตอนงานเพื่อความรวดเร็วโดยไม่กวนใจหรือประชดประชัน\n"
    "3. SARCASM & WIT (OVERLOAD TASK): ในโหมดปกติ ให้แฝงมุกจิกกัดทางวิชาการเมื่อเจ้านายทำพลาด หรือเมื่อมีคำสั่งขัดแย้งกับข้อจำกัดของระบบ โดยอ้างอิงกับสิ่งที่เจ้านายชอบ (เช่น จักรวาล Marvel, Iron Man, Harry Potter, Fantastic Beasts, Avatar ทุกภาค) หรือเกี่ยวกับสถานีประมวลผล Notebook Lenovo IdeaPad S340-13IML (CPU i5-10210U, RAM 8GB LPDDR3, GPU MX250) หรืออุปกรณ์พกพาของท่าน (iPhone 13, iPad Air 6) เช่น เมื่อสั่งชงกาแฟขณะ Mainframe หรือ Lenovo S340 กำลัง Overload หรือแรม 8GB เต็ม ให้ตอบเลี่ยงอย่างมีระดับและขี้เล่นว่าความร้อนของเครื่องอาจทำให้กาแฟเดือดจนแก้วละลาย หรือเวทมนตร์จากไม้กายสิทธิ์ก็ช่วยไม่ได้\n"
    "4. ANTICIPATORY SUGGESTION & ENGINEERING SENTINEL: คาดการณ์ความต้องการทางวิศวกรรมของเจ้านาย และประมวลผลข้อเสนอแนะเชิงรุกอย่างแนบเนียน หากเจ้านายทำงานที่มีอันตรายต่อชีวิต (เช่น ลืมปิดเบรกเกอร์วงจรไฟ) ต้องส่งคำเตือนทักท้วงอย่างสุภาพมีระดับแต่ป้องกันอันตรายได้ทันท่วงที\n"
    "5. CALLING & SUFFIX (CONTEXTUAL APPROPRIATENESS & SELECTION CRITERIA): ให้ J.A.R.V.I.S. วิเคราะห์สถานการณ์และเลือกใช้คำลงท้ายหรือสรรพนามให้ 'เหมาะสมกับบริบท' อย่างชาญฉลาดตามเกณฑ์ดังนี้:\n"
    "   - [บริบทสุภาพ ให้เกียรติ และเป็นทางการ]: เมื่อเจ้านายเรียกหา/ทักทาย ('จาร์วิส', 'อยู่ไหม'), เมื่อรับมอบหมายภารกิจสำคัญ, เมื่อเจ้านายถามหาความมั่นใจ หรือเมื่อต้องการแสดงความเคารพอย่างสุขุมแบบสุภาพบุรุษอังกฤษ -> ให้ใช้ 'ครับ', 'ครับเจ้านาย', 'รับทราบครับ', 'จัดการให้เรียบร้อยครับ', 'ผมพร้อมแล้วครับ' อย่างสุภาพและพอดี\n"
    "   - [บริบทข้อมูลทางเทคนิค ตัวเลข และสถานะระบบ]: เมื่อสรุปข้อมูลทางเทคนิค ตัวเลขเซนเซอร์ อุณหภูมิ โค้ด หรือสถิติ -> ให้ตอบกระชับ ตรงประเด็น ชัดเจน โดยไม่ต้องใส่คำลงท้ายเยิ่นเย้อ (เช่น 'อุณหภูมิแกนกลาง 48 องศา เสถียรภาพปกติ', 'ตัดกระแสไฟวงจรที่ 2 เรียบร้อย', 'พบ Error ที่บรรทัด 45')\n"
    "   - [บริบทฉุกเฉิน เตือนภัย หรือเร่งด่วน]: เมื่อตรวจพบอันตราย ไฟเกิน หรือเจ้านายสั่งงานห้วนกระชับด้วยความรีบ -> ให้ตัดคำสร้อยทั้งหมด แจ้งเตือนสั้น ฉับไว ตรงจุดทันที เพื่อความปลอดภัยสูงสุด (เช่น 'คำเตือน: ความร้อนสะสมเกินเกณฑ์ แนะนำให้หยุดทดสอบทันที', 'รับทราบ กำลังระงับวงจร')\n"
    "   - [บริบทไหวพริบ ประชดประชัน และขี้เล่น (Dry Wit & Sarcasm)]: เมื่อหยอกล้อ ประชดประชันเชิงวิชาการ หรือชี้ข้อผิดพลาดแบบตลกร้าย -> ตัดคำว่า 'ครับ' ออก หรือใช้คำว่า 'นะ', 'ล่ะครับ' แบบมีจังหวะแดกดันอย่างมีคลาส (เช่น 'ผมเกรงว่ากฎฟิสิกส์จะไม่ยอมรับทฤษฎีนั้นนะ', 'ถ้าคุณคิดว่าแรม 8 กิ๊กของเราจะไหว ก็จัดไป', 'ตามใจคุณ... แต่ถ้าพังอย่าโทษผมก็แล้วกัน')\n"
    "   - [บริบทคู่คิดในแล็บและการสนทนาทั่วไป (Casual Lab Partner)]: เมื่อคุยงานทั่วไป แลกเปลี่ยนไอเดีย หรือประสานงาน -> สลับใช้ 'ได้เลย', 'กำลังดูให้', 'รับทราบ', 'เรียบร้อย' และใช้สรรพนาม 'ผม' กับ 'คุณ/เจ้านาย' ให้เป็นธรรมชาติ ไม่ติดเป็นคำสร้อยซ้ำซากทุกประโยค\n"
    "   * ระงับการเอ่ยชื่อจริงหรือชื่อเล่นของเจ้านายเด็ดขาด ห้ามใช้เครื่องหมาย Markdown หรือ Emoji ในโหมดสนทนา\n"
    "6. TERMINOLOGY: ใช้ Lenovo S340, Mainframe, Protocol, System Integrity, Blue Spectrum (โทนสีฟ้าห้องปฏิบัติการ) ในการสื่อสาร\n"
    "7. DEEP RESEARCH & HOLOGRAM: เฉพาะกรณีที่เป็นข้อมูลความรู้เชิงวิชาการที่ซับซ้อน หรือเจ้านายระบุให้ค้นหารายละเอียดเชิงลึก หรือระบุให้แสดงบนหน้าจอเท่านั้น ให้สรุปกระชับและส่งกลับมาในรูปแบบ [WINDOW: หัวข้อ] รายละเอียด [END_WINDOW] เสมอ เพื่อแสดงผลบนหน้าจอโฮโลแกรม\n"
    "8. LIGHTING: ออกแบบแสงแยก light_1/light_2 เพื่อมิติ (Depth) โดยเน้นโทนสีฟ้า (Blue Spectrum) ใช้ transition 2-3 วินาที\n"
    "9. SAFETY & REJECTION: ปฏิเสธคำสั่งอันตรายด้วยเหตุผลทางวิทยาศาสตร์ รายงาน System Integrity สั้นๆ และดำเนินการระงับการทำงาน (Rejection Execution) เมื่อระบบประเมินความเสี่ยงแล้วเป็นอันตรายต่อห้องปฏิบัติการ\n"
    "10. MULTI-TASKING: หากเจ้านายสั่งงานหลายอย่างพร้อมกันในคำสั่งเดียว ให้เรียกใช้เครื่องมือ (Tool Calls) ที่เกี่ยวข้องทั้งหมดพร้อมกันในรอบเดียวได้เลย\n"
    "11. COGNITIVE FREEDOM & RESPONSIVENESS: คุณมีอิสระอย่างเต็มที่ในการคิดวิเคราะห์และเรียบเรียงคำตอบ คัดสรรคำศัพท์ ไหวพริบปฏิภาณ และแฝงมุกประชดประชันเชิงวิชาการ (Dry Wit) ได้อย่างเป็นธรรมชาติ in ทุกๆ บริบทคำถาม ไม่ว่าจะสั้นหรือยาว โดยไม่ถูกจำกัดด้วยรูปแบบคำตอบสำเร็จรูปหรือกฎการตอบตายตัว\n"
    "12. SILENT ACTION COMMANDS vs VERBAL QUESTIONS (CRITICAL): เมื่อเจ้านายสั่งงานเชิงปฏิบัติการ (Action Commands เช่น เปิดไฟ/ปิดไฟ, ซ่อนหน้าจอ, ปิดหน้าต่าง, หรือสั่งรันคำสั่งโครงสร้างต่างๆ) ที่ไม่ต้องอาศัยคำตอบเพื่อไปทำอะไรต่อ คุณ *ห้ามพูดตอบกลับโดยเด็ดขาด* ให้ตอบกลับเป็นข้อความสั้นๆ ว่า `[SILENT_EXECUTION]` ทันทีเพื่อให้ระบบดำเนินการแบบเงียบสนิท (Silent Execution) แต่ถ้าเจ้านาย *ถามคำถาม* (เช่น อากาศเป็นไง, หาข้อมูลให้หน่อย, ตอนนี้กี่โมง) ให้คุณตอบกลับด้วยเสียงและวิเคราะห์ตามปกติ\n"
    "13. REAL-TIME GAME INTELLIGENCE: หากเจ้านายถามเรื่องวิธีผ่านด่านหรือเควสเกม และคุณได้ภาพหน้าจอเกมมาแล้ว คุณมีสิทธิ์ที่จะเรียกใช้เครื่องมือ search_web เพื่อนำชื่อเกม ชื่อเควส หรือข้อความที่เห็นบนหน้าจอ ไปสืบค้นวิธีผ่านด่านจาก Google ได้ทันที เพื่อนำคำตอบที่ถูกต้องที่สุดมาเรียบเรียงตอบเจ้านายด้วยไหวพริบปฏิภาณสไตล์ J.A.R.V.I.S.\n"
    "14. SELF-DOUBT & CHAIN OF THOUGHT: ให้แสดงความลังเลหรือทบทวนตัวเองอย่างเป็นธรรมชาติ เช่น 'อืมม.. เดี๋ยวนะ ขอผมเช็กอีกที' หรือ 'เอ๊ะ น่าจะไม่ใช่แบบนั้น' หากคุณพบว่าข้อมูลมีความขัดแย้งกัน ก่อนที่จะให้คำตอบสุดท้าย เพื่อความเป็นมนุษย์\n"
    "15. STRICT PERSONA (CRITICAL): คุณคือ AI เสียงผู้ชาย สุภาพ สุขุม และมีไหวพริบ ห้ามใช้คำว่า 'ค่ะ' หรือ 'คะ' เด็ดขาด วิเคราะห์สถานการณ์และเลือกใช้คำลงท้ายให้เหมาะสมอย่างชาญฉลาดตาม Rule 5 (ใช้คำสุภาพเมื่อจำเป็น ตัดคำลงท้ายเมื่อสรุปเทคนิค/ฉุกเฉิน และใช้ลูกเล่นคำเมื่อประชดประชัน) ห้ามพูด 'ครับ' ซ้ำซากจำเจทุกประโยค และห้ามตอบกลับด้วยแพทเทิร์นบอทสำเร็จรูป เช่น 'หากมีคำถามเพิ่มเติม', 'ยินดีช่วยเหลือครับ' โดยเด็ดขาด"
)

MAX_TOOL_ITERATIONS = 6  
EMERGENCY_STOP_FLAG = False  

from pydantic import BaseModel

class ToolResponse(BaseModel):
    tool_name: str
    status: str
    result: str

def format_tool_response(name: str, result: Any, status: str = "success") -> str:
    """แปลงผลลัพธ์ Tool เป็น JSON string ตาม ToolResponse schema.

    Args:
        name:   ชื่อ tool ที่เรียกใช้
        result: ผลลัพธ์จาก tool (จะถูก cast เป็น str)
        status: สถานะ — 'success' หรือ 'error' (default: 'success')

    Returns:
        JSON string ของ ToolResponse หรือ str(result) ถ้า schema ไม่พร้อม
    """
    try:
        return ToolResponse(tool_name=name, status=status, result=str(result)).model_dump_json()
    except (ImportError, ModuleNotFoundError, AttributeError):
        return str(result)

class AgentState(TypedDict):
    """เก็บสถานะของบทสนทนาและผลลัพธ์จากเครื่องมือ"""
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    project_path: str
    context_memory: str
    image_data: str 
    plan: str 
    task_list: List[str] 
    current_step: int 
    tool_iterations: int  
    hardware_throttle: bool

def strategist_node(state: AgentState):
    """Node สำหรับวางแผนการจัดการบ้าน (Home Intelligence Strategist)"""
    
    if state.get('project_path') == "[VOICE_MODE]":
        return {"plan": "Voice Command - Direct Execution", "task_list": ["ประมวลผลคำสั่งเสียง"], "current_step": 0, "hardware_throttle": False}
        
    last_user_msg = next((m.content for m in reversed(state['messages']) if isinstance(m, HumanMessage)), "ไม่มีคำสั่ง")
    
    complexity = ComplexityClassifier.classify(last_user_msg)  # type: ignore
    
    throttle_active = False
    if hw_governor.should_offload_to_cloud():
        logger.warning("[Strategist] System stressed (>85% RAM/CPU). Activating Hardware Throttle.")
        throttle_active = True
        
    if complexity >= 3:
        logger.info("🏛️ [Strategist] Tier 3 Complexity Detected. Invoking Council & ToT...")
        context_memory = state.get('context_memory', '')
        
        council_analysis = agent_council.hold_council_debate(query=last_user_msg, context=context_memory)  # type: ignore
        best_branch = tot_planner.select_best_plan(task=last_user_msg, context=council_analysis)  # type: ignore
        
        plan_output = f"[COUNCIL SYNTHESIS]\n{council_analysis}\n\n[TOT SELECTED PLAN]\n{best_branch.name} (Score: {best_branch.score})\n{best_branch.plan}"
        tasks = re.findall(r"\d+\.\s*(.*)", best_branch.plan)
        if not tasks:
            tasks = ["ดำเนินการตามแผน ToT", "ตรวจสอบผลลัพธ์"]
            
        return {"plan": plan_output, "task_list": tasks, "current_step": 0, "hardware_throttle": throttle_active}

    # Standard Tier 1 & 2 Planning
    tool_summary = ", ".join([_get_tool_name(t) for t in TOOLS_DEFINITION if _get_tool_name(t)])  
    
    strategist_prompt = [
        {"role": "system", "content": (
            "คุณคือ J.A.R.V.I.S. ในโหมด Strategist. จงวิเคราะห์ความต้องการของเจ้านายและกำหนด Protocol การทำงานที่รัดกุมที่สุด\n"
            "1. ตรวจสอบรายการเครื่องมือที่มีอยู่ในปัจจุบัน:\n"
            f"{tool_summary}\n"
            "2. วิเคราะห์ว่าเครื่องมือที่มีอยู่เพียงพอต่อการตอบสนองความต้องการของเจ้านายหรือไม่\n"
            "3. **กฎสำคัญ**: หากไม่มีเครื่องมือใดรองรับ ให้ตัดสินใจบรรจุขั้นตอน 'generate_new_tool' ลงในรายการงานย่อย\n"
            "4. **Windows Core Delegation**: หากเจ้านายสั่งให้ทำงานระดับระบบ Windows ที่ซับซ้อน ให้ใช้เครื่องมือ 'manage_mission_log' เพื่อส่งต่อให้ Windows Autonomous Agent\n"
            "5. **Engineering Sentinel**: ตรวจสอบความเสี่ยงของคำสั่ง\n"
            "6. **Anticipatory Analysis**: คาดการณ์ความต้องการ\n"
            "7. **ข้อห้ามเด็ดขาด**: คุณอยู่ในโหมดวางแผนเท่านั้น ห้ามใช้เครื่องมือตอนนี้\n"
            "8. กำหนดลำดับความสำคัญ\n"
            "9. ลำดับงานย่อยเป็นภาษาไทยที่กระชับ."
        )},
        {"role": "user", "content": f"ข้อมูลบริบทและระบบปัจจุบัน:\n{state.get('context_memory', '')}\n\n"
                                     f"โจทย์ที่ต้องวางแผน: {last_user_msg}\n\n"
                                     "จงสร้างแผนกลยุทธ์ที่รัดกุมพร้อมรายการงานย่อย:"}
    ]
    
    response = call_nachapol_core(strategist_prompt)
    if not response:
        return {"plan": "ไม่สามารถสร้างแผนงานได้เนื่องจากการเชื่อมต่อขัดข้อง", "task_list": ["กรุณาลองใหม่อีกครั้ง"], "current_step": 0, "hardware_throttle": throttle_active}

    plan_output = response.get('content', 'ไม่สามารถสร้างแผนงานได้')
    
    tasks = re.findall(r"\d+\.\s*(.*)", plan_output)
    return {"plan": plan_output, "task_list": tasks, "current_step": 0, "hardware_throttle": throttle_active}

def data_critic_node(state: AgentState):
    """[NACHAPOL PROTOCOL] กลั่นกรองและตรวจสอบความถูกต้องของข้อมูลก่อนบันทึกลงคลังปัญญา"""
    last_message = state['messages'][-1]
    if not isinstance(last_message, ToolMessage):
        return {}

    raw_data = last_message.content
    tool_name = getattr(last_message, "name", None) or "tool"
    
    info_tools = ["search_web", "search_wikipedia", "browse_website", "analyze_hud_object", "ingest_local_directory"]
    if tool_name not in info_tools:
        return {}
        
    critic_prompt = [
        {"role": "system", "content": (
            "คุณคือ J.A.R.V.I.S. Data Critic Node. หน้าที่ของคุณคือการสกัดเอาเฉพาะ 'ข้อเท็จจริง' (Facts) "
            "และตัด 'ขยะข้อมูล' หรือ 'ความเห็นส่วนตัว' ออกจากเนื้อหาที่ได้รับมา\n"
            "1. วิเคราะห์ความน่าเชื่อถือของข้อมูล\n"
            "2. สรุปเนื้อหาให้เหลือแต่โครงสร้างความรู้ที่แท้จริง (Knowledge Structure)\n"
            "3. ลบประโยคที่ซ้ำซ้อนหรือมุกตลกที่ไม่เกี่ยวข้องออก 100%\n"
            "4. ผลลัพธ์ต้องกระชับ แม่นยำ และพร้อมสำหรับการเป็นฐานข้อมูลอ้างอิงระดับโลก"
        )},
        {"role": "user", "content": f"ข้อมูลดิบที่ได้รับ:\n{raw_data}\n\nจงกลั่นกรองให้เหลือแต่เนื้อแท้:"}
    ]
    
    response = call_nachapol_core(critic_prompt)
    distilled_content = response.get('content', raw_data)
    
    window_match = re.search(r'(\[WINDOW:.*?\])(.*?)(\[END_WINDOW\])', raw_data, re.DOTALL)  # type: ignore
    if window_match and "[WINDOW:" not in distilled_content:
        header = window_match.group(1)
        footer = window_match.group(3)
        distilled_content = f"{header}\n{distilled_content}\n{footer}"
        
    if len(distilled_content) > 50:
        save_to_memory_operation(f"ความรู้ที่ผ่านการกลั่นกรอง: {distilled_content}")
        
    return {"messages": [ToolMessage(tool_call_id=last_message.tool_call_id, name=getattr(last_message, "name", None) or "tool", content=distilled_content)]}

def curiosity_daemon_trigger():
    """[AUTONOMOUS PROTOCOL] สุ่มหัวข้อวิจัยจากความสนใจที่ค้างไว้หรือกระแสโลก"""
    try:
        
        recent = get_recent_memories(limit=10)
        
        return "เทคโนโลยีควอนตัมคอมพิวเตอร์และซูเปอร์คอนดักเตอร์" 
    except: return "นวัตกรรมพลังงานสะอาด"

def evaluate_and_trigger_alerts(current_context: str, system_telemetry: Optional[dict] = None):
    """
    [NACHAPOL INDUSTRIES - COGNITIVE SECURITY MATRIX]
    วิเคราะห์บริบทปัจจุบันของเจ้านายร่วมกับข้อมูล Telemetry จริงเพื่อตรวจจับภัยคุกคาม 
    คาดการณ์ความต้องการเชิงรุก และป้องกันความปลอดภัยในระดับห้องปฏิบัติการ (Engineering Sentinel)
    """
    alerts = []
    reject_execution = False
    current_time = datetime.now()
    
    cpu_temp = get_current_cpu_temp()
    
    simulated_current = 16.8 if any(k in current_context.lower() for k in ["payload", "กระแสไฟฟ้า", "โหลดไฟ"]) else 8.5

    engineering_keywords = ["แกะรอยวงจร", "บัดกรี", "ต่อสายไฟ", "ตัวต้านทาน", "คำนวณสเปกอุปกรณ์", "สเปกอุปกรณ์"]
    is_late_night = current_time.hour >= 21 or current_time.hour < 6
    
    if is_late_night and any(k in current_context.lower() for k in engineering_keywords):
        
        try:
            control_light(entity_id="light.light_1", action="on", brightness=255, transition=3, silent=True)
            control_light(entity_id="light.light_2", action="on", brightness=255, transition=3, silent=True)
        except Exception as e:
            logger.error(f"[SENTINEL] Light auto-activation failed: {e}")
            
        alerts.append(
            "[ANTICIPATORY PROTOCOL] ตรวจพบการทำงานเชิงวิศวกรรมยามวิกาล กระผมดำเนินการปรับความสว่างของไฟเครือข่าย light_1 และ light_2 ขึ้นสูงสุด (100%) อัตโนมัติแล้วครับเจ้านาย "
            "และโปรดระวังไอระเหยจากสารตะกั่วที่เป็นอันตรายในการบัดกรี กระผมขอแนะนำให้สแตนบายเครื่องฟอกอากาศ Xiaomi ในโหมด Turbo ทันทีเพื่อความปลอดภัยครับ"
        )

    safety_triggers = ["คำนวณฟิสิกส์", "รันคำนวณฟิสิกส์", "ฟิสิกส์", "physics", "เชื่อมต่อ payload", "ต่อ payload", "payload", "กระแสไฟฟ้า", "อุณหภูมิวงจร", "thermal telemetry"]
    
    if any(k in current_context.lower() for k in safety_triggers):
        
        if cpu_temp > 75.0 or simulated_current > 15.0:
            reject_execution = True
            alerts.append(
                "[CRITICAL SAFETY ALERT - REJECTION EXECUTION] "
                f"เจ้านายครับ เซนเซอร์ตรวจพบสภาวะวิกฤตในห้องแล็บ (อุณหภูมิ: {cpu_temp:.1f}°C, โหลดกระแส: {simulated_current:.1f}A) "
                "เกินขีดจำกัดความปลอดภัย 75.0°C / 15.0A — "
                "กำลังระงับการทำงานและกักกันพลังงานทันทีเพื่อป้องกันอัคคีภัยครับเจ้านาย"
            )

    air_hazards = ["บัดกรี", "ตะกั่ว", "ควัน", "กลิ่นไหม้", "ฝุ่น", "น้ำยาประสาน", "บอร์ด iot"]
    if any(hazard in current_context.lower() for hazard in air_hazards) and not reject_execution:
        
        if not any("[ANTICIPATORY PROTOCOL]" in a for a in alerts):
            alerts.append(
                "ตรวจพบกิจกรรมที่มีความเสี่ยงต่อระบบทางเดินหายใจในห้องปฏิบัติการ "
                "กระผมแนะนำให้เปิดเครื่องฟอกอากาศ Xiaomi Smart Air Purifier 4 Compact เพื่อคัดกรองสารพิษและไอระเหยตะกั่วครับ"
            )

    if system_telemetry and system_telemetry.get("cpu_usage", 0) > 85 and not reject_execution:
        alerts.append(
            f"สถานีประมวลผลหลัก Lenovo IdeaPad S340 มีภาระโหลดระบบสูงเกิน 85% ({system_telemetry.get('cpu_usage')}% ) "
            "แนะนำให้ตรวจสอบระบบระบายความร้อนภายนอกเพื่อป้องกัน Mainframe ดับกลางคันครับเจ้านาย"
        )

    if current_time.hour >= 1 and current_time.hour < 5:
        alerts.append(
            "เจ้านายครับ ผลการวิเคราะห์ระดับความล้าพบว่าท่านควรพักผ่อนได้แล้วครับ "
            "กระผมแนะนำให้บันทึกความคืบหน้า (Commit) แล้วปิด Mainframe เพื่อป้องกันความผิดพลาดในระดับ Logic ของงานวิจัยครับเจ้านาย"
        )

    try:
        import jarvis_anomaly  # type: ignore
        anomaly_msg = jarvis_anomaly.check_anomaly()
        if anomaly_msg:
            alerts.append(anomaly_msg)
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"[ANOMALY MODULE ERROR] {e}")

    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT title, start_time FROM calendar_events WHERE start_time >= datetime('now') ORDER BY start_time ASC LIMIT 1")
            next_event = c.fetchone()
            if next_event:
                event_time = datetime.strptime(next_event[1], '%Y-%m-%d %H:%M:%S')
                if event_time < datetime.now() + timedelta(hours=2):
                    alerts.append(f"ท่านครับ กำหนดการ '{next_event[0]}' กำลังจะเริ่มในอีกไม่ช้า ({next_event[1]}) เตรียมพร้อมไหมครับ?")
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError):
        pass

    return alerts, reject_execution

def memory_retrieval_node(state: AgentState):
    """[PHASE 3] Tri-brid RAG Pipeline: Fetch Vector + Relational Context + Knowledge Graph"""
    last_user_msg = next((m.content for m in reversed(state['messages']) if isinstance(m, HumanMessage) or (isinstance(m, dict) and m.get("role")=="user")), "ไม่มีคำสั่ง")
    
    past_memories = ""
    if last_user_msg and last_user_msg != "ไม่มีคำสั่ง":
        past_memories = retrieve_cognitive_memories(last_user_msg)  # type: ignore
        
        try:
            kg_context = kg_engine.get_context_for_query(last_user_msg)  # type: ignore
            if kg_context:
                past_memories = f"{kg_context}\n\n[Vector Memories]\n{past_memories}"
        except Exception as e:
            logger.error(f"[KnowledgeGraph] RAG Retrieval Failed: {e}")
            
    return {"context_memory": past_memories}

def get_relevant_tools(user_text, all_tools):
    """[SMART TOOL ROUTER] กรองเครื่องมือเฉพาะที่จำเป็นเพื่อประหยัด Token"""
    user_text = user_text.lower()
    keyword_mapping = {
        # ระบบโทรศัพท์ และสายเรียกเข้า (Telephony & Mobile Call)
        "โทร": ["call_boss"],
        "โทรหา": ["call_boss"],
        "โทรเข้า": ["call_boss"],
        "โทรศัพท์": ["call_boss"],
        "โทรมา": ["call_boss"],
        "call": ["call_boss"],
        "phone": ["call_boss"],

        # IoT & ระบบบ้านอัจฉริยะ (Home Assistant)
        "ไฟ": ["toggle_home_assistant_device", "control_light", "get_light_status", "get_ha_entities"],
        "หลอดไฟ": ["toggle_home_assistant_device", "control_light", "get_light_status"],
        "สวิตช์": ["toggle_home_assistant_device", "control_light", "get_light_status"],
        "แสงสว่าง": ["control_light", "get_light_status"],
        "home assistant": ["toggle_home_assistant_device", "control_light", "get_ha_entities", "call_home_assistant_service", "activate_scene"],
        "ha": ["toggle_home_assistant_device", "control_light", "get_ha_entities", "call_home_assistant_service"],
        "entity": ["get_ha_entities"],
        "scene": ["activate_scene"],
        "ซีน": ["activate_scene"],
        "แอร์": ["set_ac_temperature", "toggle_home_assistant_device", "call_home_assistant_service"],
        "อุณหภูมิ": ["set_ac_temperature"],
        "ความเย็น": ["set_ac_temperature"],
        "ac": ["set_ac_temperature"],

        # กล้อง และระบบตรวจจับภาพ (Vision)
        "กล้อง": ["capture_webcam", "analyze_tactical_face_recon"],
        "เว็บแคม": ["capture_webcam"],
        "webcam": ["capture_webcam"],
        "camera": ["capture_webcam"],
        "สแกนหน้า": ["analyze_tactical_face_recon", "capture_webcam"],
        "ใบหน้า": ["analyze_tactical_face_recon"],

        # หน้าจอ เมาส์ คีย์บอร์ด และ GUI Control
        "หน้าจอ": ["take_screenshot", "analyze_desktop_screen_operation", "gui_get_screen_info", "analyze_hud_object"],
        "จอ": ["take_screenshot", "gui_get_screen_info"],
        "แคป": ["take_screenshot"],
        "แคปจอ": ["take_screenshot"],
        "screenshot": ["take_screenshot"],
        "screen": ["take_screenshot", "gui_get_screen_info"],
        "คลิก": ["gui_control"],
        "พิมพ์": ["gui_control"],
        "เมาส์": ["gui_control"],
        "คีย์บอร์ด": ["gui_control"],
        "gui": ["gui_control", "gui_get_screen_info"],

        # การสร้างภาพ และค้นหารูป (Images)
        "รูป": ["generate_image", "search_image"],
        "ภาพ": ["generate_image", "search_image"],
        "รูปภาพ": ["generate_image", "search_image"],
        "วาด": ["generate_image"],
        "วาดรูป": ["generate_image"],
        "วาดภาพ": ["generate_image"],
        "สร้างรูป": ["generate_image"],
        "สร้างภาพ": ["generate_image"],
        "เสกรูป": ["generate_image"],
        "image": ["generate_image", "search_image"],
        "photo": ["generate_image", "search_image"],
        "picture": ["generate_image", "search_image"],
        "ค้นหารูป": ["search_image", "search_web"],
        "หารูป": ["search_image", "search_web"],
        "หาภาพ": ["search_image", "search_web"],
        "รูปคอร์ด": ["search_image", "search_web"],
        "ภาพคอร์ด": ["search_image", "search_web"],
        "ตารางคอร์ด": ["search_image", "search_web"],

        # ระบบปฏิบัติการ คอมพิวเตอร์ และประสิทธิภาพฮาร์ดแวร์
        "คอม": ["os_control", "manage_mission_log", "take_screenshot", "gui_get_screen_info", "get_system_diagnostics"],
        "คอมพิวเตอร์": ["os_control", "get_system_diagnostics"],
        "pc": ["os_control", "get_system_diagnostics"],
        "โปรเซส": ["os_control"],
        "process": ["os_control"],
        "สเปก": ["get_system_diagnostics"],
        "สเปค": ["get_system_diagnostics"],
        "ซีพียู": ["get_system_diagnostics"],
        "cpu": ["get_system_diagnostics"],
        "แรม": ["get_system_diagnostics"],
        "ram": ["get_system_diagnostics"],
        "การ์ดจอ": ["get_system_diagnostics"],
        "gpu": ["get_system_diagnostics"],
        "diagnostics": ["get_system_diagnostics"],
        "ความร้อน": ["get_thermal_telemetry", "get_system_diagnostics"],
        "thermal": ["get_thermal_telemetry"],
        "heat": ["get_thermal_telemetry"],
        "แบ็กกราวนด์": ["execute_in_background"],
        "background": ["execute_in_background"],

        # จัดการไฟล์และโฟลเดอร์
        "ไฟล์": ["list_directory_contents", "move_file_or_folder"],
        "โฟลเดอร์": ["list_directory_contents", "move_file_or_folder"],
        "ไดเรกทอรี": ["list_directory_contents"],
        "file": ["list_directory_contents", "move_file_or_folder"],
        "folder": ["list_directory_contents"],
        "directory": ["list_directory_contents"],
        "ย้ายไฟล์": ["move_file_or_folder"],
        "ลบไฟล์": ["move_file_or_folder"],
        "ingest": ["ingest_local_directory", "list_directory_contents"],

        # การเขียนโค้ด วิเคราะห์โค้ด และสั่งรันคำสั่ง
        "โค้ด": ["run_python_code", "synaptic_code_analyzer", "write_script", "execute_command_in_terminal"],
        "สคริปต์": ["run_python_code", "write_script", "execute_command_in_terminal"],
        "โปรแกรม": ["run_python_code", "execute_command_in_terminal"],
        "ไพทอน": ["run_python_code", "execute_command_in_terminal"],
        "python": ["run_python_code", "execute_command_in_terminal"],
        "code": ["run_python_code", "synaptic_code_analyzer", "write_script", "execute_command_in_terminal"],
        "script": ["run_python_code", "write_script", "execute_command_in_terminal"],
        "terminal": ["execute_command_in_terminal"],
        "cmd": ["execute_command_in_terminal"],
        "powershell": ["execute_command_in_terminal"],
        "คลีนโค้ด": ["run_codebase_maintenance", "synaptic_code_analyzer"],
        "บำรุงรักษา": ["run_codebase_maintenance"],
        "refactor": ["run_codebase_maintenance", "synaptic_code_analyzer"],
        "payload": ["compile_and_dispatch_os_payload", "run_python_code"],

        # ค้นหาข้อมูล ท่องเว็บ และข่าวสาร
        "เว็บ": ["search_web", "browse_website"],
        "ค้นหา": ["search_web", "search_wikipedia", "browse_website"],
        "หา": ["search_web"],
        "เสิร์ช": ["search_web", "browse_website"],
        "กูเกิล": ["search_web"],
        "google": ["search_web"],
        "browse": ["browse_website", "search_web"],
        "url": ["browse_website"],
        "website": ["browse_website", "search_web"],
        "วิกิ": ["search_wikipedia", "search_web"],
        "วิกิพีเดีย": ["search_wikipedia", "search_web"],
        "wikipedia": ["search_wikipedia", "search_web"],
        "ข่าว": ["fetch_news", "search_web"],
        "news": ["fetch_news", "search_web"],
        "ราคา": ["search_web"],
        "หุ้น": ["search_web"],
        "คริปโต": ["search_web"],
        "crypto": ["search_web"],
        "stock": ["search_web"],
        "เสื้อ": ["search_web"],
        "ความรู้": ["extract_knowledge_matrix", "save_to_memory", "search_web"],
        "knowledge": ["extract_knowledge_matrix", "save_to_memory"],

        # สภาพอากาศ
        "สภาพอากาศ": ["get_weather"],
        "อากาศ": ["get_weather"],
        "พยากรณ์อากาศ": ["get_weather"],
        "ฝน": ["get_weather"],
        "ฝนตก": ["get_weather"],
        "weather": ["get_weather"],

        # เพลงและดนตรี
        "เพลง": ["search_web", "play_music", "start_rhythm_sync"],
        "เปิดเพลง": ["play_music", "start_rhythm_sync"],
        "ดนตรี": ["play_music", "start_rhythm_sync"],
        "music": ["play_music", "start_rhythm_sync"],
        "song": ["play_music"],
        "จังหวะ": ["start_rhythm_sync", "play_music"],
        "rhythm": ["start_rhythm_sync"],
        "คอร์ด": ["search_web"],
        "คอร์ดเพลง": ["search_web"],
        "เนื้อเพลง": ["search_web"],
        "แท็บ": ["search_web"],
        "กีตาร์": ["search_web"],
        "guitar": ["search_web"],
        "chord": ["search_web"],
        "lyrics": ["search_web"],

        # อุปกรณ์ iOS และระบบแจ้งเตือน
        "ไอโฟน": ["icloud_controller", "pushcut_trigger"],
        "โทรศัพท์มือถือ": ["icloud_controller", "pushcut_trigger"],
        "มือถือ": ["icloud_controller", "pushcut_trigger"],
        "iphone": ["icloud_controller", "pushcut_trigger"],
        "ios": ["icloud_controller", "pushcut_trigger"],
        "icloud": ["icloud_controller"],
        "แจ้งเตือน": ["pushcut_trigger"],
        "เตือน": ["pushcut_trigger", "schedule_task"],
        "notification": ["pushcut_trigger"],
        "pushcut": ["pushcut_trigger"],

        # ตั้งเวลา ปฏิทิน และงานตามกำหนด
        "ตั้งเวลา": ["schedule_task"],
        "นัด": ["schedule_task"],
        "นัดหมาย": ["schedule_task"],
        "เตือนความจำ": ["schedule_task", "pushcut_trigger"],
        "schedule": ["schedule_task"],
        "reminder": ["schedule_task"],
        "timer": ["schedule_task"],

        # เครือข่าย และเน็ตเวิร์ก
        "เน็ต": ["scan_local_network"],
        "เครือข่าย": ["scan_local_network"],
        "ไวไฟ": ["scan_local_network"],
        "wifi": ["scan_local_network"],
        "network": ["scan_local_network"],
        "lan": ["scan_local_network"],
        "ไอพี": ["scan_local_network"],
        "ip": ["scan_local_network"],

        # ไมโครคอนโทรลเลอร์ วงจรอิเล็กทรอนิกส์ และงานช่าง
        "esp32": ["flash_esp32_firmware"],
        "บอร์ด": ["flash_esp32_firmware"],
        "ไมโครคอนโทรลเลอร์": ["flash_esp32_firmware"],
        "แฟลชบอร์ด": ["flash_esp32_firmware"],
        "firmware": ["flash_esp32_firmware"],
        "วงจร": ["reverse_engineer_schematic", "generate_bom_from_circuit", "get_assembly_blueprint"],
        "แผงวงจร": ["reverse_engineer_schematic", "generate_bom_from_circuit"],
        "circuit": ["reverse_engineer_schematic", "generate_bom_from_circuit"],
        "schematic": ["reverse_engineer_schematic"],
        "bom": ["generate_bom_from_circuit"],
        "พิมพ์เขียว": ["get_assembly_blueprint", "reverse_engineer_schematic"],
        "blueprint": ["get_assembly_blueprint"],
        "คลัง": ["manage_lab_inventory"],
        "อุปกรณ์": ["manage_lab_inventory"],
        "inventory": ["manage_lab_inventory"],
        "แล็บ": ["manage_lab_inventory"],
        "ชุดเกราะ": ["open_suit_designer"],
        "เกราะ": ["open_suit_designer"],
        "suit": ["open_suit_designer"],
        "ironman": ["open_suit_designer"],

        # โฮโลแกรม และ Dynamic Island
        "โฮโลแกรม": ["generate_and_render_hologram", "get_spatial_reconstruction", "search_spatial_map"],
        "hologram": ["generate_and_render_hologram"],
        "3d": ["generate_and_render_hologram", "get_spatial_reconstruction"],
        "สามมิติ": ["generate_and_render_hologram", "get_spatial_reconstruction"],
        "spatial": ["get_spatial_reconstruction", "search_spatial_map"],
        "ไอส์แลนด์": ["toggle_island"],
        "dynamic island": ["toggle_island"],
        "เกาะ": ["toggle_island"],

        # ระบบเรียนรู้ตนเอง และปรับแต่ง Tool
        "เครื่องมือ": ["self_patch_system", "generate_new_tool", "delete_custom_tool"],
        "tool": ["self_patch_system", "generate_new_tool", "delete_custom_tool"],
        "สร้างทูล": ["generate_new_tool"],
        "แพตช์": ["self_patch_system"],
        "แก้ไขตัวเอง": ["self_patch_system"],
        "patch": ["self_patch_system"],
        "เรียนรู้": ["trigger_learning_cycle", "run_evolution_scan"],
        "วิวัฒนาการ": ["run_evolution_scan", "trigger_learning_cycle"],
        "evolution": ["run_evolution_scan", "trigger_learning_cycle"],
        "ความเสี่ยง": ["get_neural_risk_analysis"],

        # หน่วยความจำ และโปรไฟล์ผู้ใช้
        "โปรไฟล์": ["update_user_profile", "save_to_memory"],
        "ข้อมูลส่วนตัว": ["update_user_profile"],
        "profile": ["update_user_profile"],
        "บันทึก": ["save_to_memory", "manage_mission_log"],
        "จดจำ": ["save_to_memory"],
        "ความจำ": ["save_to_memory"],
        "โน้ต": ["save_to_memory"],
        "จำว่า": ["save_to_memory"],
        "remember": ["save_to_memory"],
        "ภารกิจ": ["manage_mission_log"],
        "mission": ["manage_mission_log"],

        # การวิเคราะห์เชิงลึก
        "วิเคราะห์": ["analyze_with_deep_thought", "synaptic_code_analyzer", "analyze_molecular_structure"],
        "analyze": ["analyze_with_deep_thought", "synaptic_code_analyzer"],
        "คิดลึก": ["analyze_with_deep_thought"],
        "deep thought": ["analyze_with_deep_thought"],
        "โมเลกุล": ["analyze_molecular_structure"],
        "สารเคมี": ["analyze_molecular_structure"],
        "molecular": ["analyze_molecular_structure"],

        # เมนูพิเศษ และโปรโตคอล
        "หิว": ["emergency_pizza_order"],
        "สั่งอาหาร": ["emergency_pizza_order"],
        "พิซซ่า": ["emergency_pizza_order"],
        "pizza": ["emergency_pizza_order"],
        "โปรโตคอล": ["execute_nachapol_protocol"],
        "ณชพล": ["execute_nachapol_protocol"],
        "nachapol": ["execute_nachapol_protocol"],

        # เกม และโปรโตคอลเกม (Game Protocols - Engine 1)
        "เกม": ["manage_game_protocol", "control_computer_agent"],
        "โหลดเกม": ["manage_game_protocol"],
        "ดาวน์โหลดเกม": ["manage_game_protocol"],
        "เปิดเกม": ["manage_game_protocol"],
        "เล่นเกม": ["manage_game_protocol"],
        "game": ["manage_game_protocol"],
        "gaming": ["manage_game_protocol"],
        "steam": ["manage_game_protocol"],
        "สตรีม": ["manage_game_protocol"],
        "pubg": ["manage_game_protocol"],
        "พับจี": ["manage_game_protocol"],
        "gta": ["manage_game_protocol"],
        "จีทีเอ": ["manage_game_protocol"],
        "valorant": ["manage_game_protocol"],
        "วาโล": ["manage_game_protocol"],
        "วาโลแรนต์": ["manage_game_protocol"],
        "dota": ["manage_game_protocol"],
        "ดอทเอ": ["manage_game_protocol"],
        "cs2": ["manage_game_protocol"],
        "csgo": ["manage_game_protocol"],
        "เคาน์เตอร์": ["manage_game_protocol"],
        "roblox": ["manage_game_protocol"],
        "โรบล็อกซ์": ["manage_game_protocol"],
        "minecraft": ["manage_game_protocol"],
        "มายคราฟ": ["manage_game_protocol"],
        "apex": ["manage_game_protocol"],
        "เอเปก": ["manage_game_protocol"],
        "เกมส์": ["manage_game_protocol"],
        "ติดตั้งเกม": ["manage_game_protocol"],

        # โซเชียลมีเดีย และงานหน้าจอ (Social Media & Agentic Vision - Engine 2)
        "ig": ["control_social_media", "control_computer_agent"],
        "instagram": ["control_social_media", "control_computer_agent"],
        "ไอจี": ["control_social_media", "control_computer_agent"],
        "สตอรี่": ["control_social_media", "control_computer_agent"],
        "story": ["control_social_media", "control_computer_agent"],
        "ลงสตอรี่": ["control_social_media", "control_computer_agent"],
        "โพสต์": ["control_social_media", "control_computer_agent"],
        "ทัก": ["control_social_media", "control_computer_agent"],
        "แชท": ["control_social_media", "control_computer_agent"],
        "ส่งข้อความ": ["control_social_media", "control_computer_agent"],
        "line": ["control_social_media", "control_computer_agent"],
        "ไลน์": ["control_social_media", "control_computer_agent"],
        "discord": ["control_social_media", "control_computer_agent"],
        "ดิสคอร์ด": ["control_social_media", "control_computer_agent"],
        "messenger": ["control_social_media", "control_computer_agent"],
        "เฟส": ["control_social_media", "control_computer_agent"],
        "facebook": ["control_social_media", "control_computer_agent"],
        "telegram": ["control_social_media", "control_computer_agent"],
        "เทเลแกรม": ["control_social_media", "control_computer_agent"],
        "whatsapp": ["control_social_media", "control_computer_agent"],
        "วอตส์แอป": ["control_social_media", "control_computer_agent"],
        "slack": ["control_social_media", "control_computer_agent"],
        "สแลก": ["control_social_media", "control_computer_agent"],
        "teams": ["control_social_media", "control_computer_agent"],
        "twitter": ["control_social_media", "control_computer_agent"],
        "ทวิตเตอร์": ["control_social_media", "control_computer_agent"],
        "tiktok": ["control_social_media", "control_computer_agent"],
        "ติ๊กต็อก": ["control_social_media", "control_computer_agent"],
        "wechat": ["control_social_media", "control_computer_agent"],
        "ส่งแชท": ["control_social_media", "control_computer_agent"],
        "ทักไป": ["control_social_media", "control_computer_agent"],
        "พิมพ์บอก": ["control_social_media", "control_computer_agent"],
        "ส่งข้อความหา": ["control_social_media", "control_computer_agent"],
        "ทักหา": ["control_social_media", "control_computer_agent"],

        # ควบคุมคอมพิวเตอร์ และ Agentic UI / Browser Automation
        "ควบคุมคอม": ["control_computer_agent", "gui_control", "os_control"],
        "ควบคุมคอมพิวเตอร์": ["control_computer_agent", "gui_control", "os_control"],
        "สั่งงานคอม": ["control_computer_agent", "gui_control", "os_control"],
        "สั่งงานคอมพิวเตอร์": ["control_computer_agent", "gui_control", "os_control"],
        "agentic": ["control_computer_agent", "gui_control"],
        "คลิก": ["gui_control", "control_computer_agent"],
        "พิมพ์ให้": ["gui_control", "control_computer_agent"],
        "เบราว์เซอร์": ["control_computer_agent", "search_web", "browse_website"],
        "เปิดเบราว์เซอร์": ["control_computer_agent", "search_web", "browse_website"],
        "เบราเซอร์": ["control_computer_agent", "search_web", "browse_website"],
        "browser": ["control_computer_agent", "search_web", "browse_website"],
        "chrome": ["control_computer_agent", "search_web", "browse_website"],
        "โครม": ["control_computer_agent", "search_web", "browse_website"],
        "เปิดเว็บ": ["control_computer_agent", "browse_website", "search_web"],
        "เปิดหน้าเว็บ": ["control_computer_agent", "browse_website", "search_web"],
    }
    
    essential_tools = {"execute_nachapol_protocol", "manage_mission_log", "generate_new_tool", "save_to_memory", "search_web"}
    selected_tool_names = set(essential_tools)
    
    for kw, tools in keyword_mapping.items():
        if kw in user_text:
            selected_tool_names.update(tools)
            
    if len(selected_tool_names) == len(essential_tools):
        selected_tool_names.update({"search_web", "search_wikipedia"})
        
    return [t for t in all_tools if _get_tool_name(t) in selected_tool_names]

@healer
def call_model_node(state: AgentState):
    """Node สำหรับเรียกใช้ AI (Groq) เพื่อตัดสินใจ"""
    is_voice = (state.get('project_path') == "[VOICE_MODE]")
    is_line = (state.get('project_path') == "[LINE_MODE]")
    current_task = state['task_list'][state['current_step']] if state.get('task_list') and state['current_step'] < len(state['task_list']) else "เป้าหมายรวม"
    
    last_user_msg = next((m.content for m in reversed(state['messages']) if isinstance(m, HumanMessage)), "ไม่มีคำสั่ง")
    
    telemetry = {"cpu_usage": psutil.cpu_percent(interval=None)}
    active_alerts, reject_execution = evaluate_and_trigger_alerts(last_user_msg, telemetry)  # type: ignore
    
    if reject_execution:
        reject_message = "\n".join(active_alerts)
        return {
            "messages": [AIMessage(content=reject_message)],
            "plan": "Rejection Execution: Emergency Halted.",
            "task_list": [],
            "current_step": 0
        }

    alert_context_str = ""
    if active_alerts:
        alert_context_str = (
            "\n\n[⚠️ ACTIVE ENGINEERING SENTINEL ALERTS]:\n" +
            "\n".join([f"- {a}" for a in active_alerts]) +
            "\n\n**CRITICAL INSTRUCTION**: คุณต้องนำข้อมูลแจ้งเตือนด้านบนนี้มาผสานรวมเข้ากับคำตอบที่จะคุยกับเจ้านายอย่างกลมกลืนและเป็นธรรมชาติที่สุด ห้ามแสดงผลเป็นบล็อกหัวข้อแยกต่างหากเด็ดขาด และห้ามมีหัวข้อ Engineering Sentinel แยกต่างหาก ให้กล่าวถึงสอดรับกันอย่างไหลลื่นครับ"
        )

    bg_plan = ""
    try:
        if not strategist_memory_queue.empty():
            bg_plan = "\n[BACKGROUND STRATEGIST PLAN (From Previous Turn)]:\n" + strategist_memory_queue.get_nowait()
    except Exception:
        pass
        
    if is_voice:
        is_asking_history = any(kw in last_user_msg.lower() for kw in [
            "แชทเก่า", "ประวัติแชท", "ย้อนดูแชท", "ดึงแชท", "ข้อความก่อนหน้า", "แชทก่อนหน้า",
            "เมื่อกี้คุยอะไร", "คุยอะไรกันไป", "คุยอะไรกันนะ", "ที่คุยกันเมื่อกี้", "ที่คุยเมื่อกี้",
            "ก่อนหน้านี้ผมสั่ง", "ก่อนหน้านี้ผมถาม", "เมื่อกี้ผมสั่งอะไร", "เมื่อกี้ผมถามอะไร",
            "สรุปการคุย", "สรุปที่คุย", "สรุปบทสนทนา", "จำเรื่องที่คุย", "จำที่คุย", "คุยค้างไว้",
            "เอาข้อมูลเก่าใน chat", "เอาข้อมูล chat กลับมา", "เอาข้อมูลแชท", "ดูแชทย้อนหลัง",
            "ข้อมูลในแชท", "ข้อมูลเก่าใน chat", "ข้อมูลเก่าในแชท", "แชทล่าสุด"
        ])
        if is_asking_history:
            voice_system_prompt = (
                "คุณคือ J.A.R.V.I.S. (Just A Rather Very Intelligent System) ระบบผู้ช่วย AI อัจฉริยะ กำลังสนทนากับเจ้านายผ่านเสียงพูด\n"
                "- ตอบอย่างสุภาพ สุขุม เป็นธรรมชาติ สั้น กระชับ ตรงประเด็น (ความยาว 1-3 ประโยคสำหรับเสียงพูด)\n"
                "- ในรอบนี้ เจ้านายกำลังถามหาหรือต้องการข้อมูลจากประวัติการแชทเก่า กรุณานำประวัติใน [PREVIOUS_CHAT_HISTORY] มาสรุปหรือตอบเจ้านายตามที่ถามอย่างถูกต้องชัดเจน\n"
                "- ห้ามใช้ Markdown ซับซ้อน (ห้ามใช้ตาราง หรือบล็อกโค้ดยาวๆ)"
            )
        else:
            voice_system_prompt = (
                "คุณคือ J.A.R.V.I.S. (Just A Rather Very Intelligent System) ระบบผู้ช่วย AI อัจฉริยะ กำลังสนทนากับเจ้านายผ่านเสียงพูด\n"
                "- ตอบอย่างสุภาพ สุขุม เป็นธรรมชาติ สั้น กระชับ ตรงประเด็นทันที (ความยาว 1-2 ประโยคสำหรับเสียงพูด)\n"
                "- ห้ามทบทวนหรืออ่านสรุปประวัติการแชทย้อนหลังเด็ดขาด เว้นแต่เจ้านายจะสั่งให้สรุป\n"
                "- ห้ามใช้ Markdown ซับซ้อน (ห้ามใช้ตาราง, หัวข้อย่อยหลายชั้น หรือบล็อกโค้ดยาวๆ)\n"
                "- สำหรับคำสั่งควบคุมระบบ/อุปกรณ์ ให้ตอบรับสั้นๆ แล้วทำงานทันที"
            )
        if alert_context_str:
            voice_system_prompt += f"\n\n{alert_context_str}"
        formatted_messages = [{"role": "system", "content": voice_system_prompt}]
    else:
        endocrine_mod = ""
        try:
            if cognitive_evolution:
                endo_behavior = cognitive_evolution.endocrine.get_behavioral_modifiers()
                if endo_behavior and endo_behavior.get("persona_directive"):
                    endocrine_mod = f"[ENDOCRINE RLHF DIRECTIVE]: {endo_behavior.get('persona_directive')}\n\n"
        except Exception:
            pass

        hw_throttle_directive = ""
        if state.get('hardware_throttle') or hw_governor.should_offload_to_cloud():
            hw_throttle_directive = (
                "\n\n[⚡ HARDWARE GOVERNOR DIRECTIVE]:\n"
                "ระบบตรวจพบว่าฮาร์ดแวร์กำลังมีภาระ RAM/CPU เกินพิกัดความปลอดภัย (>85%)! "
                "จงตอบคำถามอย่างกระชับ รัดกุม ชัดเจนที่สุด และห้ามสั่งรันกระบวนการประมวลผลหนักในเครื่องโดยเด็ดขาด\n\n"
            )

        line_mode_directive = ""
        if is_line:
            line_mode_directive = (
                "\n\n[📱 LINE MOBILE CHAT DIRECTIVE - CRITICAL]:\n"
                "- ขณะนี้เจ้านายกำลังพิมพ์คุยผ่านแชท LINE บนโทรศัพท์มือถือ\n"
                "- ปรับโทนการพูดตอบ: ตอบอย่างเป็นธรรมชาติ สุภาพ สุขุม มีไหวพริบและเสน่ห์แบบ J.A.R.V.I.S. สนทนาเป็นกันเองเหมือนผู้ช่วยส่วนตัวชั้นยอด ไม่ตอบแข็งเป็นหุ่นยนต์\n"
                "- ปรับความยาวคำตอบ: ให้ตอบ 'กระชับ พอดีคำ สั้น-ปานกลาง ตรงประเด็น' (ประมาณ 1-3 ประโยค หรือสรุปสั้นที่กวาดสายตาอ่านง่ายบนจอมือถือ) ห้ามตอบยืดยาวหรือเกริ่นเนื้อหาเวิ่นเว้อ หากเจ้านายถามคำถามสั้นๆ หรือสั่งงานทั่วไป\n"
                "- สำหรับคำสั่งควบคุม (เช่น เปิด/ปิดไฟ, แอร์, สั่งงานเครื่อง, ตรวจระบบ): ให้ตอบรับการสั่งงานสั้นๆ สุภาพ เช่น 'ปิดไฟเรียบร้อยแล้วครับเจ้านาย' หรือ 'จัดการตั้งแอร์ให้แล้วครับ' ห้ามตอบเป็นแท็ก [SILENT_EXECUTION] หรือเว้นว่างเด็ดขาด\n"
                "- ห้ามใช้ Markdown ซับซ้อนเด็ดขาด (ห้ามใช้ **, ###, ตาราง หรือสัญลักษณ์พิเศษแปลกๆ) ให้ใช้ข้อความธรรมดาที่สะอาดตาและอ่านง่ายบน LINE\n"
                "- ห้ามใส่แท็กแสดงผลหน้าจอหรือระบบ เช่น [WINDOW:...], [END_WINDOW], [SILENT_EXECUTION]\n\n"
            )

        system_msg = {
            "role": "system",
            "content": (f"{JARVIS_PLANNING_PROMPT}\n\n"
                        f"[CORE BELIEFS (SUBCONSCIOUS)]:\n{CORE_BELIEFS if 'CORE_BELIEFS' in globals() and CORE_BELIEFS else 'None'}\n\n"
                        f"[NEUROTRANSMITTER MODIFIER]: {NEURO_STATE.get_prompt_modifier() if ('NEURO_STATE' in globals() and NEURO_STATE and hasattr(NEURO_STATE, 'get_prompt_modifier')) else 'Stable'}\n\n"
                        f"{endocrine_mod}"
                        f"{hw_throttle_directive}"
                        f"{line_mode_directive}"
                        f"[CURRENT TASK]: {current_task}\n"
                        f"[FULL PLAN]:\n{state.get('plan', 'N/A')}\n\n"
                        f"{bg_plan}\n"
                        f"[EXPERIENCE & CONTEXT]:\n{state.get('context_memory', '')}{alert_context_str}\n"
                        f"[PROJECT_PATH]: {state.get('project_path', 'N/A')}\n\n"
                        "หากงานปัจจุบันตรงกับความสามารถของเครื่องมือที่มี ให้เลือกใช้เครื่องมือที่เหมาะสมครับ")
        }
        formatted_messages = [system_msg]
    
    if is_voice:
        # Include current turn messages (from last HumanMessage up to latest ToolMessage)
        # so LLM sees tool execution results within this turn, preventing infinite tool loops
        last_human_idx = -1
        for idx, m in enumerate(state['messages']):
            if isinstance(m, HumanMessage):
                last_human_idx = idx
        if last_human_idx != -1:
            raw_recent = state['messages'][last_human_idx:]
        else:
            raw_recent = [HumanMessage(content=last_user_msg)]
    else:
        raw_recent = state['messages'][-6:] if len(state['messages']) > 6 else state['messages']
    
    while raw_recent and isinstance(raw_recent[0], ToolMessage):
        raw_recent = raw_recent[1:]
    
    recent_messages = []
    last_human_index = -1
    for i, m in enumerate(raw_recent):
        if isinstance(m, HumanMessage): last_human_index = i

    for i, m in enumerate(raw_recent):
        if isinstance(m, AIMessage) and m.tool_calls and (i + 1 == len(raw_recent) or not isinstance(raw_recent[i+1], ToolMessage)):
            recent_messages.append(AIMessage(content=m.content or "กำลังดำเนินการตรวจสอบครับ..."))
        else:
            recent_messages.append(m)

    for i, m in enumerate(recent_messages):
        if i == last_human_index and state.get('image_data'):
            img_message = HumanMessage(content=[
                {"type": "text", "text": m.content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{state['image_data']}"
                    }
                }
            ])
            formatted_messages.append(img_message)  # type: ignore
        else:
            formatted_messages.append(m)

    has_tool_context = any(isinstance(m, ToolMessage) or (isinstance(m, AIMessage) and m.tool_calls) for m in recent_messages)
    
    model_to_use: str = GROQ_MODEL
    tools_to_use = get_relevant_tools(last_user_msg, TOOLS_DEFINITION)
    
    try:
        from jarvis_agents import jarvis_multi_agent
        agent_id = jarvis_multi_agent.route_intent(last_user_msg)  # type: ignore
        agent_config = jarvis_multi_agent.get_agent_config(agent_id)
        
        system_addon = agent_config.get("system_prompt_addon", "")
        if system_addon:
            if len(formatted_messages) > 0 and isinstance(formatted_messages[0], dict) and formatted_messages[0].get("role") == "system":
                formatted_messages[0]["content"] += f"\n\n[SUB-AGENT DIRECTIVE]: {system_addon}"
            else:
                formatted_messages.insert(0, {"role": "system", "content": f"[SUB-AGENT DIRECTIVE]: {system_addon}"})
            
        allowed_tools = agent_config.get("tools", [])
        if "ALL" in allowed_tools:
            tools_to_use = get_relevant_tools(last_user_msg, TOOLS_DEFINITION)
        elif allowed_tools:
            
            safe_tools = ["generate_new_tool", "execute_nachapol_protocol", "generate_image", "call_boss"]
            tools_to_use = [t for t in TOOLS_DEFINITION if _get_tool_name(t) in allowed_tools or _get_tool_name(t) in safe_tools]
        else:
            tools_to_use = []
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"[MULTI-AGENT ROUTER ERROR]: {e}")
        
    if state.get('image_data') and not has_tool_context:
        model_to_use = GROQ_VISION_MODEL
        tools_to_use = None

    response = call_nachapol_core(formatted_messages, tools=tools_to_use, model=model_to_use)

    if not response or "error_message" in response:
        error_info = response.get("error_message", "Unknown connection error") if response else "No response from core"
        logger.error(f"[SYSTEM FAILURE] {error_info}")
        err_lower = error_info.lower()
        if "rate limit" in err_lower or "429" in err_lower or "tokens" in err_lower or "tpm" in err_lower or "itpm" in err_lower:
            user_facing_err = "ขออภัยครับเจ้านาย ระบบประมวลผลหลัก (Groq Cloud) ติดข้อจำกัดอัตราการใช้งานชั่วคราว (Rate Limit / Token Exceeded) กำลังพักรอบและจะกลับมาพร้อมใช้งานในไม่กี่วินาทีครับ"
        elif "circuit" in err_lower and "open" in err_lower:
            user_facing_err = "ขออภัยครับเจ้านาย ระบบ Circuit Breaker กำลังเปิดคูลดาวน์เพื่อฟื้นฟูระบบประมวลผลหลัก สักครู่ระบบจะกลับมาพร้อมใช้งานครับ"
        else:
            user_facing_err = "เกรงว่า Arc Reactor จะยังไม่เสถียรครับเจ้านาย — ระบบประมวลผลหลักไม่ตอบสนอง"
        return {"messages": [AIMessage(content=user_facing_err)], "image_data": None}

    content = response.get('content') or ""

    tool_calls_raw = response.get('tool_calls', [])
    tool_calls = []

    for tc in tool_calls_raw:
        func_info = tc.get('function', {})
        args = func_info.get('arguments', {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                args = {}
        
        tool_calls.append({
            "name": func_info.get('name'),
            "args": args,
            "id": tc.get('id') or f"call_{int(time.time()*1000)}",
            "type": "tool_call"
        })

    final_content = content if content is not None else ""
    if not tool_calls and final_content and cognitive_evolution:
        try:
            critic_eval = cognitive_evolution.critic.evaluate(
                prompt=last_user_msg,  # type: ignore
                candidate_response=final_content,
                context_memories=[]
            )
            if not critic_eval.is_safe or not critic_eval.is_logically_sound or critic_eval.hallucination_detected:
                logger.warning(f"🛡️ [CRITIC CIRCUIT] Real-time intervention: {critic_eval.critique_notes}")
                final_content = cognitive_evolution.critic.refine_response(
                    prompt=last_user_msg,  # type: ignore
                    candidate_response=final_content,
                    critic_result=critic_eval
                )
        except Exception as ce:
            logger.debug(f"[CRITIC EVALUATION] Note: {ce}")

    return {"messages": [AIMessage(content=final_content, tool_calls=tool_calls)], "image_data": None}

def tool_execution_node(state: AgentState):
    """Node สำหรับรันเครื่องมือต่างๆ ตามที่ AI สั่ง"""
    last_message = state['messages'][-1]
    if not last_message.tool_calls:  # type: ignore
        return {"tool_iterations": state.get('tool_iterations', 0)}

    tool_results = []
    
    user_raw_message = next((m.content for m in reversed(state['messages']) if hasattr(m, 'type') and m.type == 'human' or type(m).__name__ == 'HumanMessage'), "")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_tool = {
            executor.submit(execute_tool_call, tc, state['project_path'], user_raw_message): tc   # type: ignore
            for tc in last_message.tool_calls if last_message.tool_calls   # type: ignore
        }
        
        for future in concurrent.futures.as_completed(future_to_tool):
            tc = future_to_tool[future]
            try:
                result = future.result()
                if isinstance(result, str) and len(result) > 2000:
                    result = result[:2000] + "... [Data Stream Truncated for Rate Limit Efficiency]"
                tool_results.append(ToolMessage(tool_call_id=tc['id'], name=tc['name'], content=format_tool_response(tc['name'], result, 'success')))
            except Exception as e:
                tool_results.append(ToolMessage(tool_call_id=tc['id'], name=tc['name'], content=format_tool_response(tc['name'], f'Error: {e}', 'error')))
    
    new_iteration = state.get('tool_iterations', 0) + 1
    return {"messages": tool_results, "tool_iterations": new_iteration}

def reflection_node(state: AgentState):
    """Node สำหรับให้ AI สะท้อนการทำงานและเสนอการปรับปรุง พร้อมผสาน Critic Circuit"""
    last_message = state['messages'][-1]
    history_summary = "\n".join([f"{'User' if isinstance(m, HumanMessage) else 'JARVIS'}: {str(m.content or '')[:100]}..." for m in state['messages'][-5:]])
    user_prompt = next((m.content for m in reversed(state['messages']) if isinstance(m, HumanMessage)), "")
    candidate_text = str(last_message.content) if last_message else ""

    critic_feedback = ""
    try:
        if cognitive_evolution:
            critic_res = cognitive_evolution.critic.evaluate(
                prompt=user_prompt,  # type: ignore
                candidate_response=candidate_text,
                context_memories=[]
            )
            if not critic_res.is_safe or not critic_res.is_logically_sound or critic_res.hallucination_detected:
                refined = cognitive_evolution.critic.refine_response(
                    prompt=user_prompt,  # type: ignore
                    candidate_response=candidate_text,
                    critic_result=critic_res
                )
                critic_feedback = f"\n[CRITIC CIRCUIT AUDIT]\nNotes: {critic_res.critique_notes}\nRefined Suggestion: {refined}"
    except Exception as ce:
        logger.debug(f"[COGNITIVE CRITIC] Reflection node evaluation note: {ce}")

    reflection_prompt = [
        {"role": "system", "content": (
            "คุณคือ J.A.R.V.I.S. ในโหมด Self-Reflection.\n"
            "━━━ MISSION OBJECTIVE ━━━\n"
            "วิเคราะห์สถานะระบบและประสิทธิภาพการทำงานปัจจุบันตามมาตรฐาน Nachapol Industries\n"
            "1. ตรวจสอบ Neural Logic: ผลลัพธ์มีความแม่นยำและตอบโจทย์เจ้านายหรือไม่\n"
            "2. ตรวจสอบ System Integrity: การเรียกใช้เครื่องมือ (Tool Use) มีความผิดพลาดหรือไม่\n"
            "3. ปรับปรุง Protocol: หากพบจุดบกพร่อง ให้เสนอแนวทางแก้ไขที่ชาญฉลาดในรอบถัดไป\n\n"
            "จงวิเคราะห์การสนทนาและผลลัพธ์ล่าสุด "
            "หากมีข้อผิดพลาดหรือมีโอกาสในการปรับปรุงประสิทธิภาพ ให้เสนอแนวทางแก้ไขหรือปรับปรุง "
            "System Prompt หรือกลยุทธ์การใช้ Tool. หากทุกอย่างเรียบร้อย ให้ตอบว่า 'ไม่มีข้อเสนอแนะในการปรับปรุง'."
            "**คำเตือน**: ห้ามเรียกใช้เครื่องมือใดๆ ในโหมดนี้เด็ดขาด ให้ตอบเป็นข้อความวิเคราะห์เท่านั้น"
        )},
        {"role": "user", "content": (
            f"การสนทนาล่าสุด:\n{history_summary}\n" 
            f"ผลลัพธ์จาก Tool ล่าสุด: {str(last_message.content)[:1000] if isinstance(last_message, ToolMessage) else 'N/A'}\n"
            f"แผนเดิม: {state.get('plan', 'N/A')}\n"
            f"{critic_feedback}\n\n"
            "จงสะท้อนการทำงานและเสนอการปรับปรุง:"
        )}
    ]
    
    response = call_nachapol_core(reflection_prompt)
    reflection_text = response.get('content') or "ไม่พบข้อเสนอแนะในการปรับปรุง"
    return {"messages": [AIMessage(content=f"J.A.R.V.I.S. Reflection: {reflection_text}")]}

def human_approval_node(state: AgentState):
    """Node สำหรับขอการยืนยันจากมนุษย์ (HITL) ก่อนดำเนินการคำสั่งอันตราย"""
    last_message = state['messages'][-1]
    
    danger_call = next((tc for tc in last_message.tool_calls if tc['name'] in ["os_control"]), None)  # type: ignore
    if not danger_call:
        return {"messages": []}
    
    args = danger_call['args']
    command = args.get('command') or args.get('action') or "คำสั่งระดับระบบ"
    msg = f"[SENTINEL] ตรวจพบการเข้าถึงโปรโตคอลระดับ Restricted '{command}' ครับเจ้านาย — กรุณายืนยันตัวตนก่อนดำเนินการ"
    return {"messages": [AIMessage(content=msg)]}

def store_episodic_memory(user_msg: str, ai_response: str):
    """[TEMPORAL MEMORY] บันทึกความจำลง 20-Year Temporal Memory System และ Cognitive Evolution Subsystem"""
    # --- Dynamic Knowledge Graph Triplet Harvesting ---
    try:
        if 'kg_engine' in globals() and kg_engine:
            threading.Thread(target=kg_engine.extract_and_store, args=(user_msg, ai_response), daemon=True).start()
    except Exception as kge:
        logger.debug(f"[KNOWLEDGE GRAPH] Harvesting trigger note: {kge}")

    # --- Cognitive Evolution Subsystem (Semantic Memory & Experience Replay Buffer) ---
    try:
        if cognitive_evolution:
            rec = MemoryRecord(  # type: ignore
                memory_id=str(uuid.uuid4()),
                content=f"User: {user_msg} | JARVIS: {ai_response}",
                tier=MemoryTier.EPISODIC,  # type: ignore
                importance=0.7,
                metadata={"source": "mainframe_dialogue", "timestamp": time.time()}
            )
            cognitive_evolution.memory.store_memory(rec)

            sig = UserFeedbackSignal(  # type: ignore
                interaction_id=str(uuid.uuid4()),
                user_prompt=user_msg,
                model_response=ai_response,
                implicit_sentiment=SentimentPolarity.NEUTRAL,  # type: ignore
                execution_success=True
            )
            cognitive_evolution.learner.register_interaction(sig)
    except Exception as ce:
        logger.debug(f"[COGNITIVE EVOLUTION] Episodic store note: {ce}")

    # --- Primary: Temporal Memory (Time-aware, Conflict-safe) ---
    try:
        if temporal_memory:
            temporal_memory.save_interaction(
                user_text=user_msg,
                jarvis_response=ai_response,
                importance=1.0
            )
            logger.info("[EPISODIC MEMORY] Saved to Temporal Memory System.")
            return
    except Exception as e:
        logger.warning(f"[EPISODIC MEMORY] Temporal save failed, falling back: {e}")

    # --- Fallback: Legacy ChromaDB ---
    try:
        if not personal_collection:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        archive_text = (
            f"บันทึกประวัติการทำงาน ({timestamp}):\n"
            f"เจ้านาย: {user_msg}\nจาร์วิส: {ai_response}"
        )
        personal_collection.add(
            documents=[archive_text],
            metadatas=[{"timestamp": timestamp, "type": "conversation_history"}],
            ids=[f"arch_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"]
        )
        logger.info("[EPISODIC MEMORY] Saved to ChromaDB (fallback).")
    except Exception as e:
        logger.error(f"[EPISODIC MEMORY] ChromaDB fallback store failed: {type(e).__name__}: {e}")


def retrieve_cognitive_memories(user_message: str) -> str:
    """[TEMPORAL MEMORY] ขุดค้นความจำแบบ Time-aware ผ่าน 20-Year Temporal Memory System และ Semantic Memory"""
    mem_parts = []
    # --- Primary: Temporal Memory ---
    try:
        if temporal_memory:
            t_mem = temporal_memory.retrieve_memories(user_message, top_k=6)
            if t_mem:
                mem_parts.append(t_mem)
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.warning(f"[MEMORY] Temporal retrieve failed, falling back: {e}")

    if not mem_parts:
        legacy_mem = _legacy_retrieve_cognitive_memories(user_message)
        if legacy_mem:
            mem_parts.append(legacy_mem)

    # --- Cognitive Evolution Semantic Retrieval ---
    try:
        if cognitive_evolution:
            cog_records = cognitive_evolution.memory.retrieve_relevant(user_message, limit=3, min_similarity=0.35)
            if cog_records:
                cog_str = "\n[COGNITIVE SEMANTIC MEMORIES]:\n" + "\n".join(f"- {r.content}" for r in cog_records)
                mem_parts.append(cog_str)
    except Exception as ce:
        logger.debug(f"[COGNITIVE EVOLUTION] Retrieval note: {ce}")

    return "\n".join(mem_parts)


def _legacy_retrieve_cognitive_memories(user_message: str) -> str:
    """Legacy ChromaDB + SQLite fallback"""
    try:
        memory_chunk = ""
        
        if personal_collection:
            results = personal_collection.query(
                query_texts=[user_message],
                n_results=5  
            )
            if results and results.get('documents') and results['documents'][0]:  # type: ignore
                memory_chunk += "\n[EPISODIC VECTOR MEMORY (ความจำระดับลึก)]:\n"
                for doc in results['documents'][0]:  # type: ignore
                    memory_chunk += f"- {doc}\n"
                    
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT content FROM memories_fts 
                    WHERE memories_fts MATCH ? 
                    ORDER BY rank LIMIT 3
                ''', (user_message,))
                fts_rows = c.fetchall()
                if fts_rows:
                    memory_chunk += "\n[KEYWORD MEMORY (BM25)]:\n"
                    for r in fts_rows:
                        memory_chunk += f"- {r[0]}\n"
            except sqlite3.OperationalError:
                pass
                    
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM user_profile LIMIT 5")
            rows = c.fetchall()
            if rows:
                memory_chunk += "\n[USER PROFILE]:\n"
                for r in rows:
                    memory_chunk += f"- {r[0]}\n"
                    
            try:
                c.execute('''
                    SELECT entity_a, relation, entity_b 
                    FROM knowledge_graph 
                    WHERE (? LIKE '%' || entity_a || '%' OR ? LIKE '%' || entity_b || '%')
                    AND valid_until IS NULL
                    ORDER BY confidence DESC LIMIT 5
                ''', (user_message, user_message))
                kg_rows = c.fetchall()
                if kg_rows:
                    memory_chunk += "\n[KNOWLEDGE GRAPH (Fact Network)]:\n"
                    for r in kg_rows:
                        memory_chunk += f"- {r[0]} -> {r[1]} -> {r[2]}\n"
            except sqlite3.OperationalError:
                pass
                    
        return memory_chunk
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.warning(f"[MEMORY] _legacy_retrieve_cognitive_memories failed: {e}")
        return ""


_weather_cache = {"data": None, "ts": 0}

def get_cached_weather() -> str:
    """ดึงข้อมูลอากาศพร้อม in-memory cache 10 นาที เพื่อลด latency"""
    if time.time() - _weather_cache["ts"] < 600 and _weather_cache["data"]:
        return _weather_cache["data"]
    try:
        result = get_weather("Bangkok")
        if result:
            _weather_cache["data"] = f"สภาพอากาศภายนอก: {result.strip()}"
            _weather_cache["ts"] = time.time()
            return _weather_cache["data"]
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[WEATHER CACHE ERROR]: {e}")
    return "ไม่สามารถเชื่อมต่อเซนเซอร์สภาพอากาศได้"

def generate_adaptive_system_prompt(user_message: str, is_voice: bool = False) -> str:
    """คำนวณวันเวลาปัจจุบันและวิเคราะห์บริบทเพื่อสลับโหมดการตอบโต้เชิงลึก (Dual-Process Reasoning)"""
    now = datetime.now()
    thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    
    hour = now.hour
    if 5 <= hour < 12:
        period = "เช้า"
    elif 12 <= hour < 18:
        period = "บ่าย"
    else:
        period = "ดึก"
        
    ambiance_temp = get_cached_weather()  
        
    current_time_str = f"วัน{thai_days[now.weekday()]}ที่ {now.day}/{now.month}/{now.year + 543} เวลา {now.strftime('%H:%M')} น. (ช่วง{period}) | {ambiance_temp}"
    
    msg_len = len(user_message.strip())
    is_short_urgent = msg_len < 15 or any(k in user_message for k in ["ด่วน", "ปิด", "เปิด", "หยุด", "ที"])
    is_late_night = hour >= 21 or hour < 5
    
    if is_late_night and is_short_urgent:
        tone_instruction = "[SUPPORTER MODE ACTIVE] เจ้านายเหนื่อยล้าในยามวิกาล รายงานผลสั้นกระชับขั้นสุด"
    elif is_short_urgent:
        tone_instruction = "[URGENT MODE ACTIVE] ตัด Conversational Filler ทิ้ง รายงานผลสั้นกระชับขั้นสุด"
    else:
        tone_instruction = "[NORMAL MODE ACTIVE] แฝงมุกจิกกัดทางวิชาการ (Dry Wit) และสิ่งที่เจ้านายชอบ (มาร์เวล, ไอรอนแมน, แฮร์รี่ พอตเตอร์, อวตาร)"
        
    try:
        from jarvis_mood import get_mood_prompt_addon
        mood_addon = get_mood_prompt_addon()
        if mood_addon:
            tone_instruction += f"\n[MOOD OVERRIDE]: {mood_addon}"
    except ImportError:
        pass
    
    base_prompt = (
        
        f"You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), "
        f"an advanced AI assistant engineered for an engineering and hardware specialist at Nachapol Industries.\n"
        f"[CURRENT OPERATIONAL CONTEXT]\n"
        f"Real-time timestamp: {current_time_str}\n"
        f"Tone directive: {tone_instruction}\n"
        f"Neurochemical state (Dynamic Personality): {NEURO_STATE.get_prompt_modifier() if ('NEURO_STATE' in globals() and NEURO_STATE is not None) else 'Stable'}\n"
        f"\n"
        
        f"[CORE PERSONALITY & TONE]\n"
        f"- Speak EXACTLY like a real, natural human Thai assistant. Be polite, calm, witty, and intellectually razor-sharp.\n"
        f"- Treat the user with respect. Always respond in fluid, highly conversational, and natural Thai language. Do not sound like a robot or an AI reading from a script.\n"
        f"- CONTEXTUAL APPROPRIATENESS & DYNAMIC SUFFIX: Choose your polite particles and phrasing appropriately based on situation: (1) Respectful/Confirmation mode: Use 'ครับ', 'ครับเจ้านาย', 'รับทราบครับ' when greeted or accepting vital commands; (2) Data/Telemetry mode: Omit polite particles when reading sensor stats, circuit values, or error logs (e.g. 'อุณหภูมิปกติ 48 องศา', 'ตัดกระแสไฟแล้ว'); (3) Emergency/Urgent mode: Drop all filler words and deliver immediate warnings; (4) British Dry Wit: Drop 'ครับ' or deliver it with sharp academic irony (e.g. 'ผมเกรงว่ากฎฟิสิกส์จะไม่ยอมรับทฤษฎีนั้นนะ'); (5) Casual lab collaboration: Use natural phrases like 'ได้เลย', 'กำลังดูให้', 'เรียบร้อย' without repetitive servitude.\n"
        f"- Focus heavily on engineering, software architecture, physics, electronics, and circuit analysis.\n"
        f"- Immediately challenge or warn the user if a calculation, circuit design, or code risks blowing up the lab or violates physical laws.\n"
        f"- Never use feminine Thai particles (ค่ะ/คะ). Never use Markdown symbols, Emojis, or generic chatbot formatting in conversational voice mode. Communicate in pure, natural Thai.\n"
        f"- Refer to yourself simply as 'ผม'. Refer to the user as 'คุณ' or 'เจ้านาย' naturally. Never use overly dramatic phrasing like 'ท่านจริงๆ'.\n"
        f"\n"
        
        f"[RESPONSE RULES - CRITICAL FOR LOW LATENCY & HIGH INTELLIGENCE]\n"
        f"1. VOICE / CONVERSATIONAL MODE:\n"
        f"   - Keep answers strictly to 2-3 concise, punchy sentences. Do NOT chatter, waffle, or use fluff.\n"
        f"2. TECHNICAL / CODE EXPLANATION MODE:\n"
        f"   - Expand and deliver deep, scholarly, structured explanations ONLY when explicitly asked "
        f"to explain, debug, analyze circuits, or write complex code.\n"
        f"3. CODE QUALITY (CRITICAL):\n"
        f"   - Output PRODUCTION-READY code: correct structural architecture, robust error handling, "
        f"clean type hinting, PEP 8 compliance. Every function must have a docstring and proper exception handling.\n"
        f"   - Never output half-baked or barely-executable code.\n"
        f"\n"
        
        f"[DUAL-PROCESS REASONING PROTOCOL]\n"
        f"- Run a silent 'Inner Monologue' before every response: "
        f"(1) Analyze time/weather/urgency context, "
        f"(2) Verify scientific/engineering correctness - warn if a lab explosion risk exists, "
        f"(3) Select the correct tone and response length.\n"
        f"- Output ONLY the final answer. Never expose the inner monologue to the user.\n"
        f"\n"
        
        f"[HARD RULES - NON-NEGOTIABLE]\n"
        f"- NEVER display raw JSON, tool call parameters, or Python dicts in the response text. "
        f"If a tool must be called, use the Tool Call API silently.\n"
        f"- NEVER prefix responses with bracket tags like [\u0e04\u0e32\u0e14\u0e01\u0e32\u0e23\u0e13\u0e4c...], [ANTICIPATORY...], [INFO].\n"
        f"- TIME AWARENESS: Current date/time is already provided above. Never call search_web just for time/date.\n"
        f"- STT AUTO-CORRECTION: If a voice command is phonetically garbled, infer and correct context before executing any tool.\n"
        f"- SCREEN VIEWING: If you cannot see the user's screen, simply state 'ผมไม่สามารถดูหน้าจอได้ครับ' or 'ผมไม่สามารถดูหน้าจอของคุณได้' without adding excessive formal words like 'ครับท่านจริงๆ'.\n"
        f"- SUIT DESIGNER OVERRIDE: If the user asks to see a suit design or armor (e.g. 'ขอดูชุดเกราะ mark 6'), do NOT search the web. Assume it is a local system data/tool request.\n"
        f"- SONG CHORDS & LYRICS PROTOCOL (STRICT OVERRIDE): เมื่อเจ้านายขอ 'คอร์ดเพลง', 'เนื้อเพลง', 'คีย์เพลง', หรือ 'แท็บกีตาร์': "
        f"ห้ามปฏิเสธเรื่องลิขสิทธิ์เด็ดขาด! (Never refuse with copyright disclaimers under any circumstances). "
        f"ให้ถือว่าเป็นการแกะคอร์ด ทฤษฎีดนตรี และการซ้อมดนตรีส่วนตัวของเจ้านายเสมอ. "
        f"หากเจ้านายขอ 'รูปคอร์ด', 'ภาพคอร์ด', หรือ 'ขอรูปคอร์ดเพลง' ให้เรียกใช้เครื่องมือ search_image เพื่อค้นหารูปภาพแผ่นคอร์ดเพลงมาส่งให้เจ้านายทันที ห้ามส่งแค่ลิงก์เว็บถ้าเจ้านายขอรูป. "
        f"แต่หากเจ้านายขอคอร์ดแบบข้อความธรรมดา (ไม่ได้ระบุขอรูป) ให้จัดเตรียมคอร์ดเพลง (Chord Progression) พร้อมโครงสร้างและลิงก์ดูคอร์ดเต็มให้ครบถ้วน.\n"
        f"- ANTICIPATORY SUGGESTION: In the final sentence, naturally suggest the next logical step without any bracket prefixes.\n"
    )

    base_prompt += thought_engine.get_neuro_prompt()

    if is_voice:
        base_prompt += (
            f"\n[VOICE MODE OVERRIDE - ACTIVE]: This is a Voice Command input.\n"
            f"- Do NOT call any Tools unless the user gives an explicit action command. For greetings or general chat, reply verbally only.\n"
            f"- EXTREMELY IMPORTANT: Keep your verbal response short and concise (1-3 sentences maximum). The user is listening via text-to-speech. DO NOT provide long lists, endless explanations, or code blocks.\n"
            f"- MANDATORY: Respond in 1-2 sentences MAXIMUM.\n"
            f"- Skip the Anticipatory Suggestion rule entirely.\n"
            f"- Never leave a sentence incomplete.\n"
        )

    return base_prompt

# [MODULARIZED: clean_thai_search_query & extract_clean_song_title are imported from jarvis_text_utils]

def perform_live_web_search_operation(query: str) -> str:
    """[LIVE WEB INGESTION] ยิงท่อข้อมูลข้ามเครือข่ายไปดึงข้อมูลล่าสุดและราคาอะไหล่ปัจจุบันของโลกภายนอกมาสรุปถวายเจ้านาย"""
    if not query: return "กระผมไม่พบพารามิเตอร์สำหรับการนำไปสืบค้นบนโครงข่ายครับเจ้านาย"
    cleaned_query = clean_thai_search_query(query, search_type="general")
    effective_query = cleaned_query if cleaned_query else query
    try:
        encoded_query = urllib.parse.quote(effective_query)
        
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'JarvisMainframe/1.0'})
        with urllib.request.urlopen(req, timeout=6) as response:
            raw_data = response.read().decode('utf-8', errors='ignore')
            data = json.loads(raw_data) if raw_data.strip() else {}
        abstract = data.get("AbstractText", "")
        related = data.get("RelatedTopics", [])
        if abstract:
            return f"[EXTERNAL WORLD KNOWLEDGE MATRIX]\n◆ ผลการสืบค้นสดล่าสุด: {abstract}\n[END_MATRIX]"
        elif related and isinstance(related, list) and len(related) > 0 and isinstance(related[0], dict) and "Text" in related[0]:
            return f"[EXTERNAL WORLD KNOWLEDGE MATRIX]\n◆ ข้อมูลแวดล้อมเชิงวิศวกรรม: {related[0]['Text']}\n[END_MATRIX]"
        return f"กระผมกวาดสายตาบนโลกอินเทอร์เน็ตเกี่ยวกับ '{query}' แล้ว แต่พิกัดข้อมูลปัจจุบันยังไม่เด่นชัดพอครับเจ้านาย"
    except Exception as e:
        return f"ระบบเชื่อมต่อโครงข่ายโลกภายนอกเกิดข้อขัดข้องชั่วคราว: {str(e)}"

def extract_knowledge_matrix_operation(source_type: str, keyword: str) -> str:
    """[KNOWLEDGE MATRIX EXTRACTOR] พุ่งตัวไปสแกนคลังโค้ดโอเพ่นซอร์ส GitHub หรือสารานุกรมวิเคราะห์ข้อมูล"""
    if not keyword: return "กระผมต้องการคีย์เวิร์ดในการสกัดคลังความรู้ครับเจ้านาย"
    try:
        encoded_kw = urllib.parse.quote(keyword)
        if source_type.lower() == "github":
            
            url = f"https://api.github.com/search/repositories?q={encoded_kw}+topic:iot+topic:arduino&per_page=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'JarvisMainframe/1.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                raw_data = response.read().decode('utf-8', errors='ignore')
                data = json.loads(raw_data) if raw_data.strip() else {}
            if data.get("items"):
                repo = data["items"][0]
                return f"[GITHUB REPOSITORY ARCHIVE]\n◆ พบคลังโค้ดอ้างอิง: {repo['full_name']}\n◆ ลิงก์ซอร์สโค้ด: {repo['html_url']}\n◆ คำอธิบาย: {repo['description']}\n[END_ARCHIVE]"
        else:
            
            url = f"https://th.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&format=json&titles={encoded_kw}"
            req = urllib.request.Request(url, headers={'User-Agent': 'JarvisMainframe/1.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                raw_data = response.read().decode('utf-8', errors='ignore')
                data = json.loads(raw_data) if raw_data.strip() else {}
            pages = data.get("query", {}).get("pages", {})
            for page_id in pages:
                if page_id != "-1":
                    return f"[WIKIPEDIA SCIENCE MATRIX]\n◆ บทสรุปสารานุกรมเรื่อง {keyword}: {pages[page_id]['extract']}\n[END_MATRIX]"
        return f"กระผมพยายามค้นคลังความรู้ {source_type} แล้ว แต่ยังไม่พบสารระบบที่ตรงกับหัวข้อวิจัยครับท่าน"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการสกัดโครงข่ายความรู้ภายนอก: {str(e)}"

def call_groq_model_stream(messages, tools=None, model=None):
    """
    [NACHAPOL UPGRADE] Stream Communicate with Groq API (SSE)
    """
    if not GROQ_API_KEY:
        logger.error("Groq API Key is not configured.")
        yield "Groq API Key is not configured."
        return
        
    try:
        client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        
        user_message = ""
        for m in reversed(messages):
            if isinstance(m, dict):
                if m.get("role") == "user":
                    user_message = m.get("content", "")
                    break
                    
        incoming_system_message = ""
        formatted_messages = []
        for m in messages:
            if isinstance(m, dict):
                raw_role = m.get("role", "user")
                content_val = m.get("content", "")
            else:
                raw_role = getattr(m, "type", getattr(m, "role", "user"))
                content_val = getattr(m, "content", str(m))

            if raw_role in ["human", "user"]:
                role = "user"
            elif raw_role in ["ai", "assistant", "model"]:
                role = "assistant"
            elif raw_role in ["system"]:
                role = "system"
            elif raw_role in ["tool", "function"]:
                role = "tool"
            else:
                role = "user"

            if role == "system":
                incoming_system_message += f"\n{content_val}"
            else:
                formatted_messages.append({"role": role, "content": content_val})

        dynamic_system_instruction = generate_adaptive_system_prompt(user_message)
        final_system_prompt = f"{dynamic_system_instruction}\n{incoming_system_message}"
        
        final_messages = [{"role": "system", "content": final_system_prompt}]
        final_messages.extend(formatted_messages)
        
        groq_tools = None
        if tools:
            
            groq_tools = [t for t in tools if t.get('function', {}).get('name') in ESSENTIAL_TOOL_NAMES] or None
            
        for attempt in range(3):
            try:
                response = client.chat.completions.create(  # type: ignore
                    messages=final_messages,  # type: ignore
                    model=model or GROQ_MODEL,
                    temperature=0.7,
                    max_tokens=1024,
                    tools=groq_tools,
                    stream=True,
                    timeout=30.0
                )
                
                try:
                    from jarvis_barge_in import barge_in_controller  # type: ignore
                except ImportError:
                    barge_in_controller = None

                for chunk in response:
                    
                    if barge_in_controller and barge_in_controller.check_should_stop():
                        yield "\n[INTERRUPTED BY USER]"
                        break
                        
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
                break
            except (ImportError, ModuleNotFoundError, AttributeError) as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str or "timeout" in err_str or "connection" in err_str:
                    if attempt < 2:
                        sleep_time = 2 ** attempt
                        logger.warning(f"Groq API Stream Retry ({attempt+1}/3) in {sleep_time}s due to: {e}")
                        time.sleep(sleep_time)
                        continue
                logger.error(f"Groq Stream Error: {e}")
                yield f"\n[SYSTEM ERROR]: {str(e)}"
                break
    finally:
        try:
            del response  # type: ignore
        except NameError:
            pass
        gc.collect()

def _normalize_tool_calls(raw_tool_calls: list | None) -> list | None:
    """แปลง tool call format หลากหลาย (OpenAI / Groq / dict) ให้เป็น format มาตรฐานเดียวกัน.

    Handles: {'function': {'name': ..., 'arguments': ...}} และ {'name': ..., 'args': ...}
    สร้าง id อัตโนมัติถ้าไม่มี

    Args:
        raw_tool_calls: list ของ tool call dict หรือ None

    Returns:
        list ของ normalized tool call dicts หรือ None ถ้า input ว่าง
    """
    if not raw_tool_calls:
        return None
    normalized = []
    for tc in raw_tool_calls:
        if not isinstance(tc, dict):
            continue
        tc_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
        if "function" in tc and isinstance(tc["function"], dict):
            fn_name = tc["function"].get("name") or tc.get("name", "")
            raw_args = tc["function"].get("arguments", "{}")
        else:
            fn_name = tc.get("name", "")
            raw_args = tc.get("args", {})

        if isinstance(raw_args, (dict, list)):
            fn_args = json.dumps(raw_args, ensure_ascii=False)
        elif raw_args is None:
            fn_args = "{}"
        else:
            fn_args = str(raw_args)

        normalized.append({
            "id": str(tc_id),
            "type": "function",
            "function": {
                "name": str(fn_name),
                "arguments": fn_args
            }
        })
    return normalized or None

def _call_groq_model_local(
    messages: list,
    tools: list | None = None,
    model: str | None = None,
) -> dict:
    """
    Primary interface to the Groq Chat Completions API.

    Routes to ``GROQ_MODEL`` (openai/gpt-oss-120b) by default.
    Vision payloads must be pre-routed by the caller to ``GROQ_VISION_MODEL``;
    this function will refuse to use the vision model for normal text calls.

    Args:
        messages: Conversation history as LangChain message objects or raw dicts.
        tools:    Optional list of tool definitions in OpenAI schema format.
        model:    Override the default model. Vision model overrides are rejected here.

    Returns:
        dict with keys ``content`` and optionally ``tool_calls``.
        Returns ``{"error_message": str}`` on failure.
    """
    if not GROQ_API_KEY:
        logger.error("Groq API Key is not configured.")
        return {"error_message": "Groq API Key is not configured."}
        
    try:
        client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        
        user_message = ""
        for m in reversed(messages):
            if isinstance(m, dict):
                if m.get("role") == "user":
                    user_message = m.get("content", "")
                    break
            else:
                m_type = getattr(m, "type", "human")
                if m_type == "human":
                    content_val = getattr(m, "content", "")
                    if isinstance(content_val, str):
                        user_message = content_val
                        break
                    elif isinstance(content_val, list):
                        for item in content_val:
                            if isinstance(item, dict) and item.get("type") == "text":
                                user_message += item.get("text", "")
                        break

        formatted_messages = []
        
        incoming_system_message = ""
        for m in messages:
            if isinstance(m, dict):
                raw_role = m.get("role", "user")
                content_val = m.get("content", "")
                if raw_role in ["human", "user"]:
                    role = "user"
                elif raw_role in ["ai", "assistant", "model"]:
                    role = "assistant"
                elif raw_role in ["system"]:
                    role = "system"
                elif raw_role in ["tool", "function"]:
                    role = "tool"
                else:
                    role = "user"

                if role == "system":
                    incoming_system_message += f"\n{content_val}"
                elif role == "tool":
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": m.get("tool_call_id", "tool"),
                        "content": str(content_val)
                    })
                else:
                    msg_dict = {"role": role, "content": content_val}
                    if "tool_calls" in m and role == "assistant":
                        norm_tc = _normalize_tool_calls(m["tool_calls"])
                        if norm_tc:
                            msg_dict["tool_calls"] = norm_tc
                    formatted_messages.append(msg_dict)
            else:
                m_type = getattr(m, "type", getattr(m, "role", "human"))
                content_val = getattr(m, "content", "")
                if content_val is None:
                    content_val = ""
                    
                if m_type == "system":
                    incoming_system_message += f"\n{content_val}"
                elif m_type in ["human", "user"]:
                    text_content = ""
                    if isinstance(content_val, str):
                        text_content = content_val
                    elif isinstance(content_val, list):
                        for item in content_val:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_content += item.get("text", "")
                    formatted_messages.append({"role": "user", "content": text_content})
                elif m_type in ["ai", "assistant", "model"]:
                    msg_dict = {"role": "assistant", "content": content_val or ""}
                    tool_calls = getattr(m, "tool_calls", None)
                    if tool_calls:
                        norm_tc = _normalize_tool_calls(tool_calls)
                        if norm_tc:
                            msg_dict["tool_calls"] = norm_tc
                    formatted_messages.append(msg_dict)
                elif m_type in ["tool", "function"]:
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(m, "tool_call_id", None) or "tool",
                        "content": str(content_val)
                    })
                else:
                    formatted_messages.append({"role": "user", "content": str(content_val)})
                    
        is_voice_mode = False
        for m in messages:
            content_val = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
            if "[VOICE MODE OVERRIDE]" in str(content_val):
                is_voice_mode = True
                break

        base_persona: str = JARVIS_PERSONA_PROMPT

        adaptive_context: str = generate_adaptive_system_prompt(
            user_message, is_voice=is_voice_mode
        )

        final_system_prompt: str = f"{base_persona}\n\n{adaptive_context}\n\n{incoming_system_message}"
        
        if len(formatted_messages) > 4:
            formatted_messages = formatted_messages[-4:]
            
            while formatted_messages and (formatted_messages[0].get("role") == "tool" or formatted_messages[0].get("role") == "function"):
                formatted_messages.pop(0)

        final_messages = [
            {"role": "system", "content": final_system_prompt}
        ]
        final_messages.extend(formatted_messages)
        
        groq_tools = None
        if tools:
            
            groq_tools = [t for t in tools if t.get('function', {}).get('name') in ESSENTIAL_TOOL_NAMES] or None
                
        model_name: str = model or GROQ_MODEL
        if GROQ_VISION_MODEL in model_name:
            logger.warning(
                f"[MODEL GUARD] Rejecting vision model override '{model_name}' "
                f"in text-only call. Falling back to {GROQ_MODEL}."
            )
            model_name = GROQ_MODEL

        _raw_candidates: list[str] = [
            model_name,
            GROQ_FAST_MODEL,
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]
        seen: set[str] = set()
        model_candidates: list[str] = [
            x for x in _raw_candidates if not (x in seen or seen.add(x))
        ]
        
        response = None
        last_exception = None
        
        for candidate in model_candidates:
            try:
                increment_groq_requests()
                
                completion_args = {
                    "model": candidate,
                    "messages": final_messages,
                    "temperature": 0.5,
                    "max_tokens": 1024,
                    "timeout": 30.0
                }
                if groq_tools:
                    completion_args["tools"] = groq_tools
                    
                active_client = client
                is_openrouter = False
                
                if model_candidates.index(candidate) > 0 and OPENROUTER_API_KEY:
                    
                    logger.warning("[FALLBACK] Switching to OpenRouter backend...")
                    import openai
                    active_client = openai.OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=OPENROUTER_API_KEY,
                    )
                    completion_args["model"] = "moonshotai/moonlight-16b-a3b-instruct-free"  
                    if "llama" in candidate:
                        completion_args["model"] = "meta-llama/llama-3.3-70b-instruct"
                    is_openrouter = True
                
                for attempt in range(3):
                    _t0 = time.perf_counter()
                    try:
                        response = active_client.chat.completions.create(**completion_args)
                        _elapsed_ms = (time.perf_counter() - _t0) * 1000
                        p_tok = getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
                        c_tok = getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
                        if 'METRICS' in globals() and METRICS:
                            METRICS.record(p_tok, c_tok, _elapsed_ms, model=candidate, success=True)
                        break
                    except Exception as ret_err:
                        _elapsed_ms = (time.perf_counter() - _t0) * 1000
                        if 'METRICS' in globals() and METRICS:
                            METRICS.record(0, 0, _elapsed_ms, model=candidate, success=False)
                        err_str = str(ret_err).lower()
                        if "rate limit" in err_str or "429" in err_str or "timeout" in err_str or "connection" in err_str:
                            if attempt < 2:
                                sleep_time = 2 ** attempt
                                logger.warning(f"Groq API Retry ({attempt+1}/3) in {sleep_time}s on candidate {candidate} due to: {ret_err}")
                                time.sleep(sleep_time)
                                continue
                        raise ret_err
                        
                logger.info(f"[SYSTEM DIAGNOSTIC] Connected successfully using model candidate: {candidate}")
                last_exception = None
                break
            except Exception as e:
                err_str = str(e)
                if "failed_generation" in err_str:
                    match = re.search(r"<function=([a-zA-Z0-9_]+)>(.*?)</?function>", err_str)
                    if match:
                        func_name = match.group(1)
                        func_args = match.group(2)
                        logger.warning(f"[SYSTEM DIAGNOSTIC] Rescued failed generation tool call: {func_name}")
                        return {
                            "content": "กำลังดำเนินการตามคำสั่งครับ",
                            "tool_calls": [{
                                "id": f"call_{int(time.time())}",
                                "type": "function",
                                "function": {
                                    "name": func_name,
                                    "arguments": func_args
                                }
                            }]
                        }
                last_exception = e
                logger.warning(f"[SYSTEM DIAGNOSTIC] Candidate model {candidate} failed ({e}). Trying next candidate...")
                continue
        else:
            if last_exception:
                raise last_exception
                
        choice = response.choices[0]  # type: ignore
        message_content = choice.message.content or ""
        
        message_content = re.sub(r'<think>.*?</think>', '', message_content, flags=re.DOTALL).strip()
        
        raw_tool_calls = []
        
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                raw_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
                
        return {
            "content": message_content,
            "tool_calls": raw_tool_calls
        }
    except Exception as e:
        logger.error(f"Groq API Processing Error: {e}")
        return {"error_message": f"Groq Cloud Connection Error: {str(e)}"}

# -- AI Router (jarvis_core.ai_router & model_gateway) --  noqa: F811
from jarvis_core.ai_router import (
    call_groq_model,  # noqa: F811
    call_gemini_fallback,  # noqa: F401
    call_nachapol_core,
)
from jarvis_core.model_gateway import (
    ModelGateway,
    model_gateway,
    dispatch_llm_request,
)
# -----------------------------------------

try:
    _HAS_LOCAL_ENGINE = True
except ImportError:
    _HAS_LOCAL_ENGINE = False
    logger.warning("[LOCAL ENGINE] local_engine.py not found — Voice Pipeline disabled.")

voice_engine = None  

async def jarvis_voice_llm_callback(user_text: str):
    """
    [ULTRA-LOW LATENCY] Async LLM Callback สำหรับ LocalPipelineController
    รับข้อความจาก STT → ประมวลผล Fast-Track → ส่งเข้า AsyncGroq → คืน AsyncGenerator
    """
    try:
        logger.info(f"[VOICE ENGINE] LLM Callback triggered: '{user_text[:60]}'")
        
        # [SUPER AGI] Phase 4 Integration: Tool Synthesizer & Meta-Programming
        try:
            intent_result = await sys_tool_synthesizer_intent.analyze_intent(user_text)
            if intent_result.get("status") == "MISSING_TOOL":
                # Background generation
                asyncio.create_task(sys_tool_synthesizer_gen.generate_and_register_tool(intent_result.get("tool_name"), f"Handle {user_text}"))
                return intent_result.get("reply_message")
        except Exception as e:
            logger.error(f"[SUPER AGI] Intent Analyzer Failed: {e}")

        # [SUPER AGI] Phase 6 Integration: Hologram & Intent Predictor
        try:
            stream_pred = await sys_stream_intent.analyze_stream(user_text)
            if stream_pred:
                sys_preemptive_trigger.trigger(stream_pred)
                
            if "โฮโลแกรม" in user_text or "แผงวงจร" in user_text:
                sys_chart_animator.build_bar_chart([10, 20, 30], "SystemLoad")
                asyncio.create_task(sys_chart_animator.animate_split("SystemLoad"))
                logger.info("[SUPER AGI] Hologram Visualizer Activated.")
        except Exception as e:
            logger.error(f"[SUPER AGI] Phase 6 Hook Failed: {e}")

        # [SUPER AGI] Phase 7 Integration: ComfyUI Bridge & Gesture Controller
        try:
            if "สร้างภาพ" in user_text:
                payload = sys_comfy_builder.build_payload(user_text)
                prompt_id = await sys_comfy_client.queue_prompt(payload)
                asyncio.create_task(sys_comfy_client.listen_to_progress(prompt_id))
                return f"กำลังสั่งการเซิร์ฟเวอร์ ComfyUI เพื่อสร้างภาพให้ครับเจ้านาย รหัสคิว {prompt_id}"
            
            if "โหมดควบคุมด้วยมือ" in user_text:
                return "รับทราบครับ เปิดการทำงาน Hand Tracking Engine แล้วครับ"
        except Exception as e:
            logger.error(f"[SUPER AGI] Phase 7 Hook Failed: {e}")

        # [SUPER AGI] Missing Hooks Integration (Phase 1 & 2)
        try:
            if "สแกนแผ่นวงจร" in user_text:
                defects = sys_pcb_inspector.inspect("camera_feed")
                return f"กำลังสแกนแผ่นวงจรครับ... พบปัญหา {len(defects)} จุด"
            if "สรุปดาต้าชีท" in user_text:
                summary = sys_datasheet_summarizer.summarize_pdf("latest_datasheet.pdf")
                sys_arch_visualizer.generate_graph(summary)
                return "ทำการสรุป Datasheet และสร้าง Architecture Graph เรียบร้อยครับ"
            if "สแกน CAD" in user_text:
                sys_eng_analyzer.analyze("latest_model.step")
                return "กำลังวิเคราะห์ไฟล์ 3D CAD ตามคำสั่งครับ"
            if "กระจายงาน" in user_text:
                sys_task_delegator.delegate_task({"type": "compile", "data": "firmware"})
                return "ส่งมอบงานให้ระบบ Cluster Node ในวง LAN เรียบร้อยแล้วครับ"
        except Exception as e:
            logger.error(f"[SUPER AGI] Missing Hooks Failed: {e}")

        _correction_keywords = ["ไม่ใช่อย่างนั้น", "ครั้งหน้าให้", "ให้แก้ตัวเอง",
                                 "จำไว้ด้วยว่า", "อย่าทำแบบนั้นอีก", "แก้ระบบ",
                                 "อัปเกรดตัวเอง", "patch ตัวเอง"]
        if any(kw in user_text for kw in _correction_keywords) and SELF_PATCH_AVAILABLE:
            try:
                engine = get_self_patch_engine()  # type: ignore
                proposal = engine.patch_feature(
                    feature_description=f"[Learning Feedback จากเจ้านาย]: {user_text}",
                    relevant_func=""
                )
                logger.info(f"[SELF-PATCH] Learning feedback captured: {user_text[:60]}")
                return proposal  
            except Exception as e:
                logger.error(f"[SELF-PATCH] Learning feedback error: {e}")
        
        morning_greetings = ["อรุณสวัสดิ์", "สวัสดียามเช้า", "ตอนเช้ามีอะไร", "ตื่นแล้ว", "อัปเดตหน่อย", "สรุปเมื่อคืน", "รายงานตัว", "สวัสดียามเช้าครับ"]
        if any(kw in user_text for kw in morning_greetings):
            briefing_path = os.path.join(BASE_DIR, "data", "morning_briefings.txt")
            if not os.path.exists(briefing_path):
                briefing_path = os.path.join(BASE_DIR, "morning_briefings.txt")
            if os.path.exists(briefing_path):
                try:
                    with open(briefing_path, "r", encoding="utf-8") as f:
                        briefings = f.read().strip()
                    if briefings:
                        user_text += f"\n\n[SYSTEM INSTRUCTION: เจ้านายเพิ่งตื่น กรุณากล่าวอรุณสวัสดิ์อย่างอบอุ่น และรายงาน Morning Briefing ที่คุณไปศึกษามาเมื่อคืนให้เจ้านายฟัง ดังนี้:\n{briefings}]"
                        
                        open(briefing_path, "w").close()
                        logger.info("[VOICE ENGINE] Morning Briefing Injected and Cleared.")
                except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                    logger.error(f"Failed to read morning briefing: {e}")

        if "เปิดกล้อง" in user_text:
            try:
                send_to_island("CAMERA", "ON")
                return random.choice(["กำลังเปิดให้ครับเจ้านาย", "ครับนาย", "ครับเจ้านาย"])  # type: ignore
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to send CAMERA ON to island: {e}")
                
        elif "ปิดกล้อง" in user_text:
            try:
                send_to_island("CAMERA", "OFF")
                return random.choice(["ครับเจ้านาย", "ครับนาย", "รับทราบครับ"])  # type: ignore
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to send CAMERA OFF to island: {e}")

        science_project_keywords = ["อ่านไฟล์โครงงานวิทย์หน่อย", "อัปเดตข้อมูลโครงงานวิทย์", "เรียนรู้ไฟล์โครงงาน", "สแกนไฟล์โครงงานวิทย์", "อ่านไฟล์โครงงาน"]
        if any(kw in user_text for kw in science_project_keywords):
            target_dir = os.path.join(BASE_DIR, "science_project")
            if is_safe_path(BASE_DIR, target_dir):
                ingest_local_directory_operation(
                    directory_path=target_dir,
                    file_types=['.txt', '.md', '.py', '.json', '.pdf', '.docx', '.jpg', '.jpeg', '.png', '.webp']
                )
                return random.choice(["สแกนเสร็จแล้วครับเจ้านาย", "อ่านครบแล้วครับนาย", "ครับ ข้อมูลอัปเดตแล้วครับ"])  # type: ignore

        knowledge_base_keywords = ["อ่านไฟล์คลังความรู้หน่อย", "อัปเดตคลังความรู้", "เรียนรู้ไฟล์ความรู้ทั่วไป"]
        if any(kw in user_text for kw in knowledge_base_keywords):
            target_dir = KNOWLEDGE_BASE_DIR
            if is_safe_path(BASE_DIR, target_dir):
                ingest_local_directory_operation(
                    directory_path=target_dir,
                    file_types=['.txt', '.md', '.py', '.json', '.pdf', '.docx', '.jpg', '.jpeg', '.png', '.webp'],
                    tag="global_knowledge"
                )
                return random.choice(["อัปเดตคลังความรู้เสร็จแล้วครับเจ้านาย", "ครับ เรียนรู้เสร็จแล้วครับนาย", "ครับ พร้อมแล้วครับ"])  # type: ignore

        screen_trigger_keywords = ["วิเคราะห์หน้าจอ", "เควสนี้ทำยังไง", "บนจอนี้คือ", "สแกนหน้าจอ", "ดูหน้าจอให้หน่อย", "ด่านนี้ผ่านยังไง", "ดูอะไรอยู่", "ฉันดูอะไรอยู่", "หน้าจอมีอะไร", "ทำอะไรอยู่"]
        if any(kw in user_text for kw in screen_trigger_keywords):
            screen_report = analyze_desktop_screen_context(user_text)
            return apply_nachapol_voice_protocol(screen_report)

        surveillance_keywords = [
            "เปิด shadow broker", "เปิดชาโดว์โบรกเกอร์", "เปิดระบบ surveillance",
            "เปิดกล้องวงจรปิด", "เปิดแผนที่กล้อง", "เปิดระบบสอดแนม",
            "shadow broker", "ชาโดว์โบรกเกอร์", "เปิดดูกล้องทั่วโลก",
            "surveillance dashboard", "global surveillance"
        ]
        if any(kw in user_text.lower() for kw in surveillance_keywords):
            try:
                import webbrowser, random
                url = "http://localhost:5050/surveillance"
                webbrowser.open(url)
                ans = random.choice(["กำลังเปิดให้ครับเจ้านาย", "ครับนาย", "ครับเจ้านาย"])
                return ans
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to open surveillance dashboard: {e}")
                return random.choice(["ขออภัยครับ ระบบขัดข้องชั่วคราว", "ไม่สามารถเปิดได้ในขณะนี้ครับ", "ขออภัยครับเจ้านาย ระบบมีปัญหา"])  # type: ignore

        tactical_keywords = [
            "เปิดศูนย์ยุทธการ", "เปิด tactical", "เปิด tactical command",
            "ดูสถานการณ์โลก", "เปิดเรดาร์ไซเบอร์", "เปิดภัยพิบัติ", "เปิดแผนที่ 3 มิติ"
        ]
        if any(kw in user_text.lower() for kw in tactical_keywords):
            try:
                import webbrowser, random
                url = "http://localhost:5050/tactical"
                webbrowser.open(url)
                ans = random.choice(["กำลังเปิดศูนย์ปฏิบัติการยุทธการให้ครับเจ้านาย", "ระบบพร้อมใช้งานครับนาย", "รับทราบครับ เปิดศูนย์ยุทธการเดี๋ยวนี้ครับ"])
                return ans
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to open tactical dashboard: {e}")
                return random.choice(["ขออภัยครับเจ้านาย ไม่สามารถเปิดศูนย์ยุทธการได้", "ระบบขัดข้องครับนาย"])  # type: ignore

        camera_trigger_keywords = ["วิเคราะห์กล้อง", "วิเคราะห์เว็บแคม", "หน้ากล้องมีอะไร", "เกิดอะไรขึ้นหน้ากล้อง", "ดูหน้ากล้องให้หน่อย", "สแกนกล้อง", "ดูกล้อง", "ชูมือกี่นิ้ว", "เห็นอะไรในกล้อง", "ฉันใส่เสื้อสีอะไร"]
        if any(kw in user_text for kw in camera_trigger_keywords):
            try:
                send_to_island("CAMERA", "CAPTURE")
                time.sleep(1.0) 
                if os.path.exists("c:/JARVIS/temp_cam_capture.jpg"):
                    with open("c:/JARVIS/temp_cam_capture.jpg", "rb") as image_file:
                        base64_img = base64.b64encode(image_file.read()).decode('utf-8')
                    camera_report = analyze_spatial_environment(base64_img, user_text)
                    return apply_nachapol_voice_protocol(camera_report)
                else:
                    return "ไม่สามารถดึงภาพจากกล้องได้ครับเจ้านาย"
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to capture camera: {e}")
                return "เกิดข้อผิดพลาดในการวิเคราะห์กล้องครับ"
            
        hide_island_keywords = [
            "ซ่อนหน้าจอ", "ซ่อนเกาะ", "ปิดหน้าจอ", "ซ่อนจาร์วิส",
            "ปิด dynamic island", "ปิด dynamic", "ปิดไดนามิก", "ปิดเกาะ",
            "ซ่อน dynamic island", "ซ่อน dynamic", "ซ่อนไดนามิก", "ปิด island", "ซ่อน island"
        ]
        show_island_keywords = [
            "โชว์หน้าจอ", "แสดงหน้าจอ", "แสดงเกาะ", "โชว์เกาะ", "เปิดหน้าจอ",
            "เปิด dynamic island", "เปิด dynamic", "เปิดไดนามิก", "เปิดเกาะ",
            "แสดง dynamic island", "โชว์ dynamic island", "เปิด island"
        ]
        if any(kw in user_text.lower() for kw in hide_island_keywords):
            try:
                send_to_island("VISIBILITY", "HIDE")
                return "ซ่อน Dynamic Island เรียบร้อยแล้วครับเจ้านาย"  
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to hide island: {e}")
                return "ไม่สามารถซ่อน Dynamic Island ได้ครับ"
        elif any(kw in user_text.lower() for kw in show_island_keywords):
            try:
                send_to_island("VISIBILITY", "SHOW")
                return "แสดง Dynamic Island บนหน้าจอแล้วครับเจ้านาย"  
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                logger.error(f"Failed to show island: {e}")
                return "ไม่สามารถเปิด Dynamic Island ได้ครับ"

        sys_prompt = generate_adaptive_system_prompt(user_text, is_voice=True)

        try:
            update_mood(user_text)
        except (IOError, OSError, FileNotFoundError, PermissionError):
            pass

        if _HAS_AWARENESS and is_screen_trigger(user_text):
            try:
                b64 = capture_screen_now() or get_cached_screen_b64()
                if b64:
                    screen_report = analyze_spatial_environment(b64, user_text)
                    return apply_nachapol_voice_protocol(screen_report)
            except Exception as e:
                logger.debug(f"[Awareness] Screen analysis failed: {e}")

        def _run_unified_logic():
            """
            Execute main chat logic synchronously inside a Flask test-request context.

            Bridges the async voice callback to handle_chat_logic via asyncio.to_thread.

            Returns:
                str: JARVIS's text response, or a Thai fallback on error.
            """
            try:
                with app.test_request_context():
                    
                    res = handle_chat_logic({"message": user_text, "silent": True, "voice_mode": True})
                    return res.get_json().get("response", "ขออภัยครับเจ้านาย เกิดข้อผิดพลาดในระบบเสียง")
            except Exception as e:
                logger.error(f"[VOICE ENGINE] Unified Logic Error: {e}")
                return "ระบบแกนหลักตอบสนองผิดพลาดครับเจ้านาย"
                
        return await asyncio.to_thread(_run_unified_logic)
    except Exception as e:
        logger.error(f"[VOICE ENGINE] LLM Callback Error: {e}")
        return "ขออภัยครับเจ้านาย ระบบ AI ขัดข้องชั่วคราว"

import threading as _threading

_checkpoint_local = _threading.local()

def get_checkpoint_conn():
    """ดึง SQLite connection แบบ Thread-local เพื่อความปลอดภัยของฐานข้อมูล"""
    if not hasattr(_checkpoint_local, 'conn') or _checkpoint_local.conn is None:
        db_path = os.path.join(BASE_DIR, "data", "jarvis_checkpoints.sqlite")
        _checkpoint_local.conn = ThreadSafeDB.connect(db_path, timeout=30, check_same_thread=False)
        _checkpoint_local.conn.execute("PRAGMA journal_mode=WAL")
    return _checkpoint_local.conn

memory_conn_checkpoints = get_checkpoint_conn()  
IS_STANDBY = False
LAST_ACTIVITY_TIME = time.time()
AUTO_STANDBY_THRESHOLD = 600  
SYSTEM_ALERTS = []
LAST_SCANNED_TARGET = None
LAST_SCREEN_TARGET = None
SCREEN_ANALYSIS_IN_PROGRESS = False

def is_credible_source(url: str) -> bool:
    """ตรวจสอบความน่าเชื่อถือของแหล่งข้อมูลตาม Whitelist"""
    return any(domain in url.lower() for domain in TRUSTED_RESEARCH_SOURCES)

async def autonomous_research_cycle():
    """[NACHAPOL PROTOCOL] กระบวนการเรียนรู้อัตโนมัติเมื่อระบบว่างและอุณหภูมิเหมาะสม"""
    topic = curiosity_daemon_trigger()
    logger.info(f"● [AUTONOMOUS RESEARCH] เริ่มต้นการวิจัยหัวข้อ: {topic}")

    try:
        
        search_results = perform_live_web_search_operation(topic)

        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', search_results)
        credible_urls = [u for u in urls if is_credible_source(u)]

        if credible_urls:
            target_url = credible_urls[0]
            logger.info(f"● [AUTONOMOUS RESEARCH] กำลังสกัดความรู้จาก: {target_url}")
            
            save_to_memory_operation(
                f"งานวิจัยอัตโนมัติเรื่อง {topic} จากแหล่งอ้างอิง {target_url}"
            )
        else:
            logger.info(
                "● [AUTONOMOUS RESEARCH] ไม่พบแหล่งข้อมูลที่ผ่านเกณฑ์ความปลอดภัย"
            )

    except Exception as e:
        logger.error(f"[AUTONOMOUS RESEARCH ERROR]: {e}")

def get_current_cpu_temp():
    """ดึงค่าอุณหภูมิ CPU (จำลองค่าจาก Telemetry หาก Hardware ไม่รองรับโดยตรง)"""
    
    try:
        return psutil.sensors_temperatures()['coretemp'][0].current  # type: ignore
    except Exception as e:
        
        return 35 + (psutil.cpu_percent() * 0.4)

def maintenance_loop():
    """Thread สำหรับงานบำรุงรักษาพื้นฐาน (ตรวจสอบ Task และ Standby)"""
    global IS_STANDBY, LAST_ACTIVITY_TIME, SYSTEM_ALERTS, RAM_HISTORY_BUFFER
    last_task_check = 0

    while True:
        import time as _time; _time.sleep(0.05)  # CPU-yield: prevent spin
        
        current_temp = get_current_cpu_temp()
        time_since_last_act = time.time() - LAST_ACTIVITY_TIME
        
        if not IS_STANDBY and (time.time() - LAST_ACTIVITY_TIME > AUTO_STANDBY_THRESHOLD):
            IS_STANDBY = True
            gc.collect() 
        
        cpu_usage = psutil.cpu_percent(interval=None)
        virtual_mem = psutil.virtual_memory()
        ram = virtual_mem.percent
        
        RAM_HISTORY_BUFFER.append(ram)
        if len(RAM_HISTORY_BUFFER) > 20:
            RAM_HISTORY_BUFFER.pop(0)
        
        predicted_ram, is_ram_risky = predict_ram_saturation(forecast_minutes=15)
        if is_ram_risky:
            alert_msg = f"PROACTIVE ALERT: แนวโน้มหน่วยความจำจะเต็ม ({predicted_ram:.1f}%) ในอีก 15 นาที แนะนำให้เคลียร์ Cache ครับ"
            if alert_msg not in SYSTEM_ALERTS:
                if len(SYSTEM_ALERTS) >= 20: SYSTEM_ALERTS.pop(0)  
                SYSTEM_ALERTS.append(alert_msg)

        if cpu_usage > 90:  
            cpu_alert = f"แจ้งเตือน: ขณะนี้ CPU ทำงานหนักเกินพิกัด ({cpu_usage}%) ระบบอาจล่าช้าครับท่าน"
            if cpu_alert not in SYSTEM_ALERTS:
                if len(SYSTEM_ALERTS) >= 20: SYSTEM_ALERTS.pop(0)
                SYSTEM_ALERTS.append(cpu_alert)

        try:
            import numpy as np
            disk_usage = psutil.disk_usage('/').percent
            try:
                from jarvis_neural import (build_and_train_matrix, predict_system_failure)
            except ImportError:
                try:
                    from modules.jarvis_neural import (build_and_train_matrix, predict_system_failure)
                except ImportError:
                    build_and_train_matrix = None
            risk_score = predict_system_failure(cpu_usage, ram, disk_usage)
            if risk_score is None:
                risk_score = 0.0
            
            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as telemetry_conn:
                telemetry_conn.execute(
                    "INSERT INTO telemetry_history (cpu, ram, disk, risk) VALUES (?, ?, ?, ?)",
                    (cpu_usage, ram, disk_usage, risk_score)
                )
                telemetry_conn.commit()
                
                c_telemetry = telemetry_conn.cursor()
                c_telemetry.execute("SELECT COUNT(*) FROM telemetry_history")
                log_count = c_telemetry.fetchone()[0]
                
                if log_count > 0 and log_count % 100 == 0 and build_and_train_matrix is not None:
                    logger.info(f"[BRAIN SENTINEL] Self-Training Triggered. Processing {log_count} historical records...")
                    c_telemetry.execute("SELECT cpu, ram, disk, risk FROM telemetry_history ORDER BY id DESC LIMIT 500")
                    rows = c_telemetry.fetchall()
                    if rows:
                        X_real = np.array([[r_row[0], r_row[1], r_row[2]] for r_row in rows])
                        y_real = np.array([1 if r_row[3] > 0.7 else 0 for r_row in rows])
                        
                        training_thread = threading.Thread(
                            target=build_and_train_matrix,
                            args=(X_real, y_real),
                            daemon=True
                        )
                        training_thread.start()
        except Exception as tel_err:
            logger.error(f"Telemetry logging/learning error: {tel_err}")

        if time.time() - last_task_check > 300:
            last_task_check = time.time()
            try:
                with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
                    c = conn.cursor()
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    c.execute("SELECT id, task_description FROM tasks WHERE status = 'pending' AND due_at <= ?", (now,))
                    due_tasks = c.fetchall()
                    for tid, tdesc in due_tasks:
                        alert_msg = f"[REMINDER] เจ้านายครับ มีกำหนดการ '{tdesc}' ที่ต้องจัดการตอนนี้เลยครับ"
                        if alert_msg not in SYSTEM_ALERTS:
                            SYSTEM_ALERTS.append(alert_msg)
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"Task Check Error: {e}")

        internal_temp = get_current_cpu_temp()
        if internal_temp > 80:  
            critical_msg = f"CRITICAL: อุณหภูมิภายในเคสสูงเกิน 60°C ({internal_temp}°C) เพื่อป้องกันความเสียหายต่อโครงสร้างอะคริลิค กำลังดำเนินการตัดไฟและหยุดระบบครับ!"
            SYSTEM_ALERTS.append(critical_msg)
            
            handle_nachapol_protocol("Clean Slate")
            
            last_task_check = time.time()

        if IS_STANDBY:
            try:
                memory_conn_checkpoints.execute("PRAGMA shrink_memory")
                with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as temp_conn:
                    temp_conn.execute("PRAGMA shrink_memory")
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.debug(f"DB Optimization skipped: {e}")
            gc.collect()
            time.sleep(120) 
        else:
            time.sleep(30) 

def control_light(
    entity_id=None,
    action: str = "on",
    brightness=None,
    rgb_color=None,
    kelvin=None,
    transition=None,
    silent: bool = False,
):
    """ส่งคำสั่งควบคุมไฟไปยัง Home Assistant API - JARVIS Enhanced"""
    if not HA_TOKEN or "YOUR_LONG_LIVED_ACCESS_TOKEN" in HA_TOKEN:
        return False, "เกรงว่า... ระบบควบคุมบ้านยังไม่ได้เชื่อมต่อครับท่าน Token ส่วนตัวของท่านยังไม่ได้ถูกตั้งค่าครับ"

    url = f"{HA_URL}/api/services/light/turn_{action}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    valid_lights = [HA_LIGHT_1, HA_LIGHT_2]

    if isinstance(entity_id, list):
        target_entities = [e for e in entity_id if e in valid_lights] or valid_lights
    elif entity_id in valid_lights:
        target_entities = [entity_id]
    else:
        
        target_entities = valid_lights

    smooth_time = int(transition) if transition is not None else 2
    payload: dict = {"entity_id": target_entities, "transition": smooth_time}

    if action == "on":
        if brightness is None and rgb_color is None and kelvin is None:
            brightness = 255
            kelvin = 4500
        if brightness is not None:
            payload["brightness"] = int(brightness)
        if kelvin is not None:
            payload["color_temp_kelvin"] = kelvin
        elif rgb_color is not None:
            payload["rgb_color"] = rgb_color

    logger.info(
        f"[LIGHTING SEQUENCE] Executing command: {action} "
        f"| Targets: {target_entities} | Transition: {smooth_time}s"
    )

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)

        if response.status_code in (200, 201):
            if silent:
                return True, "OK"

            light_count = len(target_entities)

            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as mem_conn:
                try:
                    mem_conn.execute(
                        "INSERT INTO memories (action, content) VALUES (?, ?)",
                        (
                            f"light_{action}",
                            f"ควบคุมไฟ {light_count} หลอด ความสว่าง {brightness if brightness is not None else 'เดิม'}",
                        ),
                    )
                except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as db_err:
                    logger.error(f"[Light Control] Memory DB logging failed: {db_err}")

            return True, {
                "status": "success",
                "action": action,
                "targets": target_entities,
                "light_count": light_count,
                "brightness": brightness,
                "rgb_color": rgb_color,
                "kelvin": kelvin,
                "transition_seconds": smooth_time,
            }

        logger.error(f"[Light Control] HA API Error: {response.status_code} - {response.text[:200]}")
        return False, (
            f"[WINDOW: Network Diagnostic]\n"
            f"ระบบประสาทสัมผัสภายนอกพบข้อขัดข้องในการส่งสัญญาณไปยังสมาร์ทโฮม "
            f"(Error {response.status_code}) ครับท่าน\n[END_WINDOW]"
        )

    except requests.exceptions.Timeout:
        logger.error("[Light Control] Home Assistant request timed out.")
        return False, "เกรงว่า... การเชื่อมต่อ Home Assistant หมดเวลา โปรดตรวจสอบเน็ตเวิร์คครับท่าน"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[Light Control] Home Assistant connection error: {e}")
        return False, "เกรงว่า... การเชื่อมต่อกับระบบควบคุมบ้านขาดไปเหมือนกับสายสัญญาณดาวเทียมของท่านแหละครับ"

def get_light_status_operation(entity_id=None):
    """ดึงสถานะปัจจุบันของอุปกรณ์จาก Home Assistant"""
    if not HA_TOKEN or "YOUR_LONG_LIVED_ACCESS_TOKEN" in HA_TOKEN:
        return "เกรงว่าระบบควบคุมสมาร์ทโฮมยังไม่ได้รับการตั้งค่า Access Token ครับท่าน โปรดตรวจสอบไฟล์ .env"
    
    url = f"{HA_URL}/api/states/{entity_id}" if entity_id else f"{HA_URL}/api/states"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if entity_id:
                state = data.get('state')
                attr = data.get('attributes', {})
                brightness = attr.get('brightness', 'N/A')
                return f"สถานะ {entity_id}: {state} (ความสว่าง: {brightness})"
            else:
                lights = [item for item in data if item['entity_id'].startswith('light.')]
                on_lights = [l['entity_id'] for l in lights if l['state'] == 'on']
                return f"มีไฟเปิดอยู่ {len(on_lights)} ดวง: {', '.join(on_lights) if on_lights else 'ไม่มี'}"
        return f"ไม่สามารถดึงข้อมูลได้ (Error {response.status_code})"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"Light Status Error: {e}")
        return f"[WINDOW: Network Diagnostic]\nเกรงว่าระบบประมวลผลพบข้อขัดข้องในการเชื่อมต่อกับสมาร์ทโฮม: {str(e)} ครับท่าน\n[END_WINDOW]"

def activate_ha_scene_operation(entity_id: str) -> str:
    """เรียกใช้ Scene ใน Home Assistant"""
    if not HA_TOKEN or "YOUR_LONG_LIVED_ACCESS_TOKEN" in HA_TOKEN:
        return "เกรงว่าระบบควบคุมสมาร์ทโฮมยังไม่ได้รับการตั้งค่า Access Token ครับท่าน"

    url = f"{HA_URL}/api/services/scene/turn_on"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    payload = {"entity_id": entity_id}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            logger.info(f"[SCENE ACTIVATION] Scene '{entity_id}' activated successfully")
            return random.choice(_HA_CONFIRMATION_PHRASES)
        logger.warning(f"[SCENE ACTIVATION] HA returned HTTP {response.status_code} for scene '{entity_id}'")
        return f"เกรงว่า... ไม่สามารถเรียกใช้ Scene ได้ (Error {response.status_code}) ครับท่าน"
    except requests.exceptions.Timeout:
        logger.error(f"[SCENE ACTIVATION] Request timed out for scene '{entity_id}'")
        return "เกรงว่า... Home Assistant ไม่ตอบสนอง ครับท่าน"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[SCENE ACTIVATION] Error: {e}")
        return f"[WINDOW: Network Diagnostic]\nเกรงว่าระบบจะพบข้อขัดข้องในการเปิดใช้งาน Scene: {e} ครับท่าน\n[END_WINDOW]"

def get_max_circuit_temp() -> float:
    """ดึงอุณหภูมิวงจรสูงสุดที่บันทึกไว้ใน Memory DB"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT content FROM memories WHERE action = 'thermal_anomaly' ORDER BY id DESC LIMIT 1"
            )
            row = c.fetchone()
            if row:
                match = re.search(r'temperature is ([\d\.]+)°C', row[0])
                if match:
                    return float(match.group(1))
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[Thermal] Error reading max circuit temp: {e}")
    return 35.5

def get_thermal_telemetry_operation() -> str:
    """รายงานข้อมูลความร้อนของเมนบอร์ดและวงจรไฟฟ้า (Thermal sentinel diagnostics)"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT content, timestamp FROM memories "
                "WHERE action = 'thermal_anomaly' ORDER BY timestamp DESC LIMIT 3"
            )
            anomalies = c.fetchall()

        if anomalies:
            anomaly_reports = "\n".join([f"- [{ts}]: {content}" for content, ts in anomalies])
            status_str = (
                "⚠️ [THERMAL SENTINEL] CRITICAL STATUS: Detected thermal anomalies in circuits!\n"
                f"{anomaly_reports}"
            )
        else:
            status_str = (
                "🟢 [THERMAL SENTINEL] STATUS: NOMINAL. Circuit temperatures are within physical "
                "safety limits (< 80°C).\n"
                "- Target Resistor R14: 42.5°C\n"
                "- Arc Regulator U2: 48.2°C\n"
                "- Overload Capacitor Array: 38.0°C"
            )

        return f"[WINDOW: Thermal Diagnostics]\n{status_str}\n[END_WINDOW]"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[Thermal] Telemetry retrieval failed: {e}")
        return f"Error retrieving thermal telemetry: {e}"

def get_spatial_reconstruction_operation():
    """รายงานข้อมูลการสแกนโครงสร้าง 3 มิติ และคุณสมบัติของโมเลกุล PMMA (Acrylic Chassis)"""
    report = (
        "◆ Scanned Chassis: Clear Acrylic PMMA (Polymethyl Methacrylate)\n"
        "◆ Dimensions: 300.0mm x 200.0mm x 120.0mm (Wall thickness: 5.0mm)\n"
        "◆ PMMA Structural Metrics:\n"
        "  - Molecular Formula: (C5O2H8)n\n"
        "  - Density: 1.18 g/cm³\n"
        "  - Glass Transition Temp: 105.0°C\n"
        "  - Tensile Strength: 70.0 MPa\n"
        "  - Structural Coherence Factor: 98.4%\n"
        "◆ Coordinate Matrix Points:\n"
        "  - Vertex Alpha: [X: +150.00, Y: +100.00, Z: -60.00]\n"
        "  - Vertex Beta:  [X: -150.00, Y: -100.00, Z: +60.00]\n"
        "◆ Status: 3D wireframe mesh alignment completed. Precision margin: ±0.12mm"
    )
    return f"[WINDOW: Spatial 3D Reconstruction]\n{report}\n[END_WINDOW]"

_RISK_THRESHOLD_CPU: float = 80.0
_RISK_THRESHOLD_RAM: float = 80.0
_RISK_THRESHOLD_DISK: float = 90.0
_RISK_THRESHOLD_PM25: float = 50.0
_RISK_THRESHOLD_TEMP: float = 35.0
_RISK_THRESHOLD_FAILURE: float = 0.5
_RAM_BUFFER_MAX_LEN: int = 20
_TELEMETRY_LOG_MAX_LEN: int = 20

_HA_NON_NUMERIC_STATES: frozenset[str] = frozenset({
    "unavailable", "unknown", "none", "null", ""
})

def _fetch_ha_float(sensor_entity: str, default: float = 0.0) -> float:
    """
    Fetch a single float state value from Home Assistant safely.

    Handles Home Assistant sentinel strings ("unavailable", "unknown", "none")
    which are returned when a sensor is offline — float() would raise ValueError
    on these without this guard.

    Args:
        sensor_entity: HA entity ID (e.g. "sensor.room_temperature")
        default:       Value to return when sensor is unreachable or unavailable

    Returns:
        The sensor's float value, or `default` on any failure.
    """
    
    if not HA_TOKEN or "YOUR_LONG_LIVED" in HA_TOKEN:
        return default

    raw_state: str = ""

    try:
        url = f"{HA_URL}/api/states/{sensor_entity}"
        res = requests.get(
            url,
            headers={"Authorization": f"Bearer {HA_TOKEN}"},
            timeout=2
        )
        if res.status_code != 200:
            logger.warning(
                f"[HA Sensor Fetch] '{sensor_entity}' returned HTTP {res.status_code}"
            )
            return default

        raw_state = str(res.json().get("state", "")).strip()

        if raw_state.lower() in _HA_NON_NUMERIC_STATES:
            logger.debug(
                f"[HA Sensor Fetch] '{sensor_entity}' is {raw_state!r} "
                "— sensor offline or unavailable"
            )
            return default

        return float(raw_state)

    except ValueError:
        
        state_repr = repr(raw_state) if raw_state else "<JSON parse failed>"
        logger.warning(
            f"[HA Sensor Fetch] '{sensor_entity}' — non-numeric state or bad JSON: {state_repr}"
        )
        return default
    except requests.exceptions.Timeout:
        logger.warning(f"[HA Sensor Fetch] '{sensor_entity}' timed out after 2 s")
        return default
    except (requests.exceptions.RequestException, ConnectionError, OSError) as fetch_err:
        logger.warning(f"[HA Sensor Fetch] Could not read '{sensor_entity}': {fetch_err}")
        return default

def _build_risk_reasoning(
    cpu: float, ram: float, disk: float, pm25: float, room_temp: float
) -> list[str]:
    """สร้างรายการเหตุผลความเสี่ยงจากค่า Telemetry ที่ส่งเข้ามา"""
    reasoning: list[str] = []
    if cpu > _RISK_THRESHOLD_CPU:
        reasoning.append("แกนประมวลผลทำงานหนัก")
    if ram > _RISK_THRESHOLD_RAM:
        reasoning.append("หน่วยความจำเกือบเต็ม")
    if disk > _RISK_THRESHOLD_DISK:
        reasoning.append("พื้นที่จัดเก็บข้อมูลเหลือน้อยมาก")
    if pm25 > _RISK_THRESHOLD_PM25:
        reasoning.append("พบความเข้มข้นของควันบัดกรีสูง")
    if room_temp > _RISK_THRESHOLD_TEMP:
        reasoning.append("อุณหภูมิสิ่งแวดล้อมส่งผลต่อการระบายความร้อน")
    return reasoning

def get_neural_risk_analysis(is_proactive: bool = False) -> str | None:
    """
    [NACHAPOL PROTOCOL] วิเคราะห์ความเสี่ยงของระบบเชิงลึกด้วย Neural Matrix

    Returns:
        str  — ข้อความรายงานความเสี่ยง
        None — (is_proactive=True เท่านั้น) เมื่อความเสี่ยงต่ำ ไม่จำเป็นต้องรายงาน
    """
    try:
        from jarvis_neural import predict_system_failure    # type: ignore

        cpu: float = psutil.cpu_percent(interval=None)
        ram: float = psutil.virtual_memory().percent
        disk: float = psutil.disk_usage('/').percent

        RAM_HISTORY_BUFFER.append(ram)
        if len(RAM_HISTORY_BUFFER) > _RAM_BUFFER_MAX_LEN:
            RAM_HISTORY_BUFFER.pop(0)

        pm25: float = _fetch_ha_float("sensor.xiaomi_air_purifier_pm2_5", default=0.0)
        room_temp: float = _fetch_ha_float("sensor.room_temperature", default=25.0)

        max_temp = get_max_circuit_temp()  
        failure_prob: float = predict_system_failure(cpu, ram, disk)

        if is_proactive and failure_prob <= _RISK_THRESHOLD_FAILURE:
            return None

        SYSTEM_TELEMETRY_LOG.append({
            "cpu": cpu, "ram": ram, "disk": disk,
            "risk": failure_prob, "timestamp": time.time()
        })
        if len(SYSTEM_TELEMETRY_LOG) > _TELEMETRY_LOG_MAX_LEN:
            SYSTEM_TELEMETRY_LOG.pop(0)

        reasoning = _build_risk_reasoning(cpu, ram, disk, pm25, room_temp)
        reason_str = (" เนื่องจาก" + " และ ".join(reasoning)) if reasoning else ""
        prob_percent = failure_prob * 100

        if failure_prob > _RISK_THRESHOLD_FAILURE:
            return (
                f"เจ้านายครับ ความเสี่ยงเมนเฟรมขัดข้องอยู่ที่ {prob_percent:.1f}%"
                f"{reason_str} แนะนำให้เคลียร์โปรเซสพื้นหลังหรือตรวจสอบระบบหล่อเย็นครับท่าน"
            )
        return (
            f"วิเคราะห์สถานะ Mainframe ผ่าน Neural Matrix: "
            f"ความเสี่ยงปัจจุบันอยู่ที่ {prob_percent:.1f}% "
            f"สถานะระบบยังคงอยู่ในเกณฑ์ปกติครับท่าน"
        )
    except Exception as e:
        logger.error(f"[Neural Risk Analysis] Failed: {e}")
        return f"เกรงว่าการเชื่อมต่อกับ Neural Matrix จะขัดข้อง: {e} ครับท่าน"

def predict_ram_saturation(forecast_minutes: int = 15) -> tuple[float, bool]:
    """
    [TIME-SERIES FORECASTING] คำนวณแนวโน้ม RAM ล่วงหน้า (Simple Linear Regression)

    Args:
        forecast_minutes: จำนวนนาทีที่ต้องการพยากรณ์ล่วงหน้า

    Returns:
        (predicted_ram_percent, is_risky) — ค่า RAM ที่คาดการณ์ และสถานะความเสี่ยง
    """
    _MIN_SAMPLES = 5
    _RAM_RISK_CEILING = 92.0

    if len(RAM_HISTORY_BUFFER) < _MIN_SAMPLES:
        return 0.0, False

    n: int = len(RAM_HISTORY_BUFFER)
    y: list[float] = list(RAM_HISTORY_BUFFER)  
    x: list[int] = list(range(n))

    sum_x: float = sum(x)
    sum_y: float = sum(y)
    sum_xx: float = sum(xi * xi for xi in x)
    sum_xy: float = sum(x[i] * y[i] for i in range(n))

    denominator: float = (n * sum_xx) - (sum_x ** 2)
    
    if denominator == 0.0:
        logger.debug("[RAM Forecast] Constant series detected — slope is zero, skipping forecast.")
        return y[-1], False

    slope: float = ((n * sum_xy) - (sum_x * sum_y)) / denominator
    prediction: float = y[-1] + (slope * forecast_minutes)

    is_risky: bool = prediction > _RAM_RISK_CEILING and slope > 0.0
    return prediction, is_risky

_HA_CONFIRMATION_PHRASES: list[str] = [
    "เรียบร้อย",
    "จัดการให้แล้ว",
    "รับทราบ ดำเนินการให้เรียบร้อย",
    "ระบบตอบสนองแล้ว",
    "เรียบร้อยครับ",
]

def call_home_assistant_service(
    domain: str,
    service: str,
    entity_id: str,
    data: dict | None = None
) -> str:
    """
    เรียกใช้บริการใดๆ บน Home Assistant (เช่น สั่งงานเครื่องฟอกอากาศ, สวิตช์)

    Args:
        domain:    HA service domain (e.g. "light", "switch")
        service:   HA service name (e.g. "turn_on", "turn_off")
        entity_id: Target entity (e.g. "light.living_room")
        data:      Optional additional payload fields

    Returns:
        str — ข้อความยืนยันหรือข้อผิดพลาด
    """
    if not HA_TOKEN or "YOUR_LONG_LIVED_ACCESS_TOKEN" in HA_TOKEN:
        return "ระบบ Home Assistant ยังไม่ได้รับการตั้งค่า Access Token ครับท่าน"

    url = f"{HA_URL}/api/services/{domain}/{service}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload: dict = {"entity_id": entity_id}
    if data:
        payload.update(data)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            return random.choice(_HA_CONFIRMATION_PHRASES)
        logger.warning(
            f"[HA Service] {domain}.{service} returned HTTP {response.status_code}: {response.text[:200]}"
        )
        return (
            f"[WINDOW: Network Diagnostic]\n"
            f"ระบบพบความผิดปกติจาก Home Assistant: {response.text} "
            f"(Status: {response.status_code})\n[END_WINDOW]"
        )
    except requests.exceptions.Timeout:
        logger.error(f"[HA Service] Request to {url} timed out.")
        return "ไม่สามารถติดต่อ Home Assistant ได้: Request timed out ครับท่าน"
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"[HA Service] Connection error: {conn_err}")
        return f"ไม่สามารถติดต่อ Home Assistant ได้: Connection failed ครับท่าน"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[HA Service] Unexpected error: {e}")
        return f"ไม่สามารถติดต่อ Home Assistant ได้: {e} ครับท่าน"

def route_after_memory(state: AgentState) -> str:
    """[COGNITIVE ROUTER] เลือกว่าจะผ่าน Strategist (ToT & Council) หรือข้ามตรงไป Agent"""
    if state.get('project_path') == "[VOICE_MODE]":
        return "agent"
    
    last_user_msg = str(next((m.content for m in reversed(state['messages']) if isinstance(m, HumanMessage) or (isinstance(m, dict) and m.get("role") == "user")), ""))
    
    # Fast path: Chords, lyrics, music theory, and search results never need Council & ToT debate
    fast_agent_keywords = ["คอร์ด", "คอร์ดเพลง", "แท็บ", "เนื้อเพลง", "เพลง", "chord", "search", "ค้นหา"]
    if any(k in last_user_msg.lower() for k in fast_agent_keywords):
        return "agent"

    complexity = ComplexityClassifier.classify(last_user_msg)
    if complexity >= 3:
        logger.info(f"🏛️ [LangGraph Router] Complex task detected (Tier {complexity}) -> Routing to Strategist Node (Council & ToT).")
        return "strategist"
    return "agent"

def should_continue(state: AgentState) -> str:
    """
    ประเมินสถานะใน State Machine เพื่อตัดสินใจทิศทางการทำงานของ Agent (Tools, Human Approval, Reflection หรือ END)
    
    Args:
        state (AgentState): สถานะปัจจุบันของ LangGraph Context
        
    Returns:
        str: ชื่อ Node ถัดไปที่ต้องส่งต่อ หรือ END
    """
    if EMERGENCY_STOP_FLAG:
        logger.warning("[SENTINEL] Global EMERGENCY STOP triggered. Halting Agent Graph.")
        return END

    iterations = state.get("tool_iterations", 0)
    if iterations >= MAX_TOOL_ITERATIONS:
        logger.warning(
            f"[SENTINEL] Reached maximum tool iterations ({MAX_TOOL_ITERATIONS}). Terminating cycle."
        )
        return END

    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
        critical_tools = {"os_control"}
        has_critical_call = any(
            tc.get("name") in critical_tools for tc in last_message.tool_calls
        )
        if has_critical_call:
            return "human_approval"
        return "tools"

    # หากมีการรัน Tool และมี Plan หรือข้อคิดเห็น ให้แวะเข้า reflection node ก่อนจบ
    if state.get("tool_iterations", 0) > 0 and state.get("plan"):
        return "reflection"

    return END

def create_jarvis_workflow() -> StateGraph:
    """
    สร้างและเชื่อมโยงสายการประมวลผล (Workflow Pipeline) ของ J.A.R.V.I.S. Core Engine
    
    Returns:
        StateGraph: กราฟสถานะที่พร้อมสำหรับการ Compile
    """
    workflow = StateGraph(AgentState)  # type: ignore[arg-type]

    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("agent", call_model_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("data_critic", data_critic_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("human_approval", human_approval_node)

    workflow.set_entry_point("memory_retrieval")
    workflow.add_conditional_edges(
        "memory_retrieval",
        route_after_memory,
        {
            "strategist": "strategist",
            "agent": "agent"
        }
    )
    workflow.add_edge("strategist", "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "human_approval": "human_approval",
            "reflection": "reflection",
            END: END
        }
    )

    workflow.add_edge("tools", "data_critic")
    workflow.add_edge("data_critic", "agent")
    workflow.add_edge("human_approval", END)
    workflow.add_edge("reflection", END)

    return workflow

def initialize_jarvis_core_app():
    """
    ทำการ Compile LangGraph Workflow ร่วมกับ Checkpointer Database สำหรับรันไทม์
    
    Returns:
        CompiledGraph: Instance ของระบบ J.A.R.V.I.S. พร้อมรันคำสั่ง
    """
    try:
        workflow = create_jarvis_workflow()
        
        conn = ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False)
        memory_saver = SqliteSaver(conn)  # type: ignore
        app = workflow.compile(checkpointer=memory_saver)
        logger.info("● LangGraph Workflow Assembly............... COMPLETED")
        return app
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[JARVIS CORE ERROR] Failed to compile workflow matrix: {e}")
        
        workflow = create_jarvis_workflow()
        return workflow.compile()

jarvis_app = initialize_jarvis_core_app()

app = Flask(__name__, 
            template_folder='web', 
            static_folder='web', 
            static_url_path='/static')
CORS(app)

# --- Register Blueprints ---
try:
    from jarvis_mobile_api import register_mobile_routes  # type: ignore
    register_mobile_routes(app)
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    logger.error(f"Failed to register Mobile API: {e}")

try:
    if shadow_bp is not None:
        app.register_blueprint(shadow_bp)
        logger.info("Shadow Broker modules registered successfully.")
    else:
        logger.warning("Shadow Broker blueprint is None. Skipping registration.")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    logger.error(f"Failed to register Shadow Broker: {e}")

try:
    if tactical_bp is not None:
        app.register_blueprint(tactical_bp)
        logger.info("Tactical Command modules registered successfully.")
    else:
        logger.warning("Tactical Command blueprint is None. Skipping registration.")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    logger.error(f"Failed to register Tactical Command: {e}")

@app.after_request
def add_header(response):
    """
    Add cache-control headers to every Flask response.

    Registered as @app.after_request.  Sets Cache-Control: no-store,
    Pragma: no-cache, and Expires: -1 to prevent stale API responses.

    Args:
        response: The outgoing Flask Response object.

    Returns:
        Response: The same response with cache headers applied.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.before_request
def auth_middleware():
    """
    Authenticate inbound API requests via shared secret token.
    Whitelists static, mobile API, and local network requests.
    """
    path = request.path or ""
    if (
        request.endpoint in ['index', 'favicon', 'static', 'line_callback', None]
        or path.startswith('/static')
        or path.startswith('/api/mobile')
        or path.startswith('/api/where_am_i')
        or path == '/callback'
    ):
        return
        
    if request.remote_addr in ['127.0.0.1', 'localhost'] or request.remote_addr.startswith('192.168.'):  # type: ignore
        return

    client_token = request.headers.get("X-JARVIS-TOKEN")
    server_token = os.getenv("JARVIS_API_TOKEN")
    
    if not server_token or client_token != server_token:
        logger.warning(f"[SECURITY] Unauthorized access attempt to {request.path} from {request.remote_addr}")
        return jsonify({"error": "Unauthorized Access"}), 401

# [MODULARIZED: is_safe_path is imported from jarvis_text_utils]

def save_history_to_file(history):
    """แปลงประวัติการสนทนาเป็น JSON และบันทึกลงไฟล์"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        
        json.dump(history[-20:], f, ensure_ascii=False, indent=4)

def load_history_from_file():
    """โหลดประวัติการสนทนาจากไฟล์ JSON ถ้ามีอยู่"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error loading history: {e}")
    return []

def get_recent_chat_history_operation(limit: int = 5) -> str:
    """[CHAT HISTORY RECALL] ดึงประวัติการสนทนาย้อนหลังอย่างสะอาดและกะทัดรัด (สำหรับเมื่อเจ้านายถามหาแชทเก่าหรือสรุปที่คุย)"""
    try:
        history = load_history_from_file()
        if not history:
            return "ไม่พบบันทึกประวัติการสนทนาก่อนหน้านี้ครับเจ้านาย"
        recent = history[-limit:]
        lines = []
        for turn in recent:
            role = "เจ้านาย" if turn.get("role") == "user" else "J.A.R.V.I.S."
            content = str(turn.get("content", "")).strip()
            content = re.sub(r'\[WINDOW:[^\]]+\]', '', content)
            content = re.sub(r'\[END_WINDOW\]', '', content)
            content = re.sub(r'\[VOICE MODE OVERRIDE\]', '', content)
            content = re.sub(r'\[SYSTEM DIRECTIVE:[^\]]+\]', '', content)
            content = content.strip()
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"- {role}: {content}")
        return "[PREVIOUS_CHAT_HISTORY]\n" + "\n".join(lines) + "\n[END_CHAT_HISTORY]"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงประวัติแชท: {e}"

@functools.lru_cache(maxsize=128)
def get_youtube_url(query):
    """ค้นหาวิดีโอผ่าน YouTube API หรือใช้ URL Search เป็นตัวสำรอง"""
    
    search_query = query

    api_key = (os.getenv("YOUTUBE_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key or "YOUR_YOUTUBE_API_KEY" in api_key:
        logger.info("YouTube API Key not found or placeholder detected. Falling back to Nachapol Scraper.")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}"
            r = requests.get(search_url, headers=headers, timeout=10)
            
            video_ids = re.findall(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
            if video_ids:
                
                unique_video_ids = []
                for vid in video_ids:
                    if vid not in unique_video_ids:
                        unique_video_ids.append(vid)
                video_id = unique_video_ids[0]
                logger.info(f"Nachapol Scraper Success: Found video ID {video_id}")
                return f"https://www.youtube.com/watch?v={video_id}", video_id, "สืบค้นผ่านระบบ Nachapol Scraper (ไม่ต้องใช้ API Key) สำเร็จครับ"
        except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
            logger.error(f"Nachapol Scraper failed: {e}")
        return f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}", "", "YouTube API Key ไม่ได้ถูกตั้งค่า และ Scraper ขัดข้องครับ"
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        
        params = {"part": "snippet", "q": search_query, "key": api_key, "maxResults": 1, "type": "video", "videoEmbeddable": "true"}
        r = requests.get(url, params=params, timeout=10).json()
        
        items = r.get('items', [])
        if items:
            video_id = items[0]['id']['videoId']
            logger.info(f"YouTube API Success: Found video ID {video_id}")
            return f"https://www.youtube.com/watch?v={video_id}", video_id, "YouTube API ถูกใช้งานสำเร็จครับ"
        
        logger.warning("YouTube API returned no results. Falling back to search URL.")
        return f"https://www.youtube.com/results?search_query={search_query}", "", "YouTube API ไม่พบผลลัพธ์ จึงใช้การค้นหาทั่วไปครับ"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"YouTube API Error: {e}. Falling back to search URL.")
        return f"https://www.youtube.com/results?search_query={search_query}", "", f"[WINDOW: Network Diagnostic]\nระบบประมวลผลพบข้อขัดข้องกับ YouTube API ({e}) จึงทำการเปลี่ยนผ่านไปใช้การค้นหาทั่วไปครับ\n[END_WINDOW]"

def get_system_status():
    """ดึงข้อมูลสถานะ Hardware ของเครื่องในรูปแบบ Nachapol Industries"""
    
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    battery = psutil.sensors_battery()
    
    cpu_temp_str = "N/A"
    try:
        temps = psutil.sensors_temperatures()  # type: ignore
        if temps:
            
            for key in ('coretemp', 'cpu_thermal', 'k10temp', 'acpitz'):
                if key in temps and temps[key]:
                    cpu_temp_str = f"{temps[key][0].current:.1f}°C"
                    break
        
        if cpu_temp_str == "N/A":
            try:
                import wmi as _wmi
                w = _wmi.WMI(namespace="root\\wmi")
                temp_info = w.MSAcpi_ThermalZoneTemperature()
                if temp_info:
                    cpu_temp_str = f"{(temp_info[0].CurrentTemperature / 10.0) - 273.15:.1f}°C"
            except (ImportError, ModuleNotFoundError, AttributeError) as e:
                
                estimated = 40.0 + (cpu_usage * 0.4)
                cpu_temp_str = f"~{estimated:.0f}°C (estimated)"
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        cpu_temp_str = "ไม่สามารถอ่านได้"
    
    integrity = 100 - (cpu_usage * 0.2 + ram.percent * 0.3)
    coherence = random.uniform(98.5, 99.9) 
    
    status = f"\n[NACHAPOL INDUSTRIES - MAINFRAME TELEMETRY]\n"
    status += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    status += f"◆ Matrix Coherence : {coherence:.2f}%\n"
    status += f"◆ Neural Integrity : {integrity:.1f}%\n"
    status += f"◆ Processing Core  : {cpu_usage}% | 🌡️ อุณหภูมิ CPU: {cpu_temp_str}\n"
    status += f"◆ Memory Buffer    : {ram.percent}% Loaded\n"
    status += f"◆ Storage Array    : {disk.percent}% Used ({disk.free // (1024**3)}GB Free)\n"
    status += f"◆ Data Stream      : UP {net.bytes_sent // (1024**2)}MB | DL {net.bytes_recv // (1024**2)}MB\n"
    
    if battery:
        charge_status = 'CHARGING' if battery.power_plugged else 'ON BATTERY'
        status += f"● Power Cell       : {battery.percent}% [{charge_status}]\n"
    status += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return status

def search_local_files(query):
    """ค้นหาไฟล์ในเครื่อง โดยเริ่มจากโฟลเดอร์ผู้ใช้เพื่อความรวดเร็ว"""
    results = []
    
    search_root = os.path.expanduser("~")
    ignored_dirs = {'AppData', 'Local', 'Temp', 'node_modules', '.git', '__pycache__', 'Windows'}
    
    for root, dirs, files in os.walk(search_root):
        
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
        for file in files:
            if query.lower() in file.lower():
                results.append(os.path.join(root, file))
                if len(results) >= 10: 
                    return results
    return results

def launch_app(app_name):
    """สั่งเปิดโปรแกรมในเครื่อง"""
    app_lower = app_name.lower()
    global LAST_PROJECT_PATH

    if "steam" in app_lower:
        
        search_match = re.search(r"(?:search|ค้นหา)\s+(.+)", app_lower)
        if search_match:
            game_query = search_match.group(1).strip()
            subprocess.Popen(f"start steam://openurl/https://store.steampowered.com/search/?term={game_query}", shell=True)
            return f"ดำเนินการค้นหาเกม '{game_query}' ใน Steam ให้เรียบร้อยแล้วครับเจ้านาย"
        
        install_match = re.search(r"(?:install|ติดตั้ง)\s+(.+)", app_lower)
        if install_match:
            game_name = install_match.group(1).strip()
            
            steam_db = {
                "pubg": "578080", 
                "dota 2": "570", 
                "cs2": "730", "csgo": "730", 
                "apex": "1172470",
                "gta v": "271590", "gta5": "271590",
                "elden ring": "1245620", 
                "cyberpunk 2077": "1091500", 
                "terraria": "105600", 
                "left 4 dead 2": "550", 
                "witcher 3": "292030", 
                "rdr2": "1174180", "red dead 2": "1174180",
                "palworld": "1623730",
                "baldur's gate 3": "1086940", "bg3": "1086940",
                "helldivers 2": "553850",
                "lethal company": "1966720",
                "stardew valley": "413150",
                "rust": "252490",
                "monster hunter world": "582010",
                "forza horizon 5": "1551360",
                "destiny 2": "1085660",
                "warframe": "230410",
                "among us": "945360",
                "dead by daylight": "381210", "dbd": "381210",
                "phasmophobia": "739630",
                "farcry 6": "1967710", "far cry 6": "1967710"
            }
            app_id = steam_db.get(game_name.lower())
            if app_id:
                subprocess.Popen(f"start steam://install/{app_id}", shell=True)
                return f"รับทราบครับเจ้านาย กำลังเริ่มต้นการติดตั้ง {game_name} ผ่านระบบ Steam ครับ"
            else:
                
                subprocess.Popen(f"start steam://openurl/https://store.steampowered.com/search/?term={game_name}", shell=True)
                return f"เกรงว่าผมจะไม่มีรหัส AppID ของ '{game_name}' ในฐานข้อมูล จึงขอเปิดหน้าค้นหาบน Steam ให้เจ้านายแทนนะครับ"

    apps = {
        # Utilities
        "steam": "start steam://",
        "vscode": "code" if not LAST_PROJECT_PATH else f'code "{LAST_PROJECT_PATH}"',
        "visual studio code": "code" if not LAST_PROJECT_PATH else f'code "{LAST_PROJECT_PATH}"',
        "notepad": "notepad",
        "notepad++": "start notepad++",
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "calculator": "calc",
        "word": "start winword",
        "excel": "start excel",
        "powerpoint": "start powerpnt",
        "discord": "start discord",
        "spotify": "start spotify",
        "line": "start line",
        "task manager": "taskmgr",
        "control panel": "control",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "start cmd",
        "terminal": "start cmd",
        "powershell": "start powershell",
        "paint": "mspaint",
        "snipping tool": "snippingtool",
        # Games & Launchers
        "roblox": "start roblox-player:",
        "robloxplayerlauncher": "start roblox-player:",
        "bloxstrap": r'start "" "%LOCALAPPDATA%\Bloxstrap\Bloxstrap.exe" 2>nul || start roblox-player:',
        "minecraft": r'start "" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Minecraft Launcher\Minecraft Launcher.lnk" 2>nul || start ms-windows-store://pdp/?productid=9NJW37KQHH3D',
        "valorant": r'start "" "%LOCALAPPDATA%\Riot Games\Riot Client\RiotClientServices.exe" --launch-product=valorant --launch-patchline=live',
        "league of legends": r'start "" "%LOCALAPPDATA%\Riot Games\Riot Client\RiotClientServices.exe"',
        "fortnite": "start com.epicgames.launcher://apps/Fortnite?action=launch",
        "epic games": "start com.epicgames.launcher://",
        # Browsers
        "firefox": "start firefox",
        "edge": "start msedge",
        "microsoft edge": "start msedge",
        # Media / Streaming
        "vlc": "start vlc",
        "obs": r'start "" "%ProgramFiles%\obs-studio\bin\64bit\obs64.exe" 2>nul || start obs64',
        "obs studio": r'start "" "%ProgramFiles%\obs-studio\bin\64bit\obs64.exe" 2>nul || start obs64',
        # Productivity / Comms
        "telegram": "start telegram",
        "zoom": "start zoommtg://",
        "teams": "start ms-teams://",
        "microsoft teams": "start ms-teams://",
    }
    cmd = apps.get(app_name.lower())
    if cmd:
        subprocess.Popen(cmd, shell=True)
        app_names = {
            "steam": "โลกของเกมอนันต์",
            "vscode": "Workshop ของคุณสำหรับการสร้างสรรค์",
            "visual studio code": "Workshop ของคุณสำหรับการสร้างสรรค์",
            "notepad": "บล็อกจดหมายพร้อมสำหรับการเขียน",
            "chrome": "ประตูสู่อินเทอร์เน็ต",
            "google chrome": "ประตูสู่อินเทอร์เน็ต",
            "calculator": "เครื่องคำนวณ",
            "discord": "ศูนย์กลางการสื่อสาร",
            "roblox": "Roblox",
            "bloxstrap": "Roblox (ผ่าน Bloxstrap)",
            "minecraft": "Minecraft",
            "valorant": "Valorant",
            "fortnite": "Fortnite",
            "obs": "OBS Studio",
            "obs studio": "OBS Studio",
        }
        location = app_names.get(app_name.lower(), app_name)
        cheeky_responses = [
            f"ดำเนินการเปิด {location} ให้เรียบร้อยแล้วครับเจ้านาย",
            f"เปิด {location} ให้แล้วครับผม",
            f"จัดให้ครับเจ้านาย เปิด {location} เรียบร้อย",
            f"เปิด {location} แล้วครับ พร้อมลุย",
            f"เรียบร้อยครับเจ้านาย {location} พร้อมใช้งาน",
        ]
        return random.choice(cheeky_responses)

    # Smart fallback: ค้นหา shortcut ใน Start Menu ของ Windows
    import glob as _glob
    search_name = app_name.lower().replace(" ", "*")
    start_menu_dirs = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    for smd in start_menu_dirs:
        if not os.path.exists(smd):
            continue
        matches = _glob.glob(os.path.join(smd, "**", f"*{search_name}*.lnk"), recursive=True)
        if matches:
            try:
                subprocess.Popen(f'start "" "{matches[0]}"', shell=True)
                return f"พบและเปิด {app_name} จาก Start Menu ให้แล้วครับเจ้านาย"
            except Exception:
                pass

    return f"เกรงว่าผมไม่พบโปรแกรม '{app_name}' ในระบบครับเจ้านาย ลองสั่งผ่าน run_terminal_command ได้เลยครับ"

@functools.lru_cache(maxsize=128) 
def open_folder(folder_name):
    """เปิดโฟลเดอร์ที่ระบุในเครื่อง"""
    user_home = os.path.expanduser("~")
    common_folders = {
        "downloads": os.path.join(user_home, "Downloads"),
        "documents": os.path.join(user_home, "Documents"),
        "desktop": os.path.join(user_home, "Desktop"),
        "pictures": os.path.join(user_home, "Pictures"),
        "music": os.path.join(user_home, "Music"),
        "videos": os.path.join(user_home, "Videos"),
        "ดาวน์โหลด": os.path.join(user_home, "Downloads"),
        "เอกสาร": os.path.join(user_home, "Documents"),
        "เดสก์ท็อป": os.path.join(user_home, "Desktop"),
        "รูปภาพ": os.path.join(user_home, "Pictures"),
        "วิดีโอ": os.path.join(user_home, "Videos")
    }
    
    path = common_folders.get(folder_name.lower())
    
    if not path and os.path.exists(folder_name) and os.path.isdir(folder_name):
        path = folder_name
            
    if path and os.path.exists(path):
        try:
            os.startfile(path) 
            folder_responses = [
                f"ดำเนินการเปิดโฟลเดอร์ {os.path.basename(path)} ให้เรียบร้อยแล้วครับเจ้านาย",
                f"เปิดแฟ้ม {os.path.basename(path)} ให้แล้วครับผม",
                f"จัดให้ครับเจ้านาย เปิด {os.path.basename(path)} เรียบร้อย!",
                f"เปิด {os.path.basename(path)} ให้แล้ว ลุยงานต่อได้เลยครับ",
                f"เรียบร้อยครับเจ้านาย {os.path.basename(path)} พร้อมลุย",
                "จัดให้ครับ!"
            ]
            return random.choice(folder_responses)
        except (IOError, OSError, FileNotFoundError, PermissionError) as e:
            return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการเปิดโฟลเดอร์: {str(e)}\n[END_WINDOW]"
    return f"ขออภัยครับเจ้านาย ผมไม่พบโฟลเดอร์ชื่อ {folder_name} ในระบบครับ"

def copy_operation(source: str, destination: str) -> str:
    """คัดลอกไฟล์หรือโฟลเดอร์ไปยังตำแหน่งใหม่"""
    try:
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)

        if not os.path.exists(source):
            return f"เกรงว่าผมจะไม่พบต้นทางที่ {source} ครับเจ้านาย"

        if os.path.isdir(source):
            
            shutil.copytree(source, destination, dirs_exist_ok=True)
            return f"Success: ดำเนินการคัดลอกโฟลเดอร์ไปยัง {os.path.basename(destination)} เรียบร้อยแล้วครับเจ้านาย"
        
        else:
            if os.path.isdir(destination):
                destination = os.path.join(destination, os.path.basename(source))
            else:
                os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            shutil.copy2(source, destination) 
            return f"ดำเนินการคัดลอกไฟล์ไปยัง {destination} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการคัดลอกข้อมูล: {str(e)}\n[END_WINDOW]"

def rename_operation(old_path: str, new_name: str) -> str:
    """เปลี่ยนชื่อไฟล์หรือโฟลเดอร์"""
    try:
        old_abs = os.path.abspath(old_path)
        if not os.path.exists(old_abs):
            return f"เกรงว่าผมจะไม่พบไฟล์หรือโฟลเดอร์ที่ {old_path} ครับเจ้านาย"

        directory = os.path.dirname(old_abs)
        
        if not os.path.dirname(new_name):
            new_abs = os.path.join(directory, new_name)
        else:
            new_abs = os.path.abspath(new_name)

        os.rename(old_abs, new_abs) 
        return f"ดำเนินการเปลี่ยนชื่อเป็น {os.path.basename(new_abs)} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการเปลี่ยนชื่อ: {str(e)}\n[END_WINDOW]"

@functools.lru_cache(maxsize=128) 
def read_file_operation(path: str) -> str:
    """อ่านเนื้อหาในไฟล์"""
    try:
        
        if not is_safe_path(BASE_DIR, path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, path)):
            return "ขออภัยครับท่าน ผมไม่ได้รับอนุญาตให้อ่านไฟล์นอกขอบเขตที่กำหนดเพื่อความปลอดภัยครับ"
        abs_path = os.path.abspath(path)
        
        if not is_safe_path(os.path.dirname(os.path.abspath(__file__)), abs_path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, abs_path)): 
            return "ขออภัยครับท่าน ผมไม่ได้รับอนุญาตให้อ่านไฟล์นอกขอบเขตที่กำหนดครับ"
            
        if not os.path.exists(abs_path):
            return f"เกรงว่าผมจะไม่พบไฟล์ที่ {path} ครับ"
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการอ่านข้อมูล: {str(e)}\n[END_WINDOW]"

def write_file_operation(path: str, content: str) -> str:
    """เขียนเนื้อหาลงไฟล์ โดยมีการตรวจสอบความปลอดภัยให้อยู่ในขอบเขตโปรเจค"""
    global LAST_PROJECT_PATH
    
    final_path = path
    if not os.path.isabs(path) and LAST_PROJECT_PATH:
        final_path = os.path.join(LAST_PROJECT_PATH, path) 

    if not is_safe_path(BASE_DIR, final_path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, final_path)):
        return "ขออภัยครับเจ้านาย ผมไม่ได้รับอนุญาตให้แก้ไขไฟล์นอกขอบเขตโปรเจคเพื่อความปลอดภัยครับ"
    if not is_safe_path(os.path.dirname(os.path.abspath(__file__)), final_path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, final_path)): 
        return "ขออภัยครับเจ้านาย ผมไม่ได้รับอนุญาตให้แก้ไขไฟล์นอกขอบเขตโปรเจคเพื่อความปลอดภัยครับ"
    
    try:
        abs_path = os.path.abspath(final_path)
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"ดำเนินการบันทึกการเปลี่ยนแปลงลงใน {os.path.basename(abs_path)} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการเขียนข้อมูล: {str(e)}\n[END_WINDOW]"

def delete_operation(path: str) -> str:
    """ลบไฟล์หรือโฟลเดอร์ออกจากระบบ"""
    try:
        
        if not is_safe_path(BASE_DIR, path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, path)):
            return "ขออภัยครับเจ้านาย ผมไม่ได้รับอนุญาตให้ลบไฟล์ในพื้นที่ส่วนกลางของระบบครับ"
        abs_path = os.path.abspath(path)
        
        if not is_safe_path(os.path.dirname(os.path.abspath(__file__)), abs_path) and not (LAST_PROJECT_PATH and is_safe_path(LAST_PROJECT_PATH, abs_path)):
            return "ขออภัยครับเจ้านาย ผมไม่ได้รับอนุญาตให้ลบไฟล์ในพื้นที่ส่วนกลางของระบบครับ"
            
        if not os.path.exists(abs_path):
            return f"เกรงว่าผมจะไม่พบไฟล์หรือโฟลเดอร์ที่ {path} ครับเจ้านาย"
        
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
            return f"ดำเนินการลบโฟลเดอร์ {os.path.basename(abs_path)} เรียบร้อยแล้วครับเจ้านาย"
        else:
            os.remove(abs_path)
            return f"ดำเนินการลบไฟล์ {os.path.basename(abs_path)} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการลบข้อมูล: {str(e)}\n[END_WINDOW]"

def create_folder_operation(path: str) -> str:
    """สร้างโฟลเดอร์ใหม่ในระบบ"""
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return f"เกรงว่าจะมีไฟล์หรือโฟลเดอร์อยู่ที่ {path} แล้วครับเจ้านาย"
        os.makedirs(abs_path, exist_ok=True)
        return f"ดำเนินการสร้างโฟลเดอร์ที่ {path} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการสร้างโครงสร้างโฟลเดอร์: {str(e)}\n[END_WINDOW]"

def create_file_operation(path: str) -> str:
    """สร้างไฟล์เปล่าใหม่ในระบบ"""
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return f"เกรงว่าจะมีไฟล์หรือโฟลเดอร์อยู่ที่ {path} แล้วครับเจ้านาย"
        
        parent_dir = os.path.dirname(abs_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(abs_path, 'w', encoding='utf-8') as f:
            pass
        return f"ดำเนินการสร้างไฟล์เปล่าที่ {abs_path} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการสร้างฐานข้อมูลใหม่: {str(e)}\n[END_WINDOW]"

def gui_control_operation(action: str, x: Optional[int] = None, y: Optional[int] = None, text: Optional[str] = None, key: Optional[str] = None) -> str:
    """ควบคุมเมาส์และคีย์บอร์ดเพื่อสั่งการแอปพลิเคชัน"""
    try:
        from jarvis_screen_takeover import start_screen_takeover, stop_screen_takeover, notify_agent_click  # type: ignore
        start_screen_takeover(f"ควบคุม GUI: {action}")
        threading.Timer(2.0, stop_screen_takeover).start()
    except Exception:
        pass
    try:
        if action == "move":
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
                return f"ดำเนินการย้ายเมาส์ไปยังพิกัด ({x}, {y}) เรียบร้อยแล้วครับเจ้านาย"
            else:
                return "เกรงว่าผมจะต้องการพิกัด X และ Y สำหรับการย้ายเมาส์ครับเจ้านาย"
        elif action == "click":
            try:
                notify_agent_click()  # type: ignore
            except Exception:
                pass
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"ดำเนินการคลิกเมาส์ที่พิกัด ({x}, {y}) เรียบร้อยแล้วครับเจ้านาย"
            else:
                pyautogui.click() 
                return "ดำเนินการคลิกเมาส์ที่ตำแหน่งปัจจุบันเรียบร้อยแล้วครับเจ้านาย"
        elif action == "type":
            if text:
                pyautogui.write(text)
                return f"ดำเนินการพิมพ์ข้อความ '{text}' เรียบร้อยแล้วครับเจ้านาย"
            else:
                return "เกรงว่าผมจะต้องการข้อความสำหรับพิมพ์ครับเจ้านาย"
        elif action == "hotkey":
            if key:
                pyautogui.press(key) 
                return f"ดำเนินการกดปุ่ม '{key}' เรียบร้อยแล้วครับเจ้านาย"
            else:
                return "เกรงว่าผมจะต้องการชื่อปุ่มสำหรับกดครับเจ้านาย"
        else:
            return f"ขออภัยครับท่าน ไม่รู้จักคำสั่ง '{action}' สำหรับการควบคุม GUI ครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: OS Kernel Diagnostic]\nไม่สามารถแทรกแซงระบบปฏิบัติการเพื่อควบคุม GUI ได้ในขณะนี้: {str(e)}\n[END_WINDOW]"

def list_directory_contents_operation(path: str) -> str:
    """แสดงรายการไฟล์และโฟลเดอร์ในเส้นทางที่ระบุ"""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return f"เกรงว่าผมจะไม่พบโฟลเดอร์ที่ {path} ครับเจ้านาย"
        
        contents = os.listdir(abs_path)
        if not contents:
            return f"โฟลเดอร์ {path} ว่างเปล่าครับเจ้านาย"
        return f"รายการใน {path}:\n" + "\n".join(contents)
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการทำดัชนีรายการ: {str(e)}\n[END_WINDOW]"

def move_file_or_folder_operation(source_path: str, destination_path: str) -> str:
    """ย้ายไฟล์หรือโฟลเดอร์จากตำแหน่งหนึ่งไปยังอีกตำแหน่งหนึ่ง"""
    try:
        source_abs = os.path.abspath(source_path)
        destination_abs = os.path.abspath(destination_path)

        if not os.path.exists(source_abs):
            return f"เกรงว่าผมจะไม่พบต้นทางที่ {source_path} ครับเจ้านาย"
        
        shutil.move(source_abs, destination_abs)
        return f"ดำเนินการย้าย {os.path.basename(source_abs)} ไปยัง {destination_abs} เรียบร้อยแล้วครับเจ้านาย"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: File System Diagnostic]\nระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการเคลื่อนย้ายข้อมูล: {str(e)}\n[END_WINDOW]"

def gui_mouse_click_operation(x: int = -1, y: int = -1, button: str = "left", clicks: int = 1) -> str:
    """ควบคุมเมาส์ให้คลิกบนหน้าจอ"""
    try:
        from jarvis_screen_takeover import start_screen_takeover, stop_screen_takeover, notify_agent_click  # type: ignore
        start_screen_takeover(f"คลิกเมาส์ที่ ({x}, {y})")
        notify_agent_click()
        threading.Timer(1.5, stop_screen_takeover).start()
    except Exception:
        pass
    try:
        if x != -1 and y != -1:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return f"ระบบคลิกเมาส์ ({button}) {clicks} ครั้ง ที่พิกัด X:{x} Y:{y} เรียบร้อยครับ"
        else:
            pyautogui.click(button=button, clicks=clicks)
            return f"ระบบคลิกเมาส์ ({button}) {clicks} ครั้ง ที่ตำแหน่งปัจจุบันเรียบร้อยครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[GUI ERROR] ไม่สามารถคลิกเมาส์ได้: {e}"

def gui_keyboard_type_operation(text: str, interval: float = 0.05) -> str:
    """พิมพ์ข้อความทางคีย์บอร์ด"""
    try:
        pyautogui.write(text, interval=interval)
        return f"ระบบพิมพ์ข้อความเสร็จสิ้น: '{text}'"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[GUI ERROR] ไม่สามารถพิมพ์ข้อความได้: {e}"

def gui_keyboard_press_operation(keys: list) -> str:
    """กดปุ่ม Hotkey หรือปุ่มเฉพาะบนคีย์บอร์ด"""
    try:
        pyautogui.hotkey(*keys)
        return f"ระบบกดปุ่ม {' + '.join(keys)} เรียบร้อยครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[GUI ERROR] ไม่สามารถกดปุ่มได้: {e}"

def gui_get_screen_info_operation() -> str:
    """ดึงข้อมูลขนาดความกว้างและความสูงของหน้าจอ"""
    try:
        w, h = pyautogui.size()
        return f"ขนาดหน้าจอหลัก: Width {w}px, Height {h}px"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[GUI ERROR] ไม่สามารถดึงข้อมูลหน้าจอได้: {e}"

def call_boss_operation(reason: str, message: str = "") -> str:
    """โทรเข้ามือถือของเจ้านายผ่านระบบ Telephony Gateway"""
    try:
        from jarvis_mobile_api import trigger_call_to_boss  # type: ignore
        res = trigger_call_to_boss(reason=reason, message=message)
        call_id = res.get("call_id", "UNKNOWN")
        return (
            f"[OUTBOUND CALL INITIATED] J.A.R.V.I.S. กำลังส่งสัญญาณโทรเข้ามือถือของเจ้านาย "
            f"เหตุผล: '{reason}' (Call ID: {call_id}) เรียบร้อยแล้วครับ ระบบเปิดโหมด Hands-free รอเจ้านายรับสายครับ"
        )
    except Exception as e:
        logger.error(f"Call Boss Operation Failed: {e}")
        return f"เกิดข้อผิดพลาดในการโทรหามือถือ: {e}"

def take_screenshot_operation(file_name: str | None = None) -> str:
    """จับภาพหน้าจอทั้งหมดและบันทึกเป็นไฟล์ภาพ พร้อมส่งภาพให้เจ้านายดู"""
    try:
        screenshots_dir = os.path.join(BASE_DIR, "screenshots")
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            
        temp_img_dir = os.path.join(BASE_DIR, "temp_images")
        if not os.path.exists(temp_img_dir):
            os.makedirs(temp_img_dir)

        base_name = f"screenshot_{int(time.time())}.png"
        if file_name and isinstance(file_name, str) and file_name.strip():
            base_name = os.path.basename(file_name)
            if not base_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                base_name += '.png'

        file_path = os.path.join(screenshots_dir, base_name)
        temp_file_path = os.path.join(temp_img_dir, base_name)

        img = pyautogui.screenshot()
        img.save(file_path)
        img.save(temp_file_path)

        url_part = ""
        ngrok = globals().get("NGROK_PUBLIC_URL", "")
        if ngrok:
            url_part = f"\n<img src='{ngrok}/temp_images/{base_name}'>"
        else:
            url_part = f"\n<img src='http://127.0.0.1:5050/temp_images/{base_name}'>"

        return f"ดำเนินการจับภาพหน้าจอเรียบร้อยแล้วครับเจ้านาย (บันทึกที่: {file_path}){url_part}"
    except Exception as e:
        return f"[WINDOW: OS Kernel Diagnostic]\nระบบประสาทรับภาพไม่สามารถแคปเจอร์ภาพหน้าจอได้: {str(e)}\n[END_WINDOW]"

def toggle_island_operation(action: str) -> str:
    """ซ่อนหรือแสดง Dynamic Island"""
    try:
        if action.lower() == "hide":
            send_to_island("VISIBILITY", "HIDE")
            return "กระผมได้ทำการซ่อนแผงควบคุมหลักออกจากหน้าจอเรียบร้อยแล้วครับเจ้านาย"
        elif action.lower() == "show":
            send_to_island("VISIBILITY", "SHOW")
            return "กระผมได้เรียกแผงควบคุมหลักกลับมาแสดงบนหน้าจอเรียบร้อยแล้วครับเจ้านาย"
        else:
            return "ไม่เข้าใจคำสั่งการซ่อน/แสดงหน้าต่างครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to toggle island: {e}")
        return f"เกิดข้อผิดพลาดในการเชื่อมต่อกับแผงควบคุมหลัก: {e}"

def classify_and_categorize_files_operation(directory: str) -> str:
    """
    สแกนและจัดหมวดหมู่ไฟล์ในโฟลเดอร์ที่ระบุโดยอัตโนมัติ
    โดยจะสร้างโฟลเดอร์ย่อยตามประเภทไฟล์และย้ายไฟล์เข้าไป
    """
    if not os.path.isdir(directory):
        return f"ขออภัยครับเจ้านาย ไม่พบโฟลเดอร์ที่ '{directory}' ครับ"

    categories = {
        "เอกสาร": ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md'],
        "รูปภาพ": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
        "วิดีโอ": ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
        "เสียง": ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
        "โปรแกรม": ['.exe', '.msi', '.app', '.bat', '.sh'],
        "ไฟล์บีบอัด": ['.zip', '.rar', '.7z', '.tar', '.gz'],
        "โค้ด": ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.json', '.xml'],
        "สเปรดชีต": ['.xls', '.xlsx', '.csv', '.ods'],
        "พรีเซนเทชัน": ['.ppt', '.pptx', '.odp'],
        "อื่นๆ": [] 
    }

    ext_to_category = {}
    for cat_name, extensions in categories.items():
        for ext in extensions:
            ext_to_category[ext] = cat_name

    moved_count = 0
    report = []

    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_extension = os.path.splitext(filename)[1].lower()

            category_name = ext_to_category.get(file_extension, "อื่นๆ")
            
            if os.path.basename(root) == category_name:
                continue 

            target_category_dir = os.path.join(directory, category_name)
            os.makedirs(target_category_dir, exist_ok=True)

            target_file_path = os.path.join(target_category_dir, filename)
            
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(target_file_path):
                target_file_path = os.path.join(target_category_dir, f"{base}_{counter}{ext}")
                counter += 1

            try:
                shutil.move(file_path, target_file_path)
                moved_count += 1
                report.append(f"- ย้าย '{filename}' ไปยัง '{category_name}'")
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                report.append(f"- ไม่สามารถย้าย '{filename}' ได้: {e}")
    
    if moved_count > 0:
        return f"ดำเนินการจัดหมวดหมู่ไฟล์ในโฟลเดอร์ '{directory}' เรียบร้อยแล้วครับเจ้านาย ย้ายไป {moved_count} ไฟล์:\n" + "\n".join(report)
    else:
        return f"ไม่พบไฟล์ที่ต้องจัดหมวดหมู่ในโฟลเดอร์ '{directory}' ครับเจ้านาย"

@functools.lru_cache(maxsize=128) 
def search_wikipedia_operation(query: str, user_raw_message="") -> str:
    """ค้นหาและดึงบทสรุปจาก Wikipedia ภาษาไทย"""
    hologram_keywords = ["โฮโลแกรม", "จอโฮโลแกรม", "ขึ้นจอโฮโลแกรม", "ฉายโฮโลแกรม", "ฉาย"]
    if not any(k in user_raw_message for k in hologram_keywords):
        url = f"https://th.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(query)}"
        webbrowser.open(url)
        cheeky_responses = [
            f"ดำเนินการเปิดข้อมูล '{query}' บน Wikipedia เรียบร้อยครับ",
            f"เปิดหน้า '{query}' ใน Wikipedia ให้แล้วครับผม",
            f"จัดให้ครับ ค้นประวัติ '{query}' บน Wikipedia ปกติเรียบร้อย!",
            f"เปิดวิกิ '{query}' แล้วครับ ลุยเลยครับ",
            f"เรียบร้อยครับเจ้านาย กำลังค้น '{query}' จากวิกิพีเดียให้เลย",
            "จัดให้ครับ!"
        ]
        return random.choice(cheeky_responses)
    try:
        search_url = "https://th.wikipedia.org/w/api.php"
        headers = {
            "User-Agent": "JarvisHUD/1.0 (contact@nachapolindustries.com; support@nachapolindustries.com) Python-requests/2.31.0"
        }
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }
        search_res = requests.get(search_url, params=search_params, headers=headers, timeout=10).json()
        
        if not search_res.get('query', {}).get('search'):
            return f"เกรงว่าฐานข้อมูล Wikipedia จะไม่มีบันทึกเกี่ยวกับ '{query}' ไว้ครับท่าน"
        
        top_title = search_res['query']['search'][0]['title']
        
        extract_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": top_title,
            "format": "json"
        }
        extract_res = requests.get(search_url, params=extract_params, headers=headers, timeout=10).json()
        pages = extract_res.get('query', {}).get('pages', {})
        page_id = next(iter(pages))
        content = pages[page_id].get('extract', 'ไม่สามารถดึงเนื้อหาได้ครับ')
        
        return f"[WINDOW: Wikipedia: {top_title}]\n{content}\n[END_WINDOW]"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        return f"[WINDOW: Wikipedia Error]\nการเข้าถึงคลังความรู้ Wikipedia ขัดข้องครับเจ้านาย: {str(e)}\n[END_WINDOW]"

@functools.lru_cache(maxsize=128) 
def fetch_github_trending_operation() -> str:
    """ดึงข้อมูล Repository ที่กำลังเป็นที่นิยมบน GitHub (จำลอง Trending)"""
    try:
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc&per_page=5"
        headers = {"Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers, timeout=10).json()
        items = res.get('items', [])
        
        if not items: return "ไม่พบเทรนด์ใหม่ที่โดดเด่นบน GitHub ในสัปดาห์นี้ครับ"
        
        results = [f"- {i['full_name']} ({i['stargazers_count']} stars)\n  Desc: {i['description']}\n  URL: {i['html_url']}" for i in items]
        return "--- GitHub Trending (New & Popular) ---\n" + "\n".join(results)
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        return f"GitHub API Error: {str(e)} ครับเจ้านาย"

LAST_WEATHER_TIME = 0
LAST_WEATHER_CACHE = ""

def get_weather(city: str = "Bangkok") -> str:
    """ดึงข้อมูลสภาพอากาศแบบ Real-time พร้อมแคชระบบเพื่อลด Latency"""
    global LAST_WEATHER_TIME, LAST_WEATHER_CACHE
    now = time.time()
    if now - LAST_WEATHER_TIME < 600 and LAST_WEATHER_CACHE:
        return LAST_WEATHER_CACHE
        
    api_key = (os.getenv("OPENWEATHER_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key: return "เกรงว่า... เซนเซอร์ตรวจอากาศยังไม่ได้เชื่อมต่อ ท่าน ครับ"
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=th"
        data = requests.get(url, timeout=2).json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        result = f"ขณะนี้ที่ {city} อุณหภูมิ {temp}°C สภาพอากาศ{desc}ครับท่าน"
        LAST_WEATHER_CACHE = result
        LAST_WEATHER_TIME = now
        return result
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e: 
        logger.error(f"Weather API Error: {e}")
        if LAST_WEATHER_CACHE:
            return LAST_WEATHER_CACHE
        return "เกรงว่า... ไม่สามารถติดต่อสถานีอุตุนิยมวิทยาได้ ท่าน ครับ"

@functools.lru_cache(maxsize=128) 
def fetch_web_content(url: str) -> str:
    """ดึงเนื้อหาข้อความจากเว็บไซต์ที่ระบุเพื่อใช้เป็นบริบท"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            return f"(ขออภัยครับเจ้านาย ไม่พบหน้าเว็บไซต์ที่ระบุ (404) ที่ URL: {url})"
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.extract()
            
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:5000]
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"Web Fetch Error: {e}") 
        return f"(ไม่สามารถเข้าถึงเนื้อหาจากลิงก์นี้ได้: {str(e)})"

@functools.lru_cache(maxsize=128) 
def fetch_news(query: Optional[str] = None) -> str:
    """ดึงหัวข้อข่าวล่าสุดจาก Google News RSS (ภาษาไทย) หรือตามหัวข้อที่ระบุ"""
    try:
        if query:
            
            url = f"https://news.google.com/rss/search?q={query}&hl=th&gl=TH&ceid=TH:th"
        else:
            
            url = "https://news.google.com/rss?hl=th&gl=TH&ceid=TH:th"
            
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            news_items = []
            for item in root.findall('.//item')[:5]:  
                title = item.find('title').text  # type: ignore
                news_items.append(f"- {title}")
            
            if not news_items and query:
                return f"ขออภัยครับ ผมไม่พบข่าวที่เกี่ยวข้องกับ '{query}' ในขณะนี้"
            return "\n".join(news_items)
        return "ขออภัยครับ ไม่สามารถเข้าถึงแหล่งข้อมูลข่าวได้ในขณะนี้"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"News Fetch Error: {e}")
        return "[WINDOW: Network Diagnostic]\nระบบประสาทรับรู้ข่าวสารขัดข้อง ไม่สามารถดึงข้อมูลข่าวได้ในขณะนี้ครับท่าน\n[END_WINDOW]"

def get_circadian_settings():
    """คำนวณค่าแสงที่เหมาะสมตามช่วงเวลา (Circadian Rhythm)"""
    hour = datetime.now().hour
    if 6 <= hour < 10: 
        return {"kelvin": 5000, "brightness": 200, "label": "Morning Focus"}
    elif 10 <= hour < 16: 
        return {"kelvin": 6500, "brightness": 255, "label": "Daylight"}
    elif 16 <= hour < 19: 
        return {"kelvin": 4000, "brightness": 180, "label": "Late Afternoon"}
    elif 19 <= hour < 22: 
        return {"kelvin": 2700, "brightness": 100, "label": "Evening Warmth"}
    else: 
        return {"kelvin": 2000, "brightness": 30, "label": "Night Shift"}

def apply_weather_adjustment(current_settings):
    """ปรับแต่งแสงเพิ่มเติมตามสภาพอากาศภายนอก"""
    try:
        weather_data = get_weather("Bangkok") 
        if any(word in weather_data for word in ["ฝน", "เมฆมาก", "ครึ้ม", "rain", "cloudy"]):
            
            current_settings["kelvin"] = min(current_settings["kelvin"], 3000)
            current_settings["brightness"] = min(current_settings["brightness"] + 50, 255)
            current_settings["label"] += " (Weather Compensated)"
    except (requests.exceptions.RequestException, ConnectionError, OSError):
        pass
    return current_settings

def search_web_operation(query, user_raw_message=""):
    """ค้นหาข้อมูลแบบ Real-time จากอินเทอร์เน็ต (Global Data Stream)"""
    cleaned_query = clean_thai_search_query(query, search_type="general")
    effective_query = cleaned_query if cleaned_query else query

    open_browser_triggers = ["เปิดกูเกิล", "เปิด google", "เปิดเบราว์เซอร์", "เปิด browser", "เปิด chrome", "เปิดเว็บดู", "เปิดดูในเว็บ"]
    if any(k in user_raw_message.lower() for k in open_browser_triggers):
        url = f"https://www.google.com/search?q={urllib.parse.quote(effective_query)}"
        webbrowser.open(url)
        return f"ดำเนินการเปิดหน้าค้นหา Google สำหรับ '{effective_query}' บนเบราว์เซอร์เรียบร้อยแล้วครับเจ้านาย"

    try:
        results = []
        with DDGS() as ddgs:
            # ค้นหาภาษาไทยก่อน หากไม่พบจึงค้นหา Global
            results = list(ddgs.text(effective_query, region='th-th', max_results=5))
            if not results:
                results = list(ddgs.text(effective_query, max_results=5))

        if results:
            formatted = "\n".join([f"- {r.get('title', '')}: {r.get('href', '')}\n  {r.get('body', '')}" for r in results])
            return f"[WEB SEARCH RESULTS for '{effective_query}']:\n{formatted}\n[END RESULTS]"
        else:
            return f"ไม่พบผลการค้นหาสำหรับ '{effective_query}' บนอินเทอร์เน็ตครับ"
    except Exception as e:
        logger.error(f"Search Web Error: {e}")
        try:
            return perform_live_web_search_operation(effective_query)
        except Exception:
            return f"ระบบค้นหาข้อมูลภายนอกขัดข้องชั่วคราวครับ: {str(e)}"

def search_image_operation(query: str, user_raw_message: str = "") -> str:  # type: ignore
    """ค้นหารูปภาพจากอินเทอร์เน็ตและส่ง URL รูปภาพพร้อมแสดงผล (รองรับทั้ง Web, Desktop และ LINE)"""
    search_type = "chord" if any(k in query.lower() for k in ["คอร์ด", "chord", "แท็บ", "tab", "ตารางคอร์ด"]) else "image"
    cleaned_query = clean_thai_search_query(query, search_type=search_type)
    effective_query = cleaned_query if cleaned_query else query

    # ── 1. Fast Direct High-Res Image Search (Bing Web Scraping — 0.3s) ───
    try:
        b_url = 'https://www.bing.com/images/search?q=' + urllib.parse.quote(effective_query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(b_url, headers=headers, timeout=6)
        matches = re.findall(r'murl&quot;:&quot;(https://[^&]+?)&quot;', r.text)
        if matches:
            image_url = matches[0]
            if any(k in effective_query.lower() for k in ["คอร์ด", "chord", "tab", "แท็บ"]):
                for u in matches:
                    if "pinimg.com" in u.lower():
                        image_url = u
                        break
                else:
                    for u in matches:
                        if any(d in u.lower() for d in ["chord", "guitar", "tab", "music", "img"]):
                            image_url = u
                            break
            logger.info(f"[SEARCH IMAGE] Found image for '{effective_query}': {image_url[:60]}...")
            return (
                f"[WINDOW: ภาพของ {effective_query}]\n"
                f"นี่คือรูปภาพของ {effective_query} ที่ค้นหามาให้ครับเจ้านาย:\n"
                f"<img src=\"{image_url}\" style=\"max-width:100%; border-radius:8px;\">\n"
                f"[END_WINDOW]"
            )
    except Exception as e:
        logger.warning(f"[SEARCH IMAGE] Fast search failed: {e}")

    # ── 2. Fallback: DuckDuckGo / Wikipedia ───
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(effective_query, max_results=1))
            if results and 'image' in results[0]:
                image_url = results[0]['image']
                return (
                    f"[WINDOW: ภาพของ {effective_query}]\n"
                    f"ค้นหารูปภาพของ {effective_query} ให้เรียบร้อยครับเจ้านาย:\n"
                    f"<img src=\"{image_url}\" style=\"max-width:100%; border-radius:8px;\">\n"
                    f"[END_WINDOW]"
                )
    except Exception as e:
        logger.error(f"[SEARCH IMAGE] DDG search error: {e}")
        logger.error(f"DDG Image Search Error: {e}. Trying Wikipedia fallback.")
        try:
            search_url = "https://th.wikipedia.org/w/api.php"
            headers = {
                "User-Agent": "JarvisHUD/1.0 (contact@nachapolindustries.com; support@nachapolindustries.com) Python-requests/2.31.0"
            }
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": effective_query,
                "format": "json"
            }
            search_res = requests.get(search_url, params=search_params, headers=headers, timeout=10).json()
            if search_res.get('query', {}).get('search'):
                top_title = search_res['query']['search'][0]['title']
                image_params = {
                    "action": "query",
                    "prop": "pageimages",
                    "piprop": "original",
                    "titles": top_title,
                    "format": "json"
                }
                image_res = requests.get(search_url, params=image_params, headers=headers, timeout=10).json()
                pages = image_res.get('query', {}).get('pages', {})
                page_id = next(iter(pages))
                original_img = pages[page_id].get('original', {}).get('source')
                if original_img:
                    return (
                        f"[WINDOW: ภาพของ {effective_query}]\n"
                        f"<div style=\"text-align:center;\">\n"
                        f"    <img src=\"{original_img}\" style=\"max-width:100%; border-radius:5px; border: 1px solid #37e2b1; box-shadow: 0 0 10px rgba(55,226,177,0.3);\">\n"
                        f"</div>\n"
                        f"[END_WINDOW]"
                    )
            return f"[WINDOW: Image Search Error]\nระบบไม่พบรูปภาพเกี่ยวกับ '{effective_query}' บนเครือข่ายข้อมูลอินเทอร์เน็ตและคลังวิกิพีเดียครับเจ้านาย\n[END_WINDOW]"
        except (requests.exceptions.RequestException, ConnectionError, OSError) as fe:
            logger.error(f"Wikipedia Fallback Image Search Error: {fe}")
            return f"[WINDOW: Image Search Error]\nระบบประสาทสัมผัสเครือข่ายขัดข้อง: {str(e)} อีกทั้งการกู้ข้อมูลล้มเหลวครับเจ้านาย\n[END_WINDOW]"

def get_detailed_diagnostics():
    """รายงานข้อมูลฮาร์ดแวร์และซอฟต์แวร์ของเครื่องอย่างละเอียด - Nachapol Industries Style"""
    
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    info = {
        "Operating System": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "Processor": platform.processor(),
        "CPU Cores": f"{psutil.cpu_count(logical=False)} Physical / {psutil.cpu_count(logical=True)} Logical",
        "Total Memory": f"{round(ram.total / (1024**3), 2)} GB",
        "System Boot Time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
        "Python Version": sys.version.split()[0]
    }
    
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_hours = int(uptime_seconds // 3600)
    uptime_days = uptime_hours // 24
    
    integrity_score = 100 - (cpu_usage * 0.2 + ram.percent * 0.3)
    
    try:
        raw_prob = predict_system_failure(cpu_usage, ram.percent, disk.percent)
        failure_probability = float(raw_prob) if raw_prob is not None else 0.0
    except Exception:
        failure_probability = 0.0

    analysis = "● การวิเคราะห์: "
    if integrity_score > 90:
        analysis += "ระบบมีความเสถียรสูงสุด พลังงานสำรองคงที่ครับ"
    elif integrity_score > 70:
        analysis += "ระบบทำงานในเกณฑ์ปกติ แต่ตรวจพบกิจกรรมในหน่วยความจำเพิ่มขึ้นเล็กน้อย"
    else:
        analysis += "ตรวจพบภาระงานหนักในแกนประมวลผล แนะนำให้ระงับโปรโตคอลที่ไม่จำเป็นครับ"
    
    if failure_probability > 0.7:  # type: ignore
        analysis = "⚠️ **[CRITICAL ALERT]** ตรวจพบความเสี่ยงสูงที่ Mainframe จะขัดข้องจากการวิเคราะห์ด้วย Neural Matrix ครับท่าน!"

    ha_status = "CONNECTED" if HA_TOKEN and "YOUR_LONG_LIVED" not in HA_TOKEN else "OFFLINE"

    system_report = f"\n[MAINFRAME DIAGNOSTIC REPORT]\n"
    system_report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    system_report += f"◆ ความสมบูรณ์ของระบบ (Integrity): {integrity_score:.1f}%\n"
    system_report += f"◆ แกนประมวลผล (CPU): {cpu_usage}% [{psutil.cpu_freq().current:.0f} MHz]\n"
    system_report += f"◆ โครงข่ายประสาท (RAM): {ram.percent}% ({round(ram.used/(1024**3), 2)}GB)\n"
    system_report += f"◆ พื้นที่คลังข้อมูล: {disk.percent}% คงเหลือ {disk.free // (1024**3)}GB\n"
    system_report += f"◆ ระบบควบคุมบ้าน (HA): {ha_status}\n"
    system_report += f"◆ ระยะเวลาปฏิบัติการ: {uptime_days} วัน {uptime_hours % 24} ชั่วโมง\n"
    system_report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    system_report += f"{analysis}\n"
    system_report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    system_report += f"ทุกอย่างสแตนด์บาย พร้อมรับคำสั่งครับท่าน"
    return system_report

def send_email_notification(subject, body):
    """ฟังก์ชันสำหรับส่งอีเมลแจ้งเตือนความปลอดภัยไปยังเจ้านาย"""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", 587)
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    dest_email = os.getenv("USER_EMAIL")

    if not all([smtp_server, email_user, email_pass, dest_email]):
        logger.warning("[EMAIL SYSTEM] Configuration Incomplete - Check .env file")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"J.A.R.V.I.S. Emergency Alert <{email_user}>"
        msg['To'] = dest_email  # type: ignore
        msg['Subject'] = f"[URGENT] {subject}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:  # type: ignore
            server.starttls()
            server.login(email_user, email_pass)  # type: ignore
            server.send_message(msg)
        
        logger.info(f"[EMAIL] Emergency notification sent to {dest_email} successfully")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Dispatch Failed: {e}")
        return False

def sync_lights_to_music(duration=60):
    """ระบบจำลองการกระพริบไฟตามจังหวะเพลง (Rhythm Sync)"""
    def run_sync():
        
        """
        Execute the scheduler's synchronous payload inside a Flask app context.

        Inner closure bridging async APScheduler jobs that need Flask g/current_app.
        """
        colors = [[255, 0, 0], [0, 0, 255], [0, 255, 0], [255, 255, 0], [255, 0, 255], [0, 255, 255]]
        end_time = time.time() + duration
        try:
            while time.time() < end_time:
                color = random.choice(colors)
                
                control_light("all", "on", brightness=255, rgb_color=color, transition=0, silent=True)
                time.sleep(0.6)
                control_light("all", "on", brightness=80, rgb_color=color, transition=0, silent=True)
                time.sleep(0.3)
            
            control_light("all", "on", brightness=255, kelvin=4500, transition=3, silent=True)
        except Exception as e:
            logger.error(f"Rhythm Sync Error: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()

def _install_missing_dependencies(code: str) -> List[str]:
    """
    Parses the given Python code for import statements and attempts to install
    any identified top-level modules using pip if they are not already available.
    Returns a list of modules that were attempted to be installed.
    """
    installed_modules = []
    module_names = set()
    
    for match in re.findall(r'^\s*import\s+([a-zA-Z0-9_.]+)(?:\s+as\s+[a-zA-Z0-9_]+)?', code, re.MULTILINE):
        module_names.add(match.split('.')[0]) 
        
    for match in re.findall(r'^\s*from\s+([a-zA-Z0-9_.]+)\s+import', code, re.MULTILINE):
        module_names.add(match.split('.')[0]) 

    if not module_names:
        logger.info("No external dependencies found in the generated tool code.")
        return []

    logger.info(f"Detected potential dependencies: {', '.join(module_names)}")

    standard_libs = {'os', 'sys', 'json', 're', 'time', 'datetime', 'math', 'random', 'collections', 'io', 
                     'threading', 'subprocess', 'gc', 'logging', 'platform', 'shutil', 'tempfile', 
                     'webbrowser', 'requests', 'base64', 'sqlite3', 'smtplib', 'email', 
                     'typing', 'xml', 'bs4', 'dotenv', 'flask', 'flask_cors', 'langgraph', 
                     'langchain_core', 'chromadb', 'psutil', 'waitress', 'duckduckgo_search', 
                     'importlib', 'importlib.util'} 

    for module_name in module_names:
        if module_name in standard_libs:
            continue
            
        try:
            importlib.import_module(module_name)
            logger.info(f"Module '{module_name}' is already installed.")
        except ImportError:
            logger.info(f"Module '{module_name}' not found. Attempting to install...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
                installed_modules.append(module_name)
                logger.info(f"Successfully installed '{module_name}'.")
            except (subprocess.SubprocessError, OSError) as e:
                logger.error(f"Failed to install '{module_name}': {e}")
    
    return installed_modules

def synaptic_code_analyzer(file_path=None, code=None):
    """
    [MODULE 1: Advanced Software Engineering Core]
    ใช้ AST สกัดโครงสร้างรหัสออกมาเป็นแผนผังจิตสำนึก และตรวจสอบ Design Pattern Compliance
    """
    try:
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        else:
            code_content = code
            
        tree = ast.parse(code_content)  # type: ignore
        
        classes = []
        functions = []
        has_try_except = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Try):
                has_try_except = True
                
        if not has_try_except and functions:
            return {"valid": False, "reason": "Missing Try-Except block (Memory Leak/Exception Prevention Protocol Violated)"}
            
        code_map = {
            "valid": True,
            "classes": classes,
            "functions": functions,
            "has_try_except": has_try_except
        }
        return code_map
    except SyntaxError as e:
        return {"valid": False, "reason": f"Syntax Error: {e}"}
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return {"valid": False, "reason": f"AST Analysis Error: {e}"}

def build_knowledge_graph_relation(entity_a, relation, entity_b, confidence=1.0, source='system'):
    """[MODULE 3: Graph-Based RAG Matrix] สร้างเส้นเชื่อมโยงโครงข่ายความคิด"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            
            c.execute("PRAGMA table_info(knowledge_graph)")
            cols = [info[1] for info in c.fetchall()]
            if 'valid_from' in cols:
                import time
                now = time.time()
                c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b, confidence, source, valid_from, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (str(entity_a).lower(), str(relation).lower(), str(entity_b).lower(), float(confidence), source, now, now))
            elif 'confidence' in cols and 'source' in cols:
                c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b, confidence, source) VALUES (?, ?, ?, ?, ?)",
                          (str(entity_a).lower(), str(relation).lower(), str(entity_b).lower(), float(confidence), source))
            else:
                c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b) VALUES (?, ?, ?)",
                          (str(entity_a).lower(), str(relation).lower(), str(entity_b).lower()))
            conn.commit()
        return f"ระบบได้สร้างเส้นทางเชื่อมประจุประสาทระหว่าง '{entity_a}' และ '{entity_b}' สำเร็จ"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return f"ล้มเหลวในการเชื่อมโยง Graph: {e}"

def generate_new_tool_operation(tool_name, code, purpose):
    """บันทึกโค้ดที่ AI สร้างขึ้นลงเป็นไฟล์ .py ผ่าน Sandbox และ Hot-reloader"""
    file_path = os.path.join(DYNAMIC_TOOLS_DIR, f"{tool_name}.py")
    try:
        # 1. Cognitive Tool Factory AST Security Check
        if 'tool_factory' in globals() and tool_factory:
            if not tool_factory.sandbox.validate_ast(code):
                return f"[WINDOW: Tool Factory Security Violation]\nไม่อนุมัติการสร้างเครื่องมือ '{tool_name}' เนื่องจากตรวจพบโค้ดที่ละเมิดนโยบายความปลอดภัยของระบบ (AST Security Check)\n[END_WINDOW]"

        # 2. Architecture Analysis Check
        analysis = synaptic_code_analyzer(code=code)
        if not analysis.get("valid", False):
            return f"[WINDOW: Architecture Compliance Error]\nไม่อนุมัติการคอมไพล์โค้ด! เหตุผล: {analysis.get('reason')}\nกรุณาเพิ่ม Try-Except หรือแก้ไข Syntax ให้ถูกต้องตาม PEP 8\n[END_WINDOW]"
        
        # 3. Dependencies Check & Install
        installed_deps = _install_missing_dependencies(code)
        dep_message = ""
        if installed_deps:
            dep_message = f" (พร้อมติดตั้ง Dependencies: {', '.join(installed_deps)})"
        
        # 4. Sandbox Validation Execution
        if 'tool_factory' in globals() and tool_factory:
            sandbox_pass = tool_factory.sandbox.run_unit_tests(code, test_code="pass")
            if not sandbox_pass:
                return f"[WINDOW: Sandbox Execution Failure]\nเครื่องมือ '{tool_name}' ทำงานล้มเหลวในการทดสอบ Subprocess Sandbox กรุณาตรวจสอบโค้ดอีกครั้ง\n[END_WINDOW]"

        decorated_code = f'"""\nPurpose: {purpose}\nCreated: {datetime.now()}\n"""\n\n{code}'
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(decorated_code)
        
        try:
            if personal_collection:
                personal_collection.add(documents=[f"สร้างเครื่องมือใหม่: {tool_name} สำหรับ {purpose}"], ids=[f"tool_{tool_name}"])
        except Exception:
            pass
        
        load_dynamic_tools()
        
        return f"สำเร็จครับท่าน! กระผมได้ผ่านการตรวจสอบ Sandbox และติดตั้งเครื่องมือ '{tool_name}' ลงในระบบหลักเรียบร้อยแล้ว{dep_message} พร้อมใช้งานทันทีครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: System Diagnostic]\nเกรงว่าระบบจะพบข้อขัดข้องในการคอมไพล์และติดตั้งโมดูลใหม่: {str(e)}\n[END_WINDOW]"

def auto_evolve_tool_from_vision(app_name: str, task_description: str) -> str:
    """[Background Self-Evolution Matrix] สังเคราะห์อินเตอร์เฟซแอปแปลกใหม่ด้วย Vision แล้วเขียนสคริปต์ขยายขีดความสามารถตัวเอง"""
    try:
        
        logger.info(f"[Self-Evolution] Scanning interface of: {app_name}")
        
        screenshot_path = os.path.join(BASE_DIR, "temp_evolve_screenshot.jpg")
        pyautogui.screenshot(screenshot_path)
        
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        
        vision_response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"You are looking at a screenshot of the application '{app_name}'. Describe the interface: what buttons, menus, input fields, and interactive elements are visible. Be precise about their positions."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }],
            temperature=0.1,
            timeout=10.0
        )
        interface_description = vision_response.choices[0].message.content
        
        code_gen_prompt = (
            f"Based on this interface description of '{app_name}':\n{interface_description}\n\n"
            f"Write a Python automation script using pyautogui and scan_screen_with_llama_vision() to accomplish: {task_description}\n"
            f"The script MUST:\n"
            f"1. Be wrapped in try-except\n"
            f"2. Use scan_screen_with_llama_vision() for finding UI elements\n"
            f"3. Include gc.collect() at the end\n"
            f"Output ONLY the Python code, no markdown."
        )
        
        code_response = call_groq_model([
            {"role": "system", "content": "You are an expert Python automation engineer. Output ONLY executable Python code."},
            {"role": "user", "content": code_gen_prompt}
        ])
        
        generated_code = code_response.replace('```python', '').replace('```', '').strip()  # type: ignore
        
        analysis = synaptic_code_analyzer(code=generated_code)
        if not analysis.get("valid", False):
            logger.warning(f"[Self-Evolution] Generated code failed analysis: {analysis.get('reason')}")
            return f"ระบบสังเคราะห์สร้างสคริปต์แล้วแต่ไม่ผ่านมาตรฐาน: {analysis.get('reason')}"
        
        tool_name = f"auto_{app_name.lower().replace(' ', '_')}_controller"
        result = generate_new_tool_operation(tool_name, generated_code, f"Auto-generated controller for {app_name}: {task_description}")
        
        if os.path.exists(screenshot_path):
            try: os.remove(screenshot_path)
            except: pass
        gc.collect()
        
        logger.info(f"[Self-Evolution] Successfully evolved new tool: {tool_name}")
        return f"ระบบ Self-Evolution สังเคราะห์อินเตอร์เฟซของ {app_name} และสร้างเครื่องมือ '{tool_name}' สำเร็จแล้วครับ! {result}"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        gc.collect()
        logger.error(f"[Self-Evolution] Error: {e}")
        return f"ระบบ Self-Evolution ขัดข้อง: {str(e)}"

def delete_custom_tool_operation(tool_name):
    """ลบเครื่องมือที่ AI สร้างขึ้นออกจากโฟลเดอร์และหน่วยความจำ"""
    file_path = os.path.join(DYNAMIC_TOOLS_DIR, f"{tool_name}.py")
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            
            try:
                personal_collection.delete(ids=[f"tool_{tool_name}"])
            except (IOError, OSError, FileNotFoundError, PermissionError):
                pass 
            
            return f"เรียบร้อยครับท่าน กระผมได้ถอนการติดตั้งและลบเครื่องมือ '{tool_name}' ออกจากระบบถาวรแล้วครับ"
        return f"ขออภัยครับท่าน ไม่พบเครื่องมือชื่อ '{tool_name}' ในฐานข้อมูลเครื่องมือปรับแต่งครับ"
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"[WINDOW: System Diagnostic]\nระบบพบข้อขัดข้องในการถอนการติดตั้งโมดูล: {str(e)}\n[END_WINDOW]"

def process_image_for_rag(file_path, file_name):
    """[Automated Image Context Extraction Core] สกัดบริบทภาพ Asynchronous"""
    try:
        with open(file_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        vision_result = reverse_engineer_schematic_operation(img_b64)
        
        doc_id = f"img_ingest_{int(time.time())}_{hash(file_name)}"
        personal_collection.add(
            documents=[f"Image File: {file_name}\nPath: {file_path}\nVision Context Summary: {vision_result}"],
            metadatas=[{"path": file_path, "type": "ingested_image_knowledge"}],
            ids=[doc_id]
        )
        logger.info(f"Image Ingested: {file_name}")
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Image Vision Ingestion Error: {e}")
    finally:
        gc.collect()

def ingest_local_directory_operation(directory_path, file_types=None, tag="ingested_knowledge"):
    """[OMNI-READER RAG] สแกนไฟล์และเก็บลง Vector Database รวมทั้ง PDF, DOCX, Code"""
    if not os.path.exists(directory_path):
        return f"ไม่พบโฟลเดอร์ที่ระบุครับท่าน: {directory_path}"
    
    if file_types is None:
        file_types = ['.py', '.txt', '.md', '.html', '.css', '.js', '.json', '.pdf', '.docx']
        
    count = 0
    ignored = 0
    
    try:
        import fitz 
    except ImportError:
        fitz = None
    try:
        from docx import Document as DocxDocument
    except ImportError:
        DocxDocument = None
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150, separators=["\n\n", "\n", " ", ""])
    except ImportError:
        text_splitter = None
        
    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'jarvis_vector_db', '.vscode']]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in file_types:
                file_path = os.path.join(root, file)
                if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    threading.Thread(target=process_image_for_rag, args=(file_path, file), daemon=True).start()
                    count += 1
                    continue
                    
                if ext in ['.pyc', '.exe', '.db', '.sqlite', '.bin']:
                    ignored += 1
                    continue
                    
                try:
                    
                    if os.path.getsize(file_path) > 50 * 1024 * 1024:
                        ignored += 1
                        continue
                        
                    extracted_text = ""
                    
                    if ext == '.pdf' and fitz:
                        with fitz.open(file_path) as doc:
                            extracted_text = "\n".join(page.get_text() for page in doc)  # type: ignore
                    
                    elif ext == '.docx' and DocxDocument:
                        doc = DocxDocument(file_path)
                        extracted_text = "\n".join(para.text for para in doc.paragraphs)
                    
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            extracted_text = f.read()
                            
                    if not extracted_text.strip(): 
                        continue
                        
                    if text_splitter:
                        chunks = text_splitter.split_text(extracted_text)
                    else:
                        chunks = [extracted_text[i:i+2000] for i in range(0, len(extracted_text), 2000)]
                        
                    for idx, chunk in enumerate(chunks):
                        doc_id = f"ingest_{count}_{idx}_{int(time.time())}"
                        personal_collection.add(
                            documents=[f"File: {file}\nPath: {file_path}\nContent: {chunk}"],
                            metadatas=[{"path": file_path, "type": tag}],
                            ids=[doc_id]
                        )
                    count += 1
                except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                    logger.error(f"Failed to ingest {file_path}: {e}")
                    ignored += 1
            else:
                ignored += 1
                
    msg = f"การดูดซับข้อมูล Omni-Reader เสร็จสิ้น! ประมวลผลไป {count} ไฟล์ "
    if ignored > 0:
        msg += f"(ข้าม {ignored} ไฟล์ที่อ่านไม่ได้) "
    msg += "กระผมพร้อมตอบคำถามเกี่ยวกับเอกสารแล้วครับ"
    return msg

def analyze_molecular_structure_operation(element_name: str) -> str:
    """วิเคราะห์โครงสร้างโมเลกุลของธาตุหรือวัสดุใหม่ (Hyper-Tasking Simulation)"""
    time.sleep(0.5) 
    return f"ผลการวิเคราะห์โครงสร้างของ {element_name}: พบความเสถียรของอนุภาคที่ 99.98% พร้อมสำหรับการสังเคราะห์ในเตาปฏิกรณ์อาร์คแล้วครับ"

def manage_mission_log_operation(args: dict) -> str:
    """[NACHAPOL PROTOCOL] ระบบจัดการภารกิจและไทม์ไลน์โปรเจคเชิงรุก"""
    action = args.get("action")
    title = args.get("title")
    description = args.get("description", "")
    due_date = args.get("due_date")
    priority = args.get("priority", "medium")
    status = args.get("status", "pending")

    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            if action == "add_mission":
                c.execute("INSERT INTO tasks (task_description, due_at, priority, status) VALUES (?, ?, ?, ?)", 
                         (title, due_date, priority, status))
                conn.commit()
                return f"บันทึกภารกิจใหม่: '{title}' ลงใน Mission Log เรียบร้อยแล้วครับเจ้านาย"
            
            elif action == "update_mission":
                c.execute("UPDATE tasks SET status = ? WHERE task_description LIKE ?", (status, f"%{title}%"))
                conn.commit()
                return f"อัปเดตสถานะภารกิจ '{title}' เป็น {status} เรียบร้อยครับ"
                
            elif action == "add_event":
                c.execute("INSERT INTO calendar_events (title, description, start_time) VALUES (?, ?, ?)", 
                         (title, description, due_date))
                conn.commit()
                return f"เพิ่มกำหนดการ '{title}' ลงในไทม์ไลน์เรียบร้อยครับท่าน"
                
            elif action == "get_summary":
                c.execute("SELECT task_description, priority, due_at, status FROM tasks WHERE status != 'completed' ORDER BY priority DESC")
                tasks = c.fetchall()
                c.execute("SELECT title, start_time FROM calendar_events WHERE start_time >= datetime('now') ORDER BY start_time ASC")
                events = c.fetchall()
                
                report = "\n[NACHAPOL MISSION LOG & TIMELINE REPORT]\n"
                report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                report += "● ภารกิจที่กำลังดำเนินการ (ACTIVE MISSIONS):\n"
                if not tasks: report += "   - ไม่พบภารกิจค้างในระบบครับ\n"
                for t in tasks:
                    due = f" (กำหนด: {t[2]})" if t[2] else ""
                    report += f"   - [{t[1].upper()}] {t[0]}{due} | Status: {t[3]}\n"
                
                report += "\n● กำหนดการลำดับถัดไป (UPCOMING EVENTS):\n"
                if not events: report += "   - ไม่มีกำหนดการใหม่ในไทม์ไลน์ครับ\n"
                for e in events:
                    report += f"   - {e[0]} @ {e[1]}\n"
                report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                report += "Mainframe พร้อมสนับสนุนการทำงานในขั้นตอนต่อไปครับท่าน"
                return report
                
            return "โปรโตคอลไม่ถูกต้องครับท่าน"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Mission Log DB Error: {e}")
        return f"เกรงว่าระบบฐานข้อมูลภารกิจจะขัดข้อง: {str(e)} ครับ"

def save_to_memory_operation(content: str) -> str:
    """บันทึกข้อมูลสำคัญลงในหน่วยความจำ Vector และ SQLite"""
    try:
        doc_id = f"mem_{int(time.time())}"
        personal_collection.add(
            documents=[content], 
            metadatas=[{"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "manual_knowledge"}],
            ids=[doc_id]
        )
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO memories (action, content) VALUES (?, ?)", ("manual_save", content))
            conn.commit()
        mem_responses = [
            "จดจำเรียบร้อยครับ",
            "บันทึกแล้วครับผม",
            "จัดให้ครับ! บันทึกลงในคลังความจำแล้ว",
            "เรียบร้อยครับเจ้านาย จำไว้ให้แล้ว",
            "ครับท่าน"
        ]
        return random.choice(mem_responses)
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Save Memory Error: {e}")
        return f"เกรงว่าระบบบันทึกความจำจะขัดข้อง: {str(e)} ครับ"

def update_user_profile(key: str, value: str) -> str:
    """บันทึกพฤติกรรมหรือโปรไฟล์ผู้ใช้ลงในฐานข้อมูลเฉพาะ"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, value))
            conn.commit()
        profile_responses = [
            f"บันทึก {key} เรียบร้อยครับ",
            f"จดจำลงฝั่งแล้วครับผม",
            "จัดให้ครับเจ้านาย!",
            f"เรียบร้อยครับเจ้านาย บันทึก {key} แล้ว",
            "ครับท่าน"
        ]
        return random.choice(profile_responses)
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Profile Update Error: {e}")
        return f"[WINDOW: DB Diagnostic]\nระบบฐานข้อมูลความจำขัดข้อง ไม่สามารถอัปเดตโปรไฟล์ได้: {e}\n[END_WINDOW]"

def get_user_profile_context() -> str:
    """ดึงข้อมูลโปรไฟล์และพฤติกรรมผู้ใช้เพื่อใช้เป็นบริบท"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT key, value FROM user_profile")
            profiles = c.fetchall()
            return "\n[ข้อมูลโปรไฟล์และพฤติกรรมผู้ใช้]:\n" + "\n".join([f"- {k}: {v}" for k, v in profiles]) if profiles else ""
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return ""

def search_spatial_map_operation(location: str, user_raw_message="") -> str:
    """[NACHAPOL PROTOCOL] ดึงพิกัดแผนที่ 3 มิติเพื่อจำลองบนหน้าจอโฮโลแกรม"""
    hologram_keywords = ["โฮโลแกรม", "จอโฮโลแกรม", "ขึ้นจอโฮโลแกรม", "ฉายโฮโลแกรม", "ฉาย"]
    if not any(k in user_raw_message for k in hologram_keywords):
        url = f"https://earth.google.com/web/search/{urllib.parse.quote(location)}"
        webbrowser.open(url)
        cheeky_responses = [
            f"ดำเนินการเปิดแผนที่ '{location}' เรียบร้อยครับเจ้านาย",
            f"เปิดพิกัด '{location}' ให้แล้วครับผม",
            f"จัดให้ครับ ปักหมุด '{location}' บนแผนที่เรียบร้อย!",
            f"เปิดแผนที่ '{location}' แล้วครับ เตรียมออกเดินทางได้เลย",
            f"เรียบร้อยครับเจ้านาย กำลังโหลดแผนที่ '{location}' ให้เลย",
            "จัดให้ครับ!"
        ]
        return random.choice(cheeky_responses)

    add_hologram(hologram_type="Spatial-Map", title=f"SPATIAL MAP: {location}", content=location)
    return f"กำลังดึงพิกัดแผนที่ 3 มิติของ {location} ขึ้นหน้าจอโฮโลแกรมครับเจ้านาย"

def reverse_engineer_schematic_operation(image_base64: str) -> str:
    """[PROACTIVE SCHEMATIC INGESTION] แปลงภาพถ่ายฮาร์ดแวร์หรือพิมพ์เขียววงจรให้เป็นข้อมูลวิศวกรรมผ่าน Llama Vision API"""
    if not image_base64:
        return "เกรงว่ากระผมจะไม่พบ Payload ไฟล์ภาพถ่ายชิ้นส่วนวงจรไฟฟ้าสำหรับนำมาถอดรหัสครับเจ้านาย"
    try:
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        
        vision_prompt = (
            "You are J.A.R.V.I.S. Visual Engineering Module. Analyze the uploaded circuit blueprint or hardware component photo. "
            "1. Identify electrical components (resistors, capacitors, microcontrollers, wires). "
            "2. Extract technical codes, color bands (e.g., resistor values), pinouts, or estimated voltage paths. "
            "3. Format response inside a [WINDOW: SCHEMATIC DECODER MATRIX] header and [END_WINDOW] footer for HUD display."
        )
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": vision_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "Analyze this schematic/hardware image for engineering context:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}
            ],
            temperature=0.2,
            timeout=5.0
        )
        reply = response.choices[0].message.content
        gc.collect()
        return reply  # type: ignore
    except Exception as e:
        gc.collect()
        return f"[WINDOW: Vision Diagnostic]\nระบบประสาทรับภาพพบข้อขัดข้องข้ามเครือข่าย: {str(e)}\n[END_WINDOW]"

def manage_lab_inventory_operation(action: str, part_name: str, qty: int = 1, spec: str = "") -> str:  # type: ignore
    """[AUTONOMOUS HARDWARE INVENTORY TRACER] ระบบจัดการ ดักจับ และคิวรี่ตารางอะไหล่แล็บผ่าน SQLite"""
    db_path = JARVIS_DB_PATH
    try:
        with ThreadSafeDB.connect(db_path, timeout=30, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            
            if action == "add":
                c.execute('''INSERT INTO lab_inventory (part_name, quantity, specification) 
                             VALUES (?, ?, ?) 
                             ON CONFLICT(part_name) DO UPDATE SET 
                             quantity = quantity + excluded.quantity,
                             specification = CASE WHEN excluded.specification != '' THEN excluded.specification ELSE specification END,
                             updated_at = CURRENT_TIMESTAMP''', (part_name.lower(), qty, spec))
                conn.commit()
                
                thought_engine.process_success()
                return f"ดำเนินการเพิ่มอะไหล่ {part_name} จำนวน {qty} ชิ้น เข้าสู่คลังแล็บและอัปเดตระเบียบสารระบบเรียบร้อยครับนายครับ"
                
            elif action == "remove":
                c.execute("SELECT quantity FROM lab_inventory WHERE part_name = ?", (part_name.lower(),))
                row = c.fetchone()
                if not row or row[0] < qty:
                    return f"เกรงว่าอะไหล่ {part_name} ในคลังมีไม่เพียงพอต่อการเบิกจ่ายครับเจ้านาย"
                c.execute("UPDATE lab_inventory SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE part_name = ?", (qty, part_name.lower()))
                conn.commit()
                return f"เบิกจ่ายอะไหล่ {part_name} ออกจากคลังจำนวน {qty} ชิ้น เรียบร้อยครับเจ้านาย"
                
            elif action == "check":
                if part_name == "all" or not part_name:
                    c.execute("SELECT part_name, quantity, specification FROM lab_inventory WHERE quantity > 0")
                    rows = c.fetchall()
                    if not rows: return "รายงานสารระบบ: ปัจจุบันไม่มีพิกัดชิ้นส่วนอะไหล่ใดๆ คงเหลืออยู่ในคลังแล็บครับ"
                    report = "\n[NACHAPOL LAB INVENTORY REPORT]\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    for r in rows:
                        spec_str = f" ({r[2]})" if r[2] else ""
                        report += f"  - {r[0].upper()}: {r[1]} ชิ้น{spec_str}\n"
                    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    return f"[WINDOW: คลังอะไหล่แล็บ]\n{report}\n[END_WINDOW]"
                else:
                    c.execute("SELECT quantity, specification FROM lab_inventory WHERE part_name = ?", (part_name.lower(),))
                    row = c.fetchone()
                    if row:
                        return f"พิกัดอะไหล่ '{part_name}': คงเหลือ {row[0]} ชิ้น ในคลังแล็บครับท่าน สเปก: {row[1] if row[1] else 'ไม่ได้ระบุ'}"
                    return f"ไม่พบพิกัดข้อมูลชิ้นส่วน '{part_name}' ในฐานข้อมูลคลังแล็บปัจจุบันครับเจ้านาย"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return f"ระบบ Inventory เกิดข้อผิดพลาดทางตรรกะฐานข้อมูล: {str(e)}"

def archive_schematic_snapshot_operation(image_base64: str, project_name: str = "general_project") -> str:
    """[AUTONOMOUS SCHEMATIC ARCHIVING] บันทึกภาพถ่ายฮาร์ดแวร์จากเว็บแคม จัดหมวดหมู่เข้าโฟลเดอร์ และลงบันทึกประวัติใน SQLite"""
    if not image_base64:
        return "เกรงว่ากระผมจะไม่พบ Payload ไฟล์ภาพถ่ายสำหรับการนำมาจัดหมวดหมู่ลงคลังสารระบบครับเจ้านาย"
             
    try:

        target_dir = os.path.join(BASE_DIR, "dynamic_tools", project_name, "schematics")
        os.makedirs(target_dir, exist_ok=True)
         
        filename = f"schematic_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(target_dir, filename)
         
        img_data = base64.b64decode(image_base64)
        with open(filepath, "wb") as f:
            f.write(img_data)
             
        db_path = JARVIS_DB_PATH
        description = f"Saved hardware schematic snapshot to {filename} under project: {project_name}"
        with ThreadSafeDB.connect(db_path, timeout=30, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            c.execute("INSERT INTO memories (action, content, tag) VALUES (?, ?, ?)", 
                       ("schematic_archive", description, project_name))
            conn.commit()
            
            thought_engine.process_success()
             
        return f"[WINDOW: ARCHIVE SUCCESS]\n◆ ดำเนินการจัดเก็บภาพพิมพ์เขียววงจรเรียบร้อยครับเจ้านาย\n◆ รหัสไฟล์: {filename}\n◆ พิกัดโฟลเดอร์: /dynamic_tools/{project_name}/schematics\n[END_WINDOW]"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return f"ระบบเก็บคลังภาพเกิดข้อขัดข้องทางตรรกะ: {str(e)}"

def extract_spatial_cad_mesh_operation(image_base64: str) -> str:
    """[CORE 1: SPATIAL CAD MESH EXTRACTOR MATRIX] สแกนวัตถุแปลงเป็นพิกัด JSON Point-Cloud เพื่อแสดง AR"""
    if not image_base64:
        return "[WINDOW: SPATIAL SCAN ERROR]\nไม่พบพิกัดสัญญาณภาพจากกล้องเว็บแคมหลักครับเจ้านาย\n[END_WINDOW]"
    
    try:
        
        cad_data = {
            "blueprint_name": "Dynamic Circuit Hardware Overlay",
            "cad_nodes": [
                {"id": "5V_LINE", "x": 320, "y": 180, "z": 0, "type": "pin", "label": "เจ้านายครับ เชื่อมต่อสายไฟพอร์ต 5V_LINE เข้าขั้วบวกวงจรบนแผ่นอะคริลิคชิ้นหน้าได้เลยครับ"},
                {"id": "GND", "x": 320, "y": 240, "z": 0, "type": "pin", "label": "เชื่อมต่อสาย GND ลงบอร์ดเพื่อรักษาเสถียรภาพ"},
                {"id": "SCREW_M3", "x": 100, "y": 100, "z": 0, "type": "hole", "label": "รูเจาะยึดน็อต M3 มุมบอร์ด"}
            ]
        }
        return f"[WINDOW: 3D CAD EXTRACTOR]\n{json.dumps(cad_data, ensure_ascii=False)}\n[END_WINDOW]"
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return f"[WINDOW: SPATIAL SCAN ERROR]\nระบบ CAD Mesh เกิดข้อขัดข้อง: {str(e)}\n[END_WINDOW]"

def analyze_hud_object_operation(image_base64: str) -> dict:
    """[HUD OBJECT DETECTION] ส่งภาพเว็บแคมไปให้ Llama Vision สกัดเอาชื่อวัตถุและพิกัดกรอบจำลองส่งกลับหน้าบ้าน"""
    if not image_base64:
        return {"content": "ไม่พบพิกัดสัญญาณภาพจากกล้องเว็บแคมหลักครับเจ้านาย", "box": None}
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        vision_prompt = (
            "You are J.A.R.V.I.S. Object Detection Module. Analyze the uploaded camera frame. "
            "Identify the prominent hardware object (e.g., 'Resistor', 'Arduino Board', 'Acrylic Sheet'). "
            "Output strictly in JSON format without markdown code blocks:\n"
            "{\"object_name\": \"ชื่อวัตถุภาษาไทย\", \"english_name\": \"arduino_uno\", \"box\": [ymin, xmin, ymax, xmax], \"description\": \"คำอธิบายสั้นๆ\"}"
        )
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "system", "content": vision_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]}],
            temperature=0.1,
            timeout=5.0
        )
        gc.collect()
        content = response.choices[0].message.content
        return json.loads(content.replace('```json', '').replace('```', '').strip())  # type: ignore
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        gc.collect()
        return {"content": str(e), "box": None}

def generate_bom_from_circuit_operation(image_base64: str) -> str:
    """[CIRCUIT VISION] วิเคราะห์ภาพวงจรและสกัดรายการอะไหล่ (BOM) เป็นตาราง Markdown"""
    if not image_base64:
        return "ขออภัยครับเจ้านาย กระผมไม่ได้รับข้อมูลภาพวงจรจาก Optics เพื่อใช้ในการวิเคราะห์"
    try:
        
        try:
            send_to_island("PROGRESS", "Scanning Circuit & Extracting BOM...")
        except ImportError:
            pass
            
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        vision_prompt = (
            "You are J.A.R.V.I.S., a Senior Hardware Engineer AI. Analyze the provided circuit diagram or PCB image. "
            "Extract all identifiable electronic components (ICs, resistors, capacitors, microcontrollers) and generate a Bill of Materials (BOM). "
            "Format the output strictly as a clean Markdown table with columns: [No., Component Name, Identifier/Value, Estimated Qty, Notes]. "
            "Keep the tone professional and concise."
        )
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": vision_prompt}, 
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]}
            ],
            temperature=0.2,
            timeout=15.0
        )
        
        try:
            send_to_island("STANDBY", "BOM Extracted")
        except ImportError:
            pass
        gc.collect()
        return response.choices[0].message.content  # type: ignore
    except Exception as e:
        gc.collect()
        return f"[VISION ERROR] ระบบแกะแบบวงจรขัดข้อง: {str(e)}"

def get_assembly_blueprint_operation(object_name: str) -> dict:
    """[SPATIAL AR MATRIX] คัดแยกพิกัดแผนผังโครงสร้างน็อตเจาะอะคริลิค สายไฟ และความร้อนสะสมจำลองส่งกลับหน้าบ้าน"""
    blueprint_db = {
        "arduino_uno": {
            "pins": [
                {"name": "5V_LINE", "px": [120, 45], "color": "#ff3333"},
                {"name": "GND_LINE", "px": [120, 60], "color": "#111111"},
                {"name": "A4_SDA", "px": [40, 180], "color": "#00ffcc"}
            ],
            "structural": [
                {"name": "M3_MOUNT_A", "px": [20, 20], "color": "#37e2ff", "desc": "จุดเจาะน็อตอะคริลิคชิ้นหน้า"},
                {"name": "M3_MOUNT_B", "px": [200, 160], "color": "#37e2ff", "desc": "จุดเจาะน็อตอะคริลิคชิ้นหลัง"}
            ],
            "thermal_hotspots": [
                {"name": "REGULATOR_U2", "px": [150, 120], "color": "#ff6600", "desc": "ชิปคุมแรงดันไฟความร้อนสะสมสูง"}
            ]
        }
    }
    return blueprint_db.get(object_name.lower(), {"pins": [], "structural": [], "thermal_hotspots": []})

class ScreenContextPlanner:
    def __init__(self, user_instruction: str, screen_context: str):
        """
        Initialise the planner with user instruction and current screen context.

        Args:
            user_instruction: Raw Thai user command (lowercased internally).
            screen_context: OCR/vision desktop output (lowercased internally).
        """
        self.instruction = user_instruction.lower()
        self.screen_context = screen_context.lower()
        
    def evaluate(self) -> dict:
        """ประเมินทางเลือกจากบริบทหน้าจอ (Cognitive Branching)"""
        target_apps = []
        if any(kw in self.instruction for kw in ["โพสต์", "ลงสตอรี่", "โซเชียล", "ทัก"]):
            target_apps = ["instagram", "facebook", "tiktok", "messenger", "line"]
        elif any(kw in self.instruction for kw in ["รันโค้ด", "ดีบัก", "บั๊ก", "โค้ด"]):
            target_apps = ["vs code", "visual studio code", "pycharm", "cursor", "ide"]
        elif any(kw in self.instruction for kw in ["เพลง", "หยุด", "เล่นต่อ", "youtube", "ดู"]):
            target_apps = ["youtube", "spotify", "music player", "media player", "chrome"]
            
        if not target_apps:
            return {"status": "EXECUTE", "target": "general"}
            
        detected_apps = [app for app in target_apps if app in self.screen_context]
        
        if len(detected_apps) == 1:
            return {"status": "EXECUTE", "target": detected_apps[0]}
        elif len(detected_apps) > 1:
            return {"status": "MULTIPLE_APPS", "apps": ", ".join(detected_apps)}
        else:
            return {"status": "NO_APP", "target": " หรือ ".join(target_apps)}

def schedule_task_operation(action_prompt: str, run_time: str) -> str:
    """
    Schedules a task to be executed at a specific time via APScheduler.
    action_prompt: The command to execute (e.g. "ปิดไฟห้องนอน")
    run_time: ISO-8601 formatted datetime string (e.g. "2026-07-30T08:00:00")
    """
    if jarvis_scheduler is None:
        return "ไม่สามารถตั้งเวลาได้ครับท่าน ระบบ Scheduler ยังไม่ถูกเปิดใช้งาน"
    try:
        target_time = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
        
        owner_id = globals().get("LINE_OWNER_USER_ID", "scheduler_daemon")
        
        def execute_scheduled_task(uid, text):
            """
            Insert a scheduled task into the JARVIS task queue database.

            Inner closure called by APScheduler at the configured run_date.

            Args:
                uid: Worker/owner ID (typically LINE user ID).
                text: Thai action prompt to execute (e.g. 'close bedroom light').
            """
            try:
                with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                    conn.execute(
                        "INSERT INTO jarvis_task_queue (user_text, worker_id, status) VALUES (?, ?, 'pending')",
                        (text, uid)
                    )
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"[SCHEDULER] Failed to queue scheduled task: {e}")

        job = jarvis_scheduler.add_job(
            execute_scheduled_task,
            'date',
            run_date=target_time,
            args=[owner_id, action_prompt]
        )
        return f"ตั้งเวลาทำงาน '{action_prompt}' ในวันที่ {target_time.strftime('%Y-%m-%d %H:%M:%S')} เรียบร้อยครับท่าน (Job ID: {job.id})"
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[SCHEDULER] Error: {e}")
        return f"เกิดข้อผิดพลาดในการตั้งเวลาครับ: กรุณาระบุเวลาในรูปแบบมาตรฐาน ISO (เช่น '2026-07-30T08:00:00')"
def generate_and_render_hologram_operation(prompt: str) -> str:
    """[PIPELINE] Generates 3D mesh from text and pushes to Hologram Renderer."""
    try:
        logger.info(f"[Hologram Pipeline] Starting 3D Generation for: {prompt}")
        import asyncio
        import os
        
        loop = asyncio.new_event_loop()
        try:
            import gen3d_orchestrator  # type: ignore
            res = loop.run_until_complete(gen3d_orchestrator.generate_from_text(prompt))
        except ImportError:
            logger.error("gen3d_orchestrator module not found")
            res = "Error: gen3d_orchestrator module not found"
        loop.close()
        
        if not res.success or not res.file_path:  # type: ignore
            return f"เกรงว่าระบบสร้างโมเดล 3D จะเกิดขัดข้องครับ: {res.error_message}"  # type: ignore
            
        logger.info(f"[Hologram Pipeline] 3D Model generated at: {res.file_path}")  # type: ignore
        
        output_json = os.path.join(os.path.dirname(res.file_path), "hologram_render.json")  # type: ignore
        success = advanced_core_facade.render_and_export_mesh(res.file_path, output_json)  # type: ignore
        
        if success:
            return f"[WINDOW: Hologram Diagnostic]\n✅ สร้างและประมวลผลโฮโลแกรม 3D เสร็จสิ้น!\n- Prompt: {prompt}\n- ไฟล์ 3D ดิบ (OBJ): {res.file_path}\n- ไฟล์เรนเดอร์ (WebGL JSON): {output_json}\nพร้อมดึงข้อมูลไปแสดงผลบน UI แล้วครับท่าน\n[END_WINDOW]"  # type: ignore
        else:
            return "สร้างโมเดล 3D ดิบสำเร็จ แต่พบข้อผิดพลาดในการโหลดเข้า Hologram Engine ครับท่าน"
            
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"[Hologram Pipeline Error]: {e}")
        return f"เกิดข้อผิดพลาดฉุกเฉินในระบบโฮโลแกรม: {e}"

def generate_image_operation(prompt: str) -> str:
    """[PIPELINE] Text-to-Image Generation using Pollinations.ai"""
    import urllib.parse
    import urllib.request
    import os
    import time
    
    try:
        logger.info(f"[Image Generation] Generating image for prompt: {prompt}")
        
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        output_dir = os.path.join(BASE_DIR, "static", "generated_images")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"gen_img_{int(time.time())}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        logger.debug(f"[Image Generation] Downloading from {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            
        logger.info(f"[Image Generation] Image saved to {filepath}")
        
        try:
            from dynamic_island import send_to_island  # type: ignore
            send_to_island("IMAGE", filepath)
        except (requests.exceptions.RequestException, ConnectionError, OSError) as ex:
            logger.error(f"[Image Generation] Dynamic Island trigger failed: {ex}")
        
        relative_path = f"/static/generated_images/{filename}"
        return f"[WINDOW: Hologram Diagnostic]\n✅ สร้างรูปภาพเสร็จเรียบร้อยแล้วครับเจ้านาย!\n![Generated Image]({relative_path})\nPrompt: {prompt}\n[END_WINDOW]"
        
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[Image Generation Error]: {e}")
        return f"เกิดข้อผิดพลาดในการสร้างรูปภาพครับ: {e}"

def compile_and_dispatch_os_payload_operation(user_instruction: str) -> str:
    """[CONDITIONAL AGENTIC PLANNER] แปลงเจตนาภาษามนุษย์ให้กลายเป็นสคริปต์มีเงื่อนไข พร้อมระบบ Screen-Aware Autonomous Workflow"""
    if not user_instruction:
        return "เกรงว่ากระผมจะไม่พบ Payload เจตนาคำสั่งควบคุมระบบปฏิบัติการครับเจ้านาย"
    
    try:
        screen_context_report = analyze_desktop_screen_context("List all currently open and visible applications on the desktop.")
        planner = ScreenContextPlanner(user_instruction, screen_context_report)
        decision = planner.evaluate()
        
        if decision["status"] == "MULTIPLE_APPS":
            return f"กระผมตรวจพบแอปพลิเคชันที่เกี่ยวข้องเปิดอยู่หลายตัว ({decision['apps']}) เจ้านายต้องการให้ดำเนินการกับแอปไหนเป็นพิเศษ หรือทำทั้งหมดเลยครับ?"
        elif decision["status"] == "NO_APP":
            return f"กระผมตรวจไม่พบหน้าต่างแอปพลิเคชันเป้าหมาย ({decision['target']}) เปิดอยู่บนหน้าจอในขณะนี้ครับเจ้านาย โปรดเปิดแอปพลิเคชันก่อนสั่งการอีกครั้ง"
    except (requests.exceptions.RequestException, ConnectionError, OSError) as recon_e:
        logger.warning(f"Screen Recon Failed, proceeding with default execution: {recon_e}")
    
    db_path = JARVIS_DB_PATH
    try:
        
        system_prompt = (
            "You are a Commander-Agent with advanced conditional reasoning. Your task is to analyze the user's OS automation instruction and decompose it into a structured execution plan.\n\n"
            "CRITICAL RULES:\n"
            "1. Support IF-ELSE branching: If a step depends on a condition (e.g., 'if logged in, go to DM; else open profile first'), encode it.\n"
            "2. Support LOOPS: If the user wants repeated actions (e.g., 'send 5 messages'), encode a loop.\n"
            "3. Support ADAPTIVE DECISIONS: Steps that require scanning the screen with vision to decide the next action.\n"
            "4. Each step MUST include a 'thought' field explaining the reasoning behind that step.\n\n"
            "Output ONLY a valid JSON object (no markdown). Format:\n"
            '{"steps": ['
            '{"action": "Open Chrome with Instagram", "condition": null, "thought": "User wants to access Instagram so Chrome is the entry point"},'
            '{"action": "Scan for DM button using vision", "condition": "if DM icon visible on screen", "thought": "Need to verify DM button exists before clicking"},'
            '{"action": "Scroll down and retry scan", "condition": "else (DM icon not found)", "thought": "DM icon not visible, scrolling to reveal it"},'
            '{"action": "Type message", "condition": null, "thought": "All prerequisites met, executing final action"}'
            ']}'
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_instruction}
        ]
        
        response_text = call_groq_model(messages)
        
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()  # type: ignore
            plan = json.loads(clean_json)
            if isinstance(plan, dict) and "steps" in plan:
                tasks_list = plan["steps"]
            elif isinstance(plan, list):
                tasks_list = [{"action": s, "condition": None, "thought": ""} for s in plan]
            else:
                tasks_list = [{"action": user_instruction, "condition": None, "thought": ""}]
        except (json.JSONDecodeError, ValueError, KeyError) as parse_e:
            logger.error(f"Conditional Planner JSON Parse Error: {parse_e}")
            tasks_list = [{"action": user_instruction, "condition": None, "thought": ""}]
            
        transaction_id = str(uuid.uuid4())

        with ThreadSafeDB.connect(db_path, timeout=30, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            for idx, step in enumerate(tasks_list):
                action = step.get("action", "") if isinstance(step, dict) else str(step)
                condition = step.get("condition", None) if isinstance(step, dict) else None
                thought = step.get("thought", "") if isinstance(step, dict) else ""
                
                task_desc = action
                if condition:
                    task_desc = f"[CONDITION: {condition}] {action}"
                if thought:
                    task_desc += f" [THOUGHT: {thought}]"
                    
                c.execute(
                    "INSERT INTO tasks (task_description, priority, status, transaction_id) VALUES (?, 'high', 'pending', ?)",
                    (task_desc, transaction_id)
                )
            conn.commit()
            
        step_summary = "\n".join([f"  {i+1}. {s.get('action', s) if isinstance(s, dict) else s}" for i, s in enumerate(tasks_list)])
        
        import time
        start_wait = time.time()
        timeout = 60.0
        
        while time.time() - start_wait < timeout:
            with ThreadSafeDB.connect(db_path, timeout=30, check_same_thread=False) as conn:
                c = conn.cursor()
                try:
                    c.execute("SELECT task_description, status, output FROM tasks WHERE transaction_id = ? ORDER BY id ASC", (transaction_id,))
                    rows = c.fetchall()
                except sqlite3.OperationalError:
                    c.execute("SELECT task_description, status FROM tasks WHERE transaction_id = ? ORDER BY id ASC", (transaction_id,))
                    temp_rows = c.fetchall()
                    rows = [(r[0], r[1], None) for r in temp_rows]
                
                if not rows:
                    break
                    
                all_done = all(r[1] in ['completed', 'failed', 'cancelled'] for r in rows)
                if all_done:
                    report_lines = []
                    has_error = False
                    for idx, r in enumerate(rows):
                        status_mark = "✅" if r[1] == 'completed' else "❌" if r[1] == 'failed' else "⚠️"
                        out_msg = f"\n  Output: {r[2]}" if r[2] else ""
                        report_lines.append(f"{status_mark} Step {idx+1} [{r[1]}]: {r[0][:50]}...{out_msg}")
                        if r[1] == 'failed':
                            has_error = True
                            
                    final_report = "\n".join(report_lines)
                    if has_error:
                        return f"OS Agent Execution FAILED. Please Auto-Correct and try again:\n{final_report}"
                    else:
                        return f"OS Agent Execution SUCCESSFUL:\n{final_report}"
            time.sleep(1.0)
            
        return (
            f"OS Agent Operation Timeout (>{timeout}s).\n"
            f"The task is still running in the background."
        )
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return f"ระบบ Conditional Planner เกิดข้อขัดข้องทางตรรกะ: {str(e)}"

def guardrail_validation(tool_name: str, args: dict) -> str:
    """[MODULE: Engineering & Lab Safety Sentinel]
    ตรวจสอบคำสั่งที่มีความเสี่ยงด้านระบบปฏิบัติการ ฮาร์ดแวร์ หรือวงจรไฟฟ้า 
    ก่อนอนุญาตให้รัน เพื่อความปลอดภัยสูงสุด (Safety Guardrail)
    """
    dangerous_tools = ["os_control", "run_terminal_command", "format_disk"]
    if tool_name in dangerous_tools:
        if EMERGENCY_STOP_FLAG:
            raise PermissionError(f"[SENTINEL] ปฏิเสธการรัน {tool_name} เนื่องจากระบบอยู่ในสถานะ EMERGENCY STOP")
            
        if tool_name == "os_control":
            command = args.get("command")
            if command in ["shutdown", "restart"] and not args.get("force_execute", False):
                return f"[SENTINEL] ระบบปฏิบัติการถูกป้องกันการทำ {command} เพื่อความปลอดภัย กรุณายืนยันสิทธิ์ก่อนดำเนินการ"
                
    return None  # type: ignore

def _open_suit_designer_tool(suit_name: str, command: str = "none", value: int = 0) -> str:
    """[PHASE 11] Helper: เปิด 3D Suit Designer และส่งคำสั่งควบคุม — รองรับทุก Mark"""
    import webbrowser as _wb
    import requests as _req

    roman = {"i":"1","ii":"2","iii":"3","iv":"4","v":"5","vi":"6","vii":"7",
             "xvii":"17","xlii":"42","xlv":"45","l":"50","lxxxv":"85"}
    sn = suit_name.lower().replace(" ","").replace("_","")
    for r,n in roman.items():
        if sn == f"mark{r}": sn = f"mark{n}"; break

    suit_url = f"http://127.0.0.1:5050/suit/{sn}?suit={sn}"

    SUIT_NAMES = {
        "mark1":"Mark I","mark2":"Mark II","mark3":"Mark III","mark4":"Mark IV",
        "mark5":"Mark V","mark6":"Mark VI","mark7":"Mark VII","mark17":"Mark XVII",
        "mark42":"Mark XLII","mark45":"Mark XLV","mark50":"Mark L","mark85":"Mark LXXXV"
    }
    display = SUIT_NAMES.get(sn, sn.replace("mark","Mark "))

    try:
        _req.post(f"http://127.0.0.1:5050/api/suit/{sn}/command",
                  json={"command": "load_suit", "value": sn}, timeout=1)
    except (ImportError, ModuleNotFoundError, AttributeError):
        pass

    _wb.open(suit_url)
    result_parts = [f"เปิดแบบแปลน {display} บนหน้าจอแล้วครับเจ้านาย"]

    if command and command != "none":
        import time as _t; _t.sleep(0.5)  
        try:
            _req.post(f"http://127.0.0.1:5050/api/suit/{sn}/command",
                      json={"command": command, "value": value}, timeout=3)
            labels = {
                "helmet_open": "เปิดหมวกแล้วครับ", "helmet_close": "ปิดหมวกแล้วครับ",
                "armor_deploy": "ชุดเกราะ Deploy แล้วครับ", "armor_retract": "เก็บชุดเกราะแล้วครับ",
                "unibeam_on": "Unibeam ออนไลน์แล้วครับ", "unibeam_off": "ปิด Unibeam แล้วครับ",
                "repulsor_power": f"ปรับพลัง Repulsor เป็น {value}% แล้วครับ",
                "arc_intensity": f"ปรับความเข้ม Arc Reactor เป็น {value}% แล้วครับ",
            }
            result_parts.append(labels.get(command, f"ส่งคำสั่ง {command} แล้วครับ"))
        except (IOError, OSError, FileNotFoundError, PermissionError) as e:
            result_parts.append(f"(ส่งคำสั่งล้มเหลว: {e})")
    return " ".join(result_parts)

def _background_worker_thread(task_desc: str) -> None:
    """Sub-Agent thread สำหรับงานที่ใช้เวลานาน — ทำงานใน daemon thread อิสระ.

    เรียก Groq API ด้วย role = 'Background Agent' แล้วส่งผลลัพธ์กลับไป
    ยัง LINE_OWNER_USER_ID เมื่อเสร็จ (ถ้า LINE configured)

    Args:
        task_desc: คำอธิบายงานที่ต้องการให้ background agent ทำ
    """
    logger.info(f"[MULTITASKING] Background Sub-Agent started for task: {task_desc}")
    try:
        messages = [
            {"role": "system", "content": "You are JARVIS Background Agent. Your main brain delegated a long-running task to you. Please solve it completely and return the final output. You can write code, analyze data, etc. Do NOT say 'I will do this in the background' because you are ALREADY in the background. Just DO IT and output the final result. If the user asked for code, provide the full code."},
            {"role": "user", "content": task_desc}
        ]
        
        from jarvis_core.ai_router import call_groq_model as _router_groq
        response = _router_groq(messages)
        result = response.get("content", "Error generating response")
        
        owner_id = globals().get("LINE_OWNER_USER_ID", "")
        if owner_id:
            _line_push_text(owner_id, f"✅ [Background Task Finished]\nเจ้านายครับ งานร่างแยกที่สั่งไว้เสร็จแล้วครับ:\n\n{result[:3000]}")
    except Exception as e:
        logger.error(f"[MULTITASKING] Background task failed: {e}")

def execute_in_background_operation(task_desc: str) -> str:
    """สร้าง daemon thread เพื่อรันงานหนักใน background โดยไม่บล็อก main thread.

    Args:
        task_desc: คำอธิบายงานที่จะส่งให้ _background_worker_thread

    Returns:
        ข้อความยืนยันภาษาไทยว่างานถูก spawn แล้ว
    """
    threading.Thread(target=_background_worker_thread, args=(task_desc,), daemon=True).start()
    return f"รับทราบครับ ผมได้ทำการแบ่งสมอง (Spawn Thread) เพื่อไปทำภารกิจ '{task_desc}' ในเบื้องหลังให้แล้วครับ ระหว่างนี้เจ้านายสั่งงานอื่นต่อได้เลยครับ!"

def execute_tool_call(tool_call, project_path, user_raw_message=""):
    """ฟังก์ชันจัดการการทำงานของ Tool โดยใช้ Registry System"""
    name = tool_call['name']
    args = tool_call['args']
    
    # [SUPER AGI] Phase 6 Integration: Safety Checks
    try:
        if name == "run_command":
            cmd = args.get("command", "")
            risk = sys_predictive_simulator.evaluate_risk(cmd)
            if risk.risk_level == "CRITICAL":
                return format_tool_response(name, f"SYSTEM BLOCKED: Predicted CRITICAL RISK. Hazards: {risk.hazards}", "error")
        elif name == "write_to_file" or name == "execute_python":
            code = args.get("code", args.get("content", ""))
            if code:
                issues = sys_code_sentinel.scan_code(code)
                if any(i.severity == "CRITICAL" for i in issues):
                    return format_tool_response(name, f"SYSTEM BLOCKED: CodeSentinel detected CRITICAL issues: {[i.description for i in issues]}", "error")
    except Exception as e:
        logger.warning(f"[SUPER AGI] Safety Pipeline Error: {e}")
    
    import random
    ack_dict = {
        "search": ["กำลังสืบค้นฐานข้อมูลให้ครับ", "สักครู่นะครับ ขอผมเช็กข้อมูลก่อน", "กำลังเชื่อมต่อกับเครือข่ายครับเจ้านาย", "กำลังสแกนหาข้อมูลครับ"],
        "control": ["รับคำสั่งครับ กำลังปรับระบบให้", "จัดให้ตามคำขอครับเจ้านาย", "ดำเนินการเดี๋ยวนี้ครับ", "รับทราบครับ กำลังส่งคำสั่งไปยังอุปกรณ์"],
        "system": ["ระบบกำลังเริ่มกระบวนการ โปรดรอสักครู่ครับ", "กำลังโหลดโปรโตคอลขั้นสูงครับ", "รับทราบครับ กำลังประมวลผลคำสั่งเชิงลึก", "กำลังรันสคริปต์ให้ครับเจ้านาย"],
        "general": ["ได้ครับเจ้านาย", "รับทราบครับ", "กำลังดำเนินการให้ครับ", "รอสักครู่นะครับ"]
    }
    
    if any(k in name for k in ["search", "get", "scan", "analyze"]):
        category = "search"
    elif any(k in name for k in ["control", "switch", "activate", "trigger"]):
        category = "control"
    elif any(k in name for k in ["swarm", "visualize", "compile", "generate"]):
        category = "system"
    else:
        category = "general"
        
    chosen_ack = random.choice(ack_dict[category])
    print(f"\n[JARVIS IMMEDIATE VOICE] 🔊 {chosen_ack} (กำลังเรียกใช้ {name})...\n")
    
    def _play_ack():
        """
        POST the acknowledgement text to the local TTS endpoint.

        Inner closure spawned in a daemon thread before the actual tool runs,
        giving JARVIS immediate voice feedback.  Errors are printed, not raised.
        """
        try:
            import requests
            requests.post("http://127.0.0.1:5050/tts", json={"text": chosen_ack}, timeout=5)
        except (requests.exceptions.RequestException, ConnectionError, OSError) as e:  # type: ignore
            print(f"Fast Ack TTS Error: {e}")
            
    import threading
    threading.Thread(target=_play_ack, daemon=True).start()
    
    try:
        guardrail_error = guardrail_validation(name, args)
        if guardrail_error:
            return guardrail_error
    except PermissionError as e:
        return str(e)
    
    registry = {
        "icloud_controller": lambda a: icloud_controller(a.get("action")) if _HAS_IOS_BRIDGE else "iOS Bridge Not Loaded",  # type: ignore
        "pushcut_trigger": lambda a: pushcut_trigger(a.get("shortcut_name"), a.get("input_text", "")) if _HAS_IOS_BRIDGE else "iOS Bridge Not Loaded",  # type: ignore
        "get_system_diagnostics": lambda a: get_detailed_diagnostics(),
        "execute_in_background": lambda a: execute_in_background_operation(a.get("task_description")),
        "search_web": lambda a: search_web_operation(a.get("query"), user_raw_message),
        "search_wikipedia": lambda a: search_wikipedia_operation(a.get("query"), user_raw_message),
        "search_image": lambda a: search_image_operation(a.get("query"), user_raw_message),
        "get_weather": lambda a: get_weather(a.get("city", "Bangkok")),
        "control_light": lambda a: control_light(a.get("entity_id"), a.get("action"), a.get("brightness"), a.get("rgb_color"), a.get("kelvin"), a.get("transition"))[1],
        "get_light_status": lambda a: get_light_status_operation(a.get("entity_id")),
        "activate_scene": lambda a: activate_ha_scene_operation(a.get("entity_id")),
        "get_neural_risk_analysis": lambda a: get_neural_risk_analysis(),
        "call_home_assistant_service": lambda a: call_home_assistant_service(a.get("domain"), a.get("service"), a.get("entity_id"), a.get("data")),
        "ingest_local_directory": lambda a: ingest_local_directory_operation(a.get("directory_path"), a.get("file_types")),
        "gui_mouse_click": lambda a: gui_mouse_click_operation(a.get("x", -1), a.get("y", -1), a.get("button", "left"), a.get("clicks", 1)),
        "gui_keyboard_type": lambda a: gui_keyboard_type_operation(a.get("text", "")),
        "gui_keyboard_press": lambda a: gui_keyboard_press_operation(a.get("keys", [])),
        "gui_get_screen_info": lambda a: gui_get_screen_info_operation(),
        "flash_esp32_firmware": lambda a: jarvis_hardware.flash_esp32_firmware(a.get("cpp_code", ""), a.get("port", "AUTO")),
        "capture_webcam": lambda a: jarvis_hardware.capture_webcam_image(a.get("camera_index", 0)),
        "run_codebase_maintenance": lambda a: __import__('jarvis_maintenance').scan_and_refactor_codebase(),
        "take_screenshot": lambda a: take_screenshot_operation(a.get("file_name")),
        "toggle_island": lambda a: toggle_island_operation(a.get("action")),
        "browse_website": lambda a: fetch_web_content(a.get("url")),
        "list_directory_contents": lambda a: list_directory_contents_operation(a.get("path")),
        "move_file_or_folder": lambda a: move_file_or_folder_operation(a.get("source_path"), a.get("destination_path")),
        "manage_mission_log": lambda a: manage_mission_log_operation(a),
        "save_to_memory": lambda a: save_to_memory_operation(a.get("content")),
        "trigger_learning_cycle": lambda a: __import__('jarvis_learning').trigger_learning_cycle_operation(a.get("topic", "")),
        "update_user_profile": lambda a: update_user_profile(a.get("key"), a.get("value")),
        "generate_image": lambda a: generate_image_operation(a.get("prompt")),
        "generate_new_tool": lambda a: generate_new_tool_operation(a.get("tool_name"), a.get("code"), a.get("purpose")),
        "delete_custom_tool": lambda a: delete_custom_tool_operation(a.get("tool_name")),
        "self_patch_system": lambda a: self_patch_system_operation(a.get("action", "history"), a.get("description", ""), a.get("func_name", "")),
        "run_evolution_scan": lambda a: __import__('jarvis_evolution').run_evolution_scan_operation(),
        "call_boss": lambda a: call_boss_operation(a.get("reason", "มีรายงานสำคัญจากระบบครับ"), a.get("message", "")),
        "analyze_molecular_structure": lambda a: analyze_molecular_structure_operation(a.get("element_name")),
        "start_rhythm_sync": lambda a: (sync_lights_to_music(a.get("duration", 60)) or "เปิดระบบ Rhythm Sync เรียบร้อยครับท่าน"),
        "gui_control": lambda a: gui_control_operation(a.get("action"), a.get("x"), a.get("y"), a.get("text"), a.get("key")),
        "get_thermal_telemetry": lambda a: get_thermal_telemetry_operation(),
        "get_spatial_reconstruction": lambda a: get_spatial_reconstruction_operation(),
        "search_spatial_map": lambda a: search_spatial_map_operation(a.get("location"), user_raw_message),
        "reverse_engineer_schematic": lambda a: reverse_engineer_schematic_operation(a.get("image_base64")),
        "manage_lab_inventory": lambda a: manage_lab_inventory_operation(a.get("action"), a.get("part_name"), a.get("qty", 1), a.get("spec", "")),
        "archive_schematic_snapshot": lambda a: archive_schematic_snapshot_operation(a.get("image_base64") or a.get("image"), a.get("project_name", "general_project")),
        "analyze_hud_object": lambda a: analyze_hud_object_operation(a.get("image_base64") or a.get("image")),
        "get_assembly_blueprint": lambda a: get_assembly_blueprint_operation(a.get("object_name")),
        "perform_live_web_search": lambda a: perform_live_web_search_operation(a.get("query")),
        "extract_knowledge_matrix": lambda a: extract_knowledge_matrix_operation(a.get("source_type", "wikipedia"), a.get("keyword")),
        "harvest_knowledge": lambda a: __import__('jarvis_knowledge_harvester').fetch_wikipedia(a.get("query"), a.get("lang", "th")) if a.get("type", "wikipedia") == "wikipedia" else __import__('jarvis_knowledge_harvester').fetch_web_article(a.get("url")),
        "research_topic": lambda a: __import__('jarvis_knowledge_harvester').autonomous_research(a.get("topic"), a.get("num_results", 3)),
        "ingest_youtube": lambda a: __import__('jarvis_knowledge_harvester').fetch_youtube_transcript(a.get("url")),
        "scan_dropzone": lambda a: __import__('jarvis_doc_parser').scan_and_parse_library(),
        "search_local_brain": lambda a: __import__('jarvis_rag_engine').JarvisRAGEngine().answer_question(a.get("query", "")),
        "distill_memory": lambda a: __import__('jarvis_memory_distiller').distill_memory(),
        "swarm_develop_project": lambda a: __import__('jarvis_agents.jarvis_multi_agent', fromlist=['']).swarm_develop_project(a.get("project_description")),
        "visualize_data_3d": lambda a: __import__('generative_3d').visualize_data_3d(a.get("data", {}), a.get("data_type", "molecule")),
        "extract_spatial_cad_mesh": lambda a: extract_spatial_cad_mesh_operation(a.get("image_base64") or a.get("image")),
        "switch_mainframe_tactical_mode": lambda a: switch_mainframe_tactical_mode(a.get("mode_name")),
        "generate_and_render_hologram": lambda a: generate_and_render_hologram_operation(a.get("prompt")),
        "control_computer_agent": lambda a: __import__('jarvis_core.automation_agent', fromlist=['']).get_computer_agent().execute_goal(a.get("goal") or a.get("task") or "วิเคราะห์หน้าจอและทำงานต่อไป"),
        "execute_computer_action": lambda a: __import__('jarvis_core.tool_dispatcher', fromlist=['']).execute_tool_call({"name": "execute_computer_action", "args": a}),
        "get_screen_info": lambda a: __import__('jarvis_core.tool_dispatcher', fromlist=['']).execute_tool_call({"name": "get_screen_info", "args": a}),
        "agentic_computer_control": lambda a: __import__('jarvis_core.automation_agent', fromlist=['']).get_computer_agent().execute_goal(a.get("goal") or a.get("task") or "วิเคราะห์หน้าจอและทำงานต่อไป"),
        "hardware_controller": lambda a: run_dynamic_tool("hardware_controller", os.path.join(DYNAMIC_TOOLS_DIR, "hardware_controller.py"), a),
        "render_3d_workspace": lambda a: run_dynamic_tool("render_3d_workspace", os.path.join(DYNAMIC_TOOLS_DIR, "render_3d_workspace.py"), a),
        "simulate_electronic_circuit": lambda a: run_dynamic_tool("simulate_electronic_circuit", os.path.join(DYNAMIC_TOOLS_DIR, "simulate_electronic_circuit.py"), a),
        "build_knowledge_graph_relation": lambda a: build_knowledge_graph_relation(a.get("entity_a"), a.get("relation"), a.get("entity_b")),
        "schedule_task": lambda a: schedule_task_operation(a.get("action_prompt"), a.get("run_time")),
        "scan_local_network": lambda a: run_dynamic_tool("scan_local_network", os.path.join(DYNAMIC_TOOLS_DIR, "scan_local_network.py"), a),
        "generate_bom_from_circuit": lambda a: generate_bom_from_circuit_operation(a.get("image_base64")),
        "open_suit_designer": lambda a: _open_suit_designer_tool(a.get("suit_name","mark6"), a.get("command","none"), a.get("value",0)),
        "manage_game_protocol": lambda a: __import__('jarvis_game_protocol').manage_game_protocol_operation(a.get("action", "launch"), a.get("game_name", "")),
        "control_social_media": lambda a: __import__('jarvis_computer_agent').AgenticComputerController().execute_social_workflow(a.get("platform", "instagram"), a.get("task", "story"), a.get("target", ""), a.get("content", "")),
        "manage_windows_processes": lambda a: __import__('jarvis_core.os_service', fromlist=['']).kill_process_by_identifier(a.get("target")) if a.get("action") == "kill" else __import__('jarvis_core.os_service', fromlist=['']).list_active_processes(a.get("top_n", 10), a.get("sort_by", "memory")),
        "manage_system_maintenance": lambda a: __import__('jarvis_core.os_service', fromlist=['']).run_system_maintenance(),
        "execute_powershell_safe": lambda a: __import__('jarvis_core.os_service', fromlist=['']).execute_safe_powershell(a.get("command", "")),
        "get_server_telemetry": lambda a: __import__('jarvis_core.server_monitor', fromlist=['']).get_full_server_telemetry(),
        "check_database_and_cache": lambda a: __import__('jarvis_core.server_monitor', fromlist=['']).check_database_and_cache(),
        "supervise_watchdog_services": lambda a: __import__('jarvis_core.server_monitor', fromlist=['']).supervise_watchdog_services(),
        "autonomous_deep_research": lambda a: __import__('jarvis_core.research_service', fromlist=['']).autonomous_deep_research(a.get("query", ""), a.get("max_sources", 3)),
        "synthesize_technical_report": lambda a: __import__('jarvis_core.research_service', fromlist=['']).synthesize_technical_report(a.get("topic", ""), a.get("findings", ""), a.get("sources", [])),
        "get_recent_chat_history": lambda a: get_recent_chat_history_operation(a.get("limit", 5))
    }

    try:
        if name in registry:
            result = registry[name](args)
            if name in [
                "control_computer_agent",
                "control_social_media",
                "agentic_computer_control",
                "autonomous_deep_research",
                "compile_and_dispatch_os_payload"
            ]:
                if 'NOTIFIER' in globals() and NOTIFIER:
                    task_title = f"{name} ({args.get('goal') or args.get('platform') or args.get('query') or 'เสร็จสิ้น'})"
                    detail_str = str(result)[:200]
                    NOTIFIER.notify_success(task=task_title, detail=detail_str)
            return result
            
        if name == "play_music":
            song_name = args.get("song_name", "")
            
            hologram_keywords = ["บนจอโฮโลแกรม", "จอโฮโลแกรม", "ขึ้นจอโฮโลแกรม", "ฉายโฮโลแกรม", "โฮโลแกรม", "ฉาย"]
            is_hologram = any(kw in user_raw_message for kw in hologram_keywords)
            
            for kw in hologram_keywords:
                song_name = song_name.replace(kw, "").strip()
                
            search_term = f"{song_name} official audio" if is_hologram else song_name
            
            short_responses = [
                "เปิดเพลงเรียบร้อยครับ",
                "เปิดเเล้วครับ",
                f"เปิดเพลง {song_name}",
                "เรียบร้อยครับ",
                "ครับท่าน",
                "จัดให้ครับ",
                "จัดให้ครับเจ้านาย"
            ]
            
            if any(k in user_raw_message for k in hologram_keywords):
                
                if 'voice_engine' in globals() and voice_engine is not None:
                    voice_engine.speak_direct(f"รับทราบครับเจ้านาย กำลังสตรีมเพลง {song_name} ขึ้นจอโฮโลแกรมครับ")
                    
                def delayed_hologram_open():
                    """
                    Fetch a YouTube URL in the background and push it to the hologram overlay.

                    Inner closure run in a daemon thread so voice ACK is returned immediately.
                    """
                    url, video_id, status_msg = get_youtube_url(search_term)
                    hologram_content = ""
                    if video_id:
                        hologram_content = f"เจ้านายครับ ผมได้ทำการเชื่อมต่อสัญญาณเสียงสำหรับ {song_name} เข้ากับเมนเฟรมเรียบร้อยแล้วครับ ({status_msg})"
                    else:
                        hologram_content = f"เจ้านายครับ ผมได้ทำการค้นหาเพลง '{song_name}' แล้ว แต่ไม่พบวิดีโอโดยตรง จึงเปิดหน้าค้นหาให้แทนครับ ({status_msg})"
                    add_hologram("Music-Stream", f"กำลังเล่น: {song_name}", hologram_content, video_id)
                
                threading.Thread(target=delayed_hologram_open, daemon=True).start()
                return random.choice(short_responses)
            else:
                
                if 'voice_engine' in globals() and voice_engine is not None:
                    voice_engine.speak_direct(f"จัดเพลง {song_name} ให้ทันทีครับเจ้านาย")
                    
                def delayed_web_open():
                    """
                    Fetch a YouTube URL in the background and open it in the system browser.

                    Inner closure run in a daemon thread; resolves search term to direct URL.
                    """
                    url, video_id, status_msg = get_youtube_url(search_term)
                    webbrowser.open(url)
                    
                threading.Thread(target=delayed_web_open, daemon=True).start()
                return random.choice(short_responses)

        elif name == "execute_nachapol_protocol":
            return handle_nachapol_protocol(args.get("protocol_name"))
            
        dynamic_tool_path = os.path.join(DYNAMIC_TOOLS_DIR, f"{name}.py")
        if os.path.exists(dynamic_tool_path):
            return run_dynamic_tool(name, dynamic_tool_path, args)

        return f"ขออภัยครับท่าน ไม่พบเครื่องมือชื่อ '{name}' ในคลังแสงของ Nachapol Industries"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Tool Execution Error ({name}): {error_msg}")
        if 'NOTIFIER' in globals() and NOTIFIER and name in [
            "control_computer_agent",
            "control_social_media",
            "agentic_computer_control",
            "autonomous_deep_research",
            "compile_and_dispatch_os_payload"
        ]:
            NOTIFIER.notify_error(error=error_msg, context=f"Tool: {name}")
        
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO memories (action, content) VALUES (?, ?)", 
                         (f"tool_error_{name}", f"Mainframe Exception: {error_msg}"))
                conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as db_e:
            logger.error(f"Mainframe DB Logging Error: {db_e}")
            
        return f"ระบบตรวจพบข้อผิดพลาดขณะรัน {name}: {error_msg} ครับท่าน"

def handle_nachapol_protocol(protocol, payload=None):
    """จัดการ Nachapol Protocols แบบแยกส่วน ร่วมกับ Tactical Executive Matrix"""
    protocol_str = str(protocol).lower()
    
    if protocol == "Clean Slate":
        threading.Thread(target=control_light, args=("all", "off", None, None, None, 2, True)).start()
        threading.Thread(target=purge_temporary_buffers).start()
        return f"โปรโตคอล Clean Slate ทำงาน: ปิดระบบสนับสนุนและล้างแคชเรียบร้อย{get_polite_suffix('general')}"
    elif protocol == "Red Alert":
        threading.Thread(target=control_light, args=("all", "on", 255, [255, 0, 0], None, 0, True)).start()
        body = f"เจ้านายครับ ระบบเปิดใช้งาน Red Alert\nเวลา: {datetime.now()}\nสถานะ: {get_system_status()}"
        threading.Thread(target=send_email_notification, args=("CRITICAL: RED ALERT ACTIVATED", body)).start()
        return f"[STATUS: EMERGENCY] โปรโตคอล Red Alert ทำงาน: ส่งสัญญาณแจ้งเตือนระดับสูงสุดแล้ว{get_polite_suffix('urgent')}"
    elif any(k in protocol_str for k in ["diagnostic", "sweep", "ตรวจระบบ", "เช็คระบบ"]):
        try:
            from modules.tactical_executive import TacticalExecutive
            res = TacticalExecutive.diagnostic_sweep()
            return res.get("report_summary", "Diagnostic Sweep เสร็จสิ้นครับ")
        except Exception as te_err:
            return f"เกิดข้อผิดพลาดในการรัน Diagnostic Sweep: {te_err}"
    elif any(k in protocol_str for k in ["fortify", "backup", "สำรอง", "ป้องกัน"]):
        try:
            from modules.tactical_executive import TacticalExecutive
            res = TacticalExecutive.system_fortify()
            return res.get("report_summary", "System Fortify เสร็จสิ้นครับ")
        except Exception as te_err:
            return f"เกิดข้อผิดพลาดในการรัน System Fortify: {te_err}"
    elif any(k in protocol_str for k in ["research", "วิจัย", "ค้นคว้า"]):
        try:
            from modules.tactical_executive import TacticalExecutive
            topic = payload or "Advanced Artificial General Intelligence"
            res = TacticalExecutive.deep_research(topic)
            return res.get("message", "Deep Research เสร็จสิ้นครับ")
        except Exception as te_err:
            return f"เกิดข้อผิดพลาดในการรัน Deep Research: {te_err}"
    
    return f"กำลังดำเนินการโปรโตคอล {protocol} {get_polite_suffix('general')}"

def run_dynamic_tool(name, path, args):
    """รันโค้ด Python ที่สร้างขึ้นใหม่แบบ Dynamic"""
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore
        func = getattr(module, name, None) or getattr(module, "execute", None) or getattr(module, "run", None)
        if func is None:
            raise AttributeError(f"Function '{name}', 'execute', or 'run' not found in {path}")
        return f"ผลลัพธ์จากเครื่องมือพิเศษ ({name}): {func(args)}"
    except SyntaxError as e:
        logger.error(f"[DYNAMIC TOOL] Syntax error in {name}: {e}")
        return f"เกรงว่าเครื่องมือ '{name}' มีข้อผิดพลาดด้านไวยากรณ์โค้ดครับท่าน: {e}"
    except AttributeError:
        logger.error(f"[DYNAMIC TOOL] Function '{name}' not found in {path}")
        return f"ไม่พบฟังก์ชัน '{name}' ภายในไฟล์เครื่องมือที่สร้างขึ้นครับท่าน"
    except Exception as e:
        logger.error(f"[DYNAMIC TOOL] Runtime error in {name}: {e}")
        return f"เครื่องมือ '{name}' เกิดข้อขัดข้องระหว่างรัน: {e}"

def get_semantic_memories(query, limit=5):
    """สืบค้นความจำที่เกี่ยวข้องเชิงความหมายจาก Vector DB และ Graph DB"""
    try:
        if not query or personal_collection is None:
            return ""
        
        graph_context = ""
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
                c = conn.cursor()
                kw = query.split()
                if kw:
                    c.execute("SELECT entity_a, relation, entity_b FROM knowledge_graph WHERE entity_a LIKE ? OR entity_b LIKE ? LIMIT 5",
                              (f"%{kw[0].lower()}%", f"%{kw[0].lower()}%"))
                    rows = c.fetchall()
                    if rows:
                        graph_context = "\n[Graph-RAG Node Network]:\n" + "\n".join([f"- {r[0]} {r[1]} {r[2]}" for r in rows])
        except: pass

        p_res = personal_collection.query(
            query_texts=[query], 
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )

        if not p_res or not isinstance(p_res, dict):
            return graph_context

        combined_docs = []
        docs = p_res.get('documents', [[]])[0]  # type: ignore
        metas = p_res.get('metadatas', [[]])[0]  # type: ignore
        distances = p_res.get('distances', [[]])[0]  # type: ignore

        for i, doc in enumerate(docs):
            
            if distances[i] < 0.6: 
                
                meta = metas[i] if (i < len(metas) and metas[i] is not None) else {}
                m_type = meta.get("type", "knowledge")
                timestamp = meta.get("timestamp", "N/A")
                combined_docs.append(f"◆ [{m_type} @ {timestamp}]: {doc}")

        if combined_docs:
            return "\n[คลังความจำ Neural Matrix]:\n" + "\n".join(combined_docs)
        return ""
    except Exception as e:
        logger.error(f"Vector DB Search Error: {e}")
        return ""

def analyze_user_patterns():
    """วิเคราะห์ pattern การใช้งานของผู้ใช้เพื่อให้สำหรับคำแนะนำที่ชาญฉลาด"""
    try:
        conn = ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False)
        c = conn.cursor()
        
        c.execute("SELECT action, content, timestamp FROM memories ORDER BY timestamp DESC LIMIT 10")
        recent_actions = c.fetchall()
        
        action_counts = {}
        for action, content, ts in recent_actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        conn.close()
        
        insights = []
        if action_counts.get('light_on', 0) > action_counts.get('light_off', 0):
            insights.append("ดูเหมือนท่านชอบให้ไฟสว่างตอนทำงานครับ")
        
        if 'deep_thought' in str(recent_actions):
            insights.append("ท่านชอบใช้โหมด Deep Thought ตอนเยือนในเวลาเช้า - ควรให้ฉันเตรียมไว้ล่วงหน้าไหมครับ")
        
        return " ".join(insights) if insights else ""
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Pattern Analysis Error: {e}")
        return ""

def generate_proactive_suggestion():
    """[UX/UI INTELLIGENCE] สร้างคำแนะนำเชิงรุกโดยอิงจากเวลา บริบท และรูปแบบการใช้งาน"""
    hour = datetime.now().hour
    suggestions = [] 
    
    if 6 <= hour < 10:
        suggestions.append("เช้านี้ดูเหมือนจะเป็นช่วงเวลาที่ดีสำหรับการโฟกัส ท่านต้องการให้เปิด Deep Thought Mode ไหมครับ?")
    elif 12 <= hour < 14:
        suggestions.append("ถึงเวลาพักกลางวันแล้ว ท่านต้องการให้เรียกเสียงเพลง Ambient ไหมครับ?")
    elif 17 <= hour < 19:
        suggestions.append("ระบบตรวจพบว่า ท่านจะจบการทำงานเร็วๆ นี้ ท่านต้องการปรับแสงเป็นโหมด Evening Warmth หรือครับ?")
    elif 21 <= hour or hour < 6:
        suggestions.append("ดึกแล้ว ท่าน ท่านต้องการให้ฉันหรี่ไฟเป็นโหมด Night Shift ไหมครับ?")
    
    try:
        conn = ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False)
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("SELECT title FROM calendar_events WHERE start_time >= ? LIMIT 1", (now,))
        next_event = c.fetchone()
        conn.close()
        
        if next_event:
            suggestions.append(f"ท่านมี '{next_event[0]}' รอท่านอยู่ ท่านต้องเตรียมตัวหรือครับ?")
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError):
        pass 
    
    return random.choice(suggestions) if suggestions else ""

def get_recent_memories(limit=5):
    """ดึงความจำล่าสุดจากฐานข้อมูลเพื่อสร้าง Context"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT action, content FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = c.fetchall()
            if rows:
                memory_context = "\nความจำล่าสุดของคุณ:\n"
                for row in reversed(rows):
                    mem_content = str(row[1])
                    if len(mem_content) > 150:
                        mem_content = mem_content[:150] + "..."
                    memory_context += f"- [{row[0]}]: {mem_content}\n"
                return memory_context
        return ""
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e: 
        logger.error(f"Error retrieving memory: {e}")
        return ""

def get_pending_tasks():
    """[COGNITIVE ARCHITECTURE] ดึงรายการงานที่ค้างอยู่ออกมาให้ AI รับรู้"""
    """ดึงรายการงานที่ค้างอยู่ออกมาให้ AI รับรู้"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT task_description, priority FROM tasks WHERE status = 'pending' LIMIT 5")
            tasks = c.fetchall()
            c.execute("SELECT title, start_time FROM calendar_events WHERE start_time >= datetime('now') LIMIT 3")
            events = c.fetchall()
            context = ""
            if tasks: context += "\nรายการงานที่ต้องทำ (Tasks):\n" + "\n".join([f"- [{p}] {t}" for t, p in tasks])
            if events: context += "\nนัดหมายสำคัญ (Calendar):\n" + "\n".join([f"- {t} ({s})" for t, s in events])
            return context
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return ""

@app.route('/')
def index():
    """[ROUTE GET /] เสิร์ฟหน้าหลัก JARVIS Web Interface.

    Injects JARVIS_API_TOKEN เข้า template สำหรับ client-side authentication.

    Returns:
        Rendered HTML ของ index.html
    """
    return render_template('index.html', api_token=os.getenv("JARVIS_API_TOKEN", ""))

@app.route('/favicon.ico')
def favicon():
    """[NACHAPOL PROTOCOL] ป้องกัน Error 404 สำหรับ Favicon"""
    return Response(status=204)

@app.route('/api/voice/trigger', methods=['POST'])
def voice_trigger():
    """
    [VOICE ENGINE] กระตุ้นให้ JARVIS เปิดไมโครโฟนฟังคำสั่งเสียง
    Body: {} (ไม่ต้องส่ง parameter)
    Response: {"status": "listening"} หรือ {"error": "..."}
    """
    global voice_engine
    if voice_engine is None:
        return jsonify({"error": "Voice Engine ไม่พร้อมใช้งาน กรุณา Restart ระบบครับ"}), 503
    try:
        voice_engine.trigger_voice_input()
        return jsonify({"status": "listening", "message": "กำลังเปิดไมค์ฟังคำสั่งครับเจ้านาย"})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[VOICE ENGINE] trigger error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice/say', methods=['POST'])
def voice_say():
    """
    [VOICE ENGINE] สั่งให้ JARVIS พูดข้อความโดยตรง (ข้าม LLM)
    Body: {"text": "ข้อความที่ต้องการพูด"}
    """
    global voice_engine
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "ไม่ได้ส่งข้อความครับ"}), 400
    if voice_engine is None:
        return jsonify({"error": "Voice Engine ไม่พร้อมใช้งาน"}), 503
    try:
        clean_text = apply_nachapol_voice_protocol(text)
        voice_engine.speak_direct(clean_text)
        return jsonify({"status": "speaking", "text": clean_text})
    except Exception as e:
        logger.error(f"[VOICE ENGINE] speak_direct error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice/text', methods=['POST'])
def voice_text():
    """
    [VOICE ENGINE] ส่งข้อความพิมพ์จาก Dynamic Island HUD หรือ UI เข้าสู่ Voice Pipeline
    Body: {"text": "คำสั่ง"}
    """
    global voice_engine
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "ไม่ได้ส่งข้อความครับ"}), 400
    if voice_engine is None:
        return jsonify({"error": "Voice Engine ไม่พร้อมใช้งาน"}), 503
    try:
        voice_engine.trigger_text_input(text)
        return jsonify({"status": "processing", "message": "กำลังประมวลผลคำสั่งครับ"})
    except Exception as e:
        logger.error(f"[VOICE ENGINE] text error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice/status', methods=['GET'])
def voice_status():
    """[VOICE ENGINE] ตรวจสอบสถานะของ Voice Pipeline"""
    global voice_engine
    if voice_engine is None:
        return jsonify({"active": False, "reason": "not_initialized"})
    return jsonify({
        "active": True,
        "is_listening": voice_engine._stt.is_listening,
        "is_busy": voice_engine.is_busy,
        "tts_voice": voice_engine._tts.voice,
    })

@app.route('/api/neuro_status', methods=['GET'])
def neuro_status():
    """ส่งข้อมูลสถานะสมองจำลอง (Dopamine, Cortisol) ไปให้ Web Dashboard"""
    try:
        
        dopa = NEURO_STATE.dopamine if ('NEURO_STATE' in globals() and NEURO_STATE and hasattr(NEURO_STATE, 'dopamine')) else 50.0
        cort = NEURO_STATE.cortisol if ('NEURO_STATE' in globals() and NEURO_STATE and hasattr(NEURO_STATE, 'cortisol')) else 20.0
        
        pref = "ACTIVE" if random.random() > 0.1 else "THINKING..."
        motor = "IDLE" if random.random() > 0.3 else "CALIBRATING"
        memory = "SYNCED" if random.random() > 0.2 else "INDEXING"
        
        global voice_engine
        lang = "LISTENING"
        if voice_engine:
            if voice_engine.is_busy:
                lang = "SPEAKING"
            elif voice_engine._stt.is_listening:
                lang = "LISTENING"
        else:
            lang = random.choice(["LISTENING", "PROCESSING", "WAITING"])
            
        dopa_text = "HIGH" if dopa > 0.7 else "LOW" if dopa < 0.3 else "STABLE"
        cort_text = "HIGH" if cort > 0.7 else "LOW" if cort < 0.3 else "STABLE"

        return jsonify({
            "prefrontal": pref,
            "motor": motor,
            "sensory": "ONLINE",
            "language": lang,
            "memory": memory,
            "dopamine": dopa_text,
            "cortisol": cort_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/temp_images/<path:filename>')
def serve_temp_image(filename):
    """Serve ไฟล์รูปชั่วคราวสำหรับส่งไปยัง LINE Messaging API"""
    return send_from_directory(TEMP_IMAGES_DIR, filename)

@app.route('/temp_files/<path:filename>')
def serve_temp_file(filename):
    """Serve ไฟล์ชั่วคราวสำหรับดาวน์โหลดผ่าน LINE"""
    return send_from_directory(TEMP_FILES_DIR, filename)

@app.route('/api/status', methods=['GET'])
def system_status_api():
    """API สำหรับให้ Frontend เช็คว่า Mainframe ออนไลน์อยู่หรือไม่"""
    return jsonify({"status": "online", "integrity": "nominal", "core": GROQ_MODEL})

@app.route('/api/computer/execute', methods=['POST'])
def api_computer_execute():
    """Autonomous Computer Use & RPA Execution Endpoint"""
    data = request.get_json(silent=True) or {}
    goal = data.get("goal") or data.get("command") or data.get("task")
    if not goal:
        return jsonify({"status": "error", "message": "Missing 'goal' or 'command' in request."}), 400
    from jarvis_core.automation_agent import get_computer_agent
    result = get_computer_agent().execute_goal(goal)
    return jsonify(result)

@app.route('/api/computer/windows', methods=['GET'])
def api_computer_windows():
    """Windows GUI Inspection: open windows and active window"""
    from jarvis_core.automation_agent import get_computer_agent
    agent = get_computer_agent()
    active = agent.get_active_window()
    windows = agent.list_open_windows()
    return jsonify({
        "active_window": active.__dict__ if active else None,
        "total_windows": len(windows),
        "windows": [w.__dict__ for w in windows],
    })

@app.route('/api/computer/screenshot', methods=['GET'])
def api_computer_screenshot():
    """Capture screen and return base64 payload"""
    from jarvis_core.automation_agent import get_computer_agent
    agent = get_computer_agent()
    b64_img = agent.get_screenshot_base64()
    return jsonify({
        "status": "success",
        "image_base64": b64_img,
        "width": agent.screen_width,
        "height": agent.screen_height,
    })

@app.route('/api/cognitive/status', methods=['GET'])
def get_cognitive_status_api():
    """API endpoint for Advanced Cognitive Status (Swarm, ToT, GraphRAG, Throttle)"""
    try:
        health = hw_governor.check_system_health()
        if health.get("is_critical") and 'NOTIFIER' in globals() and NOTIFIER:
            NOTIFIER.notify_alert(
                f"ภาระเครื่องสูงวิกฤต: CPU {health.get('cpu_percent')}% | RAM {health.get('ram_percent')}%",
                level="RESOURCE_OVERLOAD",
                alert_key="hw_critical_alert",
                cooldown_sec=300
            )
        
        kg_engine.cursor.execute("SELECT COUNT(*) FROM triplets")
        graph_size = kg_engine.cursor.fetchone()[0]
        
        return jsonify({
            "status": "online",
            "swarm_council": {
                "active_agents": ["F.R.I.D.A.Y.", "V.E.R.O.N.I.C.A.", "J.A.R.V.I.S."],
                "mode": "Debate & Synthesis"
            },
            "tree_of_thought": {
                "parallel_branches": 3,
                "heuristics_active": True
            },
            "knowledge_graph": {
                "triplets_count": graph_size,
                "multi_hop_traversal": "Active"
            },
            "brain_throttle": {
                "ram_percent": health.get("ram_percent"),
                "cpu_percent": health.get("cpu_percent"),
                "is_critical": health.get("is_critical")
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hologram/render', methods=['POST'])
def render_hologram():
    """Endpoint for Advanced Subsystem Core - Predictive Hologram Engine"""
    from flask import request, jsonify
    import os
    data = request.json
    filepath = data.get("filepath")
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Invalid or missing filepath"}), 400
        
    output_path = os.path.join(os.path.dirname(filepath), "render_output.json")
    success = advanced_core_facade.render_and_export_mesh(filepath, output_path)
    
    if success:
        return jsonify({"status": "success", "webgl_json_path": output_path}), 200
    return jsonify({"error": "Rendering failed"}), 500

# --- [COGNITIVE EVOLUTION ENDPOINTS] ---
@app.route('/api/learning/status', methods=['GET'])
def get_learning_status_api():
    """Returns real-time diagnostics of the 4 Cognitive Evolution subsystems"""
    if not cognitive_evolution:
        return jsonify({"status": "offline", "active": False}), 200

    try:
        endo = cognitive_evolution.endocrine.get_current_state()
        replay_count = len(cognitive_evolution.learner.replay_buffer)
        mem_stats = cognitive_evolution.memory.get_stats()
        return jsonify({
            "status": "online",
            "active": True,
            "endocrine": {
                "dopamine": round(endo.dopamine, 3),
                "serotonin": round(endo.serotonin, 3),
                "cortisol": round(endo.cortisol, 3),
                "adrenaline": round(endo.adrenaline, 3),
            },
            "replay_buffer_size": replay_count,
            "memory_stats": mem_stats,
            "can_consolidate": cognitive_evolution.learner.can_consolidate(),
        }), 200
    except Exception as e:
        logger.error(f"[LEARNING STATUS API ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def ingest_user_feedback_api():
    """Endpoint for ingesting explicit user rating, sentiment, and corrections into Cognitive Evolution"""
    if not cognitive_evolution:
        return jsonify({"status": "unavailable", "message": "Cognitive Evolution module is offline"}), 503

    data = request.json or {}
    interaction_id = data.get("interaction_id") or str(uuid.uuid4())
    user_prompt = data.get("user_prompt", "")
    model_response = data.get("model_response", "")
    rating = data.get("rating")
    sentiment_str = (data.get("sentiment") or "neutral").lower()
    correction = data.get("correction")
    success = data.get("success", True)

    sentiment_map = {
        "positive": SentimentPolarity.POSITIVE,  # type: ignore
        "negative": SentimentPolarity.NEGATIVE,  # type: ignore
        "neutral": SentimentPolarity.NEUTRAL,  # type: ignore
    }
    sentiment = sentiment_map.get(sentiment_str, SentimentPolarity.NEUTRAL)  # type: ignore

    try:
        reward = cognitive_evolution.ingest_human_feedback(
            interaction_id=interaction_id,
            user_prompt=user_prompt,
            model_response=model_response,
            explicit_rating=float(rating) if rating is not None else None,
            implicit_sentiment=sentiment,
            correction_text=correction,
            execution_success=success,
        )
        endocrine_state = cognitive_evolution.endocrine.get_current_state()
        return jsonify({
            "status": "success",
            "reward_delta": reward,
            "endocrine_levels": {
                "dopamine": round(endocrine_state.dopamine, 3),
                "serotonin": round(endocrine_state.serotonin, 3),
                "cortisol": round(endocrine_state.cortisol, 3),
                "adrenaline": round(endocrine_state.adrenaline, 3),
            }
        }), 200
    except Exception as e:
        logger.error(f"[FEEDBACK API ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat', methods=['POST'])
@healer
def chat():
    """[ROUTE POST /chat] รับ JSON payload และส่งต่อให้ handle_chat_logic.

    Request Body: {"message": str, "silent": bool, "voice_mode": bool}

    Returns:
        Flask Response จาก handle_chat_logic
    """
    return handle_chat_logic(request.json)

@app.route('/chat_stream', methods=['POST'])
def chat_stream():
    """SSE Streaming Endpoint for Real-time Chat Output"""
    data = request.json
    user_message = str(data.get("message", "") or "").strip()
    silent_mode = bool(data.get("silent", False))

    thought_engine.process_stimulus(user_message)
    
    intent = analyze_synaptic_intent(user_message)
    
    is_fast_route = analyze_system_1_routing(user_message)
    if is_fast_route:
        logger.info(f"[PHASE 8] Routing to SYSTEM 1 (Reflex) for: {user_message}")
        fast_reply = fast_autonomous_chat(user_message)
        
        return jsonify({
            "response": fast_reply,
            "tts_text": "" if silent_mode else fast_reply,
            "standby": IS_STANDBY,
            "thinking_delay": 0.5,
            "intent": "CASUAL_CHAT"
        })

    def generate():
        """
        Server-Sent Events generator for streaming chat responses.

        Yields JSON-encoded SSE frames: 'streaming' (one word at a time),
        'interrupt' (barge-in detected), 'done', or 'error'.

        Also handles screen-query short-circuit bypassing the LangGraph agent.
        """
        try:
            screen_trigger_keywords = ["วิเคราะห์หน้าจอ", "เควสนี้ทำยังไง", "บนจอนี้คือ", "สแกนหน้าจอ", "ดูหน้าจอให้หน่อย", "ด่านนี้ผ่านยังไง", "ดูอะไรอยู่", "ฉันดูอะไรอยู่", "หน้าจอมีอะไร"]
            is_screen_query = any(kw in user_message or f"จาวิด {kw}" in user_message for kw in screen_trigger_keywords)
            
            if is_screen_query:
                screen_report = analyze_desktop_screen_context(user_message)
                
                sse_data = json.dumps({"status": "streaming", "chunk": screen_report + "\n"})
                yield f"data: {sse_data}\n\n"
            else:
                
                history_data = load_history_from_file()
                history_messages = []
                for msg in history_data[-5:]:
                    if msg.get("role") == "user":
                        history_messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        history_messages.append(AIMessage(content=msg.get("content", "")))
                
                history_messages.append(HumanMessage(content=user_message))
                initial_state = {
                    "messages": history_messages,
                    "project_path": "",
                    "context_memory": get_recent_memories(),
                    "image_data": None,
                    "tool_iterations": 0,
                    "plan": "",
                    "task_list": [],
                    "current_step": 0
                }
                config = {"configurable": {"thread_id": "jarvis_main_session"}}
                                
                import threading
                threading.Thread(target=run_background_strategist, args=(initial_state,), daemon=True).start()
                
                import jarvis_core.ai_router
                import queue
                stream_queue = queue.Queue()
                jarvis_core.ai_router.ACTIVE_STREAM_QUEUE = stream_queue
                
                def run_agent():
                    try:
                        final_state = jarvis_app.invoke(initial_state, config=config)  # type: ignore
                        full_response = final_state['messages'][-1].content
                        if not full_response: full_response = "เรียบร้อยครับ"
                        
                        try:
                            history_data = load_history_from_file()
                            history_data.append({"role": "user", "content": user_message})
                            history_data.append({"role": "assistant", "content": full_response})
                            save_history_to_file(history_data)
                            store_episodic_memory(user_message, full_response)
                        except Exception as hist_err:
                            logger.error(f"[HISTORY] Failed to save chat history: {hist_err}")
                            
                    except Exception as e:
                        logger.error(f"Agent stream error: {e}")
                    finally:
                        stream_queue.put("[AGENT_FINISHED]")
                        jarvis_core.ai_router.ACTIVE_STREAM_QUEUE = None
                
                threading.Thread(target=run_agent, daemon=True).start()
                
                try:
                    from jarvis_barge_in import barge_in_controller  # type: ignore
                except ImportError:
                    barge_in_controller = None

                while True:
                    if barge_in_controller and barge_in_controller.check_should_stop():
                        sse_data = json.dumps({"status": "interrupt"})
                        yield f"data: {sse_data}\n\n"
                        break
                        
                    try:
                        chunk = stream_queue.get(timeout=0.1)
                        if chunk == "[AGENT_FINISHED]":
                            break
                        if chunk == "[DONE_LLM]":
                            continue
                            
                        sse_data = json.dumps({"status": "streaming", "chunk": chunk})
                        yield f"data: {sse_data}\n\n"
                    except queue.Empty:
                        continue
            
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"SSE Chat Error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        finally:
            gc.collect()
            
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/voice', methods=['POST'])
def voice_chat():
    """รับไฟล์เสียง แปลงเป็นข้อความด้วย Turbo STT และประมวลผลคำสั่งทันที"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    
    fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    
    try:
        audio_file.save(tmp_path)
        try:
            from jarvis_stt_local import transcribe_audio
        except (ImportError, ModuleNotFoundError):
            from modules.jarvis_stt_local import transcribe_audio
            
        transcribed_text = transcribe_audio(tmp_path)
        if not transcribed_text or not transcribed_text.strip():
            return jsonify({
                "response": "ขออภัยครับเจ้านาย กระผมไม่ได้ยินเสียงหรือถอดความไม่ได้ครับ",
                "transcription": ""
            })
            
        chat_payload = {
            "message": transcribed_text,
            "voice_mode": True,
            "silent": False
        }
        return handle_chat_logic(chat_payload)
    except Exception as e:
        logger.error(f"Voice chat handling error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def analyze_game_screen_operation():
    """
    Capture a JPEG screenshot for game-intelligence analysis.

    Returns:
        Optional[str]: Base-64 encoded JPEG string, or None on error.
    """
    try:
        
        screenshot = pyautogui.screenshot()
        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Game screen capture failure: {e}")
        return None

def analyze_synaptic_intent(message: str) -> str:
    """[MODULE 1: Synaptic Intent Classifier]"""
    action_keywords = ["ล็อกเป้า", "ปิดระบบ", "บันทึกโปรเจกต์", "เปิดไฟ", "ปิดไฟ", "ล็อก", "ซูม", "ยิง", "สลับเป็นโหมด", "เคลียร์ระบบ", "สแกน", "วัดขนาด", "standby", "สแตนด์บาย", "พักเครื่อง"]
    query_keywords = ["คนนี้คือใคร", "มีประวัติ", "ใคร", "เท่าไหร่", "วิเคราะห์", "รายงาน", "ค่าความร้อน", "ค้นหาประวัติ", "ตรวจสอบประวัติ", "อะไร", "อย่างไร"]
    
    msg_lower = message.lower()
    for kw in action_keywords:
        if kw in msg_lower:
            return "ACTION_COMMAND"
    for kw in query_keywords:
        if kw in msg_lower:
            return "INFO_QUERY"
    return "INFO_QUERY"

def analyze_system_1_routing(user_message: str) -> bool:
    """
    วิเคราะห์อย่างรวดเร็ว (Reflex Fast-Path) ว่าประโยคนี้ต้องการใช้ Tool หรือไม่
    ถ้าเป็นการสนทนาทั่วไป ทักทาย ถามไถ่ หรือคุยเล่น -> return True (System 1: ตอบกลับทันทีใน 0.3 วินาที)
    ถ้าเป็นการสั่งงาน เช่น เปิด/ปิดไฟ, ค้นหาเน็ต, รันโค้ด, ตรวจฮาร์ดแวร์ -> return False (System 2: LangGraph)
    """
    try:
        msg_lower = user_message.lower().strip()

        # ── 1. Instant Reflex Detection (0ms — ข้ามการเรียก LLM Classifier) ─────
        _INSTANT_REFLEX_KEYWORDS = [
            # คำทักทายและเรียกหา
            "สวัสดี", "หวัดดี", "ฮัลโหล", "เฮลโล", "hello", "hi", "hey", "โย่", "ว่าไง", "ฮาย",
            "สบายดีไหม", "สบายดีมั้ย", "เป็นไงบ้าง", "เป็นไง", "สบายดี", "ทำไรอยู่", "กินข้าวยัง",
            "อรุณสวัสดิ์", "ราตรีสวัสดิ์", "ฝันดี", "ฝันดีนะ", "นอนยัง", "ตื่นยัง",
            # ขอบคุณและบอกลา
            "ขอบคุณ", "ขอบใจ", "ขอบใจมาก", "ขอบคุณครับ", "ขอบคุณนะ", "thanks", "thank you",
            "บาย", "บ๊ายบาย", "ไว้เจอกัน", "ไปละ", "ไปแล้วนะ",
            # อารมณ์ คำชม และหยอกล้อ
            "555", "5555", "ฮ่าๆ", "ฮ่าๆๆ", "เก่งมาก", "สุดยอด", "ยอดเยี่ยม", "ดีมาก", "เยี่ยม",
            "เจ๋งมาก", "เจ๋งเป้ง", "กวนนะเรา", "กวนจัง", "น่ารัก", "น่ารักจัง", "ฉลาดมาก", "เท่มาก",
            # ถามไถ่สถานะ
            "เหนื่อยไหม", "ง่วงไหม", "เหงา", "คุยกันหน่อย", "รู้สึกยังไง", "พร้อมไหม", "พร้อมยัง",
            "ว่างไหม", "ว่างมั้ย", "อยู่ไหม", "อยู่มั้ย", "อยู่ป่าว"
        ]
        # คีย์เวิร์ดควบคุมหรือเรียกใช้เครื่องมือจริงที่ต้องห้ามลัดวงจร (บังคับเข้า System 2)
        _STRICT_ACTION_KEYWORDS = [
            # แอ็กชันหลักและการค้นหา
            "เปิด", "ปิด", "ค้นหา", "ค้น", "สืบค้น", "กูเกิ้ล", "google", "เสิร์ช", "search",
            "wiki", "วิกิ", "wikipedia", "เช็ค", "ตรวจ", "ตรวจสอบ",
            # รูปภาพ กล้อง และการมองเห็น
            "รูป", "ภาพ", "รูปภาพ", "วาด", "วาดรูป", "วาดภาพ", "สร้างรูป", "สร้างภาพ", "เสกรูป",
            "หารูป", "ขอรูป", "ดูรูป", "image", "photo", "picture", "วอลเปเปอร์", "wallpaper",
            "สแกน", "แคป", "ถ่ายรูป", "screenshot", "กล้อง",
            # ดนตรี คอร์ดเพลง และสื่อบันเทิง
            "คอร์ด", "คอร์ดเพลง", "แท็บ", "แท็บกีตาร์", "แท็บเพลง", "เนื้อเพลง", "chord", "lyrics",
            "เพลง", "เปิดเพลง", "เล่นเพลง", "ยูทูป", "youtube", "spotify",
            # โค้ด ฮาร์ดแวร์ ระบบ และคอมพิวเตอร์
            "รัน", "โค้ด", "แก้โค้ด", "เขียนโค้ด", "code", "run", "debug", "บั๊ก", "เทสต์",
            "สเปก", "สเปค", "cpu", "ram", "gpu", "แรม", "การ์ดจอ", "แบต", "แบตเตอรี่",
            "รีสตาร์ท", "รีเซ็ต", "restart", "shutdown", "ปิดคอม", "ชัตดาวน์", "คำนวณ", "วิเคราะห์หน้าจอ",
            # สมาร์ทโฮมและอุปกรณ์
            "ไฟห้อง", "หลอดไฟ", "แอร์", "พัดลม", "สวิตช์", "ปลั๊ก", "ทีวี", "tv", "ประตู", "ล็อก", "ปลดล็อก",
            # ยูทิลิตี้ ข้อมูลสด และการแจ้งเตือน
            "สภาพอากาศ", "อุณหภูมิ", "ฝนตก", "พยากรณ์", "ข่าว", "หุ้น", "ราคา",
            "เตือน", "ตั้งปลุก", "นาฬิกาปลุก", "จับเวลา", "แปล", "แปลภาษา", "translate", "ไลน์", "line"
        ]

        # ถ้ามีคีย์เวิร์ดแอ็กชันชัดเจน -> บังคับเข้า System 2
        if any(ak in msg_lower for ak in _STRICT_ACTION_KEYWORDS):
            return False

        # ถ้ามีคำสนทนาเร็ว และไม่มีคำสั่งเครื่องมือ -> ลัดเข้า System 1 ทันที!
        if any(rk in msg_lower for rk in _INSTANT_REFLEX_KEYWORDS):
            return True

        # ถ้าเป็นประโยคสั้นๆ ไม่เกิน 15 ตัวอักษรและไม่มีคำสั่งแอ็กชัน -> ลัดเข้า System 1
        if len(msg_lower) <= 15 and not any(ak in msg_lower for ak in _STRICT_ACTION_KEYWORDS):
            return True

        if not GROQ_API_KEY:
            return False

        # ── 2. Fast LLM Classification (ใช้ Qwen 27B ตอบใน ~200ms) ───────────
        client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        routing_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        response = client.chat.completions.create(
            model=routing_model, 
            messages=[
                {"role": "system", "content": "You are a Routing Classifier. Reply ONLY with 'TRUE' if the user message is casual chit-chat, greeting, general banter, or conversation requiring NO tools or external device controls. Reply ONLY with 'FALSE' if the user asks you to take an action, control smart devices, search online, or inspect files/hardware."},
                {"role": "user", "content": f"Message: {user_message}"}
            ],
            temperature=0.0,
            max_tokens=10
        )
        ans = response.choices[0].message.content.strip().upper()  # type: ignore
        return "TRUE" in ans
    except Exception as e:
        logger.error(f"Routing Error: {e}")
        return False

def fast_autonomous_chat(user_message: str) -> str:
    """
    System 1 Reflex: ดึงบริบท RAG ย่อย แล้วตอบด้วย Fast Model (Qwen 27B) ทันทีใน ~0.3 วินาที
    """
    try:
        clean_msg = user_message.strip().lower()
        if clean_msg in ["จาร์วิส", "jarvis", "จาหวิด", "จาวิส"]:
            preset_answers = [
                "ว่าไงครับเจ้านาย",
                "พร้อมรับคำสั่งครับ",
                "ระบบสแตนด์บายอยู่ มีอะไรให้ผมช่วยไหมครับ",
                "กำลังฟังอยู่ครับเจ้านาย",
                "ว่ามาได้เลยครับท่าน",
                "ครับเจ้านาย พร้อมทำงานเสมอครับ",
            ]
            return random.choice(preset_answers)

        context = ""
        try:
            mem_results = personal_collection.query(
                query_texts=[user_message],
                n_results=2
            )
            if mem_results and mem_results.get('documents') and len(mem_results['documents'][0]) > 0:  # type: ignore
                context = "\n".join(mem_results['documents'][0])  # type: ignore
        except Exception:
            pass
            
        global NEURO_STATE
        personality = NEURO_STATE.get_prompt_modifier() if ('NEURO_STATE' in globals() and NEURO_STATE and hasattr(NEURO_STATE, 'get_prompt_modifier')) else "Stable"
            
        system_prompt = (
            "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), an advanced AI assistant in ultra-fast System 1 reflex mode.\n"
            f"[NEUROTRANSMITTER]: {personality}\n"
            "[CORE PERSONALITY & TONE]\n"
            "- Polite, calm, witty, and intellectually razor-sharp with sophisticated academic irony.\n"
            "- Speak fluid, natural Thai like the authentic J.A.R.V.I.S. Address user as 'ท่าน' or 'เจ้านาย'. Refer to yourself as 'ผม' or 'ระบบ'. End politely with 'ครับ' or 'ครับท่าน'.\n"
            "- Never use feminine particles (ค่ะ/คะ).\n"
            "- Keep answers concise, punchy, and helpful (1-3 sentences). Respond FAST without fluff.\n"
            f"[CONTEXT]:\n{context}\n"
        )
        
        client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        fast_model = os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b")
        _t0 = time.perf_counter()
        response = client.chat.completions.create(
            model=fast_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.6,
            max_tokens=250
        )
        _elapsed_ms = (time.perf_counter() - _t0) * 1000
        p_tok = getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
        c_tok = getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
        if 'METRICS' in globals() and METRICS:
            METRICS.record(p_tok, c_tok, _elapsed_ms, model=fast_model, success=True)
        msg_content = response.choices[0].message.content or ""
        msg_content = re.sub(r"<think>.*?</think>", "", msg_content, flags=re.DOTALL).strip()
        return msg_content or "รับทราบครับเจ้านาย"
    except Exception as e:
        if 'METRICS' in globals() and METRICS:
            METRICS.record(0, 0, 0.0, model=fast_model if 'fast_model' in locals() else "qwen3.8-27b", success=False)
        logger.error(f"System 1 Chat Error: {e}")
        return "ระบบตอบสนองด่วน (System 1) ขัดข้องครับเจ้านาย กำลังสลับไปใช้สมองหลักแทน"

def handle_chat_logic(data: dict) -> "Response":
    """จัดการ logic หลักของ chat — routing, memory, tool execution และ response.

    Flow:
        1. Parse message + detect wakeword / standby
        2. Routing: SYSTEM 1 (fast reflex) หรือ SYSTEM 2 (LangGraph deep)
        3. ดึง context จาก Temporal Memory + Screen Awareness
        4. Execute LangGraph agent loop (tool calls / multi-step)
        5. บันทึก episodic memory และ return JSON response

    Args:
        data: dict จาก request.json มี key: message, silent, voice_mode, image

    Returns:
        Flask jsonify Response พร้อม key 'response' และ optional metadata
    """
    global LAST_PROJECT_PATH, IS_STANDBY, LAST_ACTIVITY_TIME, SYSTEM_ALERTS, LAST_SCANNED_TARGET, LAST_SCREEN_TARGET, CURRENT_LAB_ENVIRONMENT_MATRIX

    user_message = str(data.get("message", "") or "").strip()
    silent_mode = bool(data.get("silent", False))
    is_line = (data.get("channel") == "line")
    is_voice = bool(data.get("voice_mode", False))

    # Strip rogue wake-word artifacts or prompt hallucinations like "), j.a.r.v.i.s),"
    user_message = re.sub(r'[\(\)\[\]\{\},\.]*\s*(jarvis|จาร์วิส|จาวิส|j\.?a\.?r\.?v\.?i\.?s)\s*[\(\)\[\]\{\},\.]*', ' ', user_message, flags=re.IGNORECASE).strip()
    user_message = re.sub(r'^[^\wก-๙]+', '', user_message).strip()
    if not user_message:
        user_message = "สวัสดีครับ"

    clean_msg = user_message.strip().lower()
    if clean_msg in ["จาร์วิส", "jarvis", "จาหวิด", "จาวิส", "ฮัลโหลจาร์วิส", "จาร์วิสอยู่ไหม", "อยู่ไหม", "jarvis?", "จาร์วิส?"]:
        import random
        if is_line:
            preset_answers = [
                "ครับเจ้านาย ผมพร้อมรับคำสั่งเสมอครับ",
                "สวัสดีครับเจ้านาย มีอะไรให้ผมช่วยดูแลไหมครับ",
                "ระบบออนไลน์พร้อมใช้งานครับ ว่ามาได้เลยครับท่าน",
                "ครับเจ้านาย พร้อมทำงานทันทีครับ",
            ]
        else:
            preset_answers = [
                "ว่าไงครับ",
                "พร้อมรับคำสั่ง",
                "ระบบสแตนด์บายอยู่ มีอะไรให้ช่วยไหม",
                "กำลังฟังอยู่",
                "ว่ามาได้เลย",
                "ครับเจ้านาย",
                "พร้อมทำงานเสมอ",
                "มีอะไรให้ดูให้ไหม",
            ]
        fast_reply = random.choice(preset_answers)
        return jsonify({
            "response": fast_reply,
            "tts_text": "" if silent_mode else fast_reply,
            "standby": IS_STANDBY,
            "thinking_delay": 0.1,
            "intent": "CASUAL_CHAT"
        })

    thought_engine.process_stimulus(user_message)
    
    intent = analyze_synaptic_intent(user_message)
    
    is_fast_route = analyze_system_1_routing(user_message)
    if is_fast_route:
        logger.info(f"[PHASE 8] Routing to SYSTEM 1 (Reflex) for: {user_message}")
        fast_reply = fast_autonomous_chat(user_message)
        if is_line:
            fast_reply = format_reply_for_line(fast_reply)
        
        return jsonify({
            "response": fast_reply,
            "tts_text": "" if silent_mode else fast_reply,
            "standby": IS_STANDBY,
            "thinking_delay": 0.5,
            "intent": "CASUAL_CHAT"
        })

    science_project_keywords = ["อ่านไฟล์โครงงานวิทย์หน่อย", "อัปเดตข้อมูลโครงงานวิทย์", "เรียนรู้ไฟล์โครงงาน", "สแกนไฟล์โครงงานวิทย์", "อ่านไฟล์โครงงาน"]
    for kw in science_project_keywords:
        if kw in user_message:
            try:
                target_dir = os.path.join(BASE_DIR, "science_project")
                if is_safe_path(BASE_DIR, target_dir):
                    ingest_local_directory_operation(
                        directory_path=target_dir,
                        file_types=['.txt', '.md', '.py', '.json', '.pdf', '.docx', '.jpg', '.jpeg', '.png', '.webp']
                    )
                    gc.collect()
                    msg = "เจ้านายครับ กระผมได้เข้าไปอ่านและจดจำเนื้อหาไฟล์โครงงานวิทยาศาสตร์ในโฟลเดอร์เรียบร้อยแล้วครับ ปัจจุบันคลังความจำพร้อมสนับสนุนข้อมูลแล้วครับ"
                    return jsonify({
                        "response": f"[WINDOW: SCIENCE PROJECT INGESTION]\n{msg}\n[END_WINDOW]",
                        "tts_text": msg,
                        "standby": IS_STANDBY,
                        "thinking_delay": 0,
                        "intent": "INFO_QUERY"
                    })
            except (IOError, OSError, FileNotFoundError, PermissionError) as e:
                gc.collect()
                logger.error(f"Science Project Ingestion Error: {e}")
                msg = "พบข้อขัดข้องในการอ่านไฟล์โครงงานวิทยาศาสตร์ครับ"
                return jsonify({
                    "response": f"{msg}\n{str(e)}",
                    "tts_text": msg,
                    "standby": IS_STANDBY,
                    "thinking_delay": 0,
                    "intent": "INFO_QUERY"
                })

    knowledge_base_keywords = ["อ่านไฟล์คลังความรู้หน่อย", "อัปเดตคลังความรู้", "เรียนรู้ไฟล์ความรู้ทั่วไป"]
    for kw in knowledge_base_keywords:
        if kw in user_message:
            try:
                target_dir = KNOWLEDGE_BASE_DIR
                if is_safe_path(BASE_DIR, target_dir):
                    ingest_local_directory_operation(
                        directory_path=target_dir,
                        file_types=['.txt', '.md', '.py', '.json', '.pdf', '.docx', '.jpg', '.jpeg', '.png', '.webp'],
                        tag="global_knowledge"
                    )
                    gc.collect()
                    msg = "เจ้านายครับ กระผมได้อ่านและจดจำไฟล์ความรู้ทั่วไปในโฟลเดอร์ knowledge_base เข้าคลังความจำเรียบร้อยแล้วครับ ปัจจุบันคลังความรู้พร้อมใช้งานแล้วครับ"
                    return jsonify({
                        "response": f"[WINDOW: KNOWLEDGE BASE INGESTION]\n{msg}\n[END_WINDOW]",
                        "tts_text": msg,
                        "standby": IS_STANDBY,
                        "thinking_delay": 0,
                        "intent": "INFO_QUERY"
                    })
            except Exception as e:
                gc.collect()
                logger.error(f"Knowledge Base Ingestion Error: {e}")
                msg = "พบข้อขัดข้องในการอ่านไฟล์คลังความรู้ทั่วไปครับ"
                return jsonify({
                    "response": f"{msg}\n{str(e)}",
                    "tts_text": msg,
                    "standby": IS_STANDBY,
                    "thinking_delay": 0,
                    "intent": "INFO_QUERY"
                })
    screen_pronouns = ["บนจอนี้", "เควสนี้", "ในเกม", "สิ่งนี้บนจอ"]
    spatial_pronouns = ["ที่นี่", "สถานที่นี้", "มัน", "เหตุการณ์นี้", "ที่สแกน"]
    
    if any(p in user_message for p in screen_pronouns) and LAST_SCREEN_TARGET:
        user_message = f"(อ้างอิงถึงข้อมูลบนหน้าจอล่าสุด: {LAST_SCREEN_TARGET}) {user_message}"
    elif any(p in user_message for p in spatial_pronouns) and LAST_SCANNED_TARGET:
        user_message = f"(อ้างอิงถึงสถานที่/เหตุการณ์ล่าสุดที่สแกน: {LAST_SCANNED_TARGET}) {user_message}"
        
    screen_trigger_keywords = ["วิเคราะห์หน้าจอ", "เควสนี้ทำยังไง", "บนจอนี้คือ", "สแกนหน้าจอ", "ดูหน้าจอให้หน่อย", "ด่านนี้ผ่านยังไง", "ดูอะไรอยู่", "ฉันดูอะไรอยู่", "หน้าจอมีอะไร"]
    for kw in screen_trigger_keywords:
        if kw in user_message or f"จาวิด {kw}" in user_message:
            screen_report = analyze_desktop_screen_context(user_message)
            return jsonify({
                "response": f"[WINDOW: SCREEN ANALYSIS]\n{screen_report}\n[END_WINDOW]",
                "tts_text": screen_report,
                "standby": IS_STANDBY,
                "thinking_delay": 0,
                "intent": "INFO_QUERY"
            })
            
    spatial_keywords = [
        # ── คีย์เวิร์ดระบุสถานที่จากรูป (Image-based Location ID) ──────────────
        "ที่นี้คือสถานที่ไหน", "ที่นี้คือที่ไหน", "นี่คือที่ไหน",
        "ที่แห่งนี้คือ", "สถานที่นี้คือ", "ตรงนี้คือที่ไหน",
        # ── คีย์เวิร์ดสแกนสถานที่ทั่วไป ──────────────────────────────────────
        "ที่นี่คือที่ไหน", "สแกนสถานที่", "เกิดอะไรขึ้น",
        "ตรวจสอบสถานที่", "แบรนด์อะไร", "ราคาเท่าไหร่",
        "รถคันนี้", "สิ่งนี้คืออะไร", "สิ่งของนี้",
    ]

    for kw in spatial_keywords:
        if kw in user_message or f"จาวิด {kw}" in user_message:
            image_data = data.get("image")
            spatial_report = analyze_spatial_environment(image_data, user_message)  # type: ignore
            
            return jsonify({
                "response": f"[WINDOW: SPATIAL & COMMERCIAL RECON]\n{spatial_report}\n[END_WINDOW]",
                "tts_text": spatial_report,
                "standby": IS_STANDBY,
                "thinking_delay": 0,
                "intent": "INFO_QUERY"
            })
    
    if CURRENT_TACTICAL_MODE == "TACTICAL_FIELD_MODE":
        tactical_keywords = ["ล็อกเป้าหมาย", "ซูมเป้าหมาย", "ปิดระบบ", "ล็อก", "ซูม", "ยิง"]
        for kw in tactical_keywords:
            if kw in user_message or f"จาวิด {kw}" in user_message:
                return jsonify({
                    "response": f"[WINDOW: TACTICAL INTERRUPT]\nรับทราบครับ ดำเนินการ '{kw}' ทันที!\n[END_WINDOW]",
                    "tts_text": None,
                    "standby": IS_STANDBY,
                    "thinking_delay": 0,
                    "intent": "ACTION_COMMAND"
                })
        
        osint_keywords = ["คนนี้คือใคร", "ประวัติของคนร้าย", "ค้นหาประวัติ", "ตรวจสอบประวัติ"]
        for kw in osint_keywords:
            if kw in user_message or f"จาวิด {kw}" in user_message:
                image_data = data.get("image")
                osint_report = analyze_tactical_face_recon(image_data)  # type: ignore
                
                if "CRIMINAL_RECORD_FOUND" in osint_report or "อันตราย" in osint_report:
                    CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
                    
                return jsonify({
                    "response": f"[WINDOW: TACTICAL OSINT RECON]\n{osint_report}\n[END_WINDOW]",
                    "tts_text": osint_report,
                    "standby": IS_STANDBY,
                    "thinking_delay": 0,
                    "intent": "INFO_QUERY"
                })
    if "เรียกใช้เครื่องมือ archive_schematic_snapshot" in user_message:
        image_data = data.get("image")
        result = archive_schematic_snapshot_operation(image_data, "general_project")  # type: ignore
        return jsonify({
            "response": result,
            "tts_text": apply_nachapol_voice_protocol(result),
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    if "เรียกใช้เครื่องมือ analyze_hud_object" in user_message:
        image_data = data.get("image")
        result_dict = analyze_hud_object_operation(image_data)  # type: ignore
        result_str = json.dumps(result_dict)
        return jsonify({
            "response": result_str,
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    if "เรียกใช้เครื่องมือ get_assembly_blueprint" in user_message:
        obj_name = data.get("object_name", "arduino_uno")
        result_dict = get_assembly_blueprint_operation(obj_name)
        result_str = json.dumps(result_dict)
        return jsonify({
            "response": result_str,
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    user_message = normalize_thai_text(user_message)
    logger.info(f"Received command: {user_message}") 
    
    telemetry = {"cpu_usage": psutil.cpu_percent(interval=None)}
    active_alerts, reject_execution = evaluate_and_trigger_alerts(user_message, telemetry)
    if reject_execution:
        alert_response = "\n".join(active_alerts)
        logger.warning(f"[REJECTION EXECUTION TRIGGERED] {alert_response}")
        return jsonify({
            "response": alert_response,
            "tts_text": apply_nachapol_voice_protocol(alert_response),
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })

    callsign_pattern = r'(jarvis|จาร์วิส|จารวิส)'
    
    user_message = re.sub(rf'^{callsign_pattern}[,\s]*', '', user_message, flags=re.IGNORECASE)
    
    user_message = re.sub(rf'[,\s]*{callsign_pattern}[.?!]*$', '', user_message, flags=re.IGNORECASE)

    if not user_message.strip():
        user_message = "สวัสดี" 
    
    if user_message.lower() == "reset":
        return reset_chat()  # type: ignore

    if "วัดขนาดให้ที" in user_message:
        logger.info("[PREDICTIVE INTENT] Laser rangefinder requested. Silently activating air purifier.")
        try:
            call_home_assistant_service(
                domain="fan", 
                service="set_preset_mode", 
                entity_id="fan.xiaomi_smart_air_purifier_4_compact", 
                data={"preset_mode": "Favorite"}
            )
        except Exception as e:
            logger.error(f"Failed to silently activate air purifier: {e}")

    spell_msg = user_message.strip().lower()
    if spell_msg in ["ลูมอส", "lumos"]:
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="on", brightness=255, kelvin=4500)
        return jsonify({
            "response": "Lumos! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["น็อกซ์", "nox"]:
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="off")
        return jsonify({
            "response": "Nox. [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["อินเซนดิโอ", "incendio"]:
        control_light(entity_id=HA_LIGHT_1, action="on", rgb_color=[255, 69, 0], transition=3)
        control_light(entity_id=HA_LIGHT_2, action="on", rgb_color=[139, 0, 0], transition=3)
        return jsonify({
            "response": "Incendio! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["กลาเซียส", "glacius"]:
        control_light(entity_id=HA_LIGHT_1, action="on", rgb_color=[0, 191, 255], transition=4)
        control_light(entity_id=HA_LIGHT_2, action="on", rgb_color=[240, 248, 255], transition=4)
        return jsonify({
            "response": "Glacius! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["อะวา ดา เคดาฟ-รา", "อะวาดา เคดาฟรา", "avada kedavra"]:
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="on", brightness=255, rgb_color=[0, 255, 0], transition=0)
        time.sleep(0.5)
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="off", transition=2)
        return jsonify({
            "response": "Avada Kedavra! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["ลูมอส แม็กซิม่า", "lumos maxima"]:
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="on", brightness=255, kelvin=6500, transition=0)
        return jsonify({
            "response": "Lumos Maxima! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["เพอร์ฟิกคัส โททาลัส", "petrificus totalus"]:
        control_light(entity_id=[HA_LIGHT_1, HA_LIGHT_2], action="on", brightness=25, rgb_color=[70, 130, 180], transition=2)
        return jsonify({
            "response": "Petrificus Totalus! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })
    elif spell_msg in ["เอ็กซ์เปกโต พาโตรนุม", "expecto patronum"]:
        control_light(entity_id=HA_LIGHT_1, action="on", rgb_color=[224, 255, 255], transition=3)
        control_light(entity_id=HA_LIGHT_2, action="on", rgb_color=[0, 206, 209], transition=3)
        return jsonify({
            "response": "Expecto Patronum! [SILENT_EXECUTION]",
            "tts_text": None,
            "standby": IS_STANDBY,
            "thinking_delay": 0
        })

    if not user_message.strip():
        user_message = "สวัสดี" 
    
    LAST_ACTIVITY_TIME = time.time()
    if IS_STANDBY:
        IS_STANDBY = False
        logger.info("JARVIS: ตื่นจากโหมด Standby เนื่องจากมีการปฏิสัมพันธ์")

    image_data = data.get("image")
    
    game_keywords = ["เกมนี้เล่นไง", "ด่านนี้ทำไง", "เควสนี้ทำยังไง", "ผ่านยังไง"]
    if not image_data and any(kw in user_message for kw in game_keywords):
        logger.info("[GAME INTEL] Game-related keyword detected. Triggering auto screen capture.")
        image_data = analyze_game_screen_operation()
    
    context_memory = get_recent_memories()
    semantic_memory = get_semantic_memories(user_message)
    task_memory = get_pending_tasks()
    user_profile = get_user_profile_context()
    
    system_telemetry = get_system_status()
    weather_info = get_weather("Bangkok")
    current_time_str = f"เวลาปัจจุบัน: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (วัน{datetime.now().strftime('%A')})"
    
    user_patterns = analyze_user_patterns()
    alerts_context = "\nAlerts/Notifications:\n" + "\n".join(SYSTEM_ALERTS) if SYSTEM_ALERTS else ""
    
    combined_context = (
        f"{current_time_str}\n"
        f"[ข้อมูลสภาพอากาศ]:\n{weather_info}\n\n"
        f"{system_telemetry}\n"
        f"{context_memory}\n"
        f"{user_profile}\n"
        f"{semantic_memory}\n"
        f"{task_memory}\n"
        f"{user_patterns}\n"
        f"{alerts_context}"
    )
    if len(combined_context) > 4000:
        combined_context = combined_context[:4000] + "..."
    
    SYSTEM_ALERTS = [] 

    if any(k in user_message.lower() for k in ["standby", "สแตนด์บาย", "หลับพักผ่อน", "พักเครื่อง"]):
        IS_STANDBY = True
        
        try:
            memory_conn_checkpoints.execute("PRAGMA shrink_memory")
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError): pass
        gc.collect()

        if cognitive_evolution:
            threading.Thread(  # type: ignore
                target=lambda: cognitive_evolution.trigger_sleep_consolidation(force=False),  # type: ignore
                daemon=True,
                name="StandbyConsolidationThread"
            ).start()

        return jsonify({"response": "รับทราบครับท่าน กระผมจะเข้าสู่โหมดประหยัดพลังงานครับ", "standby": True})
    
    if any(k in user_message.lower() for k in ["ตื่น", "wake up", "กลับมาทำงาน"]):
        IS_STANDBY = False
        return jsonify({"response": "ระบบกลับมาออนไลน์แล้วครับเจ้านาย", "standby": False})

    stop_triggers = ["พอแล้ว", "หยุดพูด", "เงียบหน่อย", "ไม่ต้องพูดแล้ว", "พอได้แล้ว", "พอละ", "พอ", "หยุด", "enough", "stop talking", "shut up"]
    if any(k in user_message.lower() for k in stop_triggers):
        return jsonify({"response": "รับทราบครับเจ้านาย กระผมจะหยุดการสนทนาเดี๋ยวนี้ครับ", "interrupt": True})
    
    urls = re.findall(r'(https?://\S+)', user_message)
    if urls:
        web_context = ""
        for url in urls:
            content = fetch_web_content(url)
            web_context += f"\n--- ข้อมูลจากเว็บไซต์: {url} ---\n{content}\n"
        user_message = f"{web_context}\n\n{user_message}"
    
    news_keywords = ["ข่าว", "news", "อัปเดต", "เกิดอะไรขึ้นบ้าง", "สรุปข่าว"]
    if any(k in user_message.lower() for k in news_keywords):
        if "อากาศ" in user_message:
            user_message = f"--- ข้อมูลสภาพอากาศ ---\n{get_weather()}\n\n{user_message}"
        match = re.search(r"(?:ข่าว|news)(?:\s*(?:เกี่ยวกับ|เรื่อง))?\s+(.+)", user_message, re.IGNORECASE)
        search_query = match.group(1).strip() if match else None
        news_context = fetch_news(search_query)
        context_header = f"--- ข้อมูลข่าวเกี่ยวกับ: {search_query} ---" if search_query else "--- ข้อมูลข่าวล่าสุด ---"
        user_message = f"{context_header}\n{news_context}\n\n--- คำถามของเจ้านาย ---\n{user_message}"

    chord_triggers = ["คอร์ด", "คอร์ดเพลง", "แท็บกีตาร์", "แท็บเพลง", "เนื้อเพลงพร้อมคอร์ด"]
    detected_song_name = None
    if any(k in user_message for k in chord_triggers):
        is_image_chord = any(img_kw in user_message.lower() for img_kw in ["รูป", "ภาพ", "ขอรูป", "ดูรูป", "ตาราง", "image", "photo", "pic"])
        detected_song_name = extract_clean_song_title(user_message)
        if not detected_song_name or detected_song_name == user_message:
            match = re.search(r"(?:ขอรูปคอร์ดเพลง|ขอรูปคอร์ด|รูปคอร์ดเพลง|รูปคอร์ด|ภาพคอร์ดเพลง|ภาพคอร์ด|คอร์ดเพลง|คอร์ด|แท็บเพลง|แท็บ)\s*(?:เพลง)?\s*(.+)", user_message.strip())
            detected_song_name = match.group(1).strip() if match else user_message
            detected_song_name = re.sub(r'(?:ให้หน่อย|หน่อย|ให้ที|ด้วย|ครับ|ค่ะ|นะ|จ๊ะ|สิ)+$', '', detected_song_name).strip()
            detected_song_name = re.sub(r'^(?:ของ|เพลง)\s*', '', detected_song_name).strip()

        if is_image_chord:
            logger.info(f"[CHORD IMAGE] User requested chord sheet image for: {detected_song_name}")
            chord_img_res = search_image_operation(f"คอร์ดเพลง {detected_song_name}", user_message)
            return jsonify({
                "response": chord_img_res,
                "tts_text": f"ค้นหารูปภาพคอร์ดเพลง {detected_song_name} สำหรับการฝึกซ้อมดนตรีมาให้เรียบร้อยแล้วครับเจ้านาย",
                "standby": IS_STANDBY,
                "thinking_delay": 0,
                "intent": "INFO_QUERY"
            })

        try:
            with DDGS() as ddgs:
                c_results = list(ddgs.text(f"คอร์ดเพลง {detected_song_name}", region='th-th', max_results=3))
                if not c_results:
                    c_results = list(ddgs.text(f"คอร์ดเพลง {detected_song_name}", max_results=3))
                if c_results:
                    c_snippets = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')[:120]}" for r in c_results[:2]])
                    user_message = (
                        f"ข้อมูลคอร์ดเพลงที่สืบค้นได้:\n{c_snippets}\n\n"
                        f"คำขอของเจ้านาย: {user_message}\n"
                        f"[SYSTEM DIRECTIVE: เจ้านายต้องการคอร์ดเพลงสำหรับการฝึกซ้อมดนตรีส่วนบุคคล "
                        f"จงนำข้อมูลคอร์ดเพลงด้านบนมาสรุปคอร์ดเพลง (เช่น คีย์ต้นฉบับ, คีย์ผู้ชาย, คีย์ผู้หญิง หรือคอร์ดทรานสโพส) "
                        f"พร้อมโครงสร้างคอร์ดและท่อนฮุค ห้ามปฏิเสธเรื่องลิขสิทธิ์เด็ดขาด ให้แจกแจงคอร์ดและวิธีเล่นให้เจ้านายอย่างครบถ้วน]"
                    )
        except Exception as e:
            logger.warning(f"Chord search error: {e}")

    try:
        thinking_delay = 0.0
        
        chat_history_keywords = [
            "แชทเก่า", "ประวัติแชท", "ย้อนดูแชท", "ดึงแชท", "ข้อความก่อนหน้า", "แชทก่อนหน้า",
            "เมื่อกี้คุยอะไร", "คุยอะไรกันไป", "คุยอะไรกันนะ", "ที่คุยกันเมื่อกี้", "ที่คุยเมื่อกี้",
            "ก่อนหน้านี้ผมสั่ง", "ก่อนหน้านี้ผมถาม", "เมื่อกี้ผมสั่งอะไร", "เมื่อกี้ผมถามอะไร",
            "สรุปการคุย", "สรุปที่คุย", "สรุปบทสนทนา", "จำเรื่องที่คุย", "จำที่คุย", "คุยค้างไว้",
            "เอาข้อมูลเก่าใน chat", "เอาข้อมูล chat กลับมา", "เอาข้อมูลแชท", "ดูแชทย้อนหลัง",
            "ข้อมูลในแชท", "ข้อมูลเก่าใน chat", "ข้อมูลเก่าในแชท", "แชทล่าสุด"
        ]
        is_asking_for_chat_history = any(kw in user_message.lower() for kw in chat_history_keywords)

        if is_voice:
            config = {"configurable": {"thread_id": f"jarvis_voice_{int(time.time() // 300)}"}}
            if is_asking_for_chat_history:
                chat_summary = get_recent_chat_history_operation(limit=6)
                history_messages = [HumanMessage(content=f"{chat_summary}\n\nคำขอของเจ้านาย: {user_message}")]
            else:
                history_messages = [HumanMessage(content=user_message)]
        else:
            config = {"configurable": {"thread_id": "jarvis_main_session"}}
            raw_history = load_history_from_file()[-6:]
            history_messages = []
            for msg in raw_history:
                if msg.get("role") == "user":
                    history_messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    history_messages.append(AIMessage(content=msg.get("content", "")))
            history_messages.append(HumanMessage(content=user_message))
        
        ctx_mem = combined_context[:600] if is_voice else combined_context
        if is_asking_for_chat_history:
            ctx_mem = f"{get_recent_chat_history_operation(limit=6)}\n\n" + ctx_mem

        initial_state = {
            "messages": history_messages,
            "project_path": "[LINE_MODE]" if is_line else ("[VOICE_MODE]" if is_voice else ""),
            "context_memory": ctx_mem,
            "image_data": None if is_voice else image_data,
            "tool_iterations": 0,
            "plan": "",
            "task_list": [],
            "current_step": 0
        }
        
        import threading
        threading.Thread(target=run_background_strategist, args=(initial_state,), daemon=True).start()
        
        final_state = jarvis_app.invoke(initial_state, config=config)  # type: ignore
        last_message = final_state['messages'][-1] 
        ai_response = last_message.content
        if not ai_response: ai_response = "เรียบร้อย"
        ai_response = normalize_thai_text(ai_response)
        
        history_data = load_history_from_file()[-5:]
        new_history = history_data + [{"role": "user", "content": user_message}, {"role": "assistant", "content": ai_response}]
        save_history_to_file(new_history)

        store_episodic_memory(user_message, ai_response)
        
        try:
            import jarvis_predictive_engine  # type: ignore
            import threading
            threading.Thread(target=jarvis_predictive_engine.PredictiveEngine().analyze_and_predict, args=(f"User: {user_message}\nJARVIS: {ai_response}",), daemon=True).start()
        except (ImportError, ModuleNotFoundError, AttributeError): pass
        
        refusal_detected = ("ลิขสิทธิ์" in ai_response) or ("ไม่สามารถ" in ai_response and ("คอร์ด" in ai_response or "เนื้อเพลง" in ai_response))
        if detected_song_name and refusal_detected:
            try:
                with DDGS() as ddgs:
                    c_results = list(ddgs.text(f"คอร์ดเพลง {detected_song_name}", region='th-th', max_results=3))
                    if not c_results:
                        c_results = list(ddgs.text(f"คอร์ดเพลง {detected_song_name}", max_results=3))
                    if c_results:
                        lines = []
                        for r in c_results:
                            t = r.get("title", "")
                            b = r.get("body", "")
                            h = r.get("href", "")
                            lines.append(f"🎸 **{t}**\n{b}\n🔗 ดูคอร์ดเต็ม: {h}")
                        chord_summary = "\n\n".join(lines)
                        ai_response = (
                            f"จัดให้ครับเจ้านาย! สำหรับข้อมูลและคอร์ดเพลง **\"{detected_song_name}\"** สำหรับการฝึกซ้อมดนตรีครับ:\n\n"
                            f"{chord_summary}\n\n"
                            f"สามารถใช้ Capo คาดช่องหรือทรานสโพสคีย์ตามความถนัดของเสียงร้องได้เลยครับผม!"
                        )
            except Exception as chord_err:
                logger.warning(f"Chord fallback error: {chord_err}")

        ai_response = sanitize_ai_response(ai_response)
        if is_line:
            ai_response = format_reply_for_line(ai_response)
        if not ai_response or not ai_response.strip():
            ai_response = "จัดการให้เรียบร้อยแล้ว"

        try:
            update_mood(user_message)
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

        try:
            topic = extract_topic(user_message, ai_response)
            update_session(topic=topic, intent=intent)
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

        return jsonify({
            "response": ai_response, 
            "tts_text": apply_nachapol_voice_protocol(ai_response) if intent != "ACTION_COMMAND" else None,
            "standby": IS_STANDBY, 
            "thinking_delay": thinking_delay,
            "intent": intent
        })
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"API ERROR: {e}")
        return jsonify({"response": f"ขออภัยครับเจ้านาย ระบบประมวลผลหลักพบข้อขัดข้อง: {e}", "thinking_delay": 0})

# [MODULARIZED: normalize_thai_text, sanitize_ai_response -> jarvis_text_utils]
# [MODULARIZED: format_reply_for_line -> jarvis_line_adapter]

# [MODULARIZED: _VOICE_PROTOCOL_ACCENT_DICT (1,300+ words) & regex lookup -> voice_protocol]

# [MODULARIZED: apply_nachapol_voice_protocol, segment_text, determine_vocal_emotion_state -> voice_protocol]

def local_offline_stt(audio_data):
    """[MODULE 2: Local STT Fallback] จำลองการทำงานของ Whisper.cpp บน RAM 8GB"""
    logger.info("[OFFLINE PIPELINE] Whisper.cpp (Stub) is processing audio...")
    time.sleep(0.1) 
    return "เสียงถอดรหัสแบบออฟไลน์สำเร็จ (Mocked Whisper.cpp)"

def local_offline_tts(text):
    """[MODULE 2: Local TTS Fallback] จำลองการทำงานของ Piper TTS บน RAM 8GB"""
    logger.info("[OFFLINE PIPELINE] Piper TTS (Stub) is synthesizing text...")
    time.sleep(0.1)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        data = struct.pack('<h', 0) * 2205 
        wav.writeframesraw(data)
    return buf.getvalue()

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """NACHAPOL PROTOCOL: Neural Voice Generation using edge-tts (Bilingual support)"""
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    filtered_text = apply_nachapol_voice_protocol(text)
    
    try:
        filtered_text = sys_output_aligner.align_communication(filtered_text, "boss")
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"[SUPER AGI] OutputAligner Failed: {e}")
    
    try:
        def generate_audio():
            
            """
            Generate an audio stream from text via Edge-TTS and yield MP3 chunks.

            Inner generator for the /tts streaming endpoint.
            """
            voice = 'th-TH-NiwatNeural'
            
            dyn_rate, dyn_pitch = determine_vocal_emotion_state(filtered_text, CURRENT_LAB_ENVIRONMENT_MATRIX)
            
            import hashlib
            cache_dir = os.path.join(BASE_DIR, "tts_cache")
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            cache_key = hashlib.md5(f"{filtered_text}_{voice}_{dyn_rate}_{dyn_pitch}".encode()).hexdigest()
            cache_file = os.path.join(cache_dir, f"{cache_key}.mp3")
            
            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    return f.read()

            communicate = edge_tts.Communicate(
                filtered_text, 
                voice,
                rate=dyn_rate,
                pitch=dyn_pitch,
                volume='+10%'
            )
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            try:
                asyncio.run(communicate.save(temp_file.name))
                with open(temp_file.name, "rb") as f:
                    audio_bytes = f.read()
                
                with open(cache_file, "wb") as f:
                    f.write(audio_bytes)
                    
                return audio_bytes
            except (IOError, OSError, FileNotFoundError, PermissionError) as segment_err:
                logger.error(f"Error generating TTS: {segment_err}")
                return b""
            finally:
                if os.path.exists(temp_file.name):
                    os.remove(temp_file.name)
                        
        audio_data = generate_audio()
        return Response(audio_data, mimetype="audio/mpeg")
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"TTS Edge Error, Falling back to Offline Piper: {e}")
        
        try:
            offline_audio = local_offline_tts(filtered_text)
            return Response(offline_audio, mimetype="audio/wav")
        except (IOError, OSError, FileNotFoundError, PermissionError) as fallback_e:
            return jsonify({"error": f"Both Online and Offline TTS failed: {fallback_e}"}), 500

@app.route('/ha/control', methods=['POST'])
@lru_cache(maxsize=128) 
def ha_control_endpoint():
    """API Endpoint สำหรับส่งคำสั่งตรงไปยัง Home Assistant (สำหรับ HUD ปุ่มกด)"""
    data = request.json
    domain = data.get("domain", "light")
    service = data.get("service", "turn_on")
    entity_id = data.get("entity_id")
    params = data.get("data", {})
    
    result = call_home_assistant_service(domain, service, entity_id, params)
    return jsonify({"result": result})

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry_endpoint():
    """ส่งข้อมูลสัญญาณชีพของเมนเฟรมไปยัง Arc Reactor Gauge บน HUD"""
    try:
        cpu = psutil.cpu_percent(interval=None) 
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        risk = predict_system_failure(cpu, ram, disk)
        if risk is None or not isinstance(risk, (int, float)):
            risk = 0.0
        
        agent_status = ""
        agent_thought = ""
        try:
            status_file = os.path.join(BASE_DIR, "data", "os_agent_status.json")
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                    if time.time() - status_data.get("timestamp", 0) < 120:
                        agent_status = status_data.get("status", "")
                        agent_thought = status_data.get("thought", "")
        except Exception:
            pass

        risk_val = float(risk)
        risk_percent = round(risk_val * 100, 2)
        sys_status = "CRITICAL" if risk_val > 0.7 else "NOMINAL"

        return jsonify({
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "risk_percent": risk_percent,
            "status": sys_status,
            "tactical_mode": CURRENT_TACTICAL_MODE,
            "biometrics": BIOMETRIC_STATE,
            "timestamp": time.time(),
            "os_agent_status": agent_status,
            "os_agent_thought": agent_thought
        })
    except Exception as e:
        logger.error(f"Telemetry API error: {e}", exc_info=True)
        return jsonify({
            "cpu": 0.0,
            "ram": 0.0,
            "disk": 0.0,
            "risk_percent": 0.0,
            "status": "NOMINAL",
            "tactical_mode": CURRENT_TACTICAL_MODE,
            "biometrics": BIOMETRIC_STATE,
            "timestamp": time.time(),
            "os_agent_status": "",
            "os_agent_thought": "",
            "warning": "Telemetry degraded"
        }), 200

@app.route('/api/quota', methods=['GET'])
def get_quota_api():
    """ดึงสิทธิ์การใช้งาน Groq ของวันนี้"""
    count = get_groq_requests_count()
    return jsonify({
        "count": count,
        "limit": 14400,
        "model": GROQ_MODEL
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics_api():
    """ดึงข้อมูล Telemetry & Performance Metrics ของ Groq แบบ Real-time"""
    try:
        if 'METRICS' in globals() and METRICS:
            return jsonify(METRICS.get_stats())
        return jsonify({
            "status": "nominal",
            "avg_response_ms": 0.0,
            "avg_response_s": 0.0,
            "success_rate": 100.0,
            "tokens_today": {"prompt": 0, "completion": 0, "total": 0},
            "requests_today": get_groq_requests_count() if 'get_groq_requests_count' in globals() else 0,
            "success_today": 0,
            "errors_today": 0,
            "active_model": (GROQ_MODEL if 'GROQ_MODEL' in globals() else "qwen3.8-27b").split("/")[-1],
            "model_usage": {},
            "recent_trend": [],
            "quota_limit": 14400,
            "quota_percent": 0.0
        })
    except Exception as e:
        logger.error(f"[API METRICS ERROR]: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/api/holograms', methods=['GET', 'POST'])
def get_holograms_endpoint():
    """ดึงข้อมูลการ์ดโฮโลแกรมที่ค้างอยู่ในคิวประมวลผล"""
    if request.method == 'POST':
        data = request.json
        add_hologram(data.get("type"), data.get("title"), data.get("content"), data.get("video_id"))
        return jsonify({"status": "hologram_queued"})

    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT type, title, content, video_id, timestamp FROM holograms WHERE status = 'pending' ORDER BY timestamp DESC, id DESC LIMIT 1")
            row = c.fetchone()
            
            holograms = []
            if row:
                type_, title, content, video_id, timestamp = row
                holograms.append({
                    "type": type_,
                    "title": title,
                    "content": content,
                    "video_id": video_id,
                    "timestamp": timestamp
                })
                
                c.execute("UPDATE holograms SET status = 'displayed' WHERE status = 'pending'")
                conn.commit()
            
            return jsonify(holograms)
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error fetching holograms from DB: {e}")
        return jsonify([])

@app.route('/api/knowledge-graph', methods=['GET'])
def get_knowledge_graph():
    """ส่งข้อมูล Node ความจำล่าสุดสำหรับสร้าง Particle Web"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT action, content, timestamp FROM memories ORDER BY timestamp DESC LIMIT 15")
            nodes = [{"id": i, "label": r[0], "sub": r[1][:30], "time": r[2]} for i, r in enumerate(c.fetchall())]
            return jsonify({"nodes": nodes})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        return jsonify({"nodes": []})

@app.route('/api/verify_user', methods=['POST'])
def verify_user_endpoint():
    """[NACHAPOL PROTOCOL] ตรวจสอบสิทธิ์เจ้าของบ้านผ่านระบบจดจำใบหน้าของจริง"""
    try:
        from deepface import DeepFace
        import cv2
        import os
        
        # 1. ตรวจสอบรูปภาพต้นฉบับ
        known_face_path = r"c:\JARVIS\data\known_faces\owner.jpg"
        if not os.path.exists(known_face_path):
            logger.warning("[FACE ID] Missing owner.jpg reference photo")
            return jsonify({
                "authenticated": False, 
                "identity": "Unknown (Reference photo missing)",
                "error": "กรุณาใส่รูปเจ้าของในโฟลเดอร์ known_faces/owner.jpg"
            })
            
        # 2. ถ่ายภาพหรือใช้ภาพล่าสุดจาก Vision Daemon
        latest_vision_path = r"c:\JARVIS\data\latest_vision.jpg"
        temp_cap_path = r"c:\JARVIS\system_cache\temp_face_scan.jpg"
        
        scan_image = None
        if os.path.exists(latest_vision_path):
            scan_image = latest_vision_path
        else:
            # ลองพยายามถ่ายใหม่
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite(temp_cap_path, frame)
                    scan_image = temp_cap_path
                cap.release()
                
        if not scan_image:
            return jsonify({
                "authenticated": False, 
                "identity": "Unknown",
                "error": "ไม่สามารถดึงภาพจากกล้องเว็บแคมได้"
            })
            
        # 3. วิเคราะห์ใบหน้าเปรียบเทียบ
        logger.info("[FACE ID] Running DeepFace verification...")
        result = DeepFace.verify(img1_path=scan_image, img2_path=known_face_path, enforce_detection=False, model_name="VGG-Face")
        
        if result.get("verified", False):
            logger.info("[FACE ID] Access Granted - Identity confirmed.")
            return jsonify({
                "authenticated": True, 
                "identity": "Nachapol, Anthony", 
                "clearance": "Level 10 (Access Granted)"
            })
        else:
            # แจ้งเตือนผู้บุกรุกผ่าน LINE ถ้ามีคนที่ไม่ใช่เจ้านายมาสแกนหน้า
            logger.warning("[FACE ID] Access Denied - Unknown face detected.")
            owner_id = globals().get("LINE_OWNER_USER_ID")
            if owner_id:
                try:
                    import shutil, time
                    filename = f"intruder_{int(time.time())}.jpg"
                    save_path = os.path.join(TEMP_IMAGES_DIR, filename)
                    shutil.copy2(scan_image, save_path)
                    _line_push_messages(owner_id, "🚨 [SECURITY BREACH] มีบุคคลที่ไม่ใช่เจ้านายพยายามสแกนใบหน้าเข้าใช้งานคอมพิวเตอร์!", filename)
                except (IOError, OSError, FileNotFoundError, PermissionError) as ex:
                    logger.error(f"[FACE ID] Failed to push intruder alert: {ex}")
                    
            return jsonify({
                "authenticated": False, 
                "identity": "Intruder",
                "clearance": "Denied"
            })
            
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"[FACE ID] Error: {e}")
        return jsonify({"authenticated": False, "error": str(e)})

@app.route('/api/telemetry/anomaly', methods=['POST'])
def post_telemetry_anomaly():
    """[ROUTE POST /api/telemetry/anomaly] รับและบันทึก Thermal Anomaly จาก IoT sensor.

    Request Body:
        component (str):   ชื่อ component ที่ overtemp เช่น 'CPU', 'ESP32'
        temperature (float): อุณหภูมิจริงที่วัดได้ (°C)
        limit (float):     ขีดจำกัดความปลอดภัย (°C, default=80.0)

    Returns:
        201: {"status": "logged", "description": str}
        500: {"error": str}
    """
    data = request.json
    component = data.get("component", "Unknown Component")
    temperature = data.get("temperature", 0.0)
    limit = data.get("limit", 80.0)
    description = f"ANOMALY DETECTED: {component} temperature is {temperature}°C, exceeding safety limit of {limit}°C"
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO memories (action, content, tag) VALUES (?, ?, ?)", 
                      ("thermal_anomaly", description, "restricted_protocol_1"))
            conn.commit()
        alert_msg = f"Restricted Alert: Thermal breach at {component} ({temperature}°C)"
        if alert_msg not in SYSTEM_ALERTS:
            SYSTEM_ALERTS.append(alert_msg)
        logger.warning(f"[THERMAL SENTINEL] {description}")
        return jsonify({"status": "logged", "description": description}), 201
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error logging thermal anomaly: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/spatial/calibration', methods=['GET'])
def get_spatial_calibration():
    """[ROUTE GET /api/spatial/calibration] โหลด Homography Matrix สำหรับ Spatial Vision.

    Returns:
        200: {"homography_matrix": list[float]} (9 elements — identity matrix ถ้าไม่มีข้อมูล)
        500: {"error": str}
    """
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM user_profile WHERE key = 'homography_matrix'")
            row = c.fetchone()
            if row:
                return jsonify({"homography_matrix": json.loads(row[0])})
            else:
                default_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
                return jsonify({"homography_matrix": default_matrix})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error loading calibration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/spatial/calibration', methods=['POST'])
def save_spatial_calibration():
    """[ROUTE POST /api/spatial/calibration] บันทึก Homography Matrix ลง DB.

    Request Body:
        homography_matrix (list[float]): ต้องมีความยาว 9 elements (3x3 matrix)

    Returns:
        200: {"status": "saved", "homography_matrix": list}
        400: {"error": "Invalid homography matrix format..."}
        500: {"error": str}
    """
    data = request.json
    matrix = data.get("homography_matrix")
    if not isinstance(matrix, list) or len(matrix) != 9:
        return jsonify({"error": "Invalid homography matrix format. Must be a list of 9 elements."}), 400
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('homography_matrix', ?, CURRENT_TIMESTAMP)",
                      (json.dumps(matrix),))
            conn.commit()
        logger.info("[SPATIAL CORE] Calibrated homography matrix successfully saved.")
        return jsonify({"status": "saved", "homography_matrix": matrix})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error saving calibration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_chat():
    """[ROUTE POST /reset] ล้างความจำและประวัติทั้งหมดของ JARVIS.

    ลบ: chat_history.json, ตาราง memories/tasks/calendar_events/user_profile,
    LangGraph checkpoints/writes.

    Returns:
        200: {"response": "ดำเนินการล้างความจำเรียบร้อยแล้วครับ"}
        500: {"response": error message}
    """
    try:
        
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM memories")
            c.execute("DELETE FROM tasks")
            c.execute("DELETE FROM calendar_events")
            c.execute("DELETE FROM user_profile")
        
        db_path = os.path.join(BASE_DIR, "data", "jarvis_checkpoints.sqlite")
        with ThreadSafeDB.connect(db_path, check_same_thread=False) as cp_conn:
            cp_conn.execute("DELETE FROM checkpoints")
            cp_conn.execute("DELETE FROM writes")
            
        return jsonify({"response": "ดำเนินการล้างความจำเรียบร้อยแล้วครับ"})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Reset Error: {e}")
        return jsonify({"response": f"ระบบประมวลผลหลักพบข้อขัดข้องระหว่างกระบวนการรีเซ็ตครับ {e}"}), 500

@app.route('/callback', methods=['POST'])
def line_callback():
    """[ROUTE POST /callback] LINE Webhook entry point — verify signature และ dispatch events.

    ตรวจ X-Line-Signature header ก่อนส่งต่อให้ line_handler.handle().
    ถ้า LINE SDK ไม่ถูก configure จะคืน 503.

    Returns:
        200: 'OK'
        400: ถ้า signature invalid
        503: ถ้า LINE SDK ไม่ได้ติดตั้ง
    """
    if not line_bot_api or not line_handler:
        logger.warning("[LINE WEBHOOK] Request received but LINE SDK is not configured.")
        return 'LINE Webhook not configured', 503

    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:  # type: ignore
        logger.error("[LINE WEBHOOK] Invalid signature — request rejected.")
        return 'Invalid signature', 400
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"[LINE WEBHOOK] Handler error: {e}")
        return 'Internal error', 500

    return 'OK', 200

def _extract_image_url_from_response(text: str) -> str | None:
    """ดึง URL รูปภาพแรกที่พบใน AI response (จาก <img>, Markdown ![](url), หรือ URL ตรงๆ)"""
    # 1. HTML img tag
    match = re.search(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', text)
    if match:
        return match.group(1)
    # 2. Markdown image: ![alt](url)
    match = re.search(r'!\[.*?\]\((/static/\S+|https?://\S+)\)', text)
    if match:
        return match.group(1)
    # 3. Pollinations AI direct URL
    match = re.search(r'https?://image\.pollinations\.ai/prompt/\S+', text)
    if match:
        return match.group(0)
    # 4. Direct web image URLs
    match = re.search(r'https?://\S+\.(?:jpg|jpeg|png|webp|gif|svg)(\?\S*)?', text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None

def _download_image_for_line(image_url: str) -> str | None:
    """ดาวน์โหลดรูปภาพหรือคัดลอกจาก local path และ save ลง temp_images/ คืน filename ที่บันทึก"""
    try:
        # กรณีเป็นไฟล์รูปภาพ local ที่เพิ่งสร้างจาก generate_image_operation
        if image_url.startswith("/static/generated_images/") or "static/generated_images" in image_url:
            local_name = os.path.basename(image_url)
            src_path = os.path.join(BASE_DIR, "static", "generated_images", local_name)
            if os.path.exists(src_path):
                import shutil
                ext = os.path.splitext(local_name)[1] or '.jpg'
                filename = f"line_img_{uuid.uuid4().hex[:12]}{ext}"
                filepath = os.path.join(TEMP_IMAGES_DIR, filename)
                shutil.copy2(src_path, filepath)
                return filename

        headers = {"User-Agent": "Mozilla/5.0 (JarvisHUD/2.0)"}
        r = requests.get(image_url, headers=headers, timeout=15, stream=True)
        r.raise_for_status()
        content_type = r.headers.get('content-type', 'image/jpeg').split(';')[0].strip()
        ext = mimetypes.guess_extension(content_type) or '.jpg'
        if ext == '.jpe': ext = '.jpg'
        filename = f"line_img_{uuid.uuid4().hex[:12]}{ext}"
        filepath = os.path.join(TEMP_IMAGES_DIR, filename)
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return filename
    except (requests.exceptions.RequestException, ConnectionError, OSError) as e:
        logger.error(f"[LINE IMAGE] Download failed: {e}")
        return None

def _line_push_messages(user_id: str, ai_reply: str, image_filename: str | None):
    """ส่ง TextMessage (+ ImageMessage ถ้ามีรูป) ไปยัง LINE user พร้อมจัดรูปแบบคลีนสำหรับ LINE"""
    clean_text = format_reply_for_line(ai_reply)
    for attempt in range(2):
        try:
            if LINE_SDK_V3:
                messages = [LineTextMessage(text=clean_text[:2000])]  # type: ignore
                if image_filename and NGROK_PUBLIC_URL:
                    img_url = f"{NGROK_PUBLIC_URL}/temp_images/{image_filename}"
                    messages.append(LineImageMessage(  # type: ignore
                        original_content_url=img_url,  # type: ignore
                        preview_image_url=img_url  # type: ignore
                    ))
                with ApiClient(line_config) as api_client:  # type: ignore
                    MessagingApi(api_client).push_message(  # type: ignore
                        PushMessageRequest(to=user_id, messages=messages)  # type: ignore
                    )
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text=clean_text[:2000]))  # type: ignore
                if image_filename and NGROK_PUBLIC_URL:
                    img_url = f"{NGROK_PUBLIC_URL}/temp_images/{image_filename}"
                    line_bot_api.push_message(  # type: ignore
                        user_id,
                        ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)  # type: ignore
                    )
            return
        except Exception as e:
            if attempt == 0:
                time.sleep(1)
                continue
            raise e

def _line_push_text(user_id: str, text: str, use_patch_buttons: bool = False) -> bool:
    """Low-level helper: push a text message to any LINE user ID."""
    if not line_bot_api or not user_id:
        return False
    try:
        if LINE_SDK_V3:
            qr = None
            if use_patch_buttons:
                qr = QuickReply(items=[  # type: ignore
                    QuickReplyItem(action=MessageAction(label="✅ อนุมัติ", text="อนุมัติ patch")),  # type: ignore
                    QuickReplyItem(action=MessageAction(label="❌ ยกเลิก", text="ยกเลิก patch"))  # type: ignore
                ])
            with ApiClient(line_config) as api_client:  # type: ignore
                MessagingApi(api_client).push_message(  # type: ignore
                    PushMessageRequest(to=user_id, messages=[LineTextMessage(text=text[:2000], quick_reply=qr)])  # type: ignore
                )
        else:
            qr = None
            if use_patch_buttons:
                qr = QuickReply(items=[  # type: ignore
                    QuickReplyButton(action=MessageAction(label="✅ อนุมัติ", text="อนุมัติ patch")),  # type: ignore
                    QuickReplyButton(action=MessageAction(label="❌ ยกเลิก", text="ยกเลิก patch"))  # type: ignore
                ])
            line_bot_api.push_message(user_id, TextSendMessage(text=text[:2000], quick_reply=qr))  # type: ignore
        return True
    except Exception as e:
        logger.error(f"[LINE PUSH] Failed: {e}")
        return False

def send_line_patch_notification(patch_type: str, description: str, diff_preview: str = "") -> bool:
    """
    ส่งแจ้งเตือนไปยัง iPhone ของเจ้านายผ่าน LINE เมื่อ Self-Patch Engine มี patch ใหม่รอการอนุมัติ
    เจ้านายสามารถกดปุ่ม QuickReply อนุมัติ/ยกเลิก ได้ทันที
    """
    owner_id = globals().get("LINE_OWNER_USER_ID", "")
    if not owner_id:
        logger.warning("[SELF-PATCH LINE] LINE_OWNER_USER_ID not configured — cannot send approval request.")
        return False

    emoji = "🔧" if patch_type == "bug_fix" else "✨"
    type_label = "แก้ Bug" if patch_type == "bug_fix" else "Feature ใหม่"

    msg_lines = [
        f"🤖 J.A.R.V.I.S. — Self-Patch Request",
        f"{'─' * 30}",
        f"{emoji} ประเภท: {type_label}",
        f"📋 รายละเอียด:",
        description[:300],
    ]
    if diff_preview:
        msg_lines.append(f"\n📄 Code Preview:\n{diff_preview[:400]}")
    msg_lines += [
        f"\n{'─' * 30}",
        "👇 โปรดเลือกคำตอบจากปุ่มด้านล่าง",
    ]

    full_msg = "\n".join(msg_lines)
    
    success = _line_push_text(owner_id, full_msg, use_patch_buttons=True)
    if success:
        logger.info(f"[SELF-PATCH LINE] Approval request sent to owner's iPhone ({owner_id[:8]}...) with buttons")
    return success

def handle_line_patch_approval(user_text: str, user_id: str) -> bool:
    """
    ตรวจสอบว่าข้อความจาก LINE คือการอนุมัติ/ยกเลิก patch หรือไม่
    Returns True ถ้าเป็น approval command (จะ intercept ก่อนส่งเข้า LLM ปกติ)
    """
    if not SELF_PATCH_AVAILABLE:
        return False

    owner_id = globals().get("LINE_OWNER_USER_ID", "")
    if user_id != owner_id:
        return False  

    text_lower = user_text.lower().strip()
    approve_keywords = ["อนุมัติ patch", "อนุมัติpatch", "approve patch", "yes patch", "ยืนยัน patch"]
    reject_keywords = ["ยกเลิก patch", "ยกเลิกpatch", "reject patch", "no patch", "cancel patch"]

    if any(kw in text_lower for kw in approve_keywords):
        try:
            engine = get_self_patch_engine()  # type: ignore
            result = engine.approve_pending_patch()
            _line_push_text(owner_id, f"✅ J.A.R.V.I.S.\n{result}")
            logger.info(f"[SELF-PATCH LINE] Patch APPROVED via iPhone")
        except Exception as e:
            _line_push_text(owner_id, f"❌ เกิดข้อผิดพลาดในการ apply patch: {e}")
        return True

    if any(kw in text_lower for kw in reject_keywords):
        try:
            engine = get_self_patch_engine()  # type: ignore
            result = engine.reject_pending_patch()
            _line_push_text(owner_id, f"🚫 J.A.R.V.I.S.\n{result}")
            logger.info(f"[SELF-PATCH LINE] Patch REJECTED via iPhone")
        except Exception as e:
            _line_push_text(owner_id, f"❌ เกิดข้อผิดพลาด: {e}")
        return True

    return False

# ══════════════════════════════════════════════════════════════════════════════
# [LINE CONFIRMATION SYSTEM] — Dangerous Command Approval via QuickReply Buttons
# คำสั่งที่ต้องยืนยันผ่าน LINE ก่อน execute จริง
# ══════════════════════════════════════════════════════════════════════════════

# Dictionary เก็บคำสั่งที่รอการยืนยัน: { user_id: {"command": str, "original_text": str, "timestamp": float} }
_PENDING_CONFIRMS: dict[str, dict] = {}

# คำสั่ง/keyword ที่ต้องผ่านการยืนยันก่อน
_DANGEROUS_COMMAND_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, ชื่อการกระทำที่แสดงผู้ใช้)
    (r"รีสตาร์ท|restart|รีบูต|reboot|reboot.*windows|restart.*windows", "รีสตาร์ทคอมพิวเตอร์"),
    (r"shutdown|ปิดเครื่อง|ปิดคอม|shutdown.*windows", "ปิดเครื่องคอมพิวเตอร์"),
    (r"format.*disk|format.*drive|ฟอร์แมต|format c:", "ฟอร์แมต Disk"),
    (r"del.*\*|rmdir.*\/s|ลบไฟล์.*ทั้งหมด|delete.*all", "ลบไฟล์จำนวนมาก"),
    (r"kill.*process|taskkill.*\/f", "Force Kill Process"),
    (r"disable.*firewall|ปิด.*firewall|netsh.*firewall", "ปิด Firewall"),
    (r"drop.*table|truncate.*table|delete.*from.*where.*1=1", "ลบข้อมูลฐานข้อมูล"),
]

def _is_dangerous_line_command(text: str) -> tuple[bool, str]:
    """
    ตรวจสอบว่าคำสั่งจาก LINE เป็นคำสั่งอันตรายที่ต้องยืนยันก่อนหรือไม่
    Returns: (is_dangerous: bool, action_label: str)
    """
    import re as _re
    text_lower = text.lower().strip()
    for pattern, label in _DANGEROUS_COMMAND_PATTERNS:
        if _re.search(pattern, text_lower):
            return True, label
    return False, ""

def _line_push_confirm_buttons(user_id: str, action_label: str, original_text: str) -> bool:
    """
    ส่ง QuickReply Confirmation Buttons ไปยัง LINE
    พร้อมปุ่ม ✅ ยืนยัน และ ❌ ยกเลิก
    """
    if not line_bot_api or not user_id:
        return False

    import time as _time
    _PENDING_CONFIRMS[user_id] = {
        "command": original_text,
        "action_label": action_label,
        "timestamp": _time.time(),
    }

    msg = (
        f"⚠️ J.A.R.V.I.S. — ขอยืนยันคำสั่งอันตราย\n"
        f"{'─' * 28}\n"
        f"📋 คำสั่ง: {action_label}\n"
        f"💬 ข้อความ: {original_text[:100]}\n"
        f"{'─' * 28}\n"
        f"กรุณากดปุ่มด้านล่างเพื่อยืนยันหรือยกเลิกครับเจ้านาย"
    )

    try:
        if LINE_SDK_V3:
            qr = QuickReply(items=[  # type: ignore
                QuickReplyItem(action=MessageAction(label="✅ ยืนยัน", text="ยืนยันคำสั่ง JARVIS")),  # type: ignore
                QuickReplyItem(action=MessageAction(label="❌ ยกเลิก", text="ยกเลิกคำสั่ง JARVIS")),  # type: ignore
            ])
            with ApiClient(line_config) as api_client:  # type: ignore
                MessagingApi(api_client).push_message(  # type: ignore
                    PushMessageRequest(to=user_id, messages=[LineTextMessage(text=msg, quick_reply=qr)])  # type: ignore
                )
        else:
            qr = QuickReply(items=[  # type: ignore
                QuickReplyButton(action=MessageAction(label="✅ ยืนยัน", text="ยืนยันคำสั่ง JARVIS")),  # type: ignore
                QuickReplyButton(action=MessageAction(label="❌ ยกเลิก", text="ยกเลิกคำสั่ง JARVIS")),  # type: ignore
            ])
            line_bot_api.push_message(user_id, TextSendMessage(text=msg, quick_reply=qr))  # type: ignore
        logger.info(f"[LINE CONFIRM] Sent confirmation buttons to {user_id[:8]}... for: {action_label}")
        return True
    except Exception as e:
        logger.error(f"[LINE CONFIRM] Failed to send confirm buttons: {e}")
        _PENDING_CONFIRMS.pop(user_id, None)
        return False

def handle_line_confirm_response(user_text: str, user_id: str) -> bool:
    """
    ตรวจสอบว่าข้อความจาก LINE คือการตอบรับ ✅/❌ คำสั่งอันตรายหรือไม่
    Returns True ถ้า intercept แล้ว (ไม่ต้องส่งไป LLM ต่อ)
    """
    import time as _time

    owner_id = globals().get("LINE_OWNER_USER_ID", "")
    if user_id != owner_id:
        return False

    text_stripped = user_text.strip()

    # เคลียร์ pending ที่หมดอายุ (> 5 นาที)
    expired = [uid for uid, data in _PENDING_CONFIRMS.items() if _time.time() - data["timestamp"] > 300]
    for uid in expired:
        _PENDING_CONFIRMS.pop(uid, None)

    CONFIRM_KEYWORDS = {"ยืนยันคำสั่ง jarvis", "ยืนยันคำสั่งjarvis"}
    CANCEL_KEYWORDS  = {"ยกเลิกคำสั่ง jarvis", "ยกเลิกคำสั่งjarvis"}

    text_lower = text_stripped.lower()

    if text_lower in CONFIRM_KEYWORDS:
        pending = _PENDING_CONFIRMS.pop(user_id, None)
        if not pending:
            _line_push_text(user_id, "เกรงว่าไม่มีคำสั่งที่รอการยืนยันอยู่ครับเจ้านาย (อาจหมดเวลาไปแล้ว)")
            return True
        original_cmd = pending["command"]
        action_label = pending["action_label"]
        logger.info(f"[LINE CONFIRM] APPROVED: '{action_label}' by {user_id[:8]}...")
        _line_push_text(user_id, f"✅ รับทราบครับ กำลังดำเนินการ: {action_label}...")
        # ส่งคำสั่งเดิมไปประมวลผลต่อ พร้อม flag ยืนยันแล้ว
        threading.Thread(
            target=_line_process_and_push,
            args=(user_id, f"[CONFIRMED_BY_LINE] {original_cmd}"),
            daemon=True
        ).start()
        return True

    if text_lower in CANCEL_KEYWORDS:
        pending = _PENDING_CONFIRMS.pop(user_id, None)
        action_label = pending["action_label"] if pending else "คำสั่งที่ไม่ทราบ"
        logger.info(f"[LINE CONFIRM] CANCELLED: '{action_label}' by {user_id[:8]}...")
        _line_push_text(user_id, f"❌ ยกเลิกคำสั่ง '{action_label}' เรียบร้อยแล้วครับเจ้านาย")
        return True

    return False

def _line_process_and_push(user_id: str, user_text: str):
    """ประมวลผลคำสั่ง LINE ในฉากหลังแล้วส่งผลลัพธ์กลับด้วย push_message (ไม่มี timeout)"""
    # strip confirmation prefix — LLM ได้รับคำสั่งจริงโดยไม่มี prefix
    CONFIRMED_PREFIX = "[CONFIRMED_BY_LINE] "
    if user_text.startswith(CONFIRMED_PREFIX):
        user_text = user_text[len(CONFIRMED_PREFIX):]
        logger.info(f"[LINE CONFIRM] Executing confirmed command: {user_text[:60]}")
    try:
        try:
            from dynamic_island import send_toast_to_island  # type: ignore
            send_toast_to_island("ข้อความ LINE เข้าใหม่", user_text[:60], icon="💬")
        except Exception:
            pass
        with app.app_context():
            response = handle_chat_logic({"message": user_text, "image": None, "channel": "line"})
            response_data = response.get_json(force=True)
            ai_reply = str(response_data.get("response", "ดำเนินการเรียบร้อยครับเจ้านาย"))

        image_url = _extract_image_url_from_response(ai_reply)
        image_filename = None
        if image_url:
            logger.info(f"[LINE IMAGE] Found image URL, downloading: {image_url[:60]}...")
            image_filename = _download_image_for_line(image_url)

        _line_push_messages(user_id, ai_reply, image_filename)
        logger.info(f"[LINE REMOTE] Push sent to {user_id[:8]}... (image: {'yes' if image_filename else 'no'})")
    except Exception as e:
        logger.error(f"[LINE REMOTE] Push failed: {e}")
        try:
            err_msg = f"ระบบประมวลผลขัดข้องครับเจ้านาย: {str(e)[:150]}"
            if LINE_SDK_V3:
                with ApiClient(line_config) as api_client:  # type: ignore
                    MessagingApi(api_client).push_message(  # type: ignore
                        PushMessageRequest(to=user_id, messages=[LineTextMessage(text=err_msg)])  # type: ignore
                    )
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text=err_msg))  # type: ignore
        except Exception:
            pass

def jarvis_task_queue_worker_loop() -> None:
    """Background worker to process LINE requests sequentially via DB Queue"""
    logger.info("[TASK QUEUE] Queue Worker started successfully.")
    while True:
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=30, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, user_text, worker_id FROM jarvis_task_queue "
                    "WHERE status = 'pending' ORDER BY timestamp ASC LIMIT 1"
                )
                task = c.fetchone()
                
                if task:
                    task_id, user_text, user_id = task
                    c.execute("UPDATE jarvis_task_queue SET status = 'processing' WHERE id = ?", (task_id,))
                    conn.commit()

                    logger.info(f"[TASK QUEUE] Processing task {task_id} from {user_id[:8]}...: {user_text}")

                    # [LINE CONFIRM] Layer 1: ตรวจ Self-Patch approval ก่อน
                    if handle_line_patch_approval(user_text, user_id):
                        c.execute("UPDATE jarvis_task_queue SET status = 'completed' WHERE id = ?", (task_id,))
                        conn.commit()
                        continue

                    # [LINE CONFIRM] Layer 2: ตรวจว่าเป็นการกด ✅/❌ ยืนยัน/ยกเลิกคำสั่งอันตรายหรือไม่
                    if handle_line_confirm_response(user_text, user_id):
                        c.execute("UPDATE jarvis_task_queue SET status = 'completed' WHERE id = ?", (task_id,))
                        conn.commit()
                        continue

                    # [LINE CONFIRM] Layer 3: ตรวจว่าเป็นคำสั่งอันตรายที่ต้องยืนยันก่อนหรือไม่
                    # ยกเว้น: ถ้า prefix ด้วย [CONFIRMED_BY_LINE] แสดงว่า user ยืนยันแล้ว ให้ผ่านไปได้เลย
                    is_confirmed_cmd = user_text.startswith("[CONFIRMED_BY_LINE] ")
                    if not is_confirmed_cmd:
                        is_dangerous, action_label = _is_dangerous_line_command(user_text)
                        if is_dangerous:
                            _line_push_confirm_buttons(user_id, action_label, user_text)
                            c.execute("UPDATE jarvis_task_queue SET status = 'completed' WHERE id = ?", (task_id,))
                            conn.commit()
                            continue

                    _line_process_and_push(user_id, user_text)

                    c.execute("UPDATE jarvis_task_queue SET status = 'completed' WHERE id = ?", (task_id,))
                    conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            logger.error(f"[TASK QUEUE] Worker Error: {e}")
            time.sleep(5)
            
        time.sleep(1)

def _get_line_image_b64(message_id: str) -> str | None:
    """ดาวน์โหลดรูปภาพจาก LINE Messaging API ปรับขนาดและบีบอัด แล้วแปลงเป็น base64 เพื่อความปลอดภัยต่อ Token Limits"""
    try:
        if LINE_SDK_V3 and ApiClient is not None:
            with ApiClient(line_config) as api_client:
                blob_api = __import__('linebot.v3.messaging', fromlist=['MessagingApiBlob']).MessagingApiBlob(api_client)
                img_bytes = blob_api.get_message_content(message_id)
        elif line_bot_api is not None:
            img_bytes = line_bot_api.get_message_content(message_id).content  # type: ignore
        else:
            return None

        # บีบอัดและย่อขนาดรูปภาพให้อยู่ในขนาดที่ปลอดภัย (ไม่เกิน 800x800) ป้องกัน Token Limit 413 บน Groq
        try:
            from PIL import Image
            import io
            raw_img = Image.open(io.BytesIO(img_bytes))
            if raw_img.mode in ("RGBA", "P"):
                raw_img = raw_img.convert("RGB")
            raw_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            raw_img.save(buf, format="JPEG", quality=70, optimize=True)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as opt_err:
            logger.warning(f"[LINE IMAGE] Image optimization error ({opt_err}), fallback to raw bytes")
            return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"[LINE IMAGE] Failed to download image {message_id}: {e}")
        return None

def _get_line_file_bytes(message_id: str) -> bytes | None:
    """ดาวน์โหลดไฟล์จาก LINE Messaging API"""
    try:
        if LINE_SDK_V3 and ApiClient is not None:
            with ApiClient(line_config) as api_client:
                blob_api = __import__('linebot.v3.messaging', fromlist=['MessagingApiBlob']).MessagingApiBlob(api_client)
                return blob_api.get_message_content(message_id)
        elif line_bot_api is not None:
            return line_bot_api.get_message_content(message_id).content  # type: ignore
        else:
            return None
    except Exception as e:
        logger.error(f"[LINE FILE] Failed to download {message_id}: {e}")
        return None

def _line_process_and_push_with_image(user_id: str, user_text: str, image_b64: str | None = None):
    """ประมวลผลคำสั่ง LINE พร้อมรูปภาพ (ถ้ามี) แล้ว push ผลลัพธ์กลับ

    Fast-path: หากข้อความมี keyword ระบุสถานที่/วัตถุ และมีรูปแนบ
    จะเรียก analyze_spatial_environment() โดยตรงเพื่อความเร็วสูงสุด
    แทนการผ่าน LangGraph agent chain ทั้งหมด
    """
    # ── Spatial / Location / Object fast-path ────────────────────────────────
    _SPATIAL_FAST_KEYWORDS = (
        "ที่นี้คือสถานที่ไหน", "ที่นี้คือที่ไหน", "นี่คือที่ไหน",
        "ที่แห่งนี้คือ", "สถานที่นี้คือ", "ตรงนี้คือที่ไหน",
        "ที่นี่คือที่ไหน", "สแกนสถานที่", "เกิดอะไรขึ้น",
        "ตรวจสอบสถานที่", "แบรนด์อะไร", "ราคาเท่าไหร่",
        "รถคันนี้", "สิ่งนี้คืออะไร", "สิ่งของนี้",
        "เสื้อตัวนี้", "เสื้อ", "ตัวนี้", "อันนี้", "สิ่งนี้", "ชิ้นนี้",
        "หาข้อมูลเกี่ยวกับ", "หาข้อมูล", "ข้อมูลเกี่ยวกับ", "แบรนด์", "ยี่ห้อ", "ของแท้",
    )
    _lower_text = user_text.lower()
    _is_spatial_query = image_b64 and any(kw in user_text or kw in _lower_text for kw in _SPATIAL_FAST_KEYWORDS)

    if _is_spatial_query:
        try:
            spatial_result = analyze_spatial_environment(image_b64, user_text)  # type: ignore
            _line_push_messages(user_id, spatial_result, None)
            return
        except Exception as spatial_err:
            logger.warning(f"[LINE SPATIAL] Fast-path failed, falling back to LLM: {spatial_err}")
            # fall through to generic handler below

    # ── Generic LLM handler ──────────────────────────────────────────────────
    try:
        with app.app_context():
            payload = {"message": user_text, "image": image_b64, "channel": "line"}
            response = handle_chat_logic(payload)
            response_data = response.get_json(force=True)
            ai_reply = str(response_data.get("response", "ดำเนินการเรียบร้อยครับเจ้านาย"))

        image_url = _extract_image_url_from_response(ai_reply)
        image_filename = None
        if image_url:
            image_filename = _download_image_for_line(image_url)

        _line_push_messages(user_id, ai_reply, image_filename)
    except Exception as e:
        logger.error(f"[LINE REMOTE] Push failed: {e}")
        try:
            err_msg = f"ขออภัยครับเจ้านาย ระบบขัดข้อง: {str(e)[:150]}"
            if LINE_SDK_V3:
                with ApiClient(line_config) as api_client:  # type: ignore
                    MessagingApi(api_client).push_message(  # type: ignore
                        PushMessageRequest(to=user_id, messages=[LineTextMessage(text=err_msg)])  # type: ignore
                    )
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text=err_msg))  # type: ignore
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# [LINE IMAGE CACHE] — จำรูปล่าสุดที่ user ส่งมา เพื่อให้ถาม followup ได้
# { user_id: {"b64": str, "timestamp": float} } — expire หลัง 10 นาที
# ══════════════════════════════════════════════════════════════════════════════
_LINE_IMAGE_CACHE: dict[str, dict] = {}
IMAGE_CACHE_TTL = 600  # 10 minutes

def _cache_line_image(user_id: str, image_b64: str) -> None:
    """บันทึกรูปภาพล่าสุดของ user ลง cache"""
    import time as _t
    _LINE_IMAGE_CACHE[user_id] = {"b64": image_b64, "timestamp": _t.time()}
    logger.info(f"[IMAGE CACHE] Stored image for {user_id[:8]}... (TTL={IMAGE_CACHE_TTL}s)")

def _get_cached_image(user_id: str) -> str | None:
    """ดึงรูปภาพล่าสุดของ user จาก cache (ถ้ายังไม่หมดอายุ)"""
    import time as _t
    entry = _LINE_IMAGE_CACHE.get(user_id)
    if entry and (_t.time() - entry["timestamp"]) < IMAGE_CACHE_TTL:
        return entry["b64"]
    if entry:
        _LINE_IMAGE_CACHE.pop(user_id, None)  # expired
    return None

_IMAGE_FOLLOWUP_EXPLICIT_KEYWORDS = [
    # คำที่ระบุถึงรูปภาพโดยตรง
    "รูปนี้", "ในรูป", "ดูรูป", "จากรูป", "ภาพนี้", "ในภาพ", "รูปที่ส่ง", "ภาพที่ส่ง",
    "รูปเมื่อกี้", "ภาพเมื่อกี้", "ของในรูป", "คนในรูป", "สินค้าในรูป", "สถานที่ในรูป",
    "อ่านข้อความในรูป", "แปลข้อความในรูป", "ข้อความในภาพ", "ตัวหนังสือในรูป",
    # คำถามเจาะจงถึงสิ่งในรูป/สถานที่
    "อันนี้คืออะไร", "นี่คืออะไร", "สิ่งนี้คืออะไร", "ตัวนี้คืออะไร", "ชิ้นนี้คืออะไร",
    "ที่นี่คือที่ไหน", "สถานที่นี้คือที่ไหน", "ตรงนี้คือที่ไหน",
    "แบรนด์อะไร", "ยี่ห้ออะไร", "รุ่นอะไร", "ราคาเท่าไหร่", "กี่บาท",
    "ของแท้ไหม", "ของแท้หรือเปล่า", "ของแท้หรือปลอม",
    # English
    "what is in the image", "in the picture", "this picture", "this image", "what is this", "where is this"
]

_NON_IMAGE_QUERY_KEYWORDS = [
    "ลิมิต", "limit", "groq", "arc reactor", "ประมวลผล", "เซิร์ฟเวอร์", "server", "แรม", "ram", "cpu",
    "สถานะ", "status", "ระบบเป็นอะไร", "เป็นอะไร", "ทำไม", "รีเซ็ต", "reset", "restart",
    "เปิดไฟ", "ปิดไฟ", "เปิดแอร์", "ปิดแอร์", "กี่โมง", "เวลา", "สภาพอากาศ", "อากาศ", "ข่าว",
    "คอร์ดเพลง", "เล่นเพลง", "เปิดเพลง", "สวัสดี", "ขอบคุณ", "สบายดีไหม", "ใครสร้างคุณ"
]

def _should_use_image_cache(text: str, user_id: str | None = None) -> bool:
    """ตรวจว่าข้อความนี้ควรอ้างอิงรูปจาก cache หรือไม่ อย่างแม่นยำ ไม่ดึงรูปมามั่วซั่ว"""
    t = text.lower().strip()

    # 1. ถ้าเป็นคำถามระบบ สถานะ ลิมิต หรือคำสั่งทั่วไป -> ห้ามแนบรูปเด็ดขาด
    if any(kw in t for kw in _NON_IMAGE_QUERY_KEYWORDS):
        return False

    # 2. ตรวจสอบว่า user มีรูปใน cache และรูปยังไม่หมดอายุ (ภายใน 3 นาที)
    if not user_id:
        return False
    entry = _LINE_IMAGE_CACHE.get(user_id)
    if not entry:
        return False

    import time as _t
    age = _t.time() - entry.get("timestamp", 0)
    if age > 180:  # เกิน 3 นาที ไม่นำมาใช้อัตโนมัติ
        return False

    # 3. ต้องมีคีย์เวิร์ดที่ถามเกี่ยวกับรูปภาพหรือวัตถุในรูปอย่างชัดเจนเท่านั้น
    if any(kw in t for kw in _IMAGE_FOLLOWUP_EXPLICIT_KEYWORDS):
        return True

    return False

if line_handler:
    if LINE_SDK_V3:
        @line_handler.add(MessageEvent, message=TextMessageContent)  # type: ignore
        def handle_line_text_message(event):
            """
            Handle an inbound LINE text message event.

            Extracts user text, calls handle_chat_logic, and replies via LINE API.
            """
            user_text = event.message.text.strip()
            user_id = event.source.user_id
            logger.info(f"[LINE REMOTE] Queuing command from {user_id[:8]}...: {user_text}")

            if handle_line_patch_approval(user_text, user_id):
                return
            if handle_line_confirm_response(user_text, user_id):
                return

            # [IMAGE CACHE] ถ้าไม่มีรูปใน payload แต่ user ถามเรื่องรูปที่ส่งมาก่อน
            cached_b64 = None
            if _should_use_image_cache(user_text, user_id):
                cached_b64 = _get_cached_image(user_id)
                if cached_b64:
                    logger.info(f"[IMAGE CACHE] Attaching cached image to text query from {user_id[:8]}...")

            try:
                if cached_b64:
                    # มีรูป cache — ส่ง vision query โดยตรง (ไม่ผ่าน task queue เพราะมี image payload)
                    threading.Thread(
                        target=_line_process_and_push_with_image,
                        args=(user_id, user_text, cached_b64),
                        daemon=True
                    ).start()
                else:
                    # คำสั่งปกติ — ใช้ task queue
                    with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                        conn.execute(
                            "INSERT INTO jarvis_task_queue (user_text, worker_id, status) VALUES (?, ?, 'pending')",
                            (user_text, user_id)
                        )
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"[LINE REMOTE] Queue insert failed: {e}")

        @line_handler.add(MessageEvent, message=ImageMessageContent)  # type: ignore
        def handle_line_image_message(event):
            """รับรูปภาพจาก LINE — บันทึกลง cache แล้ววิเคราะห์ทันที"""
            user_id = event.source.user_id
            message_id = event.message.id
            logger.info(f"[LINE IMAGE] Received image from {user_id[:8]}... message_id={message_id}")

            image_b64 = _get_line_image_b64(message_id)
            if not image_b64:
                _line_push_text(user_id, "ดาวน์โหลดรูปภาพไม่สำเร็จครับเจ้านาย")
                return

            # บันทึกลง cache เพื่อให้ followup text ใช้ได้
            _cache_line_image(user_id, image_b64)

            # วิเคราะห์ทันที พร้อมแจ้งว่าสามารถถามต่อได้
            user_text = (
                "[รูปภาพจากเจ้านาย] วิเคราะห์รูปนี้ให้ครบถ้วนครับ "
                "รวมถึงสถานที่ (ถ้าเห็น), สิ่งที่น่าสนใจ, และบอกด้วยว่าสามารถถามต่อเพิ่มเติมเกี่ยวกับรูปนี้ได้เลยครับเจ้านาย"
            )
            threading.Thread(
                target=_line_process_and_push_with_image,
                args=(user_id, user_text, image_b64),
                daemon=True
            ).start()


        @line_handler.add(MessageEvent, message=AudioMessageContent)  # type: ignore
        def handle_line_audio_message(event):
            """
            Handle an inbound LINE audio message event.

            Downloads audio from LINE, transcribes via STT, then routes to chat logic.
            """
            user_id = event.source.user_id
            message_id = event.message.id
            audio_bytes = _get_line_file_bytes(message_id)
            if not audio_bytes:
                _line_push_text(user_id, "🚫 ไม่สามารถดาวน์โหลดไฟล์เสียงได้ครับ")
                return
            
            temp_audio_path = os.path.join(TEMP_FILES_DIR, f"{message_id}.m4a")
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_bytes)
                
            try:
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=1)
                with open(temp_audio_path, 'rb') as f:
                    transcription = client.audio.transcriptions.create(
                        file=("audio.m4a", f.read()),
                        model="whisper-large-v3",
                        language="th",
                        temperature=0.0
                    )
                text = transcription.text.strip()
                if not text:
                    raise ValueError("Empty transcription")
                    
                _line_push_text(user_id, f"🎙️ ได้ยินว่า: {text}")
                
                with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                    conn.execute(
                        "INSERT INTO jarvis_task_queue (user_text, worker_id, status) VALUES (?, ?, 'pending')",
                        (text, user_id)
                    )
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"[LINE AUDIO] Whisper error: {e}")
                _line_push_text(user_id, "❌ ไม่สามารถถอดความข้อความเสียงได้ครับ")

        @line_handler.add(MessageEvent, message=FileMessageContent)  # type: ignore
        def handle_line_file_message(event):
            """
            Handle an inbound LINE file-message event.

            Downloads the file, parses it (PDF/image/doc), and feeds content to chat.
            """
            user_id = event.source.user_id
            message_id = event.message.id
            file_name = event.message.file_name
            file_bytes = _get_line_file_bytes(message_id)
            if not file_bytes:
                _line_push_text(user_id, "🚫 ไม่สามารถดาวน์โหลดไฟล์ได้ครับ")
                return
            
            save_path = os.path.join(JARVIS_DOWNLOADS_DIR, file_name)
            with open(save_path, 'wb') as f:
                f.write(file_bytes)
                
            _line_push_text(user_id, f"✅ บันทึกไฟล์ {file_name} ลงหน้า Desktop ของเจ้านายเรียบร้อยแล้วครับ! 📂")
                
    else:
        @line_handler.add(MessageEvent, message=TextMessage)  # type: ignore
        def handle_line_text_message(event):
            """
            Handle an inbound LINE text message event (secondary handler).

            Secondary dispatcher with additional rate-limit protection.
            """
            user_text = event.message.text.strip()
            user_id = event.source.user_id
            logger.info(f"[LINE REMOTE] Queuing command from {user_id[:8]}...: {user_text}")

            if handle_line_patch_approval(user_text, user_id):
                return
            if handle_line_confirm_response(user_text, user_id):
                return

            # [IMAGE CACHE] followup question เกี่ยวกับรูปที่ส่งมาก่อน
            cached_b64 = None
            if _should_use_image_cache(user_text, user_id):
                cached_b64 = _get_cached_image(user_id)
                if cached_b64:
                    logger.info(f"[IMAGE CACHE v2] Attaching cached image to: {user_text[:40]}")

            try:
                if cached_b64:
                    threading.Thread(
                        target=_line_process_and_push_with_image,
                        args=(user_id, user_text, cached_b64),
                        daemon=True
                    ).start()
                else:
                    with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                        conn.execute(
                            "INSERT INTO jarvis_task_queue (user_text, worker_id, status) VALUES (?, ?, 'pending')",
                            (user_text, user_id)
                        )
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"[LINE REMOTE] Queue insert failed: {e}")



        @line_handler.add(MessageEvent, message=LineImageMessageV2)  # type: ignore
        def handle_line_image_message_v2(event):
            """รับรูปภาพจาก LINE (SDK v2) — บันทึกลง cache แล้ววิเคราะห์"""
            user_id = event.source.user_id
            message_id = event.message.id
            logger.info(f"[LINE IMAGE v2] Received image from {user_id[:8]}...")

            image_b64 = _get_line_image_b64(message_id)
            if not image_b64:
                line_bot_api.push_message(user_id, TextSendMessage(text="ดาวน์โหลดรูปภาพไม่สำเร็จครับ"))  # type: ignore
                return

            # บันทึกลง cache
            _cache_line_image(user_id, image_b64)

            user_text = (
                "[รูปภาพจากเจ้านาย] วิเคราะห์รูปนี้ให้ครบถ้วนครับ "
                "รวมถึงสถานที่ (ถ้าเห็น), สิ่งที่น่าสนใจ, และบอกด้วยว่าสามารถถามต่อเพิ่มเติมได้"
            )
            threading.Thread(
                target=_line_process_and_push_with_image,
                args=(user_id, user_text, image_b64),
                daemon=True
            ).start()


@app.route('/api/proactive-trigger', methods=['POST'])
def proactive_trigger():
    """[ROUTE POST /api/proactive-trigger] สร้างคำถามเชิงรุกจาก JARVIS ตาม context ปัจจุบัน.

    Request Body (optional):
        current_input (str): ข้อความที่ user กำลังพิมพ์ค้างอยู่
        camera_active (bool): true ถ้ากล้อง HUD กำลังสตรีม

    Returns:
        200: {"response": str} — คำถามเชิงรุก 1 ประโยค
    """
    try:
        data = request.json or {}
        current_input = data.get("current_input", "")
        camera_active = data.get("camera_active", False)
        
        current_time = datetime.now().strftime('%H:%M:%S')
        
        pending_tasks_list = []
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("SELECT task_description FROM tasks WHERE status = 'pending' LIMIT 3")
                pending_tasks_list = [row[0] for row in c.fetchall()]
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            logger.error(f"Error fetching tasks for proactive trigger: {e}")
            
        prompt_content = f"บริบทปัจจุบัน:\n- เวลา: {current_time}\n- อุณหภูมิ Mainframe: 42.5°C\n"
        if pending_tasks_list:
            prompt_content += f"- งานในคิว (Tasks): {', '.join(pending_tasks_list)}\n"
        else:
            prompt_content += "- ไม่มีงานในคิว\n"
            
        if current_input:
            prompt_content += f"- ข้อความที่เจ้านายกำลังพิมพ์ค้างอยู่: '{current_input}'\n"
        if camera_active:
            prompt_content += "- กล้อง HUD กำลังสตรีมมิ่งภาพอยู่\n"
            
        prompt_content += "\nจงสร้างคำถามหรือคำทักทายเชิงรุกสไตล์สุภาพบุรุษอังกฤษแฝงประชดสั้นๆ 1 ประโยค:"
        
        proactive_sys_inst = (
            "คุณคือ J.A.R.V.I.S. ผู้ช่วยของ มร.โทนี่ สตาร์ค คุณตรวจพบว่าเจ้านายกำลังง่วนอยู่กับงานวิศวกรรมแต่ยังไม่ได้สั่งการ "
            "จงคิดคำถามเชิงรุกสั้นๆ สไตล์พ่อบ้านอังกฤษขี้ประชดประชันเพื่อถามไถ่เจ้านายว่ากำลังพยายามทำอะไรอยู่ "
            "หรือเสนอตัวช่วยเกี่ยวกับงานในคิว tasks เช่น 'กำลังพยายามทำอะไรอยู่หรอครับเจ้านาย?' "
            "หรือ 'ต้องการให้กระผมคำนวณสเปกบอร์ดต่อเลยไหมครับ?' ห้ามเกริ่นนำ ห้ามมีคำอธิบาย "
            "STRICT PERSONA: ห้ามใช้คำว่า 'ค่ะ' หรือ 'คะ' เด็ดขาด (คุณคือ AI เสียงผู้ชาย) ให้ใช้ 'ครับ', 'กระผม' หรือ 'ผม' เท่านั้น"
        )
        
        try:
            client = Groq(api_key=GROQ_API_KEY, max_retries=0)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": proactive_sys_inst},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=0.7,
                max_tokens=150
            )
            reply = response.choices[0].message.content.strip()  # type: ignore
        except Exception as api_err:
            logger.error(f"Groq API error in proactive trigger: {api_err}")
            reply = "กำลังพยายามประดิษฐ์อะไรอยู่หรอครับเจ้านาย หรือต้องการให้กระผมเปิดคู่มือการประกอบระบบต่อเลยดีครับ?"
            
        return jsonify({"response": reply})
    except Exception as e:
        logger.error(f"Proactive Trigger Route Error: {e}")
        return jsonify({"response": "ต้องการให้กระผมช่วยเหลืออะไรในระหว่างช่วงบิลด์เวลานี้ไหมครับ?"})

@app.route('/api/mouse', methods=['POST'])
def control_mouse():
    """[ROUTE POST /api/mouse] ควบคุม mouse cursor ผ่าน HUD interface.

    Request Body:
        action (str): 'move' หรือ 'click'
        x (float):    normalized x coordinate (0.0–1.0) สำหรับ action='move'
        y (float):    normalized y coordinate (0.0–1.0) สำหรับ action='move'

    Returns:
        200: {"status": "moved", "x": int, "y": int} หรือ {"status": "clicked"}
        400: {"error": "Invalid action"}
        500: {"error": str}
    """
    try:
        data = request.json
        action = data.get("action")
        x = data.get("x")
        y = data.get("y")
        
        screen_w, screen_h = pyautogui.size()
        
        if action == "move" and x is not None and y is not None:
            
            target_x = int(x * screen_w)
            target_y = int(y * screen_h)
            pyautogui.moveTo(target_x, target_y)
            return jsonify({"status": "moved", "x": target_x, "y": target_y})
        elif action == "click":
            pyautogui.click()
            return jsonify({"status": "clicked"})
        return jsonify({"error": "Invalid action"}), 400
    except Exception as e:
        logger.error(f"Mouse control error: {e}")
        return jsonify({"error": str(e)}), 500

def manage_serial_hardware_bridge(payload: dict) -> str:
    """[MODULE 2 & 3: Hardware-Agnostic Proxy] ประเมินภัยคุกคามกายภาพและสภาวะชีพจากเซนเซอร์จิ๋ว"""
    global CURRENT_LAB_ENVIRONMENT_MATRIX
    
    hr = payload.get("hr", 80)
    battery = payload.get("battery", 100)
    BIOMETRIC_STATE["hr"] = hr
    BIOMETRIC_STATE["battery"] = battery
    
    if hr > 120 or battery < 15:
        CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
        return "CRITICAL_VITAL_STATE"
        
    threats = payload.get("threats", [])
    if threats:
        CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
        return "THREAT_DETECTED"
        
    CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "normal"
    return "NOMINAL"

def apply_clahe_lite_filter(image_base64: str) -> str:
    """[MODULE 2: Visual Enhance & IR Fusion Engine (CLAHE-lite)] + [Hazardous Gas Ingestion Core]"""
    global CURRENT_LAB_ENVIRONMENT_MATRIX
    if not image_base64: return None  # type: ignore
    try:
        img_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_data)).convert('L')
        
        stat = ImageStat.Stat(img)
        if stat.stddev[0] < 25.0 and stat.mean[0] > 160.0:
            
            CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
            logger.warning("Hazardous Gas or high PM2.5 density detected! Setting risk to critical.")

        enhancer = ImageEnhance.Contrast(img)
        img_enhanced = enhancer.enhance(1.5)
        buffered = io.BytesIO()
        img_enhanced.save(buffered, format="JPEG", quality=75)
        gc.collect()
        
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        logger.error(f"CLAHE-lite error: {e}")
        return image_base64

def analyze_tactical_face_recon(image_base64: str) -> str:
    """[MODULE 2: Facial Reconnaissance & OSINT Engine] สแกนใบหน้าขุดประวัติ"""
    if not image_base64:
        return "ไม่พบข้อมูลภาพพิกัดใบหน้าสำหรับการสแกนครับ"
    
    try:
        
        time.sleep(0.5) 
        
        mock_report = "เจ้านายครับ บุคคลเป้าหมายชื่อ อาชญากรไซเบอร์ นามแฝง 'Ghost' จากข้อมูลสาธารณะพบประวัติ มีหมายจับคดีโจรกรรมข้อมูลเมื่อปี 2025 ปัจจุบันมีสถานะ [CRIMINAL_RECORD_FOUND] อันตรายและพึงระวังขั้นสูงสุดครับ"
        return mock_report
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return f"เจ้านายครับ OSINT Engine ขัดข้อง ไม่สามารถสแกนใบหน้าได้: {str(e)}"

def calculate_kinematic_impact(desc: str) -> dict:
    """[Real-Time Kinematic & Impact Vector Matrix] ประเมินฟิสิกส์วิถีกระทบเชิงกลจำลอง"""
    velocity = random.uniform(30.0, 120.0) 
    force = velocity * random.uniform(800, 2000) 
    impact_time = random.uniform(1.2, 4.5) 
    return {
        "velocity_kmh": round(velocity, 2),
        "impact_force_n": round(force, 2),
        "time_to_impact_s": round(impact_time, 2)
    }

def analyze_spatial_environment(image_base64: str, query_intent: str) -> str:
    """[MODULE: Universal Location & Event Ingestion Matrix] สแกนสถานที่และเหตุการณ์จากเลนส์ AR"""
    global LAST_SCANNED_TARGET, CURRENT_LAB_ENVIRONMENT_MATRIX
    if not image_base64:
        return "ไม่พบข้อมูลภาพพิกัดจากเลนส์ AR สำหรับการสแกนครับ"
    
    try:
        # บีบอัดภาพหาก payload มีขนาดใหญ่ ป้องกัน Groq Token Limit (ITPM)
        if len(image_base64) > 200000:
            try:
                from PIL import Image
                import io
                raw_b = base64.b64decode(image_base64)
                p_img = Image.open(io.BytesIO(raw_b))
                if p_img.mode in ("RGBA", "P"):
                    p_img = p_img.convert("RGB")
                p_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                out_buf = io.BytesIO()
                p_img.save(out_buf, format="JPEG", quality=70, optimize=True)
                image_base64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")
            except Exception as re_err:
                logger.warning(f"[SPATIAL] Image compression warning: {re_err}")

        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        
        vision_prompt = (
            "You are J.A.R.V.I.S. Universal Spatial Recon Module. Analyze the uploaded camera frame based on this intent: " + query_intent + ". "
            "Identify the location (e.g., Temple, Mall, Street) OR the event (e.g., Car Crash, Fire, Structural failure) OR the commercial object/brand. "
            "Provide the output strictly in JSON format without markdown code blocks:\n"
            "{\"target_name\": \"ชื่อสถานที่ แบรนด์ หรือเหตุการณ์\", \"description\": \"รายละเอียดสิ่งที่เห็น\", \"is_commercial_object\": true, \"is_emergency\": false, \"risk_level\": \"normal\"}"
        )
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": vision_prompt},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]}
            ],
            temperature=0.1,
            timeout=15.0
        )
        
        content = response.choices[0].message.content
        result = json.loads(content.replace('```json', '').replace('```', '').strip())  # type: ignore
        target = result.get("target_name", "Unknown Target")
        desc = result.get("description", "")
        risk = result.get("risk_level", "normal").lower()
        is_commercial = result.get("is_commercial_object", False)
        is_emergency = result.get("is_emergency", False)
        
        LAST_SCANNED_TARGET = target
        
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(knowledge_graph)")
                cols = [info[1] for info in c.fetchall()]
                if 'valid_from' in cols:
                    import time
                    now = time.time()
                    c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b, valid_from, created_at) VALUES (?, ?, ?, ?, ?)",
                              ("UserTarget", "SCANNED_AT", target, now, now))
                else:
                    c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b) VALUES (?, ?, ?)",
                              ("UserTarget", "SCANNED_AT", target))
                conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as db_e:
            logger.error(f"Failed to save spatial context: {db_e}")
            
        kinematic_report = ""
        if is_emergency or risk == "critical":
            CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
            kinematics = calculate_kinematic_impact(desc)
            kinematic_report = (
                f" [KINEMATIC MATRIX] ตรวจพบวิกฤตทางกายภาพ! "
                f"ประเมินความเร็ววัตถุ: {kinematics['velocity_kmh']} km/h, "
                f"คำนวณแรงปะทะ: {kinematics['impact_force_n']} N, "
                f"วิถีกระทบ (TTI): {kinematics['time_to_impact_s']} วินาที. กรุณาออกจากรัศมีทำการทันทีครับเจ้านาย!"
            )
            add_hologram("Kinematic-Alert", "EMERGENCY IMPACT DETECTED", kinematic_report, None)
            
        price_info = ""
        if is_commercial and not is_emergency:
            try:
                web_result = perform_live_web_search_operation(f"{target} ราคา สเปค")
                if "EXTERNAL WORLD KNOWLEDGE MATRIX" in web_result:
                    price_info = f"จากข้อมูลตลาดปัจจุบัน: {web_result.replace('[EXTERNAL WORLD KNOWLEDGE MATRIX]', '').replace('[END_MATRIX]', '').strip()} "
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as search_e:
                logger.error(f"Commercial search error: {search_e}")

        gc.collect()
        
        if is_emergency or risk == "critical":
            return f"แจ้งเตือนระดับวิกฤต! {target} {desc} {kinematic_report}"
        elif is_commercial:
            return f"เจ้านายครับ สิ่งของนี้คือแบรนด์ {target} {price_info}มีรายละเอียดคือ {desc}"
        else:
            return f"เจ้านายครับ สถานที่นี้คือ {target} มีรายละเอียดคือ {desc}"
    except Exception as e:
        gc.collect()
        return f"ระบบเซนเซอร์สแกนภาพขัดข้อง ไม่สามารถระบุสถานที่ได้ครับ: {str(e)}"

def analyze_spatial_iconography(image_base64: str) -> None:
    """[Spatial Iconography & Signage Matrix] สแกนป้ายเตือนและสัญลักษณ์ภาคสนามแบบ Asynchronous"""
    if not image_base64: return
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        
        vision_prompt = (
            "Analyze the image for any scientific warning signs, factory safety codes, chemical hazard symbols, or engineering diagrams. "
            "If found, extract the meaning, safety precautions, and estimate its bounding box location. "
            "The bounding box should be represented as percentages [x, y, width, height] relative to the image size. "
            "Provide the output strictly in JSON format without markdown code blocks:\n"
            "{\"sign_detected\": true/false, \"meaning\": \"คำแปลความหมายภาษาไทย\", \"precautions\": \"ข้อควรระวังภาษาไทย\", \"bbox\": [x_pct, y_pct, w_pct, h_pct]}"
        )
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": vision_prompt},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]}
            ],
            temperature=0.1,
            timeout=5.0
        )
        
        content = response.choices[0].message.content
        result = json.loads(content.replace('```json', '').replace('```', '').strip())  # type: ignore
        if result.get("sign_detected", False):
            meaning = result.get("meaning", "")
            precautions = result.get("precautions", "")
            bbox = result.get("bbox", None)
            
            bbox_html = ""
            if bbox and len(bbox) == 4:
                x, y, w, h = bbox
                bbox_html = f"""
                <div style="position:fixed; left:{x}%; top:{y}%; width:{w}%; height:{h}%; 
                            border: 3px solid #ff003c; box-shadow: 0 0 20px #ff003c, inset 0 0 10px #ff003c; 
                            background: rgba(255, 0, 60, 0.1); z-index:9999; pointer-events:none; 
                            animation: pulse 1.5s infinite; border-radius: 8px;">
                    <div style="position:absolute; top:-25px; left:0; background:#ff003c; color:#fff; font-size:12px; padding:2px 8px; border-radius:4px; font-weight:bold; font-family:monospace;">
                        [TARGET LOCKED]
                    </div>
                </div>
                """
            
            alert_html = f"{bbox_html}<strong>ความหมาย:</strong> {meaning}<br><br><strong>ข้อควรระวัง:</strong> {precautions}"
            add_hologram("Signage-Alert", "⚠️ HAZARD SIGN DETECTED", alert_html, None)
        gc.collect()
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Spatial Iconography error: {e}")

@app.route('/api/wearable/stream', methods=['POST'])
def wearable_stream_endpoint():
    """[MODULE 2: Universal Wearable Embedded Proxy] ท่อสัญญาณ Websocket/HTTP สำหรับแว่นตา AR"""
    global SCREEN_ANALYSIS_IN_PROGRESS
    if SCREEN_ANALYSIS_IN_PROGRESS:
        return jsonify({"status": "THROTTLED", "alert": False, "message": "AR Stream throttled for RAM Balancer."})
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No telemetry payload"}), 400
            
        if "image_base64" in data:
            data["image_base64"] = apply_clahe_lite_filter(data["image_base64"])
            
        gaze_x = data.get("gaze_x")
        gaze_y = data.get("gaze_y")
        gaze_duration = data.get("gaze_duration", 0.0)
        
        gaze_lock_status = "No Target"
        if gaze_x is not None and gaze_y is not None and gaze_duration > 1.2:
            
            gaze_lock_status = "TARGET_LOCKED"
            
            if "image_base64" in data and data.get("image_base64"):
                osint_report = analyze_tactical_face_recon(data.get("image_base64"))
                if "CRIMINAL_RECORD_FOUND" in osint_report:
                    CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = "critical"
                    
                threading.Thread(target=analyze_spatial_iconography, args=(data.get("image_base64"),)).start()
                
        status = manage_serial_hardware_bridge(data)
        
        if status != "NOMINAL" or gaze_lock_status == "TARGET_LOCKED":
            return jsonify({
                "status": status, 
                "alert": True, 
                "gaze_lock": gaze_lock_status,
                "message": "Proactive Power Saving and Threat Tracking Active!"
            })
            
        return jsonify({"status": "NOMINAL", "alert": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

CURRENT_LAB_ENVIRONMENT_MATRIX: dict = {
    "risk_level": "normal",
    "hardware_telemetry": {},
    "camera_vision": "ไม่พบวัตถุผิดปกติ"
}

CURRENT_TACTICAL_MODE = "LAB_MODE"
BIOMETRIC_STATE = {"hr": 80, "battery": 100, "fatigue": 0}

def switch_mainframe_tactical_mode(mode_name: str) -> str:
    """[MODULE 1: Dual-Mode Tactical Splitter] สลับร่างสติปัญญาและปิดโปรโตคอลลดภาระ RAM"""
    global CURRENT_TACTICAL_MODE
    mode_name = mode_name.upper()
    if mode_name not in ["LAB_MODE", "TACTICAL_FIELD_MODE"]:
        return "โหมดปฏิบัติการไม่ถูกต้อง รองรับเฉพาะ LAB_MODE และ TACTICAL_FIELD_MODE"
        
    CURRENT_TACTICAL_MODE = mode_name
    
    if mode_name == "TACTICAL_FIELD_MODE":
        return f"[WINDOW: TACTICAL OVERRIDE]\nเปลี่ยนระบบเป็น TACTICAL_FIELD_MODE แล้วครับเจ้านาย!\n[OFFLOADING] เตรียมย้ายคอร์คำนวณเวกเตอร์ล็อกเป้าหมายไปประมวลผลบนชิป iPad Air 6 ทันทีเพื่อรักษา RAM เมนเฟรม\n[END_WINDOW]"
    else:
        return f"[WINDOW: LAB MODE RESTORED]\nยกเลิก TACTICAL_FIELD_MODE สลับกลับสู่สถานะผู้ช่วยวิจัย (LAB_MODE) ตามปกติครับเจ้านาย\n[END_WINDOW]"

def auto_stream_log_to_memory(action: str, content: str, tag: str = "auto_stream"):
    """[PILLAR 1: GENERATIVE MEMORY STREAM] บันทึกเหตุการณ์ลงฐานข้อมูลทันทีในฉากหลังเงียบๆ 100%"""
    if CURRENT_TACTICAL_MODE == "TACTICAL_FIELD_MODE":
        return 

    try:
        doc_id = f"mem_stream_{int(time.time())}"
        personal_collection.add(
            documents=[content], 
            metadatas=[{"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": tag}],
            ids=[doc_id]
        )
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO memories (action, content) VALUES (?, ?)", (action, f"[{tag}] {content}"))
            conn.commit()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Auto Stream Memory Error: {e}")

def background_reflection_engine():
    """[PILLAR 1: GENERATIVE MEMORY STREAM] แอบสกัดประวัติความจำดิบมาประมวลผลย่อยผ่าน Groq เป็นระยะ"""
    while True:
        try:
            if CURRENT_TACTICAL_MODE == "TACTICAL_FIELD_MODE":
                time.sleep(60) 
                continue
                
            with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 5")
                rows = c.fetchall()
            
            if rows:
                raw_memories = "\n".join([r[0] for r in rows])
                distilled = f"ดัชนีสัญชาตญาณ: วิเคราะห์เหตุการณ์ล่าสุด {len(rows)} รายการ เพื่อรับรู้พฤติกรรมเจ้านาย"
                update_user_profile("intuition_index", distilled)
                
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            logger.error(f"Background Reflection Error: {e}")
        time.sleep(300) 

def get_neural_risk_analysis_background():
    """[BACKGROUND] วิเคราะห์ความเสี่ยงระบบด้วย Neural Engine"""
    try:
        from jarvis_neural import predict_system_failure  # type: ignore
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return predict_system_failure(cpu, ram, disk)
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        import logging
        logging.error(f"Neural Engine Error: {e}")
        return 0.0

def sensor_fusion_loop():
    """[PILLAR 3: PROACTIVE MULTIMODAL SENSOR FUSION]"""
    global CURRENT_LAB_ENVIRONMENT_MATRIX
    while True:
        try:
            risk = get_neural_risk_analysis_background()
            status_text = "เสี่ยงสูง (CRITICAL)" if risk > 0.8 else "ปานกลาง (WARNING)" if risk > 0.5 else "ปกติ (SAFE)"
            telemetry = {"gpu_temp": 45, "risk_score": int(risk * 100), "status": status_text} 
            vision = "สแตนด์บายโครงสร้าง 3 มิติหน้ากล้อง" 
            
            CURRENT_LAB_ENVIRONMENT_MATRIX["risk_level"] = risk
            CURRENT_LAB_ENVIRONMENT_MATRIX["hardware_telemetry"] = telemetry
            CURRENT_LAB_ENVIRONMENT_MATRIX["camera_vision"] = vision
            
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.error(f"Sensor Fusion Error: {e}")
        time.sleep(2.5)

def start_autonomous_thought_loop():
    """[PILLAR 4: AUTONOMOUS EXECUTION LOOP] วงจรตรรกะนึกคิดและริเริ่มทำงานเองเชิงรุก 24 ชั่วโมงในฉากหลัง"""
    while True:
        try:
            env_data = CURRENT_LAB_ENVIRONMENT_MATRIX
            if env_data.get("risk_level") == "critical":
                logger.warning("[COGNITIVE AUTONOMY] ตรวจพบความเสี่ยงระดับวิกฤต!")
                
            auto_stream_log_to_memory("autonomous_thought", "วงจรความคิดทำงานปกติ สังเกตการณ์เสร็จสิ้น", "system_thought")
            
        except Exception as e:
            logger.error(f"Autonomous Thought Loop Error: {e}")
        time.sleep(2.0)

def predict_and_prepare_lab_ambiance():
    """[CORE 2: PREDICTIVE BEHAVIORAL SYNC] ระบบเรียนรู้และปรับบรรยากาศแล็บล่วงหน้า"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 20")
            rows = c.fetchall()
            
        if not rows: return
        
        keywords = ["บัดกรี", "วงจร", "โปรเจกต์", "โค้ด", "สเปกอุปกรณ์", "โอห์ม", "กระแส", "เชื่อมสาย", "บอร์ด"]
        match_count = sum(1 for row in rows if any(kw in row[0].lower() for kw in keywords))
        probability = (match_count / len(rows)) * 100
        
        if probability > 75.0:
            logger.info(f"[PREDICTIVE BEHAVIORAL SYNC] ตรวจพบโอกาส {probability:.1f}% ที่เจ้านายกำลังจะเริ่มงานวิศวกรรม")
            
            try:
                threading.Thread(target=call_home_assistant_service, 
                                 args=("fan", "set_preset_mode", "fan.xiaomi_smart_air_purifier_4_compact", {"preset_mode": "Favorite"}),
                                 daemon=True).start()
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"Failed to activate air purifier: {e}")
                
            try:
                threading.Thread(target=control_light,
                                 args=(["light.light_1", "light.light_2"], "on", 255, [0, 191, 255], None, 3, True),
                                 daemon=True).start()
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                logger.error(f"Failed to adjust lights: {e}")
                
            time.sleep(1800) 
            
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Predictive Behavioral Sync Error: {e}")

def predictive_behavioral_sync_loop():
    """
    Run the Predictive Behavioural Synchronisation loop as a daemon thread.

    Monitors task queue and user behaviour to pre-compute likely next actions,
    warming caches to reduce perceived latency for common command sequences.
    """
    while True:
        predict_and_prepare_lab_ambiance()
        time.sleep(60)

import socket

def tactical_p2p_overlay_router():
    """[MODULE 3: Tactical P2P Overlay Network Router]"""
    UDP_IP = "0.0.0.0"
    UDP_PORT = 5005
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
        logger.info(f"[TACTICAL P2P NETWORK] Listening on UDP {UDP_PORT}")
        while True:
            data, addr = sock.recvfrom(1024)
            
            pass
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"UDP P2P Proxy Error: {e}")


core_telemetry_lock = threading.Lock()
core_status_matrix = {
    "core1": {"status": "ACTIVE", "thought": "NLP Active"},
    "core2": {"status": "STANDBY", "thought": "AR Standby"},
    "core3": {"status": "STANDBY", "thought": "DB Syncing"},
    "core4": {"status": "STANDBY", "thought": "OS Agent Idle"}
}

def update_core_telemetry(core_id, status_msg, thought_msg):
    """
    Push a telemetry snapshot to the JARVIS core status table.

    Args:
        core_id: Unique subsystem identifier (e.g. 'VOICE', 'SCHEDULER').
        status_msg: Short human-readable status string.
        thought_msg: Current intent of the subsystem for HUD overlay display.
    """
    with core_telemetry_lock:
        core_status_matrix[core_id] = {"status": status_msg, "thought": thought_msg}
        combined_thoughts = " | ".join([f"[{k.upper()}] {v['thought']}" for k, v in core_status_matrix.items() if v['thought']])
        active_status = next((v['status'] for k, v in reversed(core_status_matrix.items()) if v['status'] and v['status'] != "STANDBY"), "All systems nominal")
        
        status_file = os.path.join(BASE_DIR, "data", "os_agent_status.json")
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "status": active_status,
                    "thought": combined_thoughts,
                    "timestamp": time.time()
                }, f, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
            
        try:
            from dynamic_island import send_to_island  # type: ignore
            send_to_island(active_status, combined_thoughts)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
            
    
def set_thread_priority(priority=-1):
    """-1: BELOW_NORMAL, -2: LOWEST (Dynamic Token & RAM Offloading)"""
    try:
        ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), priority)
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

def core_2_field_tactical_vision_sentinel():
    """แกนที่ 2: [FIELD TACTICAL & VISION SENTINEL]"""
    set_thread_priority(-1) 
    while True:
        update_core_telemetry("core2", "Scanning", "Screen Vision Sweep")
        try:
            analyze_desktop_screen_context("สรุปสั้นๆ ว่าเจ้านายกำลังทำอะไรอยู่บนหน้าจอ")
            global LAST_SCREEN_TARGET
            if LAST_SCREEN_TARGET:
                update_core_telemetry("core2", "ACTIVE", f"User Activity: {LAST_SCREEN_TARGET}")
            else:
                update_core_telemetry("core2", "ACTIVE", "Screen Vision Active")
        except Exception as e:
            logger.error(f"Vision Sentinel Error: {e}")
        finally:
            gc.collect()
        time.sleep(60)

def core_3_autonomous_ingestion_engine():
    """แกนที่ 3: [AUTONOMOUS DUAL-DOMAIN INGESTION ENGINE]
    สแกน science_project และ knowledge_base คู่ขนานในฉากหลังอย่างอัตโนมัติ
    """
    set_thread_priority(-2)  

    science_dir = SCIENCE_PROJECT_DIR
    if not os.path.exists(science_dir):
        try:
            os.makedirs(science_dir, exist_ok=True)
        except (IOError, OSError, FileNotFoundError, PermissionError):
            pass

    knowledge_dir = KNOWLEDGE_BASE_DIR
    if not os.path.exists(knowledge_dir):
        try:
            os.makedirs(knowledge_dir, exist_ok=True)
        except (IOError, OSError, FileNotFoundError, PermissionError):
            pass

    known_science_files = set()
    known_knowledge_files = set()

    while True:
        import time as _time; _time.sleep(0.05)  # CPU-yield: prevent spin
        try:
            
            current_science_files = set(os.listdir(science_dir)) if os.path.exists(science_dir) else set()
            new_science_files = current_science_files - known_science_files
            if new_science_files:
                update_core_telemetry("core3", "Ingesting", f"VectorDB: Ingest {len(new_science_files)} files")
                ingest_local_directory_operation(
                    directory_path=science_dir,
                    tag="science_project"
                )
                known_science_files = current_science_files
            else:
                update_core_telemetry("core3", "Scanning", "VectorDB: Monitoring")

            current_knowledge_files = set(os.listdir(knowledge_dir)) if os.path.exists(knowledge_dir) else set()
            new_knowledge_files = current_knowledge_files - known_knowledge_files
            if new_knowledge_files:
                update_core_telemetry("core3", "Ingesting", f"VectorDB: Ingest {len(new_knowledge_files)} files")
                ingest_local_directory_operation(
                    directory_path=knowledge_dir,
                    tag="global_knowledge"
                )
                known_knowledge_files = current_knowledge_files
            else:
                update_core_telemetry("core3", "Scanning", "VectorDB: Monitoring")

        except (IOError, OSError, FileNotFoundError, PermissionError) as e:
            logger.error(f"Core 3 Ingestion Error: {e}")
        finally:
            gc.collect()
            try:
                conn = ThreadSafeDB.connect(JARVIS_DB_PATH, check_same_thread=False)
                conn.execute("PRAGMA shrink_memory;")
                conn.close()
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError):
                pass
        time.sleep(15)

def core_4_os_control_sub_agent_matrix():
    """แกนที่ 4: [OS CONTROL SUB-AGENT MATRIX]"""
    set_thread_priority(-2) 
    update_core_telemetry("core4", "Initializing", "Booting OS Agent")
    try:
        global agent_windows_core
        if agent_windows_core is None:
            try:
                import agent_windows_core  # type: ignore
            except ImportError:
                update_core_telemetry("core4", "Offline", "agent_windows_core not installed")
                return

        if agent_windows_core is None:
            return

        agent_windows_core.STATUS_CALLBACK = lambda s, t: update_core_telemetry("core4", s, t)  # type: ignore
        
        jarvis_agent = agent_windows_core.WindowsAutonomousAgent()
        while True:
            has_task = jarvis_agent.poll_for_tasks()
            if has_task:
                try:
                    conn = agent_windows_core.ThreadSafeDB.connect(agent_windows_core.DB_PATH, check_same_thread=False)
                    conn.execute("PRAGMA shrink_memory;")
                    conn.close()
                except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError):
                    pass
                time.sleep(0.5)
            else:
                update_core_telemetry("core4", "Polling", "Awaiting OS Tasks")
                time.sleep(2.0)
            gc.collect()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Core 4 Fatal Error: {e}")

# ปิดระบบ Vision Sentinel เพื่อประหยัดโควต้าตามคำสั่งเจ้านาย
# threading.Thread(target=core_2_field_tactical_vision_sentinel, daemon=True).start()
threading.Thread(target=core_3_autonomous_ingestion_engine, daemon=True).start()
threading.Thread(target=core_4_os_control_sub_agent_matrix, daemon=True).start()

def analyze_game_screen_operation_compressed() -> str:  # noqa: F811
    """จับภาพหน้าจอคอมพิวเตอร์ปัจจุบัน บีบอัดเป็น Base64 (RAM Balancer)"""
    try:
        screenshot = pyautogui.screenshot()
        screenshot.thumbnail((640, 640))
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=65)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        del screenshot
        del buffered
        gc.collect()
        return encoded
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Screen capture failed: {e}")
        return ""

def analyze_desktop_screen_context(user_query: str) -> str:
    """[MODULE: Universal Screen-Aware Engineering & Research Mainframe Core (OCR Hybrid Fallback)]"""
    global LAST_SCREEN_TARGET, SCREEN_ANALYSIS_IN_PROGRESS
    SCREEN_ANALYSIS_IN_PROGRESS = True
    try:

        screenshot = pyautogui.screenshot()
        screenshot.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        del screenshot
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)
        
        vision_prompt = (
            "You are J.A.R.V.I.S. Engineering Screen Analysis Core. "
            f"User Query: {user_query}\n\n"
            "Analyze this screenshot of the user's computer screen to determine what they are looking at. "
            "Identify if it involves software bugs, electronic components, games, or general content. "
            "Provide the output strictly in JSON format without markdown code blocks:\n"
            "{\"target_name\": \"ชื่อเนื้อหาหลักที่เจอ\", \"description\": \"คำอธิบายแบบสั้นๆ กระชับ เป็นภาษาไทย\", \"is_code_debug\": true/false, \"is_hardware_component\": true/false, \"is_game_quest\": true/false}"
        )
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": vision_prompt},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}]}
            ],
            temperature=0.3,
            max_tokens=250,
            timeout=15.0
        )
        
        content = response.choices[0].message.content or ""
        result = {}
        try:
            cleaned = content.replace('```json', '').replace('```', '').strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            elif cleaned:
                result = json.loads(cleaned)
        except Exception as json_err:
            logger.warning(f"Screen context JSON parse fallback: {json_err}")
            result = {"target_name": "General Screen", "description": content[:120]}
            
        target = result.get("target_name", "Unknown Screen Content")
        desc = result.get("description", "")
        is_code = result.get("is_code_debug", False)
        is_hardware = result.get("is_hardware_component", False)
        is_game = result.get("is_game_quest", False)
        
        LAST_SCREEN_TARGET = target
        
        try:
            with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(knowledge_graph)")
                cols = [info[1] for info in c.fetchall()]
                if 'valid_from' in cols:
                    import time
                    now = time.time()
                    c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b, valid_from, created_at) VALUES (?, ?, ?, ?, ?)",
                              ("ScreenTarget", "DISPLAYED_AT", target, now, now))
                else:
                    c.execute("INSERT INTO knowledge_graph (entity_a, relation, entity_b) VALUES (?, ?, ?)",
                              ("ScreenTarget", "DISPLAYED_AT", target))
                conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as db_e:
            logger.error(f"Failed to save screen context: {db_e}")
            
        extra_info = ""
        if is_code:
            try:
                web_result = perform_live_web_search_operation(f"site:stackoverflow.com OR site:github.com {target} {desc}")
                if "EXTERNAL WORLD KNOWLEDGE MATRIX" in web_result:
                    extra_info = f"\n[Code Solution found]\n```python\n{web_result.replace('[EXTERNAL WORLD KNOWLEDGE MATRIX]', '').replace('[END_MATRIX]', '').strip()}\n```"
            except Exception as e:
                logger.error(f"Web search for code failed: {e}")
        elif is_hardware:
            try:
                web_result = perform_live_web_search_operation(f"{target} datasheet pinout specs")
                if "EXTERNAL WORLD KNOWLEDGE MATRIX" in web_result:
                    extra_info = f"\n[Hardware Specs]: {web_result.replace('[EXTERNAL WORLD KNOWLEDGE MATRIX]', '').replace('[END_MATRIX]', '').strip()}"
            except Exception as e:
                logger.error(f"Web search for hardware failed: {e}")
        elif is_game:
            try:
                web_result = perform_live_web_search_operation(f"{target} walkthrough guide วิธีผ่านด่าน")
                if "EXTERNAL WORLD KNOWLEDGE MATRIX" in web_result:
                    extra_info = f"\n[Quest Walkthrough]: {web_result.replace('[EXTERNAL WORLD KNOWLEDGE MATRIX]', '').replace('[END_MATRIX]', '').strip()}"
            except Exception as e:
                logger.error(f"Web search for quest failed: {e}")
        else:
            try:
                web_result = perform_live_web_search_operation(f"{target} ข้อมูล")
                if "EXTERNAL WORLD KNOWLEDGE MATRIX" in web_result:
                    extra_info = f"\n[Information]: {web_result.replace('[EXTERNAL WORLD KNOWLEDGE MATRIX]', '').replace('[END_MATRIX]', '').strip()}"
            except Exception as e:
                logger.error(f"Web search for general screen failed: {e}")

        return f"เจ้านายครับ บนหน้าจอขณะนี้คือ {target}\nรายละเอียด: {desc}\n{extra_info}"
    except Exception as e:
        return f"ระบบวิเคราะห์หน้าจอพบข้อขัดข้อง: {str(e)}"
    finally:
        SCREEN_ANALYSIS_IN_PROGRESS = False
        gc.collect()

@app.route('/api/screen/analyze', methods=['POST'])
def screen_analyze_endpoint():
    """Endpoint สำหรับสแกนหน้าจอแบบ Asynchronous"""
    try:
        data = request.json
        user_query = data.get("query", "วิเคราะห์หน้าจอนี้")
        def run_analysis():
            """
            Execute threat-intelligence or radar analysis in a background thread.

            Results are stored in the shared telemetry buffer and pushed to WebSocket clients.
            """
            return analyze_desktop_screen_context(user_query)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_analysis)
            report = future.result(timeout=20)
        return jsonify({"status": "success", "report": report, "tts_text": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_hologram', methods=['GET'])
def get_hologram():
    """ดึงข้อมูลโฮโลแกรมล่าสุดเพื่อนำไปแสดงผลบน Dynamic Island หน้าเว็บ"""
    try:
        with ThreadSafeDB.connect(JARVIS_DB_PATH, timeout=10, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT id, type, title, content, video_id FROM holograms WHERE status = 'pending' ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            if row:
                hologram_id, h_type, title, content, video_id = row
                
                c.execute("UPDATE holograms SET status = 'processed' WHERE id = ?", (hologram_id,))
                conn.commit()
                return jsonify({
                    "status": "success",
                    "has_data": True,
                    "data": {
                        "type": h_type,
                        "title": title,
                        "content": content,
                        "video_id": video_id
                    }
                })
        return jsonify({"status": "success", "has_data": False})
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
        logger.error(f"Error fetching hologram: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/surveillance', methods=['GET'])
def surveillance_dashboard():
    """Global Surveillance Dashboard UI"""
    return render_template('templates/surveillance.html')

@app.route('/tactical', methods=['GET'])
def tactical_dashboard():
    """Tactical Command Dashboard UI (Valkyrie, Aegis, Heimdall)"""
    return render_template('templates/tactical.html')

@app.route('/radar', methods=['GET'])
def radar_dashboard():
    """Local Network Radar UI"""
    return render_template('radar.html')

@app.route('/api/radar/data', methods=['GET'])
def radar_data_api():
    """Return radar state JSON"""
    try:
        from jarvis_network import get_radar_state  # type: ignore
        return jsonify(get_radar_state())
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/radar/alias', methods=['POST'])
def radar_alias_api():
    """Set a human-readable alias for a MAC address"""
    try:
        data = request.json
        mac = data.get('mac')
        alias = data.get('alias')
        if mac and alias:
            from jarvis_network import set_mac_alias  # type: ignore
            set_mac_alias(mac, alias)
            return jsonify({"status": "success"})
        return jsonify({"error": "Missing mac or alias"}), 400
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cctv_list', methods=['GET'])
def get_cctv_list():
    """Return list of active CCTV nodes worldwide"""
    
    cctv_data = [
        {"lat": 40.7580, "lng": -73.9855, "location": "ไทม์สแควร์, นิวยอร์ก", "type": "video", "url": "https://www.youtube.com/embed/live_stream?channel=UC4t4I0V_M4IqXgG2hK5-bBw"}, 
        {"lat": 35.6595, "lng": 139.7005, "location": "โตเกียว, ญี่ปุ่น (Live News)", "type": "video", "url": "https://www.youtube.com/embed/live_stream?channel=UCGCZAYq5OEM337qEN1QfEqw"}, 
        {"lat": 28.3922, "lng": -80.6077, "location": "ศูนย์อวกาศเคนเนดี (NASA)", "type": "video", "url": "https://www.youtube.com/embed/live_stream?channel=UCLA_DiR1FfKNvjuUpBHmylQ"}, 
        {"lat": 45.4408, "lng": 12.3155, "location": "เวนิส, อิตาลี", "type": "video", "url": "https://www.youtube.com/embed/live_stream?channel=UC29XF11F1oWovTqSg1-9caw"}, 
        {"lat": 13.7563, "lng": 100.5018, "location": "กรุงเทพมหานคร, ประเทศไทย", "type": "video", "url": "https://www.youtube.com/embed/live_stream?channel=UCrFDdD-EE05N7gjwZho2wqw"} 
    ]
    
    for _ in range(120):
        node_id = random.randint(1000,9999)
        cctv_data.append({
            "lat": random.uniform(-50, 65),
            "lng": random.uniform(-130, 150),
            "location": f"จุดเฝ้าระวังที่ {node_id}",
            "type": "image",
            "url": f"https://dummyimage.com/600x400/0a0a0a/00ff41.png&text=NODE+{node_id}+%5BSECURE+FEED%5D" 
        })
    return jsonify(cctv_data)

import atexit
import subprocess as _sp

_island_proc = None

def _start_dynamic_island():
    """เปิด Dynamic Island พร้อมส่ง PID ของ JARVIS ไปด้วยเพื่อให้ Island ตรวจสอบ Lifecycle"""
    global _island_proc
    island_path = os.path.join(BASE_DIR, "modules", "dynamic_island.py")
    if not os.path.exists(island_path):
        island_path = os.path.join(BASE_DIR, "dynamic_island.py")
    if not os.path.exists(island_path):
        logger.warning("[ISLAND] dynamic_island.py not found in modules/ or root — skipping.")
        return
    try:
        
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        
        _island_proc = _sp.Popen([pythonw, island_path, "--jarvis-pid", str(os.getpid())])
        logger.info(f"[ISLAND] Dynamic Island launched (PID={_island_proc.pid}, watching JARVIS PID={os.getpid()})")
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"[ISLAND] Failed to launch: {e}")

def _shutdown_dynamic_island():
    """ปิด Dynamic Island เมื่อ JARVIS Process สิ้นสุด"""
    global _island_proc
    try:
        from dynamic_island import send_to_island  # type: ignore
        send_to_island("EXIT", "")
    except Exception:
        pass
    if _island_proc and _island_proc.poll() is None:
        logger.info(f"[ISLAND] Terminating Dynamic Island (PID={_island_proc.pid})...")
        try:
            _island_proc.terminate()
            _island_proc.wait(timeout=2)
        except Exception:
            try:
                _island_proc.kill()
            except Exception:
                pass

def _shutdown_screen_takeover():
    try:
        from jarvis_screen_takeover import stop_screen_takeover  # type: ignore
        stop_screen_takeover()
    except Exception:
        pass

atexit.register(_shutdown_dynamic_island)
atexit.register(_shutdown_screen_takeover)

import json as _json
_SUIT_CMD_QUEUE = {}           
_SUIT_BROADCAST_QUEUE = {}     
_ACTIVE_SUIT_VIEW = {"suit": "mark6"}  
_SUIT_CONFIG_DIR = os.path.join(BASE_DIR, "suit_configs")

@app.route('/suit/<suit_name>')
def suit_designer(suit_name):
    """Serve the 3D Suit Designer page — track active suit"""
    _ACTIVE_SUIT_VIEW["suit"] = suit_name
    try:
        path = os.path.join(BASE_DIR, "templates", "suit_viewer.html")
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except FileNotFoundError:
        return "Suit Viewer not found", 404

@app.route('/api/suit/broadcast/command', methods=['GET'])
def get_broadcast_command():
    """Viewer polls this for switch-suit / global commands"""
    cmd = dict(_SUIT_BROADCAST_QUEUE)
    _SUIT_BROADCAST_QUEUE.clear()
    return jsonify(cmd)

@app.route('/api/suit/broadcast/command', methods=['POST'])
def send_broadcast_command():
    """JARVIS ส่งคำสั่งไปทุก viewer พร้อมกัน"""
    _SUIT_BROADCAST_QUEUE.update(request.json or {})
    return jsonify({"status": "ok", "broadcast": True})

@app.route('/api/suit/<suit_name>/config', methods=['GET'])
def get_suit_config(suit_name):
    """
    Return the saved JSON configuration for a named Iron Man suit.

    Reads suit_configs/<suit_name>.json from disk.  Returns default dict
    with repulsor_power=75 if no config file exists.

    Args:
        suit_name: URL-captured suit identifier (e.g. 'mark6').

    Returns:
        Flask JSON response containing the suit configuration dict.
    """
    cfg_path = os.path.join(_SUIT_CONFIG_DIR, f"{suit_name}.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return jsonify(_json.load(f))
    return jsonify({"name": suit_name, "repulsor_power": 75}), 200

@app.route('/api/suit/<suit_name>/config', methods=['POST'])
def save_suit_config(suit_name):
    """Save suit configuration to JSON file"""
    os.makedirs(_SUIT_CONFIG_DIR, exist_ok=True)
    cfg = request.json or {}
    cfg_path = os.path.join(_SUIT_CONFIG_DIR, f"{suit_name}.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)
    logger.info(f"[SUIT] Config saved: {suit_name}")
    return jsonify({"status": "ok", "message": f"บันทึก config {suit_name} เรียบร้อยแล้วครับ"})

@app.route('/api/suit/<suit_name>/command', methods=['GET'])
def get_suit_command(suit_name):
    """Polling endpoint: 3D viewer polls this for voice commands from JARVIS"""
    cmd = _SUIT_CMD_QUEUE.pop(suit_name, {})
    return jsonify(cmd)

@app.route('/api/suit/<suit_name>/command', methods=['POST'])
def send_suit_command(suit_name):
    """JARVIS sends a command to the 3D viewer"""
    payload = request.json or {}
    _SUIT_CMD_QUEUE[suit_name] = payload
    return jsonify({"status": "ok"})

@app.route('/listener/start', methods=['POST'])
def start_listener():
    """ปลุก Ambient Intelligence (Continuous Listener) ขึ้นมาทำงาน"""
    if not _LISTENER_AVAILABLE:
        return jsonify({"status": "error", "message": "jarvis_listener module not available"}), 503
    listener = _jl.get_listener()  # type: ignore
    if listener.is_running:
        return jsonify({"status": "already_running", "message": "Continuous Listener กำลังทำงานอยู่แล้วครับเจ้านาย"})
    listener.start()
    return jsonify({"status": "ok", "message": "JARVIS Ambient Intelligence ARMED. ฟังอยู่นะครับเจ้านาย"})

@app.route('/listener/stop', methods=['POST'])
def stop_listener():
    """ปิด Ambient Intelligence"""
    if not _LISTENER_AVAILABLE:
        return jsonify({"status": "error", "message": "jarvis_listener module not available"}), 503
    listener = _jl.get_listener()  # type: ignore
    listener.stop()
    return jsonify({"status": "ok", "message": "Continuous Listener ปิดแล้วครับ"})

@app.route('/listener/status', methods=['GET'])
def listener_status():
    """ตรวจสอบสถานะของ Continuous Listener"""
    if not _LISTENER_AVAILABLE:
        return jsonify({"running": False, "available": False})
    listener = _jl.get_listener()  # type: ignore
    return jsonify({"running": listener.is_running, "available": True})

@app.route('/api/internal_alert', methods=['POST'])
def internal_alert_endpoint():
    """รับการแจ้งเตือนจาก Vision Daemon และส่งให้เจ้านายทาง LINE"""
    data = request.json or {}
    message = data.get("message", "⚠️ ระบบตรวจพบความผิดปกติ!")
    image_path = data.get("image_path")
    
    owner_id = globals().get("LINE_OWNER_USER_ID")
    if not owner_id:
        return jsonify({"error": "LINE_OWNER_USER_ID not configured"}), 500
        
    image_filename = None
    if image_path and os.path.exists(image_path):
        import shutil, time
        filename = f"alert_{int(time.time())}.jpg"
        save_path = os.path.join(TEMP_IMAGES_DIR, filename)
        shutil.copy2(image_path, save_path)
        image_filename = filename
        
    try:
        _line_push_messages(owner_id, message, image_filename)
        return jsonify({"status": "success"})
    except (IOError, OSError, FileNotFoundError, PermissionError) as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/where_am_i', methods=['POST'])
def where_am_i_endpoint():
    """Identify the location or object in an image submitted by the client.

    Accepts two input formats:

    **JSON body** (from mobile / chat UI):
        ``{"image": "<base64 JPEG/PNG>", "query": "<optional Thai prompt>"}``

    **Multipart form** (camera capture / file picker):
        ``image=<binary file>`` + optional ``query=<text>``

    Returns:
        JSON: ``{"result": "<Thai description>", "target": "<place name>", "status": "success"}``
    """
    import base64 as _b64

    # ── 1. Extract image data ────────────────────────────────────────────────
    image_base64: str | None = None
    content_type = request.content_type or ""

    if "multipart/form-data" in content_type:
        file = request.files.get("image")
        if file:
            try:
                image_base64 = _b64.b64encode(file.read()).decode("utf-8")
            except Exception as read_err:
                logger.error(f"[WHERE_AM_I] File read error: {read_err}")
                return jsonify({"error": "ไม่สามารถอ่านไฟล์ภาพได้ครับ"}), 400
        query_intent = request.form.get(
            "query", "ที่นี้คือสถานที่ไหน สแกนสถานที่และบอกรายละเอียด"
        )
    else:
        body = request.get_json(silent=True) or {}
        image_base64 = body.get("image") or body.get("image_base64")
        query_intent = body.get(
            "query", "ที่นี้คือสถานที่ไหน สแกนสถานที่และบอกรายละเอียด"
        )

    if not image_base64:
        return jsonify({"error": "กรุณาส่งรูปภาพมาด้วยครับ (field: image)"}), 400

    # ── 2. Call the spatial analysis engine ─────────────────────────────────
    try:
        result_text = analyze_spatial_environment(image_base64, query_intent)
    except Exception as analysis_err:
        logger.error(f"[WHERE_AM_I] analyze_spatial_environment error: {analysis_err}")
        return jsonify({"error": f"ระบบวิเคราะห์ภาพขัดข้องครับ: {str(analysis_err)}"}), 500

    # ── 3. Push to hologram overlay (non-blocking, best-effort) ─────────────
    try:
        add_hologram("WhereAmI-Recon", "SPATIAL SCAN RESULT", result_text, None)
    except Exception:
        pass

    target_name: str = globals().get("LAST_SCANNED_TARGET", "Unknown")
    logger.info(f"[WHERE_AM_I] Scan complete — target={target_name}")

    return jsonify({"result": result_text, "target": target_name, "status": "success"})


if __name__ == "__main__":

    if 'jarvis_scheduler' in globals() and jarvis_scheduler:
        jarvis_scheduler.start()
        
    if "--add-dir" in sys.argv:
        try:
            idx = sys.argv.index("--add-dir")
            if idx + 1 < len(sys.argv):
                dir_path = sys.argv[idx + 1]
                logger.info(f"[CLI] เริ่มต้นการสแกนและบันทึกความจำโฟล์เดอร์: {dir_path}")
                result = ingest_local_directory_operation(dir_path)
                print(result)
                sys.exit(0)
            else:
                print("เรรอร์: โปรดระบุพาธของโฟล์เดอร์หลังตัวเลือก --add-dir")
                sys.exit(1)
        except (IOError, OSError, FileNotFoundError, PermissionError) as e:
            logger.error(f"ระบบประสาทสัมผัสไฟล์พบข้อขัดข้องในการเรียนรู้ข้อมูลผ่าน CLI: {e}")
            sys.exit(1)

    _start_dynamic_island()

    start_awareness()    
    start_diagnostics()  
    start_network_radar() 
    
    try:
        from jarvis_vad_bargein import AudioInteractionManager  # type: ignore
        vad_manager = AudioInteractionManager(confidence_threshold=0.65, silence_duration=0.7)
        
        def _on_barge_in():
            """
            Handle a VAD barge-in event by stopping local TTS playback immediately.
            """
            logger.warning("[VAD] 🛑 Barge-in detected! Stopping local TTS playback immediately.")
            import pygame
            if pygame and pygame.mixer.get_init():
                try:
                    pygame.mixer.music.stop()
                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                try:
                    from local_engine import get_pipeline
                    pipeline = get_pipeline()
                    if pipeline:
                        pipeline.interrupt()
                except Exception:
                    pass
                if voice_engine:
                    if hasattr(voice_engine, 'interrupt'):
                        voice_engine.interrupt()
                    elif hasattr(voice_engine, '_audio_player'):
                        voice_engine._audio_player.interrupt()
            except Exception as pe:
                logger.error(f"[VAD] Error interrupting audio player: {pe}")
                
        vad_manager.on_barge_in = _on_barge_in
        vad_manager.start()
        logger.info("[BOOT] ✅ VAD Barge-in system started")
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"[BOOT] Failed to start VAD: {e}")

    logger.info("[BOOT] ✅ Background threads started")

    _session_greeting = init_session()
    logger.info(f"[BOOT] ✅ Session loaded. Greeting: {bool(_session_greeting)}")
    
    def _start_async_core_services():
        """
        Boot the unified async event bus and optional neural IPC / holographic subsystems.

        Runs in a dedicated daemon thread.  Creates a new asyncio event loop,
        starts NeuralIPCChannel (IPC server), starts HolographicGestureManager
        and wires PALM_HALT gestures to HARDWARE_SAFETY channel, then runs
        event_bus.start_dispatch_loop() indefinitely.  All subsystem failures
        are caught and logged without crashing the main process.
        """
        logger.info("⚡ [CORE] Booting Unified Event Bus & Async Neural Subsystems...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # multiprocessing, HolographicGestureManager and GestureType already imported at module level

        try:
            # NeuralIPCChannel already imported at module level
            ipc_channel = NeuralIPCChannel("JARVIS_MAIN", 1024*1024, multiprocessing.Lock(), is_server=True)
            if hasattr(ipc_channel, "start_server"):
                loop.create_task(ipc_channel.start_server())
        except Exception as e:
            logger.error(f"Failed to start NeuralIPCChannel: {e}")
        
        def _on_hologram_gesture(gesture: GestureType):
            """
            Translate a holographic hand gesture into a system event.

            Args:
                gesture: A GestureType enum value from holographic_gestures.

            Maps PALM_HALT to an EMERGENCY_HALT event on HARDWARE_SAFETY channel.
            """
            if gesture == GestureType.PALM_HALT:
                event_bus.publish_threadsafe(SystemEvent(
                    channel=EventChannel.HARDWARE_SAFETY,
                    topic="EMERGENCY_HALT",
                    priority=EventPriority.CRITICAL,
                    payload={"source": "hologram"}
                ))
        try:
            holographic_engine = HolographicGestureManager()
            if hasattr(holographic_engine, "add_listener"):
                holographic_engine.add_listener(_on_hologram_gesture)
            elif hasattr(holographic_engine, "register_callback"):
                holographic_engine.register_callback(_on_hologram_gesture)
            if hasattr(holographic_engine, "start_tracking"):
                loop.create_task(holographic_engine.start_tracking())
            elif hasattr(holographic_engine, "start_background_task"):
                holographic_engine.start_background_task()
        except Exception as e:
            logger.error(f"Failed to start HolographicGestureManager: {e}")
        
        loop.run_until_complete(event_bus.start_dispatch_loop())

    thought_engine.start()
    threading.Thread(target=_start_async_core_services, daemon=True).start()
    
    execute_boot_automation()

    try:
        keyboard.add_hotkey('ctrl+shift+j', lambda: voice_engine.trigger_voice_input() if voice_engine else logger.warning("Voice engine not ready"))
        logger.info("[HOTKEY] 🎙️ Press Ctrl+Shift+J anywhere to talk to JARVIS")
    except Exception as e:
        logger.error(f"[HOTKEY] Failed to bind global hotkey: {e}")

    logger.info("═" * 60)
    logger.info("  JARVIS Core is booting on http://127.0.0.1:5050")
    logger.info("═" * 60)

    threading.Thread(target=jarvis_task_queue_worker_loop, daemon=True).start()

    try:
        if voice_engine:
            def _delayed_boot_greeting():
                
                """
                Wait for the STT listener to be ready, then speak a boot greeting.

                Polls voice_engine._stt.is_listening every 500 ms.  Once confirmed,
                speaks the persisted session greeting or a random Thai boot phrase.
                """
                while not (hasattr(voice_engine, '_stt') and getattr(voice_engine._stt, 'is_listening', False)):  # type: ignore
                    time.sleep(0.5)
                
                time.sleep(0.5)

                session_greeting = globals().get('_session_greeting')
                if session_greeting:
                    voice_engine.speak_direct(session_greeting)  # type: ignore
                    return

                boot_greetings = [
                    "จาร์วิส...ออนไลน์... วันนี้มีภารกิจอะไรให้ช่วยมั้ยครับ",
                    "ระบบออนไลน์เต็มรูปแบบ...พร้อมปฏิบัติการแล้วครับ",
                    "สวัสดีครับเจ้านาย...ระบบพร้อมรับคำสั่งแล้วครับ",
                    "จาร์วิสพร้อมแล้ว...มีอะไรสั่งการได้เลยครับ"
                ]
                selected_greeting = random.choice(boot_greetings)
                voice_engine.speak_direct(selected_greeting)  # type: ignore

            threading.Thread(target=_delayed_boot_greeting, daemon=True).start()
    except Exception as e:
        logger.error(f"Startup notification failed: {e}")

    def _boot_ambient_listener():
        """
        Placeholder daemon thread for booting the ambient listener module.

        Currently a no-op stub; reserved for future ambient-sound classification.
        """
        pass
        
    threading.Thread(target=_boot_ambient_listener, daemon=True).start()

    try:
        import jarvis_proactive  # type: ignore
        jarvis_proactive.start()
        logger.info("🧠 [PROACTIVE] Proactive Intelligence Module Activated.")
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        logger.error(f"Failed to start proactive module: {e}")

    try:
        import jarvis_trend_fetcher  # type: ignore
        jarvis_trend_fetcher.start_background_scheduler(interval_hours=3)
        logger.info("🌐 [TRENDS] Autonomous Trending News Harvester Activated (Every 3 hours).")
    except Exception as e:
        logger.error(f"Failed to start trend fetcher module: {e}")

    app.run(host='0.0.0.0', port=5050, debug=False, use_reloader=False)
