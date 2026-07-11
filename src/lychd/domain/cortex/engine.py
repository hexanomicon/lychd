"""`RunEngine` + `QueueRouter` — the single run entry point (A4 §6, C2).

`RunEngine.submit(intent)` is the one law for every surface (Bridge now; CLI and
A2A later): route ONCE via the `WorkflowRegistry`, resolve `(queue_name, priority)`
via the `QueueRouter` (the `[orchestration.routing]` map), persist a QUEUED `Run`
via the `RunLedger`, open the run's channel on the `RunEventBus`, and enqueue
`perform_run` onto the SAQ `runs` queue. The `asyncio.create_task` path in
`agents/router.submit` is gone — its logic lives here and in `ghouls/runs.py`.

Consent is a Wave-1 placeholder: `approve` exists as the AWAITING_CONSENT re-enqueue
seam, but honest HitL resume is Wave 4. `cancel` aborts the SAQ job by key and
writes the terminal `CANCELLED` + `DONE`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.priority import (
    PRIORITY_BACKGROUND,
    PRIORITY_DEFAULT,
    PRIORITY_INTERACTIVE,
    saq_wire_priority,
)
from lychd.domain.cortex.runs import TERMINAL_STATUSES, IllegalRunTransitionError, RunHandle, RunStatus
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord

__all__ = [
    "DEFAULT_ROUTING",
    "QueueRouter",
    "RouteRule",
    "RunEngine",
    "RunQueue",
    "admit_consent_resume",
    "enqueue_run",
    "run_job_key",
]


def run_job_key(run_id: str, enqueue_seq: int) -> str:
    """Return the SAQ job key: unique per (run, resume-hop); idempotent within a hop."""
    return f"run:{run_id}:{enqueue_seq}"


async def enqueue_run(
    queues: Mapping[str, RunQueue],
    ledger: RunLedger,
    run: RunRecord,
    *,
    resume: bool = False,
    enqueue_seq: int | None = None,
) -> None:
    """Enqueue `perform_run` for a run on its physical queue under a unique hop key.

    The ONE enqueue law, shared by `RunEngine._enqueue` and `perform_run`'s post-flip
    consent re-admission (F1) so both mint the same idempotent SAQ job key + priority.
    """
    seq = enqueue_seq if enqueue_seq is not None else await ledger.bump_enqueue_seq(run.run_id)
    queue = queues[run.queue_name]
    await queue.enqueue(
        "perform_run",
        run_id=run.run_id,
        resume=resume,
        enqueue_seq=seq,
        key=run_job_key(run.run_id, seq),
        retries=0,  # graph retries are GraphRunner's job, not SAQ's
        timeout=0,  # no broker wall clock; graph/orchestrator own bounded waits
        # Wire inversion (R9): doctrine is higher=hotter, saq dequeues lowest-first.
        # The one and only inversion point lives in `saq_wire_priority`.
        priority=saq_wire_priority(run.priority),
    )


async def admit_consent_resume(
    queues: Mapping[str, RunQueue],
    ledger: RunLedger,
    run: RunRecord,
) -> bool:
    """Atomically admit and publish one consent resume hop.

    Cancellation may arrive while the admission CAS is committing or in the gap
    before broker publication. Shield the CAS, then compensate every post-admission
    failure back to ``AWAITING_CONSENT``. ``enqueue_seq`` remains monotonic because a
    job key that may have reached the broker is never reused.
    """
    admit_task = asyncio.ensure_future(ledger.try_admit_consent(run.run_id))
    try:
        enqueue_seq = await asyncio.shield(admit_task)
    except asyncio.CancelledError:
        enqueue_seq = await complete_under_cancellation(admit_task)
        if enqueue_seq is not None:
            await complete_under_cancellation(ledger.try_restore_consent_wait(run.run_id, enqueue_seq=enqueue_seq))
        raise
    if enqueue_seq is None:
        return False
    try:
        refreshed = await ledger.get(run.run_id) or run
        await enqueue_run(
            queues,
            ledger,
            refreshed,
            resume=True,
            enqueue_seq=enqueue_seq,
        )
    except BaseException:
        await complete_under_cancellation(ledger.try_restore_consent_wait(run.run_id, enqueue_seq=enqueue_seq))
        raise
    return True


class RunQueue(Protocol):
    """The narrow SAQ-queue surface the engine needs (`saq.Queue` satisfies it)."""

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any | None: ...

    async def job(self, job_key: str, /) -> Any | None: ...

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None: ...


@dataclass(frozen=True)
class RouteRule:
    """One `[orchestration.routing]` entry: which physical queue, at what priority."""

    queue: str
    priority: int


# [orchestration.routing] — intent source → (queue, default priority 0..100).
# Agent 7 wires TOML loading of this shape; these are the doctrine defaults (A4 §0).
#
# Priority direction (R9): doctrine keeps HIGHER = more important everywhere these
# numbers are read or tuned (bridge=70 is hotter than cli=50). saq's postgres queue,
# however, dequeues `ORDER BY priority ASC` (lowest number first), so the doctrine
# number is INVERTED once, in `saq_wire_priority`. Keep these numbers intuitive here.
DEFAULT_ROUTING: dict[str, RouteRule] = {
    "default": RouteRule(queue="runs", priority=PRIORITY_DEFAULT),
    "bridge": RouteRule(queue="runs", priority=PRIORITY_INTERACTIVE),
    "cli": RouteRule(queue="runs", priority=PRIORITY_DEFAULT),
    "rite": RouteRule(queue="rites", priority=PRIORITY_BACKGROUND),
}


@dataclass(frozen=True)
class QueueRouter:
    """Resolve `(queue_name, priority)` for an intent from the routing table.

    Priority precedence: an explicit `Intent.priority` overrides the per-source
    default; an unknown source falls back to the ``default`` rule.
    """

    routing: Mapping[str, RouteRule] = field(default_factory=lambda: dict(DEFAULT_ROUTING))

    def resolve(self, intent: Intent) -> tuple[str, int]:
        """Return ``(queue_name, priority)`` for ``intent``."""
        rule = self.routing.get(intent.source) or self.routing["default"]
        priority = intent.priority if intent.priority is not None else rule.priority
        return rule.queue, priority


class RunEngine:
    """The single run entry point. Routes once, persists, enqueues onto SAQ.

    This service is intentionally not a dataclass: web dependency frameworks
    interpret dataclasses as request-data schemas and would try to materialize its
    infrastructure collaborators (ledger, bus, queues) from HTTP input.
    """

    __slots__ = ("bus", "cancellations", "ledger", "queue_router", "queues", "stasis_store", "workflows")

    def __init__(
        self,
        *,
        ledger: RunLedger,
        bus: RunEventBus,
        workflows: Any,
        queue_router: QueueRouter,
        queues: Mapping[str, RunQueue],
        cancellations: RunCancellationCoordinator | None = None,
        stasis_store: Any | None = None,
    ) -> None:
        """Bind the already-constructed run collaborators."""
        self.ledger = ledger
        self.bus = bus
        self.workflows = workflows
        self.queue_router = queue_router
        self.queues = queues
        self.cancellations = cancellations or RunCancellationCoordinator()
        if stasis_store is None:
            from lychd.domain.cortex.stasis import InMemoryStasisStore

            stasis_store = InMemoryStasisStore()
        self.stasis_store = stasis_store

    async def submit(self, intent: Intent) -> RunHandle:
        """Route once, persist QUEUED, open the channel, and enqueue `perform_run`.

        S3: the run id is the LEDGER's canonical id (`run.run_id`); `intent.run_id`
        is advisory client-correlation only (stashed in the intent JSONB). The
        handle and every downstream surface (SSE URL, Step rows, checkpoint row, lease
        holder) key on `run.run_id`.

        Compensation (F3/H2): if `_enqueue` raises (broker down, or an unknown
        physical queue) the QUEUED row is not left to rot — it is failed, a terminal
        `DONE` is emitted so any open stream never hangs, the channel is closed, and
        the original error re-raises for the caller.
        """
        workflow = self.workflows.route(intent)
        queue_name, priority = self.queue_router.resolve(intent)
        create_task = asyncio.ensure_future(
            self.ledger.create(
                intent,
                workflow_name=workflow.name,
                queue_name=queue_name,
                priority=priority,
            )
        )
        try:
            run = await asyncio.shield(create_task)
        except asyncio.CancelledError as exc:
            # The DB commit may have won the cancellation race. Learn the
            # canonical id, then settle only an unclaimed row before propagating.
            run = await complete_under_cancellation(create_task)
            await complete_under_cancellation(self._compensate_enqueue_failure(run.run_id, exc))
            raise
        channel = self.bus.open(run.run_id)
        try:
            await self._enqueue(run)
        except BaseException as exc:
            await complete_under_cancellation(self._compensate_enqueue_failure(run.run_id, exc))
            raise
        return RunHandle(run_id=run.run_id, workflow_name=workflow.name, channel=channel)

    async def _compensate_enqueue_failure(self, run_id: str, exc: BaseException) -> None:
        """Fail only an unclaimed QUEUED run, then terminate its event channel."""
        settled = False
        with suppress(Exception):  # compensation must never mask the enqueue error
            settled = await self.ledger.try_fail_queued(run_id, error=f"enqueue failed: {exc}")
        if not settled:
            return  # a worker already claimed the ambiguously published job
        with suppress(Exception):
            self.bus.emitter(run_id).done(RunStatus.FAILED.value)
            self.bus.close(run_id)

    async def cancel(self, run_id: str) -> None:
        """Abort the run's SAQ job (by key), mark CANCELLED, emit the terminal DONE.

        Race tolerance (R2/R3/R7): the CAS `set_status` retries a lost cancel against
        a legal fresh edge (e.g. losing a QUEUED→RUNNING claim, then RUNNING→CANCELLED).
        If completion WON the race instead (the fresh row is already terminal, so
        DONE→CANCELLED is genuinely illegal), that is a benign no-op — the run is
        already terminal and `perform_run`'s finally emitted its DONE and closed the
        channel — not a 500 to the caller. On the winning path the channel is CLOSED
        after the terminal emit (R2: cancel must close what it will never re-enter).
        """
        run = await self.ledger.get(run_id)
        if run is None or run.status in TERMINAL_STATUSES:
            return
        cancel_task = asyncio.ensure_future(self._cancel_run(run))
        try:
            await asyncio.shield(cancel_task)
        except asyncio.CancelledError:
            # A disconnected caller must not interrupt the abort/status sequence.
            await complete_under_cancellation(cancel_task)
            raise

    async def _cancel_run(self, run: RunRecord) -> None:
        """Abort and durably settle one run while publishing the worker fence."""
        # Elect exactly one abort/status writer. A concurrent waiter retries only
        # when the leader failed to reach a terminal row; this prevents duplicate
        # terminal events while preserving retry after an abort infrastructure error.
        while not self.cancellations.begin(run.run_id):
            await self.cancellations.wait(run.run_id)
            fresh = await self.ledger.get(run.run_id)
            if fresh is None or fresh.status in TERMINAL_STATUSES:
                return
            run = fresh
        try:
            # Re-read after election. Another request may have completed cancellation
            # between this caller's optimistic read and its task being scheduled.
            fresh = await self.ledger.get(run.run_id)
            if fresh is None or fresh.status in TERMINAL_STATUSES:
                return
            run = fresh
            await self._abort_job(run)
            try:
                await self.ledger.set_status(run.run_id, RunStatus.CANCELLED)
            except IllegalRunTransitionError:
                fresh = await self.ledger.get(run.run_id)
                if fresh is not None and fresh.status in TERMINAL_STATUSES:
                    return  # completion won the race — cancel is a benign no-op
                raise
            self.bus.emitter(run.run_id).done(RunStatus.CANCELLED.value)
            self.bus.close(run.run_id)
            await self._discard_stasis_checkpoint(run.run_id)
        finally:
            self.cancellations.finish(run.run_id)

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        """Consent verdict seam (C3): admit the parked run for a resume hop.

        Both verdicts re-enqueue (AWAITING_CONSENT → QUEUED); the resume hop reads the
        verdict from the ConsentLedger (never a payload). ``approved`` is kept for the
        seam signature + logging only — the row IS the durable verdict.

        The AWAITING_CONSENT → QUEUED edge is the SINGLE admission gate (F1/F4):
        `try_admit_consent` is an atomic CAS, so a double-click / replayed CLI, and a
        race against `perform_run`'s post-flip re-check, resolve to exactly one enqueue.
        A call that does not win the CAS (not parked, already admitted, terminal) no-ops.
        """
        _ = approved
        run = await self.ledger.get_by_consent(consent_id)
        if run is None:
            return
        await admit_consent_resume(self.queues, self.ledger, run)

    async def _enqueue(self, run: RunRecord, *, resume: bool = False) -> None:
        """Enqueue `perform_run` for the run on its physical queue (unique key)."""
        await enqueue_run(self.queues, self.ledger, run, resume=resume)

    async def _abort_job(self, run: RunRecord) -> None:
        """Abort the run's current SAQ job if still present."""
        queue = self.queues.get(run.queue_name)
        if queue is None:
            return
        job = await queue.job(run_job_key(run.run_id, run.enqueue_seq))
        if job is not None:
            await queue.abort(job, "cancelled by the Magus")

    async def _discard_stasis_checkpoint(self, run_id: str) -> None:
        """Delete a cancelled run's checkpoint from the shared Stasis store."""
        await self.stasis_store.delete(run_id)
