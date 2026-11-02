"""Read-only exact Pattern inspection, separate from executable workflow lookup."""

from __future__ import annotations

import asyncio
from typing import Annotated

from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, QueryParameter
from litestar.response import Response
from litestar.status_codes import HTTP_404_NOT_FOUND

from lychd.agents.workflows import WorkflowRegistry
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.oculus.models import OrbRuntimeSnapshot
from lychd.domain.oculus.runtime import RuntimeCatalogue
from lychd.domain.weaver.inspection import PatternInspectionEntry
from lychd.domain.web.contracts import FrameworkError, LoomSummary
from lychd.domain.web.schemas import LoomView, build_inspection_view


def _exact_entry(
    snapshot: OrbRuntimeSnapshot,
    pattern_id: str,
    revision: str,
    *,
    source_id: str | None,
    generation: str | None,
    profile_id: str | None,
    profile_revision: str | None,
) -> PatternInspectionEntry:
    """Never substitute a newer source generation or a similarly named profile."""
    selection = (source_id, generation, profile_id, profile_revision)
    candidates = [
        entry
        for entry in snapshot.patterns
        if entry.descriptor.pattern_id == pattern_id and entry.descriptor.revision == revision
    ]
    if any(value is not None for value in selection):
        candidates = [
            entry
            for entry in candidates
            if (
                entry.binding.source_id,
                entry.binding.source_generation,
                entry.binding.profile_id,
                entry.binding.profile_revision,
            )
            == selection
        ]
    else:
        native = [entry for entry in candidates if entry.binding.executable]
        candidates = native or candidates
    if len(candidates) != 1:
        raise NotFoundException(detail="No exact selected Pattern inspection is available.")
    return candidates[0]


class LoomController(Controller):
    """Serve inert metadata from the selected inspection catalogue."""

    path = "/api/v1/loom"

    @get("", name="loom:catalogue", operation_id="getLoomCatalogue", guards=[requires_scopes("altar:read")])
    async def catalogue(
        self,
        workflows: NamedDependency[WorkflowRegistry],
        runtime_observations: NamedDependency[RuntimeCatalogue],
    ) -> list[LoomSummary]:
        snapshot = await asyncio.to_thread(runtime_observations.snapshot, workflows)
        return [
            LoomSummary(
                pattern_id=entry.descriptor.pattern_id,
                revision=entry.descriptor.revision,
                implementation_revision=entry.descriptor.implementation_revision,
                entry_node=entry.descriptor.entry_node,
                digest=entry.descriptor.digest,
                title=entry.descriptor.title,
                description=entry.descriptor.description,
                trigger_hint=entry.descriptor.trigger_hint,
                detail_path=entry.detail_path,
                active=entry.binding.executable
                and workflows.is_active(entry.descriptor.pattern_id, entry.descriptor.revision),
                default=entry.binding.executable
                and workflows.is_default(entry.descriptor.pattern_id, entry.descriptor.revision),
                route_rank=workflows.route_rank(entry.descriptor.pattern_id, entry.descriptor.revision)
                if entry.binding.executable
                else None,
                publication=entry.binding.publication,
                binding=entry.binding,
            )
            for entry in snapshot.patterns
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
        runtime_observations: NamedDependency[RuntimeCatalogue],
    ) -> LoomView:
        """Keep the current-executable convenience route's existing meaning."""
        found = workflows.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        snapshot = await asyncio.to_thread(runtime_observations.snapshot, workflows)
        return build_inspection_view(
            _exact_entry(
                snapshot,
                workflow,
                found.manifest.revision,
                source_id=None,
                generation=None,
                profile_id=None,
                profile_revision=None,
            )
        )

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
        runtime_observations: NamedDependency[RuntimeCatalogue],
        source_id: Annotated[str | None, QueryParameter(max_length=128)] = None,
        generation: Annotated[str | None, QueryParameter(max_length=128)] = None,
        profile_id: Annotated[str | None, QueryParameter(max_length=128)] = None,
        profile_revision: Annotated[str | None, QueryParameter(max_length=128)] = None,
    ) -> LoomView:
        snapshot = await asyncio.to_thread(runtime_observations.snapshot, workflows)
        return build_inspection_view(
            _exact_entry(
                snapshot,
                pattern_id,
                revision,
                source_id=source_id,
                generation=generation,
                profile_id=profile_id,
                profile_revision=profile_revision,
            )
        )

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
        runtime_observations: NamedDependency[RuntimeCatalogue],
    ) -> Response[str]:
        found = workflows.get(workflow)
        if found is None:
            raise NotFoundException(detail="No such pattern is woven.")
        snapshot = await asyncio.to_thread(runtime_observations.snapshot, workflows)
        entry = _exact_entry(
            snapshot,
            workflow,
            found.manifest.revision,
            source_id=None,
            generation=None,
            profile_id=None,
            profile_revision=None,
        )
        return Response(content=entry.descriptor.mermaid(), media_type=MediaType.TEXT)

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
        runtime_observations: NamedDependency[RuntimeCatalogue],
        source_id: Annotated[str | None, QueryParameter(max_length=128)] = None,
        generation: Annotated[str | None, QueryParameter(max_length=128)] = None,
        profile_id: Annotated[str | None, QueryParameter(max_length=128)] = None,
        profile_revision: Annotated[str | None, QueryParameter(max_length=128)] = None,
    ) -> Response[str]:
        snapshot = await asyncio.to_thread(runtime_observations.snapshot, workflows)
        entry = _exact_entry(
            snapshot,
            pattern_id,
            revision,
            source_id=source_id,
            generation=generation,
            profile_id=profile_id,
            profile_revision=profile_revision,
        )
        return Response(content=entry.descriptor.mermaid(), media_type=MediaType.TEXT)
