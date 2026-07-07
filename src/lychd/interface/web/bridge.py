"""`BridgeController` — Bridge page, session, send, SSE stream, consent, inspector.

The chat surface and the mature core the rest of the Altar is normalized to. `send`
launches a run via the single `RunEngine.submit()` law and returns the two sibling
turn fragments plus an out-of-band rail update (one wrapper template); `stream` maps
the run's `RunChannel` events to Server-Sent Events, rendering every payload through
the `Projector` (Projection Law); `consent` records the Magus's verdict and re-renders
the card (the honest park-and-resume seam lands in Wave 4).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, cast

from litestar import Controller, get, post
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate, HXLocation
from litestar.response import Redirect, Response, ServerSentEvent, ServerSentEventMessage, Template
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_303_SEE_OTHER,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from lychd.agents.router import Intent

# Runtime imports: Litestar resolves handler param/return annotations at registration.
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.runs import TERMINAL_STATUSES
from lychd.domain.web.altar_services import RunEngine
from lychd.domain.web.projection import Projector
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import SessionStorePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.web.schemas import ConsentCard
    from lychd.domain.web.sessions import SessionRecord

# Keepalive cadence: litestar's `ServerSentEvent` has NO `ping_interval` param
# (verified in .venv, saq/litestar), so a comment-event fallback keeps proxies open.
_SSE_KEEPALIVE_S = 15.0


def _parse_last_event_id(raw: str | None) -> int | None:
    """Parse a `Last-Event-ID` header (an event seq) to an int, or `None`."""
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


async def _terminal_stream(projector: Projector, run_id: str, status: str) -> AsyncIterator[ServerSentEventMessage]:
    """Synthesize a finite STATUS+DONE stream for an already-terminal run (F5/H4).

    A client that (re)connects after the run finished and its channel was dropped
    gets an immediate, honest resync — the settled status then the terminal — and the
    stream ends. It never subscribes to a minted-empty channel and never hangs.
    """
    status_event = RunEvent(run_id=run_id, seq=0, kind=RunEventKind.STATUS, data=status)
    done_event = RunEvent(run_id=run_id, seq=1, kind=RunEventKind.DONE, data=status)
    yield ServerSentEventMessage(event="status", data=await projector.project(status_event), id="0")
    yield ServerSentEventMessage(event="done", data=await projector.project(done_event), id="1")


class BridgeController(Controller):
    """Serve the Bridge page and all of its fragments, SSE, and consent endpoints."""

    path = "/bridge"

    @get("/", name="bridge:page", guards=[requires_scopes("altar:read")])
    async def page(
        self, bridge_sessions: SessionStorePort, consents: ConsentLedger, projector: Projector, state: State
    ) -> Template:
        """Render the Bridge over the newest session (or an empty shell)."""
        sessions = await bridge_sessions.list_sessions()
        session = sessions[0] if sessions else None
        cards = await self._pending_cards(consents, projector, state, session)
        return self._bridge_page(sessions, session, await consents.pending_count(), cards)

    @get("/{session_id:str}", name="bridge:session", guards=[requires_scopes("altar:read")])
    async def session_page(
        self,
        session_id: str,
        bridge_sessions: SessionStorePort,
        consents: ConsentLedger,
        projector: Projector,
        state: State,
    ) -> Template:
        """Render the Bridge over the selected session."""
        sessions = await bridge_sessions.list_sessions()
        session = await bridge_sessions.get_session(session_id)
        cards = await self._pending_cards(consents, projector, state, session)
        return self._bridge_page(sessions, session, await consents.pending_count(), cards)

    @post("/sessions", status_code=HTTP_200_OK, name="bridge:create", guards=[requires_scopes("runs:submit")])
    async def create_session(
        self,
        request: HTMXRequest,
        bridge_sessions: SessionStorePort,
    ) -> Response[Any]:
        """Open a new séance and steer the client onto it."""
        session = await bridge_sessions.create_session()
        target = f"/bridge/{session.id}"
        if request.htmx:
            return HXLocation(target, target="#altar-main", swap="innerHTML")
        return Redirect(target, status_code=HTTP_303_SEE_OTHER)

    @post("/{session_id:str}/messages", name="bridge:send", guards=[requires_scopes("runs:submit")])
    async def send(
        self,
        request: HTMXRequest,
        session_id: str,
        bridge_sessions: SessionStorePort,
        run_engine: RunEngine,
    ) -> Template | Response[str]:
        """Record the user turn, launch the run, and return the two turn fragments."""
        if not request.htmx:
            return Response(content="Bridge send is an HTMX-only endpoint.", status_code=HTTP_400_BAD_REQUEST)

        session = await bridge_sessions.get_session(session_id)
        if session is None:
            return Response(content="Unknown session.", status_code=HTTP_404_NOT_FOUND)

        form = await request.form()
        prompt = str(form.get("prompt", "")).strip()
        if not prompt:
            return Response(content="An empty offering cannot be spoken.", status_code=HTTP_400_BAD_REQUEST)

        # S3: the bridge no longer mints a `run_…` id. The run identity is the
        # ledger's to assign; `engine.submit` returns the canonical id on the handle,
        # and every downstream surface (this SSE slot, Step rows, stasis) uses it.
        await bridge_sessions.add_turn(session_id, BridgeTurn(role="user", content=prompt))
        handle = await run_engine.submit(Intent(session_id=session_id, prompt=prompt, source="bridge"))
        return HTMXTemplate(
            template_name="bridge/message_accepted.html.j2",
            context={
                "turn": BridgeTurn(role="user", content=prompt),
                "run_id": handle.run_id,
                "item": session,
                "current": True,
                "oob": True,
            },
        )

    @get("/runs/{run_id:str}/stream", name="bridge:stream", guards=[requires_scopes("altar:read")])
    async def stream(
        self,
        request: HTMXRequest,
        run_id: str,
        run_bus: InProcessEventBus,
        projector: Projector,
        state: State,
    ) -> ServerSentEvent:
        """Stream the run's events as SSE, rendered through the Projector.

        Ledger-first (F5/H4): consult the run ledger BEFORE subscribing so the stream
        never mints an empty channel that hangs on keepalives forever.
        - unknown run → 404;
        - already-terminal run → synthetic STATUS + DONE, then end;
        - live run → subscribe to its channel.

        Reconnect (A2-U5): a `Last-Event-ID` header replays events strictly after that
        seq over `RunChannel.subscribe(from_seq)`; a cursor that does not align with
        the live head yields a fresh STATUS resync (never silence, never an error). A
        keepalive comment fires on idle since litestar's `ServerSentEvent` has no
        `ping_interval`.
        """
        from_seq = _parse_last_event_id(request.headers.get("Last-Event-ID"))

        ledger = state.services.ledger
        run = await ledger.get(run_id)
        if run is None:
            raise NotFoundException(detail="Unknown run.")
        if run.status in TERMINAL_STATUSES:
            return ServerSentEvent(_terminal_stream(projector, run_id, run.status.value))

        async def events() -> AsyncIterator[ServerSentEventMessage]:
            source = run_bus.subscribe(run_id, from_seq=from_seq)
            pending: asyncio.Task[Any] | None = None
            try:
                while True:
                    if pending is None:
                        pending = asyncio.ensure_future(source.__anext__())
                    done, _ = await asyncio.wait({pending}, timeout=_SSE_KEEPALIVE_S)
                    if not done:  # idle: keep proxies open without dropping the queued item
                        yield ServerSentEventMessage(comment="keepalive")
                        continue
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        return
                    finally:
                        pending = None
                    yield ServerSentEventMessage(
                        event=str(event.kind),
                        data=await projector.project(event),
                        id=str(event.seq),
                    )
            finally:
                # F10: await the cancelled pending task before closing the generator, so
                # its subscriber queue is discarded (in `subscribe`'s finally) before we
                # walk away — no lingering entry in `RunChannel._subscribers`.
                if pending is not None:
                    pending.cancel()
                    with contextlib.suppress(BaseException):
                        await pending
                aclose = getattr(source, "aclose", None)
                if aclose is not None:
                    with contextlib.suppress(Exception):
                        await aclose()

        return ServerSentEvent(events())

    @post("/consents/{consent_id:str}", name="bridge:consent", guards=[requires_scopes("runs:approve")])
    async def consent(
        self,
        request: HTMXRequest,
        consent_id: str,
        consents: ConsentLedger,
        run_engine: RunEngine,
        projector: Projector,
    ) -> Template | Response[str]:
        """Record the Magus's verdict, resume the parked run, re-render the card.

        Ordering is load-bearing (C3): the verdict row commits (`consents.decide`)
        BEFORE `run_engine.approve` re-enqueues, so the resumed `AwaitConsent` always
        reads a non-None verdict. Idempotent: a settled verdict re-renders, never re-resolves.
        """
        if not request.htmx:
            return Response(content="Consent is an HTMX-only endpoint.", status_code=HTTP_400_BAD_REQUEST)

        view = await consents.get(consent_id)
        if view is None:
            return Response(content="Unknown consent.", status_code=HTTP_404_NOT_FOUND)

        if view.status != "pending":  # idempotent: settled verdicts re-render, never re-resolve
            return HTMXTemplate(
                template_name="bridge/consent_update.html.j2",
                context=await projector.consent_context(view),
            )

        form = await request.form()
        approved = str(form.get("verdict", "")) == "approve"
        sigil = cast("Sigil", request.user)  # the middleware Sigil (4C-1)
        decided = await consents.decide(consent_id, approved=approved, decided_by=sigil.name)
        await run_engine.approve(consent_id, approved=approved)  # AFTER the row commit — load-bearing
        return HTMXTemplate(
            template_name="bridge/consent_update.html.j2",
            context=await projector.consent_context(decided or view),
        )

    @get("/{session_id:str}/inspector", name="bridge:inspector", guards=[requires_scopes("altar:read")])
    async def inspector(
        self,
        session_id: str,
        bridge_sessions: SessionStorePort,
        consents: ConsentLedger,
    ) -> Template:
        """Render the contextual inspector for the selected session."""
        session = await bridge_sessions.get_session(session_id)
        return Template(
            template_name="bridge/inspector.html.j2",
            context={
                "session": session,
                "session_id": session_id,
                "pending": await consents.pending_count(),
            },
        )

    # -- helpers ----------------------------------------------------------

    async def _pending_cards(
        self,
        consents: ConsentLedger,
        projector: Projector,
        state: State,
        session: SessionRecord | None,
    ) -> list[ConsentCard]:
        """Still-pending consent cards belonging to the rendered session (restart re-render)."""
        if session is None:
            return []
        ledger = state.services.ledger
        cards: list[ConsentCard] = []
        for view in await consents.pending_views():
            run = await ledger.get(view.run_id)
            if run is not None and run.session_id == session.id:
                cards.append(projector.consent_card_view(view))
        return cards

    def _bridge_page(
        self,
        sessions: list[SessionRecord],
        session: SessionRecord | None,
        pending: int,
        pending_consents: list[ConsentCard],
    ) -> Template:
        return Template(
            template_name="altar/pages/bridge.html.j2",
            context={
                "active": "bridge",
                "pending": pending,
                "pending_consents": pending_consents,
                "sessions": sessions,
                "session": session,
                "turns": session.turns if session is not None else [],
            },
        )
