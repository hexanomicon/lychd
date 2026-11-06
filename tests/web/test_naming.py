"""Authenticated naming acceptance and current authority without model effects."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State

from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil
from lychd.domain.naming import InMemoryNamingStore, NamingSnapshot, NamingStoreError
from lychd.interface.web.naming import NamingController
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.web.conftest import AsgiClient

PASSWORD = "naming-synthetic-test-password-0123456789"  # noqa: S105
AUTH = "Basic " + base64.b64encode(f"magus:{PASSWORD}".encode()).decode()
ROOT = "/api/v1/altar/naming"
PAYLOAD: dict[str, Any] = {
    "expected_revision": 0,
    "names": {
        "magus_name": "Zenith Runeweaver",
        "primus_name": "Liora Moonwhisper",
        "magus_origin": "manual",
        "primus_origin": "self_chosen",
    },
}


@pytest.fixture
def client() -> AsgiClient:
    access = LocalOperatorAccess(access_password=PASSWORD)
    app = Litestar(
        route_handlers=[NamingController],
        state=State({"services": SimpleNamespace(naming=InMemoryNamingStore()), "local_operator_access": access}),
        middleware=[sigil_auth_middleware(operator_access=access)],
        csrf_config=CSRFConfig(secret=str(uuid4()), cookie_secure=False),
        plugins=[StrictPydanticSchemaPlugin()],
        openapi_config=build_openapi_config(title="Naming", version="test", use_handler_docstrings=True),
    )
    client = AsgiClient(app, headers={"authorization": AUTH})
    token = client.get(ROOT).cookies["csrftoken"]
    client.headers.update({"cookie": f"csrftoken={token}", "x-csrftoken": token})
    return client


def test_suggestions_inert_acceptance_and_stale_conflict(client: AsgiClient) -> None:
    assert client.get(ROOT).json() == {"current": None}
    assert len(client.get(ROOT + "/suggestions").json()["names"]) == 6
    assert client.get(ROOT).json() == {"current": None}
    first = client.request("PUT", ROOT, json=PAYLOAD)
    assert first.status_code == 200
    assert "no-store" in first.headers["cache-control"]
    assert first.json()["current"] == {"revision": 1, **PAYLOAD["names"]}
    assert client.request("PUT", ROOT, json=PAYLOAD).status_code == 409
    assert client.get(ROOT).json() == first.json()
    second = client.request("PUT", ROOT, json={**PAYLOAD, "expected_revision": 1})
    assert second.status_code == 200
    assert second.json()["current"]["revision"] == 2


def test_auth_csrf_injection_bounds_and_scope(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.get(ROOT, headers={"authorization": ""}).status_code == 401
    assert client.request("PUT", ROOT, json={**PAYLOAD, "owner": "victim"}).status_code == 400
    assert client.request("PUT", ROOT, json={**PAYLOAD, "expected_revision": True}).status_code == 400
    assert client.request("PUT", ROOT, json={**PAYLOAD, "expected_revision": "0"}).status_code == 400
    assert client.request("PUT", ROOT, json={**PAYLOAD, "expected_revision": 0.0}).status_code == 400
    plain = AsgiClient(client.app, headers={"authorization": AUTH})
    assert plain.request("PUT", ROOT, json=PAYLOAD).status_code == 403
    assert client.request("PUT", ROOT, json=PAYLOAD, headers={"origin": "https://foreign.invalid"}).status_code == 403
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil",
        lambda: Sigil(name="reader", scopes=frozenset({"altar:read"})),
    )
    assert client.get(ROOT).status_code == 200
    assert client.request("PUT", ROOT, json=PAYLOAD).status_code == 403


def test_current_authority_after_read_and_private_failures(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def revoke(owner: str) -> NamingSnapshot | None:
        assert owner
        client.app.state.local_operator_access.revoke()
        return None

    monkeypatch.setattr(client.app.state.services.naming, "get", revoke)
    assert client.get(ROOT).status_code == 403


def test_storage_unavailable_and_schema(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    schema = client.get("/schema/openapi.json").json()
    assert {"NamingAcceptance", "NamingView", "NamingSnapshot", "PersonalNames", "NameSuggestions"} <= set(
        schema["components"]["schemas"]
    )

    async def fail(owner: str) -> NamingSnapshot | None:
        assert owner
        msg = "naming_storage_failure"
        raise NamingStoreError(msg)

    monkeypatch.setattr(client.app.state.services.naming, "get", fail)
    assert client.get(ROOT).status_code == 503
    client.app.state.services.naming = None
    assert client.get(ROOT).status_code == 503
