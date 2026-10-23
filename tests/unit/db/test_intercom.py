"""Closed in-process custody oracles; actual PostgreSQL proof belongs to integration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.intercom import (
    NETWORK_ALLOWANCE,
    IntercomStore,
    IntercomStoreError,
    _canonical,  # pyright: ignore[reportPrivateUsage]
    _digest,  # pyright: ignore[reportPrivateUsage]
    _key,  # pyright: ignore[reportPrivateUsage]
    _record,  # pyright: ignore[reportPrivateUsage]
    task_snapshot,
)
from lychd.db.models.intercom import (
    IntercomCapacity,
    IntercomCredential,
    IntercomOutbox,
    IntercomPeer,
    IntercomTask,
    IntercomTransmission,
)


def _rows() -> tuple[IntercomPeer, IntercomCredential, IntercomTask, IntercomOutbox]:
    peer_id, task_id = uuid4(), uuid4()
    pem = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEArwaj4ykXFOTzVsGcmxXNGVHsbmZiqne+B1R/KJODNB0=\n-----END PUBLIC KEY-----\n"
    key = {"key_id": "fixture-key", "public_key_pem": pem}
    enrollment = {"key": key, "policy": {"generation": 1}}
    peer = IntercomPeer(
        id=peer_id,
        enrollment=enrollment,
        enrollment_digest=_digest(_canonical(enrollment)),
        key_version=1,
        policy_generation=1,
        revocation_generation=0,
        revoked=False,
        policy=enrollment["policy"],
    )
    raw_pem, digest = _key(key)
    credential = IntercomCredential(
        id=uuid4(),
        peer_id=peer_id,
        version=1,
        key_id=key["key_id"],
        public_key_pem=raw_pem,
        public_key_digest=digest,
        record=key,
        record_digest=_digest(_canonical(key)),
    )
    declaration_id, operation_id = uuid4(), uuid4()
    expiry = datetime.now(UTC) + timedelta(minutes=5)
    record = {
        "peer_id": str(peer_id),
        "declaration_id": str(declaration_id),
        "operation_id": str(operation_id),
        "purpose": "public-task",
        "task_schema": "example.public-text@1",
        "body": "{}",
        "expires_at": expiry.isoformat(),
        "policy_generation": 1,
        "key_version": 1,
        "revocation_generation": 0,
    }
    task = IntercomTask(
        id=task_id,
        peer_id=peer_id,
        declaration_id=declaration_id,
        operation_id=operation_id,
        purpose=record["purpose"],
        task_schema=record["task_schema"],
        expires_at=expiry,
        policy_generation=1,
        key_version=1,
        revocation_generation=0,
        record=record,
        record_digest=_digest(_canonical(record)),
        local_status="prepared",
        foreign_task_id=None,
        foreign_status=None,
        terminal_record=None,
    )
    outbox = IntercomOutbox(id=uuid4(), task_id=task_id, body=b"{}", body_digest=_digest(b"{}"), submit_claimed=False)
    return peer, credential, task, outbox


def _capacities() -> list[IntercomCapacity]:
    return [
        IntercomCapacity(
            id=uuid4(),
            scope=scope,
            scope_id=scope,
            uses_limit=10,
            application_limit=100_000,
            network_limit=NETWORK_ALLOWANCE * 10,
            uses_charged=0,
            application_charged=0,
            network_charged=0,
        )
        for scope in ("host", "purpose", "peer", "task")
    ]


def _limits() -> dict[str, Any]:
    return {
        scope: {"uses": 10, "application_bytes": 100_000, "network_bytes": NETWORK_ALLOWANCE * 10}
        for scope in ("host", "purpose", "peer", "task")
    }


def _claim() -> dict[str, Any]:
    return {
        "method": "SendMessage",
        "application_bytes": 200,
        "network_bytes": NETWORK_ALLOWANCE,
        "wire_digest": "a" * 64,
        "policy_generation": 1,
        "key_version": 1,
        "revocation_generation": 0,
    }


def _store(rows: Sequence[object], *, previous: IntercomTransmission | None = None) -> tuple[IntercomStore, MagicMock]:
    session = MagicMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    session.scalar = AsyncMock(side_effect=rows)
    session.get = AsyncMock(return_value=previous)
    factory = cast("async_sessionmaker[AsyncSession]", lambda: session)
    return IntercomStore(factory), session


@pytest.mark.asyncio
async def test_claim_commits_full_nonrefundable_capacity_before_return() -> None:
    peer, key, task, outbox = _rows()
    capacities = _capacities()
    store, session = _store([task, *capacities, peer, key, task, outbox])
    result = await store.claim(task.id, uuid4(), _claim(), _limits())
    session.commit.assert_awaited_once()
    assert result["task"]["submit_claimed"] is True
    assert result["task"]["status"] == "submitting"
    assert [(row.uses_charged, row.application_charged, row.network_charged) for row in capacities] == [
        (1, 200, NETWORK_ALLOWANCE)
    ] * 4
    assert not hasattr(store, "activate")


@pytest.mark.asyncio
async def test_capacity_locks_use_fixed_order_and_stable_task_family_identity() -> None:
    _, _, task, _ = _rows()
    capacities = _capacities()
    store, session = _store(capacities)
    await store._capacities(cast("AsyncSession", session), task, _limits())  # pyright: ignore[reportPrivateUsage]
    scopes: list[str] = []
    identifiers: list[str] = []
    for call in session.execute.call_args_list:
        compiled = call.args[0].compile(dialect=postgresql.dialect())
        scopes.append(compiled.params["scope"])
        identifiers.append(compiled.params["scope_id"])
    assert scopes == ["host", "purpose", "peer", "task"]
    assert identifiers == [
        "host",
        task.purpose,
        str(task.peer_id),
        _digest(f"{task.peer_id}\n{task.task_schema}".encode()),
    ]
    assert str(task.id) not in identifiers
    assert all(
        "FOR UPDATE" in str(call.args[0].compile(dialect=postgresql.dialect()))
        for call in session.scalar.call_args_list
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("same_attempt", [False, True])
async def test_submit_cannot_be_claimed_again_even_after_unknown(*, same_attempt: bool) -> None:
    peer, key, task, outbox = _rows()
    outbox.submit_claimed = True
    task.local_status = "unknown"
    attempt_id = uuid4()
    record = _claim()
    previous = (
        IntercomTransmission(id=attempt_id, task_id=task.id, record=record, record_digest=_digest(_canonical(record)))
        if same_attempt
        else None
    )
    store, session = _store([task, *_capacities(), peer, key, task, outbox], previous=previous)
    with pytest.raises(IntercomStoreError, match="claimed"):
        await store.claim(task.id, attempt_id, record, _limits())
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_uncertainty_returns_no_claim_or_private_driver_diagnostic() -> None:
    peer, key, task, outbox = _rows()
    store, session = _store([task, *_capacities(), peer, key, task, outbox])
    session.commit.side_effect = RuntimeError("PRIVATE-DRIVER-CONTENT")
    with pytest.raises(IntercomStoreError, match="commit-unknown") as caught:
        await store.claim(task.id, uuid4(), _claim(), _limits())
    assert "PRIVATE" not in str(caught.value)
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_requires_known_foreign_id_and_new_physical_charge() -> None:
    peer, key, task, outbox = _rows()
    record = {**_claim(), "method": "GetTask"}
    store, session = _store([task, *_capacities(), peer, key, task, outbox])
    with pytest.raises(IntercomStoreError, match="missing-foreign-task"):
        await store.claim(task.id, uuid4(), record, _limits())
    session.commit.assert_not_awaited()
    task.foreign_task_id = "remote-task"
    outbox.submit_claimed = True
    capacities = _capacities()
    store, session = _store([task, *capacities, peer, key, task, outbox])
    await store.claim(task.id, uuid4(), record, _limits())
    session.commit.assert_awaited_once()
    assert capacities[0].network_charged == NETWORK_ALLOWANCE


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["revoked", "policy", "expired", "capacity"])
async def test_current_authority_expiry_and_permanent_ceiling_refuse(change: str) -> None:
    peer, key, task, outbox = _rows()
    capacities = _capacities()
    if change == "revoked":
        peer.revoked = True
    elif change == "policy":
        peer.policy_generation = 2
    elif change == "expired":
        task.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        task.record["expires_at"] = task.expires_at.isoformat()
        task.record_digest = _digest(_canonical(task.record))
    else:
        capacities[0].uses_charged = capacities[0].uses_limit
    store, session = _store([task, *capacities, peer, key, task, outbox])
    with pytest.raises(IntercomStoreError):
        await store.claim(task.id, uuid4(), _claim(), _limits())
    session.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "field", ["body_digest", "body", "task_id", "record_digest", "peer_id", "purpose", "key_version"]
)
def test_changed_content_or_critical_column_binding_cannot_be_read(field: str) -> None:
    _, _, task, outbox = _rows()
    owner = outbox if field in {"body_digest", "body", "task_id"} else task
    setattr(owner, field, b"other" if field == "body" else "bad")
    with pytest.raises(IntercomStoreError, match="conflict"):
        task_snapshot(task, outbox)


@pytest.mark.parametrize("key", ["private_key", "private_key_pem", "password", "secret", "run_id"])
def test_no_private_credential_or_fabricated_run_can_be_retained(key: str) -> None:
    with pytest.raises(IntercomStoreError, match="record"):
        _record({"nested": [{key: "SYNTHETIC-PRIVATE"}]})


@pytest.mark.asyncio
async def test_terminal_is_first_wins_and_late_poll_cannot_reopen() -> None:
    peer, _, task, outbox = _rows()
    first = {
        "status": "received",
        "response_nonce": "first-terminal-nonce",
        "terminal": True,
        "result": {"text": "first"},
        "context_id": "remote-context",
    }
    task.local_status, task.terminal_record = "terminal", first
    attempt_id = uuid4()
    record = {**_claim(), "method": "GetTask"}
    transmission = IntercomTransmission(
        id=attempt_id,
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=None,
    )
    store, session = _store([task, peer, task, outbox, None], previous=transmission)
    result = await store.settle(
        task.id,
        attempt_id,
        {"status": "received", "response_nonce": "late-terminal-nonce", "terminal": True, "result": {"text": "late"}},
    )
    assert result["result"] == {"text": "first"}
    assert result["context_id"] == "remote-context"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_changed_settlement_identity_refuses_without_new_commit() -> None:
    peer, _, task, outbox = _rows()
    record = _claim()
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement={"status": "unknown"},
    )
    store, session = _store([task, peer, task, outbox], previous=transmission)
    with pytest.raises(IntercomStoreError, match="conflict"):
        await store.settle(task.id, transmission.id, {"status": "refused"})
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_plain_read_returns_evidence_without_activating_or_committing() -> None:
    _, _, task, outbox = _rows()
    store, session = _store([task, outbox])
    result = await store.task(task.id)
    assert result["body"] == b"{}"
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_peer_restricted_task_query_checks_owner_before_reading_body() -> None:
    _, _, task, _ = _rows()
    store, session = _store([None])
    with pytest.raises(IntercomStoreError, match="missing"):
        await store.task(task.id, peer_id=uuid4())
    assert session.scalar.await_count == 1
    compiled = session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "intercom_task.peer_id =" in str(compiled)
    session.add.assert_not_called()


def test_public_key_fingerprint_is_stable_across_pem_whitespace() -> None:
    _, key, _, _ = _rows()
    alternate = {**key.record, "public_key_pem": key.record["public_key_pem"].replace("\n", "\r\n")}
    assert _key(alternate)[1] == key.public_key_digest


@pytest.mark.asyncio
async def test_rotation_preserves_policy_generation_and_retired_key_cannot_return() -> None:
    peer, key, _, _ = _rows()
    peer.key_version = 2
    current = IntercomCredential(
        id=uuid4(),
        peer_id=peer.id,
        version=2,
        key_id=key.key_id,
        public_key_pem=key.public_key_pem,
        public_key_digest=key.public_key_digest,
        record=key.record,
        record_digest=key.record_digest,
    )
    store, session = _store([peer, current, key])
    with pytest.raises(IntercomStoreError, match="revoked"):
        await store.rotate(peer.id, key.record)
    assert peer.key_version == 2
    assert peer.policy_generation == 1
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_policy_generation_jumps_forward_and_never_backwards() -> None:
    peer, key, _, _ = _rows()
    store, session = _store([peer, key])
    result = await store.set_policy(peer.id, {"generation": 5}, expected_generation=1)
    assert result["policy_generation"] == 5
    assert result["policy"] == {"generation": 5}
    session.commit.assert_awaited_once()
    store, session = _store([peer])
    with pytest.raises(IntercomStoreError, match="policy"):
        await store.set_policy(peer.id, {"generation": 1}, expected_generation=5)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_local_cancel_is_durable_and_authenticated_late_completion_cannot_adopt() -> None:
    peer, key, task, outbox = _rows()
    task.foreign_task_id = "remote-task"
    outbox.submit_claimed = True
    store, session = _store([task, peer, task, outbox])
    result = await store.close_task(task.id, peer_id=peer.id)
    assert result["status"] == "cancelled"
    session.commit.assert_awaited_once()
    record = {**_claim(), "method": "CancelTask"}
    store, session = _store([task, *_capacities(), peer, key, task, outbox])
    await store.claim(task.id, uuid4(), record, _limits())
    session.commit.assert_awaited_once()
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=None,
    )
    store, session = _store([task, peer, task, outbox, None], previous=transmission)
    result = await store.settle(
        task.id,
        transmission.id,
        {
            "status": "received",
            "foreign_task_id": "remote-task",
            "foreign_status": "completed",
            "response_nonce": "late-after-cancel-nonce",
            "terminal": True,
            "result": {"text": "too-late"},
        },
    )
    assert result["status"] == "cancelled"
    assert result["result"] is None
    assert result["cancellation_observation"]["foreign_status"] == "completed"
    assert "result" not in result["cancellation_observation"]


@pytest.mark.asyncio
async def test_response_nonce_replay_is_peer_scoped_atomic_and_never_settles() -> None:
    peer, _, task, outbox = _rows()
    record = _claim()
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=None,
    )
    store, session = _store([task, peer, task, outbox, uuid4()], previous=transmission)
    with pytest.raises(IntercomStoreError, match="replay"):
        await store.settle(task.id, transmission.id, {"status": "received", "response_nonce": "same-nonce"})
    assert transmission.settlement is None
    session.commit.assert_not_awaited()
    statement = session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "intercom_task.peer_id =" in str(statement)
    assert str(peer.id) in [str(value) for value in statement.params.values()]


@pytest.mark.asyncio
@pytest.mark.parametrize("nonce", [None, "", "has space", "control\n", "nonascii-ž"])
async def test_received_settlement_requires_bounded_visible_response_nonce(nonce: object) -> None:
    store, session = _store([])
    record = {"status": "received"} if nonce is None else {"status": "received", "response_nonce": nonce}
    with pytest.raises(IntercomStoreError, match="record"):
        await store.settle(uuid4(), uuid4(), record)
    session.scalar.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_exact_received_settlement_replay_is_idempotent_without_reusing_nonce_check() -> None:
    peer, _, task, outbox = _rows()
    record = _claim()
    settled = {"status": "received", "response_nonce": "retained-nonce", "terminal": False}
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=settled,
    )
    store, session = _store([task, peer, task, outbox], previous=transmission)
    result = await store.settle(task.id, transmission.id, settled)
    assert result["task_id"] == str(task.id)
    assert session.scalar.await_count == 4
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_result_fence_runs_after_queries_before_any_adoption_mutation() -> None:
    peer, _, task, outbox = _rows()
    record = _claim()
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=None,
    )
    store, session = _store([task, peer, task, outbox, None], previous=transmission)

    def stale() -> None:
        assert session.scalar.await_count == 5
        assert transmission.settlement is None
        code = "policy"
        raise IntercomStoreError(code)

    with pytest.raises(IntercomStoreError, match="policy"):
        await store.settle(
            task.id, transmission.id, {"status": "received", "response_nonce": "fresh-live-nonce"}, current=stale
        )
    assert transmission.settlement is None
    assert task.local_status == "prepared"
    session.commit.assert_not_awaited()


def _native_rows() -> tuple[Any, Any, Any, IntercomPeer, IntercomCredential, IntercomTask, IntercomOutbox]:
    from lychd.db.intercom import _native_binding  # pyright: ignore[reportPrivateUsage]
    from lychd.db.models.run import Run
    from lychd.db.models.run_delivery import RunDelivery
    from lychd.domain.intercom.native import PeerRunBinding, PeerTaskRef

    peer, key, task, outbox = _rows()
    binding = PeerRunBinding(
        request_id=uuid4(),
        declaration_id=task.declaration_id,
        operation_id=task.operation_id,
        peer_id=peer.id,
        purpose=task.purpose,
        task_schema=task.task_schema,
        endpoint="https://peer.example:443/a2a",
        source_digest="a" * 64,
        text_digest="b" * 64,
        expires_at=task.expires_at,
    )
    ref = PeerTaskRef(
        task_id=task.id,
        run_id=str(uuid4()),
        station="peer_wait",
        request_id=binding.request_id,
        binding_digest=binding.digest,
    )
    manifest = {
        "schema_version": 2,
        "key": "native_public_peer",
        "revision": "1",
        "implementation_revision": "1",
        "checkpoint_schema": "1",
        "entry_node": "peer_wait",
        "nodes": [{"key": "peer_wait", "label": "Peer wait", "kind": "peer"}],
        "edges": [],
    }
    manifest["digest"] = _digest(_canonical(manifest))
    run = Run(
        id=UUID(ref.run_id),
        workflow_name="native_public_peer",
        status="running",
        enqueue_seq=0,
        pattern_manifest=manifest,
        intent={"admitted_peer": binding.model_dump(mode="json")},
    )
    delivery = RunDelivery(run_id=run.id, enqueue_seq=0, state="claimed")
    task.record = {
        **task.record,
        "endpoint": binding.endpoint,
        "category": "public-task",
        "source_digest": binding.source_digest,
        "text_digest": binding.text_digest,
    }
    task.record_digest = _digest(_canonical(task.record))
    native = _native_binding(
        run,
        delivery,
        ref,
        task.record,
        pattern_digest=manifest["digest"],
        enqueue_seq=0,
        step_id=str(uuid4()),
        occurrence_id=str(uuid4()),
    )
    for field, value in native.items():
        setattr(task, field, value)
    task.adoption_closed = False
    task.native_reauthorizations = []
    return run, delivery, ref, peer, key, task, outbox


def test_native_metadata_retains_seven_tables_and_typed_restrict_owner() -> None:
    from sqlalchemy import CheckConstraint, Table, UniqueConstraint

    table = cast("Table", IntercomTask.__table__)
    assert len([name for name in table.metadata.tables if name.startswith("intercom_")]) == 7
    assert next(iter(table.c.native_run_id.foreign_keys)).ondelete == "RESTRICT"
    native_foreign_keys = list(table.c.native_run_id.foreign_keys)
    assert native_foreign_keys
    assert any(
        isinstance(item, UniqueConstraint)
        and tuple(column.name for column in item.columns) == ("native_run_id", "native_station", "native_request_id")
        for item in table.constraints
    )
    assert any(
        isinstance(item, CheckConstraint) and "native_occurrence_id IS NOT NULL" in str(item.sqltext)
        for item in table.constraints
    )
    assert table.c.adoption_closed.nullable is False
    assert table.c.native_reauthorizations.nullable is False


@pytest.mark.parametrize(
    "change", ["request", "binding", "pattern", "station", "claim", "sequence", "workflow", "source"]
)
def test_native_preparation_refuses_substituted_provenance(change: str) -> None:
    from lychd.db.intercom import _native_binding  # pyright: ignore[reportPrivateUsage]

    run, delivery, ref, _, _, task, _ = _native_rows()
    if change == "request":
        ref = ref.model_copy(update={"request_id": uuid4()})
    elif change == "binding":
        ref = ref.model_copy(update={"binding_digest": "c" * 64})
    elif change == "pattern":
        run.pattern_manifest = {**run.pattern_manifest, "digest": "c" * 64}
    elif change == "station":
        ref = ref.model_copy(update={"station": "different"})
    elif change == "claim":
        delivery.state = "settled"
    elif change == "sequence":
        run.enqueue_seq = 1
    elif change == "workflow":
        run.workflow_name = "other"
    else:
        task.record = {**task.record, "source_digest": "c" * 64}
    with pytest.raises(IntercomStoreError, match="native-binding"):
        _native_binding(
            run,
            delivery,
            ref,
            task.record,
            pattern_digest=cast("str", task.native_pattern_digest),
            enqueue_seq=0,
            step_id=cast("str", task.native_step_id),
            occurrence_id=cast("str", task.native_occurrence_id),
        )


@pytest.mark.asyncio
async def test_native_create_locks_real_run_and_claim_before_peer_then_preserves_provenance() -> None:
    from lychd.db.models.intercom import IntercomDeclaration

    run, delivery, ref, peer, key, task, outbox = _native_rows()
    declaration = IntercomDeclaration(
        id=task.declaration_id,
        peer_id=peer.id,
        operation_id=task.operation_id,
        policy_generation=1,
        record=task.record,
        record_digest=task.record_digest,
    )
    store, session = _store([run, delivery, None, peer, key, task.id, task, outbox])
    session.get.return_value = declaration
    result = await store.create_native_task(
        task.id,
        task.record,
        ref=ref,
        pattern_digest=cast("str", task.native_pattern_digest),
        enqueue_seq=0,
        step_id=cast("str", task.native_step_id),
        occurrence_id=cast("str", task.native_occurrence_id),
    )
    statements = [str(call.args[0].compile(dialect=postgresql.dialect())) for call in session.scalar.call_args_list]
    assert "FROM run " in statements[0]
    assert "FOR UPDATE" in statements[0]
    assert "FROM run_delivery " in statements[1]
    assert "FOR UPDATE" in statements[1]
    assert "FOR UPDATE" not in statements[2]
    assert result["native_run_id"] == str(run.id)
    assert result["native_binding_digest"] == ref.binding_digest
    assert result["native_step_id"] == task.native_step_id
    assert result["adoption_closed"] is False
    session.commit.assert_awaited_once()
    values = session.scalar.call_args_list[5].args[0].compile(dialect=postgresql.dialect()).params
    assert values["native_run_id"] == run.id
    assert values["native_request_id"] == ref.request_id


@pytest.mark.asyncio
async def test_native_close_sweeps_prepark_and_terminal_and_preserves_first_terminal() -> None:
    run, _, _, _, _, first, first_outbox = _native_rows()
    _, _, _, _, _, terminal, terminal_outbox = _native_rows()
    terminal.native_run_id = run.id
    terminal.local_status = "terminal"
    terminal.terminal_record = {"status": "received", "terminal": True, "result": {"text": "first"}}
    store, session = _store([run, first_outbox, terminal_outbox])
    rows = MagicMock()
    rows.all.return_value = [first, terminal]
    session.scalars = AsyncMock(return_value=rows)
    snapshots = await store.close_native_run(str(run.id))
    assert all(snapshot["adoption_closed"] for snapshot in snapshots)
    assert first.local_status == "cancelled"
    assert terminal.local_status == "terminal"
    assert terminal.terminal_record is not None
    assert cast("dict[str, Any]", terminal.terminal_record)["result"] == {"text": "first"}
    assert terminal.closure_reason == "cancelled"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_first", [False, True])
async def test_native_late_observation_is_retained_without_reopening_closed_adoption(*, terminal_first: bool) -> None:
    _, _, _, peer, _, task, outbox = _native_rows()
    task.adoption_closed = True
    task.closure_reason = "cancelled"
    task.local_status = "terminal" if terminal_first else "cancelled"
    original = {"status": "received", "terminal": True, "result": {"text": "first"}}
    task.terminal_record = original if terminal_first else None
    record = _claim()
    transmission = IntercomTransmission(
        id=uuid4(),
        task_id=task.id,
        record=record,
        record_digest=_digest(_canonical(record)),
        network_bytes=NETWORK_ALLOWANCE,
        settlement=None,
    )
    store, session = _store([task, peer, task, outbox, None], previous=transmission)
    result = await store.settle(
        task.id,
        transmission.id,
        {
            "status": "received",
            "terminal": True,
            "response_nonce": "late-native-response",
            "foreign_task_id": "newly-observed-remote",
            "foreign_status": "TASK_STATE_COMPLETED",
            "result": {"text": "late"},
        },
    )
    assert result["adoption_closed"] is True
    assert result["foreign_task_id"] == "newly-observed-remote"
    assert result["foreign_status"] == "TASK_STATE_COMPLETED"
    assert task.local_status == ("terminal" if terminal_first else "cancelled")
    if terminal_first:
        assert task.terminal_record == original
    else:
        assert result["result"] is None
        assert result["cancellation_observation"]["foreign_task_id"] == "newly-observed-remote"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_native_authorization_history_refuses_overflow_and_never_truncates() -> None:
    run, _, _, _, _, task, _ = _native_rows()
    record = {
        "subject": "local-operator",
        "authentication_generation": str(uuid4()),
        "actions": ["read", "resume"],
        "reaffirm_public_source": False,
        "authorized_at": datetime.now(UTC).isoformat(),
        "binding_digest": task.native_binding_digest,
    }
    task.native_reauthorizations = [record] * 64
    store, session = _store([run, task])
    with pytest.raises(IntercomStoreError, match="authorization-capacity"):
        await store.record_native_authorization(str(run.id), task.id, record, current=lambda: None)
    assert len(task.native_reauthorizations) == 64
    session.commit.assert_not_awaited()


@pytest.mark.parametrize("field", ["native_run_id", "native_station", "native_binding_digest", "adoption_closed"])
def test_arbitrary_record_cannot_invent_typed_native_authority(field: str) -> None:
    with pytest.raises(IntercomStoreError, match="record"):
        _record({"nested": {field: "invented"}})


def test_task_snapshot_detaches_terminal_result_and_native_authorization_history() -> None:
    _, _, _, _, _, task, outbox = _native_rows()
    task.local_status = "terminal"
    task.terminal_record = {"status": "received", "terminal": True, "result": {"text": ["original"]}}
    task.native_reauthorizations = [{"actions": ["read"]}]
    snapshot = task_snapshot(task, outbox)
    snapshot["result"]["text"].append("caller mutation")
    snapshot["native_reauthorizations"][0]["actions"].append("submit")
    assert task.terminal_record == {"status": "received", "terminal": True, "result": {"text": ["original"]}}
    assert task.native_reauthorizations == [{"actions": ["read"]}]


def _transmission(task_id: UUID, *, terminal: bool = True) -> IntercomTransmission:
    claim = _claim()
    settlement = {
        "status": "received",
        "response_nonce": "canonical-terminal-nonce",
        "response_digest": "c" * 64,
        "foreign_task_id": "known-remote",
        "foreign_status": "TASK_STATE_COMPLETED",
        "terminal": terminal,
        "result": {"text": ["attributed public response"], "origin": "authenticated-foreign-data"},
    }
    return IntercomTransmission(
        id=uuid4(),
        task_id=task_id,
        **{
            field: claim[field]
            for field in (
                "method",
                "policy_generation",
                "key_version",
                "revocation_generation",
                "application_bytes",
                "network_bytes",
            )
        },
        record=claim,
        record_digest=_digest(_canonical(claim)),
        status="received",
        accepted_network_bytes=0,
        settlement=settlement,
    )


@pytest.mark.parametrize("field", ["method", "policy_generation", "key_version", "application_bytes", "network_bytes"])
def test_transmission_snapshot_refuses_mutated_typed_claim(field: str) -> None:
    from lychd.db.intercom import transmission_snapshot

    transmission = _transmission(uuid4())
    setattr(transmission, field, "GetTask" if field == "method" else 999)
    with pytest.raises(IntercomStoreError, match="conflict"):
        transmission_snapshot(transmission)


@pytest.mark.asyncio
async def test_native_terminal_evidence_requires_actual_same_task_exact_received_transmission() -> None:
    _, _, _, _, _, task, outbox = _native_rows()
    transmission = _transmission(task.id)
    task.local_status = "terminal"
    task.foreign_task_id = "known-remote"
    task.foreign_status = "TASK_STATE_COMPLETED"
    task.terminal_record = transmission.settlement
    outbox.submit_claimed = True
    store, session = _store([task, outbox, transmission])
    result = await store.terminal_transmission(task.id)
    assert result is not None
    assert result["task_id"] == str(task.id)
    assert result["settlement"] == task.terminal_record
    assert result["record"] == transmission.record
    query = session.scalar.call_args_list[2].args[0].compile(dialect=postgresql.dialect())
    assert "intercom_transmission.task_id =" in str(query)
    assert "intercom_transmission.settlement =" in str(query)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_terminal_shape_without_received_transmission_supplies_no_evidence() -> None:
    _, _, _, _, _, task, outbox = _native_rows()
    task.local_status = "terminal"
    task.terminal_record = _transmission(task.id).settlement
    store, session = _store([task, outbox, None])
    assert await store.terminal_transmission(task.id) is None
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_authorization_terminal_open_is_append_only_and_current_after_flush() -> None:
    run, _, _, _, _, task, _ = _native_rows()
    task.local_status = "terminal"
    record = {
        "subject": "local-operator",
        "authentication_generation": str(uuid4()),
        "actions": ["read", "resume"],
        "reaffirm_public_source": False,
        "authorized_at": datetime.now(UTC).isoformat(),
        "binding_digest": task.native_binding_digest,
    }
    store, session = _store([run, task])
    checks = 0

    def current() -> None:
        nonlocal checks
        checks += 1

    await store.record_native_authorization(str(run.id), task.id, record, current=current)
    assert task.native_reauthorizations == [record]
    assert checks == 2
    session.commit.assert_awaited_once()
    assert task.record.get("native_reauthorizations") is None
