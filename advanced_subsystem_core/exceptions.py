class JarvisAdvancedCoreException(Exception):
    """Base exception for J.A.R.V.I.S. Advanced Subsystem Core."""
    pass

# [1] PREDICTIVE HOLOGRAM ENGINE EXCEPTIONS
class RenderEngineInitializationError(JarvisAdvancedCoreException):
    """Raised when the 3D rendering engine fails to initialize."""
    pass

class MeshProcessingError(JarvisAdvancedCoreException):
    """Raised when processing 3D mesh or spatial data fails."""
    pass

class UnsupportedExportStrategyError(JarvisAdvancedCoreException):
    """Raised when an unsupported export strategy is requested."""
    pass


# [2] PROACTIVE THREAT & SAFETY GOVERNOR EXCEPTIONS
class SafetyGovernorViolationError(JarvisAdvancedCoreException):
    """Base exception for safety rule violations."""
    pass

class ElectricalOverloadError(SafetyGovernorViolationError):
    """Raised when current or voltage exceeds maximum safety limits."""
    pass

class ThermalCriticalError(SafetyGovernorViolationError):
    """Raised when thermal telemetry indicates a severe overheating risk."""
    pass

class ShortCircuitAnomalyError(SafetyGovernorViolationError):
    """Raised when telemetry signatures match a short-circuit profile."""
    pass

class EmergencyBreakerTriggered(JarvisAdvancedCoreException):
    """Raised when the emergency circuit breaker halts the execution context."""
    pass


# [3] AUTONOMOUS CODE SELF-HEALING ENGINE EXCEPTIONS
class SelfHealingFailureError(JarvisAdvancedCoreException):
    """Raised when the self-healing engine cannot synthesize a valid patch."""
    pass

class ASTParsingError(SelfHealingFailureError):
    """Raised when the abstract syntax tree cannot be parsed from the traceback."""
    pass

class SandboxExecutionError(SelfHealingFailureError):
    """Raised when a synthesized patch fails inside the isolated sandbox."""
    pass
