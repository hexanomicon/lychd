"""Closed native requests and public, correlated Tether evidence."""

from __future__ import annotations

import hashlib
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.tether.models import CompiledTetherPlan, TetherPeerIntent


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


class PrepareImageRequest(OperationRequest):
    """A cold image transition, distinct from historical initial preparation."""

    kind: Literal["prepare-image"] = "prepare-image"
    expected_preparation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


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


class EnrollmentStartupAdmission(Record):
    """A native enrollment's exact request may first activate in this kernel boot."""

    boot_id: UUID
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class OperationReceipt(Record):
    request_digest: str
    request: PrepareRequest | PrepareImageRequest | EnrollRequest | RevokeRequest
    stages: tuple[str, ...] = ()
    complete: bool = False
    binding_generation: str | None = None
    closure: ClosureObservation | None = None
    startup_admission: EnrollmentStartupAdmission | None = None

    def require_enrollment_startup(
        self, peer: TetherPeerIntent, *, envelope_digest: str, binding_generation: str, boot_id: UUID
    ) -> None:
        """Require completed enrollment or its exact native first-start admission."""
        request = self.request
        if (
            not isinstance(request, EnrollRequest)
            or request.installation_id != peer.installation_id
            or request.operation_id != peer.operation_id
            or request.peer != peer
            or request.expected_generation != peer.generation - 1
            or request.intent_digest != digest(peer)
            or request.envelope_digest != envelope_digest
            or self.request_digest != digest(request)
            or self.binding_generation != binding_generation
        ):
            msg = "Tether startup lacks exact correlated native enrollment authority"
            raise TetherError(msg)
        fenced = {"activation-fenced", "interrupted-activation-fenced", "handler-closure-observed"}
        if self.closure is not None or fenced.intersection(self.stages):
            msg = "Interrupted or fenced Tether enrollment cannot authorize startup"
            raise TetherError(msg)
        if self.complete:
            if not self.stages or self.stages[-1] != "forwarder-active":
                msg = "Tether enrollment completion lacks its successful terminal stage"
                raise TetherError(msg)
            return
        admission = self.startup_admission
        if (
            admission is None
            or admission.boot_id != boot_id
            or admission.request_digest != self.request_digest
            or "wireguard-start-requested" not in self.stages
        ):
            msg = "Incomplete Tether enrollment lacks its exact current-boot startup admission"
            raise TetherError(msg)


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


class PreparationSelection(Record):
    """The sole current-preparation commit identity, including its exact parent."""

    version: Literal[1] = 1
    installation_id: UUID
    operation_id: UUID
    bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_preparation_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class InitialPreparationBundle(Record):
    """Typed view of the original immutable pair; no new creation authority."""

    plan: CompiledTetherPlan
    preparation: PreparationReceipt


class ImagePreparationBundle(Record):
    """An immutable image-only transition, inert until selected."""

    parent_selection: PreparationSelection
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan: CompiledTetherPlan
    preparation: PreparationReceipt


class SelectedPreparation(Record):
    """Resolved native selection and its exact plan/flat preparation receipt."""

    selection: PreparationSelection
    plan: CompiledTetherPlan
    preparation: PreparationReceipt


class PreparedInspection(Record):
    """Public selection metadata, available before binding or peer enrollment."""

    installation_id: UUID
    envelope_digest: str
    preparation_digest: str
    peer_generation: int = Field(ge=0)
    preparation: PreparationReceipt


def require_image_only_change(old: CompiledTetherPlan, new: CompiledTetherPlan) -> None:
    """Refuse any migration other than one changed immutable transport image."""
    if old.envelope.image == new.envelope.image or old.envelope.model_dump(
        exclude={"image"}
    ) != new.envelope.model_dump(exclude={"image"}):
        msg = "Tether replacement permits only a changed immutable image reference"
        raise TetherError(msg)
