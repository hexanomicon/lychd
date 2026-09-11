"""Local credential possession, origin refusal, and stream admission."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import Any

import pytest
from litestar import Litestar, Request, get, post
from litestar.config.csrf import CSRFConfig
from litestar.response import ServerSentEvent

from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.middleware import sigil_auth_middleware
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION, AsgiClient


@get("/read", guards=[requires_scopes("altar:read")])
async def read() -> dict[str, bool]:
    """Stand in for a protected application read."""
    return {"ok": True}


@post("/write", guards=[requires_scopes("runs:submit")])
async def write(request: Request[Any, Any, Any]) -> dict[str, str]:
    """Return only the server-owned identity after admission."""
    return {"name": request.user.name}


@get("/events", guards=[requires_scopes("altar:read")])
async def events() -> ServerSentEvent:
    """Stand in for a finite protected SSE response."""

    async def source() -> AsyncIterator[str]:
        yield "synthetic event"

    return ServerSentEvent(source())


@get(["/_app/asset", "/schema/openapi.json", "/_application/private", "/schema-private"])
async def asset() -> dict[str, bool]:
    """Expose exact public paths and lookalikes to test exclusion anchoring."""
    return {"asset": True}


def _client(*, origins: tuple[str, ...] = (), csrf: bool = False) -> AsgiClient:
    app = Litestar(
        route_handlers=[read, write, events, asset],
        middleware=[sigil_auth_middleware(access_password=TEST_ACCESS_PASSWORD, allowed_origins=origins)],
        csrf_config=CSRFConfig(secret=TEST_ACCESS_PASSWORD, cookie_secure=False) if csrf else None,
        openapi_config=None,
    )
    return AsgiClient(app)


@pytest.mark.parametrize(
    "authorization",
    [
        "",
        "Bearer fake",
        "Basic !!!",
        "Basic " + base64.b64encode(b"magus:wrong").decode(),
        "Basic " + base64.b64encode(f"admin:{TEST_ACCESS_PASSWORD}".encode()).decode(),
        "Basic " + base64.b64encode(b"magus").decode(),
        "Basic " + "A" * 2048,
    ],
)
@pytest.mark.parametrize("path", ["/read", "/events"])
def test_protected_reads_and_sse_require_exact_credential(authorization: str, path: str) -> None:
    response = _client().get(path, headers={"authorization": authorization})

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith('Basic realm="LychD local operator"')
    assert TEST_ACCESS_PASSWORD not in response.text


def test_duplicate_authorization_is_refused() -> None:
    response = _client().get(
        "/read", headers=[("authorization", TEST_AUTHORIZATION), ("authorization", TEST_AUTHORIZATION)]
    )
    assert response.status_code == 401


def test_valid_credential_admits_http_and_native_sse_shape() -> None:
    client = _client()
    assert client.get("/read", headers={"authorization": TEST_AUTHORIZATION}).status_code == 200
    response = client.get("/events", headers={"authorization": TEST_AUTHORIZATION})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "synthetic event" in response.text


def test_shared_pod_and_browser_headers_cannot_replace_credential() -> None:
    response = _client().get(
        f"/read?password={TEST_ACCESS_PASSWORD}",
        headers={
            "host": "127.0.0.1:7134",
            "origin": "http://127.0.0.1:7134",
            "sec-fetch-site": "same-origin",
            "x-forwarded-user": "magus",
            "cookie": f"authorization={TEST_AUTHORIZATION}",
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize("origin", ["http://attacker.example", "http://127.0.0.1:5173", "null"])
def test_valid_csrf_form_cannot_override_foreign_origin(origin: str) -> None:
    client = _client(csrf=True)
    token = client.get("/read", headers={"authorization": TEST_AUTHORIZATION}).cookies["csrftoken"]
    response = client.post(
        "/write",
        headers={"authorization": TEST_AUTHORIZATION, "cookie": f"csrftoken={token}", "origin": origin},
        data={"_csrf_token": token},
    )
    assert response.status_code == 403
    assert "Origin" in response.json()["detail"]


@pytest.mark.parametrize("origin", [None, "http://testserver.local", "http://localhost:5173"])
def test_credential_and_csrf_admit_only_same_or_configured_origin(origin: str | None) -> None:
    client = _client(origins=("http://localhost:5173",), csrf=True)
    token = client.get("/read", headers={"authorization": TEST_AUTHORIZATION}).cookies["csrftoken"]
    headers = {"authorization": TEST_AUTHORIZATION, "cookie": f"csrftoken={token}", "x-csrftoken": token}
    if origin is not None:
        headers["origin"] = origin
    response = client.post("/write", headers=headers)
    assert response.status_code == 201
    assert response.json() == {"name": "magus"}


def test_password_cannot_replace_csrf() -> None:
    response = _client(csrf=True).post("/write", headers={"authorization": TEST_AUTHORIZATION})
    assert response.status_code == 403


def test_public_assets_do_not_widen_prefix_exclusion() -> None:
    client = _client()
    assert client.get("/_app/asset").status_code == 200
    assert client.get("/schema/openapi.json").status_code == 200
    assert client.get("/_application/private").status_code == 401
    assert client.get("/schema-private").status_code == 401


def test_missing_startup_credential_has_no_bootstrap_fallback() -> None:
    with pytest.raises(ValueError, match="local access password is unavailable"):
        sigil_auth_middleware(access_password="")
