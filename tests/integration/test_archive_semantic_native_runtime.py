"""Opt-in authenticated ASGI + registered native CPU embedding + disposable PG.

Two public synthetic sources and one stable natural query exercise current
factories/controllers. This is a fixed composition receipt, not quality or a
deployed Vessel/CLI/browser/Bridge qualification. No model response is replaced.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx
import httpx2
import pytest
from litestar import Litestar
from litestar.datastructures import State
from litestar.middleware import DefineMiddleware
from sqlalchemy import Table, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lychd.config.settings import SettingsSnapshot
from lychd.db.archive import DbArchiveStore
from lychd.db.models.archive import ArchiveIntake, ArchiveNamespace, ArchiveNote, ArchiveRecall
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from lychd.domain.animation.embeddings import EmbeddingBinding, embedding_vector_digest
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.archive import ArchiveProfile, ArchiveService, ArchiveSubject, NoteProposal, NoteRecord, text_digest
from lychd.domain.archive.derivation import DerivationReceipt, DerivationRequest, DerivationStatus
from lychd.domain.archive.semantic import SemanticRecallProjection, SemanticRecallRequest, SemanticRecallResult
from lychd.domain.codex.middleware import SigilAuthMiddleware
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.llamacpp.embedding import LlamaCppEmbeddingDriver
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.interface.web.archive import ArchiveController
from lychd.interface.web.archive_access import LocalArchivePolicy
from lychd.interface.web.archive_derivation import ArchiveDerivationController
from lychd.interface.web.archive_derivation_factory import build_archive_derivation
from lychd.interface.web.archive_semantic import ArchiveSemanticController
from lychd.interface.web.archive_semantic_factory import build_archive_semantic
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin
from tests.support import archive_semantic_runtime as proof

pytestmark = [pytest.mark.integration, pytest.mark.container]


async def _workflow(  # noqa: C901, PLR0915 - one ordered eight-operation receipt, retaining the historical/current transitions together
    root: Path,
    socket: Path,
    port: int,
    monkeypatch: pytest.MonkeyPatch,
    resources: dict[str, Any],
) -> dict[str, Any]:
    subject = ArchiveSubject(identity="local-operator")
    profile = ArchiveProfile(namespace_id=uuid4(), owner_subject=subject, policy_revision="public-notes.1")
    engine = create_async_engine(
        "postgresql+asyncpg://scout:fixture@/scout",
        connect_args={"host": str(socket)},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tables = cast(
        "list[Table]",
        [
            ArchiveNamespace.__table__,
            ArchiveNote.__table__,
            ArchiveIntake.__table__,
            ArchiveRecall.__table__,
            ArchiveEmbeddingGeneration.__table__,
            ArchiveNoteEmbedding.__table__,
        ],
    )
    wires: list[dict[str, Any]] = []
    api: list[dict[str, Any]] = []
    clients: dict[int, httpx2.AsyncClient] = {}
    executions: list[dict[str, Any]] = []
    derivations: list[dict[str, Any]] = []
    leases = LeaseLedger()
    rendered_query = PROFILE.query_prefix + proof.QUERY
    inputs = [
        rendered_query,
        proof.SUPPORT,
        proof.CONTROL,
        rendered_query,
        rendered_query,
        proof.CORRECTION,
        rendered_query,
        rendered_query,
    ]
    send = httpx2.AsyncClient.send
    original_post = LlamaCppEmbeddingDriver._post  # pyright: ignore[reportPrivateUsage]

    async def observe_post(
        driver: LlamaCppEmbeddingDriver, path: str, payload: dict[str, object], *, authorize: Callable[[], None]
    ) -> dict[str, Any]:
        # Observe only after the real bounded parser has consumed and closed its stream.
        result = await original_post(driver, path, payload, authorize=authorize)
        if path == "/tokenize" and isinstance(result.get("tokens"), list):
            entry = wires[-1]
            assert entry["path"] == path
            entry["native_input_tokens"] = len(result["tokens"])
            proof.persist(root, "http-wire-after-read.json", wires)
        return result

    async def observe(client: httpx2.AsyncClient, request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        if request.url.host == "testserver.local":
            return await send(client, request, **kwargs)
        assert request.url.scheme == "http"
        assert request.url.host == "127.0.0.1"
        assert request.url.port == port
        clients[id(client)] = client
        entry: dict[str, Any] = {"method": request.method, "path": request.url.path}
        if request.method == "POST":
            posts = [item for item in wires if item["method"] == "POST"]
            assert len(posts) < proof.POSTS
            expected_path = "/tokenize" if len(posts) % 2 == 0 else "/v1/embeddings"
            assert request.url.path == expected_path
            payload = json.loads(request.content)
            content = payload["content"] if expected_path == "/tokenize" else payload["input"]
            assert content == inputs[len(posts) // 2]
            assert len(leases.active()) == 1
            entry["rendered_sha256"] = text_digest(content)
        else:
            assert request.method == "GET"
            assert request.url.path in {"/health", "/v1/models"}
            assert sum(item["method"] == "GET" for item in wires) < 16
        wires.append(entry)
        proof.persist(root, "http-wire-before-send.json", wires)
        response = await send(client, request, **kwargs)
        entry["status"] = response.status_code
        proof.persist(root, "http-wire-after-send.json", wires)
        # Pass the original streamed response through untouched to its real driver.
        return response

    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(ArchiveNote.metadata.create_all, tables=tables)
        stone = LlamaCppSoulstoneConfig.model_validate(
            {
                "name": "embedding-proof",
                "port": port,
                "base_url": f"http://127.0.0.1:{port}/v1",
                "embedding_profile": PROFILE.profile_id,
                "model_path": "/models/embedding.gguf",
                "quadlet": {"image": IMAGE},
            }
        )
        registry = AnimatorRegistry(
            declarations=AnimatorDeclarations(soulstones=(stone,), portals=()),
            runtime_adapters=(LlamaCppRuntimeAdapter(),),
        )
        binding = EmbeddingBinding(
            capability_key=f"embedding-proof:embedding:{PROFILE.model_id}", profile_digest=PROFILE.digest
        )
        settings = SettingsSnapshot(
            payload=json.dumps(
                {
                    "archive": {
                        "profile": profile.model_dump(mode="json"),
                        "derivation": {
                            "generation_id": str(uuid4()),
                            "binding": binding.model_dump(mode="json"),
                        },
                        "semantic": True,
                    }
                }
            )
        ).materialize()
        caller = default_local_sigil()
        policy = LocalArchivePolicy(profile=profile, caller=caller)
        archive = ArchiveService(profile=profile, store=DbArchiveStore(factory), authorizer=policy)
        with monkeypatch.context() as patch:
            patch.setattr("lychd.db.engine.get_session_factory", lambda: factory)
            patch.setattr(httpx2.AsyncClient, "send", observe)
            patch.setattr(LlamaCppEmbeddingDriver, "_post", observe_post)
            derivation = build_archive_derivation(settings, registry, leases, caller)
            semantic = build_archive_semantic(settings, registry, leases, caller)
            assert derivation is not None
            assert semantic is not None
            assert derivation.reference == semantic.reference
            assert derivation.manifest == semantic.manifest
            assert not wires
            assert not leases.active()
            async with factory() as session:
                assert list(await session.scalars(select(ArchiveEmbeddingGeneration))) == []
            services = SimpleNamespace(
                archive=archive,
                archive_derivation=derivation,
                archive_semantic=semantic,
                substrate=SimpleNamespace(archive_subject_resolver=policy.subject_for),
            )
            password = "public-synthetic-native-proof-password"  # noqa: S105 - generated fixture authority only
            authorization = "Basic " + base64.b64encode(f"magus:{password}".encode()).decode()
            app = Litestar(
                route_handlers=[ArchiveController, ArchiveDerivationController, ArchiveSemanticController],
                middleware=[DefineMiddleware(SigilAuthMiddleware, access_password=password)],
                state=State({"services": services}),
                plugins=[StrictPydanticSchemaPlugin()],
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=cast("Any", app)),
                base_url="http://testserver.local",
                headers={"authorization": authorization},
            ) as client:

                async def call(method: str, path: str, body: Any = None, *, status: int = 201) -> Any:
                    response = await client.request(method, "/api/v1/archive" + path, json=body)
                    value = response.json()
                    api.append({"method": method, "path": path, "status": response.status_code, "body": value})
                    proof.persist(root, "api-before-assert.json", api)
                    assert response.status_code == status, response.text
                    assert not leases.active()
                    assert all(item.is_closed for item in clients.values())
                    return value

                async def admit(key: str, revision: str, content: str) -> NoteRecord:
                    proposal = NoteProposal(
                        namespace_id=profile.namespace_id,
                        request_id=uuid4(),
                        source_key=key,
                        source_revision=revision,
                        source_digest=text_digest(content),
                        text=content,
                        producer="operator",
                        observed_at=datetime(2026, 10, 19, tzinfo=UTC),
                    )
                    return NoteRecord.model_validate(await call("POST", "/notes", proposal.model_dump(mode="json")))

                async def promote(note: NoteRecord) -> NoteRecord:
                    response = await call(
                        "POST",
                        f"/notes/{note.reference.record_id}/promote",
                        {"expected_version": note.reference.lifecycle_version},
                    )
                    return NoteRecord.model_validate(response)

                async def derive(note: NoteRecord) -> tuple[dict[str, Any], DerivationStatus]:
                    body = DerivationRequest(generation=semantic.reference, source=note.reference).model_dump(
                        mode="json"
                    )
                    status = DerivationStatus.model_validate(await call("POST", "/derivations/derive", body))
                    assert status.state == "complete"
                    async with factory() as session:
                        row = await session.get(ArchiveNoteEmbedding, status.derivation_id)
                        observed: dict[str, Any] = {
                            "row_present": row is not None,
                            "vector_present": row is not None and row.vector is not None,
                            "receipt": row.receipt if row is not None else None,
                            "status": status.model_dump(mode="json"),
                        }
                        proof.persist(root, "derivation-before-assert.json", observed)
                        assert row is not None
                        assert row.vector is not None
                        assert row.receipt is not None
                        receipt = DerivationReceipt.model_validate(row.receipt)
                        vector_digest = embedding_vector_digest(tuple(float(value) for value in row.vector))
                        observed["postgres_vector_digest"] = vector_digest
                        proof.persist(root, "derivation-before-assert.json", observed)
                        assert vector_digest == status.vector_digest == receipt.vector_digest
                        assert receipt.profile_digest == PROFILE.digest
                        assert receipt.input_digest == note.source_digest
                        derivations.append(
                            {"status": status.model_dump(mode="json"), "receipt": receipt.model_dump(mode="json")}
                        )
                    return body, status

                path = "/semantic/recalls"

                async def query() -> tuple[dict[str, Any], SemanticRecallResult]:
                    request = SemanticRecallRequest(
                        namespace_id=profile.namespace_id,
                        request_id=uuid4(),
                        generation=semantic.reference,
                        query=proof.QUERY,
                        min_cosine=0.0,
                        max_results=2,
                        char_budget=512,
                    )
                    body = request.model_dump(mode="json")
                    result = SemanticRecallResult.model_validate(await call("POST", path, body))
                    assert result.current_query_execution == result.receipt.query_execution
                    assert result.current_query_execution is not None
                    executions.append(result.current_query_execution.model_dump(mode="json"))
                    assert result.receipt.query_digest == text_digest(proof.QUERY)
                    assert result.receipt.query_execution.profile_digest == PROFILE.digest
                    return body, result

                async def historical(body: dict[str, Any], result: SemanticRecallResult) -> None:
                    before = len(wires)
                    replay = SemanticRecallResult.model_validate(await call("POST", path, body))
                    assert replay.receipt == result.receipt
                    assert replay.current_query_execution is None
                    assert await call("POST", path + "/inspect", body) == result.receipt.model_dump(mode="json")
                    assert len(wires) == before

                async def resolve(result: SemanticRecallResult, *, stale: bool = False) -> Any:
                    receipt = result.receipt
                    value = await call(
                        "POST",
                        f"{path}/{receipt.receipt_id}/resolve",
                        {"receipt_digest": receipt.receipt_digest},
                        status=409 if stale else 201,
                    )
                    if stale:
                        assert value["extra"]["code"] == "source_integrity"
                        return None
                    return SemanticRecallProjection.model_validate(value)

                unauthorized = await client.get("/api/v1/archive/profile", headers={"authorization": ""})
                api.append({"path": "/profile", "status": unauthorized.status_code})
                proof.persist(root, "api-before-assert.json", api)
                assert unauthorized.status_code == 401
                assert not wires
                discovered = await call("GET", "/derivations/generations/configured", status=200)
                assert discovered == semantic.reference.model_dump(mode="json")
                assert not wires
                await call("POST", "/derivations/generations/register", discovered)
                supporting = await admit("observatory", "1", proof.SUPPORT)
                control = await admit("ferry", "1", proof.CONTROL)
                rejected = await call(
                    "POST",
                    "/derivations/derive",
                    DerivationRequest(generation=semantic.reference, source=supporting.reference).model_dump(
                        mode="json"
                    ),
                    status=409,
                )
                assert rejected["extra"]["code"] == "source_stale"
                assert not wires
                _, empty = await query()  # Operation1: candidates are unavailable.
                assert empty.receipt.selected == ()
                assert empty.receipt.coverage.promoted_notes == empty.receipt.coverage.eligible_notes == 0
                supporting, control = await promote(supporting), await promote(control)
                original_body, original_status = await derive(supporting)  # Operation2.
                await derive(control)  # Operation3.
                before = len(wires)
                replayed_derivation = DerivationStatus.model_validate(
                    await call("POST", "/derivations/derive", original_body)
                )
                assert replayed_derivation.model_dump(exclude={"observed_at"}) == original_status.model_dump(
                    exclude={"observed_at"}
                )
                assert len(wires) == before
                original_query, selected = await query()  # Operation4.
                assert selected.receipt.coverage.promoted_notes == selected.receipt.coverage.eligible_notes == 2
                assert [item.reference for item in selected.receipt.selected] == [
                    supporting.reference,
                    control.reference,
                ]
                assert selected.receipt.selected[0].score > selected.receipt.selected[1].score
                projection = await resolve(selected)
                assert [item.text for item in projection.items] == [proof.SUPPORT, proof.CONTROL]
                assert projection.items[0].selection.source_key == "observatory"
                await historical(original_query, selected)
                correction = await admit("observatory", "2", proof.CORRECTION)
                correction = await promote(correction)
                invalidated = await call("POST", "/derivations/status", original_body)
                assert invalidated["state"] == "invalidated"
                async with factory() as session:
                    row = await session.get(ArchiveNoteEmbedding, original_status.derivation_id)
                    proof.persist(
                        root,
                        "correction-fence-before-assert.json",
                        {
                            "row_present": row is not None,
                            "vector_cleared": row is not None and row.vector is None,
                            "attempt_cleared": row is not None and row.attempt_token is None,
                        },
                    )
                    assert row is not None
                    assert row.vector is None
                    assert row.attempt_token is None
                await resolve(selected, stale=True)
                await historical(original_query, selected)
                _, partial = await query()  # Operation5: correction needs explicit derivation.
                assert partial.receipt.coverage.promoted_notes == 2
                assert partial.receipt.coverage.eligible_notes == 1
                assert all(item.reference.record_id == control.reference.record_id for item in partial.receipt.selected)
                correction_body, correction_status = await derive(correction)  # Operation6.
                corrected_query, corrected = await query()  # Operation7.
                assert corrected.receipt.coverage.promoted_notes == corrected.receipt.coverage.eligible_notes == 2
                assert [item.reference for item in corrected.receipt.selected] == [
                    correction.reference,
                    control.reference,
                ]
                assert corrected.receipt.selected[0].score > corrected.receipt.selected[1].score
                assert (await resolve(corrected)).items[0].text == proof.CORRECTION
                await call(
                    "POST",
                    f"/notes/{correction.reference.record_id}/revoke",
                    {"expected_version": correction.reference.lifecycle_version},
                )
                assert (await call("POST", "/derivations/status", correction_body))["state"] == "invalidated"
                async with factory() as session:
                    row = await session.get(ArchiveNoteEmbedding, correction_status.derivation_id)
                    note = await session.get(ArchiveNote, correction.reference.record_id)
                    proof.persist(
                        root,
                        "revocation-fence-before-assert.json",
                        {
                            "row_present": row is not None,
                            "vector_cleared": row is not None and row.vector is None,
                            "attempt_cleared": row is not None and row.attempt_token is None,
                            "source_cleared": note is not None and note.content is None,
                        },
                    )
                    assert row is not None
                    assert row.vector is None
                    assert row.attempt_token is None
                    assert note is not None
                    assert note.content is None
                await resolve(corrected, stale=True)
                await historical(corrected_query, corrected)
                _, revoked = await query()  # Operation8.
                assert revoked.receipt.coverage.promoted_notes == revoked.receipt.coverage.eligible_notes == 1
                assert all(item.reference == control.reference for item in revoked.receipt.selected)
                assert (await resolve(revoked)).items[0].text == proof.CONTROL
                resources["generation"] = {
                    "reference": semantic.reference.model_dump(mode="json"),
                    "manifest": semantic.manifest.model_dump(mode="json"),
                }
        assert not leases.active()
        assert all(client.is_closed for client in clients.values())
        posts = [item for item in wires if item["method"] == "POST"]
        tokens = sum(item["tokens"] for item in executions) + sum(item["receipt"]["tokens"] for item in derivations)
        result = {
            "operations": len(executions) + len(derivations),
            "query_operations": len(executions),
            "derivation_operations": len(derivations),
            "native_input_tokens": tokens,
            "embedding_POSTs": len(posts),
            "tokenize_POSTs": sum(item["path"] == "/tokenize" for item in posts),
            "vector_POSTs": sum(item["path"] == "/v1/embeddings" for item in posts),
            "readiness_GETs": sum(item["method"] == "GET" for item in wires),
            "executions": executions,
            "derivations": derivations,
            "leases_remaining": len(leases.active()),
            "all_observed_clients_closed": all(client.is_closed for client in clients.values()),
            "profile_digest": PROFILE.digest,
        }
        proof.persist(root, "proof-before-assert.json", result)
        assert result["operations"] == proof.OPERATIONS
        assert len(posts) == proof.POSTS
        assert result["tokenize_POSTs"] == result["vector_POSTs"] == proof.OPERATIONS
        assert result["readiness_GETs"] == 16
        assert 0 < tokens <= proof.NATIVE_TOKENS
        assert sum(item["native_input_tokens"] for item in wires if item["path"] == "/tokenize") == tokens
        return result
    finally:
        resources["leases_remaining"] = len(leases.active())
        resources["all_observed_clients_closed"] = all(client.is_closed for client in clients.values())
        proof.persist(
            root,
            "workflow-final.json",
            {
                "wires": wires,
                "api": api,
                "executions": executions,
                "derivations": derivations,
                "leases_remaining": len(leases.active()),
                "all_observed_clients_closed": all(client.is_closed for client in clients.values()),
            },
        )
        await engine.dispose()


def test_archive_semantic_native_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = proof.run_native_semantic_proof(tmp_path / "archive-semantic-native", monkeypatch, _workflow)
    assert receipt["status"] == "passed"
    assert receipt["cleanup"] == "passed"
    assert receipt["artifact_unchanged_after_cleanup"] is True
