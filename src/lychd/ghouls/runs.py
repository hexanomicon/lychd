"""Run execution, durable delivery repair, and restart reconciliation.

`perform_run` is the SAQ task and the ONLY place a workflow graph executes: claim →
RUNNING → build `WorkflowServices` + `GraphRunner` → iterate → events on the shared
`RunEventBus` → single terminal `DONE` (or FAILED as a DONE carrying the terminal
status). Topology A: it runs in-process on the web loop (`separate_process=False`),
so the SSE handler and this task share one `RunEventBus`.

`reconcile_runs` settles pre-boot active work and repairs exact durable deliveries.
The lifespan runs it before admission and owns a bounded publication relay afterward.
Consent and delegated waits exit without terminal `DONE`; a decided exact owner
re-enters through a newly committed delivery hop and durable checkpoint.
"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

import structlog

from lychd.domain.cortex.engine import (
    RUN_JOB_HEARTBEAT_S,
    admit_consent_resume,
    admit_delegate_resume,
    contain_run_effects,
    enqueue_run,
    run_job_key,
)
from lychd.domain.cortex.graph_runner import GraphRunner, NodeOccurrenceEvent, TransitionTraceEvent
from lychd.domain.cortex.runs import (
    TERMINAL_STATUSES,
    IllegalRunTransitionError,
    RunDeliveryState,
    RunParked,
    RunStatus,
)
from lychd.domain.cortex.stasis import DurableStasisPhylactery, LiveStasisPhylactery
from lychd.domain.cortex.substrate import get_run_substrate
from lychd.domain.delegation.signals import DelegatedAgentParked
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.events import RunEmitter
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunDeliveryRecord, RunRecord
    from lychd.domain.cortex.substrate import RunSubstrate
    from lychd.extensions.protocols import PhylacteryProtocol

logger = structlog.get_logger()

DELIVERY_RELAY_INTERVAL_S = 1.0
DELIVERY_RELAY_BATCH_SIZE = 32
DELIVERY_BROKER_PROBE_TIMEOUT_S = 5.0
DELEGATE_RELAY_INTERVAL_S = 2.0
DELEGATE_RELAY_BATCH_SIZE = 32
DELEGATE_PROBE_TIMEOUT_S = 10.0
CONSENT_RELAY_INTERVAL_S = 2.0
FAILURE_CONTAINMENT_ATTEMPTS = 3
FAILURE_CONTAINMENT_RETRY_S = 0.05
STARTUP_RECONCILIATION_BATCH_SIZE = 128
RECONCILIATION_LOG_ID_LIMIT = 32
RUN_JOB_HEARTBEAT_INTERVAL_S = RUN_JOB_HEARTBEAT_S / 4

_FAILURE_MESSAGE = (
    "The summoning faltered — no capability answered. Ensure a chat Soulstone is bound and warm, then speak again."
)


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


def _require_claimed_delivery(
    delivery: RunDeliveryRecord | None,
    *,
    run_id: str,
    enqueue_seq: int,
) -> RunDeliveryRecord:
    """Return exact claimed delivery authority or raise an invariant failure."""
    if delivery is None or delivery.state is not RunDeliveryState.CLAIMED:
        msg = f"claimed Run {run_id!r} has no authoritative delivery {enqueue_seq}"
        raise RuntimeError(msg)
    return delivery


async def _refresh_run_job_heartbeat(job: Any, *, run_id: str) -> None:
    """Keep SAQ's ACTIVE generation fresh while its graph hop is genuinely live."""
    while True:
        await asyncio.sleep(RUN_JOB_HEARTBEAT_INTERVAL_S)
        try:
            await job.update()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - broker uncertainty must expire fail-closed
            logger.warning(
                "run_job_heartbeat_failed",
                run_id=run_id,
                error=str(exc),
            )


async def perform_run(
    ctx: dict[str, Any],
    *,
    run_id: str,
    resume: bool | None = None,
    enqueue_seq: int | None = None,
) -> dict[str, Any]:
    """Execute one run's workflow graph. The ONLY graph-execution site.

    A fresh hop iterates from the start node; a durable delivery marked ``resume``
    resumes the checkpoint. The broker's legacy ``resume`` argument is accepted but
    never trusted: mode authority lives in ``RunDelivery``. The consent verdict is
    read from the ConsentLedger inside `AwaitConsent` — never carried in a payload.

    Production SAQ contexts carry the active Job. Its heartbeat updater is owned by
    this invocation and stops before the worker writes terminal broker truth. Test
    contexts without a Job retain the same execution contract without broker effects.
    """
    heartbeat_task: asyncio.Task[None] | None = None
    job = ctx.get("job")
    if callable(getattr(job, "update", None)):
        heartbeat_task = asyncio.create_task(
            _refresh_run_job_heartbeat(job, run_id=run_id),
            name=f"run-heartbeat:{run_id}",
        )
    try:
        return await _perform_run(
            ctx,
            run_id=run_id,
            resume=resume,
            enqueue_seq=enqueue_seq,
        )
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task


async def _perform_run(  # noqa: C901, PLR0911, PLR0912, PLR0915 - honest fresh/resume/park/fail path
    ctx: dict[str, Any],
    *,
    run_id: str,
    resume: bool | None = None,
    enqueue_seq: int | None = None,
) -> dict[str, Any]:
    """Execute one ledger hop after heartbeat ownership has been established."""
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
        settle_task = asyncio.ensure_future(
            _settle_terminal(
                ledger,
                run_id,
                claim_enqueue_seq,
                status,
                error=error,
            )
        )
        try:
            terminal_owned = await asyncio.shield(settle_task)
        except asyncio.CancelledError:
            # The commit may have won. Learn its ownership before propagating so
            # finally cannot mistake our terminal row for somebody else's event.
            terminal_owned = await complete_under_cancellation(settle_task)
            raise

    try:
        claimed_delivery = _require_claimed_delivery(
            await ledger.get_delivery(run_id, enqueue_seq=claim_enqueue_seq),
            run_id=run_id,
            enqueue_seq=claim_enqueue_seq,
        )
        # Compatibility payloads may lie or be stale; durable delivery truth wins.
        resume = claimed_delivery.resume
        if resume:
            # R1-safe channel seeding: a durable resume after restart mints a fresh channel
            # that MUST continue the persisted seq, never restart at 0 (else re-collided,
            # silently-shed Step rows). Seed BEFORE any emitter opens the channel.
            substrate.bus.open(run_id, from_seq=await ledger.next_seq(run_id))
        emitter = substrate.bus.emitter(run_id)
        from lychd.agents.workflows.base import pattern_snapshot_is_valid

        pinned_key = str(run.pattern_manifest.get("key", ""))
        pinned_revision = str(run.pattern_manifest.get("revision", ""))
        workflow = substrate.workflows.get_revision(pinned_key, pinned_revision)
        if (
            not pattern_snapshot_is_valid(run.pattern_manifest)
            or pinned_key != run.workflow_name
            or workflow is None
            or run.pattern_manifest != workflow.manifest.snapshot()
        ):
            await settle_terminal(
                RunStatus.FAILED,
                error=(f"pinned Pattern unavailable: {pinned_key or run.workflow_name}@{pinned_revision or 'unknown'}"),
            )
            await _cleanup_claim_resources(substrate, run, persistence=None)
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
            emitter.status(RunStatus.AWAITING_HARDWARE.value)

        async def _on_stasis_exit() -> None:
            await ledger.set_status(run_id, RunStatus.RUNNING)
            emitter.status(RunStatus.RUNNING.value)

        def _on_node_event(event: NodeOccurrenceEvent) -> None:
            emitter.node(
                workflow.manifest.node_key(event.node_type),
                phase=event.phase,
                occurrence_id=event.occurrence_id,
                pattern_id=workflow.manifest.key,
                pattern_revision=workflow.manifest.revision,
                wait_kind=event.wait_kind or "",
                transition_request_id=event.transition_request_id or "",
                delegated_job_id=event.delegated_job_id or "",
                delegated_runtime=event.delegated_runtime or "",
            )

        def _on_transition_event(event: TransitionTraceEvent) -> None:
            emitter.transition(
                event.request_id,
                phase=event.phase,
                capability_key=event.target_capability_key,
                occurrence_id=event.occurrence_id or "",
                physical_transition_id=event.physical_transition_id or "",
                compensation_transition_id=event.compensation_transition_id or "",
                action_type=event.action_type or "",
            )

        runner: GraphRunner[Any] = GraphRunner(
            orchestrator=substrate.orchestrator,
            persistence=persistence,
            signal_priority=run.priority,
            on_stasis_enter=_on_stasis_enter,
            on_stasis_exit=_on_stasis_exit,
            on_node_event=_on_node_event,
            on_transition_event=_on_transition_event,
            run_id=run_id,
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
        if isinstance(result, DelegatedAgentParked):
            return await _commit_delegate_park(substrate, ledger, emitter, run_id, result)
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
        # channel. A nonterminal park/resume leaves the channel open on purpose.
        terminal = await complete_under_cancellation(ledger.get(run_id))
        if terminal_owned and terminal is not None and terminal.status in TERMINAL_STATUSES:
            await complete_under_cancellation(_emit_terminal(substrate, run_id, emitter=emitter))


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
    Once the Run is ``CANCELLING``, the worker releases its resources immediately so
    SAQ can acknowledge containment; the API commits ``CANCELLED`` only after that
    acknowledgement. Outside that elected state, the worker waits for an in-process
    cancellation leader before falling back to its exact-sequence failure CAS.

    Returns ``True`` only when this worker owns the terminal write and must emit the
    terminal event.  A terminal written elsewhere owns its own event publication.
    """
    current = await substrate.ledger.get(run.run_id)
    if current is None:
        return False
    if current.status is RunStatus.CANCELLING and current.enqueue_seq == enqueue_seq:
        # The API is waiting for SAQ to observe this task's cancellation. Release
        # graph resources now; waiting on the API coordinator here would deadlock
        # the containment acknowledgement.
        await _cleanup_cancelled_claim(substrate, run, persistence=persistence)
        return False
    if substrate.cancellations.active(run.run_id):
        await substrate.cancellations.wait(run.run_id)
        current = await substrate.ledger.get(run.run_id)
        if current is None:
            return False
        if current.status is RunStatus.CANCELLING and current.enqueue_seq == enqueue_seq:
            await _cleanup_cancelled_claim(substrate, run, persistence=persistence)
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
    containment_errors = await _contain_failed_run_effects(substrate, run.run_id)
    if containment_errors:
        for exc in containment_errors:
            logger.error(
                "failed_run_containment_failed",
                run_id=run.run_id,
                enqueue_seq=enqueue_seq,
                error=str(exc),
            )
        msg = f"Failure containment failed for Run {run.run_id!r}."
        raise RuntimeError(msg) from containment_errors[0]
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


async def _contain_failed_run_effects(substrate: RunSubstrate, run_id: str) -> list[BaseException]:
    """Retry transient child-authority failures before leaving nonterminal truth."""
    errors: list[BaseException] = []
    for attempt in range(FAILURE_CONTAINMENT_ATTEMPTS):
        errors = await contain_run_effects(
            run_id,
            delegates=substrate.delegates,
            consents=substrate.consents,
            decided_by="cortex:worker-failure-containment",
        )
        if not errors:
            return []
        if attempt + 1 < FAILURE_CONTAINMENT_ATTEMPTS:
            logger.warning(
                "failed_run_containment_retry",
                run_id=run_id,
                attempt=attempt + 1,
                errors=len(errors),
            )
            await asyncio.sleep(FAILURE_CONTAINMENT_RETRY_S * (attempt + 1))
    return errors


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
    await ledger.park_consent(run_id, parked.consent_id)
    emitter.consent(parked.consent_id, tool_name=parked.tool_name)

    try:
        verdict = await substrate.consents.verdict(parked.consent_id) if substrate.consents is not None else None
    except asyncio.CancelledError:
        logger.warning(
            "consent_post_park_probe_cancelled",
            run_id=run_id,
            consent_id=parked.consent_id,
        )
        return {"status": "awaiting_consent", "run_id": run_id}
    except Exception as exc:  # noqa: BLE001 - parked truth is durable; relay retries
        logger.warning(
            "consent_post_park_probe_failed",
            run_id=run_id,
            consent_id=parked.consent_id,
            error=str(exc),
        )
        verdict = None
    if verdict is not None:
        run = await ledger.get(run_id)
        if run is not None and await admit_consent_resume(
            substrate.queues,
            ledger,
            substrate.consents,
            run,
            consent_id=parked.consent_id,
        ):
            return {"status": "queued", "run_id": run_id}
    return {"status": "awaiting_consent", "run_id": run_id}


async def _commit_delegate_park(
    substrate: RunSubstrate,
    ledger: RunLedger,
    emitter: RunEmitter,
    run_id: str,
    parked: DelegatedAgentParked,
) -> dict[str, Any]:
    """Commit a delegated wait, then close the pre-status terminal-result race."""
    from lychd.domain.delegation.models import TERMINAL_DELEGATED_AGENT_STATUSES

    if parked.job.run_id != run_id:
        msg = f"Delegated job {parked.job.job_id!r} belongs to Run {parked.job.run_id!r}, not {run_id!r}."
        raise ValueError(msg)
    await ledger.park_delegate(run_id, parked.job.job_id)
    emitter.status(RunStatus.AWAITING_DELEGATE.value)
    if substrate.delegates is not None:
        try:
            job = await substrate.delegates.refresh(parked.job.job_id)
        except asyncio.CancelledError:
            logger.warning(
                "delegate_post_park_probe_cancelled",
                run_id=run_id,
                delegated_job_id=parked.job.job_id,
            )
            return {
                "status": RunStatus.AWAITING_DELEGATE.value,
                "run_id": run_id,
                "job_id": parked.job.job_id,
            }
        except Exception as exc:  # noqa: BLE001 - parked truth is durable; relay retries
            logger.warning(
                "delegate_post_park_probe_failed",
                run_id=run_id,
                delegated_job_id=parked.job.job_id,
                error=str(exc),
            )
            job = None
        if job is not None and job.status in TERMINAL_DELEGATED_AGENT_STATUSES:
            run = await ledger.get(run_id)
            if run is not None and await admit_delegate_resume(
                substrate.queues,
                ledger,
                run,
                job_id=parked.job.job_id,
            ):
                return {
                    "status": RunStatus.QUEUED.value,
                    "run_id": run_id,
                    "job_id": parked.job.job_id,
                }
    return {
        "status": RunStatus.AWAITING_DELEGATE.value,
        "run_id": run_id,
        "job_id": parked.job.job_id,
    }


async def _cleanup_stasis(substrate: RunSubstrate, run_id: str, _persistence: PhylacteryProtocol) -> None:
    """Delete a terminal durable checkpoint after the terminal run commit."""
    if isinstance(_persistence, DurableStasisPhylactery):
        await substrate.stasis_store.delete(run_id)


async def _settle_terminal(
    ledger: RunLedger,
    run_id: str,
    enqueue_seq: int,
    status: RunStatus,
    *,
    error: str | None = None,
) -> bool:
    """Write terminal status under the exact claimed generation.

    A failed conditional settlement triggers one re-read. Existing terminal truth is
    benign; any nonterminal generation or status mismatch is an illegal transition.
    """
    if await ledger.try_settle_claim(
        run_id,
        enqueue_seq=enqueue_seq,
        status=status,
        error=error,
    ):
        return True
    fresh = await ledger.get(run_id)
    if fresh is not None and fresh.status in TERMINAL_STATUSES:
        logger.info(
            "terminal_write_lost_race",
            run_id=run_id,
            attempted=status.value,
            settled=fresh.status.value,
        )
        return False
    current = fresh.status if fresh is not None else RunStatus.CANCELLED
    raise IllegalRunTransitionError(run_id, current, status)


def _job_is_terminal(job: object) -> bool:
    """Return whether a probed SAQ job can no longer execute this delivery."""
    status = getattr(job, "status", None)
    value = getattr(status, "value", status)
    return value in {"aborted", "complete", "failed"}


def _active_job_predates_boot(job: object, boot_cutoff: datetime) -> bool | None:
    """Classify SAQ ACTIVE ownership by its millisecond start timestamp.

    ``None`` means the broker row claims to be active but lacks the timestamp needed
    to prove which process owns it; startup must degrade instead of aborting blindly.
    """
    status = getattr(job, "status", None)
    value = getattr(status, "value", status)
    if value not in {"active", "aborting"}:
        return False
    started = getattr(job, "started", None)
    if isinstance(started, bool) or not isinstance(started, (int, float)) or started <= 0:
        return None
    return started < int(boot_cutoff.timestamp() * 1000)


async def _abort_orphaned_job(queue: RunQueue, job: object, *, error: str) -> None:
    """Terminally fence a broker generation known to belong to a dead process."""
    abort_orphan = getattr(queue, "abort_orphan", None)
    if abort_orphan is not None:
        await abort_orphan(job, error)
        return
    await queue.abort(job, error)


async def _fence_preboot_active_delivery(
    queue: RunQueue,
    job: object,
    *,
    run: RunRecord,
    delivery: RunDeliveryRecord,
    job_key: str,
    boot_cutoff: datetime,
) -> bool | None:
    """Fence a proven pre-boot ACTIVE job.

    ``False`` retains a current/non-active generation. ``None`` represents broker
    uncertainty and requires degraded startup; ``True`` permits delivery rotation.
    """
    predates_boot = _active_job_predates_boot(job, boot_cutoff)
    if predates_boot is None:
        logger.error(
            "reconcile_active_job_timestamp_missing",
            run_id=run.run_id,
            queue_name=delivery.queue_name,
            job_key=job_key,
        )
        return None
    if not predates_boot:
        return False
    try:
        await _abort_orphaned_job(
            queue,
            job,
            error="pre-claim delivery orphaned by a prior LychD process",
        )
        async with asyncio.timeout(DELIVERY_BROKER_PROBE_TIMEOUT_S):
            fenced = await queue.job(job_key)
    except Exception as exc:
        logger.exception(
            "reconcile_preclaim_fence_failed",
            run_id=run.run_id,
            queue_name=delivery.queue_name,
            job_key=job_key,
            error=str(exc),
        )
        return None
    if fenced is not None and not _job_is_terminal(fenced):
        logger.error(
            "reconcile_preclaim_fence_unacknowledged",
            run_id=run.run_id,
            queue_name=delivery.queue_name,
            job_key=job_key,
        )
        return None
    return True


@dataclass(frozen=True)
class _DeliveryFlushOutcome:
    repaired: int = 0
    errors: int = 0
    revisit: bool = False


async def _delivery_target(  # noqa: PLR0911 - each rejected invariant has distinct recovery truth
    substrate: RunSubstrate,
    run: RunRecord,
    *,
    refuse_held: bool,
) -> tuple[RunDeliveryRecord, RunQueue] | _DeliveryFlushOutcome:
    """Validate one Run/delivery projection and resolve its physical queue."""
    ledger = substrate.ledger
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=run.enqueue_seq)
    if delivery is None:
        logger.error("reconcile_delivery_missing", run_id=run.run_id, enqueue_seq=run.enqueue_seq)
        return _DeliveryFlushOutcome(errors=1)
    if delivery.state is RunDeliveryState.HELD:
        if not refuse_held:
            return _DeliveryFlushOutcome(revisit=True)
        refused = await ledger.try_fail_held(
            run.run_id,
            enqueue_seq=run.enqueue_seq,
            error="admission context unresolved",
        )
        if not refused:
            return _DeliveryFlushOutcome()
        await substrate.stasis_store.delete(run.run_id)
        await _emit_terminal(substrate, run.run_id)
        return _DeliveryFlushOutcome(repaired=1)
    if delivery.state not in {RunDeliveryState.PENDING, RunDeliveryState.PUBLISHED}:
        logger.error(
            "reconcile_delivery_state_invalid",
            run_id=run.run_id,
            enqueue_seq=run.enqueue_seq,
            delivery_state=delivery.state.value,
        )
        return _DeliveryFlushOutcome(errors=1)
    if delivery.queue_name != run.queue_name or delivery.priority != run.priority:
        logger.error(
            "reconcile_delivery_projection_mismatch",
            run_id=run.run_id,
            enqueue_seq=run.enqueue_seq,
        )
        return _DeliveryFlushOutcome(errors=1)
    queue = substrate.queues.get(delivery.queue_name)
    if queue is None:
        logger.error("reconcile_queue_missing", run_id=run.run_id, queue_name=delivery.queue_name)
        return _DeliveryFlushOutcome(errors=1)
    return delivery, queue


async def _publish_delivery(  # noqa: PLR0911 - every broker truth has a distinct recovery result
    substrate: RunSubstrate,
    run: RunRecord,
    delivery: RunDeliveryRecord,
    queue: RunQueue,
    *,
    boot_cutoff: datetime | None = None,
) -> _DeliveryFlushOutcome:
    """Probe, rotate when necessary, and publish one validated delivery."""
    ledger = substrate.ledger
    job_key = run_job_key(run.run_id, delivery.enqueue_seq)
    try:
        async with asyncio.timeout(DELIVERY_BROKER_PROBE_TIMEOUT_S):
            job = await queue.job(job_key)
    except Exception as exc:
        logger.exception(
            "reconcile_queue_probe_failed",
            run_id=run.run_id,
            queue_name=delivery.queue_name,
            job_key=job_key,
            error=str(exc),
        )
        return _DeliveryFlushOutcome(errors=1)
    rotate_delivery = job is not None and _job_is_terminal(job)
    if job is not None and not rotate_delivery:
        fenced = (
            await _fence_preboot_active_delivery(
                queue,
                job,
                run=run,
                delivery=delivery,
                job_key=job_key,
                boot_cutoff=boot_cutoff,
            )
            if boot_cutoff is not None
            else False
        )
        if fenced is None:
            return _DeliveryFlushOutcome(errors=1)
        if not fenced:
            if delivery.state is RunDeliveryState.PENDING:
                await ledger.mark_delivery_published(run.run_id, enqueue_seq=delivery.enqueue_seq)
            return _DeliveryFlushOutcome(revisit=True)
        rotate_delivery = True

    repaired = 0
    if rotate_delivery:
        next_seq = await ledger.rotate_delivery(run.run_id, enqueue_seq=delivery.enqueue_seq)
        if next_seq is None:
            return _DeliveryFlushOutcome()
        refreshed_run = await ledger.get(run.run_id)
        refreshed_delivery = await ledger.get_delivery(run.run_id, enqueue_seq=next_seq)
        if refreshed_run is None or refreshed_delivery is None:
            logger.error("reconcile_delivery_rotation_incomplete", run_id=run.run_id, enqueue_seq=next_seq)
            return _DeliveryFlushOutcome(errors=1)
        run = refreshed_run
        delivery = refreshed_delivery
        repaired = 1
    try:
        await enqueue_run(
            substrate.queues,
            ledger,
            run,
            enqueue_seq=delivery.enqueue_seq,
        )
    except Exception as exc:
        logger.exception(
            "reconcile_delivery_publish_failed",
            run_id=run.run_id,
            queue_name=delivery.queue_name,
            job_key=run_job_key(run.run_id, delivery.enqueue_seq),
            error=str(exc),
        )
        return _DeliveryFlushOutcome(repaired=repaired, errors=1)
    return _DeliveryFlushOutcome(repaired=repaired)


async def flush_run_deliveries(
    ctx: dict[str, Any],
    *,
    refuse_held: bool = False,
    boot_cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Complete a keyset-paged recovery sweep of every relayable delivery."""
    substrate = _substrate(ctx)
    cursor: tuple[datetime, str] | None = None
    repaired_total = 0
    error_total = 0
    while True:
        result, next_cursor = await _flush_run_delivery_page(
            substrate,
            after=cursor,
            refuse_held=refuse_held,
            boot_cutoff=boot_cutoff,
        )
        repaired_total += int(result["count"])
        error_total += int(result["probe_errors"])
        if next_cursor is None:
            break
        cursor = next_cursor

    return {
        "status": "degraded" if error_total else "reconciled",
        "count": repaired_total,
        "probe_errors": error_total,
    }


async def _flush_run_delivery_page(
    substrate: RunSubstrate,
    *,
    after: tuple[datetime, str] | None,
    refuse_held: bool,
    boot_cutoff: datetime | None = None,
    limit: int = DELIVERY_RELAY_BATCH_SIZE,
) -> tuple[dict[str, Any], tuple[datetime, str] | None]:
    """Process one bounded keyset page and return the next-page cursor."""
    repaired = 0
    errors = 0
    revisit = False
    runs = await substrate.ledger.list_delivery_candidates(after=after, limit=limit)
    for run in runs:
        try:
            target = await _delivery_target(substrate, run, refuse_held=refuse_held)
            if isinstance(target, _DeliveryFlushOutcome):
                outcome = target
            else:
                outcome = await _publish_delivery(
                    substrate,
                    run,
                    *target,
                    boot_cutoff=boot_cutoff,
                )
        except Exception as exc:
            logger.exception(
                "run_delivery_row_failed",
                run_id=run.run_id,
                enqueue_seq=run.enqueue_seq,
                error=str(exc),
            )
            outcome = _DeliveryFlushOutcome(errors=1)
        repaired += outcome.repaired
        errors += outcome.errors
        revisit = revisit or outcome.revisit
    next_cursor = (runs[-1].updated_at, runs[-1].run_id) if len(runs) == limit else None
    return (
        {
            "status": "degraded" if errors else "reconciled",
            "count": repaired,
            "probe_errors": errors,
            "_revisit": revisit,
        },
        next_cursor,
    )


@dataclass
class _RelayPageScheduler:
    """Alternate forward keyset progress with exact pages that still need custody."""

    cursor: tuple[datetime, str] | None = None
    retry_pages: deque[tuple[datetime, str] | None] = field(default_factory=deque)
    retry_set: set[tuple[datetime, str] | None] = field(default_factory=set)
    retry_turn: bool = False

    def take(self) -> tuple[tuple[datetime, str] | None, bool]:
        """Return the next page cursor and whether it came from the revisit queue."""
        retrying = bool(self.retry_pages) and self.retry_turn
        if not retrying:
            return self.cursor, False
        page_after = self.retry_pages.popleft()
        self.retry_set.discard(page_after)
        return page_after, True

    def failed(self, page_after: tuple[datetime, str] | None, *, retrying: bool) -> None:
        """Retain a failed page and preserve forward/retry alternation."""
        self._remember(page_after)
        self.retry_turn = not retrying and bool(self.retry_pages)

    def completed(
        self,
        page_after: tuple[datetime, str] | None,
        *,
        retrying: bool,
        next_cursor: tuple[datetime, str] | None,
        revisit: bool,
    ) -> None:
        """Advance forward truth and retain a clean page whose external wait remains live."""
        if not retrying:
            self.cursor = next_cursor
        if revisit:
            self._remember(page_after)
        self.retry_turn = not retrying and bool(self.retry_pages)

    def _remember(self, page_after: tuple[datetime, str] | None) -> None:
        if page_after in self.retry_set:
            return
        self.retry_pages.append(page_after)
        self.retry_set.add(page_after)


async def relay_run_deliveries(
    ctx: dict[str, Any],
    *,
    stop: asyncio.Event,
    interval_s: float = DELIVERY_RELAY_INTERVAL_S,
) -> None:
    """Advance the delivery sweep while fairly revisiting every blocked page."""
    pages = _RelayPageScheduler()
    while not stop.is_set():
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        if stop.is_set():
            return
        page_after, retrying = pages.take()
        try:
            result, next_cursor = await _flush_run_delivery_page(
                _substrate(ctx),
                after=page_after,
                refuse_held=False,
            )
        except Exception as exc:
            logger.exception("run_delivery_relay_failed", error=str(exc))
            pages.failed(page_after, retrying=retrying)
            continue
        degraded = result["status"] == "degraded"
        needs_retry = degraded or bool(result.get("_revisit", False))
        pages.completed(
            page_after,
            retrying=retrying,
            next_cursor=next_cursor,
            revisit=needs_retry,
        )
        if degraded:
            logger.warning(
                "run_delivery_relay_degraded",
                probe_errors=result["probe_errors"],
            )


async def relay_delegated_runs(
    *,
    engine: Any,
    stop: asyncio.Event,
    interval_s: float = DELEGATE_RELAY_INTERVAL_S,
) -> None:
    """Refresh delegated waits while fairly retrying every degraded page."""
    pages = _RelayPageScheduler()
    while not stop.is_set():
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        if stop.is_set():
            return
        page_after, retrying = pages.take()
        try:
            result, next_cursor = await _reconcile_delegate_page(engine, after=page_after)
        except Exception as exc:
            logger.exception("delegate_relay_failed", error=str(exc))
            pages.failed(page_after, retrying=retrying)
            continue
        needs_retry = result["status"] == "degraded" or bool(result.get("_revisit", False))
        pages.completed(
            page_after,
            retrying=retrying,
            next_cursor=next_cursor,
            revisit=needs_retry,
        )
        if result["status"] == "degraded":
            logger.warning("delegate_relay_degraded", probe_errors=result["probe_errors"])


async def _reconcile_delegate_page(
    engine: Any,
    *,
    after: tuple[datetime, str] | None,
    limit: int = DELEGATE_RELAY_BATCH_SIZE,
) -> tuple[dict[str, Any], tuple[datetime, str] | None]:
    """Poll and adopt one keyset page of AWAITING_DELEGATE runs."""
    runs = await engine.ledger.list_by_status(
        RunStatus.AWAITING_DELEGATE,
        after=after,
        limit=limit,
    )
    resumed = 0
    errors = 0
    revisit = False
    delegates = engine.delegates
    for run in runs:
        job_id = run.delegated_job_id
        if delegates is None or job_id is None:
            logger.error("delegate_relay_owner_missing", run_id=run.run_id)
            errors += 1
            continue
        try:
            async with asyncio.timeout(DELEGATE_PROBE_TIMEOUT_S):
                await delegates.refresh(job_id)
                did_resume = await engine.resume_delegate(job_id)
                resumed += int(did_resume)
                revisit = revisit or not did_resume
        except Exception as exc:
            logger.exception(
                "delegate_relay_probe_failed",
                run_id=run.run_id,
                delegated_job_id=job_id,
                error=str(exc),
            )
            errors += 1
    next_cursor = (runs[-1].created_at, runs[-1].run_id) if len(runs) == limit else None
    return (
        {
            "status": "degraded" if errors else "reconciled",
            "count": resumed,
            "probe_errors": errors,
            "_revisit": revisit,
        },
        next_cursor,
    )


async def reconcile_delegated_runs(*, engine: Any) -> dict[str, Any]:
    """Sweep every delegated wait through the bounded runtime reconciliation path."""
    cursor: tuple[datetime, str] | None = None
    resumed = 0
    errors = 0
    while True:
        result, cursor = await _reconcile_delegate_page(engine, after=cursor)
        resumed += int(result["count"])
        errors += int(result["probe_errors"])
        if cursor is None:
            return {
                "status": "degraded" if errors else "reconciled",
                "count": resumed,
                "probe_errors": errors,
            }


async def reconcile_runs(ctx: dict[str, Any], *, boot_cutoff: datetime | None = None) -> dict[str, Any]:
    """Reconcile work stranded by a previous process.

    Two orphan classes are inspected:

    - RUNNING / AWAITING_HARDWARE: a crash mid-run leaves the row non-terminal with
      no live task. A run is an orphan of a PREVIOUS process only — never a run THIS
      process just claimed. Under Topology A a worker cannot claim until the
      composition root publishes the substrate, which happens AFTER `boot_cutoff` is
      stamped, so any run started this boot has ``started_at >= boot_cutoff`` and is
      left alone. When no cutoff is supplied every nonterminal row is swept
      (the pre-boot-gate behavior). Revisit heartbeats only if a multi-process
      Topology B ever lands.
    - QUEUED: the exact durable delivery is inspected. A HELD admission is refused
      because caller-owned context never became publishable. PENDING/PUBLISHED work
      is probed and, when absent, republished under the same idempotent key. Missing
      delivery truth or an unavailable queue makes reconciliation degraded.
    """
    substrate = _substrate(ctx)
    ledger = substrate.ledger
    reconciled_count = 0
    reconciled_ids: list[str] = []
    orphan_errors = 0
    for status in (RunStatus.RUNNING, RunStatus.AWAITING_HARDWARE):
        cursor: tuple[datetime, str] | None = None
        while True:
            runs = await ledger.list_by_status(
                status,
                after=cursor,
                limit=STARTUP_RECONCILIATION_BATCH_SIZE,
            )
            for run in runs:
                if not _predates_boot(run, boot_cutoff):
                    continue  # claimed by THIS process after boot — not an orphan (F3)
                if not await _reconcile_orphaned_run(substrate, run):
                    orphan_errors += 1
                    continue
                reconciled_count += 1
                if len(reconciled_ids) < RECONCILIATION_LOG_ID_LIMIT:
                    reconciled_ids.append(run.run_id)
            if len(runs) < STARTUP_RECONCILIATION_BATCH_SIZE:
                break
            cursor = (runs[-1].created_at, runs[-1].run_id)

    delivery_result = await flush_run_deliveries(
        ctx,
        refuse_held=True,
        boot_cutoff=boot_cutoff,
    )
    total_count = reconciled_count + int(delivery_result["count"])

    if total_count:
        logger.warning(
            "reconcile_runs",
            count=total_count,
            run_ids=reconciled_ids,
            run_ids_truncated=reconciled_count > len(reconciled_ids),
        )
    probe_errors = int(delivery_result["probe_errors"]) + orphan_errors
    return {
        "status": "degraded" if probe_errors else "reconciled",
        "count": total_count,
        "probe_errors": probe_errors,
    }


async def _reconcile_orphaned_run(substrate: RunSubstrate, run: RunRecord) -> bool:
    """Fence one pre-boot worker, recover an exact park, or contain before failure."""
    consent_id = await _recoverable_consent_park(substrate, run)
    delegated_job_id = await _recoverable_delegate_park(substrate, run)
    if not await _fence_orphaned_job(substrate, run):
        return False
    if consent_id is not None and delegated_job_id is None:
        await substrate.ledger.park_consent(run.run_id, consent_id)
        return True
    if delegated_job_id is not None and consent_id is None:
        await substrate.ledger.park_delegate(run.run_id, delegated_job_id)
        return True
    containment_errors = await contain_run_effects(
        run.run_id,
        delegates=substrate.delegates,
        consents=substrate.consents,
        decided_by="cortex:orphan-failed",
    )
    if containment_errors:
        for exc in containment_errors:
            logger.error(
                "reconcile_orphan_effect_containment_failed",
                run_id=run.run_id,
                error=str(exc),
            )
        return False
    await substrate.ledger.set_status(run.run_id, RunStatus.FAILED, error="ghoul lost")
    await substrate.stasis_store.delete(run.run_id)
    await _emit_terminal(substrate, run.run_id)
    return True


async def _recoverable_consent_park(substrate: RunSubstrate, run: RunRecord) -> str | None:
    """Recognize the narrow crash window after checkpoint+Consent, before Run park."""
    if substrate.consents is None:
        return None
    view = await substrate.consents.latest_for_run(run.run_id)
    if view is None or view.status == "cancelled":
        return None
    snapshots = await substrate.stasis_store.load(run.run_id)
    if snapshots is None or not _checkpoint_binds_consent(
        snapshots,
        run_id=run.run_id,
        consent_id=view.id,
    ):
        return None
    return view.id


async def _recoverable_delegate_park(substrate: RunSubstrate, run: RunRecord) -> str | None:
    """Recognize the crash window after exact delegate checkpoint, before Run park."""
    if substrate.delegates is None:
        return None
    jobs = await substrate.delegates.jobs_for_run(run.run_id)
    if not jobs:
        return None
    snapshots = await substrate.stasis_store.load(run.run_id)
    if snapshots is None:
        return None
    for job in jobs:
        if _checkpoint_binds_delegate(
            snapshots,
            run_id=run.run_id,
            job_id=job.ref.job_id,
        ):
            return job.ref.job_id
    return None


def _checkpoint_binds_consent(
    snapshots: list[Any],
    *,
    run_id: str,
    consent_id: str,
) -> bool:
    """Bind recovery to the exact node snapshot Pydantic Graph will resume first."""
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            return False
        snapshot_data = cast("dict[str, Any]", snapshot)
        if snapshot_data.get("kind") != "node" or snapshot_data.get("status") != "created":
            continue
        state = snapshot_data.get("state")
        if not isinstance(state, dict):
            return False
        state_data = cast("dict[str, Any]", state)
        return state_data.get("run_id") == run_id and state_data.get("pending_consent_id") == consent_id
    return False


def _checkpoint_binds_delegate(
    snapshots: list[Any],
    *,
    run_id: str,
    job_id: str,
) -> bool:
    """Bind delegate recovery to the exact next resumable node state."""
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            return False
        snapshot_data = cast("dict[str, Any]", snapshot)
        if snapshot_data.get("kind") != "node" or snapshot_data.get("status") != "created":
            continue
        state = snapshot_data.get("state")
        if not isinstance(state, dict):
            return False
        state_data = cast("dict[str, Any]", state)
        return state_data.get("run_id") == run_id and state_data.get("job_id") == job_id
    return False


async def _fence_orphaned_job(substrate: RunSubstrate, run: RunRecord) -> bool:
    """Prevent a pre-boot SAQ generation from surviving its failed Run truth."""
    queue = substrate.queues.get(run.queue_name)
    if queue is None:
        logger.error("reconcile_orphan_queue_missing", run_id=run.run_id, queue_name=run.queue_name)
        return False
    try:
        async with asyncio.timeout(DELIVERY_BROKER_PROBE_TIMEOUT_S):
            job = await queue.job(run_job_key(run.run_id, run.enqueue_seq))
            if job is None:
                return True
            await _abort_orphaned_job(
                queue,
                job,
                error="orphaned by a prior LychD process",
            )
    except Exception as exc:
        logger.exception(
            "reconcile_orphan_fence_failed",
            run_id=run.run_id,
            queue_name=run.queue_name,
            error=str(exc),
        )
        return False
    return True


class ConsentApprover(Protocol):
    """The narrow slice of `RunEngine` `reconcile_consents` needs."""

    async def approve(self, consent_id: str, *, approved: bool) -> None: ...


async def _reconcile_consent_page(
    substrate: RunSubstrate,
    engine: ConsentApprover,
    *,
    after: tuple[datetime, str] | None,
    limit: int | None = None,
) -> tuple[dict[str, Any], tuple[datetime, str] | None]:
    """Probe one bounded keyset page of parked consent owners."""
    page_limit = STARTUP_RECONCILIATION_BATCH_SIZE if limit is None else limit
    runs = await substrate.ledger.list_by_status(
        RunStatus.AWAITING_CONSENT,
        after=after,
        limit=page_limit,
    )
    refired = 0
    errors = 0
    revisit = False
    for run in runs:
        try:
            if run.consent_id is None:
                logger.error("reconcile_consent_owner_missing", run_id=run.run_id)
                errors += 1
                continue
            view = await substrate.consents.get(run.consent_id)
            if view is None or view.run_id != run.run_id:
                logger.error("reconcile_consent_missing", run_id=run.run_id)
                errors += 1
                continue
            if view.status == "pending":
                revisit = True
                continue
            await engine.approve(view.id, approved=(view.status == "granted"))
            refired += 1
        except Exception as exc:
            logger.exception(
                "reconcile_consent_probe_failed",
                run_id=run.run_id,
                error=str(exc),
            )
            errors += 1
    next_cursor = (runs[-1].created_at, runs[-1].run_id) if len(runs) == page_limit else None
    return (
        {
            "status": "degraded" if errors else "reconciled",
            "count": refired,
            "probe_errors": errors,
            "_revisit": revisit,
        },
        next_cursor,
    )


async def reconcile_consents(ctx: dict[str, Any], *, engine: ConsentApprover) -> dict[str, Any]:
    """Re-fire verdicts recorded while the process was down (B10, design §1.4).

    A crash between `ConsentService.grant/deny` and `engine.approve` leaves a decided
    consent row with no enqueue. This sweep re-fires the verdict of each Run's exact
    persisted Consent owner; still-pending owners are left alone. An AWAITING_CONSENT
    Run without that exact Consent row is corrupt durable state and degrades startup
    rather than being silently accepted. Idempotent via `approve`'s
    AWAITING_CONSENT status guard. `"expired"` counts as
    decided-denied (refusal-resumes). Startup requires one clean full sweep; the
    lifespan-owned runtime relay repeats bounded pages afterward.
    """
    substrate = _substrate(ctx)
    refired_count = 0
    errors = 0
    cursor: tuple[datetime, str] | None = None
    while True:
        result, cursor = await _reconcile_consent_page(
            substrate,
            engine,
            after=cursor,
        )
        refired_count += int(result["count"])
        errors += int(result["probe_errors"])
        if cursor is None:
            break
    if refired_count:
        logger.warning(
            "reconcile_consents",
            count=refired_count,
        )
    return {
        "status": "degraded" if errors else "reconciled",
        "count": refired_count,
        "probe_errors": errors,
    }


async def relay_consents(
    *,
    engine: ConsentApprover,
    substrate: RunSubstrate,
    stop: asyncio.Event,
    interval_s: float = CONSENT_RELAY_INTERVAL_S,
) -> None:
    """Re-fire decided consent waits while fairly retrying degraded pages."""
    pages = _RelayPageScheduler()
    while not stop.is_set():
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        if stop.is_set():
            return
        page_after, retrying = pages.take()
        try:
            result, next_cursor = await _reconcile_consent_page(
                substrate,
                engine,
                after=page_after,
            )
        except Exception as exc:
            logger.exception("consent_relay_failed", error=str(exc))
            pages.failed(page_after, retrying=retrying)
            continue
        needs_retry = result["status"] == "degraded" or bool(result.get("_revisit", False))
        pages.completed(
            page_after,
            retrying=retrying,
            next_cursor=next_cursor,
            revisit=needs_retry,
        )
        if result["status"] == "degraded":
            logger.warning("consent_relay_degraded", probe_errors=result["probe_errors"])


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


async def _emit_terminal(
    substrate: RunSubstrate,
    run_id: str,
    *,
    emitter: RunEmitter | None = None,
) -> None:
    """Emit a reconciled run's terminal DONE onto a correctly-seeded, closed channel.

    R1: a fresh process restarts channel seqs at 0, but a swept run already has Step
    rows (it reached RUNNING → persisted seq 0), so a verbatim seq-0 terminal would
    collide with `uq_step_run_seq` and be dropped. Seed the freshly minted channel
    from the run's persisted next-seq so the terminal lands past the history.
    R2: close the channel after the emit — reconcile mints a channel per orphan and
    would otherwise leak one per startup sweep.
    """
    settled = await substrate.ledger.get(run_id)
    status = settled.status if settled is not None and settled.status in TERMINAL_STATUSES else RunStatus.FAILED
    if emitter is None:
        next_seq = await substrate.ledger.next_seq(run_id)
        substrate.bus.open(run_id, from_seq=next_seq)
        emitter = substrate.bus.emitter(run_id)
    emitter.done(status.value)
    try:
        await substrate.bus.wait_persisted(run_id)
    finally:
        # A failed append leaves the in-memory channel terminal. Drop it so a
        # later evidence repair can seed a fresh channel and retry persistence.
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
