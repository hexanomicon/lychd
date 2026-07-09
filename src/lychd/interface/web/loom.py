"""`LoomController` — the Loom page, workflow gallery, and mermaid projections.

The Loom projects each registered `Workflow` as a client-rendered mermaid
stateDiagram-v2. Graph *source* only ever leaves the process as text — rendering
is client-side (Sovereignty Wall; no remote mermaid.ink).
"""

from __future__ import annotations

from litestar import Controller, get
from litestar.enums import MediaType
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import Response, Template
from litestar.status_codes import HTTP_404_NOT_FOUND

from lychd.agents.workflows import WORKFLOW_REGISTRY
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.web.schemas import build_loom_view

# Runtime import: Litestar resolves handler param annotations at registration.


class LoomController(Controller):
    """Serve the Loom's page, workflow graphs, and their mermaid source."""

    path = "/loom"

    @get("/", name="loom:page", guards=[requires_scopes("altar:read")])
    async def page(self, consents: ConsentLedger) -> Template:
        """Render the Loom with the first workflow pre-selected."""
        workflow = WORKFLOW_REGISTRY.default
        return Template(
            template_name="altar/pages/loom.html.j2",
            context={
                "active": "loom",
                "pending": await consents.pending_count(),
                "workflows": WORKFLOW_REGISTRY.all(),
                "view": build_loom_view(workflow),
                "selected": workflow.name,
            },
        )

    @get("/{workflow:str}", name="loom:view")
    async def view(self, request: HTMXRequest, workflow: str) -> Template | Response[str]:
        """Return the graph fragment (htmx, push_url) or the full Loom page."""
        found = WORKFLOW_REGISTRY.get(workflow)
        if found is None:
            return Response(content="No such pattern is woven.", status_code=HTTP_404_NOT_FOUND)

        view = build_loom_view(found)
        if request.htmx:
            return HTMXTemplate(
                template_name="loom/graph.html.j2",
                context={"view": view},
                push_url=f"/loom/{found.name}",
            )
        return Template(
            template_name="altar/pages/loom.html.j2",
            context={
                "active": "loom",
                "workflows": WORKFLOW_REGISTRY.all(),
                "view": view,
                "selected": found.name,
            },
        )

    @get("/{workflow:str}/source", name="loom:source")
    async def source(self, workflow: str) -> Response[str]:
        """Return the mermaid stateDiagram-v2 source as plain text (curl-able)."""
        found = WORKFLOW_REGISTRY.get(workflow)
        if found is None:
            return Response(content="No such pattern is woven.", status_code=HTTP_404_NOT_FOUND)
        return Response(content=found.mermaid(), media_type=MediaType.TEXT)
