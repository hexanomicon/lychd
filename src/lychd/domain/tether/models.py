"""Closed public Tether intent, admission snapshots, and selected service identities.

These values perform no I/O and contain secret references, never secret values.
The host supplies the current admission snapshot; a Rune cannot authorize itself.
"""

from __future__ import annotations

import base64
import binascii
import ipaddress
import re
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from lychd.config.quadlet import QuadletConfig
from lychd.config.runes.base import RuneConfig
from lychd.system.secret_names import validate_podman_secret_name

_WG_KEY_BYTES = 32
_DNS_LABEL_BYTES = 63
_SSH_KEY_PARTS = 2
_SSH_ED25519_WIRE_BYTES = 51
_UNIX_PATH_BYTES = 107

_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")
_HOST = re.compile(r"(?=.{1,253}\Z)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")


def _identifier(value: str) -> str:
    if _ID.fullmatch(value) is None:
        msg = "Tether identity must be a bounded lowercase identifier"
        raise ValueError(msg)
    return value


def _address(value: str) -> str:
    address = ipaddress.IPv4Address(value)
    if str(address) != value or address.is_unspecified or address.is_multicast or address.is_loopback:
        msg = "Tether requires a canonical non-loopback unicast IPv4 address"
        raise ValueError(msg)
    if value == "255.255.255.255":
        msg = "Tether refuses the broadcast address"
        raise ValueError(msg)
    return value


def _interface_name(value: str) -> str:
    if re.fullmatch(r"[a-z][a-z0-9]{0,14}", value) is None or value in {"lo", "eth0", "tap0"}:
        message = "Tether interface must not replace a reserved namespace device"
        raise ValueError(message)
    return value


def _interface_address(value: str) -> str:
    address = ipaddress.IPv4Interface(value)
    _address(str(address.ip))
    if str(address) != value or address.network.prefixlen == 0:
        msg = "Tether interface requires a canonical explicit IPv4 prefix"
        raise ValueError(msg)
    return value


def _key(value: str) -> str:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        msg = "Invalid WireGuard public key"
        raise ValueError(msg) from error
    if len(decoded) != _WG_KEY_BYTES or not any(decoded) or base64.b64encode(decoded).decode() != value:
        msg = "Invalid WireGuard public key"
        raise ValueError(msg)
    return value


def _secret(value: str) -> str:
    validate_podman_secret_name(value, field_name="Tether secret reference")
    if not value.startswith("lychd-tether-"):
        msg = "Tether secrets require their purpose-specific namespace"
        raise ValueError(msg)
    return value


def _hostname(value: str) -> str:
    if _HOST.fullmatch(value) is None:
        msg = "Tether requires a canonical TLS hostname"
        raise ValueError(msg)
    for label in value.split("."):
        if not label or len(label) > _DNS_LABEL_BYTES or label.startswith("-") or label.endswith("-"):
            msg = "Invalid TLS hostname label"
            raise ValueError(msg)
    return value


def _ssh_key(value: str) -> str:
    parts = value.split(" ")
    if len(parts) != _SSH_KEY_PARTS or parts[0] != "ssh-ed25519":
        msg = "Owner access accepts only one uncommented Ed25519 public key"
        raise ValueError(msg)
    try:
        raw = base64.b64decode(parts[1], validate=True)
    except (ValueError, binascii.Error) as error:
        msg = "Invalid SSH public key"
        raise ValueError(msg) from error
    if len(raw) != _SSH_ED25519_WIRE_BYTES or raw[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
        msg = "Invalid Ed25519 SSH wire key"
        raise ValueError(msg)
    if not any(raw[19:]) or base64.b64encode(raw).decode() != parts[1]:
        msg = "Invalid SSH public key"
        raise ValueError(msg)
    return value


Identifier = Annotated[str, AfterValidator(_identifier)]
Address = Annotated[str, AfterValidator(_address)]
InterfaceAddress = Annotated[str, AfterValidator(_interface_address)]
PublicKey = Annotated[str, AfterValidator(_key)]
SecretRef = Annotated[str, AfterValidator(_secret)]
Hostname = Annotated[str, AfterValidator(_hostname)]
SSHKey = Annotated[str, AfterValidator(_ssh_key)]
Port = Annotated[int, Field(strict=True, ge=1, le=65535)]
Generation = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
Epoch = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class TetherValue(BaseModel):
    """Immutable, closed public data accepted across the Tether boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TetherSelection(TetherValue):
    """A complete service selection; addresses alone never select a road."""

    remote_lich_id: Identifier
    attachment_id: Identifier
    generation: Generation
    service_id: Identifier


class ImportedService(TetherValue):
    """Exact TCP coordinates with independently verified application hostname."""

    id: Identifier
    address: Address
    port: Port
    hostname: Hostname
    application_identity_ref: Identifier
    protocol: Literal["tcp"] = "tcp"


class OfferedService(TetherValue):
    """An independently authenticated external backend, never a Core listener."""

    id: Identifier
    listen_port: Port
    backend_address: Address
    backend_port: Port


class OwnerAccess(TetherValue):
    """Optional same-owner SSH forwarding; the compiler owns its fixed target."""

    ssh_public_key: SSHKey
    ssh_host_key_ref: SecretRef
    listen_port: Port


class OfferedPeer(TetherValue):
    """Current public peer admission or retained disabled tombstone."""

    id: Identifier
    generation: Generation
    public_key: PublicKey
    address: Address
    service_ids: tuple[Identifier, ...] = Field(default=(), max_length=64)
    owner_access: OwnerAccess | None = None
    enabled: bool = Field(default=True, strict=True)
    preshared_key_ref: SecretRef | None = None

    @model_validator(mode="after")
    def unique_services(self) -> OfferedPeer:
        """Refuse ambiguous duplicate service admission."""
        if len(self.service_ids) != len(set(self.service_ids)):
            msg = "Peer service admissions must be unique"
            raise ValueError(msg)
        return self


class OfferedNetwork(TetherValue):
    """One offered routing domain; peer admission is supplied separately."""

    id: Identifier
    interface: Annotated[str, AfterValidator(_interface_name)]
    address: InterfaceAddress
    listen_address: Annotated[str, AfterValidator(lambda value: str(ipaddress.IPv4Address(value)))]
    listen_port: Port
    private_key_ref: SecretRef
    services: tuple[OfferedService, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def validate_services(self) -> OfferedNetwork:
        """Reserve each service listener and name once inside the network."""
        if len({service.id for service in self.services}) != len(self.services):
            msg = "Offered service identities must be unique"
            raise ValueError(msg)
        ports = [self.listen_port, *(service.listen_port for service in self.services)]
        if len(ports) != len(set(ports)):
            msg = "Offered service ports must be distinct"
            raise ValueError(msg)
        return self


class ImportedAttachment(TetherValue):
    """One isolated routing domain with static endpoint and service resolution."""

    id: Identifier
    remote_lich_id: Identifier
    interface: Annotated[str, AfterValidator(_interface_name)]
    address: InterfaceAddress
    private_key_ref: SecretRef
    remote_public_key: PublicKey
    preshared_key_ref: SecretRef | None = None
    endpoint_address: Address
    endpoint_port: Port
    keepalive: Annotated[int, Field(strict=True, ge=0, le=65535)] = 25
    services: tuple[ImportedService, ...] = Field(min_length=1, max_length=64)
    allowed_callers: tuple[Identifier, ...] = Field(min_length=1, max_length=64)
    dns_policy: Literal["admitted-static"] = "admitted-static"

    @model_validator(mode="after")
    def validate_services(self) -> ImportedAttachment:
        """Keep inner destinations distinct from the outer contact and local address."""
        if not self.services or not self.allowed_callers:
            msg = "Imported attachments require services and admitted callers"
            raise ValueError(msg)
        if len({service.id for service in self.services}) != len(self.services):
            msg = "Imported service identities must be unique"
            raise ValueError(msg)
        if len(self.allowed_callers) != len(set(self.allowed_callers)):
            msg = "Imported callers must be unique"
            raise ValueError(msg)
        local_interface = ipaddress.IPv4Interface(self.address)
        if ipaddress.IPv4Address(self.endpoint_address) in local_interface.network:
            message = "Outer WireGuard endpoint cannot route through the local tunnel prefix"
            raise ValueError(message)
        local = str(local_interface.ip)
        if any(service.address in {local, self.endpoint_address} for service in self.services):
            msg = "Inner service addresses cannot alias local or outer endpoint addresses"
            raise ValueError(msg)
        return self


class AttachmentAdmission(TetherValue):
    """Host-owned admission generation independent of other attachments."""

    attachment_id: Identifier
    generation: Generation
    enabled: bool = Field(default=True, strict=True)


class TetherSnapshot(TetherValue):
    """Current host-supplied public authority; restore never makes it fresh itself."""

    installation_epoch: Epoch
    offered_generation: Generation = Field(
        default=1, description="Network topology generation; peer-only mutations change only peer generations."
    )
    offered_peers: tuple[OfferedPeer, ...] = Field(default=(), max_length=128)
    attachments: tuple[AttachmentAdmission, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def unique_admissions(self) -> TetherSnapshot:
        """Include tombstones in collision checks to prevent unsafe address reuse."""
        for values in (
            [peer.id for peer in self.offered_peers],
            [peer.address for peer in self.offered_peers],
            [peer.public_key for peer in self.offered_peers],
            [entry.attachment_id for entry in self.attachments],
        ):
            if len(values) != len(set(values)):
                msg = "Tether admission identities, keys and addresses must be unique"
                raise ValueError(msg)
        return self


class TetherRune(RuneConfig):
    """Static Tether topology; the separate admission snapshot authorizes activation."""

    path_fragment: ClassVar[Path] = Path("tether")
    profile: Literal["rootless-wireguard-stream-v1"] = "rootless-wireguard-stream-v1"
    quadlet: QuadletConfig
    offered: OfferedNetwork | None = None
    attachments: tuple[ImportedAttachment, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def unique_networks(self) -> TetherRune:
        """Keep credential custody separate across independently managed networks."""
        names = [attachment.id for attachment in self.attachments]
        keys = [attachment.private_key_ref for attachment in self.attachments]
        if self.offered is not None:
            names.append(self.offered.id)
            keys.append(self.offered.private_key_ref)
        if len(names) != len(set(names)) or len(keys) != len(set(keys)):
            msg = "Tether networks require unique identities and private-key references"
            raise ValueError(msg)
        return self


class TetherRoute(TetherValue):
    """Public Core catalog row with an exact immutable socket selection."""

    selection: TetherSelection
    installation_epoch: Epoch
    policy_digest: Digest
    socket_path: str
    hostname: Hostname
    application_identity_ref: Identifier
    address: Address
    port: Port
    allowed_callers: tuple[Identifier, ...] = Field(min_length=1, max_length=64)
    unit_name: str

    @model_validator(mode="after")
    def exact_socket(self) -> TetherRoute:
        """Reject path traversal, overlong UNIX addresses and arbitrary socket targets."""
        if re.fullmatch(r"/run/lychd-tether/[0-9a-f]{16}/[0-9a-f]{32}\.sock", self.socket_path) is None:
            msg = "Tether route socket must be a compiler-owned generation address"
            raise ValueError(msg)
        if len(self.socket_path.encode()) > _UNIX_PATH_BYTES or not self.allowed_callers:
            msg = "Invalid Tether route socket or caller admission"
            raise ValueError(msg)
        if re.fullmatch(r"lychd-tether-[a-z0-9-]+\.service", self.unit_name) is None:
            msg = "Invalid Tether route unit"
            raise ValueError(msg)
        return self
