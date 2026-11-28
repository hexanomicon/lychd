"""HTTP Webcrawler authority with real middleware/admission and inert queue/storage.

These tests prove local request wiring, not PostgreSQL custody or acquisition.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
import pytest
import pytest_asyncio
from litestar import Litestar
from litestar.datastructures import State
from litestar.middleware.authentication import AuthenticationResult
from sqlalchemy.ext.asyncio import async_sessionmaker

from lychd.agents.workflows import BRIDGE_CHAT_WEBCRAWLER, BuiltinWorkflowRegistry
from lychd.db import engine as db_engine
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.middleware import SigilAuthMiddleware, sigil_auth_middleware
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine, RunQueue
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.scout.attempts import ScoutAttemptSnapshot, ScoutPreparation, document_digest
from lychd.domain.web.contracts import CsrfClientContract
from lychd.domain.web.projection import EventProjector
from lychd.domain.webcrawler.review import page_review
from lychd.interface.web import BridgeController, altar_services
from lychd.interface.web.deps import web_dependencies
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin
from lychd.interface.web.webcrawler_review import WebcrawlerConsentReviews
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION
from tests.webcrawler_fixtures import CAPABILITY, PROMPT, webcrawler_profile

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import SimpleNamespace

    from litestar.connection import ASGIConnection

    from lychd.interface.web.webcrawler_admission import WebcrawlerAdmissionService
    from lychd.system.services.webcrawler_workflow import WebcrawlerWorkflowService

# Composition identity and the native in-memory custody fixture intentionally inspect owners.
# pyright: reportPrivateUsage=false


@dataclass
class HttpWebcrawler:
    services: SimpleNamespace
    access: LocalOperatorAccess
    service: WebcrawlerWorkflowService
    admission: WebcrawlerAdmissionService
    reviews: WebcrawlerConsentReviews
    queue: Mock
    client: httpx.AsyncClient


@pytest_asyncio.fixture
async def http_webcrawler(
    fake_services: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[HttpWebcrawler]:
    access = LocalOperatorAccess(access_password=TEST_ACCESS_PASSWORD)
    # An unbound factory constructs the real composition without connecting a database.
    monkeypatch.setattr(db_engine, "get_session_factory", async_sessionmaker)
    service, admission, reviews = altar_services._build_webcrawler(
        persistence="postgres",
        profile=webcrawler_profile(),
        capability_key=CAPABILITY,
        access=access,
        ledger=fake_services.ledger,
        consents=fake_services.consents,
        reviews=None,
    )
    assert service is not None
    assert admission is not None
    assert isinstance(reviews, WebcrawlerConsentReviews)
    queue = Mock(spec=RunQueue)
    queue.enqueue = AsyncMock(return_value=None)
    queue.job = AsyncMock(return_value=None)
    fake_services.webcrawler_admission = admission
    fake_services.run_engine = RunEngine(
        ledger=fake_services.ledger,
        bus=fake_services.bus,
        workflows=BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT_WEBCRAWLER,)),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        consents=fake_services.consents,
        bridge_capability_key=CAPABILITY,
        bridge_webcrawler=webcrawler_profile(),
        webcrawler_admission=admission,
    )
    fake_services.projector = EventProjector(
        fragments=fake_services.fragments,
        sessions=fake_services.bridge_sessions,
        consents=fake_services.consents,
        consent_reviews=reviews,
    )
    app = Litestar(
        route_handlers=[BridgeController],
        dependencies=web_dependencies,
        middleware=[sigil_auth_middleware(operator_access=access)],
        plugins=[StrictPydanticSchemaPlugin()],
        state=State(
            {
                "services": fake_services,
                "csrf_contract": CsrfClientContract(
                    cookie_name="csrftoken",
                    header_name="x-csrftoken",
                ),
            }
        ),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)),
        base_url="http://testserver.local",
        headers={"authorization": TEST_AUTHORIZATION},
    ) as client:
        yield HttpWebcrawler(fake_services, access, service, admission, reviews, queue, client)


async def request(s: HttpWebcrawler, method: str, path: str, **kwargs: Any) -> httpx.Response:
    return await asyncio.wait_for(s.client.request(method, path, **kwargs), timeout=5)


async def admit(s: HttpWebcrawler) -> tuple[str, str, str]:
    created = await request(s, "POST", "/api/v1/bridge/sessions")
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]
    request_id = str(uuid4())
    response = await request(
        s, "POST", f"/api/v1/bridge/sessions/{session_id}/messages", json={"request_id": request_id, "prompt": PROMPT}
    )
    assert response.status_code == 200, response.text
    return session_id, request_id, response.json()["run_id"]


async def seed_review(s: HttpWebcrawler, run_id: str, monkeypatch: pytest.MonkeyPatch) -> ScoutAttemptSnapshot:
    run = await s.services.ledger.get(run_id)
    binding = run.admitted_webcrawler
    p, d = binding.profile, binding.declaration
    preparation = ScoutPreparation(
        request_id=binding.request_id,
        attempt_id=uuid4(),
        run_id=UUID(run_id),
        enqueue_seq=run.enqueue_seq,
        workflow_name=run.workflow_name,
        sigil_name=run.sigil_name,
        capability_key=CAPABILITY,
        pattern_digest=document_digest(run.pattern_manifest),
        intent_digest=document_digest(run.to_intent().model_dump(mode="json")),
        subject=d.subject,
        authentication_generation=d.authentication_generation,
        declaration=d,
        url=d.url,
        provider_id=p.provider_id,
        profile=p.profile,
        binding_digest=p.binding_digest,
        configuration_digest=p.configuration_digest,
        resolver_address=p.resolver_address,
        resolver_port=p.resolver_port,
        resolver_custody_digest=p.resolver_custody_digest,
        resolver_custody_statement=p.resolver_custody_statement,
        purpose=d.purpose,
        policy_revision=p.policy_revision,
        revocation_generation=p.revocation_generation,
        expires_at=d.declared_at + timedelta(seconds=p.review_ttl_seconds),
        allowance=p.allowance,
    )
    native, _ = page_review(preparation)
    decision = await s.services.consents.park(
        run_id=run_id,
        tool_name="webcrawler.fetch_extract",
        tool_call_id=str(preparation.attempt_id),
        call_ids=(str(preparation.attempt_id),),
        args={},
        sigil=default_local_sigil(),
    )
    row = s.services.consents._rows[decision.consent_id]
    row.native_review_required, row.native_binding = True, native
    snapshot = ScoutAttemptSnapshot(
        preparation=preparation, consent_id=UUID(decision.consent_id), native_binding=native, status="prepared"
    )
    monkeypatch.setattr(s.reviews._store, "read", AsyncMock(return_value=snapshot))
    await s.services.ledger.set_status(run_id, RunStatus.RUNNING)
    await s.services.ledger.park_consent(run_id, decision.consent_id)
    return snapshot


@pytest.mark.asyncio
async def test_http_admission_uses_current_marker_and_exact_replay(http_webcrawler: HttpWebcrawler) -> None:
    s = http_webcrawler
    session_id, request_id, run_id = await admit(s)
    run = await s.services.ledger.get(run_id)
    original = run.admitted_webcrawler
    assert original.request_id == uuid5(NAMESPACE_URL, f"lychd:scout:bridge:{session_id}:{request_id}")
    assert original.declaration.source_manifest[0].source_id == original.request_id
    assert s.access.current_binding(original.declaration.subject, original.declaration.authentication_generation)
    assert run.pattern_manifest["revision"] == "4"
    assert run.admitted_capability_key == CAPABILITY
    path = f"/api/v1/bridge/sessions/{session_id}/messages"
    replay = await request(s, "POST", path, json={"request_id": request_id, "prompt": PROMPT})
    assert replay.status_code == 200
    assert replay.json()["run_id"] == run_id
    assert (await s.services.ledger.get(run_id)).admitted_webcrawler == original
    changed = await request(s, "POST", path, json={"request_id": request_id, "prompt": PROMPT + " changed"})
    assert changed.status_code == 400
    assert len((await s.services.bridge_sessions.get_session(session_id)).turns) == 1
    s.queue.enqueue.assert_awaited_once()
    s.access.revoke()
    refused = await request(s, "POST", path, json={"request_id": request_id, "prompt": PROMPT})
    assert refused.status_code == 401
    s.queue.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_http_native_consent_current_marker_resolves_and_resumes(
    http_webcrawler: HttpWebcrawler,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = http_webcrawler
    session_id, _, run_id = await admit(s)
    snapshot = await seed_review(s, run_id, monkeypatch)
    view = await request(s, "GET", f"/api/v1/bridge/sessions/{session_id}")
    card = view.json()["pending_consents"][0]
    assert card["native_review_status"] == "available"
    assert card["can_decide"] is True
    assert card["review_binding_digest"] == snapshot.native_binding.digest
    decision = await request(
        s,
        "POST",
        f"/api/v1/bridge/consents/{snapshot.consent_id}/decision",
        json={"verdict": "approve", "review_binding_digest": snapshot.native_binding.digest},
    )
    assert decision.status_code == 200, decision.text
    assert await s.services.consents.verdict(str(snapshot.consent_id)) is True
    assert s.queue.enqueue.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("forgery", ["sigil", "equal_marker"])
async def test_http_native_consent_refuses_forged_authentication(
    http_webcrawler: HttpWebcrawler,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    s = http_webcrawler
    session_id, _, run_id = await admit(s)
    snapshot = await seed_review(s, run_id, monkeypatch)
    original = SigilAuthMiddleware.authenticate_request

    async def substituted(
        self: SigilAuthMiddleware, connection: ASGIConnection[Any, Any, Any, Any]
    ) -> AuthenticationResult:
        authenticated = await original(self, connection)
        marker = default_local_sigil() if forgery == "sigil" else replace(authenticated.auth)
        return AuthenticationResult(user=authenticated.user, auth=marker)

    monkeypatch.setattr(SigilAuthMiddleware, "authenticate_request", substituted)
    view = await request(s, "GET", f"/api/v1/bridge/sessions/{session_id}")
    card = view.json()["pending_consents"][0]
    assert card["native_review_status"] == "unavailable"
    assert card["can_decide"] is False
    response = await request(
        s,
        "POST",
        f"/api/v1/bridge/consents/{snapshot.consent_id}/decision",
        json={"verdict": "approve", "review_binding_digest": snapshot.native_binding.digest},
    )
    assert response.status_code == 403
    assert await s.services.consents.verdict(str(snapshot.consent_id)) is None
    s.queue.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_http_consent_rechecks_revocation_after_retained_read(
    http_webcrawler: HttpWebcrawler,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = http_webcrawler
    _, _, run_id = await admit(s)
    snapshot = await seed_review(s, run_id, monkeypatch)

    async def revoke(_attempt_id: UUID) -> ScoutAttemptSnapshot:
        await asyncio.sleep(0)
        s.access.revoke()
        return snapshot

    monkeypatch.setattr(s.reviews._store, "read", revoke)
    response = await request(
        s,
        "POST",
        f"/api/v1/bridge/consents/{snapshot.consent_id}/decision",
        json={"verdict": "approve", "review_binding_digest": snapshot.native_binding.digest},
    )
    assert response.status_code == 403
    assert await s.services.consents.verdict(str(snapshot.consent_id)) is None
    s.queue.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_webcrawler_composition_shares_authority_and_custody(http_webcrawler: HttpWebcrawler) -> None:
    s = http_webcrawler
    assert s.service._store is s.reviews._store
    assert s.service._authorizer is s.admission._authorizer is s.reviews._authorizer
    assert s.service._store._authorizer is s.service._authorizer
    assert s.service._completions is s.service._store._settlement_verifier
    assert s.admission._access is s.reviews._access is s.access


@pytest.mark.parametrize("missing", ["postgres", "credential_owner", "capability"])
def test_webcrawler_composition_refuses_missing_prerequisites(
    fake_services: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    database = Mock(side_effect=AssertionError("No database access before prerequisite validation"))
    monkeypatch.setattr(db_engine, "get_session_factory", database)
    with pytest.raises(ValueError, match="Webcrawler requires PostgreSQL"):
        altar_services._build_webcrawler(
            persistence="memory" if missing == "postgres" else "postgres",
            profile=webcrawler_profile(),
            capability_key=None if missing == "capability" else CAPABILITY,
            access=None if missing == "credential_owner" else LocalOperatorAccess(access_password=TEST_ACCESS_PASSWORD),
            ledger=fake_services.ledger,
            consents=fake_services.consents,
            reviews=None,
        )
    database.assert_not_called()


@pytest.mark.asyncio
async def test_http_cancellation_enters_engine_before_any_ledger_read(
    http_webcrawler: HttpWebcrawler,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = http_webcrawler
    events: list[str] = []

    async def cancel(_self: RunEngine, _run_id: str, *, orphaned: bool = False) -> None:
        _ = orphaned
        events.append("cancel")

    async def read(_run_id: str) -> None:
        events.append("read")
        assert events[0] == "cancel"

    monkeypatch.setattr(RunEngine, "cancel", cancel)
    monkeypatch.setattr(s.services.ledger, "get", read)
    response = await request(s, "POST", "/api/v1/bridge/runs/unknown/cancel")
    assert response.status_code == 404
    assert events == ["cancel", "read"]
