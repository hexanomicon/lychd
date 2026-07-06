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
from uuid import UUID

from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import (
    TERMINAL_STATUSES,
    IllegalRunTransitionError,
    RunRecord,
    RunStatus,
    can_transition,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEvent

__all__ = ["DbRunLedger", "InMemoryRunLedger", "RunLedger"]


class RunLedger(Protocol):
    """The run-truth surface consumed by the engine and the ghoul plane."""

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
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

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id a run is parked on."""
        ...

    async def set_stasis_path(self, run_id: str, path: str | None) -> None:
        """Record (or clear) the durable-stasis checkpoint path."""
        ...

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event to the run's Step ledger."""
        ...

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status`` (feeds `reconcile_runs`)."""
        ...

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id`` (feeds `engine.approve`)."""
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

    def __init__(self) -> None:
        """Create an empty ledger."""
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[RunEvent]] = {}

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        queue_name: str,
        priority: int,
    ) -> RunRecord:
        """Persist a fresh run as QUEUED keyed by ``intent.run_id``."""
        record = RunRecord(
            run_id=intent.run_id,
            session_id=intent.session_id,
            workflow_name=workflow_name,
            source=intent.source,
            queue_name=queue_name,
            priority=priority,
            status=RunStatus.QUEUED,
            prompt=intent.prompt,
            sigil_scopes=intent.sigil_scopes,
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

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id."""
        self._require(run_id).consent_id = consent_id

    async def set_stasis_path(self, run_id: str, path: str | None) -> None:
        """Record (or clear) the durable-stasis path."""
        self._require(run_id).stasis_path = path

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event to the run's step list."""
        if event.kind is RunEventKind.TOKEN:
            return
        self._events.setdefault(event.run_id, []).append(event)

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status``."""
        return [record for record in self._runs.values() if record.status is status]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id``."""
        for record in self._runs.values():
            if record.consent_id == consent_id:
                return record
        return None

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
        self._consent_index: dict[str, str] = {}  # consent_id -> run_id (Wave-4 seam)

    async def create(
        self,
        intent: Intent,
        *,
        workflow_name: str,
        queue_name: str,
        priority: int,
    ) -> RunRecord:
        """Insert a QUEUED `Run` row and return its record (run_id = str(row.id))."""
        from lychd.db.models import Run
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.create(
                Run(
                    workflow_name=workflow_name,
                    source=intent.source,
                    status=RunStatus.QUEUED.value,
                    priority=priority,
                    sigil_name="magus",
                    intent={
                        "session_id": intent.session_id,
                        "run_id": intent.run_id,
                        "prompt": intent.prompt,
                        "source": intent.source,
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

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Advance a run's status, validated against the state machine."""
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            row = await svc.get_one_or_none(id=UUID(run_id))
            if row is None:
                msg = f"Unknown run: {run_id}"
                raise KeyError(msg)
            record = self._to_record(row)
            _apply_status(record, status, error=error)
            await svc.update(
                {
                    "status": record.status.value,
                    "error": record.error,
                    "attempt": record.attempt,
                    "started_at": record.started_at,
                    "finished_at": record.finished_at,
                },
                item_id=UUID(run_id),
                auto_commit=True,
            )

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

    async def set_consent(self, run_id: str, consent_id: str | None) -> None:
        """Record (or clear) the consent id in the best-effort side map (Wave-4 seam)."""
        self._consent_index = {cid: rid for cid, rid in self._consent_index.items() if rid != run_id}
        if consent_id is not None:
            self._consent_index[consent_id] = run_id

    async def set_stasis_path(self, run_id: str, path: str | None) -> None:
        """Record (or clear) the durable-stasis path on the run row."""
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            await svc.update({"stasis_path": path}, item_id=UUID(run_id), auto_commit=True)

    async def append_event(self, event: RunEvent) -> None:
        """Append one non-TOKEN event as a Step row."""
        if event.kind is RunEventKind.TOKEN:
            return
        from lychd.domain.cortex.services import StepService

        node_key = event.data if event.kind is RunEventKind.NODE else None
        async with self._session_factory() as session:
            svc = StepService(session=session)
            await svc.append(
                run_id=UUID(event.run_id),
                kind=event.kind.value,
                payload={"data": event.data, "meta": event.meta},
                node_key=node_key,
            )

    async def list_by_status(self, status: RunStatus) -> list[RunRecord]:
        """Return every run currently in ``status``."""
        from lychd.db.models import Run
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            svc = RunService(session=session)
            rows = await svc.list(Run.status == status.value)
            return [self._to_record(row) for row in rows]

    async def get_by_consent(self, consent_id: str) -> RunRecord | None:
        """Return the run parked on ``consent_id`` (best-effort side map, Wave-4 seam)."""
        run_id = self._consent_index.get(consent_id)
        return await self.get(run_id) if run_id is not None else None

    @staticmethod
    def _to_record(row: object) -> RunRecord:
        """Map a `Run` ORM row to a storage-agnostic `RunRecord`."""
        intent: dict[str, object] = getattr(row, "intent", {}) or {}
        scopes_val = intent.get("sigil_scopes", [])
        scopes: frozenset[str] = frozenset[str]()
        if isinstance(scopes_val, list):
            scopes = frozenset(str(s) for s in cast("list[Any]", scopes_val))
        return RunRecord(
            run_id=str(row.id),  # type: ignore[attr-defined]
            session_id=str(intent.get("session_id", "")),
            workflow_name=str(row.workflow_name),  # type: ignore[attr-defined]
            source=str(row.source),  # type: ignore[attr-defined]
            queue_name=str(row.queue_name),  # type: ignore[attr-defined]
            priority=int(row.priority),  # type: ignore[attr-defined]
            status=RunStatus(str(row.status)),  # type: ignore[attr-defined]
            prompt=str(intent.get("prompt", "")),
            sigil_scopes=scopes,
            attempt=int(row.attempt),  # type: ignore[attr-defined]
            enqueue_seq=int(row.enqueue_seq),  # type: ignore[attr-defined]
            error=row.error,  # type: ignore[attr-defined]
            stasis_path=row.stasis_path,  # type: ignore[attr-defined]
            started_at=row.started_at,  # type: ignore[attr-defined]
            finished_at=row.finished_at,  # type: ignore[attr-defined]
        )
