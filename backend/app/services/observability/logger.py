"""
Loguru unified logging configuration with JSON format, rotation, and trace_id support.
"""
from __future__ import annotations

import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger as _loguru_logger

# Async-safe context variable for trace_id
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def set_trace_id(trace_id: str | None = None) -> str:
    """Set trace_id in context. Generates UUID if not provided."""
    tid = trace_id or str(uuid.uuid4())
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Get current trace_id from context."""
    return _trace_id_var.get()


def _inject_trace_id(record: dict) -> None:
    """Inject trace_id into log record extra dict."""
    record["extra"]["trace_id"] = get_trace_id()


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    log_rotation: str = "100 MB",
    log_retention: int = 10,
) -> None:
    """
    Initialize loguru with file sink and optional console output.
    """
    # Remove all existing handlers
    _loguru_logger.remove()

    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Simple text format for console (no trace_id to avoid format issues)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    _loguru_logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        enqueue=False,
    )

    # JSON file sink with trace_id via filter
    def _add_trace_id_filter(record):
        record["extra"]["trace_id"] = get_trace_id()
        return True

    _loguru_logger.add(
        str(log_path / "app_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {extra[trace_id]} | {message}",
        level=log_level,
        rotation=log_rotation,
        retention=log_retention,
        compression="zip",
        enqueue=False,
        filter=_add_trace_id_filter,
    )


def get_logger(name: str):
    """
    Get a logger instance for the given module name.
    """
    return _loguru_logger.bind(name=name)


# Auto-setup on import
_log_level = os.getenv("LOG_LEVEL", "INFO")
_log_dir = os.getenv("LOG_DIR", "./logs")
_log_rotation = os.getenv("LOG_ROTATION", "100 MB")
_log_retention = int(os.getenv("LOG_RETENTION", "10"))

setup_logging(
    log_level=_log_level,
    log_dir=_log_dir,
    log_rotation=_log_rotation,
    log_retention=_log_retention,
)
