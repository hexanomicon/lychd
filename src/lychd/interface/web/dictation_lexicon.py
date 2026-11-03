"""Private approved vocabulary and explicit suggestions from owned transcripts."""

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
from lychd.domain.dictation import DictationLexiconRuleRequest
from lychd.domain.dictation_lexicon import (
    DictationLexiconDeleted,
    DictationLexiconError,
    DictationLexiconRule,
    DictationSuggestion,
    DictationSuggestionRequest,
)
from lychd.domain.dictation_lexicon_service import DictationLexiconService
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


def _service(state: State) -> DictationLexiconService:
    service = getattr(getattr(state, "services", None), "dictation_lexicon", None)
    if not isinstance(service, DictationLexiconService):
        raise HTTPException(status_code=503, detail="Vocabulary storage is unavailable.")
    return service


def _storage_error(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, DictationLexiconError):
        return HTTPException(
            status_code=404 if error.reason == "unavailable" else 409,
            detail="Vocabulary operation refused.",
            extra={"reason": error.reason},
        )
    return HTTPException(status_code=503, detail="Vocabulary storage outcome is unavailable; reload to recover.")


class DictationLexiconController(Controller):
    path = "/api/v1/bridge/dictation"
    guards = (requires_scopes("altar:read"),)
    opt: Mapping[str, Any] | None = MappingProxyType({PRIVATE_CONTENT_LOG_OPT: True})
    cache_control: CacheControlHeader | None = CacheControlHeader(no_store=True)

    @get("/lexicon", operation_id="listDictationLexicon", responses=_ERRORS)
    async def list_rules(
        self,
        request: Request[Any, Any, Any],
        state: State,
    ) -> tuple[DictationLexiconRule, ...]:
        owner = _authorize(request)
        try:
            result = await _service(state).list_rules(owner)
            _authorize(request)
        except Exception as error:  # noqa: BLE001 - private diagnostics cannot cross HTTP
            raise _storage_error(error) from None
        return result

    @post(
        "/lexicon",
        status_code=200,
        operation_id="approveDictationLexiconRule",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=4096,
    )
    async def approve(
        self,
        data: DictationLexiconRuleRequest,
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationLexiconRule:
        owner = _authorize(request, mutation=True)
        try:
            result = await _service(state).approve(owner, data)
            _authorize(request, mutation=True)
        except Exception as error:  # noqa: BLE001 - private diagnostics cannot cross HTTP
            raise _storage_error(error) from None
        return result

    @post(
        "/lexicon/{rule_id:uuid}/delete",
        status_code=200,
        operation_id="deleteDictationLexiconRule",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=4096,
    )
    async def delete(
        self,
        rule_id: FromPath[UUID],
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationLexiconDeleted:
        owner = _authorize(request, mutation=True)
        try:
            result = await _service(state).delete(owner, rule_id)
            _authorize(request, mutation=True)
        except Exception as error:  # noqa: BLE001 - private diagnostics cannot cross HTTP
            raise _storage_error(error) from None
        return result

    @post(
        "/suggestions",
        status_code=200,
        operation_id="suggestDictationVocabulary",
        responses=_ERRORS,
        guards=[requires_scopes("runs:submit")],
        request_max_body_size=4096,
    )
    async def suggest(
        self,
        data: DictationSuggestionRequest,
        request: Request[Any, Any, Any],
        state: State,
    ) -> DictationSuggestion:
        owner = _authorize(request, mutation=True)

        def current() -> None:
            _authorize(request, mutation=True)

        try:
            result = await _service(state).suggest(owner, data, authorize=current)
            current()
        except Exception as error:  # noqa: BLE001 - private diagnostics cannot cross HTTP
            raise _storage_error(error) from None
        return result
