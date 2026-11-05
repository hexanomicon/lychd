"""Portable native identity, decision fencing, and PostgreSQL statement contracts."""

# Typed native rows are deliberately seeded without inventing a production creation route.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import hashlib
import importlib
import io
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from lychd.db.models import Consent
from lychd.domain.codex.ledger import InMemoryConsentLedger, _ConsentRow
from lychd.domain.codex.schemas import ConsentBindingConflict, NativeConsentBinding, decode_native_binding
from lychd.domain.codex.services import ConsentService, row_to_view


def binding(**changes: Any) -> NativeConsentBinding:
    values: dict[str, Any] = {
        "owner": "blockworld",
        "action_id": "00000000-0000-0000-0000-000000000001",
        "preparation_digest": "a" * 64,
        "review_profile": "blockworld.placement",
        "review_profile_revision": "1",
        "review_producer": "blockworld.placement-review",
        "review_producer_revision": "1",
        "audience_digest": "b" * 64,
        "review_digest": "c" * 64,
    }
    return NativeConsentBinding(**(values | changes))


def test_binding_is_scalar_frozen_and_digest_has_exact_schema_bytes() -> None:
    value = binding()
    payload = value.document()
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert value.digest == hashlib.sha256(b"lychd.native-consent-binding.v1\n" + canonical).hexdigest()
    assert decode_native_binding(json.loads(json.dumps(payload))) == value
    payload["owner"] = "other"
    assert value.owner == "blockworld"
    with pytest.raises(FrozenInstanceError):
        cast("Any", value).owner = "other"
    assert replace(value, audience_digest="d" * 64).digest != value.digest


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"action_id": "invalid"},
        {"owner": ""},
        {"owner": "x" * 201},
        {"review_profile_revision": 1},
        {"audience_digest": "A" * 64},
        {"preparation_digest": "c" * 63},
        {"review_digest": {}},
        {"metadata": {}},
    ],
)
def test_binding_rejects_unsupported_or_non_scalar_identity(changes: dict[str, Any]) -> None:
    with pytest.raises((TypeError, ValueError)):
        binding(**changes)
    assert decode_native_binding(binding().document() | changes) is None


@pytest.mark.parametrize("stored", [None, {}, {"schema_version": 2}, "untrusted", {"schema_version": True}])
def test_required_storage_never_decodes_as_legacy(stored: Any) -> None:
    row = Consent(
        id=UUID(int=1),
        run_id=UUID(int=2),
        tool_name="place",
        status="granted",
        decided_by="reviewer",
        decided_at=datetime.now(UTC),
        payload={"args": {"secret": "hidden"}},
        native_review_required=True,
        native_binding=stored,
    )
    view = row_to_view(row)
    assert view.native_review_required is True
    assert view.native_binding is None
    assert "hidden" not in json.dumps(view.args)


@pytest.mark.asyncio
async def test_native_decision_requires_exact_binding_and_first_verdict_survives_retry() -> None:
    ledger = InMemoryConsentLedger()
    expected = binding()
    ledger._rows["native"] = _ConsentRow(
        id="native",
        run_id="run",
        tool_name="place",
        args={},
        call_ids=(),
        native_review_required=True,
        native_binding=expected,
    )
    before = await ledger.get("native")
    for wrong in (None, replace(expected, preparation_digest="d" * 64)):
        for approved in (True, False):
            with pytest.raises(ConsentBindingConflict):
                await ledger.decide("native", approved=approved, decided_by="wrong", expected_native_binding=wrong)
            assert await ledger.get("native") == before
    first = await ledger.decide("native", approved=False, decided_by="first", expected_native_binding=expected)
    second = await ledger.decide("native", approved=True, decided_by="second", expected_native_binding=expected)
    assert first == second
    assert first is not None
    assert first.status == "denied"
    assert first.decided_by == "first"
    assert await ledger.verdict("native") is False
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide("native", approved=True, decided_by="second")
    assert (
        await ledger.decide("missing", approved=True, decided_by="reviewer", expected_native_binding=expected) is None
    )


@pytest.mark.asyncio
async def test_malformed_required_memory_row_cannot_grant_or_settle() -> None:
    ledger = InMemoryConsentLedger()
    ledger._rows["native"] = _ConsentRow(
        id="native",
        run_id="run",
        tool_name="place",
        args={},
        call_ids=(),
        native_review_required=True,
        native_binding=None,
        status="granted",
        decided_by="reviewer",
        decided_at=datetime.now(UTC),
    )
    assert await ledger.verdict("native") is None
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide("native", approved=True, decided_by="reviewer")


@pytest.mark.asyncio
async def test_legacy_cannot_acquire_native_binding_through_a_decision() -> None:
    ledger = InMemoryConsentLedger()
    ledger._rows["legacy"] = _ConsentRow(id="legacy", run_id="run", tool_name="legacy", args={}, call_ids=())
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide("legacy", approved=True, decided_by="reviewer", expected_native_binding=binding())
    assert await ledger.verdict("legacy") is None
    first = await ledger.decide("legacy", approved=True, decided_by="reviewer")
    assert await ledger.decide("legacy", approved=False, decided_by="other") == first


@pytest.mark.asyncio
async def test_service_stages_complete_binding_without_taking_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.bind = SimpleNamespace(dialect=postgresql.dialect())
    service = ConsentService(session=session)
    retained: list[tuple[Consent, bool]] = []

    async def create(row: Consent, *, auto_commit: bool) -> Consent:
        retained.append((row, auto_commit))
        return row

    monkeypatch.setattr(service, "create", create)
    value = binding()
    row = await service.request(
        run_id=str(UUID(int=2)),
        tool_name="place",
        tool_call_id="one",
        call_ids=("one",),
        payload={"opaque": "secret"},
        preauth=None,
        native_binding=value,
        auto_commit=False,
    )
    assert retained == [(row, False)]
    assert row.native_review_required
    assert row.native_binding == value.document()
    assert row_to_view(row).native_binding == value
    session.commit.assert_not_awaited()
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
async def test_service_decision_fences_full_binding_in_pending_update(
    *, native: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.bind = SimpleNamespace(dialect=postgresql.dialect())
    service = ConsentService(session=session)
    value = binding() if native else None
    row = Consent(
        id=UUID(int=1),
        run_id=UUID(int=2),
        tool_name="place",
        status="denied",
        decided_by="first",
        decided_at=datetime.now(UTC),
        native_review_required=native,
        native_binding=value.document() if value else None,
    )
    monkeypatch.setattr(service, "get_one_or_none", AsyncMock(return_value=row))
    result = await service.grant(str(row.id), decided_by="second", expected_native_binding=value)
    assert result is not None
    assert result.status == "denied"
    assert result.decided_by == "first"
    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    update_clause, where_clause = sql.split(" WHERE ", 1)
    assert "native_binding" not in update_clause
    assert "native_review_required" not in update_clause
    assert "consent.status =" in where_clause
    assert f"consent.native_review_required IS {'true' if native else 'false'}" in where_clause
    if value:
        assert "consent.native_binding =" in where_clause
        assert value.document() in compiled.params.values()
        assert "consent.native_binding ->>" in where_clause
        assert "schema_version" in compiled.params.values()
        assert "1" in compiled.params.values()
    else:
        assert "consent.native_binding IS NULL" in where_clause


def test_legacy_binding_uses_sql_null_and_migration_keeps_refusal_inside_lock() -> None:
    column = Consent.__table__.c.native_binding
    dialect = postgresql.asyncpg.dialect()
    processor = column.type.dialect_impl(dialect).bind_processor(dialect)
    assert processor is not None
    assert processor(None) is None
    assert processor(postgresql.JSONB.NULL) == "null"
    document = binding().document()
    serialized = processor(document)
    assert isinstance(serialized, str)
    assert json.loads(serialized) == document
    migration = importlib.import_module("lychd.db.migrations.versions.0010_native_consent_binding")
    assert (migration.revision, migration.down_revision) == ("0010", "0009")
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "DEFAULT false NOT NULL" in sql
    assert "jsonb_typeof(native_binding) = 'object'" in sql
    assert sql.index("LOCK TABLE consent IN ACCESS EXCLUSIVE MODE") < sql.index("IF EXISTS") < sql.index("DROP COLUMN")
    assert "WHERE native_review_required OR native_binding IS NOT NULL" in sql
    assert "COMMIT" not in sql
    assert "DELETE FROM" not in sql


@pytest.mark.asyncio
async def test_false_requirement_with_bound_memory_row_cannot_grant() -> None:
    ledger = InMemoryConsentLedger()
    ledger._rows["inconsistent"] = _ConsentRow(
        id="inconsistent",
        run_id="run",
        tool_name="place",
        args={},
        call_ids=(),
        native_review_required=False,
        native_binding=binding(),
        status="granted",
        decided_by="first",
        decided_at=datetime.now(UTC),
    )
    view = await ledger.get("inconsistent")
    assert view is not None
    assert view.native_review_required
    assert view.native_binding is None
    assert await ledger.verdict("inconsistent") is None
    with pytest.raises(ConsentBindingConflict):
        await ledger.decide("inconsistent", approved=True, decided_by="second", expected_native_binding=binding())
