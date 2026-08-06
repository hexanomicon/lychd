from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import JsonValue, ValidationError

from lychd.domain.intercom.models import (
    PeerEnvelope,
    PeerTaskPayload,
    PeerTaskResult,
    PeerTaskStatus,
    VerifiedPeerEnvelope,
)


def _envelope() -> PeerEnvelope:
    now = datetime.now(UTC)
    return PeerEnvelope(
        protocol_version="test-protocol:v1",
        schema_version="task:test:v1",
        sender_peer_id="peer:sender",
        recipient_peer_id="peer:local",
        message_id="message:1",
        task_id="task:1",
        idempotency_key="request:1",
        nonce="nonce:1",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        task_type="summarize",
        payload=PeerTaskPayload(values={"prompt": "bounded"}),
    )


def test_envelope_requires_forward_aware_time_window() -> None:
    envelope = _envelope()
    with pytest.raises(ValidationError, match="expiry must be later"):
        PeerEnvelope.model_validate({**envelope.model_dump(), "expires_at": envelope.issued_at})
    with pytest.raises(ValidationError, match="canonical"):
        PeerEnvelope.model_validate({**envelope.model_dump(), "task_id": " task:1"})


def test_verified_envelope_binds_authenticated_sender() -> None:
    with pytest.raises(ValidationError, match="does not match"):
        VerifiedPeerEnvelope(
            envelope=_envelope(),
            canonical_envelope_digest=f"sha256:{'0' * 64}",
            authenticated_peer_id="peer:other",
            key_generation=1,
            revocation_generation=2,
        )


def test_peer_payload_is_frozen_bounded_json() -> None:
    payload = PeerTaskPayload(values={"nested": [1, True, None, "text"]})

    assert payload.values == {"nested": [1, True, None, "text"]}
    with pytest.raises(ValidationError, match="encoded limit"):
        PeerTaskPayload(values={"oversized": "x" * 1_048_576})
    nested: JsonValue = "leaf"
    for _ in range(34):
        nested = [nested]
    with pytest.raises(ValidationError, match="nesting limit"):
        PeerTaskPayload(values={"nested": nested})


def test_terminal_result_requires_failure_reason_and_never_embeds_work_handles() -> None:
    with pytest.raises(ValidationError, match="must carry a reason"):
        PeerTaskResult(task_id="task:1", status=PeerTaskStatus.LOST)
    with pytest.raises(ValidationError, match="cannot carry"):
        PeerTaskResult(task_id="task:1", status=PeerTaskStatus.SUCCEEDED, reason="not really")
    with pytest.raises(ValidationError, match="success payload"):
        PeerTaskResult(
            task_id="task:1",
            status=PeerTaskStatus.REFUSED,
            reason="not admitted",
            payload=PeerTaskPayload(values={"should": "not cross"}),
        )
