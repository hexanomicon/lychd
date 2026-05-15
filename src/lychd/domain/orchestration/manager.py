import asyncio
from typing import Any

from lychd.extensions.protocols import CapabilityProtocol
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.domain.orchestration.schema import TransitionPlan

class OrchestratorManager:
    """
    The Physical Will of LychD.
    Calculates optimal VRAM states using the Matrix DSL Solver and executes
    physical transmutations safely via Systemd.
    """
    
    def __init__(self, worker_broker: Any, all_capabilities: list[CapabilityProtocol] | None = None) -> None:
        """
        :param worker_broker: The interface to the SAQ/Worker layer (Ghouls).
        :param all_capabilities: The registry of known cognitive powers.
        """
        self.worker_broker = worker_broker
        self.all_capabilities = all_capabilities or []
    
    async def calculate_transition_plan(self, target_capability_id: str) -> TransitionPlan:
        """
        THE MATRIX SOLVER (Public Interface).
        Calculates the lowest-cost transition path for the requested capability.
        """
        target = next((c for c in self.all_capabilities if c.identifier == target_capability_id), None)
        if not target:
            raise ValueError(f"Unknown capability: {target_capability_id}")

        # 1. Determine if a Hard Swap is even needed
        # We assume coven_id == capability_id for routing logic
        is_warm = await self._is_coven_target_active(target.identifier)
        
        if is_warm:
            # If warm, it's a soft swap (if not already active) or a no-op
            return TransitionPlan(
                total_metabolic_cost=0.0,
                evict_coven_ids=[],
                launch_coven_ids=[],
                action_type="SOFT_SWAP" if not target.is_active else "NO_OP"
            )

        # 2. Run the Matrix Solver
        current_active = {c for c in self.all_capabilities if c.is_active}
        best_cost = float('inf')
        best_evictees = set()
        best_candidates = set()
        
        for matrix_set in target.matrix_sets:
            candidate_set = {c for c in self.all_capabilities if matrix_set in c.matrix_sets}
            evictees = current_active - candidate_set
            cost = sum(m.evict_cost for m in evictees)
            
            if cost < best_cost:
                best_cost = cost
                best_evictees = evictees
                best_candidates = candidate_set

        # Launching candidates that aren't already active
        to_launch = best_candidates - current_active
        # Ensure target is in launch list if not active
        if target not in current_active:
            to_launch.add(target)

        return TransitionPlan(
            total_metabolic_cost=float(best_cost),
            evict_coven_ids=[m.identifier for m in best_evictees],
            launch_coven_ids=[m.identifier for m in to_launch],
            action_type="HARD_SWAP"
        )

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None:
        """
        Resolves a HardwareTransitionRequired signal by executing a transition plan.
        """
        await self.request_transition(exception.capability.identifier, signal_priority)
        
        # SOFT SWAP logic (always run to ensure model is loaded in the runner/relic)
        # Note: In a manual override, we might not have the animator available here 
        # unless we find it in the registry. For now, handle_transition keeps its behavior.
        await exception.animator.activate_capability(exception.capability)

    async def request_transition(self, target_capability_id: str, priority: float) -> TransitionPlan:
        """
        The Master Switch.
        Calculates and executes a transition plan with full Graceful Drain physics.
        """
        plan = await self.calculate_transition_plan(target_capability_id)
        
        if plan.action_type == "HARD_SWAP":
            # THE GRACEFUL DRAIN PROTOCOL
            await self.worker_broker.pause_queues()
            await self.worker_broker.broadcast_soft_stop()
            await self._await_active_drain()
            
            try:
                # PHYSICAL EXECUTION
                for evict_id in plan.evict_coven_ids:
                    await self._stop_coven_target(evict_id)
                
                for start_id in plan.launch_coven_ids:
                    await self._start_coven_target(start_id)
            finally:
                await self.worker_broker.unpause_queues()
        
        return plan

    async def _is_coven_target_active(self, coven_id: str) -> bool:
        """Asynchronously checks the Systemd status of the Coven Target."""
        process = await asyncio.create_subprocess_exec(
            "systemctl", "--user", "is-active", f"lychd-coven-{coven_id}.target",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
        return process.returncode == 0

    async def _start_coven_target(self, coven_id: str) -> None:
        """Asynchronously executes the Systemd start command."""
        process = await asyncio.create_subprocess_exec(
            "systemctl", "--user", "start", f"lychd-coven-{coven_id}.target"
        )
        await process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Physical manifestation failed: systemctl returned {process.returncode}")

    async def _stop_coven_target(self, coven_id: str) -> None:
        """Asynchronously executes the Systemd stop command."""
        process = await asyncio.create_subprocess_exec(
            "systemctl", "--user", "stop", f"lychd-coven-{coven_id}.target"
        )
        await process.wait()

    async def _await_active_drain(self) -> None:
        """Polls the worker broker until the active job count reaches 0."""
        while await self.worker_broker.get_active_worker_count() > 0:
            await asyncio.sleep(1)
