"""
modules/jarvis_node_manager.py
==============================
J.A.R.V.I.S. Mainframe Node Manager (Server Side)
------------------------------------------------
Manages remote satellite computers (Gaming PC, Laptops, Workstations)
allowing J.A.R.V.I.S. to orchestrate apps, mouse/keyboard, vision, and power remotely.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("JarvisNodeManager")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NODES_CONFIG_FILE = os.path.join(BASE_DIR, "data", "satellite_nodes.json")


class JarvisNodeManager:
    """Manages satellite client nodes and dispatches commands over Local LAN or VPN."""

    _instance: Optional["JarvisNodeManager"] = None

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.load_nodes()

    @classmethod
    def get_instance(cls) -> "JarvisNodeManager":
        if cls._instance is None:
            cls._instance = JarvisNodeManager()
        return cls._instance

    def load_nodes(self):
        """Loads registered satellite nodes from configuration."""
        if os.path.exists(NODES_CONFIG_FILE):
            try:
                with open(NODES_CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.nodes = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load nodes config: {e}")
                self.nodes = {}
        else:
            # Default placeholder config
            self.nodes = {
                "gaming_pc": {
                    "name": "Gaming PC (ห้องนอน)",
                    "host": "192.168.1.150",
                    "port": 5055,
                    "token": "jarvis_secret_link_2026",
                    "status": "unverified"
                }
            }
            self.save_nodes()

    def save_nodes(self):
        """Persists registered nodes list."""
        try:
            os.makedirs(os.path.dirname(NODES_CONFIG_FILE), exist_ok=True)
            with open(NODES_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.nodes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save nodes config: {e}")

    def register_node(self, node_id: str, name: str, host: str, port: int = 5055, token: str = ""):
        """Registers a new satellite PC node."""
        self.nodes[node_id] = {
            "name": name,
            "host": host,
            "port": port,
            "token": token or "jarvis_secret_link_2026",
            "status": "active"
        }
        self.save_nodes()
        logger.info(f"Registered satellite node: {node_id} ({host}:{port})")

    def send_command(self, node_id: str, action: str, params: Optional[Dict[str, Any]] = None, timeout: float = 5.0) -> Dict[str, Any]:
        """Dispatches an action command to the designated satellite node."""
        node = self.nodes.get(node_id)
        if not node:
            # Try matching by friendly name
            matched = [n for nid, n in self.nodes.items() if node_id.lower() in n.get("name", "").lower() or node_id.lower() in nid.lower()]
            if matched:
                node = matched[0]
            else:
                return {"success": False, "error": f"Node '{node_id}' not found"}

        host = node.get("host", "127.0.0.1")
        port = node.get("port", 5055)
        token = node.get("token", "")
        url = f"http://{host}:{port}/"

        payload = {"action": action}
        if params:
            payload.update(params)

        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Jarvis-Token"] = token

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except requests.RequestException as e:
            logger.warning(f"Connection failed to node '{node.get('name')}': {e}")
            return {"success": False, "error": f"Node unreachable: {e}"}

    def capture_screen(self, node_id: str) -> Optional[str]:
        """Fetches base64 screenshot from designated satellite node."""
        res = self.send_command(node_id, "screen", {"max_dim": 1280}, timeout=8.0)
        if res.get("status") == "success" and res.get("image_b64"):
            return res.get("image_b64")
        return None

    def launch_game_or_app(self, node_id: str, uri_or_cmd: str) -> Dict[str, Any]:
        """Orders satellite PC to open game (steam://, roblox://) or program."""
        if "://" in uri_or_cmd:
            return self.send_command(node_id, "launch_uri", {"uri": uri_or_cmd})
        else:
            return self.send_command(node_id, "exec_command", {"command": uri_or_cmd})

    def lock_node(self, node_id: str) -> Dict[str, Any]:
        """Locks satellite PC screen."""
        return self.send_command(node_id, "lock")

    def ping_all_nodes(self) -> Dict[str, bool]:
        """Checks connectivity across all registered satellite nodes."""
        results = {}
        for nid, info in self.nodes.items():
            host = info.get("host", "")
            port = info.get("port", 5055)
            try:
                r = requests.get(f"http://{host}:{port}/status", timeout=2.0)
                results[nid] = (r.status_code == 200)
            except Exception:
                results[nid] = False
        return results


def get_node_manager() -> JarvisNodeManager:
    return JarvisNodeManager.get_instance()
