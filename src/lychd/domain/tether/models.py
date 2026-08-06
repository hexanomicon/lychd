"""Immutable, secret-reference-only intent for a future Tether provider."""

from __future__ import annotations

import base64
import binascii
import re
from enum import StrEnum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyInterface,
    IPvAnyNetwork,
    field_validator,
    model_validator,
)

from lychd.system.secret_names import is_valid_podman_secret_name

__all__ = ["TetherIntent", "TetherInterfaceIntent", "TetherPeerIntent", "TetherPeerState"]

_INTERFACE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,14}$")
_DNS_NAME_PATTERN = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.?$"
)
_MAX_IDENTIFIER_LENGTH = 128
_MAX_PEERS = 1024
_MAX_PORT = 65_535
_MIN_IPV6_CLOSING_INDEX = 2
_WIREGUARD_KEY_BYTES = 32

type IpInterface = IPv4Interface | IPv6Interface
type IpNetwork = IPv4Network | IPv6Network


class TetherPeerState(StrEnum):
    """Persisted public intent for one peer credential."""

    ENABLED = "enabled"
    REVOKED = "revoked"


class TetherInterfaceIntent(BaseModel):
    """Public interface configuration plus one private-key secret reference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(default="lychd0", min_length=1, max_length=15)
    addresses: tuple[IPvAnyInterface, ...] = Field(min_length=1, max_length=16)
    listen_port: int = Field(ge=1, le=65535)
    private_key_secret_name: str = Field(min_length=1, max_length=253)
    peer_limit: int = Field(default=64, ge=1, le=_MAX_PEERS)

    @field_validator("name")
    @classmethod
    def _validate_interface_name(cls, value: str) -> str:
        if not _INTERFACE_NAME_PATTERN.fullmatch(value):
            msg = "Tether interface name must be a conservative Linux interface identifier."
            raise ValueError(msg)
        return value

    @field_validator("private_key_secret_name")
    @classmethod
    def _validate_private_key_reference(cls, value: str) -> str:
        if not is_valid_podman_secret_name(value):
            msg = "Tether private key must be an option-safe Podman secret reference."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_unique_addresses(self) -> Self:
        if len(set(self.addresses)) != len(self.addresses):
            msg = "Tether interface addresses must be unique."
            raise ValueError(msg)
        return self


class TetherPeerIntent(BaseModel):
    """Versioned public peer/routing intent without private key material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    peer_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    revision: int = Field(ge=1)
    public_key: str = Field(min_length=44, max_length=44)
    preshared_key_secret_name: str | None = Field(default=None, min_length=1, max_length=253)
    allowed_routes: tuple[IPvAnyNetwork, ...] = Field(min_length=1, max_length=256)
    endpoint: str | None = Field(default=None, min_length=1, max_length=320)
    persistent_keepalive_seconds: int | None = Field(default=None, ge=1, le=65535)
    state: TetherPeerState = TetherPeerState.ENABLED
    revoked_at: AwareDatetime | None = None

    @field_validator("peer_id")
    @classmethod
    def _validate_peer_id(cls, value: str) -> str:
        if value != value.strip():
            msg = "Tether peer identity must be a canonical non-whitespace value."
            raise ValueError(msg)
        return value

    @field_validator("public_key")
    @classmethod
    def _validate_public_key(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            msg = "WireGuard public key must be canonical base64."
            raise ValueError(msg) from exc
        canonical = base64.b64encode(decoded).decode("ascii")
        if len(decoded) != _WIREGUARD_KEY_BYTES or canonical != value:
            msg = "WireGuard public key must be canonical base64 encoding of exactly 32 bytes."
            raise ValueError(msg)
        return value

    @field_validator("preshared_key_secret_name")
    @classmethod
    def _validate_preshared_key_reference(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_podman_secret_name(value):
            msg = "Tether preshared key must be an option-safe Podman secret reference."
            raise ValueError(msg)
        return value

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        _parse_endpoint(value)
        return value

    @model_validator(mode="after")
    def _validate_routes_and_revocation(self) -> Self:
        if len(set(self.allowed_routes)) != len(self.allowed_routes):
            msg = f"Tether peer {self.peer_id!r} allowed routes must be unique."
            raise ValueError(msg)
        if self.state is TetherPeerState.REVOKED and self.revoked_at is None:
            msg = "A revoked Tether peer must record a revocation time."
            raise ValueError(msg)
        if self.state is TetherPeerState.ENABLED and self.revoked_at is not None:
            msg = "An enabled Tether peer cannot retain a revocation time."
            raise ValueError(msg)
        return self


class TetherIntent(BaseModel):
    """One immutable public Tether generation suitable only for later compilation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: int = Field(ge=1)
    interface: TetherInterfaceIntent
    peers: tuple[TetherPeerIntent, ...] = Field(default=(), max_length=_MAX_PEERS)

    @model_validator(mode="after")
    def _validate_peer_set(self) -> Self:
        if len(self.peers) > self.interface.peer_limit:
            msg = "Tether peer count exceeds the interface peer limit."
            raise ValueError(msg)
        peer_ids = [peer.peer_id for peer in self.peers]
        if len(set(peer_ids)) != len(peer_ids):
            msg = "Tether peer identities must be unique."
            raise ValueError(msg)
        public_keys = [peer.public_key for peer in self.peers]
        if len(set(public_keys)) != len(public_keys):
            msg = "Tether peer public keys must be unique."
            raise ValueError(msg)
        active_routes: list[tuple[str, IpNetwork]] = []
        for peer in self.peers:
            if peer.state is TetherPeerState.REVOKED:
                continue
            for route in peer.allowed_routes:
                for owner, existing in active_routes:
                    if route.version == existing.version and route.overlaps(existing):
                        msg = (
                            f"Tether route {route} for peer {peer.peer_id!r} overlaps "
                            f"route {existing} owned by peer {owner!r}."
                        )
                        raise ValueError(msg)
                active_routes.append((peer.peer_id, route))
        return self


def _parse_endpoint(value: str) -> tuple[str, int]:
    host: str
    port_text: str
    if value.startswith("["):
        closing = value.find("]")
        if closing < _MIN_IPV6_CLOSING_INDEX or closing + 1 >= len(value) or value[closing + 1] != ":":
            msg = "IPv6 Tether endpoints must use [address]:port form."
            raise ValueError(msg)
        host = value[1:closing]
        port_text = value[closing + 2 :]
        try:
            IPv6Address(host)
        except ValueError as exc:
            msg = "Tether endpoint contains an invalid IPv6 address."
            raise ValueError(msg) from exc
    else:
        if value.count(":") != 1:
            msg = "Tether endpoint must use host:port form."
            raise ValueError(msg)
        host, port_text = value.rsplit(":", maxsplit=1)
        try:
            IPv4Address(host)
        except ValueError:
            if not _DNS_NAME_PATTERN.fullmatch(host):
                msg = "Tether endpoint host must be an IPv4 address, bracketed IPv6 address, or DNS name."
                raise ValueError(msg) from None
    if not port_text.isascii() or not port_text.isdecimal():
        msg = "Tether endpoint port must be decimal."
        raise ValueError(msg)
    port = int(port_text)
    if not 1 <= port <= _MAX_PORT:
        msg = "Tether endpoint port must be between 1 and 65535."
        raise ValueError(msg)
    return host, port
