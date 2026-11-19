"""Versioned Nexus JSON API and transition event stream."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any

from litestar import Controller, Request, get, post
from litestar.datastructures import CacheControlHeader, State
from litestar.di import NamedDependency
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
    ValidationException,
)
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, FromQuery
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_202_ACCEPTED, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_503_SERVICE_UNAVAILABLE

from lychd.config.logging import PRIVATE_CONTENT_LOG_OPT
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.priority import PRIORITY_MAX
from lychd.domain.intercom.presence import PresenceBoard, PresenceIntent
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan, TransitionTrace
from lychd.domain.web.contracts import (
    DelegatedRuntimeObservation,
    FrameworkError,
    NexusOperator,
    NexusSnapshot,
    SwapAccepted,
    SwapIntent,
    TransitionEventEnvelope,
    TransitionRecordView,
)
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.schemas import SwapTicket, build_nexus_board
from lychd.domain.web.swap_requests import SwapRequestLedger
from lychd.domain.web.tickets import TicketCapacityError, TicketRecord, TicketStore
from lychd.system.services.colleague_presence import AudienceChangedError, ColleaguePresence

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

    @get(
        "",
        name="nexus:snapshot",
        operation_id="getNexusSnapshot",
        guards=[requires_scopes("altar:read")],
        opt={PRIVATE_CONTENT_LOG_OPT: True},
        cache_control=CacheControlHeader(no_store=True),
    )
    async def snapshot(
        self,
        request: Request[Any, Any, Any],
        orchestrator: NamedDependency[OrchestratorManager],
        registry: NamedDependency[AnimatorRegistry],
        state: State,
    ) -> NexusSnapshot:
        """Return the current capability board."""
        delegated_runtimes: list[DelegatedRuntimeObservation] = []
        for registration in getattr(state.services, "delegated_runtime_catalog", ()):
            definition = registration.definition
            delegated_runtimes.append(
                DelegatedRuntimeObservation(
                    runtime_id=definition.runtime_id,
                    display_name=definition.display_name,
                    registrant_id=registration.registrant_id,
                    transport="reference",
                    delivery="available",
                    runnable=True,
                    coffin_profiles=[],
                    provider_gate="not_required",
                    capacity_posture="not_configured",
                    limitations=list(definition.limitations),
                )
            )
        presence: ColleaguePresence | None = getattr(state, "colleague_presence", None)
        return NexusSnapshot(
            snapshot_at=datetime.now(UTC),
            configuration=getattr(state.services, "nexus_configuration", None),
            operator=(
                NexusOperator(subject=request.auth.subject, sigil=request.user.name, scopes=sorted(request.user.scopes))
                if isinstance(request.auth, LocalOperatorAuthentication) and isinstance(request.user, Sigil)
                else None
            ),
            board=build_nexus_board(orchestrator, registry),
            containment_reason=orchestrator.containment_reason,
            transitions=[_transition_view(record) for record in orchestrator.transitions.recent()],
            delegated_runtimes=delegated_runtimes,
            presence=presence.board() if presence is not None else None,
        )

    @post(
        "/presence",
        status_code=200,
        name="nexus:presence",
        operation_id="setNexusPresence",
        opt={PRIVATE_CONTENT_LOG_OPT: True},
        cache_control=CacheControlHeader(no_store=True),
        guards=[requires_scopes("nexus:share-presence")],
    )
    async def set_presence(self, request: Request[Any, Any, Any], data: PresenceIntent, state: State) -> PresenceBoard:
        """Share a coarse availability choice with the displayed paired audience."""
        presence: ColleaguePresence | None = getattr(state, "colleague_presence", None)
        if presence is None:
            raise NotFoundException(detail="No colleagues are paired for presence.")
        access = getattr(state, "local_operator_access", None)
        if not isinstance(access, LocalOperatorAccess) or not access.current(request.auth):
            raise PermissionDeniedException(detail="Current local operator authority is required.")
        try:
            return await presence.choose(data, permitted=partial(access.current, request.auth))
        except AudienceChangedError as exc:
            raise ClientException(
                detail="Refresh Nexus to see the current audience.", status_code=HTTP_409_CONFLICT
            ) from exc

    @get(
        "/plan",
        name="nexus:plan",
        operation_id="getNexusPlan",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
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
        responses={
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_409_CONFLICT: ResponseSpec(
                FrameworkError,
                generate_examples=False,
                description="The durable request was already admitted but its process-local ticket is unavailable.",
            ),
            HTTP_503_SERVICE_UNAVAILABLE: ResponseSpec(
                FrameworkError,
                generate_examples=False,
                description="Process-local transition ticket capacity is temporarily exhausted.",
            ),
        },
    )
    async def swap(
        self,
        data: SwapIntent,
        orchestrator: NamedDependency[OrchestratorManager],
        tickets: NamedDependency[TicketStore],
        swap_requests: NamedDependency[SwapRequestLedger],
        projector: NamedDependency[EventProjector],
    ) -> SwapAccepted:
        """Launch one caller-identified transition and return its process-local ticket."""
        existing = tickets.get_by_request_id(data.request_id)
        if existing is not None:
            return self._repeat_swap(existing, target=data.target, projector=projector)
        try:
            plan = await orchestrator.calculate_transition_plan(data.target)
        except ValueError as exc:
            raise NotFoundException(detail=f"Unknown capability target: {data.target}") from exc
        # The planner is asynchronous. Recheck after it yields so two concurrent
        # retries cannot both cross the launch boundary for one request identity.
        existing = tickets.get_by_request_id(data.request_id)
        if existing is not None:
            return self._repeat_swap(existing, target=data.target, projector=projector)
        try:
            tickets.reserve_capacity(data.request_id)
        except TicketCapacityError as exc:
            raise ServiceUnavailableException(detail=str(exc)) from exc
        try:
            claim = await swap_requests.claim(request_id=data.request_id, target=data.target)
            if claim.target != data.target:
                raise ValidationException(
                    detail=(f"Transition request {data.request_id!r} already names target {claim.target!r}.")
                )
            if not claim.created:
                # The durable admission may outlive its process-local ticket. Never
                # translate missing projection state into a second physical mutation.
                existing = tickets.get_by_request_id(data.request_id)
                if existing is not None:
                    return self._repeat_swap(existing, target=data.target, projector=projector)
                raise ClientException(
                    detail=(
                        f"Transition request {data.request_id!r} was already admitted; "
                        "its process-local ticket is no longer available and no transition was relaunched."
                    ),
                    status_code=HTTP_409_CONFLICT,
                )
            trace = TransitionTrace(
                target_capability_key=data.target,
                priority=float(PRIORITY_MAX),
                request_id=data.request_id,
            )
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
                    reservation=data.request_id,
                )
            except TicketCapacityError as exc:  # reservation invariant guard
                raise ServiceUnavailableException(detail=str(exc)) from exc
            return SwapAccepted(ticket=projector.ticket_view(record))
        finally:
            tickets.release_capacity(data.request_id)

    @classmethod
    def _repeat_swap(
        cls,
        record: TicketRecord,
        *,
        target: str,
        projector: EventProjector,
    ) -> SwapAccepted:
        """Return the first launch or reject semantic reuse of its identity."""
        if record.target != target:
            raise ValidationException(
                detail=(f"Transition request {record.trace.request_id!r} already names target {record.target!r}.")
            )
        return SwapAccepted(ticket=cls._ticket(record, projector))

    @get(
        "/swaps/{ticket_id:str}",
        name="nexus:ticket",
        operation_id="getNexusSwap",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
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
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
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
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
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
