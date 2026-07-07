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

from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from lychd.domain.cortex.runs import TERMINAL_STATUSES, IllegalRunTransitionError, RunHandle, RunStatus

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
    "run_job_key",
]


def run_job_key(run_id: str, enqueue_seq: int) -> str:
    """Return the SAQ job key: unique per (run, resume-hop); idempotent within a hop."""
    return f"run:{run_id}:{enqueue_seq}"


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
# number is INVERTED once, at the single enqueue site (`_enqueue`: `100 - run.priority`).
# Keep these numbers intuitive here; only the wire is flipped.
DEFAULT_ROUTING: dict[str, RouteRule] = {
    "default": RouteRule(queue="runs", priority=50),
    "bridge": RouteRule(queue="runs", priority=70),
    "cli": RouteRule(queue="runs", priority=50),
    "rite": RouteRule(queue="rites", priority=20),
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


@dataclass
class RunEngine:
    """The single run entry point. Routes once, persists, enqueues onto SAQ."""

    ledger: RunLedger
    bus: RunEventBus
    workflows: Any  # WorkflowRegistry (structural; avoids an agents→cortex import cycle)
    queue_router: QueueRouter
    queues: Mapping[str, RunQueue]

    async def submit(self, intent: Intent) -> RunHandle:
        """Route once, persist QUEUED, open the channel, and enqueue `perform_run`.

        S3: the run id is the LEDGER's canonical id (`run.run_id`); `intent.run_id`
        is advisory client-correlation only (stashed in the intent JSONB). The
        handle and every downstream surface (SSE URL, Step rows, stasis path, lease
        holder) key on `run.run_id`.

        Compensation (F3/H2): if `_enqueue` raises (broker down, or an unknown
        physical queue) the QUEUED row is not left to rot — it is failed, a terminal
        `DONE` is emitted so any open stream never hangs, the channel is closed, and
        the original error re-raises for the caller.
        """
        workflow = self.workflows.route(intent)
        queue_name, priority = self.queue_router.resolve(intent)
        run = await self.ledger.create(
            intent,
            workflow_name=workflow.name,
            queue_name=queue_name,
            priority=priority,
        )
        channel = self.bus.open(run.run_id)
        try:
            await self._enqueue(run)
        except Exception as exc:
            await self._compensate_enqueue_failure(run.run_id, exc)
            raise
        return RunHandle(run_id=run.run_id, workflow_name=workflow.name, channel=channel)

    async def _compensate_enqueue_failure(self, run_id: str, exc: Exception) -> None:
        """Fail an un-enqueued QUEUED run, emit its terminal DONE, and close it."""
        with suppress(Exception):  # compensation must never mask the enqueue error
            await self.ledger.set_status(run_id, RunStatus.FAILED, error=f"enqueue failed: {exc}")
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
        await self._abort_job(run)
        try:
            await self.ledger.set_status(run_id, RunStatus.CANCELLED)
        except IllegalRunTransitionError:
            fresh = await self.ledger.get(run_id)
            if fresh is not None and fresh.status in TERMINAL_STATUSES:
                return  # completion won the race — already terminal, cancel is a no-op
            raise
        self.bus.emitter(run_id).done(RunStatus.CANCELLED.value)
        self.bus.close(run_id)

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        """Consent verdict seam (C3): re-enqueue the parked run for a resume hop.

        Both verdicts re-enqueue: AWAITING_CONSENT → QUEUED, then a resume hop reads
        the verdict from the ConsentLedger (never a payload). ``approved`` is kept for
        the seam signature + logging only — the row IS the durable verdict.
        Idempotent: a double-click / replayed CLI over a non-parked run is a no-op.
        """
        _ = approved
        run = await self.ledger.get_by_consent(consent_id)
        if run is None or run.status is not RunStatus.AWAITING_CONSENT:
            return
        await self.ledger.set_status(run.run_id, RunStatus.QUEUED)
        refreshed = await self.ledger.get(run.run_id) or run
        await self._enqueue(refreshed, resume=True)

    async def _enqueue(self, run: RunRecord, *, resume: bool = False) -> None:
        """Enqueue `perform_run` for the run on its physical queue (unique key)."""
        seq = await self.ledger.bump_enqueue_seq(run.run_id)
        queue = self.queues[run.queue_name]
        await queue.enqueue(
            "perform_run",
            run_id=run.run_id,
            resume=resume,
            key=run_job_key(run.run_id, seq),
            retries=0,  # graph retries are GraphRunner's job, not SAQ's
            # Wire inversion (R9): doctrine is higher=hotter, saq dequeues lowest-first,
            # so a higher `run.priority` must map to a LOWER saq priority number.
            priority=100 - run.priority,
        )

    async def _abort_job(self, run: RunRecord) -> None:
        """Abort the run's current SAQ job if still present."""
        queue = self.queues.get(run.queue_name)
        if queue is None:
            return
        job = await queue.job(run_job_key(run.run_id, run.enqueue_seq))
        if job is not None:
            await queue.abort(job, "cancelled by the Magus")
