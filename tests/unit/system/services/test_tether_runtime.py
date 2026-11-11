"""Runtime wire rejection and active-stream fencing without host network effects."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import socket
from pathlib import Path
from typing import Any, cast

import pytest

from lychd.system.services.tether import runtime


def common(role: str) -> dict[str, Any]:
    return {
        "schema": "lychd.tether.runtime",
        "version": 1,
        "role": role,
        "network_id": "remote-b",
        "installation_epoch": "a" * 32,
        "generation": 3,
        "policy_digest": "b" * 64,
        "fence_path": "/etc/lychd-tether/fences.json",
    }


def imported() -> dict[str, Any]:
    return {
        **common("imported-relay"),
        "remote_lich_id": "lich-b",
        "caller_uid": 1000,
        "allowed_callers": ["intercom"],
        "routes": [
            {
                "service_id": "tasks",
                "generation": 3,
                "socket_path": "/run/lychd-tether/12345678/12345678.sock",
                "address": "10.77.0.2",
                "port": 443,
                "application_identity_ref": "peer:b",
            }
        ],
    }


def fences(p: dict[str, Any], *, enabled: bool = True) -> dict[str, Any]:
    return {
        "schema": "lychd.tether.fences",
        "version": 1,
        "installation_epoch": p["installation_epoch"],
        "network_id": p["network_id"],
        "generation": p["generation"],
        "enabled": enabled,
        "peers": [],
    }


def header(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": 1,
        "installation_epoch": p["installation_epoch"],
        "policy_digest": p["policy_digest"],
        "remote_lich_id": p["remote_lich_id"],
        "attachment_id": p["network_id"],
        "generation": p["generation"],
        "service_id": "tasks",
        "caller": "intercom",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generation", True),
        ("generation", 2),
        ("caller", "scout"),
        ("attachment_id", "remote-c"),
        ("remote_lich_id", "lich-c"),
        ("service_id", "database"),
        ("installation_epoch", "c" * 32),
        ("policy_digest", "d" * 64),
        ("version", True),
    ],
)
def test_header_binds_every_selection_field(field: str, value: object) -> None:
    p = imported()
    relay = runtime.Relay(runtime.validate_config(p))
    request = header(p)
    relay.validate_header(json.dumps(request).encode() + b"\n", p["routes"][0], 1000)
    request[field] = value
    with pytest.raises(ValueError, match="refused"):
        relay.validate_header(json.dumps(request).encode() + b"\n", p["routes"][0], 1000)


def test_header_rejects_extra_target_duplicate_fields_and_wrong_uid() -> None:
    p = imported()
    relay = runtime.Relay(p)
    request = header(p)
    request["address"] = "127.0.0.1"
    with pytest.raises(ValueError, match="refused"):
        relay.validate_header(json.dumps(request).encode() + b"\n", p["routes"][0], 1000)
    encoded = json.dumps(header(p)).encode()
    with pytest.raises(ValueError, match="refused"):
        relay.validate_header(encoded[:-1] + b',"caller":"intercom"}\n', p["routes"][0], 1000)
    with pytest.raises(ValueError, match="refused"):
        relay.validate_header(encoded + b"\n", p["routes"][0], 1001)
    with pytest.raises(ValueError, match="refused"):
        relay.validate_header(encoded + b" " * runtime.MAX_HEADER + b"\n", p["routes"][0], 1000)


@pytest.mark.parametrize("extra", ["PostUp", "PreDown", "DNS", "AllowedIPs", "command"])
def test_import_rejects_configuration_authority(extra: str) -> None:
    p = imported()
    p[extra] = "arbitrary"
    with pytest.raises(ValueError, match="refused"):
        runtime.validate_config(p)


def test_fence_rejects_epoch_rollback_and_wrong_generation() -> None:
    p = imported()
    f = fences(p)
    runtime.validate_fences(f, p)
    f["installation_epoch"] = "0" * 32
    with pytest.raises(ValueError, match="refused"):
        runtime.validate_fences(f, p)
    f = fences(p)
    f["generation"] = 2
    with pytest.raises(ValueError, match="refused"):
        runtime.validate_fences(f, p)
    assert not runtime.admitted(p, None)
    assert not runtime.admitted(p, fences(p, enabled=False))


def wg() -> dict[str, Any]:
    return {
        **common("wireguard"),
        "interface": "wg0",
        "address": "10.77.0.1/32",
        "listen_port": 0,
        "private_key_path": "/run/secrets/wg-private",
        "peers": [
            {
                "id": "lich-b",
                "generation": 3,
                "public_key": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
                "allowed_ips": ["10.77.0.2/32"],
                "endpoint_address": "203.0.113.1",
                "endpoint_port": 51820,
                "keepalive": 25,
                "preshared_key_path": None,
            }
        ],
        "ingress": [],
        "owner_loopback_port": None,
        "egress": [
            {"address": "10.77.0.2", "port": 443, "protocol": "tcp"},
            {"address": "203.0.113.1", "port": 51820, "protocol": "udp"},
        ],
    }


def test_imported_nft_never_accepts_inner_tcp_on_outer_interface() -> None:
    p = runtime.validate_config(wg())
    policy = runtime.nft_policy(p, fences(p))
    tcp_rules = [line for line in policy.splitlines() if "tcp " in line]
    assert tcp_rules
    assert all('ifname  "wg0"' in line for line in tcp_rules)
    assert not any('!= "wg0"' in line for line in tcp_rules)
    assert 'oifname != "wg0" ip daddr 203.0.113.1 udp dport 51820 accept' in policy
    assert "forward { type filter hook forward priority -150; policy drop; }" in policy
    closed = runtime.nft_policy(p, None)
    assert "accept" not in closed
    assert "policy drop" in closed


def test_offered_revocation_removes_only_peer_ingress() -> None:
    p = wg()
    p["listen_port"] = 51820
    p["egress"] = []
    p["peers"][0].update(endpoint_address=None, endpoint_port=None)
    second = copy.deepcopy(p["peers"][0])
    second.update(id="lich-c", allowed_ips=["10.77.0.3/32"])
    p["peers"].append(second)
    p["ingress"] = [{"peer_address": "10.77.0.2", "port": 2222}, {"peer_address": "10.77.0.3", "port": 2223}]
    f = fences(p)
    f["peers"] = [
        {"id": "lich-b", "generation": 3, "enabled": False},
        {"id": "lich-c", "generation": 3, "enabled": True},
    ]
    policy = runtime.nft_policy(p, f)
    assert "10.77.0.2" not in policy
    assert "10.77.0.3" in policy
    f["peers"][1]["generation"] = 4
    assert "10.77.0.3" not in runtime.nft_policy(p, f)


class Writer:
    """Observe writes and closure without opening real sockets."""

    def __init__(self, source: str = "10.77.0.2") -> None:
        """Collect observable stream writes and closure."""
        self.source = source
        self.writes: list[bytes] = []
        self.closed = False

    def get_extra_info(self, name: str) -> tuple[str, int]:
        assert name == "peername"
        return self.source, 12345

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_active_stream_fence_prevents_future_upstream_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    p = {
        **common("offered-relay"),
        "services": [],
        "peers": [{"id": "peer-b", "generation": 1, "address": "10.77.0.2", "service_ids": ["tasks"]}],
    }
    f = fences(p)
    f["peers"] = [{"id": "peer-b", "generation": 1, "enabled": True}]

    def fake_load_fences(_p: dict[str, Any]) -> dict[str, Any]:
        return f

    monkeypatch.setattr(runtime, "load_fences", fake_load_fences)
    incoming, outgoing = asyncio.StreamReader(), asyncio.StreamReader()
    client, upstream = Writer(), Writer()
    connected = asyncio.Event()

    async def connect(*_args: object, **_kwargs: object) -> tuple[asyncio.StreamReader, Writer]:
        connected.set()
        return outgoing, upstream

    monkeypatch.setattr(asyncio, "open_connection", connect)
    relay = runtime.Relay(p)
    task = asyncio.create_task(
        relay.handle(
            incoming,
            cast("asyncio.StreamWriter", client),
            {"service_id": "tasks", "backend_address": "192.0.2.3", "backend_port": 443},
        )
    )
    await asyncio.wait_for(connected.wait(), 1)
    incoming.feed_data(b"before")
    for _ in range(5):
        await asyncio.sleep(0)
    assert upstream.writes == [b"before"]
    f["peers"][0]["enabled"] = False
    incoming.feed_data(b"must-not-cross")
    await asyncio.wait_for(task, 1)
    assert upstream.writes == [b"before"]
    assert client.closed
    assert upstream.closed
    assert not relay.tasks


@pytest.mark.asyncio
async def test_offered_wrong_peer_never_opens_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    p: dict[str, Any] = {**common("offered-relay"), "peers": []}

    def fake_load_fences(_p: dict[str, Any]) -> dict[str, Any]:
        return fences(p)

    monkeypatch.setattr(runtime, "load_fences", fake_load_fences)
    opened = False

    async def connect(*_args: object, **_kwargs: object) -> None:
        nonlocal opened
        opened = True

    monkeypatch.setattr(asyncio, "open_connection", connect)
    writer = Writer()
    await runtime.Relay(p).handle(asyncio.StreamReader(), cast("asyncio.StreamWriter", writer), {"service_id": "tasks"})
    assert not opened
    assert writer.closed


def test_owner_policy_is_exact_forward_only() -> None:
    config = runtime.ssh_config({"listen_port": 2222, "listen_address": "10.0.0.1", "target_port": 27713})
    assert "PermitOpen 127.0.0.1:27713\n" in config
    for line in (
        "MaxSessions 0",
        "AllowTcpForwarding local",
        "AllowStreamLocalForwarding no",
        "PermitListen none",
        "PermitTTY no",
        "PermitTunnel no",
        "AllowAgentForwarding no",
    ):
        assert line + "\n" in config


def test_nft_comparison_keeps_interface_negation_significant() -> None:
    expected = 'oifname "wg0" ip daddr 10.77.0.2 tcp dport 443 accept'
    bypass = 'oifname != "wg0" ip daddr 10.77.0.2 tcp dport 443 accept'
    assert runtime.policy_tokens(expected) != runtime.policy_tokens(bypass)


def test_restart_adopts_only_exact_marked_table(monkeypatch: pytest.MonkeyPatch) -> None:
    p = wg()
    table = {"family": "inet", "name": "lychd_tether", "comment": runtime.ownership_marker(p)}

    def fake_run(_argv: tuple[str, ...]) -> str:
        return json.dumps({"nftables": [{"table": table}]})

    monkeypatch.setattr(runtime, "run", fake_run)
    assert runtime.existing_owned_table(p)
    table["comment"] = "foreign-installation"
    with pytest.raises(ValueError, match="refused"):
        runtime.existing_owned_table(p)


def test_restart_adopts_only_marked_wireguard_and_exact_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    p = wg()
    links = [{"ifalias": runtime.ownership_marker(p), "linkinfo": {"info_kind": "wireguard"}}]

    def run(argv: tuple[str, ...]) -> str:
        if "link" in argv:
            return json.dumps(links)
        if "address" in argv:
            return json.dumps([{"addr_info": [{"family": "inet", "local": "10.77.0.1", "prefixlen": 32}]}])
        return json.dumps([{"dst": "10.77.0.2", "protocol": "boot"}])

    monkeypatch.setattr(runtime, "run", run)
    assert runtime.owned_interface_routes(p) == {"10.77.0.2/32"}
    links[0]["ifalias"] = "foreign"
    with pytest.raises(ValueError, match="refused"):
        runtime.owned_interface_routes(p)


class WireGuardKernel:
    """Enforce link-state and denial guards without changing a network namespace."""

    def __init__(self, config: dict[str, Any], fence: dict[str, Any], routes: set[str]) -> None:
        """Start with a down interface and explicit recovered route state."""
        self.config = config
        self.fence = fence
        self.routes = set(routes)
        self.up = False
        self.denied = False
        self.peers_configured = False
        self.ready = False
        self.grants = 0

    def run(self, argv: tuple[str, ...], *, content: str | None = None) -> str:
        if argv == (runtime.NFT, "-f", "-"):
            assert content is not None
            self.denied = "accept" not in content
            if not self.denied:
                assert self.fence["enabled"]
                assert self.up
                assert self.peers_configured
                assert self.routes == {"10.77.0.2/32"}
                self.grants += 1
        elif argv[1:3] == ("link", "set") and argv[-1] == "up":
            assert self.denied
            assert self.peers_configured
            self.up = True
        elif argv[1:3] == ("route", "add"):
            if not self.up:
                message = "Device for nexthop is not up"
                raise ValueError(message)
            assert self.denied
            self.routes.add(argv[3])
        elif argv[1:3] == ("route", "delete"):
            assert self.denied
            self.routes.remove(argv[3])
        elif argv[1:3] == ("link", "delete"):
            assert self.denied
            self.up = False
        else:
            assert self.denied
        return ""

    def configure_peers(self, config: dict[str, Any], current_fence: dict[str, Any] | None) -> None:
        assert self.denied
        assert config == self.config
        assert current_fence == self.fence
        self.peers_configured = True

    def notify_ready(self) -> None:
        assert self.up
        assert self.routes == ({"10.77.0.2/32"} if self.fence["enabled"] else set())
        assert self.denied is not self.fence["enabled"]
        self.ready = True


@pytest.mark.asyncio
@pytest.mark.parametrize("recovered", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
async def test_wireguard_routes_require_up_device_under_denial(
    monkeypatch: pytest.MonkeyPatch, *, recovered: bool, enabled: bool
) -> None:
    p = runtime.validate_config(wg())
    fence = fences(p, enabled=enabled)
    initial_routes: set[str] = {"10.77.0.99/32"} if recovered else set()
    kernel = WireGuardKernel(p, fence, initial_routes)

    async def stop_after_reconciliation(_seconds: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(runtime, "run", kernel.run)

    def fake_existing_owned_table(_p: dict[str, Any]) -> bool:
        return recovered

    monkeypatch.setattr(runtime, "existing_owned_table", fake_existing_owned_table)

    def fake_owned_interface_routes(_p: dict[str, Any]) -> set[str] | None:
        return initial_routes if recovered else None

    monkeypatch.setattr(runtime, "owned_interface_routes", fake_owned_interface_routes)
    monkeypatch.setattr(runtime, "load_config", lambda: p)

    def fake_load_fences(_p: dict[str, Any]) -> dict[str, Any]:
        return fence

    monkeypatch.setattr(runtime, "load_fences", fake_load_fences)
    monkeypatch.setattr(runtime, "configure_peers", kernel.configure_peers)
    monkeypatch.setattr(runtime, "notify_ready", kernel.notify_ready)

    def fake_public_status(_p: dict[str, Any], **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(runtime, "public_status", fake_public_status)
    monkeypatch.setattr(runtime.asyncio, "sleep", stop_after_reconciliation)
    with pytest.raises(asyncio.CancelledError):
        await runtime.wireguard(p)
    assert kernel.ready
    assert kernel.denied
    assert not kernel.up
    assert kernel.grants == int(enabled)


def test_stale_socket_recovery_refuses_live_listener_and_regular_file(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    relay = runtime.Relay(imported())
    relay.lock_producer(tmp_path)
    path = tmp_path / "route.sock"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as producer:
            producer.bind(str(path))
            path.chmod(0o600)
            producer.listen(1)
            with pytest.raises(ValueError, match="refused"):
                relay.recover_socket(path)
            assert path.exists()
        relay.recover_socket(path)
        assert not path.exists()
        path.write_text("not a socket")
        path.chmod(0o600)
        with pytest.raises(ValueError, match="refused"):
            relay.recover_socket(path)
        assert path.read_text() == "not a socket"
    finally:
        assert relay.lock_descriptor is not None
        os.close(relay.lock_descriptor)


def test_producer_lock_refuses_second_live_producer_and_symlink(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    first, second = runtime.Relay(imported()), runtime.Relay(imported())
    first.lock_producer(tmp_path)
    try:
        with pytest.raises(BlockingIOError):
            second.lock_producer(tmp_path)
        target = tmp_path / "target"
        target.write_text("untouched")
        path = tmp_path / "route.sock"
        path.symlink_to(target)
        with pytest.raises(ValueError, match="refused"):
            first.recover_socket(path)
        assert target.read_text() == "untouched"
        assert path.is_symlink()
    finally:
        assert first.lock_descriptor is not None
        os.close(first.lock_descriptor)


# Default nft formatting retains symbolic protocol/state names and numeric addresses/ports.
_OBSERVED_NFT = """table inet lychd_tether {
    comment "lychd-tether:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:remote-b"
    chain input {
        type filter hook input priority mangle; policy drop;
        iifname != "wg0" meta nfproto ipv4 udp dport 51820 accept
        iifname "wg0" ip saddr 10.77.0.2 ip daddr 10.77.0.1 tcp dport 443 ct state established,new accept
    }
    chain output {
        type filter hook output priority mangle; policy drop;
        oifname != "wg0" meta nfproto ipv4 udp sport 51820 accept
        oifname "wg0" ip saddr 10.77.0.1 ip daddr 10.77.0.2 tcp sport 443 ct state established accept
    }
    chain forward {
        type filter hook forward priority mangle; policy drop;
    }
}
"""


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("", ""),
        ("dport 443", "dport 444"),
        ('iifname != "wg0"', 'iifname "wg0"'),
        ("hook forward priority mangle; policy drop", "hook forward priority mangle; policy accept"),
        ("nfproto ipv4", "nfproto ipv6"),
        ("nfproto ipv4", "nfproto 2"),
        ("ct state established,new", "ct state established,related"),
        ("priority mangle", "priority filter"),
        ("udp dport 51820 accept", "udp dport 51820 drop"),
        ('        iifname != "wg0" meta nfproto ipv4 udp dport 51820 accept\n', ""),
        (
            '        iifname != "wg0" meta nfproto ipv4 udp dport 51820 accept\n        iifname "wg0" ip saddr 10.77.0.2 ip daddr 10.77.0.1 tcp dport 443 ct state established,new accept\n',
            '        iifname "wg0" ip saddr 10.77.0.2 ip daddr 10.77.0.1 tcp dport 443 ct state established,new accept\n        iifname != "wg0" meta nfproto ipv4 udp dport 51820 accept\n',
        ),
        ("    chain forward {", "    chain forward { accept"),
        ("ct state established,new accept", "accept ct state established,new"),
    ],
)
def test_public_status_requires_exact_default_formatted_nft_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, before: str, after: str
) -> None:
    p = wg()
    p["listen_port"] = 51820
    p["peers"][0]["endpoint_address"] = None
    p["peers"][0]["endpoint_port"] = None
    p["ingress"] = [{"peer_address": "10.77.0.2", "port": 443}]
    p["egress"] = []
    runtime.validate_config(p)
    f = fences(p)
    f["peers"] = [{"id": "lich-b", "generation": 3, "enabled": True}]
    observed = _OBSERVED_NFT.replace(before, after) if before else _OBSERVED_NFT
    assert not before or observed != _OBSERVED_NFT
    calls: list[tuple[str, ...]] = []
    public_key = p["peers"][0]["public_key"]

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[0] == runtime.NFT:
            # Default output never opts into reverse DNS, service names or numeric enum names.
            assert argv == (runtime.NFT, "--stateless", "list", "table", "inet", "lychd_tether")
            return observed
        assert argv[:3] == (runtime.WG, "show", "wg0")
        return {"peers": public_key, "allowed-ips": public_key + " 10.77.0.2/32", "public-key": public_key}[argv[3]]

    def current_fences(_p: dict[str, Any]) -> dict[str, Any]:
        return f

    def current_capabilities(_role: str) -> dict[str, str]:
        return {"CapEff": "1000"}

    status = tmp_path / "status" / "status.json"
    monkeypatch.setattr(runtime, "run", fake_run)
    monkeypatch.setattr(runtime, "load_fences", current_fences)
    monkeypatch.setattr(runtime, "capabilities", current_capabilities)
    monkeypatch.setattr(runtime, "STATUS", status)
    if before:
        with pytest.raises(ValueError, match="refused"):
            runtime.public_status(p, wg=True)
        assert not status.exists()
    else:
        runtime.public_status(p, wg=True)
        result = json.loads(status.read_text())
        assert result["enabled"] is True
        assert result["peer_public_keys"] == [public_key]
        assert result["public_key"] == public_key
    assert len(calls) == 4
