"""Protected finite observation admission and app-owned field operations."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import CacheControlHeader, State
from litestar.exceptions import HTTPException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath
from pydantic import ValidationError

from lychd.compositions.scavenger.schemas import (
    REQUEST_BYTES,
    DeleteObservationRequest,
    LiteralFilter,
    ObservationAdmission,
    ObservationDeleted,
    ObservationDocument,
    ObservationView,
    ObserveMarketRequest,
    Record,
    ScavengerRefused,
    ScavengerState,
    decode_request,
)
from lychd.compositions.scavenger.services import ScavengerService
from lychd.config.logging import PRIVATE_CONTENT_LOG_OPT
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.cortex.ledger import RunAdmissionConflictError
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.web.contracts import FrameworkError
from lychd.domain.web.schemas import ConsentCard
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding
from lychd.domain.webcrawler.profile import WebcrawlerWorkflowError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lychd.domain.cortex.runs import RunRecord

_ERROR_RESPONSES = {
    code: ResponseSpec(FrameworkError, generate_examples=False) for code in (400, 401, 403, 404, 409, 413, 503)
}

_CODES = frozenset(
    {
        "application_authority",
        "application_unavailable",
        "application_custody",
        "application_storage",
        "application_binding",
        "conflicting_replay",
        "deleted",
        "reservation_unavailable",
        "delete_identity",
        "terminal_disposition_required",
        "run_custody",
        "held_delivery_required",
        "adoption_unavailable",
        "scout_custody",
        "field_unavailable",
        "record_bytes",
        "invalid_json",
        "duplicate_key",
        "body_mismatch",
    }
)


def _service(state: State) -> ScavengerService:
    service = getattr(state.services, "scavenger", None)
    if service is None:
        raise HTTPException(status_code=404, detail="Scavenger is not configured.")
    return cast("ScavengerService", service)


def _refusal(error: Exception) -> HTTPException:
    if isinstance(error, ScavengerRefused):
        code = str(error) if str(error) in _CODES else "application_refused"
    elif isinstance(error, WebcrawlerWorkflowError):
        code = "scout_" + error.code.value
    elif isinstance(error, RunAdmissionConflictError):
        code = "conflicting_run"
    else:
        code = "invalid_request"
    status = {"application_storage": 503, "application_authority": 403, "application_unavailable": 404}.get(code, 409)
    return HTTPException(status_code=status, detail="Scavenger operation refused.", extra={"code": code})


def _consent_run(run: RunRecord | None, admission_id: UUID) -> RunRecord | None:
    if (
        run is None
        or run.source != "scavenger"
        or type(run.admitted_webcrawler) is not WebcrawlerFeedBinding
        or run.admitted_webcrawler.consumer.application_admission_id != admission_id
    ):
        reason = "run_custody"
        raise ScavengerRefused(reason)
    return run if run.status is RunStatus.AWAITING_CONSENT and run.consent_id is not None else None


async def _body[T: Record](request: Request[Any, Any, Any], expected: T) -> T:
    document = decode_request(await request.body(), type(expected))
    if document != expected:
        reason = "body_mismatch"
        raise ScavengerRefused(reason)
    return document


class ScavengerController(Controller):
    opt: Mapping[str, Any] | None = MappingProxyType({PRIVATE_CONTENT_LOG_OPT: True})
    cache_control: CacheControlHeader | None = CacheControlHeader(no_store=True)
    path = "/api/v1/scavenger"

    @get("", operation_id="getScavengerState", guards=[requires_scopes("altar:read")], responses=_ERROR_RESPONSES)
    async def current(self, request: Request[Any, Any, Any], state: State) -> ScavengerState:
        if getattr(state.services, "scavenger", None) is None:
            return ScavengerState(configured=False, profile=None, current=None)
        try:
            return await _service(state).current(authentication=request.auth, principal=request.user)
        except ScavengerRefused as error:
            raise _refusal(error) from None

    @post(
        "/observations",
        status_code=200,
        operation_id="submitMarketObservation",
        guards=[requires_scopes("runs:submit")],
        responses=_ERROR_RESPONSES,
        request_max_body_size=REQUEST_BYTES,
    )
    async def submit(
        self, data: ObserveMarketRequest, request: Request[Any, Any, Any], state: State
    ) -> ObservationAdmission:
        service = _service(state)
        admission = state.services.feed_admission
        if admission is None:
            raise HTTPException(status_code=503, detail="Scavenger admission is unavailable.")
        try:
            service.policy.http(request.auth, request.user, "reserve")
            document = await _body(request, data)
            return await service.submit(
                document,
                authentication=request.auth,
                principal=request.user,
                engine=state.services.run_engine,
                admission=admission,
            )
        except (ScavengerRefused, WebcrawlerWorkflowError, RunAdmissionConflictError, ValidationError) as error:
            raise _refusal(error) from None

    @get(
        "/observations/{admission_id:uuid}",
        operation_id="readMarketObservation",
        guards=[requires_scopes("altar:read")],
        responses=_ERROR_RESPONSES,
    )
    async def read(
        self, admission_id: FromPath[UUID], request: Request[Any, Any, Any], state: State
    ) -> ObservationDocument:
        try:
            return await _service(state).document(
                admission_id=admission_id, authentication=request.auth, principal=request.user
            )
        except ScavengerRefused as error:
            raise _refusal(error) from None

    @get(
        "/observations/{admission_id:uuid}/consent",
        operation_id="getMarketObservationConsent",
        guards=[requires_scopes("altar:read")],
        responses=_ERROR_RESPONSES,
    )
    async def consent(
        self, admission_id: FromPath[UUID], request: Request[Any, Any, Any], state: State
    ) -> ConsentCard | None:
        service = _service(state)
        try:
            retained = await service.read(
                admission_id=admission_id, authentication=request.auth, principal=request.user
            )
            if retained.run_id is None or retained.run_status is not RunStatus.AWAITING_CONSENT:
                return None
            ledger = state.services.run_engine.ledger
            run = _consent_run(await ledger.get(str(retained.run_id)), admission_id)
            service.policy.http(request.auth, request.user, "read")
            if run is None:
                return None
            view = await state.services.consents.get(run.consent_id)
            service.policy.http(request.auth, request.user, "read")
            if view is None or view.run_id != run.run_id:
                return None
            card = await state.services.projector.consent_card_view(
                view, reviewer=request.user, authentication=request.auth
            )
            latest = _consent_run(await ledger.get(run.run_id), admission_id)
            service.policy.http(request.auth, request.user, "read")
        except ScavengerRefused as error:
            raise _refusal(error) from None
        else:
            return card if latest is not None and latest.consent_id == run.consent_id else None

    @post(
        "/observations/{admission_id:uuid}/view",
        status_code=200,
        operation_id="filterMarketObservation",
        guards=[requires_scopes("altar:read")],
        responses=_ERROR_RESPONSES,
        request_max_body_size=REQUEST_BYTES,
    )
    async def view(
        self, admission_id: FromPath[UUID], data: LiteralFilter, request: Request[Any, Any, Any], state: State
    ) -> ObservationView:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "read")
            selection = await _body(request, data)
            return await service.view(
                admission_id=admission_id, selection=selection, authentication=request.auth, principal=request.user
            )
        except (ScavengerRefused, ValidationError) as error:
            raise _refusal(error) from None

    @post(
        "/observations/{admission_id:uuid}/delete",
        status_code=200,
        operation_id="deleteMarketObservation",
        guards=[requires_scopes("runs:cancel")],
        responses=_ERROR_RESPONSES,
        request_max_body_size=REQUEST_BYTES,
    )
    async def delete(
        self,
        admission_id: FromPath[UUID],
        data: DeleteObservationRequest,
        request: Request[Any, Any, Any],
        state: State,
    ) -> ObservationDeleted:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "delete")
            document = await _body(request, data)
            await service.delete(
                admission_id=admission_id,
                request_digest=document.request_digest,
                observation_digest=document.observation_digest,
                authentication=request.auth,
                principal=request.user,
            )
            return ObservationDeleted(
                admission_id=admission_id,
                request_digest=document.request_digest,
                observation_digest=document.observation_digest,
            )
        except (ScavengerRefused, ValidationError) as error:
            raise _refusal(error) from None
