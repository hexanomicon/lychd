"""Side-effect-free factory functions that assemble Litestar plugin/app config.

Importing this module performs NO I/O and resolves NO secrets: every config
object is produced by a ``build_*`` factory called from the composition root
(``AppInit.on_app_init``) or from a SAQ worker startup hook.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig
from litestar.plugins.problem_details import ProblemDetailsConfig
from litestar.plugins.sqlalchemy import AlembicAsyncConfig
from litestar.template import TemplateConfig
from litestar_saq import QueueConfig, SAQConfig
from litestar_vite import ViteConfig

from lychd.config.constants import (
    DB_MIGRATION_VERSION_TABLE,
    PATH_HTML_TEMPLATE_DIR,
    PATH_MIGRATION_CONFIG,
    PATH_MIGRATION_DIR,
    PATH_VITE_BUNDLE_DIR,
    PATH_VITE_RESOURCE_DIR,
)
from lychd.config.logging import build_log_config, should_render_as_json
from lychd.config.settings import get_settings
from lychd.db.engine import get_engine, get_session_factory

if TYPE_CHECKING:
    from litestar.plugins.structlog import StructlogConfig

    from lychd.config.settings import Settings


def build_db_config(settings: Settings) -> SQLAlchemyAsyncConfig:
    """Build the Phylactery (database) plugin config from the process engine."""
    return SQLAlchemyAsyncConfig(
        engine_instance=get_engine(settings.db),
        before_send_handler="autocommit",
        session_config=AsyncSessionConfig(expire_on_commit=False),
        alembic_config=AlembicAsyncConfig(
            version_table_name=DB_MIGRATION_VERSION_TABLE,
            script_config=str(PATH_MIGRATION_CONFIG),
            script_location=str(PATH_MIGRATION_DIR),
        ),
    )


def build_saq_config(settings: Settings, *, extra_tasks: Sequence[str] = ()) -> SAQConfig:
    """Build the Ghoul-queue (SAQ) config. ``extra_tasks`` extends core rite tasks."""
    tasks = ["lychd.ghouls.rites.perform_rite", *extra_tasks]
    return SAQConfig(
        web_enabled=settings.saq.web_enabled,
        worker_processes=settings.saq.processes,
        use_server_lifespan=settings.saq.use_server_lifespan,
        queue_configs=[
            QueueConfig(
                name="rites",
                dsn=settings.db.saq_dsn,
                tasks=tasks,
                concurrency=settings.saq.concurrency,
                startup=worker_startup,
                shutdown=worker_shutdown,
            ),
        ],
    )


def build_vite_config(settings: Settings) -> ViteConfig:
    """Build the Vite asset-bundler config."""
    return ViteConfig(
        bundle_dir=PATH_VITE_BUNDLE_DIR,
        resource_dir=PATH_VITE_RESOURCE_DIR,
        use_server_lifespan=settings.vite.use_server_lifespan,
        dev_mode=settings.vite.dev_mode,
        hot_reload=settings.vite.hot_reload,
        port=settings.vite.port,
        host=settings.vite.host,
    )


def build_structlog_config(settings: Settings) -> StructlogConfig:  # noqa: ARG001
    """Build the Scrying (structlog) config."""
    return build_log_config(render_as_json=should_render_as_json())


def build_template_config(settings: Settings) -> TemplateConfig[JinjaTemplateEngine]:  # noqa: ARG001
    """Build the Jinja HTML template config for SSR + HTMX."""
    return TemplateConfig(engine=JinjaTemplateEngine(directory=PATH_HTML_TEMPLATE_DIR))


def build_cors_config(settings: Settings) -> CORSConfig:
    """Build the CORS config from allowed origins."""
    return CORSConfig(allow_origins=settings.app.allowed_cors_origins)


def build_csrf_config(settings: Settings) -> CSRFConfig:
    """Build the CSRF config from the app signing key."""
    return CSRFConfig(
        secret=settings.app.secret_key,
        cookie_name=settings.app.csrf_cookie_name,
        cookie_secure=settings.app.csrf_cookie_secure,
    )


def build_compression_config(settings: Settings) -> CompressionConfig:  # noqa: ARG001
    """Build the gzip compression config."""
    return CompressionConfig(backend="gzip")


def build_problem_details_config(settings: Settings) -> ProblemDetailsConfig:  # noqa: ARG001
    """Build the RFC-9457 problem-details config."""
    return ProblemDetailsConfig(enable_for_all_http_exceptions=True)


async def worker_startup(ctx: dict[str, Any]) -> None:
    """Initialize a forked SAQ worker process.

    Forked workers cannot reuse the parent's asyncpg connections, so a fresh
    engine is built via the process-memoized ``db.engine`` seat. Workers also
    receive the assembled extensions so they see the same surface as the app.
    """
    from lychd.extensions.host import get_extensions

    engine = get_engine(get_settings().db, fresh=True)
    ctx["db_engine"] = engine
    ctx["db_session_factory"] = get_session_factory()
    ctx["extensions"] = get_extensions()


async def worker_shutdown(ctx: dict[str, Any]) -> None:
    """Dispose the worker's database engine on shutdown."""
    engine = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
