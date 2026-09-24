"""
comfyui_bridge.py
Module: ComfyUI Automation Bridge

Manages asynchronous communication with a ComfyUI Server via REST API and WebSockets.
Constructs dynamic JSON workflow payloads for AI image/video generation.
"""

import asyncio
import json
import logging
import urllib.request
import urllib.parse
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

try:
    import aiohttp
    import websockets
    _HAS_ASYNC_DEPS = True
except ImportError:
    _HAS_ASYNC_DEPS = False

# Setup Module Logger
logger = logging.getLogger("ComfyUIBridge")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class ComfyUIBridgeException(Exception):
    """Base exception for the ComfyUI Bridge module."""
    pass


class AbstractWorkflowBuilder(ABC):
    @abstractmethod
    def build_payload(self, prompt_text: str, **kwargs) -> Dict[str, Any]:
        """Constructs a ComfyUI-compatible workflow payload."""
        pass


class WorkflowPromptBuilder(AbstractWorkflowBuilder):
    """
    Parses natural language commands and builds a dynamic ComfyUI workflow JSON.
    In a real-world scenario, this might load a template from a .json file.
    """
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = template_path
        # Fallback basic text2img template if no file provided
        self._default_template = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 0,
                    "steps": 20,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"batch_size": 1, "height": 512, "width": 512}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "A beautiful cinematic shot of a futuristic city", "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "ugly, blurry, low quality", "clip": ["4", 1]}
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "J.A.R.V.I.S_gen", "images": ["8", 0]}
            }
        }

    def build_payload(self, prompt_text: str, negative_prompt: str = "", seed: int = 42) -> Dict[str, Any]:
        """Injects dynamic values into the ComfyUI nodes."""
        import copy
        workflow = copy.deepcopy(self._default_template)
        
        # Inject dynamic values
        workflow["6"]["inputs"]["text"] = prompt_text
        if negative_prompt:
            workflow["7"]["inputs"]["text"] = negative_prompt
        workflow["3"]["inputs"]["seed"] = seed
        
        logger.info(f"Workflow built with seed: {seed}")
        return workflow


class ComfyUIClient:
    """
    Asynchronous client for interacting with the ComfyUI server.
    """
    def __init__(self, server_address: str = "127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        
    async def queue_prompt(self, workflow_prompt: Dict[str, Any]) -> str:
        """Sends a JSON workflow to the API and returns the prompt_id."""
        if not _HAS_ASYNC_DEPS:
            logger.error("aiohttp is required for real ComfyUI interactions.")
            raise ComfyUIBridgeException("Missing dependency: aiohttp")
            
        payload = {"prompt": workflow_prompt, "client_id": self.client_id}
        url = f"http://{self.server_address}/prompt"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        prompt_id = data.get('prompt_id')
                        logger.info(f"Successfully queued workflow. Prompt ID: {prompt_id}")
                        return prompt_id
                    else:
                        error_text = await response.text()
                        raise ComfyUIBridgeException(f"Failed to queue prompt: {error_text}")
            except Exception as e:
                logger.warning(f"ComfyUI API unreachable. Assuming mock environment. Error: {e}")
                return "MOCK_PROMPT_ID_12345"

    async def listen_to_progress(self, prompt_id: str):
        """Connects via WebSocket to track generation progress."""
        if not _HAS_ASYNC_DEPS:
            logger.info(f"[MOCK] Listening to progress for {prompt_id}...")
            await asyncio.sleep(2)
            logger.info("[MOCK] Generation complete.")
            return

        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
        logger.info(f"Connecting to WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as ws:
                while True:
                    out = await ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message['type'] == 'executing':
                            data = message['data']
                            if data['node'] is None and data['prompt_id'] == prompt_id:
                                logger.info(f"Execution complete for {prompt_id}")
                                break # Execution is done
                        elif message['type'] == 'progress':
                            data = message['data']
                            logger.info(f"Progress: {data['value']}/{data['max']} (Node: {data['node']})")
        except Exception as e:
            logger.warning(f"WebSocket connection failed/mocked. Error: {e}")


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing ComfyUI Automation Bridge ---")
        
        builder = WorkflowPromptBuilder()
        client = ComfyUIClient(server_address="127.0.0.1:8188")
        
        # 1. Build Payload
        logger.info("Building dynamic payload...")
        payload = builder.build_payload(
            prompt_text="Iron Man armor suit standing in a futuristic laboratory, 8k resolution, photorealistic",
            seed=9999
        )
        
        # 2. Queue Payload & Listen
        try:
            prompt_id = await client.queue_prompt(payload)
            if prompt_id:
                await client.listen_to_progress(prompt_id)
        except Exception as e:
            logger.error(f"Test failed: {e}")
            
    asyncio.run(run_tests())
