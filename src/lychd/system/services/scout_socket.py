"""One pinned TCP connection with a gate at each connect/send syscall.

The synchronous host gate owns current authority and atomic budget debits. These
streams own numeric peer pinning, finite buffers, one absolute monotonic deadline,
and closure. They do not resolve names, retry contacts, or infer authority from a
target. TLS uses memory BIOs so OpenSSL never receives a network socket.
"""

# The two stream implementations and factories share private mechanics in this module.
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import errno
import math
import socket
import ssl
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from ipaddress import IPv6Address, ip_address
from pathlib import Path
from typing import Literal

from lychd.domain.scout.transport import FetchCode, FetchError, NetworkGate, NetworkHandoff, NetworkTarget

MAX_CHUNK_BYTES = 16 * 1024
MAX_APPLICATION_BYTES = 64 * 1024
MAX_RECEIVE_BYTES = 4 * 1024 * 1024
MAX_SEND_BYTES = 512 * 1024
MAX_HANDSHAKE_BYTES = 256 * 1024
_MAX_BIO_BYTES = 64 * 1024
_MAX_TLS_STEPS = 1024
_MAX_HOST_LENGTH = 253
_MAX_PORT = 65535
_CONNECT_PENDING = frozenset({errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, errno.EINTR})
type _SendPhase = Literal["dns", "tls", "http"]
type _SocketAddress = tuple[str, int] | tuple[str, int, int, int]


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise FetchError(FetchCode.TIMEOUT)
    return remaining


def _target_address(target: NetworkTarget, deadline: float) -> tuple[socket.AddressFamily, _SocketAddress]:
    if (
        type(target) is not NetworkTarget
        or type(deadline) not in {int, float}
        or not math.isfinite(deadline)
        or type(target.address) is not str
        or type(target.hostname) is not str
        or type(target.port) is not int
        or not 1 <= target.port <= _MAX_PORT
        or target.role not in {"resolver", "origin"}
        or not 1 <= len(target.hostname) <= _MAX_HOST_LENGTH
        or not target.hostname.isascii()
        or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:" for char in target.hostname
        )
        or "%" in target.address
    ):
        raise FetchError(FetchCode.CONFIG)
    try:
        address = ip_address(target.address)
    except ValueError:
        raise FetchError(FetchCode.DESTINATION) from None
    if str(address) != target.address:
        raise FetchError(FetchCode.DESTINATION)
    _remaining(deadline)
    if isinstance(address, IPv6Address):
        return socket.AF_INET6, (target.address, target.port, 0, 0)
    return socket.AF_INET, (target.address, target.port)


async def _ready(sock: socket.socket, deadline: float, *, writable: bool) -> None:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[None] = loop.create_future()
    descriptor = sock.fileno()

    def ready() -> None:
        if not future.done():
            future.set_result(None)

    if writable:
        loop.add_writer(descriptor, ready)
    else:
        loop.add_reader(descriptor, ready)
    try:
        async with asyncio.timeout(_remaining(deadline)):
            await future
    except TimeoutError:
        raise FetchError(FetchCode.TIMEOUT) from None
    finally:
        if writable:
            loop.remove_writer(descriptor)
        else:
            loop.remove_reader(descriptor)
    _remaining(deadline)


class PinnedTcpStream:
    """An owned numeric connection; its public send is DNS-only for a resolver."""

    def __init__(self, sock: socket.socket, target: NetworkTarget, gate: NetworkGate, deadline: float) -> None:
        """Use open_pinned_tcp to obtain a connected, peer-checked stream."""
        self._socket = sock
        self._target = target
        self._gate = gate
        self._deadline = deadline
        self._closed = False
        self._busy = False
        self._sent = 0
        self._received = 0

    @contextmanager
    def _operation(self) -> Generator[None]:
        if self._closed or self._busy:
            raise FetchError(FetchCode.PROTOCOL)
        self._busy = True
        try:
            _remaining(self._deadline)
            yield
        except ssl.SSLError:
            self.close()
            raise FetchError(FetchCode.TLS) from None
        except OSError:
            self.close()
            raise FetchError(FetchCode.TRANSPORT) from None
        except BaseException:
            self.close()
            raise
        finally:
            self._busy = False

    def _handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        active = True
        called = False
        results: list[int] = []

        def once() -> int:
            nonlocal called
            if not active or called:
                raise FetchError(FetchCode.EGRESS)
            called = True
            _remaining(self._deadline)
            result = action()
            results.append(result)
            return result

        try:
            observed = self._gate.handoff(handoff, once)
        finally:
            active = False
        if len(results) != 1 or type(observed) is not int or observed != results[0]:
            raise FetchError(FetchCode.EGRESS)
        return observed

    async def _connect(self, address: _SocketAddress) -> None:
        handoff = NetworkHandoff(self._target, "connect", b"", None)
        status = self._handoff(handoff, lambda: self._socket.connect_ex(address))
        if status in _CONNECT_PENDING:
            await _ready(self._socket, self._deadline, writable=True)
            status = self._socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if status != 0:
            raise FetchError(FetchCode.CONNECT)
        peer = self._socket.getpeername()
        try:
            matches = str(ip_address(peer[0])) == self._target.address and peer[1] == self._target.port
        except (ValueError, IndexError, TypeError):
            raise FetchError(FetchCode.PEER) from None
        if not matches:
            raise FetchError(FetchCode.PEER)

    async def _send_wire(self, data: bytes, phase: _SendPhase, application_bytes: bytes | None) -> None:
        offset = 0
        while offset < len(data):
            _remaining(self._deadline)
            fragment = data[offset : offset + MAX_CHUNK_BYTES]
            if self._sent + len(fragment) > MAX_SEND_BYTES:
                raise FetchError(FetchCode.LIMIT)
            handoff = NetworkHandoff(self._target, phase, fragment, application_bytes)
            try:
                count = self._handoff(handoff, lambda fragment=fragment: self._socket.send(fragment))
            except (BlockingIOError, InterruptedError):
                await _ready(self._socket, self._deadline, writable=True)
                continue
            if not 0 < count <= len(fragment):
                raise FetchError(FetchCode.TRANSPORT)
            offset += count
            self._sent += count

    async def _receive_wire(self, max_bytes: int) -> bytes:
        while True:
            _remaining(self._deadline)
            try:
                data = self._socket.recv(max_bytes)
            except (BlockingIOError, InterruptedError):
                await _ready(self._socket, self._deadline, writable=False)
                continue
            self._received += len(data)
            if self._received > MAX_RECEIVE_BYTES:
                raise FetchError(FetchCode.LIMIT)
            return data

    async def send(self, data: bytes) -> None:
        """Send one already prepared DNS-over-TCP message through the current gate."""
        with self._operation():
            if self._target.role != "resolver" or type(data) is not bytes or not 0 < len(data) <= MAX_APPLICATION_BYTES:
                raise FetchError(FetchCode.INPUT)
            await self._send_wire(data, "dns", data)

    async def receive(self, max_bytes: int = MAX_CHUNK_BYTES) -> bytes:
        """Read one finite chunk; framing and aggregate response bounds are upstream."""
        with self._operation():
            if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_CHUNK_BYTES:
                raise FetchError(FetchCode.INPUT)
            return await self._receive_wire(max_bytes)

    def close(self) -> None:
        """Close the raw socket without sending TLS alerts or application bytes."""
        if not self._closed:
            self._closed = True
            self._socket.close()


async def open_pinned_tcp(target: NetworkTarget, *, gate: NetworkGate, deadline: float) -> PinnedTcpStream:
    """Connect once to a canonical numeric target and verify its actual peer."""
    family, address = _target_address(target, deadline)
    if not callable(getattr(gate, "handoff", None)):
        raise FetchError(FetchCode.CONFIG)
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
    except OSError:
        raise FetchError(FetchCode.CONNECT) from None
    try:
        sock.settimeout(0.0)
        sock.set_inheritable(False)
        stream = PinnedTcpStream(sock, target, gate, deadline)
        await stream._connect(address)
    except OSError:
        sock.close()
        raise FetchError(FetchCode.CONNECT) from None
    except BaseException:
        sock.close()
        raise
    return stream


def _tls_context(ca_file: Path) -> ssl.SSLContext:
    if not ca_file.is_absolute() or not ca_file.is_file():
        raise FetchError(FetchCode.CONFIG)
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.hostname_checks_common_name = False
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.options |= ssl.OP_NO_RENEGOTIATION
        context.post_handshake_auth = False
        context.load_verify_locations(cafile=str(ca_file))
        context.set_alpn_protocols(["http/1.1"])
    except (OSError, ValueError):
        raise FetchError(FetchCode.CONFIG) from None
    return context


class PinnedTlsStream:
    """A verified HTTP/1.1 TLS stream with explicit gated ciphertext drainage."""

    def __init__(self, tcp: PinnedTcpStream, context: ssl.SSLContext) -> None:
        """Use open_pinned_tls; the SSLObject itself has no socket or I/O transport."""
        self._tcp = tcp
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        # CPython/OpenSSL verify IP identities here without placing an IP in SNI.
        self._tls = context.wrap_bio(self._incoming, self._outgoing, server_hostname=tcp._target.hostname)
        self._handshake_in = 0
        self._handshake_out = 0
        self._application_started = False

    async def _flush(self, phase: _SendPhase = "tls", application_bytes: bytes | None = None) -> None:
        if self._outgoing.pending > _MAX_BIO_BYTES:
            raise FetchError(FetchCode.LIMIT)
        while self._outgoing.pending:
            data = self._outgoing.read(MAX_CHUNK_BYTES)
            if phase == "tls":
                self._handshake_out += len(data)
                if self._handshake_out > MAX_HANDSHAKE_BYTES:
                    raise FetchError(FetchCode.LIMIT)
            await self._tcp._send_wire(data, phase, application_bytes)

    async def _feed(self, *, handshake: bool = False) -> None:
        data = await self._tcp._receive_wire(MAX_CHUNK_BYTES)
        if handshake:
            self._handshake_in += len(data)
            if self._handshake_in > MAX_HANDSHAKE_BYTES:
                raise FetchError(FetchCode.LIMIT)
        if self._incoming.pending + len(data) > _MAX_BIO_BYTES:
            raise FetchError(FetchCode.LIMIT)
        if data:
            self._incoming.write(data)
        else:
            self._incoming.write_eof()

    async def _handshake(self) -> None:
        with self._tcp._operation():
            for _ in range(_MAX_TLS_STEPS):
                _remaining(self._tcp._deadline)
                try:
                    self._tls.do_handshake()
                except ssl.SSLWantReadError:
                    await self._flush()
                    await self._feed(handshake=True)
                except ssl.SSLWantWriteError:
                    await self._flush()
                else:
                    await self._flush()
                    if self._tls.selected_alpn_protocol() not in {None, "http/1.1"}:
                        raise FetchError(FetchCode.TLS)
                    return
            raise FetchError(FetchCode.LIMIT)

    async def send(self, data: bytes) -> None:
        """Bind the sealed plaintext argument to every generated ciphertext fragment.

        The gate receives this exact full application value even after a partial
        socket write. Output generated by an SSL write operation is conservatively
        attributed to that application operation; the gate never decrypts/invents it.
        """
        with self._tcp._operation():
            if self._application_started:
                raise FetchError(FetchCode.PROTOCOL)
            self._application_started = True
            if type(data) is not bytes or not 0 < len(data) <= MAX_APPLICATION_BYTES:
                raise FetchError(FetchCode.INPUT)
            await self._flush()
            offset = 0
            for _ in range(_MAX_TLS_STEPS):
                _remaining(self._tcp._deadline)
                fragment = data[offset : offset + MAX_CHUNK_BYTES]
                try:
                    count = self._tls.write(fragment)
                except ssl.SSLWantReadError:
                    await self._flush("http", data)
                    await self._feed()
                except ssl.SSLWantWriteError:
                    await self._flush("http", data)
                else:
                    if not 0 < count <= len(fragment):
                        raise FetchError(FetchCode.TLS)
                    await self._flush("http", data)
                    offset += count
                    if offset == len(data):
                        return
            raise FetchError(FetchCode.LIMIT)

    async def receive(self, max_bytes: int = MAX_CHUNK_BYTES) -> bytes:
        """Return plaintext only after gating any TLS output generated while reading."""
        with self._tcp._operation():
            if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_CHUNK_BYTES:
                raise FetchError(FetchCode.INPUT)
            for _ in range(_MAX_TLS_STEPS):
                _remaining(self._tcp._deadline)
                try:
                    data = self._tls.read(max_bytes)
                except ssl.SSLWantReadError:
                    await self._flush()
                    await self._feed()
                except ssl.SSLWantWriteError:
                    await self._flush()
                except ssl.SSLZeroReturnError:
                    await self._flush()
                    return b""
                else:
                    await self._flush()
                    return data
            raise FetchError(FetchCode.LIMIT)

    def close(self) -> None:
        """Close without SSL unwrap/shutdown, which could generate ungated output."""
        self._tcp.close()


async def open_pinned_tls(
    target: NetworkTarget, *, gate: NetworkGate, deadline: float, ca_file: Path
) -> PinnedTlsStream:
    """Verify one pinned origin using only the supplied trust roots and host name."""
    _target_address(target, deadline)
    if target.role != "origin":
        raise FetchError(FetchCode.CONFIG)
    context = _tls_context(ca_file)
    tcp = await open_pinned_tcp(target, gate=gate, deadline=deadline)
    try:
        stream = PinnedTlsStream(tcp, context)
        await stream._handshake()
    except ssl.SSLError:
        tcp.close()
        raise FetchError(FetchCode.TLS) from None
    except BaseException:
        tcp.close()
        raise
    return stream
