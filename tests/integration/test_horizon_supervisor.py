"""Native Runs and real fake-game sockets under the finite process-local arbiter."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from lychd.compositions.blockworld.horizon_assist import AssistRequest, HorizonAssistService, parse_text
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.compositions.blockworld.horizon_behaviors import BehaviorDirective, BehaviorPolicy, HorizonBehaviorService
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services import horizon_control, horizon_observer
from lychd.system.services import horizon_supervisor as supervisor_module
from lychd.system.services.horizon_control import HorizonControlError, HorizonControlSession
from lychd.system.services.horizon_observer import HorizonTargetObserver
from lychd.system.services.horizon_supervisor import HorizonSupervisor, SupervisorResult
from tests.integration.test_horizon_assist import FakeGame, policy

pytestmark = pytest.mark.asyncio


class Target:
    async def observe(self) -> dict[str, Any]:
        return {
            "world": "Test",
            "dimension": "minecraft:overworld",
            "screen": "playing",
            "paused": False,
            "player": {"position": [7.0, 64.0, 0.0], "health": 20},
        }


class CompletionGame(FakeGame):
    """Opt-in client success without displacement; ordinary cancellation fixture otherwise."""

    complete_follow = False

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        line = await reader.readline()
        if self.complete_follow and line.startswith(b"goto "):
            self.commands.append(line.decode().strip())
            self.issued.set()
            writer.write(b'{"ok":true}\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        replay = asyncio.StreamReader()
        replay.feed_data(line)
        replay.feed_eof()
        await super().handle(replay, writer)


class HeldTarget(FakeGame):
    """Hold one selected query while the native Run loses follow authority."""

    def __init__(self, endpoint: Path) -> None:
        super().__init__(endpoint)
        self.hold_command: bytes | None = None
        self.held = asyncio.Event()
        self.release_read = asyncio.Event()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        self.connections.add(task)
        try:
            line = await reader.readline()
            if line == self.hold_command:
                self.hold_command = None
                self.held.set()
                await self.release_read.wait()
            replay = asyncio.StreamReader()
            replay.feed_data(line)
            replay.feed_eof()
            await super().handle(replay, writer)
        finally:
            self.connections.discard(task)


@dataclass
class Lab:
    game: CompletionGame
    control: HorizonControlSession
    behaviors: HorizonBehaviorService
    runner: LocalAssistRunner
    supervisor: HorizonSupervisor
    records: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    unknown_expected: bool = False


@pytest_asyncio.fixture
async def lab(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Lab]:
    with TemporaryDirectory(prefix="lhs-") as directory:
        root = Path(directory)
        monkeypatch.setattr(horizon_control, "_ownership_root", lambda: root / "ownership")
        game = CompletionGame(root / "game.sock")
        server = await asyncio.start_unix_server(game.handle, path=game.endpoint)
        control = HorizonControlSession(game.binding())
        assist = HorizonAssistService(policy().model_copy(update={"action_timeout_s": 0.25}), control)
        behaviors = HorizonBehaviorService(assist, Target())
        runner = LocalAssistRunner(assist, control, behaviors=behaviors)
        records: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        supervisor = HorizonSupervisor(runner, control, behaviors=behaviors, record=records.put)
        instance = Lab(game, control, behaviors, runner, supervisor, records)
        await control.open()
        await runner.open()
        try:
            yield instance
        finally:
            errors: list[Exception] = []
            for close in (supervisor.stop, runner.aclose):
                try:
                    await close()
                except Exception as exc:  # noqa: BLE001 - assert cleanup failures explicitly below
                    errors.append(exc)
            server.close()
            await server.wait_closed()
            for task in tuple(game.connections):
                task.cancel()
            await asyncio.gather(*game.connections, return_exceptions=True)
            if instance.unknown_expected:
                assert errors
                assert any(isinstance(error, HorizonControlError) for error in errors)
                records_on_disk = [json.loads(path.read_bytes()) for path in (root / "ownership").glob("*.json")]
                assert any(record["state"] == "unknown" for record in records_on_disk)
            elif errors:
                msg = "Unexpected controller cleanup failure"
                raise ExceptionGroup(msg, errors)
            assert all(job.task is not None and job.task.done() for job in runner.queue.jobs.values())


def directive(kind: str = "idle", seconds: float = 5.0) -> BehaviorDirective:
    return BehaviorDirective.model_validate({"kind": kind, "task_id": str(uuid4()), "duration_s": seconds})


def request(text: str = "state") -> AssistRequest:
    return AssistRequest(request_id=str(uuid4()), action=parse_text(text))


async def test_idle_native_events_zero_effects_and_no_catchup(lab: Lab) -> None:
    lab.behaviors.clock = lambda: 100.0
    await lab.supervisor.start(directive())
    record = await asyncio.wait_for(lab.records.get(), timeout=2)
    assert record["kind"] == "changed"
    assert record["model_calls"] == record["action_attempts"] == 0
    assert record["observation_calls"] == 1
    assert record["elapsed_s"] >= 0
    assert record["process_cpu_s"] >= 0
    # Publication can wake its reader before the current tick has returned.
    # Joining that tick must not admit another Run; the following call is a
    # deterministic cadence refusal under the unchanged monotonic test clock.
    await lab.supervisor.tick_once()
    assert len(lab.runner.queue.jobs) == 1
    assert (await lab.supervisor.tick_once()).kind == "skipped"
    assert set(lab.game.commands) <= {"state", "status"}
    assert lab.runner.services is not None
    events = await lab.runner.services.ledger.list_events(record["run_id"])
    assert any(event.kind == "node" and event.data == "observe" for event in events)


async def test_client_success_without_progress_stops_follow_before_successor(lab: Lab) -> None:
    lab.game.complete_follow = True
    await lab.supervisor.start(directive("follow"))
    record = await asyncio.wait_for(lab.records.get(), timeout=2)
    assert record["kind"] == "no_progress"
    assert record["model_calls"] == 0
    assert record["observation_calls"] == 3
    assert record["action_attempts"] == 1
    assert lab.behaviors.directive is None
    await lab.supervisor.tick_once()
    assert (await lab.supervisor.tick_once()).kind == "skipped"
    assert len(lab.runner.queue.jobs) == 1
    assert sum(command.startswith("goto ") for command in lab.game.commands) == 1
    result = next(iter(lab.behaviors.results.values()))
    assert result.kind == "no_progress"
    assert result.action_result is not None
    assert result.action_result.kind == "client_observed"
    assert not lab.supervisor.stopped.is_set()
    assert (await lab.supervisor.submit_operator(request())).kind == "client_observed"


async def test_cpu_and_elapsed_metrics_keep_independent_clock_measurements(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Process CPU includes all threads and need not be <= wall time. Separate
    # clock reads also need not end at the same instant; never clamp evidence.
    monkeypatch.setattr(supervisor_module, "time", SimpleNamespace(monotonic=lambda: 50.5, process_time=lambda: 20.75))
    # Directly inspect the metric sink without changing production visibility.
    await lab.supervisor._publish(  # pyright: ignore[reportPrivateUsage]
        SupervisorResult(None, "skipped", "No effect."), "idle", 50.0, 20.0
    )
    record = lab.records.get_nowait()
    assert record["elapsed_s"] == 0.5
    assert record["process_cpu_s"] == 0.75


async def test_tick_burst_coalesces_while_read_waits_and_stop_joins_every_task(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = asyncio.Event()
    original = lab.control.observe

    async def blocked() -> dict[str, Any]:
        entered.set()
        await asyncio.Event().wait()
        return await original()

    monkeypatch.setattr(lab.control, "observe", blocked)
    await lab.supervisor.start(directive())
    await asyncio.wait_for(entered.wait(), timeout=2)
    burst = [asyncio.create_task(lab.supervisor.tick_once()) for _ in range(12)]
    await asyncio.sleep(0)
    assert lab.supervisor.metrics["coalesced"] == 12
    assert len(lab.runner.queue.jobs) == 1
    await lab.supervisor.stop()
    await asyncio.gather(*burst, return_exceptions=True)
    assert all(task.done() for task in burst)
    assert not any(command.startswith("goto") for command in lab.game.commands)
    assert not [task for task in asyncio.all_tasks() if task.get_name().startswith("horizon-supervisor-admission")]
    with pytest.raises(ValueError, match="stopped"):
        await lab.supervisor.start(directive())


@pytest.mark.parametrize("after_enqueue", [False, True])
async def test_operator_priority_during_admission_gap_never_sends_old_generation(
    lab: Lab, monkeypatch: pytest.MonkeyPatch, *, after_enqueue: bool
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    original = lab.runner.submit_behavior

    async def delayed(tick: Any) -> str:
        run_id = await original(tick) if after_enqueue else None
        entered.set()
        await release.wait()
        return run_id if run_id is not None else await original(tick)

    monkeypatch.setattr(lab.runner, "submit_behavior", delayed)
    await lab.supervisor.start(directive("follow"))
    await asyncio.wait_for(entered.wait(), timeout=2)
    operator = asyncio.create_task(lab.supervisor.submit_operator(request()))
    await asyncio.sleep(0)
    release.set()
    result = await asyncio.wait_for(operator, timeout=2)
    assert result.kind == "client_observed"
    assert not any(command.startswith("goto") for command in lab.game.commands)
    assert lab.behaviors.directive is None
    assert not lab.supervisor.stopped.is_set()


async def test_freshness_deadline_independently_stops_waiting_game_action(lab: Lab) -> None:
    lab.behaviors.policy = BehaviorPolicy(freshness_s=0.3)
    await lab.supervisor.start(directive("follow"))
    await asyncio.wait_for(lab.game.issued.wait(), timeout=2)
    record = await asyncio.wait_for(lab.records.get(), timeout=2)
    assert record["kind"] == "expired"
    assert lab.game.stops >= 1
    assert not lab.game.active
    assert sum(command.startswith("goto ") for command in lab.game.commands) == 1
    assert lab.behaviors.directive is None
    assert not lab.supervisor.stopped.is_set()
    assert (await lab.supervisor.submit_operator(request())).kind == "client_observed"


async def test_operator_waits_for_stop_containment_before_next_effect(lab: Lab) -> None:
    lab.game.delay_action = True
    await lab.supervisor.start(directive("follow"))
    await asyncio.wait_for(lab.game.issued.wait(), timeout=2)
    result = await asyncio.wait_for(lab.supervisor.submit_operator(request("say Ahoj")), timeout=2)
    assert result.kind == "client_observed"
    assert lab.game.stops >= 2
    assert not lab.game.active
    assert lab.game.commands.index("chat Ahoj") > max(
        index for index, command in enumerate(lab.game.commands) if command == "stop"
    )


async def test_stop_during_operator_admission_gap_fences_future_run(lab: Lab, monkeypatch: pytest.MonkeyPatch) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    original = lab.runner.submit

    async def delayed(command: AssistRequest) -> str:
        entered.set()
        await release.wait()
        return await original(command)

    monkeypatch.setattr(lab.runner, "submit", delayed)
    operation = asyncio.create_task(lab.supervisor.submit_operator(request("say hello")))
    await entered.wait()
    stopping = asyncio.create_task(lab.supervisor.stop())
    await asyncio.sleep(0)
    release.set()
    await asyncio.wait_for(stopping, timeout=2)
    assert operation.cancelled()
    assert "chat hello" not in lab.game.commands
    with pytest.raises(ValueError, match="stopped"):
        await lab.supervisor.submit_operator(request())


async def test_terminal_unknown_run_still_gets_explicit_containment_and_disarms(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab.unknown_expected = True
    lab.game.disconnect = True
    contained: list[str] = []
    original = lab.control.contain

    async def observed(run_id: str) -> None:
        contained.append(run_id)
        await original(run_id)

    monkeypatch.setattr(lab.control, "contain", observed)
    command = request("goto 1 64 0")
    with pytest.raises(HorizonControlError):
        await lab.supervisor.submit_operator(command)
    run_id = lab.supervisor.run_ids[command.request_id]
    assert run_id in contained
    assert lab.runner.active_run is None
    assert lab.runner.services is not None
    native = await lab.runner.services.ledger.get(run_id)
    assert native is not None
    assert native.status == RunStatus.DONE
    assert lab.supervisor.stopped.is_set()
    with pytest.raises(ValueError, match="stopped"):
        await lab.supervisor.submit_operator(request("say successor"))
    assert "chat successor" not in lab.game.commands


async def test_additional_operator_admissions_explicitly_refuse(lab: Lab) -> None:
    first = asyncio.create_task(lab.supervisor.submit_operator(request("goto 1 64 0")))
    await lab.game.issued.wait()
    with pytest.raises(ValueError, match="reserved"):
        await lab.supervisor.submit_operator(request("say raced"))
    with pytest.raises(ValueError, match="reserved"):
        await lab.supervisor.start(directive())
    await lab.supervisor.stop()
    assert first.cancelled()
    assert "chat raced" not in lab.game.commands


@pytest.mark.parametrize("instruction", ["goto 100 64 0", "goto 8 70 8"])
async def test_native_policy_refusal_remains_known_and_allows_a_valid_successor(lab: Lab, instruction: str) -> None:
    command = request(instruction)
    result = await lab.supervisor.submit_operator(command)
    assert result.kind == "refused"
    assert result.run_id is not None
    assert lab.runner.assist.run_results[result.run_id].request_id == command.request_id
    assert not lab.supervisor.stopped.is_set()
    assert not any(line.startswith("goto") for line in lab.game.commands)
    assert (await lab.supervisor.submit_operator(request())).kind == "client_observed"


async def test_operator_replacement_during_evidence_wait_preserves_known_outcome(lab: Lab) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(record: dict[str, Any]) -> None:
        if record["source"] == "idle":
            entered.set()
            await release.wait()
        await lab.records.put(record)

    lab.supervisor.record = delayed
    await lab.supervisor.start(directive())
    await asyncio.wait_for(entered.wait(), timeout=2)
    operator = asyncio.create_task(lab.supervisor.submit_operator(request()))
    await asyncio.sleep(0)
    release.set()
    assert (await asyncio.wait_for(operator, timeout=2)).kind == "client_observed"
    assert not lab.supervisor.stopped.is_set()
    assert (await lab.records.get())["source"] == "idle"
    assert lab.game.commands.count("state") >= 2


@pytest_asyncio.fixture
async def attached_target(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[HeldTarget, HorizonTargetObserver]]:
    with TemporaryDirectory(prefix="owned-feed-native-") as directory:
        person = HeldTarget(Path(directory) / "person.sock")
        person.positions = [[0.5, 64.0, 0.0]]
        person.status_reply = {
            "server": {"address": "127.0.0.1:25565", "name": "Target", "joined": True, "loaded": True}
        }
        server = await asyncio.start_unix_server(person.handle, path=person.endpoint)
        person.endpoint.chmod(0o600)
        bot = replace(lab.control.binding, pid=os.getpid() + 1, start_ticks=lab.control.binding.start_ticks + 1)
        original_start = horizon_observer._process_start  # pyright: ignore[reportPrivateUsage]

        def process_start(pid: int) -> int:
            return bot.start_ticks if pid == bot.pid else original_start(pid)

        monkeypatch.setattr(horizon_observer, "_process_start", process_start)
        observer = HorizonTargetObserver(
            replace(person.binding(), client_name="Target"), bot_binding=bot, settle_cancelled_reads=True
        )
        try:
            await observer.open()
            lab.behaviors.target = observer
            yield person, observer
        finally:
            person.release_read.set()
            await lab.supervisor.pause()
            await observer.aclose()
            server.close()
            await server.wait_closed()
            tasks = tuple(person.connections)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.parametrize("command", [b"state\n", b"status\n"])
@pytest.mark.parametrize("expiry", [False, True])
async def test_owned_target_read_settles_after_authority_ends_and_same_feed_serves_fresh_follow(
    lab: Lab, attached_target: tuple[HeldTarget, HorizonTargetObserver], command: bytes, *, expiry: bool
) -> None:
    person, observer = attached_target
    person.hold_command = command
    await lab.supervisor.start(directive("follow", seconds=0.2 if expiry else 5))
    await asyncio.wait_for(person.held.wait(), timeout=2)
    paused = None if expiry else asyncio.create_task(lab.supervisor.pause())
    if expiry:
        await asyncio.sleep(0.22)
        assert lab.behaviors.clock() >= lab.behaviors.deadline
    else:
        await asyncio.sleep(0)
        assert lab.behaviors.directive is None
        assert paused is not None
        assert not paused.done()
    assert lab.records.empty()
    assert not any(line.startswith("goto ") for line in lab.game.commands)
    person.release_read.set()
    if paused is not None:
        await asyncio.wait_for(paused, timeout=2)
    record = await asyncio.wait_for(lab.records.get(), timeout=2)
    assert record["kind"] == ("expired" if expiry else "cancelled")
    assert record["action_attempts"] == 0
    assert all(job.task is not None and job.task.done() for job in lab.runner.queue.jobs.values())
    assert not [task for task in asyncio.all_tasks() if task.get_name() == "horizon-target-observation"]
    await lab.supervisor.start(directive("follow"))
    fresh = await asyncio.wait_for(lab.records.get(), timeout=2)
    assert fresh["kind"] == "unchanged"
    assert fresh["run_id"] != record["run_id"]
    assert fresh["action_attempts"] == 0
    assert lab.behaviors.target is observer
    assert person.commands == ["state", "status"] * 3
    assert not any(line.startswith("goto ") for line in lab.game.commands)
