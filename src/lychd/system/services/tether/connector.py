"""Explicit generation-bound broker streams; the catalog grants no application authority."""

# The broker carrier deliberately reuses the bounded stream mechanics.

from __future__ import annotations

import asyncio
import errno
import json
import math
import os
import re
import socket
import ssl
import stat
import struct
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from lychd.domain.scout.transport import FetchCode, FetchError, NetworkGate, NetworkHandoff, NetworkTarget
from lychd.domain.tether.models import TetherRoute, TetherSelection
from lychd.system.services import scout_socket

_ACK = b'{"version":1,"ok":true}\n'
_SOCKET_DEPTH = 2
_MAX_PRELUDE = 2048
_ROOT = Path("/run/lychd-tether")
_CATALOG = _ROOT / "catalog.json"
_MAX_CATALOG_BYTES = 1024 * 1024
_CATALOG_MODE = 0o600
_DIRECTORY_MODE = 0o700
_SOCKET_MODE = 0o600
_CATALOG_KEYS = {"schema", "version", "installation_epoch", "routes"}
_PENDING = {errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, errno.EINTR}


class _CurrentGate:
    def __init__(self, current: Callable[[], None], delegate: NetworkGate) -> None:
        self.current, self.delegate = current, delegate

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        self.current()
        return self.delegate.handoff(handoff, action)


class _BrokerStream(scout_socket.PinnedTcpStream):
    """AF_UNIX carrier retaining the existing finite TLS stream's syscall gates."""

    def _current(self) -> None:
        if not isinstance(self._gate, _CurrentGate):
            raise FetchError(FetchCode.CONFIG)
        self._gate.current()

    async def _receive_wire(self, max_bytes: int) -> bytes:
        self._current()
        result = await super()._receive_wire(max_bytes)
        self._current()
        return result

    async def wrap_tls(self, *, ca_file: Path) -> scout_socket.PinnedTlsStream:
        """Verify application TLS over this connected, gated broker carrier.

        Reuse the shared stream's exact target and trust policy; Tether owns
        only broker-carrier assembly and closure if that assembly fails.
        """
        try:
            # The broker reuses Scout's validator without acquiring a new IP socket.
            scout_socket._target_address(self._target, self._deadline)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            if self._target.role != "origin":
                raise FetchError(FetchCode.CONFIG)  # noqa: TRY301 - carrier owns failed assembly cleanup
            # Keep one CA/hostname/ALPN policy for both numeric and broker carriers.
            context = scout_socket._tls_context(ca_file)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            stream = scout_socket.PinnedTlsStream(self, context)
            # The shared TLS engine retains all syscall gates, bounds and deadline.
            await stream._handshake()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        except ssl.SSLError:
            self.close()
            raise FetchError(FetchCode.TLS) from None
        except BaseException:
            self.close()
            raise
        return stream

    async def connect_broker(self, path: str, header: bytes) -> None:
        handoff = NetworkHandoff(self._target, "connect", b"", None)
        status = self._handoff(handoff, lambda: self._socket.connect_ex(path))
        if status in _PENDING:
            loop = asyncio.get_running_loop()
            ready: asyncio.Future[None] = loop.create_future()
            descriptor = self._socket.fileno()

            def connected() -> None:
                if not ready.done():
                    ready.set_result(None)

            loop.add_writer(descriptor, connected)
            try:
                async with asyncio.timeout(max(0, self._deadline - time.monotonic())):
                    await ready
            except TimeoutError:
                raise FetchError(FetchCode.TIMEOUT) from None
            finally:
                loop.remove_writer(descriptor)
            status = self._socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if status:
            raise FetchError(FetchCode.CONNECT)
        credentials = self._socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        _, uid, _ = struct.unpack("3i", credentials)
        if uid != os.getuid():
            raise FetchError(FetchCode.PEER)
        # The prelude causes the broker's fixed TCP connect; it is egress-gated
        # as control traffic before TLS, with no application disclosure.
        await self._send_wire(header, "tls", None)
        acknowledgement = bytearray()
        while len(acknowledgement) < len(_ACK):
            data = await self._receive_wire(len(_ACK) - len(acknowledgement))
            if not data:
                raise FetchError(FetchCode.CONNECT)
            acknowledgement.extend(data)
        if bytes(acknowledgement) != _ACK:
            raise FetchError(FetchCode.PROTOCOL)


class TetherConnector:
    """Trusted assembly binds caller and fresh catalog; requests supply only a selection.

    The catalog reader must return current host-published admission, including an
    empty catalog while reconciliation is fenced. No connection pool is retained.
    """

    def __init__(
        self,
        *,
        catalog: Callable[[], tuple[TetherRoute, ...]],
        installation_epoch: str,
        caller: str,
    ) -> None:
        """Bind only trusted host assembly, never request-supplied caller metadata."""
        self.catalog = catalog
        self.installation_epoch = installation_epoch
        self.caller = caller

    @classmethod
    def from_catalog(cls, *, caller: str, catalog_path: Path = _CATALOG) -> TetherConnector:
        """Pin the installation epoch from trusted host assembly's catalog path."""
        epoch, _ = _read_catalog(catalog_path)

        def current_rows() -> tuple[TetherRoute, ...]:
            current_epoch, rows = _read_catalog(catalog_path)
            if current_epoch != epoch:
                raise FetchError(FetchCode.EGRESS)
            return rows

        return cls(catalog=current_rows, installation_epoch=epoch, caller=caller)

    def resolve(self, selection: TetherSelection) -> TetherRoute:
        """Require one exact current admitted tuple without address-based inference."""
        if type(selection) is not TetherSelection:
            raise FetchError(FetchCode.CONFIG)
        rows = self.catalog()
        matches = [row for row in rows if row.selection == selection]
        if len(matches) != 1:
            raise FetchError(FetchCode.DESTINATION)
        route = matches[0]
        if route.installation_epoch != self.installation_epoch or self.caller not in route.allowed_callers:
            raise FetchError(FetchCode.EGRESS)
        path = Path(route.socket_path)
        if not path.is_relative_to(_ROOT) or len(path.relative_to(_ROOT).parts) != _SOCKET_DEPTH or ".." in path.parts:
            raise FetchError(FetchCode.CONFIG)
        return route

    def current(self, route: TetherRoute) -> None:
        """Refuse changed epoch, policy, generation or destination on this stream."""
        if self.resolve(route.selection) != route:
            raise FetchError(FetchCode.EGRESS)

    async def open_tls(
        self,
        selection: TetherSelection,
        *,
        target: NetworkTarget,
        application_identity_ref: str,
        gate: NetworkGate,
        deadline: float,
        ca_file: Path,
    ) -> scout_socket.PinnedTlsStream:
        """Open only the compiler's socket, then verify end-to-end application TLS."""
        route = self.resolve(selection)
        if (
            target != NetworkTarget(route.address, route.port, route.hostname, "origin")
            or route.application_identity_ref != application_identity_ref
        ):
            raise FetchError(FetchCode.DESTINATION)
        if type(deadline) not in {int, float} or not math.isfinite(deadline) or deadline <= time.monotonic():
            raise FetchError(FetchCode.CONFIG)
        if not callable(getattr(gate, "handoff", None)):
            raise FetchError(FetchCode.CONFIG)
        path = Path(route.socket_path)
        self._check_socket(path)
        sock: socket.socket | None = None
        try:
            header = (
                json.dumps(
                    {
                        "version": 1,
                        "installation_epoch": route.installation_epoch,
                        "policy_digest": route.policy_digest,
                        **selection.model_dump(),
                        "caller": self.caller,
                    },
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("ascii")
                + b"\n"
            )
            if len(header) > _MAX_PRELUDE:
                raise FetchError(FetchCode.CONFIG)
            self.current(route)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(0.0)
            sock.set_inheritable(False)
        except OSError:
            if sock is not None:
                sock.close()
            raise FetchError(FetchCode.CONNECT) from None
        stream = _BrokerStream(sock, target, _CurrentGate(lambda: self.current(route), gate), deadline)
        try:
            await stream.connect_broker(str(path), header)
            self.current(route)
            tls = await stream.wrap_tls(ca_file=ca_file)
        except BaseException:
            stream.close()
            raise
        else:
            return tls

    @staticmethod
    def _check_socket(path: Path) -> None:
        try:
            if not os.statvfs(_ROOT).f_flag & os.ST_RDONLY:
                raise FetchError(FetchCode.CONFIG)
            for parent in (path.parent.parent, path.parent):
                metadata = parent.lstat()
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != _DIRECTORY_MODE
                ):
                    raise FetchError(FetchCode.CONFIG)
            metadata = path.lstat()
            if (
                not stat.S_ISSOCK(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != _SOCKET_MODE
            ):
                raise FetchError(FetchCode.CONFIG)
        except OSError:
            raise FetchError(FetchCode.CONFIG) from None


def _read_catalog(path: Path) -> tuple[str, tuple[TetherRoute, ...]]:
    """Read a bounded non-symlink owner-only publication through one descriptor."""
    try:
        if not path.is_absolute() or path.parent.resolve() != path.parent:
            raise FetchError(FetchCode.CONFIG)
        parent = path.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
            raise FetchError(FetchCode.CONFIG)
        if path == _CATALOG and not os.statvfs(path.parent).f_flag & os.ST_RDONLY:
            raise FetchError(FetchCode.CONFIG)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            metadata = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != _CATALOG_MODE
                or metadata.st_size > _MAX_CATALOG_BYTES
            ):
                raise FetchError(FetchCode.CONFIG)
            data = source.read(_MAX_CATALOG_BYTES + 1)
        if len(data) > _MAX_CATALOG_BYTES:
            raise FetchError(FetchCode.LIMIT)
        return _decode_catalog(data)
    except (OSError, ValueError, TypeError, RecursionError, ValidationError):
        raise FetchError(FetchCode.CONFIG) from None


def _decode_catalog(data: bytes) -> tuple[str, tuple[TetherRoute, ...]]:
    """Validate exact public catalog fields before narrowing their JSON types."""
    decoded: object = json.loads(data, object_pairs_hook=_unique_object)
    if type(decoded) is not dict:
        raise FetchError(FetchCode.CONFIG)
    record = cast("dict[str, object]", decoded)
    epoch = record.get("installation_epoch")
    raw_routes = record.get("routes")
    if (
        set(record) != _CATALOG_KEYS
        or record["schema"] != "lychd.tether.catalog"
        or type(record["version"]) is not int
        or record["version"] != 1
        or not isinstance(epoch, str)
        or re.fullmatch(r"[0-9a-f]{32}", epoch) is None
        or type(raw_routes) is not list
    ):
        raise FetchError(FetchCode.CONFIG)
    rows = tuple(
        TetherRoute.model_validate_json(json.dumps(row), strict=True) for row in cast("list[object]", raw_routes)
    )
    selections = {
        (
            row.selection.remote_lich_id,
            row.selection.attachment_id,
            row.selection.generation,
            row.selection.service_id,
        )
        for row in rows
    }
    if any(row.installation_epoch != epoch for row in rows) or len(selections) != len(rows):
        raise FetchError(FetchCode.CONFIG)
    return epoch, rows


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise FetchError(FetchCode.CONFIG)
        result[name] = value
    return result
