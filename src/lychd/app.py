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
        from litestar.config.response_cache import ResponseCacheConfig
        from litestar.contrib.sqlalchemy.plugins import SQLAlchemyPlugin
        from litestar.plugins.problem_details import ProblemDetailsPlugin
        from litestar.plugins.structlog import StructlogPlugin
        from litestar.stores.memory import MemoryStore
        from litestar.stores.registry import StoreRegistry
        from litestar_granian import GranianPlugin
        from litestar_saq import SAQPlugin
        from litestar_vite import VitePlugin

        from lychd.__about__ import __version__ as current_version
        from lychd.config.components import (
            cors_config,
            csrf_config,
            db_config,
            log_config,
            problem_details_config,
            saq_config,
            template_config,
            vite_config,
        )
        from lychd.config.constants import CACHE_EXPIRATION
        from lychd.config.telemetry import TelemetryPlugin
        from lychd.lib.exceptions import ApplicationError

        settings = get_settings()

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
                VitePlugin(config=vite_config),
                SQLAlchemyPlugin(config=db_config),
                SAQPlugin(config=saq_config),
                StructlogPlugin(config=log_config),
                ProblemDetailsPlugin(config=problem_details_config),
                TelemetryPlugin(otel_endpoint=f"{settings.phoenix.url}/v1/traces"),
            ],
        )

        # CORS
        app_config.cors_config = cors_config
        app_config.csrf_config = csrf_config
        # HTML templates
        app_config.template_config = template_config

        # --- 6. Memory Stores ---
        app_config.stores = StoreRegistry(default_factory=lambda _: MemoryStore())
        app_config.exception_handlers = {
            ApplicationError: exception_to_http_response,
            RepositoryError: exception_to_http_response,
        }
        app_config.response_cache_config = ResponseCacheConfig(default_expiration=CACHE_EXPIRATION)

        # Routers

        # Dependencies

        # Signatures

        # Shutdownappend

        # Listeners

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
        from lychd.cli.commands import bind_quadlets, init_codex

        cli.add_command(init_codex)
        cli.add_command(bind_quadlets)


def create_app() -> Litestar:
    """Central Application Factory for both Server and CLI contexts.

    Instantiates the Litestar application, delegating context-specific logic
    (server plugin setup vs. CLI command injection) to the `AppInit` plugin protocol
    implementation.

    Returns:
        Litestar: CLI or fully configured web application

    """
    return Litestar(
        plugins=[AppInit()],
    )
