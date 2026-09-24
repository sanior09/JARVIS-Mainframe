from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

# =============================================================================
# [1] PREDICTIVE HOLOGRAM / 3D SPATIAL RENDERING MODELS
# =============================================================================

class VertexData(BaseModel):
    """Represents a single 3D vertex in spatial space."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")
    color: Optional[Tuple[int, int, int]] = Field(None, description="RGB color tuple")
    normal: Optional[Tuple[float, float, float]] = Field(None, description="Vertex normal vector")

class Mesh3D(BaseModel):
    """Represents a full 3D mesh object (PCB, Structural Data, etc.)."""
    id: str = Field(..., description="Unique identifier for the mesh")
    vertices: List[VertexData] = Field(default_factory=list, description="List of vertices")
    faces: List[Tuple[int, int, int]] = Field(default_factory=list, description="List of triangular faces")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context (e.g., thermal bounds)")

class ThermalOverlay(BaseModel):
    """Represents thermal telemetry to be overlaid onto the 3D mesh."""
    mesh_id: str = Field(..., description="ID of the target mesh")
    temperature_gradient: Dict[int, float] = Field(
        ..., description="Mapping of vertex index to temperature (Celsius)"
    )


# =============================================================================
# [2] PROACTIVE THREAT & SAFETY GOVERNOR MODELS
# =============================================================================

class HardwareTelemetry(BaseModel):
    """Real-time data snapshot from the embedded systems/hardware."""
    timestamp: float = Field(..., description="Unix timestamp of telemetry")
    voltage: float = Field(..., description="Current voltage (V)")
    current: float = Field(..., description="Current draw (A)")
    temperature_celsius: float = Field(..., description="Core/Ambient temperature")
    active_circuits: int = Field(..., description="Number of active sub-circuits")
    
    @property
    def power_draw(self) -> float:
        """Calculates current power draw in Watts."""
        return self.voltage * self.current


# =============================================================================
# [3] AUTONOMOUS CODE SELF-HEALING ENGINE MODELS
# =============================================================================

class FaultContext(BaseModel):
    """Captures the context of a runtime crash or anomaly."""
    exception_type: str = Field(..., description="The type of exception raised")
    error_message: str = Field(..., description="The raw error message")
    traceback_lines: List[str] = Field(default_factory=list, description="Full traceback string lines")
    failing_file: str = Field(..., description="File where the crash originated")
    failing_line_number: int = Field(..., description="Line number of the crash")
    local_vars_snapshot: Dict[str, str] = Field(default_factory=dict, description="Stringified local vars at crash")

class SynthesizedPatch(BaseModel):
    """Represents a generated code patch ready for sandbox testing."""
    patch_id: str = Field(..., description="UUID of the patch")
    target_file: str = Field(..., description="File to be patched")
    original_code_snippet: str = Field(..., description="The failing AST node/code block")
    proposed_code_snippet: str = Field(..., description="The synthesized AST node/code block")
    confidence_score: float = Field(..., description="Confidence from the synthesis engine (0.0 to 1.0)")
