from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilitySpec,
)
from lychd.domain.animation.errors import ActivationTimeout, HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.cortex.priority import validate_priority
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationNoEffectError,
    RuntimeCancellationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.domain.orchestration.arbiter import TransitionArbiter, TransitionDeclined
from lychd.domain.orchestration.journal import TransitionJournal, notify_transition
from lychd.domain.orchestration.schema import TransitionPlan, TransitionTrace
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lychd.config.settings.orchestration import SwitchingSettings
    from lychd.domain.cortex.leases import LeaseLedger
    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.actuator import RuntimeActuator
    from lychd.domain.orchestration.policies import SwitchPolicy
    from lychd.domain.orchestration.schema import TransitionPhase

__all__ = ["OrchestratorManager", "TransitionDeclined"]


class OrchestratorManager:
    """Plan and execute local runtime transitions from the canonical registry."""

    def __init__(
        self,
        worker_broker: Any,
        registry: CapabilityRegistry,
        *,
        leases: LeaseLedger,
        policy: SwitchPolicy,
        arbiter: TransitionArbiter,
        actuator: RuntimeActuator,
        switching: SwitchingSettings,
        transitions: TransitionJournal | None = None,
    ) -> None:
        """Initialize orchestration against the injected registry, leases, and policy.

        ``worker_broker`` is fully queue-bound at composition time. Production uses
        ``GhoulBroker``; focused manager tests may inject a protocol-compatible fake.
        """
        self.worker_broker = worker_broker
        self.registry = registry
        self._leases = leases
        self._policy = policy
        self._arbiter = arbiter
        self._actuator = actuator
        self._switching = switching
        self.transitions = transitions or TransitionJournal()
        self._contained_reason: str | None = None

    def _publish(
        self,
        trace: TransitionTrace,
        phase: TransitionPhase,
        *,
        detail: str | None = None,
    ) -> None:
        """Acknowledge one semantic phase to the shared journal and optional Run sink."""
        trace.phase = phase
        if detail is not None:
            trace.detail = detail
        record = self.transitions.record(trace)
        notify_transition(record, trace.observer)

    @property
    def containment_reason(self) -> str | None:
        """Explain a fail-closed physical-world containment, when active."""
        return self._contained_reason

    def list_capability_statuses(self) -> list[dict[str, Any]]:
        """Return a canonical status snapshot for the orchestrator API."""
        items: list[dict[str, Any]] = []
        for spec in sorted(self.registry.list_capabilities(), key=lambda item: item.key):
            state = self.registry.get_capability_state(spec.key)
            if state is None:
                continue
            items.append(
                {
                    "capability_key": spec.key,
                    "animator_name": spec.animator_name,
                    "family": spec.family,
                    "runtime": spec.runtime,
                    "source_kind": spec.source_kind,
                    "is_dynamic": spec.is_dynamic,
                    "phase": state.phase.value,
                    "model_id": spec.model_id,
                    "is_static": not spec.is_dynamic,
                    "is_active": state.is_active,
                    "is_available": state.is_available,
                    "warm": state.warm,
                    "health": state.health,
                    "reason": state.reason,
                    "checked_at": state.checked_at,
                    "dedicated": spec.concurrency.dedicated,
                    "persistent_resident": spec.concurrency.persistent_resident,
                }
            )
        return items

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan:
        """Calculate from fresh managed-runtime observations under one planning deadline."""
        # A target-only refresh is insufficient: persistent residents start in
        # parallel at boot and an operator may also start a managed unit outside
        # this process.  Policy and the host stale-world fence must therefore see
        # the same current peer set. The registry serializes probes under one lock,
        # so refresh deterministically instead of creating fake parallel tasks.
        planning_deadline = asyncio.timeout(self._switching.planning_timeout_s)
        try:
            async with planning_deadline:
                await self._refresh_lifecycle_managed_animators()
        except TimeoutError as exc:
            if not planning_deadline.expired():
                raise
            msg = f"Transition planning for '{target_capability_key}' exceeded the planning deadline."
            raise RuntimePreconditionError(msg) from exc
        target = self.registry.get_capability(target_capability_key)
        if target is None:
            msg = f"Unknown capability: {target_capability_key}"
            raise ValueError(msg)
        target_state = self.registry.get_capability_state(target_capability_key)
        if target_state is None:
            msg = f"Capability state is unavailable for '{target_capability_key}'."
            raise ValueError(msg)

        if target_state.warm:
            return TransitionPlan(
                total_metabolic_cost=0.0,
                evict_coven_ids=[],
                launch_coven_ids=[],
                action_type="NO_OP",
            )

        if not target.concurrency.dedicated:
            msg = (
                f"Capability '{target.key}' is provided by shared animator '{target.animator_name}' "
                "and cannot be lifecycle-managed by the orchestrator."
            )
            raise RuntimeError(msg)

        if self._is_animator_runtime_started(target.animator_name):
            return TransitionPlan(
                total_metabolic_cost=0.0,
                evict_coven_ids=[],
                launch_coven_ids=[],
                action_type="SOFT_SWAP",
            )

        decision = self._policy.solve(target, self.registry)
        return TransitionPlan(
            total_metabolic_cost=decision.metabolic_cost,
            evict_coven_ids=decision.evict_animator_names,
            launch_coven_ids=decision.launch_animator_names,
            action_type="HARD_SWAP",
            policy=self._policy.name,
        )

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: Priority,
        *,
        trace: TransitionTrace | None = None,
    ) -> None:
        """Converge the requested capability; propagate priority or readiness failure."""
        await self.request_transition(exception.capability_key, signal_priority, trace=trace)

    async def request_transition(
        self,
        target_capability_key: str,
        priority: Priority,
        *,
        trace: TransitionTrace | None = None,
    ) -> TransitionPlan:
        """Converge on WARM, coalescing same-capability, same-priority requests.

        Warm/open preflight bypasses physical arbitration. All other plans refresh
        inside the arbiter; only HARD_SWAP is subject to the priority threshold.
        """
        priority = validate_priority(priority)
        trace = trace or TransitionTrace(target_capability_key=target_capability_key, priority=float(priority))
        self.transitions.record(trace)
        try:
            self._raise_if_contained()
            in_flight = self._arbiter.follow_inflight(target_capability_key, priority)
            if in_flight is not None:
                self._publish(trace, "arbitrating")
                result = await in_flight
            else:
                result = await self._arbiter.run(
                    target_capability_key,
                    priority,
                    lambda: self._execute_transition(target_capability_key, priority, trace=trace),
                    resolve_before_acquire=lambda: self._resolve_transition_preflight(
                        target_capability_key,
                        trace,
                    ),
                )
        except TransitionDeclined as exc:
            trace.action_type, trace.total_metabolic_cost = exc.plan.action_type, exc.plan.total_metabolic_cost
            self._publish(trace, "declined_no_effect", detail=str(exc))
            raise
        except (RuntimePreconditionError, RuntimeCancellationNoEffectError) as exc:
            self._publish(trace, "declined_no_effect", detail=str(exc))
            raise
        except RuntimeActuationRestoredError as exc:
            self._publish(trace, "failed_restored", detail=str(exc))
            raise
        except RuntimeCancellationRestoredError as exc:
            self._publish(trace, "cancelled_restored", detail=str(exc))
            raise
        except BaseException as exc:
            if trace.phase not in {
                "declined_no_effect",
                "failed_restored",
                "cancelled_restored",
                "contained_uncertain",
            }:
                phase = (
                    "contained_uncertain"
                    if self._contained_reason is not None
                    else "declined_no_effect"
                    if trace.phase == "requested"
                    else "failed"
                )
                self._publish(
                    trace,
                    phase,
                    detail=str(exc),
                )
            else:
                trace.detail = str(exc)
                self.transitions.record(trace)
            raise
        # Coalesced followers report the owner's outcome without retaining its plan.
        trace.action_type, trace.total_metabolic_cost = result.action_type, result.total_metabolic_cost
        self._publish(trace, "completed")
        return result

    async def _resolve_transition_preflight(
        self,
        target_capability_key: str,
        trace: TransitionTrace,
    ) -> TransitionPlan | None:
        """Resolve a warm/open fast path after this request owns its cohort."""
        pre = await self.calculate_transition_plan(target_capability_key)
        # The refresh above yields. Another transition may have latched global
        # containment while this request was planning; recheck before a fast return
        # that bypasses the physical section.
        self._raise_if_contained()
        target_animator = self._target_animator(target_capability_key)
        if pre.action_type == "NO_OP" and self._leases.admission(target_animator) is AnimatorAdmission.OPEN:
            trace.action_type, trace.total_metabolic_cost = pre.action_type, pre.total_metabolic_cost
            return pre
        self._publish(trace, "arbitrating")
        return None

    async def _execute_transition(  # noqa: PLR0915 - explicit transition/compensation state machine
        self,
        target_capability_key: str,
        priority: Priority,
        *,
        trace: TransitionTrace,
    ) -> TransitionPlan:
        """Run the arbiter-guarded critical section: re-plan against fresh world, then actuate."""
        self._raise_if_contained()
        plan = await self.calculate_transition_plan(target_capability_key)  # fresh, post-predecessor
        trace.action_type, trace.total_metabolic_cost = plan.action_type, plan.total_metabolic_cost
        if plan.action_type == "NO_OP":
            target_animator = self._target_animator(target_capability_key)
            if self._leases.admission(target_animator) is not AnimatorAdmission.OPEN:
                msg = (
                    f"Animator '{target_animator}' admission remains closed; "
                    "operator recovery or process restart is required."
                )
                raise RuntimeError(msg)
            return plan

        if plan.action_type == "HARD_SWAP":
            threshold = self._switching.min_priority_for_hard_swap
            if priority < threshold:
                raise TransitionDeclined(plan, priority, threshold)

            affected_animators = list(dict.fromkeys([*plan.evict_coven_ids, *plan.launch_coven_ids]))
            self._publish(trace, "draining")
            async with self._runtime_mutation_barrier(affected_animators):
                intent = TransitionIntent(
                    config_generation=capability_config_generation(self.registry),
                    target_animator=self._target_animator(target_capability_key),
                    target_capability_key=target_capability_key,
                    evict_animators=tuple(plan.evict_coven_ids),
                    launch_animators=tuple(plan.launch_coven_ids),
                    expected_active_animators=self._active_animators(),
                )
                trace.physical_transition_id = intent.transition_id
                self._publish(trace, "actuating")
                try:
                    await self._actuator.apply(intent)
                except (
                    RuntimePreconditionError,
                    RuntimeActuationRestoredError,
                    RuntimeCancellationNoEffectError,
                    RuntimeCancellationRestoredError,
                ):
                    # The host either rejected before mutation or proved that a
                    # failed transaction restored the exact pre-transition
                    # world. In both cases the barrier may safely reopen.
                    raise
                except (Exception, asyncio.CancelledError):
                    # The current actuator contract cannot prove whether a
                    # raising call restored the expected world. Keep both gates
                    # closed rather than admit work into a possibly partial swap.
                    self._contain("runtime actuator outcome is uncertain")
                    raise
                try:
                    # The actuator returns only after the physical transition has
                    # a terminal outcome. Keep queue claims and evictee admission
                    # closed for the separate readiness convergence that follows.
                    self._publish(trace, "verifying")
                    convergence_deadline = asyncio.get_running_loop().time() + self._switching.warmup_timeout_s
                    await self._converge_warm(target_capability_key, deadline=convergence_deadline)
                    await self._converge_evicted_cold(
                        plan.evict_coven_ids,
                        deadline=convergence_deadline,
                    )
                except (Exception, asyncio.CancelledError) as convergence_error:
                    compensation = build_compensation_intent(intent)
                    trace.compensation_transition_id = compensation.transition_id
                    self._publish(trace, "compensating")
                    compensation_task = asyncio.create_task(self._actuator.apply(compensation))
                    try:
                        await complete_under_cancellation(compensation_task)
                    except BaseException as compensation_error:
                        # A half-restored physical world is unsafe. Deliberately
                        # leave both admission layers closed for operator recovery.
                        self._contain("typed runtime compensation failed")
                        message = (
                            f"Transition '{intent.transition_id}' failed readiness convergence and "
                            "its typed compensation failed; runtime admission remains closed."
                        )
                        raise RuntimeError(message) from compensation_error
                    self._publish(
                        trace,
                        (
                            "cancelled_restored"
                            if isinstance(convergence_error, asyncio.CancelledError)
                            else "failed_restored"
                        ),
                    )
                    raise
            return plan

        # A SOFT_SWAP is still a mutable-runtime transition: loading target B
        # can unload model A from the same process. Drain the whole animator so
        # an existing A grant cannot be invalidated underneath a running graph.
        target_animator = self._target_animator(target_capability_key)
        self._publish(trace, "draining")
        async with self._runtime_mutation_barrier([target_animator]):
            try:
                self._publish(trace, "actuating")
                deadline = asyncio.get_running_loop().time() + self._switching.warmup_timeout_s
                await self._converge_warm(target_capability_key, deadline=deadline)
            except (Exception, asyncio.CancelledError):
                # There is no trustworthy model-level inverse without recording
                # the previously loaded model. Do not reopen into unknown state.
                self._contain("soft runtime mutation failed without a trustworthy model inverse")
                raise
        return plan

    @asynccontextmanager
    async def _runtime_mutation_barrier(
        self,
        animator_names: list[str],
    ) -> AsyncGenerator[None]:
        """Drain affected leases; reopen both gates unless containment was latched."""
        self._leases.begin_drain(animator_names)
        try:
            try:
                await self.worker_broker.pause_queues()
                drained = await self._leases.drained(
                    animator_names,
                    timeout=self._switching.drain_timeout_s,
                )
                if not drained:
                    msg = f"Lease drain timed out on: {animator_names}"
                    raise RuntimeError(msg)
                yield
            finally:
                # The claim gate must reopen on timeout, cancellation, or a
                # failed drain; otherwise all future runs wedge.
                if self._contained_reason is None:
                    await self.worker_broker.unpause_queues()
        finally:
            if self._contained_reason is None:
                self._leases.end_drain(animator_names)

    def _contain(self, reason: str) -> None:
        """Latch the first uncertain physical outcome until this process restarts."""
        if self._contained_reason is None:
            self._contained_reason = reason

    def _raise_if_contained(self) -> None:
        if self._contained_reason is None:
            return
        msg = (
            f"Runtime mutation containment is active ({self._contained_reason}); "
            "operator recovery or process restart is required."
        )
        raise RuntimeError(msg)

    async def _refresh_lifecycle_managed_animators(self) -> None:
        """Refresh every local managed runtime before policy reads peer state."""
        animator_names = sorted(
            {
                spec.animator_name
                for spec in self.registry.list_capabilities()
                if self.registry.get_soulstone_rune(spec.animator_name) is not None
            }
        )
        for animator_name in animator_names:
            await self.registry.refresh_capability_states_for_animator(animator_name)

    def _is_animator_runtime_started(self, animator_name: str) -> bool:
        """Return whether any capability observes this runtime as started."""
        return any(state.runtime_started for state in self.registry.list_capability_states_for_animator(animator_name))

    async def _activate_dynamic_capability(self, target: CapabilitySpec) -> None:
        result = await self.registry.activate_capability(target.key)
        if not result.accepted:
            reason = f": {result.reason}" if result.reason else ""
            msg = f"Failed to activate capability '{target.key}' on '{target.animator_name}'{reason}."
            raise RuntimeError(msg)

    async def _converge_warm(self, capability_key: str, *, deadline: float) -> None:
        """Perform target refresh, activation, and WARM proof under one deadline."""
        loop = asyncio.get_running_loop()
        try:
            async with asyncio.timeout_at(deadline):
                spec, current_state = await require_capability_record(self.registry, capability_key)
                if spec.is_dynamic and current_state.phase not in {CapabilityPhase.WARM, CapabilityPhase.WARMING}:
                    await self._activate_dynamic_capability(spec)
                remaining = max(0.0, deadline - loop.time())
                await self.registry.await_warm(spec.key, timeout_s=remaining)
        except TimeoutError as exc:
            raise ActivationTimeout(
                capability_key,
                reason="target convergence exceeded the warm-up deadline",
            ) from exc

    async def _converge_evicted_cold(self, animator_names: list[str], *, deadline: float) -> None:
        """Refresh evictee state and prove no stopped runtime remains active."""
        still_started: list[str] = []
        try:
            async with asyncio.timeout_at(deadline):
                for animator_name in animator_names:
                    states = await self.registry.refresh_capability_states_for_animator(animator_name)
                    if any(state.runtime_started for state in states):
                        still_started.append(animator_name)
        except TimeoutError as exc:
            msg = f"Timed out proving evicted animator runtimes cold: {sorted(animator_names)}"
            raise RuntimeError(msg) from exc
        if still_started:
            msg = f"Evicted animator runtimes remain active after transition: {sorted(still_started)}"
            raise RuntimeError(msg)

    def _target_animator(self, capability_key: str) -> str:
        spec = self.registry.get_capability(capability_key)
        if spec is None:
            msg = f"Unknown capability: {capability_key}"
            raise RuntimeError(msg)
        return spec.animator_name

    def _active_animators(self) -> tuple[str, ...]:
        """Snapshot observed active animators for stale-intent validation."""
        return tuple(
            sorted(
                {
                    spec.animator_name
                    for spec in self.registry.list_capabilities()
                    if self.registry.get_soulstone_rune(spec.animator_name) is not None
                    and (state := self.registry.get_capability_state(spec.key)) is not None
                    and state.runtime_started
                }
            )
        )
