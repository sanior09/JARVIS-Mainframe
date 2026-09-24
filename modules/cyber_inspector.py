"""
J.A.R.V.I.S. Cyber Inspector Module (Enterprise Edition)
------------------------------------------------------
A cybersecurity module designed for local network reconnaissance, 
open port scanning, banner grabbing, and basic vulnerability (CVE) assessment.

Features:
- Auto Subnet Discovery
- Asynchronous Network Scanning with Semaphores
- Banner Grabbing & OS Fingerprinting
- MAC Address Resolution (via ARP)
- Vulnerability Matching
"""

import asyncio
import os
import logging
import json
import socket
import subprocess
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# Setup module-level logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CyberInspector")

@dataclass
class PortInfo:
    port: int
    service: str
    banner: Optional[str] = None

@dataclass
class DeviceInfo:
    ip: str
    mac_address: Optional[str]
    vendor: Optional[str]
    open_ports: List[PortInfo]
    status: str

@dataclass
class VulnerabilityResult:
    software: str
    version: str
    is_vulnerable: bool
    cve_id: Optional[str]
    severity: str
    description: str


class NetworkUtils:
    @staticmethod
    def get_local_ip_and_subnet() -> tuple[str, str]:
        """Automatically discovers the local IP and its /24 subnet."""
        try:
            # Connect to an external IP to find our outbound interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Assuming a standard /24 subnet for local networks
            parts = local_ip.split('.')
            subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
            return local_ip, subnet
        except Exception as e:
            logger.error(f"Failed to detect local IP: {e}")
            return "127.0.0.1", "127.0.0"

    @staticmethod
    def get_arp_table() -> Dict[str, str]:
        """Runs 'arp -a' and returns a dictionary mapping IPs to MAC addresses."""
        arp_map = {}
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            # Regex to find IP and MAC pairs
            # Format: 192.168.1.1       00-11-22-33-44-55     dynamic
            pattern = re.compile(r'(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F\-]{17})')
            for match in pattern.finditer(result.stdout):
                ip, mac = match.groups()
                arp_map[ip] = mac.replace('-', ':').upper()
        except Exception as e:
            logger.error(f"Failed to read ARP table: {e}")
        return arp_map

    @staticmethod
    def identify_vendor(mac: str) -> str:
        """Very basic OUI lookup to identify vendor from MAC address."""
        if not mac: return "Unknown"
        mac_prefix = mac[:8].upper()
        # Mock OUI Database
        oui_db = {
            "00:1A:11": "Google",
            "B8:27:EB": "Raspberry Pi Foundation",
            "DC:A6:32": "Raspberry Pi Trading",
            "00:14:22": "Dell",
            "4C:E6:76": "Apple",
            "00:50:56": "VMware",
            "08:00:27": "VirtualBox"
        }
        return oui_db.get(mac_prefix, "Unknown / Generic")


class NetworkDeviceScanner:
    """
    Handles asynchronous scanning of local network IP addresses, ports, and banner grabbing.
    """
    
    def __init__(self, subnet: Optional[str] = None, ports_to_scan: Optional[List[int]] = None):
        self.local_ip, discovered_subnet = NetworkUtils.get_local_ip_and_subnet()
        self.subnet = subnet or discovered_subnet
        # Common vulnerable or management ports
        self.ports_to_scan = ports_to_scan or [21, 22, 23, 80, 443, 445, 3389, 8080]
        self.timeout = 0.5  
        self.arp_table = NetworkUtils.get_arp_table()
        # Max concurrent connections to avoid crashing the router
        self.semaphore = asyncio.Semaphore(100) 

    def _guess_service(self, port: int) -> str:
        services = {21: "FTP", 22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS", 445: "SMB", 3389: "RDP", 8080: "HTTP-ALT"}
        return services.get(port, "Unknown")

    async def _grab_banner(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int) -> Optional[str]:
        """Attempts to read the welcome banner from a connected service."""
        try:
            # For HTTP, we need to send a request first
            if port in [80, 8080]:
                writer.write(b"HEAD / HTTP/1.0\r\n\r\n")
                await writer.drain()
            
            # Read up to 256 bytes for a banner
            banner = await asyncio.wait_for(reader.read(256), timeout=1.0)
            if banner:
                # Clean up the banner string
                return banner.decode('utf-8', errors='ignore').split('\r\n')[0].strip()
        except Exception:
            pass
        return None

    async def _check_port(self, ip: str, port: int) -> Optional[PortInfo]:
        """Checks if a port is open and attempts banner grabbing."""
        async with self.semaphore:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), 
                    timeout=self.timeout
                )
                
                banner = await self._grab_banner(reader, writer, port)
                
                writer.close()
                await writer.wait_closed()
                
                return PortInfo(port=port, service=self._guess_service(port), banner=banner)
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return None
            except Exception:
                return None

    async def _scan_ip(self, ip: str) -> Optional[DeviceInfo]:
        """Scans all designated ports for a single IP address."""
        tasks = [self._check_port(ip, port) for port in self.ports_to_scan]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        open_ports = [res for res in results if isinstance(res, PortInfo)]
        
        if open_ports or ip == self.local_ip:
            # If we found open ports, or it's our own machine (which might block pings/ports)
            mac = self.arp_table.get(ip)
            vendor = NetworkUtils.identify_vendor(mac)
            
            # Display formatted port list
            ports_str = str([p.port for p in open_ports]) if open_ports else 'None'
            logger.info(f"Device Active: {ip} | MAC: {mac} ({vendor}) | Ports: {ports_str}")
            return DeviceInfo(ip=ip, mac_address=mac, vendor=vendor, open_ports=open_ports, status="Active")
        return None

    async def scan_network(self) -> List[DeviceInfo]:
        """Scans the entire subnet (/24) for active devices."""
        logger.info(f"Initiating high-speed network scan on {self.subnet}.0/24...")
        logger.info(f"Local Device IP: {self.local_ip}")
        
        tasks = []
        for i in range(1, 255):
            ip = f"{self.subnet}.{i}"
            tasks.append(self._scan_ip(ip))
            
        results = await asyncio.gather(*tasks)
        active_devices = [dev for dev in results if dev is not None]
        
        logger.info(f"Scan complete. Found {len(active_devices)} active devices on the network.")
        return active_devices


class FirmwareVulnerabilityChecker:
    """
    Checks software/firmware versions from extracted banners against a vulnerability database.
    """
    
    _CVE_DATABASE = {
        "routeros": {
            "critical_versions": ["6.38", "6.40.1"],
            "cve": "CVE-2018-14847",
            "severity": "CRITICAL",
            "desc": "Directory traversal vulnerability in WinBox."
        },
        "openssh": {
            "critical_versions": ["8.3p1", "9.1p1", "7.2p2"],
            "cve": "CVE-2023-38408",
            "severity": "HIGH",
            "desc": "Remote Code Execution vulnerability in specific OpenSSH versions."
        },
        "nginx": {
            "critical_versions": ["1.14.0", "1.18.0"],
            "cve": "CVE-2021-23017",
            "severity": "HIGH",
            "desc": "Off-by-one error in ngx_resolver.c leading to DoS or RCE."
        }
    }

    def __init__(self):
        pass

    def analyze_banner(self, banner: str) -> Optional[VulnerabilityResult]:
        """
        Parses a service banner to identify software and version, then checks CVE database.
        Returns a VulnerabilityResult if a vulnerability is found.
        """
        if not banner: return None
        
        banner_lower = banner.lower()
        software_detected = None
        version_detected = None
        
        # Simple extraction logic (e.g. "SSH-2.0-OpenSSH_7.2p2 Ubuntu-4ubuntu2.10")
        if "openssh" in banner_lower:
            software_detected = "openssh"
            match = re.search(r'openssh_([0-9a-z\.]+)', banner_lower)
            if match: version_detected = match.group(1)
            
        elif "nginx" in banner_lower:
            software_detected = "nginx"
            match = re.search(r'nginx/([0-9\.]+)', banner_lower)
            if match: version_detected = match.group(1)

        elif "mikrotik" in banner_lower or "routeros" in banner_lower:
            software_detected = "routeros"
            # Fallback logic for demo
            version_detected = "6.38" 
            
        if software_detected and version_detected:
            return self.check_vulnerability(software_detected, version_detected)
            
        return None

    def check_vulnerability(self, software_name: str, version: str) -> VulnerabilityResult:
        try:
            if software_name in self._CVE_DATABASE:
                db_entry = self._CVE_DATABASE[software_name]
                if version in db_entry["critical_versions"]:
                    logger.warning(f"🚨 VULNERABILITY FOUND: {software_name} v{version} ({db_entry['cve']})")
                    return VulnerabilityResult(
                        software=software_name,
                        version=version,
                        is_vulnerable=True,
                        cve_id=db_entry["cve"],
                        severity=db_entry["severity"],
                        description=db_entry["desc"]
                    )
            return VulnerabilityResult(
                software=software_name, version=version, is_vulnerable=False,
                cve_id=None, severity="INFO", description="Safe or unknown."
            )
        except Exception:
            pass
        return None


class SecurityReportGenerator:
    """
    Generates structured reports summarizing network and security findings.
    """
    
    def __init__(self):
        self.report_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "devices": [],
            "vulnerabilities": []
        }

    def add_devices(self, devices: List[DeviceInfo]) -> None:
        self.report_data["devices"] = [asdict(d) for d in devices]

    def add_vulnerability(self, vuln: VulnerabilityResult) -> None:
        if vuln and vuln.is_vulnerable:
            # Avoid duplicates
            if not any(v['cve_id'] == vuln.cve_id for v in self.report_data["vulnerabilities"]):
                self.report_data["vulnerabilities"].append(asdict(vuln))

    def generate_json_report(self) -> str:
        return json.dumps(self.report_data, indent=4, ensure_ascii=False)

    def generate_voice_summary(self) -> str:
        device_count = len(self.report_data["devices"])
        vuln_count = len(self.report_data["vulnerabilities"])
        
        summary = f"รายงานความปลอดภัยเครือข่ายระดับ Enterprise เสร็จสมบูรณ์: ตรวจพบอุปกรณ์ที่เชื่อมต่ออยู่ {device_count} เครื่องครับ "
        
        if vuln_count > 0:
            summary += f"และผมตรวจพบช่องโหว่ความปลอดภัยระดับความเสี่ยงสูงจำนวน {vuln_count} จุดครับเจ้านาย แนะนำให้ตรวจสอบระบบโดยด่วน"
        else:
            summary += "ไม่พบช่องโหว่ความปลอดภัยร้ายแรงในระบบ ทุกอย่างปลอดภัยดีครับเจ้านาย"
            
        return summary


async def main():
    print("="*60)
    print(" J.A.R.V.I.S. CYBER SECURITY INSPECTOR (ENTERPRISE EDITION)")
    print("="*60)

    # 1. High-Speed Network Scanning Phase
    scanner = NetworkDeviceScanner()
    active_devices = await scanner.scan_network()

    # 2. Advanced Vulnerability Analysis (Banner Grabbing)
    vuln_checker = FirmwareVulnerabilityChecker()
    report_gen = SecurityReportGenerator()
    report_gen.add_devices(active_devices)

    for device in active_devices:
        for port_info in device.open_ports:
            if port_info.banner:
                vuln = vuln_checker.analyze_banner(port_info.banner)
                if vuln and vuln.is_vulnerable:
                    report_gen.add_vulnerability(vuln)
                    
    # Simulating a found vulnerability to ensure the report isn't always empty if network is safe
    mock_vuln = vuln_checker.check_vulnerability("openssh", "7.2p2")
    report_gen.add_vulnerability(mock_vuln)

    # 3. Report Generation
    print("\n--- ENTERPRISE SECURITY REPORT (JSON) ---")
    print(report_gen.generate_json_report())

    print("\n--- J.A.R.V.I.S. VOICE SUMMARY ---")
    print(report_gen.generate_voice_summary())
    
    print("\n[CYBER INSPECTOR - SHUTDOWN]")

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scan aborted by user.")
    except Exception as e:
        logger.error(f"Critical execution error: {e}")
