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
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger


class AltarController(Controller):
    """Serve the root redirect and the unbuilt-instrument skeleton shells."""

    @get("/", name="altar:index")
    async def index(self) -> Response[Any]:
        """Redirect the bare root to the Bridge (the resident instrument)."""
        return Redirect("/bridge", status_code=HTTP_302_FOUND)

    @get("/scrying", name="altar:scrying", guards=[requires_scopes("altar:read")])
    async def scrying(self, consents: ConsentLedger) -> Template:
        """Render the Scrying skeleton shell."""
        return await self._skeleton("scrying", consents)

    @get("/reliquary", name="altar:reliquary", guards=[requires_scopes("altar:read")])
    async def reliquary(self, consents: ConsentLedger) -> Template:
        """Render the Reliquary skeleton shell."""
        return await self._skeleton("reliquary", consents)

    @get("/bindings", name="altar:bindings", guards=[requires_scopes("altar:read")])
    async def bindings(self, consents: ConsentLedger) -> Template:
        """Render the Bindings skeleton shell."""
        return await self._skeleton("bindings", consents)

    async def _skeleton(self, slug: str, consents: ConsentLedger) -> Template:
        return Template(
            template_name=f"altar/pages/{slug}.html.j2",
            context={"active": slug, "pending": await consents.pending_count()},
        )
