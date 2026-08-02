"""Versioned Loom workflow catalogue and graph projections."""

from __future__ import annotations

from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath
from litestar.response import Response
from litestar.status_codes import HTTP_404_NOT_FOUND

from lychd.agents.workflows import WorkflowRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.web.contracts import FrameworkError, LoomSummary
from lychd.domain.web.schemas import LoomView, build_loom_view


class LoomController(Controller):
    """Serve workflow metadata and inert Mermaid source as data."""

    path = "/api/v1/loom"

    @get("", name="loom:catalogue", operation_id="getLoomCatalogue", guards=[requires_scopes("altar:read")])
    async def catalogue(self, workflows: NamedDependency[WorkflowRegistry]) -> list[LoomSummary]:
        """Return the registered workflow catalogue."""
        return [
            LoomSummary(
                pattern_id=workflow.manifest.key,
                revision=workflow.manifest.revision,
                implementation_revision=workflow.manifest.implementation_revision,
                entry_node=workflow.manifest.entry_node,
                digest=workflow.manifest.digest,
                title=workflow.title,
                description=workflow.description,
                trigger_hint=workflow.trigger.hint,
                detail_path=f"/loom/{workflow.manifest.key}/{workflow.manifest.revision}",
                active=workflows.is_active(workflow.manifest.key, workflow.manifest.revision),
                default=workflows.is_default(workflow.manifest.key, workflow.manifest.revision),
                route_rank=workflows.route_rank(workflow.manifest.key, workflow.manifest.revision),
            )
            for workflow in workflows.all()
        ]

    @get(
        "/{workflow:str}",
        name="loom:view",
        operation_id="getLoomWorkflow",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def view(
        self,
        workflow: FromPath[str],
        workflows: NamedDependency[WorkflowRegistry],
    ) -> LoomView:
        """Return the current registered revision as a convenience projection."""
        found = workflows.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        return build_loom_view(found)

    @get(
        "/{pattern_id:str}/{revision:str}",
        name="loom:revision",
        operation_id="getLoomPatternRevision",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def revision(
        self,
        pattern_id: FromPath[str],
        revision: FromPath[str],
        workflows: NamedDependency[WorkflowRegistry],
    ) -> LoomView:
        """Return one exact registered immutable Pattern revision."""
        found = workflows.get_revision(pattern_id, revision)
        if found is None:
            raise NotFoundException(detail="No such Pattern revision is woven.")
        return build_loom_view(found)

    @get(
        "/source/workflows/{workflow:str}",
        name="loom:source",
        operation_id="getLoomWorkflowSource",
        media_type=MediaType.TEXT,
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def source(
        self,
        workflow: FromPath[str],
        workflows: NamedDependency[WorkflowRegistry],
    ) -> Response[str]:
        """Return the Mermaid source as a curl-friendly text representation."""
        found = workflows.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        return Response(content=found.mermaid(), media_type=MediaType.TEXT)

    @get(
        "/source/patterns/{pattern_id:str}/{revision:str}",
        name="loom:revision-source",
        operation_id="getLoomPatternRevisionSource",
        media_type=MediaType.TEXT,
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def revision_source(
        self,
        pattern_id: FromPath[str],
        revision: FromPath[str],
        workflows: NamedDependency[WorkflowRegistry],
    ) -> Response[str]:
        """Return one exact revision's inert Mermaid projection as plain text."""
        found = workflows.get_revision(pattern_id, revision)
        if found is None:
            raise NotFoundException(detail="No such Pattern revision is woven.")
        return Response(content=found.mermaid(), media_type=MediaType.TEXT)
