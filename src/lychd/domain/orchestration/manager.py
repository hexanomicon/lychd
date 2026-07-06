from __future__ import annotations

import asyncio
from typing import Any

from lychd.domain.animation.capabilities import (
    CapabilityLifecycle,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.orchestration.schema import TransitionPlan


class OrchestratorManager:
    """Plan and execute local runtime transitions from the canonical registry."""

    def __init__(
        self,
        worker_broker: Any,
        registry: CapabilityRegistry,
    ) -> None:
        """Initialize orchestration against the injected canonical registry."""
        self.worker_broker = worker_broker
        self.registry = registry

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
        target, target_state = self._get_capability_record(target_capability_key)

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

        evict_ids, launch_ids, total_cost = self._solve_transition(target)
        return TransitionPlan(
            total_metabolic_cost=float(total_cost),
            evict_coven_ids=evict_ids,
            launch_coven_ids=launch_ids,
            action_type="HARD_SWAP",
        )

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None:
        """Execute the required transition and finish dynamic soft activation when needed."""
        plan = await self.request_transition(exception.spec.key, signal_priority)
        if exception.spec.lifecycle is not CapabilityLifecycle.DYNAMIC:
            return

        if plan.action_type not in {"SOFT_SWAP", "HARD_SWAP", "NO_OP"}:
            return
        await self._activate_dynamic_capability(exception.spec)

    async def request_transition(self, target_capability_key: str, priority: float) -> TransitionPlan:
        """Calculate and execute the physical transition plan."""
        _ = priority
        plan = await self.calculate_transition_plan(target_capability_key)

        if plan.action_type != "HARD_SWAP":
            return plan

        await self.worker_broker.pause_queues()
        await self.worker_broker.broadcast_soft_stop()
        await self._await_active_drain()

        try:
            for animator_name in plan.evict_coven_ids:
                await self._stop_animator_runtime(animator_name)

            for animator_name in plan.launch_coven_ids:
                await self._start_animator_runtime(animator_name)
        finally:
            await self.worker_broker.unpause_queues()

        return plan

    def _solve_transition(self, target: CapabilitySpec) -> tuple[list[str], list[str], int]:
        """Select the local eviction set from lifecycle ownership hints."""
        local_specs = self._local_animator_specs()
        active_specs = {
            spec.animator_name: spec
            for spec in local_specs.values()
            if (state := self.registry.get_capability_state(spec.key)) is not None and state.is_active
        }

        if target.animator_name in active_specs:
            return ([], [], 0)

        evictees = [
            spec
            for spec in active_specs.values()
            if spec.concurrency.dedicated and not spec.concurrency.persistent_resident
        ]
        return (self._sorted_animator_ids(evictees), [target.animator_name], len(evictees))

    def _local_animator_specs(self) -> dict[str, CapabilitySpec]:
        specs: dict[str, CapabilitySpec] = {}
        for spec in self.registry.list_capabilities():
            if spec.source_kind != "soulstone":
                continue
            specs.setdefault(spec.animator_name, spec)
        return specs

    def _sorted_animator_ids(self, specs: list[CapabilitySpec]) -> list[str]:
        return sorted(spec.animator_name for spec in specs)

    def _get_capability_record(self, key: str) -> tuple[CapabilitySpec, CapabilityState]:
        return require_capability_record(self.registry, key)

    def _is_animator_runtime_warm(self, animator_name: str) -> bool:
        for state in self.registry.list_capability_states_for_animator(animator_name):
            if state.is_active or state.warm:
                return True
        return False

    async def _activate_dynamic_capability(self, target: CapabilitySpec) -> None:
        result = self.registry.activate_capability(target.key)
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

        runtime = self.registry.get_runtime(animator_name)
        if runtime is not None:
            runtime.connector.link.up = True
        self.registry.refresh_capability_states_for_animator(animator_name)

    async def _stop_animator_runtime(self, animator_name: str) -> None:
        unit_name = self._runtime_unit(animator_name)
        if unit_name is None:
            return

        process = await asyncio.create_subprocess_exec("systemctl", "--user", "stop", unit_name)
        await process.wait()

        runtime = self.registry.get_runtime(animator_name)
        if runtime is not None:
            runtime.connector.link.up = False
        self.registry.refresh_capability_states_for_animator(animator_name)

    def _runtime_unit(self, animator_name: str) -> str | None:
        soulstone = self.registry.get_soulstone_rune(animator_name)
        if soulstone is None:
            return None
        return f"{soulstone.service_name}.service"

    async def _await_active_drain(self) -> None:
        """Poll the worker broker until the active job count reaches zero."""
        while await self.worker_broker.get_active_worker_count() > 0:  # noqa: ASYNC110
            await asyncio.sleep(1)
