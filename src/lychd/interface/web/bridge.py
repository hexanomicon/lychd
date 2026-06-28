"""`BridgeController` — session, send, SSE stream, consent, inspector (routes 4-8).

The chat surface. `send` launches a run via the single `submit()` law and returns
the two sibling turn fragments plus an out-of-band rail update; `stream` maps the
run's `RunChannel` events to Server-Sent Events, rendering every payload
server-side (Projection Law); `consent` resolves a parked, approval-bearing tool
call in-process (Live path).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from litestar import Controller, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import State
from litestar.enums import MediaType
from litestar.plugins.htmx import HTMXRequest, HXLocation
from litestar.response import Redirect, Response, ServerSentEvent, ServerSentEventMessage, Template
from litestar.status_codes import HTTP_303_SEE_OTHER, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pydantic_ai.tools import DeferredToolResults

from lychd.agents.router import Intent, submit
from lychd.agents.workflows.bridge_chat import default_sigil
from lychd.domain.cortex.stasis import RunEvent
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.web.fragments import FragmentRegistry, ValidatedFragment
from lychd.domain.web.schemas import BridgeTurn, ConsentCard
from lychd.domain.web.sessions import BridgeSessionStore, ConsentRecord

_SWAP_TOOL = "request_coven_swap"


def _new_run_id() -> str:
    """Return a fresh run id."""
    return f"run_{uuid.uuid4().hex[:12]}"


def _render(engine: JinjaTemplateEngine, name: str, context: dict[str, Any]) -> str:
    """Render a Jinja template to an HTML string (autoescaped)."""
    return engine.get_template(name).render(context)


def _consent_card_from_record(record: ConsentRecord) -> ConsentCard:
    """Build the Seat-of-Consent view-model from a parked consent record."""
    vision = str(record.args.get("reason") or "This action requires the Magus's consent before it may proceed.")
    return ConsentCard(
        id=record.id,
        run_id=record.run_id,
        session_id=record.session_id,
        tool_name=record.tool_name,
        args=record.args,
        vision=vision,
        state=record.status,
    )


class BridgeController(Controller):
    """Serve the Bridge chat endpoints (create, send, stream, consent, inspect)."""

    path = "/bridge"

    @post("/sessions")
    async def create_session(
        self,
        request: HTMXRequest,
        bridge_sessions: BridgeSessionStore,
    ) -> Response[Any]:
        """Open a new séance and steer the client onto it."""
        session = bridge_sessions.create_session()
        if request.htmx:
            return HXLocation(f"/bridge/{session.id}", target="#altar-main", swap="innerHTML")
        return Redirect(f"/bridge/{session.id}", status_code=HTTP_303_SEE_OTHER)

    @post("/{session_id:str}/messages")
    async def send(
        self,
        request: HTMXRequest,
        session_id: str,
        state: State,
        bridge_sessions: BridgeSessionStore,
    ) -> Response[str]:
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

        intent = Intent(session_id=session_id, run_id=run_id, prompt=prompt, source="bridge")
        await submit(intent, state=state)

        engine = self._engine(request)
        user_html = _render(engine, "bridge/turn_user.html.j2", {"turn": BridgeTurn(role="user", content=prompt)})
        slot_html = _render(engine, "bridge/stream_slot.html.j2", {"run_id": run_id})
        rail_html = _render(
            engine,
            "bridge/session_rail.html.j2",
            {"item": session, "current": True, "oob": True},
        )
        return Response(content=user_html + slot_html + rail_html, media_type=MediaType.HTML)

    @get("/runs/{run_id:str}/stream")
    async def stream(
        self,
        request: HTMXRequest,
        run_id: str,
        bridge_sessions: BridgeSessionStore,
        fragments: FragmentRegistry,
    ) -> ServerSentEvent:
        """Stream the run's channel as SSE, rendering every payload server-side."""
        engine = self._engine(request)
        channel = bridge_sessions.channel(run_id)

        async def events() -> AsyncIterator[ServerSentEventMessage]:
            async for event in channel.subscribe():
                data = self._render_event(event, engine=engine, fragments=fragments, sessions=bridge_sessions)
                yield ServerSentEventMessage(event=event.kind, data=data, id=str(event.seq))

        return ServerSentEvent(events())

    @post("/consents/{consent_id:str}")
    async def consent(
        self,
        request: HTMXRequest,
        consent_id: str,
        bridge_sessions: BridgeSessionStore,
        orchestrator: OrchestratorManager,
    ) -> Response[Any]:
        """Resolve a parked consent; on approval, enact the swap and jump to Nexus."""
        if not request.htmx:
            return Response(content="Consent is an HTMX-only endpoint.", status_code=HTTP_400_BAD_REQUEST)

        record = bridge_sessions.get_consent(consent_id)
        if record is None:
            return Response(content="Unknown consent.", status_code=HTTP_404_NOT_FOUND)

        form = await request.form()
        approved = str(form.get("verdict", "")) == "approve"

        # The privileged effect is gated on the Sigil scope the tool declares
        # (`request_coven_swap` requires `nexus:swap`). Until the honest deferred-tool
        # resume lands (P2/M2.1) the tool body never runs on this path, so the scope
        # MUST be enforced here or an approval would bypass authorization.
        enact_swap = approved and record.tool_name == _SWAP_TOOL
        if enact_swap and "nexus:swap" not in default_sigil().scopes:
            enact_swap = False
            approved = False

        # Build the DeferredToolResults that encodes the verdict. The current graph
        # settles with a placeholder rather than truly pausing, so a real in-process
        # agent-run resume is future (Durable/HitL) work; here the verdict is honoured
        # by enacting the tool's effect directly on the Live path.
        call = record.requests.approvals[0] if record.requests.approvals else None
        if call is not None:
            _results = DeferredToolResults(approvals={call.tool_call_id: approved})

        bridge_sessions.resolve_consent(consent_id, approved=approved)

        if enact_swap:
            target = str(record.args.get("capability_key", ""))
            if target:
                _ = asyncio.create_task(  # noqa: RUF006  # fire-and-forget Live-path transition
                    orchestrator.request_transition(target, priority=50.0),
                    name=f"consent-swap:{consent_id}",
                )
            return HXLocation("/nexus", target="#altar-main", swap="innerHTML")

        engine = self._engine(request)
        card = _consent_card_from_record(record)
        card_html = _render(engine, "bridge/consent_card.html.j2", {"consent": card})
        sigil_html = _render(
            engine,
            "altar/partials/consent_sigil.html.j2",
            {"pending": bridge_sessions.pending_consent_count(), "oob": True},
        )
        return Response(content=card_html + sigil_html, media_type=MediaType.HTML)

    @get("/{session_id:str}/inspector")
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

    def _engine(self, request: HTMXRequest) -> JinjaTemplateEngine:
        engine = cast("JinjaTemplateEngine | None", request.app.template_engine)
        if engine is None:  # pragma: no cover - template config is always present
            msg = "Template engine is not configured."
            raise RuntimeError(msg)
        return engine

    def _render_event(
        self,
        event: RunEvent,
        *,
        engine: JinjaTemplateEngine,
        fragments: FragmentRegistry,
        sessions: BridgeSessionStore,
    ) -> str:
        """Render one run event's SSE payload (already-escaped tokens pass through)."""
        if event.kind in {"token", "status"}:
            return event.payload
        if event.kind == "fragment":
            return self._render_fragment(event.payload, engine=engine, fragments=fragments)
        if event.kind == "consent":
            record = sessions.get_consent(event.payload)
            if record is None:
                return ""
            card_html = _render(engine, "bridge/consent_card.html.j2", {"consent": _consent_card_from_record(record)})
            sigil_html = _render(
                engine,
                "altar/partials/consent_sigil.html.j2",
                {"pending": sessions.pending_consent_count(), "oob": True},
            )
            return card_html + sigil_html
        # done: replace the whole streaming slot with the settled turn.
        session = self._session_of_run(sessions, event.run_id)
        turn = self._settled_turn(session, event.run_id)
        return _render(engine, "bridge/turn_agent.html.j2", {"turn": turn, "oob": True})

    def _render_fragment(
        self,
        payload: str,
        *,
        engine: JinjaTemplateEngine,
        fragments: FragmentRegistry,
    ) -> str:
        parsed = json.loads(payload)
        definition = fragments.get(str(parsed.get("key", "")))
        if definition is None:
            return ""
        params = definition.params_model.model_validate(parsed.get("params", {}))
        validated = ValidatedFragment(key=definition.key, template=definition.template, params=params)
        return fragments.render(validated, engine=engine)

    def _session_of_run(self, sessions: BridgeSessionStore, run_id: str) -> Any:
        for session in sessions.list_sessions():
            if any(turn.run_id == run_id for turn in session.turns):
                return session
        return None

    def _settled_turn(self, session: Any, run_id: str) -> BridgeTurn:
        if session is not None:
            for turn in reversed(session.turns):
                if turn.run_id == run_id and turn.role == "agent":
                    return turn
        return BridgeTurn(role="agent", content="The turn has settled.", run_id=run_id, state="settled")
