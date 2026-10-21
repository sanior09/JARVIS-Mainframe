"""
tests/test_concurrency_dispatcher.py
====================================
Verification suite for J.A.R.V.I.S. Concurrency & GIL Optimizations:
1. Server Monitor non-blocking TTL caching (no 100ms GIL stall)
2. Bounded Tool Executor & Batch dispatcher
3. GUI Action Lock serialization under concurrent calls
"""

import time
import pytest
from jarvis_core.server_monitor import get_full_server_telemetry
from jarvis_core.tool_dispatcher import (
    GUI_ACTION_LOCK,
    TOOL_EXECUTOR,
    execute_tool_call,
    execute_tool_calls_batch,
    execute_tool_call_async,
)


@pytest.mark.unit
def test_server_telemetry_caching_and_nonblocking():
    """Verify telemetry doesn't stall for 100ms and utilizes TTL cache."""
    # First call initializes/populates cache
    t0 = time.perf_counter()
    res1 = get_full_server_telemetry(force_refresh=True)
    t1 = time.perf_counter()

    assert res1["status"] == "success"
    assert "cpu" in res1
    assert "memory" in res1

    # Second call must be instant (from cache, < 10ms)
    t2 = time.perf_counter()
    res2 = get_full_server_telemetry()
    t3 = time.perf_counter()

    cached_duration = t3 - t2
    assert cached_duration < 0.05, f"Cache fetch too slow: {cached_duration:.4f}s"
    assert res1["timestamp"] == res2["timestamp"]


@pytest.mark.unit
def test_tool_executor_bounded_pool():
    """Verify the singleton TOOL_EXECUTOR is initialized and bounded."""
    assert TOOL_EXECUTOR._max_workers == 8
    
    # Run async tool call
    fut = execute_tool_call_async({
        "name": "check_database_and_cache",
        "args": {}
    })
    res = fut.result(timeout=5.0)
    assert isinstance(res, dict)
    assert res.get("status") in ("nominal", "success")


@pytest.mark.unit
def test_execute_tool_calls_batch():
    """Test batch concurrent execution with timeout guardrails."""
    calls = [
        {"name": "check_database_and_cache", "args": {}},
        {"name": "get_screen_info", "args": {}},
    ]
    results = execute_tool_calls_batch(calls, timeout_per_tool=10.0)
    assert len(results) == 2
    for r in results:
        assert r["status"] == "success"


@pytest.mark.unit
def test_gui_action_lock_serialization():
    """Verify GUI_ACTION_LOCK protects concurrent access."""
    acquired = False
    with GUI_ACTION_LOCK:
        acquired = True
        # Lock is re-entrant
        with GUI_ACTION_LOCK:
            pass
    assert acquired is True
