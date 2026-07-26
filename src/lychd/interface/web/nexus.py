"""Versioned Nexus JSON API and transition event stream."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from litestar import Controller, get, post
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, FromQuery
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_202_ACCEPTED

from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.cortex.priority import PRIORITY_MAX
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.domain.web.contracts import NexusSnapshot, SwapAccepted, SwapIntent, TransitionEventEnvelope
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.schemas import SwapTicket, build_nexus_board
from lychd.domain.web.tickets import TicketRecord, TicketStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class NexusController(Controller):
    """Serve capability state and typed transition intents."""

    path = "/api/v1/nexus"

    @get("", name="nexus:snapshot", operation_id="getNexusSnapshot", guards=[requires_scopes("altar:read")])
    async def snapshot(
        self,
        orchestrator: NamedDependency[OrchestratorManager],
        registry: NamedDependency[AnimatorRegistry],
    ) -> NexusSnapshot:
        """Return the current capability board."""
        return NexusSnapshot(board=build_nexus_board(orchestrator, registry))

    @get("/plan", name="nexus:plan", operation_id="getNexusPlan", guards=[requires_scopes("altar:read")])
    async def plan(
        self,
        orchestrator: NamedDependency[OrchestratorManager],
        target: FromQuery[str],
    ) -> TransitionPlan:
        """Dry-run the transition solver."""
        try:
            return await orchestrator.calculate_transition_plan(target)
        except ValueError as exc:
            raise NotFoundException(detail=f"Unknown capability target: {target}") from exc

    @post(
        "/swaps",
        status_code=HTTP_202_ACCEPTED,
        name="nexus:swap",
        operation_id="createNexusSwap",
        guards=[requires_scopes("orchestrator:transition")],
    )
    async def swap(
        self,
        data: SwapIntent,
        orchestrator: NamedDependency[OrchestratorManager],
        tickets: NamedDependency[TicketStore],
        projector: NamedDependency[EventProjector],
    ) -> SwapAccepted:
        """Launch one transition and return a process-local ticket."""
        try:
            plan = await orchestrator.calculate_transition_plan(data.target)
        except ValueError as exc:
            raise NotFoundException(detail=f"Unknown capability target: {data.target}") from exc
        task = asyncio.create_task(
            orchestrator.request_transition(data.target, priority=PRIORITY_MAX),
            name=f"swap:{data.target}",
        )
        record = tickets.open(
            target=data.target,
            action_type=plan.action_type,
            total_metabolic_cost=plan.total_metabolic_cost,
            task=task,
        )
        return SwapAccepted(ticket=projector.ticket_view(record))

    @get(
        "/swaps/{ticket_id:str}",
        name="nexus:ticket",
        operation_id="getNexusSwap",
        guards=[requires_scopes("altar:read")],
    )
    async def swap_status(
        self,
        ticket_id: FromPath[str],
        tickets: NamedDependency[TicketStore],
        projector: NamedDependency[EventProjector],
    ) -> SwapAccepted:
        """Return the current state of one transition ticket."""
        record = tickets.get(ticket_id)
        if record is None:
            raise NotFoundException(detail="Unknown ticket.")
        return SwapAccepted(ticket=self._ticket(record, projector))

    @get(
        "/swaps/{ticket_id:str}/events",
        name="nexus:ticket-events",
        operation_id="streamNexusSwapEvents",
        guards=[requires_scopes("altar:read")],
        responses={
            200: ResponseSpec(
                TransitionEventEnvelope,
                generate_examples=False,
                media_type="text/event-stream",
                description="Versioned semantic transition events.",
            ),
        },
    )
    async def swap_events(
        self,
        ticket_id: FromPath[str],
        tickets: NamedDependency[TicketStore],
        projector: NamedDependency[EventProjector],
    ) -> ServerSentEvent:
        """Stream warming and terminal ticket state without HTML polling."""
        record = tickets.get(ticket_id)
        if record is None:
            raise NotFoundException(detail="Unknown ticket.")

        async def stream() -> AsyncIterator[ServerSentEventMessage]:
            warming = projector.ticket_view(record)
            yield self._ticket_event(warming, seq=0)
            if not record.task.done():
                await asyncio.wait({record.task})
            yield self._ticket_event(self._ticket(record, projector), seq=1)

        return ServerSentEvent(stream())

    @staticmethod
    def _ticket(record: TicketRecord, projector: EventProjector) -> SwapTicket:
        failed = record.task.cancelled() or (record.task.done() and record.task.exception() is not None)
        return projector.ticket_view(record, settled=record.task.done(), failed=failed)

    @staticmethod
    def _ticket_event(ticket: SwapTicket, *, seq: int) -> ServerSentEventMessage:
        return ServerSentEventMessage(
            event="transition",
            id=str(seq),
            data=json.dumps({"schema_version": 1, "seq": seq, "ticket": asdict(ticket)}),
        )
