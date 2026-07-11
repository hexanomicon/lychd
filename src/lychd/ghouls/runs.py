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
from typing import TYPE_CHECKING, Any, Protocol

import structlog

from lychd.domain.cortex.engine import admit_consent_resume, run_job_key
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.runs import TERMINAL_STATUSES, IllegalRunTransitionError, RunParked, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, LiveStasisPhylactery
from lychd.domain.cortex.substrate import get_run_substrate
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow
    from lychd.domain.cortex.events import RunEmitter
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.cortex.substrate import RunSubstrate
    from lychd.extensions.protocols import PhylacteryProtocol

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


def _phylactery_for(run: RunRecord, workflow: Workflow, substrate: RunSubstrate) -> PhylacteryProtocol:
    """Select durable Postgres-backed Stasis for durable workflows, else live memory."""
    if workflow.durable:
        return DurableStasisPhylactery(job_id=run.run_id, store=substrate.stasis_store)
    return LiveStasisPhylactery(job_id=run.run_id)


async def _await_claim_gate(substrate: RunSubstrate) -> None:
    """Park on the broker's claim gate while intake is paused for a transition.

    Drain honesty is the LeaseLedger's; pausing merely stops NEW runs from claiming
    while a physical transition is in flight. The gate lives on the production
    `GhoulBroker`; narrow test fakes may expose none, so the wait is skipped then.
    """
    broker = getattr(substrate.orchestrator, "worker_broker", None)
    gate = getattr(broker, "claim_gate", None)
    if gate is not None:
        await gate.wait()


async def perform_run(  # noqa: C901, PLR0912, PLR0915 - honest fresh/resume/park/fail path
    ctx: dict[str, Any],
    *,
    run_id: str,
    resume: bool = False,
    enqueue_seq: int | None = None,
) -> dict[str, Any]:
    """Execute one run's workflow graph. The ONLY graph-execution site.

    A fresh hop iterates from the start node; a ``resume`` hop (a re-enqueued
    consent verdict) resumes the durable checkpoint. The verdict is read from the
    ConsentLedger inside `AwaitConsent` — never carried in a payload (C3).
    """
    substrate = _substrate(ctx)
    await _await_claim_gate(substrate)
    ledger = substrate.ledger
    run = await ledger.get(run_id)
    delivery_seq = run.enqueue_seq if run is not None and enqueue_seq is None else enqueue_seq
    if run is None or delivery_seq is None or run.status is not RunStatus.QUEUED or run.enqueue_seq != delivery_seq:
        return {"status": "skipped", "run_id": run_id}  # stale / duplicate claim guard
    claim_enqueue_seq = delivery_seq
    claim_task = asyncio.ensure_future(ledger.try_claim_run(run_id, enqueue_seq=claim_enqueue_seq))
    try:
        claimed = await asyncio.shield(claim_task)
    except asyncio.CancelledError:
        claimed = await complete_under_cancellation(claim_task)
        if claimed:
            settled = await complete_under_cancellation(
                _settle_interrupted_claim(
                    substrate,
                    run,
                    enqueue_seq=claim_enqueue_seq,
                    error="run worker cancelled",
                    persistence=None,
                )
            )
            if settled:
                await complete_under_cancellation(_emit_terminal(substrate, run_id))
        raise
    if not claimed:
        return {"status": "skipped", "run_id": run_id}  # atomic redelivery fence

    emitter: RunEmitter | None = None
    persistence: PhylacteryProtocol | None = None
    terminal_owned = False

    async def settle_terminal(status: RunStatus, *, error: str | None = None) -> None:
        """Commit terminal truth despite cancellation and preserve emit ownership."""
        nonlocal terminal_owned
        settle_task = asyncio.ensure_future(_settle_terminal(ledger, run_id, status, error=error))
        try:
            terminal_owned = await asyncio.shield(settle_task)
        except asyncio.CancelledError:
            # The commit may have won. Learn its ownership before propagating so
            # finally cannot mistake our terminal row for somebody else's event.
            terminal_owned = await complete_under_cancellation(settle_task)
            raise

    try:
        workflow = substrate.workflows.get(run.workflow_name)
        if resume:
            # R1-safe channel seeding: a durable resume after restart mints a fresh channel
            # that MUST continue the persisted seq, never restart at 0 (else re-collided,
            # silently-shed Step rows). Seed BEFORE any emitter opens the channel.
            substrate.bus.open(run_id, from_seq=await ledger.next_seq(run_id))
        emitter = substrate.bus.emitter(run_id)
        if workflow is None:
            # F2: settle the terminal INSIDE the try so the finally emits the single DONE
            # and CLOSES the channel — an early return here leaked the open channel,
            # tailing keepalives forever.
            await settle_terminal(
                RunStatus.FAILED,
                error=f"unknown workflow: {run.workflow_name}",
            )
            await _cleanup_claim_resources(
                substrate,
                run,
                persistence=None,
            )
            return {"status": "failed", "run_id": run_id}

        if resume and not await substrate.stasis_store.exists(run.run_id):
            # Honest failure: never a silent re-run of a run whose checkpoint is gone.
            # F2: settle inside the try so the finally emits the terminal + closes the channel.
            await settle_terminal(RunStatus.FAILED, error="stasis lost")
            await _cleanup_claim_resources(
                substrate,
                run,
                persistence=None,
            )
            return {"status": "failed", "run_id": run_id}

        persistence = _phylactery_for(run, workflow, substrate)

        async def _on_stasis_enter() -> None:
            # The run parks while the orchestrator transitions hardware (C7). It holds no
            # lease while parked, so it never blocks its own drain (requester-not-counted).
            await ledger.set_status(run_id, RunStatus.AWAITING_HARDWARE)

        async def _on_stasis_exit() -> None:
            await ledger.set_status(run_id, RunStatus.RUNNING)

        runner: GraphRunner[Any] = GraphRunner(
            orchestrator=substrate.orchestrator,
            persistence=persistence,
            signal_priority=run.priority,
            on_stasis_enter=_on_stasis_enter,
            on_stasis_exit=_on_stasis_exit,
        )
        from lychd.domain.codex.sigil import Sigil

        services = substrate.build_services(
            sigil=Sigil(name=run.sigil_name, scopes=run.sigil_scopes),
        )

        emitter.status(RunStatus.RUNNING.value)
        if resume:
            result = await runner.resume_graph(workflow.graph, deps=services)
        else:
            result = await runner.run_graph(
                workflow.graph,
                workflow.start_node(),
                workflow.make_state(run.to_intent()),
                deps=services,
            )
        if isinstance(result, RunParked):
            return await _commit_consent_park(substrate, ledger, emitter, run_id, result)
        await settle_terminal(RunStatus.DONE)
        await _cleanup_claim_resources(
            substrate,
            run,
            persistence=persistence,
        )
    except asyncio.CancelledError:
        # Once the claim CAS wins, every cancellation path settles durable truth
        # before propagating, including setup/checkpoint and resume-seeding awaits.
        if terminal_owned:
            await complete_under_cancellation(
                _cleanup_claim_resources(
                    substrate,
                    run,
                    persistence=persistence,
                )
            )
        else:
            terminal_owned = await complete_under_cancellation(
                _settle_interrupted_claim(
                    substrate,
                    run,
                    enqueue_seq=claim_enqueue_seq,
                    error="run worker cancelled",
                    persistence=persistence,
                )
            )
        raise
    except Exception as exc:
        logger.exception("perform_run_failed", run_id=run_id, workflow=run.workflow_name)
        if terminal_owned:
            await complete_under_cancellation(
                _cleanup_claim_resources(
                    substrate,
                    run,
                    persistence=persistence,
                )
            )
        else:
            terminal_owned = await complete_under_cancellation(
                _settle_interrupted_claim(
                    substrate,
                    run,
                    enqueue_seq=claim_enqueue_seq,
                    error=str(exc),
                    persistence=persistence,
                )
            )
            if terminal_owned:
                await _write_failed_turn(substrate, run_id=run_id, session_id=run.session_id)
        raise
    else:
        return {"status": "done", "run_id": run_id}
    finally:
        # The never-hang guarantee, one place: emit the single terminal DONE from the
        # AUTHORITATIVE row status (cancel may have won the race), then close the
        # channel (F5/H4). A non-terminal park/resume leaves the channel open on purpose.
        terminal = await complete_under_cancellation(ledger.get(run_id))
        if terminal_owned and terminal is not None and terminal.status in TERMINAL_STATUSES:
            if emitter is None:
                await complete_under_cancellation(_emit_terminal(substrate, run_id))
            else:
                emitter.done(terminal.status.value)
                substrate.bus.close(run_id)


async def _settle_interrupted_claim(
    substrate: RunSubstrate,
    run: RunRecord,
    *,
    enqueue_seq: int,
    error: str,
    persistence: PhylacteryProtocol | None,
) -> bool:
    """Let an API cancellation settle first, else fail this exact claimed hop.

    SAQ marks an active job aborting before its worker task receives cancellation.
    Under Topology A the API and worker share ``cancellations``: the worker waits for
    the API's durable ``CANCELLED`` write instead of racing it with ``FAILED``.  If
    abort/status settlement failed, the row remains active and this delivery falls
    back to its exact-sequence failure CAS.

    Returns ``True`` only when this worker owns the terminal write and must emit the
    terminal event.  A terminal written elsewhere owns its own event publication.
    """
    if substrate.cancellations.active(run.run_id):
        await substrate.cancellations.wait(run.run_id)
    current = await substrate.ledger.get(run.run_id)
    if current is None:
        return False
    if current.status in TERMINAL_STATUSES:
        if current.status is RunStatus.CANCELLED and current.enqueue_seq == enqueue_seq:
            await _cleanup_cancelled_claim(substrate, run, persistence=persistence)
        return False
    return await _fail_claimed_run(
        substrate,
        run,
        enqueue_seq=enqueue_seq,
        error=error,
        persistence=persistence,
    )


async def _cleanup_cancelled_claim(
    substrate: RunSubstrate,
    run: RunRecord,
    *,
    persistence: PhylacteryProtocol | None,
) -> None:
    """Release resources created after the API took its pre-abort run snapshot."""
    await _cleanup_claim_resources(
        substrate,
        run,
        persistence=persistence,
    )


async def _fail_claimed_run(
    substrate: RunSubstrate,
    run: RunRecord,
    *,
    enqueue_seq: int,
    error: str,
    persistence: PhylacteryProtocol | None,
) -> bool:
    """Settle and clean only the active hop this delivery actually claimed."""
    settled = await complete_under_cancellation(
        substrate.ledger.try_fail_claimed(
            run.run_id,
            enqueue_seq=enqueue_seq,
            error=error,
        )
    )
    if not settled:
        return False
    await _cleanup_claim_resources(
        substrate,
        run,
        persistence=persistence,
    )
    return True


async def _cleanup_claim_resources(
    substrate: RunSubstrate,
    run: RunRecord,
    *,
    persistence: PhylacteryProtocol | None,
) -> None:
    """Best-effort terminal cleanup that can never hide committed run truth."""
    substrate.context.release(run.run_id)
    try:
        if persistence is None:
            await substrate.stasis_store.delete(run.run_id)
        else:
            await _cleanup_stasis(substrate, run.run_id, persistence)
    except Exception as exc:  # noqa: BLE001 - terminal truth already committed
        # Terminal publication must not depend on deleting a checkpoint pointer.
        # Reconciliation can retry cleanup from the retained durable path.
        logger.warning(
            "terminal_resource_cleanup_failed",
            run_id=run.run_id,
            error=str(exc),
        )


async def _commit_consent_park(
    substrate: RunSubstrate,
    ledger: RunLedger,
    emitter: RunEmitter,
    run_id: str,
    parked: RunParked,
) -> dict[str, Any]:
    """Commit the consent park, then close the pre-flip verdict race (F1).

    S4 order: persist consent + durable path + status, THEN emit CONSENT last, so a
    verdict arriving on the SSE-event path can never beat the `engine.approve` guard.
    But the Bridge PAGE-RENDER path exposes the (already-committed) consent row before
    no-op (row still RUNNING) and stranded the run AWAITING_CONSENT forever. Guard it:
    once we are AWAITING_CONSENT, re-read the verdict and, if already decided, win the
    SAME atomic admission CAS and enqueue the resume ourselves. Exactly one of {this,
    `engine.approve`} wins the CAS — no double-enqueue (F4).
    """
    await ledger.set_consent(run_id, parked.consent_id)
    await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)
    emitter.consent(parked.consent_id, tool_name=parked.tool_name)

    verdict = await substrate.consents.verdict(parked.consent_id) if substrate.consents is not None else None
    if verdict is not None:
        run = await ledger.get(run_id)
        if run is not None and await admit_consent_resume(substrate.queues, ledger, run):
            return {"status": "queued", "run_id": run_id}
    return {"status": "awaiting_consent", "run_id": run_id}


async def _cleanup_stasis(substrate: RunSubstrate, run_id: str, _persistence: PhylacteryProtocol) -> None:
    """Delete a terminal durable checkpoint after the terminal run commit."""
    if isinstance(_persistence, DurableStasisPhylactery):
        await substrate.stasis_store.delete(run_id)


async def _settle_terminal(
    ledger: RunLedger,
    run_id: str,
    status: RunStatus,
    *,
    error: str | None = None,
) -> bool:
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
            return False
        raise
    else:
        return True


async def reconcile_runs(ctx: dict[str, Any], *, boot_cutoff: datetime | None = None) -> dict[str, Any]:
    """Fail runs stranded non-terminal by a dead process (F3/F9/H2).

    Two orphan classes are swept to FAILED (each emitting its terminal `DONE`):

    - RUNNING / AWAITING_HARDWARE: a crash mid-run leaves the row non-terminal with
      no live task. A run is an orphan of a PREVIOUS process only — never a run THIS
      process just claimed. Under Topology A a worker cannot claim until the
      composition root publishes the substrate, which happens AFTER `boot_cutoff` is
      stamped, so any run started this boot has ``started_at >= boot_cutoff`` and is
      left alone (F3). When no cutoff is supplied every non-terminal row is swept
      (the pre-boot-gate behavior). Revisit heartbeats only if a multi-process
      Topology B ever lands.
    - QUEUED older than `RECONCILE_QUEUED_AFTER_S`: `engine.submit` compensates a
      failed `_enqueue`, but a crash between `create` and `_enqueue` (or a lost
      broker job) can strand a QUEUED row with no job. The durable queue is probed
      by the exact ``(run_id, enqueue_seq)`` key before an aged row is failed. A
      present job protects the run; an unavailable/misconfigured broker leaves the
      row untouched and makes this reconcile result explicitly degraded.
    """
    substrate = _substrate(ctx)
    ledger = substrate.ledger
    reconciled: list[str] = []
    for status in (RunStatus.RUNNING, RunStatus.AWAITING_HARDWARE):
        for run in await ledger.list_by_status(status):
            if not _predates_boot(run, boot_cutoff):
                continue  # claimed by THIS process after boot — not an orphan (F3)
            await ledger.set_status(run.run_id, RunStatus.FAILED, error="ghoul lost")
            await substrate.stasis_store.delete(run.run_id)
            await _emit_terminal(substrate, run.run_id)
            reconciled.append(run.run_id)

    # This rite currently runs once at web startup (lifespan), though it is also a
    # registered SAQ task for an operator/cron caller.  A durable SAQ row can outlive
    # the process that published it, so age alone never proves an enqueue was lost.
    # Probe the exact monotonic hop key before settling the Run row terminally.
    now = datetime.now(UTC)
    probe_errors: list[str] = []
    for run in await ledger.list_by_status(RunStatus.QUEUED):
        if (now - run.created_at).total_seconds() < RECONCILE_QUEUED_AFTER_S:
            continue
        queue = substrate.queues.get(run.queue_name)
        if queue is None:
            logger.error(
                "reconcile_queue_missing",
                run_id=run.run_id,
                queue_name=run.queue_name,
            )
            probe_errors.append(run.run_id)
            continue
        job_key = run_job_key(run.run_id, run.enqueue_seq)
        try:
            job = await queue.job(job_key)
        except Exception as exc:
            # A broker outage is not evidence that the job is absent.  Preserve the
            # non-terminal row for a later retry and surface the degraded sweep.
            logger.exception(
                "reconcile_queue_probe_failed",
                run_id=run.run_id,
                queue_name=run.queue_name,
                job_key=job_key,
                error=str(exc),
            )
            probe_errors.append(run.run_id)
            continue
        if job is not None:
            continue
        await ledger.set_status(run.run_id, RunStatus.FAILED, error="enqueue lost")
        await substrate.stasis_store.delete(run.run_id)
        await _emit_terminal(substrate, run.run_id)
        reconciled.append(run.run_id)

    if reconciled:
        logger.warning("reconcile_runs", count=len(reconciled), run_ids=reconciled)
    return {
        "status": "degraded" if probe_errors else "reconciled",
        "count": len(reconciled),
        "probe_errors": len(probe_errors),
    }


class ConsentApprover(Protocol):
    """The narrow slice of `RunEngine` `reconcile_consents` needs."""

    async def approve(self, consent_id: str, *, approved: bool) -> None: ...


async def reconcile_consents(ctx: dict[str, Any], *, engine: ConsentApprover) -> dict[str, Any]:
    """Re-fire verdicts recorded while the process was down (B10, design §1.4).

    A crash between `ConsentService.grant/deny` and `engine.approve` leaves a decided
    consent row with no enqueue. This sweep re-fires those verdicts; still-pending
    parks (and orphans with no consent row) are LEFT ALONE. Idempotent via `approve`'s
    AWAITING_CONSENT status guard. `"expired"` counts as decided-denied (refusal-resumes).
    Lifespan-only this wave (not a SAQ cron).
    """
    substrate = _substrate(ctx)
    refired: list[str] = []
    for run in await substrate.ledger.list_by_status(RunStatus.AWAITING_CONSENT):
        view = await substrate.consents.latest_for_run(run.run_id)
        if view is None or view.status == "pending":
            continue  # still parked (or an orphan) — leave it alone
        await engine.approve(view.id, approved=(view.status == "granted"))
        refired.append(run.run_id)
    if refired:
        logger.warning("reconcile_consents", count=len(refired), run_ids=refired)
    return {"status": "reconciled", "count": len(refired)}


def _predates_boot(run: RunRecord, boot_cutoff: datetime | None) -> bool:
    """Whether a non-terminal run is a PRE-boot orphan (safe for reconcile to sweep).

    F3: a run this process started has ``started_at >= boot_cutoff`` (the worker cannot
    claim before the substrate is published, which is after the cutoff is stamped), so
    it is NOT an orphan. A run with no ``started_at`` — or no cutoff supplied — cannot
    belong to this boot and is swept.
    """
    if boot_cutoff is None or run.started_at is None:
        return True
    return run.started_at < boot_cutoff


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
    settled = await substrate.ledger.get(run_id)
    status = settled.status if settled is not None and settled.status in TERMINAL_STATUSES else RunStatus.FAILED
    substrate.bus.open(run_id, from_seq=next_seq)
    substrate.bus.emitter(run_id).done(status.value)
    substrate.bus.close(run_id)


async def _write_failed_turn(substrate: RunSubstrate, *, run_id: str, session_id: str) -> None:
    """Write a friendly failed agent turn so the settled slot renders the fault."""
    from lychd.domain.web.schemas import BridgeTurn

    try:
        await substrate.turns.add_turn(
            session_id,
            BridgeTurn(role="agent", content=_FAILURE_MESSAGE, run_id=run_id, state="failed"),
        )
    except Exception:  # noqa: BLE001 - turn bookkeeping must never mask the real failure
        logger.debug("failed_turn_write_skipped", run_id=run_id)
