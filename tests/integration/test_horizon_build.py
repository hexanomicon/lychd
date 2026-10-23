"""Real native Run/Graph with source-derived fake observations, no live I/O."""

from __future__ import annotations

import asyncio
import copy
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
    ReadAction,
)
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.compositions.blockworld.horizon_build import (
    BuildPlan,
    BuildState,
    BuildStep,
    HorizonBuildService,
    decode_plan,
    decode_step,
)
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import LiveStasisPhylactery, NodeSnapshot
from lychd.ghouls import runs

pytestmark = pytest.mark.asyncio


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def inventory(count: int = 3) -> dict[str, Any]:
    held = {"item": "minecraft:oak_planks", "count": count} if count else None
    return {
        "selected": 1,
        "held": held,
        "hotbar": [{"slot": i, **held} if i == 0 and held else {"slot": i, "item": None} for i in range(9)],
        "main": [{"slot": i, "item": None} for i in range(9, 36)],
        "armor": [
            {"slot": 500 + i, "item": None, "part": name} for i, name in enumerate(("head", "chest", "legs", "feet"))
        ],
        "offhand": {"slot": 504, "item": None},
        "carried": None,
        "counts": {"minecraft:oak_planks": count} if count else {},
    }


def block(cell: tuple[int, int, int], material: str) -> dict[str, Any]:
    return {"pos": list(cell), "block": material, "state": material, "loaded": True}


class Control:
    def __init__(self) -> None:
        self.bag = inventory()
        self.state: dict[str, Any] = {
            "world": "Test",
            "dimension": "minecraft:overworld",
            "gamemode": "survival",
            "screen": "playing",
            "paused": False,
            "busy": None,
            "sleeping": None,
            "using": None,
            "player": {"position": [0.0, 64.0, 0.0], "eye": [0.0, 65.62, 0.0], "health": 20.0},
            "selected": 1,
            "held": copy.deepcopy(self.bag["held"]),
        }
        self.cells: dict[tuple[int, int, int], dict[str, Any]] = {}
        self.commands: list[str] = []
        self.reads = 0
        self.handoff: Callable[[], None] | None = None
        self.on_read: Callable[[], Awaitable[None]] | None = None
        self.outcome = "client_observed"
        self.post_material = "minecraft:oak_planks"
        self.consume = 1
        self.unexpected_delta = False
        self.lost = False
        self.wait_action = False
        self.issued = asyncio.Event()
        self.release = asyncio.Event()
        self.fenced: set[str] = set()

    async def observe(self) -> dict[str, Any]:
        self.reads += 1
        if self.on_read:
            await self.on_read()
        return copy.deepcopy(self.state)

    async def inspect_inventory(self) -> dict[str, Any]:
        self.reads += 1
        return copy.deepcopy(self.bag)

    async def inspect_cell(self, x: int, y: int, z: int) -> dict[str, Any]:
        self.reads += 1
        cell = (x, y, z)
        return copy.deepcopy(self.cells.get(cell, block(cell, "minecraft:stone" if y == 63 else "minecraft:air")))

    async def invoke(
        self, run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> AssistResult:
        assert not query
        if self.handoff:
            self.handoff()
        if authorize:
            try:
                authorize(copy.deepcopy(self.state))
            except ValueError:
                return AssistResult(request_id=run_id, kind="refused", detail="No bytes sent.")
        self.commands.append(line)
        _, x, y, z = line.split()
        cell = (int(x), int(y), int(z))
        self.cells[cell] = block(cell, self.post_material)
        held = self.bag["held"]
        self.bag = inventory(held["count"] - self.consume)
        if self.unexpected_delta:
            self.bag["counts"]["minecraft:dirt"] = 1
        self.state["held"] = copy.deepcopy(self.bag["held"])
        self.issued.set()
        if self.wait_action:
            await self.release.wait()
        if self.lost:
            msg = "Lost after possible placement."
            raise OSError(msg)
        return AssistResult.model_validate(
            {"request_id": run_id, "kind": self.outcome, "detail": "Client only.", "observation": {"ok": True}}
        )

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
        self.release.set()

    async def contain_all(self) -> None:
        self.release.set()

    async def aclose(self) -> None:
        self.release.set()


def policy(**changes: Any) -> AssistPolicy:
    return AssistPolicy.model_validate(
        {
            "session_id": "build-test",
            "principal": "operator",
            "expires_at": datetime.now(UTC) + timedelta(minutes=2),
            "min_x": -8.0,
            "max_x": 8.0,
            "min_y": 60.0,
            "max_y": 70.0,
            "min_z": -8.0,
            "max_z": 8.0,
            "max_actions": 10,
            "permitted": ("state", "place"),
            **changes,
        }
    )


def plan(cells: tuple[tuple[int, int, int], ...] = ((1, 64, 0),), **changes: Any) -> BuildPlan:
    return BuildPlan.model_validate(
        {
            "plan_id": str(uuid4()),
            "session_id": "build-test",
            "world": "Test",
            "dimension": "minecraft:overworld",
            "mode": "survival",
            "cells": cells,
            "plot_min": (-8, 60, -8),
            "plot_max": (8, 70, 8),
            "expires_at": datetime.now(UTC) + timedelta(seconds=55),
            "max_placements": len(cells),
            "max_reads": 8 * len(cells),
            **changes,
        }
    )


@pytest_asyncio.fixture
async def assembly() -> AsyncIterator[tuple[Clock, Control, HorizonBuildService, LocalAssistRunner]]:
    clock, control = Clock(), Control()
    assist = HorizonAssistService(policy(), control)
    service = HorizonBuildService(assist, control, clock=clock)
    runner = LocalAssistRunner(assist, control, builds=service)
    await runner.open()
    try:
        yield clock, control, service, runner
    finally:
        await runner.aclose()


async def step_run(service: HorizonBuildService, runner: LocalAssistRunner) -> tuple[BuildStep, str]:
    step = service.new_step()
    run_id = await runner.submit_build(step)
    await runner.wait(run_id)
    return step, run_id


async def test_strict_plan_bytes_digest_immutability_and_bounds() -> None:
    original = plan()
    assert BuildPlan.model_validate_json(original.model_dump_json()).digest == original.digest
    assert len(original.digest) == 64
    assert original.model_copy(update={"world": "Other"}).digest != original.digest
    with pytest.raises(ValidationError):
        original.mode = "creative"
    invalid_changes: tuple[dict[str, Any], ...] = (
        {"cells": ((True, 64, 0),)},
        {"cells": ((1.5, 64, 0),)},
        {"cells": ((2**31, 64, 0),)},
        {"cells": ((1, 64, 0), (1, 64, 0), (2, 64, 0)), "max_placements": 3, "max_reads": 24},
        {"plot_min": (2, 60, -8)},
        {"plot_min": (-8, 64, -8)},
        {"duration_s": 61.0},
        {"max_reads": 25},
        {"max_placements": 2},
        {"material": "minecraft:dirt"},
    )
    for changes in invalid_changes:
        with pytest.raises(ValidationError):
            plan(**changes)


async def test_one_cell_native_manifest_events_and_inert_normal_boot(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.begin(plan())
    step, run_id = await step_run(service, runner)
    result = service.results[step.request_id]
    assert result.kind == "placed"
    assert service.cursor == 1
    assert result.read_count == 8
    assert result.action_count == 1
    assert service.assist.used == 1
    assert control.commands == ["place 1 64 0"]
    assert service.run_results[run_id] == result
    before_report = (service.cursor, len(service.records), dict(service.results))
    repeated = BuildState(run_id=run_id, session_id=service.assist.policy.session_id, prompt=step.model_dump_json())
    assert service.report(repeated) == result
    assert (service.cursor, len(service.records), service.results) == before_report
    assert runner.services is not None
    run = await runner.services.ledger.get(run_id)
    assert run.status is RunStatus.DONE
    assert run.pattern_manifest["key"] == "blockworld.horizon_build_step"
    assert run.pattern_manifest["revision"] == "1"
    events = await runner.services.ledger.list_events(run_id)
    assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
        "validate",
        "read_preflight",
        "decide",
        "place",
        "read_postflight",
        "report",
    ]
    assert any(event.kind == "log" and '"kind": "placed"' in event.data for event in events)
    assert not any("horizon" in workflow.name for workflow in builtin_workflow_registry().all())
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.new_step()


async def test_three_cells_are_three_fresh_runs_exactly_three_effects(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.begin(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    identities = [await step_run(service, runner) for _ in range(3)]
    assert len({run_id for _, run_id in identities}) == 3
    assert control.commands == ["place 1 64 0", "place 2 64 0", "place 3 64 0"]
    assert service.cursor == service.assist.used == service.action_count == 3
    assert service.read_count == 24
    assert all(service.results[step.request_id].kind == "placed" for step, _ in identities)


@pytest.mark.parametrize(
    "case",
    [
        "occupied",
        "unloaded",
        "support",
        "reach",
        "mode",
        "world",
        "dimension",
        "screen",
        "paused",
        "busy",
        "health",
        "missing",
        "components",
        "selection",
        "offhand",
        "carried",
        "insufficient",
    ],
)
async def test_preflight_refuses_observed_changes_without_effect(assembly: Any, case: str) -> None:  # noqa: C901 - explicit negative fixture mutations
    _, control, service, runner = assembly
    admitted = plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))) if case == "insufficient" else plan()
    if case in {"occupied", "unloaded", "support"}:
        cell = (1, 63, 0) if case == "support" else (1, 64, 0)
        control.cells[cell] = block(cell, "minecraft:dirt" if case != "unloaded" else "minecraft:air")
        if case == "unloaded":
            control.cells[cell]["loaded"] = False
    elif case == "reach":
        control.state["player"]["eye"] = [10.0, 65.62, 0.0]
    elif case in {"mode", "world", "dimension", "screen", "paused", "busy"}:
        key = "gamemode" if case == "mode" else case
        control.state[key] = {
            "mode": "creative",
            "world": "Other",
            "dimension": "minecraft:the_nether",
            "screen": "inventory",
            "paused": True,
            "busy": "goto",
        }[case]
    elif case == "health":
        control.state["player"]["health"] = 0
    elif case == "missing":
        control.bag["held"] = None
    elif case == "components":
        control.bag["held"]["components"] = "{}"
    elif case == "selection":
        control.bag["selected"] = 2
    elif case == "offhand":
        control.bag["offhand"] = {"slot": 504, "item": "minecraft:torch", "count": 1}
    elif case == "carried":
        control.bag["carried"] = {"item": "minecraft:dirt", "count": 1}
    else:
        control.bag = inventory(2)
        control.state["held"] = copy.deepcopy(control.bag["held"])
    service.begin(admitted)
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "refused"
    assert service.cursor == service.assist.used == 0
    assert not control.commands
    assert service.plan is None


@pytest.mark.parametrize("case", ["pose", "held", "expiry", "policy", "generation", "freshness", "budget"])
async def test_final_sync_guard_refuses_before_physical_send(assembly: Any, case: str) -> None:
    clock, control, service, runner = assembly
    service.begin(plan())

    def change() -> None:
        if case == "pose":
            control.state["player"]["eye"] = [9.0, 65.62, 0.0]
        elif case == "held":
            control.state["held"] = {"item": "minecraft:dirt", "count": 3}
        elif case == "policy":
            service.assist.policy = service.assist.policy.model_copy(update={"principal": "other"})
        elif case == "generation":
            service.fence("operator replacement")
        elif case == "budget":
            service.assist.used = service.assist.policy.max_actions
        else:
            clock.now += 60 if case == "expiry" else 1

    control.handoff = change
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "refused"
    assert not control.commands
    assert service.assist.used == (service.assist.policy.max_actions if case == "budget" else 0)
    assert service.cursor == 0
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.new_step()


@pytest.mark.parametrize("case", ["material", "delta", "other_inventory", "client_error", "lost"])
async def test_postflight_failures_stop_without_advance_or_second_attempt(assembly: Any, case: str) -> None:
    _, control, service, runner = assembly
    service.begin(plan())
    if case == "material":
        control.post_material = "minecraft:dirt"
    elif case == "delta":
        control.consume = 0
    elif case == "other_inventory":
        control.unexpected_delta = True
    elif case == "client_error":
        control.outcome = "client_error"
    else:
        control.lost = True
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == ("client_error" if case == "client_error" else "outcome_unknown")
    assert service.cursor == 0
    assert len(control.commands) == service.assist.used == 1
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        await runner.submit_build(step)
    assert len(control.commands) == 1


async def test_explicit_creative_zero_consumption_and_empty_remote_label(assembly: Any) -> None:
    _, control, service, runner = assembly
    control.state["gamemode"] = "creative"
    control.state["world"] = ""
    control.consume = 0
    service.begin(plan(mode="creative", world=""))
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "placed"


async def test_plan_identity_shared_budget_and_policy_requirements(assembly: Any) -> None:
    _, _, service, runner = assembly
    original = plan()
    service.begin(original)
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.begin(original)
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.begin(original.model_copy(update={"world": "Other"}))
    step = service.new_step()
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.new_step()
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        await runner.submit_build(step.model_copy(update={"cell": (2, 64, 0)}))
    service.assist.used = service.assist.policy.max_actions
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        await runner.submit_build(step)
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.begin(plan())
    service.assist.used = 0
    service.assist.policy = service.assist.policy.model_copy(update={"permitted": ("place",)})
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.begin(plan())
    service.assist.policy = service.assist.policy.model_copy(update={"permitted": ("state",)})
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.begin(plan())


async def test_operator_action_and_build_share_last_budget_slot(assembly: Any) -> None:
    _, _, service, runner = assembly
    service.assist.policy = service.assist.policy.model_copy(update={"max_actions": 1})
    service.begin(plan())
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "placed"
    assert service.assist.used == 1
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        service.assist.validate(
            AssistRequest(request_id=str(uuid4()), action=ReadAction(kind="state")),
            Sigil(name="operator", scopes=frozenset({"horizon:assist"})),
        )


async def test_foreign_run_cannot_replay_or_overwrite_original_result(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.begin(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    step, first_run = await step_run(service, runner)
    original = service.results[step.request_id]
    next_step = service.new_step()
    reads = control.reads
    assert runner.services is not None
    second = await runner.services.run_engine.submit(
        Intent(
            session_id=service.assist.policy.session_id,
            prompt=step.model_dump_json(),
            source="horizon.build_step",
            sigil_name="operator",
            sigil_scopes=frozenset({"horizon:assist"}),
        ),
        idempotency_key="forced-foreign-run",
        exclusive_session=True,
    )
    await runner.wait(second.run_id)
    assert first_run != second.run_id
    assert service.run_results[second.run_id].kind == "refused"
    assert service.results[step.request_id] == service.run_results[first_run] == original
    assert service.cursor == 1
    assert service.plan is not None
    assert control.reads == reads
    assert len(control.commands) == 1
    next_run = await runner.submit_build(next_step)
    await runner.wait(next_run)
    assert service.cursor == 2


async def test_cancel_after_click_is_unknown_and_never_advances(assembly: Any) -> None:
    _, control, service, runner = assembly
    control.wait_action = True
    service.begin(plan())
    step = service.new_step()
    run_id = await runner.submit_build(step)
    await asyncio.wait_for(control.issued.wait(), 2)
    await runner.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner.wait(run_id)
    assert service.results[step.request_id].kind == "outcome_unknown"
    assert service.cursor == 0
    assert len(control.commands) == 1
    assert service.plan is None
    with pytest.raises(ValueError, match=r"(?i)(identity|budget|session|plan|cell|step)"):
        await runner.submit_build(step)


async def test_real_native_running_checkpoint_retains_exact_step(
    assembly: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, control, service, runner = assembly
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
    service.begin(plan())
    step = service.new_step()
    run_id = await runner.submit_build(step)
    await asyncio.wait_for(entered.wait(), 2)
    snapshots = await captured[0].load_all()
    assert [snap.status for snap in snapshots if isinstance(snap, NodeSnapshot)] == ["success", "running"]
    latest = snapshots[-1]
    assert isinstance(latest, NodeSnapshot)
    assert latest.node.get_node_id() == "ReadBuildPreflight"
    assert latest.state.step == step
    assert latest.state.run_id == run_id
    release.set()
    await runner.wait(run_id)
    assert service.results[step.request_id].kind == "placed"


async def test_stale_run_refusal_cannot_fence_successor_generation(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.begin(plan())
    successor = plan(cells=((2, 64, 0),))

    def replace() -> None:
        service.begin(successor)

    control.handoff = replace
    step, first_run = await step_run(service, runner)
    assert service.run_results[first_run].kind == "refused"
    assert service.results[step.request_id].kind == "refused"
    assert service.plan == successor
    assert service.generation > step.generation
    assert not control.commands
    control.handoff = None
    next_step, _ = await step_run(service, runner)
    assert service.results[next_step.request_id].kind == "placed"
    assert control.commands == ["place 2 64 0"]


async def test_postflight_cancellation_retains_unknown_and_stops_plan(assembly: Any) -> None:
    _, control, service, runner = assembly
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause_post() -> None:
        if control.commands:
            entered.set()
            await release.wait()

    control.on_read = pause_post
    service.begin(plan())
    step = service.new_step()
    run_id = await runner.submit_build(step)
    await asyncio.wait_for(entered.wait(), 2)
    await runner.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner.wait(run_id)
    assert service.run_results[run_id].kind == "outcome_unknown"
    assert service.results[step.request_id].kind == "outcome_unknown"
    assert service.plan is None
    assert service.cursor == 0
    assert len(control.commands) == 1


async def test_final_postflight_slot_consumption_leaves_empty_held(assembly: Any) -> None:
    _, control, service, runner = assembly
    control.bag = inventory(1)
    control.state["held"] = copy.deepcopy(control.bag["held"])
    service.begin(plan())
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "placed"
    assert control.bag["held"] is None


async def test_duplicate_json_and_nonfinite_build_wire_refuse() -> None:
    original = plan()
    assert decode_plan(original.model_dump_json()) == original
    for document in (
        original.model_dump_json()[:-1] + ',"world":"Other"}',
        original.model_dump_json().replace('"duration_s":60.0', '"duration_s":NaN'),
    ):
        with pytest.raises(ValueError, match=r"Duplicate|Non-finite"):
            decode_plan(document)
    with pytest.raises(ValueError, match="Duplicate"):
        decode_step('{"request_id":"a","request_id":"b"}')


async def test_replacing_shared_assist_cannot_reset_build_budget(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.begin(plan())
    step = service.new_step()
    service.assist = HorizonAssistService(service.assist.policy, control)
    with pytest.raises(ValueError, match="Plan bytes"):
        await runner.submit_build(step)
    assert not control.commands


async def test_shared_bounds_and_expiry_are_not_expanded_by_plan(assembly: Any) -> None:
    _, _, service, _ = assembly
    invalid_changes: tuple[dict[str, Any], ...] = (
        {"plot_max": (9, 70, 8)},
        {"expires_at": service.assist.policy.expires_at + timedelta(seconds=1)},
        {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
        {"session_id": "another-session"},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError, match="Plan identity"):
            service.begin(plan(**changes))


async def test_shared_distance_also_limits_placement_without_spending_action(assembly: Any) -> None:
    _, control, service, runner = assembly
    service.assist.policy = service.assist.policy.model_copy(update={"max_distance": 0.25})
    service.begin(plan())
    step, _ = await step_run(service, runner)
    assert service.results[step.request_id].kind == "refused"
    assert not control.commands
    assert service.assist.used == service.cursor == 0
