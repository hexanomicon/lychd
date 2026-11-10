"""Closed native operations, with journaled cold activation and durable closure."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Literal, overload

from lychd.domain.tether.models import (
    TetherPeerIntent,
    render_authorized_key,
    render_sshd_config,
    render_wireguard_public,
    validate_peer,
)
from lychd.system.services.scribe.models import PersistentBindingIdentity
from lychd.system.services.tether.custody import PreparationStore
from lychd.system.services.tether.models import (
    ClosureLatch,
    ClosureObservation,
    EnrollmentStartupAdmission,
    EnrollRequest,
    Inspection,
    InspectRequest,
    OperationReceipt,
    OperationRequest,
    PreparationReceipt,
    PrepareImageRequest,
    PrepareRequest,
    RevocationRecord,
    RevokeRequest,
    SelectedPreparation,
    TetherError,
    digest,
    require_image_only_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from lychd.domain.tether.models import CompiledTetherPlan
    from lychd.system.operator.process import ProcessRunner
    from lychd.system.services.tether.closure import TetherStopAdapter
    from lychd.system.services.tether.custody import TetherCustody
    from lychd.system.services.tether.secrets import TetherSecrets


class TetherOperations:
    """Own only Tether intent, receipts and the compiler's exact transport units."""

    def __init__(
        self,
        plan: CompiledTetherPlan,
        custody: TetherCustody,
        secrets: TetherSecrets,
        stop: TetherStopAdapter,
        runner: ProcessRunner,
        *,
        systemctl_bin: str,
        binding_probe: Callable[[], PersistentBindingIdentity],
        lock_factory: Callable[[], AbstractContextManager[object]],
        desired_probe: Callable[[], str] | None = None,
        preparation_cold_probe: Callable[[CompiledTetherPlan], ClosureObservation] | None = None,
    ) -> None:
        """Bind the fixed compiler plan to trusted effect and ownership ports."""
        self.plan, self.custody, self.secrets, self.stop_adapter, self.runner = plan, custody, secrets, stop, runner
        self.systemctl, self.binding_probe, self.lock_factory = systemctl_bin, binding_probe, lock_factory
        self.desired_probe = desired_probe
        self.preparation_cold_probe = preparation_cold_probe

    def _current(self) -> TetherPeerIntent | None:
        raw = self.custody.read("public", "peer.json")
        return TetherPeerIntent.model_validate_json(raw) if raw is not None else None

    def _latch(self) -> ClosureLatch | None:
        raw = self.custody.read("private", "closed.json")
        return ClosureLatch.model_validate_json(raw) if raw is not None else None

    def _validate(self, request: OperationRequest) -> None:
        if (
            request.installation_id != self.plan.envelope.installation_id
            or request.envelope_digest != self.plan.envelope_digest
        ):
            msg = "Tether request installation or envelope changed"
            raise TetherError(msg)

    def _begin(self, request: PrepareRequest | PrepareImageRequest | EnrollRequest | RevokeRequest) -> OperationReceipt:  # noqa: C901 - closed finite request kinds have distinct admission checks
        self._validate(request)
        name = f"{request.operation_id}.json"
        previous = self.custody.read("operations", name)
        if previous is not None:
            receipt = OperationReceipt.model_validate_json(previous)
            if receipt.request_digest != digest(request) or receipt.request != request:
                msg = "Operation identity was already used with different intent"
                raise TetherError(msg)
            return receipt
        peer = self._current()
        generation = peer.generation if peer else 0
        if request.expected_generation != generation:
            msg = "Tether peer generation changed; inspect before retrying"
            raise TetherError(msg)
        if isinstance(request, PrepareRequest):
            if request.intent_digest != self.plan.envelope_digest or generation:
                msg = "Preparation requires the exact static envelope and no enrolled peer"
                raise TetherError(msg)
        elif isinstance(request, PrepareImageRequest):
            if request.intent_digest != self.plan.envelope_digest:
                msg = "Image preparation requires the exact target envelope intent"
                raise TetherError(msg)
        elif isinstance(request, EnrollRequest):
            validate_peer(self.plan, request.peer)
            if (
                request.intent_digest != digest(request.peer)
                or request.peer.operation_id != request.operation_id
                or request.peer.generation != generation + 1
            ):
                msg = "Enrollment requires the exact next public generation and operation"
                raise TetherError(msg)
        elif peer is None or request.intent_digest != digest(peer):
            msg = "Revocation requires the exact current peer intent digest"
            raise TetherError(msg)
        receipt = OperationReceipt(request_digest=digest(request), request=request)
        self.custody.write("operations", name, receipt)
        return receipt

    def _record(self, receipt: OperationReceipt, stage: str, **updates: object) -> OperationReceipt:
        stages = receipt.stages if stage in receipt.stages else (*receipt.stages, stage)
        result = receipt.model_copy(update={"stages": stages, **updates})
        # Revalidate model_copy updates before durable publication.
        result = OperationReceipt.model_validate(result.model_dump())
        self.custody.write("operations", f"{receipt.request.operation_id}.json", result)
        return result

    def _control(self, action: str, *units: str) -> None:
        result = self.runner.run((self.systemctl, "--user", action, *units), timeout_s=45)
        if result.returncode:
            msg = "Tether user-manager transition failed; preserve journal and fence"
            raise TetherError(msg)

    def _active(self, unit: str) -> bool:
        result = self.runner.run(
            (self.systemctl, "--user", "show", unit, "--property=ActiveState", "--value"), timeout_s=5
        )
        return result.returncode == 0 and result.stdout.strip() == "active"

    def _require_active(self, unit: str) -> None:
        if not self._active(unit):
            msg = "Tether transport did not reach its required active readiness state"
            raise TetherError(msg)

    def prepare(self, request: PrepareRequest, *, dry_run: bool = False) -> PreparationReceipt | PrepareRequest:
        """Provision only the two referenced server secrets, before ordinary bind."""
        self._validate(request)
        if dry_run:
            if request.expected_generation != 0 or request.intent_digest != self.plan.envelope_digest:
                msg = "Preparation plan requires generation zero and the static envelope digest"
                raise TetherError(msg)
            self.secrets.preview_prepare()
            # No lock, mkdir, key factory or Podman mutation in a preview.
            return request
        with self.lock_factory():
            self.custody.initialize()
            receipt = self._begin(request)
            if receipt.complete:
                return self.secrets.attest()
            prepared = self.secrets.prepare(request.operation_id)
            self._record(receipt, "prepared", complete=True)
            return prepared

    def _require_retained_revocation(
        self, peer: TetherPeerIntent, *, selected_plan: CompiledTetherPlan | None = None
    ) -> ClosureLatch:
        raw = self.custody.read("operations", f"{peer.operation_id}.json")
        if raw is None:
            msg = "Revoked peer has no retained enrollment authority"
            raise TetherError(msg)
        enrollment = OperationReceipt.model_validate_json(raw)
        request = enrollment.request
        if (
            not isinstance(request, EnrollRequest)
            or request.peer != peer
            or request.installation_id != peer.installation_id
            or request.operation_id != peer.operation_id
            or request.expected_generation != peer.generation - 1
            or request.intent_digest != digest(peer)
            or enrollment.request_digest != digest(request)
            or enrollment.binding_identity is None
        ):
            msg = "Revoked peer differs from its exact retained enrollment"
            raise TetherError(msg)
        current_plan = selected_plan or self.plan
        old_plan = current_plan
        if request.envelope_digest != current_plan.envelope_digest:
            store = PreparationStore(self.custody)
            store.require_lineage(request.envelope_digest, current_plan.envelope_digest)
            old_plan = store.historical_plan(request.envelope_digest)
        validate_peer(old_plan, peer)
        generation = self.custody.read("generations", f"{peer.generation}.json")
        raw_revocation = self.custody.read("revocations", f"{peer.generation}.json")
        raw_latch = self.custody.read("private", "closed.json")
        if (
            generation is None
            or TetherPeerIntent.model_validate_json(generation) != peer
            or raw_revocation is None
            or raw_latch is None
        ):
            msg = "Image replacement requires exact peer generation, retained revocation and active latch"
            raise TetherError(msg)
        record = RevocationRecord.model_validate_json(raw_revocation)
        latch = ClosureLatch.model_validate_json(raw_latch)
        if (
            record.latch != latch
            or record.latch_digest != digest(latch)
            or latch.installation_id != peer.installation_id
            or latch.generation != peer.generation
            or latch.intent_digest != digest(peer)
            or latch.envelope_digest != request.envelope_digest
            or latch.binding_identity != enrollment.binding_identity
        ):
            msg = "Retained revocation or active latch differs from its historical envelope and binding"
            raise TetherError(msg)
        return latch

    def _image_transition_parent(self, request: PrepareImageRequest) -> SelectedPreparation:
        self._validate(request)
        parent = self.secrets.attest_selected()
        if digest(parent.selection) != request.expected_preparation_digest:
            msg = "Expected preparation selection is stale"
            raise TetherError(msg)
        require_image_only_change(parent.plan, self.plan)
        peer = self._current()
        if (
            request.expected_generation != (peer.generation if peer else 0)
            or request.intent_digest != self.plan.envelope_digest
        ):
            msg = "Image preparation peer generation or target intent changed"
            raise TetherError(msg)
        if peer is not None:
            self._require_retained_revocation(peer, selected_plan=parent.plan)
        elif (
            self._latch() is not None
            or self.custody.names("generations")
            or any(
                self.custody.read("private", name) is not None
                for name in ("activation.json", "incarnation.json", "runtime.json")
            )
        ):
            msg = "A no-peer installation cannot adopt unexplained latch or generation/runtime history"
            raise TetherError(msg)
        if self.preparation_cold_probe is None or not self.preparation_cold_probe(parent.plan).closed:
            msg = "Image preparation requires exact owned whole-road cold proof"
            raise TetherError(msg)
        return parent

    def _image_operation(self, request: PrepareImageRequest) -> OperationReceipt | None:
        raw = self.custody.read("operations", f"{request.operation_id}.json")
        receipt = OperationReceipt.model_validate_json(raw) if raw is not None else None
        if receipt is not None and (receipt.request != request or receipt.request_digest != digest(request)):
            msg = "Operation identity was already used with different intent"
            raise TetherError(msg)
        return receipt

    def _committed_image_result(
        self, request: PrepareImageRequest, selected: SelectedPreparation, receipt: OperationReceipt | None
    ) -> PreparationReceipt | None:
        if selected.selection.operation_id == request.operation_id:
            if (
                receipt is None
                or selected.selection.parent_preparation_digest != request.expected_preparation_digest
                or selected.plan != self.plan
            ):
                msg = "Selected transition does not match the exact pending image request"
                raise TetherError(msg)
            return self.secrets.attest()
        if receipt is not None and receipt.complete:
            msg = "Superseded image preparation cannot select itself again"
            raise TetherError(msg)
        return None

    def prepare_image(
        self, request: PrepareImageRequest, *, dry_run: bool = False
    ) -> PreparationReceipt | PrepareImageRequest:
        """Select only a cold image replacement, reusing exact original server identities."""
        self._validate(request)
        if dry_run:
            selected = PreparationStore(self.custody).selected()
            if self._committed_image_result(request, selected, self._image_operation(request)) is None:
                self._image_transition_parent(request)
            return request
        with self.lock_factory():
            self.custody.attest()
            store = PreparationStore(self.custody)
            selected = store.selected()
            existing = self._image_operation(request)
            completed = self._committed_image_result(request, selected, existing)
            if completed is not None:
                if existing is None:
                    msg = "Committed image selection lost its operation journal"
                    raise TetherError(msg)
                self._record(existing, "image-selected", complete=True)
                return completed
            parent = self._image_transition_parent(request)
            receipt = self._begin(request)
            receipt = self._record(receipt, "image-cold-proven")
            if self.secrets.attest_selected() != parent:
                msg = "Selected preparation or server identities changed before image commit"
                raise TetherError(msg)
            prepared = PreparationReceipt(
                installation_id=request.installation_id,
                operation_id=request.operation_id,
                envelope_digest=self.plan.envelope_digest,
                secrets=parent.preparation.secrets,
            )
            store.commit(request, parent, prepared, self.plan)
            self._record(receipt, "image-selected", complete=True)
            return prepared

    def startup_preflight(self, expected_binding: PersistentBindingIdentity | None = None) -> None:
        """Revalidate live intent, secrets, binding and guard before UDP activation."""
        self.custody.attest()
        binding = self.binding_probe()
        if expected_binding is not None and expected_binding != binding:
            msg = "Tether Scribe binding identity changed during the operation"
            raise TetherError(msg)
        peer = self._current()
        if peer is None:
            msg = "Tether has no enrolled public peer"
            raise TetherError(msg)
        validate_peer(self.plan, peer)
        generation = self.custody.read("generations", f"{peer.generation}.json")
        if generation is None or TetherPeerIntent.model_validate_json(generation) != peer:
            msg = "Tether current peer lacks immutable generation evidence"
            raise TetherError(msg)
        if self.custody.read("revocations", f"{peer.generation}.json") is not None:
            msg = "Tether generation has retained revocation evidence and cannot restart"
            raise TetherError(msg)
        raw_receipt = self.custody.read("operations", f"{peer.operation_id}.json")
        if raw_receipt is None:
            msg = "Tether current peer lacks its correlated native enrollment receipt"
            raise TetherError(msg)
        OperationReceipt.model_validate_json(raw_receipt).require_enrollment_startup(
            peer,
            envelope_digest=self.plan.envelope_digest,
            binding_identity=binding,
            boot_id=self.stop_adapter.boot_id(),
        )
        self.secrets.attest()
        expected = {
            ("wireguard", "public.json"): render_wireguard_public(self.plan, peer).model_dump_json().encode(),
            ("forwarder", "sshd_config"): render_sshd_config(self.plan).encode(),
            ("forwarder", "authorized_keys"): render_authorized_key(self.plan, peer).encode(),
        }
        if any(self.custody.read(role, name) != content for (role, name), content in expected.items()):
            msg = "Tether runtime projection differs from the retained current generation"
            raise TetherError(msg)
        if self._latch() is not None or not self._active(self.plan.guard_unit):
            msg = "Tether closure latch exists or continuous guard is inactive"
            raise TetherError(msg)

    def role_preflight(self, role: str) -> None:
        """Check the fixed startup role without taking a parent's lifecycle lock."""
        self.startup_preflight()
        peer = self._current()
        if peer is None:
            msg = "Tether startup has no current generation"
            raise TetherError(msg)
        incarnation = self.stop_adapter.incarnation()
        if role == "pod":
            self.stop_adapter.require_prior_activation_attested(binding_identity=self.binding_probe())
            if incarnation is not None and not self.stop_adapter.incarnation_closed(incarnation):
                msg = "Same-boot Tether restart requires exact old-incarnation cold proof"
                raise TetherError(msg)
            return
        if (
            role not in {"wireguard", "forwarder"}
            or incarnation is None
            or incarnation.generation != peer.generation
            or incarnation.boot_id != self.stop_adapter.boot_id()
            or incarnation.binding_identity != self.binding_probe()
        ):
            msg = "Tether role startup lacks current Pod poststart attestation"
            raise TetherError(msg)
        if self.custody.read("generations", f"role-{incarnation.pod_id}-{role}.json") is not None:
            msg = "A role cannot restart inside an already used Pod incarnation"
            raise TetherError(msg)
        if (
            role == "forwarder"
            and self.custody.read("generations", f"role-{incarnation.pod_id}-wireguard.json") is None
        ):
            msg = "Forwarder requires ordered WireGuard poststart attestation"
            raise TetherError(msg)

    def begin_pod(self) -> None:
        """Journal a fixed manager-attested attempt after read-only Pod preflight."""
        self.role_preflight("pod")
        peer = self._current()
        if peer is None:
            msg = "Pod startup has no current public generation"
            raise TetherError(msg)
        self.stop_adapter.begin_pod(peer.generation, self.binding_probe())

    def attest_started(self, role: str) -> None:
        """Publish fixed poststart identity receipts before the next role starts."""
        self.startup_preflight()
        peer = self._current()
        if peer is None:
            msg = "Tether poststart has no current public generation"
            raise TetherError(msg)
        binding = self.binding_probe()
        if role == "pod":
            self.stop_adapter.attest_pod(peer.generation, binding)
        elif role in {"wireguard", "forwarder"}:
            incarnation = self.stop_adapter.incarnation()
            if (
                incarnation is None
                or incarnation.generation != peer.generation
                or incarnation.binding_identity != binding
                or incarnation.boot_id != self.stop_adapter.boot_id()
            ):
                msg = "Tether role poststart belongs to another incarnation"
                raise TetherError(msg)
            self.stop_adapter.attest_role(role)
            if role == "forwarder":
                self.stop_adapter.capture_runtime(peer.generation, binding)
        else:
            msg = "Unknown fixed Tether poststart role"
            raise TetherError(msg)
        # A concurrent fence can only turn this readback into refusal. No
        # attestation path starts anything, clears a latch or compensates.
        self.startup_preflight(binding)

    def _retained_binding(self, peer: TetherPeerIntent) -> PersistentBindingIdentity:
        raw = self.custody.read("operations", f"{peer.operation_id}.json")
        if raw is not None:
            value = OperationReceipt.model_validate_json(raw)
            if value.binding_identity is not None:
                return value.binding_identity
        incarnation = self.stop_adapter.incarnation()
        if incarnation is not None and incarnation.generation == peer.generation:
            return incarnation.binding_identity
        msg = "Retained Tether binding identity is absent; closure authority is unconfirmed"
        raise TetherError(msg)

    def _fence(
        self, request: EnrollRequest | RevokeRequest, peer: TetherPeerIntent, binding: PersistentBindingIdentity
    ) -> ClosureLatch:
        existing = self._latch()
        if existing is not None:
            if (
                existing.generation != peer.generation
                or existing.intent_digest != digest(peer)
                or existing.envelope_digest != self.plan.envelope_digest
                or existing.binding_identity != binding
            ):
                msg = "Existing Tether closure latch does not match the current generation"
                raise TetherError(msg)
            latch = existing
        else:
            raw = self.custody.read("revocations", f"{peer.generation}.json")
            latch = (
                RevocationRecord.model_validate_json(raw).latch
                if raw is not None
                else ClosureLatch(
                    installation_id=request.installation_id,
                    operation_id=request.operation_id,
                    generation=peer.generation,
                    intent_digest=digest(peer),
                    envelope_digest=self.plan.envelope_digest,
                    binding_identity=binding,
                )
            )
            if (
                latch.installation_id != request.installation_id
                or latch.generation != peer.generation
                or latch.intent_digest != digest(peer)
                or latch.envelope_digest != self.plan.envelope_digest
                or latch.binding_identity != binding
            ):
                msg = "Retained Tether revocation does not match exact current ownership"
                raise TetherError(msg)
            # This durable fixed-path publication MUST precede every stop effect.
            self.custody.write("private", "closed.json", latch, immutable=True)
        record = RevocationRecord(latch=latch, latch_digest=digest(latch))
        self.custody.write("revocations", f"{peer.generation}.json", record, immutable=True)
        return latch

    @overload
    def enroll(self, request: EnrollRequest, *, dry_run: Literal[False] = False) -> OperationReceipt: ...

    @overload
    def enroll(self, request: EnrollRequest, *, dry_run: Literal[True]) -> EnrollRequest: ...

    @overload
    def enroll(self, request: EnrollRequest, *, dry_run: bool) -> OperationReceipt | EnrollRequest: ...

    def enroll(self, request: EnrollRequest, *, dry_run: bool = False) -> OperationReceipt | EnrollRequest:  # noqa: C901, PLR0912, PLR0915 - ordered durability/effect transaction
        """Publish the next generation only after exact cold proof and reset guard."""
        self._validate(request)
        if dry_run:
            self.secrets.attest()
            self._preview_generation(request)
            self.binding_probe()
            if not self.stop_adapter.observe().closed:
                msg = "Enrollment requires a proven cold Tether road"
                raise TetherError(msg)
            return request
        with self.lock_factory():
            receipt = self._begin(request)
            if receipt.complete:
                return receipt
            binding = self.binding_probe()
            if receipt.binding_identity is not None and receipt.binding_identity != binding:
                msg = "Pending Tether operation belongs to another binding identity"
                raise TetherError(msg)
            self.secrets.attest()
            if (
                "wireguard-start-requested" in receipt.stages
                or self.custody.read("revocations", f"{request.peer.generation}.json") is not None
            ):
                # A retry cannot restart an uncertain or previously fenced
                # generation. Reconcile only toward closure, then use a fresh
                # next-generation enrollment operation.
                self._fence(request, request.peer, binding)
                observation = self.stop_adapter.stop()
                return self._record(receipt, "interrupted-activation-fenced", closure=observation, complete=False)
            receipt = self._record(receipt, "prepared", binding_identity=binding)
            if not self.stop_adapter.observe().closed:
                msg = "Enrollment requires full cold proof, including Pod/process/job absence"
                raise TetherError(msg)
            receipt = self._record(receipt, "cold-proven")
            # Stops/reset happen while the previous generation remains fenced.
            self._control("stop", self.plan.guard_unit)
            receipt = self._record(receipt, "watcher-stopped")
            old_latch_bytes = self.custody.read("private", "closed.json")
            if old_latch_bytes is not None:
                old_latch = ClosureLatch.model_validate_json(old_latch_bytes)
                old_peer_raw = self.custody.read("generations", f"{old_latch.generation}.json")
                old_peer = TetherPeerIntent.model_validate_json(old_peer_raw) if old_peer_raw is not None else None
                if old_peer is not None and old_peer.generation == old_latch.generation:
                    if old_latch.envelope_digest == self.plan.envelope_digest and old_latch.binding_identity == binding:
                        self._fence(request, old_peer, binding)
                    elif self._require_retained_revocation(old_peer) != old_latch:
                        msg = "Historical closure latch changed before cold image reenrollment"
                        raise TetherError(msg)
                else:
                    msg = "Old closure evidence does not match the enrolled generation"
                    raise TetherError(msg)
            self._control("stop", self.plan.closure_unit)
            self._control("reset-failed", self.plan.closure_unit, self.plan.guard_unit)
            receipt = self._record(receipt, "handler-reset")
            self.custody.write("generations", f"{request.peer.generation}.json", request.peer, immutable=True)
            self.custody.publish(
                "wireguard", "public.json", render_wireguard_public(self.plan, request.peer).model_dump_json().encode()
            )
            self.custody.publish("forwarder", "sshd_config", render_sshd_config(self.plan).encode())
            self.custody.publish(
                "forwarder", "authorized_keys", render_authorized_key(self.plan, request.peer).encode()
            )
            self.custody.write("public", "peer.json", request.peer)
            receipt = self._record(receipt, "generation-published")
            if old_latch_bytes is not None:
                self.custody.clear_latch(old_latch_bytes)
            receipt = self._record(receipt, "active-latch-cleared")
            receipt = self._record(
                receipt,
                "wireguard-start-requested",
                startup_admission=EnrollmentStartupAdmission(
                    boot_id=self.stop_adapter.boot_id(),
                    request_digest=digest(request),
                ),
            )
            try:
                self._control("start", self.plan.guard_unit)
                self.startup_preflight(binding)
                receipt = self._record(receipt, "guard-attested")
                # systemd's WG Notify readiness gates the forwarder; no one-shot
                # exit is used as evidence of a configured transport.
                self._control("start", self.plan.pod_unit, self.plan.wireguard_unit)
                self._require_active(self.plan.wireguard_unit)
                receipt = self._record(receipt, "wireguard-ready")
                self.startup_preflight(binding)
                self._control("start", self.plan.forwarder_unit)
                self._require_active(self.plan.forwarder_unit)
                self.stop_adapter.capture_runtime(request.peer.generation, binding)
                return self._record(receipt, "forwarder-active", complete=True)
            except BaseException:
                self._fence(request, request.peer, binding)
                observation = self.stop_adapter.stop()
                self._record(receipt, "activation-fenced", closure=observation)
                raise

    def _preview_generation(self, request: EnrollRequest) -> None:
        peer = self._current()
        if request.expected_generation != (peer.generation if peer else 0):
            msg = "Tether peer generation changed"
            raise TetherError(msg)
        validate_peer(self.plan, request.peer)
        if (
            request.peer.generation != request.expected_generation + 1
            or request.peer.operation_id != request.operation_id
            or request.intent_digest != digest(request.peer)
        ):
            msg = "Enrollment must name the exact next public generation"
            raise TetherError(msg)

    @overload
    def revoke(self, request: RevokeRequest, *, dry_run: Literal[False] = False) -> OperationReceipt: ...

    @overload
    def revoke(self, request: RevokeRequest, *, dry_run: Literal[True]) -> RevokeRequest: ...

    @overload
    def revoke(self, request: RevokeRequest, *, dry_run: bool) -> OperationReceipt | RevokeRequest: ...

    def revoke(self, request: RevokeRequest, *, dry_run: bool = False) -> OperationReceipt | RevokeRequest:
        """Attest retained ownership before activating a durable fence and stopping."""
        self._validate(request)
        if dry_run:
            peer = self._current()
            if peer is None or request.expected_generation != peer.generation or request.intent_digest != digest(peer):
                msg = "Revocation preview must match the current public generation"
                raise TetherError(msg)
            self.binding_probe()
            return request
        with self.lock_factory():
            receipt = self._begin(request)
            if receipt.complete:
                return receipt
            peer = self._current()
            if peer is None or peer.generation != request.expected_generation or digest(peer) != request.intent_digest:
                msg = "Current Tether intent changed during pending revocation"
                raise TetherError(msg)
            binding = self._retained_binding(peer)
            try:
                owned_binding = self.binding_probe()
            except (TetherError, ValueError, OSError):
                self._retain_inert_revocation(request, peer, binding)
                return self._record(receipt, "ownership-unconfirmed", binding_identity=binding, complete=False)
            if owned_binding != binding:
                self._retain_inert_revocation(request, peer, binding)
                return self._record(receipt, "ownership-changed", binding_identity=binding, complete=False)
            # Publishing closed.json can itself trigger systemd Conflicts stops;
            # retained actual ownership must therefore precede that publication.
            latch = self._fence(request, peer, binding)
            receipt = self._record(receipt, "fence-durable", binding_identity=latch.binding_identity)
            observation = self.stop_adapter.stop()
            return self._record(receipt, "closure-observed", closure=observation, complete=observation.closed)

    def _retain_inert_revocation(
        self, request: RevokeRequest, peer: TetherPeerIntent, binding: PersistentBindingIdentity
    ) -> None:
        """Retain restart refusal without activating a guard against unowned units."""
        name = f"{peer.generation}.json"
        if self.custody.read("revocations", name) is not None:
            return
        latch = ClosureLatch(
            installation_id=request.installation_id,
            operation_id=request.operation_id,
            generation=peer.generation,
            intent_digest=digest(peer),
            envelope_digest=self.plan.envelope_digest,
            binding_identity=binding,
        )
        self.custody.write(
            "revocations", name, RevocationRecord(latch=latch, latch_digest=digest(latch)), immutable=True
        )

    def handle_closure(self) -> OperationReceipt:
        """Handle persistent closure after systemd orders conflicting transport stops."""
        with self.lock_factory():
            latch = self._latch()
            if latch is None:
                msg = "Closure handler requires the persistent active latch"
                raise TetherError(msg)
            current_binding = self.binding_probe()
            if current_binding != latch.binding_identity:
                store = PreparationStore(self.custody)
                store.require_replacement_ancestry(latch.envelope_digest)
                if not self.stop_adapter.observe().closed:
                    msg = "Closure handler binding differs without proven cold image-transition authority"
                    raise TetherError(msg)
            peer = self._current()
            if peer is None or peer.generation != latch.generation or digest(peer) != latch.intent_digest:
                msg = "Closure handler generation disagrees with public intent"
                raise TetherError(msg)
            self.custody.write(
                "revocations",
                f"{peer.generation}.json",
                RevocationRecord(latch=latch, latch_digest=digest(latch)),
                immutable=True,
            )
            raw = self.custody.read("operations", f"{latch.operation_id}.json")
            if raw is None:
                msg = "Closure latch has no correlated native operation"
                raise TetherError(msg)
            receipt = OperationReceipt.model_validate_json(raw)
            observation = self.stop_adapter.observe()
            result = self._record(
                receipt,
                "handler-closure-observed",
                closure=observation,
                complete=observation.closed and isinstance(receipt.request, RevokeRequest),
            )
            if not observation.closed:
                msg = "Whole Tether road closure remains incomplete"
                raise TetherError(msg)
            return result

    def inspect(self, request: InspectRequest) -> Inspection:
        """Observe fixed public state without acquiring a mutating lock."""
        self._validate(request)
        peer = self._current()
        if request.expected_generation != (peer.generation if peer else 0) or request.intent_digest != (
            digest(peer) if peer else self.plan.envelope_digest
        ):
            msg = "Inspection request no longer matches current intent"
            raise TetherError(msg)
        prepared: PreparationReceipt | None = None
        prepared_attested = False
        try:
            prepared = self.secrets.preparation_metadata()
            prepared_attested = self.secrets.attest() == prepared
        except (TetherError, ValueError, OSError):
            prepared_attested = False
        runtime = self.stop_adapter.runtime_identity()
        binding: PersistentBindingIdentity | None = None
        attested = False
        try:
            binding = self.binding_probe()
            if runtime is not None and peer is not None:
                observed = self.stop_adapter.capture_runtime(peer.generation, binding, publish=False)
                attested = observed == runtime
        except (TetherError, ValueError, OSError):
            # Desired intent and retained loaded identity remain inspectable
            # when actual transport is stopped, stale or indeterminate.
            attested = False
        desired: str | None = self.plan.envelope_digest
        if self.desired_probe is not None:
            try:
                desired = self.desired_probe()
            except (TetherError, ValueError, OSError):
                desired = None
        return Inspection(
            installation_id=request.installation_id,
            envelope_digest=self.plan.envelope_digest,
            peer=peer,
            closure_latch=self._latch(),
            preparation=prepared,
            preparation_attested=prepared_attested,
            observation=self.stop_adapter.observe(),
            loaded_runtime=runtime,
            runtime_attested=attested,
            binding_identity=binding,
            desired_envelope_digest=desired,
            configuration_drift=desired != self.plan.envelope_digest,
        )
