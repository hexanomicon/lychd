"""Personal native runtime authority, process ownership and durable duplicate handling."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import json
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
from lychd.system.desktop.private import private_directory
from lychd.system.services.native_runtime import NativeRuntimeActuator
from lychd.system.services.runtime import build_runtime_actuator

# Virtual-environment redirectors on Windows give the listening process a different PID.
_PYTHON = str(Path(sys.base_prefix) / "python.exe") if os.name == "nt" else sys.executable


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _profile(tmp_path: Path) -> tuple[Mock, SwitchingSettings, dict[str, LlamaCppSoulstoneConfig]]:
    tmp_path = tmp_path.resolve(strict=True)
    root = tmp_path / "state"
    private_directory(root)
    engine = tmp_path / ("llama-server.exe" if os.name == "nt" else "llama-server")
    engine.touch(mode=0o700)
    model = tmp_path / "personal.gguf"
    model.touch()
    settings = SwitchingSettings(
        actuator="native-process", native_state_dir=root, native_llama_server=engine, native_model_root=tmp_path
    )
    runes: dict[str, LlamaCppSoulstoneConfig] = {}
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
    registry.lifecycle_binding_digest = None
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


async def _assert_serving(port: int | None) -> None:
    assert port is not None
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET / HTTP/1.0\r\n\r\n")
    await writer.drain()
    assert b"200 OK" in await asyncio.wait_for(reader.readline(), 5)
    writer.close()
    await writer.wait_closed()


def _record_launches(
    actuator: NativeRuntimeActuator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[subprocess.Popen[bytes]], list[Path]]:
    launch_engine = actuator._launch
    scratch_dirs: list[Path] = []
    children: list[subprocess.Popen[bytes]] = []

    def launch(args: list[str], scratch: Path) -> subprocess.Popen[bytes]:
        assert args[args.index("--host") + 1] == "127.0.0.1"
        assert args[args.index("-m") + 1] == str(tmp_path.resolve() / "personal.gguf")
        port = args[args.index("--port") + 1]
        assert scratch.parent == tmp_path.resolve() / "state"
        assert scratch not in scratch_dirs
        scratch_dirs.append(scratch)
        child = launch_engine(
            [_PYTHON, "-m", "http.server", port, "--bind", "127.0.0.1"],
            scratch,
        )
        children.append(child)
        return child

    monkeypatch.setattr(actuator, "_launch", launch)
    return children, scratch_dirs


@pytest.mark.asyncio
async def test_switch_owned_foreground_listeners_and_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry, settings, runes = _profile(tmp_path)
    actuator = build_runtime_actuator(settings, registry)
    assert isinstance(actuator, NativeRuntimeActuator)
    children, scratch_dirs = _record_launches(actuator, tmp_path, monkeypatch)
    first = _intent(registry, "alpha")
    try:
        await actuator.verify_startup()
        await actuator.apply(first)
        await actuator.apply(first)
        assert len(children) == 1
        await _assert_serving(runes["alpha"].port)
        with pytest.raises(RuntimeError, match="unresolved"):
            NativeRuntimeActuator(registry, settings)
        with pytest.raises(RuntimePreconditionError, match="different intent"):
            await actuator.apply(first.model_copy(update={"target_capability_key": "other"}))
        second = _intent(registry, "beta", ("alpha",))
        await actuator.apply(second)
        assert children[0].poll() is not None
        assert children[1].poll() is None
        with pytest.raises(RuntimePreconditionError, match="no longer matches"):
            await actuator.apply(first)
        assert len(children) == 2
        assert children[1].poll() is None
        compensation = build_compensation_intent(second)
        await actuator.apply(compensation)
        await actuator.apply(compensation)
        assert len(children) == 3
        assert children[1].poll() is not None
        assert children[2].poll() is None
        with pytest.raises(RuntimePreconditionError):
            await actuator.apply(build_compensation_intent(second))
    finally:
        await actuator.aclose()
    assert all(not directory.exists() for directory in scratch_dirs)
    assert all(child.poll() is not None for child in children)
    next_owner = NativeRuntimeActuator(registry, settings)
    await next_owner.verify_startup()
    try:
        with pytest.raises(RuntimePreconditionError, match="no longer matches"):
            await next_owner.apply(first)
    finally:
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
    actuator = NativeRuntimeActuator(registry, settings)
    original = runes["alpha"]
    for override in ({"extra_args": ("--port", "99")}, {"security_label_disable": True}):
        runes["alpha"] = original.model_copy(update=override)
        with pytest.raises(RuntimePreconditionError, match="overrides"):
            await actuator.apply(_intent(registry, "alpha"))
    await actuator.aclose()
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

    def launch(args: list[str], _scratch: Path) -> subprocess.Popen[bytes]:
        port = args[args.index("--port") + 1]
        upstream_ports.append(int(port))
        return subprocess.Popen([_PYTHON, "-c", script, port, str(stop_file), str(released)])  # noqa: S603

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


def test_native_child_environment_and_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scratch = tmp_path.resolve() / "scratch"
    scratch.mkdir(mode=0o700)
    monkeypatch.setenv("LYCHD_TEST_CREDENTIAL", "private")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    script = """
import os, pathlib, sys
cwd = pathlib.Path.cwd()
for key in ("HOME", "USERPROFILE", "TMPDIR", "TEMP", "TMP", "XDG_CACHE_HOME"):
    assert pathlib.Path(os.environ[key]) == cwd
assert "LYCHD_TEST_CREDENTIAL" not in os.environ
if os.name == "posix":
    try:
        descriptor = os.fstat(int(sys.argv[1]))
    except OSError:
        pass
    else:
        assert not os.path.samestat(descriptor, os.stat(sys.argv[2]))
pathlib.Path("receipt").touch()
"""
    handle_path = tmp_path / "core-only"
    with handle_path.open("wb") as handle:
        os.set_inheritable(handle.fileno(), True)  # noqa: FBT003 - positional-only OS interface
        child = NativeRuntimeActuator._launch([_PYTHON, "-c", script, str(handle.fileno()), str(handle_path)], scratch)
        assert child.wait(5) == 0
    assert (scratch / "receipt").is_file()


@pytest.mark.parametrize("binding", ["engine", "root", "model"])
def test_redirected_native_binding_fails_preflight(tmp_path: Path, binding: str) -> None:
    registry, settings, runes = _profile(tmp_path)
    target = tmp_path / "indirect"
    if os.name == "nt":
        # Windows symlink creation can require administrator privileges.
        target.mkdir()
        parent = target / ".."
    else:
        target.symlink_to(tmp_path, target_is_directory=True)
        parent = target
    if binding == "engine":
        assert settings.native_llama_server
        settings = settings.model_copy(update={"native_llama_server": parent / settings.native_llama_server.name})
    elif binding == "root":
        settings = settings.model_copy(update={"native_model_root": parent})
    else:
        runes["alpha"] = runes["alpha"].model_copy(update={"model_path": str(parent / "personal.gguf")})
    with pytest.raises(RuntimePreconditionError, match=r"redirected|canonical local path|inside native_model_root"):
        NativeRuntimeActuator(registry, settings)._command("alpha")


@pytest.mark.parametrize("failure", ["spawn", "early-exit", "timeout", "cancel"])
@pytest.mark.asyncio
async def test_failed_child_cleans_scratch_and_fences_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    registry, settings, _ = _profile(tmp_path)
    actuator = NativeRuntimeActuator(registry, settings)
    if failure == "timeout":
        settings.warmup_timeout_s = 0.1
    spawn = actuator._launch
    children: list[subprocess.Popen[bytes]] = []
    directories: list[Path] = []
    started = asyncio.Event()

    def launch(_args: list[str], scratch: Path) -> subprocess.Popen[bytes]:
        directories.append(scratch)
        if failure == "spawn":
            return spawn([str(tmp_path / "missing-executable")], scratch)
        script = "raise SystemExit(1)" if failure == "early-exit" else "import time; time.sleep(60)"
        child = spawn([_PYTHON, "-c", script], scratch)
        children.append(child)
        started.set()
        return child

    monkeypatch.setattr(actuator, "_launch", launch)
    try:
        await actuator.verify_startup()
        task = asyncio.create_task(actuator.apply(_intent(registry, "alpha")))
        if failure == "cancel":
            await asyncio.wait_for(started.wait(), 5)
            task.cancel()
        errors = {
            "spawn": FileNotFoundError,
            "early-exit": RuntimeError,
            "timeout": TimeoutError,
            "cancel": asyncio.CancelledError,
        }
        with pytest.raises(errors[failure]):
            await task
        assert all(child.poll() is not None for child in children)
        assert not directories[0].exists()
    finally:
        await actuator.aclose()
    assert len(directories) == 1
    assert not directories[0].exists()
    with pytest.raises(RuntimeError, match="unresolved"):
        NativeRuntimeActuator(registry, settings)


def test_native_binding_accepts_packaged_hard_links(tmp_path: Path) -> None:
    registry, settings, _ = _profile(tmp_path)
    assert settings.native_llama_server is not None
    (tmp_path / "packaged-engine").hardlink_to(settings.native_llama_server)
    (tmp_path / "packaged-model").hardlink_to(tmp_path / "personal.gguf")
    args, _ = NativeRuntimeActuator(registry, settings)._command("alpha")
    assert args[0] == str(settings.native_llama_server)


@pytest.mark.skipif(os.name != "posix", reason="POSIX public write bits")
@pytest.mark.parametrize("mode", [0o707, 0o770])
def test_publicly_writable_engine_rejected(tmp_path: Path, mode: int) -> None:
    registry, settings, _ = _profile(tmp_path)
    assert settings.native_llama_server is not None
    settings.native_llama_server.chmod(mode)
    with pytest.raises(RuntimePreconditionError, match="publicly writable"):
        NativeRuntimeActuator(registry, settings)._command("alpha")


@pytest.mark.asyncio
async def test_mixed_desktop_switch_restores_and_fences(  # noqa: PLR0915 - one serial failure and recovery history
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inert engine fixture exercises real native child eviction, reconvergence and ambiguity."""
    from lychd.config.settings.orchestration import DesktopContainerBinding
    from lychd.domain.orchestration.actuator import RuntimeActuationRestoredError
    from lychd.system.services.desktop_container import UnsettledContainerError

    registry, settings, runes = _profile(tmp_path)
    runes["beta"] = runes["beta"].model_copy(update={"placement": "container"})
    binding = DesktopContainerBinding(
        animator="beta",
        engine="docker",
        endpoint="unix:///local/engine.sock",
        container_id="a" * 64,
        host_port=_free_port(),
        container_port=8443,
        tls_sha256="b" * 64,
    )
    settings.containers = (binding,)
    actuator = NativeRuntimeActuator(registry, settings)
    container = actuator._containers["beta"]
    calls: list[str] = []
    incarnation: str | None = None

    def change(verb: str, *, expected: str | None = None) -> str | None:
        nonlocal incarnation
        assert expected == incarnation
        calls.append(verb)
        incarnation = f"started-{len(calls)}" if verb == "start" else None
        return incarnation

    monkeypatch.setattr(container, "verify_engine", lambda: None)
    monkeypatch.setattr(container, "observe", lambda: incarnation)
    monkeypatch.setattr(container, "change", change)
    children, _ = _record_launches(actuator, tmp_path, monkeypatch)
    await actuator.verify_startup()
    try:
        await actuator.apply(_intent(registry, "alpha"))
        to_container = _intent(registry, "beta", ("alpha",))
        await actuator.apply(to_container)
        await actuator.recover(to_container)
        assert calls == ["start"]
        assert children[0].poll() is not None
        back = _intent(registry, "alpha", ("beta",))
        with monkeypatch.context() as patch:
            patch.setattr(actuator, "_launch", Mock(side_effect=OSError("fixture spawn failure")))
            with pytest.raises(RuntimeActuationRestoredError):
                await actuator.apply(back)
        assert calls == ["start", "stop", "start"]
        with pytest.raises(RuntimeActuationRestoredError):
            await actuator.recover(back)
        await actuator.apply(_intent(registry, "alpha", ("beta",)))
        assert calls[-1] == "stop"
        assert children[1].poll() is None
        # Unsupported/changed ownership before eviction leaves alpha running.
        with monkeypatch.context() as patch:
            patch.setattr(container, "verify_engine", Mock(side_effect=RuntimePreconditionError("wrong owner")))
            with pytest.raises(RuntimePreconditionError, match="wrong owner"):
                await actuator.apply(_intent(registry, "beta", ("alpha",)))
        assert children[1].poll() is None
        monkeypatch.setattr(container, "change", Mock(side_effect=UnsettledContainerError("ambiguous start")))
        with pytest.raises(UnsettledContainerError, match="ambiguous"):
            await actuator.apply(_intent(registry, "beta", ("alpha",)))
        assert children[1].poll() is not None
        with pytest.raises(RuntimeError, match="unresolved"):
            await actuator.apply(_intent(registry, "alpha"))
    finally:
        await actuator.aclose()
    with pytest.raises(RuntimeError, match="unresolved"):
        NativeRuntimeActuator(registry, settings)


@pytest.mark.parametrize("engine", ["docker", "podman"])
def test_desktop_container_attests_each_effect(engine: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.config.settings.orchestration import DesktopContainerBinding
    from lychd.system.services.desktop_container import DesktopContainer, UnsettledContainerError

    binding = DesktopContainerBinding.model_validate(
        {
            "animator": "fixture",
            "engine": engine,
            "endpoint": "unix:///run/user/2000/engine.sock",
            "container_id": "a" * 64,
            "container_port": 8443,
            "host_port": 19999,
            "tls_sha256": "b" * 64,
        }
    )
    engine_info = (
        {"OSType": "linux", "SecurityOptions": ["name=rootless"]}
        if engine == "docker"
        else {"host": {"security": {"rootless": True}}}
    )
    host = {
        "PortBindings": {"8443/tcp": [{"HostIp": "127.0.0.1", "HostPort": "19999"}]},
        "RestartPolicy": {"Name": "no"},
        "AutoRemove": False,
        "NetworkMode": "bridge",
        "Privileged": False,
    }
    labels = {"io.lychd.soulstone": "fixture"}
    state: dict[str, object] = {"Status": "exited", "Running": False}
    commands: list[tuple[str, ...]] = []

    def command(*args: str) -> str:
        commands.append(args)
        if args[0] == "info":
            return json.dumps(engine_info)
        assert args[0] == "container"
        assert args[-1] == binding.container_id
        if args[1] == "inspect":
            return json.dumps(
                [{"Id": binding.container_id, "Config": {"Labels": labels}, "HostConfig": host, "State": state}]
            )
        if args[1] == "start":
            state.update(Status="running", Running=True, StartedAt="first")
        else:
            assert args[1] == "stop"
            state.update(Status="exited", Running=False)
        return ""

    container = DesktopContainer(binding, timeout=3)
    monkeypatch.setattr(container, "_command", command)
    assert container.change("start") == "first"
    with pytest.raises(RuntimePreconditionError, match="changed before"):
        container.change("stop", expected="replaced")
    assert container.change("stop", expected="first") is None
    mutations = [command for command in commands if command[0:2] in (("container", "start"), ("container", "stop"))]
    assert [c[1] for c in mutations] == ["start", "stop"]

    # Another client can restart the same pinned ID after inspection but before our stop reaches the engine.
    def competing_stop(*args: str) -> str:
        if args[:2] == ("container", "stop"):
            state["StartedAt"] = "second"
        return command(*args)

    monkeypatch.setattr(container, "_command", competing_stop)
    assert container.change("start") == "first"
    with pytest.raises(UnsettledContainerError, match="unresolved") as unsettled:
        container.change("stop", expected="first")
    assert "incarnation differs" in str(unsettled.value.__cause__)
    labels.clear()
    with pytest.raises(RuntimePreconditionError, match="identity"):
        container.change("start")
    assert commands[-1][1] == "inspect"
    for forbidden in ("tcp://127.0.0.1:2375", "ssh://localhost", "unix:///a/../b", "npipe:////remote/pipe/engine"):
        with pytest.raises(ValidationError, match="local"):
            DesktopContainerBinding.model_validate({**binding.model_dump(), "endpoint": forbidden})


@pytest.mark.asyncio
async def test_native_state_has_one_owner_until_close(tmp_path: Path) -> None:
    registry, settings, _ = _profile(tmp_path)
    owner = NativeRuntimeActuator(registry, settings)
    try:
        with pytest.raises(RuntimePreconditionError, match="another host owner"):
            NativeRuntimeActuator(registry, settings)
    finally:
        await owner.aclose()
    fresh = NativeRuntimeActuator(registry, settings)
    try:
        with pytest.raises(RuntimePreconditionError, match="closed"):
            await owner.apply(_intent(registry, "alpha"))
    finally:
        await fresh.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("peer", ["bound", "replacement", "new-incarnation"])
async def test_container_tls_binds_connected_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, peer: str
) -> None:
    import hashlib
    import ssl

    from lychd.config.settings.orchestration import DesktopContainerBinding
    from lychd.system.desktop.reactor_identity import create_identities
    from lychd.system.services.desktop_container import DesktopContainer

    await asyncio.to_thread(create_identities, tmp_path)
    cert = tmp_path / "host/identity.pem"
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, tmp_path / "host/identity.key")
    received = asyncio.get_running_loop().create_future()

    async def observe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            received.set_result(await reader.read(1024))
        finally:
            writer.close()

    async with await asyncio.start_server(observe, "127.0.0.1", 0, ssl=context) as server:
        pin = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
        binding = DesktopContainerBinding(
            animator="beta",
            engine="docker",
            endpoint="unix:///local/engine.sock",
            container_id="a" * 64,
            host_port=server.sockets[0].getsockname()[1],
            container_port=8443,
            tls_sha256=pin if peer != "replacement" else "b" * 64,
        )
        container = DesktopContainer(binding, timeout=2)
        monkeypatch.setattr(container, "observe", lambda: "second" if peer == "new-incarnation" else "first")
        if peer == "bound":
            _, writer = await container.connect("first")
            writer.write(b"private prompt")
            await writer.drain()
            writer.close()
            assert await asyncio.wait_for(received, 5) == b"private prompt"
        else:
            with pytest.raises(RuntimePreconditionError, match="binding"):
                await container.connect("first")
            assert await asyncio.wait_for(received, 5) == b""
