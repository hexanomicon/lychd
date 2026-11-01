"""Owner-scoped Canvas workspace retention and stateless CPU proposal review."""

from __future__ import annotations

from typing import Any, cast

from litestar import Controller, Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import HTTPException, NotFoundException, ValidationException
from litestar.openapi.datastructures import ResponseSpec
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from lychd.compositions.canvas.operations import review_proposal, validate_document
from lychd.compositions.canvas.schemas import (
    MAX_DOCUMENT_BYTES,
    MAX_REVIEW_BYTES,
    CanvasContracts,
    CanvasDocument,
    CanvasReviewRequest,
    CanvasReviewResult,
)
from lychd.compositions.canvas.workspace import lychd_project_id, lychd_workspace_document
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.sigil import Sigil
from lychd.domain.web.atlas import (
    AtlasConflictError,
    AtlasNotFoundError,
    AtlasProject,
    AtlasStorePort,
    CanvasProjectCreate,
)
from lychd.domain.web.contracts import FrameworkError


def _retained_workspace(project: AtlasProject) -> AtlasProject:
    """Refuse an invalid reserved record without replacing any retained content."""
    if project.builtin and project.workspace_state == "kept" and project.canvas_document is not None:
        return project
    message = "The reserved LychD Project identity does not contain a valid built-in workspace."
    raise AtlasConflictError(message)


class CanvasController(Controller):
    """Retain primary boards through Atlas while review remains a pure operation."""

    path = "/api/v1/canvas"

    @get(
        "/contracts",
        name="canvas:contracts",
        operation_id="getCanvasContracts",
        guards=[requires_scopes("altar:read")],
    )
    async def contracts(self) -> CanvasContracts:
        """Describe the portable profile and its unavailable external effects."""
        return CanvasContracts()

    @post(
        "/projects",
        name="canvas:create-project",
        operation_id="createCanvasProject",
        request_max_body_size=MAX_DOCUMENT_BYTES + 4096,
        guards=[requires_scopes("altar:read", "canvas:write", "atlas:write")],
        responses={
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_409_CONFLICT: ResponseSpec(FrameworkError, generate_examples=False),
        },
    )
    async def create_project(
        self,
        data: CanvasProjectCreate,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
    ) -> AtlasProject:
        """Atomically create a discardable draft Project with its primary board."""
        try:
            return await atlas.create_canvas_project(cast("Sigil", request.user).name, data)
        except AtlasNotFoundError as exc:
            raise NotFoundException(detail="Atlas project identity is unavailable.") from exc
        except AtlasConflictError as exc:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail=str(exc), extra={"code": "atlas_write_rejected"}
            ) from exc

    @post(
        "/workspace/bootstrap",
        name="canvas:bootstrap-workspace",
        operation_id="bootstrapCanvasWorkspace",
        status_code=HTTP_200_OK,
        guards=[requires_scopes("altar:read", "canvas:write", "atlas:write")],
        responses={
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_409_CONFLICT: ResponseSpec(FrameworkError, generate_examples=False),
        },
    )
    async def bootstrap_workspace(
        self,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
    ) -> AtlasProject:
        """Retain or replay the caller's pinned, editable static LychD reference."""
        owner = cast("Sigil", request.user).name
        try:
            try:
                current = await atlas.get_project(owner, lychd_project_id(owner))
            except AtlasNotFoundError:
                current = None
            if current is not None:
                return _retained_workspace(current)
            data = CanvasProjectCreate(id=lychd_project_id(owner), canvas_document=lychd_workspace_document(owner))
            return await atlas.create_canvas_project(owner, data, builtin=True)
        except AtlasNotFoundError as exc:
            raise NotFoundException(detail="Atlas project identity is unavailable.") from exc
        except AtlasConflictError as exc:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail=str(exc), extra={"code": "atlas_write_rejected"}
            ) from exc

    @post(
        "/documents/validate",
        name="canvas:validate-document",
        operation_id="validateCanvasDocument",
        status_code=HTTP_200_OK,
        request_max_body_size=MAX_DOCUMENT_BYTES,
        guards=[requires_scopes("altar:read", "canvas:write")],
        responses={HTTP_400_BAD_REQUEST: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def document(self, data: CanvasDocument) -> CanvasDocument:
        """Return an identity-validated local document; no file or state is saved."""
        try:
            return validate_document(data)
        except ValueError as exc:
            raise ValidationException(detail="Canvas document validation failed.") from exc

    @post(
        "/review",
        name="canvas:review",
        operation_id="reviewCanvasProposal",
        status_code=HTTP_200_OK,
        request_max_body_size=MAX_REVIEW_BYTES,
        guards=[requires_scopes("altar:read", "canvas:write")],
        responses={HTTP_400_BAD_REQUEST: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def review(self, data: CanvasReviewRequest) -> CanvasReviewResult:
        """Return a validated successor of this packet, without applying server state."""
        try:
            return review_proposal(data)
        except ValueError as exc:
            raise ValidationException(detail="Canvas proposal validation failed.") from exc
