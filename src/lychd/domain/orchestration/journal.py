"""Bounded process-local transition evidence shared by Graph and Nexus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from lychd.domain.orchestration.schema import TransitionTrace


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionRecord:
    """Immutable observation of one orchestration request at its latest phase."""

    request_id: str
    source: Literal["run", "operator"]
    target_capability_key: str
    priority: float
    phase: str
    requested_at: datetime
    observed_at: datetime
    run_id: str | None
    occurrence_id: str | None
    action_type: str | None
    physical_transition_id: str | None
    compensation_transition_id: str | None
    detail: str | None


class TransitionJournal:
    """Loop-confined bounded latest-state journal for every transition source."""

    def __init__(self, *, capacity: int = 512) -> None:
        """Create an empty bounded latest-observation store."""
        if capacity < 1:
            msg = "Transition journal capacity must be positive."
            raise ValueError(msg)
        self._capacity = capacity
        self._records: dict[str, TransitionRecord] = {}

    def record(self, trace: TransitionTrace) -> TransitionRecord:
        """Snapshot a mutable trace without retaining host handles or callbacks."""
        record = TransitionRecord(
            request_id=trace.request_id,
            source="run" if trace.run_id is not None else "operator",
            target_capability_key=trace.target_capability_key,
            priority=trace.priority,
            phase=trace.phase,
            requested_at=trace.requested_at,
            observed_at=datetime.now(UTC),
            run_id=trace.run_id,
            occurrence_id=trace.occurrence_id,
            action_type=trace.plan.action_type if trace.plan is not None else None,
            physical_transition_id=trace.physical_transition_id,
            compensation_transition_id=trace.compensation_transition_id,
            detail=trace.detail,
        )
        if trace.request_id in self._records:
            self._records.pop(trace.request_id)
        elif len(self._records) >= self._capacity:
            oldest = next(iter(self._records))
            self._records.pop(oldest)
        self._records[trace.request_id] = record
        return record

    def get(self, request_id: str) -> TransitionRecord | None:
        """Return the latest retained observation for one request."""
        return self._records.get(request_id)

    def recent(self, *, limit: int = 24) -> tuple[TransitionRecord, ...]:
        """Return newest observations first, bounded by the caller and journal."""
        bounded = min(max(limit, 1), self._capacity)
        return tuple(reversed(tuple(self._records.values())))[:bounded]
