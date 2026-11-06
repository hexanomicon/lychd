"""Accepted forms of address are pinned once, independently of current naming."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.agents.workflows import resolve_pinned_workflow
from lychd.domain.cortex.ledger import DbRunLedger, _intent_payload
from lychd.domain.naming import NamingSnapshot
from tests.unit.domain.cortex.test_engine import _engine


def _names(revision: int = 1) -> NamingSnapshot:
    return NamingSnapshot(
        magus_name="Zenith Runeweaver",
        primus_name="Nadir Runeweaver" if revision == 1 else "Aster Shadowdancer",
        magus_origin="manual",
        primus_origin="self_chosen",
        revision=revision,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("initially_named", [False, True])
async def test_replay_and_reconstructed_state_keep_original_names(*, initially_named: bool) -> None:
    engine, ledger, _queues = _engine()
    current = _names() if initially_named else None
    lookups: list[str] = []

    async def lookup(owner: str) -> NamingSnapshot | None:
        lookups.append(owner)
        return current

    engine.naming_lookup = lookup
    intent = Intent(session_id="session", prompt="hello", sigil_name="authenticated-operator")
    handle = await engine.submit(intent, idempotency_key="naming-admission")
    record = await ledger.get(handle.run_id)
    assert record is not None
    expected = current
    assert record.admitted_naming == expected
    current = _names(2)
    replay = await engine.submit(intent, idempotency_key="naming-admission")
    assert replay.run_id == handle.run_id
    assert lookups == ["authenticated-operator"]
    retained = await ledger.get(handle.run_id)
    assert retained is not None
    restored = retained.to_intent()
    workflow = resolve_pinned_workflow(
        engine.workflows, workflow_name=retained.workflow_name, snapshot=retained.pattern_manifest
    )
    assert workflow is not None
    state = workflow.make_state(restored)
    assert state.model_dump().get("naming") == (expected.model_dump() if expected is not None else None)
    assert workflow.validate_state is not None
    workflow.validate_state(restored, state)
    substituted = state.model_copy(update={"naming": current})
    with pytest.raises(ValueError, match="checkpoint does not match"):
        workflow.validate_state(restored, substituted)
    later = await engine.submit(intent, idempotency_key="later-admission")
    later_record = await ledger.get(later.run_id)
    assert later_record is not None
    assert later_record.admitted_naming == current


@pytest.mark.asyncio
async def test_caller_cannot_supply_accepted_naming_metadata() -> None:
    engine, _ledger, queues = _engine()
    intent = Intent(session_id="session", prompt="hello", admitted_naming=_names())
    with pytest.raises(ValueError, match="server-owned admission metadata"):
        await engine.submit(intent)
    assert not queues["runs"].enqueued


@pytest.mark.asyncio
async def test_naming_read_failure_never_publishes_or_falls_back() -> None:
    engine, _ledger, queues = _engine()

    async def unavailable(_owner: str) -> NamingSnapshot | None:
        msg = "naming store unavailable"
        raise RuntimeError(msg)

    engine.naming_lookup = unavailable
    with pytest.raises(RuntimeError, match="naming store unavailable"):
        await engine.submit(Intent(session_id="session", prompt="hello"))
    assert not queues["runs"].enqueued


@pytest.mark.asyncio
@pytest.mark.parametrize("named", [False, True])
async def test_run_jsonb_reconstruction_preserves_naming_and_explicit_absence(*, named: bool) -> None:
    engine, ledger, _queues = _engine()
    names = _names() if named else None

    async def lookup(_owner: str) -> NamingSnapshot | None:
        return names

    engine.naming_lookup = lookup
    handle = await engine.submit(Intent(session_id="session", prompt="hello"))
    record = await ledger.get(handle.run_id)
    assert record is not None
    payload = _intent_payload(record.to_intent())
    assert "admitted_naming" in payload
    row_values = asdict(record)
    row_values.update(id=UUID(record.run_id), intent=payload)
    row = SimpleNamespace(**row_values)
    restored = DbRunLedger._to_record(row)
    assert restored.admitted_naming == names
    assert restored.to_intent().admitted_naming == names
    if names is None:
        del payload["admitted_naming"]
        assert DbRunLedger._to_record(row).admitted_naming is None
    else:
        payload["admitted_naming"] = {**names.model_dump(), "revision": 0}
        with pytest.raises(ValidationError):
            DbRunLedger._to_record(row)


@pytest.mark.asyncio
async def test_named_admission_requires_registered_execution_fence_before_publication() -> None:
    from lychd.agents.workflows import BRIDGE_CHAT, BuiltinWorkflowRegistry

    engine, _ledger, queues = _engine()
    engine.workflows = BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT,))

    async def lookup(_owner: str) -> NamingSnapshot:
        return _names()

    engine.naming_lookup = lookup
    with pytest.raises(ValueError, match="cannot execute retained Bridge naming"):
        await engine.submit(Intent(session_id="session", prompt="hello"))
    assert not queues["runs"].enqueued


@pytest.mark.asyncio
async def test_named_replay_retains_execution_fence_after_current_names_are_absent() -> None:
    engine, ledger, _queues = _engine()
    current: NamingSnapshot | None = _names()
    calls: list[str] = []

    async def lookup(owner: str) -> NamingSnapshot | None:
        calls.append(owner)
        return current

    engine.naming_lookup = lookup
    intent = Intent(session_id="session", prompt="hello")
    original = await engine.submit(intent, idempotency_key="named")
    current = None
    replay = await engine.submit(intent, idempotency_key="named")
    assert replay.run_id == original.run_id
    assert calls == ["magus"]
    retained = await ledger.get(replay.run_id)
    assert retained is not None
    assert retained.pattern_manifest["revision"] == "1-naming1"
    assert retained.admitted_naming == _names()
    later = await engine.submit(intent, idempotency_key="unnamed")
    later_record = await ledger.get(later.run_id)
    assert later_record is not None
    assert later_record.pattern_manifest["revision"] == "1"
    assert later_record.admitted_naming is None
