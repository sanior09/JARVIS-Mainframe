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

from jarvis_core.automation_agent import WindowsAutomationAgent, get_computer_agent
from jarvis_core.tool_dispatcher import execute_tool_call, format_tool_response, guardrail_validation
from jarvis_core.web_app import create_app
from jarvis_core.boot import perform_system_boot_sequence, start_background_daemons, execute_boot_automation
from jarvis_core.state import update_core_telemetry, get_telemetry_snapshot

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
    "WindowsAutomationAgent",
    "get_computer_agent",
    "execute_tool_call",
    "format_tool_response",
    "guardrail_validation",
    "create_app",
    "perform_system_boot_sequence",
    "start_background_daemons",
    "execute_boot_automation",
    "update_core_telemetry",
    "get_telemetry_snapshot",
]


