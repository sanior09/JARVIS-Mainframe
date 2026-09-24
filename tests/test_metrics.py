"""
Unit Tests for JarvisMetricsCollector and /api/metrics endpoint
"""

import os
import sys
import time
import pytest

# Add project root and modules to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from modules.jarvis_metrics import JarvisMetricsCollector


def test_metrics_collector_init():
    collector = JarvisMetricsCollector(max_history=50)
    stats = collector.get_stats()
    assert stats["status"] == "online"
    assert stats["tokens_today"]["total"] == 0
    assert stats["requests_today"] == 0
    assert stats["success_rate"] == 100.0
    assert stats["avg_response_ms"] == 0.0
    assert isinstance(stats["recent_trend"], list)
    assert len(stats["recent_trend"]) == 0


def test_metrics_collector_record_success():
    collector = JarvisMetricsCollector(max_history=50)
    collector.record(
        prompt_tokens=150,
        completion_tokens=50,
        response_time_ms=850.5,
        model="qwen/qwen3.8-27b",
        success=True
    )

    stats = collector.get_stats()
    assert stats["requests_today"] == 1
    assert stats["success_today"] == 1
    assert stats["errors_today"] == 0
    assert stats["success_rate"] == 100.0
    assert stats["tokens_today"]["prompt"] == 150
    assert stats["tokens_today"]["completion"] == 50
    assert stats["tokens_today"]["total"] == 200
    assert stats["avg_response_ms"] == 850.5
    assert stats["avg_response_s"] == 0.85
    assert stats["model_usage"]["qwen3.8-27b"] == 1
    assert len(stats["recent_trend"]) == 1
    assert stats["recent_trend"][0]["tokens"] == 200
    assert stats["recent_trend"][0]["ok"] is True


def test_metrics_collector_record_error_and_rate():
    collector = JarvisMetricsCollector(max_history=50)
    # 3 successes
    for _ in range(3):
        collector.record(prompt_tokens=100, completion_tokens=50, response_time_ms=1000.0, success=True)
    # 1 failure
    collector.record(prompt_tokens=0, completion_tokens=0, response_time_ms=500.0, success=False)

    stats = collector.get_stats()
    assert stats["requests_today"] == 4
    assert stats["success_today"] == 3
    assert stats["errors_today"] == 1
    assert stats["success_rate"] == 75.0
    assert stats["tokens_today"]["total"] == 450
    # Average response time only considers successful requests
    assert stats["avg_response_ms"] == 1000.0


def test_metrics_collector_rolling_window():
    collector = JarvisMetricsCollector(max_history=5)
    for i in range(10):
        collector.record(
            prompt_tokens=10,
            completion_tokens=10,
            response_time_ms=float(i * 100),
            success=True
        )

    assert len(collector._requests) == 5
    # Total tokens today accumulated all 10 requests
    assert collector._tokens_today["total"] == 200
    # Rolling window only holds last 5
    stats = collector.get_stats()
    assert len(stats["recent_trend"]) == 5


def test_metrics_collector_schema_compatibility():
    collector = JarvisMetricsCollector()
    collector.record(10, 20, 300.0, "test-model", True)
    stats = collector.get_stats()

    # Verify all expected keys for web dashboard HUD
    required_keys = [
        "status",
        "avg_response_ms",
        "avg_response_s",
        "success_rate",
        "tokens_today",
        "requests_today",
        "success_today",
        "errors_today",
        "active_model",
        "model_usage",
        "recent_trend",
        "quota_limit",
        "quota_percent"
    ]
    for key in required_keys:
        assert key in stats, f"Missing key '{key}' in stats output"
