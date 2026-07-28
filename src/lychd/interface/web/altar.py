"""Static Svelte Altar shell and its shared status endpoint."""

from __future__ import annotations

from typing import Any

from litestar import Controller, get
from litestar.datastructures import State
from litestar.di import NamedDependency
from litestar.enums import MediaType
from litestar.params import FromPath
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_302_FOUND

from lychd.config.constants import PATH_ALTAR_INDEX
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.web.contracts import AltarStatus

_ALTAR_INDEX = PATH_ALTAR_INDEX.read_text(encoding="utf-8")


class AltarController(Controller):
    """Serve the compiled SPA at every admitted browser deep link."""

    @get("/", name="altar:index", include_in_schema=False)
    async def index(self) -> Response[Any]:
        """Redirect the bare root to the resident Bridge instrument."""
        return Redirect("/bridge", status_code=HTTP_302_FOUND)

    @get(
        ["/bridge", "/nexus", "/loom", "/orb"],
        name="altar:instrument",
        guards=[requires_scopes("altar:read")],
        include_in_schema=False,
    )
    async def instrument(self) -> Response[str]:
        """Return the static SvelteKit fallback document."""
        return Response(content=_ALTAR_INDEX, media_type=MediaType.HTML)

    @get(
        ["/bridge/{client_path:str}", "/orb/{client_path:str}"],
        name="altar:deep-link",
        guards=[requires_scopes("altar:read")],
        include_in_schema=False,
    )
    async def deep_link(self, client_path: FromPath[str]) -> Response[str]:
        """Return the same shell for a client-owned dynamic route."""
        _ = client_path
        return Response(content=_ALTAR_INDEX, media_type=MediaType.HTML)

    @get(
        "/loom/{pattern_id:str}/{revision:str}",
        name="altar:loom-revision",
        guards=[requires_scopes("altar:read")],
        include_in_schema=False,
    )
    async def loom_revision(
        self,
        pattern_id: FromPath[str],
        revision: FromPath[str],
    ) -> Response[str]:
        """Return the SPA shell for an exact client-owned Pattern deep link."""
        _ = (pattern_id, revision)
        return Response(content=_ALTAR_INDEX, media_type=MediaType.HTML)

    @get(
        "/api/v1/altar/status",
        name="altar:status",
        operation_id="getAltarStatus",
        guards=[requires_scopes("altar:read")],
    )
    async def status(
        self,
        consents: NamedDependency[ConsentLedger],
        state: State,
    ) -> AltarStatus:
        """Return shell-wide attention state."""
        return AltarStatus(
            pending_consents=await consents.pending_count(),
            csrf=state.csrf_contract,
        )
