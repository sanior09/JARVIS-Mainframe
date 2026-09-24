import json
import logging
from typing import Any
from ...domain.models import Mesh3D
from ...domain.interfaces import ExportStrategyInterface
from ...exceptions import UnsupportedExportStrategyError

logger = logging.getLogger(__name__)

class WebGLJSONExportStrategy(ExportStrategyInterface):
    """Exports 3D mesh data to a JSON format compatible with Three.js (WebGL)."""
    
    def export(self, mesh: Mesh3D, filepath: str) -> bool:
        try:
            data = {
                "metadata": {
                    "version": 4.5,
                    "type": "BufferGeometry",
                    "generator": "JarvisAdvancedCore"
                },
                "id": mesh.id,
                "position": [],
                "color": [],
                "normal": [],
                "indices": []
            }
            
            for v in mesh.vertices:
                data["position"].extend([v.x, v.y, v.z])
                if v.color:
                    data["color"].extend([c / 255.0 for c in v.color])
                if v.normal:
                    data["normal"].extend([v.normal[0], v.normal[1], v.normal[2]])
                    
            for f in mesh.faces:
                data["indices"].extend([f[0], f[1], f[2]])
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            logger.info(f"[Hologram Export] Successfully exported {mesh.id} to {filepath}")
            return True
        except Exception as e:
            logger.error(f"[Hologram Export] Failed to export WebGL JSON: {e}")
            return False

class GLTFExportStrategy(ExportStrategyInterface):
    """Exports to standardized GLTF format (mock implementation for architecture demonstration)."""
    
    def export(self, mesh: Mesh3D, filepath: str) -> bool:
        if not filepath.endswith(".gltf"):
            raise UnsupportedExportStrategyError("Filepath must end with .gltf")
        logger.info(f"[Hologram Export] Mocking GLTF export for {mesh.id} to {filepath}")
        return True
