from ...domain.interfaces import RendererInterface
from .implementations import Open3DRenderer

class RendererFactory:
    """Factory Pattern to decouple the caller from specific rendering libraries."""
    
    @staticmethod
    def get_renderer(engine_name: str = "open3d") -> RendererInterface:
        if engine_name.lower() == "open3d":
            return Open3DRenderer()
        else:
            raise ValueError(f"Rendering engine '{engine_name}' is not supported.")
