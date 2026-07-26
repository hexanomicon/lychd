"""Versioned Loom workflow catalogue and graph projections."""

from __future__ import annotations

from litestar import Controller, get
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.response import Response

from lychd.agents.workflows import WORKFLOW_REGISTRY
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.web.contracts import LoomSummary
from lychd.domain.web.schemas import LoomView, build_loom_view


class LoomController(Controller):
    """Serve workflow metadata and inert Mermaid source as data."""

    path = "/api/v1/loom"

    @get("", name="loom:catalogue", operation_id="getLoomCatalogue", guards=[requires_scopes("altar:read")])
    async def catalogue(self) -> list[LoomSummary]:
        """Return the registered workflow catalogue."""
        return [
            LoomSummary(
                name=workflow.name,
                title=workflow.title,
                description=workflow.description,
                trigger_hint=workflow.trigger.hint,
            )
            for workflow in WORKFLOW_REGISTRY.all()
        ]

    @get(
        "/{workflow:str}",
        name="loom:view",
        operation_id="getLoomWorkflow",
        guards=[requires_scopes("altar:read")],
    )
    async def view(self, workflow: FromPath[str]) -> LoomView:
        """Return one workflow projection."""
        found = WORKFLOW_REGISTRY.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        return build_loom_view(found)

    @get(
        "/{workflow:str}/source",
        name="loom:source",
        operation_id="getLoomWorkflowSource",
        guards=[requires_scopes("altar:read")],
    )
    async def source(self, workflow: FromPath[str]) -> Response[str]:
        """Return the Mermaid source as a curl-friendly text representation."""
        found = WORKFLOW_REGISTRY.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        return Response(content=found.mermaid(), media_type=MediaType.TEXT)
