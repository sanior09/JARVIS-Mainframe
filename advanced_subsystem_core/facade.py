import logging
import asyncio
from typing import Optional, Callable, Awaitable
from .domain.models import HardwareTelemetry, Mesh3D
from .core.rendering.factory import RendererFactory
from .core.rendering.strategies import WebGLJSONExportStrategy
from .core.safety.governor import SafetyGovernor
from .core.healing.sandbox import IsolatedSandbox
from .core.healing.synthesizer import TracebackASTAnalyzer
from .core.healing.interceptor import SelfHealingInterceptor

logger = logging.getLogger(__name__)

class JarvisAdvancedSubsystemFacade:
    """
    Unified Entry Point for all Advanced Subsystems (Facade Pattern).
    Encapsulates the complexity of initialization and lifecycle management.
    """
    def __init__(self):
        # 1. Initialize Rendering Engine
        self.renderer = RendererFactory.get_renderer("open3d")
        self.renderer.set_export_strategy(WebGLJSONExportStrategy())
        
        # 2. Initialize Safety Governor
        self.governor = SafetyGovernor()
        
        # 3. Initialize Self-Healing Engine
        self.sandbox = IsolatedSandbox()
        self.synthesizer = TracebackASTAnalyzer()
        self.healer = SelfHealingInterceptor(self.sandbox, self.synthesizer)
        
    def start_safety_monitoring(self, telemetry_provider: Callable[[], Awaitable[HardwareTelemetry]]):
        """Starts the proactive threat safety governor."""
        self.governor.set_telemetry_provider(telemetry_provider)
        # This returns a coroutine that the caller must run/schedule in their asyncio loop
        return self.governor.start_monitoring(interval_seconds=2.0)
        
    def stop_safety_monitoring(self):
        self.governor.stop_monitoring()
        
    def get_healing_context(self):
        """Returns the context manager/decorator for protecting blocks of code."""
        return self.healer

    def render_and_export_mesh(self, input_filepath: str, output_filepath: str) -> bool:
        """Loads, potentially modifies, and exports a 3D mesh."""
        try:
            # Under the hood, this uses the factory and strategy pattern
            mesh: Mesh3D = self.renderer.load_mesh(input_filepath)
            # (Thermal application would go here in a real flow)
            return self.renderer.export(mesh, output_filepath)
        except Exception as e:
            logger.error(f"[Facade] Rendering failed: {e}")
            return False
