import sys
import os
import subprocess
import json

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "scan_local_network",
        "description": "Perform an active network sweep using the Enterprise Cyber Inspector module to find active IoT/computing devices and check for known vulnerabilities (CVEs).",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

def execute(args):
    """
    Entry point for JARVIS to scan local network using cyber_inspector.py.
    """
    try:
        # Run cyber_inspector as a subprocess to avoid event loop conflicts
        script_path = os.path.join(r"c:\JARVIS", "cyber_inspector.py")
        result = subprocess.run(
            ["python", script_path], 
            capture_output=True, 
            text=True, 
            cwd=r"c:\JARVIS",
            timeout=30  # Assuming scan takes 5-10s
        )
        
        output = result.stdout
        
        # Extract the JSON payload from the output
        if "--- ENTERPRISE SECURITY REPORT (JSON) ---" in output:
            json_block = output.split("--- ENTERPRISE SECURITY REPORT (JSON) ---")[1].split("--- J.A.R.V.I.S. VOICE SUMMARY ---")[0].strip()
            try:
                report_data = json.loads(json_block)
                
                devices = report_data.get("devices", [])
                vulns = report_data.get("vulnerabilities", [])
                
                report = f"Cyber Inspector (Enterprise) Scan Report:\n"
                report += f"Total Active Devices: {len(devices)}\n\n"
                
                for d in devices:
                    ports = ", ".join([str(p['port']) for p in d['open_ports']])
                    report += f"- IP: {d['ip']} | MAC: {d['mac_address']} | Vendor: {d['vendor']} | Ports: {ports}\n"
                
                if vulns:
                    report += f"\n[WARNING] {len(vulns)} Vulnerabilities Detected!\n"
                    for v in vulns:
                        report += f"- {v['software']} v{v['version']} -> {v['cve_id']} ({v['severity']})\n"
                else:
                    report += "\nNo critical vulnerabilities found."
                    
                return report
            except Exception as e:
                return f"Failed to parse JSON report from Cyber Inspector: {e}"
        
        return "Cyber Inspector executed, but no report was generated."
        
    except subprocess.TimeoutExpired:
        return "Network scan timed out after 30 seconds."
    except Exception as e:
        return f"Error executing Cyber Inspector: {str(e)}"
