"""The `RunLedger` — the run truth store (A4-U3).

One protocol, two implementations: `InMemoryRunLedger` (loop-confined, DB-free —
keeps unit tests and the Wave-2 in-process profile honest) and `DbRunLedger` (over
A7's `RunService`/`StepService`, the durable Postgres substrate). Both enforce the
run state machine (`runs.LEGAL_TRANSITIONS`) in `set_status` — an illegal edge
raises `IllegalRunTransitionError`.

Single-writer discipline (A4 §2) is a contract on the CALLERS, not enforced here
beyond the transition table: `RunEngine` writes QUEUED/CANCELLED + the consent
re-enqueue, `perform_run` writes RUNNING + terminal states, stasis states are
written from inside the run.

Persistence tee (spec §3): non-`TOKEN` events land as Step rows via `append_event`;
`TOKEN` deltas are too chatty and are dropped (settled text lands on the session
turn). The `RunEventBus` already filters `TOKEN` before calling `append_event`;
this layer drops it defensively too.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast
from uuid import UUID, uuid4

from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import (
    TERMINAL_STATUSES,
    IllegalRunTransitionError,
    RunRecord,
    RunStatus,
    can_transition,
)

if TYPE_CHECKING:
    from sqlalchemy import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEvent

__all__ = ["DbRunLedger", "InMemoryRunLedger", "RunLedger"]


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
    ) -> RunRecord:
        """Persist a fresh run as QUEUED and return its record."""
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

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Claim QUEUED → RUNNING only for this exact published delivery hop."""
        ...

    async def try_fail_queued(self, run_id: str, *, error: str) -> bool:
        """Atomically settle QUEUED → FAILED only if no worker claimed it."""
        ...

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail only the RUNNING/AWAITING_HARDWARE hop with this enqueue sequence."""
        ...

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id a run is parked on."""
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

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status`` (feeds `reconcile_runs`)."""
        ...

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id`` (feeds `engine.approve`)."""
        ...

    async def try_admit_consent(self, run_id: str) -> int | None:
        """Atomically admit a parked run and allocate its next enqueue sequence.

        The SINGLE resume-admission gate (F1/F4): returns the new sequence iff THIS
        caller performed the transition. Concurrent approves, and an `engine.approve`
        racing `perform_run`'s post-flip re-check, all funnel here so exactly one
        sequence is allocated and enqueued.
        """
        ...

    async def try_restore_consent_wait(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Compensate a failed resume enqueue (QUEUED → AWAITING_CONSENT).

        Returns ``True`` only when this caller restored the exact admitted hop. The
        conditional transition deliberately lives outside the public run state
        machine: it is a narrow rollback for the admission CAS, not a normal edge.
        """
        ...


def _apply_status(record: RunRecord, status: RunStatus, *, error: str | None) -> None:
    """Mutate ``record`` for a validated status change (timestamps + error)."""
    if status is record.status:
        return  # idempotent no-op (a re-claim or duplicate terminal write)
    if not can_transition(record.status, status):
        raise IllegalRunTransitionError(record.run_id, record.status, status)
    if status is RunStatus.RUNNING and record.started_at is None:
        record.started_at = datetime.now(UTC)
    if status is RunStatus.QUEUED and record.status is RunStatus.FAILED:
        record.attempt += 1  # explicit retry
    if status in TERMINAL_STATUSES:
        record.finished_at = datetime.now(UTC)
    record.status = status
    record.error = error


class InMemoryRunLedger:
    """Loop-confined, DB-free run ledger (unit tests + the Wave-2 in-process profile)."""

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
        self._honor_intent_run_id = honor_intent_run_id

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        pattern_manifest: dict[str, Any] | None = None,
        queue_name: str,
        priority: int,
    ) -> RunRecord:
        """Persist a fresh run as QUEUED under a ledger-assigned canonical id.

        S3/R4 (run_id duality dies): identity is ALWAYS the LEDGER's to mint,
        mirroring `DbRunLedger` (whose id is the row UUID). `intent.run_id` is
        advisory client-correlation ONLY and is never adopted as the identity —
        except under the test-only `honor_intent_run_id` constructor seam.
        """
        run_id = intent.run_id if (self._honor_intent_run_id and intent.run_id) else str(uuid4())
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
        )
        self._runs[record.run_id] = record
        self._events[record.run_id] = []
        return record

    async def get(self, run_id: str) -> RunRecord | None:
        """Return the run record, or ``None``."""
        return self._runs.get(run_id)

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a run's status, validated against the state machine."""
        record = self._require(run_id)
        _apply_status(record, status, error=error)

    async def bump_enqueue_seq(self, run_id: str) -> int:
        """Increment and return the run's enqueue seq."""
        record = self._require(run_id)
        record.enqueue_seq += 1
        return record.enqueue_seq

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """Claim the exact queued hop on the loop; stale/duplicate deliveries lose."""
        record = self._require(run_id)
        if record.status is not RunStatus.QUEUED or record.enqueue_seq != enqueue_seq:
            return False
        _apply_status(record, RunStatus.RUNNING, error=None)
        return True

    async def try_fail_queued(self, run_id: str, *, error: str) -> bool:
        """Fail only an unclaimed queued run after broker publication failed."""
        record = self._require(run_id)
        if record.status is not RunStatus.QUEUED:
            return False
        _apply_status(record, RunStatus.FAILED, error=error)
        return True

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """Fail this claimed hop without overwriting a resumed or terminal run."""
        record = self._require(run_id)
        if record.enqueue_seq != enqueue_seq or record.status not in {
            RunStatus.RUNNING,
            RunStatus.AWAITING_HARDWARE,
        }:
            return False
        _apply_status(record, RunStatus.FAILED, error=error)
        return True

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id."""
        self._require(run_id).consent_id = consent_id

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

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status``."""
        return [record for record in self._runs.values() if record.status is status]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id``."""
        for record in self._runs.values():
            if record.consent_id == consent_id:
                return record
        return None

    async def try_admit_consent(self, run_id: str) -> int | None:
        """CAS the parked run to QUEUED and allocate its sequence in one loop turn.

        There is no await across either mutation, so no stale job can claim between
        admission and sequence allocation.
        """
        record = self._require(run_id)
        if record.status is not RunStatus.AWAITING_CONSENT:
            return None
        _apply_status(record, RunStatus.QUEUED, error=None)
        record.enqueue_seq += 1
        return record.enqueue_seq

    async def try_restore_consent_wait(self, run_id: str, *, enqueue_seq: int) -> bool:
        """CAS the exact QUEUED hop back to wait after resume publication failed.

        The failed enqueue sequence is intentionally not rolled back: its job key may
        have reached the broker before the error surfaced and must never be reused.
        """
        record = self._require(run_id)
        if record.status is not RunStatus.QUEUED or record.enqueue_seq != enqueue_seq:
            return False
        record.status = RunStatus.AWAITING_CONSENT
        return True

    def events(self, run_id: str) -> list[RunEvent]:
        """Return the recorded non-TOKEN events for a run (test/observability read)."""
        return list(self._events.get(run_id, []))

    def _require(self, run_id: str) -> RunRecord:
        record = self._runs.get(run_id)
        if record is None:
            msg = f"Unknown run: {run_id}"
            raise KeyError(msg)
        return record


class DbRunLedger:
    """Durable run ledger over A7's `RunService`/`StepService` (Postgres substrate).

    Runtime-validation seam (PG/SAQ, Linux): this impl requires the ``run``/``step``
    tables (migration 0001) and a live engine. It is NOT unit-tested here (the
    in-memory ledger is). Wave-2 caveats until A7's session persistence lands:
    - `run_id` is the DB row's UUID as a string (C4: strings elsewhere are `str(id)`).
    - `session_id` is stashed in the `intent` JSONB, not the `session` FK (sessions
      are still in-memory this wave); the FK stays NULL.
    - consent is a placeholder (no `consent` column in 0001): consent ids are held
      in a best-effort in-memory side map for the `engine.approve` seam (Wave 4).
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
    ) -> RunRecord:
        """Insert a QUEUED `Run` row and return its record (run_id = str(row.id)).

        Session FK (4C-6): set the real `session_id` when the intent's session id parses
        as a UUID (it always does once `DbBridgeSessionStore` mints UUID ids); otherwise
        leave it NULL. The FK is for joins; the `intent` JSONB stays the Intent record.
        """
        from lychd.db.models import Run
        from lychd.domain.cortex.services import RunService

        try:
            session_fk: UUID | None = UUID(intent.session_id)
        except ValueError:
            session_fk = None
        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.create(
                Run(
                    workflow_name=workflow_name,
                    pattern_manifest=pattern_manifest or _legacy_pattern_manifest(workflow_name),
                    source=intent.source,
                    status=RunStatus.QUEUED.value,
                    priority=priority,
                    sigil_name=intent.sigil_name,
                    session_id=session_fk,
                    intent={
                        "session_id": intent.session_id,
                        "run_id": intent.run_id,
                        "prompt": intent.prompt,
                        "content": [part.model_dump(mode="json") for part in intent.content],
                        "source": intent.source,
                        "sigil_name": intent.sigil_name,
                        "sigil_scopes": sorted(intent.sigil_scopes),
                    },
                    queue_name=queue_name,
                ),
                auto_commit=True,
            )
            return self._to_record(row)

    async def get(self, run_id: str) -> RunRecord | None:
        """Return the run record for ``run_id`` (a UUID string), or ``None``."""
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.get_one_or_none(id=UUID(run_id))
            return self._to_record(row) if row is not None else None

    # One bounded re-read+retry under a lost CAS is enough under Topology A (a single
    # process, a single competing writer — R3): the fresh row can only have moved once.
    _CAS_RETRIES = 1

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a run's status with COMPARE-AND-SWAP concurrency (F4/H5, R3).

        The state machine is validated against the row read at the top, then the write
        is a conditional ``UPDATE ... WHERE id = :id AND status = :expected``. If a
        competing writer moved the row in the window, 0 rows update. Rather than
        blindly raise, we RE-READ the fresh truth and, if ``current → target`` is a
        LEGAL edge (e.g. a cancel losing to a concurrent QUEUED→RUNNING claim, then
        RUNNING→CANCELLED), retry the CAS against the fresh expected status (bounded,
        one loop). We raise `IllegalRunTransitionError` only when the fresh edge is
        genuinely illegal (e.g. CANCELLED over a DONE that won the race), and treat a
        concurrent writer that already reached this same target as a benign no-op.
        """
        from sqlalchemy import update

        from lychd.db.models import Run
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
                record = self._to_record(row)
                _apply_status(record, status, error=error)  # raises on an illegal edge
                result = cast(
                    "CursorResult[Any]",
                    await session.execute(
                        update(Run)
                        .where(Run.id == UUID(run_id), Run.status == expected.value)
                        .values(
                            status=record.status.value,
                            error=record.error,
                            attempt=record.attempt,
                            started_at=record.started_at,
                            finished_at=record.finished_at,
                        )
                    ),
                )
                await session.commit()
                if result.rowcount != 0:
                    return  # CAS won
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
        """Increment and return the run's enqueue seq."""
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.get_one_or_none(id=UUID(run_id))
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            next_seq = row.enqueue_seq + 1
            await svc.update({"enqueue_seq": next_seq}, item_id=UUID(run_id), auto_commit=True)
            return next_seq

    async def try_claim_run(self, run_id: str, *, enqueue_seq: int) -> bool:
        """CAS this exact QUEUED delivery → RUNNING; stale broker jobs lose."""
        from sqlalchemy import update

        from lychd.db.models import Run

        async with self._session_factory() as session:
            result = cast(
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
                        started_at=datetime.now(UTC),
                        error=None,
                    )
                ),
            )
            await session.commit()
            return result.rowcount == 1

    async def try_fail_queued(self, run_id: str, *, error: str) -> bool:
        """CAS QUEUED → FAILED without overwriting a worker claim."""
        from sqlalchemy import update

        from lychd.db.models import Run

        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(Run)
                    .where(Run.id == UUID(run_id), Run.status == RunStatus.QUEUED.value)
                    .values(
                        status=RunStatus.FAILED.value,
                        error=error,
                        finished_at=datetime.now(UTC),
                    )
                ),
            )
            await session.commit()
            return result.rowcount == 1

    async def try_fail_claimed(self, run_id: str, *, enqueue_seq: int, error: str) -> bool:
        """CAS the owned active hop to FAILED without touching a later resume."""
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
                        status=RunStatus.FAILED.value,
                        error=error,
                        finished_at=datetime.now(UTC),
                    )
                ),
            )
            await session.commit()
            return result.rowcount == 1

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record nothing (S8): the Consent row IS the durable record.

        The ghoul still calls this in `perform_run`; the DB impl needs no side map
        because `get_by_consent` reads the consent table directly.
        """
        _ = (run_id, consent_id)

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event as a Step row, persisting `event.seq` VERBATIM.

        Seq fidelity (F4/H5, Orb evidence): the Step's `seq` IS the channel event's
        seq — no insert-time `max(seq)+1` allocation, no retry-on-collision. Ordering
        is guaranteed upstream by the bus's per-run writer chain, so Step.seq equals
        emit order. The `uq_step_run_seq` constraint is now a pure integrity check.
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

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status``."""
        from lychd.db.models import Run
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            rows = await svc.list(Run.status == status.value)
            return [self._to_record(row) for row in rows]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id`` (S8: a direct consent-table select)."""
        from sqlalchemy import select

        from lychd.db.models import Consent

        try:
            cid = UUID(consent_id)
        except ValueError:
            return None  # malformed id → unknown (mirror get()'s do-not-invent-a-run stance)
        async with self._session_factory() as session:
            run_id = await session.scalar(select(Consent.run_id).where(Consent.id == cid))
        return await self.get(str(run_id)) if run_id is not None else None

    async def try_admit_consent(self, run_id: str) -> int | None:
        """CAS parked → QUEUED and allocate the resume sequence atomically.

        One conditional ``UPDATE`` changes status and increments ``enqueue_seq``.
        Returning the new value makes admission, delivery identity, and publication
        one logical hop even though broker publication remains a later operation.
        """
        from sqlalchemy import update

        from lychd.db.models import Run

        async with self._session_factory() as session:
            result = await session.execute(
                update(Run)
                .where(Run.id == UUID(run_id), Run.status == RunStatus.AWAITING_CONSENT.value)
                .values(
                    status=RunStatus.QUEUED.value,
                    enqueue_seq=Run.enqueue_seq + 1,
                )
                .returning(Run.enqueue_seq)
            )
            enqueue_seq = result.scalar_one_or_none()
            await session.commit()
            return int(enqueue_seq) if enqueue_seq is not None else None

    async def try_restore_consent_wait(self, run_id: str, *, enqueue_seq: int) -> bool:
        """CAS the exact QUEUED hop back to wait after resume publication failed.

        This is the inverse of ``try_admit_consent`` only for enqueue compensation;
        retaining ``enqueue_seq`` prevents reuse of a possibly accepted broker key.
        """
        from sqlalchemy import update

        from lychd.db.models import Run

        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(Run)
                    .where(
                        Run.id == UUID(run_id),
                        Run.status == RunStatus.QUEUED.value,
                        Run.enqueue_seq == enqueue_seq,
                    )
                    .values(status=RunStatus.AWAITING_CONSENT.value)
                ),
            )
            await session.commit()
            return result.rowcount == 1

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
            attempt=int(row.attempt),  # type: ignore[attr-defined]
            enqueue_seq=int(row.enqueue_seq),  # type: ignore[attr-defined]
            error=row.error,  # type: ignore[attr-defined]
            created_at=row.created_at,  # type: ignore[attr-defined]  # UUIDAuditBase; feeds the QUEUED-age sweep
            started_at=row.started_at,  # type: ignore[attr-defined]
            finished_at=row.finished_at,  # type: ignore[attr-defined]
        )
