"""`NexusController` — coven board, transition plan, and swaps (routes 10-13).

The board is a read-only projection of the orchestrator's capability statuses; a
swap is a long mutation surfaced as a self-polling ticket that settles with an
HTTP 286 (stop-polling) plus a body event that the board hears to refresh once.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, cast

from litestar import Controller, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import Response, Template
from litestar.status_codes import HTTP_202_ACCEPTED

from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.domain.web.schemas import SwapTicket, build_nexus_board

# HTMX swaps the response body *and* stops the element polling on this code.
_HTTP_286_STOP_POLLING = 286


@dataclass
class _TicketRecord:
    """An in-flight coven transition tracked for the polling ticket strip."""

    id: str
    target: str
    action_type: str
    total_metabolic_cost: float
    task: asyncio.Task[Any]


# Loop-confined, process-local: the slice has no durable ticket store yet.
_TICKETS: dict[str, _TicketRecord] = {}


class NexusController(Controller):
    """Serve the Nexus coven board, plan drawer, and swap lifecycle."""

    path = "/nexus"

    @get("/board")
    async def board(
        self,
        request: HTMXRequest,
        orchestrator: OrchestratorManager,
        registry: AnimatorRegistry,
    ) -> Template:
        """Return the coven board fragment (htmx) or the full Nexus page."""
        ctx: dict[str, Any] = {"board": build_nexus_board(orchestrator, registry)}
        if request.htmx:
            return HTMXTemplate(template_name="nexus/board.html.j2", context=ctx)
        ctx["active"] = "nexus"
        return Template(template_name="altar/pages/nexus.html.j2", context=ctx)

    @get("/plan")
    async def plan(
        self,
        request: HTMXRequest,
        orchestrator: OrchestratorManager,
        target: str,
    ) -> Template | TransitionPlan:
        """Dry-run the transition solver: drawer fragment (htmx) or JSON."""
        try:
            transition_plan = await orchestrator.calculate_transition_plan(target)
        except ValueError as exc:
            msg = f"Unknown capability target: {target}"
            raise NotFoundException(msg) from exc
        if request.htmx:
            return HTMXTemplate(
                template_name="nexus/swap_plan.html.j2",
                context={"plan": transition_plan, "target": target},
            )
        return transition_plan

    @post("/swap", status_code=HTTP_202_ACCEPTED)
    async def swap(
        self,
        request: HTMXRequest,
        orchestrator: OrchestratorManager,
    ) -> Response[str] | Template:
        """Launch a transition and return the self-polling ticket strip (202)."""
        if not request.htmx:
            return Response(content="Swap is an HTMX-only endpoint.", status_code=400)

        form = await request.form()
        target = str(form.get("target", "")).strip()
        if not target:
            return Response(content="No swap target named.", status_code=400)

        try:
            transition_plan = await orchestrator.calculate_transition_plan(target)
        except ValueError as exc:
            msg = f"Unknown capability target: {target}"
            raise NotFoundException(msg) from exc
        ticket_id = f"ticket_{uuid.uuid4().hex[:12]}"
        task = asyncio.create_task(
            orchestrator.request_transition(target, priority=100.0),
            name=f"swap:{ticket_id}",
        )
        _TICKETS[ticket_id] = _TicketRecord(
            id=ticket_id,
            target=target,
            action_type=transition_plan.action_type,
            total_metabolic_cost=transition_plan.total_metabolic_cost,
            task=task,
        )
        return HTMXTemplate(
            template_name="nexus/swap_ticket.html.j2",
            context={"ticket": self._ticket_view(_TICKETS[ticket_id])},
            re_target="#nexus-plan",
            re_swap="innerHTML",
        )

    @get("/swap/{ticket_id:str}")
    async def swap_status(self, request: HTMXRequest, ticket_id: str) -> Template | Response[str]:
        """Return the ticket strip; settle with 286 + a board-refresh trigger."""
        record = _TICKETS.get(ticket_id)
        if record is None:
            return Response(content="Unknown ticket.", status_code=404)

        if not record.task.done():
            return HTMXTemplate(
                template_name="nexus/swap_ticket.html.j2",
                context={"ticket": self._ticket_view(record)},
            )

        failed = record.task.exception() is not None
        ticket = self._ticket_view(record, settled=True, failed=failed)
        _TICKETS.pop(ticket_id, None)

        engine = cast("JinjaTemplateEngine | None", request.app.template_engine)
        if engine is None:  # pragma: no cover - template config is always present
            msg = "Template engine is not configured."
            raise RuntimeError(msg)
        html = engine.get_template("nexus/swap_ticket.html.j2").render({"ticket": ticket})
        return Response(
            content=html,
            status_code=_HTTP_286_STOP_POLLING,
            media_type=MediaType.HTML,
            headers={"HX-Trigger-After-Settle": "nexus:swap-settled"},
        )

    # -- helpers ----------------------------------------------------------

    def _ticket_view(self, record: _TicketRecord, *, settled: bool = False, failed: bool = False) -> SwapTicket:
        if failed:
            state, phase = "failed", "faulted"
        elif settled:
            state, phase = "settled", "risen"
        else:
            state, phase = "in_flight", "transmuting"
        return SwapTicket(
            id=record.id,
            target=record.target,
            state=state,
            phase=phase,
            action_type=record.action_type,
            total_metabolic_cost=record.total_metabolic_cost,
        )
