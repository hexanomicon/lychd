"""Closed placement port over real UDS with synthetic client observations only."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
import pytest_asyncio

from lychd.compositions.blockworld.horizon_assist import decode_request, parse_text
from lychd.system.services import horizon_control
from lychd.system.services.horizon_control import HorizonControlError, HorizonControlSession
from tests.integration.test_horizon_assist import FakeGame, policy

pytestmark = pytest.mark.asyncio


class PlacementGame(FakeGame):
    def __init__(self, endpoint: Path) -> None:
        super().__init__(endpoint)
        self.hold_place = False
        self.wire: dict[str, bytes] = {}
        self.delay_s = 0.0
        self.cell = {"pos": [1, 64, 0], "block": "minecraft:air", "state": "minecraft:air", "loaded": True}
        self.inventory = {
            "selected": 1,
            "held": {"item": "minecraft:oak_planks", "count": 3},
            "hotbar": [{"slot": 0, "item": "minecraft:oak_planks", "count": 3}],
            "main": [],
            "armor": [],
            "offhand": None,
            "carried": None,
            "counts": {"minecraft:oak_planks": 3},
        }

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        raw = await reader.readline()
        command = raw.decode().strip()
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if command not in self.wire and command != "inventory" and not command.startswith(("block ", "place ")):
            reader.feed_data(raw)
            await super().handle(reader, writer)
            return
        task = asyncio.current_task()
        assert task is not None
        self.connections.add(task)
        self.commands.append(command)
        try:
            if command in self.wire:
                reply = self.wire[command]
            elif command == "inventory":
                reply = json.dumps(self.inventory).encode() + b"\n"
            elif command.startswith("block "):
                reply = json.dumps(self.cell).encode() + b"\n"
            else:
                self.active = True
                self.issued.set()
                if self.disconnect:
                    return
                if self.hold_place:
                    await self.release.wait()
                    result = {"error": "cancelled by stop", "cancelled": True}
                else:
                    result = {"ok": True, "pos": [1, 64, 0], "block": "minecraft:oak_planks", "ticks": 2}
                self.active = False
                reply = json.dumps(result).encode() + b"\n"
            writer.write(reply)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            self.connections.discard(task)


@pytest_asyncio.fixture
async def game(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[PlacementGame]:
    # Keep the real UDS below Linux's path limit, inside the assigned external test root.
    with TemporaryDirectory(prefix="hp-", dir=tmp_path_factory.getbasetemp()) as directory:
        root = Path(directory)
        monkeypatch.setattr(horizon_control, "_ownership_root", lambda: root / "ownership")
        fake = PlacementGame(root / "g.sock")
        server = await asyncio.start_unix_server(fake.handle, path=fake.endpoint)
        try:
            yield fake
        finally:
            server.close()
            await server.wait_closed()
            for task in tuple(fake.connections):
                task.cancel()
            await asyncio.gather(*fake.connections, return_exceptions=True)


def control_for(game: PlacementGame) -> HorizonControlSession:
    return HorizonControlSession(replace(game.binding(), timeout_s=6.0))


async def test_fixed_queries_return_raw_observations_without_attempts(game: PlacementGame) -> None:
    control = control_for(game)
    await control.open()
    try:
        game.commands.clear()
        assert control.query_count == 2
        assert await control.inspect_cell(1, 64, 0) == game.cell
        assert await control.inspect_inventory() == game.inventory
        assert game.commands == ["state", "status", "block 1 64 0", "state", "status", "inventory"]
        assert control.attempts == {}
        assert control.query_count == 8
        assert (await control.invoke("one", "place 1 64 0")).kind == "client_observed"
        assert control.query_count == 12
    finally:
        await control.aclose()


@pytest.mark.parametrize("value", [True, False, 1.0, 1.5, "1", None, -(2**31) - 1, 2**31])
@pytest.mark.parametrize("axis", range(3))
async def test_cell_queries_require_original_i32_coordinates(game: PlacementGame, value: Any, axis: int) -> None:
    control = control_for(game)
    await control.open()
    try:
        before = list(game.commands)
        point = [1, 64, 0]
        point[axis] = value
        with pytest.raises(HorizonControlError, match="original i32"):
            await control.inspect_cell(*point)
        assert game.commands == before
        assert control.attempts == {}
    finally:
        await control.aclose()


async def test_cell_queries_accept_i32_endpoints_without_interpretation(game: PlacementGame) -> None:
    control = control_for(game)
    await control.open()
    try:
        await control.inspect_cell(-(2**31), 0, 2**31 - 1)
        assert "block -2147483648 0 2147483647" in game.commands
    finally:
        await control.aclose()


@pytest.mark.parametrize(
    ("line", "query"),
    [
        ("place 1 64 0", True),
        ("inventory", True),
        ("block 1 64 0", True),
        ("inventory", False),
        ("block 1 64 0", False),
        ("place 1 64 0 --item oak_planks", False),
        ("place 1 64 0 --timeout 5", False),
        ("place true 64 0", False),
        ("place 1.0 64 0", False),
        ("place 1e0 64 0", False),
        ("place +1 64 0", False),
        ("place 01 64 0", False),
        ("place -0 64 0", False),
        ("place 2147483648 64 0", False),
        ("place -2147483649 64 0", False),
        ("place 1 64", False),
        ("place 1 64 0 extra", False),
        ("place  1 64 0", False),
        (" place 1 64 0", False),
        ("place 1 64 0 ", False),
        ("place\t1 64 0", False),
        ("place 1 64 0\n", False),
        ("place \uff11 64 0", False),
    ],
)
async def test_closed_action_and_query_grammar(game: PlacementGame, line: str, *, query: bool) -> None:
    control = control_for(game)
    with pytest.raises(HorizonControlError, match="closed assist dialect"):
        await control.invoke("bad", line, query=query)
    assert not game.commands
    assert control.attempts == {}


async def test_policy_permission_does_not_add_a_public_place_action() -> None:
    assert policy().model_copy(update={"permitted": ("place",)}).permitted == ("place",)
    admitted = policy().model_dump(mode="json")
    admitted["permitted"] = ["place"]
    assert type(policy()).model_validate_json(json.dumps(admitted)).permitted == ("place",)
    with pytest.raises(ValueError, match="Unsupported"):
        parse_text("place 1 64 0")
    with pytest.raises(ValueError, match="place"):
        decode_request(
            '{"request_id":"00000000-0000-0000-0000-000000000001","action":{"kind":"place","x":1,"y":64,"z":0}}'
        )


@pytest.mark.parametrize("timeout_s", [0.3, 5.0, 5.999])
async def test_short_timeout_refuses_before_any_send_or_attempt(game: PlacementGame, timeout_s: float) -> None:
    control = HorizonControlSession(replace(game.binding(), timeout_s=timeout_s))
    await control.open()
    try:
        before = list(game.commands)
        result = await control.invoke("short", "place 1 64 0")
        assert result.kind == "refused"
        assert "six seconds" in result.detail
        assert game.commands == before
        assert control.attempts == {}
    finally:
        await control.aclose()


async def test_one_place_per_run_and_no_replay_of_changed_line(game: PlacementGame) -> None:
    control = control_for(game)
    await control.open()
    try:
        first = await control.invoke("one", "place 1 64 0")
        assert first.kind == "client_observed"
        assert first.observation == {"ok": True, "pos": [1, 64, 0], "block": "minecraft:oak_planks", "ticks": 2}
        assert await control.invoke("one", "place 1 64 0") == first
        assert await control.invoke("one", "place 2 64 0") == first
        assert [line for line in game.commands if line.startswith("place ")] == ["place 1 64 0"]
    finally:
        await control.aclose()


async def test_place_uses_latest_state_and_final_authority_callback(game: PlacementGame) -> None:
    control = control_for(game)
    await control.open()
    game.positions = [[2.0, 64.0, 0.0]]
    seen: list[dict[str, Any]] = []

    def refuse(state: dict[str, Any]) -> None:
        seen.append(state)
        msg = "Expired placement plan."
        raise ValueError(msg)

    try:
        result = await control.invoke("expired", "place 1 64 0", authorize=refuse)
        assert result.kind == "refused"
        assert seen[0]["player"]["position"] == [2.0, 64.0, 0.0]
        assert not any(line.startswith("place ") for line in game.commands)
        assert (await control.invoke("expired", "place 1 64 0")).kind == "refused"
    finally:
        await control.aclose()


async def test_failed_nonzero_claim_fences_place_without_send(game: PlacementGame) -> None:
    control = control_for(game)
    await control.open()
    try:
        control.fence_claim("retired", 7, "cancelled")
        assert (await control.invoke("retired", "place 1 64 0")).kind == "refused"
        assert not any(line.startswith("place ") for line in game.commands)
    finally:
        await control.aclose()


async def test_cancel_waiting_place_requires_separate_stop_socket(game: PlacementGame) -> None:
    game.hold_place = True
    control = control_for(game)
    await control.open()
    pending = asyncio.create_task(control.invoke("cancelled", "place 1 64 0"))
    try:
        await asyncio.wait_for(game.issued.wait(), timeout=1)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert game.active
        assert game.stops == 0
        await control.contain("cancelled")
        assert game.stops >= 1
        assert not game.active
        assert (await control.invoke("cancelled", "place 1 64 0")).kind == "outcome_unknown"
        assert game.commands.count("place 1 64 0") == 1
    finally:
        await control.aclose()


async def test_lost_place_reply_has_no_replay_and_quarantines_generation(game: PlacementGame) -> None:
    game.disconnect = True
    control = control_for(game)
    await control.open()
    first = await control.invoke("lost", "place 1 64 0")
    assert first.kind == "outcome_unknown"
    assert await control.invoke("lost", "place 1 64 0") == first
    assert (await control.invoke("another", "place 2 64 0")).kind == "refused"
    assert game.commands.count("place 1 64 0") == 1
    with pytest.raises(HorizonControlError, match="reply"):
        await control.aclose()
    with pytest.raises(HorizonControlError, match=r"uncertain|quarantined"):
        await control_for(game).open()


@pytest.mark.parametrize("inspection", ["cell", "inventory"])
async def test_inspections_require_open_armed_session(game: PlacementGame, inspection: str) -> None:
    control = control_for(game)

    async def inspect() -> dict[str, Any]:
        return await control.inspect_cell(1, 64, 0) if inspection == "cell" else await control.inspect_inventory()

    with pytest.raises(HorizonControlError, match="open, armed"):
        await inspect()
    assert not game.commands
    await control.open()
    try:
        before = list(game.commands)
        control.fence_all("stopped")
        with pytest.raises(HorizonControlError, match="open, armed"):
            await inspect()
        assert game.commands == before
    finally:
        await control.aclose()


@pytest.mark.parametrize("fault", ["world", "health", "loaded", "generation"])
async def test_inspection_binding_failures_disarm_without_query(game: PlacementGame, fault: str) -> None:
    control = control_for(game)
    await control.open()
    try:
        if fault == "world":
            game.world = "Other"
        elif fault == "health":
            game.wire["state"] = json.dumps({"player": {"health": 0}}).encode() + b"\n"
        elif fault == "loaded":
            game.wire["status"] = (
                b'{"server":{"address":"127.0.0.1:25565","name":"Companion","joined":true,"loaded":false}}\n'
            )
        else:
            control.binding = replace(control.binding, start_ticks=1)
        with pytest.raises(HorizonControlError, match="inspection is unavailable"):
            await control.inspect_inventory()
        assert "inventory" not in game.commands
        assert (await control.invoke("after-bad-read", "place 1 64 0")).kind == "refused"
        assert control.attempts == {}
    finally:
        await control.aclose()


@pytest.mark.parametrize(
    "reply",
    [
        b'{"error":"unavailable"}\n',
        b'{"loaded":true,"loaded":false}\n',
        b'{"count":NaN}\n',
        b'{"count":1e999}\n',
        b"[]\n",
        b'{"incomplete":true}',
        b"x" * (horizon_control.MAX_REPLY_BYTES + 1) + b"\n",
    ],
    ids=["client-error", "duplicate-key", "nan", "overflow", "array", "incomplete", "oversized"],
)
@pytest.mark.parametrize("inspection", ["cell", "inventory"])
async def test_bad_inspection_reply_disarms_without_retry(game: PlacementGame, reply: bytes, inspection: str) -> None:
    control = control_for(game)
    await control.open()
    command = "block 1 64 0" if inspection == "cell" else "inventory"
    game.wire[command] = reply
    try:
        read = control.inspect_cell(1, 64, 0) if inspection == "cell" else control.inspect_inventory()
        with pytest.raises(HorizonControlError, match="inspection is unavailable"):
            await read
        assert game.commands.count(command) == 1
        assert (await control.invoke("after-bad-read", "place 1 64 0")).kind == "refused"
        assert control.attempts == {}
    finally:
        await control.aclose()


async def test_combined_inspection_deadline_disarms_without_retry(game: PlacementGame) -> None:
    control = HorizonControlSession(replace(game.binding(), timeout_s=0.15))
    await control.open()
    game.delay_s = 0.06
    try:
        with pytest.raises(HorizonControlError, match="inspection is unavailable"):
            await control.inspect_inventory()
        assert game.commands.count("inventory") <= 1
        assert control.attempts == {}
        assert (await control.invoke("after-timeout", "chat hello")).kind == "refused"
    finally:
        await control.aclose()


@pytest.mark.parametrize("change", ["fence", "generation"])
async def test_inspection_rechecks_fence_and_generation_after_query_connect(
    game: PlacementGame, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    control = control_for(game)
    await control.open()
    original_connect = asyncio.open_unix_connection
    calls = 0

    async def changed_connect(path: str, *, limit: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        nonlocal calls
        calls += 1
        connection = await original_connect(path, limit=limit)
        if calls == 3:
            if change == "fence":
                control.fence_all("stopped")
            else:
                control.binding = replace(control.binding, start_ticks=1)
        return connection

    monkeypatch.setattr(asyncio, "open_unix_connection", changed_connect)
    try:
        with pytest.raises(HorizonControlError, match="inspection is unavailable"):
            await control.inspect_inventory()
        assert "inventory" not in game.commands
        assert control.query_count == 4
        assert control.attempts == {}
    finally:
        await control.aclose()
