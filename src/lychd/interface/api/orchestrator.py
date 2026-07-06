from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from litestar import Controller, Request, Response, get, post
from litestar.status_codes import HTTP_202_ACCEPTED, HTTP_409_CONFLICT

from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.substrate import get_run_substrate
from lychd.domain.orchestration.arbiter import TransitionDeclined
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan

if TYPE_CHECKING:
    from lychd.domain.cortex.leases import LeaseRow


def _handle_transition_declined(_request: Request[Any, Any, Any], exc: TransitionDeclined) -> Response[dict[str, Any]]:
    """Render a declined HARD_SWAP as a 409 carrying the plan + threshold (honest refusal)."""
    return Response(
        content={
            "detail": str(exc),
            "priority": exc.priority,
            "threshold": exc.threshold,
            "plan": exc.plan.model_dump(),
        },
        status_code=HTTP_409_CONFLICT,
    )


def _lease_row_json(row: LeaseRow) -> dict[str, Any]:
    return {
        "grant_id": row.grant_id,
        "holder": row.holder,
        "capability_key": row.capability_key,
        "animator_name": row.animator_name,
        "priority": row.priority,
        "issued_at": row.issued_at.isoformat(),
    }


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

    @post(
        "/activate",
        status_code=HTTP_202_ACCEPTED,
        exception_handlers={TransitionDeclined: _handle_transition_declined},
    )
    async def activate_capability(
        self, orchestrator: OrchestratorManager, target: str, priority: float = 100.0
    ) -> TransitionPlan:
        """Manually trigger the transition path for one capability key.

        A HARD_SWAP whose ``priority`` is below the switching gate is declined with a
        409 (the plan + threshold in the body); SOFT_SWAP / NO_OP are never gated.
        """
        return await orchestrator.request_transition(target, priority=priority)

    @get("/queues")
    async def get_queues(self, orchestrator: OrchestratorManager, leases: LeaseLedger) -> dict[str, Any]:
        """Report live SAQ queue depths + the current lease rows (drain-truth view).

        Queues are read from the published `RunSubstrate` (zero substrate injection —
        the F1 lesson): a bare test client with no substrate reports none. Missing
        ``Queue.info()`` keys tolerate to zeros; ``paused`` reflects the broker's
        claim gate.
        """
        paused = bool(getattr(getattr(orchestrator, "worker_broker", None), "paused", False))
        queue_rows: list[dict[str, Any]] = []
        try:
            substrate = get_run_substrate()
        except RuntimeError:
            substrate = None
        if substrate is not None:
            for name, queue in substrate.queues.items():
                info: dict[str, Any] = {}
                try:
                    info = dict(await cast("Any", queue).info())
                except Exception:  # noqa: BLE001 - offline queue tolerates to zeros
                    info = {}
                queue_rows.append(
                    {
                        "name": name,
                        "depth": int(info.get("queued", 0)),
                        "active": int(info.get("active", 0)),
                        "paused": paused,
                    }
                )
        return {"queues": queue_rows, "leases": [_lease_row_json(row) for row in leases.active()]}
