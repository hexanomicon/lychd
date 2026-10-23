"""Explicit native Run assembly and finite operator FIFO for the companion lab."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, replace
from math import ceil
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from lychd.agents.context_limits import limit_model_requests
from lychd.agents.deps import LychDDeps
from lychd.agents.factory import build_agent
from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.blockworld.companion import (
    MAX_ACTIONS,
    MAX_QUEUE,
    CompanionReason,
    CompanionRefusalError,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    companion_workflow,
    strict_json,
)
from lychd.compositions.blockworld.companion_intent import (
    CompanionInstruction,
    CompanionIntentProfile,
    revalidate_intent_profile,
)
from lychd.compositions.blockworld.local_runtime import LocalRunQueue, RefuseHostTransitions
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import SettingsSnapshot
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.domain.cortex.substrate import get_run_substrate, reset_run_substrate, set_run_substrate
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from lychd.extensions.builtin.animator.vllm.register import register
from lychd.extensions.context import ExtensionContext
from lychd.interface.web.altar_services import AltarServices, build_altar_services
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.companion_bridge import CompanionBridge
from lychd.system.services.companion_intent import (
    CompanionIntentError,
    CompanionIntentModel,
    companion_intent_spec,
    decode_intent_decision,
)

type RecordSink = Callable[[dict[str, Any]], Awaitable[None]]
type CompanionInput = CompanionRequest | CompanionInstruction


class NativeCompanionInterpreter:
    """One exact native grant per instruction, with a finite session request budget."""

    def __init__(self, profile: CompanionIntentProfile, service: CompanionService) -> None:
        """Bind the immutable selected profile and the physical authority owner."""
        self.profile, self.service = revalidate_intent_profile(profile), service
        self.profile_digest = self.profile.digest
        self.used = 0

    async def interpret(self, instruction: CompanionInstruction, common: WorkflowServices, run_id: str) -> str:
        self.service.validate_envelope(instruction, common.sigil_provider())
        if instruction.profile_digest != self.profile_digest:
            raise CompanionRefusalError(reason="interpretation_unavailable")
        if self.used >= self.profile.max_requests:
            raise CompanionRefusalError(reason="interpretation_budget_exhausted")
        remaining = instruction.expires_at_ms / 1000 - time.time()
        if remaining <= 0:
            msg = "Original instruction expired."
            raise ValueError(msg)
        self.used += 1
        try:
            return await self._interpret(instruction, common, run_id, remaining)
        except CompanionRefusalError:
            raise
        except CompanionIntentError:
            raise CompanionRefusalError(reason="interpretation_response_refused") from None
        except ValueError:
            raise
        except Exception:  # noqa: BLE001 - provider diagnostics do not define a host reason
            raise CompanionRefusalError(reason="interpretation_unavailable") from None

    async def _interpret(
        self, instruction: CompanionInstruction, common: WorkflowServices, run_id: str, remaining: float
    ) -> str:
        async with asyncio.timeout(min(remaining, self.profile.inference_timeout_s)):
            async with common.dispatcher.lease_grant(
                family="chat", capability_key=self.profile.capability_key, run_id=run_id, requires_tools=False
            ) as grant:
                self.service.validate_envelope(instruction, common.sigil_provider())
                model, limits = limit_model_requests(
                    grant.model, context_window=self.profile.context_tokens, output_reserve=self.profile.max_tokens
                )
                limits = cast("UsageLimits", limits)
                limits.request_limit, limits.tool_calls_limit = 1, 0
                limits.total_tokens_limit = self.profile.context_tokens
                guarded = CompanionIntentModel(cast("Model", model), model_id=self.profile.model_id)
                deps = LychDDeps(
                    sigil=common.sigil_provider(),
                    grant=grant,
                    dispatcher=common.dispatcher,
                    orchestrator=common.orchestrator,
                    context=common.context,
                    run_id=run_id,
                    step_id="interpret",
                    priority=50,
                )
                prompt = json.dumps(
                    {
                        "instruction": instruction.instruction,
                        "bound_player_available": instruction.target_id is not None,
                    },
                    ensure_ascii=False,
                )
                answer = await common.forge.agent_for(companion_intent_spec(max_tokens=self.profile.max_tokens)).run(
                    prompt,
                    deps=deps,
                    model=guarded,
                    model_settings=grant.model_settings(),
                    usage_limits=limits,
                )
                self.service.validate_envelope(instruction, common.sigil_provider())
                return str(decode_intent_decision(answer.output))


class LocalCompanionRunner:
    """Every action crosses RunEngine, perform_run, native Graph and event ledger."""

    def __init__(
        self,
        service: CompanionService,
        bridge: CompanionBridge,
        *,
        intent_profile: CompanionIntentProfile | None = None,
    ) -> None:
        """Bind one native service and its exact physical effect owner."""
        if service.bridge is not bridge:
            msg = "Runner requires the exact companion service bridge."
            raise ValueError(msg)
        self.service, self.bridge = service, bridge
        self.queue = LocalRunQueue()
        self.services: AltarServices | None = None
        self.active_run: str | None = None
        self.intent_profile = None if intent_profile is None else revalidate_intent_profile(intent_profile)
        self.interpreter = (
            None if self.intent_profile is None else NativeCompanionInterpreter(self.intent_profile, service)
        )

    async def open(self) -> None:
        try:
            get_run_substrate()
        except RuntimeError:
            pass
        else:
            msg = "Local companion requires an unpublished process Run substrate."
            raise RuntimeError(msg)
        workflow = companion_workflow(self.service, self.interpreter)
        settings = SettingsSnapshot(
            payload='{"server":{"database":{"profile":"memory"}},"extensions":{"builtins":[],"crypt":[]}}'
        ).materialize()
        context = ExtensionContext()
        runes: tuple[VllmSoulstoneConfig, ...] = ()
        if self.intent_profile is not None:
            profile = self.intent_profile
            register(context.registration_view("builtin:animator/vllm"))
            runes = (
                VllmSoulstoneConfig(
                    name="companion-intent",
                    base_url=profile.base_url,  # pyright: ignore[reportArgumentType] - explicit profile and Rune both validate
                    port=urlsplit(profile.base_url).port,
                    served_model_id=profile.model_id,
                    concurrency=ConcurrencyIntent(dedicated=False),
                    generation=GenerationProfile(
                        max_context=profile.context_tokens, max_tokens=profile.max_tokens, temperature=0
                    ),
                ),
            )
        context.freeze()
        services = build_altar_services(
            queues={"runs": self.queue, "rites": self.queue},
            runes=RuneRegistry(runes),
            soulstone_registrations=context.soulstones.registrations,
            settings=settings,
            workflows=BuiltinWorkflowRegistry(workflows=(workflow,), default_name=workflow.name),
            profile="memory",
            runtime_actuator=RefuseHostTransitions(),
            soft_activation_guard=RefuseHostTransitions(),
        )
        services.substrate.effects = self.bridge
        services.run_engine.effects = self.bridge
        services.registry.ensure_loaded()
        if self.intent_profile is not None:
            services.substrate.forge.register("companion-intent", lambda spec: build_agent(spec, toolset_factories={}))
        self.services = services
        set_run_substrate(services.substrate)

    async def submit(self, request: CompanionInput) -> str:
        """Carry only capabilities selected by the immutable session policy into admission."""
        services = self.services
        if services is None:
            msg = "Local companion runner is closed."
            raise RuntimeError(msg)
        scopes = {"blockworld:companion"}
        if self.service.policy.allow_weather:
            scopes.add("blockworld:weather")
        if self.service.policy.allow_time:
            scopes.add("blockworld:time")

        async def retain(run_id: str) -> None:
            self.active_run = run_id
            if request.generation != self.bridge.epoch or self.bridge.paused:
                self.bridge.fence(run_id, "stop_during_admission")

        handle = await services.run_engine.submit(
            Intent(
                session_id=self.service.policy.session_id,
                prompt=request.model_dump_json(),
                source="blockworld.companion",
                sigil_name=self.service.policy.principal,
                sigil_scopes=frozenset(scopes),
            ),
            retain_before_publish=retain,
            idempotency_key=f"companion:{self.service.policy.session_id}:{request.request_id}",
            exclusive_session=True,
        )
        self.active_run = handle.run_id
        return handle.run_id

    async def wait(self, run_id: str) -> dict[str, Any]:
        services = self.services
        if services is None:
            msg = "Local companion runner is closed."
            raise RuntimeError(msg)
        jobs = [job for job in self.queue.jobs.values() if job.run_id == run_id]
        if len(jobs) != 1 or jobs[0].task is None:
            msg = "Expected one exact local native delivery."
            raise RuntimeError(msg)
        result = await asyncio.shield(jobs[0].task)
        await services.bus.wait_persisted(run_id)
        if self.active_run == run_id:
            self.active_run = None
        return result

    async def cancel(self) -> None:
        if self.services is not None and self.active_run is not None:
            run_id = self.active_run
            await self.services.run_engine.cancel(run_id)
            if self.active_run == run_id:
                self.active_run = None

    async def aclose(self) -> None:
        try:
            await self.cancel()
            await self.bridge.aclose()
        finally:
            await self.queue.close()
            if self.services is not None:
                reset_run_substrate()
                await self.services.aclose()
                self.services = None


@dataclass(frozen=True)
class SessionResult:
    """A game disposition snapshot; session outcomes retain later receipt settlement."""

    request_id: str
    run_id: str | None
    kind: str
    detail: str
    result: CompanionResult | None = None
    evidence_status: Literal["not_requested", "pending", "recorded", "failed"] = "not_requested"
    reason: CompanionReason | None = None


@dataclass
class PendingCommand:
    request: CompanionInput
    captured_generation: int
    expires_at: float
    future: asyncio.Future[SessionResult]


type CompanionCommandPhase = Literal["queued", "admission_pending", "response_pending", "settling"]


@dataclass(frozen=True)
class CompanionCommandStatus:
    """One retained slot, not proof of an effect or a terminal disposition."""

    request_id: str
    run_id: str | None
    phase: CompanionCommandPhase
    remaining_ms: int
    original_deadline_ms: int | None


@dataclass(frozen=True)
class CompanionSessionStatus:
    """Process-local owner observation; closed means admission closed, not retirement."""

    observed_at_ms: int
    opened: bool
    closed: bool
    stopping: bool
    fenced: bool
    generation: int
    capacity: int
    actor_id: str
    current: CompanionCommandStatus | None
    pending: tuple[CompanionCommandStatus, ...]
    pending_evidence: int


class CompanionSession:
    """One active Run, a finite expiring FIFO, and synchronous stop fencing.

    Idle is one explicit finite server goal, never a background tick producer.
    Stop permits later fresh commands after its server barrier and command receipts settle.
    Early queue dispositions resolve synchronously; ``outcomes`` retains their settled
    evidence status even when the caller cancels its result future.
    """

    def __init__(
        self,
        runner: LocalCompanionRunner,
        bridge: CompanionBridge,
        *,
        capacity: int = MAX_QUEUE,
        max_age_s: float = 15.0,
        record: RecordSink | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a finite volatile FIFO without starting native work."""
        if runner.bridge is not bridge or not 1 <= capacity <= MAX_QUEUE or not 0 < max_age_s <= 60:  # noqa: PLR2004 - finite command age
            msg = "Session collaborators, queue capacity or finite age are invalid."
            raise ValueError(msg)
        self.runner, self.bridge = runner, bridge
        self.capacity, self.max_age_s, self.record, self.clock = capacity, max_age_s, record, clock
        self.run_ids: dict[str, str] = {}
        self.outcomes: dict[str, SessionResult] = {}
        self._pending: deque[PendingCommand] = deque()
        self._retained: dict[str, tuple[bytes, asyncio.Future[SessionResult]]] = {}
        self._worker: asyncio.Task[None] | None = None
        self._admission: asyncio.Task[str] | None = None
        self._current: PendingCommand | None = None
        self._stop_task: asyncio.Task[CompanionResult] | None = None
        self._publications: dict[str, asyncio.Task[SessionResult]] = {}
        self._closed = False
        self._opened = False

    async def open(self) -> None:
        if self._opened or self._closed:
            msg = "Companion session already opened or closed."
            raise RuntimeError(msg)
        if self.bridge.state is None:
            await self.bridge.open()
        if self.runner.services is None:
            await self.runner.open()
        self._opened = True

    def capture_generation(self) -> int:
        """Capture before microphone/file transcription starts, never afterwards."""
        return self.bridge.epoch

    def snapshot(self) -> CompanionSessionStatus:
        """Read bounded owner state without expiring, admitting, polling or settling work."""
        now = self.clock()

        def status(
            command: PendingCommand,
            phase: CompanionCommandPhase,
        ) -> CompanionCommandStatus:
            return CompanionCommandStatus(
                request_id=command.request.request_id,
                run_id=self.run_ids.get(command.request.request_id),
                phase=phase,
                remaining_ms=max(0, ceil((command.expires_at - now) * 1000)),
                original_deadline_ms=command.request.expires_at_ms,
            )

        current = self._current
        phase: CompanionCommandPhase = (
            "settling"
            if current is not None and current.request.request_id in self.outcomes
            else (
                "response_pending"
                if current is not None and current.request.request_id in self.run_ids
                else "admission_pending"
            )
        )
        return CompanionSessionStatus(
            observed_at_ms=int(time.time() * 1000),
            opened=self._opened,
            closed=self._closed,
            stopping=self._stop_task is not None and not self._stop_task.done(),
            fenced=self.bridge.paused,
            generation=self.bridge.epoch,
            capacity=self.capacity,
            actor_id=self.bridge.binding.actor_id,
            current=None if current is None else status(current, phase),
            pending=tuple(status(command, "queued") for command in self._pending),
            pending_evidence=sum(
                not task.done() and self.outcomes[identity].evidence_status == "pending"
                for identity, task in self._publications.items()
            ),
        )

    def _resolve(self, command: PendingCommand, result: SessionResult) -> None:
        if not command.future.done():
            command.future.set_result(result)

    def _expire(self) -> None:
        while self._pending and self._pending[0].expires_at <= self.clock():
            command = self._pending.popleft()
            self._complete(
                command,
                SessionResult(
                    command.request.request_id,
                    None,
                    "expired",
                    "Command expired before native admission.",
                    reason="expired_before_execution",
                ),
                resolve_now=True,
            )

    def enqueue(
        self, request: CompanionInput, *, captured_generation: int | None = None
    ) -> asyncio.Future[SessionResult]:
        """Admit synchronously; repeated identical identities share one result future."""
        if not self._opened or self._closed:
            msg = "Companion session is not open."
            raise ValueError(msg)
        generation = request.generation if captured_generation is None else captured_generation
        if isinstance(request, CompanionInstruction) and generation != request.generation:
            msg = "Original instruction generation cannot change."
            raise ValueError(msg)
        admitted = request.model_dump(mode="python", warnings=False)
        admitted["generation"] = generation
        request = (
            CompanionInstruction.model_validate(admitted)
            if isinstance(request, CompanionInstruction)
            else CompanionRequest.model_validate(admitted)
        )
        document = request.model_dump_json().encode()
        strict_json(document)
        retained = self._retained.get(request.request_id)
        if retained is not None:
            if retained[0] != document:
                msg = "Request identity reused with changed content."
                raise ValueError(msg)
            return retained[1]
        if (
            generation != self.bridge.epoch
            or self.bridge.paused
            or (self._stop_task is not None and not self._stop_task.done())
        ):
            msg = "Captured instruction predates stop or stop remains unsettled."
            raise ValueError(msg)
        self._expire()
        if len(self._pending) >= self.capacity or len(self._retained) >= min(
            MAX_ACTIONS, self.runner.service.policy.max_actions
        ):
            msg = "Finite command FIFO or retained request budget is full."
            raise ValueError(msg)
        future: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
        remaining = self.max_age_s
        if request.expires_at_ms is not None:
            remaining = min(remaining, max(0, request.expires_at_ms / 1000 - time.time()))
        command = PendingCommand(request, generation, self.clock() + remaining, future)
        self._retained[request.request_id] = document, future
        self._pending.append(command)
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._drain(), name="companion-operator-fifo")
        return future

    async def _publish(self, outcome: SessionResult) -> None:
        if self.record is None:
            return
        document: dict[str, Any] = {
            "request_id": outcome.request_id,
            "run_id": outcome.run_id,
            "kind": outcome.kind,
            "detail": outcome.detail,
            "reason": outcome.reason,
            "result": None if outcome.result is None else outcome.result.model_dump(mode="json"),
            "input": json.loads(self._retained[outcome.request_id][0]),
        }
        services = self.runner.services
        if services is not None and outcome.run_id is not None:
            document["events"] = [
                event.model_dump(mode="json") for event in await services.ledger.list_events(outcome.run_id)
            ]
        await self.record(document)

    def _complete(
        self, command: PendingCommand, outcome: SessionResult, *, resolve_now: bool = False
    ) -> asyncio.Task[SessionResult]:
        """Retain one owned publication per admitted identity, independent of its caller."""
        previous = self._publications.get(outcome.request_id)
        if previous is not None:
            return previous
        outcome = replace(outcome, evidence_status="pending" if self.record is not None else "not_requested")
        self.outcomes[outcome.request_id] = outcome
        if resolve_now:
            self._resolve(command, outcome)
        task = asyncio.create_task(self._settle_outcome(command, outcome), name="companion-command-receipt")
        self._publications[outcome.request_id] = task
        return task

    async def _settle_outcome(self, command: PendingCommand, outcome: SessionResult) -> SessionResult:
        try:
            await self._publish(outcome)
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - custody failure cannot erase the game disposition
            outcome = replace(outcome, evidence_status="failed")
        else:
            outcome = replace(outcome, evidence_status="recorded" if self.record is not None else "not_requested")
        self.outcomes[outcome.request_id] = outcome
        self._resolve(command, outcome)
        return outcome

    async def _join_publications(self) -> None:
        if self._publications:
            await complete_under_cancellation(asyncio.gather(*self._publications.values()))

    async def _drive(self, command: PendingCommand) -> SessionResult:
        request_id = command.request.request_id
        if command.expires_at <= self.clock():
            return SessionResult(
                request_id,
                None,
                "expired",
                "Command expired before native admission.",
                reason="expired_before_execution",
            )
        if command.captured_generation != self.bridge.epoch or self.bridge.paused:
            return SessionResult(
                request_id,
                None,
                "cancelled",
                "Stop fenced the queued command.",
                reason="cancelled_before_execution",
            )
        self._admission = asyncio.create_task(self.runner.submit(command.request), name="companion-native-admission")
        run_id = await asyncio.shield(self._admission)
        self.run_ids[command.request.request_id] = run_id
        if command.captured_generation != self.bridge.epoch:
            await self.runner.cancel()
            return SessionResult(request_id, run_id, "cancelled", "Stop overtook native admission.")
        await self.runner.wait(run_id)
        result = self.runner.service.run_results.get(run_id)
        if result is None:
            return SessionResult(request_id, run_id, "unknown", "Native Run ended without an action receipt.")
        return SessionResult(request_id, run_id, result.kind, result.detail, result, reason=result.reason)

    async def _drain(self) -> None:
        while self._pending and not self._closed:
            self._expire()
            if not self._pending:
                return
            command = self._pending.popleft()
            self._current = command
            try:
                outcome = await self._drive(command)
            except asyncio.CancelledError:
                outcome = SessionResult(
                    command.request.request_id,
                    self.run_ids.get(command.request.request_id),
                    "cancelled",
                    "Native command interrupted; server stop owns containment.",
                )
            except Exception:  # noqa: BLE001 - every admitted future must receive an honest terminal disposition
                outcome = SessionResult(
                    command.request.request_id,
                    self.run_ids.get(command.request.request_id),
                    "unknown",
                    "Native command failed; no action completion is claimed.",
                )
            await complete_under_cancellation(self._complete(command, outcome))
            self._current = None
            self._admission = None

    def stop(self) -> Coroutine[Any, Any, CompanionResult]:
        """Advance the capture fence and drain the FIFO before returning an awaitable."""
        if self._stop_task is None or self._stop_task.done():
            priority = self.bridge.begin_stop(run_id=self.runner.active_run)
            while self._pending:
                command = self._pending.popleft()
                self._complete(
                    command,
                    SessionResult(
                        command.request.request_id,
                        None,
                        "cancelled",
                        "Priority stop cleared the queued command.",
                        reason="cancelled_before_execution",
                    ),
                    resolve_now=True,
                )
            self._stop_task = asyncio.create_task(self._settle_stop(priority), name="companion-stop-settlement")
        return complete_under_cancellation(self._stop_task)

    async def _settle_stop(self, priority: asyncio.Task[CompanionResult]) -> CompanionResult:
        admission = self._admission
        if admission is not None:
            await asyncio.gather(asyncio.shield(admission), return_exceptions=True)
        cancellation = await asyncio.gather(self.runner.cancel(), return_exceptions=True)
        try:
            result = await complete_under_cancellation(priority)
        finally:
            worker = self._worker
            if worker is not None and worker is not asyncio.current_task():
                await asyncio.gather(asyncio.shield(worker), return_exceptions=True)
            await self._join_publications()
        if any(isinstance(item, BaseException) for item in cancellation):
            return CompanionResult(
                request_id=result.request_id,
                kind="unknown",
                detail="Server stop or native cancellation settlement remains unknown.",
            )
        if any(outcome.evidence_status == "failed" for outcome in self.outcomes.values()):
            return result.model_copy(
                update={"detail": f"{result.detail} Private command evidence publication failed."[:300]}
            )
        return result

    async def aclose(self) -> None:
        self._closed = True
        try:
            if self._opened:
                await self.stop()
        finally:
            try:
                await self._join_publications()
            finally:
                await self.runner.aclose()
                self._opened = False
