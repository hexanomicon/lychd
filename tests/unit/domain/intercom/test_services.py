from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from lychd.domain.intercom.models import (
    PeerAdmissionDecision,
    PeerEnvelope,
    PeerTaskPayload,
    PeerTaskResult,
    PeerTaskStatus,
    VerifiedPeerEnvelope,
)
from lychd.domain.intercom.services import (
    IllegalPeerTaskTransitionError,
    InMemoryPeerTaskStore,
    IntercomAdmissionService,
    PeerEnvelopeRejectedError,
    PeerReplayConflictError,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def _verified(
    *,
    task_id: str = "task:1",
    message_id: str = "message:1",
    idempotency_key: str = "request:1",
    nonce: str = "nonce:1",
    digest_digit: str = "0",
    protocol_version: str = "test-protocol:v1",
    recipient_peer_id: str = "peer:local",
    issued_at: datetime = NOW - timedelta(seconds=1),
    expires_at: datetime = NOW + timedelta(minutes=5),
) -> VerifiedPeerEnvelope:
    envelope = PeerEnvelope(
        protocol_version=protocol_version,
        schema_version="task:test:v1",
        sender_peer_id="peer:sender",
        recipient_peer_id=recipient_peer_id,
        message_id=message_id,
        task_id=task_id,
        idempotency_key=idempotency_key,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
        task_type="summarize",
        payload=PeerTaskPayload(values={"prompt": digest_digit}),
    )
    return VerifiedPeerEnvelope(
        envelope=envelope,
        canonical_envelope_digest=f"sha256:{digest_digit * 64}",
        authenticated_peer_id="peer:sender",
        key_generation=1,
        revocation_generation=2,
        verified_at=NOW,
    )


@dataclass
class _Verifier:
    verified: VerifiedPeerEnvelope

    async def verify(self, message: bytes) -> VerifiedPeerEnvelope:
        assert message == b"verified-wire-message"
        return self.verified


@dataclass
class _Policy:
    allowed: bool = True

    async def decide(self, verified: VerifiedPeerEnvelope) -> PeerAdmissionDecision:
        assert verified.authenticated_peer_id == "peer:sender"
        return PeerAdmissionDecision(
            allowed=self.allowed,
            policy_revision="peer-policy:v1",
            reason=None if self.allowed else "task class is not authorized",
        )


def _service(
    verified: VerifiedPeerEnvelope,
    *,
    store: InMemoryPeerTaskStore | None = None,
    allowed: bool = True,
    clock: Callable[[], datetime] | None = None,
) -> IntercomAdmissionService:
    return IntercomAdmissionService(
        local_peer_id="peer:local",
        supported_protocol_versions=frozenset({"test-protocol:v1"}),
        supported_schema_versions=frozenset({"task:test:v1"}),
        verifier=_Verifier(verified),
        policy=_Policy(allowed=allowed),
        store=store or InMemoryPeerTaskStore(),
        clock=clock or (lambda: NOW),
    )


@pytest.mark.asyncio
async def test_admission_is_idempotent_for_exact_verified_replay() -> None:
    store = InMemoryPeerTaskStore()
    service = _service(_verified(), store=store)

    first = await service.receive(b"verified-wire-message")
    second = await service.receive(b"verified-wire-message")

    assert first.status is PeerTaskStatus.ADMITTED
    assert second == first
    assert second.admission is not None


@pytest.mark.asyncio
async def test_exact_replay_ignores_observation_time_and_current_revocation_generation() -> None:
    store = InMemoryPeerTaskStore()
    original = _verified()
    await store.receive(original)
    replay = original.model_copy(
        update={
            "verified_at": NOW + timedelta(seconds=1),
            "revocation_generation": original.revocation_generation + 1,
        },
        deep=True,
    )

    retained, created = await store.receive(replay)

    assert created is False
    assert retained.verified == original


@pytest.mark.asyncio
async def test_changed_content_reusing_task_or_nonce_fails_closed() -> None:
    store = InMemoryPeerTaskStore()
    await store.receive(_verified())

    with pytest.raises(PeerReplayConflictError, match="task id"):
        await store.receive(_verified(digest_digit="1"))
    with pytest.raises(PeerReplayConflictError, match="nonce"):
        await store.receive(
            _verified(
                task_id="task:2",
                message_id="message:2",
                idempotency_key="request:2",
                digest_digit="2",
            )
        )


@pytest.mark.asyncio
async def test_store_defensively_snapshots_nested_payload_values() -> None:
    store = InMemoryPeerTaskStore()
    verified = _verified()

    received, _ = await store.receive(verified)
    verified.envelope.payload.values["prompt"] = "mutated-before-read"
    received.verified.envelope.payload.values["prompt"] = "mutated-view"

    retained = await store.get("task:1")
    assert retained is not None
    assert retained.verified.envelope.payload.values == {"prompt": "0"}


@pytest.mark.asyncio
async def test_policy_refusal_and_expiry_never_reach_queue() -> None:
    refusal_service = _service(_verified(), allowed=False)
    refused = await refusal_service.receive(b"verified-wire-message")
    replayed_refusal = await refusal_service.receive(b"verified-wire-message")
    expired = await _service(
        _verified(expires_at=NOW - timedelta(microseconds=1)),
    ).receive(b"verified-wire-message")

    assert refused.status is PeerTaskStatus.REFUSED
    assert refused.result is not None
    assert refused.result.reason == "task class is not authorized"
    assert refused.admission is not None
    assert replayed_refusal == refused
    assert expired.status is PeerTaskStatus.EXPIRED


@pytest.mark.asyncio
async def test_recipient_and_version_mismatch_are_rejected_before_storage() -> None:
    store = InMemoryPeerTaskStore()
    with pytest.raises(PeerEnvelopeRejectedError, match="recipient"):
        await _service(_verified(recipient_peer_id="peer:other"), store=store).receive(b"verified-wire-message")
    with pytest.raises(PeerEnvelopeRejectedError, match="protocol version"):
        await _service(_verified(protocol_version="unknown:v9"), store=store).receive(b"verified-wire-message")
    assert await store.get("task:1") is None


@pytest.mark.asyncio
async def test_lifecycle_is_ordered_and_first_terminal_result_wins() -> None:
    service = _service(_verified())
    await service.receive(b"verified-wire-message")
    with pytest.raises(IllegalPeerTaskTransitionError, match="Illegal peer-task transition"):
        await service.start("task:1")
    await service.queue("task:1")
    await service.start("task:1")

    success = PeerTaskResult(
        task_id="task:1",
        status=PeerTaskStatus.SUCCEEDED,
        payload=PeerTaskPayload(values={"answer": "bounded"}),
    )
    first, adopted = await service.adopt("task:1", success)
    assert success.payload is not None
    success.payload.values["answer"] = "mutated-after-adoption"
    late, late_adopted = await service.adopt(
        "task:1",
        PeerTaskResult(task_id="task:1", status=PeerTaskStatus.FAILED, reason="late"),
    )

    assert adopted is True
    assert late_adopted is False
    assert first == late
    assert late.status is PeerTaskStatus.SUCCEEDED
    assert late.result is not None
    assert late.result.payload is not None
    assert late.result.payload.values == {"answer": "bounded"}


@pytest.mark.asyncio
async def test_expiry_fences_queue_start_and_terminal_adoption() -> None:
    observed_now = NOW

    def clock() -> datetime:
        return observed_now

    service = _service(_verified(expires_at=NOW + timedelta(seconds=1)), clock=clock)
    await service.receive(b"verified-wire-message")
    observed_now = NOW + timedelta(seconds=2)

    queued = await service.queue("task:1")
    started = await service.start("task:1")
    adopted, did_adopt = await service.adopt(
        "task:1",
        PeerTaskResult(
            task_id="task:1",
            status=PeerTaskStatus.SUCCEEDED,
            payload=PeerTaskPayload(values={"answer": "too late"}),
        ),
    )

    assert queued.status is PeerTaskStatus.EXPIRED
    assert started == queued
    assert adopted == queued
    assert did_adopt is False
