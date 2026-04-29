"""App config objects assembled from settings."""

from typing import Any

from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig
from litestar.plugins.problem_details import ProblemDetailsConfig
from litestar.plugins.sqlalchemy import AlembicAsyncConfig
from litestar.plugins.structlog import StructlogConfig
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
from lychd.config.settings import Settings, get_settings
from lychd.db.factory import create_db_engine

settings: Settings = get_settings()
_db_engine_instance: Any = None


def get_db_engine(*, force_new: bool = False) -> Any:
    """Get or create the global database engine instance."""
    global _db_engine_instance
    if _db_engine_instance is None or force_new:
        _db_engine_instance = create_db_engine(settings.db)
    return _db_engine_instance


structlog_config: StructlogConfig = build_log_config(render_as_json=should_render_as_json())


async def worker_startup(ctx: dict[str, Any]) -> None:
    """Initialize the worker process.

    This function is called when a worker starts. It initializes the DB engine
    and session factory for tasks.
    """
    # Use the factory to get a fresh engine due to process forking via multiprocessing
    engine = create_db_engine(settings.db)

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
    secret=settings.app.secret_key,
    cookie_name=settings.app.csrf_cookie_name,
    cookie_secure=settings.app.csrf_cookie_secure,
)

# --- Template Engine Config ---
# This tells Litestar where to find your HTML files for SSR with HTMX.
template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=PATH_HTML_TEMPLATE_DIR))

# Vite asset bundler for htmx alpine tailwind
vite_config = ViteConfig(
    bundle_dir=PATH_VITE_BUNDLE_DIR,
    resource_dir=PATH_VITE_RESOURCE_DIR,
    use_server_lifespan=settings.vite.use_server_lifespan,
    dev_mode=settings.vite.dev_mode,
    hot_reload=settings.vite.hot_reload,
    port=settings.vite.port,
    host=settings.vite.host,
)

# --- The Phylactery (Database) Config ---
db_config = SQLAlchemyAsyncConfig(
    engine_instance=get_db_engine(),
    before_send_handler="autocommit",
    session_config=AsyncSessionConfig(expire_on_commit=False),
    alembic_config=AlembicAsyncConfig(
        version_table_name=DB_MIGRATION_VERSION_TABLE,
        script_config=str(PATH_MIGRATION_CONFIG),
        script_location=str(PATH_MIGRATION_DIR),
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
