import logging
from typing import Optional
from ...domain.models import HardwareTelemetry
from ...domain.interfaces import SafetyStateInterface
from ...exceptions import EmergencyBreakerTriggered

logger = logging.getLogger(__name__)

class NormalState(SafetyStateInterface):
    """System is operating within normal parameters."""
    
    def handle_telemetry(self, telemetry: HardwareTelemetry) -> SafetyStateInterface:
        power = telemetry.power_draw
        if power > 1500 or telemetry.temperature_celsius > 85:
            logger.warning("[Safety Governor] Transitioning to WARNING state.")
            return WarningState()
        return self

class WarningState(SafetyStateInterface):
    """System is operating near limits. Requires caution."""
    
    def handle_telemetry(self, telemetry: HardwareTelemetry) -> SafetyStateInterface:
        power = telemetry.power_draw
        
        if power > 2000 or telemetry.temperature_celsius > 105:
            logger.critical("[Safety Governor] Transitioning to HALTED state. Emergency breaker triggered!")
            return HaltedState()
            
        # Recover if metrics drop
        if power < 1000 and telemetry.temperature_celsius < 70:
            logger.info("[Safety Governor] Metrics recovered. Transitioning to NORMAL state.")
            return NormalState()
            
        return self

class HaltedState(SafetyStateInterface):
    """Emergency breaker tripped. Execution is locked until manual reset."""
    
    def handle_telemetry(self, telemetry: HardwareTelemetry) -> SafetyStateInterface:
        # In halted state, we reject further telemetry processing and block execution
        raise EmergencyBreakerTriggered("System is HALTED due to critical safety breach.")
