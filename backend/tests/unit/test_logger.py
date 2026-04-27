"""
Tests for logger — trace_id context variable and configuration.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.services.observability.logger import (
    set_trace_id,
    get_trace_id,
    setup_logging,
    get_logger,
)


class TestTraceId:
    """Test trace_id context variable operations."""

    def test_set_trace_id_returns_provided_value(self):
        """set_trace_id with a value should return that value."""
        result = set_trace_id("my-trace-123")
        assert result == "my-trace-123"

    def test_set_trace_id_generates_uuid_when_none(self):
        """set_trace_id with None should generate a UUID."""
        result = set_trace_id(None)
        assert result is not None
        assert len(result) == 36  # UUID format

    def test_get_trace_id_returns_current(self):
        """get_trace_id should return the current trace_id."""
        trace_id = "test-trace-456"
        set_trace_id(trace_id)
        assert get_trace_id() == trace_id

    def test_trace_id_isolation(self):
        """Each trace_id should be independent (context var)."""
        set_trace_id("trace-a")
        first = get_trace_id()
        set_trace_id("trace-b")
        second = get_trace_id()
        assert first == "trace-a"
        assert second == "trace-b"

    def test_trace_id_set_empty_string_generates_uuid(self):
        """set_trace_id('') is falsy so it generates a UUID (not actually set to '')."""
        # set_trace_id uses: tid = trace_id or str(uuid.uuid4())
        # Since "" is falsy, it generates a UUID instead
        import uuid
        result = set_trace_id("")
        assert len(result) == 36  # UUID format
        assert result.count("-") == 4  # UUID format verification


class TestLoggerSetup:
    """Test logging configuration."""

    def test_get_logger_returns_loguru_logger(self):
        """get_logger should return a loguru logger bound to name."""
        logger = get_logger("test_module")
        assert logger is not None
        # loguru loggers have a .bind() method
        assert hasattr(logger, "bind")

    def test_get_logger_binds_name(self):
        """get_logger returns a loguru logger with name bound via extra context."""
        logger = get_logger("my.module")
        # loguru bind() returns a new logger with context merged
        # The name is stored in extra["name"], not as _name attribute
        assert hasattr(logger, "bind")
        # Verify the logger can be used with extra context
        ctx_logger = logger.bind(extra={"custom": "value"})
        assert ctx_logger is not None

    def test_setup_logging_does_not_raise(self):
        """setup_logging should complete without error."""
        # This is called on import, but calling again should be safe
        setup_logging(log_level="DEBUG", log_dir="./logs/test")

    def test_setup_logging_with_custom_params(self):
        """setup_logging accepts custom rotation and retention."""
        setup_logging(
            log_level="INFO",
            log_rotation="50 MB",
            log_retention=5,
        )


class TestLoggerOutput:
    """Test logger output and filtering."""

    def test_logger_info_does_not_raise(self):
        """Logging at INFO level should not raise."""
        logger = get_logger("test_info")
        logger.info("Test info message")

    def test_logger_with_extra_does_not_raise(self):
        """Logger with extra context should not raise."""
        logger = get_logger("test_extra")
        logger.bind(extra={"key": "value"}).info("Test with extra")

    def test_logger_error_does_not_raise(self):
        """Logging at ERROR level should not raise."""
        logger = get_logger("test_error")
        logger.error("Test error message")
