"""Exercise durability/effect ordering, interrupted activation and cold generations."""

from __future__ import annotations

# pyright: reportPrivateUsage=false
import base64
import hashlib
import os
import struct
from contextlib import nullcontext
from ipaddress import IPv4Address, IPv4Interface
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from lychd.domain.tether.models import (
    CompiledTetherPlan,
    TetherEnvelope,
    TetherPeerIntent,
    TetherSecretReference,
    compile_tether_plan,
)
from lychd.system.operator.process import ProcessResult
from lychd.system.path_identity import PersistentPathIdentity
from lychd.system.services.scribe.models import PersistentBindingIdentity
from lychd.system.services.tether.closure import TetherStopAdapter
from lychd.system.services.tether.custody import PreparationStore, TetherCustody
from lychd.system.services.tether.models import (
    ActivationAttempt,
    ClosureLatch,
    ClosureObservation,
    EnrollRequest,
    InspectRequest,
    OperationReceipt,
    PreparationReceipt,
    PreparationSelection,
    PrepareImageRequest,
    RevocationRecord,
    RevokeRequest,
    TetherError,
    digest,
)
from lychd.system.services.tether.operations import TetherOperations
from lychd.system.services.tether.secrets import TetherSecrets


def make_binding(label: str = "binding-1") -> PersistentBindingIdentity:
    """Return a distinct typed synthetic durable binding identity."""
    return PersistentBindingIdentity(version=1, digest=hashlib.sha256(label.encode()).hexdigest())


def make_plan() -> CompiledTetherPlan:
    """Return synthetic public intent, unrelated to any installed service."""
    return compile_tether_plan(
        TetherEnvelope(
            installation_id=UUID(int=1),
            interface="wgaltar",
            server_address=IPv4Interface("10.77.0.1/32"),
            udp_bind_address=IPv4Address("192.0.2.5"),
            udp_port=51820,
            advertised_endpoint="203.0.113.2:51820",
            image="localhost/tether@sha256:" + "a" * 64,
            wireguard_secret=TetherSecretReference(purpose="wireguard-server", name="test-wg"),
            ssh_host_secret=TetherSecretReference(purpose="ssh-host", name="test-ssh"),
            altar_port=7134,
        )
    )


def make_peer(generation: int = 1, operation_id: UUID | None = None) -> TetherPeerIntent:
    """Return bare valid public keys; no client private key is generated."""
    blob = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + b"p" * 32
    return TetherPeerIntent(
        installation_id=UUID(int=1),
        operation_id=operation_id or uuid4(),
        generation=generation,
        peer_id="operator",
        wireguard_public_key=base64.b64encode(b"w" * 32).decode(),
        address=IPv4Interface("10.77.0.2/32"),
        ssh_authorized_public_key="ssh-ed25519 " + base64.b64encode(blob).decode(),
    )


class FixtureTetherCustody(TetherCustody):
    """Keep filesystem provider qualification outside in-process operation fixtures."""

    @staticmethod
    def _identity(descriptor: int) -> PersistentPathIdentity:
        return PersistentPathIdentity(
            filesystem="ext4", filesystem_uuid=str(UUID(int=100)), inode=os.fstat(descriptor).st_ino, generation=1
        )


def make_custody(tmp_path: Path) -> TetherCustody:
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    custody = FixtureTetherCustody(codex, crypt)
    custody.initialize()
    return custody


def closed(*, value: bool = True) -> ClosureObservation:
    return ClosureObservation(
        closed=value,
        services=(),
        pod_absent=value,
        containers_absent=value,
        jobs_absent=value,
        process_trees_empty=value,
    )


def stack(tmp_path: Path) -> tuple[TetherOperations, TetherCustody, MagicMock, MagicMock, MagicMock]:
    plan, custody = make_plan(), make_custody(tmp_path)
    runner, secrets, stop = MagicMock(), MagicMock(), MagicMock()

    def run(argv: tuple[str, ...], **_: object) -> ProcessResult:
        return ProcessResult(argv, 0, "active\n" if "show" in argv else "")

    runner.run.side_effect = run
    stop.boot_id.return_value = TetherStopAdapter.boot_id()
    stop.observe.return_value = closed()
    stop.stop.return_value = closed()
    operations = TetherOperations(
        plan,
        custody,
        secrets,
        stop,
        runner,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=make_binding,
        lock_factory=nullcontext,
    )
    return operations, custody, runner, secrets, stop


def enroll_request(peer: TetherPeerIntent) -> EnrollRequest:
    plan = make_plan()
    return EnrollRequest(
        installation_id=peer.installation_id,
        operation_id=peer.operation_id,
        expected_generation=peer.generation - 1,
        envelope_digest=plan.envelope_digest,
        intent_digest=digest(peer),
        peer=peer,
    )


def admit_peer(custody: TetherCustody, peer: TetherPeerIntent) -> None:
    """Retain native enrollment authority before exercising a later revoke."""
    request = enroll_request(peer)
    custody.write("public", "peer.json", peer)
    custody.write("generations", f"{peer.generation}.json", peer, immutable=True)
    custody.write(
        "operations",
        f"{peer.operation_id}.json",
        OperationReceipt(
            request_digest=digest(request),
            request=request,
            binding_identity=make_binding(),
            stages=("prepared", "generation-published"),
            complete=True,
        ),
    )


def revoke_request(peer: TetherPeerIntent) -> RevokeRequest:
    return RevokeRequest(
        installation_id=peer.installation_id,
        operation_id=uuid4(),
        expected_generation=peer.generation,
        envelope_digest=make_plan().envelope_digest,
        intent_digest=digest(peer),
    )


def test_revoke_durably_fences_before_stop_and_retains_history(tmp_path: Path) -> None:
    operations, custody, _, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    request = revoke_request(peer)

    def observe_fence() -> ClosureObservation:
        assert ClosureLatch.model_validate_json(cast("bytes", custody.read("private", "closed.json"))).generation == 1
        assert custody.read("revocations", "1.json") is not None
        return closed()

    stop.stop.side_effect = observe_fence
    result = operations.revoke(request)
    assert result.complete
    assert operations.revoke(request) == result
    assert stop.stop.call_count == 1


@pytest.mark.parametrize("boundary", ["latch", "history", "journal", "stop"])
def test_crash_after_fence_preserves_restart_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    operations, custody, _, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    request = revoke_request(peer)
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        if (
            (boundary == "latch" and name == "closed.json")
            or (boundary == "history" and role == "revocations")
            or (boundary == "journal" and role == "operations" and "fence-durable" in getattr(value, "stages", ()))
        ):
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "write", crash)
    if boundary == "stop":
        stop.stop.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        operations.revoke(request)
    assert custody.read("private", "closed.json") is not None
    with pytest.raises(TetherError):
        operations.startup_preflight()
    monkeypatch.setattr(custody, "write", original)
    stop.stop.side_effect = None
    assert operations.revoke(request).complete


def test_unknown_stop_stays_incomplete_and_never_starts(tmp_path: Path) -> None:
    operations, custody, runner, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    stop.stop.return_value = closed(value=False)
    result = operations.revoke(revoke_request(peer))
    assert not result.complete
    assert custody.read("private", "closed.json")
    assert not runner.run.called


def test_enrollment_uses_guard_then_ready_wg_then_ssh_without_unit_writes(tmp_path: Path) -> None:
    operations, custody, runner, _, _ = stack(tmp_path)
    peer = make_peer()
    result = operations.enroll(enroll_request(peer))
    assert result.complete
    starts = [call.args[0] for call in runner.run.call_args_list if call.args[0][2] == "start"]
    assert starts == [
        ("/usr/bin/systemctl", "--user", "start", "lychd-tether-guard.path"),
        ("/usr/bin/systemctl", "--user", "start", "lychd-tether-pod.service", "lychd-tether-wg.service"),
        ("/usr/bin/systemctl", "--user", "start", "lychd-tether-ssh.service"),
    ]
    assert custody.read("generations", "1.json") == peer.model_dump_json().encode()
    assert all("core" not in str(call) for call in runner.run.call_args_list)


def test_cold_reenroll_preserves_old_revocation_and_resets_exact_handler(tmp_path: Path) -> None:
    operations, custody, runner, _, _ = stack(tmp_path)
    first = make_peer()
    operations.enroll(enroll_request(first))
    operations.revoke(revoke_request(first))
    history = custody.read("revocations", "1.json")
    second = make_peer(2)
    result = operations.enroll(enroll_request(second))
    assert result.complete
    assert custody.read("private", "closed.json") is None
    assert custody.read("revocations", "1.json") == history
    assert (
        "/usr/bin/systemctl",
        "--user",
        "reset-failed",
        "lychd-tether-close.service",
        "lychd-tether-guard.path",
    ) in [call.args[0] for call in runner.run.call_args_list]


def test_interrupted_activation_retry_fences_and_never_restarts_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operations, custody, runner, _, _ = stack(tmp_path)
    peer = make_peer()
    request = enroll_request(peer)
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        if role == "operations" and "wireguard-start-requested" in getattr(value, "stages", ()):
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "write", crash)
    with pytest.raises(KeyboardInterrupt):
        operations.enroll(request)
    monkeypatch.setattr(custody, "write", original)
    runner.reset_mock()
    result = operations.enroll(request)
    assert not result.complete
    assert custody.read("private", "closed.json") is not None
    assert not runner.run.called


def test_reused_operation_identity_with_other_intent_refuses(tmp_path: Path) -> None:
    operations, _, _, _, _ = stack(tmp_path)
    request = enroll_request(make_peer())
    operations.enroll(request)
    different = request.model_copy(update={"intent_digest": "f" * 64})
    with pytest.raises(TetherError, match="different intent"):
        operations.enroll(different)


def test_guard_handler_stays_fenced_and_requires_full_observation(tmp_path: Path) -> None:
    operations, custody, _, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    operations.revoke(revoke_request(peer))
    stop.observe.return_value = closed(value=False)
    with pytest.raises(TetherError, match="incomplete"):
        operations.handle_closure()
    stop.observe.return_value = closed()
    assert operations.handle_closure().complete
    raw_latch = custody.read("private", "closed.json")
    assert raw_latch is not None
    latch = ClosureLatch.model_validate_json(raw_latch)
    raw_receipt = custody.read("operations", f"{latch.operation_id}.json")
    assert raw_receipt is not None
    receipt = OperationReceipt.model_validate_json(raw_receipt)
    assert receipt.closure is not None
    assert receipt.closure.closed


@pytest.mark.parametrize("boundary", ["generation", "wireguard", "sshd", "authorized", "peer"])
def test_cold_reenroll_reconciles_crash_after_each_individual_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    operations, custody, _, _, _ = stack(tmp_path)
    first = make_peer()
    operations.enroll(enroll_request(first))
    operations.revoke(revoke_request(first))
    retained = custody.read("revocations", "1.json")
    second = make_peer(2)
    request = enroll_request(second)
    original = custody.publish
    fired = False
    targets = {
        "generation": ("generations", "2.json"),
        "wireguard": ("wireguard", "public.json"),
        "sshd": ("forwarder", "sshd_config"),
        "authorized": ("forwarder", "authorized_keys"),
        "peer": ("public", "peer.json"),
    }

    def crash(role: str, name: str, content: bytes, **kwargs: bool) -> None:
        nonlocal fired
        original(role, name, content, **kwargs)
        if not fired and (role, name) == targets[boundary]:
            fired = True
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "publish", crash)
    with pytest.raises(KeyboardInterrupt):
        operations.enroll(request)
    assert custody.read("private", "closed.json") is not None
    assert custody.read("revocations", "1.json") == retained
    monkeypatch.setattr(custody, "publish", original)
    assert operations.enroll(request).complete
    assert custody.read("private", "closed.json") is None
    assert custody.read("revocations", "1.json") == retained


def test_retained_revocation_blocks_start_even_if_active_latch_is_lost(tmp_path: Path) -> None:
    operations, custody, _, _, _ = stack(tmp_path)
    peer = make_peer()
    operations.enroll(enroll_request(peer))
    operations.revoke(revoke_request(peer))
    latch = custody.read("private", "closed.json")
    assert latch is not None
    custody.clear_latch(latch)
    with pytest.raises(TetherError, match="retained revocation"):
        operations.startup_preflight()


@pytest.mark.parametrize("ownership", ["foreign", "unknown"])
def test_revoke_keeps_active_guard_inert_for_unowned_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ownership: str
) -> None:
    operations, custody, runner, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    request = revoke_request(peer)
    original = custody.write

    def active_guard(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        # Model an already active PathExists guard: publication itself would
        # enqueue the handler's Conflicts stops, before its own ownership check.
        if role == "private" and name == "closed.json":
            stop.stop()

    monkeypatch.setattr(custody, "write", active_guard)

    def probe() -> PersistentBindingIdentity:
        if ownership == "unknown":
            msg = "Actual Scribe ownership unavailable"
            raise TetherError(msg)
        return make_binding("foreign-binding")

    operations.binding_probe = probe
    result = operations.revoke(request)
    assert not result.complete
    assert ("ownership-changed" if ownership == "foreign" else "ownership-unconfirmed") in result.stages
    assert custody.read("private", "closed.json") is None
    raw = custody.read("revocations", "1.json")
    assert raw is not None
    tombstone = RevocationRecord.model_validate_json(raw)
    assert tombstone.latch.binding_identity == make_binding()
    assert tombstone.latch.generation == peer.generation
    assert tombstone.latch_digest == digest(tombstone.latch)
    assert operations.revoke(request) == result
    assert custody.read("revocations", "1.json") == raw
    stop.stop.assert_not_called()
    runner.run.assert_not_called()
    operations.binding_probe = make_binding
    with pytest.raises(TetherError, match="retained revocation"):
        operations.startup_preflight()
    assert operations.revoke(request).complete
    assert custody.read("private", "closed.json") is not None


def test_revoke_preserves_retained_authority_when_desired_rune_is_removed(tmp_path: Path) -> None:
    operations, custody, _, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)

    def removed() -> str:
        msg = "Tether Rune removed"
        raise ValueError(msg)

    operations.desired_probe = removed
    assert operations.revoke(revoke_request(peer)).complete
    assert custody.read("private", "closed.json") is not None
    assert custody.read("revocations", "1.json") is not None
    stop.stop.assert_called_once()


def test_peer_publication_crash_cannot_be_promoted_to_enrollment_by_reboot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operations, custody, runner, _, stop = stack(tmp_path)
    peer = make_peer()
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        if role == "operations" and "generation-published" in getattr(value, "stages", ()):
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "write", crash)
    with pytest.raises(KeyboardInterrupt):
        operations.enroll(enroll_request(peer))
    monkeypatch.setattr(custody, "write", original)
    stop.boot_id.return_value = UUID(int=99)
    runner.reset_mock()
    with pytest.raises(TetherError, match="current-boot startup admission"):
        operations.startup_preflight()
    assert custody.read("public", "peer.json") == peer.model_dump_json().encode()
    assert not runner.run.called


def test_incomplete_native_admission_is_exact_and_current_boot_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operations, custody, runner, _, stop = stack(tmp_path)
    peer = make_peer()
    request = enroll_request(peer)
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        if role == "operations" and "wireguard-start-requested" in getattr(value, "stages", ()):
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "write", crash)
    with pytest.raises(KeyboardInterrupt):
        operations.enroll(request)
    monkeypatch.setattr(custody, "write", original)
    operations.startup_preflight()
    stop.boot_id.return_value = UUID(int=99)
    with pytest.raises(TetherError, match="current-boot startup admission"):
        operations.startup_preflight()
    runner.reset_mock()
    assert not operations.enroll(request).complete
    assert custody.read("private", "closed.json") is not None
    assert not runner.run.called


def test_completed_exact_enrollment_remains_admitted_after_kernel_reboot(tmp_path: Path) -> None:
    operations, _, _, _, stop = stack(tmp_path)
    assert operations.enroll(enroll_request(make_peer())).complete
    stop.boot_id.return_value = UUID(int=99)
    operations.startup_preflight()


@pytest.mark.parametrize(
    "fault",
    [
        "request-kind",
        "peer",
        "operation",
        "installation",
        "generation",
        "intent",
        "envelope",
        "binding",
        "request-digest",
        "completion-flag",
        "fenced-complete",
    ],
)
def test_startup_requires_exact_correlated_successful_enrollment(tmp_path: Path, fault: str) -> None:
    operations, custody, _, _, _ = stack(tmp_path)
    peer = make_peer()
    receipt = operations.enroll(enroll_request(peer))
    assert isinstance(receipt.request, EnrollRequest)
    request = receipt.request
    request_changes: dict[str, dict[str, object]] = {
        "peer": {"peer": peer.model_copy(update={"peer_id": "another"})},
        "operation": {"operation_id": uuid4()},
        "installation": {"installation_id": UUID(int=99)},
        "generation": {"expected_generation": peer.generation},
        "intent": {"intent_digest": "f" * 64},
        "envelope": {"envelope_digest": "f" * 64},
    }
    receipt_changes: dict[str, dict[str, object]] = {
        "request-kind": {"request": revoke_request(peer)},
        "binding": {"binding_identity": make_binding("foreign")},
        "request-digest": {"request_digest": "f" * 64},
        "completion-flag": {"stages": ("generation-published",)},
        "fenced-complete": {"stages": ("activation-fenced", "forwarder-active")},
    }
    updates = receipt_changes.get(fault, {})
    request_updates = request_changes.get(fault, {})
    if request_updates:
        updates["request"] = request.model_copy(update=request_updates)
    if "request" in updates:
        changed = updates["request"]
        assert isinstance(changed, (EnrollRequest, RevokeRequest))
        updates["request_digest"] = digest(changed)
    corrupted = OperationReceipt.model_validate(receipt.model_copy(update=updates).model_dump())
    custody.write("operations", f"{peer.operation_id}.json", corrupted)
    with pytest.raises(TetherError):
        operations.startup_preflight()


def test_later_enrollment_recovers_after_intermediate_grant_dies_before_begin_pod(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operations, custody, runner, _, _ = stack(tmp_path)
    first = make_peer()
    admit_peer(custody, first)
    attempt = ActivationAttempt(
        installation_id=first.installation_id,
        generation=1,
        envelope_digest=operations.plan.envelope_digest,
        binding_identity=make_binding(),
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        service_cgroup="/old-attempt",
    )
    old_name = f"attempt-{attempt.boot_id.hex}-{attempt.invocation_id.hex}.json"
    custody.write("generations", old_name, attempt, immutable=True)
    custody.write("private", "activation.json", attempt)
    adapter = TetherStopAdapter(
        operations.plan, runner, podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "observe", MagicMock(return_value=closed()))
    monkeypatch.setattr(adapter, "capture_runtime", MagicMock())
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    monkeypatch.setattr(adapter, "_manager_invocation", MagicMock(return_value=(uuid4(), "/new-attempt")))
    operations.stop_adapter = adapter
    assert operations.revoke(revoke_request(first)).complete
    second = make_peer(2)
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        original(role, name, value, **kwargs)
        if role == "operations" and "wireguard-start-requested" in getattr(value, "stages", ()):
            raise KeyboardInterrupt

    monkeypatch.setattr(custody, "write", crash)
    with pytest.raises(KeyboardInterrupt):
        operations.enroll(enroll_request(second))
    monkeypatch.setattr(custody, "write", original)
    assert adapter.activation() == attempt
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=3))
    with pytest.raises(TetherError, match="current-boot startup admission"):
        operations.startup_preflight()
    assert operations.revoke(revoke_request(second)).complete

    def manager_start(argv: tuple[str, ...], **_: object) -> ProcessResult:
        if argv[2] == "start" and operations.plan.pod_unit in argv:
            operations.role_preflight("pod")
            adapter.begin_pod(3, make_binding())
        return ProcessResult(argv, 0, "active\n" if "show" in argv else "")

    runner.run.side_effect = manager_start
    assert operations.enroll(enroll_request(make_peer(3))).complete
    current = adapter.activation()
    assert current is not None
    assert current.generation == 3
    assert current.boot_id == UUID(int=3)
    assert custody.read("generations", old_name) == attempt.model_dump_json().encode()
    assert custody.read("revocations", "1.json") is not None
    assert custody.read("revocations", "2.json") is not None


def image_stack(tmp_path: Path) -> tuple[TetherOperations, TetherSecrets, dict[str, dict[str, Any]], list[str]]:
    """Use real receipt/secret/transition services against one bounded fake Podman."""
    from tests.unit.system.services.test_tether_secrets import secret_stack

    initial, custody, values, created = secret_stack(tmp_path)
    initial.prepare(uuid4())
    target = compile_tether_plan(
        initial.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )
    gateway = TetherSecrets(
        target, custody, initial.runner, podman_bin=initial.podman, wg_bin=initial.wg, ssh_keygen_bin=initial.ssh_keygen
    )
    process, stop = MagicMock(), MagicMock()

    def run(argv: tuple[str, ...], **_: object) -> ProcessResult:
        return ProcessResult(argv, 0, "active\n" if "show" in argv else "")

    process.run.side_effect = run
    stop.boot_id.return_value = TetherStopAdapter.boot_id()
    stop.observe.return_value = closed()
    stop.stop.return_value = closed()
    operations = TetherOperations(
        target,
        custody,
        gateway,
        stop,
        process,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=lambda: make_binding("new-binding"),
        lock_factory=nullcontext,
        preparation_cold_probe=MagicMock(return_value=closed()),
    )
    return operations, initial, values, created


def image_request(operations: TetherOperations, *, generation: int = 0) -> PrepareImageRequest:
    return PrepareImageRequest(
        installation_id=operations.plan.envelope.installation_id,
        operation_id=uuid4(),
        expected_generation=generation,
        envelope_digest=operations.plan.envelope_digest,
        intent_digest=operations.plan.envelope_digest,
        expected_preparation_digest=digest(PreparationStore(operations.custody).selected().selection),
    )


def test_image_preparation_before_first_peer_reuses_creation_identities_and_does_not_bind(tmp_path: Path) -> None:
    operations, original, _, created = image_stack(tmp_path)
    before = PreparationStore(operations.custody).selected()
    original_plan = operations.custody.read("private", "plan.json")
    original_receipt = operations.custody.read("private", "preparation.json")
    request = image_request(operations)
    prepared = operations.prepare_image(request)
    assert isinstance(prepared, PreparationReceipt)
    assert prepared.secrets == before.preparation.secrets
    assert prepared.envelope_digest == operations.plan.envelope_digest
    assert operations.secrets.attest() == prepared
    assert operations.prepare_image(request) == prepared
    assert operations.custody.read("private", "plan.json") == original_plan
    assert operations.custody.read("private", "preparation.json") == original_receipt
    assert operations.custody.read("public", "peer.json") is None
    assert operations.custody.read("private", "closed.json") is None
    assert created == ["test-wg", "test-ssh"]
    cast("MagicMock", operations.runner).run.assert_not_called()
    cast("MagicMock", operations.stop_adapter).stop.assert_not_called()
    cast("MagicMock", original._factory).assert_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("interface", "wgdifferent"),
        ("udp_port", 51821),
        ("advertised_endpoint", "203.0.113.3:51820"),
        ("ssh_port", 2223),
        ("altar_port", 7135),
        ("installation_id", UUID(int=99)),
    ],
)
def test_image_preparation_rejects_every_non_image_migration(tmp_path: Path, field: str, value: object) -> None:
    operations, _, _, created = image_stack(tmp_path)
    operations.plan = compile_tether_plan(operations.plan.envelope.model_copy(update={field: value}))
    request = image_request(operations)
    with pytest.raises(TetherError, match="only a changed immutable image"):
        operations.prepare_image(request)
    assert operations.custody.read("private", "current-preparation.json") is None
    assert created == ["test-wg", "test-ssh"]


def test_image_preparation_dry_run_preserves_selector_journal_and_keys(tmp_path: Path) -> None:
    operations, _, _, created = image_stack(tmp_path)
    request = image_request(operations)
    lock = MagicMock(side_effect=AssertionError("dry run must not acquire a mutation lock"))
    operations.lock_factory = lock
    assert operations.prepare_image(request, dry_run=True) == request
    assert operations.custody.read("private", "current-preparation.json") is None
    assert operations.custody.read("operations", f"{request.operation_id}.json") is None
    assert created == ["test-wg", "test-ssh"]
    lock.assert_not_called()


@pytest.mark.parametrize("boundary", ["legacy-selector", "bundle", "selected", "completion"])
def test_image_transition_crashes_reconcile_exactly_without_recreating_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    operations, _, _, created = image_stack(tmp_path)
    request = image_request(operations)
    parent = PreparationStore(operations.custody).selected()
    selector = operations.custody.select_preparation
    writer = operations.custody.write
    fired = False

    def select(expected: bytes | None, value: PreparationSelection) -> None:
        nonlocal fired
        selector(expected, value)
        hit = (boundary == "legacy-selector" and value.parent_preparation_digest is None) or (
            boundary == "selected" and value.parent_preparation_digest is not None
        )
        if hit and not fired:
            fired = True
            raise KeyboardInterrupt

    def write(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        nonlocal fired
        writer(role, name, value, **kwargs)
        hit = (boundary == "bundle" and name.startswith("image-preparation-")) or (
            boundary == "completion" and "image-selected" in getattr(value, "stages", ())
        )
        if hit and not fired:
            fired = True
            raise KeyboardInterrupt

    monkeypatch.setattr(operations.custody, "select_preparation", select)
    monkeypatch.setattr(operations.custody, "write", write)
    with pytest.raises(KeyboardInterrupt):
        operations.prepare_image(request)
    monkeypatch.setattr(operations.custody, "select_preparation", selector)
    monkeypatch.setattr(operations.custody, "write", writer)
    selected = PreparationStore(operations.custody).selected()
    assert selected.plan == (parent.plan if boundary in {"legacy-selector", "bundle"} else operations.plan)
    prepared = operations.prepare_image(request)
    assert isinstance(prepared, PreparationReceipt)
    assert prepared.secrets == parent.preparation.secrets
    assert created == ["test-wg", "test-ssh"]


def test_stale_and_superseded_image_requests_cannot_reselect_old_authority(tmp_path: Path) -> None:
    operations, _, _, _ = image_stack(tmp_path)
    first = image_request(operations)
    operations.prepare_image(first)
    second_target = compile_tether_plan(
        operations.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "c" * 64})
    )
    operations.plan = second_target
    operations.secrets = TetherSecrets(
        second_target,
        operations.custody,
        operations.secrets.runner,
        podman_bin=operations.secrets.podman,
        wg_bin=operations.secrets.wg,
        ssh_keygen_bin=operations.secrets.ssh_keygen,
    )
    second = image_request(operations)
    operations.prepare_image(second)
    current = PreparationStore(operations.custody).selected()
    operations.plan = compile_tether_plan(
        operations.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )
    with pytest.raises(TetherError, match="Superseded"):
        operations.prepare_image(first)
    with pytest.raises(TetherError, match="stale"):
        operations.prepare_image(first.model_copy(update={"operation_id": uuid4()}))
    assert PreparationStore(operations.custody).selected() == current


def test_revoked_peer_image_transition_and_new_binding_preserve_historical_latch(tmp_path: Path) -> None:
    operations, original, _, created = image_stack(tmp_path)
    old = TetherOperations(
        original.plan,
        operations.custody,
        original,
        operations.stop_adapter,
        operations.runner,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=lambda: make_binding("old-binding"),
        lock_factory=nullcontext,
    )
    peer = make_peer()
    assert old.enroll(enroll_request(peer)).complete
    assert old.revoke(revoke_request(peer)).complete
    latch = operations.custody.read("private", "closed.json")
    revocation = operations.custody.read("revocations", "1.json")
    original_peer = operations.custody.read("generations", "1.json")
    operations.prepare_image(image_request(operations, generation=1))
    assert operations.custody.read("private", "closed.json") == latch
    assert operations.custody.read("revocations", "1.json") == revocation
    assert operations.custody.read("public", "peer.json") == peer.model_dump_json().encode()
    assert operations.enroll(
        enroll_request(make_peer(2)).model_copy(update={"envelope_digest": operations.plan.envelope_digest})
    ).complete
    assert operations.custody.read("private", "closed.json") is None
    assert operations.custody.read("revocations", "1.json") == revocation
    assert operations.custody.read("generations", "1.json") == original_peer
    assert created == ["test-wg", "test-ssh"]


def test_missing_public_peer_cannot_reset_generation_authority_for_image_preparation(tmp_path: Path) -> None:
    operations, original, _, _ = image_stack(tmp_path)
    peer = make_peer()
    admit_peer(operations.custody, peer)
    (operations.custody.directories["public"] / "peer.json").unlink()
    with pytest.raises(TetherError, match="generation/runtime history"):
        operations.prepare_image(image_request(operations))
    cast("MagicMock", operations.preparation_cold_probe).assert_not_called()
    assert operations.custody.read("private", "current-preparation.json") is None
    assert original.plan.envelope_digest == PreparationStore(operations.custody).selected().plan.envelope_digest


def test_selector_corruption_does_not_remove_owned_enrollment_closure_or_inspection(tmp_path: Path) -> None:
    operations, _, _, _ = image_stack(tmp_path)
    operations.prepare_image(image_request(operations))
    peer = make_peer()
    enrollment_request = enroll_request(peer).model_copy(update={"envelope_digest": operations.plan.envelope_digest})
    enrollment = operations.enroll(enrollment_request)
    operations.custody.publish("private", "current-preparation.json", b"invalid selection")
    store = PreparationStore(operations.custody)
    assert store.retained_enrollment_plan(peer, enrollment) == operations.plan
    with pytest.raises(ValidationError):
        store.selected()
    cast("MagicMock", operations.stop_adapter).runtime_identity.return_value = None
    request = RevokeRequest(
        installation_id=peer.installation_id,
        operation_id=uuid4(),
        expected_generation=peer.generation,
        envelope_digest=operations.plan.envelope_digest,
        intent_digest=digest(peer),
    )
    assert operations.revoke(request).complete
    inspection = operations.inspect(
        InspectRequest(
            installation_id=peer.installation_id,
            operation_id=uuid4(),
            expected_generation=peer.generation,
            envelope_digest=operations.plan.envelope_digest,
            intent_digest=digest(peer),
        )
    )
    assert inspection.preparation is None
    assert not inspection.preparation_attested
    assert inspection.peer == peer
    assert inspection.observation.closed
    with pytest.raises(ValidationError):
        store.selected()


def test_data_only_plan_reader_rejects_missing_enrollment_authority(tmp_path: Path) -> None:
    operations, _, _, _ = image_stack(tmp_path)
    operations.prepare_image(image_request(operations))
    peer = make_peer()
    request = enroll_request(peer).model_copy(update={"envelope_digest": operations.plan.envelope_digest})
    receipt = OperationReceipt(
        request_digest=digest(request), request=request, binding_identity=make_binding("new-binding")
    )
    with pytest.raises(TetherError, match="immutable peer and enrollment"):
        PreparationStore(operations.custody).retained_enrollment_plan(peer, receipt)


@pytest.mark.parametrize("case", ["round-trip", "no-replacement", "unrelated"])
def test_cold_historical_handler_requires_actual_replacement_ancestry_and_preserves_old_binding(
    tmp_path: Path, case: str
) -> None:
    operations, original, _, _ = image_stack(tmp_path)
    old = TetherOperations(
        original.plan,
        operations.custody,
        original,
        operations.stop_adapter,
        operations.runner,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=lambda: make_binding("old-binding"),
        lock_factory=nullcontext,
    )
    peer = make_peer()
    old.enroll(enroll_request(peer))
    old.revoke(revoke_request(peer))
    if case != "no-replacement":
        operations.prepare_image(image_request(operations, generation=1))
    if case == "round-trip":
        operations.plan = original.plan
        operations.secrets = original
        operations.prepare_image(image_request(operations, generation=1))
    else:
        operations.plan = original.plan
        operations.secrets = original
    if case == "unrelated":
        raw = operations.custody.read("private", "closed.json")
        assert raw is not None
        latch = ClosureLatch.model_validate_json(raw).model_copy(update={"envelope_digest": "f" * 64})
        operations.custody.write("private", "closed.json", latch)
    latch_bytes = operations.custody.read("private", "closed.json")
    revocation_bytes = operations.custody.read("revocations", "1.json")
    cast("MagicMock", operations.runner).reset_mock()
    cast("MagicMock", operations.stop_adapter).stop.reset_mock()
    if case == "round-trip":
        result = operations.handle_closure()
        assert result.complete
        assert result.binding_identity == make_binding("old-binding")
    else:
        with pytest.raises(TetherError, match="replacement"):
            operations.handle_closure()
    assert operations.custody.read("private", "closed.json") == latch_bytes
    assert operations.custody.read("revocations", "1.json") == revocation_bytes
    cast("MagicMock", operations.runner).run.assert_not_called()
    cast("MagicMock", operations.stop_adapter).stop.assert_not_called()


def test_missing_retained_binding_identity_cannot_activate_a_latch_or_stop(tmp_path: Path) -> None:
    operations, custody, _, _, stop = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    raw = custody.read("operations", f"{peer.operation_id}.json")
    assert raw is not None
    receipt = OperationReceipt.model_validate_json(raw).model_copy(update={"binding_identity": None})
    custody.write("operations", f"{peer.operation_id}.json", receipt)
    stop.incarnation.return_value = None
    with pytest.raises(TetherError, match="binding identity is absent"):
        operations.revoke(revoke_request(peer))
    assert custody.read("private", "closed.json") is None
    assert custody.read("revocations", "1.json") is None
    stop.stop.assert_not_called()
