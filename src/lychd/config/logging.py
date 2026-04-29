"""Shared stdlib logging and structlog setup for web and CLI."""

from __future__ import annotations

import sys
from functools import lru_cache

import structlog
from litestar.logging.config import (
    LoggingConfig,
    StructLoggingConfig,
    default_logger_factory,
    default_structlog_processors,
    default_structlog_standard_lib_processors,
)
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig
from structlog.typing import Processor

from lychd.config.settings import get_settings

settings = get_settings()


@lru_cache
def _is_tty() -> bool:
    """Return True if stdout or stderr is attached to a terminal."""
    return bool(sys.stderr.isatty() or sys.stdout.isatty())


def should_render_as_json() -> bool:
    """Return JSON mode for the current runtime."""
    if settings.log.json_format is not None:
        return settings.log.json_format
    return not _is_tty()


def build_log_config(*, render_as_json: bool) -> StructlogConfig:
    """Build StructlogConfig for Litestar or direct bootstrap."""
    structlog_processors: list[Processor] = default_structlog_processors(as_json=render_as_json)
    structlog_processors.insert(1, structlog.processors.EventRenamer("message"))

    stdlib_processors: list[Processor] = default_structlog_standard_lib_processors(as_json=render_as_json)
    stdlib_processors.insert(1, structlog.processors.EventRenamer("message"))

    return StructlogConfig(
        middleware_logging_config=LoggingMiddlewareConfig(
            request_log_fields=settings.log.request_fields,
            response_log_fields=settings.log.response_fields,
        ),
        structlog_logging_config=StructLoggingConfig(
            log_exceptions="always",
            processors=structlog_processors,
            logger_factory=default_logger_factory(as_json=render_as_json),
            standard_lib_logging_config=LoggingConfig(
                root={"level": settings.log.level.upper(), "handlers": ["console"]},
                formatters={
                    "standard": {
                        "()": "structlog.stdlib.ProcessorFormatter",
                        "processors": stdlib_processors,
                    },
                },
                handlers={
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "standard",
                    },
                },
                loggers={
                    "granian.access": {
                        "propagate": False,
                        "level": settings.log.granian_level,
                        "handlers": ["console"],
                    },
                    "saq": {
                        "propagate": False,
                        "level": settings.log.saq_level,
                        "handlers": ["console"],
                    },
                    "sqlalchemy.engine": {
                        "propagate": False,
                        "level": settings.log.sqlalchemy_level,
                        "handlers": ["console"],
                    },
                    "pydantic_ai": {
                        "propagate": False,
                        "level": settings.log.pydantic_ai_level,
                        "handlers": ["console"],
                    },
                },
            ),
        ),
    )


def apply_logging(*, force_json: bool | None = None) -> None:
    """Apply stdlib logging and structlog to the current process."""
    render_as_json = force_json if force_json is not None else should_render_as_json()
    config = build_log_config(render_as_json=render_as_json)
    structlog_config = config.structlog_logging_config
    stdlib_config = structlog_config.standard_lib_logging_config
    if stdlib_config is not None:
        stdlib_config.configure()

    structlog_config.configure()
