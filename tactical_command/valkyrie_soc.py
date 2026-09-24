"""
Project Valkyrie: Global Cyber Threat & SOC Matrix (Module 1).
Actively scans the local network for live hosts and open ports.
"""
import time
import socket
import asyncio
import concurrent.futures
from .core import BaseDataCollector, InMemoryCache, logger

# Common ports to scan to identify devices (HTTP, HTTPS, SSH, Home Assistant, RTSP, SMB)
COMMON_PORTS = [22, 80, 443, 445, 554, 8123]
SUBNET_PREFIX = "192.168.1."

class ValkyrieSOC(BaseDataCollector):
    """Actively scans local network and acts as a lightweight SOC."""
    
    def __init__(self, cache: InMemoryCache):
        super().__init__(cache)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)

    def scan_port(self, ip: str, port: int, timeout: float = 0.5) -> dict:
        """Scan a single port on a given IP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                return {"port": port, "status": "open"}
        except Exception:
            pass
        return {"port": port, "status": "closed"}
        
    def scan_host(self, ip: str) -> dict:
        """Scan common ports for a single IP."""
        open_ports = []
        # We run this synchronously in threads for simplicity
        for port in COMMON_PORTS:
            res = self.scan_port(ip, port)
            if res["status"] == "open":
                open_ports.append(port)
                
        if open_ports:
            return {"ip": ip, "status": "online", "open_ports": open_ports}
        return None

    def perform_network_sweep(self) -> dict:
        """Sweep the local /24 subnet for active devices."""
        logger.info(f"[VALKYRIE SOC] Initiating active network sweep on {SUBNET_PREFIX}0/24...")
        
        active_hosts = []
        futures = []
        
        # Scan IPs .1 to .254
        for i in range(1, 255):
            ip = f"{SUBNET_PREFIX}{i}"
            futures.append(self.executor.submit(self.scan_host, ip))
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                active_hosts.append(res)
                
        return {
            "status": "success",
            "timestamp": time.time(),
            "scanned_subnet": f"{SUBNET_PREFIX}0/24",
            "total_active_hosts": len(active_hosts),
            "hosts": active_hosts
        }
        
    def get_network_status(self) -> dict:
        """Returns network status, using cache to prevent spamming the network."""
        cache_key = "valkyrie_soc_scan"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        data = self.perform_network_sweep()
        self.cache.set(cache_key, data, ttl=300) # Cache scan results for 5 minutes
        return data

# Singleton instance
cache_store = InMemoryCache()
valkyrie_collector = ValkyrieSOC(cache_store)

def get_soc_report():
    """Helper function to be called from main JARVIS logic."""
    return valkyrie_collector.get_network_status()
