"""Real HTTP composition around inert, current-owner machine stop admission.

The production configuration uses explicit in-memory inputs and controlled
publication; this proves HTTP admission, not deployed host startup or shutdown.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from litestar import Litestar, Request, post
from pydantic import SecretStr

from lychd.app import AppInit
from lychd.config.constants import STOP_ADMISSION_LAUNCHER_PROFILE, STOP_ADMISSION_PATH
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings, SettingsSnapshot
from lychd.developer import create_developer_app
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from lychd.interface.api.lifecycle import StopAdmissionState
from lychd.system.operator.admission import MAX_ADMISSION_BODY_BYTES, StopAdmissionProtocol
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.types import Receive, Scope, Send

_URL = "http://127.0.0.1:8000" + STOP_ADMISSION_PATH


@post(STOP_ADMISSION_PATH + "-other")
async def ordinary_mutation() -> dict[str, bool]:
    return {"ok": True}


def _inputs() -> tuple[Settings, AssembledExtensions, RuneRegistry]:
    settings = SettingsSnapshot(
        payload=json.dumps(
            {
                "server": {"port": 8000, "database": {"profile": "memory"}},
                "extensions": {"builtins": [], "crypt": []},
            }
        ),
        web_access_password=SecretStr(TEST_ACCESS_PASSWORD),
        web_secret_key=SecretStr("synthetic-lifecycle-signing-key"),
    ).materialize()
    extensions = AssembledExtensions(context=ExtensionManager(builtins=(), crypt=()).assemble())
    return settings, extensions, RuneRegistry(())


def _app(monkeypatch: pytest.MonkeyPatch) -> Litestar:
    """Keep AppInit's real security stack and replace only effectful composition."""
    inputs = _inputs()

    def composition(_self: AppInit, _config: AppConfig) -> tuple[Settings, AssembledExtensions, RuneRegistry]:
        return inputs

    async def no_machine_identity(request: Request[Any, Any, Any]) -> None:
        if request.scope["path"] == STOP_ADMISSION_PATH:
            assert "user" not in request.scope
            assert "auth" not in request.scope

    monkeypatch.setattr(AppInit, "_configure_composition", composition)
    return Litestar(
        plugins=[AppInit(listener_port=8000)],
        route_handlers=[ordinary_mutation],
        before_request=no_machine_identity,
    )


def _publish_owned_native(app: Litestar) -> None:
    admission: StopAdmissionState = app.state.stop_admission
    admission.arm_native_launcher()
    admission.publish()


def _client(app: Litestar) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),  # pyright: ignore[reportArgumentType] - ASGI typing differs
        base_url="http://127.0.0.1:8000",
        follow_redirects=False,
    )


def _pending() -> tuple[StopAdmissionProtocol, httpx.Request]:
    protocol = StopAdmissionProtocol(TEST_ACCESS_PASSWORD)
    return protocol, protocol.request(_URL, "host-attested-generation")


def _forbidden(*_args: Any, **_kwargs: Any) -> Any:
    pytest.fail("Machine admission reached an unrelated authentication or effect owner")


@pytest.mark.asyncio
async def test_real_http_stack_returns_unchanged_signed_ack_without_browser_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.domain.codex import middleware
    from lychd.domain.cortex.engine import RunEngine
    from lychd.domain.orchestration.manager import OrchestratorManager
    from lychd.system.operator.control import OperatorControlService
    from lychd.system.services import runtime
    from lychd.system.services.lifecycle.lock import LifecycleLock

    app = _app(monkeypatch)
    _publish_owned_native(app)
    for owner, name in (
        (LocalOperatorAccess, "authenticate"),
        (middleware, "default_local_sigil"),
        (RunEngine, "submit"),
        (RunEngine, "cancel"),
        (OrchestratorManager, "request_transition"),
        (OperatorControlService, "execute"),
        (LifecycleLock, "__enter__"),
        (runtime, "wait_for_host_reactor_idle"),
    ):
        monkeypatch.setattr(owner, name, _forbidden)
    protocol, pending = _pending()
    async with _client(app) as client:
        for _ in range(2):
            response = await client.send(pending)
            assert response.status_code == 200
            assert "www-authenticate" not in response.headers
            assert "set-cookie" not in response.headers
            assert TEST_ACCESS_PASSWORD not in response.text
            protocol.verify_reply(pending, response)
        schema = await client.get("/schema/openapi.json")
        assert STOP_ADMISSION_PATH not in schema.json()["paths"]
    assert "services" not in app.state


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["unarmed", "environment", "unpublished", "withdrawn", "republished", "revoked"])
async def test_current_owner_and_runtime_publication_gate_ack(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    if state == "environment":
        monkeypatch.setenv("LYCHD_MODE", "uncaged")
    app = _app(monkeypatch)
    admission: StopAdmissionState = app.state.stop_admission
    assert admission.launcher_profile is None
    if state not in {"unarmed", "environment"}:
        admission.arm_native_launcher()
    if state != "unpublished":
        admission.publish()
    if state in {"withdrawn", "republished"}:
        admission.withdraw()
    if state == "republished":
        admission.publish()
        assert admission.launcher_profile is None
    if state == "revoked":
        app.state.local_operator_access.revoke()
    _protocol, pending = _pending()
    async with _client(app) as client:
        response = await client.send(pending)
    assert response.status_code == 403
    assert "signature" not in response.headers
    assert "www-authenticate" not in response.headers
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_bad_hmac_never_consults_current_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    pending = StopAdmissionProtocol("different-synthetic-password-0123456789").request(_URL, "generation")
    monkeypatch.setattr(LocalOperatorAccess, "current", _forbidden)
    async with _client(app) as client:
        response = await client.send(pending)
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "basic-only",
        "basic-and-signature",
        "same-origin",
        "foreign-origin",
        "query",
        "encoded-path",
        "method",
        "operation",
    ],
)
async def test_machine_port_refuses_other_authentication_targets_and_operations(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    _protocol, pending = _pending()
    if change == "basic-only":
        pending = httpx.Request("POST", _URL, headers={"authorization": TEST_AUTHORIZATION})
    elif change == "basic-and-signature":
        pending.headers["authorization"] = TEST_AUTHORIZATION
    elif change in {"same-origin", "foreign-origin"}:
        pending.headers["origin"] = "http://127.0.0.1:8000" if change == "same-origin" else "https://evil.example"
    elif change == "query":
        pending.url = httpx.URL(_URL + "?operation=system-stop")
    elif change == "encoded-path":
        pending.url = httpx.URL(_URL.replace("operator", "%6fperator"))
    elif change == "method":
        pending.method = "PUT"
    else:
        body = json.loads(pending.content)
        body["operation"] = "system-restart"
        pending = httpx.Request("POST", _URL, content=json.dumps(body).encode(), headers=pending.headers)
    async with _client(app) as client:
        response = await client.send(pending)
    assert response.status_code in {401, 405}
    assert "www-authenticate" not in response.headers
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header", ["host", "content-type", "content-digest", "content-length", "signature", "signature-input"]
)
async def test_duplicate_raw_critical_headers_reach_protocol_and_refuse(
    monkeypatch: pytest.MonkeyPatch, header: str
) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    _protocol, pending = _pending()
    headers = [*pending.headers.raw, (header.encode(), pending.headers[header].encode())]
    pending = httpx.Request("POST", _URL, content=pending.content, headers=headers)
    async with _client(app) as client:
        response = await client.send(pending)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_host_boundary_and_csrf_bypass_are_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    _protocol, pending = _pending()
    pending.headers["host"] = "evil.example"
    async with _client(app) as client:
        assert (await client.send(pending)).status_code == 400
        ordinary = await client.post(STOP_ADMISSION_PATH + "-other", headers={"authorization": TEST_AUTHORIZATION})
        assert ordinary.status_code == 403
        assert "CSRF" in ordinary.json()["detail"]
        anonymous = await client.post(STOP_ADMISSION_PATH + "-other")
        assert anonymous.status_code == 401
        assert "www-authenticate" in anonymous.headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_path",
    [None, b"/api/v1/%6fperator/stop-admission", b"/api/v1/operator/./stop-admission"],
)
async def test_raw_asgi_target_requires_original_exact_path(
    monkeypatch: pytest.MonkeyPatch, raw_path: bytes | None
) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    _protocol, pending = _pending()
    monkeypatch.setattr(StopAdmissionProtocol, "admit", _forbidden)

    async def original_path_scope(scope: Scope, receive: Receive, send: Send) -> None:
        wire_scope = cast("dict[str, object]", scope)
        if raw_path is None:
            wire_scope.pop("raw_path", None)
        else:
            wire_scope["raw_path"] = raw_path
        await app(scope, receive, send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=original_path_scope),  # pyright: ignore[reportArgumentType] - ASGI typing differs
        follow_redirects=False,
    ) as client:
        response = await client.send(pending)
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert "signature" not in response.headers


@pytest.mark.asyncio
async def test_raw_body_limit_precedes_protocol_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    _publish_owned_native(app)
    monkeypatch.setattr(StopAdmissionProtocol, "admit", _forbidden)

    async def chunks() -> AsyncIterator[bytes]:
        yield b"x" * MAX_ADMISSION_BODY_BYTES
        yield b"x"
        pytest.fail("Oversized request continued reading its body")

    async with _client(app) as client:
        response = await client.post(STOP_ADMISSION_PATH, content=chunks())
    assert response.status_code == 413
    assert "www-authenticate" not in response.headers


@pytest.mark.asyncio
async def test_real_developer_fixture_never_publishes_machine_admission() -> None:
    app = create_developer_app(
        access_password=SecretStr(TEST_ACCESS_PASSWORD), signing_key=SecretStr("synthetic-fixture-signing-key")
    )
    _protocol, pending = _pending()
    async with app.lifespan(), _client(app) as client:
        assert app.state.services is not None
        assert not app.state.stop_admission.production
        assert not app.state.stop_admission.published
        _publish_owned_native(app)
        assert not app.state.stop_admission.published
        assert app.state.stop_admission.launcher_profile is None
        response = await client.send(pending)
    assert response.status_code == 403
    assert "signature" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_recovery", [False, True])
async def test_production_lifespan_publication_and_synchronous_withdrawal(
    monkeypatch: pytest.MonkeyPatch, *, fail_recovery: bool
) -> None:
    from lychd.config.settings import root
    from lychd.domain.cortex import substrate
    from lychd.extensions import host
    from lychd.interface.web import lifespan
    from lychd.system.services import runtime

    app = _app(monkeypatch)
    settings, extensions, _runes = _inputs()
    admission: StopAdmissionState = app.state.stop_admission
    admission.arm_native_launcher()
    published: list[object] = []
    services = SimpleNamespace(
        registry=SimpleNamespace(ensure_loaded=lambda: None),
        substrate=SimpleNamespace(effects=None),
        run_engine=object(),
        aclose=AsyncMock(),
    )

    async def recover(**_kwargs: Any) -> None:
        assert (admission.published, published) == (False, [])
        if fail_recovery:
            message = "required recovery failed"
            raise RuntimeError(message)

    def publish(value: object) -> None:
        assert not admission.published
        assert "services" not in app.state
        published.append(value)

    async def drain(*_args: Any, **_kwargs: Any) -> None:
        assert (admission.published, admission.launcher_profile) == (False, None)
        await asyncio.sleep(0)
        assert (admission.published, admission.launcher_profile) == (False, None)

    monkeypatch.setattr(root, "get_settings", lambda: settings)
    monkeypatch.setattr(host, "get_extensions", lambda: extensions)
    monkeypatch.setattr(runtime, "wait_for_host_reactor_idle", AsyncMock())
    monkeypatch.setattr(lifespan, "_soft_activation_guard_at_startup", object)
    monkeypatch.setattr(lifespan, "_collect_run_queues", Mock(return_value={}))
    monkeypatch.setattr(lifespan, "protect_run_queues", Mock(return_value={}))
    monkeypatch.setattr(lifespan, "connect_run_queues", AsyncMock(return_value=()))
    monkeypatch.setattr(lifespan, "build_altar_services", Mock(return_value=services))
    monkeypatch.setattr(lifespan, "_recover_durable_state", recover)
    for name in ("_start_delivery_relay", "_start_delegate_relay", "_start_consent_relay"):
        monkeypatch.setattr(lifespan, name, Mock(return_value=object()))
    monkeypatch.setattr(substrate, "set_run_substrate", publish)
    monkeypatch.setattr(substrate, "reset_run_substrate", lambda: None)
    monkeypatch.setattr(lifespan, "_drain_process_work", drain)
    monkeypatch.setattr(lifespan, "disconnect_run_queues", AsyncMock())
    if fail_recovery:
        with pytest.raises(RuntimeError, match="required recovery failed"):
            async with lifespan.altar_services_lifespan(app):
                pytest.fail("Failed startup published admission")
        assert not published
    else:
        async with lifespan.altar_services_lifespan(app):
            assert app.state.services is services
            assert published == [services.substrate]
            assert (admission.published, admission.launcher_profile) == (True, STOP_ADMISSION_LAUNCHER_PROFILE)
    assert (admission.published, admission.launcher_profile) == (False, None)
    services.aclose.assert_awaited_once()
