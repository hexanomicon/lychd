from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lychd.domain.animation.capabilities import (
    CapabilityLifecycle,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.orchestration.arbiter import TransitionArbiter, TransitionDeclined
from lychd.domain.orchestration.schema import TransitionPlan

if TYPE_CHECKING:
    from lychd.config.settings import SwitchingSettings
    from lychd.domain.cortex.leases import LeaseLedger
    from lychd.domain.orchestration.policies import SwitchPolicy

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
        switching: SwitchingSettings,
    ) -> None:
        """Initialize orchestration against the injected registry, leases, and policy.

        ``worker_broker`` is a plain attribute: the lifespan late-binds the honest
        ``GhoulBroker`` onto it once the SAQ queues exist (`wire_runtime`); before
        that it is the `QuiescentBroker` stand-in.
        """
        self.worker_broker = worker_broker
        self.registry = registry
        self._leases = leases
        self._policy = policy
        self._arbiter = arbiter
        self._switching = switching

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
                    "lifecycle": spec.lifecycle.value,
                    "phase": state.phase.value,
                    "model_id": spec.model_id,
                    "is_static": state.is_static,
                    "is_active": state.is_active,
                    "is_available": state.is_available,
                    "warm": state.warm,
                    "health": state.health,
                    "reason": state.reason,
                    "dedicated": spec.concurrency.dedicated,
                    "persistent_resident": spec.concurrency.persistent_resident,
                }
            )
        return items

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan:
        """Calculate the transition for a requested capability key."""
        target, target_state = await self._get_capability_record(target_capability_key)

        if target_state.warm:
            return TransitionPlan(
                total_metabolic_cost=0.0,
                evict_coven_ids=[],
                launch_coven_ids=[],
                action_type="NO_OP",
            )

        if target.lifecycle is CapabilityLifecycle.DYNAMIC and self._is_animator_runtime_warm(target.animator_name):
            return TransitionPlan(
                total_metabolic_cost=0.0,
                evict_coven_ids=[],
                launch_coven_ids=[],
                action_type="SOFT_SWAP",
            )

        if not target.concurrency.dedicated:
            msg = (
                f"Capability '{target.key}' is provided by shared animator '{target.animator_name}' "
                "and cannot be lifecycle-managed by the orchestrator."
            )
            raise RuntimeError(msg)

        decision = self._policy.solve(target, self.registry, self._leases)
        return TransitionPlan(
            total_metabolic_cost=decision.metabolic_cost,
            evict_coven_ids=decision.evict_animator_names,
            launch_coven_ids=decision.launch_animator_names,
            action_type="HARD_SWAP",
            policy=self._policy.name,
            reason=decision.reason,
        )

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None:
        """Execute the required transition and converge deterministically on WARM.

        ``TransitionDeclined`` (a priority-gated HARD_SWAP) propagates to `perform_run`
        and fails the run with the plan in the message — an honest refusal, not a hang.
        The terminal ``await_warm`` fails the transition loudly (``ActivationTimeout``)
        instead of handing a cold capability back to the stasis loop.
        """
        spec, _state = await self._get_capability_record(exception.capability_key)
        plan = await self.request_transition(spec.key, signal_priority)
        dynamic = spec.lifecycle is CapabilityLifecycle.DYNAMIC
        if dynamic and plan.action_type in {"SOFT_SWAP", "HARD_SWAP", "NO_OP"}:
            await self._activate_dynamic_capability(spec)
        await self.registry.await_warm(spec.key, timeout_s=self._switching.drain_timeout_s)

    async def request_transition(self, target_capability_key: str, priority: float) -> TransitionPlan:
        """Calculate and (if a HARD_SWAP) execute the physical transition plan.

        A HARD_SWAP below ``min_priority_for_hard_swap`` is declined loudly.
        SOFT_SWAP / NO_OP are NEVER gated (they return before the gate). The physical
        eviction/launch runs inside the arbiter's single-owner section, and drain
        honesty is the LeaseLedger's — never the (lying) broker job count.
        """
        plan = await self.calculate_transition_plan(target_capability_key)
        if plan.action_type != "HARD_SWAP":
            return plan

        threshold = self._switching.min_priority_for_hard_swap
        if priority < threshold:
            raise TransitionDeclined(plan, priority, threshold)

        async def _executor() -> TransitionPlan:
            # The claim gate MUST reopen on EVERY exit path — drain-timeout RuntimeError,
            # a CancelledError raised mid-drain (the up-to-120s wait), or a raising
            # broadcast_soft_stop — or a paused GhoulBroker gate stays closed for the
            # process's life and every future perform_run wedges at intake (F1, P1).
            await self.worker_broker.pause_queues()
            try:
                await self.worker_broker.broadcast_soft_stop()
                drained = await self._leases.drained(plan.evict_coven_ids, timeout=self._switching.drain_timeout_s)
                if not drained:
                    msg = f"Lease drain timed out on: {plan.evict_coven_ids}"
                    raise RuntimeError(msg)

                for animator_name in plan.evict_coven_ids:
                    await self._stop_animator_runtime(animator_name)
                for animator_name in plan.launch_coven_ids:
                    await self._start_animator_runtime(animator_name)
            finally:
                await self.worker_broker.unpause_queues()
            return plan

        return await self._arbiter.run(target_capability_key, priority, _executor)

    async def _get_capability_record(self, key: str) -> tuple[CapabilitySpec, CapabilityState]:
        return await require_capability_record(self.registry, key)

    def _is_animator_runtime_warm(self, animator_name: str) -> bool:
        # Re-reads observed activity: is_active already means phase in {WARM, WARMING}.
        return any(state.is_active for state in self.registry.list_capability_states_for_animator(animator_name))

    async def _activate_dynamic_capability(self, target: CapabilitySpec) -> None:
        result = await self.registry.activate_capability(target.key)
        if not result.accepted:
            reason = f": {result.reason}" if result.reason else ""
            msg = f"Failed to activate capability '{target.key}' on '{target.animator_name}'{reason}."
            raise RuntimeError(msg)

    async def _start_animator_runtime(self, animator_name: str) -> None:
        unit_name = self._runtime_unit(animator_name)
        if unit_name is None:
            msg = f"Animator '{animator_name}' is not backed by a local lifecycle-managed runtime."
            raise RuntimeError(msg)

        process = await asyncio.create_subprocess_exec("systemctl", "--user", "start", unit_name)
        await process.wait()
        if process.returncode != 0:
            msg = f"Physical manifestation failed: systemctl returned {process.returncode} for {unit_name}"
            raise RuntimeError(msg)

        # LAW: the ONLY writer of ``Link.up`` is the adapter probe path. We never
        # fabricate readiness here — the freshly started server is re-probed and
        # honestly reads COLD/WARMING; convergence is handle_transition's await_warm.
        await self.registry.refresh_capability_states_for_animator(animator_name)

    async def _stop_animator_runtime(self, animator_name: str) -> None:
        unit_name = self._runtime_unit(animator_name)
        if unit_name is None:
            return

        process = await asyncio.create_subprocess_exec("systemctl", "--user", "stop", unit_name)
        await process.wait()

        await self.registry.refresh_capability_states_for_animator(animator_name)

    def _runtime_unit(self, animator_name: str) -> str | None:
        soulstone = self.registry.get_soulstone_rune(animator_name)
        if soulstone is None:
            return None
        return f"{soulstone.service_name}.service"
