"""Hold native unit exit metadata on the same manager used by host control.

The synchronous owner keeps one asyncio loop and one full-bus connection alive
while host commands run. Exchanges have deadlines; the held reference has no
independent lifetime timeout. Importing this module does not import D-Bus.
"""

from __future__ import annotations

import asyncio
import os
import re
import socket
import stat
import struct
from collections.abc import Coroutine, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, TypeVar
from urllib.parse import quote

from lychd.system.operator.models import OperatorAuthorityError

if TYPE_CHECKING:
    from dbus_fast import Message
    from dbus_fast.aio import MessageBus

_NATIVE_UNIT = "lychd-uncaged-vessel.service"
_DAEMON = "org.freedesktop.DBus"
_DAEMON_PATH = "/org/freedesktop/DBus"
_MANAGER = "org.freedesktop.systemd1"
_MANAGER_PATH = "/org/freedesktop/systemd1"
_MANAGER_INTERFACE = "org.freedesktop.systemd1.Manager"
_EXCHANGE_SECONDS = 5.0
_UNREF_SECONDS = 2.0
_CLOSE_SECONDS = 1.0
_PEER_SECONDS = 1.0
_UNIQUE_NAME = re.compile(r":[0-9]+(?:\.[0-9]+)+\Z")
_UNIX_PATH_BYTES = 107
_PRIVATE_DIRECTORY_MODE = 0o700
_MAX_BUS_NAME_LENGTH = 255
_T = TypeVar("_T")


class ExitReference(Protocol):
    """A held native exit-evidence lifetime, checked before further effects."""

    def verify(self) -> None:
        """Refuse unless the original reference and manager remain live."""


@dataclass(frozen=True)
class _ManagerPeer:
    pid: int
    uid: int


def _refuse(stage: str) -> NoReturn:
    message = f"Native exit evidence {stage} could not be verified."
    raise OperatorAuthorityError(message) from None


def _runtime_directory(runtime_dir: Path | None) -> Path:
    value = os.environ.get("XDG_RUNTIME_DIR") if runtime_dir is None else os.fspath(runtime_dir)
    if not value or "\0" in value:
        _refuse("runtime")
    path = Path(value)
    try:
        info = path.lstat()
        valid = (
            path.is_absolute()
            and path.resolve(strict=True) == path
            and stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == _PRIVATE_DIRECTORY_MODE
            and len(os.fsencode(path / "systemd" / "private")) <= _UNIX_PATH_BYTES
        )
    except (OSError, ValueError, RuntimeError):
        _refuse("runtime")
    if not valid:
        _refuse("runtime")
    return path


def _private_peer(runtime: Path) -> _ManagerPeer:
    """Observe the authenticated Unix peer without issuing a manager request."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(_PEER_SECONDS)
        peer.connect(os.fspath(runtime / "systemd" / "private"))
        credentials = peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    pid, uid, _gid = struct.unpack("3i", credentials)
    if pid <= 0 or uid != os.getuid():
        _refuse("manager identity")
    return _ManagerPeer(pid, uid)


def _new_bus(address: str) -> MessageBus:
    """Construct only the fixed Unix transport on the owner's running loop."""
    from dbus_fast.aio import MessageBus
    from dbus_fast.auth import AuthExternal

    return MessageBus(
        bus_address=address,
        auth=AuthExternal(),
        negotiate_unix_fd=False,
        auth_timeout=_EXCHANGE_SECONDS,
    )


def _unique_name(value: object) -> bool:
    return isinstance(value, str) and len(value) <= _MAX_BUS_NAME_LENGTH and _UNIQUE_NAME.fullmatch(value) is not None


def _validate_reply(
    reply: Message | None,
    *,
    serial: int,
    sender: str,
    destination: str,
    signature: str,
) -> list[Any]:
    from dbus_fast import MessageType

    if (
        reply is None
        or reply.message_type is not MessageType.METHOD_RETURN
        or reply.reply_serial != serial
        or reply.sender != sender
        or reply.destination != destination
        or reply.error_name is not None
        or reply.signature != signature
        or reply.unix_fds
        or type(reply.body) is not list
    ):
        _refuse("reply")
    return reply.body


class _NativeExitReference:
    def __init__(self, runner: asyncio.Runner, runtime: Path, *, from_environment: bool) -> None:
        self._runner = runner
        self._runtime = runtime
        self._from_environment = from_environment
        self._bus: MessageBus | None = None
        self._connected = False
        self._pinned = False
        self._closed = False
        self._owner = ""
        self._peer: _ManagerPeer | None = None

    def _run(self, operation: Coroutine[Any, Any, _T], stage: str) -> _T:
        try:
            return self._runner.run(operation)
        except Exception:  # noqa: BLE001 - fixed operator errors fence transport details.
            _refuse(stage)

    def acquire(self) -> None:
        self._run(self._acquire(), "acquisition")

    async def _acquire(self) -> None:
        async with asyncio.timeout(_EXCHANGE_SECONDS):
            self._peer = _private_peer(self._runtime)
            self._bus = _new_bus("unix:path=" + quote(os.fspath(self._runtime / "bus"), safe="/"))
            hello: list[Message] = []

            def capture_hello(message: Message) -> None:
                if message.reply_serial == 1:
                    hello.append(message)

            # dbus-fast 5.2 starts a new connection with Hello at serial 1.
            self._bus.add_message_handler(capture_hello)
            try:
                await self._bus.connect()
                self._connected = True
            finally:
                self._bus.remove_message_handler(capture_hello)
            name = self._bus.unique_name
            if not _unique_name(name) or len(hello) != 1 or name is None:
                _refuse("connection identity")
            body = _validate_reply(hello[0], serial=1, sender=_DAEMON, destination=name, signature="s")
            if body != [name]:
                _refuse("connection identity")
            self._owner = await self._manager_owner()
            await self._check_manager()
            await self._manager_call("RefUnit")
            self._pinned = True
            await self._verify_live()

    async def _call(
        self,
        *,
        destination: str,
        path: str,
        interface: str,
        member: str,
        signature: str = "",
        body: list[Any] | None = None,
        reply_signature: str = "",
    ) -> list[Any]:
        from dbus_fast import Message

        bus = self._bus
        if bus is None or not bus.connected or bus.unique_name is None:
            _refuse("connection")
        request = Message(
            destination=destination,
            path=path,
            interface=interface,
            member=member,
            signature=signature,
            body=[] if body is None else body,
        )
        reply = await bus.call(request)
        return _validate_reply(
            reply,
            serial=request.serial,
            sender=destination,
            destination=bus.unique_name,
            signature=reply_signature,
        )

    async def _daemon_call(self, member: str, value: str, reply_signature: str) -> list[Any]:
        return await self._call(
            destination=_DAEMON,
            path=_DAEMON_PATH,
            interface=_DAEMON,
            member=member,
            signature="s",
            body=[value],
            reply_signature=reply_signature,
        )

    async def _manager_owner(self) -> str:
        body = await self._daemon_call("GetNameOwner", _MANAGER, "s")
        if len(body) != 1 or not _unique_name(body[0]):
            _refuse("manager identity")
        return str(body[0])

    async def _check_manager(self) -> None:
        if await self._manager_owner() != self._owner:
            _refuse("manager continuity")
        pid = await self._daemon_call("GetConnectionUnixProcessID", self._owner, "u")
        uid = await self._daemon_call("GetConnectionUnixUser", self._owner, "u")
        peer = self._peer
        if (
            peer is None
            or len(pid) != 1
            or len(uid) != 1
            or type(pid[0]) is not int
            or type(uid[0]) is not int
            or pid[0] != peer.pid
            or uid[0] != peer.uid
            or _private_peer(self._runtime) != peer
        ):
            _refuse("manager identity")

    async def _manager_call(self, member: str) -> None:
        body = await self._call(
            destination=self._owner,
            path=_MANAGER_PATH,
            interface=_MANAGER_INTERFACE,
            member=member,
            signature="s",
            body=[_NATIVE_UNIT],
        )
        if body:
            _refuse("reply")

    async def _verify_live(self) -> None:
        current = _runtime_directory(None if self._from_environment else self._runtime)
        if current != self._runtime or not self._pinned:
            _refuse("runtime continuity")
        await self._check_manager()
        body = await self._call(
            destination=self._owner,
            path=_MANAGER_PATH,
            interface="org.freedesktop.DBus.Peer",
            member="Ping",
        )
        if body:
            _refuse("reply")

    def verify(self) -> None:
        if self._closed:
            _refuse("reference lifetime")
        self._run(self._verify(), "continuity")

    async def _verify(self) -> None:
        async with asyncio.timeout(_EXCHANGE_SECONDS):
            await self._verify_live()

    def close(self) -> None:
        self._run(self._close(), "release or close")

    async def _close(self) -> None:
        """Attempt release and local close independently, retaining uncertainty."""
        self._closed = True
        failure: BaseException | None = None
        try:
            if self._pinned:
                async with asyncio.timeout(_UNREF_SECONDS):
                    await self._manager_call("UnrefUnit")
        except BaseException as exc:  # noqa: BLE001 - closing must survive primary cancellation.
            failure = exc
        finally:
            self._pinned = False
        bus = self._bus
        if bus is not None:
            try:
                bus.disconnect()
                # Failed/cancelled connect closes its own socket in dbus-fast;
                # its disconnect future never settles on that path.
                if self._connected:
                    async with asyncio.timeout(_CLOSE_SECONDS):
                        await bus.wait_for_disconnect()
            except BaseException as exc:  # noqa: BLE001 - finish local close before propagating cancellation.
                failure = failure or exc
                with suppress(Exception):
                    # Pinned dbus-fast 5.2 fallback closes local descriptors and
                    # removes loop readers. Needing it always remains failure.
                    bus._finalize()  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        if failure is not None:
            if not isinstance(failure, Exception):
                raise failure
            _refuse("release or close")


@contextmanager
def hold_native_exit(*, runtime_dir: Path | None = None) -> Generator[ExitReference]:
    """Pin exact native exit metadata until the caller's decision completes.

    Production uses the validated current ``XDG_RUNTIME_DIR`` for both sockets,
    matching systemctl's private user-manager route. Explicit runtime injection
    requires the caller to bind its process runner to that same runtime.
    """
    runtime = _runtime_directory(runtime_dir)
    runner = asyncio.Runner()
    reference = _NativeExitReference(runner, runtime, from_environment=runtime_dir is None)
    primary: BaseException | None = None
    try:
        reference.acquire()
        yield reference
    except BaseException as exc:
        primary = exc
        raise
    finally:
        cleanup: BaseException | None = None
        try:
            reference.close()
        except BaseException as exc:  # noqa: BLE001 - preserve primary failure while closing loop.
            cleanup = exc
        try:
            runner.close()
        except BaseException as exc:  # noqa: BLE001 - cleanup uncertainty must refuse success.
            cleanup = cleanup or exc
        if cleanup is not None:
            if primary is not None:
                primary.add_note("Native exit evidence release or close could not be verified.")
            elif isinstance(cleanup, Exception):
                _refuse("release or close")
            else:
                raise cleanup
