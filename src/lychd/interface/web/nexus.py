"""`NexusController` — Nexus page, coven board, transition plan, and swaps.

The board is a read-only projection of the orchestrator's capability statuses; a
swap is a long mutation surfaced as a self-polling ticket (tracked in the
`TicketStore`, not a module global) that settles with an HTTP 286 (stop-polling)
plus a body event the board hears to refresh once.
"""

from __future__ import annotations

import asyncio
from typing import Any

from litestar import Controller, get, post
from litestar.exceptions import NotFoundException
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import Response, Template
from litestar.status_codes import HTTP_202_ACCEPTED

# Runtime imports: Litestar resolves handler param/return annotations at registration.
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.cortex.priority import PRIORITY_MAX
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.domain.web.projection import Projector, stop_polling
from lychd.domain.web.schemas import build_nexus_board
from lychd.domain.web.tickets import TicketStore


class NexusController(Controller):
    """Serve the Nexus coven board, plan drawer, and swap lifecycle."""

    path = "/nexus"

    @get("/", name="nexus:page", guards=[requires_scopes("altar:read")])
    async def page(self, consents: ConsentLedger) -> Template:
        """Render the Nexus page; the coven board self-loads over HTMX."""
        return Template(
            template_name="altar/pages/nexus.html.j2",
            context={"active": "nexus", "pending": await consents.pending_count()},
        )

    @get("/board", name="nexus:board", guards=[requires_scopes("altar:read")])
    async def board(
        self,
        request: HTMXRequest,
        orchestrator: OrchestratorManager,
        registry: AnimatorRegistry,
    ) -> Template:
        """Return the coven board fragment (htmx) or the full Nexus page (dual-render)."""
        ctx: dict[str, Any] = {"board": build_nexus_board(orchestrator, registry)}
        if request.htmx:
            return HTMXTemplate(template_name="nexus/board.html.j2", context=ctx)
        ctx["active"] = "nexus"
        return Template(template_name="altar/pages/nexus.html.j2", context=ctx)

    @get("/plan", name="nexus:plan", guards=[requires_scopes("altar:read")])
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

    @post(
        "/swap",
        status_code=HTTP_202_ACCEPTED,
        name="nexus:swap",
        guards=[requires_scopes("orchestrator:transition")],
    )
    async def swap(
        self,
        request: HTMXRequest,
        orchestrator: OrchestratorManager,
        tickets: TicketStore,
        projector: Projector,
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

        task = asyncio.create_task(
            orchestrator.request_transition(target, priority=PRIORITY_MAX),
            name=f"swap:{target}",
        )
        record = tickets.open(
            target=target,
            action_type=transition_plan.action_type,
            total_metabolic_cost=transition_plan.total_metabolic_cost,
            task=task,
        )
        return HTMXTemplate(
            template_name="nexus/swap_ticket.html.j2",
            context={"ticket": projector.ticket_view(record)},
            re_target="#nexus-plan",
            re_swap="innerHTML",
            status_code=HTTP_202_ACCEPTED,
        )

    @get("/swap/{ticket_id:str}", name="nexus:ticket", guards=[requires_scopes("altar:read")])
    async def swap_status(
        self,
        ticket_id: str,
        tickets: TicketStore,
        projector: Projector,
    ) -> Template | Response[str]:
        """Return the ticket strip; settle with 286 + a board-refresh trigger."""
        record = tickets.get(ticket_id)
        if record is None:
            return Response(content="Unknown ticket.", status_code=404)

        if not record.task.done():
            return HTMXTemplate(
                template_name="nexus/swap_ticket.html.j2",
                context={"ticket": projector.ticket_view(record)},
            )

        failed = record.task.cancelled() or record.task.exception() is not None
        ticket = projector.ticket_view(record, settled=True, failed=failed)
        tickets.settle(ticket_id)
        html = projector.render("nexus/swap_ticket.html.j2", {"ticket": ticket})
        return stop_polling(html, trigger_after_settle="nexus:swap-settled")
