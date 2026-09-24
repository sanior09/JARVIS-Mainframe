from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .models import Mesh3D, ThermalOverlay, HardwareTelemetry, SynthesizedPatch, FaultContext

# =============================================================================
# [1] PREDICTIVE HOLOGRAM / 3D SPATIAL RENDERING INTERFACES
# =============================================================================

class ExportStrategyInterface(ABC):
    """Abstract Strategy for exporting 3D Mesh data to different formats."""
    @abstractmethod
    def export(self, mesh: Mesh3D, filepath: str) -> bool:
        """Exports the mesh to a specific format."""
        pass

class RendererInterface(ABC):
    """Abstract Base Class for 3D Rendering Engines (Open3D, Trimesh, etc.)."""
    @abstractmethod
    def initialize_engine(self) -> None:
        """Sets up the rendering engine environment."""
        pass
        
    @abstractmethod
    def load_mesh(self, filepath: str) -> Mesh3D:
        """Loads a 3D model into standard domain models."""
        pass
        
    @abstractmethod
    def apply_thermal_overlay(self, mesh: Mesh3D, thermal: ThermalOverlay) -> Mesh3D:
        """Projects thermal telemetry onto the vertices of the mesh."""
        pass

    @abstractmethod
    def set_export_strategy(self, strategy: ExportStrategyInterface) -> None:
        """Injects the export strategy dynamically."""
        pass


# =============================================================================
# [2] PROACTIVE THREAT & SAFETY GOVERNOR INTERFACES
# =============================================================================

class SafetyStateInterface(ABC):
    """State Machine Interface for system safety states."""
    @abstractmethod
    def handle_telemetry(self, telemetry: HardwareTelemetry) -> 'SafetyStateInterface':
        """Processes telemetry and transitions to the next state if necessary."""
        pass

class CheckHandlerInterface(ABC):
    """Chain of Responsibility node interface for safety checks."""
    def __init__(self, next_handler: Optional['CheckHandlerInterface'] = None):
        self._next = next_handler

    def set_next(self, handler: 'CheckHandlerInterface') -> 'CheckHandlerInterface':
        self._next = handler
        return handler

    @abstractmethod
    def check(self, telemetry: HardwareTelemetry) -> bool:
        """
        Validates telemetry. Raises exception if violated.
        Returns True if passed and calls next handler.
        """
        pass


# =============================================================================
# [3] AUTONOMOUS CODE SELF-HEALING ENGINE INTERFACES
# =============================================================================

class ASTSynthesizerInterface(ABC):
    """Abstract interface for modifying and analyzing Abstract Syntax Trees."""
    @abstractmethod
    def analyze_fault(self, context: FaultContext) -> str:
        """Finds the logical flaw using AST and returns the root cause."""
        pass

    @abstractmethod
    def synthesize_patch(self, context: FaultContext) -> SynthesizedPatch:
        """Generates a fix based on the AST analysis."""
        pass

class SandboxObserverInterface(ABC):
    """Observer interface for subscribing to sandbox execution results."""
    @abstractmethod
    def on_patch_success(self, patch: SynthesizedPatch, results: Dict[str, Any]) -> None:
        pass
        
    @abstractmethod
    def on_patch_failure(self, patch: SynthesizedPatch, error: str) -> None:
        pass
