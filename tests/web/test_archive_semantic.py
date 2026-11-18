"""Explicit semantic transport denial, purpose and safe-error boundaries; no native model proof."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from litestar import Litestar
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AuthenticationResult

from lychd.config.settings import SettingsSnapshot
from lychd.domain.animation.embeddings import EmbeddingRefused
from lychd.domain.archive import ArchiveAuthorization, ArchiveProfile, ArchiveRefused, ArchiveSubject
from lychd.domain.archive.derivation import GenerationRef
from lychd.domain.archive.semantic import SemanticRecallRequest
from lychd.domain.codex.middleware import SigilAuthMiddleware
from lychd.domain.codex.sigil import Sigil, default_local_sigil
from lychd.domain.cortex.leases import LeaseLedger
from lychd.interface.web.archive_access import LocalArchivePolicy
from lychd.interface.web.archive_semantic import ArchiveSemanticController
from lychd.interface.web.archive_semantic_factory import build_archive_semantic
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

SUBJECT = ArchiveSubject(identity="public-note-owner")
PROFILE = ArchiveProfile(namespace_id=uuid4(), owner_subject=SUBJECT, policy_revision="one")
REQUEST = SemanticRecallRequest(
    namespace_id=PROFILE.namespace_id,
    generation=GenerationRef(generation_id=uuid4(), manifest_digest="a" * 64),
    request_id=uuid4(),
    query="explicit public query",
    min_cosine=0.0,
)


def client(service: AsyncMock, *, configured: bool = True, caller: Sigil | None = None) -> httpx.AsyncClient:
    policy = LocalArchivePolicy(profile=PROFILE, caller=default_local_sigil())

    class CallerMiddleware(SigilAuthMiddleware):
        async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
            await super().authenticate_request(connection)
            return AuthenticationResult(user=caller or default_local_sigil(), auth=None)

    services = SimpleNamespace(
        archive=Mock(),
        archive_semantic=service if configured else None,
        substrate=SimpleNamespace(archive_subject_resolver=policy.subject_for),
    )
    app = Litestar(
        route_handlers=[ArchiveSemanticController],
        plugins=[StrictPydanticSchemaPlugin()],
        middleware=[DefineMiddleware(CallerMiddleware, access_password=TEST_ACCESS_PASSWORD)],
        state=State({"services": services}),
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)),
        base_url="http://testserver.local",
        headers={"authorization": TEST_AUTHORIZATION},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", ["recalls", "recalls/inspect", "recalls/5b2d8f4a-1e7c-4a9b-8d3f-0e6a2c9b7f15/resolve"]
)
async def test_semantic_absence_and_denied_callers_do_no_service_work(operation: str) -> None:
    service = AsyncMock()
    body = {"receipt_digest": "b" * 64} if operation.endswith("resolve") else REQUEST.model_dump(mode="json")
    path = "/api/v1/archive/semantic/" + operation
    async with client(service) as http:
        assert (await http.post(path, json=body, headers={"authorization": ""})).status_code == 401
    async with client(service, configured=False) as http:
        assert (await http.post(path, json=body)).status_code == 404
    foreign = Sigil(name="foreign", scopes=default_local_sigil().scopes)
    async with client(service, caller=foreign) as http:
        assert (await http.post(path, json=body)).status_code == 403
    async with client(service, caller=Sigil(name="magus", scopes=frozenset())) as http:
        assert (await http.post(path, json=body)).status_code == 403
    assert service.mock_calls == []


@pytest.mark.asyncio
async def test_query_transport_keeps_required_threshold_and_safe_domain_refusal() -> None:
    service = AsyncMock()
    service.recall.side_effect = ArchiveRefused("generation_missing")
    body = REQUEST.model_dump(mode="json")
    async with client(service) as http:
        missing = {key: value for key, value in body.items() if key != "min_cosine"}
        assert (await http.post("/api/v1/archive/semantic/recalls", json=missing)).status_code == 400
        assert service.mock_calls == []
        response = await http.post("/api/v1/archive/semantic/recalls", json=body)
    assert response.status_code == 409
    assert response.json()["extra"]["code"] == "generation_missing"
    assert REQUEST.query not in response.text
    service.recall.assert_awaited_once_with(SUBJECT, REQUEST, purpose="archive:answer")


@pytest.mark.asyncio
async def test_embedding_refusal_is_not_an_empty_semantic_result() -> None:
    service = AsyncMock()
    service.recall.side_effect = EmbeddingRefused("input_tokens")
    async with client(service) as http:
        response = await http.post("/api/v1/archive/semantic/recalls", json=REQUEST.model_dump(mode="json"))
    assert response.status_code == 409
    assert response.json()["extra"]["code"] == "input_tokens"
    assert REQUEST.query not in response.text


@pytest.mark.parametrize("action", ["semantic_recall", "semantic_resolve"])
def test_semantic_policy_needs_its_own_opt_in_and_answer_purpose(action: str) -> None:
    request = ArchiveAuthorization.model_validate(
        {
            "subject": SUBJECT,
            "namespace_id": PROFILE.namespace_id,
            "owner_subject": SUBJECT,
            "policy_revision": PROFILE.policy_revision,
            "action": action,
            "purpose": "archive:answer",
            "object_id": REQUEST.request_id,
            "binding_digest": "b" * 64,
        }
    )
    assert not LocalArchivePolicy(profile=PROFILE, caller=default_local_sigil(), derivations=True).authorize(request)
    policy = LocalArchivePolicy(profile=PROFILE, caller=default_local_sigil(), semantic=True)
    assert policy.authorize(request)
    assert not policy.authorize(request.model_copy(update={"purpose": "archive:manage"}))
    assert not policy.authorize(request.model_copy(update={"namespace_id": uuid4()}))


@pytest.mark.parametrize("with_derivation", [False, True])
def test_unselected_semantic_factory_does_not_prepare_registry_or_storage(*, with_derivation: bool) -> None:
    archive: dict[str, Any] = {"profile": PROFILE.model_dump(mode="json")}
    if with_derivation:
        archive["derivation"] = {
            "generation_id": str(uuid4()),
            "binding": {"capability_key": "local:embedding:model", "profile_digest": "a" * 64},
        }
    settings = SettingsSnapshot(payload=json.dumps({"archive": archive})).materialize()
    registry = Mock()
    leases = LeaseLedger()
    assert build_archive_semantic(settings, registry, leases, default_local_sigil()) is None
    assert registry.mock_calls == []
    assert leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["recalls", "recalls/inspect"])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_results", True),
        ("max_results", "2"),
        ("max_results", 2.0),
        ("char_budget", True),
        ("char_budget", "20"),
        ("char_budget", 20.0),
        ("min_cosine", True),
        ("min_cosine", "0.25"),
    ],
)
async def test_semantic_http_refuses_numeric_coercion_before_service(operation: str, field: str, value: object) -> None:
    service = AsyncMock()
    body = REQUEST.model_dump(mode="json")
    body[field] = value
    async with client(service) as http:
        response = await http.post("/api/v1/archive/semantic/" + operation, json=body)
    assert response.status_code == 400, response.text
    assert REQUEST.query not in response.text
    assert service.mock_calls == []
