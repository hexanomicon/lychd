from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import CLIPluginProtocol, InitPluginProtocol
from litestar.repository.exceptions import RepositoryError

from lychd.config.settings import get_settings
from lychd.lib.exceptions import exception_to_http_response

if TYPE_CHECKING:
    from click import Group
    from litestar.config.app import AppConfig
    from litestar.datastructures import State

    from lychd.config.runes.registry import RuneRegistry
    from lychd.extensions.host import AssembledExtensions


def provide_extensions(state: State) -> AssembledExtensions:
    """Provide the process-wide assembled extensions from app state."""
    return state.extensions


def provide_runes(state: State) -> RuneRegistry:
    """Provide the process-wide validated rune registry from app state."""
    return state.runes


class AppInit(InitPluginProtocol, CLIPluginProtocol):
    """A plugin that is a protocol mixin that orchestrates application initialization.

    Acts as a central hub for configuration in different contexts:
    - Server
    - CLI
    """

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
        from litestar.plugins.htmx import HTMXPlugin
        from litestar.plugins.problem_details import ProblemDetailsPlugin
        from litestar.plugins.structlog import StructlogPlugin
        from litestar.stores.memory import MemoryStore
        from litestar.stores.registry import StoreRegistry
        from litestar_granian import GranianPlugin
        from litestar_saq import SAQPlugin
        from litestar_vite import VitePlugin

        from lychd.__about__ import __version__ as current_version
        from lychd.config.components import (
            build_cors_config,
            build_csrf_config,
            build_db_config,
            build_problem_details_config,
            build_saq_config,
            build_structlog_config,
            build_template_config,
            build_vite_config,
        )
        from lychd.config.constants import CACHE_EXPIRATION
        from lychd.config.runes.registry import load_rune_registry
        from lychd.domain.animation.services.store import SoulstoneRecordService
        from lychd.domain.cortex.services import KarmaService, RunService, StepService
        from lychd.domain.web.services import SessionService
        from lychd.extensions.host import get_extensions
        from lychd.lib.exceptions import ApplicationError

        settings = get_settings()
        extensions = get_extensions()  # THE one assembly for this process
        runes = load_rune_registry(extensions)  # validated TOML instances, loaded once

        app_config.debug = settings.app.debug

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.name,
            version=current_version,
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )

        app_config.plugins.extend(
            [
                GranianPlugin(),
                VitePlugin(config=build_vite_config(settings)),
                SQLAlchemyPlugin(config=build_db_config(settings)),
                SAQPlugin(config=build_saq_config(settings)),
                StructlogPlugin(config=build_structlog_config(settings)),
                ProblemDetailsPlugin(config=build_problem_details_config(settings)),
                HTMXPlugin(),
            ],
        )

        # CORS / CSRF / HTML templates
        app_config.cors_config = build_cors_config(settings)
        app_config.csrf_config = build_csrf_config(settings)
        app_config.template_config = build_template_config(settings)

        # --- 6. Memory Stores ---
        app_config.stores = StoreRegistry(default_factory=lambda _: MemoryStore())
        app_config.exception_handlers = {
            ApplicationError: exception_to_http_response,
            RepositoryError: exception_to_http_response,
        }
        app_config.response_cache_config = ResponseCacheConfig(default_expiration=CACHE_EXPIRATION)

        # Routers (core product surfaces)
        from lychd.interface.api.orchestrator import OrchestratorController
        from lychd.interface.web import (
            AltarController,
            BridgeController,
            LoomController,
            NexusController,
        )

        app_config.route_handlers.extend(
            [
                OrchestratorController,
                AltarController,
                BridgeController,
                NexusController,
                LoomController,
            ],
        )

        # State: the one assembly + validated runes
        app_config.state.update({"extensions": extensions, "runes": runes})

        # Dependencies
        from lychd.interface.web.deps import build_web_singletons, web_dependencies

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
        # Kept until Agent 2's DI rework lands (web builder removes it later).
        app_config.on_startup.append(build_web_singletons)

        return app_config

    def on_cli_init(self, cli: Group) -> None:
        """Injects custom commands into the CLI.

        Triggered by `litestar_group()` during CLI bootstrap. This hook
        dynamically adds custom project commands (e.g., `init`, `bind`) to
        the main CLI group, making them available to the user.

        Args:
            cli (Group): The default command group

        """
        # Lazy import is CRITICAL here.
        # We don't want to load the whole app just to show --help.
        from lychd.cli.commands import bind_quadlets, init_codex, inspect_animators

        cli.add_command(init_codex)
        cli.add_command(bind_quadlets)
        cli.add_command(inspect_animators)


def create_app() -> Litestar:
    """Central Application Factory for both Server and CLI contexts.

    Instantiates the Litestar application, delegating context-specific logic
    (server plugin setup vs. CLI command injection) to the `AppInit` plugin protocol
    implementation.

    Returns:
        Litestar: CLI or fully configured web application

    """
    # Get Arize Phoenix Plugin for Tracing
    # Better yet, create a function gathering plugins - in plugin - base.py
    # Call it here and insert into Litestar app

    return Litestar(
        plugins=[AppInit()],
    )
