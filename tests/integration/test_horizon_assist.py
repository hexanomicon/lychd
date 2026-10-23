"""Real native Run/Graph and real local sockets, with no game or model effects."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError

from lychd.agents.workflows import builtin_workflow_registry
from lychd.compositions.blockworld.horizon_assist import (
    AssistPolicy,
    AssistRequest,
    HorizonAssistService,
    PointAction,
    SayAction,
    decode_request,
    parse_text,
)
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services import horizon_control
from lychd.system.services.horizon_control import (
    HorizonBinding,
    HorizonControlError,
    HorizonControlSession,
    load_assist_profile,
    run_assist_cli,
)

CHECKOUT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.asyncio


class FakeGame:
    def __init__(self, endpoint: Path) -> None:
        self.endpoint = endpoint
        self.commands: list[str] = []
        self.active = False
        self.world = "Test"
        self.release = asyncio.Event()
        self.issued = asyncio.Event()
        self.connections: set[asyncio.Task[None]] = set()
        self.disconnect = False
        self.delay_action = False
        self.stops = 0
        self.remote = True
        self.omit_server = False
        self.status_reply: dict[str, object] | None = None
        self.positions = [[0.0, 64.0, 0.0]]

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        self.connections.add(task)
        try:
            command = (await reader.readline()).decode().strip()
            self.commands.append(command)
            if command == "state":
                position = self.positions.pop(0) if len(self.positions) > 1 else self.positions[0]
                result = {
                    "world": self.world,
                    "dimension": "minecraft:overworld",
                    "screen": "playing",
                    "paused": False,
                    "player": {"position": position, "health": 20},
                    "busy": "goto" if self.active else None,
                }
            elif command == "status":
                result = {"server": {"address": "127.0.0.1:25565", "name": "Companion", "joined": True, "loaded": True}}
                if not self.remote:
                    result = {"server": None}
                if self.omit_server:
                    result = {}
                result = self.status_reply if self.status_reply is not None else result
            elif command == "stop":
                self.stops += 1
                was_active = self.active
                if was_active:
                    self.active = False
                    self.release.set()
                result = {"ok": True, "cancelled": "goto" if was_active else None}
            elif command.startswith("goto "):
                self.issued.set()
                if self.delay_action:
                    await asyncio.sleep(0.04)
                self.active = True
                if self.disconnect:
                    return
                await self.release.wait()
                self.active = False
                result = {"error": "cancelled by stop", "cancelled": True}
            else:
                result = {"ok": True}
            writer.write(json.dumps(result).encode() + b"\n")
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            self.connections.discard(task)

    def binding(self) -> HorizonBinding:
        fields = Path(f"/proc/{os.getpid()}/stat").read_text().rsplit(")", 1)[1].split()
        return HorizonBinding(
            endpoint=self.endpoint,
            pid=os.getpid(),
            start_ticks=int(fields[19]),
            world="Test",
            dimension="minecraft:overworld",
            server_address="127.0.0.1:25565",
            client_name="Companion",
            timeout_s=0.3,
        )


@pytest_asyncio.fixture
async def game(tmp_path: Path, material_root: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FakeGame]:
    monkeypatch.setattr(horizon_control, "_ownership_root", lambda: material_root / "ownership")
    fake = FakeGame(tmp_path / "game.sock")
    server = await asyncio.start_unix_server(fake.handle, path=fake.endpoint)
    try:
        yield fake
    finally:
        server.close()
        await server.wait_closed()
        for task in tuple(fake.connections):
            task.cancel()
        await asyncio.gather(*fake.connections, return_exceptions=True)


@pytest.fixture
def material_root() -> Iterator[Path]:
    with TemporaryDirectory(prefix="lychd-horizon-material-") as directory:
        yield Path(directory)


def policy() -> AssistPolicy:
    return AssistPolicy(
        session_id="test-session",
        principal="test-operator",
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        min_x=-8,
        max_x=8,
        min_y=60,
        max_y=70,
        min_z=-8,
        max_z=8,
        permitted=("state", "status", "look_at", "goto", "say"),
    )


@pytest.mark.parametrize(
    "text",
    [
        "Zastał.",
        "follow me",
        "goto nan 64 0",
        "say /give @s diamond",
        "say hello\ncommand stop",
        "goto 1 2",
        "choď tam",
    ],
)
async def test_ambiguous_or_injected_text_refuses(text: str) -> None:
    with pytest.raises(ValueError, match=r".+"):
        parse_text(text)


async def test_strict_original_values_and_chat() -> None:
    with pytest.raises(ValidationError):
        PointAction(kind="goto", x=True, y=64, z=0)
    with pytest.raises(ValidationError):
        SayAction(kind="say", text=" /op me")
    assert parse_text("choď 1 64 2").kind == "goto"
    assert parse_text("povedz Ahoj").kind == "say"


async def test_endpoint_exclusive_and_changed_world_disarms(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    other = HorizonControlSession(game.binding())
    with pytest.raises(BlockingIOError):
        await other.open()
    game.world = "Changed"
    result = await control.invoke("run", "chat hello")
    assert result.kind == "refused"
    assert "chat hello" not in game.commands
    game.world = "Test"
    assert (await control.invoke("later", "chat hello")).kind == "refused"
    await control.aclose()


async def test_no_replay_after_lost_reply(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    game.disconnect = True
    result = await control.invoke("run", "goto 1 64 0 --near 1.5 --timeout 0.25")
    assert result.kind == "outcome_unknown"
    assert await control.invoke("run", "goto 1 64 0 --near 1.5 --timeout 0.25") == result
    assert sum(line.startswith("goto ") for line in game.commands) == 1
    with pytest.raises((HorizonControlError, ConnectionError)):
        await control.aclose()
    with pytest.raises(HorizonControlError, match=r"uncertain|quarantined"):
        await HorizonControlSession(game.binding()).open()


async def test_native_graph_logs_observation_and_default_boot_stays_inert(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    assist = HorizonAssistService(policy(), control)
    runner = LocalAssistRunner(assist, control)
    await runner.open()
    try:
        request = AssistRequest(request_id=str(uuid4()), action=parse_text("povedz Ahoj"))
        run_id = await runner.submit(request)
        await runner.wait(run_id)
        assert runner.services is not None
        run = await runner.services.ledger.get(run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        assert run.pattern_manifest["key"] == "blockworld.horizon_assist"
        events = await runner.services.ledger.list_events(run_id)
        entered = [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"]
        assert entered == ["validate", "execute", "report"]
        result = assist.results[request.request_id]
        assert result.kind == "client_observed"
        assert sum(command == "chat Ahoj" for command in game.commands) == 1
        assert any(event.kind == "log" and "client_observed" in event.data for event in events)
        assert await runner.submit(request) == run_id
        assert all(workflow.name != "blockworld.horizon_assist" for workflow in builtin_workflow_registry().all())
    finally:
        await runner.aclose()


async def test_status_projection_reaches_control_native_results_and_events(game: FakeGame) -> None:
    sentinel = "synthetic-private-status-sentinel"
    expected = {
        "screen": "playing",
        "dimension": "minecraft:overworld",
        "creative": False,
        "fps": 59.5,
        "frames": 120,
        "ticks": 40,
        "day_time": 6000,
        "render_distance": 8,
        "chunks": 81,
        "mobs": 2,
        "block_entities": 3,
        "pending_chunks": 4,
        "generated_chunks": 5,
        "meshed_sections": 6,
        "dirty_light": 7,
        "uptime_seconds": 2.5,
        "renderer": {
            "gpu": "Synthetic GPU",
            "vendor": "Synthetic vendor",
            "driver": "Synthetic driver",
            "device_type": "discrete",
            "backend": "vulkan",
            "present_mode": "fifo",
            "size": [1280, 720],
            "drawn_sections": 10,
            "section_draws": 11,
            "section_draw_calls": 12,
            "culled_sections": 13,
            "uploaded_bytes": 14,
            "resident_sections": 15,
            "arena_bytes": 16,
            "section_vertex_bytes": 17,
            "gpu_allocated_bytes": 18,
            "gpu_reserved_bytes": None,
        },
        "server": {"address": "127.0.0.1:25565", "name": "Companion", "joined": True, "loaded": True},
    }
    raw = json.loads(json.dumps(expected))
    raw.update(
        debug={"clipboard": sentinel},
        clipboard=sentinel,
        keys=[sentinel],
        physical_keys=[sentinel],
        nametags=[sentinel],
        future_field={"payload": sentinel},
    )
    raw["renderer"].update(debug={"clipboard": sentinel}, future_field=sentinel)
    raw["server"].update(debug={"clipboard": sentinel}, future_field=sentinel)
    game.status_reply = raw
    control = HorizonControlSession(game.binding())
    await control.open()
    assist = HorizonAssistService(policy(), control)
    runner = LocalAssistRunner(assist, control)
    await runner.open()
    try:
        outcome = await control.invoke("direct-status", "status", query=True)
        assert outcome.kind == "client_observed"
        assert outcome.observation == expected
        assert sentinel not in json.dumps(outcome.observation)
        request = AssistRequest(request_id=str(uuid4()), action=parse_text("status"))
        run_id = await runner.submit(request)
        await runner.wait(run_id)
        result = assist.results[request.request_id]
        assert result.kind == "client_observed"
        assert result.observation == expected
        assert control.attempts[run_id].observation == expected
        assert sentinel not in result.model_dump_json()
        assert runner.services is not None
        run = await runner.services.ledger.get(run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        events = await runner.services.ledger.list_events(run_id)
        reports = [json.loads(event.data) for event in events if event.kind == "log"]
        assert any(report.get("observation") == expected for report in reports)
        assert all(sentinel not in event.model_dump_json() for event in events)
    finally:
        await runner.aclose()


async def test_status_projection_drops_nested_payloads_in_scalar_fields(game: FakeGame) -> None:
    sentinel = {"clipboard": "synthetic-scalar-payload-sentinel"}
    server = {"address": "127.0.0.1:25565", "name": "Companion", "joined": True, "loaded": True}
    game.status_reply = {
        "screen": sentinel,
        "dimension": [sentinel],
        "creative": 1,
        "fps": True,
        "frames": 1.5,
        "ticks": sentinel,
        "uptime_seconds": "2.5",
        "renderer": {
            "gpu": sentinel,
            "vendor": [sentinel],
            "size": [1280, sentinel],
            "drawn_sections": True,
            "arena_bytes": 1.5,
            "gpu_allocated_bytes": sentinel,
            "gpu_reserved_bytes": None,
        },
        "server": server,
    }
    control = HorizonControlSession(game.binding())
    await control.open()
    try:
        outcome = await control.invoke("invalid-status-leaves", "status", query=True)
        assert outcome.kind == "client_observed"
        assert outcome.observation == {"renderer": {"gpu_reserved_bytes": None}, "server": server}
    finally:
        await control.aclose()


@pytest.mark.parametrize("lab", [False, True])
@pytest.mark.parametrize("server", [False, 0, "server", [], [None]])
async def test_malformed_status_server_never_becomes_null_binding(game: FakeGame, server: object, *, lab: bool) -> None:
    game.status_reply = {"server": server}
    binding = replace(game.binding(), mode="singleplayer_lab" if lab else "remote")
    with pytest.raises(HorizonControlError, match="binding"):
        await HorizonControlSession(binding).open()


@pytest.mark.parametrize("server", [{}, {"address": "wrong"}, {"joined": 1, "loaded": True}, None])
async def test_remote_status_identity_stays_required(game: FakeGame, server: object) -> None:
    game.status_reply = {"server": server}
    with pytest.raises(HorizonControlError, match="binding"):
        await HorizonControlSession(game.binding()).open()


async def test_status_projection_preserves_explicit_nulls(game: FakeGame) -> None:
    game.status_reply = {"server": None, "renderer": None}
    control = HorizonControlSession(replace(game.binding(), mode="singleplayer_lab"))
    await control.open()
    try:
        outcome = await control.invoke("null-status", "status", query=True)
        assert outcome.kind == "client_observed"
        assert outcome.observation == {"server": None, "renderer": None}
    finally:
        await control.aclose()


@pytest.mark.parametrize("error", [None, False, {"clipboard": "synthetic-error-payload-sentinel"}])
async def test_status_error_presence_refuses_without_exposing_payload(game: FakeGame, error: object) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    game.status_reply = {
        "server": {"address": "127.0.0.1:25565", "name": "Companion", "joined": True, "loaded": True},
        "error": error,
    }
    try:
        outcome = await control.invoke("status-error", "status", query=True)
        assert outcome.kind == "refused"
        assert outcome.observation is None
        assert "synthetic-error-payload-sentinel" not in repr(outcome)
    finally:
        await control.aclose()


async def test_stop_overtaking_action_is_not_false_settlement(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    game.delay_action = True
    assist = HorizonAssistService(policy(), control)
    runner = LocalAssistRunner(assist, control)
    await runner.open()
    try:
        run_id = await runner.submit(AssistRequest(request_id=str(uuid4()), action=parse_text("goto 1 64 0")))
        await game.issued.wait()
        await runner.cancel()
        assert not game.active
        assert game.stops >= 2
        assert runner.services is not None
        run = await runner.services.ledger.get(run_id)
        assert run is not None
        assert run.status is RunStatus.CANCELLED
        assert sum(command.startswith("goto ") for command in game.commands) == 1
    finally:
        await runner.aclose()


async def test_singleplayer_lab_is_explicit_and_remote_does_not_accept_it(game: FakeGame) -> None:
    game.remote = False
    remote = HorizonControlSession(game.binding())
    with pytest.raises(HorizonControlError, match="binding"):
        await remote.open()
    lab = HorizonControlSession(replace(game.binding(), mode="singleplayer_lab", server_address="", client_name=""))
    await lab.open()
    assert (await lab.invoke("lab", "state", query=True)).kind == "client_observed"
    await lab.aclose()
    game.remote = True
    wrong = HorizonControlSession(replace(game.binding(), mode="singleplayer_lab"))
    with pytest.raises(HorizonControlError, match="binding"):
        await wrong.open()


async def test_duplicate_wire_keys_and_unknown_fields_refuse() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        decode_request('{"request_id":"x","request_id":"y","action":{"kind":"state"}}')
    with pytest.raises(ValidationError, match="extra"):
        decode_request(json.dumps({"request_id": str(uuid4()), "action": {"kind": "state"}, "shell": "command"}))


async def test_cancel_before_send_does_not_issue(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    control.fence("fenced", "cancelled")
    assert (await control.invoke("fenced", "chat hello")).kind == "refused"
    assert "chat hello" not in game.commands
    await control.aclose()


async def test_nonzero_failed_claim_permanently_retires_run(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    control.fence_claim("failed-claim", 9, "worker interrupted")
    assert (await control.invoke("failed-claim", "chat hello")).kind == "refused"
    assert "chat hello" not in game.commands
    await control.aclose()


async def test_nonzero_claim_fence_during_connection_refuses_handoff(
    game: FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    original_connect = asyncio.open_unix_connection
    connecting = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def delayed_connect(path: str, *, limit: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        nonlocal calls
        calls += 1
        # invoke rechecks state and status before connecting for the action.
        if calls == 3:
            connecting.set()
            await release.wait()
        return await original_connect(path, limit=limit)

    monkeypatch.setattr(asyncio, "open_unix_connection", delayed_connect)
    pending = asyncio.create_task(control.invoke("failed-claim", "chat hello"))
    try:
        await asyncio.wait_for(connecting.wait(), timeout=2)
        control.fence_claim("failed-claim", 9, "worker interrupted")
        release.set()
        assert (await pending).kind == "refused"
        assert "chat hello" not in game.commands
    finally:
        release.set()
        await pending
        await control.aclose()


async def test_wrong_process_generation_refuses(game: FakeGame) -> None:
    control = HorizonControlSession(replace(game.binding(), start_ticks=1))
    with pytest.raises(HorizonControlError, match="generation"):
        await control.open()


async def test_empty_singleplayer_world_label_is_not_a_remote_label_allowance(game: FakeGame) -> None:
    game.world = ""
    game.remote = False
    control = HorizonControlSession(replace(game.binding(), mode="singleplayer_lab", world=""))
    with pytest.raises(HorizonControlError, match="nonempty"):
        await control.open()


async def test_singleplayer_requires_explicit_null_server_observation(game: FakeGame) -> None:
    game.remote = False
    game.omit_server = True
    with pytest.raises(HorizonControlError, match="binding"):
        await HorizonControlSession(replace(game.binding(), mode="singleplayer_lab")).open()


async def test_process_generation_is_rechecked_after_action_connection_before_write(
    game: FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    original_connect = asyncio.open_unix_connection
    original_ticks = control.binding.start_ticks
    calls = 0
    changed = False

    async def changed_generation(path: str, *, limit: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        nonlocal calls, changed
        calls += 1
        connection = await original_connect(path, limit=limit)
        if calls == 3:
            changed = True
        return connection

    monkeypatch.setattr(asyncio, "open_unix_connection", changed_generation)

    def observed_start(pid: int) -> int:
        assert pid == control.binding.pid
        return original_ticks + int(changed)

    monkeypatch.setattr(horizon_control, "_process_start", observed_start)
    assert (await control.invoke("changed", "chat hello")).kind == "refused"
    assert "chat hello" not in game.commands
    await control.aclose()


async def test_latest_preflight_pose_refuses_target(game: FakeGame) -> None:
    game.positions = [[0.0, 64.0, 0.0], [0.0, 64.0, 0.0], [100.0, 64.0, 0.0]]
    control = HorizonControlSession(game.binding())
    await control.open()
    assist = HorizonAssistService(policy(), control)
    runner = LocalAssistRunner(assist, control)
    await runner.open()
    try:
        request = AssistRequest(request_id=str(uuid4()), action=parse_text("goto 1 64 0"))
        run_id = await runner.submit(request)
        await runner.wait(run_id)
        assert assist.results[request.request_id].kind == "refused"
        assert not any(command.startswith("goto") for command in game.commands)
    finally:
        await runner.aclose()


async def test_quarantine_follows_client_generation_across_new_socket_inode(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    game.disconnect = True
    assert (await control.invoke("lost", "goto 1 64 0 --near 1.5 --timeout 0.25")).kind == "outcome_unknown"
    with pytest.raises(HorizonControlError, match="reply"):
        await control.aclose()
    game.endpoint.unlink()
    replacement = await asyncio.start_unix_server(game.handle, path=game.endpoint)
    try:
        with pytest.raises(HorizonControlError, match=r"uncertain|quarantined"):
            await HorizonControlSession(game.binding()).open()
    finally:
        replacement.close()
        await replacement.wait_closed()


async def test_dead_prior_generation_preserves_its_unknown_history(game: FakeGame, material_root: Path) -> None:
    prior = {"pid": 999999999, "start_ticks": 1, "endpoint": str(game.endpoint), "state": "unknown"}
    root = material_root / "ownership"
    root.mkdir(mode=0o700)
    history = root / "999999999-1.json"
    history.write_text(json.dumps(prior))
    endpoint_record = game.endpoint.with_name(game.endpoint.name + ".lychd-assist.lock")
    endpoint_record.write_text(json.dumps(prior))
    endpoint_record.chmod(0o600)
    control = HorizonControlSession(game.binding())
    await control.open()
    await control.aclose()
    retained = await asyncio.to_thread(history.read_text)
    assert json.loads(retained) == prior


@pytest.mark.parametrize("instruction", ["State.", "Stav!", "status?", "STATE..."])
async def test_read_only_sentence_punctuation(instruction: str) -> None:
    assert parse_text(instruction).kind in {"state", "status"}
    with pytest.raises(ValueError, match="Unsupported"):
        parse_text("state. goto 1 64 2")


async def test_authority_is_checked_after_connection_before_write(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()

    def expired(_latest: dict[str, object]) -> None:
        msg = "Expired session."
        raise ValueError(msg)

    outcome = await control.invoke("expired", "chat hello", authorize=expired)
    assert outcome.kind == "refused"
    assert "chat hello" not in game.commands
    await control.aclose()


async def test_bounded_action_refuses_without_a_game_command(game: FakeGame) -> None:
    control = HorizonControlSession(game.binding())
    await control.open()
    assist = HorizonAssistService(policy(), control)
    runner = LocalAssistRunner(assist, control)
    await runner.open()
    try:
        request = AssistRequest(request_id=str(uuid4()), action=parse_text("goto 100 64 0"))
        run_id = await runner.submit(request)
        await runner.wait(run_id)
        assert not any(command.startswith("goto") for command in game.commands)
        assert runner.services is not None
        events = await runner.services.ledger.list_events(run_id)
        assert any(event.kind == "log" and '"refused"' in event.data for event in events)
    finally:
        await runner.aclose()


async def test_one_shot_cli_retains_external_native_events(game: FakeGame, material_root: Path) -> None:
    workspace = material_root / "private"
    workspace.mkdir(mode=0o700)
    binding = game.binding()
    profile = workspace / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "binding": {
                    "endpoint": str(binding.endpoint),
                    "pid": binding.pid,
                    "start_ticks": binding.start_ticks,
                    "world": binding.world,
                    "dimension": binding.dimension,
                    "server_address": binding.server_address,
                    "client_name": binding.client_name,
                    "timeout_s": binding.timeout_s,
                },
                "policy": policy().model_dump(mode="json"),
                "workspace": str(workspace),
                "checkout_roots": [str(CHECKOUT)],
            }
        )
    )
    result = await run_assist_cli(profile, "stav", transcript=True)
    assert result["result"]["kind"] == "client_observed"
    evidence = Path(result["evidence"])
    assert evidence.parent == workspace
    metadata = await asyncio.to_thread(evidence.stat)
    assert metadata.st_mode & 0o777 == 0o600
    retained = await asyncio.to_thread(evidence.read_text)
    events = [json.loads(line) for line in retained.splitlines()]
    assert [event["data"] for event in events if event["kind"] == "done"] == ["done"]


@pytest.mark.parametrize(
    "boundary", ["workspace_inside", "workspace_ancestor", "profile_inside", "symlink_root", "missing_roots"]
)
async def test_profile_fences_every_checkout_in_both_directions(material_root: Path, boundary: str) -> None:
    checkout = material_root / "other-checkout"
    checkout.mkdir(mode=0o700)
    workspace = material_root / "private"
    workspace.mkdir(mode=0o700)
    roots = [str(checkout)]
    if boundary == "workspace_inside":
        workspace = checkout / "private"
        workspace.mkdir(mode=0o700)
    elif boundary == "workspace_ancestor":
        checkout = workspace / "nested-checkout"
        checkout.mkdir(mode=0o700)
        roots = [str(checkout)]
    elif boundary == "symlink_root":
        alias = material_root / "alias"
        alias.symlink_to(checkout, target_is_directory=True)
        roots = [str(alias)]
    profile = (checkout if boundary == "profile_inside" else workspace) / "profile.json"
    document: dict[str, object] = {"binding": {}, "policy": {}, "workspace": str(workspace), "checkout_roots": roots}
    if boundary == "missing_roots":
        del document["checkout_roots"]
    profile.write_text(json.dumps(document))
    with pytest.raises(HorizonControlError, match=r"checkout|Checkout|workspace"):
        await asyncio.to_thread(load_assist_profile, profile)


async def test_profile_rejects_oversized_read(material_root: Path) -> None:
    profile = material_root / "large.json"
    profile.write_bytes(b"x" * (horizon_control.MAX_REPLY_BYTES + 1))
    with pytest.raises(HorizonControlError, match="bounded regular"):
        await asyncio.to_thread(load_assist_profile, profile)
