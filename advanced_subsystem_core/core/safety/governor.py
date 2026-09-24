import asyncio
import logging
from typing import Callable, Awaitable
from ...domain.models import HardwareTelemetry
from ...domain.interfaces import SafetyStateInterface
from .state import NormalState
from .chain import OverloadCheckHandler, ThermalCheckHandler, ShortCircuitCheckHandler

logger = logging.getLogger(__name__)

class SafetyGovernor:
    """Async watchdog that monitors telemetry via State Machine and Chain of Responsibility."""
    
    def __init__(self):
        self._current_state: SafetyStateInterface = NormalState()
        self._is_running: bool = False
        self._telemetry_provider: Callable[[], Awaitable[HardwareTelemetry]] = None
        
        # Build the chain of responsibility
        self._safety_chain = OverloadCheckHandler()
        self._safety_chain.set_next(ThermalCheckHandler()).set_next(ShortCircuitCheckHandler())
        
        self._lock = asyncio.Lock()
        
    def set_telemetry_provider(self, provider: Callable[[], Awaitable[HardwareTelemetry]]):
        """Inject an async function that provides the latest telemetry."""
        self._telemetry_provider = provider
        
    async def start_monitoring(self, interval_seconds: float = 1.0):
        """Starts the async monitoring loop."""
        if not self._telemetry_provider:
            raise ValueError("Telemetry provider not set.")
            
        self._is_running = True
        logger.info("[Safety Governor] Threat monitoring active.")
        
        while self._is_running:
            try:
                telemetry = await self._telemetry_provider()
                await self._process_telemetry(telemetry)
            except Exception as e:
                logger.error(f"[Safety Governor] Loop error: {e}")
                
            await asyncio.sleep(interval_seconds)
            
    def stop_monitoring(self):
        self._is_running = False
        logger.info("[Safety Governor] Threat monitoring stopped.")
        
    async def _process_telemetry(self, telemetry: HardwareTelemetry):
        """Thread/Async-safe telemetry processing."""
        async with self._lock:
            # 1. State Machine handling (Warning/Halted transitions)
            self._current_state = self._current_state.handle_telemetry(telemetry)
            
            # 2. Chain of Responsibility (Absolute failure checks)
            self._safety_chain.check(telemetry)
