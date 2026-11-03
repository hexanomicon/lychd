"""Real middleware and shared credential marker around synthetic dictation."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State

from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.interface.web.dictation import DictationController
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.unit.domain.test_dictation_service import request, setup
from tests.web.conftest import AsgiClient

PASSWORD = "dictation-synthetic-test-password-0123456789"  # noqa: S105
AUTH = "Basic " + base64.b64encode(f"magus:{PASSWORD}".encode()).decode()
PATH = "/api/v1/bridge/dictation"


@pytest.fixture
def client() -> AsgiClient:
    service, _adapter = setup()
    access = LocalOperatorAccess(access_password=PASSWORD)
    app = Litestar(
        route_handlers=[DictationController],
        state=State({"services": SimpleNamespace(dictation=service), "local_operator_access": access}),
        middleware=[sigil_auth_middleware(operator_access=access)],
        csrf_config=CSRFConfig(secret=str(uuid4()), cookie_secure=False),
        plugins=[StrictPydanticSchemaPlugin()],
        openapi_config=build_openapi_config(
            title="Dictation isolated contract", version="test", use_handler_docstrings=True
        ),
    )
    client = AsgiClient(app, headers={"authorization": AUTH})
    token = client.get(PATH).cookies["csrftoken"]
    client.headers.update({"cookie": f"csrftoken={token}", "x-csrftoken": token})
    return client


def test_authenticated_discovery_and_no_store(client: AsgiClient) -> None:
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert "no-store" in response.headers["cache-control"]
    assert "endpoint" not in response.text
    assert client.get(PATH, headers={"authorization": ""}).status_code == 401


def test_transcribe_recover_correct_delete(client: AsgiClient) -> None:
    incoming = request().model_dump(mode="json")
    first = client.post(PATH + "/transcribe", json=incoming)
    assert first.status_code == 200
    assert first.json()["original_text"] == "Original words"
    identifier = incoming["attempt_id"]
    assert client.get(f"{PATH}/attempts/{identifier}").json() == first.json()
    correction = client.post(PATH + "/corrections", json={"attempt_id": identifier, "final_text": "Edited"})
    assert correction.json()["original_text"] == "Original words"
    assert len(client.get(PATH + "/corrections").json()) == 1
    assert client.post(f"{PATH}/attempts/{identifier}/delete").json()["status"] == "deleted"
    assert client.get(f"{PATH}/attempts/{identifier}").status_code == 404


def test_origin_csrf_owner_injection_and_size_refused(client: AsgiClient) -> None:
    incoming = request().model_dump(mode="json")
    assert (
        client.post(PATH + "/transcribe", json=incoming, headers={"origin": "https://foreign.invalid"}).status_code
        == 403
    )
    plain = AsgiClient(client.app, headers={"authorization": AUTH})
    assert plain.post(PATH + "/transcribe", json=incoming).status_code == 403
    assert client.post(PATH + "/transcribe", json={**incoming, "owner": "victim"}).status_code == 400
    assert client.post(PATH + "/transcribe", json={**incoming, "audio_base64": "A" * 1_500_000}).status_code == 413


def test_missing_current_access_fails_closed(client: AsgiClient) -> None:
    client.app.state.local_operator_access = None
    assert client.get(PATH).status_code == 403


def test_schema_exposes_canonical_dictation_models(client: AsgiClient) -> None:
    schema = client.get("/schema/openapi.json").json()
    assert PATH + "/transcribe" in schema["paths"]
    assert {"DictationRequest", "DictationResult", "DictationCorrection"} <= set(schema["components"]["schemas"])


def test_read_and_mutation_scopes_are_independent(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.domain.codex.sigil import Sigil

    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil",
        lambda: Sigil(name="reader", scopes=frozenset({"altar:read"})),
    )
    assert client.get(PATH).status_code == 200
    assert client.post(PATH + "/transcribe", json=request().model_dump(mode="json")).status_code == 403
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil",
        lambda: Sigil(name="writer", scopes=frozenset({"runs:submit"})),
    )
    assert client.get(PATH).status_code == 403
    assert client.post(PATH + "/transcribe", json=request().model_dump(mode="json")).status_code == 403


def test_revoked_during_read_does_not_release_result(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = client.app.state.services.dictation
    original = service.get_result

    async def revoked_read(owner: str, attempt_id: object) -> object:
        result = await original(owner, attempt_id)
        client.app.state.local_operator_access.revoke()
        return result

    monkeypatch.setattr(service, "get_result", revoked_read)
    assert client.get(f"{PATH}/attempts/{request().attempt_id}").status_code == 403
