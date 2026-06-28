"""`AltarController` — the instrument pages (routes 1, 2, 3, 9, 14, 17).

Pages render inside `altar/base.html.j2`. The Bridge/Nexus/Loom pages are static
shells whose live regions self-populate over HTMX; Scrying/Reliquary/Bindings are
skeleton shells for the unbuilt instruments.
"""

from __future__ import annotations

from typing import Any

from litestar import Controller, get
from litestar.response import Redirect, Response, Template
from litestar.status_codes import HTTP_302_FOUND

from lychd.agents.workflows import WORKFLOWS
from lychd.domain.web.schemas import build_loom_view
from lychd.domain.web.sessions import BridgeSessionStore, SessionRecord


class AltarController(Controller):
    """Serve the Altar's instrument pages within the shared shell."""

    @get("/")
    async def index(self) -> Response[Any]:
        """Redirect the bare root to the Bridge (the resident instrument)."""
        return Redirect("/bridge", status_code=HTTP_302_FOUND)

    @get("/bridge")
    async def bridge(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bridge over the newest session (or an empty shell)."""
        sessions = bridge_sessions.list_sessions()
        session = sessions[0] if sessions else None
        return self._bridge_page(bridge_sessions, sessions, session)

    @get("/bridge/{session_id:str}")
    async def bridge_session(self, session_id: str, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bridge over the selected session."""
        sessions = bridge_sessions.list_sessions()
        session = bridge_sessions.get_session(session_id)
        return self._bridge_page(bridge_sessions, sessions, session)

    @get("/nexus")
    async def nexus(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Nexus page; the coven board self-loads over HTMX."""
        return Template(
            template_name="altar/pages/nexus.html.j2",
            context={"active": "nexus", "pending": bridge_sessions.pending_consent_count()},
        )

    @get("/loom")
    async def loom(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Loom with the first workflow pre-selected."""
        workflow = WORKFLOWS[0]
        return Template(
            template_name="altar/pages/loom.html.j2",
            context={
                "active": "loom",
                "pending": bridge_sessions.pending_consent_count(),
                "workflows": WORKFLOWS,
                "view": build_loom_view(workflow),
                "selected": workflow.name,
            },
        )

    @get("/scrying")
    async def scrying(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Scrying skeleton shell."""
        return self._skeleton("scrying", bridge_sessions)

    @get("/reliquary")
    async def reliquary(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Reliquary skeleton shell."""
        return self._skeleton("reliquary", bridge_sessions)

    @get("/bindings")
    async def bindings(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bindings skeleton shell."""
        return self._skeleton("bindings", bridge_sessions)

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

    def _skeleton(self, slug: str, bridge_sessions: BridgeSessionStore) -> Template:
        return Template(
            template_name=f"altar/pages/{slug}.html.j2",
            context={"active": slug, "pending": bridge_sessions.pending_consent_count()},
        )
