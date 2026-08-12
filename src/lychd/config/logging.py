"""Shared stdlib logging and structlog setup for web and CLI."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

import structlog
from litestar.logging.config import (
    LoggingConfig,
    StructLoggingConfig,
    default_structlog_processors,
    default_structlog_standard_lib_processors,
)
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig
from structlog.typing import Processor

if TYPE_CHECKING:
    from lychd.config.settings.root import Settings
    from lychd.config.settings.server import LoggingSettings


@lru_cache
def _is_tty() -> bool:
    """Return True if stdout or stderr is attached to a terminal."""
    return bool(sys.stderr.isatty() or sys.stdout.isatty())


def should_render_as_json(settings: Settings | None = None) -> bool:
    """Return JSON mode for the current runtime."""
    if settings is None:
        from lychd.config.settings.root import get_settings

        settings = get_settings()
    if settings.server.logging.json_format is not None:
        return settings.server.logging.json_format
    return not _is_tty()


def build_log_config(
    *,
    render_as_json: bool,
    settings: Settings | None = None,
) -> StructlogConfig:
    """Build StructlogConfig for Litestar or direct bootstrap."""
    if settings is None:
        from lychd.config.settings.root import get_settings

        settings = get_settings()
    return _build_log_config(
        settings.server.logging,
        render_as_json=render_as_json,
    )


def _build_log_config(
    settings: LoggingSettings,
    *,
    render_as_json: bool,
) -> StructlogConfig:
    """Build one shared pipeline from an already-owned logging section."""
    structlog_processors: list[Processor] = default_structlog_processors(as_json=render_as_json)
    stdlib_processors: list[Processor] = default_structlog_standard_lib_processors(as_json=render_as_json)
    if render_as_json:
        # Rename immediately before the renderer. Human consoles retain `event`
        # as the primary line instead of degrading it into a `message=` field.
        structlog_processors.insert(-1, structlog.processors.EventRenamer("message"))
        stdlib_processors.insert(-1, structlog.processors.EventRenamer("message"))

    standard_lib_logging_config = LoggingConfig(
        root={"level": settings.level, "handlers": ["console"]},
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
                "level": settings.granian_level,
                "handlers": ["console"],
            },
            "_granian": {
                "propagate": False,
                "level": settings.granian_level,
                "handlers": ["console"],
            },
            "saq": {
                "propagate": False,
                "level": settings.saq_level,
                "handlers": ["console"],
            },
            "sqlalchemy.engine": {
                "propagate": False,
                "level": settings.sqlalchemy_level,
                "handlers": ["console"],
            },
            "sqlalchemy.pool": {
                "propagate": False,
                "level": settings.sqlalchemy_level,
                "handlers": ["console"],
            },
            "pydantic_ai": {
                "propagate": False,
                "level": settings.pydantic_ai_level,
                "handlers": ["console"],
            },
        },
    )
    # Litestar injects an unused queue listener and routes its own logger through
    # it. ``dictConfig`` eagerly starts that listener, so repeated CLI/test/app
    # bootstraps otherwise leak one process-owned thread apiece.
    standard_lib_logging_config.loggers["litestar"]["handlers"] = ["console"]
    standard_lib_logging_config.handlers.pop("queue_listener", None)

    return StructlogConfig(
        middleware_logging_config=LoggingMiddlewareConfig(
            request_log_fields=settings.request_fields,
            response_log_fields=settings.response_fields,
        ),
        structlog_logging_config=StructLoggingConfig(
            log_exceptions="always",
            processors=structlog_processors,
            # Direct Structlog records are diagnostics, never command results.
            # Keep stdout pristine for stable projections such as `status --json`.
            logger_factory=(
                structlog.BytesLoggerFactory(file=sys.stderr.buffer)
                if render_as_json
                else structlog.WriteLoggerFactory(file=sys.stderr)
            ),
            wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[settings.level]),
            standard_lib_logging_config=standard_lib_logging_config,
        ),
    )


def apply_logging(*, force_json: bool | None = None) -> None:
    """Apply shared logging, falling back safely when operator settings are invalid."""
    from lychd.config.settings.root import get_settings

    try:
        settings = get_settings()
    except Exception:  # noqa: BLE001 - help/recovery commands must survive malformed settings
        from lychd.config.settings.server import LoggingSettings

        render_as_json = force_json if force_json is not None else not _is_tty()
        config = _build_log_config(
            LoggingSettings(),
            render_as_json=render_as_json,
        )
    else:
        render_as_json = force_json if force_json is not None else should_render_as_json(settings)
        config = build_log_config(
            render_as_json=render_as_json,
            settings=settings,
        )
    structlog_config = config.structlog_logging_config
    stdlib_config = structlog_config.standard_lib_logging_config
    if stdlib_config is not None:
        stdlib_config.configure()

    structlog_config.configure()
