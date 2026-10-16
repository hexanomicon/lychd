"""[LINUX] PostgreSQL consent atomicity and first-verdict receipts."""

# pyright: reportMissingImports=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import Table, delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.db.models import CodexPreauthorization, Consent, Run, Session
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.runes import CodexPreauthRune
from lychd.domain.codex.schemas import CENSORED_VALUE, ConsentBindingConflict
from lychd.domain.codex.services import (
    PREAUTH_DIGEST_PAYLOAD_KEY,
    ConsentService,
    PreauthService,
    preauth_authorization_digest,
)
from lychd.domain.codex.sigil import Sigil
from tests.codex.test_native_consent import binding

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from lychd.domain.codex.schemas import ConsentDecision

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Keep one disposable PostgreSQL container alive for this module."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Build and dispose the asyncpg pool on the current pytest event loop."""
    engine: AsyncEngine = create_async_engine(pg_url)
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            CodexPreauthorization.__table__,
            Consent.__table__,
        ],
    )
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _run_id(factory: async_sessionmaker[AsyncSession]) -> str:
    async with factory() as session:
        row = Run(
            workflow_name="bridge_chat",
            pattern_manifest={},
            source="bridge",
            status="queued",
            priority=70,
            sigil_name="magus",
            intent={},
            queue_name="runs",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return str(row.id)


def _preauth_row(slug: str, **overrides: Any) -> CodexPreauthorization:
    values: dict[str, Any] = {
        "klass": "standard",
        "sigil_pattern": "magus",
        "tool_pattern": "request_coven_swap",
        "constraints": {},
        "expires_at": None,
        "max_uses": None,
        "uses": 0,
        "enabled": True,
        "granted_by": "codex:rune",
    }
    values.update(overrides)
    return CodexPreauthorization(slug=slug, **values)


def _rune(slug: str, **overrides: Any) -> CodexPreauthRune:
    values: dict[str, Any] = {"tool_pattern": "request_coven_swap"}
    values.update(overrides)
    return CodexPreauthRune(slug=slug, **values)


async def _park_with_preauth(
    factory: async_sessionmaker[AsyncSession],
    *,
    slug: str,
    expires_at: datetime | None = None,
) -> tuple[CodexConsentLedger, str]:
    run_id = await _run_id(factory)
    async with factory() as session:
        session.add(_preauth_row(slug, expires_at=expires_at))
        await session.commit()
    ledger = CodexConsentLedger(session_factory=factory)
    decision = await ledger.park(
        run_id=run_id,
        tool_name="request_coven_swap",
        tool_call_id=f"call-{slug}",
        call_ids=(f"call-{slug}",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    assert decision.status == "granted"
    return ledger, decision.consent_id


@pytest.mark.asyncio
async def test_overlapping_preauth_priority_matches_memory_order(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        session.add_all(
            [
                _preauth_row("z-low", priority=10),
                _preauth_row("z-tie", priority=80),
                _preauth_row("a-tie", priority=80),
            ]
        )
        await session.commit()
    ledger = CodexConsentLedger(session_factory=pg_factory)

    decision = await ledger.park(
        run_id=run_id,
        tool_name="request_coven_swap",
        tool_call_id="priority-call",
        call_ids=("priority-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )

    assert decision.preauth_slug == "a-tie"


@pytest.mark.asyncio
async def test_contradictory_concurrent_verdicts_keep_the_first_commit(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        row = Consent(
            run_id=UUID(run_id),
            tool_name="request_coven_swap",
            tool_call_id="call-race",
            payload={"args": {}},
            status="pending",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        consent_id = str(row.id)

    grant = CodexConsentLedger(session_factory=pg_factory)
    deny = CodexConsentLedger(session_factory=pg_factory)
    views = await asyncio.gather(
        grant.decide(consent_id, approved=True, decided_by="magus:grant"),
        deny.decide(consent_id, approved=False, decided_by="magus:deny"),
    )

    winner = views[0]
    assert winner is not None
    assert (winner.status, winner.decided_by) in {
        ("granted", "magus:grant"),
        ("denied", "magus:deny"),
    }
    assert winner.decided_at is not None
    assert views[1] == winner

    reopened = CodexConsentLedger(session_factory=pg_factory)
    assert await reopened.get(consent_id) == winner
    late = await reopened.decide(consent_id, approved=winner.status == "denied", decided_by="magus:late")
    assert late == winner
    assert await CodexConsentLedger(session_factory=pg_factory).get(consent_id) == winner


@pytest.mark.asyncio
async def test_run_cancellation_settles_pending_consent_durably(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    decision = await ledger.park(
        run_id=run_id,
        tool_name="request_coven_swap",
        tool_call_id="call-cancel",
        call_ids=("call-cancel",),
        args={"target": "chat:local"},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    assert decision.status == "pending"

    assert await ledger.cancel_pending_for_run(run_id) == 1
    assert await ledger.cancel_pending_for_run(run_id) == 0

    view = await ledger.get(decision.consent_id)
    assert view is not None
    assert view.status == "cancelled"
    assert view.decided_by == "cortex:run-cancelled"
    assert await ledger.verdict(decision.consent_id) is False
    assert await ledger.pending_count() == 0


@pytest.mark.asyncio
async def test_consent_payload_is_censored_before_postgres_storage(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    sentinel = "durable-secret-sentinel"
    args = {
        "authorization": sentinel,
        "nested": {"unknown": sentinel},
        "items": [sentinel],
    }
    async with pg_factory() as session:
        session.add(
            _preauth_row(
                "raw-argument-match",
                constraints={"args": {"authorization": [sentinel]}},
            )
        )
        await session.commit()

    decision = await ledger.park(
        run_id=run_id,
        tool_name="request_coven_swap",
        tool_call_id="call-censor",
        call_ids=("call-censor",),
        args=args,
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    assert decision.status == "granted"
    assert decision.preauth_slug == "raw-argument-match"

    async with pg_factory() as session:
        payload = await session.scalar(select(Consent.payload).where(Consent.id == UUID(decision.consent_id)))
    assert isinstance(payload, dict)
    assert payload["args"] == dict.fromkeys(args, CENSORED_VALUE)
    assert sentinel not in json.dumps(payload)
    view = await ledger.get(decision.consent_id)
    assert view is not None
    assert view.args == dict.fromkeys(args, CENSORED_VALUE)


@pytest.mark.asyncio
async def test_legacy_raw_consent_payload_is_censored_at_the_read_boundary(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    sentinel = "legacy-secret-sentinel"
    raw_args = {
        "reason": sentinel,
        "authorization": sentinel,
        "nested": {"unknown": sentinel},
    }
    async with pg_factory() as session:
        row = Consent(
            run_id=UUID(run_id),
            tool_name="legacy_tool",
            tool_call_id="legacy-call",
            payload={"args": raw_args},
            status="pending",
        )
        session.add(row)
        await session.commit()
        consent_id = str(row.id)

    view = await ledger.get(consent_id)

    assert view is not None
    assert view.args == dict.fromkeys(raw_args, CENSORED_VALUE)
    assert sentinel not in json.dumps(view.args)


@pytest.mark.asyncio
async def test_malformed_consent_read_identity_is_absent(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = CodexConsentLedger(session_factory=pg_factory)

    assert await ledger.get("not-a-uuid") is None


@pytest.mark.asyncio
async def test_preauth_use_rolls_back_when_consent_insert_fails(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        session.add(
            CodexPreauthorization(
                slug="atomic-preauth",
                klass="standard",
                sigil_pattern="magus",
                tool_pattern="request_coven_swap",
                constraints={},
                max_uses=1,
                uses=0,
                enabled=True,
                granted_by="test",
            )
        )
        await session.commit()

    original_request = ConsentService.request

    async def fail_request(self: ConsentService, **kwargs: Any) -> Consent:
        _ = (self, kwargs)
        message = "injected consent insert failure"
        raise RuntimeError(message)

    monkeypatch.setattr(ConsentService, "request", fail_request)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    with pytest.raises(RuntimeError, match="injected consent insert failure"):
        await ledger.park(
            run_id=run_id,
            tool_name="request_coven_swap",
            tool_call_id="call-fail",
            call_ids=("call-fail",),
            args={},
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
        )

    async with pg_factory() as session:
        uses = await session.scalar(
            select(CodexPreauthorization.uses).where(CodexPreauthorization.slug == "atomic-preauth")
        )
        consent_count = await session.scalar(select(func.count()).select_from(Consent))
    assert uses == 0
    assert consent_count == 0

    monkeypatch.setattr(ConsentService, "request", original_request)
    decision = await ledger.park(
        run_id=run_id,
        tool_name="request_coven_swap",
        tool_call_id="call-success",
        call_ids=("call-success",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    assert decision.status == "granted"

    async with pg_factory() as session:
        uses = await session.scalar(
            select(CodexPreauthorization.uses).where(CodexPreauthorization.slug == "atomic-preauth")
        )
        consent_count = await session.scalar(select(func.count()).select_from(Consent))
    assert uses == 1
    assert consent_count == 1


@pytest.mark.asyncio
async def test_concurrent_preauth_consumers_cannot_overdraw_one_use(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        session.add(_preauth_row("single-use", max_uses=1))
        await session.commit()

    async def consume() -> CodexPreauthorization | None:
        async with pg_factory() as session:
            return await PreauthService(session=session).match_and_consume(
                sigil=Sigil(name="magus", scopes=frozenset({"*"})),
                tool_name="request_coven_swap",
                payload={},
            )

    consumed = await asyncio.gather(consume(), consume())

    assert sum(row is not None for row in consumed) == 1
    async with pg_factory() as session:
        uses = await session.scalar(
            select(CodexPreauthorization.uses).where(CodexPreauthorization.slug == "single-use")
        )
    assert uses == 1


@pytest.mark.asyncio
async def test_rune_sync_reconciles_complete_set_without_resetting_operator_state(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        session.add_all(
            [
                _preauth_row("present", uses=4, tool_pattern="old-present"),
                _preauth_row("manual-disabled", uses=2, enabled=False, tool_pattern="old-disabled"),
                _preauth_row("removed", uses=3),
                _preauth_row("operator-owned", granted_by="magus:operator"),
            ]
        )
        await session.commit()

    runes = [
        _rune("present", tool_pattern="new-present", max_uses=9),
        _rune("manual-disabled", tool_pattern="new-disabled", constraints={"args": {"mode": ["safe"]}}),
        _rune("new-policy", tool_pattern="new-tool"),
    ]
    async with pg_factory() as session:
        assert await PreauthService(session=session).sync_from_runes(runes) == 3

    async with pg_factory() as session:
        rows = (await session.scalars(select(CodexPreauthorization))).all()
    by_slug = {row.slug: row for row in rows}
    assert (by_slug["present"].tool_pattern, by_slug["present"].uses, by_slug["present"].enabled) == (
        "new-present",
        4,
        True,
    )
    assert (
        by_slug["manual-disabled"].tool_pattern,
        by_slug["manual-disabled"].uses,
        by_slug["manual-disabled"].enabled,
    ) == ("new-disabled", 2, False)
    assert by_slug["removed"].enabled is True
    assert by_slug["removed"].source_present is False
    assert by_slug["operator-owned"].enabled is True
    assert by_slug["operator-owned"].source_present is True
    assert (by_slug["new-policy"].uses, by_slug["new-policy"].enabled) == (0, True)

    async with pg_factory() as session:
        assert await PreauthService(session=session).sync_from_runes([_rune("removed")]) == 1
    async with pg_factory() as session:
        reappeared = await session.scalar(select(CodexPreauthorization).where(CodexPreauthorization.slug == "removed"))
        disabled = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "manual-disabled")
        )
    assert reappeared is not None
    assert reappeared.enabled is True
    assert reappeared.source_present is True
    assert disabled is not None
    assert disabled.enabled is False
    assert disabled.source_present is False


@pytest.mark.asyncio
async def test_rune_sync_rejects_duplicate_slugs_before_mutation(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        session.add(_preauth_row("existing", uses=3, tool_pattern="unchanged"))
        await session.commit()

    async with pg_factory() as session:
        with pytest.raises(ValueError, match=r"Duplicate preauthorization Rune slug\(s\): a, z"):
            await PreauthService(session=session).sync_from_runes(
                [
                    _rune("z", tool_pattern="first-z"),
                    _rune("a", tool_pattern="first-a"),
                    _rune("z", tool_pattern="second-z"),
                    _rune("a", tool_pattern="second-a"),
                ]
            )

    async with pg_factory() as session:
        rows = (await session.scalars(select(CodexPreauthorization))).all()
    assert [(row.slug, row.tool_pattern, row.uses, row.source_present) for row in rows] == [
        ("existing", "unchanged", 3, True)
    ]


@pytest.mark.asyncio
async def test_rune_sync_refuses_non_rune_owned_slug_without_partial_mutation(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        session.add_all(
            [
                _preauth_row(
                    "operator-owned",
                    granted_by="magus:operator",
                    uses=7,
                    tool_pattern="operator-tool",
                ),
                _preauth_row("rune-owned", uses=2, tool_pattern="old-rune-tool"),
            ]
        )
        await session.commit()

    async with pg_factory() as session:
        with pytest.raises(
            ValueError,
            match=r"non-Rune-owned preauthorization slug.*operator-owned.*magus:operator",
        ):
            await PreauthService(session=session).sync_from_runes(
                [
                    _rune("new-rune"),
                    _rune("operator-owned", tool_pattern="forged-overwrite"),
                ]
            )

    async with pg_factory() as session:
        rows = (await session.scalars(select(CodexPreauthorization))).all()
    by_slug = {row.slug: row for row in rows}
    operator = by_slug["operator-owned"]
    assert (operator.granted_by, operator.tool_pattern, operator.uses) == (
        "magus:operator",
        "operator-tool",
        7,
    )
    assert (by_slug["rune-owned"].tool_pattern, by_slug["rune-owned"].source_present) == (
        "old-rune-tool",
        True,
    )
    assert "new-rune" not in by_slug


@pytest.mark.asyncio
async def test_rune_sync_rolls_back_updates_inserts_and_absent_disables_together(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        session.add_all(
            [
                _preauth_row("present", uses=5, tool_pattern="old-present"),
                _preauth_row("removed", uses=2),
            ]
        )
        await session.commit()

    invalid_slug = "x" * 101
    async with pg_factory() as session:
        with pytest.raises(DBAPIError):
            await PreauthService(session=session).sync_from_runes(
                [
                    _rune("present", tool_pattern="new-present"),
                    _rune(invalid_slug),
                ]
            )

    async with pg_factory() as session:
        rows = (await session.scalars(select(CodexPreauthorization))).all()
    by_slug = {row.slug: row for row in rows}
    assert (by_slug["present"].tool_pattern, by_slug["present"].uses) == ("old-present", 5)
    assert by_slug["removed"].enabled is True
    assert by_slug["removed"].source_present is True
    assert invalid_slug not in by_slug


@pytest.mark.asyncio
async def test_consume_update_rechecks_expiry_with_database_time(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_expired = datetime.now(UTC) - timedelta(minutes=1)
    async with pg_factory() as session:
        session.add(_preauth_row("expired-race", expires_at=database_expired, max_uses=1))
        await session.commit()

    real_datetime = datetime

    class StalePythonClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            stale = real_datetime.now(UTC) - timedelta(days=1)
            return stale if tz is not None else stale.replace(tzinfo=None)

    monkeypatch.setattr("lychd.domain.codex.services.datetime", StalePythonClock)
    async with pg_factory() as session:
        matched = await PreauthService(session=session).match_and_consume(
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
            tool_name="request_coven_swap",
            payload={},
        )
    assert matched is None

    async with pg_factory() as session:
        uses = await session.scalar(
            select(CodexPreauthorization.uses).where(CodexPreauthorization.slug == "expired-race")
        )
    assert uses == 0


async def _wait_for_preauth_expiry(session: AsyncSession, expiry: datetime) -> None:
    """Cross a near expiry without changing the policy or either clock."""
    async with asyncio.timeout(4):
        before = await session.execute(select(func.transaction_timestamp(), func.clock_timestamp()))
        transaction_before, wall_before = before.one()
        assert isinstance(transaction_before, datetime)
        assert isinstance(wall_before, datetime)
        assert transaction_before <= wall_before < expiry
        delay = (expiry - wall_before).total_seconds() + 0.02
        assert 0 < delay <= 3.02
        await session.execute(select(func.pg_sleep(delay)))
        after = await session.execute(select(func.transaction_timestamp(), func.clock_timestamp()))
        transaction_after, wall_after = after.one()
        assert isinstance(transaction_after, datetime)
        assert isinstance(wall_after, datetime)
        assert transaction_after == transaction_before
        assert transaction_after < expiry <= wall_after


@pytest.mark.asyncio
@pytest.mark.parametrize("with_fallback", [False, True], ids=["pending", "lower-priority-fallback"])
async def test_legacy_park_rechecks_unchanged_expiry_after_candidate_await(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_fallback: bool,
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        expiry = await session.scalar(select(func.clock_timestamp() + timedelta(seconds=3)))
        assert isinstance(expiry, datetime)
        expiring = _preauth_row("a-expiring", priority=80, expires_at=expiry, max_uses=1)
        session.add(expiring)
        if with_fallback:
            session.add(_preauth_row("z-valid", priority=10, max_uses=1))
        await session.flush()
        original_digest = preauth_authorization_digest(expiring)
        await session.commit()

    original_get_many = PreauthService.get_many
    candidate_reads = 0

    async def delay_candidates(service: PreauthService, *filters: Any, **kwargs: Any) -> list[CodexPreauthorization]:
        nonlocal candidate_reads
        rows = cast("list[CodexPreauthorization]", await original_get_many(service, *filters, **kwargs))
        candidate_reads += 1
        assert {row.slug for row in rows} == ({"a-expiring", "z-valid"} if with_fallback else {"a-expiring"})
        await _wait_for_preauth_expiry(service.repository.session, expiry)
        return rows

    ledger = CodexConsentLedger(session_factory=pg_factory)
    with monkeypatch.context() as delay:
        delay.setattr(PreauthService, "get_many", delay_candidates)
        decision = await ledger.park(
            run_id=run_id,
            tool_name="request_coven_swap",
            tool_call_id="delayed-legacy-park",
            call_ids=("delayed-legacy-park",),
            args={},
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
        )
    assert candidate_reads == 1

    async with pg_factory() as session:
        policies = {row.slug: row for row in (await session.scalars(select(CodexPreauthorization))).all()}
        consents = (await session.scalars(select(Consent))).all()
    expired = policies["a-expiring"]
    assert (expired.expires_at, expired.uses, expired.enabled, expired.source_present) == (expiry, 0, True, True)
    assert preauth_authorization_digest(expired) == original_digest
    assert len(consents) == 1
    consent = consents[0]
    assert (str(consent.id), str(consent.run_id), consent.tool_call_id) == (
        decision.consent_id,
        run_id,
        "delayed-legacy-park",
    )
    if with_fallback:
        assert policies["z-valid"].uses == 1
        assert (decision.status, decision.preauth_slug) == ("granted", "z-valid")
        assert (consent.status, consent.preauth_slug, consent.decided_by) == ("granted", "z-valid", "codex:preauth")
        assert consent.decided_at is not None
        assert consent.payload[PREAUTH_DIGEST_PAYLOAD_KEY] == preauth_authorization_digest(policies["z-valid"])
        assert await ledger.verdict(decision.consent_id) is True
    else:
        assert (decision.status, decision.preauth_slug) == ("pending", None)
        assert (consent.status, consent.preauth_slug, consent.decided_by, consent.decided_at) == (
            "pending",
            None,
            None,
            None,
        )
        assert PREAUTH_DIGEST_PAYLOAD_KEY not in consent.payload
        assert await ledger.verdict(decision.consent_id) is None


@pytest.mark.asyncio
async def test_preauth_verdict_rechecks_unchanged_expiry_after_policy_await(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    async with pg_factory() as session:
        expiry = await session.scalar(select(func.clock_timestamp() + timedelta(seconds=3)))
        assert isinstance(expiry, datetime)
    ledger, consent_id = await _park_with_preauth(pg_factory, slug="expiry-during-verdict", expires_at=expiry)
    assert await ledger.verdict(consent_id) is True
    async with pg_factory() as session:
        consent_before = await session.get(Consent, UUID(consent_id))
        assert consent_before is not None
        stored_digest = consent_before.payload[PREAUTH_DIGEST_PAYLOAD_KEY]
        policy_before = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "expiry-during-verdict")
        )
        assert policy_before is not None
        assert (policy_before.uses, policy_before.expires_at) == (1, expiry)
        assert preauth_authorization_digest(policy_before) == stored_digest

    original_scalar = AsyncSession.scalar
    policy_reads = 0

    async def delay_policy(session: AsyncSession, statement: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal policy_reads
        result = await original_scalar(session, statement, *args, **kwargs)
        if isinstance(result, CodexPreauthorization):
            policy_reads += 1
            assert (result.slug, result.expires_at) == ("expiry-during-verdict", expiry)
            assert preauth_authorization_digest(result) == stored_digest
            await _wait_for_preauth_expiry(session, expiry)
        return result

    with monkeypatch.context() as delay:
        delay.setattr(AsyncSession, "scalar", delay_policy)
        verdict = await ledger.verdict(consent_id)
    assert policy_reads == 1
    assert verdict is False

    async with pg_factory() as session:
        policy_after = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "expiry-during-verdict")
        )
        consent_after = await session.get(Consent, UUID(consent_id))
        consent_count = await session.scalar(select(func.count()).select_from(Consent))
    assert policy_after is not None
    assert (policy_after.uses, policy_after.expires_at, policy_after.enabled, policy_after.source_present) == (
        1,
        expiry,
        True,
        True,
    )
    assert preauth_authorization_digest(policy_after) == stored_digest
    assert consent_count == 1
    assert consent_after is not None
    assert (consent_after.status, consent_after.decided_by) == ("granted", "codex:preauth")
    assert consent_after.decided_at == consent_before.decided_at
    assert consent_after.expires_at == consent_before.expires_at == expiry
    assert consent_after.preauth_slug == consent_before.preauth_slug == "expiry-during-verdict"
    assert consent_after.payload == consent_before.payload


async def _park_across_unchanged_preauth_lock(
    pg_factory: async_sessionmaker[AsyncSession],
    ledger: CodexConsentLedger,
    run_id: str,
    consumer_started: asyncio.Future[tuple[int, datetime]],
    expiry: datetime,
    original_digest: str,
) -> ConsentDecision:
    async with pg_factory() as blocker, pg_factory() as observer:
        locked = await blocker.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "unchanged-lock").with_for_update()
        )
        assert locked is not None
        assert preauth_authorization_digest(locked) == original_digest
        blocker_pid = await blocker.scalar(select(func.pg_backend_pid()))
        assert isinstance(blocker_pid, int)
        park = asyncio.create_task(
            ledger.park(
                run_id=run_id,
                tool_name="request_coven_swap",
                tool_call_id="unchanged-lock-call",
                call_ids=("unchanged-lock-call",),
                args={},
                sigil=Sigil(name="magus", scopes=frozenset({"*"})),
            )
        )
        try:
            async with asyncio.timeout(1):
                consumer_pid, consumer_transaction = await consumer_started
                assert consumer_pid != blocker_pid
                while True:
                    observation = await observer.execute(
                        select(func.pg_blocking_pids(consumer_pid), func.clock_timestamp())
                    )
                    blocking_pids, observed_at = observation.one()
                    assert isinstance(blocking_pids, list)
                    assert isinstance(observed_at, datetime)
                    assert consumer_transaction <= observed_at < expiry
                    assert not park.done()
                    if blocker_pid in blocking_pids:
                        break
                    await asyncio.sleep(0.01)
            await _wait_for_preauth_expiry(observer, expiry)
            release_at = await observer.scalar(select(func.clock_timestamp()))
            assert isinstance(release_at, datetime)
            assert consumer_transaction < expiry <= release_at
            assert preauth_authorization_digest(locked) == original_digest
            assert not blocker.dirty
            assert not park.done()
            await blocker.commit()
            async with asyncio.timeout(2):
                decision = await park
        finally:
            if not park.done():
                park.cancel()
            async with asyncio.timeout(2):
                await blocker.rollback()
                await asyncio.gather(park, return_exceptions=True)
    return decision


@pytest.mark.asyncio
async def test_legacy_park_rechecks_expiry_after_observed_unchanged_row_lock(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        expiry = await session.scalar(select(func.clock_timestamp() + timedelta(seconds=3)))
        assert isinstance(expiry, datetime)
        policy = _preauth_row("unchanged-lock", expires_at=expiry, max_uses=1)
        session.add(policy)
        await session.flush()
        original_digest = preauth_authorization_digest(policy)
        await session.commit()

    original_get_many = PreauthService.get_many
    candidate_reads = 0
    consumer_started: asyncio.Future[tuple[int, datetime]] = asyncio.get_running_loop().create_future()

    async def observe_consumer(service: PreauthService, *filters: Any, **kwargs: Any) -> list[CodexPreauthorization]:
        nonlocal candidate_reads
        rows = cast("list[CodexPreauthorization]", await original_get_many(service, *filters, **kwargs))
        candidate_reads += 1
        assert [row.slug for row in rows] == ["unchanged-lock"]
        clocks = await service.repository.session.execute(
            select(func.pg_backend_pid(), func.transaction_timestamp(), func.clock_timestamp())
        )
        consumer_pid, transaction_start, wall_now = clocks.one()
        assert isinstance(consumer_pid, int)
        assert isinstance(transaction_start, datetime)
        assert isinstance(wall_now, datetime)
        assert transaction_start <= wall_now < expiry
        consumer_started.set_result((consumer_pid, transaction_start))
        return rows

    ledger = CodexConsentLedger(session_factory=pg_factory)
    with monkeypatch.context() as observe:
        observe.setattr(PreauthService, "get_many", observe_consumer)
        decision = await _park_across_unchanged_preauth_lock(
            pg_factory, ledger, run_id, consumer_started, expiry, original_digest
        )
    assert candidate_reads == 1
    assert (decision.status, decision.preauth_slug) == ("pending", None)
    async with pg_factory() as session:
        current = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "unchanged-lock")
        )
        consents = (await session.scalars(select(Consent))).all()
    assert current is not None
    assert (current.uses, current.expires_at, current.enabled, current.source_present) == (0, expiry, True, True)
    assert preauth_authorization_digest(current) == original_digest
    assert len(consents) == 1
    consent = consents[0]
    assert (str(consent.id), str(consent.run_id), consent.tool_call_id) == (
        decision.consent_id,
        run_id,
        "unchanged-lock-call",
    )
    assert (consent.status, consent.preauth_slug, consent.decided_by, consent.decided_at) == (
        "pending",
        None,
        None,
        None,
    )
    assert PREAUTH_DIGEST_PAYLOAD_KEY not in consent.payload
    assert await ledger.verdict(decision.consent_id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("changed_field", ["tool", "constraints"])
async def test_legacy_park_rechecks_current_match_after_candidate_await(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    changed_field: str,
) -> None:
    run_id = await _run_id(pg_factory)
    matching_constraints = {"args": {"mode": ["safe"]}}
    async with pg_factory() as session:
        session.add(_preauth_row("changed-candidate", constraints=matching_constraints, max_uses=1))
        await session.commit()
    new_tool = "different_tool" if changed_field == "tool" else "request_coven_swap"
    new_constraints = {"args": {"mode": ["other"]}} if changed_field == "constraints" else matching_constraints
    original_get_many = PreauthService.get_many
    candidate_reads = 0

    async def change_after_read(service: PreauthService, *filters: Any, **kwargs: Any) -> list[CodexPreauthorization]:
        nonlocal candidate_reads
        rows = cast("list[CodexPreauthorization]", await original_get_many(service, *filters, **kwargs))
        candidate_reads += 1
        assert len(rows) == 1
        cached = rows[0]
        assert (cached.slug, cached.tool_pattern, cached.constraints) == (
            "changed-candidate",
            "request_coven_swap",
            matching_constraints,
        )
        async with asyncio.timeout(2), pg_factory() as change_session:
            assert (
                await PreauthService(session=change_session).sync_from_runes(
                    [
                        _rune(
                            "changed-candidate",
                            sigil_pattern="magus",
                            tool_pattern=new_tool,
                            constraints=new_constraints,
                            max_uses=1,
                        )
                    ]
                )
                == 1
            )
            current = await change_session.scalar(
                select(CodexPreauthorization).where(CodexPreauthorization.slug == "changed-candidate")
            )
            assert current is not None
            assert (current.id, current.tool_pattern, current.constraints, current.uses) == (
                cached.id,
                new_tool,
                new_constraints,
                0,
            )
        assert (cached.tool_pattern, cached.constraints) == ("request_coven_swap", matching_constraints)
        return rows

    ledger = CodexConsentLedger(session_factory=pg_factory)
    with monkeypatch.context() as change:
        change.setattr(PreauthService, "get_many", change_after_read)
        decision = await ledger.park(
            run_id=run_id,
            tool_name="request_coven_swap",
            tool_call_id="changed-candidate-call",
            call_ids=("changed-candidate-call",),
            args={"mode": "safe"},
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
        )
    assert candidate_reads == 1
    assert (decision.status, decision.preauth_slug) == ("pending", None)
    async with pg_factory() as session:
        current = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "changed-candidate")
        )
        consents = (await session.scalars(select(Consent))).all()
    assert current is not None
    assert (current.tool_pattern, current.constraints) == (new_tool, new_constraints)
    assert (current.uses, current.expires_at, current.max_uses, current.enabled, current.source_present) == (
        0,
        None,
        1,
        True,
        True,
    )
    assert len(consents) == 1
    consent = consents[0]
    assert (str(consent.id), str(consent.run_id), consent.tool_call_id) == (
        decision.consent_id,
        run_id,
        "changed-candidate-call",
    )
    assert (consent.status, consent.preauth_slug, consent.decided_by, consent.decided_at) == (
        "pending",
        None,
        None,
        None,
    )
    assert PREAUTH_DIGEST_PAYLOAD_KEY not in consent.payload
    assert await ledger.verdict(decision.consent_id) is None


@pytest.mark.asyncio
async def test_consume_update_rechecks_rune_presence_after_candidate_selection(
    pg_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with pg_factory() as session:
        session.add(_preauth_row("removed-race", max_uses=1))
        await session.commit()

    async with pg_factory() as session:
        service = PreauthService(session=session)
        original_get_many = service.get_many

        async def get_many_then_remove_rune(*filters: Any, **kwargs: Any) -> list[CodexPreauthorization]:
            rows = cast("list[CodexPreauthorization]", await original_get_many(*filters, **kwargs))
            async with pg_factory() as removal_session:
                await PreauthService(session=removal_session).sync_from_runes([])
            return rows

        monkeypatch.setattr(service, "get_many", get_many_then_remove_rune)
        matched = await service.match_and_consume(
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
            tool_name="request_coven_swap",
            payload={},
        )

    assert matched is None
    async with pg_factory() as session:
        removed = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "removed-race")
        )
    assert removed is not None
    assert removed.source_present is False
    assert removed.uses == 0


@pytest.mark.asyncio
async def test_preauth_verdict_rejects_changed_policy_without_rewriting_first_verdict(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger, consent_id = await _park_with_preauth(pg_factory, slug="policy-change")

    async with pg_factory() as session:
        payload = await session.scalar(select(Consent.payload).where(Consent.id == UUID(consent_id)))
        assert isinstance(payload, dict)
        assert isinstance(payload.get(PREAUTH_DIGEST_PAYLOAD_KEY), str)
        await session.execute(
            update(CodexPreauthorization).where(CodexPreauthorization.slug == "policy-change").values(uses=17)
        )
        await session.commit()
    assert await ledger.verdict(consent_id) is True

    async with pg_factory() as session:
        await session.execute(
            update(CodexPreauthorization)
            .where(CodexPreauthorization.slug == "policy-change")
            .values(constraints={"args": {"mode": ["different"]}})
        )
        await session.commit()
    assert await ledger.verdict(consent_id) is False

    async with pg_factory() as session:
        consent = await session.get(Consent, UUID(consent_id))
        assert consent is not None
    assert (consent.status, consent.decided_by) == ("granted", "codex:preauth")


@pytest.mark.asyncio
async def test_removed_rune_preauth_no_longer_validates_first_verdict(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger, consent_id = await _park_with_preauth(pg_factory, slug="removed-verdict")

    async with pg_factory() as session:
        assert await PreauthService(session=session).sync_from_runes([]) == 0

    assert await ledger.verdict(consent_id) is False
    async with pg_factory() as session:
        preauth = await session.scalar(
            select(CodexPreauthorization).where(CodexPreauthorization.slug == "removed-verdict")
        )
        consent = await session.get(Consent, UUID(consent_id))
    assert preauth is not None
    assert preauth.source_present is False
    assert consent is not None
    assert (consent.status, consent.decided_by) == ("granted", "codex:preauth")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalidity", ["missing", "disabled", "expired"])
async def test_preauth_verdict_rejects_noncurrent_authority(
    pg_factory: async_sessionmaker[AsyncSession],
    invalidity: str,
) -> None:
    expires_at = datetime.now(UTC) + timedelta(seconds=1) if invalidity == "expired" else None
    ledger, consent_id = await _park_with_preauth(
        pg_factory,
        slug=f"invalid-{invalidity}",
        expires_at=expires_at,
    )

    async with pg_factory() as session:
        if invalidity == "missing":
            await session.execute(
                delete(CodexPreauthorization).where(CodexPreauthorization.slug == f"invalid-{invalidity}")
            )
        elif invalidity == "disabled":
            await session.execute(
                update(CodexPreauthorization)
                .where(CodexPreauthorization.slug == f"invalid-{invalidity}")
                .values(enabled=False)
            )
        else:
            await session.execute(
                update(CodexPreauthorization)
                .where(CodexPreauthorization.slug == f"invalid-{invalidity}")
                .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
        await session.commit()

    assert await ledger.verdict(consent_id) is False


@pytest.mark.asyncio
async def test_legacy_preauth_digest_fails_closed_while_human_grant_remains_valid(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        session.add(_preauth_row("legacy"))
        legacy = Consent(
            run_id=UUID(run_id),
            tool_name="request_coven_swap",
            tool_call_id="call-legacy",
            payload={"args": {}},
            status="granted",
            decided_by="codex:preauth",
            decided_at=datetime.now(UTC),
            preauth_slug="legacy",
        )
        human = Consent(
            run_id=UUID(run_id),
            tool_name="request_coven_swap",
            tool_call_id="call-human",
            payload={"args": {}},
            status="granted",
            decided_by="magus:operator",
            decided_at=datetime.now(UTC),
            preauth_slug="legacy",
        )
        session.add_all([legacy, human])
        await session.commit()
        await session.refresh(legacy)
        await session.refresh(human)
        legacy_id = str(legacy.id)
        human_id = str(human.id)

    ledger = CodexConsentLedger(session_factory=pg_factory)
    assert await ledger.verdict(legacy_id) is False
    assert await ledger.verdict(human_id) is True


@pytest.mark.asyncio
async def test_latest_for_run_uses_newest_deterministic_order(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    created_at = datetime.now(UTC)
    first_id = UUID(int=1)
    second_id = UUID(int=2)
    async with pg_factory() as session:
        session.add_all(
            [
                Consent(
                    id=first_id,
                    run_id=UUID(run_id),
                    tool_name="first",
                    tool_call_id="call-first",
                    payload={"args": {}},
                    status="pending",
                    created_at=created_at,
                    updated_at=created_at,
                ),
                Consent(
                    id=second_id,
                    run_id=UUID(run_id),
                    tool_name="second",
                    tool_call_id="call-second",
                    payload={"args": {}},
                    status="pending",
                    created_at=created_at,
                    updated_at=created_at,
                ),
            ]
        )
        await session.commit()

    latest = await CodexConsentLedger(session_factory=pg_factory).latest_for_run(run_id)
    assert latest is not None
    assert (latest.id, latest.tool_name) == (str(second_id), "second")


@pytest.mark.asyncio
async def test_archive_metadata_keyset_pages_do_not_hydrate_retained_session_payloads(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The production SQL page keeps UUID ties and exact timestamp precision."""
    instant = datetime(2026, 9, 8, 12, 30, 0, 123456, tzinfo=UTC)
    async with pg_factory() as session:
        session.add_all(
            Session(
                id=UUID(int=index),
                channel="bridge",
                title=f"Session {index}",
                sigil_name="magus",
                created_at=instant,
                # A full SessionRecord conversion would reject these unrelated
                # historical turns; identity navigation must not deserialize them.
                meta={"turns": [{"invalid_retained_turn": True}]},
                message_history=[{"retained": "x" * 4096}],
            )
            for index in range(1, 54)
        )
        await session.commit()
    store = DbBridgeSessionStore(pg_factory, sigil_name="magus")

    first = await store.list_session_summaries()
    assert len(first) == 51
    boundary = first[49]
    second = await store.list_session_summaries(before=(boundary.created_at, boundary.id))

    assert [item.id for item in first[:50]] + [item.id for item in second] == [
        str(UUID(int=index)) for index in range(53, 0, -1)
    ]
    assert all(item.created_at == instant for item in [*first, *second])


@pytest.mark.asyncio
async def test_archive_pending_counts_group_only_requested_sessions_in_postgres(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Several Runs aggregate to one session, excluding settled and foreign rows."""
    session_ids = [UUID(int=index) for index in range(1, 4)]
    run_owners = [session_ids[0], session_ids[0], session_ids[1], session_ids[2], None]
    async with pg_factory() as session:
        session.add_all(Session(id=session_id, sigil_name="magus") for session_id in session_ids)
        await session.flush()
        session.add_all(
            Run(
                id=UUID(int=100 + index),
                session_id=owner,
                workflow_name="bridge_chat",
                source="bridge",
                status="queued",
                priority=70,
                sigil_name="magus",
                queue_name="runs",
            )
            for index, owner in enumerate(run_owners)
        )
        await session.flush()
        session.add_all(
            Consent(
                run_id=UUID(int=100 + index),
                tool_name="archive-count",
                tool_call_id=f"pending-{index}",
                status="pending",
            )
            for index in range(len(run_owners))
        )
        session.add(
            Consent(
                run_id=UUID(int=100),
                tool_name="archive-count",
                tool_call_id="settled",
                status="denied",
                decided_by="magus",
                decided_at=datetime.now(UTC),
            )
        )
        await session.commit()
    ledger = CodexConsentLedger(session_factory=pg_factory)

    async def run_session_id(_run_id: str) -> str | None:
        pytest.fail("Grouped DB query must not hydrate Runs")

    counts = await ledger.pending_counts_for_sessions(
        frozenset(map(str, session_ids[:2])), run_session_id=run_session_id
    )

    assert counts == {str(session_ids[0]): 2, str(session_ids[1]): 1}
    assert await ledger.pending_count() == 5
    assert await ledger.pending_counts_for_sessions(frozenset(), run_session_id=run_session_id) == {}


@pytest.mark.asyncio
async def test_native_binding_round_trip_fences_and_concurrent_first_verdict(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(pg_factory)
    expected = binding()
    async with pg_factory() as session:
        row = await ConsentService(session=session).request(
            run_id=run_id,
            tool_name="place",
            tool_call_id="native",
            call_ids=("native",),
            payload={},
            preauth=None,
            native_binding=expected,
        )
        consent_id = str(row.id)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    before = await ledger.get(consent_id)
    assert before is not None
    assert before.native_review_required
    assert before.native_binding == expected
    for wrong in (None, binding(audience_digest="d" * 64)):
        with pytest.raises(ConsentBindingConflict):
            await ledger.decide(consent_id, approved=True, decided_by="wrong", expected_native_binding=wrong)
        assert await ledger.get(consent_id) == before
    results = await asyncio.gather(
        ledger.decide(consent_id, approved=True, decided_by="first", expected_native_binding=expected),
        ledger.decide(consent_id, approved=False, decided_by="second", expected_native_binding=expected),
    )
    winner = results[0]
    assert winner is not None
    assert winner.status in {"granted", "denied"}
    assert winner.decided_by == {"granted": "first", "denied": "second"}[winner.status]
    assert winner.decided_at is not None
    assert results[1] is not None
    assert results[1] == winner
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide(consent_id, approved=False, decided_by="late")
    assert await ledger.get(consent_id) == results[0]


@pytest.mark.asyncio
async def test_native_request_respects_owned_transaction_rollback(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    run_id = await _run_id(pg_factory)
    async with pg_factory() as session:
        row = await ConsentService(session=session).request(
            run_id=run_id,
            tool_name="place",
            tool_call_id="native-rollback",
            call_ids=("native",),
            payload={},
            preauth=None,
            native_binding=binding(),
            auto_commit=False,
        )
        await session.flush()
        consent_id = str(row.id)
        await session.rollback()
    assert await CodexConsentLedger(session_factory=pg_factory).get(consent_id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("approved", [False, True])
async def test_jsonb_numeric_equivalence_cannot_settle_unsupported_native_schema(
    pg_factory: async_sessionmaker[AsyncSession], *, approved: bool
) -> None:
    run_id = await _run_id(pg_factory)
    expected = binding()
    async with pg_factory() as session:
        row = Consent(
            run_id=UUID(run_id),
            tool_name="place",
            tool_call_id="unsupported-numeric-schema",
            payload={},
            status="pending",
            native_review_required=True,
            native_binding=expected.document() | {"schema_version": 1.0},
        )
        session.add(row)
        await session.commit()
        consent_id = str(row.id)
    ledger = CodexConsentLedger(session_factory=pg_factory)
    before = await ledger.get(consent_id)
    assert before is not None
    assert before.native_review_required
    assert before.native_binding is None
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide(consent_id, approved=approved, decided_by="reviewer", expected_native_binding=expected)
    assert await ledger.get(consent_id) == before
    async with pg_factory() as session:
        row = await session.get(Consent, UUID(consent_id))
        assert row is not None
        assert (row.status, row.decided_by, row.decided_at) == ("pending", None, None)
