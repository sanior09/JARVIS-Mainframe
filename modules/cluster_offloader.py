"""
cluster_offloader.py
Module 3: Distributed Task Offloader

Responsible for monitoring local LAN nodes and delegating heavy computational
tasks to them asynchronously to prevent the main machine from bottlenecking.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional

# Setup Module Logger
logger = logging.getLogger("ClusterOffloader")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class ClusterException(Exception):
    """Base exception for the Distributed Task Offloader module."""
    pass


class NodeUnavailableError(ClusterException):
    """Raised when no nodes are available to take a task."""
    pass


@dataclass
class ClusterNode:
    """Represents a computational node in the network."""
    node_id: str
    ip_address: str
    cpu_usage_percent: float = 0.0
    memory_available_mb: float = 0.0
    is_online: bool = False

    @property
    def can_accept_task(self) -> bool:
        # Simple heuristic: Reject tasks if CPU > 85% or Memory < 500MB
        return self.is_online and self.cpu_usage_percent < 85.0 and self.memory_available_mb > 500.0


class ClusterNodeManager:
    """Manages the registry and health checks of all cluster nodes."""
    
    def __init__(self):
        self.nodes: Dict[str, ClusterNode] = {}
        
    def register_node(self, node: ClusterNode):
        """Registers a new node into the cluster."""
        self.nodes[node.node_id] = node
        logger.info(f"Registered node: {node.node_id} ({node.ip_address})")
        
    async def ping_all_nodes(self):
        """Asynchronously pings all nodes to update their telemetry."""
        logger.debug("Pinging cluster nodes for telemetry update...")
        # Simulating network latency and telemetry updates
        await asyncio.sleep(0.1)
        for node in self.nodes.values():
            if node.is_online:
                # Simulated fluctuation
                node.cpu_usage_percent = max(0.0, min(100.0, node.cpu_usage_percent + 5.0))
                
    def get_best_available_node(self) -> Optional[ClusterNode]:
        """Returns the node with the lowest CPU usage that can accept a task."""
        available_nodes = [n for n in self.nodes.values() if n.can_accept_task]
        if not available_nodes:
            return None
            
        # Sort by lowest CPU usage
        available_nodes.sort(key=lambda n: n.cpu_usage_percent)
        return available_nodes[0]


class TaskDelegator:
    """
    Handles the delegation of heavy functions to cluster nodes.
    Uses Dependency Injection to receive the ClusterNodeManager.
    """
    
    def __init__(self, node_manager: ClusterNodeManager):
        self.node_manager = node_manager
        
    async def offload_task(self, task_name: str, payload: Any, timeout: float = 10.0) -> Any:
        """
        Offloads a computing task to the best available node in the cluster.
        """
        # Ensure telemetry is up to date
        await self.node_manager.ping_all_nodes()
        
        target_node = self.node_manager.get_best_available_node()
        if not target_node:
            logger.warning(f"Failed to offload task '{task_name}': No available nodes.")
            raise NodeUnavailableError("No cluster nodes available to accept the task.")
            
        logger.info(f"Offloading task '{task_name}' to Node: {target_node.node_id} [{target_node.ip_address}]")
        
        try:
            # Simulate an HTTP/RPC request to the target node
            result = await asyncio.wait_for(self._simulate_network_rpc(target_node, task_name, payload), timeout=timeout)
            logger.info(f"Task '{task_name}' completed successfully by {target_node.node_id}.")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Task '{task_name}' timed out on node {target_node.node_id}.")
            raise ClusterException(f"Task execution timed out on {target_node.node_id}")
            
    async def _simulate_network_rpc(self, node: ClusterNode, task_name: str, payload: Any) -> Dict[str, Any]:
        """Simulates the network delay and processing time of a remote task."""
        # Simulated heavy processing delay
        await asyncio.sleep(1.5)
        return {
            "status": "COMPLETED",
            "processed_by": node.node_id,
            "task": task_name,
            "result_data": f"Processed payload of size {len(str(payload))}"
        }


if __name__ == "__main__":
    async def run_tests():
        logger.info("--- Testing Distributed Task Offloader ---")
        manager = ClusterNodeManager()
        
        # Register nodes
        manager.register_node(ClusterNode("node-alpha", "192.168.1.101", 90.0, 1024.0, True))  # CPU too high
        manager.register_node(ClusterNode("node-beta", "192.168.1.102", 45.0, 2048.0, True))   # Good candidate
        manager.register_node(ClusterNode("node-gamma", "192.168.1.103", 10.0, 8192.0, False)) # Offline
        
        delegator = TaskDelegator(manager)
        
        try:
            # Dispatch heavy task
            heavy_payload = "A" * 10000
            result = await delegator.offload_task("TrainNeuralNetwork", heavy_payload)
            logger.info(f"Final Result: {result}")
            
        except ClusterException as e:
            logger.error(f"Offloading failed: {e}")

    asyncio.run(run_tests())
