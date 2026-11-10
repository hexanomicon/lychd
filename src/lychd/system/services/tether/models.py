"""Closed native requests and public, correlated Tether evidence."""

from __future__ import annotations

import hashlib
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.tether.models import TetherPeerIntent


class TetherError(RuntimeError):
    """Refused or incomplete Tether operation; evidence remains available."""


class Record(BaseModel):
    """Frozen evidence with no caller extension fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def digest(value: BaseModel) -> str:
    """Hash the canonical typed representation, including operation identity."""
    return hashlib.sha256(value.model_dump_json().encode()).hexdigest()


class OperationRequest(Record):
    installation_id: UUID
    operation_id: UUID
    expected_generation: int = Field(ge=0, strict=True)
    envelope_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PrepareRequest(OperationRequest):
    kind: Literal["prepare"] = "prepare"


class EnrollRequest(OperationRequest):
    kind: Literal["enroll"] = "enroll"
    peer: TetherPeerIntent


class InspectRequest(OperationRequest):
    kind: Literal["inspect"] = "inspect"


class RevokeRequest(OperationRequest):
    kind: Literal["revoke"] = "revoke"


class SecretIdentity(Record):
    purpose: Literal["wireguard-server", "ssh-host"]
    name: str
    podman_id: str = Field(pattern=r"^[a-zA-Z0-9]{12,128}$")
    public_key: str
    fingerprint: str = Field(pattern=r"^SHA256:[A-Za-z0-9+/]{43}$")


class PreparationReceipt(Record):
    installation_id: UUID
    operation_id: UUID
    envelope_digest: str
    secrets: tuple[SecretIdentity, SecretIdentity]


class ClosureLatch(Record):
    installation_id: UUID
    operation_id: UUID
    generation: int = Field(ge=1)
    intent_digest: str
    envelope_digest: str
    binding_generation: str


class ClosureObservation(Record):
    closed: bool
    services: tuple[tuple[str, str], ...]
    pod_absent: bool
    containers_absent: bool
    jobs_absent: bool
    process_trees_empty: bool
    guard_state: str = "unknown"
    handler_state: str = "unknown"


class OperationReceipt(Record):
    request_digest: str
    request: PrepareRequest | EnrollRequest | RevokeRequest
    stages: tuple[str, ...] = ()
    complete: bool = False
    binding_generation: str | None = None
    closure: ClosureObservation | None = None


class RevocationRecord(Record):
    latch: ClosureLatch
    latch_digest: str


class RuntimeIdentity(Record):
    """Observed physical identity after cold, Scribe-owned transport creation."""

    installation_id: UUID
    generation: int = Field(ge=1)
    binding_generation: str
    boot_id: UUID
    pod_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    wireguard_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    forwarder_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    netns_inode: int = Field(gt=0)
    service_cgroups: tuple[str, str, str]
    container_cgroups: tuple[str, str]
    host_uid_ranges: tuple[tuple[int, int], ...]


class Inspection(Record):
    installation_id: UUID
    envelope_digest: str
    peer: TetherPeerIntent | None
    closure_latch: ClosureLatch | None
    preparation: PreparationReceipt | None
    preparation_attested: bool
    observation: ClosureObservation
    loaded_runtime: RuntimeIdentity | None
    runtime_attested: bool
    binding_generation: str | None
    desired_envelope_digest: str | None
    configuration_drift: bool


class IncarnationIdentity(Record):
    """Pod poststart receipt, before either role can activate."""

    installation_id: UUID
    generation: int
    envelope_digest: str
    binding_generation: str
    boot_id: UUID
    pod_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    infra_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    invocation_id: UUID
    netns_inode: int = Field(gt=0)
    infra_cgroup: str
    host_uid_ranges: tuple[tuple[int, int], ...]


class RoleIdentity(Record):
    """Immutable physical identity for one fixed role of one Pod incarnation."""

    pod_id: str
    role: Literal["wireguard", "forwarder"]
    container_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_digest: str
    netns_inode: int
    cgroup: str


class ActivationAttempt(Record):
    """Manager-attested Pod start intent, durable before Podman can create it."""

    installation_id: UUID
    generation: int
    envelope_digest: str
    binding_generation: str
    boot_id: UUID
    invocation_id: UUID
    service_cgroup: str
