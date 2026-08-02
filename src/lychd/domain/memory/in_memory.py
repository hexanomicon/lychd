"""Loop-local in-memory adapter for the candidate Archive contract."""

from __future__ import annotations

import asyncio

from lychd.domain.memory.models import (
    CandidateArchiveRecord,
    CandidateDerivative,
    CandidateProcessingState,
    RawCandidate,
)
from lychd.domain.memory.ports import (
    CandidateArchiveIdentityConflictError,
    CandidateLineageError,
    IllegalCandidateProcessingTransitionError,
    StaleCandidateProcessingAttemptError,
    UnknownCandidateError,
)

__all__ = ["InMemoryCandidateArchive"]


class InMemoryCandidateArchive:
    """Atomic, loop-confined adapter with no durability or runtime integration."""

    def __init__(self) -> None:
        """Create one empty adapter for use within a single event loop."""
        self._records: dict[str, CandidateArchiveRecord] = {}
        self._ingestion_index: dict[str, str] = {}
        self._derivatives: dict[str, CandidateDerivative] = {}
        self._derivation_index: dict[str, str] = {}
        self._derivation_sources: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def admit_raw(self, candidate: RawCandidate) -> tuple[CandidateArchiveRecord, bool]:
        """Admit exact retries once and reject every semantic identity collision."""
        async with self._lock:
            existing = self._records.get(candidate.candidate_id)
            if existing is not None:
                _require_same_identity(
                    existing.candidate,
                    candidate,
                    identity=f"candidate id {candidate.candidate_id!r}",
                )
                return existing, False
            if candidate.candidate_id in self._derivatives:
                _raise_identity_conflict(f"record id {candidate.candidate_id!r}")

            existing_id = self._ingestion_index.get(candidate.ingestion_key)
            if existing_id is not None:
                existing = self._records[existing_id]
                _require_same_identity(
                    existing.candidate,
                    candidate,
                    identity=f"ingestion key {candidate.ingestion_key!r}",
                )
                return existing, False

            record = CandidateArchiveRecord(candidate=candidate)
            self._records[candidate.candidate_id] = record
            self._ingestion_index[candidate.ingestion_key] = candidate.candidate_id
            return record, True

    async def get_raw(self, candidate_id: str) -> CandidateArchiveRecord | None:
        async with self._lock:
            return self._records.get(candidate_id)

    async def get_raw_by_ingestion_key(self, ingestion_key: str) -> CandidateArchiveRecord | None:
        async with self._lock:
            candidate_id = self._ingestion_index.get(ingestion_key)
            return self._records.get(candidate_id) if candidate_id is not None else None

    async def transition_processing(
        self,
        candidate_id: str,
        state: CandidateProcessingState,
        *,
        attempt: int | None = None,
        failure_code: str | None = None,
    ) -> tuple[CandidateArchiveRecord, bool]:
        """Replace the immutable read model after one legal processing edge."""
        async with self._lock:
            record = self._require_raw(candidate_id)
            if record.state is state:
                _require_matching_attempt(record, state, attempt)
                if record.failure_code != failure_code:
                    msg = f"Processing state {state.value!r} for candidate {candidate_id!r} was reused differently."
                    raise IllegalCandidateProcessingTransitionError(msg)
                return record, False
            if not _is_legal_transition(record.state, state):
                msg = f"Illegal candidate processing transition for {candidate_id!r}: {record.state} -> {state}"
                raise IllegalCandidateProcessingTransitionError(msg)
            _require_failure_shape(state, failure_code)
            next_attempt = _next_processing_attempt(record, state, attempt)

            updated = CandidateArchiveRecord(
                candidate=record.candidate,
                state=state,
                processing_attempt=next_attempt,
                failure_code=failure_code,
            )
            self._records[candidate_id] = updated
            return updated, True

    async def admit_derivative(self, derivative: CandidateDerivative) -> tuple[CandidateDerivative, bool]:
        """Admit an exact derivative retry only while its raw source is processing."""
        async with self._lock:
            existing = self._derivatives.get(derivative.derivative_id)
            if existing is not None:
                _require_same_identity(
                    existing,
                    derivative,
                    identity=f"derivative id {derivative.derivative_id!r}",
                )
                self._require_current_derivative(existing)
                return existing, False
            if derivative.derivative_id in self._records:
                _raise_identity_conflict(f"record id {derivative.derivative_id!r}")

            bound_source_id = self._derivation_sources.get(derivative.derivation_key)
            if bound_source_id is not None and bound_source_id != derivative.source_candidate_id:
                _raise_identity_conflict(f"derivation key {derivative.derivation_key!r}")

            existing_id = self._derivation_index.get(derivative.derivation_key)
            if existing_id is not None:
                existing = self._derivatives[existing_id]
                if self._derivative_is_current(existing):
                    _require_same_identity(
                        existing,
                        derivative,
                        identity=f"derivation key {derivative.derivation_key!r}",
                    )
                    return existing, False

            source = self._require_raw(derivative.source_candidate_id)
            if source.state is not CandidateProcessingState.PROCESSING:
                msg = (
                    f"Derivative {derivative.derivative_id!r} requires source "
                    f"{derivative.source_candidate_id!r} to be processing."
                )
                raise CandidateLineageError(msg)
            if derivative.processing_attempt != source.processing_attempt:
                msg = (
                    f"Derivative {derivative.derivative_id!r} belongs to processing attempt "
                    f"{derivative.processing_attempt}, not current attempt {source.processing_attempt}."
                )
                raise CandidateLineageError(msg)
            if derivative.derived_at < source.candidate.observed_at:
                msg = f"Derivative {derivative.derivative_id!r} cannot predate its raw source observation."
                raise CandidateLineageError(msg)
            source_attribution = source.candidate.attribution
            derivative_attribution = derivative.attribution
            if (
                source_attribution.namespace_id != derivative_attribution.namespace_id
                or source_attribution.subject_id != derivative_attribution.subject_id
            ):
                msg = f"Derivative {derivative.derivative_id!r} crosses its source attribution boundary."
                raise CandidateLineageError(msg)

            self._derivatives[derivative.derivative_id] = derivative
            self._derivation_index[derivative.derivation_key] = derivative.derivative_id
            self._derivation_sources.setdefault(
                derivative.derivation_key,
                derivative.source_candidate_id,
            )
            return derivative, True

    async def get_derivative(self, derivative_id: str) -> CandidateDerivative | None:
        async with self._lock:
            derivative = self._derivatives.get(derivative_id)
            return derivative if derivative is not None and self._derivative_is_current(derivative) else None

    async def get_derivative_by_derivation_key(self, derivation_key: str) -> CandidateDerivative | None:
        async with self._lock:
            derivative_id = self._derivation_index.get(derivation_key)
            derivative = self._derivatives.get(derivative_id) if derivative_id is not None else None
            return derivative if derivative is not None and self._derivative_is_current(derivative) else None

    def _require_current_derivative(self, derivative: CandidateDerivative) -> None:
        source = self._require_raw(derivative.source_candidate_id)
        if not self._derivative_is_current(derivative, source=source):
            msg = (
                f"Derivative {derivative.derivative_id!r} belongs to stale processing attempt "
                f"{derivative.processing_attempt}; source is {source.state.value} at attempt "
                f"{source.processing_attempt}."
            )
            raise CandidateLineageError(msg)

    def _derivative_is_current(
        self,
        derivative: CandidateDerivative,
        *,
        source: CandidateArchiveRecord | None = None,
    ) -> bool:
        source = source or self._records.get(derivative.source_candidate_id)
        return (
            source is not None
            and source.processing_attempt == derivative.processing_attempt
            and source.state in {CandidateProcessingState.PROCESSING, CandidateProcessingState.PROCESSED}
        )

    def _require_raw(self, candidate_id: str) -> CandidateArchiveRecord:
        try:
            return self._records[candidate_id]
        except KeyError as exc:
            msg = f"Unknown raw candidate: {candidate_id!r}"
            raise UnknownCandidateError(msg) from exc


def _require_same_identity[T](existing: T, incoming: T, *, identity: str) -> None:
    if existing != incoming:
        _raise_identity_conflict(identity)


def _raise_identity_conflict(identity: str) -> None:
    msg = f"Archive {identity} was reused with different semantics."
    raise CandidateArchiveIdentityConflictError(msg)


def _require_matching_attempt(
    record: CandidateArchiveRecord,
    state: CandidateProcessingState,
    attempt: int | None,
) -> None:
    if state in {CandidateProcessingState.PROCESSED, CandidateProcessingState.FAILED} and attempt is None:
        msg = f"Replaying processing state {state.value!r} requires its processing attempt."
        raise IllegalCandidateProcessingTransitionError(msg)
    if attempt is not None and attempt != record.processing_attempt:
        _raise_stale_attempt(
            record.candidate.candidate_id,
            expected=record.processing_attempt,
            received=attempt,
        )


def _require_failure_shape(state: CandidateProcessingState, failure_code: str | None) -> None:
    if state is CandidateProcessingState.FAILED and failure_code is None:
        msg = "Failed processing requires a failure code."
        raise IllegalCandidateProcessingTransitionError(msg)
    if state is not CandidateProcessingState.FAILED and failure_code is not None:
        msg = "Only failed processing accepts a failure code."
        raise IllegalCandidateProcessingTransitionError(msg)


def _next_processing_attempt(
    record: CandidateArchiveRecord,
    target: CandidateProcessingState,
    attempt: int | None,
) -> int:
    candidate_id = record.candidate.candidate_id
    if target is CandidateProcessingState.PROCESSING:
        next_attempt = record.processing_attempt + 1
        if attempt is not None and attempt != next_attempt:
            _raise_stale_attempt(candidate_id, expected=next_attempt, received=attempt)
        return next_attempt
    if record.state is CandidateProcessingState.PROCESSING:
        if attempt is None:
            msg = f"Settling candidate {candidate_id!r} requires its processing attempt."
            raise IllegalCandidateProcessingTransitionError(msg)
        if attempt != record.processing_attempt:
            _raise_stale_attempt(candidate_id, expected=record.processing_attempt, received=attempt)
        return record.processing_attempt

    next_attempt = record.processing_attempt + 1
    if attempt is None:
        msg = f"Failing candidate {candidate_id!r} requires its processing attempt."
        raise IllegalCandidateProcessingTransitionError(msg)
    if attempt != next_attempt:
        _raise_stale_attempt(candidate_id, expected=next_attempt, received=attempt)
    return next_attempt


def _raise_stale_attempt(candidate_id: str, *, expected: int, received: int) -> None:
    msg = f"Stale processing attempt for {candidate_id!r}: expected {expected}, received {received}."
    raise StaleCandidateProcessingAttemptError(msg)


def _is_legal_transition(current: CandidateProcessingState, target: CandidateProcessingState) -> bool:
    match current:
        case CandidateProcessingState.PENDING:
            return target in {CandidateProcessingState.PROCESSING, CandidateProcessingState.FAILED}
        case CandidateProcessingState.PROCESSING:
            return target in {CandidateProcessingState.PROCESSED, CandidateProcessingState.FAILED}
        case CandidateProcessingState.FAILED:
            return target is CandidateProcessingState.PROCESSING
        case CandidateProcessingState.PROCESSED:
            return False
