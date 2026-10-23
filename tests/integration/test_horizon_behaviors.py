"""Native finite behavior Runs with in-memory observations and no live effects."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.compositions.blockworld.horizon_assist import (
    AssistPolicy,
    AssistRequest,
    AssistResult,
    HorizonAssistService,
    SayAction,
)
from lychd.compositions.blockworld.horizon_assist_runtime import BehaviorAdmissionRefused, LocalAssistRunner
from lychd.compositions.blockworld.horizon_behaviors import (
    BehaviorDirective,
    BehaviorPolicy,
    BehaviorTick,
    HorizonBehaviorService,
)
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import LiveStasisPhylactery, NodeSnapshot
from lychd.ghouls import runs

pytestmark = pytest.mark.asyncio


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def observation(x: float = 0.0) -> dict[str, Any]:
    return {
        "world": "Test",
        "dimension": "minecraft:overworld",
        "screen": "playing",
        "paused": False,
        "player": {"position": [x, 64.0, 0.0], "health": 20.0},
        "busy": None,
    }


class Feed:
    def __init__(self, x: float = 0.0) -> None:
        self.state = observation(x)
        self.reads = 0
        self.on_read: Callable[[], Awaitable[None]] | None = None
        self.error = False

    async def observe(self) -> dict[str, Any]:
        self.reads += 1
        if self.on_read is not None:
            await self.on_read()
        if self.error:
            msg = "Read unavailable."
            raise OSError(msg)
        return self.state


class Control(Feed):
    def __init__(self) -> None:
        super().__init__()
        self.commands: list[str] = []
        self.handoff: Callable[[], None] | None = None
        self.after_reply: Callable[[], None] | None = None
        self.outcome = "client_observed"
        self.contained = 0
        self.fenced: set[str] = set()

    async def invoke(
        self, run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> AssistResult:
        del query
        latest = await self.observe()
        if self.handoff is not None:
            self.handoff()
        if authorize is not None:
            try:
                authorize(latest)
            except ValueError:
                return AssistResult(request_id=run_id, kind="refused", detail="No bytes sent.")
        self.commands.append(line)
        if self.after_reply is not None:
            self.after_reply()
        return AssistResult.model_validate({"request_id": run_id, "kind": self.outcome, "detail": "Client only."})

    def fence(self, run_id: str, reason: str) -> None:
        del reason
        self.fenced.add(run_id)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        del enqueue_seq
        self.fence(run_id, reason)

    def fence_all(self, reason: str) -> None:
        del reason

    async def contain(self, run_id: str) -> None:
        self.fenced.add(run_id)
        self.contained += 1

    async def contain_all(self) -> None:
        self.contained += 1

    async def aclose(self) -> None:
        pass


def assist_policy(**changes: Any) -> AssistPolicy:
    return AssistPolicy.model_validate(
        {
            "session_id": "behavior-test",
            "principal": "operator",
            "expires_at": datetime.now(UTC) + timedelta(minutes=2),
            "min_x": -32.0,
            "max_x": 32.0,
            "min_y": 60.0,
            "max_y": 70.0,
            "min_z": -32.0,
            "max_z": 32.0,
            "action_timeout_s": 1.0,
            "permitted": ("state", "status", "goto", "say"),
            **changes,
        }
    )


def directive(kind: str = "idle", duration: float = 60.0) -> BehaviorDirective:
    return BehaviorDirective.model_validate({"kind": kind, "task_id": str(uuid4()), "duration_s": duration})


@pytest_asyncio.fixture
async def assembly() -> AsyncIterator[tuple[Clock, Control, Feed, HorizonBehaviorService, LocalAssistRunner]]:
    clock, control, target = Clock(), Control(), Feed()
    assist = HorizonAssistService(assist_policy(), control)
    service = HorizonBehaviorService(assist, target, clock=clock)
    runner = LocalAssistRunner(assist, control, behaviors=service)
    await runner.open()
    try:
        yield clock, control, target, service, runner
    finally:
        await runner.aclose()


async def tick_run(service: HorizonBehaviorService, runner: LocalAssistRunner) -> tuple[BehaviorTick, str]:
    tick = service.new_tick()
    run_id = await runner.submit_behavior(tick)
    await runner.wait(run_id)
    return tick, run_id


async def test_strict_finite_immutable_inputs() -> None:
    for changes in ({"duration_s": True}, {"duration_s": 61.0}, {"duration_s": float("nan")}, {"task_id": "x"}):
        with pytest.raises(ValidationError):
            BehaviorDirective.model_validate({"kind": "idle", "task_id": str(uuid4()), "duration_s": 1.0, **changes})
    for changes in (
        {"max_ticks": 61},
        {"cadence_s": 0.5},
        {"freshness_s": 4.0},
        {"deadband": 1.0},
        {"max_segment": 5.0},
    ):
        with pytest.raises(ValidationError):
            BehaviorPolicy.model_validate(changes)
    task = directive()
    with pytest.raises(ValidationError):
        task.kind = "follow"


async def test_idle_native_manifest_logs_coalescible_observations_and_inert_boot(assembly: Any) -> None:
    _, control, _, service, runner = assembly
    service.begin(directive())
    first, run_id = await tick_run(service, runner)
    second, _ = await tick_run(service, runner)
    assert service.results[first.request_id].kind == "changed"
    assert service.results[second.request_id].kind == "unchanged"
    assert control.commands == []
    assert service.observation_count == 2
    assert service.action_count == service.assist.used == 0
    assert await runner.submit_behavior(first) == run_id
    assert runner.services is not None
    run = await runner.services.ledger.get(run_id)
    assert run.status is RunStatus.DONE
    assert run.pattern_manifest["key"] == "blockworld.horizon_idle_tick"
    assert run.pattern_manifest["revision"] == "1"
    assert [node["key"] for node in run.pattern_manifest["nodes"]] == ["validate", "observe", "decide", "report", "end"]
    events = await runner.services.ledger.list_events(run_id)
    assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
        "validate",
        "observe",
        "decide",
        "report",
    ]
    assert any(event.kind == "log" and "changed" in event.data for event in events)
    assert not any("horizon" in workflow.name for workflow in builtin_workflow_registry().all())
    assert service.records[-1]["observation_count"] == 1


async def test_follow_stationary_target_has_no_movement(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(1.0)
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "unchanged"
    assert not result.stop_required
    assert result.observation_count == 2
    assert result.action_count == 0
    assert control.commands == []


async def test_matching_explicit_empty_remote_labels_preserve_client_observation_only(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    control.state["world"] = target.state["world"] = ""
    target.state["player"]["position"] = [1.0, 64.0, 0.0]
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    assert service.results[tick.request_id].kind == "unchanged"
    assert not control.commands


async def test_follow_segment_is_finite_native_and_uses_shared_budget(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    control.after_reply = lambda: control.state.update(observation(2.0))
    service.begin(directive("follow"))
    tick, run_id = await tick_run(service, runner)
    assert control.commands == ["goto 4 64 0 --near 1.5 --timeout 1"]
    result = service.results[tick.request_id]
    assert result.kind == "moved"
    assert not result.stop_required
    assert result.start_position == (0.0, 64.0, 0.0)
    assert result.end_position == (2.0, 64.0, 0.0)
    assert result.displacement == result.progress == 2.0
    assert result.distance_after == 10.0
    assert result.observation_count == service.observation_count == 3
    assert control.reads == 4  # Two logical reads plus assist preflight and final handoff.
    assert target.reads == 1
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert result.action_count == service.assist.used == service.action_count == 1
    assert runner.services is not None
    run = await runner.services.ledger.get(run_id)
    assert run.pattern_manifest["key"] == "blockworld.horizon_follow_tick"
    events = await runner.services.ledger.list_events(run_id)
    assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
        "validate",
        "observe",
        "decide",
        "action",
        "report",
    ]
    await runner.submit_behavior(tick)
    assert len(control.commands) == 1


@pytest.mark.parametrize("position", [[0.0, 64.0, 0.0], [0.0, 64.0, 2.0], [-2.0, 64.0, 0.0], [0.04, 64.0, 0.0]])
async def test_client_ok_without_measured_progress_stops_finite_follow(assembly: Any, position: list[float]) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    control.after_reply = lambda: control.state["player"].update(position=position)
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "no_progress"
    assert result.stop_required
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert result.action_result.detail == "Client only."
    assert result.observation_count == service.observation_count == 3
    assert result.action_count == service.assist.used == service.action_count == 1
    assert service.directive is None
    with pytest.raises(ValueError, match="authority"):
        service.new_tick()
    with pytest.raises(BehaviorAdmissionRefused):
        await runner.submit_behavior(tick)
    assert len(control.commands) == 1


async def test_progress_starts_at_final_authorized_pose_and_pins_original_target(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    control.handoff = lambda: control.state.update(observation(1.0))

    def after_reply() -> None:
        # The earlier observation would falsely credit one block. The target's
        # later motion cannot change the sample used for this finite tick.
        control.state = observation(1.0)
        target.state = observation(-12.0)

    control.after_reply = after_reply
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "no_progress"
    assert result.start_position == result.end_position == (1.0, 64.0, 0.0)
    assert result.distance == 12.0
    assert result.distance_after == 11.0
    assert result.displacement == result.progress == 0.0


@pytest.mark.parametrize(
    "failure", ["error", "stale", "world", "dimension", "health_loss", "busy", "bounds", "invalid", "loading"]
)
async def test_unsafe_postflight_preserves_known_reply_and_never_repeats(assembly: Any, failure: str) -> None:
    clock, control, target, service, runner = assembly
    target.state = observation(12.0)
    changed_fields = {"world": {"world": "Other"}, "dimension": {"dimension": "other"}, "busy": {"busy": "goto"}}

    def after_reply() -> None:
        control.state = observation(2.0)
        if failure == "error":
            control.error = True
        elif failure == "stale":

            async def age() -> None:
                clock.now += service.policy.freshness_s

            control.on_read = age
        elif failure in changed_fields:
            control.state.update(changed_fields[failure])
        elif failure == "health_loss":
            control.state["player"]["health"] = 19.0
        elif failure == "bounds":
            control.state = observation(33.0)
        elif failure == "invalid":
            control.state["player"]["position"][0] = float("nan")
        else:
            control.state["screen"] = "loading"

    control.after_reply = after_reply
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "movement_unverified"
    assert result.stop_required
    assert result.action_result == service.assist.results[tick.request_id]
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert result.end_position is result.displacement is result.progress is result.distance_after is None
    assert result.observation_count == service.observation_count == 3
    assert result.action_count == service.assist.used == 1
    assert service.directive is None
    with pytest.raises(BehaviorAdmissionRefused):
        await runner.submit_behavior(tick)
    assert len(control.commands) == 1


async def test_postflight_generation_race_cannot_fence_successor(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    service.begin(directive("follow"))
    prior_generation = service.generation
    successor = directive()

    def after_reply() -> None:
        async def replace() -> None:
            service.begin(successor)

        control.on_read = replace

    control.after_reply = after_reply
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "movement_unverified"
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert service.directive == successor
    assert service.generation > prior_generation
    control.on_read = None
    successor_tick, _ = await tick_run(service, runner)
    assert service.results[successor_tick.request_id].kind == "changed"
    assert len(control.commands) == 1


async def test_cancelled_postflight_retains_known_reply_and_read_count(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    entered = asyncio.Event()

    async def blocked() -> None:
        entered.set()
        await asyncio.Event().wait()

    control.after_reply = lambda: setattr(control, "on_read", blocked)
    service.begin(directive("follow"))
    tick = service.new_tick()
    await runner.submit_behavior(tick)
    await asyncio.wait_for(entered.wait(), timeout=1)
    service.fence("operator_cancelled")
    await runner.cancel()
    result = service.results[tick.request_id]
    assert result.kind == "movement_unverified"
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert result.stop_required
    assert result.observation_count == 3
    assert result.action_count == 1
    assert len(control.commands) == 1


async def test_missing_final_authorization_pose_never_credits_motion(
    assembly: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)

    async def unguarded(
        run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> AssistResult:
        del query, authorize
        control.commands.append(line)
        control.state = observation(2.0)
        return AssistResult(request_id=run_id, kind="client_observed", detail="Client only.")

    monkeypatch.setattr(control, "invoke", unguarded)
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "movement_unverified"
    assert result.stop_required
    assert result.start_position is result.end_position is None
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert len(control.commands) == 1


@pytest.mark.parametrize("where", ["handoff", "next_observe"])
async def test_health_loss_refuses_handoff_and_later_follow(assembly: Any, where: str) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    service.begin(directive("follow"))
    if where == "handoff":
        control.handoff = lambda: control.state["player"].update(health=19.0)
    else:
        control.after_reply = lambda: control.state.update(observation(2.0))
        first, _ = await tick_run(service, runner)
        assert service.results[first.request_id].kind == "moved"
        control.state["player"]["health"] = 19.0
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == "refused"
    assert result.stop_required
    assert len(control.commands) == (1 if where == "next_observe" else 0)


@pytest.mark.parametrize("outcome", ["refused", "client_error", "outcome_unknown"])
async def test_noncompletion_keeps_disposition_without_postflight(assembly: Any, outcome: str) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(12.0)
    control.outcome = outcome
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.kind == outcome
    assert result.action_result is not None
    assert result.action_result.kind == outcome
    assert result.observation_count == 2
    assert control.reads == 3
    assert len(control.commands) == 1


async def test_tick_and_shared_operator_budget_refuse(assembly: Any) -> None:
    _, control, _, service, runner = assembly
    service.policy = BehaviorPolicy(max_ticks=1)
    service.begin(directive())
    await tick_run(service, runner)
    with pytest.raises(ValueError, match="budget"):
        service.new_tick()
    service.assist.policy = assist_policy(max_actions=1)
    request = AssistRequest(request_id=str(uuid4()), action=SayAction(kind="say", text="Hello"))
    await runner.wait(await runner.submit(request))
    service.begin(directive())
    with pytest.raises(ValueError, match="budget"):
        await runner.submit_behavior(service.new_tick())
    assert control.commands == ["chat Hello"]


@pytest.mark.parametrize("where", ["bot", "target", "handoff"])
@pytest.mark.parametrize("change", ["freshness", "generation", "deadline"])
async def test_authority_expiring_during_reads_or_final_handoff_sends_nothing(
    assembly: Any, where: str, change: str
) -> None:
    clock, control, target, service, runner = assembly
    target.state = observation(10.0)
    service.begin(directive("follow"))
    old_generation = service.generation

    def invalidate() -> None:
        if change == "freshness":
            clock.now += 3.0
        elif change == "deadline":
            clock.now = service.deadline
        else:
            service.begin(directive())

    async def awaited_invalidation() -> None:
        invalidate()

    if where == "handoff":
        control.handoff = invalidate
    elif where == "bot":
        control.on_read = awaited_invalidation
    else:
        target.on_read = awaited_invalidation
    tick, _ = await tick_run(service, runner)
    result = service.results[tick.request_id]
    assert result.stop_required
    assert result.kind == "refused"
    assert control.commands == []
    if change == "generation":
        assert service.directive is not None
        assert service.directive.kind == "idle"
        assert service.generation > old_generation
        control.on_read = target.on_read = None
        control.handoff = None
        next_tick, _ = await tick_run(service, runner)
        assert service.results[next_tick.request_id].kind == "changed"


@pytest.mark.parametrize(
    "failure", ["dead", "loading", "nan", "dimension", "separation", "error", "bounds", "numeric_paused"]
)
async def test_bad_target_refuses_and_requires_stop(assembly: Any, failure: str) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(10.0)
    if failure == "dead":
        target.state["player"]["health"] = 0.0
    elif failure == "loading":
        target.state["screen"] = "loading"
    elif failure == "nan":
        target.state["player"]["position"][0] = float("nan")
    elif failure == "dimension":
        target.state["dimension"] = "different"
    elif failure == "separation":
        target.state = observation(20.0)
    elif failure == "bounds":
        target.state = observation(33.0)
    elif failure == "numeric_paused":
        target.state["paused"] = 0
    else:
        target.error = True
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    assert service.results[tick.request_id].kind == "refused"
    assert service.results[tick.request_id].stop_required
    assert service.directive is None
    assert control.commands == []


@pytest.mark.parametrize("outcome", ["refused", "client_error", "outcome_unknown"])
async def test_action_noncompletion_disarms_behavior(assembly: Any, outcome: str) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(10.0)
    control.outcome = outcome
    service.begin(directive("follow"))
    tick, _ = await tick_run(service, runner)
    assert service.results[tick.request_id].kind == outcome
    assert service.results[tick.request_id].stop_required
    assert service.directive is None
    with pytest.raises(ValueError, match="authority"):
        service.new_tick()


async def test_final_latest_bot_bounds_and_four_block_segment_rechecked(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(10.0)
    service.begin(directive("follow"))
    # The final callback receives a current snapshot, as the production adapter does.
    original = control.state
    control.handoff = lambda: original.update(observation(-1.0))
    tick, _ = await tick_run(service, runner)
    assert service.results[tick.request_id].kind == "refused"
    assert control.commands == []


async def test_reused_task_or_substituted_tick_identity_refuses(assembly: Any) -> None:
    _, _, _, service, runner = assembly
    task = directive()
    service.begin(task)
    tick = service.new_tick()
    changed = tick.model_copy(update={"sequence": 2})
    with pytest.raises(ValueError, match="identity"):
        await runner.submit_behavior(changed)
    with pytest.raises(ValueError, match="identity"):
        service.begin(task)
    assert service.directive is None
    with pytest.raises(ValueError, match="identity"):
        await runner.submit_behavior(tick)


async def test_follow_requires_finite_short_action_timeout() -> None:
    control = Control()
    service = HorizonBehaviorService(HorizonAssistService(assist_policy(action_timeout_s=2.0), control), Feed())
    with pytest.raises(ValueError, match="one second"):
        service.begin(directive("follow"))
    no_target = HorizonBehaviorService(HorizonAssistService(assist_policy(), control))
    with pytest.raises(ValueError, match="bound target"):
        no_target.begin(directive("follow"))


@pytest.mark.parametrize("boundary", ["policy", "assist_policy", "target"])
async def test_task_binding_substitution_refuses(assembly: Any, boundary: str) -> None:
    _, control, _, service, runner = assembly
    service.begin(directive("follow"))
    tick = service.new_tick()
    if boundary == "policy":
        service.policy = BehaviorPolicy(max_segment=3.0)
    elif boundary == "assist_policy":
        service.assist.policy = assist_policy(max_distance=9.0)
    else:
        service.target = Feed(10.0)
    with pytest.raises(ValueError, match="identity"):
        await runner.submit_behavior(tick)
    assert control.commands == []


async def test_just_outside_deadband_places_horizon_near_radius_at_stop_distance(assembly: Any) -> None:
    _, control, target, service, runner = assembly
    target.state = observation(2.0)
    service.begin(directive("follow"))
    await tick_run(service, runner)
    assert control.commands == ["goto 2 64 0 --near 1.5 --timeout 1"]
    target_distance = float(control.commands[0].split()[1])
    assert target_distance > 1.5
    assert 2.0 - (target_distance - 1.5) == service.policy.deadband


async def test_session_tasks_and_nonfinite_clock_are_bounded(assembly: Any) -> None:
    clock, _, _, service, _ = assembly
    service.policy = BehaviorPolicy(max_tasks=1)
    service.begin(directive())
    clock.now = float("nan")
    with pytest.raises(ValueError, match="authority"):
        service.new_tick()
    clock.now = 100.0
    with pytest.raises(ValueError, match="task budget"):
        service.begin(directive())
    assert service.directive is None


async def test_fenced_tick_has_typed_refusal_before_any_queue_admission(assembly: Any) -> None:
    _, _, _, service, runner = assembly
    service.begin(directive())
    tick = service.new_tick()
    service.fence("cancelled")
    with pytest.raises(BehaviorAdmissionRefused):
        await runner.submit_behavior(tick)
    assert runner.queue.jobs == {}


async def test_substituted_tick_refuses_inside_native_graph_without_runner_bypass(assembly: Any) -> None:
    _, control, _, service, runner = assembly
    service.begin(directive())
    tick = service.new_tick().model_copy(update={"sequence": 2})
    assert runner.services is not None
    handle = await runner.services.run_engine.submit(
        Intent(
            session_id=service.assist.policy.session_id,
            prompt=tick.model_dump_json(),
            source="horizon.idle_tick",
            sigil_name=service.assist.policy.principal,
            sigil_scopes=frozenset({"horizon:assist"}),
        ),
        idempotency_key=f"substituted:{tick.request_id}",
        exclusive_session=True,
    )
    await runner.wait(handle.run_id)
    assert service.results[tick.request_id].kind == "refused"
    assert service.results[tick.request_id].stop_required
    assert control.reads == 0
    assert control.commands == []


async def test_native_paused_observe_retains_real_typed_running_checkpoint(
    assembly: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, control, _, service, runner = assembly
    captured: list[LiveStasisPhylactery] = []

    class CapturedLive(LiveStasisPhylactery):
        def __init__(self, *, job_id: str) -> None:
            super().__init__(job_id=job_id)
            captured.append(self)

    monkeypatch.setattr(runs, "LiveStasisPhylactery", CapturedLive)
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause() -> None:
        entered.set()
        await release.wait()

    control.on_read = pause
    service.begin(directive())
    tick = service.new_tick()
    run_id = await runner.submit_behavior(tick)
    await asyncio.wait_for(entered.wait(), timeout=1.0)
    assert len(captured) == 1
    snapshots = await captured[0].load_all()
    assert [snapshot.status for snapshot in snapshots if isinstance(snapshot, NodeSnapshot)] == ["success", "running"]
    latest = snapshots[-1]
    assert isinstance(latest, NodeSnapshot)
    assert latest.node.get_node_id() == "ObserveIdle"
    assert latest.state.tick == tick
    assert latest.state.run_id == run_id
    release.set()
    await runner.wait(run_id)
    assert service.results[tick.request_id].kind == "changed"
