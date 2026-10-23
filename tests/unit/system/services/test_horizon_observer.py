"""Query-only target observations through fake local Unix sockets."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
import pytest_asyncio

from lychd.system.services import horizon_observer
from lychd.system.services.horizon_control import HorizonBinding, HorizonControlError
from lychd.system.services.horizon_observer import HorizonTargetObserver

pytestmark = pytest.mark.asyncio


def process_start_ticks(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


class FakePerson:
    def __init__(self, endpoint: Path) -> None:
        self.endpoint = endpoint
        self.commands: list[bytes] = []
        self.tasks: set[asyncio.Task[None]] = set()
        self.state: dict[str, Any] = {
            "world": "Test",
            "dimension": "minecraft:overworld",
            "screen": "playing",
            "paused": False,
            "player": {"position": [1.0, 64.0, 2.0], "health": 20},
            # Deliberately unrelated and unordered: only player.position counts.
            "players": ["other", "Target"],
            "positions": [[999, 0, 0], [888, 0, 0]],
        }
        self.status: dict[str, Any] = {
            "server": {"address": "example.invalid:25565", "name": "Target", "joined": True, "loaded": True}
        }
        self.raw: bytes | None = None
        self.delay = 0.0
        self.disconnect = False
        self.received = asyncio.Event()
        self.block_command: bytes | None = None
        self.blocked = asyncio.Event()
        self.release = asyncio.Event()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        self.tasks.add(task)
        try:
            command = await reader.readline()
            if not command:
                return
            self.commands.append(command)
            self.received.set()
            if command == self.block_command:
                self.blocked.set()
                await self.release.wait()
            await asyncio.sleep(self.delay)
            if self.disconnect:
                return
            assert command in {b"state\n", b"status\n"}
            value = self.state if command == b"state\n" else self.status
            raw = self.raw if self.raw is not None else json.dumps(value).encode() + b"\n"
            writer.write(raw)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            self.tasks.discard(task)

    def binding(self) -> HorizonBinding:
        return HorizonBinding(
            endpoint=self.endpoint,
            pid=os.getpid(),
            start_ticks=process_start_ticks(os.getpid()),
            world="Test",
            dimension="minecraft:overworld",
            server_address="example.invalid:25565",
            client_name="Target",
            timeout_s=0.1,
        )


@pytest_asyncio.fixture
async def clients(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[FakePerson, HorizonBinding]]:
    tmp_path = tmp_path_factory.mktemp("uds")
    person = FakePerson(tmp_path / "person.sock")
    bot = FakePerson(tmp_path / "bot.sock")
    servers = [await asyncio.start_unix_server(client.handle, path=client.endpoint) for client in (person, bot)]
    for client in (person, bot):
        client.endpoint.chmod(0o600)
    real_start = process_start_ticks
    bot_pid = os.getpid() + 1
    bot_ticks = real_start(os.getpid()) + 1

    def process_start(pid: int) -> int:
        # Both fake listeners belong to pytest. Only the fake bot's expected
        # /proc boundary is substituted; target SO_PEERCRED remains real.
        return bot_ticks if pid == bot_pid else real_start(pid)

    monkeypatch.setattr(horizon_observer, "_process_start", process_start)
    bot_binding = replace(bot.binding(), pid=bot_pid, start_ticks=bot_ticks, client_name="Bot")
    try:
        yield person, bot_binding
        assert not bot.commands
    finally:
        for server in servers:
            server.close()
            await server.wait_closed()
        tasks = tuple(person.tasks | bot.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_default_peer_path_uses_own_pose_and_never_mutates(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    # Horizon default mode is usable because the owned parent is private.
    person.endpoint.chmod(0o755)
    lock = person.endpoint.with_name("person.sock.lychd-assist.lock")
    lock.write_bytes(b"human client's existing ownership")
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    state = await observer.observe()
    assert state == person.state
    assert state["player"]["position"] == [1.0, 64.0, 2.0]
    await observer.aclose()
    await observer.aclose()
    assert person.commands == [b"state\n", b"status\n"] * 2
    assert lock.read_bytes() == b"human client's existing ownership"
    assert not any(hasattr(observer, name) for name in ("invoke", "stop", "contain", "discover", "command"))
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    with pytest.raises(HorizonControlError, match="reopened"):
        await observer.open()


async def test_explicit_empty_remote_world_label_is_an_observation_not_an_invented_name(
    clients: tuple[FakePerson, HorizonBinding],
) -> None:
    person, bot = clients
    person.state["world"] = ""
    observer = HorizonTargetObserver(replace(person.binding(), world=""), bot_binding=replace(bot, world=""))
    await observer.open()
    assert (await observer.observe())["world"] == ""
    person.state["world"] = "Changed"
    with pytest.raises(HorizonControlError, match="changed"):
        await observer.observe()
    await observer.aclose()


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "singleplayer_lab"},
        {"server_address": ""},
        {"client_name": ""},
        {"world": "Elsewhere"},
        {"dimension": "minecraft:the_nether"},
        {"timeout_s": float("nan")},
        {"timeout_s": float("inf")},
        {"timeout_s": True},
        {"pid": True},
        {"start_ticks": 0},
    ],
)
async def test_invalid_bindings_refuse_before_queries(
    clients: tuple[FakePerson, HorizonBinding], changes: dict[str, Any]
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(replace(person.binding(), **changes), bot_binding=bot)
    with pytest.raises(HorizonControlError):
        await observer.open()
    assert not person.commands


async def test_bot_binding_and_distinct_generations_are_required(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    binding = person.binding()
    for wrong in (
        replace(bot, mode="singleplayer_lab"),
        replace(bot, server_address="other.invalid:25565"),
        replace(bot, client_name=""),
        replace(bot, world="Elsewhere"),
        replace(bot, pid=binding.pid, start_ticks=binding.start_ticks),
        replace(bot, endpoint=binding.endpoint),
    ):
        observer = HorizonTargetObserver(binding, bot_binding=wrong)
        with pytest.raises(HorizonControlError):
            await observer.open()
    assert not person.commands


async def test_wrong_peer_pid_refuses_before_send(
    clients: tuple[FakePerson, HorizonBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    person, bot = clients
    binding = replace(person.binding(), pid=os.getpid() + 2)

    def process_start(pid: int) -> int:
        return (
            binding.start_ticks
            if pid == binding.pid
            else bot.start_ticks
            if pid == bot.pid
            else process_start_ticks(pid)
        )

    monkeypatch.setattr(horizon_observer, "_process_start", process_start)
    with pytest.raises(HorizonControlError, match="peer"):
        await HorizonTargetObserver(binding, bot_binding=bot).open()
    assert not person.commands


async def test_changed_process_generation_closes_without_stale_sample(
    clients: tuple[FakePerson, HorizonBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()

    def changed_start(pid: int) -> int:
        return process_start_ticks(pid) + 1

    monkeypatch.setattr(horizon_observer, "_process_start", changed_start)
    with pytest.raises(HorizonControlError, match="generation"):
        await observer.observe()
    monkeypatch.setattr(horizon_observer, "_process_start", process_start_ticks)
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    assert person.commands == [b"state\n", b"status\n"]


async def test_replaced_inode_refuses_without_query(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.endpoint.rename(person.endpoint.with_suffix(".original"))
    replacement = await asyncio.start_unix_server(person.handle, path=person.endpoint)
    person.endpoint.chmod(0o600)
    try:
        with pytest.raises(HorizonControlError, match="generation"):
            await observer.observe()
        assert person.commands == [b"state\n", b"status\n"]
    finally:
        replacement.close()
        await replacement.wait_closed()


async def test_symlink_and_public_socket_or_directory_refuse(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    alias = person.endpoint.with_name("alias.sock")
    alias.symlink_to(person.endpoint)
    with pytest.raises(HorizonControlError, match="private"):
        await HorizonTargetObserver(replace(person.binding(), endpoint=alias), bot_binding=bot).open()
    person.endpoint.chmod(0o660)
    with pytest.raises(HorizonControlError, match="private"):
        await HorizonTargetObserver(person.binding(), bot_binding=bot).open()
    person.endpoint.chmod(0o600)
    person.endpoint.parent.chmod(0o755)
    try:
        with pytest.raises(HorizonControlError, match="private"):
            await HorizonTargetObserver(person.binding(), bot_binding=bot).open()
    finally:
        person.endpoint.parent.chmod(0o700)
    assert not person.commands


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("server", "address", "other.invalid:25565"),
        ("server", "name", "Impostor"),
        ("server", "joined", False),
        ("server", "loaded", False),
        ("state", "world", "Elsewhere"),
        ("state", "dimension", "minecraft:the_nether"),
        ("state", "screen", "death"),
        ("state", "paused", True),
        ("player", "health", 0),
        ("player", "health", -1),
        ("player", "health", True),
        ("player", "health", float("nan")),
        ("player", "health", float("inf")),
        ("player", "position", None),
        ("player", "position", [1, 2]),
        ("player", "position", [1, 2, 3, 4]),
        ("player", "position", [True, 2, 3]),
        ("player", "position", ["1", 2, 3]),
        ("player", "position", [1, float("inf"), 3]),
        ("player", "position", [1, float("nan"), 3]),
    ],
)
async def test_current_identity_life_and_own_finite_pose_required(
    clients: tuple[FakePerson, HorizonBinding], section: str, key: str, value: Any
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    target = person.status["server"] if section == "server" else person.state
    if section == "player":
        target = person.state["player"]
    before = target[key]
    target[key] = value
    with pytest.raises(HorizonControlError):
        await observer.observe()
    target[key] = before
    commands = len(person.commands)
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    assert len(person.commands) == commands
    assert set(person.commands) <= {b"state\n", b"status\n"}


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}\n',
        b'{"nested":{"a":1,"a":2}}\n',
        b'{"value":NaN}\n',
        b'{"value":Infinity}\n',
        b'{"value":1e999}\n',
        b'{"error":"unavailable"}\n',
        b"[]\n",
        b'{"unfinished":true}',
        b'"' + b"x" * horizon_observer.MAX_REPLY_BYTES + b'"\n',
    ],
    ids=["duplicate", "nested-duplicate", "nan", "infinity", "overflow", "error", "array", "incomplete", "oversize"],
)
async def test_malformed_error_incomplete_or_oversize_json_disarms(
    clients: tuple[FakePerson, HorizonBinding], raw: bytes
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.raw = raw
    with pytest.raises((HorizonControlError, ValueError)):
        await observer.observe()
    person.raw = None
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()


async def test_disconnect_and_deadline_close_without_retry(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.disconnect = True
    with pytest.raises(HorizonControlError, match="incomplete"):
        await observer.observe()
    assert person.commands == [b"state\n", b"status\n", b"state\n"]
    person.disconnect = False
    person.delay = 0.3
    later = HorizonTargetObserver(person.binding(), bot_binding=bot)
    started = asyncio.get_running_loop().time()
    with pytest.raises(TimeoutError):
        await later.open()
    assert asyncio.get_running_loop().time() - started < 0.5
    assert person.commands == [b"state\n", b"status\n", b"state\n", b"state\n"]


async def test_close_fences_waiting_query_without_stop(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.delay = 0.3
    person.received.clear()
    task = asyncio.create_task(observer.observe())
    await person.received.wait()
    await observer.aclose()
    with pytest.raises(HorizonControlError):
        await task
    assert person.commands == [b"state\n", b"status\n", b"state\n"]


async def test_wrong_peer_uid_refuses_before_send(
    clients: tuple[FakePerson, HorizonBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    person, bot = clients

    def wrong_credentials(writer: asyncio.StreamWriter) -> tuple[int, int, int]:
        return os.getpid(), os.getuid() + 1, os.getgid()

    monkeypatch.setattr(horizon_observer, "_peer_credentials", wrong_credentials)
    with pytest.raises(HorizonControlError, match="peer"):
        await HorizonTargetObserver(person.binding(), bot_binding=bot).open()
    assert not person.commands


async def test_total_deadline_includes_waiting_for_another_read(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.delay = 0.08
    started = asyncio.get_running_loop().time()
    first = asyncio.create_task(observer.observe())
    second = asyncio.create_task(observer.observe())
    results = await asyncio.gather(first, second, return_exceptions=True)
    assert isinstance(results[0], dict)
    assert isinstance(results[1], TimeoutError)
    assert asyncio.get_running_loop().time() - started < 0.5
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()


async def test_cancelled_query_permanently_disarms(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot)
    await observer.open()
    person.delay = 0.3
    person.received.clear()
    task = asyncio.create_task(observer.observe())
    await person.received.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    assert person.commands == [b"state\n", b"status\n", b"state\n"]


@pytest.mark.parametrize("command", [b"state\n", b"status\n"])
@pytest.mark.parametrize("expiry", [False, True])
async def test_opt_in_settles_cancelled_read_discards_sample_and_keeps_fresh_feed(
    clients: tuple[FakePerson, HorizonBinding], command: bytes, *, expiry: bool
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot, settle_cancelled_reads=True)
    await observer.open()
    person.block_command = command

    async def read() -> dict[str, Any]:
        async with asyncio.timeout(0.02 if expiry else 1):
            return await observer.observe()

    task = asyncio.create_task(read())
    await person.blocked.wait()
    if expiry:
        await asyncio.sleep(0.03)
    else:
        task.cancel("original cancellation")
        await asyncio.sleep(0)
        task.cancel("repeated cancellation")
        await asyncio.sleep(0)
    assert not task.done()
    person.release.set()
    with pytest.raises(TimeoutError if expiry else asyncio.CancelledError, match=None if expiry else "original"):
        await asyncio.wait_for(task, timeout=1)
    assert not [task for task in asyncio.all_tasks() if task.get_name() == "horizon-target-observation"]
    assert person.commands == [b"state\n", b"status\n"] * 2
    person.state["player"]["position"] = [2.0, 64.0, 3.0]
    assert (await observer.observe())["player"]["position"] == [2.0, 64.0, 3.0]
    assert person.commands == [b"state\n", b"status\n"] * 3
    await observer.aclose()


@pytest.mark.parametrize("command", [b"state\n", b"status\n"])
@pytest.mark.parametrize("failure", ["timeout", "identity", "close", "disconnect"])
async def test_opt_in_cancelled_read_failure_still_retires_and_preserves_cancellation(
    clients: tuple[FakePerson, HorizonBinding], command: bytes, failure: str
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot, settle_cancelled_reads=True)
    await observer.open()
    person.block_command = command
    task = asyncio.create_task(observer.observe())
    await person.blocked.wait()
    task.cancel("original cancellation")
    await asyncio.sleep(0)
    if failure == "identity":
        person.status["server"]["name"] = "Changed"
    elif failure == "close":
        await observer.aclose()
    elif failure == "disconnect":
        person.disconnect = True
    if failure != "timeout":
        person.release.set()
    with pytest.raises(asyncio.CancelledError, match="original"):
        await asyncio.wait_for(task, timeout=1)
    person.release.set()
    assert not [task for task in asyncio.all_tasks() if task.get_name() == "horizon-target-observation"]
    commands = list(person.commands)
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    assert person.commands == commands
    assert set(commands) <= {b"state\n", b"status\n"}


async def test_opt_in_read_retains_real_timeout_and_total_read_bound(
    clients: tuple[FakePerson, HorizonBinding],
) -> None:
    person, bot = clients
    observer = HorizonTargetObserver(person.binding(), bot_binding=bot, settle_cancelled_reads=True)
    await observer.open()
    person.delay = 0.08
    first = asyncio.create_task(observer.observe())
    second = asyncio.create_task(observer.observe())
    results = await asyncio.gather(first, second, return_exceptions=True)
    assert isinstance(results[0], dict)
    assert isinstance(results[1], TimeoutError)
    with pytest.raises(HorizonControlError, match="closed"):
        await observer.observe()
    assert not [task for task in asyncio.all_tasks() if task.get_name() == "horizon-target-observation"]


async def test_cancellation_settlement_requires_explicit_boolean(clients: tuple[FakePerson, HorizonBinding]) -> None:
    person, bot = clients
    with pytest.raises(HorizonControlError, match="boolean"):
        HorizonTargetObserver(person.binding(), bot_binding=bot, settle_cancelled_reads=cast("bool", 1))
    assert not person.commands
