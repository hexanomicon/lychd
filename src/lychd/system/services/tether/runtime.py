"""Standalone, standard-library Tether container roles with closed public inputs.

The compiler supplies destinations; clients select them but cannot supply new ones.
Every relay owns both streams. Durable fences are polled independently of the host
request, and all missing, malformed or mismatched authority fails closed.
"""

from __future__ import annotations

import asyncio
import base64
import errno
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

CONFIG = Path("/etc/lychd-tether/config.json")
FENCES = Path("/etc/lychd-tether/fences.json")
IP, NFT, WG, SSHD = "/usr/sbin/ip", "/usr/sbin/nft", "/usr/bin/wg", "/usr/sbin/sshd"
POLL_SECONDS = 0.1
MAX_CONFIG = 262144
MAX_HEADER = 2048
KEY_BYTES = 32
MAX_SOCKET_PATH = 108
MAX_STREAMS = 128
STATUS_MAX_AGE = 3
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
STATUS = Path("/tmp/lychd-tether-status/status.json")  # noqa: S108 - private role tmpfs, directory mode verified
ACK = b'{"version":1,"ok":true}\n'
COMMON = {"schema", "version", "role", "network_id", "installation_epoch", "generation", "policy_digest", "fence_path"}
ROLE_FIELDS = {
    "wireguard": {
        "interface",
        "address",
        "listen_port",
        "private_key_path",
        "peers",
        "ingress",
        "egress",
        "owner_loopback_port",
    },
    "imported-relay": {"remote_lich_id", "allowed_callers", "caller_uid", "routes"},
    "offered-relay": {"services", "peers"},
    "owner-ssh": {
        "peer_id",
        "peer_generation",
        "peer_address",
        "listen_address",
        "listen_port",
        "ssh_public_key",
        "ssh_host_key_path",
        "target_address",
        "target_port",
    },
}


def require(value: bool) -> None:  # noqa: FBT001 - assertion helper, not a mode flag
    """Keep runtime failure messages free of input and secret material."""
    if not value:
        message = "Tether runtime input or authority refused"
        raise ValueError(message)


def exact(value: Any, fields: set[str]) -> dict[str, Any]:
    """Admit one closed object, never a permissive imported configuration."""
    require(type(value) is dict and set(value) == fields)
    return value


def integer(value: Any, minimum: int = 1, maximum: int = 65535) -> int:
    require(type(value) is int and minimum <= value <= maximum)
    return value


def identifier(value: Any) -> str:
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}", value) is not None)
    return value


def address(value: Any) -> str:
    require(type(value) is str)
    parsed = ipaddress.IPv4Address(value)
    require(str(parsed) == value and not parsed.is_multicast and not parsed.is_unspecified)
    return value


def key(value: Any) -> str:
    require(type(value) is str)
    decoded = base64.b64decode(value, validate=True)
    require(len(decoded) == KEY_BYTES and any(decoded) and base64.b64encode(decoded).decode() == value)
    return value


def rows(value: Any, maximum: int = 256) -> list[Any]:
    require(type(value) is list and len(value) <= maximum)
    return value


def unique(values: list[Any]) -> None:
    require(len(values) == len(set(values)))


def read_file(path: Path, maximum: int = MAX_CONFIG, *, secret: bool = False) -> bytes:
    """Read one non-symlink regular file through its verified descriptor."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o022)
        if secret:
            require(info.st_uid == os.geteuid() and not info.st_mode & 0o077)
        result = os.read(fd, maximum + 1)
        require(len(result) <= maximum)
        return result
    finally:
        os.close(fd)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    unique([name for name, _ in pairs])
    return dict(pairs)


def decode(raw: bytes) -> Any:
    return json.loads(raw.decode("ascii"), object_pairs_hook=_object)


def validate_config(p: Any) -> dict[str, Any]:  # noqa: C901, PLR0912, PLR0915 - closed role wire validator
    """Validate the compiler wire format again at the capability boundary."""
    require(type(p) is dict and p.get("role") in ROLE_FIELDS)
    p = cast("dict[str, Any]", p)
    exact(p, COMMON | ROLE_FIELDS[p["role"]])
    require(p["schema"] == "lychd.tether.runtime" and type(p["version"]) is int and p["version"] == 1)
    require(p["fence_path"] == str(FENCES))
    identifier(p["network_id"])
    integer(p["generation"], 1, 2**63 - 1)
    require(type(p["installation_epoch"]) is str and re.fullmatch(r"[0-9a-f]{32}", p["installation_epoch"]) is not None)
    require(type(p["policy_digest"]) is str and re.fullmatch(r"[0-9a-f]{64}", p["policy_digest"]) is not None)
    role = p["role"]
    if role == "wireguard":
        require(
            type(p["interface"]) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,14}", p["interface"]) is not None
        )
        require(p["interface"] not in {"lo", "eth0", "tap0"})
        local = ipaddress.IPv4Interface(p["address"])
        require(str(local) == p["address"])
        address(str(local.ip))
        integer(p["listen_port"], 0)
        require(p["private_key_path"] == "/run/secrets/wg-private")
        for peer in rows(p["peers"]):
            exact(
                peer,
                {
                    "id",
                    "generation",
                    "public_key",
                    "allowed_ips",
                    "endpoint_address",
                    "endpoint_port",
                    "keepalive",
                    "preshared_key_path",
                },
            )
            identifier(peer["id"])
            integer(peer["generation"], 1, 2**63 - 1)
            key(peer["public_key"])
            for item in rows(peer["allowed_ips"], 64):
                network = ipaddress.IPv4Network(item)
                require(network.prefixlen == KEY_BYTES and str(network) == item)
                address(str(network.network_address))
            require(bool(peer["allowed_ips"]))
            if peer["endpoint_address"] is None:
                require(peer["endpoint_port"] is None and p["listen_port"] != 0)
            else:
                address(peer["endpoint_address"])
                integer(peer["endpoint_port"])
            integer(peer["keepalive"], 0, 65535)
            secret = peer["preshared_key_path"]
            require(
                secret is None
                or (type(secret) is str and re.fullmatch(r"/run/secrets/psk-[0-9a-f]{8,64}", secret) is not None)
            )
        unique([peer["id"] for peer in p["peers"]])
        unique([peer["public_key"] for peer in p["peers"]])
        unique([item for peer in p["peers"] for item in peer["allowed_ips"]])
        require(f"{local.ip}/32" not in [item for peer in p["peers"] for item in peer["allowed_ips"]])
        for entry in rows(p["ingress"]):
            exact(entry, {"peer_address", "port"})
            address(entry["peer_address"])
            integer(entry["port"])
        for entry in rows(p["egress"]):
            exact(entry, {"address", "port", "protocol"})
            address(entry["address"])
            integer(entry["port"])
            require(entry["protocol"] in {"tcp", "udp"})
        if p["owner_loopback_port"] is not None:
            integer(p["owner_loopback_port"])
    elif role == "imported-relay":
        identifier(p["remote_lich_id"])
        integer(p["caller_uid"], 0, 2**32 - 2)
        for caller in rows(p["allowed_callers"], 64):
            identifier(caller)
        require(bool(p["allowed_callers"]))
        for route in rows(p["routes"], 64):
            exact(route, {"service_id", "generation", "socket_path", "address", "port", "application_identity_ref"})
            identifier(route["service_id"])
            identifier(route["application_identity_ref"])
            require(route["generation"] == p["generation"] and type(route["generation"]) is int)
            require(
                type(route["socket_path"]) is str
                and re.fullmatch(r"/run/lychd-tether/[0-9a-f]{8,64}/[0-9a-f]{8,64}\.sock", route["socket_path"])
                is not None
            )
            require(len(route["socket_path"].encode()) < MAX_SOCKET_PATH)
            address(route["address"])
            integer(route["port"])
        unique([route["service_id"] for route in p["routes"]])
        unique([route["socket_path"] for route in p["routes"]])
    elif role == "offered-relay":
        for service in rows(p["services"], 64):
            exact(service, {"service_id", "listen_address", "listen_port", "backend_address", "backend_port"})
            identifier(service["service_id"])
            address(service["listen_address"])
            address(service["backend_address"])
            integer(service["listen_port"])
            integer(service["backend_port"])
        unique([service["service_id"] for service in p["services"]])
        unique([(service["listen_address"], service["listen_port"]) for service in p["services"]])
        for peer in rows(p["peers"]):
            exact(peer, {"id", "generation", "address", "service_ids"})
            identifier(peer["id"])
            integer(peer["generation"], 1, 2**63 - 1)
            address(peer["address"])
            for name in rows(peer["service_ids"], 64):
                require(name in {service["service_id"] for service in p["services"]})
        unique([peer["id"] for peer in p["peers"]])
        unique([peer["address"] for peer in p["peers"]])
    else:
        identifier(p["peer_id"])
        integer(p["peer_generation"], 1, 2**63 - 1)
        address(p["peer_address"])
        address(p["listen_address"])
        integer(p["listen_port"])
        integer(p["target_port"])
        require(p["target_address"] == "127.0.0.1" and p["ssh_host_key_path"] == "/run/secrets/ssh-host")
        require(
            type(p["ssh_public_key"]) is str
            and re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]{68}", p["ssh_public_key"]) is not None
        )
    return p


def load_config() -> dict[str, Any]:
    return validate_config(decode(read_file(CONFIG)))


def validate_fences(raw: Any, p: dict[str, Any]) -> dict[str, Any]:
    f = exact(raw, {"schema", "version", "installation_epoch", "network_id", "generation", "enabled", "peers"})
    require(f["schema"] == "lychd.tether.fences" and type(f["version"]) is int and f["version"] == 1)
    require(f["installation_epoch"] == p["installation_epoch"] and f["network_id"] == p["network_id"])
    require(type(f["enabled"]) is bool and type(f["generation"]) is int and f["generation"] == p["generation"])
    for peer in rows(f["peers"]):
        exact(peer, {"id", "generation", "enabled"})
        identifier(peer["id"])
        integer(peer["generation"], 1, 2**63 - 1)
        require(type(peer["enabled"]) is bool)
    unique([peer["id"] for peer in f["peers"]])
    return f


def load_fences(p: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return validate_fences(decode(read_file(FENCES)), p)
    except (OSError, ValueError, TypeError, KeyError):
        return None


def admitted(
    p: dict[str, Any], fence: dict[str, Any] | None, peer_id: str | None = None, generation: int | None = None
) -> bool:
    if fence is None or not fence["enabled"]:
        return False
    if peer_id is None or (p["role"] == "wireguard" and p["listen_port"] == 0):
        return True
    return any(
        row["id"] == peer_id and row["enabled"] and (generation is None or row["generation"] == generation)
        for row in fence["peers"]
    )


def run(argv: tuple[str, ...], *, content: str | None = None, pass_fds: tuple[int, ...] = ()) -> str:
    result = subprocess.run(  # noqa: S603 - fixed tools and validated closed projections
        argv, input=content, capture_output=True, text=True, timeout=10, check=False, pass_fds=pass_fds
    )
    require(result.returncode == 0 and len(result.stdout) <= MAX_CONFIG)
    return result.stdout


def nft_policy(p: dict[str, Any], fence: dict[str, Any] | None) -> str:  # noqa: C901 - exact direction-specific rules
    """No transit, IPv6, ambient DNS, or imported inner traffic on outer NICs."""
    interface = p["interface"]
    local = p["address"].split("/")[0]
    incoming: list[str] = []
    outgoing: list[str] = []
    if admitted(p, fence):
        if p["listen_port"]:
            incoming.append(f' iifname != "{interface}" meta nfproto ipv4 udp dport {p["listen_port"]} accept')
            outgoing.append(f' oifname != "{interface}" meta nfproto ipv4 udp sport {p["listen_port"]} accept')
        active_addresses = {
            item.split("/")[0]
            for peer in p["peers"]
            if admitted(p, fence, peer["id"], peer["generation"])
            for item in peer["allowed_ips"]
        }
        for peer in p["peers"]:
            if admitted(p, fence, peer["id"], peer["generation"]) and peer["endpoint_address"] is not None:
                endpoint, port = peer["endpoint_address"], peer["endpoint_port"]
                outgoing.append(f' oifname != "{interface}" ip daddr {endpoint} udp dport {port} accept')
                incoming.append(
                    f' iifname != "{interface}" ip saddr {endpoint} udp sport {port} ct state established accept'
                )
        for row in p["ingress"]:
            if row["peer_address"] in active_addresses:
                peer, port = row["peer_address"], row["port"]
                incoming.append(
                    f' iifname "{interface}" ip saddr {peer} ip daddr {local} tcp dport {port} ct state new,established accept'
                )
                outgoing.append(
                    f' oifname "{interface}" ip saddr {local} ip daddr {peer} tcp sport {port} ct state established accept'
                )
        for row in p["egress"]:
            if row["protocol"] != "tcp":
                continue  # Outer UDP comes only from the admitted WireGuard peer endpoints.
            target, port = row["address"], row["port"]
            operator = "!=" if p["listen_port"] else ""
            outgoing.append(
                f' oifname {operator} "{interface}" ip daddr {target} tcp dport {port} ct state new,established accept'
            )
            incoming.append(
                f' iifname {operator} "{interface}" ip saddr {target} tcp sport {port} ct state established accept'
            )
        if p["owner_loopback_port"] is not None:
            port = p["owner_loopback_port"]
            for rules in (incoming, outgoing):
                iface = "iifname" if rules is incoming else "oifname"
                rules.extend(
                    (
                        f' {iface} "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport {port} ct state new,established accept',
                        f' {iface} "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport {port} ct state established accept',
                    )
                )
    return (
        f'table inet lychd_tether {{\n comment "{ownership_marker(p)}"\n'
        " chain input { type filter hook input priority -150; policy drop;\n"
        + "\n".join(incoming)
        + "\n }\n chain output { type filter hook output priority -150; policy drop;\n"
        + "\n".join(outgoing)
        + "\n }\n chain forward { type filter hook forward priority -150; policy drop; }\n}\n"
    )


def ownership_marker(p: dict[str, Any]) -> str:
    """Identify the exact installation/network in its private namespace."""
    return f"lychd-tether:{p['installation_epoch']}:{p['network_id']}"


def existing_owned_table(p: dict[str, Any]) -> bool:
    """Adopt only our exact marked table; never flush another firewall owner."""
    try:
        document = decode(run((NFT, "-j", "list", "table", "inet", "lychd_tether")).encode())
    except ValueError:
        return False  # Create handles absence and refuses other tool failures.
    require(type(document) is dict and type(document.get("nftables")) is list)
    document = cast("dict[str, Any]", document)
    tables: list[Any] = [row["table"] for row in document["nftables"] if type(row) is dict and "table" in row]
    require(len(tables) == 1)
    table = tables[0]
    require(type(table) is dict)
    table = cast("dict[str, Any]", table)
    require(
        table.get("family") == "inet"
        and table.get("name") == "lychd_tether"
        and table.get("comment") == ownership_marker(p)
    )
    return True


def owned_interface_routes(p: dict[str, Any]) -> set[str] | None:
    """Recover only the marked WireGuard interface and its exact static routes."""
    try:
        links = decode(run((IP, "-j", "-d", "link", "show", "dev", p["interface"])).encode())
    except ValueError:
        return None
    require(type(links) is list and len(links) == 1)
    links = cast("list[dict[str, Any]]", links)
    require(
        links[0].get("ifalias") == ownership_marker(p) and links[0].get("linkinfo", {}).get("info_kind") == "wireguard"
    )
    addresses = decode(run((IP, "-j", "address", "show", "dev", p["interface"])).encode())
    require(type(addresses) is list and len(addresses) == 1)
    addresses = cast("list[dict[str, Any]]", addresses)
    actual = {(row.get("family"), row.get("local"), row.get("prefixlen")) for row in addresses[0].get("addr_info", [])}
    expected = ipaddress.IPv4Interface(p["address"])
    require(actual == {("inet", str(expected.ip), expected.network.prefixlen)})
    result: set[str] = set()
    for row in decode(run((IP, "-j", "route", "show", "dev", p["interface"])).encode()):
        if row.get("protocol") == "kernel":
            continue
        destination = row.get("dst")
        require(type(destination) is str and destination != "default")
        network = ipaddress.IPv4Network(destination if "/" in destination else destination + "/32")
        require(network.prefixlen == KEY_BYTES)
        result.add(str(network))
    return result


def install_policy(p: dict[str, Any], fence: dict[str, Any] | None, *, initial: bool = False) -> None:
    policy = nft_policy(p, fence)
    content = "create " + policy if initial else "delete table inet lychd_tether\n" + policy
    run((NFT, "-f", "-"), content=content)


def wireguard_config(p: dict[str, Any], fence: dict[str, Any] | None) -> str:
    private = key(read_file(Path(p["private_key_path"]), 128, secret=True).decode().strip())
    lines = ["[Interface]", f"PrivateKey = {private}", f"ListenPort = {p['listen_port']}"]
    for peer in p["peers"]:
        if not admitted(p, fence, peer["id"], peer["generation"]):
            continue
        lines.extend(
            (
                "[Peer]",
                f"PublicKey = {peer['public_key']}",
                f"AllowedIPs = {','.join(peer['allowed_ips'])}",
                f"PersistentKeepalive = {peer['keepalive']}",
            )
        )
        if peer["endpoint_address"] is not None:
            lines.append(f"Endpoint = {peer['endpoint_address']}:{peer['endpoint_port']}")
        if peer["preshared_key_path"] is not None:
            secret = key(read_file(Path(peer["preshared_key_path"]), 128, secret=True).decode().strip())
            lines.append(f"PresharedKey = {secret}")
    return "\n".join(lines) + "\n"


def configure_peers(p: dict[str, Any], fence: dict[str, Any] | None) -> None:
    fd = os.memfd_create("tether-wireguard", os.MFD_CLOEXEC)
    try:
        os.write(fd, wireguard_config(p, fence).encode())
        os.lseek(fd, 0, os.SEEK_SET)
        run((WG, "syncconf", p["interface"], f"/proc/self/fd/{fd}"), pass_fds=(fd,))
    finally:
        os.close(fd)


def capabilities(role: str) -> dict[str, str]:
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    expected = 1 << 12 if role == "wireguard" else ((1 << 6) | (1 << 7) | (1 << 18) if role == "owner-ssh" else 0)
    require(all(int(fields[name].strip(), 16) == expected for name in ("CapEff", "CapPrm", "CapBnd")))
    require(
        all(int(fields[name].strip(), 16) == 0 for name in ("CapInh", "CapAmb"))
        and fields.get("NoNewPrivs", "").strip() == "1"
    )
    return {name: fields[name].strip() for name in ("CapEff", "CapPrm", "CapBnd", "NoNewPrivs")}


def notify_ready() -> None:
    name = os.environ.get("NOTIFY_SOCKET")
    if not name:
        return
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.connect("\x00" + name[1:] if name.startswith("@") else name)
        connection.sendall(b"READY=1")


async def wireguard(p: dict[str, Any]) -> None:
    """Reconcile public peer sets without restarting the shared interface."""
    interface = p["interface"]
    created = False
    install_policy(p, None, initial=not existing_owned_table(p))
    try:
        existing_routes = owned_interface_routes(p)
        if existing_routes is None:
            run((IP, "link", "add", "dev", interface, "type", "wireguard"))
            created = True
            run((IP, "link", "set", "dev", interface, "alias", ownership_marker(p)))
            run((IP, "address", "add", p["address"], "dev", interface))
        else:
            created = True
        previous: bytes | None = None
        routes: set[str] = existing_routes or set()
        observed = 0.0
        while True:
            new = load_config()
            require(
                all(
                    new[field] == p[field]
                    for field in (
                        "role",
                        "network_id",
                        "installation_epoch",
                        "interface",
                        "address",
                        "listen_port",
                        "private_key_path",
                    )
                )
            )
            require(new["generation"] >= p["generation"])
            p = new
            fence = load_fences(p)
            fingerprint = json.dumps([p, fence], sort_keys=True).encode()
            if fingerprint != previous:
                install_policy(p, None)
                configure_peers(p, fence)
                desired_routes = {
                    item
                    for peer in p["peers"]
                    if admitted(p, fence, peer["id"], peer["generation"])
                    for item in peer["allowed_ips"]
                }
                # Route installation requires an up device; denial remains until reconciliation finishes.
                run((IP, "link", "set", "dev", interface, "up"))
                for item in routes - desired_routes:
                    run((IP, "route", "delete", item, "dev", interface))
                for item in desired_routes - routes:
                    run((IP, "route", "add", item, "dev", interface))
                routes = desired_routes
                install_policy(p, fence)
                previous = fingerprint
                notify_ready()
            if time.monotonic() - observed >= 1:
                public_status(p, fence=fence, wg=True)
                observed = time.monotonic()
            await asyncio.sleep(POLL_SECONDS)
    finally:
        install_policy(p, None)
        if created:
            run((IP, "link", "delete", "dev", interface))


class Relay:
    """Own bounded streams and terminate the exact generation when fenced."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Own stream tasks within exactly one immutable role generation."""
        self.config = config
        self.tasks: dict[asyncio.Task[Any], tuple[str | None, int | None]] = {}
        self.servers: list[asyncio.Server] = []
        self.sockets: list[Path] = []
        self.lock_descriptor: int | None = None

    def current(self, peer_id: str | None = None, generation: int | None = None) -> bool:
        if peer_id is not None and not any(
            row["id"] == peer_id and row["generation"] == generation for row in self.config["peers"]
        ):
            return False
        return admitted(self.config, load_fences(self.config), peer_id, generation)

    def validate_header(self, raw: bytes, route: dict[str, Any], uid: int) -> None:
        require(len(raw) <= MAX_HEADER and raw.endswith(b"\n") and uid == self.config["caller_uid"])
        h = exact(
            decode(raw),
            {
                "version",
                "installation_epoch",
                "policy_digest",
                "remote_lich_id",
                "attachment_id",
                "generation",
                "service_id",
                "caller",
            },
        )
        require(type(h["version"]) is int and h["version"] == 1 and type(h["generation"]) is int)
        require(h["policy_digest"] == self.config["policy_digest"])
        require(
            h["installation_epoch"] == self.config["installation_epoch"]
            and h["remote_lich_id"] == self.config["remote_lich_id"]
        )
        require(
            h["attachment_id"] == self.config["network_id"]
            and h["generation"] == route["generation"]
            and h["service_id"] == route["service_id"]
        )
        require(type(h["caller"]) is str and h["caller"] in self.config["allowed_callers"])

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, route: dict[str, Any]) -> None:  # noqa: PLR0915 - owned stream lifecycle
        task = asyncio.current_task()
        require(task is not None)
        task = cast("asyncio.Task[Any]", task)
        upstream: asyncio.StreamWriter | None = None
        peer_id: str | None = None
        generation: int | None = None
        self.tasks[task] = (None, None)
        try:
            require(len(self.tasks) <= MAX_STREAMS and self.current())
            if self.config["role"] == "imported-relay":
                credentials = writer.get_extra_info("socket").getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                )
                _, uid, _ = struct.unpack("3i", credentials)
                raw = await asyncio.wait_for(reader.readuntil(b"\n"), 5)
                self.validate_header(raw, route, uid)
                target, port = route["address"], route["port"]
            else:
                source = writer.get_extra_info("peername")[0]
                peer = next(
                    (
                        row
                        for row in self.config["peers"]
                        if row["address"] == source and route["service_id"] in row["service_ids"]
                    ),
                    None,
                )
                require(peer is not None)
                peer = cast("dict[str, Any]", peer)
                peer_id, generation = peer["id"], peer["generation"]
                target, port = route["backend_address"], route["backend_port"]
            self.tasks[task] = (peer_id, generation)
            require(self.current(peer_id, generation))
            remote, upstream = await asyncio.wait_for(
                asyncio.open_connection(target, port, family=socket.AF_INET, limit=65536), 10
            )
            require(self.current(peer_id, generation))
            if self.config["role"] == "imported-relay":
                writer.write(ACK)
                await writer.drain()

            async def pump(source: asyncio.StreamReader, destination: asyncio.StreamWriter) -> None:
                while True:
                    chunk = await source.read(16384)
                    if not chunk:
                        return
                    require(self.current(peer_id, generation))
                    destination.write(chunk)
                    await destination.drain()

            left = asyncio.create_task(pump(reader, upstream))
            right = asyncio.create_task(pump(remote, writer))
            try:
                await asyncio.wait((left, right), return_when=asyncio.FIRST_COMPLETED)
            finally:
                left.cancel()
                right.cancel()
                await asyncio.gather(left, right, return_exceptions=True)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            TimeoutError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ):
            pass
        finally:
            writer.close()
            if upstream is not None:
                upstream.close()
            self.tasks.pop(task, None)

    def lock_producer(self, directory: Path) -> None:
        """Hold an exclusive producer lease across restart-safe socket recovery."""
        metadata = directory.lstat()
        require(
            stat.S_ISDIR(metadata.st_mode)
            and metadata.st_uid == os.geteuid()
            and stat.S_IMODE(metadata.st_mode) == PRIVATE_DIRECTORY_MODE
        )
        fd = os.open(directory / ".producer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            info = os.fstat(fd)
            require(
                stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and info.st_uid == os.geteuid()
                and stat.S_IMODE(info.st_mode) == PRIVATE_FILE_MODE
            )
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        self.lock_descriptor = fd

    def recover_socket(self, path: Path) -> None:
        """Unlink only an owned stale socket, refusing live listeners and other types."""
        require(self.lock_descriptor is not None)
        try:
            before = path.lstat()
        except FileNotFoundError:
            return
        require(
            stat.S_ISSOCK(before.st_mode)
            and before.st_uid == os.geteuid()
            and stat.S_IMODE(before.st_mode) == PRIVATE_FILE_MODE
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.0)
            result = probe.connect_ex(str(path))
        require(result == errno.ECONNREFUSED)
        after = path.lstat()
        require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino))
        path.unlink()

    async def serve(self) -> None:  # noqa: C901, PLR0912 - fixed listener and fence lifecycle
        try:
            if self.config["role"] == "imported-relay":
                require(bool(self.config["routes"]))
                directories = {Path(row["socket_path"]).parent for row in self.config["routes"]}
                require(len(directories) == 1)
                self.lock_producer(next(iter(directories)))
                for route in self.config["routes"]:
                    path = Path(route["socket_path"])
                    self.recover_socket(path)
                    server = await asyncio.start_unix_server(
                        lambda r, w, route=route: self.handle(r, w, route), path=str(path), limit=MAX_HEADER
                    )
                    path.chmod(0o600)  # noqa: ASYNC240 - bounded local socket admission
                    self.sockets.append(path)
                    self.servers.append(server)
            else:
                for route in self.config["services"]:
                    server = await asyncio.start_server(
                        lambda r, w, route=route: self.handle(r, w, route),
                        route["listen_address"],
                        route["listen_port"],
                        family=socket.AF_INET,
                        limit=65536,
                    )
                    self.servers.append(server)
            notify_ready()
            while True:
                if self.config["role"] == "offered-relay":
                    new = load_config()
                    require(
                        all(
                            new[field] == self.config[field]
                            for field in ("role", "network_id", "installation_epoch", "generation", "services")
                        )
                    )
                    self.config = new
                for task, (peer, generation) in tuple(self.tasks.items()):
                    if not self.current(peer, generation):
                        task.cancel()
                counts: dict[str, int] = {}
                for peer, _generation in self.tasks.values():
                    name = peer or self.config["network_id"]
                    counts[name] = counts.get(name, 0) + 1
                public_status(self.config, fence=load_fences(self.config), streams=counts)
                await asyncio.sleep(POLL_SECONDS)
        finally:
            for server in self.servers:
                server.close()
                await server.wait_closed()
            tasks = tuple(self.tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for path in self.sockets:
                path.unlink(missing_ok=True)
            if self.lock_descriptor is not None:
                os.close(self.lock_descriptor)
                self.lock_descriptor = None


def ssh_config(p: dict[str, Any]) -> str:
    """Generate only the single-purpose forwarding daemon's closed directives."""
    return f"""Port {p["listen_port"]}
ListenAddress {p["listen_address"]}
AddressFamily inet
HostKey /run/secrets/ssh-host
PidFile /run/sshd/tether.pid
AuthorizedKeysFile /run/sshd/authorized_keys
AllowUsers tether
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
HostbasedAuthentication no
UsePAM no
UseDNS no
MaxSessions 0
MaxAuthTries 3
LoginGraceTime 20
MaxStartups 8:30:16
AllowTcpForwarding local
PermitOpen 127.0.0.1:{p["target_port"]}
PermitListen none
AllowStreamLocalForwarding no
PermitTTY no
PermitTunnel no
X11Forwarding no
AllowAgentForwarding no
PermitUserRC no
PermitUserEnvironment no
StrictModes yes
LogLevel ERROR
"""


def write_private(path: Path, content: str, mode: int = 0o600) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        os.fchmod(fd, mode)
        os.write(fd, content.encode())
    finally:
        os.close(fd)


async def owner_ssh(p: dict[str, Any]) -> None:
    require(admitted(p, load_fences(p), p["peer_id"], p["peer_generation"]))
    read_file(Path(p["ssh_host_key_path"]), 8192, secret=True)
    Path("/run/sshd").mkdir(mode=0o755, exist_ok=True)  # noqa: ASYNC240 - fixed tmpfs
    Path("/run/sshd").chmod(0o755)  # noqa: ASYNC240 - permit only public key traversal
    write_private(Path("/run/sshd/authorized_keys"), p["ssh_public_key"] + "\n", 0o644)
    write_private(Path("/run/sshd/config"), ssh_config(p))
    run((SSHD, "-t", "-f", "/run/sshd/config"))
    process = await asyncio.create_subprocess_exec(
        SSHD, "-D", "-e", "-f", "/run/sshd/config", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        notify_ready()
        while process.returncode is None and admitted(p, load_fences(p), p["peer_id"], p["peer_generation"]):
            public_status(p, fence=load_fences(p))
            await asyncio.sleep(POLL_SECONDS)
    finally:
        # This process is the container init. Its exit settles the PID namespace;
        # host additionally stops the exact owner-peer container/cgroup.
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 2)
            except TimeoutError:
                process.kill()
                await process.wait()


def policy_tokens(value: str) -> list[str]:
    """Normalize nft formatting only, keeping interface comparisons significant."""
    value = value.replace("priority -150", "priority mangle")
    value = re.sub(r"new\s*,\s*established", "established,new", value)
    return re.findall(r'"[^"\n]*"|[A-Za-z0-9_.:/+-]+|!=|[{};,]', value)


def public_status(
    p: dict[str, Any], *, fence: dict[str, Any] | None, streams: dict[str, int] | None = None, wg: bool = False
) -> None:
    """Observe the supplied applied snapshot; consumers separately require current authority.

    WireGuard passes the fence used for its kernel reconciliation, so a concurrent
    publication cannot turn an unapplied admission change into apparent kernel drift.
    """
    result: dict[str, Any] = {
        "schema": "lychd.tether.runtime-observation",
        "version": 1,
        "role": p["role"],
        "network_id": p["network_id"],
        "installation_epoch": p["installation_epoch"],
        "generation": p["generation"],
        "policy_digest": p["policy_digest"],
        "enabled": admitted(p, fence),
        "fence_digest": hashlib.sha256(json.dumps(fence, sort_keys=True).encode()).hexdigest(),
        "observed_monotonic": time.monotonic(),
        "capabilities": capabilities(p["role"]),
        "streams": streams or {},
    }
    if wg:
        actual = set(run((WG, "show", p["interface"], "peers")).split())
        expected = {peer["public_key"] for peer in p["peers"] if admitted(p, fence, peer["id"], peer["generation"])}
        require(actual == expected)
        actual_allowed: dict[str, set[str]] = {}
        for line in run((WG, "show", p["interface"], "allowed-ips")).splitlines():
            parts = line.split()
            require(bool(parts) and bool(parts[1:]))
            actual_allowed[parts[0]] = set(parts[1:])
        expected_allowed = {
            peer["public_key"]: set(peer["allowed_ips"]) for peer in p["peers"] if peer["public_key"] in expected
        }
        require(actual_allowed == expected_allowed)
        own = key(run((WG, "show", p["interface"], "public-key")).strip())
        policy = run((NFT, "--stateless", "list", "table", "inet", "lychd_tether"))
        require(policy_tokens(policy) == policy_tokens(nft_policy(p, fence)))
        result.update(
            public_key=own, peer_public_keys=sorted(actual), nft_digest=hashlib.sha256(policy.encode()).hexdigest()
        )
    STATUS.parent.mkdir(mode=0o700, exist_ok=True)
    directory = STATUS.parent.lstat()
    require(
        stat.S_ISDIR(directory.st_mode)
        and stat.S_IMODE(directory.st_mode) == PRIVATE_DIRECTORY_MODE
        and directory.st_uid == os.geteuid()
    )
    temporary = STATUS.with_suffix(".tmp")
    write_private(temporary, json.dumps(result, sort_keys=True) + "\n")
    temporary.replace(STATUS)


def observe() -> None:
    """Read an independently refreshed bounded observation, refusing stale output."""
    p = load_config()
    raw = read_file(STATUS)
    value = decode(raw)
    require(type(value) is dict and value.get("policy_digest") == p["policy_digest"])
    value = cast("dict[str, Any]", value)
    stamp = value.get("observed_monotonic")
    require(type(stamp) in {int, float})
    stamp = cast("int | float", stamp)
    require(0 <= time.monotonic() - stamp < STATUS_MAX_AGE)
    require(
        value.get("fence_digest") == hashlib.sha256(json.dumps(load_fences(p), sort_keys=True).encode()).hexdigest()
    )
    print(raw.decode().strip())  # noqa: T201 - public bounded observation protocol


async def main_async() -> None:
    require(sys.argv[1:] == [str(CONFIG)])
    task = asyncio.current_task()
    require(task is not None)
    task = cast("asyncio.Task[Any]", task)
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, task.cancel)
    p = load_config()
    capabilities(p["role"])
    require(admitted(p, load_fences(p)))
    if p["role"] == "wireguard":
        await wireguard(p)
    elif p["role"] == "owner-ssh":
        await owner_ssh(p)
    else:
        await Relay(p).serve()


def main() -> None:
    os.umask(0o077)
    try:
        if sys.argv[1:] == ["--observe", str(CONFIG)]:
            observe()
        else:
            asyncio.run(main_async())
    except (Exception, KeyboardInterrupt, asyncio.CancelledError):  # noqa: BLE001 - no foreign or secret-bearing diagnostics
        print("Tether runtime refused or lost its admitted profile", file=sys.stderr)  # noqa: T201
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
