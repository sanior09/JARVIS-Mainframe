"""
jarvis_core -- JARVIS modular architecture package.
"""

from jarvis_core.database import JARVIS_DB_PATH, ThreadSafeDB
from jarvis_core.tool_registry import TOOLS_DEFINITION
from jarvis_core.ai_router import call_groq_model, call_gemini_fallback, call_nachapol_core
from jarvis_core.model_gateway import ModelGateway, model_gateway, dispatch_llm_request
from jarvis_core.error_handlers import safe_import, safe_db_call, log_and_default
from jarvis_core.os_service import (
    list_active_processes,
    kill_process_by_identifier,
    run_system_maintenance,
    execute_safe_powershell,
)
from jarvis_core.server_monitor import (
    get_full_server_telemetry,
    check_listening_ports,
    check_database_and_cache,
    supervise_watchdog_services,
)
from jarvis_core.research_service import (
    autonomous_deep_research,
    synthesize_technical_report,
    fetch_and_clean_url,
)

__all__ = [
    "JARVIS_DB_PATH",
    "ThreadSafeDB",
    "TOOLS_DEFINITION",
    "call_groq_model",
    "call_gemini_fallback",
    "call_nachapol_core",
    "ModelGateway",
    "model_gateway",
    "dispatch_llm_request",
    "safe_import",
    "safe_db_call",
    "log_and_default",
    "list_active_processes",
    "kill_process_by_identifier",
    "run_system_maintenance",
    "execute_safe_powershell",
    "get_full_server_telemetry",
    "check_listening_ports",
    "check_database_and_cache",
    "supervise_watchdog_services",
    "autonomous_deep_research",
    "synthesize_technical_report",
    "fetch_and_clean_url",
]


