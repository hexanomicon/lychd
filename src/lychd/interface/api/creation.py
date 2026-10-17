"""Protected local investigation admission and exact historical custody."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import State
from litestar.exceptions import HTTPException
from litestar.params import FromPath
from pydantic import ValidationError

from lychd.compositions.creation.schemas import (
    REQUEST_BYTES,
    CaseView,
    ContinueRequest,
    CreationRefused,
    ExternalAssessment,
    FeedbackEntry,
    FeedbackView,
    InvestigationRequest,
    OwnerDecision,
    decode,
    refuse,
)
from lychd.compositions.creation.services import InvestigationService
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.sigil import Sigil


def _service(state: State) -> InvestigationService:
    service = state.services.creation
    if service is None:
        raise HTTPException(status_code=404, detail="Creation investigation is not configured.")
    return cast("InvestigationService", service)


def _refusal(exc: Exception) -> HTTPException:
    code = str(exc) if isinstance(exc, CreationRefused) else "invalid_request"
    status = 403 if code == "local_authority" else (404 if code == "unknown_case" else 409)
    return HTTPException(status_code=status, detail="Creation investigation refused.", extra={"code": code})


async def _document(request: Request[Any, Any, Any]) -> Any:
    # The literal body is decoded once here; framework JSON decoding must not erase duplicate keys.
    body = await request.body()
    if len(body) > REQUEST_BYTES:
        refuse("request_bytes")
    return decode(body)


class CreationController(Controller):
    path = "/api/v1/creation/investigations"

    @post("", status_code=200, operation_id="submitCreationInvestigation", guards=[requires_scopes("runs:submit")])
    async def submit(self, data: InvestigationRequest, request: Request[Any, Any, Any], state: State) -> CaseView:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "submit")
            document = InvestigationRequest.model_validate(await _document(request))
            if document != data:
                refuse("body_mismatch")
            return await service.submit(
                document,
                authentication=request.auth,
                principal=request.user,
                engine=state.services.run_engine,
                sessions=state.services.bridge_sessions,
            )
        except (CreationRefused, ValidationError, UnicodeError) as exc:
            raise _refusal(exc) from None

    @get("/{case_id:uuid}", operation_id="readCreationInvestigation", guards=[requires_scopes("altar:read")])
    async def read(self, case_id: FromPath[UUID], request: Request[Any, Any, Any], state: State) -> CaseView:
        try:
            return await _service(state).read(
                case_id, authentication=request.auth, principal=cast("Sigil", request.user)
            )
        except CreationRefused as exc:
            raise _refusal(exc) from None

    @post(
        "/{case_id:uuid}/cancel",
        status_code=200,
        operation_id="cancelCreationInvestigation",
        guards=[requires_scopes("runs:cancel")],
    )
    async def cancel(self, case_id: FromPath[UUID], request: Request[Any, Any, Any], state: State) -> CaseView:
        try:
            return await _service(state).cancel(
                case_id, authentication=request.auth, principal=request.user, engine=state.services.run_engine
            )
        except CreationRefused as exc:
            raise _refusal(exc) from None

    @post(
        "/{case_id:uuid}/continue",
        status_code=200,
        operation_id="continueCreationInvestigation",
        guards=[requires_scopes("runs:submit")],
    )
    async def continue_case(
        self, case_id: FromPath[UUID], data: ContinueRequest, request: Request[Any, Any, Any], state: State
    ) -> CaseView:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "continue")
            document = ContinueRequest.model_validate(await _document(request))
            if document != data:
                refuse("body_mismatch")
            return await service.continue_case(
                case_id,
                document,
                authentication=request.auth,
                principal=request.user,
                engine=state.services.run_engine,
                sessions=state.services.bridge_sessions,
            )
        except (CreationRefused, ValidationError) as exc:
            raise _refusal(exc) from None

    @post(
        "/{case_id:uuid}/assessments",
        status_code=200,
        operation_id="assessCreationInvestigation",
        guards=[requires_scopes("runs:submit")],
    )
    async def assess(
        self, case_id: FromPath[UUID], data: ExternalAssessment, request: Request[Any, Any, Any], state: State
    ) -> FeedbackEntry:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "assess")
            document = ExternalAssessment.model_validate(await _document(request))
            if document != data:
                refuse("body_mismatch")
            return await service.assess(case_id, document, authentication=request.auth, principal=request.user)
        except (CreationRefused, ValidationError, UnicodeError) as exc:
            raise _refusal(exc) from None

    @post(
        "/{case_id:uuid}/decisions",
        status_code=200,
        operation_id="decideCreationInvestigation",
        guards=[requires_scopes("runs:submit")],
    )
    async def decide(
        self, case_id: FromPath[UUID], data: OwnerDecision, request: Request[Any, Any, Any], state: State
    ) -> FeedbackEntry:
        service = _service(state)
        try:
            service.policy.http(request.auth, request.user, "decide")
            document = OwnerDecision.model_validate(await _document(request))
            if document != data:
                refuse("body_mismatch")
            return await service.decide(case_id, document, authentication=request.auth, principal=request.user)
        except (CreationRefused, ValidationError, UnicodeError) as exc:
            raise _refusal(exc) from None

    @get("/{case_id:uuid}/feedback", operation_id="readCreationFeedback", guards=[requires_scopes("altar:read")])
    async def feedback(self, case_id: FromPath[UUID], request: Request[Any, Any, Any], state: State) -> FeedbackView:
        try:
            return await _service(state).feedback(case_id, authentication=request.auth, principal=request.user)
        except CreationRefused as exc:
            raise _refusal(exc) from None
