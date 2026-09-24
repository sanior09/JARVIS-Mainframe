"""
modules/jarvis_agents.py
========================
Unified Multi-Agent Architecture for J.A.R.V.I.S.
Loads the canonical multi-agent implementation from jarvis_agents/jarvis_multi_agent.py
without Python package collision.
"""

import os
import importlib.util

_multi_agent_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jarvis_agents",
    "jarvis_multi_agent.py"
)

_spec = importlib.util.spec_from_file_location("_jarvis_multi_agent_core", _multi_agent_path)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    jarvis_multi_agent = _mod.jarvis_multi_agent
    route_intent = _mod.route_intent
    get_agent_config = _mod.get_agent_config
    AGENT_CONFIGURATIONS = _mod.AGENT_CONFIGURATIONS
    JarvisMultiAgentRouter = _mod.JarvisMultiAgentRouter
    create_swarm = _mod.create_swarm
    swarm_develop_project = _mod.swarm_develop_project
else:
    raise ImportError(f"Cannot load JarvisMultiAgent from {_multi_agent_path}")

__all__ = [
    "jarvis_multi_agent",
    "route_intent",
    "get_agent_config",
    "AGENT_CONFIGURATIONS",
    "JarvisMultiAgentRouter",
    "create_swarm",
    "swarm_develop_project",
]
