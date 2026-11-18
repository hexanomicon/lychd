"""Personal single-process llama.cpp effect owner for a private desktop installation."""

from __future__ import annotations

import asyncio
import os
import socket
import sqlite3
import stat
import subprocess
import sys
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.conflicts import build_conflict_topology
from lychd.domain.orchestration.actuator import (
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppMode, LlamaCppSoulstoneConfig
from lychd.system.path_safety import path_has_symlink_component

if TYPE_CHECKING:
    from lychd.config.settings.orchestration import SwitchingSettings
    from lychd.domain.animation.protocols import CapabilityRegistry
    from lychd.domain.orchestration.containment import SoftActivationRecord

_PRIVATE_MODE = 0o700
_WINDOWS_TCP_COLUMNS = 5
_UNSETTLED = (
    "Native runtime ownership is unresolved. Stop Core, inspect the private native.sqlite3 journal, "
    "verify the recorded llama-server processes are stopped and their ports are free before archiving the journal."
)


class NativeSingleModelGuard:
    """The personal process profile admits single-model hard swaps only."""

    def assert_clear(self) -> None:
        """No dynamic activation can begin through this guard."""

    def arm(self, record: SoftActivationRecord) -> None:
        msg = f"Native Animator {record.target_animator!r} requires a fixed single model."
        raise RuntimePreconditionError(msg)

    def clear(self, record: SoftActivationRecord) -> None:
        msg = f"No native dynamic activation was armed for {record.activation_id!r}."
        raise RuntimePreconditionError(msg)


class NativeRuntimeActuator:
    """Own foreground children by live process handle and journal transitions before mutation.

    The desktop launcher holds the installation's single-Core lock. No stored PID is
    used as termination authority. A crash with a live or pending owner fences startup.
    """

    def __init__(self, registry: CapabilityRegistry, settings: SwitchingSettings) -> None:
        """Open the installation journal before accepting native work."""
        directory = settings.native_state_dir
        if directory is None or not directory.is_dir() or path_has_symlink_component(directory) is not None:
            msg = "Native runtime requires an existing private native_state_dir."
            raise RuntimePreconditionError(msg)
        if os.name == "posix" and (
            directory.stat().st_uid != os.getuid() or stat.S_IMODE(directory.stat().st_mode) != _PRIVATE_MODE
        ):
            msg = "Native state directory must be current-user owned with permissions 0700."
            raise RuntimePreconditionError(msg)
        self._journal = directory / "native.sqlite3"
        if self._journal.is_symlink() or self._journal.is_junction():
            msg = "Native journal cannot be redirected."
            raise RuntimePreconditionError(msg)
        self._registry = registry
        self._settings = settings
        self._children: dict[str, subprocess.Popen[bytes]] = {}
        self._lock = asyncio.Lock()
        self._endpoints: dict[str, asyncio.Server] = {}
        self._upstreams: dict[str, int] = {}
        self._connections: set[asyncio.Task[None]] = set()
        with closing(sqlite3.connect(self._journal)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS transition (id TEXT PRIMARY KEY, intent TEXT NOT NULL, done INTEGER NOT NULL)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS child (name TEXT PRIMARY KEY, pid INTEGER NOT NULL)")
            if db.execute("SELECT 1 FROM child UNION ALL SELECT 1 FROM transition WHERE done=0").fetchone():
                raise RuntimeError(_UNSETTLED)

    def _command(self, name: str) -> tuple[list[str], int]:
        rune = self._registry.get_soulstone_rune(name)
        engine = self._settings.native_llama_server
        root = self._settings.native_model_root
        if (
            not isinstance(rune, LlamaCppSoulstoneConfig)
            or not rune.concurrency.dedicated
            or engine is None
            or root is None
        ):
            msg = f"No managed native llama.cpp binding for {name!r}."
            raise RuntimePreconditionError(msg)
        if (
            rune.startup_mode != LlamaCppMode.SINGLE
            or not rune.model_path
            or rune.port is None
            or rune.exec
            or rune.extra_args
            or rune.env_vars
            or rune.secret_env_files
            or rune.lora_adapters
            or rune.embedding_profile
            or rune.models_dir
            or rune.models_preset
            or rune.chat_template
            or rune.devices
            or rune.volumes
            or "quadlet" in rune.model_fields_set
        ):
            msg = "Native llama.cpp requires a single typed model with no command, environment, adapter or container overrides."
            raise RuntimePreconditionError(msg)
        if rune.base_url is not None and str(rune.base_url).rstrip("/") != f"http://127.0.0.1:{rune.port}/v1":
            msg = "Native llama.cpp requires an explicit http://127.0.0.1:<port>/v1 endpoint."
            raise RuntimePreconditionError(msg)
        if (
            engine.name != ("llama-server.exe" if os.name == "nt" else "llama-server")
            or not engine.is_file()
            or not os.access(engine, os.X_OK)
        ):
            msg = "The approved llama-server executable is missing or unusable."
            raise RuntimePreconditionError(msg)
        model = Path(rune.model_path)
        if (
            not model.is_absolute()
            or not root.is_dir()
            or not model.resolve().is_relative_to(root.resolve())
            or model.suffix.lower() != ".gguf"
            or not model.is_file()
        ):
            msg = "Native model must be an existing absolute GGUF file inside native_model_root."
            raise RuntimePreconditionError(msg)
        planner = LlamaCppRuntimePlanner()
        args = planner.plan_exec_args(
            soulstone=rune, inferred=LlamaCppRuntimeInference(), mode="single", listen_host="127.0.0.1"
        )
        return [str(engine.resolve(strict=True)), *args], rune.port

    async def verify_startup(self) -> None:
        """Reserve configured loopback endpoints before any registry observation."""
        try:
            for rune in self._registry.list_soulstone_runes():
                _, port = self._command(rune.name)
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    if os.name == "nt":
                        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    else:
                        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind(("127.0.0.1", port))
                    self._endpoints[rune.name] = await asyncio.start_server(
                        partial(self._connect, rune.name), sock=listener
                    )
                except BaseException:
                    listener.close()
                    raise
        except OSError as exc:
            await self.aclose()
            msg = "Native endpoint is occupied or unavailable; its listener cannot be adopted."
            raise RuntimePreconditionError(msg) from exc
        except BaseException:
            await self.aclose()
            raise

    def _connect(self, name: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.create_task(self._forward(name, reader, writer))
        self._connections.add(task)
        task.add_done_callback(self._connections.discard)

    async def _forward(self, name: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        child = self._children.get(name)
        port = self._upstreams.get(name)
        upstream: asyncio.StreamWriter | None = None
        try:
            if child is None or child.poll() is not None or port is None:
                return
            source, upstream = await asyncio.open_connection("127.0.0.1", port)
            # Verify after connecting. A subsequent bind cannot redirect this stream.
            if not await asyncio.to_thread(_owns_listener, child.pid, port) or child.poll() is not None:
                return
            async with asyncio.TaskGroup() as group:
                group.create_task(_pipe(reader, upstream))
                group.create_task(_pipe(source, writer))
        except (OSError, ExceptionGroup, subprocess.SubprocessError):
            return
        finally:
            if upstream is not None:
                upstream.close()
            writer.close()

    async def apply(self, intent: TransitionIntent) -> None:
        async with self._lock:
            with closing(sqlite3.connect(self._journal)) as db:
                db.execute("BEGIN IMMEDIATE")
                if await self._replayed(db, intent):
                    return
                self._validate(db, intent)
                commands = {name: self._command(name) for name in (*intent.evict_animators, *intent.launch_animators)}
                for name in intent.launch_animators:
                    if name not in self._endpoints:
                        msg = "Native endpoint has not been reserved or is occupied."
                        raise RuntimePreconditionError(msg)
                with db:
                    db.execute(
                        "INSERT INTO transition VALUES (?, ?, 0)", (intent.transition_id, intent.model_dump_json())
                    )
                for name in intent.evict_animators:
                    await self._stop(db, name)
                for name in intent.launch_animators:
                    args, _ = commands[name]
                    with socket.socket() as probe:
                        probe.bind(("127.0.0.1", 0))
                        port = int(probe.getsockname()[1])
                    args[args.index("--port") + 1] = str(port)
                    child = self._launch(args)
                    self._children[name] = child
                    with db:
                        db.execute("INSERT INTO child VALUES (?, ?)", (name, child.pid))
                    await self._await_listener(child, port)
                    self._upstreams[name] = port
                with db:
                    db.execute("UPDATE transition SET done=1 WHERE id=?", (intent.transition_id,))

    @staticmethod
    def _launch(args: list[str]) -> subprocess.Popen[bytes]:
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "HOME", "TEMP", "TMP", "TMPDIR", "USERPROFILE"}
        }
        return subprocess.Popen(  # noqa: S603 - fixed executable and typed extension planner
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=Path(args[0]).parent,
        )

    async def _await_listener(self, child: subprocess.Popen[bytes], port: int) -> None:
        # Orchestrator subsequently verifies exact model readiness through its registry.
        async with asyncio.timeout(self._settings.warmup_timeout_s):
            while child.poll() is None:
                if await asyncio.to_thread(_owns_listener, child.pid, port) and child.poll() is None:
                    return
                await asyncio.sleep(0.1)
        raise RuntimeError(_UNSETTLED)

    async def _replayed(self, db: sqlite3.Connection, intent: TransitionIntent) -> bool:
        """Acknowledge a completed intent only while its owned process outcome still holds."""
        if db.execute("SELECT 1 FROM transition WHERE done=0").fetchone():
            raise RuntimeError(_UNSETTLED)
        row = db.execute("SELECT intent FROM transition WHERE id=?", (intent.transition_id,)).fetchone()
        if row is None:
            return False
        if row[0] != intent.model_dump_json():
            msg = "Native transition ID was reused with a different intent."
            raise RuntimePreconditionError(msg)
        live = self._owned_processes(db)
        for name, pid in live.items():
            port = self._upstreams.get(name)
            if (
                port is None
                or not await asyncio.to_thread(_owns_listener, pid, port)
                or self._children[name].poll() is not None
            ):
                raise RuntimeError(_UNSETTLED)
        desired = (set(intent.expected_active_animators) - set(intent.evict_animators)) | set(intent.launch_animators)
        if desired != live.keys() or intent.config_generation != capability_config_generation(self._registry):
            msg = "Completed native transition no longer matches the current configuration or active processes."
            raise RuntimePreconditionError(msg)
        return True

    def _owned_processes(self, db: sqlite3.Connection) -> dict[str, int]:
        recorded = dict(db.execute("SELECT name, pid FROM child"))
        live = {name: child.pid for name, child in self._children.items() if child.poll() is None}
        if recorded != live or live.keys() != self._children.keys():
            raise RuntimeError(_UNSETTLED)
        return live

    def _validate(self, db: sqlite3.Connection, intent: TransitionIntent) -> None:
        spec = self._registry.get_capability(intent.target_capability_key)
        if (
            spec is None
            or spec.animator_name != intent.target_animator
            or intent.config_generation != capability_config_generation(self._registry)
        ):
            msg = "Native transition target or configuration generation is stale."
            raise RuntimePreconditionError(msg)
        live = self._owned_processes(db)
        prior = set(intent.expected_active_animators)
        if set(live) != prior:
            msg = "Native transition expected a different set of owned processes."
            raise RuntimePreconditionError(msg)
        if intent.operation == "compensation":
            row = db.execute(
                "SELECT intent FROM transition WHERE id=? AND done=1 AND rowid=(SELECT MAX(rowid) FROM transition)",
                (intent.rollback_of,),
            ).fetchone()
            if row is not None:
                original = TransitionIntent.model_validate_json(row[0])
                inverse = build_compensation_intent(original) if original.operation == "forward" else None
                if inverse and inverse.model_copy(update={"transition_id": intent.transition_id}) == intent:
                    return
            msg = "Native compensation requires the exact inverse of a completed forward transition."
            raise RuntimePreconditionError(msg)
        topology = build_conflict_topology(self._registry.list_soulstone_runes())
        if intent.launch_animators != (intent.target_animator,) or set(intent.evict_animators) != prior.intersection(
            topology.neighbors_for(intent.target_animator)
        ):
            msg = "Native intent does not match the declared conflict plan."
            raise RuntimePreconditionError(msg)

    async def _stop(self, db: sqlite3.Connection, name: str) -> None:
        child = self._children[name]
        row = db.execute("SELECT pid FROM child WHERE name=?", (name,)).fetchone()
        if row != (child.pid,):
            raise RuntimeError(_UNSETTLED)
        if child.poll() is None:
            child.terminate()
            try:
                await asyncio.to_thread(child.wait, 10)
            except subprocess.TimeoutExpired:
                child.kill()
                await asyncio.to_thread(child.wait, 10)
        with db:
            db.execute("DELETE FROM child WHERE name=? AND pid=?", (name, child.pid))
        self._upstreams.pop(name, None)
        del self._children[name]

    async def aclose(self) -> None:
        """Stop only children of this instance before releasing its installation lock."""
        async with self._lock:
            with closing(sqlite3.connect(self._journal)) as db:
                for endpoint in self._endpoints.values():
                    endpoint.close()
                connections = tuple(self._connections)
                for connection in connections:
                    connection.cancel()
                await asyncio.gather(*connections, return_exceptions=True)
                for endpoint in self._endpoints.values():
                    await endpoint.wait_closed()
                self._endpoints.clear()
                for name in tuple(self._children):
                    await self._stop(db, name)


async def _pipe(source: asyncio.StreamReader, target: asyncio.StreamWriter) -> None:
    while data := await source.read(65536):
        target.write(data)
        await target.drain()
    target.write_eof()


def _owns_listener(pid: int, port: int) -> bool:
    """Match the listening socket to the exact live foreground process."""
    if sys.platform == "linux":
        return _owns_linux_listener(pid, port)
    if os.name == "nt":
        import ctypes

        directory = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(directory, len(directory))
        if not 0 < length < len(directory):
            raise RuntimeError(_UNSETTLED)
        command = [str(Path(directory.value) / "netstat.exe"), "-ano", "-p", "TCP"]
    else:
        command = ["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid), f"-iTCP@127.0.0.1:{port}", "-sTCP:LISTEN", "-Fn"]
    result = subprocess.run(command, capture_output=True, timeout=5, check=False)  # noqa: S603 - fixed OS observer
    address = f"127.0.0.1:{port}".encode("ascii")
    if os.name == "nt":
        return result.returncode == 0 and any(
            len(fields) == _WINDOWS_TCP_COLUMNS
            and fields[:3] == [b"TCP", address, b"0.0.0.0:0"]
            and fields[-1] == str(pid).encode("ascii")
            for line in result.stdout.splitlines()
            if (fields := line.split())
        )
    return result.returncode == 0 and b"n" + address in result.stdout.splitlines()


def _owns_linux_listener(pid: int, port: int) -> bool:
    """Match the Linux loopback socket inode against this child's open descriptors."""
    process = Path("/proc") / str(pid)
    try:
        with (process / "net/tcp").open(encoding="ascii") as stream:
            inodes = {
                fields[9]
                for line in stream
                if (fields := line.split()) and fields[1] == f"0100007F:{port:04X}" and fields[3] == "0A"
            }
        targets = {f"socket:[{inode}]" for inode in inodes}
        return bool(targets) and any(str(fd.readlink()) in targets for fd in (process / "fd").iterdir())
    except FileNotFoundError:
        return False
