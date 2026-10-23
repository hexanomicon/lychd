"""Pure closed recording-owner tests; injected claims do not prove PostgreSQL."""

from __future__ import annotations

import asyncio
import copy
import time
from collections.abc import Callable
from dataclasses import replace
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.privacy.contracts import PreparationPolicy, PreparedCut, digest
from lychd.domain.privacy.disclosure import (
    DisclosureCapacity,
    DisclosureError,
    DisclosureLimits,
    DisclosurePreparation,
    DisclosureRunBinding,
    DisclosureSnapshot,
    FreshDisclosureClaim,
)
from lychd.domain.privacy.fixtures import diagnostic_fixture, fixture_binding
from lychd.domain.privacy.preparation import CutAuthority, make_plan, prepare_cut
from lychd.system.services.privacy_disclosure import PrivacyDisclosureService, RecordingSink, SyntheticExportAuthority


def _fixture() -> tuple[PrivacyDisclosureService, PreparedCut, SyntheticExportAuthority, RecordingSink, RunEffectFence]:
    binding, policy, cuts = fixture_binding(), PreparationPolicy(), CutAuthority()
    run = DisclosureRunBinding(
        run_id=binding.run_id,
        delivery_id=uuid4(),
        enqueue_seq=0,
        priority=50,
        queue_name="runs",
        workflow_name="offline-recording",
        sigil_name="synthetic",
        intent_digest=digest({}),
        pattern_digest=digest({}),
    )
    authority = SyntheticExportAuthority(
        host_id=UUID(int=700),
        binding=binding,
        run=run,
        policy=policy,
        configuration_digest=digest("synthetic-configuration"),
    )
    source = diagnostic_fixture()
    now = int(time.time())
    plan = make_plan(source, binding, policy, expires_at=now + 300)
    prepared = prepare_cut(source, plan, policy, cuts, now=now)
    sink, fence = RecordingSink(), RunEffectFence()
    limits = DisclosureLimits(
        host=DisclosureCapacity(uses=4, bytes=100_000), purpose=DisclosureCapacity(uses=3, bytes=100_000)
    )
    service = PrivacyDisclosureService(
        async_sessionmaker(), authority=authority, cut_authority=cuts, limits=limits, fence=fence, sink=sink
    )
    return service, prepared, authority, sink, fence


async def _admit(
    monkeypatch: pytest.MonkeyPatch, service: PrivacyDisclosureService, prepared: PreparedCut
) -> FreshDisclosureClaim:
    async def retain(preparation: DisclosurePreparation) -> DisclosureSnapshot:
        return DisclosureSnapshot(preparation=preparation, status="prepared")

    monkeypatch.setattr(service.store, "prepare", retain)
    snapshot = await service.prepare(prepared, request_id=uuid4(), transmission_id=uuid4())
    claim = FreshDisclosureClaim(snapshot.preparation, uuid4())
    monkeypatch.setattr(service.store, "_live", {claim.claim_id: claim})

    async def retained_check(_claim: FreshDisclosureClaim) -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(service.store, "check_claim", retained_check)
    return claim


@pytest.mark.asyncio
async def test_exact_bytes_once_and_identity_owned_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, _, sink, _ = _fixture()
    claim = await _admit(monkeypatch, service, prepared)
    with pytest.raises(DisclosureError, match="claim"):
        await service.record(copy.copy(claim))
    completion = await service.record(claim)
    assert completion.outcome == "recorded"
    assert sink.records == (prepared.candidate,)
    service.verify_completion(claim, completion)
    with pytest.raises(DisclosureError, match="claim"):
        service.verify_completion(claim, copy.copy(completion))
    with pytest.raises(DisclosureError, match="claim"):
        service.verify_completion(replace(claim), completion)
    with pytest.raises(DisclosureError, match="claim"):
        await service.record(claim)
    object.__setattr__(completion, "transmission_id", uuid4())
    with pytest.raises(DisclosureError, match="claim"):
        service.verify_completion(claim, completion)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    [
        "consumer_id",
        "principal_id",
        "sigil_digest",
        "purpose_id",
        "target_digest",
        "run_id",
        "occurrence_id",
        "attempt_id",
    ],
)
async def test_cut_self_equality_cannot_supply_host_authority(field: str, monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, authority, sink, _ = _fixture()
    # Even a correctly sealed Cut from this very issuer must match independent host pins.
    changed = authority.binding.model_copy(update={field: "f" * 64 if "digest" in field else uuid4()})
    source, cuts = diagnostic_fixture(), CutAuthority()
    monkeypatch.setattr(service, "_cuts", cuts)
    plan = make_plan(source, changed, authority.policy, expires_at=prepared.cut.expires_at)
    forged = prepare_cut(source, plan, authority.policy, cuts, now=int(time.time()))
    with pytest.raises(DisclosureError, match="authority"):
        await service.prepare(forged, request_id=uuid4(), transmission_id=uuid4())
    assert sink.records == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["revoke", "generation", "policy", "expiry", "fence", "all-fence", "prepared"])
async def test_change_during_await_fences_recording(change: str, monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, authority, sink, fence = _fixture()
    claim = await _admit(monkeypatch, service, prepared)

    async def retained_check(_claim: FreshDisclosureClaim) -> None:
        await asyncio.sleep(0)
        if change == "revoke":
            authority.revoked = True
        elif change == "generation":
            authority.generation += 1
        elif change == "policy":
            authority.policy = authority.policy.model_copy(update={"max_lifetime_seconds": 400})
        elif change == "expiry":
            monkeypatch.setattr(time, "time", lambda: float(prepared.cut.expires_at))
        elif change == "fence":
            fence.fence_claim(str(authority.run.run_id), 0, "synthetic-stop")
        elif change == "all-fence":
            fence.fence_all("synthetic-shutdown")
        else:
            monkeypatch.setattr(service, "_prepared", {})

    monkeypatch.setattr(service.store, "check_claim", retained_check)
    completion = await service.record(claim)
    assert completion.outcome == "refused"
    assert sink.records == ()
    with pytest.raises(DisclosureError, match="claim"):
        await service.record(claim)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["candidate", "receipts", "verification", "cut"])
async def test_substituted_material_refuses_before_retention(field: str) -> None:
    service, prepared, _, sink, _ = _fixture()
    changes = {
        "candidate": prepared.candidate + b" ",
        "receipts": prepared.receipts[:1],
        "verification": prepared.verification.model_copy(update={"candidate_digest": "f" * 64}),
        "cut": prepared.cut.model_copy(update={"seal": "f" * 64}),
    }
    changed = prepared.model_copy(update={field: changes[field]})
    with pytest.raises(DisclosureError):
        await service.prepare(changed, request_id=uuid4(), transmission_id=uuid4())
    assert sink.records == ()


@pytest.mark.asyncio
async def test_same_loop_nonyielding_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, authority, sink, fence = _fixture()
    claim = await _admit(monkeypatch, service, prepared)
    original = SyntheticExportAuthority.authorize
    calls = 0

    def schedule_revocation(owner: SyntheticExportAuthority, preparation: DisclosurePreparation) -> None:
        nonlocal calls
        original(owner, preparation)
        calls += 1
        asyncio.get_running_loop().call_soon(fence.fence, str(authority.run.run_id), "late-stop")

    monkeypatch.setattr(SyntheticExportAuthority, "authorize", schedule_revocation)
    completion = await service.record(claim)
    assert calls >= 1
    assert completion.outcome == "recorded"
    assert sink.records == (prepared.candidate,)
    await asyncio.sleep(0)
    assert fence.reason(str(authority.run.run_id), 0) == "late-stop"


@pytest.mark.asyncio
async def test_concurrent_record_consumes_before_await(monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, _, sink, _ = _fixture()
    claim = await _admit(monkeypatch, service, prepared)
    results = await asyncio.gather(service.record(claim), service.record(claim), return_exceptions=True)
    assert sum(isinstance(result, DisclosureError) for result in results) == 1
    assert sink.records == (prepared.candidate,)


@pytest.mark.asyncio
async def test_possible_recording_failure_is_unknown_and_raw_error_is_discarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, prepared, _, sink, _ = _fixture()
    claim = await _admit(monkeypatch, service, prepared)
    original = RecordingSink.record

    def append_then_fail(recorder: RecordingSink, candidate: bytes) -> None:
        original(recorder, candidate)
        message = "SYNTHETIC-PRIVATE-FOREIGN-ERROR"
        raise RuntimeError(message)

    monkeypatch.setattr(RecordingSink, "record", append_then_fail)
    completion = await service.record(claim)
    assert completion.outcome == "unknown"
    assert sink.records == (prepared.candidate,)
    assert b"PRIVATE" not in completion.canonical_bytes()
    with pytest.raises(DisclosureError, match="claim"):
        await service.record(claim)


@pytest.mark.asyncio
async def test_foreign_service_and_loop_cannot_use_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    service, prepared, _, sink, _ = _fixture()
    claim = await _admit(monkeypatch, service, prepared)
    other, _, _, _, _ = _fixture()
    with pytest.raises(DisclosureError, match="claim"):
        await other.record(claim)
    monkeypatch.setattr(service, "_loop", object())
    with pytest.raises(DisclosureError, match="claim"):
        await service.record(claim)
    assert sink.records == ()


def test_recorder_capacity_and_no_callback_destination() -> None:
    sink = RecordingSink(max_records=1, max_bytes=3)
    sink.record(b"abc")
    with pytest.raises(DisclosureError, match="capacity"):
        sink.record(b"a")
    assert sink.records == (b"abc",)


@pytest.mark.asyncio
async def test_sink_subclass_and_callback_are_rejected() -> None:
    service, _, authority, _, fence = _fixture()

    class CallerSink(RecordingSink):
        pass

    for sink in (CallerSink(), cast("RecordingSink", cast("Callable[..., object]", lambda: None))):
        with pytest.raises(DisclosureError, match="contract"):
            PrivacyDisclosureService(
                async_sessionmaker(),
                authority=authority,
                cut_authority=CutAuthority(),
                limits=DisclosureLimits(
                    host=DisclosureCapacity(uses=1, bytes=1), purpose=DisclosureCapacity(uses=1, bytes=1)
                ),
                fence=fence,
                sink=sink,
            )
    assert service is not None


def test_nonexport_host_binding_refuses() -> None:
    binding = fixture_binding()
    run = DisclosureRunBinding(
        run_id=binding.run_id,
        delivery_id=uuid4(),
        enqueue_seq=0,
        priority=50,
        queue_name="runs",
        workflow_name="offline",
        sigil_name="synthetic",
        intent_digest=digest({}),
        pattern_digest=digest({}),
    )
    with pytest.raises(DisclosureError, match="binding"):
        SyntheticExportAuthority(
            host_id=uuid4(),
            binding=binding.model_copy(update={"consumer_kind": "a2a"}),
            run=run,
            policy=PreparationPolicy(),
            configuration_digest=digest("synthetic"),
        )
