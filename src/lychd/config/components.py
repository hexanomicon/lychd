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
from lychd.db.engine import get_engine

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
    """Build the Ghoul-queue (SAQ) config: the ``runs`` + ``rites`` queues (A4-U4).

    Topology A (v1, F1 hardening): ``separate_process=False`` on BOTH queues is the
    ONE switch (litestar_saq 0.5.3) that routes each worker through
    ``Worker.on_app_startup`` onto the *web* event loop instead of forking a
    ``multiprocessing.Process``. The in-process ghoul (`perform_run`) and the SSE
    handler therefore share one ``RunEventBus`` — a run's events reach its open
    stream. ``use_server_lifespan=False`` completes the topology: it stops the SAQ
    plugin's ``server_lifespan`` from spawning the (now no-op) forked worker
    processes. No forked workers remain; the substrate is built ONCE in
    ``altar_services_lifespan`` and read from the process memo by `perform_run`.

    ``runs`` carries interactive graph runs; ``rites`` carries background rites.
    Both register `perform_run` so rite-routed intents (`source="rite"` → ``rites``)
    are claimable. ``extra_tasks`` still extends the rite task list (Wave-1 contract).
    """
    rite_tasks = [
        "lychd.ghouls.runs.perform_run",
        "lychd.ghouls.rites.perform_rite",
        "lychd.ghouls.runs.reconcile_runs",
        *extra_tasks,
    ]
    return SAQConfig(
        web_enabled=settings.saq.web_enabled,
        use_server_lifespan=False,  # Topology A: no forked workers — on_app_startup owns the loop.
        queue_configs=[
            QueueConfig(
                name="runs",
                dsn=settings.db.saq_dsn,
                tasks=["lychd.ghouls.runs.perform_run", "lychd.ghouls.runs.reconcile_runs"],
                concurrency=settings.saq.concurrency,
                separate_process=False,  # Topology A: run on the web loop, share the RunEventBus.
                startup=worker_startup,
            ),
            QueueConfig(
                name="rites",
                dsn=settings.db.saq_dsn,
                tasks=rite_tasks,
                concurrency=settings.saq.concurrency,
                separate_process=False,  # Topology A: run on the web loop, share the RunEventBus.
                startup=worker_startup,
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
    """Topology-A worker startup: no per-worker construction (F1/S7).

    Under Topology A the worker runs *in the web process on the web loop*
    (`separate_process=False`), so there are no forked children to build a fresh
    engine/session-factory/extensions for — those live on the shared process and
    the run collaborators are read from the ONE `RunSubstrate` the web lifespan
    (`altar_services_lifespan`) publishes via `set_run_substrate`. `perform_run`
    reads that memo through `_substrate(ctx)`. This hook is retained only as the
    documented seam; it deliberately does nothing.
    """
    _ = ctx
