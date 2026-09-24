"""
tests/test_config_and_state.py
Unit tests for configuration, runtime state, and telemetry.
"""

import os
import pytest
from jarvis_core.config import (
    BASE_DIR,
    MODULES_DIR,
    DATA_DIR,
    JARVIS_DB_PATH,
    JARVIS_SYSTEM_PROMPT,
)
from jarvis_core.state import (
    update_core_telemetry,
    get_telemetry_snapshot,
    increment_metric,
    get_metric,
)
from jarvis_core.database import ThreadSafeDB


@pytest.mark.unit
def test_directory_configuration():
    assert os.path.exists(BASE_DIR)
    assert os.path.exists(MODULES_DIR)
    assert os.path.exists(DATA_DIR)
    assert "J.A.R.V.I.S." in JARVIS_SYSTEM_PROMPT


@pytest.mark.unit
def test_telemetry_and_metrics():
    # Test metric increment
    init_val = get_metric("test_counter", 0)
    new_val = increment_metric("test_counter", 5)
    assert new_val == init_val + 5
    assert get_metric("test_counter") == new_val

    # Test core telemetry update
    update_core_telemetry("core4", "Testing", "Computer Agent Active")
    snapshot = get_telemetry_snapshot()
    assert snapshot["status"] == "Online"
    assert "core4" in snapshot["cores"]
    assert snapshot["cores"]["core4"]["status"] == "Testing"


@pytest.mark.unit
def test_threadsafedb_connection():
    # In-memory DB test
    conn = ThreadSafeDB.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, msg TEXT)")
    cursor.execute("INSERT INTO test (msg) VALUES (?)", ("jarvis_ok",))
    conn.commit()

    cursor.execute("SELECT msg FROM test WHERE id = 1")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "jarvis_ok"
    conn.close()
