from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPluginProtocol
from litestar.repository.exceptions import RepositoryError

# Runtime imports: Litestar evaluates the `provide_*` return annotations below at
# app-init to type the injected dependencies, so these must resolve at runtime.
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.extensions.host import AssembledExtensions
from lychd.lib.exceptions import exception_to_http_response

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.datastructures import State


def provide_extensions(state: State) -> AssembledExtensions:
    """Provide the process-wide assembled extensions from app state."""
    return state.extensions


def provide_runes(state: State) -> RuneRegistry:
    """Provide the process-wide validated rune registry from app state."""
    return state.runes


class AppInit(InitPluginProtocol):
    """Configure the server application from side-effect-free component factories."""

    # Pre-declare attributes for memory optimization

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application when run as a web server.

        This hook is triggered by an ASGI server (e.g., Granian) during
        application startup.

        Args:
            app_config (AppConfig): Injected Litestar Configuration object with plugins,routes...

        Returns:
            AppConfig: Fully configured app

        """
        # Lazy import of settings to keep startup fast
        from advanced_alchemy.extensions.litestar.providers import create_service_provider
        from litestar.config.response_cache import ResponseCacheConfig
        from litestar.contrib.sqlalchemy.plugins import SQLAlchemyPlugin
        from litestar.di import Provide
        from litestar.plugins.problem_details import ProblemDetailsPlugin
        from litestar.plugins.structlog import StructlogPlugin
        from litestar.stores.memory import MemoryStore
        from litestar.stores.registry import StoreRegistry
        from litestar_granian import GranianPlugin
        from litestar_saq import SAQPlugin

        from lychd.__about__ import __version__ as current_version
        from lychd.config.components import (
            build_cors_config,
            build_csrf_config,
            build_db_config,
            build_problem_details_config,
            build_saq_config,
            build_structlog_config,
        )
        from lychd.config.constants import CACHE_EXPIRATION
        from lychd.config.runes.registry import load_rune_registry
        from lychd.domain.animation.services.store import SoulstoneRecordService
        from lychd.domain.cortex.services import KarmaService, RunService, StepService
        from lychd.domain.web.contracts import CsrfClientContract
        from lychd.domain.web.services import SessionService
        from lychd.extensions.host import get_extensions
        from lychd.lib.exceptions import ApplicationError

        settings = get_settings()
        extensions = get_extensions()  # THE one assembly for this process
        runes = load_rune_registry(extensions)  # validated TOML instances, loaded once

        app_config.debug = settings.server.web.debug

        app_config.openapi_config = OpenAPIConfig(
            title=settings.server.web.name,
            version=current_version,
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )

        app_config.plugins.extend(
            [
                GranianPlugin(),
                SQLAlchemyPlugin(config=build_db_config(settings)),
                SAQPlugin(config=build_saq_config(settings)),
                StructlogPlugin(config=build_structlog_config(settings)),
                ProblemDetailsPlugin(config=build_problem_details_config(settings)),
            ],
        )

        # CORS / CSRF
        app_config.cors_config = build_cors_config(settings)
        csrf_config = build_csrf_config(settings)
        app_config.csrf_config = csrf_config

        # The Ward (4C-1): stamp every request's connection.user with the settings Sigil
        # so the scope guards can rule. Excludes /_app + /schema (unauthenticated assets).
        from lychd.domain.codex.middleware import sigil_auth_middleware

        app_config.middleware.append(sigil_auth_middleware())

        # --- 6. Memory Stores ---
        app_config.stores = StoreRegistry(default_factory=lambda _: MemoryStore())
        app_config.exception_handlers = {
            ApplicationError: exception_to_http_response,
            RepositoryError: exception_to_http_response,
        }
        app_config.response_cache_config = ResponseCacheConfig(default_expiration=CACHE_EXPIRATION)

        # Routers (core product surfaces)
        from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]

        from lychd.config.constants import PATH_ALTAR_ASSET_DIR
        from lychd.interface.api.orchestrator import OrchestratorController
        from lychd.interface.web import (
            AltarController,
            BridgeController,
            LoomController,
            NexusController,
        )

        app_config.route_handlers.extend(
            [
                create_static_files_router(
                    path="/_app",
                    directories=[PATH_ALTAR_ASSET_DIR],
                    name="altar-assets",
                ),
                OrchestratorController,
                AltarController,
                BridgeController,
                NexusController,
                LoomController,
            ],
        )

        # State: the one assembly + validated runes
        app_config.state.update(
            {
                "extensions": extensions,
                "runes": runes,
                "csrf_contract": CsrfClientContract(
                    cookie_name=csrf_config.cookie_name,
                    header_name=csrf_config.header_name,
                ),
            },
        )

        # Dependencies
        from lychd.interface.web.deps import web_dependencies
        from lychd.interface.web.lifespan import altar_services_lifespan

        app_config.dependencies.update(web_dependencies)
        app_config.dependencies.update(
            {
                "extensions": Provide(provide_extensions, sync_to_thread=False),
                "runes": Provide(provide_runes, sync_to_thread=False),
                "runs_service": create_service_provider(RunService),
                "steps_service": create_service_provider(StepService),
                "sessions_service": create_service_provider(SessionService),
                "karma_service": create_service_provider(KarmaService),
                "soulstone_records_service": create_service_provider(SoulstoneRecordService),
            }
        )
        # The ONE web-layer assembly site: build AltarServices, warm the registry,
        # publish on app.state, drain on shutdown.
        app_config.lifespan.append(altar_services_lifespan)  # pyright: ignore[reportUnknownMemberType]

        return app_config


def create_app() -> Litestar:
    """Create the server application.

    Returns:
        Litestar: Fully configured web application.

    """
    # Get Arize Phoenix Plugin for Tracing
    # Better yet, create a function gathering plugins - in plugin - base.py
    # Call it here and insert into Litestar app

    import os

    granian_workers = os.getenv("GRANIAN_WORKERS")
    if granian_workers not in {None, "", "1"}:
        message = "LychD v1 requires GRANIAN_WORKERS=1; the run event plane is process-local."
        raise RuntimeError(message)

    return Litestar(
        plugins=[AppInit()],
    )
