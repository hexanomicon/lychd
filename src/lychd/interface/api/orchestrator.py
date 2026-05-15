from typing import Any
from litestar import Controller, get, post
from litestar.status_codes import HTTP_202_ACCEPTED
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.domain.orchestration.manager import OrchestratorManager

class OrchestratorController(Controller):
    """
    The Sovereign Interface.
    Exposes the Physical Will of the Orchestrator to the Magus.
    Bound to the local coven boundaries.
    """
    path = "/orchestrator"
    tags = ["Orchestrator"]

    @get("/status")
    async def get_status(self, orchestrator: OrchestratorManager) -> dict[str, Any]:
        """
        Returns the current VRAM occupancy and known cognitive capabilities.
        """
        return {
            "active_capabilities": [c.identifier for c in orchestrator.all_capabilities if c.is_active],
            "all_capabilities": [
                {
                    "identifier": c.identifier,
                    "is_active": c.is_active,
                    "evict_cost": c.evict_cost,
                    "matrix_sets": c.matrix_sets
                } for c in orchestrator.all_capabilities
            ]
        }

    @get("/solver/plan")
    async def get_transition_plan(self, orchestrator: OrchestratorManager, target: str) -> TransitionPlan:
        """
        Dry-run the Matrix Solver to see the metabolic cost of a transition.
        """
        return await orchestrator.calculate_transition_plan(target)

    @post("/activate", status_code=HTTP_202_ACCEPTED)
    async def activate_capability(self, orchestrator: OrchestratorManager, target: str) -> TransitionPlan:
        """
        Manually trigger a hardware swap. 
        Follows the standard Graceful Drain and queue-pausing ritual.
        """
        # We use a default priority of 100 for manual overrides
        return await orchestrator.request_transition(target, priority=100.0)
