"""Personal native runtime authority, process ownership and durable duplicate handling."""

from __future__ import annotations

import asyncio
import os
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.animation.capabilities import CapabilitySpec, SourceKind
from lychd.domain.animation.protocols import CapabilityRegistry
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.orchestration.actuator import (
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.system.services.native_runtime import NativeRuntimeActuator
from lychd.system.services.runtime import build_runtime_actuator


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _profile(tmp_path: Path) -> tuple[Mock, SwitchingSettings, dict[str, LlamaCppSoulstoneConfig]]:
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    engine = tmp_path / ("llama-server.exe" if os.name == "nt" else "llama-server")
    engine.touch(mode=0o700)
    model = tmp_path / "personal.gguf"
    model.touch()
    settings = SwitchingSettings(
        actuator="native-process", native_state_dir=root, native_llama_server=engine, native_model_root=tmp_path
    )
    runes = {}
    for name in ("alpha", "beta"):
        port = _free_port()
        runes[name] = LlamaCppSoulstoneConfig.model_validate(
            {
                "name": name,
                "startup_mode": "single",
                "model_path": str(model),
                "port": port,
                "base_url": f"http://127.0.0.1:{port}/v1",
            }
        )
    specs = {
        name: CapabilitySpec(
            key=name,
            animator_name=name,
            runtime="llamacpp",
            model_id="personal",
            source_kind=SourceKind.SOULSTONE,
            family=CapabilityFamily.CHAT,
        )
        for name in runes
    }
    registry = Mock(spec=CapabilityRegistry)
    registry.get_soulstone_rune.side_effect = runes.get
    registry.list_soulstone_runes.side_effect = lambda: list(runes.values())
    registry.get_capability.side_effect = specs.get
    registry.list_capabilities.return_value = list(specs.values())
    return registry, settings, runes


def _intent(registry: CapabilityRegistry, target: str, prior: tuple[str, ...] = ()) -> TransitionIntent:
    return TransitionIntent(
        config_generation=capability_config_generation(registry),
        target_animator=target,
        target_capability_key=target,
        expected_active_animators=prior,
        evict_animators=prior,
        launch_animators=(target,),
    )


@pytest.mark.asyncio
async def test_switch_owned_foreground_listeners_and_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry, settings, runes = _profile(tmp_path)
    actuator = build_runtime_actuator(settings, registry)
    assert isinstance(actuator, NativeRuntimeActuator)
    children: list[subprocess.Popen[bytes]] = []

    def launch(args: list[str]) -> subprocess.Popen[bytes]:
        assert args[args.index("--host") + 1] == "127.0.0.1"
        assert args[args.index("-m") + 1] == str(tmp_path / "personal.gguf")
        port = args[args.index("--port") + 1]
        child = subprocess.Popen(  # noqa: S603 - fixed Python loopback listener fixture
            [sys.executable, "-m", "http.server", port, "--bind", "127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        children.append(child)
        return child

    monkeypatch.setattr(actuator, "_launch", launch)
    first = _intent(registry, "alpha")
    try:
        await actuator.verify_startup()
        await actuator.apply(first)
        await actuator.apply(first)
        assert len(children) == 1
        reader, writer = await asyncio.open_connection("127.0.0.1", runes["alpha"].port)
        writer.write(b"GET / HTTP/1.0\r\n\r\n")
        await writer.drain()
        assert b"200 OK" in await asyncio.wait_for(reader.readline(), 5)
        writer.close()
        await writer.wait_closed()
        with pytest.raises(RuntimeError, match="unresolved"):
            NativeRuntimeActuator(registry, settings)
        with pytest.raises(RuntimePreconditionError, match="different intent"):
            await actuator.apply(first.model_copy(update={"target_capability_key": "other"}))
        second = _intent(registry, "beta", ("alpha",))
        await actuator.apply(second)
        assert children[0].poll() is not None
        assert children[1].poll() is None
        await actuator.apply(build_compensation_intent(second))
        assert children[1].poll() is not None
        assert children[2].poll() is None
        with pytest.raises(RuntimePreconditionError):
            await actuator.apply(build_compensation_intent(second))
    finally:
        await actuator.aclose()
    assert all(child.poll() is not None for child in children)
    next_owner = NativeRuntimeActuator(registry, settings)
    await next_owner.verify_startup()
    await next_owner.aclose()


@pytest.mark.asyncio
async def test_foreign_listener_and_untrusted_command_refused_before_claim(tmp_path: Path) -> None:
    registry, settings, runes = _profile(tmp_path)
    actuator = NativeRuntimeActuator(registry, settings)
    with socket.socket() as foreign:
        assert runes["alpha"].port is not None
        foreign.bind(("127.0.0.1", runes["alpha"].port))
        foreign.listen()
        with pytest.raises(RuntimePreconditionError, match="occupied"):
            await actuator.apply(_intent(registry, "alpha"))
        with pytest.raises(RuntimePreconditionError, match="occupied"):
            await actuator.verify_startup()
    runes["alpha"] = runes["alpha"].model_copy(update={"extra_args": ("--port", "99")})
    with pytest.raises(RuntimePreconditionError, match="overrides"):
        await actuator.apply(_intent(registry, "alpha"))
    assert settings.native_state_dir is not None
    with closing(sqlite3.connect(settings.native_state_dir / "native.sqlite3")) as db:
        assert db.execute("SELECT count(*) FROM transition").fetchone() == (0,)


def test_native_settings_allow_external_portal_only_and_require_bound_pair(tmp_path: Path) -> None:
    SwitchingSettings(actuator="native-process", native_state_dir=tmp_path)
    with pytest.raises(ValidationError, match="configured together"):
        SwitchingSettings(actuator="native-process", native_state_dir=tmp_path, native_model_root=tmp_path)


@pytest.mark.asyncio
async def test_configured_endpoint_never_forwards_to_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, settings, runes = _profile(tmp_path)
    actuator = NativeRuntimeActuator(registry, settings)
    public = runes["alpha"].port
    assert public is not None
    stop_file = tmp_path / "release"
    released = tmp_path / "released"
    script = """
import pathlib, socket, sys, time
with socket.socket() as listener:
    listener.bind(("127.0.0.1", int(sys.argv[1])))
    listener.listen()
    while not pathlib.Path(sys.argv[2]).exists():
        time.sleep(.01)
pathlib.Path(sys.argv[3]).touch()
time.sleep(60)
"""
    upstream_ports: list[int] = []

    def launch(args: list[str]) -> subprocess.Popen[bytes]:
        port = args[args.index("--port") + 1]
        upstream_ports.append(int(port))
        return subprocess.Popen([sys.executable, "-c", script, port, str(stop_file), str(released)])  # noqa: S603

    async def post_prompt() -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", public)
        try:
            writer.write(b"POST /v1/chat/completions HTTP/1.1\r\nContent-Length: 14\r\n\r\nprivate prompt")
            await writer.drain()
            assert not await asyncio.wait_for(reader.read(1), 5)
        except ConnectionError:
            pass
        finally:
            writer.close()

    received: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    async def foreign(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        received.set_result(await reader.read())
        writer.close()

    monkeypatch.setattr(actuator, "_launch", launch)
    try:
        await actuator.verify_startup()
        await post_prompt()
        intent = _intent(registry, "alpha")
        await actuator.apply(intent)
        stop_file.touch()
        async with asyncio.timeout(5):
            while not released.exists():  # noqa: ASYNC110 - acknowledgment comes from the fixture subprocess
                await asyncio.sleep(0.01)
        async with await asyncio.start_server(foreign, "127.0.0.1", upstream_ports[0]):
            with pytest.raises(RuntimeError, match="unresolved"):
                await actuator.apply(intent)
            await post_prompt()
            assert await asyncio.wait_for(received, 5) == b""
    finally:
        await actuator.aclose()
