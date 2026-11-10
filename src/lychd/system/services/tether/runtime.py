"""Standalone standard-library entry point for the fixed Tether OCI image.

This file is installed directly at /usr/libexec/lychd-tether-runtime. It imports
no Core code or dependencies. Public projections contain no private keys.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType
from typing import Any, NoReturn, cast

_KEY_BYTES = 32
_PROJECT = Path("/etc/lychd-tether")
_IP = "/usr/sbin/ip"
_NFT = "/usr/sbin/nft"
_WG = "/usr/bin/wg"
_SSHD = "/usr/sbin/sshd"
_FIELDS = {
    "interface",
    "server_address",
    "listen_port",
    "peer_public_key",
    "peer_address",
    "persistent_keepalive",
    "ssh_port",
    "altar_port",
}


def _run(argv: tuple[str, ...], *, content: str | None = None, pass_fds: tuple[int, ...] = ()) -> str:
    completed = subprocess.run(  # noqa: S603 - only fixed distro tools consume validated projections
        argv, input=content, capture_output=True, text=True, timeout=10, check=False, pass_fds=pass_fds
    )
    if completed.returncode:
        msg = "Tether runtime command failed; diagnostics suppressed"
        raise RuntimeError(msg)
    return completed.stdout


def _read(path: Path, maximum: int = 65536) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
            msg = "Unsafe Tether runtime input"
            raise RuntimeError(msg)
        content = os.read(descriptor, maximum + 1)
        if len(content) > maximum:
            msg = "Oversized Tether runtime input"
            raise RuntimeError(msg)
        return content.decode()
    finally:
        os.close(descriptor)


def _public() -> dict[str, Any]:
    raw: Any = json.loads(_read(_PROJECT / "public.json"))
    projection = cast("dict[str, Any]", raw)
    if not isinstance(raw, dict) or set(projection) != _FIELDS:
        msg = "Unknown or missing Tether runtime projection field"
        raise RuntimeError(msg)
    interface = projection["interface"]
    if (
        not isinstance(interface, str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,14}", interface) is None
        or interface in {"lo", "tap0", "eth0"}
    ):
        msg = "Invalid Tether interface"
        raise RuntimeError(msg)
    networks = tuple(ipaddress.IPv4Network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
    for field in ("server_address", "peer_address"):
        address = ipaddress.IPv4Interface(projection[field])
        if address.network.prefixlen != _KEY_BYTES or not any(address.ip in network for network in networks):
            msg = "Tether addresses must be RFC1918 /32"
            raise RuntimeError(msg)
        projection[field] = str(address)
    if projection["server_address"] == projection["peer_address"]:
        msg = "Overlapping Tether addresses"
        raise RuntimeError(msg)
    for field in ("listen_port", "ssh_port", "altar_port", "persistent_keepalive"):
        value = projection[field]
        low, high = (
            (0, 120) if field == "persistent_keepalive" else ((1, 65535) if field == "altar_port" else (1024, 65535))
        )
        if type(value) is not int or not low <= value <= high:
            msg = "Invalid Tether runtime port or keepalive"
            raise RuntimeError(msg)
    key = base64.b64decode(projection["peer_public_key"], validate=True)
    if len(key) != _KEY_BYTES or not any(key) or base64.b64encode(key).decode() != projection["peer_public_key"]:
        msg = "Invalid Tether peer public key"
        raise RuntimeError(msg)
    return projection


def nft_policy(p: dict[str, Any]) -> str:
    """Render the fixed namespace policy installed before interface up."""
    server, peer = p["server_address"].split("/")[0], p["peer_address"].split("/")[0]
    interface, udp, ssh, altar = p["interface"], p["listen_port"], p["ssh_port"], p["altar_port"]
    return f"""table inet lychd_tether {{
 chain input {{
  type filter hook input priority -150; policy drop;
  udp dport {{ 53, 853 }} drop
  tcp dport {{ 53, 853 }} drop
  meta nfproto ipv4 udp dport {udp} accept
  iifname "{interface}" ip saddr {peer} ip daddr {server} tcp dport {ssh} ct state new,established accept
  iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport {altar} ct state new,established accept
  iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport {altar} ct state established accept
 }}
 chain output {{
  type filter hook output priority -150; policy drop;
  udp dport {{ 53, 853 }} drop
  tcp dport {{ 53, 853 }} drop
  meta nfproto ipv4 udp sport {udp} accept
  oifname "{interface}" ip saddr {server} ip daddr {peer} tcp sport {ssh} ct state established accept
  oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport {altar} ct state new,established accept
  oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport {altar} ct state established accept
 }}
 chain forward {{
  type filter hook forward priority -150; policy drop;
 }}
}}
"""


def _notify_ready() -> None:
    # sd_notify's process-local socket is the sole consumed environment value.
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        msg = "WireGuard requires the container readiness socket"
        raise RuntimeError(msg)
    if address.startswith("@"):
        address = "\x00" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.connect(address)
        connection.sendall(b"READY=1")


def _verify(p: dict[str, Any]) -> None:
    state = json.loads(_run((_IP, "-j", "address", "show", "dev", p["interface"])))
    if len(state) != 1 or "UP" not in state[0].get("flags", ()):
        msg = "WireGuard interface is not up"
        raise RuntimeError(msg)
    addresses = {(row.get("family"), row.get("local"), row.get("prefixlen")) for row in state[0].get("addr_info", ())}
    if addresses != {("inet", p["server_address"].split("/")[0], 32)}:
        msg = "WireGuard interface address differs from the exact projection"
        raise RuntimeError(msg)
    if _run((_WG, "show", p["interface"], "listen-port")).strip() != str(p["listen_port"]):
        msg = "WireGuard listen port differs"
        raise RuntimeError(msg)
    if _run((_WG, "show", p["interface"], "peers")).strip() != p["peer_public_key"]:
        msg = "WireGuard peer differs"
        raise RuntimeError(msg)
    allowed = _run((_WG, "show", p["interface"], "allowed-ips")).split()
    if allowed != [p["peer_public_key"], p["peer_address"]]:
        msg = "WireGuard allowed IPs differ"
        raise RuntimeError(msg)
    policy = _run((_NFT, "--stateless", "list", "table", "inet", "lychd_tether"))
    if _policy_tokens(policy) != _policy_tokens(nft_policy(p)):
        msg = "Tether namespace policy differs from the exact compiled rules"
        raise RuntimeError(msg)


def _policy_tokens(value: str) -> list[str]:
    """Normalize only nft's whitespace, named priority and state-set order."""
    value = value.replace("priority -150", "priority mangle").replace("new,established", "established,new")
    return re.findall(r'"[^"\n]*"|[A-Za-z0-9_.:/+-]+|[{};,]', value)


def wireguard() -> None:
    """Install policy, configure kernel WireGuard, attest, then supervise it."""
    p = _public()
    # New Pod network namespace: preexisting policy/interface refuses, never
    # flush an unknown policy or adopt a previously configured interface.
    _run((_NFT, "-f", "-"), content="create table inet lychd_tether\n" + nft_policy(p))
    private = _read(Path("/run/secrets/tether-wg-server"), 128).strip()
    decoded = base64.b64decode(private, validate=True)
    if len(decoded) != _KEY_BYTES or not any(decoded) or base64.b64encode(decoded).decode() != private:
        msg = "Invalid WireGuard server secret"
        raise RuntimeError(msg)
    interface = p["interface"]
    created = False
    try:
        _run((_IP, "link", "add", "dev", interface, "type", "wireguard"))
        created = True
        descriptor = os.memfd_create("tether-wireguard", os.MFD_CLOEXEC)
        try:
            content = f"[Interface]\nPrivateKey = {private}\nListenPort = {p['listen_port']}\n[Peer]\nPublicKey = {p['peer_public_key']}\nAllowedIPs = {p['peer_address']}\nPersistentKeepalive = {p['persistent_keepalive']}\n"
            os.write(descriptor, content.encode())
            os.lseek(descriptor, 0, os.SEEK_SET)
            _run((_WG, "setconf", interface, f"/proc/self/fd/{descriptor}"), pass_fds=(descriptor,))
        finally:
            os.close(descriptor)
        _run((_IP, "address", "add", p["server_address"], "dev", interface))
        _run((_IP, "route", "add", p["peer_address"], "dev", interface))
        _run((_IP, "link", "set", "dev", interface, "up"))
        _verify(p)
        _notify_ready()

        # The supervisor remains alive, so exiting a configuring one-shot is
        # never mistaken for transport absence. Any drift exits and stops SSH.
        def exit_cleanly(_signum: int, _frame: FrameType | None) -> NoReturn:
            sys.exit(0)

        signal.signal(signal.SIGTERM, exit_cleanly)
        signal.signal(signal.SIGINT, exit_cleanly)
        while True:
            time.sleep(2)
            _verify(p)
    finally:
        if created:
            _run((_IP, "link", "delete", "dev", interface))


def forwarder() -> None:
    """Execute only distro OpenSSH against the compiler's public configuration."""
    _read(_PROJECT / "authorized_keys")
    _read(_PROJECT / "sshd_config")
    _read(Path("/run/secrets/tether-ssh-host"))
    Path("/run/sshd").mkdir(mode=0o755, exist_ok=True)
    Path("/run/tether").mkdir(mode=0o755, exist_ok=True)
    _run((_SSHD, "-t", "-f", str(_PROJECT / "sshd_config")))
    effective = _run((_SSHD, "-T", "-f", str(_PROJECT / "sshd_config")))
    lines = dict(line.split(" ", 1) for line in effective.splitlines() if " " in line)
    required = {
        "maxsessions": "0",
        "passwordauthentication": "no",
        "kbdinteractiveauthentication": "no",
        "allowtcpforwarding": "local",
        "allowstreamlocalforwarding": "no",
        "permittty": "no",
        "permittunnel": "no",
        "x11forwarding": "no",
        "allowagentforwarding": "no",
        "usepam": "no",
        "permitlisten": "none",
    }
    if any(lines.get(name) != value for name, value in required.items()):
        msg = "OpenSSH effective policy differs from the fixed forwarding profile"
        raise RuntimeError(msg)
    os.execv(_SSHD, (_SSHD, "-D", "-e", "-f", str(_PROJECT / "sshd_config")))  # noqa: S606 - fixed distro daemon and fixed configuration


def _capabilities(role: str) -> None:
    """Refuse a wider capability set or missing no-new-privileges at runtime."""
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    expected = 1 << 12 if role == "wireguard" else (1 << 6) | (1 << 7) | (1 << 18)
    if (
        any(int(fields[name].strip(), 16) != expected for name in ("CapEff", "CapPrm", "CapBnd"))
        or any(int(fields[name].strip(), 16) != 0 for name in ("CapInh", "CapAmb"))
        or fields.get("NoNewPrivs", "").strip() != "1"
    ):
        msg = "Tether runtime capabilities differ from its exact rootless profile"
        raise RuntimeError(msg)


def main() -> None:
    """Accept only a fixed role with no command or path argument."""
    if sys.argv[1:] == ["wireguard"]:
        _capabilities("wireguard")
        wireguard()
    elif sys.argv[1:] == ["forwarder"]:
        _capabilities("forwarder")
        forwarder()
    else:
        msg = "Expected the fixed wireguard or forwarder role"
        raise RuntimeError(msg)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - runtime boundary suppresses all secret-bearing diagnostics
        print("Tether runtime refused or lost its fixed profile", file=sys.stderr)  # noqa: T201 - fixed stderr diagnostic
        raise SystemExit(1) from None
