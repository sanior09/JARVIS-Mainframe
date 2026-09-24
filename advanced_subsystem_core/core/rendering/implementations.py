import logging
from typing import Optional
from ...domain.models import Mesh3D, ThermalOverlay, VertexData
from ...domain.interfaces import RendererInterface, ExportStrategyInterface
from ...exceptions import RenderEngineInitializationError, MeshProcessingError

logger = logging.getLogger(__name__)

class Open3DRenderer(RendererInterface):
    """Implementation of the RendererInterface using Open3D backend."""
    
    def __init__(self):
        self._engine_ready = False
        self._export_strategy: Optional[ExportStrategyInterface] = None
        self._o3d = None
        
    def initialize_engine(self) -> None:
        try:
            import open3d as o3d
            self._o3d = o3d
            self._engine_ready = True
            logger.info("[Open3DRenderer] Engine initialized successfully.")
        except ImportError:
            self._engine_ready = False
            raise RenderEngineInitializationError("open3d library is not installed.")
            
    def set_export_strategy(self, strategy: ExportStrategyInterface) -> None:
        self._export_strategy = strategy
        
    def load_mesh(self, filepath: str) -> Mesh3D:
        if not self._engine_ready or not self._o3d:
            self.initialize_engine()
            
        try:
            mesh = self._o3d.io.read_triangle_mesh(filepath)
            if not mesh.has_vertices():
                raise MeshProcessingError(f"Mesh at {filepath} has no vertices.")
            
            # Map o3d mesh to domain model
            domain_vertices = []
            import numpy as np
            vertices_np = np.asarray(mesh.vertices)
            
            for idx, v in enumerate(vertices_np):
                domain_vertices.append(VertexData(x=v[0], y=v[1], z=v[2]))
                
            domain_faces = []
            if mesh.has_triangles():
                triangles_np = np.asarray(mesh.triangles)
                for t in triangles_np:
                    domain_faces.append((int(t[0]), int(t[1]), int(t[2])))
                    
            return Mesh3D(
                id=filepath.split('/')[-1].split('.')[0],
                vertices=domain_vertices,
                faces=domain_faces
            )
        except Exception as e:
            raise MeshProcessingError(f"Failed to load mesh {filepath}: {e}")
            
    def apply_thermal_overlay(self, mesh: Mesh3D, thermal: ThermalOverlay) -> Mesh3D:
        """Applies a heat map (red-blue) to vertices based on thermal data."""
        if mesh.id != thermal.mesh_id:
            logger.warning("[Open3DRenderer] Thermal data ID does not match Mesh ID.")
            return mesh
            
        for v_idx, temp in thermal.temperature_gradient.items():
            if v_idx < len(mesh.vertices):
                # Simple red shift for higher temps, blue for lower
                normalized = min(max((temp - 20) / 80.0, 0.0), 1.0) 
                red = int(normalized * 255)
                blue = int((1.0 - normalized) * 255)
                mesh.vertices[v_idx].color = (red, 0, blue)
                
        return mesh

    def export(self, mesh: Mesh3D, filepath: str) -> bool:
        if not self._export_strategy:
            logger.warning("[Open3DRenderer] No export strategy set. Using default WebGL.")
            from .strategies import WebGLJSONExportStrategy
            self._export_strategy = WebGLJSONExportStrategy()
            
        return self._export_strategy.export(mesh, filepath)
