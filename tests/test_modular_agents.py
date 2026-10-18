"""
tests/test_modular_agents.py
============================
Automated Test Suite for Modular Services (os_service, server_monitor, research_service)
and the Multi-Agent Router & Tool Execution Pipeline.
"""

import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
modules_dir = os.path.join(BASE_DIR, "modules")
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)


class TestModularAgents(unittest.TestCase):

    def test_os_service_processes(self):
        """Test listing active processes and sorting."""
        from jarvis_core.os_service import list_active_processes
        res = list_active_processes(top_n=5, sort_by="memory")
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["processes"], list)
        self.assertGreater(len(res["processes"]), 0)
        first_proc = res["processes"][0]
        self.assertIn("pid", first_proc)
        self.assertIn("name", first_proc)
        self.assertIn("memory_mb", first_proc)
        print(f"\n[TEST PASS] OS Service Top Process: {first_proc['name']} ({first_proc['memory_mb']} MB)")

    def test_os_service_maintenance(self):
        """Test disk check and maintenance report."""
        from jarvis_core.os_service import run_system_maintenance
        res = run_system_maintenance()
        self.assertEqual(res["status"], "success")
        self.assertIn("details", res)
        details = res["details"]
        self.assertIn("disk", details)
        self.assertIn("memory", details)
        print(f"[TEST PASS] OS Maintenance Free Disk: {details['disk']['free_gb']} GB, RAM used: {details['memory']['percent_used']}%")

    def test_server_monitor_telemetry(self):
        """Test full server telemetry retrieval."""
        from jarvis_core.server_monitor import get_full_server_telemetry, check_listening_ports
        telem = get_full_server_telemetry()
        self.assertEqual(telem["status"], "success")
        self.assertIn("cpu", telem)
        self.assertIn("memory", telem)
        self.assertIn("core_process", telem)

        ports = check_listening_ports([5050, 8000])
        self.assertEqual(ports["status"], "success")
        self.assertIn(5050, ports["ports"])
        print(f"[TEST PASS] Server Telemetry: CPU={telem['cpu']['total_percent']}%, Memory={telem['memory']['percent']}%")

    def test_server_monitor_db_and_watchdog(self):
        """Test database integrity and watchdog supervision."""
        from jarvis_core.server_monitor import check_database_and_cache, supervise_watchdog_services
        db_res = check_database_and_cache()
        self.assertEqual(db_res["status"], "success")
        self.assertIn("database", db_res)
        self.assertIn("caches", db_res)

        wd_res = supervise_watchdog_services()
        self.assertEqual(wd_res["status"], "success")
        self.assertIn("watchdog_active", wd_res)
        print(f"[TEST PASS] DB & Cache Check: DB exists={db_res['database']['db_exists']}, GC objects={wd_res['gc_collected_objects']}")

    def test_research_service_report_synthesis(self):
        """Test synthesis of technical report to reports/ directory."""
        from jarvis_core.research_service import synthesize_technical_report
        res = synthesize_technical_report(
            topic="Test Modular Architecture",
            findings="J.A.R.V.I.S. Core Services successfully extracted into modular services.",
            sources=["https://github.com/JARVIS-Mainframe/core"]
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["filepath"]))
        print(f"[TEST PASS] Research Report Synthesized: {res['filename']}")

    def test_multi_agent_router_intent(self):
        """Test sub-agent intent classification and configuration scoping."""
        from jarvis_agents import jarvis_multi_agent

        # Test routing
        intent_os = jarvis_multi_agent.route_intent("ช่วยดูหน่อยว่าโปรแกรมไหนกินแรมเยอะและช่วยเคลียร์ไฟล์ temp")
        self.assertEqual(intent_os, "os_control")

        intent_server = jarvis_multi_agent.route_intent("ตรวจดู telemetry เซิร์ฟเวอร์และพอร์ต 5050 หน่อยครับ")
        self.assertEqual(intent_server, "server_monitor")

        intent_research = jarvis_multi_agent.route_intent("ช่วยค้นคว้าวิจัยข้อมูลเชิงลึกเกี่ยวกับ Quantum AI ให้หน่อย")
        self.assertEqual(intent_research, "research")

        intent_creative = jarvis_multi_agent.route_intent("ช่วยวาดรูป Iron Man ในห้องแล็บไฮเทคให้หน่อย")
        self.assertEqual(intent_creative, "creative")

        intent_home = jarvis_multi_agent.route_intent("เปิดไฟห้องทำงานและปรับแอร์")
        self.assertEqual(intent_home, "home")

        # Test config
        cfg_os = jarvis_multi_agent.get_agent_config("os_control")
        self.assertIn("manage_windows_processes", cfg_os["tools"])
        self.assertIn("SUB-AGENT", cfg_os["system_prompt_addon"].upper())

        cfg_server = jarvis_multi_agent.get_agent_config("server_monitor")
        self.assertIn("get_server_telemetry", cfg_server["tools"])

        cfg_research = jarvis_multi_agent.get_agent_config("research")
        self.assertIn("autonomous_deep_research", cfg_research["tools"])

        print("[TEST PASS] Multi-Agent Intent Routing & Tool Scoping Verified!")

    def test_tool_registry_and_services(self):
        """Test that new tools are properly declared in TOOLS_DEFINITION and execute accurately."""
        from jarvis_core.tool_registry import TOOLS_DEFINITION
        tool_names = [t.get("function", {}).get("name") for t in TOOLS_DEFINITION]
        
        expected_new_tools = [
            "manage_windows_processes",
            "manage_system_maintenance",
            "execute_powershell_safe",
            "get_server_telemetry",
            "check_database_and_cache",
            "supervise_watchdog_services",
            "autonomous_deep_research",
            "synthesize_technical_report"
        ]
        
        for tool in expected_new_tools:
            self.assertIn(tool, tool_names, f"Missing tool in registry: {tool}")

        # Direct execution of os_service tool
        from jarvis_core.os_service import list_active_processes
        p_res = list_active_processes(top_n=3)
        self.assertEqual(p_res["status"], "success")
        self.assertEqual(len(p_res["processes"]), 3)

        # Direct execution of server_monitor tool
        from jarvis_core.server_monitor import get_full_server_telemetry
        s_res = get_full_server_telemetry()
        self.assertEqual(s_res["status"], "success")
        self.assertIn("cpu", s_res)

        print(f"[TEST PASS] All 8 New Tools successfully registered in TOOLS_DEFINITION and functional!")

    def test_metrics_and_notifier_integration(self):
        """Test JarvisMetricsCollector and JarvisNotifier integration."""
        from modules.jarvis_metrics import JarvisMetricsCollector, METRICS
        from modules.jarvis_notifier import JarvisNotifier, NOTIFIER

        self.assertIsNotNone(METRICS)
        self.assertIsNotNone(NOTIFIER)

        collector = JarvisMetricsCollector()
        collector.record(100, 50, 420.0, "qwen3.8-27b", True)
        stats = collector.get_stats()
        self.assertEqual(stats["tokens_today"]["total"], 150)
        self.assertEqual(stats["requests_today"], 1)
        self.assertEqual(stats["success_rate"], 100.0)

        notifier = JarvisNotifier(access_token="dummy", owner_id="dummy_owner")
        self.assertTrue(notifier.is_configured)
        print("\n[TEST PASS] Metrics and Notifier Modular Subsystems fully integrated!")


if __name__ == "__main__":
    unittest.main()


