"""Public-page casting keeps source transient and never repeats material loss."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any, Literal, cast
from uuid import UUID

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage
from pydantic_graph import GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.webcrawler_context import WebcrawlerModel
from lychd.agents.workflows.webcrawler_chat import (
    BRIDGE_CHAT_WEBCRAWLER,
    AcquireAndAnswerPage,
    AwaitPageConsent,
    PreparePageReview,
    SettlePageAnswer,
    WebcrawlerChatState,
)
from lychd.domain.animation.capabilities import CapabilityGrant, SourceKind
from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.runs import ConsentPending
from lychd.domain.webcrawler.profile import (
    WebcrawlerBinding,
    WebcrawlerMaterial,
    WebcrawlerReviewRef,
    WebcrawlerWorkflowCode,
    WebcrawlerWorkflowError,
)
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeDispatcher, FakeEvents, FakeOrchestrator, FakeTurns
from tests.webcrawler_fixtures import CAPABILITY, PROMPT, QUESTION, SOURCE_TEXT, webcrawler_binding, webcrawler_material, webcrawler_review


class _Model(FunctionModel):
    def __init__(self) -> None:
        super().__init__(self.respond, stream_function=self.stream)
        self.sent: list[bytes] = []
        self.counted: list[bytes] = []
        self.tools: list[str] = []

    async def respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.sent.append(ModelMessagesTypeAdapter.dump_json(messages))
        self.tools.extend(tool.name for tool in info.function_tools)
        return ModelResponse(parts=[TextPart("ordinary answer")], usage=RequestUsage(input_tokens=10))

    async def stream(self, messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        await self.respond(messages, info)
        yield "ordinary answer"

    async def count_tokens(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> RequestUsage:
        _ = model_settings, model_request_parameters
        self.counted.append(ModelMessagesTypeAdapter.dump_json(messages))
        return RequestUsage(input_tokens=10)


class _Dispatcher(FakeDispatcher):
    source_kind = SourceKind.SOULSTONE
    family = CapabilityFamily.CHAT
    wait = False

    @asynccontextmanager
    async def lease_grant(self, **kwargs: Any) -> AsyncGenerator[CapabilityGrant]:
        if self.wait:
            raise HardwareTransitionRequired(CAPABILITY)
        async with super().lease_grant(**kwargs) as grant:
            grant.spec.source_kind = self.source_kind
            grant.spec.family = self.family
            yield grant


class _Webcrawler:
    def __init__(self) -> None:
        self.verdict: Literal["pending", "granted", "refused"] = "pending"
        self.acquisitions = 0
        self.consumptions = 0
        self.settlements = 0
        self.lost = False
        self.revoked = False

    async def prepare(self, *, run_id: str, binding: WebcrawlerBinding) -> WebcrawlerReviewRef:
        _ = run_id, binding
        return webcrawler_review()

    async def consent(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef
    ) -> Literal["pending", "granted", "refused"]:
        _ = run_id, binding, review
        return self.verdict

    async def acquire(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerMaterial:
        _ = run_id, binding, review
        if self.lost:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.MATERIAL_UNAVAILABLE)
        self.acquisitions += 1
        self.lost = True
        return webcrawler_material()

    def authorize_consume(
        self,
        *,
        run_id: str,
        binding: WebcrawlerBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerMaterial,
        capability_key: str,
    ) -> None:
        _ = run_id, binding, review, material
        assert capability_key == CAPABILITY
        self.consumptions += 1
        if self.revoked:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.CONSENT)

    async def authorize_settle(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef, receipt_id: UUID | None
    ) -> None:
        _ = run_id, binding, review, receipt_id
        self.settlements += 1


def _context() -> tuple[GraphRunContext[WebcrawlerChatState, WorkflowServices], _Webcrawler, _Dispatcher, _Model, FakeTurns]:
    model, webcrawler, turns = _Model(), _Webcrawler(), FakeTurns()
    dispatcher = _Dispatcher(model=model, key=CAPABILITY)
    services = make_services(
        model=model, events=FakeEvents(), turns=turns, consents=FakeConsents(), orchestrator=FakeOrchestrator()
    )
    services = replace(services, webcrawler=webcrawler, dispatcher=dispatcher)
    intent = Intent(
        session_id="session",
        run_id=str(UUID(int=10)),
        prompt=PROMPT,
        admitted_capability_key=CAPABILITY,
        admitted_webcrawler=webcrawler_binding(),
    )
    state = cast("WebcrawlerChatState", BRIDGE_CHAT_WEBCRAWLER.make_state(intent))
    return GraphRunContext(state=state, deps=services), webcrawler, dispatcher, model, turns


@pytest.mark.asyncio
async def test_consent_then_local_acquire_answer_and_settle_keeps_source_out_of_state_and_history() -> None:
    ctx, webcrawler, dispatcher, model, turns = _context()
    turns.seed_session("session", turns=[], message_history=[{"content": "OLD_HISTORY_MUST_NOT_REPLAY"}])
    assert isinstance(await PreparePageReview().run(ctx), AwaitPageConsent)
    with pytest.raises(ConsentPending):
        await AwaitPageConsent().run(ctx)
    assert webcrawler.acquisitions == 0
    assert dispatcher.calls == []
    webcrawler.verdict = "granted"
    assert isinstance(await AwaitPageConsent().run(ctx), AcquireAndAnswerPage)
    assert isinstance(await AcquireAndAnswerPage().run(ctx), SettlePageAnswer)
    assert webcrawler.acquisitions == 1
    assert webcrawler.consumptions >= 2
    assert dispatcher.capability_key_calls == [CAPABILITY]
    assert dispatcher.requires_tools_calls == [False]
    assert model.tools == []
    assert "WEBCRAWLER_RAW_SOURCE" not in ctx.state.model_dump_json()
    assert all(b"OLD_HISTORY_MUST_NOT_REPLAY" not in wire for wire in model.sent)
    assert model.counted == model.sent
    source = ModelMessagesTypeAdapter.validate_json(model.sent[0])[0]
    assert isinstance(source, ModelRequest)
    part = source.parts[0]
    assert isinstance(part, UserPromptPart)
    assert isinstance(part.content, str)
    envelope = json.loads(part.content)
    assert envelope["text"] == SOURCE_TEXT
    assert envelope["instruction_authority"] == "none"
    assert envelope["attribution"]["contacted_url"] == webcrawler_material().contacted_url
    restored = WebcrawlerChatState.model_validate_json(ctx.state.model_dump_json())
    result = await SettlePageAnswer().run(GraphRunContext(state=restored, deps=ctx.deps))
    assert result.data.answer == "ordinary answer"
    assert "WEBCRAWLER_RAW_SOURCE" not in repr(turns.sessions["session"].message_history)
    assert webcrawler.acquisitions == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["portal", "key", "family"])
async def test_nonlocal_or_different_model_refuses_before_fetch(fault: str) -> None:
    ctx, webcrawler, dispatcher, model, _ = _context()
    ctx.state.review = webcrawler_review()
    if fault == "portal":
        dispatcher.source_kind = SourceKind.PORTAL
    elif fault == "key":
        dispatcher.key = "different:chat:key"
    else:
        dispatcher.family = CapabilityFamily.TOOL_EXECUTION
    await AcquireAndAnswerPage().run(ctx)
    assert ctx.state.refusal == "model"
    assert webcrawler.acquisitions == 0
    assert model.sent == []


@pytest.mark.asyncio
async def test_hardware_wait_precedes_claim_and_material_loss_never_refetches() -> None:
    ctx, webcrawler, dispatcher, model, _ = _context()
    ctx.state.review = webcrawler_review()
    dispatcher.wait = True
    with pytest.raises(HardwareTransitionRequired):
        await AcquireAndAnswerPage().run(ctx)
    assert webcrawler.acquisitions == 0
    dispatcher.wait = False
    webcrawler.lost = True
    await AcquireAndAnswerPage().run(ctx)
    assert ctx.state.refusal == "material_unavailable"
    assert webcrawler.acquisitions == 0
    assert model.sent == []


@pytest.mark.asyncio
async def test_denied_consent_never_leases_or_acquires() -> None:
    ctx, webcrawler, dispatcher, model, _ = _context()
    ctx.state.review = webcrawler_review()
    webcrawler.verdict = "refused"
    assert isinstance(await AwaitPageConsent().run(ctx), SettlePageAnswer)
    assert ctx.state.refusal == "consent"
    assert dispatcher.calls == []
    assert webcrawler.acquisitions == 0
    assert model.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["count", "request", "stream"])
async def test_transient_projection_checks_current_authority_before_each_provider_handoff(operation: str) -> None:
    model = _Model()
    allowed = True

    def authorize() -> None:
        if not allowed:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.CONSENT)

    wrapped = WebcrawlerModel(model, material=webcrawler_material(), authorize=authorize, max_chars=16000)
    assert wrapped.projected_chars() > len(SOURCE_TEXT)
    allowed = False
    messages: list[ModelMessage] = [ModelRequest.user_text_prompt(QUESTION)]
    parameters = ModelRequestParameters()

    async def invoke() -> None:
        if operation == "count":
            await wrapped.count_tokens(messages, None, parameters)
        elif operation == "request":
            await wrapped.request(messages, None, parameters)
        else:
            async with wrapped.request_stream(messages, None, parameters):
                pytest.fail("revoked stream opened")

    with pytest.raises(WebcrawlerWorkflowError):
        await invoke()
    assert model.sent == model.counted == []
    assert b"webcrawler_public_page" not in ModelMessagesTypeAdapter.dump_json(messages)


@pytest.mark.asyncio
async def test_agent_result_does_not_serialize_injected_projection_and_oversize_refuses() -> None:
    model = _Model()
    projected = WebcrawlerModel(model, material=webcrawler_material(), authorize=lambda: None, max_chars=16000)
    result = await Agent(projected).run(QUESTION)
    assert b"WEBCRAWLER_RAW_SOURCE" not in result.new_messages_json()
    assert b"webcrawler_public_page" not in result.all_messages_json()
    with pytest.raises(WebcrawlerWorkflowError):
        WebcrawlerModel(model, material=webcrawler_material(), authorize=lambda: None, max_chars=1)
