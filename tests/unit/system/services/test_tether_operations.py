"""Exercise durability/effect ordering, interrupted activation and cold generations."""

from __future__ import annotations

# pyright: reportPrivateUsage=false
import base64
import struct
from contextlib import nullcontext
from ipaddress import IPv4Address, IPv4Interface
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from lychd.domain.tether.models import (
    CompiledTetherPlan,
    TetherEnvelope,
    TetherPeerIntent,
    TetherSecretReference,
    compile_tether_plan,
)
from lychd.system.operator.process import ProcessResult
from lychd.system.services.tether.custody import TetherCustody
from lychd.system.services.tether.models import (
    ClosureLatch,
    ClosureObservation,
    EnrollRequest,
    OperationReceipt,
    RevocationRecord,
    RevokeRequest,
    TetherError,
    digest,
)
from lychd.system.services.tether.operations import TetherOperations


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


def make_custody(tmp_path: Path) -> TetherCustody:
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    custody = TetherCustody(codex, crypt)
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
    runner.run.side_effect = lambda argv, **_: ProcessResult(argv, 0, "active\n" if "show" in argv else "")
    stop.observe.return_value = closed()
    stop.stop.return_value = closed()
    operations = TetherOperations(
        plan,
        custody,
        secrets,
        stop,
        runner,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=lambda: "binding-1",
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
            binding_generation="binding-1",
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
    assert custody.read("private", "closed.json") is not None
    assert OperationReceipt.model_validate_json(
        custody.read(
            "operations",
            f"{ClosureLatch.model_validate_json(custody.read('private', 'closed.json')).operation_id}.json",
        )
    ).closure.closed


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

    def probe() -> str:
        if ownership == "unknown":
            msg = "Actual Scribe ownership unavailable"
            raise TetherError(msg)
        return "foreign-binding"

    operations.binding_probe = probe
    result = operations.revoke(request)
    assert not result.complete
    assert ("ownership-changed" if ownership == "foreign" else "ownership-unconfirmed") in result.stages
    assert custody.read("private", "closed.json") is None
    raw = custody.read("revocations", "1.json")
    assert raw is not None
    tombstone = RevocationRecord.model_validate_json(raw)
    assert tombstone.latch.binding_generation == "binding-1"
    assert tombstone.latch.generation == peer.generation
    assert tombstone.latch_digest == digest(tombstone.latch)
    assert operations.revoke(request) == result
    assert custody.read("revocations", "1.json") == raw
    stop.stop.assert_not_called()
    runner.run.assert_not_called()
    operations.binding_probe = lambda: "binding-1"
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
