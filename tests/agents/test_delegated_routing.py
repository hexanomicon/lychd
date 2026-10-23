"""Configured delegation binds before dispatch and never invents fallback authority."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from pydantic import ValidationError
from pydantic_graph import GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.workflows import DELEGATED_RITE, DELEGATED_RITE_BOUND, builtin_workflow_registry
from lychd.agents.workflows.delegated_rite import BoundDelegatedRiteState, DelegatedRiteState, DispatchBoundDelegate
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import DelegationCastingSettings, Settings, SettingsSnapshot, WeaverSettings
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.delegation.models import DelegatedAgentJobRef, DelegatedAgentJobStatus, DelegatedAgentRequest
from lychd.domain.delegation.routing import DelegatedRuntimeBinding
from lychd.domain.delegation.services import DelegatedAgentCoordinator, InMemoryDelegatedAgentJobStore
from lychd.domain.delegation.signals import DelegatedAgentPending
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime
from lychd.interface.web.altar_services import build_altar_services
from tests.runtime_guards import InertSoftActivationGuard
from tests.unit.domain.cortex.test_engine import _FakeQueue  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from lychd.agents.services import WorkflowServices


def _selection(runtime: str = "reference") -> DelegationCastingSettings:
    return DelegationCastingSettings(revision="2", runtime=runtime)


@pytest.mark.parametrize(
    "fields",
    [
        {"revision": "1", "runtime": "reference"},
        {"revision": "2", "runtime": "../codex"},
        {"revision": "2", "runtime": "codex\n"},
        {"revision": "2", "runtime": "codex", "fallback": "claude"},
        {"revision": "2", "runtime": "codex", "trusted": True},
        {"revision": "2", "runtime": "codex", "command": "codex exec"},
    ],
)
def test_route_configuration_refuses_authority_and_unimplemented_fallback(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DelegationCastingSettings.model_validate(fields)


def test_selection_is_frozen_snapshot_owned_and_default_is_reference_only() -> None:
    assert WeaverSettings().delegation is None
    selection = _selection()
    with pytest.raises(ValidationError, match="frozen"):
        selection.runtime = "other"
    settings = Settings(weaver=WeaverSettings(delegation=selection))
    snapshot = SettingsSnapshot.capture(settings)
    settings.weaver.delegation = _selection("other")
    assert snapshot.materialize().weaver.delegation == selection
    assert builtin_workflow_registry().route(Intent(session_id="s", prompt="/delegate task")) is DELEGATED_RITE
    registry = builtin_workflow_registry(weaver=WeaverSettings(delegation=selection))
    assert registry.route(Intent(session_id="s", prompt="/delegate task")) is DELEGATED_RITE_BOUND
    assert registry.get_revision("delegated_rite", "1") is DELEGATED_RITE
    assert builtin_workflow_registry().get_revision("delegated_rite", "2") is DELEGATED_RITE_BOUND


def test_assembly_refuses_unregistered_runtime_before_other_service_construction() -> None:
    with pytest.raises(ValueError, match="exactly one registered adapter"):
        build_altar_services(
            queues={},
            runes=RuneRegistry(()),
            settings=Settings(weaver=WeaverSettings(delegation=_selection("codex"))),
            profile="memory",
            delegated_runtime_adapters=(ReferenceDelegatedAgentRuntime(),),
            soft_activation_guard=InertSoftActivationGuard(),
        )


@pytest.mark.asyncio
async def test_real_admission_pins_selection_across_configuration_change_and_dispatch() -> None:
    runtime = ReferenceDelegatedAgentRuntime()
    queue = _FakeQueue()
    settings = Settings(weaver=WeaverSettings(delegation=_selection()))
    services = build_altar_services(
        queues={"runs": queue, "rites": queue},
        runes=RuneRegistry(()),
        settings=settings,
        profile="memory",
        delegated_runtime_adapters=(runtime,),
        soft_activation_guard=InertSoftActivationGuard(),
    )
    try:
        intent = Intent(session_id="s", prompt="/delegate inspect")
        handle = await services.run_engine.submit(intent, idempotency_key="same-admission")
        record = await services.run_engine.ledger.get(handle.run_id)
        assert record is not None
        assert record.admitted_delegation == _selection().binding()
        assert record.pattern_manifest["revision"] == "2"
        services.run_engine.delegation_binding = _selection("other").binding()
        replay = await services.run_engine.submit(intent, idempotency_key="same-admission")
        assert replay.run_id == handle.run_id
        replayed = await services.run_engine.ledger.get(replay.run_id)
        assert replayed is not None
        assert replayed.admitted_delegation == record.admitted_delegation
        state = DELEGATED_RITE_BOUND.make_state(replayed.to_intent())
        assert isinstance(state, BoundDelegatedRiteState)
        restored = BoundDelegatedRiteState.model_validate_json(state.model_dump_json())
        assert DELEGATED_RITE_BOUND.validate_state is not None
        DELEGATED_RITE_BOUND.validate_state(replayed.to_intent(), restored)
        context: GraphRunContext[DelegatedRiteState, WorkflowServices] = GraphRunContext(
            state=restored, deps=cast("WorkflowServices", SimpleNamespace(delegates=services.delegates))
        )
        with pytest.raises(DelegatedAgentPending) as pending:
            await DispatchBoundDelegate().run(context)
        assert pending.value.job.runtime == "reference"
        assert services.delegates is not None
        job = await services.delegates.refresh(pending.value.job.job_id)
        assert job.status is DelegatedAgentJobStatus.SUCCEEDED
    finally:
        await services.aclose()


@pytest.mark.asyncio
async def test_caller_cannot_supply_runtime_admission_metadata() -> None:
    ledger = InMemoryRunLedger()
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": _FakeQueue()},
    )
    with pytest.raises(ValueError, match="server-owned"):
        await engine.submit(
            Intent(
                session_id="s", prompt="/delegate task", admitted_delegation=DelegatedRuntimeBinding(runtime="codex")
            )
        )


class _RefusingRuntime(ReferenceDelegatedAgentRuntime):
    name = "codex"

    def __init__(self) -> None:
        super().__init__()
        self.starts = 0

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        _ = (request, job)
        self.starts += 1
        message = "host admission denied; no fallback authorized"
        raise PermissionError(message)


@pytest.mark.parametrize("configured", [False, True])
def test_duplicate_unselected_adapters_cannot_replace_owners_of_retained_jobs(*, configured: bool) -> None:
    settings = Settings(weaver=WeaverSettings(delegation=_selection() if configured else None))
    queue = _FakeQueue()
    with pytest.raises(ValueError, match="Duplicate delegated runtime identities"):
        build_altar_services(
            queues={"runs": queue, "rites": queue},
            runes=RuneRegistry(()),
            settings=settings,
            profile="memory",
            delegated_runtime_adapters=(ReferenceDelegatedAgentRuntime(), _RefusingRuntime(), _RefusingRuntime()),
            soft_activation_guard=InertSoftActivationGuard(),
        )


@pytest.mark.asyncio
async def test_runtime_refusal_never_selects_another_runtime_or_replays_start() -> None:
    runtime = _RefusingRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime, "reference": ReferenceDelegatedAgentRuntime()},
        store=InMemoryDelegatedAgentJobStore(),
    )
    intent = Intent(
        session_id="s", run_id="r", prompt="/delegate task", admitted_delegation=_selection("codex").binding()
    )
    state = DELEGATED_RITE_BOUND.make_state(intent)
    assert isinstance(state, BoundDelegatedRiteState)
    context: GraphRunContext[DelegatedRiteState, WorkflowServices] = GraphRunContext(
        state=state, deps=cast("WorkflowServices", SimpleNamespace(delegates=coordinator))
    )
    with pytest.raises(PermissionError, match="host admission denied"):
        await DispatchBoundDelegate().run(context)
    with pytest.raises(DelegatedAgentPending):
        await DispatchBoundDelegate().run(context)
    with pytest.raises(RuntimeError, match="settled lost"):
        await DispatchBoundDelegate().run(context)
    assert runtime.starts == 1
    jobs = await coordinator.jobs_for_run("r")
    assert len(jobs) == 1
    assert jobs[0].ref.runtime == "codex"
    changed = state.model_copy(update={"binding": _selection("reference").binding()})
    assert DELEGATED_RITE_BOUND.validate_state is not None
    with pytest.raises(ValueError, match="runtime binding"):
        DELEGATED_RITE_BOUND.validate_state(intent, changed)


def test_database_projection_retains_and_validates_delegation_binding() -> None:
    from datetime import UTC, datetime

    from lychd.domain.cortex.ledger import DbRunLedger, _intent_payload  # pyright: ignore[reportPrivateUsage]

    binding = _selection("codex").binding()
    intent = Intent(session_id="s", prompt="/delegate task", admitted_delegation=binding)
    payload = _intent_payload(intent)
    row = SimpleNamespace(
        intent=payload,
        id="run-1",
        sigil_name="magus",
        workflow_name="delegated_rite",
        pattern_manifest=DELEGATED_RITE_BOUND.manifest.snapshot(),
        source="bridge",
        queue_name="runs",
        priority=50,
        status="queued",
        attempt=0,
        enqueue_seq=0,
        error=None,
        consent_id=None,
        delegated_job_id=None,
        peer_task_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=None,
        finished_at=None,
    )
    record = DbRunLedger._to_record(row)  # pyright: ignore[reportPrivateUsage]
    assert record.admitted_delegation == binding
    assert record.to_intent().admitted_delegation == binding
    payload["admitted_delegation"] = {"runtime": "../other", "profile": "read"}
    with pytest.raises(ValidationError):
        DbRunLedger._to_record(row)  # pyright: ignore[reportPrivateUsage]
