"""A one-shot exit, failed watcher or successful stop reply cannot prove closure."""

from __future__ import annotations

import os

# pyright: reportPrivateUsage=false
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from lychd.system.operator.process import ProcessResult
from lychd.system.services.tether.closure import TetherStopAdapter
from lychd.system.services.tether.models import (
    ActivationAttempt,
    ClosureLatch,
    EnrollmentStartupAdmission,
    IncarnationIdentity,
    OperationReceipt,
    RevocationRecord,
    RoleIdentity,
    RuntimeIdentity,
    TetherError,
    digest,
)
from lychd.system.services.tether.units import render_tether_units
from tests.unit.system.services.test_tether_operations import admit_peer, make_custody, make_peer, make_plan, stack


@pytest.mark.parametrize("fault", [None, "wg-active", "container", "pod", "unknown", "job", "pid", "renamed-member"])
def test_whole_road_closure_requires_every_layer(fault: str | None) -> None:
    plan, runner = make_plan(), MagicMock()

    def probe(argv: tuple[str, ...], **_: object) -> ProcessResult:
        if "show" in argv:
            active = fault == "wg-active" and plan.wireguard_unit in argv
            return ProcessResult(
                argv,
                0,
                f"ActiveState={'active' if active else 'inactive'}\nSubState=dead\nMainPID={'4' if fault == 'pid' else '0'}\nControlPID=0\nControlGroup=\n",
            )
        if "list-jobs" in argv:
            return ProcessResult(argv, 0, "1 lychd-tether-ssh.service stop running" if fault == "job" else "")
        if argv[1] == "ps":
            return ProcessResult(argv, 0, '[{"PodName":"lychd-tether"}]' if fault == "renamed-member" else "[]")
        return ProcessResult(
            argv,
            125
            if fault == "unknown"
            else (
                0 if (fault == "pod" and argv[1] == "pod") or (fault == "container" and argv[1] == "container") else 1
            ),
        )

    runner.run.side_effect = probe
    adapter = TetherStopAdapter(plan, runner, podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl")
    observation = adapter.observe()
    assert observation.closed is (fault is None)
    assert all("start" not in call.args[0] and "restart" not in call.args[0] for call in runner.run.call_args_list)


def test_guard_is_persistent_latched_and_has_no_conflicting_pull_edges() -> None:
    plan = make_plan()
    units = render_tether_units(plan, crypt_root=Path("/owned/crypt"), executable=Path("/owned/venv/bin/python"))
    path, handler = units[plan.guard_unit], units[plan.closure_unit]
    assert 'PathExists="/owned/crypt/tether/closed.json"' in path
    assert "PathChanged=" not in path
    assert "Type=oneshot\nRemainAfterExit=yes" in handler
    assert "TimeoutStartSec=60" in handler
    assert "TimeoutStopSec=10" in handler
    assert "StartLimitIntervalSec=infinity\nStartLimitBurst=3" in handler
    assert "Conflicts=" + " ".join(plan.transport_units) in handler
    assert "After=" + " ".join(plan.transport_units) in handler
    assert "Requires=" not in handler
    assert "BindsTo=" not in handler
    assert "-m lychd.system.services.tether.composition close" in handler


def test_removed_pod_objects_cannot_hide_a_surviving_recorded_namespace() -> None:
    runtime = RuntimeIdentity(
        installation_id=make_plan().envelope.installation_id,
        generation=1,
        binding_generation="binding-1",
        boot_id=TetherStopAdapter.boot_id(),
        pod_id="a" * 64,
        wireguard_id="b" * 64,
        forwarder_id="c" * 64,
        netns_inode=Path("/proc/self/ns/net").stat().st_ino,
        service_cgroups=("/absent-a", "/absent-b", "/absent-c"),
        container_cgroups=("/absent-wg", "/absent-ssh"),
        host_uid_ranges=((os.getuid(), 1),),
    )
    # This process is the surviving namespace holder despite all synthetic
    # objects and recorded cgroups being absent.
    assert not TetherStopAdapter._namespace_absent(runtime)


def test_absent_objects_with_live_recorded_namespace_stay_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    plan, runner = make_plan(), MagicMock()

    def probe(argv: tuple[str, ...], **_: object) -> ProcessResult:
        if "show" in argv:
            return ProcessResult(
                argv, 0, "ActiveState=inactive\nSubState=dead\nMainPID=0\nControlPID=0\nControlGroup=\n"
            )
        if "list-jobs" in argv:
            return ProcessResult(argv, 0, "")
        if "ps" in argv:
            return ProcessResult(argv, 0, "[]")
        return ProcessResult(argv, 1)

    runner.run.side_effect = probe
    runtime = RuntimeIdentity(
        installation_id=plan.envelope.installation_id,
        generation=1,
        binding_generation="binding-1",
        boot_id=TetherStopAdapter.boot_id(),
        pod_id="a" * 64,
        wireguard_id="b" * 64,
        forwarder_id="c" * 64,
        netns_inode=Path("/proc/self/ns/net").stat().st_ino,
        service_cgroups=("/absent-a", "/absent-b", "/absent-c"),
        container_cgroups=("/absent-wg", "/absent-ssh"),
        host_uid_ranges=((os.getuid(), 1),),
    )
    adapter = TetherStopAdapter(plan, runner, podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl")
    monkeypatch.setattr(adapter, "runtime_identity", lambda: runtime)
    result = adapter.observe()
    assert result.pod_absent
    assert result.containers_absent
    assert result.jobs_absent
    assert not result.process_trees_empty
    assert not result.closed


def test_missing_pod_poststart_receipt_keeps_current_boot_attempt_incomplete(tmp_path: Path) -> None:
    custody, plan = make_custody(tmp_path), make_plan()
    attempt = ActivationAttempt(
        installation_id=plan.envelope.installation_id,
        generation=1,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=TetherStopAdapter.boot_id(),
        invocation_id=uuid4(),
        service_cgroup="/absent-tether",
    )
    custody.write("private", "activation.json", attempt)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    assert adapter._unattested_activation()


def test_reboot_proves_old_attempt_dead_but_same_boot_needs_physical_absence(monkeypatch: pytest.MonkeyPatch) -> None:
    plan, runner = make_plan(), MagicMock()
    adapter = TetherStopAdapter(plan, runner, podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl")
    value = IncarnationIdentity(
        installation_id=plan.envelope.installation_id,
        generation=1,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        pod_id="a" * 64,
        infra_id="b" * 64,
        netns_inode=1,
        infra_cgroup="/absent-infra",
        host_uid_ranges=((os.getuid(), 1),),
    )
    assert adapter.incarnation_closed(value)
    runner.run.assert_not_called()
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=1))
    runner.run.return_value = ProcessResult(("podman",), 0)
    assert not adapter.incarnation_closed(value)


@pytest.mark.parametrize("entry", ["pod-preflight", "begin-pod"])
def test_current_boot_unattested_attempt_cannot_be_hidden_by_another_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    operations, custody, _, _, _ = stack(tmp_path)
    peer = make_peer()
    admit_peer(custody, peer)
    plan = make_plan()
    attempt = ActivationAttempt(
        installation_id=plan.envelope.installation_id,
        generation=peer.generation,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=TetherStopAdapter.boot_id(),
        invocation_id=uuid4(),
        service_cgroup="/absent-uncertain-attempt",
    )
    name = f"attempt-{attempt.boot_id.hex}-{attempt.invocation_id.hex}.json"
    custody.write("generations", name, attempt, immutable=True)
    custody.write("private", "activation.json", attempt)
    original = custody.read("private", "activation.json")
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    operations.stop_adapter = adapter

    def startup_preflight(_expected_binding: str | None = None) -> None:
        return None

    monkeypatch.setattr(operations, "startup_preflight", startup_preflight)
    manager = MagicMock(return_value=(uuid4(), "/replacement-attempt"))
    monkeypatch.setattr(adapter, "_manager_invocation", manager)
    action = (
        (lambda: operations.role_preflight("pod"))
        if entry == "pod-preflight"
        else (lambda: adapter.begin_pod(peer.generation, "binding-1"))
    )
    with pytest.raises(TetherError, match=r"current-boot.*poststart"):
        action()
    manager.assert_not_called()
    assert custody.read("private", "activation.json") == original
    assert custody.read("generations", name) == original
    assert list(custody.directories["generations"].glob("attempt-*.json")) == [
        custody.directories["generations"] / name
    ]


def test_new_kernel_boot_cannot_hide_an_unmatched_prior_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custody, plan = make_custody(tmp_path), make_plan()
    old = ActivationAttempt(
        installation_id=plan.envelope.installation_id,
        generation=1,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        service_cgroup="/old-attempt",
    )
    name = f"attempt-{old.boot_id.hex}-{old.invocation_id.hex}.json"
    custody.write("generations", name, old, immutable=True)
    custody.write("private", "activation.json", old)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    manager = MagicMock(return_value=(UUID(int=3), "/new-attempt"))
    monkeypatch.setattr(adapter, "_manager_invocation", manager)
    with pytest.raises(TetherError, match=r"retained.*poststart"):
        adapter.begin_pod(1, "binding-1")
    manager.assert_not_called()
    assert custody.read("generations", name) == old.model_dump_json().encode()
    assert adapter.activation() == old


@pytest.mark.parametrize("fault", [None, "pod-id", "container-id", "namespace-membership"])
def test_live_closure_requires_retained_exact_object_ids_without_adoption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from tests.unit.system.services.test_tether_operations import closed

    custody, plan = make_custody(tmp_path), make_plan()
    incarnation = IncarnationIdentity(
        installation_id=plan.envelope.installation_id,
        generation=1,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=TetherStopAdapter.boot_id(),
        invocation_id=uuid4(),
        pod_id="a" * 64,
        infra_id="b" * 64,
        netns_inode=1,
        infra_cgroup="/retained-infra",
        host_uid_ranges=((os.getuid(), 1),),
    )
    custody.write("private", "incarnation.json", incarnation)
    rows = {
        plan.pod_name: {"Id": incarnation.pod_id, "Name": plan.pod_name, "InfraContainerID": incarnation.infra_id},
    }
    for role, name, identity in (
        ("wireguard", plan.wireguard_container, "c" * 64),
        ("forwarder", plan.forwarder_container, "d" * 64),
    ):
        record = RoleIdentity(
            pod_id=incarnation.pod_id,
            role="wireguard" if role == "wireguard" else "forwarder",
            container_id=identity,
            image_digest=plan.envelope.image.split("@", 1)[1],
            netns_inode=incarnation.netns_inode,
            cgroup=f"/retained-{role}",
        )
        custody.write("generations", f"role-{incarnation.pod_id}-{role}.json", record, immutable=True)
        rows[name] = {"Id": identity, "Name": name, "Pod": incarnation.pod_id, "ImageDigest": record.image_digest}
    if fault == "pod-id":
        rows[plan.pod_name]["Id"] = "e" * 64
    elif fault == "container-id":
        rows[plan.forwarder_container]["Id"] = "e" * 64
    elif fault == "namespace-membership":
        rows[plan.forwarder_container]["Pod"] = "e" * 64
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "observe", lambda: closed(value=False))

    def object_exists(*_arguments: str) -> bool:
        return True

    def inspect_object(_kind: str, name: str) -> dict[str, str]:
        return rows[name]

    monkeypatch.setattr(adapter, "_exists", object_exists)
    monkeypatch.setattr(adapter, "_inspect_object", inspect_object)
    publish = MagicMock(wraps=custody.write)
    monkeypatch.setattr(custody, "write", publish)
    if fault is None:
        adapter.require_retained_runtime_ownership("binding-1")
    else:
        with pytest.raises(TetherError, match=r"replaced|retained Pod"):
            adapter.require_retained_runtime_ownership("binding-1")
    publish.assert_not_called()


def test_new_boot_cannot_restart_a_retained_revoked_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custody, plan = make_custody(tmp_path), make_plan()
    latch = ClosureLatch(
        installation_id=plan.envelope.installation_id,
        operation_id=uuid4(),
        generation=1,
        intent_digest="retained-public-generation",
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
    )
    custody.write("revocations", "1.json", RevocationRecord(latch=latch, latch_digest=digest(latch)), immutable=True)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    manager = MagicMock(return_value=(UUID(int=3), "/new-attempt"))
    monkeypatch.setattr(adapter, "_manager_invocation", manager)
    with pytest.raises(TetherError, match="retained revocation"):
        adapter.begin_pod(1, "binding-1")
    manager.assert_not_called()
    assert custody.read("private", "activation.json") is None


def test_successfully_matched_old_attempt_remains_valid_for_completed_reboot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custody, plan = make_custody(tmp_path), make_plan()
    attempt = ActivationAttempt(
        installation_id=plan.envelope.installation_id,
        generation=1,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        service_cgroup="/old",
    )
    incarnation = IncarnationIdentity(
        installation_id=attempt.installation_id,
        generation=attempt.generation,
        envelope_digest=attempt.envelope_digest,
        binding_generation=attempt.binding_generation,
        boot_id=attempt.boot_id,
        invocation_id=attempt.invocation_id,
        pod_id="a" * 64,
        infra_id="b" * 64,
        netns_inode=1,
        infra_cgroup="/old-infra",
        host_uid_ranges=((os.getuid(), 1),),
    )
    custody.write("private", "activation.json", attempt)
    custody.write("private", "incarnation.json", incarnation)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    adapter.require_prior_activation_attested(binding_generation="binding-1")


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "latch-digest",
        "intent",
        "installation",
        "generation",
        "envelope",
        "binding",
        "admission-boot",
        "cold-proof",
    ],
)
def test_old_unmatched_attempt_requires_exact_revocation_and_fresh_next_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from tests.unit.system.services.test_tether_operations import enroll_request

    custody, plan = make_custody(tmp_path), make_plan()
    old = make_peer()
    admit_peer(custody, old)
    attempt = ActivationAttempt(
        installation_id=old.installation_id,
        generation=old.generation,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        service_cgroup="/old",
    )
    attempt_name = f"attempt-{attempt.boot_id.hex}-{attempt.invocation_id.hex}.json"
    custody.write("generations", attempt_name, attempt, immutable=True)
    custody.write("private", "activation.json", attempt)
    latch = ClosureLatch(
        installation_id=old.installation_id,
        operation_id=uuid4(),
        generation=old.generation,
        intent_digest=digest(old),
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
    )
    latch_changes: dict[str, dict[str, object]] = {
        "intent": {"intent_digest": "f" * 64},
        "installation": {"installation_id": UUID(int=99)},
        "generation": {"generation": 99},
        "envelope": {"envelope_digest": "f" * 64},
        "binding": {"binding_generation": "foreign"},
    }
    latch = latch.model_copy(update=latch_changes.get(fault or "", {}))
    record = RevocationRecord(latch=latch, latch_digest="f" * 64 if fault == "latch-digest" else digest(latch))
    custody.write("revocations", "1.json", record, immutable=True)
    peer = make_peer(2)
    admit_peer(custody, peer)
    request = enroll_request(peer)
    admission = EnrollmentStartupAdmission(
        boot_id=UUID(int=1 if fault == "admission-boot" else 2), request_digest=digest(request)
    )
    receipt = OperationReceipt(
        request_digest=digest(request),
        request=request,
        binding_generation="binding-1",
        stages=("wireguard-start-requested",)
        if fault == "cold-proof"
        else ("cold-proven", "wireguard-start-requested"),
        startup_admission=admission,
    )
    custody.write("operations", f"{peer.operation_id}.json", receipt)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    manager = MagicMock(return_value=(UUID(int=3), "/new"))
    monkeypatch.setattr(adapter, "_manager_invocation", manager)
    if fault is None:
        assert adapter.begin_pod(2, "binding-1").generation == 2
        manager.assert_called_once()
    else:
        with pytest.raises(TetherError, match=r"retained.*poststart"):
            adapter.begin_pod(2, "binding-1")
        manager.assert_not_called()
        assert adapter.activation() == attempt
    assert custody.read("generations", attempt_name) == attempt.model_dump_json().encode()
    assert custody.read("revocations", "1.json") == record.model_dump_json().encode()


@pytest.mark.parametrize("current_generation", [1, 2])
def test_reconciled_enrollment_must_be_strictly_later_than_the_old_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, current_generation: int
) -> None:
    from tests.unit.system.services.test_tether_operations import enroll_request

    custody, plan = make_custody(tmp_path), make_plan()
    old = make_peer(2)
    admit_peer(custody, old)
    attempt = ActivationAttempt(
        installation_id=old.installation_id,
        generation=2,
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
        boot_id=UUID(int=1),
        invocation_id=uuid4(),
        service_cgroup="/old",
    )
    name = f"attempt-{attempt.boot_id.hex}-{attempt.invocation_id.hex}.json"
    custody.write("generations", name, attempt, immutable=True)
    custody.write("private", "activation.json", attempt)
    latch = ClosureLatch(
        installation_id=old.installation_id,
        operation_id=uuid4(),
        generation=2,
        intent_digest=digest(old),
        envelope_digest=plan.envelope_digest,
        binding_generation="binding-1",
    )
    revoked = RevocationRecord(latch=latch, latch_digest=digest(latch))
    custody.write("revocations", "2.json", revoked, immutable=True)
    peer = old if current_generation == 2 else make_peer(1)
    admit_peer(custody, peer)
    request = enroll_request(peer)
    receipt = OperationReceipt(
        request_digest=digest(request),
        request=request,
        binding_generation="binding-1",
        stages=("cold-proven", "wireguard-start-requested"),
        startup_admission=EnrollmentStartupAdmission(boot_id=UUID(int=2), request_digest=digest(request)),
    )
    custody.write("operations", f"{peer.operation_id}.json", receipt)
    adapter = TetherStopAdapter(
        plan, MagicMock(), podman_bin="/usr/bin/podman", systemctl_bin="/usr/bin/systemctl", custody=custody
    )
    monkeypatch.setattr(adapter, "boot_id", lambda: UUID(int=2))
    with pytest.raises(TetherError, match=r"retained.*poststart"):
        adapter.require_prior_activation_attested(binding_generation="binding-1")
    assert adapter.activation() == attempt
    assert custody.read("generations", name) == attempt.model_dump_json().encode()
    assert custody.read("revocations", "2.json") == revoked.model_dump_json().encode()
