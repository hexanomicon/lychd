"""`AltarController` — the root redirect and the unbuilt skeleton shells.

Each live instrument (Bridge, Nexus, Loom) now owns its own full page and fragments;
`AltarController` shrinks to `/` plus the honest `data-state="unbuilt"` placeholders
for the instruments not yet built (Scrying, Reliquary, Bindings).
"""

from __future__ import annotations

from typing import Any

from litestar import Controller, get
from litestar.response import Redirect, Response, Template
from litestar.status_codes import HTTP_302_FOUND

# Runtime import: Litestar resolves handler param annotations at registration.
from lychd.domain.web.sessions import BridgeSessionStore


class AltarController(Controller):
    """Serve the root redirect and the unbuilt-instrument skeleton shells."""

    @get("/", name="altar:index")
    async def index(self) -> Response[Any]:
        """Redirect the bare root to the Bridge (the resident instrument)."""
        return Redirect("/bridge", status_code=HTTP_302_FOUND)

    @get("/scrying", name="altar:scrying")
    async def scrying(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Scrying skeleton shell."""
        return self._skeleton("scrying", bridge_sessions)

    @get("/reliquary", name="altar:reliquary")
    async def reliquary(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Reliquary skeleton shell."""
        return self._skeleton("reliquary", bridge_sessions)

    @get("/bindings", name="altar:bindings")
    async def bindings(self, bridge_sessions: BridgeSessionStore) -> Template:
        """Render the Bindings skeleton shell."""
        return self._skeleton("bindings", bridge_sessions)

    def _skeleton(self, slug: str, bridge_sessions: BridgeSessionStore) -> Template:
        return Template(
            template_name=f"altar/pages/{slug}.html.j2",
            context={"active": slug, "pending": bridge_sessions.pending_consent_count()},
        )
