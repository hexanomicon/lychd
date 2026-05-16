from __future__ import annotations

from typing import Any

from litestar import Controller, get, post
from litestar.status_codes import HTTP_202_ACCEPTED

from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan


class OrchestratorController(Controller):
    """Expose orchestrator planning and activation over the local API."""

    path = "/orchestrator"
    tags = ("Orchestrator",)

    @get("/status")
    async def get_status(self, orchestrator: OrchestratorManager) -> dict[str, Any]:
        """Return capability status from the canonical registry view."""
        capabilities = orchestrator.list_capability_statuses()
        return {
            "active_capabilities": [item["capability_key"] for item in capabilities if item["is_active"]],
            "all_capabilities": capabilities,
        }

    @get("/solver/plan")
    async def get_transition_plan(self, orchestrator: OrchestratorManager, target: str) -> TransitionPlan:
        """Dry-run the transition solver for one capability key."""
        return await orchestrator.calculate_transition_plan(target)

    @post("/activate", status_code=HTTP_202_ACCEPTED)
    async def activate_capability(self, orchestrator: OrchestratorManager, target: str) -> TransitionPlan:
        """Manually trigger the transition path for one capability key."""
        return await orchestrator.request_transition(target, priority=100.0)
