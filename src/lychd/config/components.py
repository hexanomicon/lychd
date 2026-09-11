"""Side-effect-free factory functions that assemble Litestar plugin/app config.

Importing this module performs NO I/O and resolves NO secrets: every config
object is produced by a ``build_*`` factory called from the application assembly root
(``AppInit.on_app_init``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
)
from litestar.config.allowed_hosts import AllowedHostsConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar_saq import SAQConfig

from lychd.config.constants import (
    DB_MIGRATION_VERSION_TABLE,
    PATH_MIGRATION_CONFIG,
    PATH_MIGRATION_DIR,
)
from lychd.config.logging import build_log_config, should_render_as_json
from lychd.db.authority import RuntimeQueueConfig
from lychd.db.engine import get_engine
from lychd.db.factory import database_saq_dsn

if TYPE_CHECKING:
    from litestar.plugins.structlog import StructlogConfig

    from lychd.config.settings.root import Settings


def build_db_config(settings: Settings) -> SQLAlchemyAsyncConfig:
    """Build the Phylactery (database) plugin config from the process engine."""
    return SQLAlchemyAsyncConfig(
        engine_instance=get_engine(settings.server.database),
        before_send_handler="autocommit",
        session_config=AsyncSessionConfig(expire_on_commit=False),
        alembic_config=AlembicAsyncConfig(
            version_table_name=DB_MIGRATION_VERSION_TABLE,
            script_config=str(PATH_MIGRATION_CONFIG),
            script_location=str(PATH_MIGRATION_DIR),
        ),
    )


def build_saq_config(settings: Settings) -> SAQConfig:
    """Build interactive Run and background Rite queues on the web event loop.

    ``separate_process=False`` keeps workers on the same loop as the SSE event bus.
    ``use_server_lifespan=False`` disables the plugin's process-server lifespan;
    application startup connects the queues and shutdown drains workers before
    shared services close. Both queues execute ``perform_run``; startup owns
    reconciliation because it supplies the boot cutoff.
    """
    if settings.server.jobs.admin_ui_enabled:
        msg = "The raw SAQ administrative UI is disabled; use the curated Altar queue projection."
        raise ValueError(msg)
    return SAQConfig(
        web_enabled=False,
        web_path=settings.server.jobs.admin_ui_path,
        use_server_lifespan=False,
        queue_configs=[
            RuntimeQueueConfig(
                name="runs",
                dsn=database_saq_dsn(settings.server.database, runtime=True),
                tasks=["lychd.ghouls.runs.perform_run"],
                concurrency=settings.server.jobs.interactive_concurrency,
                separate_process=False,
            ),
            RuntimeQueueConfig(
                name="rites",
                dsn=database_saq_dsn(settings.server.database, runtime=True),
                tasks=["lychd.ghouls.runs.perform_run"],
                concurrency=settings.server.jobs.background_concurrency,
                separate_process=False,
            ),
        ],
    )


def build_structlog_config(settings: Settings) -> StructlogConfig:
    """Build the structured-logging configuration."""
    return build_log_config(
        render_as_json=should_render_as_json(settings),
        settings=settings,
    )


def build_cors_config(settings: Settings) -> CORSConfig:
    """Build fail-closed CORS from explicitly configured loopback origins."""
    return CORSConfig(allow_origins=settings.server.web.allowed_cors_origins)


def build_allowed_hosts_config(
    settings: Settings,
    *,
    listener_port: int | None = None,
) -> AllowedHostsConfig:
    """Admit literal loopback authorities on configured and actual listener ports."""
    ports = tuple(dict.fromkeys((settings.server.port, listener_port)))
    loopback_hosts = ("127.0.0.1", "localhost", "[::1]")
    return AllowedHostsConfig(
        allowed_hosts=[
            host
            for name in loopback_hosts
            for host in (name, *(f"{name}:{port}" for port in ports if port is not None))
        ],
        www_redirect=False,
    )


def build_csrf_config(settings: Settings) -> CSRFConfig:
    """Build the CSRF config from the app signing key."""
    if settings.server.web.secret_key is None:
        msg = "Required application signing key is unavailable in Settings."
        raise ValueError(msg)
    return CSRFConfig(
        secret=settings.server.web.secret_key.get_secret_value(),
        cookie_name=settings.server.web.csrf_cookie_name,
        cookie_secure=settings.server.web.csrf_cookie_secure,
    )
