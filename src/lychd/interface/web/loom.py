"""`LoomController` — workflow gallery and mermaid projections (routes 15-16).

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

from lychd.agents.workflows import WORKFLOWS
from lychd.agents.workflows.base import Workflow
from lychd.domain.web.schemas import build_loom_view


def _find_workflow(name: str) -> Workflow | None:
    """Return the workflow with the given slug, or `None`."""
    for workflow in WORKFLOWS:
        if workflow.name == name:
            return workflow
    return None


class LoomController(Controller):
    """Serve the Loom's workflow graphs and their mermaid source."""

    path = "/loom"

    @get("/{workflow:str}")
    async def view(self, request: HTMXRequest, workflow: str) -> Template | Response[str]:
        """Return the graph fragment (htmx, push_url) or the full Loom page."""
        found = _find_workflow(workflow)
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
                "workflows": WORKFLOWS,
                "view": view,
                "selected": found.name,
            },
        )

    @get("/{workflow:str}/source")
    async def source(self, workflow: str) -> Response[str]:
        """Return the mermaid stateDiagram-v2 source as plain text (curl-able)."""
        found = _find_workflow(workflow)
        if found is None:
            return Response(content="No such pattern is woven.", status_code=HTTP_404_NOT_FOUND)
        return Response(content=found.mermaid(), media_type=MediaType.TEXT)
