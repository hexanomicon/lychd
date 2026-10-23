"""Restricted evidence integrity and safe error projection without a database."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Self, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.models.privacy import DisclosureTransmission
from lychd.db.privacy import DbDisclosureStore
from lychd.domain.privacy.contracts import PreparationPolicy, canonical_bytes, digest
from lychd.domain.privacy.disclosure import (
    DisclosureCapacity,
    DisclosureDecision,
    DisclosureError,
    DisclosureLimits,
    DisclosurePreparation,
    DisclosureRunBinding,
    DisclosureSettlement,
    FreshDisclosureClaim,
    RecordingCompletion,
)
from lychd.domain.privacy.fixtures import diagnostic_fixture, fixture_binding
from lychd.domain.privacy.preparation import CutAuthority, make_plan, prepare_cut


def _row() -> DisclosureTransmission:
    source, binding, policy = diagnostic_fixture(), fixture_binding(), PreparationPolicy()
    now = int(time.time())
    plan = make_plan(source, binding, policy, expires_at=now + 300)
    prepared = prepare_cut(source, plan, policy, CutAuthority(), now=now)
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
    preparation = DisclosurePreparation(
        request_id=uuid4(),
        transmission_id=uuid4(),
        host_id=uuid4(),
        configuration_digest=digest("synthetic"),
        authority_generation=0,
        run=run,
        cut=prepared.cut,
        candidate_size=len(prepared.candidate),
    )
    return DisclosureTransmission(
        id=preparation.transmission_id,
        request_id=preparation.request_id,
        run_id=run.run_id,
        delivery_id=run.delivery_id,
        occurrence_id=binding.occurrence_id,
        attempt_id=binding.attempt_id,
        preparation_bytes=preparation.canonical_bytes(),
        preparation_digest=preparation.digest,
        status="prepared",
        claim_id=None,
        claimed_at=None,
        decision_bytes=None,
        receipt_id=None,
        settlement_bytes=None,
    )


class _NoEffects:
    def authorize(self, preparation: DisclosurePreparation) -> None:
        del preparation
        message = "A read must not authorize an effect."
        raise AssertionError(message)

    def verify_completion(self, claim: FreshDisclosureClaim, completion: RecordingCompletion) -> None:
        del claim, completion
        message = "A read must not admit settlement."
        raise AssertionError(message)


class _ReadSession:
    def __init__(self, row: DisclosureTransmission | None, error: Exception | None) -> None:
        self.row, self.error = row, error

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, _model: object, _identity: UUID) -> DisclosureTransmission | None:
        if self.error is not None:
            raise self.error
        return self.row


def _store(row: DisclosureTransmission | None, error: Exception | None = None) -> DbDisclosureStore:
    factory = cast("async_sessionmaker[AsyncSession]", lambda: _ReadSession(row, error))
    owners = _NoEffects()
    limit = DisclosureCapacity(uses=1, bytes=100_000)
    return DbDisclosureStore(factory, owners, DisclosureLimits(host=limit, purpose=limit), owners)


@pytest.mark.asyncio
async def test_read_evidence_does_not_create_live_authority() -> None:
    row = _row()
    store = _store(row)
    snapshot = await store.read(row.id)
    assert snapshot is not None
    assert snapshot.status == "prepared"
    claim = FreshDisclosureClaim(snapshot.preparation, uuid4())
    with pytest.raises(DisclosureError, match="claim"):
        store.consume(claim)
    assert await _store(None).read(uuid4()) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    [
        "preparation_digest",
        "id",
        "request_id",
        "run_id",
        "delivery_id",
        "occurrence_id",
        "attempt_id",
        "preparation_bytes",
        "claim_id",
    ],
)
async def test_corrupted_preparation_or_owner_columns_refuse(field: str) -> None:
    row = _row()
    values = {"preparation_digest": "f" * 64, "preparation_bytes": row.preparation_bytes + b" ", "claim_id": uuid4()}
    setattr(row, field, values.get(field, uuid4()))
    with pytest.raises(DisclosureError, match="conflict"):
        await _store(row).read(row.id)


def _claim_row() -> DisclosureTransmission:
    row = _row()
    preparation = DisclosurePreparation.model_validate_json(row.preparation_bytes)
    row.status, row.claim_id, row.claimed_at = "claimed", uuid4(), datetime.now(UTC)
    assert row.claim_id is not None
    assert row.claimed_at is not None
    decision = DisclosureDecision(
        preparation_digest=preparation.digest,
        claim_id=cast("UUID", row.claim_id),
        charged_bytes=preparation.candidate_size,
        admitted_at=cast("datetime", row.claimed_at),
    )
    row.decision_bytes = canonical_bytes(decision.model_dump(mode="json"))
    return row


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["preparation_digest", "claim_id", "charged_bytes", "admitted_at", "encoding"])
async def test_corrupted_decision_binding_refuses(field: str) -> None:
    row = _claim_row()
    assert row.decision_bytes is not None
    decision = DisclosureDecision.model_validate_json(row.decision_bytes)
    values = {
        "preparation_digest": "f" * 64,
        "claim_id": uuid4(),
        "charged_bytes": 0,
        "admitted_at": datetime(2000, 1, 1, tzinfo=UTC),
    }
    row.decision_bytes = (
        row.decision_bytes + b" "
        if field == "encoding"
        else canonical_bytes(decision.model_copy(update={field: values[field]}).model_dump(mode="json"))
    )
    with pytest.raises(DisclosureError, match="conflict"):
        await _store(row).read(row.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["receipt_id", "transmission_id", "claim_id", "outcome", "encoding"])
async def test_corrupted_settlement_binding_refuses(field: str) -> None:
    row = _claim_row()
    assert row.claim_id is not None
    row.status, row.receipt_id = "recorded", uuid4()
    assert row.receipt_id is not None
    settlement = DisclosureSettlement(
        receipt_id=cast("UUID", row.receipt_id), transmission_id=row.id, claim_id=row.claim_id, outcome="recorded"
    )
    values = {"receipt_id": uuid4(), "transmission_id": uuid4(), "claim_id": uuid4(), "outcome": "unknown"}
    row.settlement_bytes = (
        canonical_bytes(settlement) + b" "
        if field == "encoding"
        else canonical_bytes(settlement.model_copy(update={field: values[field]}))
    )
    with pytest.raises(DisclosureError, match="conflict"):
        await _store(row).read(row.id)


@pytest.mark.asyncio
async def test_unknown_with_no_completion_is_valid_and_not_authority() -> None:
    row = _claim_row()
    row.status = "unknown"
    result = await _store(row).read(row.id)
    assert result is not None
    assert result.status == "unknown"
    assert result.receipt_id is None


@pytest.mark.asyncio
async def test_foreign_database_error_has_only_closed_public_projection() -> None:
    private_content = "SYNTHETIC-PRIVATE-DRIVER-CONTENT"
    with pytest.raises(DisclosureError, match="store") as caught:
        await _store(None, RuntimeError(private_content)).read(uuid4())
    assert private_content not in str(caught.value)
    assert caught.value.__suppress_context__
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_restricted_evidence_excludes_raw_source_subject_spans_and_candidate() -> None:
    row = _claim_row()
    snapshot = await _store(row).read(row.id)
    assert snapshot is not None
    evidence = row.preparation_bytes + (row.decision_bytes or b"")
    assert b"SYNTHETIC-PERSON-017" not in evidence
    assert b"Build node-a" not in evidence
    assert str(UUID(int=101)).encode() not in evidence
    assert b"sensitive_spans" not in evidence
    assert b"credential" not in evidence
