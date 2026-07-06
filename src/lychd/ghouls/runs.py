"""The run substrate ghoul (A4-U4): `perform_run` + `reconcile_runs`.

`perform_run` is the SAQ task and the ONLY place a workflow graph executes: claim →
RUNNING → build `WorkflowServices` + `GraphRunner` → iterate → events on the shared
`RunEventBus` → single terminal `DONE` (or FAILED as a DONE carrying the terminal
status). Topology A: it runs in-process on the web loop (`separate_process=False`),
so the SSE handler and this task share one `RunEventBus`.

`reconcile_runs` is a startup/periodic rite: a process that dies mid-run leaves a
RUNNING row with no live task, so orphaned RUNNING rows are marked FAILED and their
terminal `DONE` emitted — no run stays stuck in RUNNING across a restart.

Consent is a Wave-1 placeholder: a run that parks a consent (via the ConsentLedger)
ends AWAITING_CONSENT and emits NO `DONE`, so the live consent card survives in the
open SSE stream. Honest park-and-resume is Wave 4 (spec-00-FINAL C3).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.runs import TERMINAL_STATUSES, IllegalRunTransitionError, RunStatus
from lychd.domain.cortex.stasis import LiveStasisPhylactery
from lychd.domain.cortex.substrate import get_run_substrate

if TYPE_CHECKING:
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.substrate import RunSubstrate

logger = structlog.get_logger()

_FAILURE_MESSAGE = (
    "The summoning faltered — no capability answered. Ensure a chat Soulstone is bound and warm, then speak again."
)

# A QUEUED row older than this at reconcile time lost its enqueue (F3/F9/H2): the
# `_enqueue` compensation should have failed it, but a crash between `create` and
# `_enqueue` can strand it QUEUED with no live job. Sweep it to FAILED.
RECONCILE_QUEUED_AFTER_S = 900


def _substrate(ctx: dict[str, Any]) -> RunSubstrate:
    """Return the run substrate for this job.

    Topology A invariant (F1/S7): there is exactly ONE substrate per process, built
    and published (`set_run_substrate`) once by `altar_services_lifespan`. Because
    the worker runs in-process on the web loop, `perform_run`/`reconcile_runs` read
    THAT substrate from the process memo (`get_run_substrate`) — same `RunEventBus`,
    same `RunLedger` the SSE handler sees. The `ctx["run_substrate"]` branch is a
    TEST-ONLY injection seam; production never populates it.
    """
    injected = ctx.get("run_substrate")
    if injected is not None:
        return injected
    return get_run_substrate()


async def perform_run(
    ctx: dict[str, Any],
    *,
    run_id: str,
    resume: bool = False,
    payload: str | None = None,
) -> dict[str, Any]:
    """Execute one run's workflow graph. The ONLY graph-execution site."""
    _ = (resume, payload)  # honest consent resume is Wave 4; placeholder ignores these
    substrate = _substrate(ctx)
    ledger = substrate.ledger
    run = await ledger.get(run_id)
    if run is None or run.status is not RunStatus.QUEUED:
        return {"status": "skipped", "run_id": run_id}  # stale / duplicate claim guard

    workflow = substrate.workflows.get(run.workflow_name)
    emitter = substrate.bus.emitter(run_id)
    if workflow is None:
        await ledger.set_status(run_id, RunStatus.RUNNING)
        await ledger.set_status(run_id, RunStatus.FAILED, error=f"unknown workflow: {run.workflow_name}")
        emitter.done(RunStatus.FAILED.value)
        return {"status": "failed", "run_id": run_id}

    persistence = LiveStasisPhylactery(job_id=run_id)
    runner: GraphRunner[Any] = GraphRunner(orchestrator=substrate.orchestrator, persistence=persistence)
    services = substrate.build_services()

    await ledger.set_status(run_id, RunStatus.RUNNING)
    emitter.status(RunStatus.RUNNING.value)
    try:
        await runner.run_graph(
            workflow.graph,
            workflow.start_node(),
            workflow.make_state(run.to_intent()),
            deps=services,
        )
    except asyncio.CancelledError:
        # Cancel path (F6/H6): free the assembled context floor and let the cancel
        # propagate. `engine.cancel` already wrote CANCELLED + emitted the terminal;
        # the finally's re-emit is dropped by the channel's closed-guard (F2/H3).
        substrate.context.release(run_id)
        raise
    except Exception as exc:
        logger.exception("perform_run_failed", run_id=run_id, workflow=run.workflow_name)
        _write_failed_turn(substrate, run_id=run_id, session_id=run.session_id)
        substrate.context.release(run_id)  # F6/H6: free the floor on failure
        await _settle_terminal(ledger, run_id, RunStatus.FAILED, error=str(exc))
        raise
    else:
        parked = substrate.sessions.pending_consent_for_run(run_id)
        if parked is not None:
            # Placeholder consent park: end AWAITING_CONSENT, emit NO done (card stays
            # live). The context floor is deliberately NOT released here — Wave 4 adds
            # release-on-park once AwaitConsent's re-assemble guard makes it safe (H6).
            await ledger.set_consent(run_id, parked.id)
            await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)
            return {"status": "awaiting_consent", "run_id": run_id}
        await _settle_terminal(ledger, run_id, RunStatus.DONE)
        return {"status": "done", "run_id": run_id}
    finally:
        # The never-hang guarantee, one place: emit the single terminal DONE from the
        # AUTHORITATIVE row status (cancel may have won the race), then close the
        # channel (F5/H4). A non-terminal park leaves the channel open on purpose.
        terminal = await ledger.get(run_id)
        if terminal is not None and terminal.status in TERMINAL_STATUSES:
            emitter.done(terminal.status.value)
            substrate.bus.close(run_id)


async def _settle_terminal(ledger: RunLedger, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
    """Write a terminal status race-tolerantly (F2/H3: one terminal writer in practice).

    If a competing writer (`engine.cancel`) already drove the row terminal, the write
    raises `IllegalRunTransitionError`; re-read, and if the row is now terminal treat
    it as benign (the other writer won) rather than exploding — the finally emits the
    single terminal from the settled truth.
    """
    try:
        await ledger.set_status(run_id, status, error=error)
    except IllegalRunTransitionError:
        fresh = await ledger.get(run_id)
        if fresh is not None and fresh.status in TERMINAL_STATUSES:
            logger.info("terminal_write_lost_race", run_id=run_id, attempted=status.value, settled=fresh.status.value)
            return
        raise


async def reconcile_runs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Fail runs stranded non-terminal by a dead process (F3/F9/H2).

    Two orphan classes are swept to FAILED (each emitting its terminal `DONE`):

    - RUNNING / AWAITING_HARDWARE: a crash mid-run leaves the row non-terminal with
      no live task. Blanket-failing every RUNNING row is CORRECT under Topology A —
      there is a single process and a single loop, so ANY RUNNING row at boot is by
      definition orphaned (its owning task died with the process; there is no live
      heartbeat to check). Revisit ONLY if a multi-process Topology B ever lands.
    - QUEUED older than `RECONCILE_QUEUED_AFTER_S`: `engine.submit` compensates a
      failed `_enqueue`, but a crash between `create` and `_enqueue` (or a lost
      broker job) can strand a QUEUED row with no job. An aged QUEUED row is failed
      with "enqueue lost" so it never keeps a stream on keepalives forever.
    """
    substrate = _substrate(ctx)
    ledger = substrate.ledger
    reconciled: list[str] = []
    for status in (RunStatus.RUNNING, RunStatus.AWAITING_HARDWARE):
        for run in await ledger.list_by_status(status):
            await ledger.set_status(run.run_id, RunStatus.FAILED, error="ghoul lost")
            await _emit_terminal(substrate, run.run_id)
            reconciled.append(run.run_id)

    # R8 (Wave-3 follow-up): two gaps left open here on purpose.
    #  1) This rite runs ONCE at web startup (lifespan) — it is not scheduled. Wave 3
    #     should register it as a saq CronJob (~300s) so a run stranded QUEUED mid
    #     process-lifetime is healed without waiting for a restart.
    #  2) saq's PG queue is durable, so an aged (>RECONCILE_QUEUED_AFTER_S) QUEUED row
    #     surviving a restart may still have a live job. The correct guard is a
    #     `queue.job(run_job_key(run.run_id, run.enqueue_seq))`-exists check before
    #     sweeping — deferred because reconcile's substrate carries no queue handle
    #     yet (adding one is Wave-3 wiring, not a half-build here).
    now = datetime.now(UTC)
    for run in await ledger.list_by_status(RunStatus.QUEUED):
        if (now - run.created_at).total_seconds() < RECONCILE_QUEUED_AFTER_S:
            continue
        await ledger.set_status(run.run_id, RunStatus.FAILED, error="enqueue lost")
        await _emit_terminal(substrate, run.run_id)
        reconciled.append(run.run_id)

    if reconciled:
        logger.warning("reconcile_runs", count=len(reconciled), run_ids=reconciled)
    return {"status": "reconciled", "count": len(reconciled)}


async def _emit_terminal(substrate: RunSubstrate, run_id: str) -> None:
    """Emit a reconciled run's terminal DONE onto a correctly-seeded, closed channel.

    R1: a fresh process restarts channel seqs at 0, but a swept run already has Step
    rows (it reached RUNNING → persisted seq 0), so a verbatim seq-0 terminal would
    collide with `uq_step_run_seq` and be dropped. Seed the freshly minted channel
    from the run's persisted next-seq so the terminal lands past the history.
    R2: close the channel after the emit — reconcile mints a channel per orphan and
    would otherwise leak one per startup sweep.
    """
    next_seq = await substrate.ledger.next_seq(run_id)
    substrate.bus.open(run_id, from_seq=next_seq)
    substrate.bus.emitter(run_id).done(RunStatus.FAILED.value)
    substrate.bus.close(run_id)


def _write_failed_turn(substrate: RunSubstrate, *, run_id: str, session_id: str) -> None:
    """Write a friendly failed agent turn so the settled slot renders the fault."""
    from lychd.domain.web.schemas import BridgeTurn

    try:
        substrate.sessions.add_turn(
            session_id,
            BridgeTurn(role="agent", content=_FAILURE_MESSAGE, run_id=run_id, state="failed"),
        )
    except Exception:  # noqa: BLE001 - turn bookkeeping must never mask the real failure
        logger.debug("failed_turn_write_skipped", run_id=run_id)
