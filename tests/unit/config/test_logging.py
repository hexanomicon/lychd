from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
import structlog

from lychd.config.logging import apply_logging, build_log_config
from lychd.config.settings.root import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_build_log_config_creates_valid_structlog_config() -> None:
    """Verifies build_log_config returns a valid Litestar structlog config with expected setup."""
    config = build_log_config(render_as_json=True)

    assert config.structlog_logging_config is not None
    assert config.structlog_logging_config.standard_lib_logging_config is not None

    stdlib_config = config.structlog_logging_config.standard_lib_logging_config

    # Verify our specific loggers are configured and have expected properties
    assert "granian.access" in stdlib_config.loggers
    assert stdlib_config.loggers["granian.access"]["propagate"] is False
    assert "_granian" in stdlib_config.loggers

    assert "sqlalchemy.engine" in stdlib_config.loggers
    assert "sqlalchemy.pool" in stdlib_config.loggers
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
    assert "message=" not in captured.err

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


def test_direct_structlog_honors_the_shared_level(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI/service Structlog calls use the configured filtering wrapper."""
    apply_logging(force_json=False)

    logger = structlog.get_logger("lychd.test.direct")
    logger.debug("filtered direct message")
    logger.info("visible direct message")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "visible direct message" in captured.err
    assert "filtered direct message" not in captured.err
    assert "message=" not in captured.err


def test_direct_json_structlog_preserves_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Semantic diagnostics stay on stderr beside machine-readable CLI output."""
    apply_logging(force_json=True)

    structlog.get_logger("lychd.test.direct-json").info(
        "direct json event",
        target="system",
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    record = json.loads(captured.err)
    assert record["message"] == "direct json event"
    assert record["target"] == "system"


def test_logging_bootstrap_survives_invalid_operator_settings(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Help and recovery verbs retain a default logger when settings cannot load."""
    mocker.patch(
        "lychd.config.settings.root.get_settings",
        side_effect=ValueError("malformed operator configuration"),
    )

    apply_logging(force_json=False)
    structlog.get_logger("lychd.test.bootstrap").info("bootstrap logger ready")

    captured = capsys.readouterr()
    assert "bootstrap logger ready" in captured.out + captured.err


def test_log_builder_uses_the_composition_owned_settings(
    mocker: MockerFixture,
) -> None:
    settings = Settings()
    settings.server.logging.level = "ERROR"
    global_loader = mocker.patch(
        "lychd.config.settings.root.get_settings",
        side_effect=AssertionError("global settings must not be reloaded"),
    )

    config = build_log_config(render_as_json=True, settings=settings)

    stdlib = config.structlog_logging_config.standard_lib_logging_config
    assert stdlib is not None
    assert stdlib.root["level"] == "ERROR"
    global_loader.assert_not_called()
