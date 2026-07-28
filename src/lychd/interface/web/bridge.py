"""Versioned Bridge JSON API and semantic run-event stream."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, cast

from litestar import Controller, Request, get, post
from litestar.datastructures import State
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException, ValidationException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from lychd.agents.router import Intent
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.cortex.engine import RunEngine
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunRecord, RunStatus
from lychd.domain.web.contracts import (
    BridgeSnapshot,
    BridgeTurnView,
    ConsentDecisionIntent,
    ConsentDecisionResult,
    MessageAccepted,
    MessageIntent,
    RunEventEnvelope,
    RunProjectionSnapshot,
    SessionCreated,
    SessionInspector,
    SessionSummary,
    SessionView,
)
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.schemas import BridgeTurn, ConsentCard
from lychd.domain.web.sessions import SessionRecord, SessionStorePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.codex.sigil import Sigil

_SSE_KEEPALIVE_S = 15.0


def _parse_last_event_id(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _turn_view(turn: BridgeTurn) -> BridgeTurnView:
    return BridgeTurnView(
        role=turn.role,
        content=turn.content,
        run_id=turn.run_id,
        state=turn.state,
        fragments=list(turn.fragments),
        created_at=turn.created_at,
    )


def _session_summary(session: SessionRecord) -> SessionSummary:
    return SessionSummary(id=session.id, title=session.title, created_at=session.created_at)


def _session_view(session: SessionRecord) -> SessionView:
    return SessionView(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        turns=[_turn_view(turn) for turn in session.turns],
    )


async def _terminal_stream(
    projector: EventProjector,
    run_id: str,
    status: str,
    *,
    from_seq: int | None,
    cursor: int,
) -> AsyncIterator[ServerSentEventMessage]:
    if from_seq is not None:
        reset_event = RunEvent(
            run_id=run_id,
            seq=max(cursor, 0),
            kind=RunEventKind.RESYNC,
            data="snapshot_required",
        )
        envelope = await projector.project(reset_event)
        yield ServerSentEventMessage(
            event=envelope.kind,
            data=envelope.model_dump_json(),
            id=str(envelope.seq),
        )
        return

    status_event = RunEvent(run_id=run_id, seq=0, kind=RunEventKind.STATUS, data=status)
    done_event = RunEvent(run_id=run_id, seq=1, kind=RunEventKind.DONE, data=status)
    for event in (status_event, done_event):
        envelope = await projector.project(event)
        yield ServerSentEventMessage(
            event=envelope.kind,
            data=envelope.model_dump_json(),
            id=str(envelope.seq),
        )


class BridgeController(Controller):
    """Serve the Bridge through one typed `/api/v1` contract."""

    path = "/api/v1/bridge"

    @get("", name="bridge:snapshot", operation_id="getBridgeSnapshot", guards=[requires_scopes("altar:read")])
    async def snapshot(
        self,
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> BridgeSnapshot:
        """Return the newest session or an empty reconstructable Bridge."""
        sessions = await bridge_sessions.list_sessions()
        session = sessions[0] if sessions else None
        return await self._snapshot(
            sessions,
            session,
            bridge_sessions,
            consents,
            run_bus,
            projector,
            state,
        )

    @get(
        "/sessions/{session_id:str}",
        name="bridge:session",
        operation_id="getBridgeSession",
        guards=[requires_scopes("altar:read")],
    )
    async def session_snapshot(
        self,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> BridgeSnapshot:
        """Return one selected session and the full session rail."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        return await self._snapshot(
            await bridge_sessions.list_sessions(),
            session,
            bridge_sessions,
            consents,
            run_bus,
            projector,
            state,
        )

    @post(
        "/sessions",
        status_code=HTTP_201_CREATED,
        name="bridge:create",
        operation_id="createBridgeSession",
        guards=[requires_scopes("runs:submit")],
    )
    async def create_session(
        self,
        bridge_sessions: NamedDependency[SessionStorePort],
    ) -> SessionCreated:
        """Open a new séance and return its typed identity."""
        return SessionCreated(session=_session_view(await bridge_sessions.create_session()))

    @post(
        "/sessions/{session_id:str}/messages",
        status_code=HTTP_200_OK,
        name="bridge:send",
        operation_id="sendBridgeMessage",
        guards=[requires_scopes("runs:submit")],
    )
    async def send(
        self,
        request: Request[Any, Any, Any],
        data: MessageIntent,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        run_engine: NamedDependency[RunEngine],
    ) -> MessageAccepted:
        """Record a complete text command and admit one run."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        prompt = data.prompt.strip()
        if not prompt:
            raise ValidationException(detail="An empty offering cannot be spoken.")

        turn = BridgeTurn(role="user", content=prompt)
        await bridge_sessions.add_turn(session_id, turn)
        sigil = cast("Sigil", request.user)
        handle = await run_engine.submit(
            Intent(
                session_id=session_id,
                prompt=prompt,
                source="bridge",
                sigil_name=sigil.name,
                sigil_scopes=frozenset(sigil.scopes),
            )
        )
        return MessageAccepted(run_id=handle.run_id, turn=_turn_view(turn))

    @get(
        "/runs/{run_id:str}",
        name="bridge:run-snapshot",
        operation_id="getBridgeRunSnapshot",
        guards=[requires_scopes("altar:read")],
    )
    async def run_snapshot(
        self,
        run_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> RunProjectionSnapshot:
        """Return one replaceable run projection at an exact stream cursor."""
        run = await state.services.ledger.get(run_id)
        if run is None:
            raise NotFoundException(detail="Unknown run.")

        return await self._run_projection(
            run,
            bridge_sessions,
            run_bus,
            projector,
            state,
        )

    async def _run_projection(
        self,
        run: RunRecord,
        bridge_sessions: SessionStorePort,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> RunProjectionSnapshot:
        live = run_bus.snapshot(run.run_id)
        if live is not None:
            fragments = [(await projector.project(fragment)).payload for fragment in live.fragments]
            return RunProjectionSnapshot(
                session_id=run.session_id,
                run_id=run.run_id,
                cursor=live.cursor,
                content=live.content,
                status=live.status,
                fragments=fragments,
                terminal=live.terminal,
            )

        turn = await bridge_sessions.settled_turn_for_run(run.run_id)
        return RunProjectionSnapshot(
            session_id=run.session_id,
            run_id=run.run_id,
            cursor=(await state.services.ledger.next_seq(run.run_id)) - 1,
            content=turn.content if turn is not None else "",
            status=run.status.value,
            fragments=[],
            terminal=run.status in TERMINAL_STATUSES,
        )

    @get(
        "/runs/{run_id:str}/events",
        name="bridge:events",
        operation_id="streamBridgeRunEvents",
        guards=[requires_scopes("altar:read")],
        responses={
            HTTP_200_OK: ResponseSpec(
                RunEventEnvelope,
                generate_examples=False,
                media_type="text/event-stream",
                description="Versioned semantic run events.",
            ),
        },
    )
    async def events(
        self,
        request: Request[Any, Any, Any],
        run_id: FromPath[str],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> ServerSentEvent:
        """Stream versioned JSON envelopes with replay and terminal synthesis."""
        from_seq = _parse_last_event_id(request.headers.get("Last-Event-ID"))
        run = await state.services.ledger.get(run_id)
        if run is None:
            raise NotFoundException(detail="Unknown run.")
        if run.status in TERMINAL_STATUSES:
            return ServerSentEvent(
                _terminal_stream(
                    projector,
                    run_id,
                    run.status.value,
                    from_seq=from_seq,
                    cursor=(await state.services.ledger.next_seq(run_id)) - 1,
                ),
            )

        async def stream() -> AsyncIterator[ServerSentEventMessage]:
            source = run_bus.subscribe(run_id, from_seq=from_seq)
            pending: asyncio.Task[Any] | None = None
            try:
                while True:
                    if pending is None:
                        pending = asyncio.ensure_future(source.__anext__())
                    done, _ = await asyncio.wait({pending}, timeout=_SSE_KEEPALIVE_S)
                    if not done:
                        yield ServerSentEventMessage(comment="keepalive")
                        continue
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        return
                    finally:
                        pending = None
                    envelope = await projector.project(event)
                    yield ServerSentEventMessage(
                        event=envelope.kind,
                        data=envelope.model_dump_json(),
                        id=str(envelope.seq),
                    )
            finally:
                if pending is not None:
                    pending.cancel()
                    with contextlib.suppress(BaseException):
                        await pending
                aclose = getattr(source, "aclose", None)
                if aclose is not None:
                    with contextlib.suppress(Exception):
                        await aclose()

        return ServerSentEvent(stream())

    @post(
        "/consents/{consent_id:str}/decision",
        status_code=HTTP_200_OK,
        name="bridge:consent",
        operation_id="decideBridgeConsent",
        guards=[requires_scopes("runs:approve")],
    )
    async def consent(
        self,
        request: Request[Any, Any, Any],
        data: ConsentDecisionIntent,
        consent_id: FromPath[str],
        consents: NamedDependency[ConsentLedger],
        run_engine: NamedDependency[RunEngine],
        projector: NamedDependency[EventProjector],
    ) -> ConsentDecisionResult:
        """Commit one idempotent verdict before re-admitting the parked run."""
        view = await consents.get(consent_id)
        if view is None:
            raise NotFoundException(detail="Unknown consent.")
        if view.status == "pending":
            approved = data.verdict == "approve"
            sigil = cast("Sigil", request.user)
            decided = await consents.decide(consent_id, approved=approved, decided_by=sigil.name)
            await run_engine.approve(consent_id, approved=approved)
            view = decided or view
        return ConsentDecisionResult(
            consent=projector.consent_card_view(view),
            pending_count=await consents.pending_count(),
        )

    @get(
        "/sessions/{session_id:str}/inspector",
        name="bridge:inspector",
        operation_id="getBridgeSessionInspector",
        guards=[requires_scopes("altar:read")],
    )
    async def inspector(
        self,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
    ) -> SessionInspector:
        """Return a compact contextual inspector."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        return SessionInspector(
            session_id=session_id,
            title=session.title,
            turn_count=len(session.turns),
            pending_count=await consents.pending_count(),
        )

    async def _snapshot(
        self,
        sessions: list[SessionRecord],
        session: SessionRecord | None,
        bridge_sessions: SessionStorePort,
        consents: ConsentLedger,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> BridgeSnapshot:
        return BridgeSnapshot(
            sessions=[_session_summary(item) for item in sessions],
            session=_session_view(session) if session is not None else None,
            active_runs=await self._active_run_projections(
                session,
                bridge_sessions,
                run_bus,
                projector,
                state,
            ),
            pending_consents=await self._pending_cards(consents, projector, state, session),
            pending_count=await consents.pending_count(),
        )

    async def _active_run_projections(
        self,
        session: SessionRecord | None,
        bridge_sessions: SessionStorePort,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> list[RunProjectionSnapshot]:
        """Project the selected session's runs whose event channels live here."""
        if session is None:
            return []

        active: dict[str, RunRecord] = {}
        for status in RunStatus:
            if status not in TERMINAL_STATUSES:
                for run in await state.services.ledger.list_by_status(status):
                    active[run.run_id] = run

        projections: list[RunProjectionSnapshot] = []
        for run in sorted(active.values(), key=lambda item: item.created_at):
            if run.session_id != session.id or run_bus.snapshot(run.run_id) is None:
                continue
            projections.append(
                await self._run_projection(
                    run,
                    bridge_sessions,
                    run_bus,
                    projector,
                    state,
                ),
            )
        return projections

    async def _pending_cards(
        self,
        consents: ConsentLedger,
        projector: EventProjector,
        state: State,
        session: SessionRecord | None,
    ) -> list[ConsentCard]:
        if session is None:
            return []
        cards: list[ConsentCard] = []
        for view in await consents.pending_views():
            run = await state.services.ledger.get(view.run_id)
            if run is not None and run.session_id == session.id:
                cards.append(projector.consent_card_view(view))
        return cards
