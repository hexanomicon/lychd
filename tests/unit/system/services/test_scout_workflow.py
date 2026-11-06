"""Production Scout coordination with inert storage and acquisition substitutes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import BRIDGE_CHAT_SCOUT, builtin_workflow_registry, resolve_named_workflow
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.schemas import ConsentView
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.naming import NamingSnapshot
from lychd.domain.scout.attempts import (
    NewScoutClaim,
    ScoutAttemptSnapshot,
    ScoutRunBinding,
    ScoutSettlement,
    ScoutStoreError,
)
from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy
from lychd.domain.scout.profile import (
    SCOUT_ANSWER_PURPOSE,
    ScoutBinding,
    ScoutReviewRef,
    ScoutWorkflowCode,
    ScoutWorkflowError,
)
from lychd.domain.scout.transport import FetchCode, FetchError
from lychd.domain.web.consent_reviews import ConsentReviewForbiddenError
from lychd.interface.web.scout_admission import ScoutAdmissionService
from lychd.interface.web.scout_review import ScoutConsentReviews
from lychd.system.services import scout_workflow
from lychd.system.services.scout_workflow import ScoutCompletions, ScoutWorkflowService
from tests.scout_fixtures import CAPABILITY, PROMPT, scout_profile


@dataclass
class Scenario:
    access: LocalOperatorAccess
    authentication: LocalOperatorAuthentication
    authorizer: ScoutHostAuthorizer
    admission: ScoutAdmissionService
    binding: ScoutBinding
    run: RunRecord
    store: Mock
    consents: Mock
    service: ScoutWorkflowService
    completions: ScoutCompletions
    review: ScoutReviewRef
    snapshot: ScoutAttemptSnapshot


async def scenario(*, naming: NamingSnapshot | None = None) -> Scenario:
    profile = scout_profile()
    credential = "fixture-credential"
    access = LocalOperatorAccess(access_password=credential)
    authentication = access.authenticate(username=b"magus", password=credential.encode())
    assert authentication is not None
    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=profile.policy_revision,
            revocation_generation=profile.revocation_generation,
            actions=frozenset(ScoutAction),
            purposes=frozenset({SCOUT_ANSWER_PURPOSE}),
            categories=frozenset({"public-web-locator"}),
            binding_digests=frozenset({profile.binding_digest}),
            resolver_custody_digests=frozenset({profile.resolver_custody_digest}),
        ),
    )
    admission = ScoutAdmissionService(access=access, authorizer=authorizer, profile=profile)
    proof = admission.declare(prompt=PROMPT, request_id=uuid4(), authentication=authentication)
    binding = admission(Intent(session_id="session", prompt=PROMPT, source="bridge"), proof, profile)
    workflow = (
        resolve_named_workflow(builtin_workflow_registry(), BRIDGE_CHAT_SCOUT)
        if naming is not None
        else BRIDGE_CHAT_SCOUT
    )
    run = RunRecord(
        run_id=str(uuid4()),
        session_id="session",
        workflow_name="bridge_chat",
        pattern_manifest=workflow.manifest.snapshot(),
        admitted_naming=naming,
        source="bridge",
        queue_name="runs",
        priority=50,
        status=RunStatus.RUNNING,
        prompt=PROMPT,
        admitted_capability_key=CAPABILITY,
        admitted_scout=binding,
        enqueue_seq=2,
    )
    store, consents, ledger, completions = Mock(), Mock(), Mock(), ScoutCompletions()
    ledger.get = AsyncMock(return_value=run)
    store.read_request = AsyncMock(return_value=None)
    store.read_run_binding = AsyncMock(
        return_value=ScoutRunBinding(
            run_id=UUID(run.run_id),
            enqueue_seq=run.enqueue_seq,
            sigil_name="magus",
            workflow_name="bridge_chat",
            pattern_digest="1" * 64,
            intent_digest="2" * 64,
        )
    )

    async def prepare(preparation: Any, native: Any, review: bytes) -> ScoutAttemptSnapshot:
        assert review
        snapshot = ScoutAttemptSnapshot(
            preparation=preparation,
            consent_id=uuid4(),
            native_binding=native,
            status="prepared",
        )
        store.read.return_value = snapshot
        store.read_request.return_value = snapshot
        return snapshot

    store.read = AsyncMock()
    store.prepare = AsyncMock(side_effect=prepare)
    store.claim, store.settle, store.unknown = AsyncMock(), AsyncMock(), AsyncMock()
    service = ScoutWorkflowService(
        store=store,
        completions=completions,
        ledger=ledger,
        consents=consents,
        profile=profile,
        capability_key=CAPABILITY,
        authorizer=authorizer,
        fence=RunEffectFence(),
    )
    review = await service.prepare(run_id=run.run_id, binding=binding)
    snapshot = store.read.return_value
    return Scenario(
        access,
        authentication,
        authorizer,
        admission,
        binding,
        run,
        store,
        consents,
        service,
        completions,
        review,
        snapshot,
    )


@pytest.mark.asyncio
async def test_admission_requires_actual_marker_and_current_policy() -> None:
    s = await scenario()
    forged = replace(s.authentication)
    assert forged == s.authentication
    for marker in (None, default_local_sigil(), forged):
        with pytest.raises(ScoutWorkflowError):
            s.admission.declare(prompt=PROMPT, request_id=uuid4(), authentication=marker)
    s.access.revoke()
    with pytest.raises(ScoutWorkflowError):
        s.admission.declare(prompt=PROMPT, request_id=uuid4(), authentication=s.authentication)


@pytest.mark.asyncio
async def test_duplicate_preparation_keeps_original_review_and_expiry() -> None:
    s = await scenario()
    assert await s.service.prepare(run_id=s.run.run_id, binding=s.binding) == s.review
    s.store.prepare.assert_awaited_once()
    assert s.snapshot.preparation.expires_at > datetime.now(UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["review", "consent"])
@pytest.mark.parametrize("fence", ["run", "claim", "shutdown"])
async def test_cancellation_during_final_read_refuses_answer_or_verdict(boundary: str, fence: str) -> None:
    s = await scenario()
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args: Any) -> Any:
        _ = args
        entered.set()
        await release.wait()
        return (
            s.snapshot
            if boundary == "review"
            else ConsentView(
                id=str(s.snapshot.consent_id),
                run_id=s.run.run_id,
                tool_name="scout",
                status="granted",
                native_binding=s.snapshot.native_binding,
            )
        )

    if boundary == "review":
        s.store.read.side_effect = delayed
        call = s.service.authorize_settle(run_id=s.run.run_id, binding=s.binding, review=s.review, receipt_id=None)
    else:
        s.consents.get = AsyncMock(side_effect=delayed)
        call = s.service.consent(run_id=s.run.run_id, binding=s.binding, review=s.review)
    task = asyncio.create_task(call)
    await entered.wait()
    if fence == "run":
        s.service.fence(s.run.run_id, "cancelled")
    elif fence == "claim":
        s.service.fence_claim(s.run.run_id, s.run.enqueue_seq, "interrupted")
    else:
        s.service.fence_all("shutdown")
    release.set()
    with pytest.raises(ScoutWorkflowError):
        await task


@pytest.mark.asyncio
async def test_old_delivery_fence_does_not_refuse_current_review() -> None:
    s = await scenario()
    s.service.fence_claim(s.run.run_id, s.run.enqueue_seq - 1, "old_worker")
    await s.service.authorize_settle(run_id=s.run.run_id, binding=s.binding, review=s.review, receipt_id=None)


@pytest.mark.asyncio
async def test_native_review_checks_actual_authentication_after_database_wait() -> None:
    s = await scenario()
    reviews = ScoutConsentReviews(access=s.access, authorizer=s.authorizer, store=s.store)
    view = ConsentView(
        id=str(s.snapshot.consent_id),
        run_id=s.run.run_id,
        tool_name="scout",
        status="pending",
        native_review_required=True,
        native_binding=s.snapshot.native_binding,
    )
    resolved = await reviews.resolve(
        consent=view, reviewer=default_local_sigil(), purpose="decide", authentication=s.authentication
    )
    assert resolved.decision_allowed
    assert resolved.document is not None
    values = " ".join(fact.value for fact in resolved.document.facts)
    assert s.binding.declaration.url in values
    assert s.binding.profile.resolver_custody_statement in values
    with pytest.raises(ConsentReviewForbiddenError):
        await reviews.resolve(
            consent=view, reviewer=default_local_sigil(), purpose="view", authentication=replace(s.authentication)
        )

    async def revoke(*args: Any) -> ScoutAttemptSnapshot:
        _ = args
        await asyncio.sleep(0)
        s.access.revoke()
        return s.snapshot

    s.store.read.side_effect = revoke
    with pytest.raises(ConsentReviewForbiddenError):
        await reviews.resolve(
            consent=view, reviewer=default_local_sigil(), purpose="decide", authentication=s.authentication
        )


def fresh_claim(s: Scenario) -> NewScoutClaim:
    return NewScoutClaim(
        preparation=s.snapshot.preparation,
        consent_id=s.snapshot.consent_id,
        enqueue_seq=s.run.enqueue_seq,
        claim_id=uuid4(),
        committed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_completion_ownership_cannot_be_restored_from_equal_values() -> None:
    s = await scenario()
    claim = fresh_claim(s)
    settlement = ScoutSettlement(
        receipt_id=uuid4(),
        outcome="refused",
        usage=s.binding.profile.allowance,
        handoff_evidence=b"{}",
        sockets="closed",
        child="not_started",
    )
    with pytest.raises(ScoutStoreError):
        s.completions.verify(claim, settlement)
    s.completions.retain(claim, settlement)
    s.completions.verify(claim, settlement)
    for other_claim, other_settlement in ((replace(claim), settlement), (claim, settlement.model_copy())):
        with pytest.raises(ScoutStoreError):
            s.completions.verify(other_claim, other_settlement)
    s.completions.forget(claim)
    with pytest.raises(ScoutStoreError):
        s.completions.verify(claim, settlement)


@pytest.mark.asyncio
async def test_duplicate_or_lost_material_never_launches_acquisition(monkeypatch: pytest.MonkeyPatch) -> None:
    s = await scenario()
    s.store.claim.return_value = replace(s.snapshot, status="unknown_after_crash")
    fetch = AsyncMock()
    monkeypatch.setattr(scout_workflow, "fetch_static_page", fetch)
    with pytest.raises(ScoutWorkflowError):
        await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    fetch.assert_not_awaited()
    s.store.settle.assert_not_awaited()


@pytest.mark.asyncio
async def test_pre_extraction_refusal_releases_only_owned_measured_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    s = await scenario()
    claim = fresh_claim(s)
    s.store.claim.return_value = claim
    monkeypatch.setattr(scout_workflow, "fetch_static_page", AsyncMock(side_effect=FetchError(FetchCode.DNS)))

    async def settle(actual: NewScoutClaim, receipt: ScoutSettlement) -> ScoutAttemptSnapshot:
        s.completions.verify(actual, receipt)
        assert actual is claim
        assert receipt.child == "not_started"
        assert receipt.usage.connects == receipt.usage.transmissions == receipt.usage.wire_bytes == 0
        return replace(s.snapshot, status="refused", receipt_id=receipt.receipt_id, receipt_digest="3" * 64)

    s.store.settle.side_effect = settle
    with pytest.raises(FetchError):
        await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    s.store.settle.assert_awaited_once()
    s.store.unknown.assert_not_awaited()
    await s.service.contain(s.run.run_id)


@pytest.mark.asyncio
async def test_unexpected_acquisition_failure_keeps_uncertainty_and_refuses_containment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await scenario()
    s.store.claim.return_value = fresh_claim(s)
    monkeypatch.setattr(scout_workflow, "fetch_static_page", AsyncMock(side_effect=RuntimeError("fixture failure")))
    with pytest.raises(RuntimeError, match="fixture failure"):
        await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    s.store.unknown.assert_awaited_once()
    s.store.settle.assert_not_awaited()
    with pytest.raises(RuntimeError, match="uncertain"):
        await s.service.contain(s.run.run_id)


def _accepted_names() -> NamingSnapshot:
    return NamingSnapshot(
        magus_name="Zenith Runeweaver",
        primus_name="Aster Shadowdancer",
        magus_origin="manual",
        primus_origin="self_chosen",
        revision=1,
    )


@pytest.mark.asyncio
async def test_named_profile_keeps_preparation_and_consent_under_existing_authority() -> None:
    s = await scenario(naming=_accepted_names())
    assert s.run.pattern_manifest["revision"] == "4-naming1"
    assert await s.service.prepare(run_id=s.run.run_id, binding=s.binding) == s.review
    s.store.prepare.assert_awaited_once()
    s.consents.get = AsyncMock(
        return_value=ConsentView(
            id=str(s.snapshot.consent_id),
            run_id=s.run.run_id,
            tool_name="scout",
            status="pending",
            native_binding=s.snapshot.native_binding,
        )
    )
    assert await s.service.consent(run_id=s.run.run_id, binding=s.binding, review=s.review) == "pending"
    s.access.revoke()
    with pytest.raises(FetchError) as caught:
        await s.service.consent(run_id=s.run.run_id, binding=s.binding, review=s.review)
    assert caught.value.code is FetchCode.EGRESS


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["revision", "manifest", "missing_names", "legacy_with_names", "invalid_names"])
async def test_named_scout_refuses_binding_substitution_before_store_access(mismatch: str) -> None:
    s = await scenario(naming=_accepted_names())
    if mismatch == "revision":
        s.run.pattern_manifest["revision"] = "4-naming2"
    elif mismatch == "manifest":
        s.run.pattern_manifest["implementation_revision"] = "foreign"
    elif mismatch == "missing_names":
        s.run.admitted_naming = None
    elif mismatch == "legacy_with_names":
        s.run.pattern_manifest = BRIDGE_CHAT_SCOUT.manifest.snapshot()
    else:
        s.run.admitted_naming = _accepted_names().model_copy(update={"revision": 0})
    s.store.reset_mock()
    with pytest.raises(ScoutWorkflowError) as caught:
        await s.service.prepare(run_id=s.run.run_id, binding=s.binding)
    assert caught.value.code is ScoutWorkflowCode.BINDING
    assert s.store.mock_calls == []
