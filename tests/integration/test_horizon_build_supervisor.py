"""Native build supervision through a real synthetic-game Unix socket."""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from scripts.blockworld_voice import VoiceSession
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.horizon_assist import AssistRequest, HorizonAssistService, SayAction
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.compositions.blockworld.horizon_build import HorizonBuildService
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services import horizon_control
from lychd.system.services.horizon_control import HorizonBinding, HorizonControlError, HorizonControlSession
from lychd.system.services.horizon_supervisor import HorizonSupervisor
from tests.integration.test_horizon_assist import FakeGame
from tests.integration.test_horizon_build import block, inventory, plan, policy
from tests.unit.cli.test_blockworld_voice import speech, wav

pytestmark = pytest.mark.asyncio
_CHECKOUT = Path(__file__).resolve().parents[2]


class BuildingGame(FakeGame):
    """Source-shaped observations with real transport and observable partial effects."""

    def __init__(self, endpoint: Path) -> None:
        super().__init__(endpoint)
        self.bag = inventory()
        self.cells: dict[tuple[int, int, int], dict[str, Any]] = {}
        self.placements: list[tuple[int, int, int]] = []
        self.material = "minecraft:oak_planks"
        self.consume = 1
        self.lose_reply = False
        self.pause_after_place = False
        self.post_entered = asyncio.Event()
        self.post_release = asyncio.Event()
        self.post_paused = False
        self.handler_errors: list[Exception] = []

    def binding(self) -> HorizonBinding:
        return replace(super().binding(), timeout_s=6.0)

    def state(self) -> dict[str, Any]:
        return {
            "world": self.world,
            "dimension": "minecraft:overworld",
            "gamemode": "survival",
            "screen": "playing",
            "paused": False,
            "sleeping": None,
            "using": None,
            "busy": "place" if self.active else None,
            "selected": self.bag["selected"],
            "held": copy.deepcopy(self.bag["held"]),
            "player": {"position": [0.0, 64.0, 0.0], "eye": [0.0, 65.62, 0.0], "health": 20.0},
        }

    async def response(self, command: str) -> dict[str, Any] | None:  # noqa: PLR0911 - closed synthetic protocol responses
        if command == "state":
            if self.pause_after_place and self.placements and not self.post_paused:
                self.post_paused = True
                self.post_entered.set()
                await self.post_release.wait()
            return self.state()
        if command == "status":
            return {"server": {"address": "127.0.0.1:25565", "name": "Companion", "joined": True, "loaded": True}}
        if command == "inventory":
            return copy.deepcopy(self.bag)
        if command.startswith("block "):
            _, x, y, z = command.split()
            cell = (int(x), int(y), int(z))
            return copy.deepcopy(
                self.cells.get(cell, block(cell, "minecraft:stone" if cell[1] == 63 else "minecraft:air"))
            )
        if command.startswith("place "):
            _, x, y, z = command.split()
            cell = (int(x), int(y), int(z))
            self.active = True
            self.placements.append(cell)
            self.cells[cell] = block(cell, self.material)
            self.bag = inventory(self.bag["held"]["count"] - self.consume)
            self.issued.set()
            if self.lose_reply:
                return None
            self.active = False
            return {
                "ok": True,
                "block_before": "minecraft:air",
                "block": self.cells[cell],
                "changed": True,
                "inventory_change": {"minecraft:oak_planks": -self.consume},
                "screen": "playing",
            }
        if command == "stop":
            self.stops += 1
            was_active = self.active
            self.active = False
            self.release.set()
            self.post_release.set()
            return {"ok": True, "cancelled": "place" if was_active else None}
        if command.startswith("chat "):
            return {"ok": True}
        msg = f"Unexpected synthetic-game command: {command}"
        raise AssertionError(msg)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        self.connections.add(task)
        try:
            command = (await reader.readline()).decode().strip()
            self.commands.append(command)
            response = await self.response(command)
            if response is not None:
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass  # A cancelled client may close its read socket before the synthetic reply.
        except Exception as exc:
            self.handler_errors.append(exc)
            raise
        finally:
            writer.close()
            with suppress(BrokenPipeError, ConnectionResetError):
                await writer.wait_closed()
            self.connections.discard(task)


@dataclass
class BuildLab:
    game: BuildingGame
    control: HorizonControlSession
    builds: HorizonBuildService
    runner: LocalAssistRunner
    supervisor: HorizonSupervisor
    records: asyncio.Queue[dict[str, Any]]
    unknown_expected: bool = False


@pytest_asyncio.fixture
async def lab(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> AsyncIterator[BuildLab]:
    with TemporaryDirectory(prefix="lhbs-", dir=tmp_path_factory.getbasetemp()) as directory:
        root = Path(directory)
        monkeypatch.setattr(horizon_control, "_ownership_root", lambda: root / "ownership")
        game = BuildingGame(root / "game.sock")
        server = await asyncio.start_unix_server(game.handle, path=game.endpoint)
        control = HorizonControlSession(game.binding())
        assist = HorizonAssistService(policy(permitted=("state", "place", "say")), control)
        builds = HorizonBuildService(assist, control)
        runner = LocalAssistRunner(assist, control, builds=builds)
        records: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        supervisor = HorizonSupervisor(runner, control, record=records.put)
        instance = BuildLab(game, control, builds, runner, supervisor, records)
        await control.open()
        await runner.open()
        try:
            yield instance
        finally:
            game.post_release.set()
            game.release.set()
            errors: list[Exception] = []
            for close in (supervisor.stop, runner.aclose):
                try:
                    await close()
                except Exception as exc:  # noqa: BLE001 - cleanup failures have explicit assertions below
                    errors.append(exc)
            server.close()
            await server.wait_closed()
            tasks = tuple(game.connections)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            assert not game.handler_errors
            if instance.unknown_expected:
                assert any(isinstance(error, HorizonControlError) for error in errors)
                records_on_disk = [json.loads(path.read_bytes()) for path in (root / "ownership").glob("*.json")]
                assert any(record["state"] == "unknown" for record in records_on_disk)
            elif errors:
                msg = "Unexpected build-lab cleanup failure"
                raise ExceptionGroup(msg, errors)
            assert all(job.task is not None and job.task.done() for job in runner.queue.jobs.values())


def say(text: str = "priority") -> AssistRequest:
    return AssistRequest(request_id=str(uuid4()), action=SayAction(kind="say", text=text))


@pytest.mark.parametrize("count", [1, 3])
async def test_build_uses_fresh_native_runs_and_exact_query_line_cost(lab: BuildLab, count: int) -> None:
    cells = tuple((index + 1, 64, 0) for index in range(count))
    admitted = plan(cells)
    assert lab.control.query_count == 2  # Explicit control admission's state/status.
    await lab.supervisor.start_build(admitted)
    await asyncio.wait_for(lab.supervisor.wait_behavior(), timeout=3)
    assert lab.game.placements == list(cells)
    assert len(lab.runner.queue.jobs) == count
    assert len(lab.supervisor.run_ids) == count
    assert lab.builds.cursor == count
    assert lab.builds.read_count == 8 * count
    assert lab.runner.assist.used == count
    assert lab.supervisor.metrics["model_calls"] == 0
    assert lab.control.query_count == 2 + 26 * count
    query_lines = [
        line for line in lab.game.commands if line in {"state", "status", "inventory"} or line.startswith("block ")
    ]
    assert len(query_lines) == lab.control.query_count
    assert [line for line in lab.game.commands if line.startswith("place ")] == [
        f"place {x} {y} {z}" for x, y, z in cells
    ]
    assert lab.runner.services is not None
    for run_id in lab.supervisor.run_ids.values():
        native = await lab.runner.services.ledger.get(run_id)
        assert native is not None
        assert native.status is RunStatus.DONE
        assert native.pattern_manifest["key"] == "blockworld.horizon_build_step"
        result = lab.builds.run_results[run_id]
        assert result.kind == "placed"
        assert lab.builds.results[result.request_id] == result
        assert result.plan_digest == admitted.digest
        events = await lab.runner.services.ledger.list_events(run_id)
        assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
            "validate",
            "read_preflight",
            "decide",
            "place",
            "read_postflight",
            "report",
        ]
        record = lab.records.get_nowait()
        assert record["kind"] == "placed"
        assert record["model_calls"] == 0
        assert record["control_query_lines"] >= 28


async def test_last_shared_action_slot_still_confirms_postflight(lab: BuildLab) -> None:
    lab.runner.assist.policy = policy(max_actions=1, permitted=("state", "place", "say"))
    await lab.supervisor.start_build(plan())
    await asyncio.wait_for(lab.supervisor.wait_behavior(), timeout=3)
    result = next(iter(lab.builds.run_results.values()))
    assert result.kind == "placed"
    assert lab.runner.assist.used == 1
    assert result.read_count == 8
    assert lab.control.query_count == 28
    assert len(lab.game.placements) == 1
    with pytest.raises(ValueError, match="budget"):
        await lab.supervisor.start_build(plan(cells=((2, 64, 0),)))
    assert len(lab.game.placements) == 1


async def test_operator_priority_stops_after_click_before_postread(lab: BuildLab) -> None:
    lab.game.pause_after_place = True
    await lab.supervisor.start_build(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    await asyncio.wait_for(lab.game.post_entered.wait(), timeout=3)
    result = await asyncio.wait_for(lab.supervisor.submit_operator(say()), timeout=3)
    assert result.kind == "client_observed"
    assert lab.game.placements == [(1, 64, 0)]
    assert lab.builds.cursor == 0
    assert lab.builds.plan is None
    assert lab.game.stops >= 1
    assert lab.game.commands.index("chat priority") > max(
        index for index, line in enumerate(lab.game.commands) if line == "stop"
    )
    assert any(result.kind == "outcome_unknown" for result in lab.builds.run_results.values())
    assert not lab.supervisor.stopped.is_set()


@pytest.mark.parametrize("cancel_after_report", [False, True])
async def test_no_successor_cell_before_native_done_even_after_report(
    lab: BuildLab, monkeypatch: pytest.MonkeyPatch, *, cancel_after_report: bool
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    assert lab.runner.services is not None
    ledger = lab.runner.services.ledger
    original = ledger.try_settle_claim
    held_run: list[str] = []

    async def delayed(run_id: str, *, enqueue_seq: int, status: RunStatus, error: str | None = None) -> bool:
        if status is RunStatus.DONE and not held_run:
            held_run.append(run_id)
            entered.set()
            await release.wait()
        return await original(run_id, enqueue_seq=enqueue_seq, status=status, error=error)

    monkeypatch.setattr(ledger, "try_settle_claim", delayed)
    await lab.supervisor.start_build(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    try:
        await asyncio.wait_for(entered.wait(), timeout=3)
        assert lab.builds.cursor == 1  # Report has observed the cell; native commit is still pending.
        assert lab.runner.services is not None
        native = await lab.runner.services.ledger.get(held_run[0])
        assert native is not None
        assert native.status is RunStatus.RUNNING
        assert lab.builds.run_results[held_run[0]].kind == "placed"
        assert lab.game.placements == [(1, 64, 0)]
        assert len(lab.runner.queue.jobs) == 1
        if cancel_after_report:
            stopping = asyncio.create_task(lab.supervisor.stop())
            await asyncio.sleep(0)
            assert lab.builds.plan is None
            release.set()
            await asyncio.wait_for(stopping, timeout=3)
            assert lab.game.placements == [(1, 64, 0)]
            assert lab.supervisor.stopped.is_set()
        else:
            release.set()
            await asyncio.wait_for(lab.supervisor.wait_behavior(), timeout=3)
            assert lab.game.placements == [(1, 64, 0), (2, 64, 0), (3, 64, 0)]
    finally:
        release.set()


async def test_wrong_material_unknown_disarms_and_never_replays(lab: BuildLab) -> None:
    lab.game.material = "minecraft:dirt"
    await lab.supervisor.start_build(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    await asyncio.wait_for(lab.supervisor.wait_behavior(), timeout=3)
    result = next(iter(lab.builds.run_results.values()))
    assert result.kind == "outcome_unknown"
    assert result.action_count == 1
    assert lab.builds.cursor == 0
    assert lab.supervisor.stopped.is_set()
    assert lab.game.placements == [(1, 64, 0)]
    with pytest.raises(ValueError, match="stopped"):
        await lab.supervisor.submit_operator(say("must not send"))
    run_id = next(iter(lab.builds.run_results))
    attempt = await lab.control.invoke(run_id, "place 1 64 0")
    assert attempt.kind == "client_observed"  # Retained transport observation cannot certify material.
    assert lab.game.placements == [(1, 64, 0)]
    assert "chat must not send" not in lab.game.commands


async def test_lost_reply_retains_partial_effect_and_quarantines_without_replay(lab: BuildLab) -> None:
    lab.unknown_expected = True
    lab.game.lose_reply = True
    await lab.supervisor.start_build(plan(((1, 64, 0), (2, 64, 0), (3, 64, 0))))
    with pytest.raises(HorizonControlError):
        await asyncio.wait_for(lab.supervisor.wait_behavior(), timeout=3)
    assert lab.game.placements == [(1, 64, 0)]
    assert lab.builds.cursor == 0
    assert lab.supervisor.stopped.is_set()
    result = next(iter(lab.builds.run_results.values()))
    assert result.kind == "outcome_unknown"
    run_id = next(iter(lab.builds.run_results))
    repeated = await lab.control.invoke(run_id, "place 1 64 0")
    assert repeated.kind == "outcome_unknown"
    assert lab.game.placements == [(1, 64, 0)]
    assert lab.runner.services is not None
    native = await lab.runner.services.ledger.get(run_id)
    assert native is not None
    assert native.status is RunStatus.DONE


async def test_voice_file_admits_only_supplied_plan_once_and_retains_native_events(lab: BuildLab) -> None:
    # Make keeps its ordinary fixtures in the checkout; private voice material cannot live there.
    with TemporaryDirectory(prefix="lhbs-voice-", dir="/tmp") as directory:
        files = PrivateWorkspace(Path(directory), (_CHECKOUT,))
        probe = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "Postav schválený plán."})))
        admitted = plan()
        session = VoiceSession(files, probe, lab.runner, lab.control, build_plan=admitted)
        lab.supervisor = session.supervisor
        first = await session.begin(wav())
        assert first["kind"] == "build_started"
        assert first["plan_digest"] == admitted.digest
        await asyncio.wait_for(session.supervisor.wait_behavior(), timeout=3)
        assert lab.game.placements == [(1, 64, 0)]
        assert len(list(files.root.glob("*-events.jsonl"))) == 1
        assert len(list(files.root.glob("*-behavior.json"))) == 1
        assert (await session.begin(wav()))["kind"] == "refused"
        assert lab.game.placements == [(1, 64, 0)]
        assert len(lab.runner.queue.jobs) == 1
        await session.stop()
