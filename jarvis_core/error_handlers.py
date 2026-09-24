"""
jarvis_core/error_handlers.py
─────────────────────────────────────────────────────
Centralized exception catalogue and specific error-handling helpers.
Converts broad 'except Exception' patterns into targeted, logged handlers.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Callable, Optional, Type, TypeVar

import requests

logger = logging.getLogger("JARVIS")

F = TypeVar("F", bound=Callable[..., Any])


# ──────────────────────────────────────────────────────────────────────────────
# Specific Exception Groups
# ──────────────────────────────────────────────────────────────────────────────

#: Exceptions that indicate the Groq/HTTP API is unreachable or overloaded.
GROQ_NETWORK_ERRORS = (
    ConnectionError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
)

#: SQLite-related errors we care about.
DB_ERRORS = (
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
    sqlite3.IntegrityError,
    sqlite3.ProgrammingError,
)

#: Import/module-loading failures.
IMPORT_ERRORS = (ImportError, ModuleNotFoundError, AttributeError)


# ──────────────────────────────────────────────────────────────────────────────
# Helper decorators / wrappers
# ──────────────────────────────────────────────────────────────────────────────

def safe_db_call(fn: F) -> F:
    """
    Decorator that wraps a DB-touching function and catches *only* DB-level errors.
    Logs the error and re-raises as RuntimeError so callers know the DB call failed.

    Usage::

        @safe_db_call
        def load_memories() -> list:
            ...
    """
    import functools

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except DB_ERRORS as e:
            logger.error(f"[DB] {fn.__name__} failed — {type(e).__name__}: {e}")
            raise RuntimeError(f"DB operation '{fn.__name__}' failed") from e

    return wrapper  # type: ignore[return-value]


def safe_import(module_name: str, package: Optional[str] = None) -> Any:
    """
    Gracefully import a module; return None and log a warning on failure.

    Args:
        module_name: Fully qualified module name string.
        package:     Optional package context for relative imports.

    Returns:
        Imported module object, or None if import failed.
    """
    import importlib

    try:
        return importlib.import_module(module_name, package=package)
    except IMPORT_ERRORS as e:
        logger.warning(f"[IMPORT] Optional module '{module_name}' not available: {e}")
        return None


def log_and_default(
    exc_types: tuple[Type[Exception], ...],
    default: Any = None,
    label: str = "operation",
) -> Callable[[F], F]:
    """
    Decorator factory: catches *specific* exceptions, logs them, and returns a default value.

    Args:
        exc_types: Tuple of exception classes to catch.
        default:   Value to return when an exception is caught.
        label:     Human-readable label for the log message.

    Usage::

        @log_and_default((ValueError, KeyError), default=[], label="tool_load")
        def load_tools() -> list:
            ...
    """
    import functools

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except exc_types as e:  # type: ignore[misc]
                logger.error(f"[{label.upper()}] {fn.__name__} error ({type(e).__name__}): {e}")
                return default

        return wrapper  # type: ignore[return-value]

    return decorator
