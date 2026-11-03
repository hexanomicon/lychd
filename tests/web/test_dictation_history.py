"""History routing uses current local authority and the private no-store envelope."""

from datetime import timedelta

import pytest

from lychd.domain.codex.sigil import Sigil
from lychd.domain.dictation import DictationTranscriberError
from tests.unit.domain.test_dictation_history import SUMMARY_FIELDS
from tests.unit.domain.test_dictation_service import NOW, request
from tests.web.conftest import AsgiClient
from tests.web.test_dictation import PATH
from tests.web.test_dictation import client as dictation_client

client = dictation_client


def test_history_lists_uncorrected_and_unknown_then_correction_and_delete(client: AsgiClient) -> None:
    service = client.app.state.services.dictation
    incoming = [request(number=number).model_dump(mode="json") for number in (1, 2, 3)]
    for payload in incoming[:2]:
        assert client.post(PATH + "/transcribe", json=payload).json()["status"] == "transcribed"
    service.transcriber.error = DictationTranscriberError("unknown", "outcome_unknown")
    assert client.post(PATH + "/transcribe", json=incoming[2]).json()["status"] == "unknown"
    response = client.get(PATH + "/attempts")
    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    history = response.json()
    assert [item["status"] for item in history] == ["transcribed", "transcribed", "unknown"]
    assert all(set(item) == SUMMARY_FIELDS and not item["has_correction"] for item in history)
    assert "Original words" not in response.text
    assert "endpoint" not in response.text
    assert (
        client.post(
            PATH + "/corrections", json={"attempt_id": incoming[0]["attempt_id"], "final_text": "Edited"}
        ).status_code
        == 200
    )
    assert [item["has_correction"] for item in client.get(PATH + "/attempts").json()] == [True, False, False]
    assert client.post(f"{PATH}/attempts/{incoming[1]['attempt_id']}/delete").status_code == 200
    assert len(client.get(PATH + "/attempts").json()) == 2
    assert service.transcriber.calls == 3


def test_history_owner_expiry_and_authentication(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post(PATH + "/transcribe", json=request().model_dump(mode="json")).status_code == 200
    assert client.get(PATH + "/attempts", headers={"authorization": ""}).status_code == 401
    with monkeypatch.context() as scoped:
        scoped.setattr(
            "lychd.domain.codex.middleware.default_local_sigil",
            lambda: Sigil(name="foreign-reader", scopes=frozenset({"altar:read"})),
        )
        assert client.get(PATH + "/attempts").json() == []
    service = client.app.state.services.dictation
    monkeypatch.setattr(service, "_now", lambda: NOW + timedelta(days=8))
    assert client.get(PATH + "/attempts").json() == []


def test_history_revocation_after_read_refuses_disclosure(client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = client.app.state.services.dictation
    original = service.list_attempts

    async def revoked_read(owner: str) -> object:
        result = await original(owner)
        client.app.state.local_operator_access.revoke()
        return result

    monkeypatch.setattr(service, "list_attempts", revoked_read)
    assert client.get(PATH + "/attempts").status_code == 403


def test_history_openapi_and_discovery_retention(client: AsgiClient) -> None:
    schema = client.get("/schema/openapi.json").json()
    assert schema["paths"][PATH + "/attempts"]["get"]["operationId"] == "listDictationAttempts"
    assert set(schema["components"]["schemas"]["DictationAttemptSummary"]["properties"]) == SUMMARY_FIELDS
    discovery = client.get(PATH).json()
    assert discovery["retention_seconds"] == 604800
    assert discovery["max_records_per_owner"] == 100
