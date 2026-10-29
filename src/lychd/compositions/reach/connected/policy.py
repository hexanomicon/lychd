"""Pure exact-target preparation and finite batch preflight, with no effects or grants."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import TypeAdapter

from lychd.compositions.reach.connected.schemas import (
    ConnectedPolicy,
    CorrespondenceRequest,
    PreparedBatch,
    PreparedOperation,
    ReadRequest,
    SendRequest,
)
from lychd.compositions.reach.schemas import require_aware

_REQUEST = TypeAdapter(CorrespondenceRequest)


def prepare_operation(
    policy: ConnectedPolicy,
    request: CorrespondenceRequest,
    *,
    now: datetime,
) -> PreparedOperation:
    """Validate an inert application request; success permits no read, send, or disclosure."""
    require_aware(now)
    # Reparse rather than trusting model_copy/model_construct values across an application boundary.
    policy = ConnectedPolicy.model_validate(policy.model_dump(mode="python"))
    request = _REQUEST.validate_python(request.model_dump(mode="python"))
    if request.kind not in policy.operations:
        msg = "The operation is outside the preparation policy."
        raise ValueError(msg)
    if request.target not in policy.allowed_targets:
        msg = "The exact target is outside the preparation policy."
        raise ValueError(msg)
    connection = next(item for item in policy.connections if item.connection_id == request.target.connection_id)
    if isinstance(request, SendRequest) and len(request.text) > policy.max_text_chars:
        msg = "The proposed text exceeds the preparation budget."
        raise ValueError(msg)
    if isinstance(request, ReadRequest) and request.limit > policy.max_read_limit:
        msg = "The selected read exceeds the preparation budget."
        raise ValueError(msg)
    return PreparedOperation(
        request=request,
        connection=connection,
        policy_digest=policy.digest,
        prepared_at=now,
        expires_at=now + timedelta(seconds=policy.ttl_seconds),
    )


def prepare_batch(
    policy: ConnectedPolicy,
    requests: tuple[CorrespondenceRequest, ...],
    *,
    now: datetime,
) -> PreparedBatch:
    """Prepare every selected operation or refuse the whole finite plan without side effects."""
    require_aware(now)
    policy = ConnectedPolicy.model_validate(policy.model_dump(mode="python"))
    if type(requests) is not tuple or not 1 <= len(requests) <= policy.max_batch_size:
        msg = "A batch requires an explicit finite tuple within its preparation budget."
        raise ValueError(msg)
    operations = tuple(prepare_operation(policy, request, now=now) for request in requests)
    return PreparedBatch(
        operations=operations,
        policy_digest=policy.digest,
        prepared_at=now,
        expires_at=now + timedelta(seconds=policy.ttl_seconds),
    )
