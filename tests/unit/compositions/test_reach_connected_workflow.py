"""Finite connected plans through the real native Run road, without provider effects."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from pydantic import ValidationError
from pydantic_graph import GraphRunContext

from lychd.agents.services import WorkflowServices
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BuiltinWorkflowRegistry, builtin_workflow_registry
from lychd.compositions.reach.connected import workflow as connected_workflow
from lychd.compositions.reach.connected.schemas import (
    ChatTarget,
    ConnectedPolicy,
    Connection,
    CorrespondenceRequest,
    EmailTarget,
    ForgeTarget,
    PreparedBatch,
    ReadRequest,
    SendRequest,
)
from lychd.compositions.reach.connected.workflow import (
    ConnectedPreparationDeps,
    ConnectedPreparationRefused,
    ConnectedPreparationResult,
    ConnectedPreparationState,
    PrepareConnectedReach,
    ProjectConnectedReach,
    connected_preparation_workflow,
    make_connected_intent,
)
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)
TEXT = "Weekly update: the public release notes are ready for review."


def correspondence() -> tuple[ConnectedPolicy, tuple[CorrespondenceRequest, ...]]:
    """One explicit WUPHF consumer: an email, team chat and issue update."""
    mail = EmailTarget(connection_id="mail", mailbox_id="me", sender="reach@example.org", to=("reviewer@example.org",))
    chat = ChatTarget(connection_id="team", conversation_id="-100123456")
    issue = ForgeTarget(connection_id="forge", repository="example/project", issue_number=7)
    policy = ConnectedPolicy(
        policy_id="weekly-release",
        connections=(
            Connection(
                connection_id="mail",
                partition_id="operator",
                provider="gmail",
                account_id="me",
                actor_id="reach@example.org",
            ),
            Connection(
                connection_id="team",
                partition_id="operator",
                provider="telegram",
                account_id="release-bot",
                actor_id="bot:reach",
            ),
            Connection(
                connection_id="forge",
                partition_id="operator",
                provider="github",
                account_id="example",
                actor_id="release-bot",
            ),
        ),
        allowed_targets=(mail, chat, issue),
        operations=("read", "send"),
    )
    requests: tuple[CorrespondenceRequest, ...] = (
        SendRequest(request_id="release-email", target=mail, text=TEXT, subject="Weekly release review"),
        SendRequest(request_id="release-chat", target=chat, text=TEXT),
        SendRequest(request_id="release-issue", target=issue, text=TEXT),
    )
    return policy, requests


def station_context(
    *,
    clock: Callable[[], datetime] = lambda: NOW,
) -> tuple[
    ConnectedPolicy,
    GraphRunContext[ConnectedPreparationState, ConnectedPreparationDeps],
    list[ConnectedPreparationResult],
]:
    policy, requests = correspondence()
    results: list[ConnectedPreparationResult] = []
    workflow = connected_preparation_workflow(policy, clock=clock, record_result=results.append)
    intent = make_connected_intent(policy, requests, session_id="session", now=NOW).model_copy(
        update={"run_id": "canonical"}
    )
    state = cast("ConnectedPreparationState", workflow.make_state(intent))
    deps = ConnectedPreparationDeps(
        common=cast("WorkflowServices", object()), policy=policy, clock=clock, record_result=results.append
    )
    return policy, GraphRunContext(state=state, deps=deps), results


@dataclass
class CapturedQueue:
    enqueued: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        assert job_or_func == "perform_run"
        self.enqueued.append(kwargs)

    async def job(self, job_key: str, /) -> None:
        del job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        del job, error, ttl
        msg = "Connected preparation cannot request queue abortion."
        raise AssertionError(msg)


@pytest.mark.asyncio
@pytest.mark.parametrize("selection", ["wuphf", "read", "single"])
@pytest.mark.parametrize("expiry", ["fresh", "before-first-station", "before-projection"])
async def test_real_run_worker_and_native_graph_prepare_explicit_consumers(selection: str, expiry: str) -> None:  # noqa: PLR0915 - explicit end-to-end Run and duplicate-delivery evidence
    policy, sends = correspondence()
    requests = sends
    if selection == "read":
        requests = (
            ReadRequest(request_id="inbox", target=sends[0].target, limit=5),
            ReadRequest(request_id="issue-comments", target=sends[2].target, limit=8),
        )
    elif selection == "single":
        requests = (sends[1],)
    results: list[ConnectedPreparationResult] = []
    expired_at = NOW + timedelta(seconds=policy.ttl_seconds)
    times = iter(
        {
            "fresh": (NOW, NOW + timedelta(seconds=1)),
            "before-first-station": (expired_at, expired_at),
            "before-projection": (NOW, expired_at),
        }[expiry]
    )
    workflow = connected_preparation_workflow(policy, clock=lambda: next(times), record_result=results.append)
    registry = BuiltinWorkflowRegistry(workflows=(workflow,))
    ledger = InMemoryRunLedger()
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    session = await sessions.create_session(title="Connected Reach finite preparation")
    queue = CapturedQueue()
    dispatcher = FakeDispatcher(model=None)
    orchestrator = FakeOrchestrator()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        orchestrator=orchestrator,
        dispatcher=dispatcher,
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=sessions,
        forge=default_forge(),
        queues={"runs": queue},
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues=substrate.queues,
        stasis_store=substrate.stasis_store,
    )
    intent = make_connected_intent(policy, requests, session_id=session.id, now=NOW)
    handle = await engine.submit(intent)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.sigil_name == "reach.guest"
    assert run.sigil_scopes == frozenset()
    assert run.pattern_manifest == workflow.manifest.snapshot()
    assert workflow.manifest.key == "reach.connect.prepare"
    assert workflow.manifest.revision == "1"
    assert not workflow.durable
    assert len(queue.enqueued) == 1
    observed = await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=run.enqueue_seq)
    await bus.wait_persisted(handle.run_id)
    assert observed == {"status": "done", "run_id": handle.run_id}
    terminal = await ledger.get(handle.run_id)
    assert terminal is not None
    assert terminal.status is RunStatus.DONE
    assert len(results) == 1
    result = results[0]
    assert result.reason == ("prepared" if expiry == "fresh" else "expired")
    if expiry == "fresh":
        assert tuple(item.preparation.request for item in result.requests) == requests
        assert all(item.preparation.prepared_at == NOW for item in result.requests)
        assert all(item.preparation.expires_at == expired_at for item in result.requests)
        assert all("authorization" not in dict(item.headers) for item in result.requests)
        if selection == "wuphf":
            assert tuple(item.preparation.connection.provider for item in result.requests) == (
                "gmail",
                "telegram",
                "github",
            )
            assert json.loads(result.requests[1].body)["text"] == TEXT
            assert json.loads(result.requests[2].body) == {"body": TEXT}
    else:
        assert result.requests == ()
        assert TEXT not in result.model_dump_json()
        assert "reviewer@example.org" not in result.model_dump_json()
    assert dispatcher.calls == []
    assert orchestrator.calls == []
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=run.enqueue_seq)
    assert len(results) == 1


def test_exact_run_session_input_policy_and_state_binding() -> None:
    policy, requests = correspondence()
    workflow = connected_preparation_workflow(policy, clock=lambda: NOW, record_result=lambda _: None)
    intent = make_connected_intent(policy, requests, session_id="session", now=NOW).model_copy(
        update={"run_id": "canonical"}
    )
    state = cast("ConnectedPreparationState", workflow.make_state(intent))
    assert workflow.validate_state is not None
    workflow.validate_state(intent, state)
    restored = ConnectedPreparationState.model_validate_json(state.model_dump_json())
    workflow.validate_state(intent, restored)
    for changes in (
        {"run_id": "other"},
        {"session_id": "other"},
        {"priority": 1},
        {"sigil_scopes": frozenset({"send"})},
        {"sigil_name": "magus"},
        {"source": "bridge"},
    ):
        with pytest.raises(ConnectedPreparationRefused):
            workflow.validate_state(intent.model_copy(update=changes), state)
    for changes in ({"run_id": "other"}, {"session_id": "other"}, {"intent_digest": "0" * 64}):
        with pytest.raises(ConnectedPreparationRefused):
            workflow.validate_state(intent, state.model_copy(update=changes))
    for schema in (True, "1", 1.0, 2):
        with pytest.raises(ValidationError):
            workflow.validate_state(intent, state.model_copy(update={"schema_version": schema}))
    replacement = make_connected_intent(
        policy,
        (requests[0].model_copy(update={"text": "Altered message"}), *requests[1:]),
        session_id="session",
        now=NOW,
    ).model_copy(update={"run_id": "canonical"})
    with pytest.raises(ConnectedPreparationRefused):
        workflow.validate_state(replacement, state)
    changed_policy = connected_preparation_workflow(
        policy.model_copy(update={"revision": "2"}), clock=lambda: NOW, record_result=lambda _: None
    )
    with pytest.raises(ConnectedPreparationRefused):
        changed_policy.make_state(intent)
    batch = PreparedBatch.model_validate_json(intent.prompt)
    changed_connection = batch.operations[0].connection.model_copy(update={"actor_id": "other@example.org"})
    altered = batch.model_copy(
        update={
            "operations": (
                batch.operations[0].model_copy(update={"connection": changed_connection}),
                *batch.operations[1:],
            )
        }
    )
    with pytest.raises(ConnectedPreparationRefused):
        workflow.make_state(intent.model_copy(update={"prompt": altered.model_dump_json()}))


@pytest.mark.parametrize("field", ["prepared_at", "expires_at"])
def test_admitted_preparation_time_cannot_be_substituted(field: str) -> None:
    policy, requests = correspondence()
    workflow = connected_preparation_workflow(policy, clock=lambda: NOW, record_result=lambda _: None)
    intent = make_connected_intent(policy, requests, session_id="session", now=NOW).model_copy(
        update={"run_id": "canonical"}
    )
    batch = PreparedBatch.model_validate_json(intent.prompt)
    altered = batch.model_copy(update={field: getattr(batch, field) + timedelta(seconds=1)})
    with pytest.raises(ConnectedPreparationRefused):
        workflow.make_state(intent.model_copy(update={"prompt": altered.model_dump_json()}))


@pytest.mark.asyncio
async def test_clock_before_preparation_returns_no_payload() -> None:
    _, ctx, results = station_context(clock=lambda: NOW - timedelta(seconds=1))
    await PrepareConnectedReach().run(ctx)
    await ProjectConnectedReach().run(ctx)
    assert len(results) == 1
    assert results[0].reason == "clock_before_preparation"
    assert results[0].requests == ()
    assert TEXT not in results[0].model_dump_json()


@pytest.mark.asyncio
async def test_payload_tampering_between_stations_refuses_before_sink() -> None:
    policy, ctx, results = station_context()
    await PrepareConnectedReach().run(ctx)
    assert ctx.state.result is not None
    original = ctx.state.result
    changed = original.requests[-1].model_copy(update={"body": '{"body":"substituted payload"}'})
    ctx.state.result = original.model_copy(update={"requests": (*original.requests[:-1], changed)})
    _, requests = correspondence()
    intent = make_connected_intent(policy, requests, session_id="session", now=NOW).model_copy(
        update={"run_id": "canonical"}
    )
    workflow = connected_preparation_workflow(policy, clock=lambda: NOW, record_result=results.append)
    assert workflow.validate_state is not None
    with pytest.raises(ConnectedPreparationRefused):
        workflow.validate_state(intent, ctx.state)
    with pytest.raises(ConnectedPreparationRefused):
        await ProjectConnectedReach().run(ctx)
    assert results == []


@pytest.mark.asyncio
async def test_expired_checkpoint_cannot_manufacture_a_fresh_ttl() -> None:
    _, ctx, results = station_context(clock=lambda: NOW + timedelta(seconds=300))
    original = ctx.state.prepared
    await PrepareConnectedReach().run(ctx)
    assert ctx.state.result is not None
    assert ctx.state.result.reason == "expired"
    # A replacement dependency clock cannot resurrect a retained refusal.
    earlier = ConnectedPreparationDeps(
        common=ctx.deps.common, policy=ctx.deps.policy, clock=lambda: NOW, record_result=results.append
    )
    await ProjectConnectedReach().run(GraphRunContext(state=ctx.state, deps=earlier))
    assert results[0].reason == "expired"
    assert results[0].requests == ()
    assert ctx.state.prepared == original
    with pytest.raises(ConnectedPreparationRefused):
        await PrepareConnectedReach().run(ctx)


def test_all_policy_preflight_precedes_any_builder_and_errors_hide_content(monkeypatch: pytest.MonkeyPatch) -> None:
    policy, requests = correspondence()
    calls: list[str] = []
    actual = connected_workflow.build_request

    def observed(operation: Any) -> Any:
        calls.append(operation.request.request_id)
        return actual(operation)

    monkeypatch.setattr(connected_workflow, "build_request", observed)
    bad = requests[-1].model_copy(
        update={"target": ForgeTarget(connection_id="forge", repository="other/project", issue_number=7)}
    )
    with pytest.raises(ConnectedPreparationRefused) as refused:
        make_connected_intent(policy, (*requests[:-1], bad), session_id="session", now=NOW)
    assert calls == []
    assert TEXT not in str(refused.value)
    assert "other/project" not in str(refused.value)


def test_unsupported_provider_operation_never_creates_an_intent() -> None:
    policy, requests = correspondence()
    telegram_read = ReadRequest(request_id="chat-history", target=requests[1].target)
    with pytest.raises(ConnectedPreparationRefused) as refused:
        make_connected_intent(policy, (requests[0], telegram_read), session_id="session", now=NOW)
    assert str(refused.value) == "Connected Reach preparation refused."
    with pytest.raises(ValueError, match="timezone-aware"):
        make_connected_intent(policy, requests, session_id="session", now=NOW.replace(tzinfo=None))


@pytest.mark.asyncio
async def test_native_stations_require_an_explicit_aware_clock() -> None:
    _, ctx, results = station_context(clock=lambda: NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        await PrepareConnectedReach().run(ctx)
    assert results == []


def test_explicit_factory_does_not_activate_registry_or_change_legacy_reach() -> None:
    policy, _ = correspondence()
    workflow = connected_preparation_workflow(policy, clock=lambda: NOW, record_result=lambda _: None)
    assert [node.key for node in workflow.manifest.nodes] == ["prepare", "project", "end"]
    assert all(item.name != "reach.connect.prepare" for item in builtin_workflow_registry().all())
