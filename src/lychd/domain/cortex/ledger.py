"""Canonical Run, delivery, and Step persistence contracts.

The loop-confined in-memory adapter and durable PostgreSQL adapter enforce the same
Run transition law. Exact delivery generations fence claims and settlement. Callers
retain ownership of higher-level transitions: ``RunEngine`` admits and cancels,
while ``perform_run`` claims, parks, and settles execution.

Non-token events may be retained as Step evidence. Token deltas remain live-only;
settled text belongs to the session turn.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import (
    TERMINAL_STATUSES,
    IllegalRunTransitionError,
    RunDeliveryRecord,
    RunDeliveryState,
    RunRecord,
    RunStatus,
    can_transition,
)

if TYPE_CHECKING:
    from sqlalchemy import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEvent

__all__ = [
    "ConsentAdmissionEvidence",
    "DbRunLedger",
    "InMemoryRunLedger",
    "RunAdmissionConflictError",
    "RunLedger",
]


@dataclass(frozen=True, kw_only=True)
class ConsentAdmissionEvidence:
    """Settled consent truth required by the non-durable Run adapter.

    PostgreSQL re-reads and locks the canonical Consent row in the same transaction.
    The loop-confined adapter has no shared database, so its caller must supply the
    exact verdict read from the consent authority before the admission CAS.
    """

    consent_id: str
    run_id: str
    status: str
    decided_by: str
    decided_at: datetime


class RunAdmissionConflictError(ValueError):
    """An idempotency identity was replayed with a different durable intent."""


def _idempotent_run_uuid(idempotency_key: str) -> UUID:
    """Derive a server-owned canonical Run identity from one scoped admission key."""
    return uuid5(NAMESPACE_URL, f"lychd:run-admission:{idempotency_key}")


def _assert_idempotent_replay(record: RunRecord, intent: Intent) -> None:
    """Reject reuse of one admission key for materially different work."""
    if (
        record.session_id != intent.session_id
        or record.prompt != intent.prompt
        or record.source != intent.source
        or record.sigil_name != intent.sigil_name
        or record.sigil_scopes != intent.sigil_scopes
        or record.content != intent.content
        or record.requested_priority != intent.priority
    ):
        msg = "Run admission idempotency key was reused with a different intent."
        raise RunAdmissionConflictError(msg)


def _intent_payload(intent: Intent, *, idempotency_key: str | None = None) -> dict[str, Any]:
    """Serialize the durable Intent plus optional admission identity."""
    return {
        "session_id": intent.session_id,
        "run_id": intent.run_id,
        "prompt": intent.prompt,
        "content": [part.model_dump(mode="json") for part in intent.content],
        "source": intent.source,
        "sigil_name": intent.sigil_name,
        "sigil_scopes": sorted(intent.sigil_scopes),
        "priority": intent.priority,
        **({"idempotency_key": idempotency_key} if idempotency_key is not None else {}),
    }


def _legacy_pattern_manifest(workflow_name: str) -> dict[str, Any]:
    """Identify a run created outside RunEngine or predating Pattern pinning.

    This is an explicit non-resumable compatibility marker, not a fabricated current
    revision. Production admission passes the exact Workflow manifest.
    """
    return {
        "schema_version": 0,
        "key": workflow_name,
        "revision": "legacy-unversioned",
        "checkpoint_schema": "unknown",
        "nodes": [],
        "edges": [],
        "digest": None,
    }


class RunLedger(Protocol):
    """The run-truth surface consumed by the engine and the ghoul plane."""

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> RunRecord:
        """Persist a fresh run and its initial delivery intent atomically."""
        ...

    async def create_idempotent(
        self,
        intent: Intent,
        *,
        idempotency_key: str,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> tuple[RunRecord, bool]:
        """Create once or return the exact prior admission and whether this call created it."""
        ...

    async def get_idempotent(self, intent: Intent, *, idempotency_key: str) -> RunRecord | None:
        """Return and validate a prior admission without routing fresh work."""
        ...

    async def get_delivery(self, run_id: str, *, enqueue_seq: int) -> RunDeliveryRecord | None:
        """Return one exact durable delivery hop, or ``None`` if it is absent."""
        ...

    async def release_delivery(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Move a caller-context-gated delivery from HELD to PENDING."""
        ...

    async def mark_delivery_published(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Record an acknowledged broker publication without overwriting a claim."""
        ...

    async def note_delivery_error(self, run_id: str, *, enqueue_seq: int, error: str) -> None:
        """Retain one publication failure while leaving the delivery retryable."""
        ...

    async def get(self, run_id: str) -> RunRecord | None:
        """Return the run record, or ``None`` if unknown."""
        ...

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a run's status (validated against the state machine)."""
        ...

    async def bump_enqueue_seq(self, run_id: str) -> int:
        """Increment and return the run's enqueue seq (unique SAQ keys across hops)."""
        ...

    async def rotate_delivery(self, run_id: str, *, enqueue_seq: int) -> int | None:
        """Replace one unclaimed delivery with a fresh key while preserving its mode."""
        ...

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Claim QUEUED → RUNNING only for this exact published delivery hop."""
        ...

    async def try_fail_queued(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Settle QUEUED → FAILED only for one exact unclaimed delivery hop."""
        ...

    async def try_fail_held(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail only the exact QUEUED delivery still held by admission."""
        ...

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail only the RUNNING/AWAITING_HARDWARE hop with this enqueue sequence."""
        ...

    async def begin_cancel(self, run_id: str) -> RunRecord | None:
        """Elect cancellation and return its exact current delivery snapshot."""
        ...

    async def finish_cancel(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Settle CANCELLING to CANCELLED only for the elected delivery generation."""
        ...

    async def try_settle_claim(
        self,
        run_id: str,
        *,
        enqueue_seq: int,
        status: RunStatus,
        error: str | None = None,
    ) -> bool:
        """Settle one exact claimed hop to a terminal status."""
        ...

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id a run is parked on."""
        ...

    async def park_consent(self, run_id: str, consent_id: str) -> None:
        """Atomically bind consent wait truth and settle the run's claimed delivery."""
        ...

    async def park_delegate(self, run_id: str, job_id: str) -> None:
        """Atomically bind a delegated job and move its owning run into wait."""
        ...

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event to the run's Step ledger."""
        ...

    @property
    def evidence_capture(self) -> str:
        """Describe this ledger's retained evidence boundary."""
        ...

    async def list_events(self, run_id: str, *, after_seq: int = -1, limit: int = 100) -> list[RunEvent]:
        """Return retained non-token events in per-run sequence order."""
        ...

    async def latest_event(self, run_id: str, kind: RunEventKind) -> RunEvent | None:
        """Return the newest retained event of one semantic kind."""
        ...

    async def next_seq(self, run_id: str) -> int:
        """Return the next unused Step seq for a run (max(seq)+1, or 0 if none)."""
        ...

    async def list_by_status(
        self,
        status: RunStatus,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int | None = None,
    ) -> list[RunRecord]:
        """Return a stable optional keyset page of runs in ``status``."""
        ...

    async def list_for_session(self, session_id: str) -> list[RunRecord]:
        """Return all Runs owned by one Bridge session in creation order."""
        ...

    async def list_delivery_candidates(
        self,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        """Return one stable keyset page of QUEUED Runs with relayable deliveries."""
        ...

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id`` (feeds `engine.approve`)."""
        ...

    async def try_admit_consent(
        self,
        run_id: str,
        *,
        consent_id: str,
        evidence: ConsentAdmissionEvidence | None = None,
    ) -> int | None:
        """Atomically admit a parked run and allocate its next enqueue sequence.

        The SINGLE resume-admission gate (F1/F4): returns the new sequence iff THIS
        caller performed the transition. Concurrent approves, and an `engine.approve`
        racing `perform_run`'s post-flip re-check, all funnel here so exactly one
        sequence is allocated and enqueued. ``consent_id`` must own the current wait
        so a historical verdict cannot advance a later gate. The in-memory adapter
        additionally requires exact settled evidence because it has no shared DB row
        to lock; PostgreSQL re-establishes the same truth transactionally.
        """
        ...

    async def try_admit_delegate(self, run_id: str, *, job_id: str) -> int | None:
        """Admit only the completed job that owns the current delegated wait."""
        ...


def _apply_status(record: RunRecord, status: RunStatus, *, error: str | None) -> None:
    """Mutate ``record`` for a validated status change (timestamps + error)."""
    if status is record.status:
        return  # idempotent no-op (a re-claim or duplicate terminal write)
    if not can_transition(record.status, status):
        raise IllegalRunTransitionError(record.run_id, record.status, status)
    if status is RunStatus.RUNNING and record.started_at is None:
        record.started_at = datetime.now(UTC)
    if status in TERMINAL_STATUSES:
        record.finished_at = datetime.now(UTC)
    record.status = status
    record.error = error
    record.updated_at = datetime.now(UTC)


def _settles_delivery(status: RunStatus) -> bool:
    return status in TERMINAL_STATUSES or status in {
        RunStatus.AWAITING_CONSENT,
        RunStatus.AWAITING_DELEGATE,
    }


def _reject_generic_resume(current: RunStatus, target: RunStatus, *, run_id: str) -> None:
    """Keep authority-bearing resume edges behind their owner-specific CAS methods."""
    if current in {RunStatus.AWAITING_CONSENT, RunStatus.AWAITING_DELEGATE} and target is RunStatus.QUEUED:
        raise IllegalRunTransitionError(run_id, current, target)


async def _settle_db_delivery(session: Any, run_id: UUID, enqueue_seq: int) -> None:
    from sqlalchemy import update

    from lychd.db.models import RunDelivery

    await session.execute(
        update(RunDelivery)
        .where(
            RunDelivery.run_id == run_id,
            RunDelivery.enqueue_seq == enqueue_seq,
            RunDelivery.state != RunDeliveryState.SETTLED.value,
        )
        .values(
            state=RunDeliveryState.SETTLED.value,
            settled_at=datetime.now(UTC),
        )
    )


class InMemoryRunLedger:
    """Loop-confined, DB-free Run ledger for tests and the memory profile."""

    def __init__(self, *, honor_intent_run_id: bool = False) -> None:
        """Create an empty ledger.

        `honor_intent_run_id` is a TEST-ONLY seam (default off): when set, `create`
        adopts `intent.run_id` as the canonical id so unit tests can key off stable
        ids. Production NEVER sets it — identity is always ledger-minted (R4/S3),
        mirroring `DbRunLedger` (whose id is always the row UUID). Do NOT overload
        the advisory `Intent.run_id` field to route identity in production.
        """
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[RunEvent]] = {}
        self._deliveries: dict[tuple[str, int], RunDeliveryRecord] = {}
        self._idempotency_keys: dict[str, str] = {}
        self._honor_intent_run_id = honor_intent_run_id

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> RunRecord:
        """Persist a fresh run as QUEUED under a ledger-assigned canonical id.

        S3/R4 (run_id duality dies): identity is ALWAYS the LEDGER's to mint,
        mirroring `DbRunLedger` (whose id is the row UUID). `intent.run_id` is
        advisory client-correlation ONLY and is never adopted as the identity —
        except under the test-only `honor_intent_run_id` constructor seam.
        """
        run_id = intent.run_id if (self._honor_intent_run_id and intent.run_id) else str(uuid4())
        return self._insert_run(
            intent,
            run_id=run_id,
            workflow_name=workflow_name,
            pattern_manifest=pattern_manifest,
            queue_name=queue_name,
            priority=priority,
            hold_delivery=hold_delivery,
        )

    async def create_idempotent(
        self,
        intent: Intent,
        *,
        idempotency_key: str,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> tuple[RunRecord, bool]:
        """Create one deterministic Run or return its validated prior admission."""
        run_id = str(_idempotent_run_uuid(idempotency_key))
        existing = self._runs.get(run_id)
        if existing is not None:
            if self._idempotency_keys.get(run_id) != idempotency_key:
                msg = "Deterministic Run identity collided with unrelated admission truth."
                raise RunAdmissionConflictError(msg)
            _assert_idempotent_replay(existing, intent)
            return existing, False
        record = self._insert_run(
            intent,
            run_id=run_id,
            workflow_name=workflow_name,
            pattern_manifest=pattern_manifest,
            queue_name=queue_name,
            priority=priority,
            hold_delivery=hold_delivery,
        )
        self._idempotency_keys[run_id] = idempotency_key
        return record, True

    async def get_idempotent(self, intent: Intent, *, idempotency_key: str) -> RunRecord | None:
        """Return a validated in-memory replay before consulting current routing."""
        run_id = str(_idempotent_run_uuid(idempotency_key))
        record = self._runs.get(run_id)
        if record is None:
            return None
        if self._idempotency_keys.get(run_id) != idempotency_key:
            msg = "Deterministic Run identity collided with unrelated admission truth."
            raise RunAdmissionConflictError(msg)
        _assert_idempotent_replay(record, intent)
        return record

    def _insert_run(
        self,
        intent: Intent,
        *,
        run_id: str,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None,
        queue_name: str,
        priority: int,
        hold_delivery: bool,
    ) -> RunRecord:
        """Insert one in-memory Run and its initial delivery."""
        record = RunRecord(
            run_id=run_id,
            session_id=intent.session_id,
            workflow_name=workflow_name,
            pattern_manifest=pattern_manifest or _legacy_pattern_manifest(workflow_name),
            source=intent.source,
            queue_name=queue_name,
            priority=priority,
            status=RunStatus.QUEUED,
            prompt=intent.prompt,
            sigil_name=intent.sigil_name,
            sigil_scopes=intent.sigil_scopes,
            content=intent.content,
            requested_priority=intent.priority,
        )
        self._runs[record.run_id] = record
        self._events[record.run_id] = []
        self._deliveries[(record.run_id, record.enqueue_seq)] = RunDeliveryRecord(
            run_id=record.run_id,
            enqueue_seq=record.enqueue_seq,
            queue_name=record.queue_name,
            priority=record.priority,
            resume=False,
            state=RunDeliveryState.HELD if hold_delivery else RunDeliveryState.PENDING,
        )
        return record

    async def get_delivery(self, run_id: str, *, enqueue_seq: int) -> RunDeliveryRecord | None:
        """Return one exact in-memory delivery hop."""
        return self._deliveries.get((run_id, enqueue_seq))

    async def release_delivery(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Release a retained-context gate exactly once."""
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if delivery is None or delivery.state is not RunDeliveryState.HELD:
            return False
        self._deliveries[(run_id, enqueue_seq)] = replace(
            delivery,
            state=RunDeliveryState.PENDING,
        )
        return True

    async def mark_delivery_published(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Record publication unless a worker or terminal writer already advanced it."""
        record = self._runs.get(run_id)
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if (
            record is None
            or record.status is not RunStatus.QUEUED
            or record.enqueue_seq != enqueue_seq
            or delivery is None
            or delivery.state
            not in {
                RunDeliveryState.PENDING,
                RunDeliveryState.PUBLISHED,
            }
        ):
            return False
        self._deliveries[(run_id, enqueue_seq)] = replace(
            delivery,
            state=RunDeliveryState.PUBLISHED,
            publish_attempts=delivery.publish_attempts + 1,
            last_error=None,
            published_at=datetime.now(UTC),
        )
        return True

    async def note_delivery_error(self, run_id: str, *, enqueue_seq: int, error: str) -> None:
        """Retain a publication failure without retracting the durable hop."""
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if delivery is None or delivery.state not in {
            RunDeliveryState.PENDING,
            RunDeliveryState.PUBLISHED,
        }:
            return
        self._deliveries[(run_id, enqueue_seq)] = replace(
            delivery,
            publish_attempts=delivery.publish_attempts + 1,
            last_error=error,
        )

    async def get(self, run_id: str) -> RunRecord | None:
        """Return the run record, or ``None``."""
        return self._runs.get(run_id)

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a run's status, validated against the state machine."""
        record = self._require(run_id)
        previous = record.status
        _reject_generic_resume(previous, status, run_id=run_id)
        _apply_status(record, status, error=error)
        if previous is not RunStatus.QUEUED and status is RunStatus.QUEUED:
            record.enqueue_seq += 1
            self._deliveries[(run_id, record.enqueue_seq)] = RunDeliveryRecord(
                run_id=run_id,
                enqueue_seq=record.enqueue_seq,
                queue_name=record.queue_name,
                priority=record.priority,
                resume=True,
                state=RunDeliveryState.PENDING,
            )
        elif _settles_delivery(status):
            self._settle_delivery(run_id, record.enqueue_seq)

    async def bump_enqueue_seq(self, run_id: str) -> int:
        """Allocate a fresh retry delivery for compatibility with explicit callers."""
        record = self._require(run_id)
        rotated = await self.rotate_delivery(run_id, enqueue_seq=record.enqueue_seq)
        if rotated is None:
            msg = f"Run {run_id!r} has no rotatable current delivery."
            raise RuntimeError(msg)
        return rotated

    async def rotate_delivery(self, run_id: str, *, enqueue_seq: int) -> int | None:
        """Fence and replace one unclaimed in-memory delivery."""
        record = self._require(run_id)
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if (
            record.status is not RunStatus.QUEUED
            or record.enqueue_seq != enqueue_seq
            or delivery is None
            or delivery.state not in {RunDeliveryState.PENDING, RunDeliveryState.PUBLISHED}
        ):
            return None
        self._settle_delivery(run_id, enqueue_seq)
        record.enqueue_seq += 1
        record.updated_at = datetime.now(UTC)
        self._deliveries[(run_id, record.enqueue_seq)] = RunDeliveryRecord(
            run_id=run_id,
            enqueue_seq=record.enqueue_seq,
            queue_name=delivery.queue_name,
            priority=delivery.priority,
            resume=delivery.resume,
            state=RunDeliveryState.PENDING,
        )
        return record.enqueue_seq

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Claim the exact queued hop on the loop; stale/duplicate deliveries lose."""
        record = self._require(run_id)
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if (
            record.status is not RunStatus.QUEUED
            or record.enqueue_seq != enqueue_seq
            or delivery is None
            or delivery.state not in {RunDeliveryState.PENDING, RunDeliveryState.PUBLISHED}
        ):
            return False
        _apply_status(record, RunStatus.RUNNING, error=None)
        self._deliveries[(run_id, enqueue_seq)] = replace(
            delivery,
            state=RunDeliveryState.CLAIMED,
            claimed_at=datetime.now(UTC),
        )
        return True

    async def try_fail_queued(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail only the exact unclaimed queued hop after publication refusal."""
        record = self._require(run_id)
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if (
            record.status is not RunStatus.QUEUED
            or record.enqueue_seq != enqueue_seq
            or delivery is None
            or delivery.state not in {RunDeliveryState.PENDING, RunDeliveryState.PUBLISHED}
        ):
            return False
        _apply_status(record, RunStatus.FAILED, error=error)
        self._settle_delivery(run_id, enqueue_seq)
        return True

    async def try_fail_held(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail only the exact initial delivery while admission still owns it."""
        record = self._require(run_id)
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if (
            record.status is not RunStatus.QUEUED
            or record.enqueue_seq != enqueue_seq
            or delivery is None
            or delivery.state is not RunDeliveryState.HELD
        ):
            return False
        _apply_status(record, RunStatus.FAILED, error=error)
        self._settle_delivery(run_id, enqueue_seq)
        return True

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail this claimed hop without overwriting a resumed or terminal run."""
        return await self.try_settle_claim(
            run_id,
            enqueue_seq=enqueue_seq,
            status=RunStatus.FAILED,
            error=error,
        )

    async def begin_cancel(self, run_id: str) -> RunRecord | None:
        """Move one live in-memory run to CANCELLING and freeze its generation."""
        record = self._require(run_id)
        if record.status in TERMINAL_STATUSES:
            return None
        _apply_status(record, RunStatus.CANCELLING, error=None)
        return replace(record)

    async def finish_cancel(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Commit CANCELLED only for the generation elected by ``begin_cancel``."""
        record = self._require(run_id)
        if record.status is not RunStatus.CANCELLING or record.enqueue_seq != enqueue_seq:
            return False
        _apply_status(record, RunStatus.CANCELLED, error=None)
        self._settle_delivery(run_id, enqueue_seq)
        return True

    async def try_settle_claim(
        self,
        run_id: str,
        *,
        enqueue_seq: int,
        status: RunStatus,
        error: str | None = None,
    ) -> bool:
        """Settle only the terminal result owned by this exact claimed hop."""
        if status not in TERMINAL_STATUSES:
            msg = f"Claim settlement must be terminal, got {status.value!r}."
            raise ValueError(msg)
        record = self._require(run_id)
        if record.enqueue_seq != enqueue_seq or record.status not in {
            RunStatus.RUNNING,
            RunStatus.AWAITING_HARDWARE,
        }:
            return False
        _apply_status(record, status, error=error)
        self._settle_delivery(run_id, enqueue_seq)
        return True

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id."""
        self._require(run_id).consent_id = consent_id

    async def park_consent(self, run_id: str, consent_id: str) -> None:
        """Bind and park one in-memory consent wait in the same loop turn."""
        record = self._require(run_id)
        _apply_status(record, RunStatus.AWAITING_CONSENT, error=None)
        record.consent_id = consent_id
        self._settle_delivery(run_id, record.enqueue_seq)

    async def park_delegate(self, run_id: str, job_id: str) -> None:
        """Bind the job and transition RUNNING → AWAITING_DELEGATE atomically."""
        record = self._require(run_id)
        _apply_status(record, RunStatus.AWAITING_DELEGATE, error=None)
        record.delegated_job_id = job_id
        self._settle_delivery(run_id, record.enqueue_seq)

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event to the run's step list."""
        if event.kind is RunEventKind.TOKEN:
            return
        self._events.setdefault(event.run_id, []).append(event)

    @property
    def evidence_capture(self) -> str:
        """Memory evidence disappears with the process."""
        return "process_local"

    async def list_events(self, run_id: str, *, after_seq: int = -1, limit: int = 100) -> list[RunEvent]:
        """Return a bounded retained event page from process memory."""
        return [event for event in self._events.get(run_id, ()) if event.seq > after_seq][:limit]

    async def latest_event(self, run_id: str, kind: RunEventKind) -> RunEvent | None:
        """Return the newest matching in-memory event."""
        return next((event for event in reversed(self._events.get(run_id, ())) if event.kind is kind), None)

    async def next_seq(self, run_id: str) -> int:
        """Return the next unused Step seq for a run (max(seq)+1, or 0 if none)."""
        return max((e.seq for e in self._events.get(run_id, [])), default=-1) + 1

    async def list_by_status(
        self,
        status: RunStatus,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int | None = None,
    ) -> list[RunRecord]:
        """Return an ordered optional keyset page from memory."""
        records = sorted(
            (record for record in self._runs.values() if record.status is status),
            key=lambda record: (record.created_at, record.run_id),
        )
        if after is not None:
            records = [record for record in records if (record.created_at, record.run_id) > after]
        return records if limit is None else records[:limit]

    async def list_for_session(self, session_id: str) -> list[RunRecord]:
        """Return one session's Runs from memory in creation order."""
        return sorted(
            (record for record in self._runs.values() if record.session_id == session_id),
            key=lambda record: (record.created_at, record.run_id),
        )

    async def list_delivery_candidates(
        self,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        """Return every QUEUED Run so reconciliation can detect corrupt delivery truth."""
        candidates = [record for record in self._runs.values() if record.status is RunStatus.QUEUED]
        candidates.sort(key=lambda record: (record.updated_at, record.run_id))
        if after is not None:
            candidates = [record for record in candidates if (record.updated_at, record.run_id) > after]
        return candidates[:limit]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id``."""
        for record in self._runs.values():
            if record.status is RunStatus.AWAITING_CONSENT and record.consent_id == consent_id:
                return record
        return None

    async def try_admit_consent(
        self,
        run_id: str,
        *,
        consent_id: str,
        evidence: ConsentAdmissionEvidence | None = None,
    ) -> int | None:
        """CAS the parked run to QUEUED and allocate its sequence in one loop turn.

        There is no await across either mutation, so no stale job can claim between
        admission and sequence allocation.
        """
        record = self._require(run_id)
        if (
            evidence is None
            or evidence.consent_id != consent_id
            or evidence.run_id != run_id
            or evidence.status not in {"granted", "denied", "expired"}
            or not evidence.decided_by
            or evidence.decided_at.tzinfo is None
            or evidence.decided_at.utcoffset() is None
        ):
            return None
        if record.status is not RunStatus.AWAITING_CONSENT or record.consent_id != consent_id:
            return None
        _apply_status(record, RunStatus.QUEUED, error=None)
        record.enqueue_seq += 1
        self._deliveries[(run_id, record.enqueue_seq)] = RunDeliveryRecord(
            run_id=run_id,
            enqueue_seq=record.enqueue_seq,
            queue_name=record.queue_name,
            priority=record.priority,
            resume=True,
            state=RunDeliveryState.PENDING,
        )
        return record.enqueue_seq

    async def try_admit_delegate(self, run_id: str, *, job_id: str) -> int | None:
        """CAS the matching delegated wait to QUEUED and allocate one resume sequence."""
        record = self._require(run_id)
        if record.status is not RunStatus.AWAITING_DELEGATE or record.delegated_job_id != job_id:
            return None
        _apply_status(record, RunStatus.QUEUED, error=None)
        record.enqueue_seq += 1
        self._deliveries[(run_id, record.enqueue_seq)] = RunDeliveryRecord(
            run_id=run_id,
            enqueue_seq=record.enqueue_seq,
            queue_name=record.queue_name,
            priority=record.priority,
            resume=True,
            state=RunDeliveryState.PENDING,
        )
        return record.enqueue_seq

    def events(self, run_id: str) -> list[RunEvent]:
        """Return the recorded non-TOKEN events for a run (test/observability read)."""
        return list(self._events.get(run_id, []))

    def _require(self, run_id: str) -> RunRecord:
        record = self._runs.get(run_id)
        if record is None:
            msg = f"Unknown run: {run_id}"
            raise KeyError(msg)
        return record

    def _settle_delivery(self, run_id: str, enqueue_seq: int) -> None:
        delivery = self._deliveries.get((run_id, enqueue_seq))
        if delivery is None or delivery.state is RunDeliveryState.SETTLED:
            return
        self._deliveries[(run_id, enqueue_seq)] = replace(
            delivery,
            state=RunDeliveryState.SETTLED,
            settled_at=datetime.now(UTC),
        )


class DbRunLedger:
    """Durable PostgreSQL ledger for Runs, exact deliveries, and Step evidence.

    Run identity is exposed as the string form of its database UUID. Intent remains
    the reconstructable request record; a UUID session id also binds the relational
    session foreign key. Consent authority lives in the Consent table rather than a
    process-local side map.
    """

    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Bind the ledger to a session factory (typically `get_session_factory()`)."""
        self._session_factory = session_factory

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> RunRecord:
        """Insert a fresh QUEUED `Run` row and its exact initial delivery."""
        record, _created = await self._create_admission(
            intent,
            run_id=None,
            idempotency_key=None,
            workflow_name=workflow_name,
            pattern_manifest=pattern_manifest,
            queue_name=queue_name,
            priority=priority,
            hold_delivery=hold_delivery,
        )
        return record

    async def create_idempotent(
        self,
        intent: Intent,
        *,
        idempotency_key: str,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
        hold_delivery: bool = False,
    ) -> tuple[RunRecord, bool]:
        """Insert once under a deterministic UUID or return the validated prior Run."""
        return await self._create_admission(
            intent,
            run_id=_idempotent_run_uuid(idempotency_key),
            idempotency_key=idempotency_key,
            workflow_name=workflow_name,
            pattern_manifest=pattern_manifest,
            queue_name=queue_name,
            priority=priority,
            hold_delivery=hold_delivery,
        )

    async def get_idempotent(self, intent: Intent, *, idempotency_key: str) -> RunRecord | None:
        """Return a validated PostgreSQL replay before consulting current routing."""
        from lychd.db.models import Run

        run_id = _idempotent_run_uuid(idempotency_key)
        async with self._session_factory() as session:
            row = await session.get(Run, run_id)
            if row is None:
                return None
            payload = dict(row.intent or {})
            if payload.get("idempotency_key") != idempotency_key:
                msg = "Deterministic Run identity collided with unrelated admission truth."
                raise RunAdmissionConflictError(msg)
            record = self._to_record(row)
            _assert_idempotent_replay(record, intent)
            return record

    async def _create_admission(
        self,
        intent: Intent,
        *,
        run_id: UUID | None,
        idempotency_key: str | None,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None,
        queue_name: str,
        priority: int,
        hold_delivery: bool,
    ) -> tuple[RunRecord, bool]:
        """Commit Run+delivery and resolve a deterministic concurrent insert.

        Session FK (4C-6): set the real `session_id` when the intent's session id parses
        as a UUID (it always does once `DbBridgeSessionStore` mints UUID ids); otherwise
        leave it NULL. The FK is for joins; the `intent` JSONB stays the Intent record.
        """
        from advanced_alchemy.exceptions import DuplicateKeyError
        from sqlalchemy.exc import IntegrityError

        from lychd.db.models import Run, RunDelivery
        from lychd.domain.cortex.services import RunService

        try:
            session_fk: UUID | None = UUID(intent.session_id)
        except ValueError:
            session_fk = None
        async with self._session_factory() as session:
            svc = RunService(session=session)
            row_data: dict[str, Any] = {
                "workflow_name": workflow_name,
                "pattern_manifest": pattern_manifest or _legacy_pattern_manifest(workflow_name),
                "source": intent.source,
                "status": RunStatus.QUEUED.value,
                "priority": priority,
                "sigil_name": intent.sigil_name,
                "session_id": session_fk,
                "intent": _intent_payload(intent, idempotency_key=idempotency_key),
                "queue_name": queue_name,
                "enqueue_seq": 0,
            }
            if run_id is not None:
                row_data["id"] = run_id
            try:
                row = await svc.create(
                    Run(**row_data),
                    auto_commit=False,
                )
                session.add(
                    RunDelivery(
                        run_id=row.id,
                        enqueue_seq=row.enqueue_seq,
                        queue_name=row.queue_name,
                        priority=row.priority,
                        resume=False,
                        state=(RunDeliveryState.HELD if hold_delivery else RunDeliveryState.PENDING).value,
                    )
                )
                await session.commit()
            except (DuplicateKeyError, IntegrityError) as exc:
                await session.rollback()
                if run_id is None or idempotency_key is None:
                    raise
                row = await session.get(Run, run_id)
                if row is None:
                    raise
                payload = dict(row.intent or {})
                if payload.get("idempotency_key") != idempotency_key:
                    msg = "Deterministic Run identity collided with unrelated admission truth."
                    raise RunAdmissionConflictError(msg) from exc
                record = self._to_record(row)
                _assert_idempotent_replay(record, intent)
                return record, False
            await session.refresh(row)
            return self._to_record(row), True

    async def get_delivery(self, run_id: str, *, enqueue_seq: int) -> RunDeliveryRecord | None:
        """Return one exact PostgreSQL delivery row."""
        from sqlalchemy import select

        from lychd.db.models import RunDelivery

        async with self._session_factory() as session:
            row = await session.scalar(
                select(RunDelivery).where(
                    RunDelivery.run_id == UUID(run_id),
                    RunDelivery.enqueue_seq == enqueue_seq,
                )
            )
        return self._to_delivery_record(row) if row is not None else None

    async def release_delivery(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Release a HELD delivery only after caller-owned admission context lands."""
        from sqlalchemy import update

        from lychd.db.models import RunDelivery

        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(RunDelivery)
                    .where(
                        RunDelivery.run_id == UUID(run_id),
                        RunDelivery.enqueue_seq == enqueue_seq,
                        RunDelivery.state == RunDeliveryState.HELD.value,
                    )
                    .values(state=RunDeliveryState.PENDING.value)
                ),
            )
            await session.commit()
            return result.rowcount == 1

    async def mark_delivery_published(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Record broker acknowledgement without racing a worker claim backwards."""
        from sqlalchemy import exists, update

        from lychd.db.models import Run, RunDelivery

        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(RunDelivery)
                    .where(
                        RunDelivery.run_id == UUID(run_id),
                        RunDelivery.enqueue_seq == enqueue_seq,
                        RunDelivery.state.in_((RunDeliveryState.PENDING.value, RunDeliveryState.PUBLISHED.value)),
                        exists().where(
                            Run.id == UUID(run_id),
                            Run.status == RunStatus.QUEUED.value,
                            Run.enqueue_seq == enqueue_seq,
                        ),
                    )
                    .values(
                        state=RunDeliveryState.PUBLISHED.value,
                        publish_attempts=RunDelivery.publish_attempts + 1,
                        last_error=None,
                        published_at=datetime.now(UTC),
                    )
                ),
            )
            await session.commit()
            return result.rowcount == 1

    async def note_delivery_error(self, run_id: str, *, enqueue_seq: int, error: str) -> None:
        """Retain one publication error while preserving retryable delivery truth."""
        from sqlalchemy import update

        from lychd.db.models import RunDelivery

        async with self._session_factory() as session:
            await session.execute(
                update(RunDelivery)
                .where(
                    RunDelivery.run_id == UUID(run_id),
                    RunDelivery.enqueue_seq == enqueue_seq,
                    RunDelivery.state.in_((RunDeliveryState.PENDING.value, RunDeliveryState.PUBLISHED.value)),
                )
                .values(
                    publish_attempts=RunDelivery.publish_attempts + 1,
                    last_error=error,
                )
            )
            await session.commit()

    async def get(self, run_id: str) -> RunRecord | None:
        """Return the run record for ``run_id`` (a UUID string), or ``None``."""
        from lychd.domain.cortex.services import RunService

        try:
            row_id = UUID(run_id)
        except ValueError:
            return None
        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.get_one_or_none(id=row_id)
            return self._to_record(row) if row is not None else None

    # One bounded re-read is enough for the single-process writer topology.
    _CAS_RETRIES = 1

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a Run status with bounded compare-and-swap concurrency.

        The state machine is validated against the row read at the top, then the write
        is a conditional ``UPDATE ... WHERE id = :id AND status = :expected``. If a
        competing writer moved the row, the ledger re-reads once and retries only when
        the fresh edge remains legal. An already reached target is a benign no-op;
        every genuinely illegal fresh edge raises ``IllegalRunTransitionError``.
        """
        from sqlalchemy import update

        from lychd.db.models import Run, RunDelivery
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            for _ in range(self._CAS_RETRIES + 1):
                row = await svc.get_one_or_none(id=UUID(run_id))
                if row is None:
                    msg = f"Unknown run: {run_id}"
                    raise KeyError(msg)
                expected = RunStatus(str(row.status))
                if status is expected:
                    return  # idempotent no-op (re-claim / duplicate terminal write)
                _reject_generic_resume(expected, status, run_id=run_id)
                record = self._to_record(row)
                _apply_status(record, status, error=error)  # raises on an illegal edge
                allocating_delivery = expected is not RunStatus.QUEUED and status is RunStatus.QUEUED
                if allocating_delivery:
                    record.enqueue_seq += 1
                result = cast(
                    "CursorResult[Any]",
                    await session.execute(
                        update(Run)
                        .where(Run.id == UUID(run_id), Run.status == expected.value)
                        .values(
                            status=record.status.value,
                            error=record.error,
                            attempt=record.attempt,
                            enqueue_seq=record.enqueue_seq,
                            updated_at=record.updated_at,
                            started_at=record.started_at,
                            finished_at=record.finished_at,
                        )
                    ),
                )
                if result.rowcount != 0:
                    if allocating_delivery:
                        session.add(
                            RunDelivery(
                                run_id=UUID(run_id),
                                enqueue_seq=record.enqueue_seq,
                                queue_name=record.queue_name,
                                priority=record.priority,
                                resume=True,
                                state=RunDeliveryState.PENDING.value,
                            )
                        )
                    elif _settles_delivery(status):
                        await _settle_db_delivery(session, UUID(run_id), record.enqueue_seq)
                    await session.commit()
                    return  # CAS won
                await session.rollback()
                session.expire_all()
                # Lost the CAS: loop re-reads the fresh row. If the fresh edge is legal
                # the retry lands it; if illegal, `_apply_status` raises on the re-read;
                # if the fresh row already IS the target, the top-of-loop check returns.
            # Retries exhausted (the row kept moving under us): rule on the fresh truth.
            await self._raise_on_lost_cas(svc, run_id, status)

    @staticmethod
    async def _raise_on_lost_cas(svc: Any, run_id: str, target: RunStatus) -> None:
        """Re-read the fresh truth and rule on it after the bounded CAS retry ran out."""
        fresh = await svc.get_one_or_none(id=UUID(run_id))
        current = RunStatus(str(fresh.status)) if fresh is not None else None
        if current is target:
            return  # a concurrent writer reached the same target — benign
        if current is None:
            msg = f"Unknown run: {run_id}"
            raise KeyError(msg)
        raise IllegalRunTransitionError(run_id, current, target)

    async def bump_enqueue_seq(self, run_id: str) -> int:
        """Allocate a fresh retry delivery for compatibility with explicit callers."""
        record = await self.get(run_id)
        if record is None:
            msg = f"Unknown run: {run_id}"
            raise KeyError(msg)
        rotated = await self.rotate_delivery(run_id, enqueue_seq=record.enqueue_seq)
        if rotated is None:
            msg = f"Run {run_id!r} has no rotatable current delivery."
            raise RuntimeError(msg)
        return rotated

    async def rotate_delivery(self, run_id: str, *, enqueue_seq: int) -> int | None:
        """Fence and replace one unclaimed PostgreSQL delivery."""
        from sqlalchemy import select

        from lychd.db.models import Run, RunDelivery

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None or RunStatus(str(row.status)) is not RunStatus.QUEUED or row.enqueue_seq != enqueue_seq:
                return None
            delivery = await session.scalar(
                select(RunDelivery)
                .where(
                    RunDelivery.run_id == row.id,
                    RunDelivery.enqueue_seq == enqueue_seq,
                )
                .with_for_update()
            )
            if delivery is None or RunDeliveryState(str(delivery.state)) not in {
                RunDeliveryState.PENDING,
                RunDeliveryState.PUBLISHED,
            }:
                return None
            delivery.state = RunDeliveryState.SETTLED.value
            delivery.settled_at = datetime.now(UTC)
            next_seq = enqueue_seq + 1
            row.enqueue_seq = next_seq
            row.updated_at = datetime.now(UTC)
            session.add(
                RunDelivery(
                    run_id=row.id,
                    enqueue_seq=next_seq,
                    queue_name=delivery.queue_name,
                    priority=delivery.priority,
                    resume=delivery.resume,
                    state=RunDeliveryState.PENDING.value,
                )
            )
            return next_seq

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Claim the exact delivery and Run in one PostgreSQL transaction."""
        from sqlalchemy import func, update

        from lychd.db.models import Run, RunDelivery

        async with self._session_factory() as session:
            now = datetime.now(UTC)
            run_result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(Run)
                    .where(
                        Run.id == UUID(run_id),
                        Run.status == RunStatus.QUEUED.value,
                        Run.enqueue_seq == enqueue_seq,
                    )
                    .values(
                        status=RunStatus.RUNNING.value,
                        started_at=func.coalesce(Run.started_at, now),
                        error=None,
                    )
                ),
            )
            if run_result.rowcount != 1:
                await session.rollback()
                return False
            delivery_result = await session.execute(
                update(RunDelivery)
                .where(
                    RunDelivery.run_id == UUID(run_id),
                    RunDelivery.enqueue_seq == enqueue_seq,
                    RunDelivery.state.in_((RunDeliveryState.PENDING.value, RunDeliveryState.PUBLISHED.value)),
                )
                .values(
                    state=RunDeliveryState.CLAIMED.value,
                    claimed_at=now,
                )
                .returning(RunDelivery.id)
            )
            if delivery_result.scalar_one_or_none() is None:
                await session.rollback()
                return False
            await session.commit()
            return True

    async def try_fail_queued(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """CAS one exact unclaimed QUEUED delivery to FAILED."""
        from sqlalchemy import exists, update

        from lychd.db.models import Run, RunDelivery

        async with self._session_factory() as session:
            result = await session.execute(
                update(Run)
                .where(
                    Run.id == UUID(run_id),
                    Run.status == RunStatus.QUEUED.value,
                    Run.enqueue_seq == enqueue_seq,
                    exists().where(
                        RunDelivery.run_id == Run.id,
                        RunDelivery.enqueue_seq == enqueue_seq,
                        RunDelivery.state.in_((RunDeliveryState.PENDING.value, RunDeliveryState.PUBLISHED.value)),
                    ),
                )
                .values(
                    status=RunStatus.FAILED.value,
                    error=error,
                    finished_at=datetime.now(UTC),
                )
                .returning(Run.id)
            )
            admitted = result.scalar_one_or_none()
            if admitted is not None:
                await _settle_db_delivery(session, UUID(run_id), enqueue_seq)
            await session.commit()
            return admitted is not None

    async def try_fail_held(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Settle a QUEUED Run only while its exact admission delivery is HELD."""
        from sqlalchemy import select

        from lychd.db.models import Run, RunDelivery

        async with self._session_factory() as session, session.begin():
            run = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if run is None or str(run.status) != RunStatus.QUEUED.value or int(run.enqueue_seq) != enqueue_seq:
                return False
            delivery = await session.scalar(
                select(RunDelivery)
                .where(
                    RunDelivery.run_id == UUID(run_id),
                    RunDelivery.enqueue_seq == enqueue_seq,
                )
                .with_for_update()
            )
            if delivery is None or str(delivery.state) != RunDeliveryState.HELD.value:
                return False
            now = datetime.now(UTC)
            run.status = RunStatus.FAILED.value
            run.error = error
            run.finished_at = now
            delivery.state = RunDeliveryState.SETTLED.value
            delivery.settled_at = now
            return True

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """CAS the owned active hop to FAILED without touching a later resume."""
        return await self.try_settle_claim(
            run_id,
            enqueue_seq=enqueue_seq,
            status=RunStatus.FAILED,
            error=error,
        )

    async def begin_cancel(self, run_id: str) -> RunRecord | None:
        """Lock the Run, elect CANCELLING, and return the exact fenced generation."""
        from sqlalchemy import select

        from lychd.db.models import Run

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            record = self._to_record(row)
            if record.status in TERMINAL_STATUSES:
                return None
            _apply_status(record, RunStatus.CANCELLING, error=None)
            row.status = record.status.value
            row.error = record.error
            row.finished_at = record.finished_at
            return record

    async def finish_cancel(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Commit CANCELLED and settle only the cancellation-elected delivery."""
        from sqlalchemy import select

        from lychd.db.models import Run

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None or RunStatus(str(row.status)) is not RunStatus.CANCELLING or row.enqueue_seq != enqueue_seq:
                return False
            record = self._to_record(row)
            _apply_status(record, RunStatus.CANCELLED, error=None)
            row.status = record.status.value
            row.error = record.error
            row.finished_at = record.finished_at
            await _settle_db_delivery(session, UUID(run_id), enqueue_seq)
            return True

    async def try_settle_claim(
        self,
        run_id: str,
        *,
        enqueue_seq: int,
        status: RunStatus,
        error: str | None = None,
    ) -> bool:
        """CAS one exact claimed hop to terminal Run and delivery truth."""
        if status not in TERMINAL_STATUSES:
            msg = f"Claim settlement must be terminal, got {status.value!r}."
            raise ValueError(msg)
        from sqlalchemy import update

        from lychd.db.models import Run

        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(Run)
                    .where(
                        Run.id == UUID(run_id),
                        Run.enqueue_seq == enqueue_seq,
                        Run.status.in_(
                            (
                                RunStatus.RUNNING.value,
                                RunStatus.AWAITING_HARDWARE.value,
                            )
                        ),
                    )
                    .values(
                        status=status.value,
                        error=error,
                        finished_at=datetime.now(UTC),
                    )
                ),
            )
            if result.rowcount == 1:
                await _settle_db_delivery(session, UUID(run_id), enqueue_seq)
            await session.commit()
            return result.rowcount == 1

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Bind or clear the exact durable Consent owner without changing Run status."""
        from sqlalchemy import select

        from lychd.db.models import Consent, Run

        consent_uuid = UUID(consent_id) if consent_id is not None else None
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            if consent_uuid is not None:
                owner = await session.scalar(
                    select(Consent.run_id).where(
                        Consent.id == consent_uuid,
                        Consent.run_id == row.id,
                    )
                )
                if owner != row.id:
                    msg = f"Consent {consent_id!r} does not belong to Run {run_id!r}."
                    raise RuntimeError(msg)
            row.consent_id = consent_uuid

    async def park_consent(self, run_id: str, consent_id: str) -> None:
        """Lock the Run, verify its Consent authority, and commit the parked hop."""
        from sqlalchemy import select

        from lychd.db.models import Consent, Run

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            consent_exists = await session.scalar(
                select(Consent.id).where(
                    Consent.id == UUID(consent_id),
                    Consent.run_id == row.id,
                )
            )
            if consent_exists is None:
                msg = f"Consent {consent_id!r} does not belong to Run {run_id!r}."
                raise RuntimeError(msg)
            record = self._to_record(row)
            _apply_status(record, RunStatus.AWAITING_CONSENT, error=None)
            row.status = record.status.value
            row.error = record.error
            row.consent_id = consent_exists
            await _settle_db_delivery(session, row.id, row.enqueue_seq)

    async def park_delegate(self, run_id: str, job_id: str) -> None:
        """Lock one Run and atomically bind its delegated wait owner."""
        from sqlalchemy import select

        from lychd.db.models import DelegatedAgentJobRecord, Run

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            job_owner = await session.scalar(
                select(DelegatedAgentJobRecord.run_id).where(DelegatedAgentJobRecord.job_id == job_id)
            )
            if job_owner != row.id:
                msg = f"Delegated job {job_id!r} does not belong to Run {run_id!r}."
                raise RuntimeError(msg)
            record = self._to_record(row)
            _apply_status(record, RunStatus.AWAITING_DELEGATE, error=None)
            row.status = record.status.value
            row.error = record.error
            row.delegated_job_id = job_id
            await _settle_db_delivery(session, UUID(run_id), row.enqueue_seq)

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event as a Step row, persisting `event.seq` VERBATIM.

        The Step's ``seq`` is the channel event's sequence: there is no insert-time
        allocation or retry-on-collision. The bus's per-Run writer chain owns ordering;
        ``uq_step_run_seq`` remains a pure integrity check.
        """
        if event.kind is RunEventKind.TOKEN:
            return
        from lychd.db.models import Step
        from lychd.domain.cortex.services import StepService

        node_key = event.data if event.kind is RunEventKind.NODE else None
        async with self._session_factory() as session:
            svc = StepService(session=session)
            await svc.create(
                Step(
                    id=UUID(event.event_id),
                    run_id=UUID(event.run_id),
                    seq=event.seq,
                    kind=event.kind.value,
                    payload={
                        "data": event.data,
                        "meta": event.meta,
                        "event_id": event.event_id,
                        "occurred_at": event.ts.isoformat(),
                    },
                    node_key=node_key,
                ),
                auto_commit=True,
            )

    @property
    def evidence_capture(self) -> str:
        """Postgres retains structural events, but the live-first tee is best effort."""
        return "durable_best_effort"

    async def list_events(self, run_id: str, *, after_seq: int = -1, limit: int = 100) -> list[RunEvent]:
        """Read a bounded Step page without inventing omitted or failed writes."""
        from sqlalchemy import select

        from lychd.db.models import Step
        from lychd.domain.cortex.events import RunEvent

        bounded = min(max(limit, 1), 500)
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(Step)
                    .where(Step.run_id == UUID(run_id), Step.seq > after_seq)
                    .order_by(Step.seq.asc())
                    .limit(bounded)
                )
            ).all()
        events: list[RunEvent] = []
        for row in rows:
            payload = row.payload or {}
            events.append(
                RunEvent.model_validate(
                    {
                        "event_id": str(row.id),
                        "run_id": str(row.run_id),
                        "seq": row.seq,
                        "kind": row.kind,
                        "data": str(payload.get("data", "")),
                        "meta": payload.get("meta", {}),
                        "ts": payload.get("occurred_at", row.created_at),
                    }
                )
            )
        return events

    async def latest_event(self, run_id: str, kind: RunEventKind) -> RunEvent | None:
        """Read the newest retained Step of one kind without scanning a long run."""
        from sqlalchemy import select

        from lychd.db.models import Step
        from lychd.domain.cortex.events import RunEvent

        async with self._session_factory() as session:
            row = await session.scalar(
                select(Step)
                .where(Step.run_id == UUID(run_id), Step.kind == kind.value)
                .order_by(Step.seq.desc())
                .limit(1)
            )
        if row is None:
            return None
        payload = row.payload or {}
        return RunEvent.model_validate(
            {
                "event_id": str(row.id),
                "run_id": str(row.run_id),
                "seq": row.seq,
                "kind": row.kind,
                "data": str(payload.get("data", "")),
                "meta": payload.get("meta", {}),
                "ts": payload.get("occurred_at", row.created_at),
            }
        )

    async def next_seq(self, run_id: str) -> int:
        """Return the next unused Step seq for a run (max(seq)+1, or 0 if none).

        Feeds the R1 channel-seq seeding: reconcile/resume open a fresh channel with
        `from_seq=next_seq(run_id)` so the terminal (and any resumed) emit lands past
        the persisted Step history instead of colliding with `uq_step_run_seq`.
        """
        from sqlalchemy import func, select

        from lychd.db.models import Step

        async with self._session_factory() as session:
            result = await session.execute(
                select(func.coalesce(func.max(Step.seq), -1) + 1).where(Step.run_id == UUID(run_id))
            )
            return int(result.scalar_one())

    async def list_by_status(
        self,
        status: RunStatus,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int | None = None,
    ) -> list[RunRecord]:
        """Return an ordered optional PostgreSQL keyset page."""
        from sqlalchemy import and_, or_, select

        from lychd.db.models import Run

        statement = select(Run).where(Run.status == status.value).order_by(Run.created_at, Run.id)
        if after is not None:
            created_at, run_id = after
            statement = statement.where(
                or_(
                    Run.created_at > created_at,
                    and_(Run.created_at == created_at, Run.id > UUID(run_id)),
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [self._to_record(row) for row in rows]

    async def list_for_session(self, session_id: str) -> list[RunRecord]:
        """Return one session's durable Runs in creation order."""
        from sqlalchemy import select

        from lychd.db.models import Run

        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return []
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(Run).where(Run.session_id == session_uuid).order_by(Run.created_at, Run.id)
                )
            ).all()
        return [self._to_record(row) for row in rows]

    async def list_delivery_candidates(
        self,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int = 100,
    ) -> list[RunRecord]:
        """Query every QUEUED Run so corrupt or missing delivery truth is visible."""
        from sqlalchemy import and_, or_, select

        from lychd.db.models import Run

        statement = (
            select(Run).where(Run.status == RunStatus.QUEUED.value).order_by(Run.updated_at, Run.id).limit(limit)
        )
        if after is not None:
            updated_at, run_id = after
            statement = statement.where(
                or_(
                    Run.updated_at > updated_at,
                    and_(Run.updated_at == updated_at, Run.id > UUID(run_id)),
                )
            )
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [self._to_record(row) for row in rows]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run only when ``consent_id`` owns its current consent wait."""
        from sqlalchemy import select

        from lychd.db.models import Run

        try:
            cid = UUID(consent_id)
        except ValueError:
            return None  # malformed id → unknown (mirror get()'s do-not-invent-a-run stance)
        async with self._session_factory() as session:
            row = await session.scalar(
                select(Run).where(
                    Run.consent_id == cid,
                    Run.status == RunStatus.AWAITING_CONSENT.value,
                )
            )
            return self._to_record(row) if row is not None else None

    async def try_admit_consent(
        self,
        run_id: str,
        *,
        consent_id: str,
        evidence: ConsentAdmissionEvidence | None = None,
    ) -> int | None:
        """Lock the exact decided Consent owner and allocate one resume delivery."""
        from sqlalchemy import select

        from lychd.db.models import Consent, Run, RunDelivery

        _ = evidence  # the database re-establishes this truth under its own lock
        try:
            consent_uuid = UUID(consent_id)
        except ValueError:
            return None
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if (
                row is None
                or RunStatus(str(row.status)) is not RunStatus.AWAITING_CONSENT
                or row.consent_id != consent_uuid
            ):
                return None
            consent = await session.scalar(
                select(Consent).where(
                    Consent.id == consent_uuid,
                    Consent.run_id == row.id,
                )
            )
            if (
                consent is None
                or consent.status not in {"granted", "denied", "expired"}
                or not consent.decided_by
                or consent.decided_at is None
            ):
                return None
            previous_seq = int(row.enqueue_seq)
            record = self._to_record(row)
            _apply_status(record, RunStatus.QUEUED, error=None)
            record.enqueue_seq += 1
            row.status = record.status.value
            row.error = record.error
            row.enqueue_seq = record.enqueue_seq
            row.updated_at = record.updated_at
            await _settle_db_delivery(session, row.id, previous_seq)
            session.add(
                RunDelivery(
                    run_id=row.id,
                    enqueue_seq=record.enqueue_seq,
                    queue_name=str(row.queue_name),
                    priority=int(row.priority),
                    resume=True,
                    state=RunDeliveryState.PENDING.value,
                )
            )
            return record.enqueue_seq

    async def try_admit_delegate(self, run_id: str, *, job_id: str) -> int | None:
        """Lock the exact owner and require a shape-valid terminal result."""
        from pydantic import ValidationError
        from sqlalchemy import select

        from lychd.db.models import DelegatedAgentJobRecord, Run, RunDelivery
        from lychd.domain.delegation.models import (
            TERMINAL_DELEGATED_AGENT_STATUSES,
            DelegatedAgentJobStatus,
            DelegatedAgentResult,
        )

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
            if (
                row is None
                or RunStatus(str(row.status)) is not RunStatus.AWAITING_DELEGATE
                or row.delegated_job_id != job_id
            ):
                return None
            job = await session.scalar(
                select(DelegatedAgentJobRecord).where(
                    DelegatedAgentJobRecord.job_id == job_id,
                    DelegatedAgentJobRecord.run_id == row.id,
                )
            )
            if job is None or job.result is None:
                return None
            try:
                terminal_status = DelegatedAgentJobStatus(str(job.status))
                result = DelegatedAgentResult.model_validate(job.result)
            except (ValueError, ValidationError):
                return None
            if (
                terminal_status not in TERMINAL_DELEGATED_AGENT_STATUSES
                or result.job_id != job_id
                or result.status is not terminal_status
            ):
                return None
            previous_seq = int(row.enqueue_seq)
            record = self._to_record(row)
            _apply_status(record, RunStatus.QUEUED, error=None)
            record.enqueue_seq += 1
            row.status = record.status.value
            row.error = record.error
            row.enqueue_seq = record.enqueue_seq
            row.updated_at = record.updated_at
            await _settle_db_delivery(session, row.id, previous_seq)
            session.add(
                RunDelivery(
                    run_id=row.id,
                    enqueue_seq=record.enqueue_seq,
                    queue_name=str(row.queue_name),
                    priority=int(row.priority),
                    resume=True,
                    state=RunDeliveryState.PENDING.value,
                )
            )
            return record.enqueue_seq

    @staticmethod
    def _to_record(row: object) -> RunRecord:
        """Map a `Run` ORM row to a storage-agnostic `RunRecord`."""
        from lychd.agents.router import Intent

        intent: dict[str, object] = getattr(row, "intent", {}) or {}
        scopes_val = intent.get("sigil_scopes", [])
        scopes: frozenset[str] = frozenset[str]()
        if isinstance(scopes_val, list):
            scopes = frozenset(str(s) for s in cast("list[Any]", scopes_val))
        parsed_intent = Intent.model_validate(
            {
                "session_id": str(intent.get("session_id", "")),
                "run_id": intent.get("run_id"),
                "prompt": str(intent.get("prompt", "")),
                "content": intent.get("content", ()),
                "source": str(intent.get("source", "bridge")),
                "sigil_name": str(intent.get("sigil_name", row.sigil_name)),  # type: ignore[attr-defined]
                "sigil_scopes": scopes,
                "priority": intent.get("priority"),
            }
        )
        return RunRecord(
            run_id=str(row.id),  # type: ignore[attr-defined]
            session_id=str(intent.get("session_id", "")),
            workflow_name=str(row.workflow_name),  # type: ignore[attr-defined]
            pattern_manifest=dict(row.pattern_manifest),  # type: ignore[attr-defined]
            source=str(row.source),  # type: ignore[attr-defined]
            queue_name=str(row.queue_name),  # type: ignore[attr-defined]
            priority=int(row.priority),  # type: ignore[attr-defined]
            status=RunStatus(str(row.status)),  # type: ignore[attr-defined]
            prompt=str(intent.get("prompt", "")),
            sigil_name=str(intent.get("sigil_name", row.sigil_name)),  # type: ignore[attr-defined]
            sigil_scopes=scopes,
            content=parsed_intent.content,
            requested_priority=parsed_intent.priority,
            attempt=int(row.attempt),  # type: ignore[attr-defined]
            enqueue_seq=int(row.enqueue_seq),  # type: ignore[attr-defined]
            error=row.error,  # type: ignore[attr-defined]
            consent_id=str(row.consent_id) if row.consent_id is not None else None,  # type: ignore[attr-defined]
            delegated_job_id=row.delegated_job_id,  # type: ignore[attr-defined]
            created_at=row.created_at,  # type: ignore[attr-defined]
            updated_at=row.updated_at,  # type: ignore[attr-defined]  # eligibility cursor for delivery repair
            started_at=row.started_at,  # type: ignore[attr-defined]
            finished_at=row.finished_at,  # type: ignore[attr-defined]
        )

    @staticmethod
    def _to_delivery_record(row: object) -> RunDeliveryRecord:
        """Map a `RunDelivery` ORM row to storage-agnostic delivery truth."""
        return RunDeliveryRecord(
            run_id=str(row.run_id),  # type: ignore[attr-defined]
            enqueue_seq=int(row.enqueue_seq),  # type: ignore[attr-defined]
            queue_name=str(row.queue_name),  # type: ignore[attr-defined]
            priority=int(row.priority),  # type: ignore[attr-defined]
            resume=bool(row.resume),  # type: ignore[attr-defined]
            state=RunDeliveryState(str(row.state)),  # type: ignore[attr-defined]
            publish_attempts=int(row.publish_attempts),  # type: ignore[attr-defined]
            last_error=row.last_error,  # type: ignore[attr-defined]
            published_at=row.published_at,  # type: ignore[attr-defined]
            claimed_at=row.claimed_at,  # type: ignore[attr-defined]
            settled_at=row.settled_at,  # type: ignore[attr-defined]
        )
