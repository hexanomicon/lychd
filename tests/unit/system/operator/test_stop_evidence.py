from __future__ import annotations

# pyright: reportPrivateUsage=false
import asyncio
import builtins
import importlib.util
import os
import socket
import struct
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import TYPE_CHECKING, Any

import pytest
from dbus_fast import Message, MessageType

from lychd.system.operator import stop_evidence
from lychd.system.operator.models import OperatorAuthorityError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class _FakeBus:
    def __init__(self) -> None:
        self.unique_name: str | None = None
        self.owner = ":1.42"
        self.pid = 1234
        self.uid = os.getuid()
        self.connected = False
        self.closed = False
        self.finalized = False
        self.serial = 1
        self.calls: list[Message] = []
        self.events: list[str] = []
        self.loops: list[asyncio.AbstractEventLoop] = []
        self.handlers: list[Callable[[Message], None]] = []
        self.rewrite: Callable[[Message], None] | None = None
        self.hello_rewrite: Callable[[Message], None] | None = None
        self.hang: str | None = None
        self.error: str | None = None
        self.cancel_stage: str | None = None
        self.cancellation = asyncio.CancelledError("acquisition cancellation")
        self.delay = 0.0
        self.references = 0

    def add_message_handler(self, handler: Callable[[Message], None]) -> None:
        self.handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[Message], None]) -> None:
        self.handlers.remove(handler)

    async def _stage(self, stage: str) -> None:
        self.loops.append(asyncio.get_running_loop())
        self.events.append(stage)
        if self.error == stage:
            message = "private secret transport detail"
            raise OSError(message)
        if self.cancel_stage == stage:
            raise self.cancellation
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.hang == stage:
            await asyncio.Future[None]()

    async def connect(self) -> _FakeBus:
        try:
            await self._stage("connect")
        except BaseException:
            # dbus-fast 5.2 closes incomplete transport/auth/Hello phases.
            self.closed = True
            raise
        self.unique_name = ":1.100"
        self.connected = True
        hello = Message(
            message_type=MessageType.METHOD_RETURN,
            sender="org.freedesktop.DBus",
            destination=self.unique_name,
            reply_serial=1,
            signature="s",
            body=[self.unique_name],
        )
        if self.hello_rewrite is not None:
            self.hello_rewrite(hello)
        for handler in self.handlers:
            handler(hello)
        return self

    async def call(self, request: Message) -> Message:
        assert self.connected
        assert request.member is not None
        self.serial += 1
        request.serial = self.serial
        self.calls.append(request)
        await self._stage(request.member)
        signature = ""
        body: list[Any] = []
        if request.member == "GetNameOwner":
            signature, body = "s", [self.owner]
        elif request.member == "GetConnectionUnixProcessID":
            signature, body = "u", [self.pid]
        elif request.member == "GetConnectionUnixUser":
            signature, body = "u", [self.uid]
        elif request.member == "RefUnit":
            self.references += 1
        elif request.member == "UnrefUnit":
            self.references -= 1
        else:
            assert request.member == "Ping"
        reply = Message(
            message_type=MessageType.METHOD_RETURN,
            sender=request.destination,
            destination=self.unique_name,
            reply_serial=request.serial,
            signature=signature,
            body=body,
        )
        if self.rewrite is not None:
            self.rewrite(reply)
        return reply

    def disconnect(self) -> None:
        self.events.append("disconnect")
        self.connected = False
        if self.error == "disconnect":
            message = "private secret disconnect detail"
            raise OSError(message)

    async def wait_for_disconnect(self) -> None:
        await self._stage("close")
        self.closed = True
        self.references = 0

    def _finalize(self) -> None:
        self.events.append("finalize")
        self.connected = False
        self.closed = True
        self.finalized = True
        self.references = 0


@pytest.fixture
def runtime() -> Iterator[Path]:
    """Keep valid Unix socket paths independent of checkout and pytest node lengths."""
    with TemporaryDirectory(prefix="lse-", dir="/tmp") as directory:
        path = Path(directory).resolve() / "runtime"
        path.mkdir(mode=0o700)
        yield path


@pytest.fixture
def bus(mocker: MockerFixture) -> _FakeBus:
    instance = _FakeBus()
    mocker.patch.object(stop_evidence, "_new_bus", return_value=instance)
    mocker.patch.object(
        stop_evidence,
        "_private_peer",
        return_value=stop_evidence._ManagerPeer(instance.pid, instance.uid),
    )
    return instance


def test_reference_pins_exact_native_and_uses_one_loop_until_explicit_release(runtime: Path, bus: _FakeBus) -> None:
    with stop_evidence.hold_native_exit(runtime_dir=runtime) as reference:
        assert bus.references == 1
        assert bus.connected
        reference.verify()
        reference.verify()
        assert bus.references == 1
        assert "UnrefUnit" not in bus.events

    calls = [request for request in bus.calls if request.member in {"RefUnit", "UnrefUnit"}]
    assert [(request.member, request.body) for request in calls] == [
        ("RefUnit", ["lychd-uncaged-vessel.service"]),
        ("UnrefUnit", ["lychd-uncaged-vessel.service"]),
    ]
    assert all(request.destination == ":1.42" for request in calls)
    assert all(request.signature == "s" for request in calls)
    assert all(request.path == "/org/freedesktop/systemd1" for request in calls)
    assert all(request.interface == "org.freedesktop.systemd1.Manager" for request in calls)
    assert len(set(bus.loops)) == 1
    assert bus.closed
    assert not bus.finalized
    assert bus.events[-3:] == ["UnrefUnit", "disconnect", "close"]
    with pytest.raises(OperatorAuthorityError, match="reference lifetime"):
        reference.verify()


def test_ambient_bus_override_is_ignored_and_environment_runtime_is_rechecked(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "tcp:host=private.invalid,port=1234")
    factory = mocker.spy(stop_evidence, "_new_bus")
    with stop_evidence.hold_native_exit() as reference:
        factory.assert_called_once_with(f"unix:path={runtime}/bus")
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime.parent))
        with pytest.raises(OperatorAuthorityError, match="continuity"):
            reference.verify()
    assert bus.closed


@pytest.mark.parametrize("value", [None, "", "relative/runtime"])
def test_missing_or_relative_runtime_refuses_before_transport(
    value: str | None, bus: _FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    if value is None:
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    else:
        monkeypatch.setenv("XDG_RUNTIME_DIR", value)
    with pytest.raises(OperatorAuthorityError, match="runtime"), stop_evidence.hold_native_exit():
        pytest.fail("invalid runtime yielded")
    assert not bus.events


@pytest.mark.parametrize("case", ["permissions", "symlink", "not-directory", "missing", "too-long"])
def test_runtime_requires_owned_canonical_private_directory(runtime: Path, bus: _FakeBus, case: str) -> None:
    if case == "permissions":
        runtime.chmod(0o750)
    elif case == "symlink":
        alias = runtime.parent / "alias"
        alias.symlink_to(runtime)
        runtime = alias
    elif case == "not-directory":
        runtime.rmdir()
        runtime.write_text("inert", encoding="utf-8")
    elif case == "missing":
        runtime.rmdir()
    else:
        runtime = runtime / ("a" * 108)
        runtime.mkdir(mode=0o700)
    with pytest.raises(OperatorAuthorityError, match="runtime"), stop_evidence.hold_native_exit(runtime_dir=runtime):
        pytest.fail("invalid runtime yielded")
    assert not bus.events


def test_full_bus_manager_must_match_private_peer_before_ref(runtime: Path, bus: _FakeBus) -> None:
    bus.pid += 1
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition"),
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("foreign manager yielded")
    assert "RefUnit" not in bus.events
    assert bus.closed


@pytest.mark.parametrize("change", ["owner", "pid", "uid", "private-peer"])
def test_live_manager_continuity_is_checked_without_repinning(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture, change: str
) -> None:
    with stop_evidence.hold_native_exit(runtime_dir=runtime) as reference:
        if change == "owner":
            bus.owner = ":1.43"
        elif change == "pid":
            bus.pid += 1
        elif change == "uid":
            bus.uid += 1
        else:
            mocker.patch.object(stop_evidence, "_private_peer", return_value=stop_evidence._ManagerPeer(5678, bus.uid))
        with pytest.raises(OperatorAuthorityError, match="continuity"):
            reference.verify()
    assert bus.events.count("RefUnit") == 1
    assert bus.closed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("message_type", MessageType.ERROR),
        ("reply_serial", 9999),
        ("sender", ":1.999"),
        ("destination", ":1.999"),
        ("signature", "u"),
        ("body", ["unexpected", "extra"]),
        ("body", [True]),
        ("error_name", "private.secret.Error"),
        ("unix_fds", [99]),
    ],
)
def test_malformed_acquisition_replies_fail_closed_without_private_error_text(
    runtime: Path, bus: _FakeBus, field: str, value: object
) -> None:
    bus.rewrite = lambda reply: setattr(reply, field, value)
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition") as caught,
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("malformed reply yielded")
    assert "secret" not in str(caught.value)
    assert "RefUnit" not in bus.events
    assert bus.closed


@pytest.mark.parametrize("field", ["sender", "reply_serial", "signature", "body", "message_type"])
def test_hello_reply_is_checked_before_manager_requests(runtime: Path, bus: _FakeBus, field: str) -> None:
    values: dict[str, object] = {
        "sender": ":1.999",
        "reply_serial": 2,
        "signature": "u",
        "body": [":1.100", "extra"],
        "message_type": MessageType.ERROR,
    }
    bus.hello_rewrite = lambda reply: setattr(reply, field, values[field])
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition"),
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("malformed Hello yielded")
    assert not bus.calls
    assert bus.closed


def test_socket_loss_is_real_roundtrip_refusal_and_not_reconnected(runtime: Path, bus: _FakeBus) -> None:
    with (  # noqa: PT012 - inspect refusal and subsequent context cleanup separately.
        pytest.raises(OperatorAuthorityError, match="release or close"),
        stop_evidence.hold_native_exit(runtime_dir=runtime) as reference,
    ):
        # Mirrors the integration harness closing this exact production bus.
        bus.disconnect()
        with pytest.raises(OperatorAuthorityError, match="continuity"):
            reference.verify()
    assert bus.events.count("connect") == 1
    assert bus.events.count("RefUnit") == 1
    assert bus.closed


@pytest.mark.parametrize("stage", ["connect", "GetNameOwner", "RefUnit", "Ping"])
def test_acquisition_has_one_bounded_stage_and_always_closes(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture, stage: str
) -> None:
    mocker.patch.object(stop_evidence, "_EXCHANGE_SECONDS", 0.01)
    bus.hang = stage
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition"),
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("stalled acquisition yielded")
    assert bus.closed
    if stage == "connect":
        assert "close" not in bus.events
    assert "disconnect" in bus.events


def test_verification_timeout_does_not_refresh_reference_or_mask_body_error(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture
) -> None:
    mocker.patch.object(stop_evidence, "_EXCHANGE_SECONDS", 0.01)
    with stop_evidence.hold_native_exit(runtime_dir=runtime) as reference:
        bus.hang = "Ping"
        with pytest.raises(OperatorAuthorityError, match="continuity"):
            reference.verify()
        bus.hang = None
    assert bus.events.count("RefUnit") == 1
    assert bus.closed


def test_slow_acquisition_shares_one_deadline_across_all_exchanges(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture
) -> None:
    mocker.patch.object(stop_evidence, "_EXCHANGE_SECONDS", 0.01)
    bus.delay = 0.006
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition"),
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("per-message timeout incorrectly renewed acquisition")
    assert "RefUnit" not in bus.events
    assert bus.closed


def test_cancelled_acquisition_after_connect_closes_without_waiting_on_an_uncreated_pin(
    runtime: Path, bus: _FakeBus
) -> None:
    bus.cancel_stage = "GetConnectionUnixUser"
    with pytest.raises(asyncio.CancelledError) as caught, stop_evidence.hold_native_exit(runtime_dir=runtime):
        pytest.fail("cancelled acquisition yielded")
    assert caught.value is bus.cancellation
    assert "RefUnit" not in bus.events
    assert "UnrefUnit" not in bus.events
    assert bus.closed
    assert not bus.finalized


def test_transport_error_is_sanitized_and_partial_reference_is_released(runtime: Path, bus: _FakeBus) -> None:
    bus.error = "Ping"
    with (
        pytest.raises(OperatorAuthorityError, match="acquisition") as caught,
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        pytest.fail("failed acquisition yielded")
    assert "secret" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert bus.events.count("RefUnit") == 1
    assert bus.events.count("UnrefUnit") == 1
    assert bus.references == 0
    assert bus.closed


@pytest.mark.parametrize("stage", ["UnrefUnit", "close", "disconnect"])
def test_late_cleanup_uncertainty_fails_even_after_local_close(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture, stage: str
) -> None:
    mocker.patch.object(stop_evidence, "_UNREF_SECONDS", 0.01)
    mocker.patch.object(stop_evidence, "_CLOSE_SECONDS", 0.01)
    if stage == "disconnect":
        bus.error = stage
    else:
        bus.hang = stage
    with (
        pytest.raises(OperatorAuthorityError, match="release or close"),
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        assert bus.references == 1
    assert bus.closed
    assert bus.finalized is (stage in {"close", "disconnect"})


def test_primary_cancellation_survives_failed_release_and_close(
    runtime: Path, bus: _FakeBus, mocker: MockerFixture
) -> None:
    mocker.patch.object(stop_evidence, "_CLOSE_SECONDS", 0.01)
    cancellation = asyncio.CancelledError("caller cancellation")
    with (  # noqa: PT012 - the primary cancellation must survive failing context cleanup.
        pytest.raises(asyncio.CancelledError) as caught,
        stop_evidence.hold_native_exit(runtime_dir=runtime),
    ):
        bus.hang = "close"
        raise cancellation
    assert caught.value is cancellation
    assert caught.value.__notes__ == ["Native exit evidence release or close could not be verified."]
    assert bus.closed
    assert bus.finalized


def test_pinned_library_fallback_really_closes_descriptors_and_removes_readers(
    runtime: Path, mocker: MockerFixture
) -> None:
    from dbus_fast.aio import MessageBus

    async def construct() -> MessageBus:
        # The installed 5.2 constructor creates no transport or socket.
        return stop_evidence._new_bus("unix:path=/synthetic/runtime/bus")

    async def stalled_close(_bus: MessageBus) -> None:
        await asyncio.Future[None]()

    mocker.patch.object(stop_evidence, "_CLOSE_SECONDS", 0.01)
    mocker.patch.object(MessageBus, "wait_for_disconnect", stalled_close)
    with asyncio.Runner() as runner:
        concrete = runner.run(construct())
        peer = mocker.MagicMock()
        stream = mocker.MagicMock()
        loop = mocker.MagicMock()
        concrete._sock = peer
        concrete._stream = stream
        concrete._fd = 37
        concrete._loop = loop
        concrete.unique_name = ":1.100"
        reference = stop_evidence._NativeExitReference(runner, runtime, from_environment=False)
        reference._bus = concrete
        reference._connected = True
        with pytest.raises(OperatorAuthorityError, match="release or close"):
            reference.close()
        peer.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        peer.close.assert_called_once_with()
        stream.close.assert_called_once_with()
        loop.remove_reader.assert_called_once_with(37)
        loop.remove_writer.assert_called_once_with(37)
        assert not concrete.connected


def test_private_peer_uses_bounded_unix_connect_and_peer_credentials(runtime: Path, mocker: MockerFixture) -> None:
    peer = mocker.MagicMock()
    peer.getsockopt.return_value = struct.pack("3i", 1234, os.getuid(), os.getgid())
    create = mocker.patch.object(socket, "socket")
    create.return_value.__enter__.return_value = peer
    result = stop_evidence._private_peer(runtime)
    assert result == stop_evidence._ManagerPeer(1234, os.getuid())
    create.assert_called_once_with(socket.AF_UNIX, socket.SOCK_STREAM)
    peer.settimeout.assert_called_once_with(1.0)
    peer.connect.assert_called_once_with(str(runtime / "systemd" / "private"))
    peer.getsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    peer.send.assert_not_called()
    create.return_value.__exit__.assert_called_once()


def test_bus_constructor_is_lazy_external_only_and_never_negotiates_fds(mocker: MockerFixture) -> None:
    constructor = mocker.patch("dbus_fast.aio.MessageBus")
    auth = mocker.patch("dbus_fast.auth.AuthExternal")
    address = "unix:path=/synthetic/runtime/bus"
    assert stop_evidence._new_bus(address) is constructor.return_value
    constructor.assert_called_once_with(
        bus_address=address, auth=auth.return_value, negotiate_unix_fd=False, auth_timeout=5.0
    )
    auth.assert_called_once_with()


def test_module_ordinary_import_does_not_import_dbus(monkeypatch: pytest.MonkeyPatch) -> None:
    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> ModuleType:
        if name.startswith("dbus_fast"):
            pytest.fail("ordinary import loaded D-Bus")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    name = "lychd.system.operator._stop_evidence_import_probe"
    spec = importlib.util.spec_from_file_location(name, stop_evidence.__file__)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert callable(module.hold_native_exit)
