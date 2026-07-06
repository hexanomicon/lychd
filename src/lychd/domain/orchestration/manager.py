from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from lychd.domain.animation.capabilities import (
    CapabilityLifecycle,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.orchestration.schema import TransitionPlan

if TYPE_CHECKING:
    from lychd.domain.cortex.leases import LeaseLedger

# D14: keel-phase drain/convergence timeout. Track O replaces this module constant
# with ``self._switching.drain_timeout_s`` in O4.
_DRAIN_TIMEOUT_S: Final[float] = 120.0


@dataclass(frozen=True, slots=True)
class _AnimatorRecord:
    """Animator-level projection the solver reasons over. Built from registry truth.

    Keel-private; Track O extracts it VERBATIM as ``policies.AnimatorRecord``.
    """

    name: str
    dedicated: bool  # rune.concurrency.dedicated
    persistent_resident: bool  # rune.concurrency.persistent_resident
    active: bool  # any state.phase in {WARM, WARMING} on it
    leased: bool  # LeaseLedger.active(animator_name=name) != []


class OrchestratorManager:
    """Plan and execute local runtime transitions from the canonical registry."""

    def __init__(
        self,
        worker_broker: Any,
        registry: CapabilityRegistry,
        *,
        leases: LeaseLedger,
    ) -> None:
        """Initialize orchestration against the injected canonical registry + leases."""
        self.worker_broker = worker_broker
        self.registry = registry
        self._leases = leases

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

        evict_ids, launch_ids, total_cost = self._solve_transition(target)
        return TransitionPlan(
            total_metabolic_cost=float(total_cost),
            evict_coven_ids=evict_ids,
            launch_coven_ids=launch_ids,
            action_type="HARD_SWAP",
        )

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None:
        """Execute the required transition and converge deterministically on WARM.

        The terminal ``await_warm`` fails the transition loudly (``ActivationTimeout``)
        instead of handing a cold capability back to the stasis loop.
        """
        spec, _state = await self._get_capability_record(exception.capability_key)
        plan = await self.request_transition(spec.key, signal_priority)
        dynamic = spec.lifecycle is CapabilityLifecycle.DYNAMIC
        if dynamic and plan.action_type in {"SOFT_SWAP", "HARD_SWAP", "NO_OP"}:
            await self._activate_dynamic_capability(spec)
        await self.registry.await_warm(spec.key, timeout_s=_DRAIN_TIMEOUT_S)

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

    def _animator_records(self) -> list[_AnimatorRecord]:
        """Project one record per soulstone-backed animator over registry truth.

        Portals are excluded (not lifecycle-managed: ``get_soulstone_rune(name) is
        None``). Concurrency comes from THE RUNE (``rune.concurrency``), NEVER from
        an arbitrary spec.
        """
        records: list[_AnimatorRecord] = []
        seen: set[str] = set()
        for spec in self.registry.list_capabilities():
            name = spec.animator_name
            if name in seen:
                continue
            rune = self.registry.get_soulstone_rune(name)
            if rune is None:
                continue
            seen.add(name)
            states = self.registry.list_capability_states_for_animator(name)
            records.append(
                _AnimatorRecord(
                    name=name,
                    dedicated=rune.concurrency.dedicated,
                    persistent_resident=rune.concurrency.persistent_resident,
                    active=any(state.is_active for state in states),
                    leased=bool(self._leases.active(animator_name=name)),
                )
            )
        return records

    def _solve_transition(self, target: CapabilitySpec) -> tuple[list[str], list[str], int]:
        """Select the eviction set honestly over the lease-aware animator records."""
        records = self._animator_records()
        if any(record.name == target.animator_name and record.active for record in records):
            return ([], [], 0)

        evictees = sorted(
            record.name
            for record in records
            if record.dedicated
            and not record.persistent_resident
            and record.active
            and not record.leased
            and record.name != target.animator_name
        )
        return (evictees, [target.animator_name], len(evictees))

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

    async def _await_active_drain(self) -> None:
        """Poll the worker broker until the active job count reaches zero."""
        while await self.worker_broker.get_active_worker_count() > 0:  # noqa: ASYNC110
            await asyncio.sleep(1)
