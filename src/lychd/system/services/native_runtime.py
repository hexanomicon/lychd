"""Personal process and pre-provisioned container ownership for one desktop installation."""

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
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from lychd.domain.animation.conflicts import build_conflict_topology
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.desktop.private import check_path, verify_private_directory, verify_private_file
from lychd.system.services.desktop_container import DesktopContainer, UnsettledContainerError
from lychd.system.services.native_llama import native_llama_command

if TYPE_CHECKING:
    from typing import BinaryIO

    from lychd.config.settings.orchestration import SwitchingSettings
    from lychd.domain.animation.protocols import CapabilityRegistry
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.domain.orchestration.containment import SoftActivationRecord

_RESTORED = 2
_WINDOWS_TCP_COLUMNS = 5
_UNSETTLED = (
    "Native runtime ownership is unresolved. Stop Core, inspect the private native.sqlite3 journal, "
    "reconcile each recorded process, container incarnation, and pending transition before archiving the journal."
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

    One host owner holds the state-directory lock for this actuator's lifetime. No stored PID is
    used as termination authority. A crash with a live or pending owner fences startup.
    """

    def __init__(self, registry: CapabilityRegistry, settings: SwitchingSettings) -> None:
        """Open the installation journal before accepting native work."""
        directory = settings.native_state_dir
        if directory is None or not directory.is_dir():
            msg = "Native runtime requires an existing private native_state_dir."
            raise RuntimePreconditionError(msg)
        try:
            verify_private_directory(directory)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            msg = "Native runtime requires a verified owner-only state directory."
            raise RuntimePreconditionError(msg) from exc
        self._journal = directory / "native.sqlite3"
        for suffix in ("", "-journal", "-wal", "-shm"):
            journal_file = directory / f"native.sqlite3{suffix}"
            try:
                info = journal_file.lstat()
            except FileNotFoundError:
                continue
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                msg = "Native journal files must be regular, singly linked files."
                raise RuntimePreconditionError(msg)
        self._registry = registry
        self._settings = settings
        self._containers = {
            binding.animator: DesktopContainer(binding, timeout=settings.systemctl_timeout_s)
            for binding in settings.containers
        }
        self._incarnations: dict[str, str] = {}
        self._scratch: dict[str, TemporaryDirectory[str]] = {}
        self._children: dict[str, subprocess.Popen[bytes]] = {}
        self._lock = asyncio.Lock()
        self._endpoints: dict[str, asyncio.Server] = {}
        self._upstreams: dict[str, int] = {}
        self._connections: set[asyncio.Task[None]] = set()
        self._owner = self._acquire_owner(directory)
        try:
            self._initialize_journal()
        except BaseException:
            self._owner.close()
            raise

    @staticmethod
    def _acquire_owner(directory: Path) -> BinaryIO:
        """Exclude every native Vessel and desktop Reactor sharing these effects."""
        path = directory / "native-owner.lock"
        check_path(path)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        stream = os.fdopen(os.open(path, flags, 0o600), "r+b")
        try:
            verify_private_file(path)
            if not os.path.samestat(os.fstat(stream.fileno()), path.lstat()):
                message = "Native ownership lock changed while opening."
                raise RuntimePreconditionError(message)  # noqa: TRY301 - release this descriptor on every failure
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            message = "Native runtime ownership is unresolved: another host owner holds the installation lock."
            raise RuntimePreconditionError(message) from exc
        except BaseException:
            stream.close()
            raise
        return stream

    def _initialize_journal(self) -> None:
        with closing(sqlite3.connect(self._journal)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS transition (id TEXT PRIMARY KEY, intent TEXT NOT NULL, done INTEGER NOT NULL)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS child (name TEXT PRIMARY KEY, pid INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS container (name TEXT PRIMARY KEY, incarnation TEXT NOT NULL)")
            if db.execute(
                "SELECT 1 FROM child UNION ALL SELECT 1 FROM container UNION ALL SELECT 1 FROM transition WHERE done=0"
            ).fetchone():
                raise RuntimeError(_UNSETTLED)

    def _command(self, name: str) -> tuple[list[str], int]:
        return native_llama_command(self._registry.get_soulstone_rune(name), self._settings, name=name)

    async def verify_startup(self) -> None:
        """Reserve configured loopback endpoints before any registry observation."""
        self._require_owner()
        try:
            runes = self._bound_runes()
            public_ports = {rune.port for rune in runes}
            for rune in runes:
                port = await self._public_port(rune, public_ports)
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

    def _bound_runes(self) -> list[SoulstoneConfig]:
        runes = self._registry.list_soulstone_runes()
        expected = {rune.name for rune in runes if rune.placement == "container"}
        if expected != self._containers.keys():
            message = "Each explicit desktop container Soulstone requires its exact local binding."
            raise RuntimePreconditionError(message)
        return runes

    async def _public_port(self, rune: SoulstoneConfig, public_ports: set[int | None]) -> int:
        container = self._containers.get(rune.name)
        if container is None:
            _, port = self._command(rune.name)
            return port
        port = rune.port
        if (
            not rune.concurrency.dedicated
            or rune.concurrency.persistent_resident
            or port is None
            or str(rune.base_url).rstrip("/") != f"http://127.0.0.1:{port}/v1"
            or container.binding.host_port in public_ports
            or any(spec.is_dynamic for spec in self._registry.list_capabilities() if spec.animator_name == rune.name)
        ):
            message = (
                "Desktop container requires a dedicated fixed model, distinct upstream and explicit loopback endpoint."
            )
            raise RuntimePreconditionError(message)
        await asyncio.to_thread(container.verify_engine)
        if await asyncio.to_thread(container.observe) is not None:
            message = "Cannot adopt a previously running desktop container."
            raise RuntimePreconditionError(message)
        return port

    def _connect(self, name: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.create_task(self._forward(name, reader, writer))
        self._connections.add(task)
        task.add_done_callback(self._connections.discard)

    async def _forward(self, name: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        child = self._children.get(name)
        port = self._upstreams.get(name)
        upstream: asyncio.StreamWriter | None = None
        try:
            if container := self._containers.get(name):
                incarnation = self._incarnations.get(name)
                if incarnation is None:
                    return
                async with asyncio.timeout(self._settings.warmup_timeout_s):
                    source, upstream = await container.connect(incarnation)
                if self._incarnations.get(name) != incarnation:
                    return
            else:
                if child is None or child.poll() is not None or port is None:
                    return
                source, upstream = await asyncio.open_connection("127.0.0.1", port)
                if not await asyncio.to_thread(_owns_listener, child.pid, port) or child.poll() is not None:
                    return
            async with asyncio.TaskGroup() as group:
                group.create_task(_pipe(reader, upstream))
                group.create_task(_pipe(source, writer))
        except (OSError, RuntimeError, ValueError, ExceptionGroup, subprocess.SubprocessError):
            return
        finally:
            if upstream is not None:
                upstream.close()
            writer.close()

    async def apply(self, intent: TransitionIntent) -> None:
        async with self._lock:
            self._require_owner()
            with closing(sqlite3.connect(self._journal)) as db:
                db.execute("BEGIN IMMEDIATE")
                if await self._replayed(db, intent):
                    return
                prior = await self._active(db)
                self._validate(db, intent, prior)
                for name in (*intent.evict_animators, *intent.launch_animators):
                    if name in self._containers:
                        await asyncio.to_thread(self._containers[name].verify_engine)
                    else:
                        self._command(name)
                    if name not in self._endpoints:
                        message = "Native endpoint has not been reserved or is occupied."
                        raise RuntimePreconditionError(message)
                with db:
                    db.execute(
                        "INSERT INTO transition VALUES (?, ?, 0)", (intent.transition_id, intent.model_dump_json())
                    )
                if self._containers:
                    await self._mixed_transition(db, intent, prior)
                else:
                    await self._switch(db, intent)
                with db:
                    db.execute("UPDATE transition SET done=1 WHERE id=?", (intent.transition_id,))

    def _require_owner(self) -> None:
        if self._owner.closed:
            message = "Native runtime owner has been closed."
            raise RuntimePreconditionError(message)

    async def recover(self, intent: TransitionIntent) -> None:
        """Revalidate the recorded result or retry only before a local effect claim exists."""
        await self.apply(intent)

    async def _switch(self, db: sqlite3.Connection, intent: TransitionIntent) -> None:
        for name in intent.evict_animators:
            await self._stop(db, name)
        if self._containers and await self._active(db) != set(intent.expected_active_animators) - set(
            intent.evict_animators
        ):
            raise UnsettledContainerError(_UNSETTLED)
        for name in intent.launch_animators:
            await self._start(db, name)
        desired = (set(intent.expected_active_animators) - set(intent.evict_animators)) | set(intent.launch_animators)
        if await self._active(db) != desired:
            raise RuntimeError(_UNSETTLED)

    async def _mixed_transition(self, db: sqlite3.Connection, intent: TransitionIntent, prior: set[str]) -> None:
        task = asyncio.create_task(self._switch(db, intent))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            # Never restore while an engine command can still change the world.
            try:
                await complete_under_cancellation(task)
            except UnsettledContainerError:
                raise
            except Exception as operation_error:  # noqa: BLE001 - reobserve before restoration
                exc.add_note(f"Switch before cancellation failed: {operation_error!r}")
            await complete_under_cancellation(self._restore(db, intent, prior))
            message = "Mixed switch cancelled and prior world restored."
            raise RuntimeCancellationRestoredError(message) from exc
        except UnsettledContainerError:
            raise
        except Exception as exc:
            await complete_under_cancellation(self._restore(db, intent, prior))
            message = "Mixed switch failed and prior world was restored."
            raise RuntimeActuationRestoredError(message) from exc

    async def _restore(self, db: sqlite3.Connection, intent: TransitionIntent, prior: set[str]) -> None:
        try:
            current = await self._active(db)
            if (current ^ prior) - {*intent.evict_animators, *intent.launch_animators}:
                raise RuntimeError(_UNSETTLED)
            for name in sorted(current - prior):
                await self._stop(db, name)
            for name in sorted(prior - current):
                await self._start(db, name)
            if await self._active(db) != prior:
                raise RuntimeError(_UNSETTLED)
        except RuntimePreconditionError as exc:
            # After an effect, a failed restoration prerequisite can never become a no-effect decline.
            raise RuntimeError(_UNSETTLED) from exc
        with db:
            db.execute("UPDATE transition SET done=2 WHERE id=?", (intent.transition_id,))

    async def _start(self, db: sqlite3.Connection, name: str) -> None:
        if container := self._containers.get(name):
            incarnation = await asyncio.to_thread(container.change, "start")
            if incarnation is None:
                raise UnsettledContainerError(_UNSETTLED)
            self._incarnations[name] = incarnation
            with db:
                db.execute("INSERT INTO container VALUES (?, ?)", (name, incarnation))
            return
        args, _ = self._command(name)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
        args[args.index("--port") + 1] = str(port)
        scratch = TemporaryDirectory(prefix="engine-", dir=self._journal.parent)
        try:
            child = self._launch(args, Path(scratch.name))
        except BaseException:
            scratch.cleanup()
            raise
        self._scratch[name] = scratch
        self._children[name] = child
        with db:
            db.execute("INSERT INTO child VALUES (?, ?)", (name, child.pid))
        try:
            await self._await_listener(child, port)
        except BaseException as exc:
            try:
                await self._stop(db, name)
            except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError) as cleanup_error:
                exc.add_note(f"Native child cleanup failed for {name!r}: {cleanup_error!r}")
            raise
        self._upstreams[name] = port

    @staticmethod
    def _launch(args: list[str], scratch: Path) -> subprocess.Popen[bytes]:
        """Start the configured engine with private home, cache and temporary paths."""
        env: dict[str, str] = dict.fromkeys(
            ("HOME", "USERPROFILE", "TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"), str(scratch)
        )
        if os.name == "nt":
            env.update({key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ})
            env.update(APPDATA=str(scratch), LOCALAPPDATA=str(scratch))
        return subprocess.Popen(  # noqa: S603 - fixed executable and typed extension planner
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=scratch,
            close_fds=True,
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
        row = db.execute("SELECT intent, done FROM transition WHERE id=?", (intent.transition_id,)).fetchone()
        if row is None:
            return False
        if row[0] != intent.model_dump_json():
            msg = "Native transition ID was reused with a different intent."
            raise RuntimePreconditionError(msg)
        live = await self._active(db)
        if row[1] == _RESTORED:
            if live != set(
                intent.expected_active_animators
            ) or intent.config_generation != capability_config_generation(self._registry):
                message = "Restored transition no longer matches the prior world."
                raise RuntimePreconditionError(message)
            message = "The recorded mixed transition restored its prior world."
            raise RuntimeActuationRestoredError(message)
        desired = (set(intent.expected_active_animators) - set(intent.evict_animators)) | set(intent.launch_animators)
        if desired != live or intent.config_generation != capability_config_generation(self._registry):
            msg = "Completed native transition no longer matches the current configuration or active processes."
            raise RuntimePreconditionError(msg)
        return True

    async def _active(self, db: sqlite3.Connection) -> set[str]:
        """Observe every bound owner and match running incarnations to the private journal."""
        children = self._owned_processes(db)
        for name, pid in children.items():
            port = self._upstreams.get(name)
            if (
                port is None
                or not await asyncio.to_thread(_owns_listener, pid, port)
                or self._children[name].poll() is not None
            ):
                raise RuntimeError(_UNSETTLED)
        if dict(db.execute("SELECT name, incarnation FROM container")) != self._incarnations:
            raise RuntimeError(_UNSETTLED)
        for name, container in self._containers.items():
            observed = await asyncio.to_thread(container.observe)
            if observed != self._incarnations.get(name):
                raise UnsettledContainerError(_UNSETTLED)
        return set(children) | set(self._incarnations)

    def _owned_processes(self, db: sqlite3.Connection) -> dict[str, int]:
        recorded = dict(db.execute("SELECT name, pid FROM child"))
        live = {name: child.pid for name, child in self._children.items() if child.poll() is None}
        if recorded != live or live.keys() != self._children.keys():
            raise RuntimeError(_UNSETTLED)
        return live

    def _validate(self, db: sqlite3.Connection, intent: TransitionIntent, live: set[str]) -> None:
        spec = self._registry.get_capability(intent.target_capability_key)
        if (
            spec is None
            or spec.animator_name != intent.target_animator
            or intent.config_generation != capability_config_generation(self._registry)
        ):
            msg = "Native transition target or configuration generation is stale."
            raise RuntimePreconditionError(msg)
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
        if container := self._containers.get(name):
            if not (owned := self._incarnations.get(name)) or await asyncio.to_thread(container.observe) != owned:
                raise UnsettledContainerError(_UNSETTLED)
            await asyncio.to_thread(container.change, "stop", expected=owned)
            del self._incarnations[name]
            with db:
                db.execute("DELETE FROM container WHERE name=? AND incarnation=?", (name, owned))
            return
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
        self._scratch.pop(name).cleanup()

    async def aclose(self) -> None:
        """Stop only children of this instance before releasing its installation lock."""
        async with self._lock:
            if self._owner.closed:
                return
            try:
                await complete_under_cancellation(self._close_owned_services())
            finally:
                self._owner.close()

    async def _close_owned_services(self) -> None:
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
            for name in (*self._children, *self._incarnations):
                await self._stop(db, name)


async def _pipe(source: asyncio.StreamReader, target: asyncio.StreamWriter) -> None:
    while data := await source.read(65536):
        target.write(data)
        await target.drain()
    if target.can_write_eof():
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
