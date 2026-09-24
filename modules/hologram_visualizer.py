"""
hologram_visualizer.py
Module 2: 3D Wireframe & Dynamic Chart Engine

Responsible for rendering and managing mathematical structures of 3D objects
and charts, rendering them into a 'Hologram-style' wireframe mesh format.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

# Setup Module Logger
logger = logging.getLogger("HologramVisualizer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class VisualizerException(Exception):
    """Base exception for the Hologram Visualizer module."""
    pass


@dataclass
class Vertex3D:
    x: float
    y: float
    z: float


@dataclass
class Edge:
    v1_index: int
    v2_index: int


@dataclass
class HologramMesh:
    """Mathematical representation of a 3D Wireframe."""
    name: str
    vertices: List[Vertex3D] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    color_hex: str = "#00FFFF"  # Default Cyan/Hologram Blue
    is_visible: bool = True
    scale: float = 1.0


class WireframeRenderer:
    """
    Renders and manipulates 3D mesh data. In a full graphics pipeline, 
    this would pass OpenGL buffer data. Here we manage the mathematical state.
    """
    
    def __init__(self):
        self._meshes: Dict[str, HologramMesh] = {}

    def load_mesh(self, mesh: HologramMesh):
        self._meshes[mesh.name] = mesh
        logger.info(f"Loaded Mesh: {mesh.name} ({len(mesh.vertices)} vertices, {len(mesh.edges)} edges)")

    def set_visibility(self, mesh_name: str, visible: bool):
        if mesh_name in self._meshes:
            self._meshes[mesh_name].is_visible = visible
            state = "VISIBLE" if visible else "HIDDEN"
            logger.info(f"Mesh '{mesh_name}' is now {state}.")

    def apply_scale(self, mesh_name: str, factor: float):
        if mesh_name in self._meshes:
            mesh = self._meshes[mesh_name]
            mesh.scale *= factor
            # Mathematical scaling of vertices
            for v in mesh.vertices:
                v.x *= factor
                v.y *= factor
                v.z *= factor
            logger.info(f"Scaled Mesh '{mesh_name}' by factor {factor:.2f}")

    def render_frame(self) -> Dict[str, Any]:
        """
        Calculates the current frame data. 
        Returns a dictionary that a frontend (Tkinter/PyQt) can draw.
        """
        frame_data = {"rendered_lines": 0, "active_meshes": []}
        
        for name, mesh in self._meshes.items():
            if mesh.is_visible:
                frame_data["active_meshes"].append(name)
                frame_data["rendered_lines"] += len(mesh.edges)
                
        return frame_data


class DynamicChartAnimator:
    """
    Manages interactive 3D charts that can split, merge, or animate.
    """
    
    def __init__(self, renderer: WireframeRenderer):
        self.renderer = renderer
        self.chart_components: List[str] = []

    def build_bar_chart(self, data: List[float], chart_name: str):
        """Constructs a basic 3D bar chart wireframe."""
        logger.info(f"Building Dynamic Chart: {chart_name} with {len(data)} columns.")
        
        vertices = []
        edges = []
        offset_x = 0.0
        
        for idx, value in enumerate(data):
            # Base of the bar (4 vertices)
            base_idx = len(vertices)
            vertices.extend([
                Vertex3D(offset_x, 0, 0), Vertex3D(offset_x + 1, 0, 0),
                Vertex3D(offset_x + 1, 0, 1), Vertex3D(offset_x, 0, 1)
            ])
            # Top of the bar (4 vertices)
            vertices.extend([
                Vertex3D(offset_x, value, 0), Vertex3D(offset_x + 1, value, 0),
                Vertex3D(offset_x + 1, value, 1), Vertex3D(offset_x, value, 1)
            ])
            
            # Simple edges for the box (12 edges)
            for i in range(4):
                edges.append(Edge(base_idx + i, base_idx + (i + 1) % 4))          # Base square
                edges.append(Edge(base_idx + 4 + i, base_idx + 4 + ((i + 1) % 4)))# Top square
                edges.append(Edge(base_idx + i, base_idx + i + 4))                # Vertical lines
                
            offset_x += 2.0  # Gap between bars
            
        mesh = HologramMesh(name=chart_name, vertices=vertices, edges=edges, color_hex="#00FF88")
        self.renderer.load_mesh(mesh)
        self.chart_components.append(chart_name)

    async def animate_split(self, chart_name: str):
        """Animates pulling the chart apart or highlighting it."""
        logger.warning(f"ANIMATION TRIGGERED: Splitting components of '{chart_name}'")
        # Simulate animation frames
        for i in range(3):
            self.renderer.apply_scale(chart_name, 1.1)
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing 3D Wireframe & Dynamic Chart Engine ---")
        
        renderer = WireframeRenderer()
        animator = DynamicChartAnimator(renderer)
        
        # 1. Build a mock 3D Chart
        mock_data = [10.5, 20.0, 5.0, 15.2]
        animator.build_bar_chart(mock_data, "ServerLoadChart")
        
        # 2. Render initial frame
        frame_1 = renderer.render_frame()
        logger.info(f"Frame 1 Render Data: {frame_1}")
        
        # 3. Animate a split/explosion effect
        await animator.animate_split("ServerLoadChart")
        
        # 4. Hide chart
        renderer.set_visibility("ServerLoadChart", False)
        frame_2 = renderer.render_frame()
        logger.info(f"Frame 2 Render Data (Hidden): {frame_2}")

    asyncio.run(run_tests())
