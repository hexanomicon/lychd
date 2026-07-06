"""`BridgeController` — Bridge page, session, send, SSE stream, consent, inspector.

The chat surface and the mature core the rest of the Altar is normalized to. `send`
launches a run via the single `RunEngine.submit()` law and returns the two sibling
turn fragments plus an out-of-band rail update (one wrapper template); `stream` maps
the run's `RunChannel` events to Server-Sent Events, rendering every payload through
the `Projector` (Projection Law); `consent` records the Magus's verdict and re-renders
the card (the honest park-and-resume seam lands in Wave 4).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from litestar import Controller, get, post
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
from lychd.domain.web.altar_services import RunEngine
from lychd.domain.web.projection import Projector
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.web.sessions import SessionRecord


def _new_run_id() -> str:
    """Return a fresh run id."""
    return f"run_{uuid.uuid4().hex[:12]}"


class BridgeController(Controller):
    """Serve the Bridge page and all of its fragments, SSE, and consent endpoints."""

    path = "/bridge"

    @get("/", name="bridge:page")
    async def page(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bridge over the newest session (or an empty shell)."""
        sessions = bridge_sessions.list_sessions()
        session = sessions[0] if sessions else None
        return self._bridge_page(bridge_sessions, sessions, session)

    @get("/{session_id:str}", name="bridge:session")
    async def session_page(self, session_id: str, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bridge over the selected session."""
        sessions = bridge_sessions.list_sessions()
        session = bridge_sessions.get_session(session_id)
        return self._bridge_page(bridge_sessions, sessions, session)

    @post("/sessions", status_code=HTTP_200_OK, name="bridge:create")
    async def create_session(
        self,
        request: HTMXRequest,
        bridge_sessions: BridgeSessionStore,
    ) -> Response[Any]:
        """Open a new séance and steer the client onto it."""
        session = bridge_sessions.create_session()
        target = f"/bridge/{session.id}"
        if request.htmx:
            return HXLocation(target, target="#altar-main", swap="innerHTML")
        return Redirect(target, status_code=HTTP_303_SEE_OTHER)

    @post("/{session_id:str}/messages", name="bridge:send")
    async def send(
        self,
        request: HTMXRequest,
        session_id: str,
        bridge_sessions: BridgeSessionStore,
        run_engine: RunEngine,
    ) -> Template | Response[str]:
        """Record the user turn, launch the run, and return the two turn fragments."""
        if not request.htmx:
            return Response(content="Bridge send is an HTMX-only endpoint.", status_code=HTTP_400_BAD_REQUEST)

        session = bridge_sessions.get_session(session_id)
        if session is None:
            return Response(content="Unknown session.", status_code=HTTP_404_NOT_FOUND)

        form = await request.form()
        prompt = str(form.get("prompt", "")).strip()
        if not prompt:
            return Response(content="An empty offering cannot be spoken.", status_code=HTTP_400_BAD_REQUEST)

        run_id = _new_run_id()
        bridge_sessions.add_turn(session_id, BridgeTurn(role="user", content=prompt))
        handle = await run_engine.submit(Intent(session_id=session_id, run_id=run_id, prompt=prompt, source="bridge"))
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

    @get("/runs/{run_id:str}/stream", name="bridge:stream")
    async def stream(
        self,
        run_id: str,
        bridge_sessions: BridgeSessionStore,
        projector: Projector,
    ) -> ServerSentEvent:
        """Stream the run's channel as SSE, rendering every payload through the Projector."""
        channel = bridge_sessions.channel(run_id)

        async def events() -> AsyncIterator[ServerSentEventMessage]:
            async for event in channel.subscribe():
                yield ServerSentEventMessage(
                    event=event.kind,
                    data=projector.project(event),
                    id=str(event.seq),
                )

        return ServerSentEvent(events())

    @post("/consents/{consent_id:str}", name="bridge:consent")
    async def consent(
        self,
        request: HTMXRequest,
        consent_id: str,
        bridge_sessions: BridgeSessionStore,
        projector: Projector,
    ) -> Template | Response[str]:
        """Record the Magus's verdict and re-render the consent card + OOB sigil.

        The honest park-and-resume path (`engine.approve` re-enqueues the run) lands
        in Wave 4 (spec-00-FINAL C3); here the verdict is recorded and rendered.
        """
        if not request.htmx:
            return Response(content="Consent is an HTMX-only endpoint.", status_code=HTTP_400_BAD_REQUEST)

        record = bridge_sessions.get_consent(consent_id)
        if record is None:
            return Response(content="Unknown consent.", status_code=HTTP_404_NOT_FOUND)

        # Idempotency: a settled verdict re-renders, it never re-resolves.
        if record.status != "pending_consent":
            return HTMXTemplate(
                template_name="bridge/consent_update.html.j2",
                context=projector.consent_context(record),
            )

        form = await request.form()
        approved = str(form.get("verdict", "")) == "approve"
        updated = bridge_sessions.resolve_consent(consent_id, approved=approved) or record
        return HTMXTemplate(
            template_name="bridge/consent_update.html.j2",
            context=projector.consent_context(updated),
        )

    @get("/{session_id:str}/inspector", name="bridge:inspector")
    async def inspector(
        self,
        session_id: str,
        bridge_sessions: BridgeSessionStore,
    ) -> Template:
        """Render the contextual inspector for the selected session."""
        session = bridge_sessions.get_session(session_id)
        return Template(
            template_name="bridge/inspector.html.j2",
            context={
                "session": session,
                "session_id": session_id,
                "pending": bridge_sessions.pending_consent_count(),
            },
        )

    # -- helpers ----------------------------------------------------------

    def _bridge_page(
        self,
        bridge_sessions: BridgeSessionStore,
        sessions: list[SessionRecord],
        session: SessionRecord | None,
    ) -> Template:
        return Template(
            template_name="altar/pages/bridge.html.j2",
            context={
                "active": "bridge",
                "pending": bridge_sessions.pending_consent_count(),
                "sessions": sessions,
                "session": session,
                "turns": session.turns if session is not None else [],
            },
        )
