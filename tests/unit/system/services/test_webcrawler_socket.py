"""Controlled socket/TLS substitutes, not real peer or network-gate qualification."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import errno
import socket
import ssl
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services import scout_socket as transport


class Gate:
    def __init__(self) -> None:
        self.calls: list[NetworkHandoff] = []
        self.actions: list[Callable[[], int]] = []
        self.allowed = True

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        self.calls.append(handoff)
        self.actions.append(action)
        if not self.allowed:
            raise FetchError(FetchCode.EGRESS)
        return action()


@pytest.fixture
def target() -> NetworkTarget:
    return NetworkTarget("192.0.2.10", 53, "resolver.example", "resolver")


@pytest.fixture
def raw(monkeypatch: pytest.MonkeyPatch, target: NetworkTarget) -> Mock:
    original_socket = socket.socket
    sock = Mock(spec=socket.socket)
    sock.connect_ex.return_value = 0
    sock.getpeername.return_value = (target.address, target.port)
    sock.send.side_effect = len
    sock.recv.return_value = b"reply"

    def create_socket(
        family: int = -1,
        sock_type: int = -1,
        proto: int = -1,
        fileno: int | None = None,
    ) -> socket.socket:
        if family in {socket.AF_INET, socket.AF_INET6}:
            return cast("socket.socket", sock)
        # asyncio owns a local UNIX wakeup pair; it is outside the mocked IP path.
        return original_socket(family, sock_type, proto, fileno=fileno)

    monkeypatch.setattr(transport.socket, "socket", create_socket)
    monkeypatch.setattr(transport.socket, "getaddrinfo", Mock(side_effect=AssertionError("No ambient DNS")))
    return sock


@pytest.mark.asyncio
async def test_single_numeric_connect_then_gated_dns_bytes(raw: Mock, target: NetworkTarget) -> None:
    gate = Gate()
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    await stream.send(b"\0\x03dns")
    assert await stream.receive(10) == b"reply"
    raw.connect_ex.assert_called_once_with((target.address, target.port))
    raw.settimeout.assert_called_once_with(0.0)
    assert raw.set_inheritable.call_args.args == (False,)
    assert [call.phase for call in gate.calls] == ["connect", "dns"]
    assert gate.calls[0].wire_bytes == b""
    assert gate.calls[1].wire_bytes == b"\0\x03dns"
    assert gate.calls[1].application_bytes == b"\0\x03dns"
    stream.close()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_partial_send_and_would_block_get_fresh_exact_handoffs(
    raw: Mock,
    target: NetworkTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw.send.side_effect = [2, BlockingIOError(errno.EWOULDBLOCK, "private error"), 3]
    ready = AsyncMock()
    monkeypatch.setattr(transport, "_ready", ready)
    gate = Gate()
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    await stream.send(b"abcde")
    assert [call.wire_bytes for call in gate.calls[1:]] == [b"abcde", b"cde", b"cde"]
    assert all(call.application_bytes == b"abcde" for call in gate.calls[1:])
    ready.assert_awaited_once()
    raw.connect_ex.assert_called_once()
    stream.close()


@pytest.mark.asyncio
async def test_revocation_during_readiness_wait_prevents_next_actual_send(
    raw: Mock,
    target: NetworkTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = Gate()
    raw.send.side_effect = [2, BlockingIOError()]

    async def revoke(*args: object, **kwargs: object) -> None:
        gate.allowed = False

    monkeypatch.setattr(transport, "_ready", revoke)
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    with pytest.raises(FetchError) as error:
        await stream.send(b"abcde")
    assert error.value.code is FetchCode.EGRESS
    assert raw.send.call_count == 2
    assert gate.calls[-1].wire_bytes == b"cde"
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_gate_cannot_replay_retained_action(raw: Mock, target: NetworkTarget) -> None:
    gate = Gate()
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    with pytest.raises(FetchError) as error:
        gate.actions[0]()
    assert error.value.code is FetchCode.EGRESS
    raw.connect_ex.assert_called_once()
    stream.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("behavior", ["omit", "twice", "forge"])
async def test_gate_must_execute_exactly_once_and_return_actual_result(
    raw: Mock,
    target: NetworkTarget,
    behavior: str,
) -> None:
    class BadGate:
        def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
            _ = handoff
            if behavior == "omit":
                return 0
            action()
            if behavior == "twice":
                return action()
            return 10

    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tcp(target, gate=BadGate(), deadline=time.monotonic() + 1)
    assert error.value.code is FetchCode.EGRESS
    assert raw.connect_ex.call_count == (0 if behavior == "omit" else 1)
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_peer_mismatch_closes_before_any_application_bytes(raw: Mock, target: NetworkTarget) -> None:
    raw.getpeername.return_value = ("192.0.2.11", 53)
    gate = Gate()
    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    assert error.value.code is FetchCode.PEER
    assert [call.phase for call in gate.calls] == ["connect"]
    raw.send.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("address", ["example.com", "192.000.2.10", "fe80::1%eth0", "2001:DB8::1"])
async def test_noncanonical_or_nonnumeric_address_never_connects(raw: Mock, address: str) -> None:
    target = NetworkTarget(address, 53, "resolver.example", "resolver")
    with pytest.raises(FetchError):
        await transport.open_pinned_tcp(target, gate=Gate(), deadline=time.monotonic() + 1)
    raw.connect_ex.assert_not_called()


@pytest.mark.asyncio
async def test_connect_pending_uses_one_connect_and_checks_completion(
    raw: Mock,
    target: NetworkTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw.connect_ex.return_value = errno.EINPROGRESS
    raw.getsockopt.return_value = errno.ECONNREFUSED
    ready = AsyncMock()
    monkeypatch.setattr(transport, "_ready", ready)
    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tcp(target, gate=Gate(), deadline=time.monotonic() + 1)
    assert error.value.code is FetchCode.CONNECT
    raw.connect_ex.assert_called_once()
    ready.assert_awaited_once()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_cancelled_connect_wait_closes_owned_socket(
    raw: Mock,
    target: NetworkTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw.connect_ex.return_value = errno.EINPROGRESS
    entered = asyncio.Event()

    async def pending(*args: object, **kwargs: object) -> None:
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(transport, "_ready", pending)
    task = asyncio.create_task(transport.open_pinned_tcp(target, gate=Gate(), deadline=time.monotonic() + 1))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    raw.close.assert_called_once()
    raw.connect_ex.assert_called_once()


@pytest.mark.asyncio
async def test_readiness_cancellation_removes_registered_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.create_future.return_value = asyncio.get_running_loop().create_future()
    monkeypatch.setattr(transport.asyncio, "get_running_loop", Mock(return_value=loop))
    sock = Mock(spec=socket.socket)
    sock.fileno.return_value = 321
    task = asyncio.create_task(transport._ready(sock, time.monotonic() + 1, writable=False))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    loop.add_reader.assert_called_once()
    loop.remove_reader.assert_called_once_with(321)


@pytest.mark.asyncio
async def test_expired_deadline_refuses_before_socket_creation(raw: Mock, target: NetworkTarget) -> None:
    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tcp(target, gate=Gate(), deadline=time.monotonic() - 1)
    assert error.value.code is FetchCode.TIMEOUT
    raw.connect_ex.assert_not_called()


@pytest.mark.asyncio
async def test_deadline_rechecked_inside_gate_action(
    raw: Mock, target: NetworkTarget, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate()
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)

    class ExpiringGate:
        def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
            _ = handoff
            monkeypatch.setattr(transport.time, "monotonic", lambda: 1e20)
            return action()

    stream._gate = ExpiringGate()
    with pytest.raises(FetchError) as error:
        await stream.send(b"query")
    assert error.value.code is FetchCode.TIMEOUT
    raw.send.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("max_bytes", [0, -1, 16385, True])
async def test_receive_chunk_bound_is_enforced(raw: Mock, target: NetworkTarget, max_bytes: int) -> None:
    stream = await transport.open_pinned_tcp(target, gate=Gate(), deadline=time.monotonic() + 1)
    with pytest.raises(FetchError) as error:
        await stream.receive(max_bytes)
    assert error.value.code is FetchCode.INPUT
    raw.recv.assert_not_called()


@pytest.fixture
def tls_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Mock, Path]:
    ca_file = tmp_path / "explicit-ca.pem"
    ca_file.touch()
    context = Mock(spec=ssl.SSLContext)
    context.options = 0
    context.keylog_filename = None
    monkeypatch.setattr(transport.ssl, "SSLContext", Mock(return_value=context))
    monkeypatch.setattr(transport.ssl, "create_default_context", Mock(side_effect=AssertionError("No ambient roots")))
    return context, ca_file


def test_tls_context_uses_only_explicit_trust_and_no_ambient_keylog(
    tls_context: tuple[Mock, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, ca_file = tls_context
    monkeypatch.setenv("SSLKEYLOGFILE", "/untrusted/keys")
    monkeypatch.setenv("SSL_CERT_FILE", "/untrusted/ca")
    monkeypatch.setenv("SSL_CERT_DIR", "/untrusted/certs")
    assert transport._tls_context(ca_file) is context
    context.load_verify_locations.assert_called_once_with(cafile=str(ca_file))
    context.load_default_certs.assert_not_called()
    context.load_cert_chain.assert_not_called()
    context.set_alpn_protocols.assert_called_once_with(["http/1.1"])
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.hostname_checks_common_name is False
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.post_handshake_auth is False
    assert context.keylog_filename is None


@pytest.mark.asyncio
async def test_memory_bio_tls_gates_handshake_application_and_read_generated_control(
    raw: Mock,
    tls_context: tuple[Mock, Path],
) -> None:
    context, ca_file = tls_context
    target = NetworkTarget("192.0.2.10", 443, "origin.example", "origin")
    raw.getpeername.return_value = (target.address, target.port)
    raw.recv.return_value = b"server handshake"
    ssl_object = Mock(spec=ssl.SSLObject)
    ssl_object.selected_alpn_protocol.return_value = "http/1.1"
    outgoing: ssl.MemoryBIO | None = None
    rounds = 0

    def wrap(incoming: ssl.MemoryBIO, output: ssl.MemoryBIO, *, server_hostname: str) -> ssl.SSLObject:
        nonlocal outgoing
        assert server_hostname == target.hostname
        raw.getpeername.assert_called_once()
        outgoing = output
        return cast("ssl.SSLObject", ssl_object)

    def handshake() -> None:
        nonlocal rounds
        assert outgoing is not None
        rounds += 1
        outgoing.write(b"hello" if rounds == 1 else b"finished")
        if rounds == 1:
            raise ssl.SSLWantReadError

    def write(data: bytes) -> int:
        assert outgoing is not None
        outgoing.write(b"encrypted:" + data)
        return len(data)

    def read(max_bytes: int) -> bytes:
        assert outgoing is not None
        outgoing.write(b"tls-key-update")
        return b"response"[:max_bytes]

    context.wrap_bio.side_effect = wrap
    ssl_object.do_handshake.side_effect = handshake
    ssl_object.write.side_effect = write
    ssl_object.read.side_effect = read
    gate = Gate()
    stream = await transport.open_pinned_tls(target, gate=gate, deadline=time.monotonic() + 1, ca_file=ca_file)
    await stream.send(b"GET / HTTP/1.1\r\n\r\n")
    assert await stream.receive() == b"response"
    assert [call.phase for call in gate.calls] == ["connect", "tls", "tls", "http", "tls"]
    assert gate.calls[3].application_bytes == b"GET / HTTP/1.1\r\n\r\n"
    assert gate.calls[3].wire_bytes == b"encrypted:GET / HTTP/1.1\r\n\r\n"
    assert gate.calls[-1].application_bytes is None
    sent = raw.send.call_count
    with pytest.raises(FetchError) as refused:
        await stream.send(b"GET / HTTP/1.1\r\n\r\n")
    assert refused.value.code is FetchCode.PROTOCOL
    assert raw.send.call_count == sent
    stream.close()
    assert raw.send.call_count == sent
    ssl_object.unwrap.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_tls_certificate_failure_never_sends_application_or_reconnects(
    raw: Mock,
    tls_context: tuple[Mock, Path],
) -> None:
    context, ca_file = tls_context
    target = NetworkTarget("192.0.2.10", 443, "origin.example", "origin")
    raw.getpeername.return_value = (target.address, target.port)
    ssl_object = Mock(spec=ssl.SSLObject)
    ssl_object.do_handshake.side_effect = ssl.SSLCertVerificationError("foreign diagnostic")
    context.wrap_bio.return_value = ssl_object
    gate = Gate()
    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tls(target, gate=gate, deadline=time.monotonic() + 1, ca_file=ca_file)
    assert error.value.code is FetchCode.TLS
    assert "foreign" not in str(error.value)
    assert [call.phase for call in gate.calls] == ["connect"]
    raw.connect_ex.assert_called_once()
    raw.send.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["send", "receive"])
async def test_wire_limits_refuse_without_salvaging_partial_result(
    raw: Mock,
    target: NetworkTarget,
    monkeypatch: pytest.MonkeyPatch,
    direction: str,
) -> None:
    gate = Gate()
    stream = await transport.open_pinned_tcp(target, gate=gate, deadline=time.monotonic() + 1)
    monkeypatch.setattr(transport, "MAX_SEND_BYTES", 3)
    monkeypatch.setattr(transport, "MAX_RECEIVE_BYTES", 3)
    operation = stream.send(b"query") if direction == "send" else stream.receive()
    with pytest.raises(FetchError) as error:
        await operation
    assert error.value.code is FetchCode.LIMIT
    raw.send.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_readiness_deadline_unregisters_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.create_future.return_value = asyncio.get_running_loop().create_future()
    monkeypatch.setattr(transport.asyncio, "get_running_loop", Mock(return_value=loop))
    sock = Mock(spec=socket.socket)
    sock.fileno.return_value = 321
    with pytest.raises(FetchError) as error:
        await transport._ready(sock, time.monotonic() + 0.001, writable=True)
    assert error.value.code is FetchCode.TIMEOUT
    loop.remove_writer.assert_called_once_with(321)


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["input", "output"])
async def test_handshake_resource_bound_closes_without_application_output(
    raw: Mock,
    tls_context: tuple[Mock, Path],
    monkeypatch: pytest.MonkeyPatch,
    direction: str,
) -> None:
    context, ca_file = tls_context
    target = NetworkTarget("192.0.2.10", 443, "origin.example", "origin")
    raw.getpeername.return_value = (target.address, target.port)
    raw.recv.return_value = b"peer handshake"
    ssl_object = Mock(spec=ssl.SSLObject)

    def wrap(incoming: ssl.MemoryBIO, outgoing: ssl.MemoryBIO, *, server_hostname: str) -> ssl.SSLObject:
        if direction == "output":
            outgoing.write(b"x" * (transport._MAX_BIO_BYTES + 1))
        return cast("ssl.SSLObject", ssl_object)

    context.wrap_bio.side_effect = wrap
    ssl_object.do_handshake.side_effect = ssl.SSLWantReadError
    monkeypatch.setattr(transport, "MAX_HANDSHAKE_BYTES", 3)
    gate = Gate()
    with pytest.raises(FetchError) as error:
        await transport.open_pinned_tls(target, gate=gate, deadline=time.monotonic() + 1, ca_file=ca_file)
    assert error.value.code is FetchCode.LIMIT
    raw.send.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_cancellation_during_tls_read_closes_without_shutdown_write(
    raw: Mock,
    tls_context: tuple[Mock, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, ca_file = tls_context
    target = NetworkTarget("192.0.2.10", 443, "origin.example", "origin")
    raw.getpeername.return_value = (target.address, target.port)
    ssl_object = Mock(spec=ssl.SSLObject)
    ssl_object.selected_alpn_protocol.return_value = "http/1.1"
    ssl_object.read.side_effect = ssl.SSLWantReadError
    context.wrap_bio.return_value = ssl_object
    gate = Gate()
    stream = await transport.open_pinned_tls(target, gate=gate, deadline=time.monotonic() + 1, ca_file=ca_file)
    raw.recv.side_effect = BlockingIOError()
    entered = asyncio.Event()

    async def pending(*args: object, **kwargs: object) -> None:
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(transport, "_ready", pending)
    task = asyncio.create_task(stream.receive())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert [call.phase for call in gate.calls] == ["connect"]
    ssl_object.unwrap.assert_not_called()
    raw.close.assert_called_once()


@pytest.mark.asyncio
async def test_literal_ip_is_kept_for_certificate_identity(
    raw: Mock,
    tls_context: tuple[Mock, Path],
) -> None:
    context, ca_file = tls_context
    target = NetworkTarget("192.0.2.10", 443, "192.0.2.10", "origin")
    raw.getpeername.return_value = (target.address, target.port)
    ssl_object = Mock(spec=ssl.SSLObject)
    ssl_object.selected_alpn_protocol.return_value = None
    context.wrap_bio.return_value = ssl_object
    stream = await transport.open_pinned_tls(target, gate=Gate(), deadline=time.monotonic() + 1, ca_file=ca_file)
    assert context.wrap_bio.call_args.kwargs["server_hostname"] == target.hostname
    # Actual absence of IP SNI is an OpenSSL/CPython fixture obligation, not proved by this substitute.
    stream.close()
