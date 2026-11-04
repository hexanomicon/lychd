"""Real HTTP, registry, Core driver and PostgreSQL with intercepted local model wires."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest
import respx
from litestar import Litestar
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AuthenticationResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.config.settings import SettingsSnapshot
from lychd.db.archive import DbArchiveStore
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from lychd.domain.animation.embeddings import EmbeddingBinding
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.archive import ArchiveService
from lychd.domain.archive.derivation import DerivationRequest, GenerationRef
from lychd.domain.codex.middleware import SigilAuthMiddleware
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.interface.web.archive_access import LocalArchivePolicy
from lychd.interface.web.archive_derivation import ArchiveDerivationController
from lychd.interface.web.archive_derivation_factory import build_archive_derivation
from tests.integration import test_archive_pg as notes
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.container,
    pytest.mark.httpx2(assert_all_called=False),
]
pg_url = notes.pg_url
factory = notes.factory


async def test_http_factory_uses_shared_leases_without_run_event_authority(  # noqa: PLR0915 - one real HTTP lifecycle/lease receipt
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    httpx2_mock: respx.MockRouter,
) -> None:
    stone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "embedding",
            "port": 8080,
            "base_url": "http://127.0.0.1:8080/v1",
            "embedding_profile": PROFILE.profile_id,
            "model_path": "/models/embedding.gguf",
            "quadlet": {"image": IMAGE},
        }
    )
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(stone,), portals=()), runtime_adapters=(LlamaCppRuntimeAdapter(),)
    )
    binding = EmbeddingBinding(capability_key=f"embedding:embedding:{PROFILE.model_id}", profile_digest=PROFILE.digest)
    leases = LeaseLedger()
    generation_id = uuid4()
    settings = SettingsSnapshot(
        payload=json.dumps(
            {
                "archive": {
                    "profile": notes.PROFILE.model_dump(mode="json"),
                    "derivation": {"generation_id": str(generation_id), "binding": binding.model_dump(mode="json")},
                }
            }
        )
    ).materialize()
    monkeypatch.setattr("lychd.db.engine.get_session_factory", lambda: factory)
    service = build_archive_derivation(settings, registry, leases, default_local_sigil())
    assert service is not None
    # Assembly has no database registration or readiness/model effects.
    async with factory() as session:
        assert list(await session.scalars(select(ArchiveEmbeddingGeneration))) == []
    assert not httpx2_mock.calls
    caller = [default_local_sigil()]
    policy = LocalArchivePolicy(profile=notes.PROFILE, caller=caller[0], derivations=True)
    archive = ArchiveService(profile=notes.PROFILE, store=DbArchiveStore(factory), authorizer=policy)
    candidate = await archive.admit(notes.SUBJECT, notes.proposal(), purpose="archive:manage")
    note = await archive.promote(
        notes.SUBJECT, candidate.reference.record_id, expected_version=1, purpose="archive:manage"
    )

    class LocalCaller(SigilAuthMiddleware):
        async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
            await super().authenticate_request(connection)
            return AuthenticationResult(user=caller[0], auth=None)

    services = SimpleNamespace(
        archive=archive,
        archive_derivation=service,
        substrate=SimpleNamespace(archive_subject_resolver=policy.subject_for),
    )
    app = Litestar(
        route_handlers=[ArchiveDerivationController],
        middleware=[DefineMiddleware(LocalCaller, access_password=TEST_ACCESS_PASSWORD)],
        state=State({"services": services}),
    )
    httpx2_mock.get("http://127.0.0.1:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://127.0.0.1:8080/v1/models").respond(200, json={"data": [{"id": PROFILE.model_id}]})
    observed: list[str] = []

    def model(request: httpx.Request) -> httpx.Response:
        assert len(leases.active()) == 1
        observed.append(request.url.path)
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": [1, 2, 3]})
        return httpx.Response(
            200,
            json={
                "model": PROFILE.model_id,
                "data": [{"index": 0, "embedding": [0.03125] * 1024}],
                "usage": {"prompt_tokens": 3, "total_tokens": 3},
            },
        )

    httpx2_mock.post("http://127.0.0.1:8080/tokenize").mock(side_effect=model)
    httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").mock(side_effect=model)
    foreign_run = uuid4()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)),
        base_url="http://testserver.local",
        headers={"authorization": TEST_AUTHORIZATION},
    ) as client:
        discovery_path = "/api/v1/archive/derivations/generations/configured"
        assert (await client.get(discovery_path, headers={"authorization": ""})).status_code == 401
        discovered = await client.get(discovery_path)
        assert discovered.status_code == 200, discovered.text
        assert discovered.json() == service.reference.model_dump(mode="json")
        assert not httpx2_mock.calls
        assert leases.active() == []
        async with factory() as session:
            assert list(await session.scalars(select(ArchiveEmbeddingGeneration))) == []
            assert list(await session.scalars(select(ArchiveNoteEmbedding))) == []
        request = DerivationRequest(
            generation=GenerationRef.model_validate(discovered.json()), source=note.reference, run_id=foreign_run
        )
        body = request.model_dump(mode="json")
        registered = await client.post("/api/v1/archive/derivations/generations/register", json=discovered.json())
        assert registered.status_code == 201, registered.text
        leases.begin_drain(["embedding"])
        waiting = await client.post("/api/v1/archive/derivations/derive", json=body)
        assert waiting.status_code == 409, waiting.text
        assert "embedding_unavailable" in waiting.text
        assert observed == []
        leases.end_drain(["embedding"])
        completed = await client.post("/api/v1/archive/derivations/derive", json=body)
        assert completed.status_code == 201, completed.text
        assert completed.json()["state"] == "complete"
        assert observed == ["/tokenize", "/v1/embeddings"]
        assert leases.active() == []
        status = await client.post("/api/v1/archive/derivations/status", json=body)
        assert status.status_code == 201
        assert not {"text", "vector", "token", "attempt_token"}.intersection(status.json())
        assert (
            await client.post("/api/v1/archive/derivations/derive", json={**body, "manifest": {}})
        ).status_code == 400
        caller[0] = replace(caller[0], name="foreign")
        assert (await client.get(discovery_path)).status_code == 403
        assert (await client.post("/api/v1/archive/derivations/status", json=body)).status_code == 403
        services.archive_derivation = None
        assert (await client.get(discovery_path)).status_code == 404
        assert (await client.post("/api/v1/archive/derivations/status", json=body)).status_code == 404
    async with factory() as session:
        row = await session.scalar(select(ArchiveNoteEmbedding))
        assert row is not None
        assert row.run_id == foreign_run
    # No Run/Step tables even exist in this fixture: a Run event write would fail.
