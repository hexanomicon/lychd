import sys
from functools import lru_cache
from typing import Any

import structlog
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig
from litestar.logging.config import (
    LoggingConfig,
    StructLoggingConfig,
    default_logger_factory,
    default_structlog_processors,
    default_structlog_standard_lib_processors,
)
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.problem_details import ProblemDetailsConfig
from litestar.plugins.sqlalchemy import AlembicAsyncConfig
from litestar.plugins.structlog import StructlogConfig
from litestar.template import TemplateConfig
from litestar_saq import QueueConfig, SAQConfig
from litestar_vite import ViteConfig

from lychd.config import get_settings
from lychd.config.constants import HTML_TEMPLATE_DIR

# This call will now create the singleton on its first run
settings = get_settings()


async def worker_startup(ctx: dict[str, Any]) -> None:
    """Initialize the worker process.

    This function is called when a worker starts. It initializes the DB engine
    and session factory for tasks.
    """
    # Use the factory from settings to ensure identical DB config (JSONB optimization) but get new engine due to process forking via multiprocessing
    engine = settings.db.get_engine(force_new=True)

    # Create the session factory
    session_factory = SQLAlchemyAsyncConfig(engine_instance=engine).create_session_maker()

    # Inject into context
    ctx["db_session_factory"] = session_factory
    ctx["db_engine"] = engine


# --- Shutdown Function ---
# Cleans up the database connection when the worker stops.
async def worker_shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("db_engine")
    if engine:
        await engine.dispose()


problem_details_config = ProblemDetailsConfig(enable_for_all_http_exceptions=True)

compression_config = CompressionConfig(backend="gzip")

cors_config = CORSConfig(allow_origins=settings.app.allowed_cors_origins)

csrf_config = CSRFConfig(
    secret=settings.app.secret_key.get_secret_value(),
    cookie_name=settings.app.csrf_cookie_name,
    cookie_secure=settings.app.csrf_cookie_secure,
)

# --- Template Engine Config ---
# This tells Litestar where to find your HTML files for SSR with HTMX.
template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=HTML_TEMPLATE_DIR))

# Vite asset bundler for htmx alpine tailwind
vite_config = ViteConfig(
    bundle_dir=settings.vite.bundle_dir,
    resource_dir=settings.vite.resource_dir,
    use_server_lifespan=settings.vite.use_server_lifespan,
    dev_mode=settings.vite.dev_mode,
    hot_reload=settings.vite.hot_reload,
    port=settings.vite.port,
    host=settings.vite.host,
)

# --- The Phylactery (Database) Config ---
db_config = SQLAlchemyAsyncConfig(
    engine_instance=settings.db.get_engine(),
    before_send_handler="autocommit",
    session_config=AsyncSessionConfig(expire_on_commit=False),
    alembic_config=AlembicAsyncConfig(
        version_table_name=settings.db.migration_ddl_version_table,
        script_config=settings.db.migration_config,
        script_location=settings.db.migration_path,
    ),
)

# --- The Ghoul Queue (SAQ) Config ---
saq_config = SAQConfig(
    # Plugin-level settings
    web_enabled=settings.saq.web_enabled,
    worker_processes=settings.saq.processes,
    use_server_lifespan=settings.saq.use_server_lifespan,
    queue_configs=[
        QueueConfig(
            name="rites",
            dsn=settings.db.url.replace("+asyncpg", ""),
            tasks=["lychd.ghouls.rites.perform_rite"],
            concurrency=settings.saq.concurrency,
            # MOVED HERE: The worker for this specific queue needs the DB connection
            startup=worker_startup,
            shutdown=worker_shutdown,
        ),
    ],
)

# --- Advanced Structlog Configuration (Corrected) ---


@lru_cache
def _is_tty() -> bool:
    # The more robust check from the reference project
    return bool(sys.stderr.isatty() or sys.stdout.isatty())


# Determine if logs should be rendered as JSON
_render_as_json = settings.log.json_format or not _is_tty()

# 1. Processors for logs created directly with structlog
_structlog_default_processors = default_structlog_processors(as_json=_render_as_json)
_structlog_default_processors.insert(1, structlog.processors.EventRenamer("message"))

# 2. Processors for logs captured from the standard library (e.g., SQLAlchemy)
_structlog_standard_lib_processors = default_structlog_standard_lib_processors(as_json=_render_as_json)
_structlog_standard_lib_processors.insert(1, structlog.processors.EventRenamer("message"))

log_config = StructlogConfig(
    # THIS IS THE MIDDLEWARE YOU CORRECTLY IDENTIFIED WAS MISSING
    middleware_logging_config=LoggingMiddlewareConfig(
        request_log_fields=settings.log.request_fields,
        response_log_fields=settings.log.response_fields,
    ),
    structlog_logging_config=StructLoggingConfig(
        log_exceptions="always",
        processors=_structlog_default_processors,  # Use the first processor list
        logger_factory=default_logger_factory(as_json=_render_as_json),
        standard_lib_logging_config=LoggingConfig(
            root={"level": settings.log.level.upper(), "handlers": ["console"]},
            formatters={
                "standard": {
                    "()": "structlog.stdlib.ProcessorFormatter",
                    "processors": _structlog_standard_lib_processors,  # Use the second list here
                },
            },
            # We now use 'console' as the handler name, but the reference
            # uses 'queue_listener'. This is just a name, but we will
            # stick to 'console' for clarity as we are logging to the terminal.
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
                # You can add your pydantic_ai logger here as well
                "pydantic_ai": {
                    "propagate": False,
                    "level": settings.log.pydantic_ai_level,
                    "handlers": ["console"],
                },
            },
        ),
    ),
)
