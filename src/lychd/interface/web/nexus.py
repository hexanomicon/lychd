"""Versioned Nexus JSON API and transition event stream."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from litestar import Controller, Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException, ServiceUnavailableException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, FromQuery
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_202_ACCEPTED

from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.cortex.priority import PRIORITY_MAX
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan, TransitionTrace
from lychd.domain.web.contracts import (
    NexusSnapshot,
    SwapAccepted,
    SwapIntent,
    TransitionEventEnvelope,
    TransitionRecordView,
)
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.schemas import SwapTicket, build_nexus_board
from lychd.domain.web.tickets import TicketCapacityError, TicketRecord, TicketStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def _parse_last_event_id(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _transition_view(record: Any) -> TransitionRecordView:
    """Project one bounded journal row with exact cross-instrument links."""
    return TransitionRecordView(
        **asdict(record),
        orb_path=f"/orb/{record.run_id}" if record.run_id else None,
        bridge_path=None,
    )


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
        return NexusSnapshot(
            snapshot_at=datetime.now(UTC),
            board=build_nexus_board(orchestrator, registry),
            containment_reason=orchestrator.containment_reason,
            transitions=[_transition_view(record) for record in orchestrator.transitions.recent()],
        )

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
        try:
            tickets.ensure_capacity()
        except TicketCapacityError as exc:
            raise ServiceUnavailableException(detail=str(exc)) from exc
        trace = TransitionTrace(target_capability_key=data.target, priority=float(PRIORITY_MAX))
        task = asyncio.create_task(
            orchestrator.request_transition(data.target, priority=PRIORITY_MAX, trace=trace),
            name=f"swap:{data.target}",
        )
        try:
            record = tickets.open(
                target=data.target,
                action_type=plan.action_type,
                total_metabolic_cost=plan.total_metabolic_cost,
                trace=trace,
                task=task,
            )
        except TicketCapacityError as exc:  # defensive if the store implementation changes
            raise ServiceUnavailableException(detail=str(exc)) from exc
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
        "/transitions/{request_id:str}",
        name="nexus:transition",
        operation_id="getNexusTransition",
        guards=[requires_scopes("altar:read")],
    )
    async def transition_status(
        self,
        request_id: FromPath[str],
        orchestrator: NamedDependency[OrchestratorManager],
    ) -> TransitionRecordView:
        """Resolve any retained run- or operator-origin transition by causal id."""
        record = orchestrator.transitions.get(request_id)
        if record is None:
            raise NotFoundException(detail="Transition evidence is not retained in this process.")
        return _transition_view(record)

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
        request: Request[Any, Any, Any],
        ticket_id: FromPath[str],
        tickets: NamedDependency[TicketStore],
        projector: NamedDependency[EventProjector],
    ) -> ServerSentEvent:
        """Stream warming and terminal ticket state without HTML polling."""
        from_seq = _parse_last_event_id(request.headers.get("Last-Event-ID"))
        record = tickets.get(ticket_id)
        if record is None:
            raise NotFoundException(detail="Unknown ticket.")

        async def stream() -> AsyncIterator[ServerSentEventMessage]:
            if record.task.done():
                # A finite process-local stream must always restate its terminal
                # truth. Returning an empty 200 makes EventSource reconnect
                # forever when the browser is already at—or above—our head.
                yield self._ticket_event(self._ticket(record, projector), seq=1)
                return
            if from_seq != 0:
                # Only cursor 0 can continue an active ticket. A future, stale,
                # or malformed numeric cursor resets to the current warming view.
                warming = projector.ticket_view(record)
                yield self._ticket_event(warming, seq=0)
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
