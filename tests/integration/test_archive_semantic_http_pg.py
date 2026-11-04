"""Authenticated ASGI + PostgreSQL + Core query driver; model responses are intercepted."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest
import respx
from litestar import Litestar
from litestar.datastructures import State
from litestar.middleware import DefineMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.config.settings import SettingsSnapshot
from lychd.db.archive import DbArchiveStore
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration
from lychd.domain.animation.embeddings import EmbeddingBinding
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.archive import ArchiveService, RecallRequest
from lychd.domain.archive.derivation import DerivationRequest
from lychd.domain.archive.semantic import SemanticRecallRequest, SemanticRecallResult
from lychd.domain.codex.middleware import SigilAuthMiddleware
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.interface.web.archive import ArchiveController
from lychd.interface.web.archive_access import LocalArchivePolicy
from lychd.interface.web.archive_derivation import ArchiveDerivationController
from lychd.interface.web.archive_derivation_factory import build_archive_derivation
from lychd.interface.web.archive_semantic import ArchiveSemanticController
from lychd.interface.web.archive_semantic_factory import build_archive_semantic
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


async def test_explicit_semantic_http_lifecycle_shared_leases_and_historical_receipts(  # noqa: PLR0915 - one composed receipt with real storage and intercepted model wires
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
    settings = SettingsSnapshot(
        payload=json.dumps(
            {
                "archive": {
                    "profile": notes.PROFILE.model_dump(mode="json"),
                    "derivation": {"generation_id": str(uuid4()), "binding": binding.model_dump(mode="json")},
                    "semantic": True,
                }
            }
        )
    ).materialize()
    monkeypatch.setattr("lychd.db.engine.get_session_factory", lambda: factory)
    leases = LeaseLedger()
    caller = default_local_sigil()
    derivation = build_archive_derivation(settings, registry, leases, caller)
    semantic = build_archive_semantic(settings, registry, leases, caller)
    assert derivation is not None
    assert semantic is not None
    assert semantic.reference == derivation.reference
    assert semantic.manifest == derivation.manifest
    async with factory() as session:
        assert list(await session.scalars(select(ArchiveEmbeddingGeneration))) == []
    assert not httpx2_mock.calls
    policy = LocalArchivePolicy(profile=notes.PROFILE, caller=caller)
    archive = ArchiveService(profile=notes.PROFILE, store=DbArchiveStore(factory), authorizer=policy)
    candidate = await archive.admit(notes.SUBJECT, notes.proposal(), purpose="archive:manage")
    services = SimpleNamespace(
        archive=archive,
        archive_derivation=derivation,
        archive_semantic=semantic,
        substrate=SimpleNamespace(archive_subject_resolver=policy.subject_for),
    )
    app = Litestar(
        route_handlers=[ArchiveController, ArchiveDerivationController, ArchiveSemanticController],
        middleware=[DefineMiddleware(SigilAuthMiddleware, access_password=TEST_ACCESS_PASSWORD)],
        state=State({"services": services}),
    )
    httpx2_mock.get("http://127.0.0.1:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://127.0.0.1:8080/v1/models").respond(200, json={"data": [{"id": PROFILE.model_id}]})
    observed: list[tuple[str, dict[str, Any]]] = []

    def model(request: httpx.Request) -> httpx.Response:
        assert len(leases.active()) == 1
        payload = json.loads(request.content)
        observed.append((request.url.path, payload))
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
    initial = SemanticRecallRequest(
        namespace_id=notes.PROFILE.namespace_id,
        request_id=uuid4(),
        generation=semantic.reference,
        query="Which public source is available?",
        min_cosine=0.25,
        run_id=uuid4(),
    )
    path = "/api/v1/archive/semantic/recalls"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)),
        base_url="http://testserver.local",
        headers={"authorization": TEST_AUTHORIZATION},
    ) as client:
        missing = await client.post(path, json=initial.model_dump(mode="json"))
        assert missing.status_code == 409, missing.text
        assert missing.json()["extra"]["code"] == "generation_missing"
        assert observed == []
        registered = await client.post(
            "/api/v1/archive/derivations/generations/register", json=semantic.reference.model_dump(mode="json")
        )
        assert registered.status_code == 201, registered.text
        empty = await client.post(path, json=initial.model_dump(mode="json"))
        assert empty.status_code == 201, empty.text
        empty_result = SemanticRecallResult.model_validate(empty.json())
        assert empty_result.receipt.selected == ()
        assert empty_result.receipt.coverage.promoted_notes == empty_result.receipt.coverage.eligible_notes == 0
        promoted = await client.post(
            f"/api/v1/archive/notes/{candidate.reference.record_id}/promote", json={"expected_version": 1}
        )
        assert promoted.status_code == 201, promoted.text
        note = await archive.get_note(notes.SUBJECT, candidate.reference.record_id, purpose="archive:manage")
        derived = await client.post(
            "/api/v1/archive/derivations/derive",
            json=DerivationRequest(generation=semantic.reference, source=note.reference).model_dump(mode="json"),
        )
        assert derived.status_code == 201, derived.text
        assert derived.json()["state"] == "complete"
        expected = initial.model_copy(update={"request_id": uuid4(), "query": "What animal protects our records?"})
        body = expected.model_dump(mode="json")
        selected = await client.post(path, json=body)
        assert selected.status_code == 201, selected.text
        result = SemanticRecallResult.model_validate(selected.json())
        assert result.current_query_execution == result.receipt.query_execution
        assert result.receipt.coverage.promoted_notes == result.receipt.coverage.eligible_notes == 1
        assert len(result.receipt.selected) == 1
        assert result.receipt.selected[0].reference == note.reference
        assert result.receipt.selected[0].score == 1.0
        assert len(observed) == 6
        assert leases.active() == []
        digest = {"receipt_digest": result.receipt.receipt_digest}
        resolve_path = f"{path}/{result.receipt.receipt_id}/resolve"
        resolved = await client.post(resolve_path, json=digest)
        assert resolved.status_code == 201, resolved.text
        assert resolved.json()["items"][0]["text"] == notes.proposal().text
        leases.begin_drain(["embedding"])
        try:
            replay = await client.post(path, json=body)
            assert replay.status_code == 201, replay.text
            replayed = SemanticRecallResult.model_validate(replay.json())
            assert replayed.receipt == result.receipt
            assert replayed.current_query_execution is None
            fresh = expected.model_copy(update={"request_id": uuid4()}).model_dump(mode="json")
            waiting = await client.post(path, json=fresh)
            assert waiting.status_code == 409, waiting.text
            assert waiting.json()["extra"]["code"] == "embedding_unavailable"
        finally:
            leases.end_drain(["embedding"])
        inspected = await client.post(path + "/inspect", json=body)
        assert inspected.status_code == 201, inspected.text
        assert inspected.json() == result.receipt.model_dump(mode="json")
        retired = await client.post(
            "/api/v1/archive/derivations/generations/retire",
            json={"reference": semantic.reference.model_dump(mode="json"), "expected_version": 1},
        )
        assert retired.status_code == 201, retired.text
        historical = await client.post(path, json=body)
        assert historical.status_code == 201, historical.text
        assert SemanticRecallResult.model_validate(historical.json()).receipt == result.receipt
        assert (await client.post(path + "/inspect", json=body)).json() == inspected.json()
        stale = await client.post(resolve_path, json=digest)
        assert stale.status_code == 409, stale.text
        assert stale.json()["extra"]["code"] == "generation_retired"
        assert (await client.post(path, json=fresh)).json()["extra"]["code"] == "generation_retired"
        lexical = RecallRequest(namespace_id=notes.PROFILE.namespace_id, request_id=uuid4(), query="fox")
        lexical_result = await client.post("/api/v1/archive/recalls", json=lexical.model_dump(mode="json"))
        assert lexical_result.status_code == 201, lexical_result.text
        conflict = await client.post(path, json={**body, "request_id": str(lexical.request_id)})
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["extra"]["code"] == "request_conflict"
    assert len(observed) == 6
    assert leases.active() == []
    rendered = [initial.query, notes.proposal().text, expected.query]
    rendered[0] = PROFILE.query_prefix + rendered[0]
    rendered[2] = PROFILE.query_prefix + rendered[2]
    assert [payload["content"] for wire, payload in observed if wire == "/tokenize"] == rendered
    assert [payload["input"] for wire, payload in observed if wire == "/v1/embeddings"] == rendered
    # These fixtures create no Run/Step tables: an event write using caller run_id would fail.
    # Three intercepted operations and six POSTs are not real model inference or token use.
