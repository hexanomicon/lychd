from __future__ import annotations

import json
import logging

import pytest

from lychd.config.logging import apply_logging, build_log_config


def test_build_log_config_creates_valid_structlog_config() -> None:
    """Verifies build_log_config returns a valid Litestar structlog config with expected setup."""
    config = build_log_config(render_as_json=True)

    assert config.structlog_logging_config is not None
    assert config.structlog_logging_config.standard_lib_logging_config is not None

    stdlib_config = config.structlog_logging_config.standard_lib_logging_config

    # Verify our specific loggers are configured and have expected properties
    assert "granian.access" in stdlib_config.loggers
    assert stdlib_config.loggers["granian.access"]["propagate"] is False

    assert "sqlalchemy.engine" in stdlib_config.loggers
    assert "pydantic_ai" in stdlib_config.loggers

    # Verify the root logger uses console handler
    assert stdlib_config.root["handlers"] == ["console"]


def test_actual_logging_output_console(capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies that console (non-JSON) mode produces human-readable text."""
    apply_logging(force_json=False)

    logger = logging.getLogger("lychd.test.console")
    logger.info("Test readable console message")

    captured = capsys.readouterr()

    # Console mode adds log level and formatting, e.g., "[info     ] message='...'"
    assert "Test readable console message" in captured.err
    assert "info" in captured.err.lower()

    # Prove it's not JSON by checking that it fails to parse
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.err.strip())


def test_actual_logging_output_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies that JSON mode produces properly formatted JSON strings."""
    apply_logging(force_json=True)

    logger = logging.getLogger("lychd.test.json")
    logger.info("Test json server message")

    captured = capsys.readouterr()

    # We should be able to parse the output as valid JSON
    log_line = captured.err.strip()

    # Parse the JSON
    log_data = json.loads(log_line)

    # Verify the JSON contains expected structlog keys
    assert log_data["message"] == "Test json server message"
    assert log_data["level"] == "info"
