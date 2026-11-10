from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr

from lychd.system.services import deployment_acceptance as acceptance
from lychd.system.services.local_access import LocalAccess

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_credential_stays_in_memory_and_evidence_contains_only_statuses(mocker: MockerFixture) -> None:
    password = "private-password-never-in-evidence"  # noqa: S105 - inert custody fixture
    mocker.patch.object(
        acceptance, "load_local_access", return_value=LocalAccess("http://127.0.0.1:7134/", SecretStr(password))
    )
    bodies: dict[str, dict[str, object]] = {
        "/api/v1/altar/status": {"pending_consents": 0},
        "/orchestrator/status": {"active_capabilities": [], "all_capabilities": []},
        "/orchestrator/queues": {"queues": [{"name": "runs", "active": 0}, {"name": "rites", "active": 0}]},
    }

    def http(url: str, token: str | None = None) -> tuple[int, bytes]:
        import base64

        decoded = base64.b64decode(token).decode() if token else ""
        if not decoded.endswith(password):
            return 401, b""
        return 200, json.dumps(next(value for path, value in bodies.items() if url.endswith(path))).encode()

    mocker.patch.object(acceptance, "observe_local_http", side_effect=http)
    checks = acceptance.api_checks()
    assert all(check["ok"] for check in checks)
    assert password not in json.dumps(checks)
    assert "Authorization" not in json.dumps(checks)


def test_secret_source_exception_is_not_rendered(mocker: MockerFixture) -> None:
    mocker.patch.object(acceptance, "load_local_access", side_effect=ValueError("secret-password"))
    checks = acceptance.api_checks()
    assert checks == [{"name": "api.access", "ok": False, "detail": "local_credential_unavailable"}]


def test_nonloopback_target_is_refused_before_any_http(mocker: MockerFixture) -> None:
    wire = mocker.patch.object(acceptance, "_http_get_async")
    assert acceptance.observe_local_http("http://example.com/", "credential") == (0, b"")
    wire.assert_not_called()


def test_redirect_never_carries_credential_to_another_listener(mocker: MockerFixture) -> None:
    import httpx2

    from lychd.lib.http import create_async_http_client

    visits: list[httpx2.Request] = []

    def endpoint(request: httpx2.Request) -> httpx2.Response:
        visits.append(request)
        return httpx2.Response(302, headers={"Location": "http://unadmitted.invalid/sink"})

    def client_factory(**_kwargs: Any) -> httpx2.AsyncClient:
        return create_async_http_client(timeout=1.0, transport=httpx2.MockTransport(endpoint))

    mocker.patch("lychd.lib.http.create_async_http_client", side_effect=client_factory)
    status, _body = acceptance.observe_local_http(
        "http://127.0.0.1:7134/api/v1/altar/status", "synthetic-in-memory-token"
    )
    assert status == 302
    assert len(visits) == 1
    assert visits[0].url.host == "127.0.0.1"


def test_oversized_response_refuses_without_exposing_body(mocker: MockerFixture) -> None:
    import httpx2

    from lychd.lib.http import create_async_http_client

    def endpoint(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"x" * (2 * 1024 * 1024))

    def client_factory(**_kwargs: Any) -> httpx2.AsyncClient:
        return create_async_http_client(timeout=1.0, transport=httpx2.MockTransport(endpoint))

    mocker.patch("lychd.lib.http.create_async_http_client", side_effect=client_factory)
    assert acceptance.observe_local_http("http://127.0.0.1:7134/api/v1/altar/status") == (0, b"")
