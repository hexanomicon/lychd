"""Closed public Tether intent and deterministic, effect-free physical planning.

These values convey intent, never preparation or startup authority. Private keys
are consumed exclusively by the runtime secret boundary.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import struct
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.system.secret_names import validate_podman_secret_name

_PRIVATE_NETWORKS = tuple(IPv4Network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
_HOST_PREFIX = 32
_KEY_BYTES = 32
_SSH_KEY_PARTS = 2
_MAX_PORT = 65535
_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_INTERFACE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,14}$")
_IMAGE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[0-9a-f]{64}$")


class TetherValue(BaseModel):
    """An immutable public document with no extension fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _private_host(value: IPv4Interface) -> IPv4Interface:
    if (
        value.network.prefixlen != _HOST_PREFIX
        or not any(value.ip in network for network in _PRIVATE_NETWORKS)
        or (value.ip.is_loopback or value.ip.is_link_local or value.ip.is_unspecified or value.ip.is_multicast)
    ):
        msg = "Tether addresses must be private, non-loopback IPv4 /32 hosts"
        raise ValueError(msg)
    return value


def _wireguard_key(value: str) -> str:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        msg = "WireGuard public key must be canonical base64 for 32 bytes"
        raise ValueError(msg) from exc
    if len(decoded) != _KEY_BYTES or not any(decoded) or base64.b64encode(decoded).decode() != value:
        msg = "WireGuard public key must be canonical base64 for 32 nonzero bytes"
        raise ValueError(msg)
    return value


class TetherSecretReference(TetherValue):
    """A purpose-bound Podman reference, never a key or factory."""

    purpose: Literal["wireguard-server", "ssh-host"]
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_podman_secret_name(value, field_name="Tether secret reference")


class TetherEnvelope(TetherValue):
    """TetherEnvelope@1: the static, complete single-operator boundary."""

    version: Literal[1] = 1
    profile: Literal["single-operator-forward@1"] = "single-operator-forward@1"
    installation_id: UUID
    service_identity: Literal["lychd-tether"] = "lychd-tether"
    interface: str
    server_address: IPv4Interface
    udp_bind_address: IPv4Address
    udp_port: int = Field(ge=1024, le=65535, strict=True)
    advertised_endpoint: str
    peer_limit: Literal[1] = 1
    image: str
    wireguard_secret: TetherSecretReference
    ssh_host_secret: TetherSecretReference
    ssh_port: int = Field(default=2222, ge=1024, le=65535, strict=True)
    altar_port: int = Field(ge=1, le=65535, strict=True)

    @field_validator("interface")
    @classmethod
    def validate_interface(cls, value: str) -> str:
        if _INTERFACE.fullmatch(value) is None or value in {"lo", "tap0", "eth0"}:
            msg = "Tether interface must be one distinct Linux interface name of at most 15 characters"
            raise ValueError(msg)
        return value

    @field_validator("server_address")
    @classmethod
    def validate_server_address(cls, value: IPv4Interface) -> IPv4Interface:
        return _private_host(value)

    @field_validator("udp_bind_address")
    @classmethod
    def validate_bind_address(cls, value: IPv4Address) -> IPv4Address:
        if value.is_multicast or value.is_link_local or value == IPv4Address("255.255.255.255"):
            msg = "Tether UDP bind must be one unicast or unspecified IPv4 address"
            raise ValueError(msg)
        return value

    @field_validator("advertised_endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        address_text, separator, port_text = value.partition(":")
        try:
            address = IPv4Address(address_text)
            port = int(port_text)
        except ValueError as exc:
            msg = "Tether endpoint must be a literal IPv4 address and port"
            raise ValueError(msg) from exc
        if (
            not separator
            or str(address) != address_text
            or str(port) != port_text
            or not 1 <= port <= _MAX_PORT
            or (address.is_unspecified or address.is_multicast or address.is_loopback or address.is_link_local)
        ):
            msg = "Tether endpoint must be an unambiguous reachable literal IPv4 address and port"
            raise ValueError(msg)
        return value

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: str) -> str:
        if _IMAGE.fullmatch(value) is None:
            msg = "Tether requires an immutable image reference with a SHA-256 digest"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> TetherEnvelope:
        if self.wireguard_secret.purpose != "wireguard-server" or self.ssh_host_secret.purpose != "ssh-host":
            msg = "Tether secret references must retain their exact server purposes"
            raise ValueError(msg)
        if self.wireguard_secret.name == self.ssh_host_secret.name:
            msg = "Tether WireGuard and SSH secret references must be disjoint"
            raise ValueError(msg)
        if self.server_address.ip in {self.udp_bind_address, IPv4Address(self.advertised_endpoint.partition(":")[0])}:
            msg = "Tether tunnel and host UDP bind addresses must be distinct"
            raise ValueError(msg)
        if self.altar_port == self.ssh_port:
            msg = "Tether SSH and Altar ports must be distinct"
            raise ValueError(msg)
        return self


class TetherPeerIntent(TetherValue):
    """TetherPeerIntent@1: one public generation, separate from shared Runes."""

    version: Literal[1] = 1
    installation_id: UUID
    generation: int = Field(ge=1, strict=True)
    operation_id: UUID
    peer_id: str
    wireguard_public_key: str
    address: IPv4Interface
    ssh_authorized_public_key: str
    persistent_keepalive: int = Field(default=25, ge=0, le=120, strict=True)
    state: Literal["enabled", "revoked"] = "enabled"

    @field_validator("peer_id")
    @classmethod
    def validate_peer_id(cls, value: str) -> str:
        if _TOKEN.fullmatch(value) is None:
            msg = "Tether peer identity must be one safe lower-case token"
            raise ValueError(msg)
        return value

    @field_validator("wireguard_public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        return _wireguard_key(value)

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: IPv4Interface) -> IPv4Interface:
        return _private_host(value)

    @field_validator("ssh_authorized_public_key")
    @classmethod
    def validate_ssh_public_key(cls, value: str) -> str:
        parts = value.split(" ")
        try:
            blob = base64.b64decode(parts[1], validate=True) if len(parts) == _SSH_KEY_PARTS else b""
        except (ValueError, binascii.Error) as exc:
            msg = "Tether SSH key must be a bare canonical ssh-ed25519 public key"
            raise ValueError(msg) from exc
        prefix = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32)
        if (
            parts[0] != "ssh-ed25519"
            or len(blob) != len(prefix) + 32
            or not blob.startswith(prefix)
            or (base64.b64encode(blob).decode() != parts[-1] or not any(blob[len(prefix) :]))
        ):
            msg = "Tether SSH key must be a bare canonical ssh-ed25519 public key"
            raise ValueError(msg)
        return value


class CompiledTetherPlan(TetherValue):
    """A compiler-owned physical identity and custody plan, not host authority."""

    envelope: TetherEnvelope
    envelope_digest: str
    pod_name: Literal["lychd-tether"] = "lychd-tether"
    pod_source: Literal["lychd-tether.pod"] = "lychd-tether.pod"
    pod_unit: Literal["lychd-tether-pod.service"] = "lychd-tether-pod.service"
    wireguard_container: Literal["lychd-tether-wg"] = "lychd-tether-wg"
    wireguard_unit: Literal["lychd-tether-wg.service"] = "lychd-tether-wg.service"
    forwarder_container: Literal["lychd-tether-ssh"] = "lychd-tether-ssh"
    forwarder_unit: Literal["lychd-tether-ssh.service"] = "lychd-tether-ssh.service"
    guard_unit: Literal["lychd-tether-guard.path"] = "lychd-tether-guard.path"
    closure_unit: Literal["lychd-tether-close.service"] = "lychd-tether-close.service"
    intent_relative_path: Literal["tether/peer.json"] = "tether/peer.json"
    wireguard_projection_directory: Literal["tether/wireguard"] = "tether/wireguard"
    forwarder_projection_directory: Literal["tether/forwarder"] = "tether/forwarder"
    closure_relative_path: Literal["tether/closed.json"] = "tether/closed.json"
    preparation_relative_path: Literal["tether/preparation.json"] = "tether/preparation.json"

    @model_validator(mode="after")
    def validate_digest(self) -> CompiledTetherPlan:
        if self.envelope_digest != _digest(self.envelope):
            msg = "Tether plan digest must match its exact validated envelope"
            raise ValueError(msg)
        return self

    @property
    def transport_units(self) -> tuple[str, str, str]:
        return (self.pod_unit, self.wireguard_unit, self.forwarder_unit)

    @property
    def plain_unit_names(self) -> tuple[str, str]:
        return (self.guard_unit, self.closure_unit)

    @property
    def secret_requirements(self) -> tuple[TetherSecretReference, TetherSecretReference]:
        return (self.envelope.wireguard_secret, self.envelope.ssh_host_secret)

    @property
    def startup_order(self) -> tuple[str, str, str, str]:
        return (self.guard_unit, *self.transport_units)

    @property
    def pasta_options(self) -> tuple[str, ...]:
        return (
            "--ipv4-only",
            "--no-map-gw",
            "--map-host-loopback",
            "none",
            "--map-guest-addr",
            "none",
            "--dns",
            "none",
            "--dns-forward",
            "169.254.1.1",
            "--dns-host",
            "127.0.0.1",
            "--search",
            "none",
            "--no-dhcp-dns",
            "--no-dhcp-search",
            "-t",
            "none",
            "-T",
            f"127.0.0.1/{self.envelope.altar_port}",
            "-U",
            "none",
        )


def _digest(value: TetherValue) -> str:
    return hashlib.sha256(value.model_dump_json().encode("utf-8")).hexdigest()


def compile_tether_plan(envelope: TetherEnvelope) -> CompiledTetherPlan:
    """Revalidate and freeze the one physical profile from public static intent."""
    checked = TetherEnvelope.model_validate(envelope.model_dump())
    return CompiledTetherPlan(envelope=checked, envelope_digest=_digest(checked))


def validate_peer(plan: CompiledTetherPlan, peer: TetherPeerIntent) -> None:
    """Refuse foreign, revoked or overlapping peer intent before any projection."""
    if peer.installation_id != plan.envelope.installation_id or peer.state != "enabled":
        msg = "Tether peer must be enabled and belong to the exact installation"
        raise ValueError(msg)
    if peer.address.ip in {
        plan.envelope.server_address.ip,
        plan.envelope.udp_bind_address,
        IPv4Address(plan.envelope.advertised_endpoint.partition(":")[0]),
    }:
        msg = "Tether peer and server addresses must be disjoint"
        raise ValueError(msg)


class WireGuardPublicProjection(TetherValue):
    """Validated inputs for the secret-consuming WireGuard runtime boundary."""

    interface: str
    server_address: IPv4Interface
    listen_port: int
    ssh_port: int
    altar_port: int
    peer_public_key: str
    peer_address: IPv4Interface
    persistent_keepalive: int


def render_wireguard_public(plan: CompiledTetherPlan, peer: TetherPeerIntent) -> WireGuardPublicProjection:
    """Return no private key, hook, path or operator-selected command."""
    validate_peer(plan, peer)
    return WireGuardPublicProjection(
        interface=plan.envelope.interface,
        server_address=plan.envelope.server_address,
        listen_port=plan.envelope.udp_port,
        ssh_port=plan.envelope.ssh_port,
        altar_port=plan.envelope.altar_port,
        peer_public_key=peer.wireguard_public_key,
        peer_address=peer.address,
        persistent_keepalive=peer.persistent_keepalive,
    )


def render_address_commands(plan: CompiledTetherPlan, peer: TetherPeerIntent) -> tuple[tuple[str, ...], ...]:
    """Return fixed iproute arguments; the runtime installs policy before link-up."""
    validate_peer(plan, peer)
    envelope = plan.envelope
    return (
        ("link", "add", "dev", envelope.interface, "type", "wireguard"),
        ("address", "add", str(envelope.server_address), "dev", envelope.interface),
        ("route", "add", str(peer.address), "dev", envelope.interface),
        ("link", "set", "dev", envelope.interface, "up"),
    )


def render_nftables(plan: CompiledTetherPlan, peer: TetherPeerIntent) -> str:
    """Close all IPv4/IPv6 flows except exact tunnel, SSH and loopback Altar."""
    validate_peer(plan, peer)
    e = plan.envelope
    server, remote = str(e.server_address.ip), str(peer.address.ip)
    return f"""table inet lychd_tether {{
 chain input {{
  type filter hook input priority -150; policy drop;
  udp dport {{ 53, 853 }} drop
  tcp dport {{ 53, 853 }} drop
  meta nfproto ipv4 udp dport {e.udp_port} accept
  iifname "{e.interface}" ip saddr {remote} ip daddr {server} tcp dport {e.ssh_port} ct state new,established accept
  iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport {e.altar_port} ct state new,established accept
  iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport {e.altar_port} ct state established accept
 }}
 chain output {{
  type filter hook output priority -150; policy drop;
  udp dport {{ 53, 853 }} drop
  tcp dport {{ 53, 853 }} drop
  meta nfproto ipv4 udp sport {e.udp_port} accept
  oifname "{e.interface}" ip saddr {server} ip daddr {remote} tcp sport {e.ssh_port} ct state established accept
  oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport {e.altar_port} ct state new,established accept
  oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport {e.altar_port} ct state established accept
 }}
 chain forward {{
  type filter hook forward priority -150; policy drop;
 }}
}}
"""


def render_sshd_config(plan: CompiledTetherPlan) -> str:
    """Fix forwarding to one literal destination and prohibit session channels."""
    e = plan.envelope
    return f"""AddressFamily inet
ListenAddress {e.server_address.ip}
Port {e.ssh_port}
HostKey /run/secrets/tether-ssh-host
PidFile /run/tether/sshd.pid
AuthorizedKeysFile /etc/lychd-tether/authorized_keys
AllowUsers tether
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
UsePAM no
StrictModes yes
AllowTcpForwarding local
PermitOpen 127.0.0.1:{e.altar_port}
PermitListen none
AllowStreamLocalForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
PermitTTY no
PermitUserRC no
PermitUserEnvironment no
GatewayPorts no
MaxSessions 0
UseDNS no
"""


def render_authorized_key(plan: CompiledTetherPlan, peer: TetherPeerIntent) -> str:
    """Bind a validated bare key to the sole admitted direct-TCP destination."""
    validate_peer(plan, peer)
    return (
        f'restrict,port-forwarding,permitopen="127.0.0.1:{plan.envelope.altar_port}" {peer.ssh_authorized_public_key}\n'
    )
