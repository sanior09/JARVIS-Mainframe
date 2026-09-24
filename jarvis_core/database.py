"""
jarvis_core/database.py
Thread-safe SQLite database connection manager.
"""

from __future__ import annotations

import os
import sqlite3 as _core_sqlite3
import threading
from typing import Any

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_DIR)
_DATA_DB = os.path.join(_PROJECT_ROOT, "data", "jarvis.db")
JARVIS_DB_PATH = _DATA_DB if os.path.exists(_DATA_DB) or os.path.exists(os.path.join(_PROJECT_ROOT, "data")) else "jarvis.db"


class ThreadSafeDB:
    """Thread-safe wrapper around sqlite3 to prevent database locks."""
    _lock = threading.Lock()

    @classmethod
    def connect(
        cls,
        database: str,
        timeout: float = 5.0,
        detect_types: int = 0,
        isolation_level: str = 'DEFERRED',
        check_same_thread: bool = False,
        factory: Any = _core_sqlite3.Connection,
        cached_statements: int = 128,
        uri: bool = False
    ) -> _LockedConnection:
        conn = _core_sqlite3.connect(
            database,
            timeout=timeout,
            detect_types=detect_types,
            isolation_level=isolation_level,
            check_same_thread=False,
            factory=factory,
            cached_statements=cached_statements,
            uri=uri
        )
        conn.execute("PRAGMA journal_mode=WAL;")
        return _LockedConnection(conn, cls._lock)


class _LockedConnection:
    def __init__(self, conn: Any, lock: threading.Lock) -> None:
        self._conn = conn
        self._lock = lock

    def cursor(self, *args: Any, **kwargs: Any) -> _LockedCursor:
        return _LockedCursor(self._conn.cursor(*args, **kwargs), self._lock)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.execute(*args, **kwargs)

    def executemany(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.executemany(*args, **kwargs)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def rollback(self) -> None:
        with self._lock:
            self._conn.rollback()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> _LockedConnection:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ('_conn', '_lock'):
            super().__setattr__(name, value)
        else:
            setattr(self._conn, name, value)


class _LockedCursor:
    def __init__(self, cursor: Any, lock: threading.Lock) -> None:
        self._cursor = cursor
        self._lock = lock

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._cursor.execute(*args, **kwargs)

    def executemany(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._cursor.executemany(*args, **kwargs)

    def fetchone(self) -> Any:
        with self._lock:
            return self._cursor.fetchone()

    def fetchall(self) -> Any:
        with self._lock:
            return self._cursor.fetchall()

    def __iter__(self) -> Any:
        with self._lock:
            return iter(self._cursor.fetchall())

    def close(self) -> None:
        with self._lock:
            self._cursor.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ('_cursor', '_lock'):
            super().__setattr__(name, value)
        else:
            setattr(self._cursor, name, value)
