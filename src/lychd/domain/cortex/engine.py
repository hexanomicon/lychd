"""`RunEngine` + `QueueRouter` — the single run entry point (A4 §6, C2).

`RunEngine.submit(intent)` is the one law for every surface (Bridge now; CLI and
A2A later): route ONCE via the `WorkflowRegistry`, resolve `(queue_name, priority)`
via the `QueueRouter` (the `[orchestration.routing]` map), persist a QUEUED `Run`
via the `RunLedger`, open the run's channel on the `RunEventBus`, and enqueue
`perform_run` onto the SAQ `runs` queue. The `asyncio.create_task` path in
`agents/router.submit` is gone — its logic lives here and in `ghouls/runs.py`.

Consent and delegated waits re-enter through exact durable delivery hops. `cancel`
settles canonical `CANCELLED` truth before best-effort physical cleanup and waits
for terminal Step evidence before closing the event channel.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

import structlog

from lychd.domain.cortex.admission import RunAdmissionCoordinator
from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.priority import (
    PRIORITY_BACKGROUND,
    PRIORITY_DEFAULT,
    PRIORITY_INTERACTIVE,
    saq_wire_priority,
)
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunDeliveryState, RunHandle, RunStatus
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.delegation.models import DelegatedAgentResult
    from lychd.domain.delegation.ports import DelegatedAgentCoordinatorPort

__all__ = [
    "DEFAULT_ROUTING",
    "QueueRouter",
    "RouteRule",
    "RunEngine",
    "RunQueue",
    "admit_consent_resume",
    "admit_delegate_resume",
    "contain_run_effects",
    "enqueue_run",
    "run_job_key",
]

logger = structlog.get_logger()
RUN_PUBLICATION_TIMEOUT_S = 10.0
RUN_JOB_HEARTBEAT_S = 120
RUN_CONTAINMENT_TIMEOUT_S = 10.0
ADMISSION_REFUSAL_ATTEMPTS = 3
ADMISSION_REFUSAL_RETRY_S = 0.05
PUBLICATION_FENCE_ABORT_ATTEMPTS = 3
PUBLICATION_FENCE_ABORT_RETRY_S = 0.05


def run_job_key(run_id: str, enqueue_seq: int) -> str:
    """Return the SAQ job key: unique per (run, resume-hop); idempotent within a hop."""
    return f"run:{run_id}:{enqueue_seq}"


async def _abort_fenced_publication(queue: RunQueue, job_key: str) -> None:
    """Retry containment when a broker accepts work after canonical truth fenced it."""
    for attempt in range(PUBLICATION_FENCE_ABORT_ATTEMPTS):
        try:
            async with asyncio.timeout(RUN_CONTAINMENT_TIMEOUT_S):
                job = await queue.job(job_key)
                if job is None:
                    return
                await queue.abort(job, "publication fenced by canonical run truth")
        except Exception:
            if attempt + 1 == PUBLICATION_FENCE_ABORT_ATTEMPTS:
                raise
            await asyncio.sleep(PUBLICATION_FENCE_ABORT_RETRY_S * (attempt + 1))
        else:
            return


async def _finish_fenced_publication(queue: RunQueue, job_key: str) -> None:
    """Complete exact late-job containment even when the publishing caller disconnects."""
    abort_task = asyncio.ensure_future(_abort_fenced_publication(queue, job_key))
    try:
        await asyncio.shield(abort_task)
    except asyncio.CancelledError as cancellation:
        try:
            await complete_under_cancellation(abort_task)
        except (Exception, asyncio.CancelledError) as exc:
            raise cancellation from exc
        raise


async def enqueue_run(
    queues: Mapping[str, RunQueue],
    ledger: RunLedger,
    run: RunRecord,
    *,
    enqueue_seq: int | None = None,
) -> None:
    """Enqueue `perform_run` for a run on its physical queue under a unique hop key.

    The ONE publication law, shared by initial admission and every resume. The
    delivery intent already exists durably; this function publishes its exact key
    and records acknowledgement without moving a concurrent worker claim backwards.
    """
    from lychd.domain.cortex.runs import RunDeliveryState

    seq = enqueue_seq if enqueue_seq is not None else run.enqueue_seq
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=seq)
    if delivery is None:
        msg = f"Run {run.run_id!r} has no delivery {seq}."
        raise RuntimeError(msg)
    if delivery.state is RunDeliveryState.HELD:
        msg = f"Run {run.run_id!r} delivery {seq} is still held by admission context."
        raise RuntimeError(msg)
    if delivery.state in {RunDeliveryState.CLAIMED, RunDeliveryState.SETTLED}:
        return
    queue = queues[run.queue_name]
    try:
        async with asyncio.timeout(RUN_PUBLICATION_TIMEOUT_S):
            await queue.enqueue(
                "perform_run",
                run_id=run.run_id,
                enqueue_seq=seq,
                key=run_job_key(run.run_id, seq),
                retries=0,  # graph retries are GraphRunner's job, not SAQ's
                timeout=0,  # graph/orchestrator own execution waits; this is broker metadata
                heartbeat=RUN_JOB_HEARTBEAT_S,
                # Wire inversion (R9): doctrine is higher=hotter, saq dequeues lowest-first.
                # The one and only inversion point lives in `saq_wire_priority`.
                priority=saq_wire_priority(run.priority),
            )
    except BaseException as exc:
        with suppress(Exception):
            await complete_under_cancellation(ledger.note_delivery_error(run.run_id, enqueue_seq=seq, error=str(exc)))
        raise
    published = await ledger.mark_delivery_published(run.run_id, enqueue_seq=seq)
    if published:
        return

    # Cancellation may have looked for this job while the broker was still
    # accepting it. If canonical truth fenced the generation before the
    # acknowledgement CAS, remove the now-stale physical job here.
    current = await ledger.get(run.run_id)
    if (
        current is not None
        and current.enqueue_seq == seq
        and current.status
        not in {
            RunStatus.CANCELLING,
            *TERMINAL_STATUSES,
        }
    ):
        return
    await _finish_fenced_publication(queue, run_job_key(run.run_id, seq))


async def admit_consent_resume(
    queues: Mapping[str, RunQueue],
    ledger: RunLedger,
    consents: ConsentAuthority,
    run: RunRecord,
    *,
    consent_id: str,
) -> bool:
    """Atomically admit and publish one consent resume hop.

    Admission atomically creates the QUEUED Run hop and its PENDING delivery. Once
    that commit wins, publication failure never retracts the verdict: startup or an
    operator reconcile republishes the same idempotent key.
    """
    consent = await consents.get(consent_id)
    if (
        consent is None
        or consent.id != consent_id
        or consent.run_id != run.run_id
        or consent.status not in {"granted", "denied", "expired"}
        or not consent.decided_by
        or consent.decided_at is None
        or consent.decided_at.tzinfo is None
        or consent.decided_at.utcoffset() is None
    ):
        return False
    from lychd.domain.cortex.ledger import ConsentAdmissionEvidence

    evidence = ConsentAdmissionEvidence(
        consent_id=consent.id,
        run_id=consent.run_id,
        status=consent.status,
        decided_by=consent.decided_by,
        decided_at=consent.decided_at,
    )
    admit_task = asyncio.ensure_future(ledger.try_admit_consent(run.run_id, consent_id=consent_id, evidence=evidence))
    try:
        enqueue_seq = await asyncio.shield(admit_task)
    except asyncio.CancelledError:
        enqueue_seq = await complete_under_cancellation(admit_task)
        _ = enqueue_seq
        raise
    if enqueue_seq is None:
        return False
    refreshed = await ledger.get(run.run_id) or run
    try:
        await enqueue_run(
            queues,
            ledger,
            refreshed,
            enqueue_seq=enqueue_seq,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - accepted delivery remains durable for relay
        logger.warning(
            "run_delivery_deferred",
            run_id=run.run_id,
            enqueue_seq=enqueue_seq,
            queue_name=refreshed.queue_name,
            error=str(exc),
        )
    return True


async def admit_delegate_resume(
    queues: Mapping[str, RunQueue],
    ledger: RunLedger,
    run: RunRecord,
    *,
    job_id: str,
) -> bool:
    """Admit and publish only the job that owns the current delegated wait."""
    admit_task = asyncio.ensure_future(ledger.try_admit_delegate(run.run_id, job_id=job_id))
    try:
        enqueue_seq = await asyncio.shield(admit_task)
    except asyncio.CancelledError:
        enqueue_seq = await complete_under_cancellation(admit_task)
        _ = enqueue_seq
        raise
    if enqueue_seq is None:
        return False
    refreshed = await ledger.get(run.run_id) or run
    try:
        await enqueue_run(
            queues,
            ledger,
            refreshed,
            enqueue_seq=enqueue_seq,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - accepted delivery remains durable for relay
        logger.warning(
            "run_delivery_deferred",
            run_id=run.run_id,
            enqueue_seq=enqueue_seq,
            queue_name=refreshed.queue_name,
            delegated_job_id=job_id,
            error=str(exc),
        )
    return True


class RunQueue(Protocol):
    """The narrow SAQ-queue surface the engine needs (`saq.Queue` satisfies it)."""

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any | None: ...

    async def job(self, job_key: str, /) -> Any | None: ...

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None: ...


class ConsentAdmissionView(Protocol):
    """Structural decided-consent view consumed without importing Codex."""

    @property
    def id(self) -> str: ...

    @property
    def run_id(self) -> str: ...

    @property
    def status(self) -> str: ...

    @property
    def decided_by(self) -> str | None: ...

    @property
    def decided_at(self) -> datetime | None: ...


class ConsentAuthority(Protocol):
    """The narrow consent read and cancellation authority required by Cortex."""

    async def get(self, consent_id: str) -> ConsentAdmissionView | None:
        """Return exact consent truth for resume admission."""
        ...

    async def cancel_pending_for_run(self, run_id: str, *, decided_by: str) -> int:
        """Settle every pending consent owned by one Run."""
        ...


async def contain_run_effects(
    run_id: str,
    *,
    delegates: DelegatedAgentCoordinatorPort | None,
    consents: ConsentAuthority | None,
    decided_by: str,
) -> list[BaseException]:
    """Contain every child authority correlated to one Run and report uncertainty."""
    errors: list[BaseException] = []
    if delegates is not None:
        try:
            async with asyncio.timeout(RUN_CONTAINMENT_TIMEOUT_S):
                jobs = await delegates.jobs_for_run(run_id, event_limit=0)
        except Exception as exc:  # noqa: BLE001 - consent containment must still run
            errors.append(exc)
        else:

            async def cancel_delegate(job_id: str) -> bool:
                async with asyncio.timeout(RUN_CONTAINMENT_TIMEOUT_S):
                    return await delegates.cancel(job_id)

            results = await asyncio.gather(
                *(cancel_delegate(job.ref.job_id) for job in jobs),
                return_exceptions=True,
            )
            errors.extend(result for result in results if isinstance(result, BaseException))
    if consents is not None:
        try:
            async with asyncio.timeout(RUN_CONTAINMENT_TIMEOUT_S):
                await consents.cancel_pending_for_run(run_id, decided_by=decided_by)
        except Exception as exc:  # noqa: BLE001 - return every containment failure
            errors.append(exc)
    return errors


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

    __slots__ = (
        "_terminal_repairs",
        "admissions",
        "bus",
        "cancellations",
        "consents",
        "delegates",
        "ledger",
        "queue_router",
        "queues",
        "stasis_store",
        "workflows",
    )

    def __init__(
        self,
        *,
        ledger: RunLedger,
        bus: RunEventBus,
        workflows: Any,
        queue_router: QueueRouter,
        queues: Mapping[str, RunQueue],
        admissions: RunAdmissionCoordinator | None = None,
        cancellations: RunCancellationCoordinator | None = None,
        stasis_store: Any | None = None,
        delegates: DelegatedAgentCoordinatorPort | None = None,
        consents: ConsentAuthority | None = None,
    ) -> None:
        """Bind the already-constructed run collaborators."""
        self.ledger = ledger
        self.bus = bus
        self.workflows = workflows
        self.queue_router = queue_router
        self.queues = queues
        self.admissions = admissions or RunAdmissionCoordinator()
        self.cancellations = cancellations or RunCancellationCoordinator()
        self._terminal_repairs = RunAdmissionCoordinator()
        self.delegates = delegates
        self.consents = consents
        if stasis_store is None:
            from lychd.domain.cortex.stasis import InMemoryStasisStore

            stasis_store = InMemoryStasisStore()
        self.stasis_store = stasis_store

    async def submit(
        self,
        intent: Intent,
        *,
        retain_before_publish: Callable[[str], Awaitable[None]] | None = None,
        idempotency_key: str | None = None,
        exclusive_session: bool = False,
    ) -> RunHandle:
        """Admit work, optionally allowing only one nonterminal Run per session.

        ``exclusive_session`` is a Topology-A causal fence for conversational
        surfaces. It serializes admission on this process's event loop, admits an
        exact idempotent replay, and otherwise refuses a second nonterminal Run for
        the same session. Terminal ledger truth releases the fence naturally; no
        process-local active marker becomes recovery authority.
        """
        if exclusive_session:
            session_key = ("exclusive_session", intent.session_id)
            while not self.admissions.begin(session_key):
                await self.admissions.wait(session_key)
            try:
                if idempotency_key is not None:
                    existing = await self.ledger.get_idempotent(intent, idempotency_key=idempotency_key)
                    if existing is not None:
                        return await self._submit_singleflight(
                            intent,
                            retain_before_publish=retain_before_publish,
                            idempotency_key=idempotency_key,
                        )
                active = await self.ledger.get_nonterminal_for_session(intent.session_id)
                if active is not None:
                    from lychd.domain.cortex.ledger import RunAdmissionConflictError

                    msg = f"Bridge session already has active Run {active.run_id!r}."
                    raise RunAdmissionConflictError(msg)
                return await self._submit_singleflight(
                    intent,
                    retain_before_publish=retain_before_publish,
                    idempotency_key=idempotency_key,
                )
            finally:
                self.admissions.finish(session_key)
        return await self._submit_singleflight(
            intent,
            retain_before_publish=retain_before_publish,
            idempotency_key=idempotency_key,
        )

    async def _submit_singleflight(
        self,
        intent: Intent,
        *,
        retain_before_publish: Callable[[str], Awaitable[None]] | None,
        idempotency_key: str | None,
    ) -> RunHandle:
        """Single-flight one optional durable admission identity."""
        if idempotency_key is None:
            return await self._submit_admission(
                intent,
                retain_before_publish=retain_before_publish,
                idempotency_key=None,
            )
        admission_key = ("idempotency", idempotency_key)
        while not self.admissions.begin(admission_key):
            await self.admissions.wait(admission_key)
        try:
            return await self._submit_admission(
                intent,
                retain_before_publish=retain_before_publish,
                idempotency_key=idempotency_key,
            )
        finally:
            self.admissions.finish(admission_key)

    async def _submit_admission(
        self,
        intent: Intent,
        *,
        retain_before_publish: Callable[[str], Awaitable[None]] | None,
        idempotency_key: str | None,
    ) -> RunHandle:
        """Route once, persist QUEUED, retain admission context, then publish work.

        S3: the run id is the LEDGER's canonical id (`run.run_id`); `intent.run_id`
        is advisory client-correlation only (stashed in the intent JSONB). The
        handle and every downstream surface (SSE URL, Step rows, checkpoint row, lease
        holder) key on `run.run_id`.

        `retain_before_publish` gates the initial delivery in ``HELD``. It receives
        the canonical run id after the atomic Run+delivery commit; only a successful
        caller-owned durable write releases that delivery to ``PENDING``.

        Retention failure terminally refuses the Run before publication. Broker
        failure is different: durable admission has succeeded, so the Run remains
        QUEUED and its exact delivery is recovered later rather than retracted.
        """
        if idempotency_key is not None:
            existing = await self.ledger.get_idempotent(intent, idempotency_key=idempotency_key)
            if existing is not None:
                if await self._repair_replayed_admission(existing, retain_before_publish):
                    return await self._publish_admission(existing)
                return await self._replayed_run_handle(existing)

        workflow = self.workflows.route(intent)
        queue_name, priority = self.queue_router.resolve(intent)
        create_task = asyncio.ensure_future(
            self._create_run_admission(
                intent,
                idempotency_key=idempotency_key,
                workflow_name=workflow.name,
                pattern_manifest=workflow.manifest.snapshot(),
                queue_name=queue_name,
                priority=priority,
                hold_delivery=retain_before_publish is not None,
            )
        )
        try:
            run, created = await asyncio.shield(create_task)
        except asyncio.CancelledError as exc:
            # The DB commit may have won the cancellation race. Learn the
            # canonical id, then refuse only a caller-context-gated admission.
            run, created = await complete_under_cancellation(create_task)
            if created and retain_before_publish is not None:
                await complete_under_cancellation(self._refuse_admission(run, exc))
            raise
        if not created:
            if not await self._repair_replayed_admission(run, retain_before_publish):
                return await self._replayed_run_handle(run)
        elif retain_before_publish is not None:
            await self._retain_and_release_admission(run, retain_before_publish)
        return await self._publish_admission(run)

    async def _publish_admission(self, run: RunRecord) -> RunHandle:
        """Open the live projection and publish one already-durable admission."""
        channel = await self._open_seeded_channel(run.run_id)
        try:
            await self._enqueue(run)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - accepted delivery remains durable for relay
            logger.warning(
                "run_delivery_deferred",
                run_id=run.run_id,
                enqueue_seq=run.enqueue_seq,
                queue_name=run.queue_name,
                error=str(exc),
            )
        return self._run_handle(run, channel=channel)

    async def _repair_replayed_admission(
        self,
        run: RunRecord,
        retain: Callable[[str], Awaitable[None]] | None,
    ) -> bool:
        """Classify replay delivery truth and repair only work still needing publication."""
        delivery = await self.ledger.get_delivery(run.run_id, enqueue_seq=run.enqueue_seq)
        if delivery is None:
            msg = f"Run {run.run_id!r} idempotent admission has no delivery truth."
            raise RuntimeError(msg)
        if delivery.state is RunDeliveryState.PENDING:
            return True
        if delivery.state is not RunDeliveryState.HELD:
            return False
        if retain is None:
            msg = f"Run {run.run_id!r} idempotent admission remains held without a retention owner."
            raise RuntimeError(msg)
        await self._retain_and_release_admission(run, retain)
        return True

    async def _create_run_admission(
        self,
        intent: Intent,
        *,
        idempotency_key: str | None,
        workflow_name: str,
        pattern_manifest: dict[str, Any],
        queue_name: str,
        priority: int,
        hold_delivery: bool,
    ) -> tuple[RunRecord, bool]:
        """Create fresh truth or resolve one exact idempotent replay."""
        if idempotency_key is not None:
            return await self.ledger.create_idempotent(
                intent,
                idempotency_key=idempotency_key,
                workflow_name=workflow_name,
                pattern_manifest=pattern_manifest,
                queue_name=queue_name,
                priority=priority,
                hold_delivery=hold_delivery,
            )
        return (
            await self.ledger.create(
                intent,
                workflow_name=workflow_name,
                pattern_manifest=pattern_manifest,
                queue_name=queue_name,
                priority=priority,
                hold_delivery=hold_delivery,
            ),
            True,
        )

    async def _replayed_run_handle(self, run: RunRecord) -> RunHandle:
        """Project replayed truth without minting a false terminal live channel."""
        channel = None if run.status in TERMINAL_STATUSES else await self._open_seeded_channel(run.run_id)
        return self._run_handle(run, channel=channel)

    async def _open_seeded_channel(self, run_id: str) -> Any:
        """Open a fresh process channel strictly after retained durable events."""
        return self.bus.open(run_id, from_seq=await self.ledger.next_seq(run_id))

    def _run_handle(self, run: RunRecord, *, channel: Any | None) -> RunHandle:
        """Project one canonical Run identity into the submit handle."""
        manifest = run.pattern_manifest
        pattern_id = str(manifest.get("key") or run.workflow_name)
        pattern_revision = str(manifest.get("revision") or "legacy-unversioned")
        return RunHandle(
            run_id=run.run_id,
            workflow_name=run.workflow_name,
            pattern_id=pattern_id,
            pattern_revision=pattern_revision,
            evidence_capture=cast(
                "Literal['process_local', 'durable_best_effort']",
                self.ledger.evidence_capture,
            ),
            channel=channel,
        )

    async def _retain_and_release_admission(
        self,
        run: RunRecord,
        retain: Callable[[str], Awaitable[None]],
    ) -> None:
        """Finish caller-owned retention and release its exact held delivery."""
        retain_task = asyncio.ensure_future(retain(run.run_id))
        try:
            await asyncio.shield(retain_task)
        except asyncio.CancelledError as cancellation:
            refusal_cause: BaseException = cancellation
            try:
                await complete_under_cancellation(retain_task)
            except (Exception, asyncio.CancelledError) as completion_exc:  # noqa: BLE001 - compensate any outcome
                refusal_cause = completion_exc
            await complete_under_cancellation(self._refuse_admission(run, refusal_cause))
            raise
        except Exception as exc:
            await complete_under_cancellation(self._refuse_admission(run, exc))
            raise
        await self._release_admission(run)

    async def _release_admission(self, run: RunRecord) -> None:
        """Release one retained delivery or compensate an ambiguous release failure."""
        release_task = asyncio.ensure_future(
            self.ledger.release_delivery(
                run.run_id,
                enqueue_seq=run.enqueue_seq,
            )
        )
        try:
            released = await asyncio.shield(release_task)
        except asyncio.CancelledError as cancellation:
            try:
                released = await complete_under_cancellation(release_task)
            except (Exception, asyncio.CancelledError) as completion_exc:
                try:
                    await complete_under_cancellation(self._resolve_release_failure(run, completion_exc))
                except (Exception, asyncio.CancelledError) as resolution_exc:
                    raise cancellation from resolution_exc
                raise cancellation from completion_exc
            if not released:
                exc = RuntimeError(f"Run {run.run_id!r} admission delivery could not be released.")
                await complete_under_cancellation(self._resolve_release_failure(run, exc))
            raise
        except Exception as exc:
            released = await complete_under_cancellation(self._resolve_release_failure(run, exc))
            if not released:
                raise
        if not released:
            exc = RuntimeError(f"Run {run.run_id!r} admission delivery could not be released.")
            released = await complete_under_cancellation(self._resolve_release_failure(run, exc))
            if not released:
                raise exc

    async def _resolve_release_failure(self, run: RunRecord, exc: BaseException) -> bool:
        """Distinguish a retained HELD delivery from one that release advanced."""
        delivery = await self.ledger.get_delivery(run.run_id, enqueue_seq=run.enqueue_seq)
        if delivery is None:
            msg = f"Run {run.run_id!r} admission delivery disappeared during release."
            raise RuntimeError(msg) from exc
        if delivery.state is not RunDeliveryState.HELD:
            return True
        if await self._refuse_admission(run, exc):
            return False
        delivery = await self.ledger.get_delivery(run.run_id, enqueue_seq=run.enqueue_seq)
        if delivery is not None and delivery.state is not RunDeliveryState.HELD:
            return True
        msg = f"Run {run.run_id!r} admission release could not be resolved safely."
        raise RuntimeError(msg) from exc

    async def _refuse_admission(self, run: RunRecord, exc: BaseException) -> bool:
        """Fail an unreleased initial admission, then terminate its event channel."""
        refusal_error: Exception | None = None
        settled = False
        for attempt in range(ADMISSION_REFUSAL_ATTEMPTS):
            try:
                settled = await self.ledger.try_fail_held(
                    run.run_id,
                    enqueue_seq=run.enqueue_seq,
                    error=f"admission failed: {exc}",
                )
                refusal_error = None
                break
            except Exception as candidate:  # noqa: BLE001 - bounded compensation retry
                refusal_error = candidate
                if attempt + 1 < ADMISSION_REFUSAL_ATTEMPTS:
                    await asyncio.sleep(ADMISSION_REFUSAL_RETRY_S * (attempt + 1))
        if refusal_error is not None:
            msg = f"Run {run.run_id!r} retained admission could not be refused."
            raise RuntimeError(msg) from refusal_error
        if not settled:
            return False
        with suppress(Exception):
            self.bus.emitter(run.run_id).done(RunStatus.FAILED.value)
            await self.bus.wait_persisted(run.run_id)
            self.bus.close(run.run_id)
        return True

    async def cancel(self, run_id: str, *, orphaned: bool = False) -> None:
        """Contain one exact run generation before committing terminal cancellation.

        ``begin_cancel`` fences claims and delivery rotation under the Run row lock.
        Delegate and broker cancellation must then acknowledge before
        ``finish_cancel`` may expose ``CANCELLED``. A failed containment attempt leaves
        honest, retryable ``CANCELLING`` truth. ``orphaned`` is startup-only authority
        to fence a pre-boot broker job whose former worker process no longer exists.
        """
        run = await self.ledger.get(run_id)
        if run is None:
            return
        if run.status is RunStatus.CANCELLED:
            errors: list[BaseException] = []
            try:
                await self._abort_job(run, orphaned=orphaned)
            except Exception as exc:  # noqa: BLE001 - child sweep must still run
                errors.append(exc)
            errors.extend(
                await contain_run_effects(
                    run_id,
                    delegates=self.delegates,
                    consents=self.consents,
                    decided_by="cortex:run-cancelled",
                )
            )
            self._raise_containment_errors(run, errors)
            try:
                await self._ensure_cancelled_evidence(run_id)
            finally:
                await self._cleanup_cancelled_checkpoint(run_id)
            return
        if run.status in TERMINAL_STATUSES:
            return
        cancel_task = asyncio.ensure_future(self._cancel_run(run, orphaned=orphaned))
        try:
            await asyncio.shield(cancel_task)
        except asyncio.CancelledError:
            # A disconnected caller must not interrupt the abort/status sequence.
            await complete_under_cancellation(cancel_task)
            raise

    async def _cancel_run(self, run: RunRecord, *, orphaned: bool) -> None:
        """Elect, contain, and durably settle one cancellation generation."""
        leader = await self._acquire_cancellation_lead(run)
        if leader is None:
            return
        try:
            elected = await self._elect_cancel_generation(leader.run_id)
            if elected is None:
                return
            errors = await self._contain_cancel(elected, orphaned=orphaned)
            self._raise_containment_errors(elected, errors)
            if not await self.ledger.finish_cancel(elected.run_id, enqueue_seq=elected.enqueue_seq):
                msg = f"Cancellation generation changed for Run {elected.run_id!r}."
                raise RuntimeError(msg)
            try:
                await self._ensure_cancelled_evidence(elected.run_id)
            finally:
                await self._cleanup_cancelled_checkpoint(elected.run_id)
        finally:
            self.cancellations.finish(leader.run_id)

    async def _acquire_cancellation_lead(self, run: RunRecord) -> RunRecord | None:
        """Serialize local cancellation callers while preserving failed retries."""
        while not self.cancellations.begin(run.run_id):
            await self.cancellations.wait(run.run_id)
            fresh = await self.ledger.get(run.run_id)
            if fresh is None or fresh.status in TERMINAL_STATUSES:
                return None
            run = fresh
        return run

    async def _elect_cancel_generation(self, run_id: str) -> RunRecord | None:
        """Re-read after local election, then fence the row's current generation."""
        fresh = await self.ledger.get(run_id)
        if fresh is None or fresh.status in TERMINAL_STATUSES:
            return None
        return await self.ledger.begin_cancel(run_id)

    async def _contain_cancel(self, run: RunRecord, *, orphaned: bool) -> list[BaseException]:
        """Stop the parent worker, then sweep every child authority it could create."""
        errors: list[BaseException] = []
        try:
            await self._abort_job(run, orphaned=orphaned)
        except Exception as exc:  # noqa: BLE001 - delegate failures must not skip broker containment
            errors.append(exc)
        errors.extend(
            await contain_run_effects(
                run.run_id,
                delegates=self.delegates,
                consents=self.consents,
                decided_by="cortex:run-cancelled",
            )
        )
        return errors

    @staticmethod
    def _raise_containment_errors(run: RunRecord, errors: list[BaseException]) -> None:
        """Keep CANCELLING nonterminal when any containment authority is uncertain."""
        for exc in errors:
            logger.error(
                "cancel_containment_failed",
                run_id=run.run_id,
                enqueue_seq=run.enqueue_seq,
                error=str(exc),
            )
        if errors:
            msg = f"Cancellation containment failed for Run {run.run_id!r}."
            raise RuntimeError(msg) from errors[0]

    async def _cleanup_cancelled_checkpoint(self, run_id: str) -> None:
        """Best-effort checkpoint cleanup after terminal cancellation truth."""
        try:
            await self._discard_stasis_checkpoint(run_id)
        except Exception as exc:  # terminal truth is already committed
            logger.exception(
                "cancel_cleanup_failed",
                run_id=run_id,
                error=str(exc),
            )

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
        if self.consents is None:
            return
        run = await self.ledger.get_by_consent(consent_id)
        if run is None:
            return
        await admit_consent_resume(
            self.queues,
            self.ledger,
            self.consents,
            run,
            consent_id=consent_id,
        )

    async def adopt_delegate(self, job_id: str, result: DelegatedAgentResult) -> bool:
        """Adopt a terminal delegated result, then publish one durable graph resume."""
        delegates = self._require_delegates()
        await delegates.adopt(job_id, result)
        return await self.resume_delegate(job_id)

    async def resume_delegate(self, job_id: str) -> bool:
        """Publish a resume only after the coordinator holds terminal job truth.

        Repeated callbacks remain useful: if a prior broker publication failed, the
        Run was restored to ``AWAITING_DELEGATE`` and this method retries admission.
        Once a caller wins the status CAS, every duplicate becomes an inert ``False``.
        """
        from lychd.domain.delegation.models import TERMINAL_DELEGATED_AGENT_STATUSES

        delegates = self._require_delegates()
        job = await delegates.get(job_id)
        if job is None or job.status not in TERMINAL_DELEGATED_AGENT_STATUSES:
            return False
        run = await self.ledger.get(job.request.run_id)
        if run is None:
            return False
        return await admit_delegate_resume(self.queues, self.ledger, run, job_id=job_id)

    async def _enqueue(self, run: RunRecord) -> None:
        """Enqueue `perform_run` for the run on its physical queue (unique key)."""
        await enqueue_run(self.queues, self.ledger, run)

    async def _abort_job(self, run: RunRecord, *, orphaned: bool = False) -> None:
        """Abort the cancellation-elected SAQ generation if it still exists."""
        queue = self.queues.get(run.queue_name)
        if queue is None:
            msg = f"Run queue {run.queue_name!r} is unavailable during cancellation."
            raise RuntimeError(msg)
        async with asyncio.timeout(RUN_CONTAINMENT_TIMEOUT_S):
            job = await queue.job(run_job_key(run.run_id, run.enqueue_seq))
            if job is None:
                return
            if orphaned:
                abort_orphan = getattr(queue, "abort_orphan", None)
                if abort_orphan is not None:
                    await abort_orphan(job, "cancelled during LychD reanimation")
                    return
            await queue.abort(job, "cancelled by the Magus")

    async def ensure_terminal_evidence(self, run_id: str) -> None:
        """Single-flight repair of one terminal event from canonical Run truth."""
        repair_key = ("terminal_evidence", run_id)
        while not self._terminal_repairs.begin(repair_key):
            await self._terminal_repairs.wait(repair_key)
        try:
            await self._repair_terminal_evidence(run_id)
        finally:
            self._terminal_repairs.finish(repair_key)

    async def _repair_terminal_evidence(self, run_id: str) -> None:
        """Drain any prior writer, then repair an absent terminal event exactly once."""
        from lychd.domain.cortex.events import RunEventKind

        run = await self.ledger.get(run_id)
        if run is None or run.status not in TERMINAL_STATUSES:
            msg = f"Run {run_id!r} has no terminal truth to evidence."
            raise RuntimeError(msg)
        # Canonical terminal truth authorizes a retry after an earlier async
        # append failed; the old generation remains latched for its own waiters.
        with suppress(Exception):
            await self.bus.wait_persisted(run_id)
        terminal = await self.ledger.latest_event(run_id, RunEventKind.DONE)
        if terminal is not None:
            if terminal.data != run.status.value:
                msg = f"Run {run_id!r} has terminal evidence {terminal.data!r}, not {run.status.value!r}."
                raise RuntimeError(msg)
            return
        self.bus.begin_persistence_retry(run_id)
        self.bus.open(run_id, from_seq=await self.ledger.next_seq(run_id))
        try:
            self.bus.emitter(run_id).done(run.status.value)
            await self.bus.wait_persisted(run_id)
        finally:
            self.bus.close(run_id)

    async def _ensure_cancelled_evidence(self, run_id: str) -> None:
        """Repair the single durable CANCELLED event using canonical Run truth."""
        await self.ensure_terminal_evidence(run_id)

    async def _discard_stasis_checkpoint(self, run_id: str) -> None:
        """Delete a cancelled run's checkpoint from the shared Stasis store."""
        await self.stasis_store.delete(run_id)

    def _require_delegates(self) -> DelegatedAgentCoordinatorPort:
        if self.delegates is None:
            msg = "Delegated-agent coordination is not configured."
            raise RuntimeError(msg)
        return self.delegates
