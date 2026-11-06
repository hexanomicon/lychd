"""Named Archive Runs retain exact historical receipt inspection."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lychd.agents.workflows import BRIDGE_CHAT_ARCHIVE, builtin_workflow_registry, resolve_named_workflow
from lychd.domain.archive.contracts import digest
from lychd.domain.naming import NamingSnapshot
from tests.web.test_archive_metadata import admission_engine, client
from tests.web.test_archive_run_recall import preseed, retained_run

pytestmark = pytest.mark.asyncio


def names() -> NamingSnapshot:
    return NamingSnapshot(
        magus_name="Zenith Runeweaver",
        primus_name="Aster Shadowdancer",
        magus_origin="manual",
        primus_origin="self_chosen",
        revision=1,
    )


async def test_named_archive_receipt_survives_changed_default_and_current_names() -> None:
    engine = admission_engine(revision="1")
    engine.workflows = builtin_workflow_registry()
    # Read projection must never reload current accepted forms of address.
    engine.naming_lookup = AsyncMock(side_effect=AssertionError("Historical recall cannot reload naming."))
    run = retained_run()
    run.admitted_naming = names()
    run.pattern_manifest = resolve_named_workflow(engine.workflows, BRIDGE_CHAT_ARCHIVE).manifest.snapshot()
    receipt = preseed(run)
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    store.inspect_recall.return_value = receipt
    async with client(store, ledger=ledger, engine=engine) as http:
        first = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
        second = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "recorded"
    assert first.json()["receipt"] == receipt.model_dump(mode="json")
    assert "PRIVATE_" not in first.text
    assert "Runeweaver" not in first.text
    assert "Shadowdancer" not in first.text
    engine.naming_lookup.assert_not_called()
    assert store.inspect_recall.await_count == 2


@pytest.mark.parametrize("invalid", ["unregistered", "changed_score", "missing_names", "names_on_legacy"])
async def test_named_archive_binding_refuses_mismatch_before_receipt_read(invalid: str) -> None:
    engine = admission_engine()
    registry = builtin_workflow_registry()
    run = retained_run()
    run.admitted_naming = names()
    run.pattern_manifest = resolve_named_workflow(registry, BRIDGE_CHAT_ARCHIVE).manifest.snapshot()
    if invalid != "unregistered":
        engine.workflows = registry
    if invalid == "changed_score":
        run.pattern_manifest["implementation_revision"] = "py.foreign"
        run.pattern_manifest["digest"] = digest(
            {key: value for key, value in run.pattern_manifest.items() if key != "digest"}
        )
    elif invalid == "missing_names":
        run.admitted_naming = None
    elif invalid == "names_on_legacy":
        run.pattern_manifest = BRIDGE_CHAT_ARCHIVE.manifest.snapshot()
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=engine) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == 409
    assert response.json()["extra"]["code"] == "run_recall_binding"
    assert store.mock_calls == []


async def test_unknown_naming_suffix_does_not_establish_archive_applicability() -> None:
    engine = admission_engine()
    engine.workflows = builtin_workflow_registry()
    run = retained_run()
    run.admitted_naming = names()
    run.pattern_manifest = resolve_named_workflow(engine.workflows, BRIDGE_CHAT_ARCHIVE).manifest.snapshot()
    run.pattern_manifest["revision"] = "3-naming2"
    run.pattern_manifest["digest"] = digest(
        {key: value for key, value in run.pattern_manifest.items() if key != "digest"}
    )
    ledger = AsyncMock()
    ledger.get.return_value = run
    store = AsyncMock()
    async with client(store, ledger=ledger, engine=engine) as http:
        response = await http.get(f"/api/v1/archive/runs/{run.run_id}/recall")
    assert response.status_code == 200
    assert response.json()["status"] == "not_applicable"
    assert store.mock_calls == []
