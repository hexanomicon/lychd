"""Atlas planning API: explicit projects, judgments, and related activity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, cast
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import State
from litestar.di import NamedDependency
from litestar.exceptions import HTTPException, NotFoundException, ValidationException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, QueryParameter
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.sigil import Sigil
from lychd.domain.web.atlas import (
    AtlasCatalogue,
    AtlasConflictError,
    AtlasCreate,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasReferenceAdd,
    AtlasStorePort,
    AtlasSummary,
    AtlasValidationError,
)
from lychd.domain.web.contracts import FrameworkError
from lychd.domain.web.sessions import SessionStorePort

if TYPE_CHECKING:
    from lychd.domain.cortex.ledger import RunLedger


def _owner(request: Request[Any, Any, Any]) -> str:
    return cast("Sigil", request.user).name


async def _check_reference(
    owner: str,
    kind: Literal["session", "run"],
    target_id: str,
    sessions: SessionStorePort,
    state: State,
) -> None:
    """Require an existing target in the caller's bootstrap identity boundary."""
    canonical_id: str | None = None
    target_owner: str | None = None
    try:
        if kind == "session":
            session = await sessions.get_session(target_id)
            if session is not None:
                canonical_id, target_owner = session.id, session.sigil_name
        else:
            ledger = cast("RunLedger", state.services.ledger)
            run = await ledger.get(target_id)
            if run is not None:
                canonical_id, target_owner = run.run_id, run.sigil_name
    except ValueError:
        pass
    if canonical_id is None or target_owner != owner:
        raise ValidationException(detail="Related activity is unavailable to this Sigil.")
    if target_id != canonical_id:
        raise ValidationException(detail="Use the exact activity identity from its Bridge or Orb URL.")


class AtlasController(Controller):
    """Retain planning without admitting execution or replacing evidence owners."""

    path = "/api/v1/atlas"

    @get(
        "/projects",
        name="atlas:projects",
        operation_id="getAtlasProjects",
        guards=[requires_scopes("altar:read")],
    )
    async def projects(
        self,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
        limit: Annotated[int, QueryParameter(ge=1, le=100)] = 50,
        offset: Annotated[int, QueryParameter(ge=0)] = 0,
    ) -> AtlasCatalogue:
        """List a bounded page of the caller's undertakings."""
        return await atlas.list_projects(_owner(request), limit=limit, offset=offset)

    @get(
        "/projects/{project_id:uuid}",
        name="atlas:project",
        operation_id="getAtlasProject",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def project(
        self,
        project_id: FromPath[UUID],
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
    ) -> AtlasProject:
        """Read the complete current Project and its retained judgments."""
        try:
            return await atlas.get_project(_owner(request), project_id)
        except AtlasNotFoundError as exc:
            raise NotFoundException(detail="Unknown Atlas project.") from exc

    @post(
        "/projects",
        name="atlas:create",
        operation_id="createAtlasProject",
        guards=[requires_scopes("altar:read", "atlas:write")],
        responses={
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_409_CONFLICT: ResponseSpec(FrameworkError, generate_examples=False),
        },
    )
    async def create(
        self,
        data: AtlasCreate,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
    ) -> AtlasProject:
        """Create an undertaking independently of any conversation or Run."""
        try:
            return await atlas.create_project(_owner(request), data)
        except AtlasNotFoundError as exc:
            raise NotFoundException(detail="Atlas project identity is unavailable.") from exc
        except AtlasConflictError as exc:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail=str(exc), extra={"code": "atlas_write_rejected"}
            ) from exc

    @post(
        "/projects/{project_id:uuid}/changes",
        name="atlas:change",
        operation_id="changeAtlasProject",
        status_code=HTTP_200_OK,
        guards=[requires_scopes("altar:read", "atlas:write")],
        responses={
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_409_CONFLICT: ResponseSpec(FrameworkError, generate_examples=False),
        },
    )
    async def change(
        self,
        project_id: FromPath[UUID],
        data: AtlasMutation,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
        bridge_sessions: NamedDependency[SessionStorePort],
        state: State,
    ) -> AtlasProject:
        """Apply one revision-checked, retry-safe planning change."""
        owner = _owner(request)
        try:
            replay = await atlas.replay_change(owner, project_id, data)
            if replay is not None:
                return replay
            if isinstance(data.change, AtlasReferenceAdd):
                await _check_reference(owner, data.change.reference_kind, data.change.target_id, bridge_sessions, state)
            return await atlas.change_project(owner, project_id, data)
        except AtlasNotFoundError as exc:
            raise NotFoundException(detail=str(exc)) from exc
        except AtlasConflictError as exc:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail=str(exc), extra={"code": "atlas_write_rejected"}
            ) from exc
        except AtlasValidationError as exc:
            raise ValidationException(detail=str(exc)) from exc

    @get(
        "/references",
        name="atlas:references",
        operation_id="getAtlasReferences",
        guards=[requires_scopes("altar:read")],
    )
    async def references(
        self,
        request: Request[Any, Any, Any],
        atlas: NamedDependency[AtlasStorePort],
        kind: Annotated[Literal["session", "run"], QueryParameter()],
        target_id: Annotated[str, QueryParameter(min_length=1, max_length=200)],
    ) -> list[AtlasSummary]:
        """Find explicit Atlas membership without changing conversation Context."""
        return await atlas.projects_for_reference(_owner(request), kind, target_id)
