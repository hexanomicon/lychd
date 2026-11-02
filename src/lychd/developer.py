"""Explicit disposable browser fixture; never an alternate production startup.

Run ``python -m lychd.developer --caged`` inside the development image for fresh
terminal-issued credentials. This
composition has no ambient Settings, Rune discovery, database, or execution
capability. Its records are synthetic and disappear when the process exits.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import signal
import sys
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar import Litestar
from litestar.exceptions import PermissionDeniedException
from pydantic import SecretStr

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings, SettingsSnapshot
from lychd.config.settings.server import validate_local_access_password
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from lychd.interface.server_policy import ServerRuntimePolicyError, validate_server_environment
from lychd.interface.web.altar_services import AltarServices, build_altar_services

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler

    from lychd.config.settings.observability import SnapshotSourceSettings
    from lychd.domain.cortex.substrate import RunSubstrate
    from lychd.domain.orchestration.actuator import TransitionIntent
    from lychd.domain.orchestration.containment import SoftActivationRecord

_BROWSER_PORT = 5173
_LISTENER_PORT = 8000
_LISTENER_HOST = "0.0.0.0"  # noqa: S104 -- internal image listener behind loopback host publication
_SYNTHETIC = "SYNTHETIC developer fixture: no graph, model, or host execution."
_READ_ONLY = "The synthetic developer fixture is read-only; mutations and execution are unavailable."


async def refuse_fixture_mutations(connection: ASGIConnection[Any, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Refuse unsafe methods after normal security checks and before admission."""
    if connection.scope["type"] == "http" and connection.scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
        raise PermissionDeniedException(detail=_READ_ONLY)


async def allow_fixture_canvas_authoring(
    connection: ASGIConnection[Any, Any, Any, Any], handler: BaseRouteHandler
) -> None:
    """Admit only Canvas/Project authoring into disposable memory, never execution.

    Normal authentication, Origin, CSRF and handler scopes still run. This guard
    is selected only by the explicit developer authoring profile.
    """
    path = connection.scope["path"]
    if (
        connection.scope["type"] == "http"
        and connection.scope["method"] == "POST"
        and (
            path
            in {
                "/api/v1/canvas/projects",
                "/api/v1/canvas/workspace/bootstrap",
                "/api/v1/canvas/documents/validate",
                "/api/v1/canvas/review",
            }
            or (path.startswith("/api/v1/atlas/projects/") and path.endswith("/changes"))
        )
    ):
        return
    await refuse_fixture_mutations(connection, handler)


class RefusingQueue:
    """Named, inert collaborator; no queue operation represents execution or health."""

    def __init__(self, name: str) -> None:
        """Retain the queue name for honest unavailable diagnostics."""
        self.name = name

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        _ = job_or_func, kwargs
        raise RuntimeError(_READ_ONLY)

    async def job(self, job_key: str, /) -> None:
        _ = job_key
        raise RuntimeError(_READ_ONLY)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = job, error, ttl
        raise RuntimeError(_READ_ONLY)

    async def info(self) -> dict[str, Any]:
        message = f"Fixture queue {self.name!r} is unavailable."
        raise RuntimeError(message)


class RefusingRuntimeActuator:
    """The fixture possesses no host transition authority."""

    async def apply(self, intent: TransitionIntent) -> None:
        _ = intent
        raise RuntimeError(_READ_ONLY)


class RefusingSoftActivationGuard:
    """Avoid host storage while refusing every fixture activation attempt."""

    def assert_clear(self) -> None:
        """There are no runtime effects to recover in this disposable fixture."""

    def arm(self, record: SoftActivationRecord) -> None:
        _ = record
        raise RuntimeError(_READ_ONLY)

    def clear(self, record: SoftActivationRecord) -> None:
        _ = record
        raise RuntimeError(_READ_ONLY)


async def _seed(services: AltarServices) -> None:
    """Retain one sample without Run submission, graph execution, or model history."""
    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEvent, RunEventKind
    from lychd.domain.cortex.runs import RunStatus
    from lychd.domain.web.schemas import BridgeTurn

    session = await services.bridge_sessions.create_session(title="SYNTHETIC: read-only developer fixture")
    workflow = services.workflows.default
    run = await services.ledger.create(
        Intent(session_id=session.id, prompt=_SYNTHETIC, source="bridge"),
        workflow_name=workflow.name,
        pattern_manifest=workflow.manifest.snapshot(),
        queue_name="runs",
        priority=70,
    )
    await services.ledger.set_status(run.run_id, RunStatus.FAILED, error=_SYNTHETIC)
    # Orb deliberately omits raw logs/prompts. A progress label stays visible
    # when the Run is opened directly, without adding invented execution events.
    await services.ledger.append_event(RunEvent(run_id=run.run_id, seq=0, kind=RunEventKind.STATUS, data=_SYNTHETIC))
    await services.ledger.append_event(
        RunEvent(run_id=run.run_id, seq=1, kind=RunEventKind.DONE, data=RunStatus.FAILED.value)
    )
    await services.bridge_sessions.add_turn(
        session.id,
        BridgeTurn(role="user", content="SYNTHETIC sample: inspect this Run in Orb and Loom.", run_id=run.run_id),
    )
    await services.bridge_sessions.settle_agent_turn(
        session.id,
        BridgeTurn(
            role="agent", content=f"{_SYNTHETIC} The failed status is sample data.", run_id=run.run_id, state="failed"
        ),
        new_messages=[],
    )


def _published_substrate() -> RunSubstrate | None:
    """Observe the process seat without acquiring another application's authority."""
    from lychd.domain.cortex.substrate import get_run_substrate

    try:
        return get_run_substrate()
    except RuntimeError:
        return None


def _require_unpublished_substrate() -> None:
    if _published_substrate() is not None:
        message = "The developer fixture requires an unpublished Run substrate."
        raise RuntimeError(message)


@dataclass(frozen=True, slots=True)
class DeveloperFixture:
    """One explicit composition, captured before common HTTP assembly runs."""

    settings: Settings
    extensions: AssembledExtensions
    runes: RuneRegistry
    canvas_authoring: bool = False

    @asynccontextmanager
    async def lifespan(self, app: Litestar) -> AsyncGenerator[None]:
        """Warm, seed, publish whole, withdraw, and close even after startup failure."""
        from lychd.domain.cortex.substrate import reset_run_substrate, set_run_substrate

        # Queue status uses a process-global seat. Refuse coexistence rather than
        # letting this fixture read another application's queue authority.
        _require_unpublished_substrate()
        services: AltarServices | None = None
        failure: BaseException | None = None
        try:
            services = build_altar_services(
                queues={name: RefusingQueue(name) for name in ("runs", "rites")},
                runes=self.runes,
                settings=self.settings,
                runtime_actuator=RefusingRuntimeActuator(),
                soft_activation_guard=RefusingSoftActivationGuard(),
            )
            # No declarations means no factories, runtime probes, or host reads.
            services.registry.ensure_loaded()
            await _seed(services)
            _require_unpublished_substrate()
            set_run_substrate(services.substrate)
            app.state.services = services
            yield
        except BaseException as exc:
            failure = exc
            raise
        finally:
            if services is not None and app.state.get("services") is services:
                app.state.pop("services", None)
            if services is not None and _published_substrate() is services.substrate:
                reset_run_substrate()
            if services is not None:
                try:
                    await services.aclose()
                except BaseException as close_error:
                    if failure is not None:
                        message = "Fixture startup/use and closure failed."
                        raise BaseExceptionGroup(message, [failure, close_error]) from None
                    raise


def create_developer_app(
    *,
    access_password: SecretStr,
    signing_key: SecretStr,
    listener_port: int = 8000,
    canvas_authoring: bool = False,
    browser_port: int = _BROWSER_PORT,
    observation_sources: tuple[SnapshotSourceSettings, ...] = (),
) -> Litestar:
    """Build protected read surfaces from explicit inputs without ambient discovery.

    Optional structural observation sources are deliberately selected by the caller;
    they grant no execution and do not make the synthetic Bridge Run real.
    """
    from lychd.app import AppInit
    from lychd.interface.server_policy import evaluate_server_runtime_policy

    evaluate_server_runtime_policy(environment={}, default_listener_port=listener_port)
    validate_local_access_password(access_password)
    if not signing_key.get_secret_value():
        msg = "The developer fixture requires an explicit signing key."
        raise ValueError(msg)
    settings = SettingsSnapshot(
        payload=json.dumps(
            {
                "server": {
                    # The configured public authority is Vite; the actual TCP
                    # listener is admitted separately by the common Host policy.
                    "port": browser_port,
                    "database": {"profile": "memory"},
                    "web": {"allowed_cors_origins": [f"http://127.0.0.1:{browser_port}"]},
                },
                "extensions": {"builtins": [], "crypt": []},
                "observability": {"sources": [source.model_dump(mode="json") for source in observation_sources]},
            }
        ),
        web_access_password=access_password,
        web_secret_key=signing_key,
    ).materialize()
    fixture = DeveloperFixture(
        settings=settings,
        extensions=AssembledExtensions(context=ExtensionManager(builtins=(), crypt=()).assemble()),
        runes=RuneRegistry(()),
        canvas_authoring=canvas_authoring,
    )
    return Litestar(plugins=[AppInit(listener_port=listener_port, fixture=fixture)])


async def _serve(app: Litestar, *, host: str, port: int) -> None:
    """Own the real lifespan so startup and closure failures reach the launcher."""
    from granian.constants import Interfaces
    from granian.server.embed import Server

    server = Server(app, address=host, port=port, interface=Interfaces.ASGINL, runtime_threads=1, blocking_threads=1)
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, server.stop)
    try:
        # Granian's embedded ASGI protocol only logs shutdown.failed. Keep one
        # explicit lifespan owner and use its no-lifespan ASGI worker instead.
        async with app.lifespan():
            await server.serve()
    finally:
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(signum)


def main(arguments: Sequence[str] | None = None) -> None:
    """Issue fresh fixture-only credentials to the invoking terminal and start one listener."""
    arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--caged", action="store_true", required=True, help="Run inside the development image")
    parser.add_argument(
        "--canvas-authoring", action="store_true", help="Allow disposable in-memory Canvas and project edits only"
    )
    options = parser.parse_args(arguments)
    try:
        validate_server_environment(os.environ)
    except ServerRuntimePolicyError as exc:
        parser.error(str(exc))
    password = SecretStr(secrets.token_urlsafe(32))
    app = create_developer_app(
        access_password=password,
        signing_key=SecretStr(secrets.token_urlsafe(48)),
        listener_port=_LISTENER_PORT,
        canvas_authoring=options.canvas_authoring,
    )
    # This explicit terminal result is the only credential output. It is never a
    # structured diagnostic, environment variable, URL, browser asset, or file.
    profile = "Canvas authoring" if options.canvas_authoring else "read-only"
    sys.stdout.write(
        f"SYNTHETIC {profile} fixture. No execution or durable state.\nUsername: magus\nPassword: {password.get_secret_value()}\n"
    )
    sys.stdout.flush()
    asyncio.run(_serve(app, host=_LISTENER_HOST, port=_LISTENER_PORT))


if __name__ == "__main__":
    main()
