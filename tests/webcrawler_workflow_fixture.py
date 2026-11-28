"""Shared Webcrawler admission, PostgreSQL custody and node choreography for live proofs.

Callers supply the acquisition profile, prompt and deterministic model answer.
Model inference and queue publication remain inert; this helper does not replace
Fetch or extraction, create runtime files, or own database lifecycle.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_graph import GraphRunContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.webcrawler_chat import (
    BRIDGE_CHAT_WEBCRAWLER,
    AcquireAndAnswerPage,
    AwaitPageConsent,
    PreparePageReview,
    WebcrawlerChatState,
)
from lychd.config.settings import BridgeCastingSettings, WeaverSettings
from lychd.db.sessions import DbBridgeSessionStore
from lychd.db.webcrawler import DbWebcrawlerAttemptStore
from lychd.domain.animation.capabilities import CapabilityGrant, SourceKind
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import ConsentPending
from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy
from lychd.domain.web.consent_reviews import ConsentReviewForbiddenError
from lychd.domain.webcrawler.profile import WEBCRAWLER_ANSWER_PURPOSE, WebcrawlerProfile, WebcrawlerWorkflowError
from lychd.interface.web.webcrawler_admission import WebcrawlerAdmissionService
from lychd.interface.web.webcrawler_review import WebcrawlerConsentReviews
from lychd.system.services.webcrawler_workflow import WebcrawlerCompletions, WebcrawlerWorkflowService
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeDispatcher, FakeEvents, FakeOrchestrator, FakeTurns
from tests.webcrawler_fixtures import CAPABILITY


class _Queue:
    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = job_or_func
        return SimpleNamespace(key=kwargs["key"])


class _LocalDispatcher(FakeDispatcher):
    @asynccontextmanager
    async def lease_grant(self, **kwargs: Any) -> AsyncGenerator[CapabilityGrant]:
        async with super().lease_grant(**kwargs) as grant:
            grant.spec.source_kind = SourceKind.SOULSTONE
            grant.spec.family = CapabilityFamily.CHAT
            yield grant


@dataclass
class WebcrawlerWorkflowFixture:
    access: LocalOperatorAccess
    authentication: LocalOperatorAuthentication
    profile: WebcrawlerProfile
    authorizer: ScoutHostAuthorizer
    ledger: DbRunLedger
    consents: CodexConsentLedger
    store: DbWebcrawlerAttemptStore
    service: WebcrawlerWorkflowService
    reviews: WebcrawlerConsentReviews
    context: GraphRunContext[WebcrawlerChatState, WorkflowServices]
    model_requests: list[bytes]
    turns: DbBridgeSessionStore
    engine: RunEngine


def workflow_service(
    factory: async_sessionmaker[AsyncSession],
    profile: WebcrawlerProfile,
    authorizer: ScoutHostAuthorizer,
    ledger: DbRunLedger,
    consents: CodexConsentLedger,
) -> tuple[DbWebcrawlerAttemptStore, WebcrawlerWorkflowService]:
    completions = WebcrawlerCompletions()
    store = DbWebcrawlerAttemptStore(factory, authorizer, profile.budget_limits, completions)
    return store, WebcrawlerWorkflowService(
        store=store,
        completions=completions,
        ledger=ledger,
        consents=consents,
        profile=profile,
        capability_key=CAPABILITY,
        authorizer=authorizer,
        fence=RunEffectFence(),
    )


async def assemble_workflow(
    factory: async_sessionmaker[AsyncSession],
    *,
    profile: WebcrawlerProfile,
    prompt: str,
    answer: str,
    claim_initial: bool = True,
) -> WebcrawlerWorkflowFixture:
    """Assemble real admission, custody and nodes with inert model and queue adapters."""
    access = LocalOperatorAccess(access_password="fixture-secret")  # noqa: S106 - inert local test credential
    authentication = access.authenticate(username=b"magus", password=b"fixture-secret")
    assert authentication is not None
    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=profile.policy_revision,
            revocation_generation=profile.revocation_generation,
            actions=frozenset(ScoutAction),
            purposes=frozenset({WEBCRAWLER_ANSWER_PURPOSE}),
            categories=frozenset({"public-web-locator"}),
            binding_digests=frozenset({profile.binding_digest}),
            resolver_custody_digests=frozenset({profile.resolver_custody_digest}),
        ),
    )
    admission = WebcrawlerAdmissionService(access=access, authorizer=authorizer, profile=profile)
    with pytest.raises(WebcrawlerWorkflowError):
        admission.declare(prompt=prompt, request_id=uuid4(), authentication=replace(authentication))
    proof = admission.declare(prompt=prompt, request_id=uuid4(), authentication=authentication)
    ledger, consents = DbRunLedger(session_factory=factory), CodexConsentLedger(session_factory=factory)
    store, service = workflow_service(factory, profile, authorizer, ledger, consents)
    turns = DbBridgeSessionStore(factory, sigil_name=default_local_sigil().name)
    session = await turns.create_session()
    bus = InProcessEventBus()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(
            weaver=WeaverSettings(
                bridge=BridgeCastingSettings(
                    revision="4",
                    capability_key=CAPABILITY,
                    webcrawler=profile,
                )
            )
        ),
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": cast("Any", _Queue())},
        bridge_capability_key=CAPABILITY,
        bridge_webcrawler=profile,
        webcrawler_admission=admission,
        effects=service,
    )
    try:
        handle = await engine.submit(Intent(session_id=session.id, prompt=prompt), webcrawler_declaration=proof)
    finally:
        await bus.aclose()
    if claim_initial:
        assert (await ledger.try_claim_run(handle.run_id, enqueue_seq=0)).acknowledged is True
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.admitted_webcrawler is not None
    assert run.admitted_webcrawler.declaration == proof.declaration
    requests: list[bytes] = []

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert not info.function_tools
        requests.append(ModelMessagesTypeAdapter.dump_json(messages))
        return ModelResponse(parts=[TextPart(answer)])

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        await respond(messages, info)
        yield answer

    model = FunctionModel(respond, stream_function=stream)
    services = make_services(
        model=model,
        events=FakeEvents(),
        turns=FakeTurns(),
        consents=FakeConsents(),
        orchestrator=FakeOrchestrator(),
    )
    services = replace(
        services,
        webcrawler=service,
        consents=consents,
        turns=turns,
        dispatcher=_LocalDispatcher(model=model, key=CAPABILITY),
    )
    state = cast("WebcrawlerChatState", BRIDGE_CHAT_WEBCRAWLER.make_state(run.to_intent()))
    return WebcrawlerWorkflowFixture(
        access,
        authentication,
        profile,
        authorizer,
        ledger,
        consents,
        store,
        service,
        WebcrawlerConsentReviews(access=access, authorizer=authorizer, store=store),
        GraphRunContext(state=state, deps=services),
        requests,
        turns,
        engine,
    )


async def approve_workflow(assembly: WebcrawlerWorkflowFixture, *, expected_url: str) -> None:
    """Approve the retained native review and claim its exact continuation."""
    ctx = assembly.context
    assert isinstance(await PreparePageReview().run(ctx), AwaitPageConsent)
    assert ctx.state.review is not None
    review = ctx.state.review
    with pytest.raises(ConsentPending):
        await AwaitPageConsent().run(ctx)
    await assembly.ledger.park_consent(ctx.state.run_id, str(review.consent_id))
    view = await assembly.consents.get(str(review.consent_id))
    assert view is not None
    assert view.status == "pending"
    with pytest.raises(ConsentReviewForbiddenError):
        await assembly.reviews.resolve(
            consent=view,
            reviewer=default_local_sigil(),
            purpose="decide",
            authentication=replace(assembly.authentication),
        )
    resolution = await assembly.reviews.resolve(
        consent=view, reviewer=default_local_sigil(), purpose="decide", authentication=assembly.authentication
    )
    assert resolution.decision_allowed
    assert resolution.document is not None
    assert any(fact.value == expected_url for fact in resolution.document.facts)
    granted = await assembly.consents.decide(
        str(review.consent_id),
        approved=True,
        decided_by=default_local_sigil().name,
        expected_native_binding=resolution.binding,
    )
    assert granted is not None
    assert granted.status == "granted"
    seq = await assembly.ledger.try_admit_consent(ctx.state.run_id, consent_id=str(review.consent_id))
    assert seq == 1
    assert (await assembly.ledger.try_claim_run(ctx.state.run_id, enqueue_seq=seq)).acknowledged is True
    assert isinstance(await AwaitPageConsent().run(ctx), AcquireAndAnswerPage)
