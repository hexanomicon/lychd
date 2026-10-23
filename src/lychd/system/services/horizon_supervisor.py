"""Finite process-local arbitration for explicit Horizon operator and behavior Runs.

Timers are volatile and never claim durable Graph waits or restart recovery.
One native Run owns the action slot until its effect disposition is classified.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lychd.compositions.blockworld.horizon_assist import AssistRequest
from lychd.compositions.blockworld.horizon_assist_runtime import BehaviorAdmissionRefused, LocalAssistRunner
from lychd.compositions.blockworld.horizon_behaviors import BehaviorDirective, HorizonBehaviorService
from lychd.compositions.blockworld.horizon_build import BuildPlan, BuildStep, HorizonBuildService
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.horizon_control import HorizonControlError, HorizonControlSession

type RecordSink = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class SupervisorResult:
    run_id: str | None
    kind: str
    detail: str


class HorizonSupervisor:
    """One session-ending stop, one action slot and no queued tick backlog."""

    def __init__(
        self,
        runner: LocalAssistRunner,
        control: HorizonControlSession,
        *,
        behaviors: HorizonBehaviorService | None = None,
        record: RecordSink | None = None,
    ) -> None:
        """Bind the exact shared service assembly without starting any work."""
        if runner.control is not control or (behaviors is not None and behaviors.assist is not runner.assist):
            msg = "Supervisor requires one shared control and assist service."
            raise ValueError(msg)
        self.runner, self.control, self.behaviors, self.record = runner, control, behaviors, record
        self.builds: HorizonBuildService | None = runner.builds
        self.stopped = asyncio.Event()
        self.metrics = {"runs": 0, "ticks": 0, "build_steps": 0, "coalesced": 0, "skipped": 0, "model_calls": 0}
        self._epoch = 0
        self._commands = asyncio.Lock()
        self._slot = asyncio.Lock()
        self._loop: asyncio.Task[None] | None = None
        self._tick: asyncio.Task[SupervisorResult] | None = None
        self._operator: asyncio.Task[Any] | None = None
        self._run_id: str | None = None
        self._last_tick = float("-inf")
        self.run_ids: dict[str, str] = {}

    def _require_open(self) -> None:
        if self.stopped.is_set():
            msg = "Horizon controller is permanently stopped."
            raise ValueError(msg)

    def interrupt_behavior(self, reason: str = "operator_priority") -> int:
        """Invalidate old authority before any await, including admission's gap."""
        self._epoch += 1
        if self.behaviors is not None:
            self.behaviors.fence(reason)
        if self.builds is not None:
            self.builds.fence(reason)
        current = asyncio.current_task()
        for task in (self._loop, self._tick):
            if task is self._loop and current is self._tick:
                # An internally disarmed tick still owns settlement/publication.
                # Its parent must observe that result or exception, not cancel
                # itself while shielded from this very child.
                continue
            if task is not None and task is not current and not task.done():
                task.cancel()
        if self._run_id is not None and self._operator is None:
            self.control.fence(self._run_id, reason)
        return self._epoch

    def fence(self, reason: str = "session_stopped") -> None:
        """Permanently refuse all sends before scheduling asynchronous settlement."""
        self.stopped.set()
        self.interrupt_behavior(reason)
        self.control.fence_all(reason)
        if self._operator is not None and self._operator is not asyncio.current_task():
            self._operator.cancel()

    async def _join_behaviors(self) -> None:
        tasks: list[asyncio.Task[Any]] = [
            task for task in (self._loop, self._tick) if task is not None and task is not asyncio.current_task()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self._loop = None
        self._tick = None
        for result in results:
            if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                self.fence("behavior_settlement_failed")
                msg = "Behavior settlement failed; controller disarmed."
                raise RuntimeError(msg) from result  # noqa: TRY004 - child task failure, not an invalid argument type

    async def pause(self) -> None:
        """Settle interrupted behavior before capture or a new operator passage."""
        self.interrupt_behavior()
        async with self._commands:
            await self._join_behaviors()
            self._require_open()

    async def start(self, directive: BehaviorDirective) -> None:
        """Replace a finite directive only after the prior effect has settled."""
        self._require_open()
        if self.behaviors is None or self._operator is not None:
            msg = "Behavior profile unavailable or operator passage reserved."
            raise ValueError(msg)
        epoch = self.interrupt_behavior("behavior_replaced")
        async with self._commands:
            await self._join_behaviors()
            self._require_open()
            if epoch != self._epoch or self._operator is not None:
                msg = "Behavior replacement superseded before admission."
                raise ValueError(msg)
            self.behaviors.begin(directive)
            self._last_tick = float("-inf")
            self._loop = asyncio.create_task(self._schedule(epoch), name="horizon-behavior-cadence")

    async def _schedule(self, epoch: int) -> None:
        service = self.behaviors
        if service is None:
            return
        while not self.stopped.is_set() and epoch == self._epoch and service.directive is not None:
            await self.tick_once()
            pause_s = min(service.policy.cadence_s, max(0.0, service.deadline - service.clock()))
            if pause_s <= 0:
                break
            # Always schedule from now: a slow tick creates no catch-up backlog.
            await asyncio.sleep(pause_s)

    async def start_build(self, plan: BuildPlan) -> None:
        """Replace background work with one finite, explicitly supplied cell plan."""
        self._require_open()
        if self.builds is None or self._operator is not None:
            msg = "Build profile unavailable or operator passage reserved."
            raise ValueError(msg)
        epoch = self.interrupt_behavior("build_replaced")
        async with self._commands:
            await self._join_behaviors()
            self._require_open()
            if epoch != self._epoch or self._operator is not None:
                msg = "Build replacement superseded before admission."
                raise ValueError(msg)
            self.builds.begin(plan)
            self._loop = asyncio.create_task(self._schedule_build(epoch), name="horizon-build-plan")

    async def _schedule_build(self, epoch: int) -> None:
        service = self.builds
        if service is None:
            return
        while not self.stopped.is_set() and epoch == self._epoch and service.plan is not None:
            if service.cursor == len(service.plan.cells):
                service.fence("completed")
                break
            self._tick = asyncio.create_task(self._build_step(epoch), name="horizon-build-step")
            result = await asyncio.shield(self._tick)
            if result.kind != "placed":
                break

    async def _drive_build(self, service: HorizonBuildService, step: BuildStep) -> SupervisorResult:
        try:
            run_id = await self._drive(
                lambda: self.runner.submit_build(step),
                time.monotonic() + max(0.0, service.deadline - service.clock()),
                step.request_id,
            )
        except TimeoutError:
            service.fence("build_deadline")
            return SupervisorResult(self.run_ids.get(step.request_id), "expired", "Cell deadline settled.")
        except BehaviorAdmissionRefused:
            service.fence("build_admission_refused")
            return SupervisorResult(None, "refused", "Cell refused before native admission.")
        observed = service.run_results.get(run_id)
        if observed is None or observed.kind == "outcome_unknown":
            return await self._unknown(run_id, "Cell has no known physical disposition.")
        self._run_id = None
        if observed.stop_required:
            service.fence(observed.kind)
        return SupervisorResult(run_id, observed.kind, observed.detail)

    async def _build_step(self, epoch: int) -> SupervisorResult:
        service = self.builds
        if service is None:
            msg = "No build profile was bound."
            raise RuntimeError(msg)
        started, cpu_started = time.monotonic(), time.process_time()
        async with self._slot:
            if self.stopped.is_set() or epoch != self._epoch or self._operator is not None:
                return SupervisorResult(None, "skipped", "Cell superseded before admission.")
            try:
                step = service.new_step()
            except ValueError:
                service.fence("build_budget_or_deadline")
                result = SupervisorResult(None, "refused", "Build budget or deadline exhausted.")
                await self._publish_owned(result, "build", started, cpu_started)
                return result
            self.metrics["build_steps"] += 1
            try:
                try:
                    result = await self._drive_build(service, step)
                except asyncio.CancelledError:
                    result = SupervisorResult(
                        self.run_ids.get(step.request_id), "cancelled", "Cell interrupted; settled."
                    )
                    publishing = asyncio.create_task(self._publish_owned(result, "build", started, cpu_started))
                    await complete_under_cancellation(publishing)
                    raise
                await self._publish_owned(result, "build", started, cpu_started)
            except BaseException:
                # Report may already have advanced the cursor before native DONE.
                # Failure/cancellation never grants the next cell permission.
                if epoch == self._epoch:
                    service.fence("build_interrupted")
                raise
            return result

    async def wait_behavior(self) -> None:
        """Join the current finite cadence task without inventing a durable wait."""
        loop = self._loop
        if loop is not None:
            await asyncio.shield(loop)

    async def tick_once(self) -> SupervisorResult:
        """Join an in-flight tick or skip; never retain a queue of obsolete poses."""
        service = self.behaviors
        if self.stopped.is_set() or service is None or service.directive is None or self._operator is not None:
            self.metrics["skipped"] += 1
            return SupervisorResult(None, "skipped", "No eligible behavior authority.")
        if self._tick is not None and not self._tick.done():
            self.metrics["coalesced"] += 1
            return await asyncio.shield(self._tick)
        if service.clock() - self._last_tick < service.policy.cadence_s:
            self.metrics["skipped"] += 1
            return SupervisorResult(None, "skipped", "Cadence has not elapsed.")
        self._last_tick = service.clock()
        self._tick = asyncio.create_task(self._behavior_tick(self._epoch), name="horizon-behavior-tick")
        return await asyncio.shield(self._tick)

    async def _settle(self, run_id: str) -> None:
        self.control.fence(run_id, "supervisor_settlement")
        try:
            await self.runner.cancel()
        finally:
            # A DONE native Run may still retain an uncertain physical command.
            await self.control.contain(run_id)

    async def _drive(self, submit: Callable[[], Coroutine[Any, Any, str]], deadline: float, identity: str) -> str:
        admission = asyncio.create_task(submit(), name="horizon-supervisor-admission")
        run_id: str | None = None
        try:
            async with asyncio.timeout(max(0.0, deadline - time.monotonic())):
                try:
                    admitted = await asyncio.shield(admission)
                except asyncio.CancelledError:
                    try:
                        run_id = await complete_under_cancellation(admission)
                    except BehaviorAdmissionRefused:
                        # The guard refused before RunEngine admission; there is
                        # no native Run or physical attempt to settle.
                        raise asyncio.CancelledError from None
                    raise
                run_id = admitted
                self._run_id = run_id
                self.run_ids[identity] = run_id
                self.metrics["runs"] += 1
                delivery = await self.runner.wait(run_id)
                if delivery.get("status") != "done":
                    self.fence("native_delivery_not_done")
                    msg = "Native delivery did not reach DONE; controller disarmed."
                    raise HorizonControlError(msg)  # noqa: TRY301 - exact Run custody must pass through settlement
        except BaseException as exc:
            if run_id is not None:
                self._run_id = run_id
                self.run_ids[identity] = run_id
                settling = asyncio.create_task(self._settle(run_id))
                try:
                    await complete_under_cancellation(settling)
                except BaseException:
                    self.fence("effect_settlement_unknown")
                    raise
                self._run_id = None
            elif not isinstance(exc, (asyncio.CancelledError, BehaviorAdmissionRefused)):
                self.fence("admission_outcome_unknown")
                settling = asyncio.create_task(self._settle_unidentified())
                await complete_under_cancellation(settling)
            raise
        else:
            return admitted

    async def _settle_unidentified(self) -> None:
        try:
            await self.control.contain_all()
        finally:
            await self.runner.queue.close()

    async def _publish(self, result: SupervisorResult, source: str, started: float, cpu_started: float) -> None:
        if self.record is not None:
            await self.record(
                {
                    "source": source,
                    "run_id": result.run_id,
                    "kind": result.kind,
                    "detail": result.detail,
                    "elapsed_s": time.monotonic() - started,
                    "process_cpu_s": time.process_time() - cpu_started,
                    "metrics": dict(self.metrics),
                    "action_attempts": self.runner.assist.used,
                    "observation_calls": self.behaviors.observation_count if self.behaviors is not None else 0,
                    "build_read_calls": self.builds.read_count if self.builds is not None else 0,
                    "control_query_lines": self.control.query_count,
                    "model_calls": 0,
                    "delivery": "experimental_process_local",
                }
            )

    async def _publish_owned(self, result: SupervisorResult, source: str, started: float, cpu_started: float) -> None:
        async def finite_record() -> None:
            async with asyncio.timeout(5):
                await self._publish(result, source, started, cpu_started)

        publishing = asyncio.create_task(finite_record(), name="horizon-behavior-evidence")
        try:
            try:
                await asyncio.shield(publishing)
            except asyncio.CancelledError:
                await complete_under_cancellation(publishing)
                raise
        except asyncio.CancelledError:
            raise
        except BaseException:
            self.fence("behavior_evidence_failed")
            raise

    async def _unknown(self, run_id: str, detail: str) -> SupervisorResult:
        self.fence("effect_outcome_unknown")
        settling = asyncio.create_task(self.control.contain(run_id))
        await complete_under_cancellation(settling)
        self._run_id = None
        return SupervisorResult(run_id, "outcome_unknown", detail)

    async def _behavior_result(self, service: HorizonBehaviorService, run_id: str, request_id: str) -> SupervisorResult:
        observed = service.results.get(request_id)
        if observed is None or observed.kind == "outcome_unknown":
            return await self._unknown(run_id, "Tick has no known physical disposition.")
        if observed.stop_required:
            service.fence("behavior_observation_refused")
        self._run_id = None
        return SupervisorResult(run_id, observed.kind, observed.detail)

    async def _behavior_tick(self, epoch: int) -> SupervisorResult:
        service = self.behaviors
        if service is None:
            msg = "No behavior profile was bound."
            raise RuntimeError(msg)
        started, cpu_started = time.monotonic(), time.process_time()
        async with self._slot:
            if self.stopped.is_set() or epoch != self._epoch or self._operator is not None:
                return SupervisorResult(None, "skipped", "Tick superseded before admission.")
            try:
                tick = service.new_tick()
            except ValueError:
                service.fence("behavior_budget_or_deadline")
                return SupervisorResult(None, "refused", "Behavior budget or deadline exhausted.")
            self.metrics["ticks"] += 1
            # Conservatively expire the entire follow tick from its start; this
            # also bounds reads before the sample-specific prewrite guard exists.
            remaining = service.deadline - service.clock()
            if tick.kind == "follow":
                remaining = min(remaining, service.policy.freshness_s)
            try:
                run_id = await self._drive(
                    lambda: self.runner.submit_behavior(tick), time.monotonic() + remaining, tick.request_id
                )
            except TimeoutError:
                service.fence("behavior_deadline")
                result = SupervisorResult(
                    self.run_ids.get(tick.request_id), "expired", "Tick deadline reached; settled."
                )
            except BehaviorAdmissionRefused:
                service.fence("behavior_admission_refused")
                result = SupervisorResult(None, "refused", "Behavior refused before native admission.")
            except asyncio.CancelledError:
                result = SupervisorResult(self.run_ids.get(tick.request_id), "cancelled", "Tick interrupted; settled.")
                publishing = asyncio.create_task(self._publish_owned(result, tick.kind, started, cpu_started))
                await complete_under_cancellation(publishing)
                raise
            else:
                result = await self._behavior_result(service, run_id, tick.request_id)
            await self._publish_owned(result, tick.kind, started, cpu_started)
            return result

    async def submit_operator(self, request: AssistRequest) -> SupervisorResult:
        """Reserve priority, settle behavior, then finish one native operator Run."""
        self._require_open()
        if self._operator is not None:
            msg = "An operator passage is already reserved."
            raise ValueError(msg)
        self.interrupt_behavior()
        self._operator = asyncio.current_task()
        started, cpu_started = time.monotonic(), time.process_time()
        try:
            async with self._commands:
                await self._join_behaviors()
                self._require_open()
                async with self._slot:
                    remaining = (self.runner.assist.policy.expires_at - datetime.now(UTC)).total_seconds()
                    run_id = await self._drive(
                        lambda: self.runner.submit(request), time.monotonic() + remaining, request.request_id
                    )
                    observed = self.runner.assist.run_results.get(run_id)
                    if observed is None or observed.kind == "outcome_unknown":
                        result = await self._unknown(run_id, "Operator Run has no known physical disposition.")
                    else:
                        result = SupervisorResult(run_id, observed.kind, observed.detail)
                        self._run_id = None
                    await self._publish_owned(result, "operator", started, cpu_started)
                    return result
        finally:
            self._operator = None

    async def stop(self) -> None:
        """Join all owned tasks and explicitly contain even a terminal native Run."""
        self.fence()
        operator = self._operator
        try:
            if operator is not None and operator is not asyncio.current_task():
                await asyncio.gather(operator, return_exceptions=True)
            await self._join_behaviors()
        finally:
            if self._run_id is not None:
                settling = asyncio.create_task(self._settle(self._run_id))
                await complete_under_cancellation(settling)
                self._run_id = None
