"""The run substrate ghoul (A4-U4): `perform_run` + `reconcile_runs`.

`perform_run` is the SAQ task and the ONLY place a workflow graph executes: claim →
RUNNING → build `WorkflowServices` + `GraphRunner` → iterate → events on the shared
`RunEventBus` → single terminal `DONE` (or FAILED as a DONE carrying the terminal
status). Topology A: it runs in-process on the web loop (`use_server_lifespan=True`),
so the SSE handler and this task share one `RunEventBus`.

`reconcile_runs` is a startup/periodic rite: a process that dies mid-run leaves a
RUNNING row with no live task, so orphaned RUNNING rows are marked FAILED and their
terminal `DONE` emitted — no run stays stuck in RUNNING across a restart.

Consent is a Wave-1 placeholder: a run that parks a consent (via the ConsentLedger)
ends AWAITING_CONSENT and emits NO `DONE`, so the live consent card survives in the
open SSE stream. Honest park-and-resume is Wave 4 (spec-00-FINAL C3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunStatus
from lychd.domain.cortex.stasis import LiveStasisPhylactery
from lychd.domain.cortex.substrate import get_run_substrate

if TYPE_CHECKING:
    from lychd.domain.cortex.substrate import RunSubstrate

logger = structlog.get_logger()

_FAILURE_MESSAGE = (
    "The summoning faltered — no capability answered. Ensure a chat Soulstone is bound and warm, then speak again."
)


def _substrate(ctx: dict[str, Any]) -> RunSubstrate:
    """Return the run substrate from the SAQ ctx, falling back to the process memo."""
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
    except Exception as exc:
        logger.exception("perform_run_failed", run_id=run_id, workflow=run.workflow_name)
        _write_failed_turn(substrate, run_id=run_id, session_id=run.session_id)
        await ledger.set_status(run_id, RunStatus.FAILED, error=str(exc))
        raise
    else:
        parked = substrate.sessions.pending_consent_for_run(run_id)
        if parked is not None:
            # Placeholder consent park: end AWAITING_CONSENT, emit NO done (card stays live).
            await ledger.set_consent(run_id, parked.id)
            await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)
            return {"status": "awaiting_consent", "run_id": run_id}
        await ledger.set_status(run_id, RunStatus.DONE)
        return {"status": "done", "run_id": run_id}
    finally:
        terminal = await ledger.get(run_id)
        if terminal is not None and terminal.status in TERMINAL_STATUSES:
            emitter.done(terminal.status.value)  # the never-hang guarantee, one place


async def reconcile_runs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Fail orphaned RUNNING/AWAITING_HARDWARE runs left by a dead process.

    A crash mid-run leaves the row RUNNING with no live task. On startup (and
    periodically) mark such orphans FAILED and emit their terminal `DONE`, so no run
    survives a restart stuck in a non-terminal, unclaimed state.
    """
    substrate = _substrate(ctx)
    ledger = substrate.ledger
    reconciled: list[str] = []
    for status in (RunStatus.RUNNING, RunStatus.AWAITING_HARDWARE):
        for run in await ledger.list_by_status(status):
            await ledger.set_status(run.run_id, RunStatus.FAILED, error="ghoul lost")
            substrate.bus.emitter(run.run_id).done(RunStatus.FAILED.value)
            reconciled.append(run.run_id)
    if reconciled:
        logger.warning("reconcile_runs", count=len(reconciled), run_ids=reconciled)
    return {"status": "reconciled", "count": len(reconciled)}


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
