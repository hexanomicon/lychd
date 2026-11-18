"""Exact Run selection is authorized metadata, including an exact public preseed."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from lychd.agents.workflows import BRIDGE_CHAT, BRIDGE_CHAT_ARCHIVE
from lychd.agents.workflows.archive_chat import archive_recall_request
from lychd.domain.archive import ArchiveRefused, ArchiveSubject, RecallReceipt
from lychd.domain.archive.contracts import text_digest
from lychd.domain.codex.sigil import Sigil, default_local_sigil
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.web.contracts import ArchiveRunRecall
from tests.web.test_archive_metadata import PROFILE, admission_engine, client

pytestmark = pytest.mark.asyncio


def retained_run() -> RunRecord:
    return RunRecord(
        run_id=str(uuid4()),
        session_id=str(uuid4()),
        workflow_name="bridge_chat",
        pattern_manifest=BRIDGE_CHAT_ARCHIVE.manifest.snapshot(),
        source="bridge",
        queue_name="runs",
        priority=70,
        status=RunStatus.DONE,
        prompt="PRIVATE_PROMPT_SENTINEL",
        admitted_archive=PROFILE,
        admitted_capability_key="chat:retained",
        error="PRIVATE_ERROR_SENTINEL",
    )


def preseed(run: RunRecord) -> RecallReceipt:
    request = archive_recall_request(profile=PROFILE, run_id=run.run_id, prompt=run.prompt)
    receipt = RecallReceipt(
        receipt_id=uuid4(),
        request_id=request.request_id,
        namespace_id=PROFILE.namespace_id,
        subject=PROFILE.owner_subject,
        purpose="archive:answer",
        policy_revision=PROFILE.policy_revision,
        query_digest=text_digest(run.prompt),
        request_digest=request.binding_digest(PROFILE, PROFILE.owner_subject, "archive:answer"),
        run_id=UUID(run.run_id),
        max_results=request.max_results,
        char_budget=request.char_budget,
        min_score=request.min_score,
        selected=(),
        omitted_for_budget=0,
        created_at=datetime.now(UTC),
        receipt_digest="0" * 64,
    )
    return receipt.model_copy(update={"receipt_digest": receipt.computed_digest()})


@pytest.mark.parametrize("status", ["queued", "done"])
async def test_exact_public_preseed_is_matching_only_even_before_execution(status: str) -> None:
    run = retained_run()
    run.status = RunStatus(status)
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    receipt = preseed(run)
    store.inspect_recall.return_value = receipt
    # A changed current default is irrelevant to the retained admission.
    async with client(store, ledger=ledger, engine=admission_engine(revision="1")) as http:
        first = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
        second = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert first.status_code == second.status_code == 200
    assert (
        first.json()
        == second.json()
        == {
            "run_id": run.run_id,
            "status": "recorded",
            "receipt": receipt.model_dump(mode="json"),
            "capture": "matching_retained_request",
        }
    )
    assert "PRIVATE_" not in first.text
    assert [call[0] for call in store.mock_calls] == ["inspect_recall", "inspect_recall"]
    assert "consumption" in (ArchiveRunRecall.__doc__ or "")
    assert "preseed" in (ArchiveRunRecall.__doc__ or "")


@pytest.mark.parametrize("state", ["unknown", "unsupported", "absent", "storage"])
async def test_unknown_unsupported_absent_and_failure_are_distinct(state: str) -> None:
    run = retained_run()
    if state == "unsupported":
        run.pattern_manifest = BRIDGE_CHAT.manifest.snapshot()
    ledger = AsyncMock()
    ledger.get.return_value = None if state == "unknown" else run
    store = AsyncMock()
    store.inspect_recall.return_value = None
    if state == "storage":
        store.inspect_recall.side_effect = ArchiveRefused("storage")
    async with client(store, ledger=ledger, engine=admission_engine()) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == {"unknown": 404, "unsupported": 200, "absent": 200, "storage": 409}[state]
    if state in {"unsupported", "absent"}:
        assert response.json()["status"] == {"unsupported": "not_applicable", "absent": "not_recorded"}[state]
        assert response.json()["receipt"] is None
    if state == "storage":
        assert response.json()["extra"]["code"] == "storage"
    if state in {"unknown", "unsupported"}:
        assert store.mock_calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workflow_name", "other"),
        ("source", "other"),
        ("admitted_capability_key", None),
        ("admitted_capability_key", ""),
        ("admitted_archive", None),
        ("admitted_archive", PROFILE.model_copy(update={"namespace_id": uuid4()})),
        ("admitted_archive", PROFILE.model_copy(update={"owner_subject": ArchiveSubject(identity="OTHER_OWNER")})),
        ("admitted_archive", PROFILE.model_copy(update={"policy_revision": "OTHER_POLICY"})),
        ("run_id", "2e8b5d1f-6a3c-4f9e-b7d4-8c0a1e5f3b26"),
        ("prompt", ""),
    ],
)
async def test_inconsistent_supported_run_refuses_before_receipt_lookup(field: str, value: Any) -> None:
    run = retained_run()
    requested_id = run.run_id
    setattr(run, field, value)
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=admission_engine()) as http:
        response = await http.get(f"/api/v1/archive/runs/{requested_id}/recall")
    assert response.status_code == 409
    assert response.json()["extra"]["code"] == "run_recall_binding"
    assert "OTHER_" not in response.text
    assert store.mock_calls == []


@pytest.mark.parametrize("forgery", ["digest", "valid_foreign_score", "extra"])
async def test_supported_pattern_requires_exact_snapshot(forgery: str) -> None:
    from lychd.domain.archive.contracts import digest

    run = retained_run()
    if forgery == "digest":
        run.pattern_manifest["digest"] = "0" * 64
    elif forgery == "extra":
        run.pattern_manifest["other"] = "private"
    else:
        run.pattern_manifest["implementation_revision"] = "py.other"
        # Pattern uses the same sorted JSON digest encoding for its unsigned value.
        run.pattern_manifest["digest"] = digest({k: v for k, v in run.pattern_manifest.items() if k != "digest"})
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=admission_engine()) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == 409
    assert store.mock_calls == []


@pytest.mark.parametrize("binding", [None, PROFILE.model_copy(update={"policy_revision": "other"})])
async def test_current_admission_profile_must_match_without_default_substitution(binding: object) -> None:
    run = retained_run()
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=admission_engine(binding=binding)) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == 409
    assert store.mock_calls == []


@pytest.mark.parametrize(
    "caller", [Sigil(name="other", scopes=default_local_sigil().scopes), Sigil(name="magus", scopes=frozenset())]
)
async def test_current_local_caller_denial_precedes_ledger_disclosure(caller: Sigil) -> None:
    store, ledger = AsyncMock(), AsyncMock()
    async with client(store, ledger=ledger, caller=caller, engine=admission_engine()) as http:
        response = await http.get(f"/api/v1/archive/runs/{uuid4()}/recall")
    assert response.status_code == 403
    assert store.mock_calls == ledger.mock_calls == []


async def test_view_rejects_status_or_run_receipt_inconsistency() -> None:
    run = retained_run()
    for status in ("not_applicable", "not_recorded"):
        with pytest.raises(ValidationError):
            ArchiveRunRecall(run_id=UUID(run.run_id), status=status, receipt=preseed(run))
    with pytest.raises(ValidationError):
        ArchiveRunRecall(run_id=UUID(run.run_id), status="recorded", receipt=None)
    with pytest.raises(ValidationError):
        ArchiveRunRecall(run_id=uuid4(), status="recorded", receipt=preseed(run))


@pytest.mark.parametrize("state", ["recorded", "unsupported", "unknown"])
async def test_current_management_authority_rechecked_after_ledger_await(state: str) -> None:
    from lychd.domain.archive import ArchiveAuthorization
    from lychd.interface.web.archive_access import LocalArchivePolicy

    allowed = [True]

    class RevokingPolicy(LocalArchivePolicy):
        def authorize(self, request: ArchiveAuthorization) -> bool:
            return allowed[0] and super().authorize(request)

    policy = RevokingPolicy(profile=PROFILE, caller=default_local_sigil())
    run = retained_run()
    if state == "unsupported":
        run.pattern_manifest = BRIDGE_CHAT.manifest.snapshot()

    async def read(_: str) -> RunRecord | None:
        allowed[0] = False
        return None if state == "unknown" else run

    ledger = AsyncMock()
    ledger.get.side_effect = read
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=admission_engine(), policy=policy) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == 403
    assert response.json()["extra"]["code"] == "authority"
    assert store.mock_calls == []


async def test_current_management_purpose_is_separate_from_recall() -> None:
    from lychd.domain.archive import ArchiveService
    from lychd.interface.web.archive_access import LocalArchivePolicy

    run = retained_run()
    request = archive_recall_request(profile=PROFILE, run_id=run.run_id, prompt=run.prompt)
    store = AsyncMock()
    policy = LocalArchivePolicy(profile=PROFILE, caller=default_local_sigil())
    archive = ArchiveService(profile=PROFILE, store=store, authorizer=policy)
    with pytest.raises(ArchiveRefused, match="authority"):
        await archive.inspect_recall(
            PROFILE.owner_subject, request, recall_purpose="archive:answer", purpose="archive:answer"
        )
    assert store.mock_calls == []
