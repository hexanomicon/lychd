from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import RepositoryError
from litestar import Litestar
from litestar.plugins import InitPluginProtocol

# Runtime imports: Litestar evaluates the `provide_*` return annotations below at
# app-init to type the injected dependencies, so these must resolve at runtime.
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.extensions.host import AssembledExtensions
from lychd.interface.server_policy import (
    ServerRuntimePolicyError,
    evaluate_server_runtime_policy,
)
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from lychd.lib.exceptions import exception_to_http_response

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.datastructures import State

    from lychd.config.settings.root import Settings
    from lychd.developer import DeveloperFixture


def provide_extensions(state: State) -> AssembledExtensions:
    """Provide the process-wide assembled extensions from app state."""
    return state.extensions


def provide_runes(state: State) -> RuneRegistry:
    """Provide the process-wide validated rune registry from app state."""
    return state.runes


class AppInit(InitPluginProtocol):
    """Configure the server application from side-effect-free component factories."""

    __slots__ = ("fixture", "listener_port")

    def __init__(self, *, listener_port: int | None = None, fixture: DeveloperFixture | None = None) -> None:
        """Select production or the explicit fixture before any ambient configuration."""
        self.listener_port = listener_port
        self.fixture = fixture

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
        from litestar.di import Provide
        from litestar.plugins.structlog import StructlogPlugin
        from litestar.stores.memory import MemoryStore
        from litestar.stores.registry import StoreRegistry

        from lychd.__about__ import __version__ as current_version
        from lychd.config.components import (
            build_allowed_hosts_config,
            build_cors_config,
            build_csrf_config,
            build_structlog_config,
        )
        from lychd.config.constants import CACHE_EXPIRATION
        from lychd.domain.web.contracts import CsrfClientContract
        from lychd.lib.exceptions import ApplicationError

        app_config.plugins.append(StrictPydanticSchemaPlugin())
        settings, extensions, runes = self._configure_composition(app_config)

        app_config.debug = settings.server.web.debug

        app_config.openapi_config = build_openapi_config(
            title=settings.server.web.name,
            version=current_version,
            use_handler_docstrings=True,
        )

        app_config.plugins.append(StructlogPlugin(config=build_structlog_config(settings)))

        # Loopback browser boundary / CSRF
        app_config.allowed_hosts = build_allowed_hosts_config(
            settings,
            listener_port=self.listener_port,
        )
        app_config.cors_config = build_cors_config(settings)
        csrf_config = build_csrf_config(settings)
        app_config.csrf_config = csrf_config

        # Local credential possession precedes the fixed Sigil; remote Ward is not delivered.
        from lychd.domain.codex.local_access import LocalOperatorAccess
        from lychd.domain.codex.middleware import sigil_auth_middleware
        from lychd.interface.api.lifecycle import StopAdmissionState, stop_admission
        from lychd.system.operator.admission import StopAdmissionProtocol

        if settings.server.web.access_password is None:
            msg = "Required local access password is unavailable in Settings."
            raise ValueError(msg)
        access_password = settings.server.web.access_password.get_secret_value()
        operator_access = LocalOperatorAccess(access_password=access_password)
        authentication = operator_access.authenticate(username=b"magus", password=access_password.encode("ascii"))
        if authentication is None:  # pragma: no cover - the owner received this exact credential
            msg = "Required local access authentication is unavailable."
            raise ValueError(msg)
        stop_admission_state = StopAdmissionState(
            protocol=StopAdmissionProtocol(access_password),
            access=operator_access,
            authentication=authentication,
            production=self.fixture is None,
        )
        app_config.middleware.append(
            sigil_auth_middleware(
                operator_access=operator_access,
                allowed_origins=settings.server.web.allowed_cors_origins,
            )
        )

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
        from lychd.interface.api.creation import CreationController
        from lychd.interface.api.orchestrator import OrchestratorController
        from lychd.interface.web import (
            AltarController,
            ArchiveController,
            ArchiveDerivationController,
            AtlasController,
            BridgeController,
            LoomController,
            NexusController,
            OrbController,
        )

        app_config.route_handlers.extend(
            [
                create_static_files_router(
                    path="/_app",
                    directories=[PATH_ALTAR_ASSET_DIR],
                    name="altar-assets",
                ),
                OrchestratorController,
                stop_admission,
                AltarController,
                AtlasController,
                ArchiveController,
                ArchiveDerivationController,
                BridgeController,
                CreationController,
                NexusController,
                LoomController,
                OrbController,
            ],
        )

        # State: the one assembly + validated runes
        app_config.state.update(
            {
                "extensions": extensions,
                "runes": runes,
                "local_operator_access": operator_access,
                "stop_admission": stop_admission_state,
                "csrf_contract": CsrfClientContract(
                    cookie_name=csrf_config.cookie_name,
                    header_name=csrf_config.header_name,
                ),
            },
        )

        # Dependencies
        from lychd.interface.web.deps import web_dependencies

        app_config.dependencies.update(web_dependencies)
        app_config.dependencies.update(
            {
                "extensions": Provide(provide_extensions, sync_to_thread=False),
                "runes": Provide(provide_runes, sync_to_thread=False),
            }
        )

        return app_config

    def _configure_composition(self, app_config: AppConfig) -> tuple[Settings, AssembledExtensions, RuneRegistry]:
        """Select service authority before the shared HTTP configuration."""
        if self.fixture is not None:
            from lychd.developer import refuse_fixture_mutations

            app_config.guards.append(refuse_fixture_mutations)  # pyright: ignore[reportUnknownMemberType]
            app_config.lifespan.append(self.fixture.lifespan)  # pyright: ignore[reportUnknownMemberType]
            return self.fixture.settings, self.fixture.extensions, self.fixture.runes

        from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
        from litestar_saq import SAQPlugin

        from lychd.config.components import build_db_config, build_saq_config
        from lychd.config.runes.registry import load_rune_registry
        from lychd.extensions.host import get_extensions
        from lychd.interface.web.lifespan import altar_services_lifespan

        settings = get_settings()
        extensions = get_extensions()
        runes = load_rune_registry(extensions)
        app_config.plugins.extend(
            [SQLAlchemyPlugin(config=build_db_config(settings)), SAQPlugin(config=build_saq_config(settings))]
        )
        app_config.lifespan.append(altar_services_lifespan)  # pyright: ignore[reportUnknownMemberType]
        return settings, extensions, runes


def create_app() -> Litestar:
    """Create the server application.

    Returns:
        Litestar: Fully configured web application.

    """
    settings = get_settings()
    try:
        policy = evaluate_server_runtime_policy(
            environment=os.environ,
            default_listener_port=settings.server.port,
            argv=sys.argv,
            original_argv=getattr(sys, "orig_argv", ()),
        )
    except ServerRuntimePolicyError as exc:
        raise RuntimeError(str(exc)) from exc
    if policy.listener_port is None:
        message = "LychD could not resolve one effective listener port."
        raise RuntimeError(message)

    return Litestar(
        plugins=[AppInit(listener_port=policy.listener_port)],
    )
