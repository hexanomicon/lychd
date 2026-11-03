"""Authenticated Bridge dictation; private content never enters generic logs."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, cast
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import CacheControlHeader, State
from litestar.exceptions import HTTPException, PermissionDeniedException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath

from lychd.config.logging import PRIVATE_CONTENT_LOG_OPT
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.codex.sigil import Sigil
from lychd.domain.dictation import (
    MAX_AUDIO_BASE64_CHARS,
    DictationAttemptSummary,
    DictationCorrection,
    DictationCorrectionRequest,
    DictationDiscovery,
    DictationError,
    DictationRequest,
    DictationResult,
)
from lychd.domain.dictation_service import DictationDeleted, DictationService
from lychd.domain.web.contracts import FrameworkError

_ERRORS = {code: ResponseSpec(FrameworkError, generate_examples=False) for code in (400, 401, 403, 404, 409, 413, 503)}


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


def _service(state: State) -> DictationService:
    service = getattr(getattr(state, "services", None), "dictation", None)
    if not isinstance(service, DictationService):
        raise HTTPException(status_code=503, detail="Dictation storage is unavailable.")
    return service


def _storage_error(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, DictationError):
        return HTTPException(status_code=409, detail="Dictation operation refused.", extra={"reason": error.reason})
    return HTTPException(status_code=503, detail="Dictation storage outcome is unavailable; use recovery.")


class DictationController(Controller):
    path = "/api/v1/bridge/dictation"
    guards = (requires_scopes("altar:read"),)
    opt: Mapping[str, Any] | None = MappingProxyType({PRIVATE_CONTENT_LOG_OPT: True})
    cache_control: CacheControlHeader | None = CacheControlHeader(no_store=True)

    @get("", operation_id="getDictationDiscovery", responses=_ERRORS)
    async def discovery(self, request: Request[Any, Any, Any], state: State) -> DictationDiscovery:
        _authorize(request)
        return _service(state).discovery()

    @post(
        "/transcribe",
        status_code=200,
        operation_id="transcribeDictation",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=MAX_AUDIO_BASE64_CHARS + 4096,
    )
    async def transcribe(
        self,
        data: DictationRequest,
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationResult:
        owner = _authorize(request, mutation=True)

        def current() -> None:
            _authorize(request, mutation=True)

        try:
            result = await _service(state).transcribe(
                owner,
                data,
                authorize=current,
            )
            _authorize(request, mutation=True)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        return result

    @get("/attempts", operation_id="listDictationAttempts", responses=_ERRORS)
    async def attempts(
        self,
        request: Request[Any, Any, Any],
        state: State,
    ) -> tuple[DictationAttemptSummary, ...]:
        owner = _authorize(request)
        try:
            result = await _service(state).list_attempts(owner)
            _authorize(request)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        return result

    @get("/attempts/{attempt_id:uuid}", operation_id="getDictationAttempt", responses=_ERRORS)
    async def recover(
        self,
        attempt_id: FromPath[UUID],
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationResult:
        owner = _authorize(request)
        try:
            result = await _service(state).get_result(owner, attempt_id)
            _authorize(request)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        if result is None:
            raise HTTPException(status_code=404, detail="Dictation attempt is unavailable.")
        return result

    @get("/corrections", operation_id="listDictationCorrections", responses=_ERRORS)
    async def corrections(
        self,
        request: Request[Any, Any, Any],
        state: State,
    ) -> tuple[DictationCorrection, ...]:
        owner = _authorize(request)
        try:
            result = await _service(state).list_corrections(owner)
            _authorize(request)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        return result

    @post(
        "/corrections",
        status_code=200,
        operation_id="correctDictation",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=65_536,
    )
    async def correct(
        self,
        data: DictationCorrectionRequest,
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationCorrection:
        owner = _authorize(request, mutation=True)
        try:
            result = await _service(state).correct(owner, data)
            _authorize(request, mutation=True)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        return result

    @post(
        "/attempts/{attempt_id:uuid}/delete",
        status_code=200,
        operation_id="deleteDictationAttempt",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=4096,
    )
    async def delete(
        self,
        attempt_id: FromPath[UUID],
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationDeleted:
        owner = _authorize(request, mutation=True)
        try:
            result = await _service(state).delete(owner, attempt_id)
            _authorize(request, mutation=True)
        except Exception as error:  # noqa: BLE001 - sanitize private persistence diagnostics
            raise _storage_error(error) from None
        return result
