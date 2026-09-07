"""Persisted Bridge casting across offline queueing and consent reconstruction.

The existing recovery-image and inert runtime harnesses supply external effects.
Registry, Dispatcher, admission, worker, graph, and checkpoint decoding stay real.
No database server, container, endpoint, or model weights are exercised.
"""

# JSON/ORM adapter contracts and the shared recovery test harness are intentional
# private test probes, never an alternate application admission API.
# pyright: reportPrivateUsage=false
from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pydantic_ai.models
import pytest
from pydantic import ValidationError
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.bridge_chat import (
    BRIDGE_CHAT,
    BRIDGE_CHAT_BOUND,
    BRIDGE_CHAT_BOUND_GRAPH,
    BoundBridgeChatState,
    Converse,
)
from lychd.config.settings.weaver import BridgeCastingSettings, WeaverSettings
from lychd.db.models.run import Run
from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import CapabilitySpec
from lychd.domain.animation.connectors import ToolConnector
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.ledger import DbRunLedger, _intent_payload
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.ghouls.runs import perform_run
from tests.agents.fakes import FakeDispatcher
from tests.capability_workflows import (
    CapabilityScenario,
    InertModelConnector,
    InertRuntimeAdapter,
    build_capability_scenario,
)
from tests.integration.test_offline_recovery_workflow import _Boot, _boot

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pydantic_ai.toolsets import AbstractToolset


@pytest.fixture(autouse=True)
def no_model_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", False)


def _select(boot: _Boot, key: str | None) -> None:
    weaver = WeaverSettings(bridge=BridgeCastingSettings(revision="2", capability_key=key)) if key else None
    workflows = builtin_workflow_registry(weaver=weaver)
    boot.engine.workflows = workflows
    boot.engine.bridge_capability_key = key
    boot.substrate.workflows = workflows


def _attach_real_dispatcher(boot: _Boot) -> CapabilityScenario:
    """Reuse the inert runtime world with the recovery harness's model/tool surface."""
    fake = boot.substrate.dispatcher
    assert isinstance(fake, FakeDispatcher)

    class BoundConnector(InertModelConnector, ToolConnector):
        def get_model(self, *, model_id: str | None = None) -> Model:
            _ = model_id
            return fake.model

        def get_toolsets(self) -> Sequence[AbstractToolset[Any]]:
            return fake.toolsets

    build_specs = InertRuntimeAdapter.build_capability_specs

    def specs(adapter: InertRuntimeAdapter, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        return [spec.model_copy(update={"supports_tools": True}) for spec in build_specs(adapter, animator)]

    def build_runtime(adapter: InertRuntimeAdapter, stone: SoulstoneConfig) -> RuntimeAnimator:
        _ = adapter
        return SoulstoneAnimator(rune=stone, connector=BoundConnector())

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(InertRuntimeAdapter, "build_capability_specs", specs)
        patch.setattr(InertRuntimeAdapter, "build_runtime", build_runtime)
        scenario = build_capability_scenario(models={"a": ("shared",), "z": ("shared",)}, active={"a", "z"})
    boot.substrate.dispatcher = Dispatcher(scenario.registry, leases=scenario.leases, events=boot.bus)
    boot.substrate.leases = scenario.leases
    boot.substrate.context = ContextOrchestrator(registry=scenario.registry)
    return scenario


@pytest.mark.asyncio
@pytest.mark.parametrize("next_key", ["a:chat:shared", None], ids=["changed", "removed"])
async def test_queued_casting_and_idempotent_replay_survive_configuration_change(
    tmp_path: Path, next_key: str | None
) -> None:
    first = _boot(executed=[], model_rounds=[])
    _select(first, "z:chat:shared")
    session = await first.sessions.create_session()
    intent = Intent(session_id=session.id, prompt="Answer with the admitted model.")
    handle = await first.engine.submit(intent, idempotency_key="casting-original")
    image = tmp_path / "queued.json"
    await first.image(image, run_id=handle.run_id)

    restored = _boot(executed=[], model_rounds=[], image_path=image)
    _select(restored, next_key)
    fake = restored.substrate.dispatcher
    assert isinstance(fake, FakeDispatcher)
    fake.model = TestModel(custom_output_args={"answer": "bound answer", "fragments": []}, call_tools=[])
    scenario = _attach_real_dispatcher(restored)

    replay = await restored.engine.submit(intent, idempotency_key="casting-original")
    assert replay.run_id == handle.run_id
    assert replay.pattern_revision == "2"
    admitted = await restored.ledger.get(handle.run_id)
    assert admitted is not None
    assert admitted.admitted_capability_key == "z:chat:shared"
    assert admitted.pattern_manifest == BRIDGE_CHAT_BOUND.manifest.snapshot()
    assert admitted.to_intent().admitted_capability_key == "z:chat:shared"

    result = await perform_run({"run_substrate": restored.substrate}, run_id=handle.run_id, enqueue_seq=0)
    assert result["status"] == "done"
    assert scenario.world.probes == ["z", "z"]
    assert scenario.leases.active() == []
    events = await restored.ledger.list_events(handle.run_id)
    dispatches = [event.data for event in events if event.kind is RunEventKind.DISPATCH]
    assert dispatches == ["z:chat:shared"]

    fresh = await restored.engine.submit(intent, idempotency_key="casting-new")
    fresh_record = await restored.ledger.get(fresh.run_id)
    assert fresh_record is not None
    assert fresh_record.admitted_capability_key == next_key
    assert fresh.pattern_revision == ("2" if next_key else "1")


@pytest.mark.asyncio
async def test_caller_cannot_supply_the_server_owned_casting() -> None:
    boot = _boot(executed=[], model_rounds=[])
    _select(boot, "z:chat:shared")
    intent = Intent(session_id="caller", prompt="Answer", admitted_capability_key="a:chat:shared")
    with pytest.raises(ValueError, match="server-owned"):
        await boot.engine.submit(intent, idempotency_key="untrusted")
    assert await boot.ledger.get_nonterminal_for_session("caller") is None
    assert boot.queue.attempts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", [None, "checkpoint-key", "checkpoint-prompt", "run-metadata"])
async def test_consent_resume_reacquires_the_exact_binding_after_configuration_removal(
    tmp_path: Path, corruption: str | None
) -> None:
    executed: list[str] = []
    rounds: list[bool] = []
    first = _boot(executed=executed, model_rounds=rounds)
    _select(first, "z:chat:shared")
    initial_scenario = _attach_real_dispatcher(first)
    session = await first.sessions.create_session()
    handle = await first.engine.submit(Intent(session_id=session.id, prompt="Record the reviewed note."))
    await perform_run({"run_substrate": first.substrate}, run_id=handle.run_id, enqueue_seq=0)
    parked = await first.ledger.get(handle.run_id)
    assert parked is not None
    assert parked.status is RunStatus.AWAITING_CONSENT
    assert parked.consent_id is not None
    assert initial_scenario.world.probes == ["z", "z"]
    assert initial_scenario.leases.active() == []
    assert rounds == [False]
    assert executed == []
    document = await first.checkpoints.load(handle.run_id)
    assert document is not None
    assert all(snapshot["state"]["capability_key"] == "z:chat:shared" for snapshot in document)
    image = tmp_path / "consent.json"
    await first.image(image, run_id=handle.run_id)

    restored = _boot(executed=executed, model_rounds=rounds, image_path=image)
    _select(restored, None)
    resumed_scenario = _attach_real_dispatcher(restored)
    if corruption in {"checkpoint-key", "checkpoint-prompt"}:
        corrupted = await restored.checkpoints.load(handle.run_id)
        assert corrupted is not None
        for snapshot in corrupted:
            snapshot["state"].update(
                {"capability_key": "a:chat:shared"}
                if corruption == "checkpoint-key"
                else {"prompt": "Run a different request that was never admitted."}
            )
        await restored.checkpoints.replace(handle.run_id, corrupted)
    elif corruption == "run-metadata":
        restored.ledger._runs[handle.run_id] = replace(parked, admitted_capability_key=None)
    await restored.consents.decide(parked.consent_id, approved=True, decided_by="magus")
    await restored.engine.resume_consent(parked.consent_id)
    if corruption:
        with pytest.raises(ValueError, match="admitted Run"):
            await perform_run({"run_substrate": restored.substrate}, run_id=handle.run_id, enqueue_seq=1)
    else:
        result = await perform_run({"run_substrate": restored.substrate}, run_id=handle.run_id, enqueue_seq=1)
        assert result["status"] == "done"
    terminal = await restored.ledger.get(handle.run_id)
    assert terminal is not None
    assert terminal.status is (RunStatus.FAILED if corruption else RunStatus.DONE)
    assert resumed_scenario.world.probes == ([] if corruption else ["z", "z"])
    assert resumed_scenario.leases.active() == []
    assert executed == ([] if corruption else ["reviewed"])
    assert rounds == ([False] if corruption else [False, True])
    assert not await restored.checkpoints.exists(handle.run_id)
    events = await restored.ledger.list_events(handle.run_id)
    dispatches = [event.data for event in events if event.kind is RunEventKind.DISPATCH]
    assert dispatches == (["z:chat:shared"] if corruption else ["z:chat:shared", "z:chat:shared"])


@pytest.mark.parametrize("key", ["z:chat:shared", None], ids=["bound", "legacy"])
def test_orm_intent_json_round_trip_preserves_admission_and_legacy_absence(key: str | None) -> None:
    intent = Intent(session_id="session", prompt="Answer", admitted_capability_key=key)
    payload = _intent_payload(intent, idempotency_key="orm-round-trip")
    if key is None:
        del payload["admitted_capability_key"]
    row = Run(
        id=uuid4(),
        workflow_name="bridge_chat",
        pattern_manifest=(BRIDGE_CHAT_BOUND if key else BRIDGE_CHAT).manifest.snapshot(),
        source="bridge",
        queue_name="runs",
        priority=70,
        status="queued",
        sigil_name="magus",
        intent=json.loads(json.dumps(payload)),
        attempt=0,
        enqueue_seq=0,
        error=None,
        consent_id=None,
        delegated_job_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=None,
        finished_at=None,
    )
    record = DbRunLedger._to_record(row)
    assert record.admitted_capability_key == key
    rebuilt = record.to_intent()
    assert rebuilt.admitted_capability_key == key
    assert rebuilt.run_id == str(row.id)
    assert rebuilt.prompt == intent.prompt
    assert rebuilt.priority == 70


@pytest.mark.asyncio
@pytest.mark.parametrize("malformation", ["missing", "null", "empty"])
async def test_v2_checkpoint_decoder_rejects_a_lost_binding(malformation: str) -> None:
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="checkpoint", store=store)
    persistence.set_graph_types(BRIDGE_CHAT_BOUND_GRAPH)
    state = BoundBridgeChatState(
        session_id="session", run_id="checkpoint", prompt="Answer", capability_key="z:chat:shared"
    )
    await persistence.snapshot_node(state, Converse())
    document = await store.load("checkpoint")
    assert document is not None
    if malformation == "missing":
        del document[0]["state"]["capability_key"]
    else:
        document[0]["state"]["capability_key"] = None if malformation == "null" else ""
    await store.replace("checkpoint", json.loads(json.dumps(document)))
    restored = DurableStasisPhylactery(job_id="checkpoint", store=store)
    restored.set_graph_types(BRIDGE_CHAT_BOUND_GRAPH)
    with pytest.raises(ValidationError, match="capability key"):
        await restored.load_all()


def test_legacy_manifest_identity_remains_unchanged() -> None:
    assert BRIDGE_CHAT.manifest.digest == "e23ba8136df95af26744f1c9eee6ba28ae74a3de4578e9769a775d9985b9d163"
