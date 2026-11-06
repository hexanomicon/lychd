"""Explicit local acceptance of private forms of address; suggestions are inert."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, cast

from litestar import Controller, Request, get, put
from litestar.datastructures import CacheControlHeader, State
from litestar.exceptions import HTTPException, PermissionDeniedException
from litestar.openapi.datastructures import ResponseSpec

from lychd.config.logging import PRIVATE_CONTENT_LOG_OPT
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.codex.sigil import Sigil
from lychd.domain.naming import (
    NameSuggestions,
    NamingAcceptance,
    NamingConflictError,
    NamingStore,
    NamingStoreError,
    NamingView,
    suggest_names,
)
from lychd.domain.web.contracts import FrameworkError

_ERRORS = {code: ResponseSpec(FrameworkError, generate_examples=False) for code in (400, 401, 403, 409, 413, 503)}


def _authorize(request: Request[Any, Any, Any], *, mutation: bool = False) -> str:
    access = getattr(request.app.state, "local_operator_access", None)
    scope = cast("Mapping[str, Any]", request.scope)
    sigil = scope.get("user")
    required = ("altar:read", "runs:submit") if mutation else ("altar:read",)
    if (
        not isinstance(access, LocalOperatorAccess)
        or not access.current(scope.get("auth"))
        or not isinstance(sigil, Sigil)
        or not scopes_satisfied(sigil.scopes, required)
    ):
        raise PermissionDeniedException(detail="Current local operator authority is required.")
    return sigil.name


def _store(state: State) -> NamingStore:
    store = getattr(getattr(state, "services", None), "naming", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Naming storage is unavailable.")
    return cast("NamingStore", store)


class NamingController(Controller):
    path = "/api/v1/altar/naming"
    guards = (requires_scopes("altar:read"),)
    opt: Mapping[str, Any] | None = MappingProxyType({PRIVATE_CONTENT_LOG_OPT: True})
    cache_control: CacheControlHeader | None = CacheControlHeader(no_store=True)

    @get(operation_id="getNaming", responses=_ERRORS)
    async def current(self, request: Request[Any, Any, Any], state: State) -> NamingView:
        owner = _authorize(request)
        try:
            result = await _store(state).get(owner)
        except NamingStoreError:
            raise HTTPException(status_code=503, detail="Names are unavailable; reload to recover.") from None
        _authorize(request)
        return NamingView(current=result)

    @put(
        operation_id="acceptNaming",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=4096,
    )
    async def accept(self, data: NamingAcceptance, request: Request[Any, Any, Any], state: State) -> NamingView:
        owner = _authorize(request, mutation=True)
        try:
            result = await _store(state).accept(owner, data.names, data.expected_revision)
        except NamingConflictError:
            raise HTTPException(status_code=409, detail="Names changed; reload before saving.") from None
        except NamingStoreError:
            raise HTTPException(status_code=503, detail="Naming outcome is unavailable; reload to recover.") from None
        _authorize(request, mutation=True)
        return NamingView(current=result)

    @get("/suggestions", operation_id="getNamingSuggestions", responses=_ERRORS)
    async def suggestions(self, request: Request[Any, Any, Any]) -> NameSuggestions:
        _authorize(request)
        return suggest_names()
