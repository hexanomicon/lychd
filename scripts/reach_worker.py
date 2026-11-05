"""Disposable native Reach documents or local conversation worker, OCI-only.

The explicit static conversation profile may request one already-running local
model through private supervisor pipes. No credentials, host runtime control,
network access, persistent memory or Mirror identity registry are available.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import stat
import sys
from collections.abc import Callable, MutableMapping
from contextlib import AbstractAsyncContextManager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NoReturn, cast
from uuid import UUID, uuid4

import structlog

from lychd.agents.factory import AgentForge, build_agent
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.reach.conversation_session import MAX_REQUESTS, ContextRounds, request_digest
from lychd.compositions.reach.conversation_workflow import (
    conversation_agent_spec,
    make_conversation_intent,
    persona_text,
    reach_conversation_workflow,
)
from lychd.compositions.reach.documents import (
    LEGACY_MAX_CORPUS_BYTES,
    MAX_CORPUS_BYTES,
    MAX_CORPUS_MANIFEST_BYTES,
    MAX_DOCUMENT_BYTES,
    PublicCorpus,
    parse_corpus_manifest,
    verify_corpus,
)
from lychd.compositions.reach.documents_workflow import (
    DocumentsRefused,
    make_documents_intent,
    reach_documents_workflow,
)
from lychd.compositions.reach.expressions import ConversationExpressions
from lychd.compositions.reach.operator_diagnostics import (
    DiagnosticCode,
    DiagnosticStage,
    FailedNodeDiagnostic,
    ReachRunDiagnostic,
    diagnostic_bytes,
    write_diagnostic_line,
)
from lychd.compositions.reach.operator_model import ModelRelay, OperatorModelAdapter, operator_model_rune
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
)
from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import (
    ReachTraceEvent,
    TraceCode,
    TraceCorrelation,
    TraceName,
    TraceSink,
    TraceStatus,
    error_code,
    trace_bytes,
)
from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    parse_request_line,
    protocol_bytes,
    strict_json,
)
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, ResearchRelay
from lychd.compositions.reach.schemas import ReachPolicy, require_aware
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import Block, ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.execution_context import current_occurrence_id, current_step_id
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.weaver.inspection import PatternInspectionDescriptor
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.schema import TransitionPlan

MAX_PENDING_INPUTS = 4
DIAGNOSTIC_TIMEOUT = 0.25
_TRACE_CORRELATION: ContextVar[TraceCorrelation | None] = ContextVar("reach_trace_correlation", default=None)


def _stderr_diagnostic(value: ReachRunDiagnostic) -> None:
    write_diagnostic_line(diagnostic_bytes(value))


def _stderr_trace(value: ReachTraceEvent) -> None:
    write_diagnostic_line(trace_bytes(value))


def _current_trace_correlation() -> TraceCorrelation | None:
    correlation = _TRACE_CORRELATION.get()
    if correlation is None:
        return None
    return correlation.model_copy(update={"occurrence_id": current_occurrence_id(), "step_id": current_step_id()})


def _trace_failure_code(error: BaseException | None) -> TraceCode | None:
    """Classify trusted types without rendering exception arguments or validation input."""
    if error is None or isinstance(error, asyncio.CancelledError):
        return None
    if (
        type(error) is DocumentsRefused
        and len(error.args) == 1
        and type(error.args[0]) is str
        and error.args[0] == "conversation_budget"
    ):
        return "budget"
    known = _failure_code(error) if isinstance(error, Exception) else None
    if known in {"model_unavailable", "model_timeout", "model_refused", "model_protocol", "model_failed"}:
        return cast("TraceCode", known)
    return error_code(error)


def _public_failure_reason(error: Exception) -> str:
    """Carry only recognized answer-preparation failures across the worker boundary."""
    code = _trace_failure_code(error)
    if code in {"budget", "model_unavailable", "model_timeout", "model_refused", "model_protocol", "model_failed"}:
        return code
    return "run_failed"


def _failure_code(error: Exception | None) -> DiagnosticCode | None:
    """Recognize exact trusted codes without rendering any exception."""
    if error is None or len(error.args) != 1:
        return None
    code = error.args[0]
    if not isinstance(code, str):
        return None
    if isinstance(error, DocumentsRefused) and code in {
        "conversation_output",
        "conversation_checkpoint",
        "conversation_fresh_state",
        "conversation_grant",
    }:
        return cast("DiagnosticCode", code)
    if type(error) is RuntimeError and code in {
        "model_unavailable",
        "model_timeout",
        "model_refused",
        "model_protocol",
        "model_failed",
    }:
        return cast("DiagnosticCode", code)
    return None


def _read_regular(path: Path, limit: int, *, directory_fd: int | None = None) -> bytes:
    """Open only one explicit regular file, refusing symlinks and excess bytes."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            msg = "file_refused"
            raise ValueError(msg)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            msg = "file_limit"
            raise ValueError(msg)
        return raw
    finally:
        os.close(descriptor)


def load_corpus(directory: Path) -> PublicCorpus:
    """Detach and verify a bounded public export through one no-follow directory handle."""
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw = _read_regular(Path("manifest.json"), MAX_CORPUS_MANIFEST_BYTES, directory_fd=descriptor)
        manifest = parse_corpus_manifest(raw)
        contents: list[bytes] = []
        total = 0
        limit = LEGACY_MAX_CORPUS_BYTES if manifest.schema_version == 1 else MAX_CORPUS_BYTES
        for document in manifest.documents:
            content = _read_regular(Path(document.file), MAX_DOCUMENT_BYTES, directory_fd=descriptor)
            total += len(content)
            if total > limit:
                msg = "corpus_limit"
                raise ValueError(msg)
            contents.append(content)
        return verify_corpus(manifest, tuple(contents))
    finally:
        os.close(descriptor)


def load_policy(path: Path) -> ReachPolicy:
    """Read explicit generic JSON policy; never discover operator files or Settings."""
    raw = _read_regular(path, MAX_WIRE_BYTES)
    strict_json(raw)
    return ReachPolicy.model_validate_json(raw)


class NoCapabilities:
    """Every inference, tool, provider and hardware capability is unavailable."""

    def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        capability_key: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
    ) -> AbstractAsyncContextManager[CapabilityGrant]:
        """Refuse instead of materializing a capability handle."""
        del family, model_name, capability_key, run_id, priority, require_modalities, requires_tools
        msg = "operator_no_capability"
        raise RuntimeError(msg)


class NoTransitions:
    """Open ordinary native claims while forbidding all runtime transitions."""

    def __init__(self) -> None:
        """Create only a local claim gate, without hardware services."""
        self.worker_broker = GhoulBroker()

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan:  # noqa: ARG002
        """Refuse every request to change physical runtime state."""
        msg = "operator_no_transition"
        raise RuntimeError(msg)


@dataclass
class LocalJob:
    """A process-owned notification, with no broker or recovery guarantee."""

    key: str
    task: asyncio.Task[Any] | None = None


@dataclass
class LocalQueue:
    """Keep exact delivery keys until their locally owned worker retires."""

    jobs: dict[str, LocalJob] = field(default_factory=dict)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> LocalJob:
        if job_or_func != "perform_run":
            msg = "operator_job_refused"
            raise ValueError(msg)
        key = str(kwargs["key"])
        return self.jobs.setdefault(key, LocalJob(key))

    async def job(self, job_key: str, /) -> LocalJob | None:
        return self.jobs.get(job_key)

    async def abort(self, job: LocalJob, error: str, /, ttl: float = 5) -> None:  # noqa: ARG002
        if job.task is not None and not job.task.done():
            job.task.cancel()
            await asyncio.gather(job.task, return_exceptions=True)


@dataclass
class DocumentsRuntime:
    """One serial native generation; no result grants a terminal replay or an external send."""

    policy: ReachPolicy
    corpus: PublicCorpus
    started_at: datetime
    clock: Callable[[], datetime]
    engine: RunEngine
    substrate: RunSubstrate
    sessions: BridgeSessionStore
    queue: LocalQueue
    bus: InProcessEventBus
    profile: OperatorConversationProfile | None = None
    pending_inputs: list[bytes] = field(default_factory=list)
    late_response_filter: Callable[[bytes], bool] | None = None
    generation: str = field(default_factory=lambda: str(uuid4()))
    diagnostic: Callable[[ReachRunDiagnostic], None] | None = None
    trace: TraceSink | None = None
    _trace_seq: int = 0
    _context_rounds: ContextRounds = field(default_factory=ContextRounds)
    _serial: asyncio.Lock = field(default_factory=asyncio.Lock)

    def observe_trace(self, name: TraceName, *, status: TraceStatus = "observed", **fields: Any) -> None:
        """Record each capture attempt before validation; later records expose skipped attempts."""
        if self.trace is None:
            return
        self._trace_seq += 1
        seq = self._trace_seq
        try:
            event = ReachTraceEvent.model_validate(
                {
                    "producer": "core",
                    "generation": self.generation,
                    "observed_at": self.clock(),
                    "trace_seq": seq,
                    "name": name,
                    "status": status,
                    **fields,
                }
            )
            self.trace(event)
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - capture cannot alter execution or cancellation
            return

    def observe_native(self, event: RunEvent) -> None:
        """Copy only structural native identities, never arbitrary event bodies or metadata."""
        names: dict[RunEventKind, TraceName] = {
            RunEventKind.STATUS: "native_status",
            RunEventKind.NODE: "native_node",
            RunEventKind.DISPATCH: "native_dispatch",
            RunEventKind.TRANSITION: "native_transition",
            RunEventKind.DONE: "native_done",
        }
        name = names.get(event.kind)
        if name is None:
            return
        correlation = _TRACE_CORRELATION.get()
        request_id = correlation.request_id if correlation is not None and correlation.run_id == event.run_id else None
        fields: dict[str, Any] = {
            "run_id": event.run_id,
            "request_id": request_id,
            "native_event_id": event.event_id,
            "native_seq": event.seq,
            "observed_at": event.ts,
        }
        status = "observed"
        if event.kind is RunEventKind.NODE:
            fields.update(
                node=event.data,
                occurrence_id=event.meta.get("occurrence_id") or None,
                pattern_id=event.meta.get("pattern_id") or None,
                pattern_revision=event.meta.get("pattern_revision") or None,
            )
            status = event.meta.get("phase", "observed")
            if status == "entered":
                fields["step_id"] = event.event_id
        elif event.kind in {RunEventKind.STATUS, RunEventKind.DONE}:
            status = event.data
        else:
            fields["occurrence_id"] = event.meta.get("occurrence_id") or None
        self.observe_trace(name, status=cast("TraceStatus", status), **fields)

    @property
    def ready(self) -> ReachWorkerReady:
        return ReachWorkerReady(
            generation=self.generation,
            started_at=self.started_at,
            policy_digest=self.policy.digest,
            corpus_digest=self.corpus.digest,
            model_binding_digest=self.profile.digest if self.profile else None,
            adaptive_context=self.profile.adaptive_context if self.profile else False,
            research_enabled=self.profile.research.enabled if self.profile else False,
            expressions=self.profile.expressions if self.profile else ConversationExpressions(),
        )

    def refuse(
        self, request_id: str, reason: str, *, error: bool = False, run_id: str | None = None
    ) -> ReachWorkerResult:
        """Return only stable codes, excluding foreign text and exception diagnostics."""
        return ReachWorkerResult(
            request_id=request_id,
            status="error" if error else "refused",
            run_id=run_id,
            policy_digest=self.policy.digest,
            corpus_digest=self.corpus.digest,
            model_binding_digest=self.profile.digest if self.profile else None,
            reason=reason,
        )

    def intent(self, request: ReachWorkerRequest, session_id: str) -> Any:
        """Select the exact development score without broadening documents mode."""
        if request.event.action == "converse":
            if self.profile is None:
                msg = "action_not_supported"
                raise DocumentsRefused(msg)
            return make_conversation_intent(
                self.policy,
                self.corpus,
                self.profile,
                request,
                session_id=session_id,
                started_at=self.started_at,
                now=self.clock(),
            )
        return make_documents_intent(
            self.policy,
            self.corpus,
            request,
            session_id=session_id,
            started_at=self.started_at,
            now=self.clock(),
        )

    async def observe_result(
        self,
        request_id: str,
        run_id: str,
        result: ReachWorkerResult,
        stage: DiagnosticStage,
        error: Exception | None,
    ) -> None:
        """Best-effort bounded projection, isolated from Run and result settlement."""
        if self.diagnostic is None:
            return
        try:
            evidence = "flushed"
            try:
                async with asyncio.timeout(DIAGNOSTIC_TIMEOUT):
                    await self.substrate.bus.wait_persisted(run_id)
            except Exception:  # noqa: BLE001 - diagnostics cannot change the result
                evidence = "unavailable"
            terminal = None
            failed = None
            try:
                async with asyncio.timeout(DIAGNOSTIC_TIMEOUT):
                    terminal = await self.substrate.ledger.get(run_id)
                    latest = await self.substrate.ledger.latest_event(run_id, RunEventKind.NODE)
                if latest is not None and latest.meta.get("phase") == "failed":
                    failed = FailedNodeDiagnostic(
                        event_id=latest.event_id,
                        seq=latest.seq,
                        node=latest.data,
                        occurrence_id=latest.meta["occurrence_id"],
                    )
            except Exception:  # noqa: BLE001 - missing structural evidence remains explicit
                evidence = "unavailable"
            try:
                admitted_request_id = request_id if str(UUID(request_id)) == request_id else None
            except ValueError:
                admitted_request_id = None
            record = ReachRunDiagnostic.model_validate(
                {
                    "observed_at": self.clock(),
                    "generation": self.generation,
                    "request_id": admitted_request_id,
                    "run_id": run_id,
                    "status": result.status,
                    "reason": result.reason,
                    "stage": stage,
                    "run_status": terminal.status.value if terminal else None,
                    "evidence": evidence,
                    "failure_code": _failure_code(error),
                    "failed_node": failed,
                }
            )
            self.diagnostic(record)
        except Exception:  # noqa: BLE001 - metadata/sink failures never become Run failure
            return

    async def process(self, request: ReachWorkerRequest, *, timeout: float = 15) -> ReachWorkerResult:  # noqa: C901, PLR0911, PLR0912, PLR0915, ASYNC109 - explicit admission, stage attribution and terminal cleanup
        """Admit each permitted round to a fresh Run and retrieve its exact settled result."""
        async with self._serial:
            digest = request_digest(request)
            adaptive = self.profile.adaptive_context if self.profile else False
            reason = self._context_rounds.reason(request, digest, adaptive=adaptive)
            if reason is not None:
                return self.refuse(request.request_id, reason)
            # Validate before even a fixture session or native Run is constructed.
            try:
                self.intent(request, "preflight")
            except DocumentsRefused as error:
                return self.refuse(request.request_id, str(error))
            self._context_rounds.admit(request, digest)
            session = await self.sessions.create_session(title="Operator public documents")
            intent = self.intent(request, session.id)
            handle = await self.engine.submit(intent, idempotency_key=f"{self.generation}:{digest}")
            self.observe_trace(
                "run_started",
                status="started",
                request_id=request.request_id,
                run_id=handle.run_id,
                pattern_id=handle.pattern_id,
                pattern_revision=handle.pattern_revision,
                context_round=request.context_round,
            )
            result = None
            failure: BaseException | None = None
            stage: DiagnosticStage = "result_lookup"
            task = None
            try:
                run = await self.substrate.ledger.get(handle.run_id)
                if run is None:
                    result = self.refuse(request.request_id, "run_missing", error=True)
                    return result
                stage = "execute"
                correlation = None
                # Legacy non-UUID fixture requests carry no diagnostic correlation.
                with suppress(ValueError):
                    correlation = TraceCorrelation(
                        generation=self.generation, request_id=request.request_id, run_id=handle.run_id
                    )
                token = _TRACE_CORRELATION.set(correlation)
                try:
                    task = asyncio.create_task(
                        perform_run({"run_substrate": self.substrate}, run_id=run.run_id, enqueue_seq=run.enqueue_seq)
                    )
                finally:
                    _TRACE_CORRELATION.reset(token)
                for job in self.queue.jobs.values():
                    if job.task is None:
                        job.task = task
                async with asyncio.timeout(timeout):
                    await task
                    stage = "evidence_flush"
                    await self.substrate.bus.wait_persisted(run.run_id)
                stage = "result_lookup"
                terminal = await self.substrate.ledger.get(run.run_id)
                turn = await self.sessions.settled_turn_for_run(run.run_id)
                if terminal is None or terminal.status is not RunStatus.DONE or turn is None:
                    result = self.refuse(request.request_id, "run_incomplete", error=True, run_id=run.run_id)
                    return result
                stage = "result_validation"
                result = ReachWorkerResult.model_validate_json(turn.content)
                if result.request_id != request.request_id or result.run_id != run.run_id:
                    result = self.refuse(request.request_id, "result_binding", error=True, run_id=run.run_id)
                    return result
                self._context_rounds.settled(request, result, adaptive=adaptive)
                return result  # noqa: TRY300 - settlement retrieval shares the guarded failure boundary
            except TimeoutError:
                failure = TimeoutError()
                result = self.refuse(request.request_id, "run_timeout", error=True, run_id=handle.run_id)
                return result
            except asyncio.CancelledError as error:
                failure = error
                raise
            except Exception as error:  # noqa: BLE001 - closed diagnostics never echo input, paths or provider errors
                failure = error
                result = self.refuse(
                    request.request_id,
                    _public_failure_reason(error),
                    error=True,
                    run_id=handle.run_id,
                )
                return result
            finally:
                if task is not None:
                    if not task.done():
                        task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                self.queue.jobs.clear()
                if result is not None:
                    await self.observe_result(
                        request.request_id,
                        handle.run_id,
                        result,
                        stage,
                        failure if isinstance(failure, Exception) else None,
                    )
                    self.observe_trace(
                        "run_finished",
                        status=result.status,
                        request_id=request.request_id,
                        run_id=handle.run_id,
                        context_round=request.context_round,
                        code=_trace_failure_code(failure),
                    )
                elif isinstance(failure, asyncio.CancelledError):
                    self.observe_trace(
                        "run_finished",
                        status="cancelled",
                        request_id=request.request_id,
                        run_id=handle.run_id,
                        context_round=request.context_round,
                    )

    async def aclose(self) -> None:
        """Retire owned tasks before withdrawing the ephemeral event bus."""
        for job in self.queue.jobs.values():
            await self.queue.abort(job, "shutdown")
        await self.bus.aclose()


def build_runtime(
    policy: ReachPolicy,
    corpus: PublicCorpus,
    *,
    profile: OperatorConversationProfile | None = None,
    model_relay: ModelRelay | None = None,
    research_relay: ResearchRelay | None = None,
    diagnostic: Callable[[ReachRunDiagnostic], None] | None = None,
    trace: TraceSink | None = None,
    started_at: datetime | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DocumentsRuntime:
    """Compose isolated memory collaborators; never publish a global application substrate."""
    boundary = started_at if started_at is not None else clock()
    require_aware(boundary)

    def observe_workflow_trace(event: ReachTraceEvent) -> None:
        fields = event.model_dump(
            exclude={"kind", "schema_version", "producer", "generation", "trace_seq", "name", "status"}
        )
        runtime.observe_trace(event.name, status=event.status, **fields)

    workflow = reach_documents_workflow(policy, corpus, started_at=boundary, clock=clock)
    workflows = [workflow]
    animator_registry = AnimatorRegistry(declarations=AnimatorDeclarations((), ()))
    leases = LeaseLedger()
    forge = AgentForge()
    identity = None
    if profile is not None:
        if model_relay is None:
            msg = "model_relay_required"
            raise ValueError(msg)
        animator_registry = AnimatorRegistry(
            declarations=AnimatorDeclarations((operator_model_rune(profile),), ()),
            runtime_adapters=(OperatorModelAdapter(profile, model_relay),),
        )
        animator_registry.load(probe_readiness=False)
        workflows.append(
            reach_conversation_workflow(
                policy,
                corpus,
                profile,
                started_at=boundary,
                clock=clock,
                research_relay=research_relay,
                trace=observe_workflow_trace if trace is not None else None,
            )
        )
        spec = conversation_agent_spec(profile)
        forge.register(spec.name, lambda selected: build_agent(selected, toolset_factories={}))
        identity = Block(layer=1, key=spec.instructions_key, text=persona_text(profile))
    registry = BuiltinWorkflowRegistry(
        workflows=tuple(workflows),
        default_name=workflow.name,
        route_precedence=tuple(item.name for item in workflows[1:]),
    )
    ledger = InMemoryRunLedger()

    def observe_native(event: RunEvent) -> None:
        runtime.observe_native(event)

    bus = InProcessEventBus(ledger=ledger, observer=observe_native if trace is not None else None)
    sessions = BridgeSessionStore(sigil_name="reach.guest")
    queue = LocalQueue()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        orchestrator=NoTransitions(),
        dispatcher=Dispatcher(animator_registry, leases=leases, events=bus) if profile else NoCapabilities(),
        context=ContextOrchestrator(registry=animator_registry, identity_block=identity),
        fragments=build_fragment_registry(),
        turns=sessions,
        forge=forge,
        leases=leases,
        queues={"operator-reach": queue},
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        queue_router=QueueRouter({"default": RouteRule(queue="operator-reach", priority=50)}),
        queues=substrate.queues,
        stasis_store=substrate.stasis_store,
        cancellations=substrate.cancellations,
    )
    runtime = DocumentsRuntime(
        policy,
        corpus,
        boundary,
        clock,
        engine,
        substrate,
        sessions,
        queue,
        bus,
        profile=profile,
        diagnostic=diagnostic,
        trace=trace,
    )
    return runtime


async def serve(runtime: DocumentsRuntime, reader: asyncio.StreamReader, write: Callable[[bytes], None]) -> None:
    """Process newline frames serially, stopping on overflow rather than retaining hostile bytes."""
    write(protocol_bytes(runtime.ready))
    while True:
        try:
            raw = runtime.pending_inputs.pop(0) if runtime.pending_inputs else await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                write(protocol_bytes(runtime.refuse("invalid", "invalid_request", error=True)))
            return
        except asyncio.LimitOverrunError:
            write(protocol_bytes(runtime.refuse("invalid", "input_limit", error=True)))
            return
        try:
            if runtime.late_response_filter is not None and runtime.late_response_filter(raw):
                continue
            request = parse_request_line(raw)
        except (ValueError, UnicodeError, RecursionError):
            write(protocol_bytes(runtime.refuse("invalid", "invalid_request", error=True)))
            continue
        try:
            budget = (
                900
                if runtime.profile and runtime.profile.research.enabled
                else 750
                if runtime.profile
                else 15
            )
            result = await runtime.process(request, timeout=budget)
        except Exception:  # noqa: BLE001 - malformed continuations never echo their diagnostics
            result = runtime.refuse(request.request_id, "run_failed", error=True)
        write(protocol_bytes(result))


class PipeModelRelay:
    """One correlated model request at a time, sharing the supervisor's bounded input pipe."""

    def __init__(
        self, profile: OperatorConversationProfile, reader: asyncio.StreamReader, write: Callable[[bytes], None]
    ) -> None:
        """Retain only the selected profile and bounded standard-stream custody."""
        self.profile, self.reader, self.write = profile, reader, write
        self.pending_inputs: list[bytes] = []
        self.retired_calls: dict[str, tuple[str, str | None]] = {}
        self.lock = asyncio.Lock()

    async def __call__(self, operation: str, payload_json: str) -> str:
        if operation not in {"probe", "generate"}:
            msg = "model_operation"
            raise ValueError(msg)
        admitted_operation: Literal["probe", "generate"] = "probe" if operation == "probe" else "generate"
        frame = OperatorModelRequest(
            call_id=str(uuid4()),
            binding_digest=self.profile.digest,
            operation=admitted_operation,
            payload_json=payload_json,
            correlation=_current_trace_correlation(),
        )
        raw = await self._exchange(
            frame.model_dump_json().encode() + b"\n", call_id=frame.call_id, budget=self.profile.timeout_seconds + 5
        )
        response = OperatorModelResponse.model_validate_json(raw)
        if response.call_id != frame.call_id or response.binding_digest != frame.binding_digest:
            msg = "model_response_binding"
            raise ValueError(msg)
        if response.status != "ok":
            raise RuntimeError(response.reason)
        return response.payload_json

    async def research(self, frame: OperatorResearchRequest) -> OperatorResearchResponse:
        """Expose only the separate catalogue/progress handoff, never an HTTP client."""
        if not self.profile.research.enabled or frame.binding_digest != self.profile.digest:
            msg = "research_binding"
            raise ValueError(msg)
        correlation = _current_trace_correlation()
        if correlation is not None and correlation.request_id != frame.request_id:
            correlation = None
        frame = frame.model_copy(update={"correlation": correlation})
        raw = await self._exchange(
            frame.model_dump_json().encode() + b"\n",
            call_id=frame.call_id,
            budget=150,
            response_kind="research_response",
            request_id=frame.request_id,
        )
        response = OperatorResearchResponse.model_validate_json(raw)
        if (response.call_id, response.request_id, response.binding_digest) != (
            frame.call_id,
            frame.request_id,
            frame.binding_digest,
        ):
            msg = "research_response_binding"
            raise ValueError(msg)
        return response

    def discard_late(self, raw: bytes) -> bool:
        """Keep a retired response from becoming another event or breaking the next call."""
        parsed = strict_json(raw)
        if not isinstance(parsed, dict):
            return False
        value = cast("dict[str, Any]", parsed)
        call_id = value.get("call_id")
        if not isinstance(call_id, str) or call_id not in self.retired_calls:
            return False
        kind, request_id = self.retired_calls[call_id]
        if value.get("kind") != kind:
            msg = "retired_response_binding"
            raise ValueError(msg)
        if value.get("kind") == "model_response":
            model = OperatorModelResponse.model_validate_json(raw)
            if model.binding_digest != self.profile.digest:
                msg = "model_response_binding"
                raise ValueError(msg)
            return True
        if value.get("kind") == "research_response":
            research = OperatorResearchResponse.model_validate_json(raw)
            if research.binding_digest != self.profile.digest or research.request_id != request_id:
                msg = "research_response_binding"
                raise ValueError(msg)
            return True
        return False

    async def _exchange(
        self,
        raw_frame: bytes,
        *,
        call_id: str,
        budget: float,
        response_kind: str = "model_response",
        request_id: str | None = None,
    ) -> bytes:
        async with self.lock:
            if len(raw_frame) > MAX_WIRE_BYTES:
                msg = "model_frame_limit"
                raise ValueError(msg)
            if len(self.retired_calls) >= MAX_REQUESTS * 4:
                msg = "model_generation_call_budget"
                raise ValueError(msg)
            try:
                self.write(raw_frame)
                async with asyncio.timeout(budget):
                    while True:
                        raw = await self.reader.readuntil(b"\n")
                        if self.discard_late(raw):
                            continue
                        value = strict_json(raw)
                        observed = cast("dict[str, Any]", value) if isinstance(value, dict) else None
                        if observed is not None and observed.get("kind") == "request":
                            parse_request_line(raw)
                            if len(self.pending_inputs) >= MAX_PENDING_INPUTS:
                                msg = "model_pending_limit"
                                raise ValueError(msg)
                            self.pending_inputs.append(raw)
                            continue
                        return raw
            finally:
                self.retired_calls[call_id] = (response_kind, request_id)


async def run(policy: ReachPolicy, corpus: PublicCorpus, profile: OperatorConversationProfile | None = None) -> None:
    """Own stdin and the native runtime until EOF, cancellation or process shutdown."""
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    protocol = asyncio.StreamReaderProtocol(reader)
    transport, _ = await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    def write(raw: bytes) -> None:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()

    relay = PipeModelRelay(profile, reader, write) if profile else None
    runtime = build_runtime(
        policy,
        corpus,
        profile=profile,
        model_relay=relay,
        research_relay=relay.research if relay is not None else None,
        diagnostic=_stderr_diagnostic,
        trace=_stderr_trace,
    )
    if relay is not None:
        runtime.pending_inputs = relay.pending_inputs
        runtime.late_response_filter = relay.discard_late
    try:
        with suppress(Exception, asyncio.CancelledError):
            declaration = (
                ReachPatternObservation(
                    generation=runtime.generation,
                    patterns=tuple(
                        PatternInspectionDescriptor.from_workflow(item) for item in runtime.substrate.workflows.all()
                    ),
                )
                .model_dump_json()
                .encode()
                + b"\n"
            )
            if len(declaration) <= MAX_WIRE_BYTES:
                write(declaration)
        await serve(runtime, reader, write)
    finally:
        transport.close()
        await runtime.aclose()


def _require_image() -> None:
    if not Path("/opt/lychd-test-image").is_file() or not (
        Path("/run/.containerenv").is_file() or Path("/.dockerenv").is_file()
    ):
        msg = "operator_image_required"
        raise ValueError(msg)


def _drop_diagnostic(_logger: Any, _method: str, _event: MutableMapping[str, Any]) -> NoReturn:
    raise structlog.DropEvent


def main(argv: list[str] | None = None) -> int:
    """Explicit startup only; help loads no operator configuration or runtime."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--corpus-dir", required=True, type=Path)
    parser.add_argument("--conversation-profile", type=Path)
    arguments = parser.parse_args(argv)
    # The wire owns stdout. Foreign/runtime diagnostics cannot become protocol
    # frames or disclose a rejected question through an exception renderer.
    previous_level = logging.root.manager.disable
    previous_config = structlog.get_config()
    logging.disable(logging.CRITICAL)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL), processors=[_drop_diagnostic]
    )
    try:
        _require_image()
        policy, corpus = load_policy(arguments.policy), load_corpus(arguments.corpus_dir)
        profile = None
        if arguments.conversation_profile is not None:
            raw_profile = _read_regular(arguments.conversation_profile, MAX_WIRE_BYTES)
            strict_json(raw_profile)
            profile = OperatorConversationProfile.model_validate_json(raw_profile)
        asyncio.run(run(policy, corpus, profile))
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:  # noqa: BLE001 - stdout stays protocol-only; errors never expose input
        print("reach_worker_startup_refused", file=sys.stderr)  # noqa: T201 - fixed local diagnostic
        return 1
    finally:
        logging.disable(previous_level)
        structlog.configure(**previous_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
