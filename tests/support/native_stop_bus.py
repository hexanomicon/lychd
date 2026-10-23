"""Exact private broker support for the native-stop systemd receipt.

These two infrastructure units belong only to the private manager. They neither
reference the native Vessel nor enter Scribe's application ownership set.
"""

# ruff: noqa: INP001 - existing tests/support namespace is intentional

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import stat
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal

from lychd.system.schemas import systemd_executable_token
from tests.support.systemd_transaction import read_properties, trusted_binary, unavailable

_BUS_UNITS = ("dbus.service", "dbus.socket")


def broker_binaries() -> dict[str, Path]:
    """Attest both installed executables before any bus or manager starts."""
    binaries: dict[str, Path] = {}
    for name in ("dbus-broker", "dbus-broker-launch"):
        binary = trusted_binary(name, (Path("/usr/bin") / name,))
        if binary is None:
            unavailable(f"native stop requires a root-controlled installed {name}")
        binaries[name] = binary
    return binaries


@dataclass(frozen=True)
class NativeStopBus:
    """One exact socket-activated broker in a private manager namespace."""

    runtime: Path
    harness: Path
    config: Path
    launcher: Path
    broker: Path

    @property
    def units(self) -> tuple[str, ...]:
        return _BUS_UNITS

    @property
    def socket_path(self) -> Path:
        return self.runtime / "bus"

    @property
    def address(self) -> str:
        return f"unix:path={self.socket_path}"

    def metadata(self) -> dict[str, object]:
        return {
            "address": self.address,
            "config_sha256": hashlib.sha256(self.config.read_bytes()).hexdigest(),
            "support_unit_sha256": {
                unit: hashlib.sha256((self.harness / unit).read_bytes()).hexdigest() for unit in self.units
            },
            "binaries": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.launcher, self.broker)
            },
        }

    def attest(
        self,
        *,
        manager_pid: int,
        outer_group: str,
        systemctl: Path,
        environment: dict[str, str],
    ) -> dict[str, Any]:
        """Join full-bus identity to the already attested private peer manager."""
        assert environment["DBUS_SESSION_BUS_ADDRESS"] == self.address
        assert environment["DBUS_SYSTEM_BUS_ADDRESS"] == f"unix:path={self.runtime / 'disabled-system-bus'}"
        assert not (self.runtime / "disabled-system-bus").exists()
        metadata = self.socket_path.lstat()
        assert stat.S_ISSOCK(metadata.st_mode)
        assert metadata.st_uid == os.getuid()
        assert stat.S_IMODE(metadata.st_mode) == 0o600
        with socket.socket(socket.AF_UNIX) as peer:
            peer.settimeout(0.5)
            peer.connect(str(self.socket_path))
            credentials = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        # Socket activation captures the manager's credentials at listen(),
        # although dbus-broker accepts the inherited listener descriptor.
        assert credentials == (manager_pid, os.getuid(), os.getgid())
        snapshots = read_properties(systemctl=systemctl, environment=environment, units=self.units)
        assert snapshots["dbus.socket"]["ActiveState"] == "active"
        assert snapshots["dbus.socket"]["SubState"] == "running"
        service = snapshots["dbus.service"]
        assert (service["ActiveState"], service["SubState"]) == ("active", "running")
        for unit, snapshot in snapshots.items():
            assert snapshot["FragmentPath"] == str(self.harness / unit)
        launcher_pid = int(service["MainPID"])
        assert str(self.launcher) in service["ExecStart"]
        assert str(self.config) in service["ExecStart"]
        assert Path(f"/proc/{launcher_pid}/exe").resolve() == self.launcher
        group = service["ControlGroup"]
        assert Path(group).is_relative_to(outer_group)
        assert group != outer_group
        cgroup = Path("/sys/fs/cgroup") / group.lstrip("/")
        pids = tuple(map(int, (cgroup / "cgroup.procs").read_text(encoding="ascii").split()))
        assert launcher_pid in pids
        assert len(pids) == 2, "private broker service has unexpected process membership"
        broker_pids = [pid for pid in pids if pid != launcher_pid]
        for pid in broker_pids:
            assert Path(f"/proc/{pid}/exe").resolve() == self.broker
            fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            assert int(fields[1]) == launcher_pid
            assert Path(f"/proc/{pid}").stat().st_uid == os.getuid()
        with asyncio.Runner() as runner:
            identity = runner.run(self._identity(manager_pid))
        return {
            **self.metadata(),
            "socket": {"inode": metadata.st_ino, "uid": metadata.st_uid, "peer_credentials": credentials},
            "properties": snapshots,
            "process_pids": pids,
            "full_bus_identity": identity,
        }

    async def _identity(self, manager_pid: int) -> dict[str, object]:
        bus = MessageBus(bus_address=self.address, auth=AuthExternal(), negotiate_unix_fd=False, auth_timeout=5.0)
        connected = False
        try:
            async with asyncio.timeout(5.0):
                await bus.connect()
                connected = True
                bus_id = await _driver_call(bus, "GetId", "", [], "s")
                assert isinstance(bus_id, str)
                assert len(bus_id) == 32
                assert all(character in "0123456789abcdef" for character in bus_id)
                owner = None
                while owner is None:
                    owner = await _driver_call(
                        bus, "GetNameOwner", "s", ["org.freedesktop.systemd1"], "s", allow_missing=True
                    )
                    if owner is None:
                        await asyncio.sleep(0.05)
                assert isinstance(owner, str)
                assert owner.startswith(":")
                pid = await _driver_call(bus, "GetConnectionUnixProcessID", "s", [owner], "u")
                uid = await _driver_call(bus, "GetConnectionUnixUser", "s", [owner], "u")
                assert type(pid) is int
                assert pid == manager_pid
                assert type(uid) is int
                assert uid == os.getuid()
                return {"bus_id": bus_id, "manager_owner": owner, "manager_pid": pid, "manager_uid": uid}
        finally:
            bus.disconnect()
            if connected:
                async with asyncio.timeout(1.0):
                    await bus.wait_for_disconnect()

    def listener_absent(self) -> bool:
        """Require the exact socket path to refuse connections after cleanup."""
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(0.2)
            try:
                connection.connect(str(self.socket_path))
            except (ConnectionRefusedError, FileNotFoundError):
                return True
        return False


async def _driver_call(
    bus: MessageBus,
    member: str,
    signature: str,
    body: list[object],
    reply_signature: str,
    *,
    allow_missing: bool = False,
) -> object:
    message = Message(
        destination="org.freedesktop.DBus",
        path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus",
        member=member,
        signature=signature,
        body=body,
    )
    reply = await bus.call(message)
    assert reply is not None
    if allow_missing and reply.message_type is MessageType.ERROR:
        assert reply.error_name == "org.freedesktop.DBus.Error.NameHasNoOwner"
        return None
    assert reply.message_type is MessageType.METHOD_RETURN
    assert reply.sender == "org.freedesktop.DBus"
    assert reply.reply_serial == message.serial
    assert reply.signature == reply_signature
    assert len(reply.body) == 1
    return reply.body[0]


def prepare_bus(*, runtime: Path, harness: Path, root: Path, binaries: dict[str, Path]) -> NativeStopBus:
    """Write only explicit private infrastructure, with no native unit reference."""
    config = root / "broker.xml"
    config.write_text(
        "<busconfig>\n"
        "  <type>session</type>\n"
        '  <policy context="default">\n'
        f'    <deny user="*"/><allow user="{os.getuid()}"/>\n'
        '    <deny own="*"/><deny send_destination="*"/><deny receive_sender="*"/>\n'
        "  </policy>\n"
        f'  <policy user="{os.getuid()}">\n'
        '    <allow own="org.freedesktop.systemd1"/>\n'
        '    <allow send_destination="*"/><allow receive_sender="*"/>\n'
        "  </policy>\n"
        "</busconfig>\n",
        encoding="utf-8",
    )
    config.chmod(0o600)
    launcher = binaries["dbus-broker-launch"]
    units = {
        "dbus.socket": "[Unit]\nDescription=LychD private full bus\nDefaultDependencies=no\n[Socket]\nListenStream=%t/bus\nSocketMode=0600\n",
        "dbus.service": (
            "[Unit]\nDescription=LychD private broker\nDefaultDependencies=no\n"
            "After=dbus.socket\nRequires=dbus.socket\n[Service]\nType=notify\nSockets=dbus.socket\n"
            f"ExecStart={systemd_executable_token(launcher)} --scope=user --config-file={systemd_executable_token(config)}\n"
        ),
    }
    for name, contents in units.items():
        assert "lychd-uncaged-vessel" not in contents
        (harness / name).write_text(contents, encoding="utf-8")
    return NativeStopBus(runtime, harness, config, launcher, binaries["dbus-broker"])
