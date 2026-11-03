"""Synthetic CPU custody proof against an explicitly owned disposable PostgreSQL.

No runtime/socket/container construction, microphone, provider or model invocation.
Run serially: each test recreates ONLY the two new dictation tables.
"""

from __future__ import annotations

import asyncio
import base64
import importlib
import json
import os
import struct
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, UniqueConstraint, event, inspect, select, text, update
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import ArgumentError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.db.dictation import (
    DbDictationStore,
    DictationStoreError,
    _lock_id,  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
)
from lychd.db.dictation_lexicon import DbDictationLexiconStore
from lychd.db.models.dictation import BridgeDictationAttempt
from lychd.db.models.dictation_lexicon import BridgeDictationLexiconRule
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.dictation import (
    DictationAttemptIdentity,
    DictationCorrectionRequest,
    DictationError,
    DictationLexiconRuleRequest,
    DictationProfile,
    DictationRequest,
    DictationResult,
)
from lychd.domain.dictation_lexicon import DictationLexiconError, DictationSuggestionRequest
from lychd.domain.dictation_lexicon_service import DictationLexiconService
from lychd.domain.dictation_service import DictationService
from lychd.domain.speech_probe import content_digest

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)
TABLES = cast("list[Table]", [BridgeDictationAttempt.__table__, BridgeDictationLexiconRule.__table__])


@pytest.fixture(scope="module")
def pg_url() -> str:
    direct = os.environ.get("LYCHD_DICTATION_TEST_DATABASE_URL")
    if not direct:
        pytest.skip("requires explicit disposable LYCHD_DICTATION_TEST_DATABASE_URL")
    try:
        url = make_url(direct)
        valid = (
            os.environ.get("LYCHD_TEST_CONTAINER") == "1"
            and url.drivername == "postgresql+asyncpg"
            and url.host == "dictation-postgres"
            and url.port == 5432
            and url.database == "dictation_test"
            and not url.query
        )
    except (ArgumentError, ValueError, TypeError):
        valid = False
    if not valid:
        pytest.fail("requires isolated dictation-postgres:5432/dictation_test OCI fixture", pytrace=False)
    return direct


def migrate(connection: Connection) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        for name in ("0025_bridge_dictation", "0026_bridge_dictation_lexicon"):
            importlib.import_module(f"lychd.db.migrations.versions.{name}").upgrade()


@pytest_asyncio.fixture(params=["models", "migrations"])
async def pg_factory(pg_url: str, request: pytest.FixtureRequest) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(BridgeDictationAttempt.metadata.drop_all, tables=TABLES)
            if request.param == "migrations":
                await connection.run_sync(migrate)
            else:
                await connection.run_sync(BridgeDictationAttempt.metadata.create_all, tables=TABLES)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(BridgeDictationAttempt.metadata.drop_all, tables=TABLES)
        await engine.dispose()


def profile(**updates: Any) -> DictationProfile:
    return DictationProfile.model_validate_json(
        json.dumps(
            {
                "transcriber_binding": {
                    "runtime": "whisper.cpp",
                    "dialect": "whisper.cpp-batch-v1",
                    "endpoint": "http://127.0.0.1:8080",
                    "runtime_revision": "a" * 40,
                    "backend": "cpu",
                    "device": "host",
                    "model": {
                        "model": "synthetic",
                        "family": "whisper-small",
                        "digest": "sha256:" + "b" * 64,
                        "languages": ["en"],
                        "license": "MIT",
                    },
                },
                **updates,
            }
        )
    )


def wav() -> bytes:
    pcm = b"\x00\x00" * 8
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            16000,
            32000,
            2,
            16,
            b"data",
            len(pcm),
        )
        + pcm
    )


def identity(pinned: DictationProfile, number: int = 1, owner: str = "alice") -> DictationAttemptIdentity:
    return DictationAttemptIdentity(
        owner=owner,
        attempt_id=UUID(int=(int(NOW.timestamp() * 1000) << 80) | (7 << 76) | (2 << 62) | number),
        source_digest=content_digest(wav()),
        profile_digest=pinned.digest,
        language="en",
    )


def result(owned: DictationAttemptIdentity, words: str = "lich a+b renewal") -> DictationResult:
    return DictationResult(
        attempt_id=owned.attempt_id,
        status="transcribed",
        source_digest=owned.source_digest,
        profile_digest=owned.profile_digest,
        language=owned.language,
        original_text=words,
    )


def approval(heard: str = "lich", replacement: str = "LychD") -> DictationLexiconRuleRequest:
    return DictationLexiconRuleRequest(language="en", heard=heard, replacement=replacement, approved=True)


async def test_two_connections_dispatch_once_and_reconstruct_exact_owner(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    pinned = profile()
    owned = identity(pinned)
    first, second = DbDictationStore(pg_factory, now=lambda: NOW), DbDictationStore(pg_factory, now=lambda: NOW)
    claims = await asyncio.gather(first.claim(owned, wav(), NOW, pinned), second.claim(owned, wav(), NOW, pinned))
    assert sum(claim.dispatch for claim in claims) == 1
    assert all(claim.record.result is not None and claim.record.result.status == "unknown" for claim in claims)
    settled = await first.settle(owned, result(owned), NOW)
    correction = await second.correct(
        "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Edited"), NOW
    )
    rebuilt = DbDictationStore(pg_factory, now=lambda: NOW)
    assert await rebuilt.get_result("alice", owned.attempt_id, NOW) == settled
    assert await rebuilt.list_corrections("alice", NOW) == (correction,)
    assert correction.original_text == "lich a+b renewal"
    assert await rebuilt.get_result("bob", owned.attempt_id, NOW) is None
    assert await rebuilt.list_corrections("bob", NOW) == ()
    with pytest.raises(DictationError, match="expired"):
        await rebuilt.correct("bob", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Foreign"), NOW)
    assert not (await rebuilt.claim(owned, wav(), NOW, pinned)).dispatch


async def test_delete_erases_bytes_and_old_id_cannot_reacquire_dispatch(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = NOW
    pinned = profile()
    owned = identity(pinned)
    store = DbDictationStore(pg_factory, now=lambda: clock)
    await store.claim(owned, wav(), NOW, pinned)
    await store.settle(owned, result(owned), NOW)
    await store.correct(
        "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Private correction"), NOW
    )
    assert await store.delete("alice", owned.attempt_id, NOW)
    async with pg_factory() as session:
        row = (
            await session.execute(
                select(
                    BridgeDictationAttempt.content_json,
                    BridgeDictationAttempt.raw_audio,
                    BridgeDictationAttempt.raw_size,
                )
            )
        ).one()
        assert tuple(row) == (None, None, 0)
    with pytest.raises(DictationError, match="expired"):
        await store.claim(owned, wav(), NOW, pinned)
    clock = NOW + timedelta(seconds=301)
    await store.purge(clock)
    async with pg_factory() as session:
        assert (await session.scalars(select(BridgeDictationAttempt))).all() == []
    with pytest.raises(DictationError, match="expired"):
        await DbDictationStore(pg_factory, now=lambda: clock).claim(owned, wav(), clock, pinned)


async def test_zero_raw_retention_never_inserts_database_bytes(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    # Inspect immediately after claim, before any read/purge boundary could hide a leak.
    pinned = profile(raw_audio_retention_seconds=0)
    claim = await DbDictationStore(pg_factory, now=lambda: NOW).claim(identity(pinned), wav(), NOW, pinned)
    assert claim.dispatch
    assert not claim.record.audio_available
    async with pg_factory() as session:
        assert tuple(
            (await session.execute(select(BridgeDictationAttempt.raw_audio, BridgeDictationAttempt.raw_size))).one()
        ) == (None, 0)


async def test_claim_quota_serializes_and_tombstones_count(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    pinned = profile(max_records_per_owner=1)
    stores = [DbDictationStore(pg_factory, now=lambda: NOW) for _ in range(2)]
    attempts = [identity(pinned, number=n) for n in (1, 2)]
    outcomes = await asyncio.gather(
        *(store.claim(owned, wav(), NOW, pinned) for store, owned in zip(stores, attempts, strict=True)),
        return_exceptions=True,
    )
    assert sum(isinstance(item, DictationError) and item.reason == "capacity" for item in outcomes) == 1
    winner = next(
        owned for owned, outcome in zip(attempts, outcomes, strict=True) if not isinstance(outcome, BaseException)
    )
    await stores[0].delete("alice", winner.attempt_id, NOW)
    with pytest.raises(DictationError, match="capacity"):
        await stores[1].claim(identity(pinned, 3), wav(), NOW, pinned)


async def test_service_commit_before_call_correction_suggestion_delete(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    pinned = profile(raw_audio_retention_seconds=0)
    owned = identity(pinned)
    calls = 0

    class CommittedTranscriber:
        profile = pinned

        async def transcribe(self, source: ArtifactRef, content: bytes, language: str) -> str:
            nonlocal calls
            calls += 1
            assert source.classification == "private"
            assert content == wav()
            assert language == "en"
            # A separate transaction must see the committed unknown before the fake call.
            observed = await DbDictationStore(pg_factory, now=lambda: NOW).get_result("alice", owned.attempt_id, NOW)
            assert observed is not None
            assert observed.status == "unknown"
            return "lich a+b renewal"

    store = DbDictationStore(pg_factory, now=lambda: NOW)
    service = DictationService(store=store, profile=pinned, transcriber=CommittedTranscriber(), now=lambda: NOW)
    vocabulary = DictationLexiconService(
        store=DbDictationLexiconStore(pg_factory, now=lambda: NOW), attempts=store, now=lambda: NOW
    )
    incoming = DictationRequest(
        attempt_id=owned.attempt_id, language="en", audio_base64=base64.b64encode(wav()).decode()
    )
    try:
        actual = await service.transcribe("alice", incoming, authorize=lambda: None)
        assert actual == result(owned)
        assert await service.transcribe("alice", incoming, authorize=lambda: None) == actual
        assert calls == 1
        correction = await service.correct(
            "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="My edit")
        )
        assert correction.original_text == actual.original_text
        assert await vocabulary.list_rules("alice") == ()
        approved = await vocabulary.approve("alice", approval())
        literal = await vocabulary.approve("alice", approval("a+b", "sum"))
        await vocabulary.approve("alice", approval("new", "must not match renewal"))
        suggestion = await vocabulary.suggest(
            "alice", DictationSuggestionRequest(attempt_id=owned.attempt_id), authorize=lambda: None
        )
        assert suggestion.original_text == "lich a+b renewal"
        assert suggestion.suggested_text == "LychD sum renewal"
        assert suggestion.applied_rule_ids == (approved.id, literal.id)
        assert await service.get_result("alice", owned.attempt_id) == actual
        with pytest.raises(DictationLexiconError, match="unavailable"):
            await vocabulary.suggest(
                "bob", DictationSuggestionRequest(attempt_id=owned.attempt_id), authorize=lambda: None
            )
        await service.delete("alice", owned.attempt_id)
        assert await service.list_corrections("alice") == ()
        with pytest.raises(DictationLexiconError, match="unavailable"):
            await vocabulary.suggest(
                "alice", DictationSuggestionRequest(attempt_id=owned.attempt_id), authorize=lambda: None
            )
        # Explicit approval custody is independent: delete it explicitly too.
        for rule in await vocabulary.list_rules("alice"):
            await vocabulary.delete("alice", rule.id)
        assert await vocabulary.list_rules("alice") == ()
        assert (await service.transcribe("alice", incoming, authorize=lambda: None)).reason == "expired"
        assert calls == 1
    finally:
        await service.aclose()


async def test_lexicon_parallel_retry_conflict_and_last_quota_slot(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first, second = (
        DbDictationLexiconStore(pg_factory, now=lambda: NOW),
        DbDictationLexiconStore(pg_factory, now=lambda: NOW),
    )
    copies = await asyncio.gather(first.approve("alice", approval(), NOW), second.approve("alice", approval(), NOW))
    assert copies[0] == copies[1]
    with pytest.raises(DictationLexiconError, match="conflict"):
        await second.approve("alice", approval(replacement="Different"), NOW)
    for n in range(126):
        await first.approve("alice", approval(f"word{n}"), NOW)
    outcomes = await asyncio.gather(
        first.approve("alice", approval("last-a"), NOW),
        second.approve("alice", approval("last-b"), NOW),
        return_exceptions=True,
    )
    assert sum(isinstance(item, DictationLexiconError) and item.reason == "capacity" for item in outcomes) == 1
    assert len(await DbDictationLexiconStore(pg_factory, now=lambda: NOW).list_rules("alice", NOW)) == 128
    assert await second.list_rules("bob", NOW) == ()


async def _expiry_operation(
    store: DbDictationStore, operation: str, owned: DictationAttemptIdentity, pinned: DictationProfile
) -> object:
    if operation == "claim":
        return await store.claim(owned, wav(), NOW, pinned)
    if operation == "correct":
        return await store.correct(
            "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Too late"), NOW
        )
    if operation == "settle":
        return await store.settle(owned, result(owned), NOW)
    if operation == "list_corrections":
        return await store.list_corrections("alice", NOW)
    return await store.get_result("alice", owned.attempt_id, NOW)


@pytest.mark.parametrize("operation", ["claim", "get_result", "correct", "settle", "list_corrections"])
async def test_expiry_is_resampled_after_real_owner_lock_wait(
    pg_factory: async_sessionmaker[AsyncSession], operation: str
) -> None:
    clock = NOW
    pinned = profile(retention_seconds=1)
    owned = identity(pinned)
    store = DbDictationStore(pg_factory, now=lambda: clock)
    if operation != "claim":
        await store.claim(owned, wav(), NOW, pinned)
        if operation != "settle":
            await store.settle(owned, result(owned), NOW)
            await store.correct(
                "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Private"), NOW
            )
    # Domain-separated key is implementation-owned; sharing it here observes the real lock.
    key = _lock_id("alice")
    unsigned = key & ((1 << 64) - 1)
    async with pg_factory() as blocker, blocker.begin():
        await blocker.execute(text("SELECT pg_advisory_xact_lock(CAST(:key AS BIGINT))"), {"key": key})
        call = _expiry_operation(store, operation, owned, pinned)
        pending = asyncio.create_task(call)
        try:
            async with asyncio.timeout(1.5):
                while True:
                    waiting = await blocker.scalar(
                        text(
                            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted "
                            "AND classid = :high AND objid = :low AND objsubid = 1"
                        ),
                        {"high": unsigned >> 32, "low": unsigned & 0xFFFFFFFF},
                    )
                    if waiting:
                        break
                    await asyncio.sleep(0.005)
            assert not pending.done()
            clock = NOW + timedelta(seconds=301 if operation == "claim" else 1)
        except BaseException:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            raise
    if operation in {"claim", "correct"}:
        with pytest.raises(DictationError, match="expired"):
            await pending
    else:
        assert await pending == (() if operation == "list_corrections" else None)
    assert await DbDictationStore(pg_factory, now=lambda: clock).get_result("alice", owned.attempt_id, clock) is None


async def test_private_parameters_required(pg_url: str, pg_factory: async_sessionmaker[AsyncSession]) -> None:
    engine = create_async_engine(pg_url, hide_parameters=False)
    try:
        with pytest.raises(DictationStoreError, match=r"^dictation_private_parameters_required$"):
            await DbDictationStore(async_sessionmaker(engine), now=lambda: NOW).get_result(
                "alice", identity(profile()).attempt_id, NOW
            )
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    "bad",
    [
        {"owner": ""},
        {"expires_at": NOW},
        {"audio_expires_at": NOW - timedelta(seconds=1)},
        {"content_json": ""},
        {"raw_size": 1},
        {"content_json": None},
    ],
)
async def test_database_rejects_attempt_constraint_violations(
    pg_factory: async_sessionmaker[AsyncSession], bad: dict[str, Any]
) -> None:
    pinned = profile()
    await DbDictationStore(pg_factory, now=lambda: NOW).claim(identity(pinned), wav(), NOW, pinned)
    with pytest.raises(IntegrityError):
        async with pg_factory() as session, session.begin():
            await session.execute(update(BridgeDictationAttempt).values(**bad))


@pytest.mark.parametrize(
    "bad", [{"owner": ""}, {"language": "EN"}, {"heard": ""}, {"replacement": ""}, {"expires_at": NOW}]
)
async def test_database_rejects_lexicon_constraint_violations(
    pg_factory: async_sessionmaker[AsyncSession], bad: dict[str, Any]
) -> None:
    await DbDictationLexiconStore(pg_factory, now=lambda: NOW).approve("alice", approval(), NOW)
    with pytest.raises(IntegrityError):
        async with pg_factory() as session, session.begin():
            await session.execute(update(BridgeDictationLexiconRule).values(**bad))


async def test_schema_columns_checks_unique_keys_and_no_foreign_custody(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    def verify(connection: Connection) -> None:
        inspector = inspect(connection)
        for table in TABLES:
            columns = {column["name"]: column for column in inspector.get_columns(table.name)}
            assert set(columns) == set(table.columns.keys())
            for column in table.columns:
                assert columns[column.name]["nullable"] == column.nullable
            expected_checks = {
                constraint.name
                for constraint in table.constraints
                if constraint.__class__.__name__ == "CheckConstraint"
            }
            assert {constraint["name"] for constraint in inspector.get_check_constraints(table.name)} == expected_checks
            expected_uniques = {
                tuple(column.name for column in constraint.columns)
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
            }
            assert {
                tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints(table.name)
            } == expected_uniques
            assert inspector.get_foreign_keys(table.name) == []

    async with pg_factory() as session:
        connection = await session.connection()
        await connection.run_sync(verify)


@pytest.mark.parametrize("operation", ["get_result", "correct", "settle", "list_corrections", "replay", "fresh_claim"])
async def test_post_commit_deadline_does_not_return_expired_content(
    pg_factory: async_sessionmaker[AsyncSession],
    operation: str,
) -> None:
    clock = NOW
    pinned = profile(retention_seconds=1)
    owned = identity(pinned)
    store = DbDictationStore(pg_factory, now=lambda: clock)
    if operation != "fresh_claim":
        await store.claim(owned, wav(), NOW, pinned)
    if operation not in {"settle", "fresh_claim"}:
        await store.settle(owned, result(owned), NOW)
        await store.correct("alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Private"), NOW)

    def cross_deadline(_session: object) -> None:
        nonlocal clock
        clock = NOW + timedelta(seconds=1)

    # Real SQLAlchemy commit boundary, without assuming an internal clock-call count.
    session_class = AsyncSession.sync_session_class
    event.listen(session_class, "after_commit", cross_deadline)
    try:
        if operation in {"replay", "fresh_claim"}:
            with pytest.raises(DictationError, match="expired"):
                await store.claim(owned, wav(), NOW, pinned)
        elif operation == "correct":
            with pytest.raises(DictationError, match="expired"):
                await store.correct(
                    "alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="Late"), NOW
                )
        elif operation == "settle":
            assert await store.settle(owned, result(owned), NOW) is None
        elif operation == "list_corrections":
            assert await store.list_corrections("alice", NOW) == ()
        else:
            assert await store.get_result("alice", owned.attempt_id, NOW) is None
    finally:
        event.remove(session_class, "after_commit", cross_deadline)


@pytest.mark.parametrize("operation", ["list", "replay", "fresh"])
async def test_lexicon_commit_deadline_does_not_return_expired_rule(
    pg_factory: async_sessionmaker[AsyncSession],
    operation: str,
) -> None:
    clock = NOW
    store = DbDictationLexiconStore(pg_factory, retention_seconds=1, now=lambda: clock)
    if operation != "fresh":
        await store.approve("alice", approval(), NOW)

    def cross_deadline(_session: object) -> None:
        nonlocal clock
        clock = NOW + timedelta(seconds=1)

    session_class = AsyncSession.sync_session_class
    event.listen(session_class, "after_commit", cross_deadline)
    try:
        if operation == "list":
            assert await store.list_rules("alice", NOW) == ()
        else:
            with pytest.raises(DictationLexiconError, match="unavailable"):
                await store.approve("alice", approval(), NOW)
    finally:
        event.remove(session_class, "after_commit", cross_deadline)
