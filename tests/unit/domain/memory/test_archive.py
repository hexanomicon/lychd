from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lychd.domain.memory import (
    CandidateArchiveIdentityConflictError,
    CandidateArchivePort,
    CandidateArchiveRecord,
    CandidateAttribution,
    CandidateDerivative,
    CandidateLineageError,
    CandidateProcessingState,
    IllegalCandidateProcessingTransitionError,
    InMemoryCandidateArchive,
    RawCandidate,
    StaleCandidateProcessingAttemptError,
    UnknownCandidateError,
)

_OBSERVED_AT = datetime(2026, 8, 2, 8, 0, tzinfo=UTC)
_DERIVED_AT = datetime(2026, 8, 2, 8, 1, tzinfo=UTC)


def _attribution(
    *,
    namespace_id: str = "namespace:operator",
    subject_id: str = "subject:magus",
    producer_id: str = "producer:bridge",
    producer_revision: str = "revision:1",
) -> CandidateAttribution:
    return CandidateAttribution(
        namespace_id=namespace_id,
        subject_id=subject_id,
        producer_id=producer_id,
        producer_revision=producer_revision,
        session_id="session:1",
        run_id="run:1",
    )


def _raw(
    *,
    candidate_id: str = "candidate:1",
    ingestion_key: str = "ingestion:source-1:unit-1",
    content: str = "The operator prefers explicit admission.",
    attribution: CandidateAttribution | None = None,
) -> RawCandidate:
    return RawCandidate(
        candidate_id=candidate_id,
        ingestion_key=ingestion_key,
        attribution=attribution or _attribution(),
        source_ref="bridge://sessions/session:1/turns/1",
        source_revision="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        kind="conversation-turn",
        content=content,
        observed_at=_OBSERVED_AT,
    )


def _derivative(
    *,
    derivative_id: str = "derivative:1",
    derivation_key: str = "derivation:candidate-1:summary-v1",
    source_candidate_id: str = "candidate:1",
    processing_attempt: int = 1,
    content: str = "Explicit admission is preferred.",
    attribution: CandidateAttribution | None = None,
    derived_at: datetime = _DERIVED_AT,
) -> CandidateDerivative:
    return CandidateDerivative(
        derivative_id=derivative_id,
        derivation_key=derivation_key,
        source_candidate_id=source_candidate_id,
        processing_attempt=processing_attempt,
        attribution=attribution
        or _attribution(
            producer_id="producer:extractor",
            producer_revision="revision:summary-v1",
        ),
        kind="summary",
        content=content,
        derived_at=derived_at,
    )


def test_models_are_frozen_extra_forbid_and_bounded() -> None:
    models = (_attribution(), _raw(), _derivative(), CandidateArchiveRecord(candidate=_raw()))
    for model in models:
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("extra") == "forbid"

    with pytest.raises(ValidationError):
        RawCandidate.model_validate({**_raw().model_dump(), "transparent_interception": True})
    with pytest.raises(ValidationError):
        _raw(content="x" * 1_048_577)
    with pytest.raises(ValidationError):
        _raw(content="   ")
    field_name = "content"
    with pytest.raises(ValidationError):
        setattr(_raw(), field_name, "mutated")


def test_processing_record_requires_failure_code_only_for_failure() -> None:
    with pytest.raises(ValidationError):
        CandidateArchiveRecord(candidate=_raw(), state=CandidateProcessingState.FAILED)
    with pytest.raises(ValidationError):
        CandidateArchiveRecord(candidate=_raw(), failure_code="extractor-failed")


@pytest.mark.asyncio
async def test_adapter_satisfies_port_and_raw_admission_is_idempotent() -> None:
    archive = InMemoryCandidateArchive()
    candidate = _raw()

    assert isinstance(archive, CandidateArchivePort)
    admitted, created = await archive.admit_raw(candidate)
    replayed, replay_created = await archive.admit_raw(candidate)

    assert created is True
    assert replay_created is False
    assert admitted == replayed
    assert admitted.state is CandidateProcessingState.PENDING
    assert await archive.get_raw(candidate.candidate_id) == admitted
    assert await archive.get_raw_by_ingestion_key(candidate.ingestion_key) == admitted


@pytest.mark.asyncio
async def test_raw_record_id_reuse_with_different_semantics_fails_closed() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())

    with pytest.raises(CandidateArchiveIdentityConflictError, match="candidate id"):
        await archive.admit_raw(_raw(content="Different source meaning."))


@pytest.mark.asyncio
async def test_ingestion_key_reuse_with_a_new_record_id_fails_closed() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())

    with pytest.raises(CandidateArchiveIdentityConflictError, match="ingestion key"):
        await archive.admit_raw(_raw(candidate_id="candidate:2"))


@pytest.mark.asyncio
async def test_processing_state_has_only_declared_idempotent_edges() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())

    with pytest.raises(IllegalCandidateProcessingTransitionError):
        await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSED)

    processing, changed = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSING,
    )
    replayed, replay_changed = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSING,
    )
    processed, completed = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSED,
        attempt=processing.processing_attempt,
    )

    assert changed is True
    assert processing.processing_attempt == 1
    assert replay_changed is False
    assert replayed == processing
    assert completed is True
    assert processed.state is CandidateProcessingState.PROCESSED

    with pytest.raises(IllegalCandidateProcessingTransitionError):
        await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)


@pytest.mark.asyncio
async def test_failed_processing_can_retry_but_failure_semantics_cannot_change_in_place() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    failed, changed = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.FAILED,
        attempt=1,
        failure_code="extractor-unavailable",
    )

    assert changed is True
    assert failed.failure_code == "extractor-unavailable"
    with pytest.raises(IllegalCandidateProcessingTransitionError):
        await archive.transition_processing(
            "candidate:1",
            CandidateProcessingState.FAILED,
            attempt=1,
            failure_code="different-failure",
        )

    retrying, retried = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSING,
    )
    assert retried is True
    assert retrying.processing_attempt == 2
    assert retrying.failure_code is None


@pytest.mark.asyncio
async def test_retry_fences_stale_settlement_and_derivative_lineage() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    first, _ = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSING,
    )
    await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.FAILED,
        attempt=first.processing_attempt,
        failure_code="extractor-unavailable",
    )
    second, _ = await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.PROCESSING,
    )

    with pytest.raises(StaleCandidateProcessingAttemptError, match="expected 2, received 1"):
        await archive.transition_processing(
            "candidate:1",
            CandidateProcessingState.PROCESSED,
            attempt=first.processing_attempt,
        )
    with pytest.raises(CandidateLineageError, match="attempt 1, not current attempt 2"):
        await archive.admit_derivative(
            _derivative(derivative_id="derivative:stale", processing_attempt=first.processing_attempt)
        )

    admitted, created = await archive.admit_derivative(
        _derivative(derivative_id="derivative:current", processing_attempt=second.processing_attempt)
    )
    assert created is True
    assert admitted.processing_attempt == 2


@pytest.mark.asyncio
async def test_retry_hides_and_rejects_a_derivative_from_the_failed_attempt() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    first, _ = await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    derivative = _derivative(processing_attempt=first.processing_attempt)
    await archive.admit_derivative(derivative)
    await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.FAILED,
        attempt=first.processing_attempt,
        failure_code="extractor-unavailable",
    )
    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)

    assert await archive.get_derivative(derivative.derivative_id) is None
    assert await archive.get_derivative_by_derivation_key(derivative.derivation_key) is None
    with pytest.raises(CandidateLineageError, match="stale processing attempt"):
        await archive.admit_derivative(derivative)


@pytest.mark.asyncio
async def test_retry_can_replace_a_stale_derivation_key_with_current_attempt_output() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    first, _ = await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    stale = _derivative(processing_attempt=first.processing_attempt)
    await archive.admit_derivative(stale)
    await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.FAILED,
        attempt=first.processing_attempt,
        failure_code="extractor-unavailable",
    )
    second, _ = await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    replacement = _derivative(
        derivative_id="derivative:2",
        processing_attempt=second.processing_attempt,
        content="The current attempt produced this summary.",
    )

    admitted, created = await archive.admit_derivative(replacement)

    assert created is True
    assert admitted == replacement
    assert await archive.get_derivative_by_derivation_key(replacement.derivation_key) == replacement
    assert await archive.get_derivative(stale.derivative_id) is None


@pytest.mark.asyncio
async def test_stale_derivation_key_remains_bound_to_its_original_raw_source() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    first, _ = await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    stale = _derivative(processing_attempt=first.processing_attempt)
    await archive.admit_derivative(stale)
    await archive.transition_processing(
        "candidate:1",
        CandidateProcessingState.FAILED,
        attempt=first.processing_attempt,
        failure_code="extractor-unavailable",
    )
    await archive.admit_raw(_raw(candidate_id="candidate:2", ingestion_key="ingestion:source-2:unit-1"))
    await archive.transition_processing("candidate:2", CandidateProcessingState.PROCESSING)

    with pytest.raises(CandidateArchiveIdentityConflictError, match="derivation key"):
        await archive.admit_derivative(
            _derivative(
                derivative_id="derivative:2",
                source_candidate_id="candidate:2",
            )
        )


@pytest.mark.asyncio
async def test_processing_unknown_candidate_fails_closed() -> None:
    archive = InMemoryCandidateArchive()

    with pytest.raises(UnknownCandidateError):
        await archive.transition_processing("candidate:missing", CandidateProcessingState.PROCESSING)


@pytest.mark.asyncio
async def test_derivative_requires_processing_source_and_preserves_lineage() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())

    with pytest.raises(CandidateLineageError, match="to be processing"):
        await archive.admit_derivative(_derivative())

    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    derivative = _derivative()
    admitted, created = await archive.admit_derivative(derivative)
    replayed, replay_created = await archive.admit_derivative(derivative)

    assert created is True
    assert replay_created is False
    assert replayed == admitted
    assert admitted.source_candidate_id == "candidate:1"
    assert await archive.get_derivative("derivative:1") == admitted
    assert await archive.get_derivative_by_derivation_key(derivative.derivation_key) == admitted


@pytest.mark.asyncio
async def test_derivative_rejects_unknown_or_cross_attribution_source() -> None:
    archive = InMemoryCandidateArchive()

    with pytest.raises(UnknownCandidateError):
        await archive.admit_derivative(_derivative(source_candidate_id="candidate:missing"))

    await archive.admit_raw(_raw())
    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    with pytest.raises(CandidateLineageError, match="attribution boundary"):
        await archive.admit_derivative(
            _derivative(attribution=_attribution(subject_id="subject:someone-else")),
        )


@pytest.mark.asyncio
async def test_derivative_cannot_predate_its_raw_source() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)

    with pytest.raises(CandidateLineageError, match="cannot predate"):
        await archive.admit_derivative(_derivative(derived_at=_OBSERVED_AT.replace(minute=59, hour=7)))


@pytest.mark.asyncio
async def test_derivative_ids_and_derivation_keys_cannot_change_meaning() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)
    await archive.admit_derivative(_derivative())

    with pytest.raises(CandidateArchiveIdentityConflictError, match="derivative id"):
        await archive.admit_derivative(_derivative(content="Different derivative."))
    with pytest.raises(CandidateArchiveIdentityConflictError, match="derivation key"):
        await archive.admit_derivative(_derivative(derivative_id="derivative:2"))


@pytest.mark.asyncio
async def test_raw_and_derivative_record_ids_share_one_collision_domain() -> None:
    archive = InMemoryCandidateArchive()
    await archive.admit_raw(_raw())
    await archive.transition_processing("candidate:1", CandidateProcessingState.PROCESSING)

    with pytest.raises(CandidateArchiveIdentityConflictError, match="record id"):
        await archive.admit_derivative(_derivative(derivative_id="candidate:1"))
