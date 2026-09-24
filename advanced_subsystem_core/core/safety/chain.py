import logging
from typing import Optional
from ...domain.models import HardwareTelemetry
from ...domain.interfaces import CheckHandlerInterface
from ...exceptions import ElectricalOverloadError, ThermalCriticalError, ShortCircuitAnomalyError

logger = logging.getLogger(__name__)

class OverloadCheckHandler(CheckHandlerInterface):
    """Checks for electrical overload."""
    def check(self, telemetry: HardwareTelemetry) -> bool:
        if telemetry.power_draw > 2500:
            logger.critical(f"[OverloadCheck] Power draw critical: {telemetry.power_draw}W")
            raise ElectricalOverloadError(f"Power draw {telemetry.power_draw}W exceeds absolute maximum.")
        if self._next:
            return self._next.check(telemetry)
        return True

class ThermalCheckHandler(CheckHandlerInterface):
    """Checks for critical thermal states."""
    def check(self, telemetry: HardwareTelemetry) -> bool:
        if telemetry.temperature_celsius > 120:
            logger.critical(f"[ThermalCheck] Temperature critical: {telemetry.temperature_celsius}C")
            raise ThermalCriticalError(f"Temperature {telemetry.temperature_celsius}C exceeds structural limits.")
        if self._next:
            return self._next.check(telemetry)
        return True

class ShortCircuitCheckHandler(CheckHandlerInterface):
    """Checks for sudden voltage drops indicating short circuits."""
    def check(self, telemetry: HardwareTelemetry) -> bool:
        # A simple heuristic: extremely high current and near zero voltage
        if telemetry.current > 100 and telemetry.voltage < 0.5:
            logger.critical("[ShortCircuitCheck] Short circuit anomaly detected!")
            raise ShortCircuitAnomalyError("Sudden voltage drop with high current draw detected.")
        if self._next:
            return self._next.check(telemetry)
        return True
