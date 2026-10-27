"""Independent preparation cases and an inert real RunEngine/worker/native Graph passage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BuiltinWorkflowRegistry, builtin_workflow_registry
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import ReachDecision, ReachEvent, ReachPolicy, ReachRule
from lychd.compositions.reach.workflow import (
    ReachPreparationRefused,
    make_preparation_intent,
    reach_preparation_workflow,
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

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def policy(**changes: Any) -> ReachPolicy:
    values: dict[str, Any] = {
        "platform": "discord",
        "account_id": "101",
        "agent_subject_id": "102",
        "space_id": "103",
        "allowed_conversation_ids": ("104",),
        "rules": (ReachRule(name="operator", subject_ids=("105",), actions=("answer_docs", "summarize_context")),),
    }
    return ReachPolicy(**(values | changes))


def event(**changes: Any) -> ReachEvent:
    values: dict[str, Any] = {
        "platform": "discord",
        "account_id": "101",
        "event_id": "110",
        "space_id": "103",
        "conversation_id": "104",
        "subject_id": "105",
        "mention_subject_ids": ("102",),
        "trigger": "mention",
        "action": "answer_docs",
        "question": "How does the public Reach contract work?",
        "occurred_at": NOW - timedelta(seconds=5),
    }
    return ReachEvent(**(values | changes))


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"platform": "telegram"}, "wrong_platform"),
        ({"account_id": "201"}, "wrong_account"),
        ({"space_id": "203"}, "wrong_space"),
        ({"conversation_id": "204"}, "conversation_not_allowed"),
        ({"subject_id": "102"}, "self_event"),
        ({"is_automated": True}, "automated_subject"),
        ({"trigger": "message"}, "trigger_not_allowed"),
        ({"mention_subject_ids": ()}, "missing_agent_mention"),
        ({"action": "run_shell"}, "action_not_supported"),
        ({"subject_id": "205"}, "subject_not_allowed"),
        ({"occurred_at": NOW + timedelta(microseconds=1)}, "event_from_future"),
        ({"occurred_at": NOW - timedelta(seconds=300)}, "event_expired"),
        ({"question": " \n\t"}, "question_empty"),
        ({"question": "x" * 2001}, "question_too_large"),
        ({"question": "private\x00material"}, "question_invalid"),
        ({"action": "summarize_context"}, "context_disabled"),
    ],
)
def test_refusal_table_drops_message_content(changes: dict[str, Any], reason: str) -> None:
    observed = event(**changes)
    decision = prepare_turn(policy(), observed, now=NOW)
    assert decision.allowed is False
    assert decision.reason == reason
    assert decision.prepared is None
    wire = decision.model_dump(mode="json")
    assert "question" not in wire
    assert "event" not in wire
    assert wire["identity"]["event_id"] == "110"
    assert wire["identity"]["account_id"] == observed.account_id
    assert decision.policy_digest == policy().digest


def test_subject_or_group_and_first_matching_rule_decides() -> None:
    configured = policy(
        context_message_limit=12,
        rules=(
            ReachRule(name="narrow", subject_ids=("105",), actions=("answer_docs",)),
            ReachRule(name="group", group_ids=("106",), actions=("summarize_context",)),
        ),
    )
    denied = prepare_turn(configured, event(group_ids=("106",), action="summarize_context"), now=NOW)
    assert denied.reason == "action_not_allowed"
    accepted = prepare_turn(
        configured, event(subject_id="107", group_ids=("106",), action="summarize_context"), now=NOW
    )
    assert accepted.allowed
    assert accepted.prepared is not None
    assert accepted.prepared.rule_name == "group"
    assert accepted.prepared.action == "summarize_context"
    assert accepted.prepared.expires_at == event().occurred_at + timedelta(seconds=300)
    assert "question" not in repr(accepted)


def test_command_does_not_need_mention_and_trigger_policy_is_shared() -> None:
    assert prepare_turn(policy(), event(trigger="command", mention_subject_ids=()), now=NOW).allowed
    assert prepare_turn(policy(allowed_triggers=("mention",)), event(trigger="command"), now=NOW).reason == (
        "trigger_not_allowed"
    )


@pytest.mark.parametrize("identity", [105, True, "", " 105", "105\n", "zero\u200bwidth", "x" * 129])
def test_opaque_ids_are_strict_bounded_and_control_free(identity: Any) -> None:
    with pytest.raises(ValidationError):
        policy(account_id=identity)


@pytest.mark.parametrize("identity", ["-100123456", "alice@example.net", "bot:reach", "0105", "+105", "0"])
def test_opaque_ids_do_not_impose_a_provider_dialect(identity: str) -> None:
    assert policy(account_id=identity).account_id == identity


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"schema_version": "1"},
        {"schema_version": 1.0},
        {"event_ttl_seconds": True},
        {"context_message_limit": 51},
        {"context_max_age_seconds": 3601},
        {"allowed_conversation_ids": ()},
        {"allowed_conversation_ids": ("104", "104")},
        {"rules": ()},
        {"rules": (ReachRule(name="same", subject_ids=("105",), actions=("answer_docs",)),) * 2},
    ],
)
def test_configuration_refuses_ambiguous_or_unbounded_values(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        policy(**changes)


def test_empty_selectors_and_unknown_actions_do_not_create_authority() -> None:
    with pytest.raises(ValidationError):
        ReachRule(name="everyone", actions=("answer_docs",))
    with pytest.raises(ValidationError):
        ReachRule.model_validate_json('{"name":"shell","subject_ids":["105"],"actions":["shell"]}')
    configured = policy()
    assert ReachPolicy.model_validate_json(configured.model_dump_json()) == configured
    with pytest.raises(ValidationError):
        configured.context_message_limit = 1


def test_explicit_clock_and_denied_ingress_never_builds_an_intent() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        prepare_turn(policy(), event(), now=NOW.replace(tzinfo=None))
    with pytest.raises(ReachPreparationRefused) as refused:
        make_preparation_intent(policy(), event(trigger="message"), session_id="fixture", now=NOW)
    assert refused.value.decision.reason == "trigger_not_allowed"
    assert refused.value.decision.prepared is None
    assert event().question not in str(refused.value)


def test_exact_binding_rejects_changed_run_session_policy_or_event() -> None:
    configured = policy()
    workflow = reach_preparation_workflow(configured, clock=lambda: NOW, record_result=lambda _: None)
    intent = make_preparation_intent(configured, event(), session_id="session", now=NOW)
    admitted = intent.model_copy(update={"run_id": "canonical"})
    state = workflow.make_state(admitted)
    assert workflow.validate_state is not None
    workflow.validate_state(admitted, state)
    for changes in ({"run_id": "other"}, {"session_id": "other"}, {"sigil_scopes": frozenset({"*"})}):
        with pytest.raises(ValueError, match=r"Reach (checkpoint differs|preparation requires)"):
            workflow.validate_state(admitted.model_copy(update=changes), state)
    for invalid_version in (True, "1", 1.0, 2):
        with pytest.raises(ValidationError):
            workflow.validate_state(admitted, state.model_copy(update={"schema_version": invalid_version}))
    replacement = make_preparation_intent(
        configured, event(question="A different question"), session_id="session", now=NOW
    )
    with pytest.raises(ValueError, match="checkpoint differs"):
        workflow.validate_state(replacement.model_copy(update={"run_id": "canonical"}), state)
    changed = reach_preparation_workflow(policy(event_ttl_seconds=200), clock=lambda: NOW, record_result=lambda _: None)
    with pytest.raises(ValueError, match="pinned policy"):
        changed.make_state(admitted)


@dataclass
class CapturedQueue:
    """No broker; keep native worker arguments without executing at publication."""

    enqueued: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        assert job_or_func == "perform_run"
        self.enqueued.append(kwargs)

    async def job(self, job_key: str, /) -> None:
        del job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        del job, error, ttl
        msg = "Preparation fixture unexpectedly requested queue abortion."
        raise AssertionError(msg)


@pytest.mark.asyncio
@pytest.mark.parametrize("expired", [False, True])
@pytest.mark.parametrize("platform", ["discord", "telegram"])
async def test_real_admission_worker_and_native_graph_have_no_effects(platform: str, *, expired: bool) -> None:
    # These are normalized fixtures, not implementations of either provider's transport.
    configured = policy(platform=platform)
    observed = event(platform=platform)
    if platform == "telegram":
        configured = policy(
            platform=platform,
            account_id="bot:reach",
            agent_subject_id="agent:reach",
            space_id=None,
            allowed_conversation_ids=("-100123456",),
            rules=(ReachRule(name="developer", subject_ids=("-105",), actions=("answer_docs",)),),
        )
        observed = event(
            platform=platform,
            account_id="bot:reach",
            space_id=None,
            conversation_id="-100123456",
            subject_id="-105",
            mention_subject_ids=("agent:reach",),
            trigger="command",
        )
    results: list[ReachDecision] = []
    execution_time = NOW + timedelta(seconds=300) if expired else NOW
    workflow = reach_preparation_workflow(configured, clock=lambda: execution_time, record_result=results.append)
    registry = BuiltinWorkflowRegistry(workflows=(workflow,))
    ledger = InMemoryRunLedger()
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    session = await sessions.create_session(title="Restricted Reach preparation fixture")
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
    intent = make_preparation_intent(configured, observed, session_id=session.id, now=NOW)
    handle = await engine.submit(intent)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.sigil_name == "reach.guest"
    assert run.sigil_scopes == frozenset()
    assert run.pattern_manifest == workflow.manifest.snapshot()
    assert len(queue.enqueued) == 1
    worker_result = await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=run.enqueue_seq)
    await bus.wait_persisted(handle.run_id)
    assert worker_result == {"status": "done", "run_id": handle.run_id}
    terminal = await ledger.get(handle.run_id)
    assert terminal is not None
    assert terminal.status is RunStatus.DONE
    assert len(results) == 1
    assert results[0].reason == ("event_expired" if expired else "prepared")
    assert results[0].allowed is not expired
    assert results[0].identity.event_id == "110"
    assert results[0].identity.platform == platform
    assert results[0].identity.account_id == configured.account_id
    assert dispatcher.calls == []
    assert orchestrator.calls == []
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=run.enqueue_seq)
    assert len(results) == 1


def test_normal_registry_never_activates_preparation() -> None:
    assert all(workflow.name != "reach.prepare" for workflow in builtin_workflow_registry().all())
