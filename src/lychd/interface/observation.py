"""Content-free, best-effort observations shared by concrete transport drivers.

A driver owns its observer. Observation failures, including cancellation raised
by a sink, cannot change the operation. Context is explicit and task-local;
transport results never imply an authoritative effect settlement.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

MAX_OBSERVATION_BYTES = 2048


def _uuid(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "observation_identity"
        raise ValueError(msg)
    return value


type ObservationUuid = Annotated[str, AfterValidator(_uuid)]
type ObservationId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
type ObservationPhase = Literal["started", "succeeded", "failed", "cancelled", "unknown"]
type ObservationError = Literal["timeout", "cancelled", "transport", "protocol", "refused", "unavailable", "unknown"]


class OperationObservation(BaseModel):
    """One closed transport/effect observation, without arbitrary metadata or paths."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)
    kind: Literal["operation_observation"] = "operation_observation"
    schema_version: Literal[1] = 1
    generation: ObservationUuid
    producer_id: ObservationId
    event_id: ObservationUuid = Field(default_factory=lambda: str(uuid4()))
    operation_id: ObservationUuid
    attempt_id: ObservationUuid
    seq: int = Field(ge=1, le=2**53 - 1)
    observed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    source: ObservationId
    target: ObservationId
    operation: ObservationId
    activity_kind: Literal["transport_attempt", "transport_result", "operation_result"]
    phase: ObservationPhase
    http_status: int | None = Field(default=None, ge=100, le=599)
    error_category: ObservationError | None = None
    elapsed_ms: float | None = Field(default=None, ge=0, le=86_400_000)
    run_id: ObservationUuid | None = None
    request_id: ObservationUuid | None = None
    station_attempt_id: ObservationUuid | None = None
    effect_outcome: Literal["succeeded", "failed", "unknown"] | None = None


type ObservationSink = Callable[[OperationObservation], None]
_CORRELATION: ContextVar[tuple[str | None, str | None]] = ContextVar("operation_correlation", default=(None, None))


@contextmanager
def observation_context(*, run_id: str | None, request_id: str | None = None) -> Generator[None]:
    """Bind only supplied canonical Run/request UUIDs for the exact lexical operation."""
    values: list[str | None] = []
    for value in (run_id, request_id):
        try:
            values.append(_uuid(value) if value is not None else None)
        except ValueError:
            values.append(None)
    token = _CORRELATION.set((values[0], values[1]))
    try:
        yield
    finally:
        _CORRELATION.reset(token)


def observation_bytes(value: OperationObservation) -> bytes:
    """Serialize bounded metadata only, suitable for one atomic diagnostic pipe write."""
    raw = value.model_dump_json(exclude_none=True).encode("ascii") + b"\n"
    if len(raw) > MAX_OBSERVATION_BYTES:
        msg = "observation_limit"
        raise ValueError(msg)
    return raw


class OperationObserver:
    """Sequence observations for one explicitly bound driver and process generation."""

    def __init__(
        self, *, generation: str, producer_id: str, source: str, target: str, sink: ObservationSink | None = None
    ) -> None:
        """Bind structural identities once; callers never pass URLs or credentials."""
        self.generation, self.producer_id = generation, producer_id
        self.source, self.target, self.sink = source, target, sink
        self.sequence = 0

    def operation(self, name: str, *, target: str | None = None) -> ObservedOperation:
        return ObservedOperation(self, name, target=target)

    def emit(
        self,
        operation: ObservedOperation,
        kind: Literal["transport_attempt", "transport_result", "operation_result"],
        phase: ObservationPhase,
        *,
        error: ObservationError | None = None,
        outcome: Literal["succeeded", "failed", "unknown"] | None = None,
    ) -> None:
        self.sequence += 1
        if self.sink is None:
            return
        try:
            self.sink(
                OperationObservation(
                    generation=self.generation,
                    producer_id=self.producer_id,
                    operation_id=operation.identity,
                    attempt_id=operation.attempt_id,
                    seq=self.sequence,
                    source=operation.source,
                    target=operation.target,
                    operation=operation.name,
                    activity_kind=kind,
                    phase=phase,
                    http_status=operation.http_status,
                    error_category=error,
                    elapsed_ms=min(86_400_000.0, max(0.0, (time.monotonic() - operation.started) * 1000)),
                    run_id=operation.run_id,
                    request_id=operation.request_id,
                    effect_outcome=outcome,
                )
            )
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - observers cannot cancel execution
            return


class ObservedOperation:
    """One actual attempt and its separately observed effect settlement."""

    def __init__(self, observer: OperationObserver, name: str, *, target: str | None = None) -> None:
        """Create identities without emitting until the driver starts transport."""
        self.observer, self.name = observer, name
        self.source, self.target = observer.source, target or observer.target
        self.identity, self.attempt_id = str(uuid4()), str(uuid4())
        self.run_id, self.request_id = _CORRELATION.get()
        self.started = time.monotonic()
        self.http_status: int | None = None

    def next_attempt(self, *, name: str | None = None, target: str | None = None) -> ObservedOperation:
        """Allocate a distinct dispatch under this same explicitly correlated operation."""
        attempt = ObservedOperation(self.observer, name or self.name, target=target or self.target)
        attempt.identity = self.identity
        attempt.run_id, attempt.request_id = self.run_id, self.request_id
        return attempt

    def start(self) -> None:
        self.started = time.monotonic()
        self.observer.emit(self, "transport_attempt", "started")

    def finish(self, phase: ObservationPhase, *, error: ObservationError | None = None) -> None:
        self.observer.emit(self, "transport_result", phase, error=error)

    def settle(self, outcome: Literal["succeeded", "failed", "unknown"]) -> None:
        self.observer.emit(self, "operation_result", outcome, outcome=outcome)
