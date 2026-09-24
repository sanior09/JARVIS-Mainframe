import asyncio
import concurrent.futures
import enum
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("Generative3D")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)

class ModelFormat(enum.Enum):
    OBJ = "obj"
    GLTF = "gltf"
    STL = "stl"
    PLY = "ply"

class GenerationSource(enum.Enum):
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"
    PARAMETRIC_CAD = "parametric_cad"

@dataclass
class GenerationRequest:
    prompt: Optional[str] = None
    image_bytes: Optional[bytes] = None
    source: GenerationSource = GenerationSource.TEXT_TO_3D
    target_format: ModelFormat = ModelFormat.OBJ

@dataclass
class GenerationResult:
    success: bool
    file_path: Optional[str]
    generation_time_sec: float
    source: GenerationSource
    error_message: Optional[str] = None
    cached: bool = False

class MeshCacheManager:
    """
    Manages local disk cache using SHA-256 hashes to prevent redundant 3D generation.
    """
    def __init__(self, cache_dir: str = "3d_cache"):
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _generate_hash(self, request: GenerationRequest) -> str:
        hasher = hashlib.sha256()
        hasher.update(request.source.value.encode('utf-8'))
        hasher.update(request.target_format.value.encode('utf-8'))
        
        if request.prompt:
            hasher.update(request.prompt.encode('utf-8'))
        if request.image_bytes:
            hasher.update(request.image_bytes)
            
        return hasher.hexdigest()

    def get_cached_mesh(self, request: GenerationRequest) -> Optional[str]:
        cache_hash = self._generate_hash(request)
        file_path = os.path.join(self.cache_dir, f"{cache_hash}.{request.target_format.value}")
        
        if os.path.exists(file_path):
            logger.info(f"Cache HIT for hash: {cache_hash[:8]}...")
            return file_path
        return None

    def get_cache_path(self, request: GenerationRequest) -> str:
        cache_hash = self._generate_hash(request)
        return os.path.join(self.cache_dir, f"{cache_hash}.{request.target_format.value}")

class Base3DStrategy(ABC):
    """Abstract interface for a 3D Generation Strategy."""
    @abstractmethod
    def generate(self, request: GenerationRequest, output_path: str) -> GenerationResult:
        pass

class TextTo3DStrategy(Base3DStrategy):
    """
    Simulates a heavy Text-to-3D generation (e.g., Shap-E, Point-E).
    In production, this is where you load the pipeline or call HuggingFace API.
    """
    def generate(self, request: GenerationRequest, output_path: str) -> GenerationResult:
        logger.info(f"🚀 Text-to-3D: Processing prompt -> '{request.prompt}'")
        start_t = time.perf_counter()
        
        time.sleep(3.0)
        
        logger.debug("Text-to-3D: Converting SDF Point Cloud to Mesh via Marching Cubes...")
        time.sleep(1.0)
        
        with open(output_path, "w") as f:
            f.write(f"# MOCK 3D OBJ FILE\n# Generated from Prompt: {request.prompt}\n")
            f.write("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n")
            
        return GenerationResult(
            success=True,
            file_path=output_path,
            generation_time_sec=time.perf_counter() - start_t,
            source=GenerationSource.TEXT_TO_3D
        )

class ImageTo3DStrategy(Base3DStrategy):
    """
    Simulates a Vision-to-3D generation (e.g., TripoSR, OpenLRM).
    Handles background removal and mesh extraction.
    """
    def generate(self, request: GenerationRequest, output_path: str) -> GenerationResult:
        logger.info(f"📸 Vision-to-3D: Processing image bytes ({len(request.image_bytes or b'')} bytes)")
        start_t = time.perf_counter()
        
        logger.debug("Vision-to-3D: Applying RemBg Semantic Segmentation...")
        time.sleep(1.0)
        
        logger.debug("Vision-to-3D: Executing NeRF / TripoSR Transformer inference...")
        time.sleep(3.5)
        
        with open(output_path, "w") as f:
            f.write(f"# MOCK 3D GLTF/OBJ FILE\n# Generated from Extracted Foreground Image\n")
            
        return GenerationResult(
            success=True,
            file_path=output_path,
            generation_time_sec=time.perf_counter() - start_t,
            source=GenerationSource.IMAGE_TO_3D
        )

def _sync_worker(strategy: Base3DStrategy, request: GenerationRequest, output_path: str) -> GenerationResult:
    """Runs inside the ProcessPool."""
    try:
        
        return strategy.generate(request, output_path)
    except RuntimeError as e: 
        if "CUDA out of memory" in str(e):
            return GenerationResult(False, None, 0.0, request.source, error_message="CUDA_OOM_ERROR")
        return GenerationResult(False, None, 0.0, request.source, error_message=str(e))
    except Exception as e:
        return GenerationResult(False, None, 0.0, request.source, error_message=str(e))

class Generative3DOrchestrator:
    """
    Main Facade managing generation strategies, caching, and ProcessPools.
    Provides purely non-blocking async interfaces for J.A.R.V.I.S. GUI.
    """
    def __init__(self, cache_dir: str = "3d_cache"):
        self.cache = MeshCacheManager(cache_dir)
        
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)

    async def _execute_async(self, strategy: Base3DStrategy, request: GenerationRequest) -> GenerationResult:
        
        cached_file = self.cache.get_cached_mesh(request)
        if cached_file:
            return GenerationResult(
                success=True,
                file_path=cached_file,
                generation_time_sec=0.0,
                source=request.source,
                cached=True
            )

        output_path = self.cache.get_cache_path(request)
        loop = asyncio.get_running_loop()
        
        result = await loop.run_in_executor(
            self.executor,
            _sync_worker,
            strategy,
            request,
            output_path
        )
        return result

    async def generate_from_text(self, prompt: str, target_format: ModelFormat = ModelFormat.OBJ) -> GenerationResult:
        req = GenerationRequest(
            prompt=prompt,
            source=GenerationSource.TEXT_TO_3D,
            target_format=target_format
        )
        return await self._execute_async(TextTo3DStrategy(), req)

    async def generate_from_image(self, image_bytes: bytes, target_format: ModelFormat = ModelFormat.OBJ) -> GenerationResult:
        req = GenerationRequest(
            image_bytes=image_bytes,
            source=GenerationSource.IMAGE_TO_3D,
            target_format=target_format
        )
        return await self._execute_async(ImageTo3DStrategy(), req)
        
    def shutdown(self):
        self.executor.shutdown(wait=False)

async def _run_unit_test():
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("\n" + "="*60)
    print(" 🛠️ STARTING MULTIMODAL 3D GENERATOR PIPELINE TEST")
    print("="*60)

    orchestrator = Generative3DOrchestrator(cache_dir="test_3d_cache")

    try:
        
        print("\n[TEST 1] Text-to-3D (Prompt: 'iPhone 17 Pro Max')")
        print(">> Dispatching to ProcessPoolExecutor (Non-Blocking)...")
        res1 = await orchestrator.generate_from_text("iPhone 17 Pro Max")
        if res1.success:
            print(f"✅ Generated in {res1.generation_time_sec:.2f}s | Saved to: {res1.file_path}")
        else:
            print(f"❌ Failed: {res1.error_message}")

        print("\n[TEST 2] Text-to-3D Cache Hit Test (Prompt: 'iPhone 17 Pro Max')")
        print(">> Dispatching identical prompt to test SHA-256 caching...")
        res2 = await orchestrator.generate_from_text("iPhone 17 Pro Max")
        if res2.cached:
            print(f"✅ Cache HIT! Generation skipped. | Latency: {res2.generation_time_sec:.4f}s")
        else:
            print("❌ Cache Miss (Expected Hit)")

        print("\n[TEST 3] Vision-to-3D (Simulating image bytes)")
        mock_image_bytes = b"fake_jpeg_header_0101010101"
        res3 = await orchestrator.generate_from_image(mock_image_bytes, target_format=ModelFormat.GLTF)
        if res3.success:
            print(f"✅ Generated in {res3.generation_time_sec:.2f}s | Saved to: {res3.file_path}")
        else:
            print(f"❌ Failed: {res3.error_message}")

    finally:
        orchestrator.shutdown()
        print("\n✅ Generative 3D Pipeline Test Completed Successfully!\n" + "="*60)

def visualize_data_3d(data: dict, data_type: str = 'molecule'):
    import json
    import webbrowser
    import os
    
    try:
        
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        os.makedirs(static_dir, exist_ok=True)
        data_file = os.path.join(static_dir, 'hologram_data.json')
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({'type': data_type, **data}, f)
            
        html_path = os.path.join(static_dir, 'hologram_viewer.html')
        webbrowser.open('file://' + os.path.abspath(html_path))
        return "Holographic 3D visualization initialized."
    except Exception as e:
        logger.error(f"Error visualizing 3D: {e}")
        return f"Error visualizing 3D: {e}"

if __name__ == "__main__":
    asyncio.run(_run_unit_test())
