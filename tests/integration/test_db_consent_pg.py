"""[LINUX] PostgreSQL consent atomicity and first-verdict receipts."""

# pyright: reportMissingImports=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="[LINUX] PG runtime pass only")

from sqlalchemy import Table, delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.db.models import CodexPreauthorization, Consent, Run, Session
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.runes import CodexPreauthRune
from lychd.domain.codex.services import PREAUTH_DIGEST_PAYLOAD_KEY, ConsentService, PreauthService
from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.integration


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

    assert all(view is not None for view in views)
    statuses = {view.status for view in views if view is not None}
    deciders = {view.decided_by for view in views if view is not None}
    assert statuses in ({"granted"}, {"denied"})
    assert deciders in ({"magus:grant"}, {"magus:deny"})


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
            match="non-Rune-owned preauthorization slug.*operator-owned.*magus:operator",
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
        original_list = service.list

        async def list_then_remove_rune(*filters: Any, **kwargs: Any) -> list[CodexPreauthorization]:
            rows = cast("list[CodexPreauthorization]", await original_list(*filters, **kwargs))
            async with pg_factory() as removal_session:
                await PreauthService(session=removal_session).sync_from_runes([])
            return rows

        monkeypatch.setattr(service, "list", list_then_remove_rune)
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

    if invalidity == "expired":
        await asyncio.sleep(1.1)
    else:
        async with pg_factory() as session:
            if invalidity == "missing":
                await session.execute(
                    delete(CodexPreauthorization).where(CodexPreauthorization.slug == f"invalid-{invalidity}")
                )
            else:
                await session.execute(
                    update(CodexPreauthorization)
                    .where(CodexPreauthorization.slug == f"invalid-{invalidity}")
                    .values(enabled=False)
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
