"""Actual auth/CSRF/schema routes around synthetic private lexicon stores."""

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
from lychd.domain.codex.sigil import Sigil
from lychd.domain.dictation_lexicon import MemoryDictationLexiconStore
from lychd.domain.dictation_lexicon_service import DictationLexiconService
from lychd.domain.dictation_store import MemoryDictationStore
from lychd.interface.web.dictation_lexicon import DictationLexiconController
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.web.conftest import AsgiClient

PASSWORD = "lexicon-synthetic-test-password-0123456789"  # noqa: S105
AUTH = "Basic " + base64.b64encode(f"magus:{PASSWORD}".encode()).decode()
ROOT = "/api/v1/bridge/dictation"
PAYLOAD = {"language": "en", "heard": "lich", "replacement": "LychD", "approved": True}


@pytest.fixture
def client() -> AsgiClient:
    service = DictationLexiconService(store=MemoryDictationLexiconStore(), attempts=MemoryDictationStore())
    access = LocalOperatorAccess(access_password=PASSWORD)
    app = Litestar(
        route_handlers=[DictationLexiconController],
        state=State({"services": SimpleNamespace(dictation_lexicon=service), "local_operator_access": access}),
        middleware=[sigil_auth_middleware(operator_access=access)],
        csrf_config=CSRFConfig(secret=str(uuid4()), cookie_secure=False),
        plugins=[StrictPydanticSchemaPlugin()],
        openapi_config=build_openapi_config(
            title="Lexicon isolated contract", version="test", use_handler_docstrings=True
        ),
    )
    client = AsgiClient(app, headers={"authorization": AUTH})
    token = client.get(ROOT + "/lexicon").cookies["csrftoken"]
    client.headers.update({"cookie": f"csrftoken={token}", "x-csrftoken": token})
    return client


def test_approval_replay_conflict_delete_and_no_store(client: AsgiClient) -> None:
    first = client.post(ROOT + "/lexicon", json=PAYLOAD)
    assert first.status_code == 200
    assert "no-store" in first.headers["cache-control"]
    assert client.post(ROOT + "/lexicon", json=PAYLOAD).json() == first.json()
    assert client.post(ROOT + "/lexicon", json={**PAYLOAD, "replacement": "different"}).status_code == 409
    assert client.get(ROOT + "/lexicon").json() == [first.json()]
    assert client.post(f"{ROOT}/lexicon/{first.json()['id']}/delete").json()["deleted"] is True
    assert client.get(ROOT + "/lexicon").json() == []


def test_approval_and_suggestion_injection_and_unsafe_origins_refused(client: AsgiClient) -> None:
    assert client.get(ROOT + "/lexicon", headers={"authorization": ""}).status_code == 401
    assert client.post(ROOT + "/lexicon", json={**PAYLOAD, "approved": False}).status_code == 400
    assert client.post(ROOT + "/lexicon", json={**PAYLOAD, "owner": "victim"}).status_code == 400
    assert (
        client.post(ROOT + "/lexicon", json=PAYLOAD, headers={"origin": "https://foreign.invalid"}).status_code == 403
    )
    plain = AsgiClient(client.app, headers={"authorization": AUTH})
    assert plain.post(ROOT + "/lexicon", json=PAYLOAD).status_code == 403
    attempt = {"attempt_id": str(uuid4())}
    assert client.post(ROOT + "/suggestions", json=attempt).status_code == 404
    assert client.post(ROOT + "/suggestions", json={**attempt, "original_text": "forged"}).status_code == 400
    assert client.post(ROOT + "/suggestions", json={**attempt, "language": "en"}).status_code == 400
    assert client.post(ROOT + "/lexicon", json={**PAYLOAD, "heard": "x" * 5000}).status_code == 413


def test_scopes_and_current_authority_required(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil",
        lambda: Sigil(name="reader", scopes=frozenset({"altar:read"})),
    )
    assert client.get(ROOT + "/lexicon").status_code == 200
    assert client.post(ROOT + "/lexicon", json=PAYLOAD).status_code == 403
    client.app.state.local_operator_access = None
    assert client.get(ROOT + "/lexicon").status_code == 403


def test_revocation_during_read_refuses_disclosure(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = client.app.state.services.dictation_lexicon
    original = service.list_rules

    async def revoked(owner: str) -> object:
        result = await original(owner)
        client.app.state.local_operator_access.revoke()
        return result

    monkeypatch.setattr(service, "list_rules", revoked)
    assert client.get(ROOT + "/lexicon").status_code == 403


def test_generated_schema_has_canonical_models(client: AsgiClient) -> None:
    schema = client.get("/schema/openapi.json").json()
    assert {
        "DictationLexiconRuleRequest",
        "DictationLexiconRule",
        "DictationSuggestionRequest",
        "DictationSuggestion",
    } <= set(
        schema["components"]["schemas"],
    )
    assert set(schema["components"]["schemas"]["DictationSuggestionRequest"]["properties"]) == {"attempt_id"}
