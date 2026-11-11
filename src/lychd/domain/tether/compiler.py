"""Pure complete Tether projection: role JSON, isolated Quadlets and Core routes.

Compilation receives current admission explicitly. It neither loads private state
nor generates keys, creates files, starts processes, or grants application roles.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lychd.domain.tether.models import (
    ImportedAttachment,
    OfferedNetwork,
    TetherRoute,
    TetherRune,
    TetherSelection,
    TetherSnapshot,
)
from lychd.system.constants import CONTAINER_LYCHD_PORT, CONTAINER_POSTGRES_PORT
from lychd.system.schemas import MountData, QuadletBase, QuadletContainer, QuadletPod, TetherPodPolicy

CONTAINER_RUNTIME = Path("/run/lychd-tether")
CONTAINER_CONFIG = Path("/etc/lychd-tether")
_UNIX_PATH_BYTES = 107
_MAX_PORT = 65535
_RUNTIME_COMMAND = "python3 -m lychd_tether_runtime /etc/lychd-tether/config.json"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Public per-role projection materialized by the host, never by the Domain."""

    name: str
    network_id: str
    role: str
    payload: dict[str, object]
    fences: dict[str, object]

    def json_bytes(self) -> bytes:
        """Encode canonical public configuration without machine-specific identity."""
        return _json(self.payload)


@dataclass(frozen=True, slots=True)
class TetherNetwork:
    """Stable per-network reconciliation subset, independent of global Scribe CAS."""

    id: str
    generation: int
    policy_digest: str
    pod_unit: str
    unit_names: tuple[str, ...]
    runtime_directory: Path


@dataclass(frozen=True, slots=True)
class TetherDeployment:
    """The complete Tether contribution to one host-owned bind generation."""

    manifests: tuple[QuadletBase, ...]
    required_secrets: tuple[str, ...]
    runtime_configs: tuple[RuntimeConfig, ...]
    routes: tuple[TetherRoute, ...]
    networks: tuple[TetherNetwork, ...]
    consumer_mount: MountData | None


def _json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _key_path(reference: str) -> str:
    return "/run/secrets/psk-" + hashlib.sha256(reference.encode()).hexdigest()[:16]


def _secret(reference: str, target: str) -> str:
    return f"{reference},target={target},mode=0400"


def _require_root(path: Path) -> None:
    text = str(path)
    if not path.is_absolute() or ".." in path.parts or any(char in text for char in "\n\r\\%$:'\""):
        msg = "Tether projection roots must be safe absolute literal paths"
        raise ValueError(msg)


def _fences(snapshot: TetherSnapshot, network_id: str, generation: int, *, offered: bool) -> dict[str, object]:
    return {
        "schema": "lychd.tether.fences",
        "version": 1,
        "installation_epoch": snapshot.installation_epoch,
        "network_id": network_id,
        "generation": generation,
        "enabled": True,
        "peers": [
            {"id": peer.id, "generation": peer.generation, "enabled": peer.enabled}
            for peer in sorted(snapshot.offered_peers, key=lambda peer: peer.id)
        ]
        if offered
        else [],
    }


class _NetworkBuilder:
    """Accumulate one isolated network without sharing mutable cross-network policy."""

    def __init__(
        self,
        *,
        rune: TetherRune,
        snapshot: TetherSnapshot,
        network_id: str,
        generation: int,
        policy: object,
        runtime_root: Path,
        config_root: Path,
        pod_policy: TetherPodPolicy,
    ) -> None:
        self.network_id = network_id
        self.generation = generation
        self.digest = _digest({"epoch": snapshot.installation_epoch, "image": rune.quadlet.image, "policy": policy})
        self.directory_name = hashlib.sha256(network_id.encode()).hexdigest()[:16]
        self.stem = "lychd-tether-" + self.directory_name
        self.runtime_directory = runtime_root / self.directory_name
        self.config_root = config_root
        self.image = rune.quadlet.image
        self.base: dict[str, object] = {
            "schema": "lychd.tether.runtime",
            "version": 1,
            "network_id": network_id,
            "installation_epoch": snapshot.installation_epoch,
            "generation": generation,
            "policy_digest": self.digest,
            "fence_path": str(CONTAINER_CONFIG / "fences.json"),
        }
        self.fences = _fences(snapshot, network_id, generation, offered=pod_policy.kind == "offered")
        self.manifests: list[QuadletBase] = [
            QuadletPod(
                description=f"Tether isolated network {network_id}",
                pod_name=self.stem,
                tether_policy=pod_policy,
                wanted_by=[],
            )
        ]
        self.configs: list[RuntimeConfig] = []
        self.secrets: set[str] = set()
        self.units: list[str] = []

    def role(
        self,
        role: Literal["wireguard", "imported-relay", "offered-relay", "owner-ssh"],
        payload: dict[str, object],
        *,
        suffix: str,
        secrets: tuple[tuple[str, str], ...] = (),
        sockets: bool = False,
    ) -> str:
        name = f"{self.stem}-{suffix}"
        base = dict(self.base)
        if role == "owner-ssh":
            # Peer-only changes never perturb another owner's live SSH adapter.
            base["policy_digest"] = _digest(
                {
                    "epoch": base["installation_epoch"],
                    "network": self.network_id,
                    "generation": self.generation,
                    "image": self.image,
                    "role": role,
                    "payload": payload,
                }
            )
        config = RuntimeConfig(name, self.network_id, role, {**base, "role": role, **payload}, dict(self.fences))
        self.configs.append(config)
        mounts = [
            MountData(
                host_path=self.config_root / name, container_path=CONTAINER_CONFIG, mirror=False, options=["ro", "z"]
            )
        ]
        if sockets:
            mounts.append(
                MountData(
                    host_path=self.runtime_directory,
                    container_path=CONTAINER_RUNTIME / self.directory_name,
                    mirror=False,
                    options=["rw", "z"],
                )
            )
        specs = [_secret(reference, target) for reference, target in secrets]
        self.secrets.update(reference for reference, _target in secrets)
        wg_unit = f"{self.stem}-wg.service"
        dependencies = [] if role == "wireguard" else [wg_unit]
        self.manifests.append(
            QuadletContainer(
                description=f"Tether {self.network_id} {role}",
                image=self.image,
                container_name=name,
                pod=f"{self.stem}.pod",
                tether_role=role,
                user="0" if role in {"wireguard", "owner-ssh"} else "%U",
                read_only=True,
                run_init=False,
                # Only native activation may journal and retain a replacement incarnation.
                restart_policy="no",
                secret_mount_tmpfs=bool(specs),
                volumes=mounts,
                secrets=specs,
                requires=dependencies,
                after=["network-online.target", *dependencies],
                binds_to=dependencies,
                exec=_RUNTIME_COMMAND,
                wanted_by=[],
            )
        )
        unit = f"{name}.service"
        self.units.append(unit)
        return unit

    def network(self) -> TetherNetwork:
        return TetherNetwork(
            self.network_id,
            self.generation,
            self.digest,
            f"{self.stem}-pod.service",
            tuple(self.units),
            self.runtime_directory,
        )


def _validate_offered(
    *,
    offered: OfferedNetwork,
    snapshot: TetherSnapshot,
    core_web_port: int,
    forbidden_backend_addresses: tuple[str, ...] | None,
) -> None:
    """Reject routing and listener ambiguity before projecting any role."""
    peers = tuple(sorted(snapshot.offered_peers, key=lambda peer: peer.id))
    own_interface = ipaddress.IPv4Interface(offered.address)
    own_address = str(own_interface.ip)
    known_services = {service.id for service in offered.services}
    occupied_ports = {offered.listen_port, *(service.listen_port for service in offered.services)}
    for peer in peers:
        if peer.address == own_address or ipaddress.IPv4Address(peer.address) not in own_interface.network:
            msg = "Offered peer address must be distinct and within its offered network"
            raise ValueError(msg)
        if not set(peer.service_ids).issubset(known_services):
            msg = "Offered peer refers to an unknown service"
            raise ValueError(msg)
        if peer.owner_access is not None:
            if peer.owner_access.listen_port in occupied_ports:
                msg = "Owner SSH listeners require distinct private ports"
                raise ValueError(msg)
            occupied_ports.add(peer.owner_access.listen_port)
    _validate_backends(offered, core_web_port, forbidden_backend_addresses)


def _validate_backends(
    offered: OfferedNetwork,
    core_web_port: int,
    forbidden_backend_addresses: tuple[str, ...] | None,
) -> None:
    """Require fresh host exclusion evidence without making it persistent route identity."""
    own_interface = ipaddress.IPv4Interface(offered.address)
    if offered.services and forbidden_backend_addresses is None:
        msg = "Offered external backends require current host-address admission context"
        raise ValueError(msg)
    forbidden = {str(ipaddress.IPv4Address(address)) for address in (forbidden_backend_addresses or ())}
    for service in offered.services:
        backend = ipaddress.IPv4Address(service.backend_address)
        if service.backend_address in forbidden or backend.is_link_local:
            msg = "Offered external backends cannot target host or link-local addresses"
            raise ValueError(msg)
        if ipaddress.IPv4Address(service.backend_address) in own_interface.network:
            msg = "An offered backend cannot target its offered network"
            raise ValueError(msg)
        if service.backend_port in {core_web_port, CONTAINER_LYCHD_PORT, CONTAINER_POSTGRES_PORT}:
            msg = "Owner web access requires the SSH profile, not a generic backend"
            raise ValueError(msg)


def _offered(
    *,
    rune: TetherRune,
    snapshot: TetherSnapshot,
    offered: OfferedNetwork,
    runtime_root: Path,
    config_root: Path,
    core_web_port: int,
    forbidden_backend_addresses: tuple[str, ...] | None,
) -> _NetworkBuilder:
    _validate_offered(
        offered=offered,
        snapshot=snapshot,
        core_web_port=core_web_port,
        forbidden_backend_addresses=forbidden_backend_addresses,
    )
    peers = tuple(sorted(snapshot.offered_peers, key=lambda peer: peer.id))
    active = tuple(peer for peer in peers if peer.enabled)
    own_address = str(ipaddress.IPv4Interface(offered.address).ip)
    # Declared owner capacity survives revocation; only active peers receive admission.
    owner_port = core_web_port if any(peer.owner_access is not None for peer in peers) else None
    builder = _NetworkBuilder(
        rune=rune,
        snapshot=snapshot,
        network_id=offered.id,
        generation=snapshot.offered_generation,
        policy={
            "definition": offered.model_dump(mode="json"),
            "peers": [peer.model_dump(mode="json") for peer in peers],
            "generation": snapshot.offered_generation,
            "owner_port": owner_port,
        },
        runtime_root=runtime_root,
        config_root=config_root,
        pod_policy=TetherPodPolicy(
            kind="offered",
            udp_address=offered.listen_address,
            udp_port=offered.listen_port,
            owner_loopback_port=owner_port,
        ),
    )
    wg_peers: list[dict[str, object]] = []
    ingress: list[dict[str, object]] = []
    key_mounts = [(offered.private_key_ref, "/run/secrets/wg-private")]
    services = {service.id: service for service in offered.services}
    for peer in active:
        psk = _key_path(peer.preshared_key_ref) if peer.preshared_key_ref else None
        if peer.preshared_key_ref and psk:
            key_mounts.append((peer.preshared_key_ref, psk))
        wg_peers.append(
            {
                "id": peer.id,
                "generation": peer.generation,
                "public_key": peer.public_key,
                "allowed_ips": [f"{peer.address}/32"],
                "endpoint_address": None,
                "endpoint_port": None,
                "keepalive": 0,
                "preshared_key_path": psk,
            }
        )
        ingress.extend({"peer_address": peer.address, "port": services[name].listen_port} for name in peer.service_ids)
        if peer.owner_access is not None:
            ingress.append({"peer_address": peer.address, "port": peer.owner_access.listen_port})
    builder.role(
        "wireguard",
        {
            "interface": offered.interface,
            "address": offered.address,
            "listen_port": offered.listen_port,
            "private_key_path": "/run/secrets/wg-private",
            "peers": wg_peers,
            "ingress": ingress,
            "egress": [
                {"address": service.backend_address, "port": service.backend_port, "protocol": "tcp"}
                for service in offered.services
            ],
            "owner_loopback_port": owner_port,
        },
        suffix="wg",
        secrets=tuple(key_mounts),
    )
    if offered.services:
        builder.role(
            "offered-relay",
            {
                "services": [
                    {
                        "service_id": service.id,
                        "listen_address": own_address,
                        "listen_port": service.listen_port,
                        "backend_address": service.backend_address,
                        "backend_port": service.backend_port,
                    }
                    for service in offered.services
                ],
                "peers": [
                    {
                        "id": peer.id,
                        "generation": peer.generation,
                        "address": peer.address,
                        "service_ids": list(peer.service_ids),
                    }
                    for peer in active
                ],
            },
            suffix="ingress",
        )
    for peer in active:
        owner = peer.owner_access
        if owner is None:
            continue
        suffix = "ssh-" + hashlib.sha256(peer.id.encode()).hexdigest()[:12]
        builder.role(
            "owner-ssh",
            {
                "peer_id": peer.id,
                "peer_generation": peer.generation,
                "peer_address": peer.address,
                "listen_address": own_address,
                "listen_port": owner.listen_port,
                "ssh_public_key": owner.ssh_public_key,
                "ssh_host_key_path": "/run/secrets/ssh-host",
                "target_address": "127.0.0.1",
                "target_port": core_web_port,
            },
            suffix=suffix,
            secrets=((owner.ssh_host_key_ref, "/run/secrets/ssh-host"),),
        )
    return builder


def _imported(
    *,
    rune: TetherRune,
    snapshot: TetherSnapshot,
    attachment: ImportedAttachment,
    generation: int,
    runtime_root: Path,
    config_root: Path,
    consumer_uid: int,
) -> tuple[_NetworkBuilder, tuple[TetherRoute, ...]]:
    builder = _NetworkBuilder(
        rune=rune,
        snapshot=snapshot,
        network_id=attachment.id,
        generation=generation,
        policy={
            "definition": attachment.model_dump(mode="json"),
            "generation": generation,
            "consumer_uid": consumer_uid,
        },
        runtime_root=runtime_root,
        config_root=config_root,
        pod_policy=TetherPodPolicy(kind="imported"),
    )
    psk = _key_path(attachment.preshared_key_ref) if attachment.preshared_key_ref else None
    key_mounts = [(attachment.private_key_ref, "/run/secrets/wg-private")]
    if attachment.preshared_key_ref and psk:
        key_mounts.append((attachment.preshared_key_ref, psk))
    builder.role(
        "wireguard",
        {
            "interface": attachment.interface,
            "address": attachment.address,
            "listen_port": 0,
            "private_key_path": "/run/secrets/wg-private",
            "peers": [
                {
                    "id": attachment.remote_lich_id,
                    "generation": generation,
                    "public_key": attachment.remote_public_key,
                    "allowed_ips": [
                        f"{address}/32" for address in sorted({service.address for service in attachment.services})
                    ],
                    "endpoint_address": attachment.endpoint_address,
                    "endpoint_port": attachment.endpoint_port,
                    "keepalive": attachment.keepalive,
                    "preshared_key_path": psk,
                }
            ],
            "ingress": [],
            "owner_loopback_port": None,
            "egress": [
                {"address": attachment.endpoint_address, "port": attachment.endpoint_port, "protocol": "udp"},
                *(
                    {"address": service.address, "port": service.port, "protocol": "tcp"}
                    for service in attachment.services
                ),
            ],
        },
        suffix="wg",
        secrets=tuple(key_mounts),
    )
    relay_unit = f"{builder.stem}-outbound.service"
    rows: list[TetherRoute] = []
    for service in sorted(attachment.services, key=lambda service: service.id):
        socket_name = (
            _digest(
                {
                    "epoch": snapshot.installation_epoch,
                    "network": attachment.id,
                    "generation": generation,
                    "service": service.id,
                    "policy": builder.digest,
                }
            )[:32]
            + ".sock"
        )
        socket_path = str(CONTAINER_RUNTIME / builder.directory_name / socket_name)
        if len(str(builder.runtime_directory / socket_name).encode()) > _UNIX_PATH_BYTES:
            msg = "Host runtime root exceeds the UNIX socket path limit"
            raise ValueError(msg)
        rows.append(
            TetherRoute(
                selection=TetherSelection(
                    remote_lich_id=attachment.remote_lich_id,
                    attachment_id=attachment.id,
                    generation=generation,
                    service_id=service.id,
                ),
                installation_epoch=snapshot.installation_epoch,
                policy_digest=builder.digest,
                socket_path=socket_path,
                hostname=service.hostname,
                application_identity_ref=service.application_identity_ref,
                address=service.address,
                port=service.port,
                allowed_callers=attachment.allowed_callers,
                unit_name=relay_unit,
            )
        )
    builder.role(
        "imported-relay",
        {
            "caller_uid": consumer_uid,
            "remote_lich_id": attachment.remote_lich_id,
            "allowed_callers": list(attachment.allowed_callers),
            "routes": [
                {
                    "service_id": row.selection.service_id,
                    "generation": generation,
                    "socket_path": row.socket_path,
                    "address": row.address,
                    "port": row.port,
                    "application_identity_ref": row.application_identity_ref,
                }
                for row in rows
            ],
        },
        suffix="outbound",
        sockets=True,
    )
    return builder, tuple(rows)


def _validate_secret_custody(rune: TetherRune, snapshot: TetherSnapshot) -> None:
    """Forbid one secret reference crossing a network, peer or credential purpose."""
    references: list[str] = []
    for attachment in rune.attachments:
        references.append(attachment.private_key_ref)
        if attachment.preshared_key_ref:
            references.append(attachment.preshared_key_ref)
    if rune.offered is not None:
        references.append(rune.offered.private_key_ref)
    for peer in snapshot.offered_peers:
        if peer.preshared_key_ref:
            references.append(peer.preshared_key_ref)
        if peer.owner_access:
            references.append(peer.owner_access.ssh_host_key_ref)
    if len(references) != len(set(references)):
        msg = "Tether secret references cannot cross network, peer or credential-purpose boundaries"
        raise ValueError(msg)


def compile_tether(
    *,
    rune: TetherRune,
    snapshot: TetherSnapshot,
    runtime_root: Path,
    config_root: Path,
    core_web_port: int,
    consumer_uid: int,
    forbidden_backend_addresses: tuple[str, ...] | None = None,
) -> TetherDeployment:
    """Compile current admitted topology without discovering or changing host state."""
    rune = TetherRune.model_validate(rune.model_dump(mode="json"))
    snapshot = TetherSnapshot.model_validate(snapshot.model_dump(mode="json"))
    _validate_secret_custody(rune, snapshot)
    _require_root(runtime_root)
    _require_root(config_root)
    if isinstance(core_web_port, bool) or not 1 <= core_web_port <= _MAX_PORT:
        msg = "Invalid Core owner loopback port"
        raise ValueError(msg)
    if isinstance(consumer_uid, bool) or not 0 <= consumer_uid <= 2**32 - 2:
        msg = "Invalid admitted consumer UID"
        raise ValueError(msg)
    declared = {attachment.id: attachment for attachment in rune.attachments}
    if any(admission.attachment_id not in declared for admission in snapshot.attachments):
        msg = "Snapshot refers to an undeclared attachment"
        raise ValueError(msg)
    if rune.offered is None and snapshot.offered_peers:
        msg = "Peer admission requires an offered network"
        raise ValueError(msg)
    builders: list[_NetworkBuilder] = []
    rows: list[TetherRoute] = []
    if rune.offered is not None:
        builders.append(
            _offered(
                rune=rune,
                snapshot=snapshot,
                offered=rune.offered,
                runtime_root=runtime_root,
                config_root=config_root,
                core_web_port=core_web_port,
                forbidden_backend_addresses=forbidden_backend_addresses,
            )
        )
    for admission in sorted(snapshot.attachments, key=lambda admission: admission.attachment_id):
        if not admission.enabled:
            continue
        builder, routes = _imported(
            rune=rune,
            snapshot=snapshot,
            attachment=declared[admission.attachment_id],
            generation=admission.generation,
            runtime_root=runtime_root,
            config_root=config_root,
            consumer_uid=consumer_uid,
        )
        builders.append(builder)
        rows.extend(routes)
    return TetherDeployment(
        manifests=tuple(manifest for builder in builders for manifest in builder.manifests),
        required_secrets=tuple(sorted({secret for builder in builders for secret in builder.secrets})),
        runtime_configs=tuple(config for builder in builders for config in builder.configs),
        routes=tuple(rows),
        networks=tuple(builder.network() for builder in builders),
        consumer_mount=MountData(
            host_path=runtime_root, container_path=CONTAINER_RUNTIME, mirror=False, options=["ro", "z"]
        ),
    )
