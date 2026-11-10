"""Monotonic stop and independent whole-road observation; never compensation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from lychd.system.services.tether.models import (
    ActivationAttempt,
    ClosureObservation,
    IncarnationIdentity,
    OperationReceipt,
    RevocationRecord,
    RoleIdentity,
    RuntimeIdentity,
    TetherError,
    digest,
)

if TYPE_CHECKING:
    from lychd.domain.tether.models import CompiledTetherPlan
    from lychd.system.operator.process import ProcessRunner
    from lychd.system.services.tether.custody import TetherCustody


_MAX_PROC_ENTRIES = 65536


class TetherStopAdapter:
    """A fenced generation can only stop, observe or remain uncertain."""

    def __init__(
        self,
        plan: CompiledTetherPlan,
        runner: ProcessRunner,
        *,
        podman_bin: str,
        systemctl_bin: str,
        custody: TetherCustody | None = None,
    ) -> None:
        """Bind fixed native roles to trusted custody and process dependencies."""
        self.plan, self.runner = plan, runner
        self.podman, self.systemctl = podman_bin, systemctl_bin
        self.custody = custody

    def stop(self) -> ClosureObservation:
        """Request exact transport stops, then independently observe every layer."""
        self.runner.run((self.systemctl, "--user", "stop", *reversed(self.plan.transport_units)), timeout_s=45)
        return self.observe()

    def require_retained_runtime_ownership(self, binding_generation: str) -> None:
        """Permit closure only for exact retained live object IDs or a proven cold road."""
        if self.observe().closed:
            return
        incarnation = self.incarnation()
        if (
            incarnation is None
            or incarnation.boot_id != self.boot_id()
            or incarnation.binding_generation != binding_generation
            or self._unattested_activation()
        ):
            msg = "Tether live road lacks exact retained current-incarnation ownership"
            raise TetherError(msg)
        expected = {
            ("pod", self.plan.pod_name): incarnation.pod_id,
            ("container", self.plan.wireguard_container): None,
            ("container", self.plan.forwarder_container): None,
        }
        if self.custody is None:
            msg = "Tether live ownership requires native custody"
            raise TetherError(msg)
        for role, name in (("wireguard", self.plan.wireguard_container), ("forwarder", self.plan.forwarder_container)):
            raw = self.custody.read("generations", f"role-{incarnation.pod_id}-{role}.json")
            if raw is not None:
                identity = RoleIdentity.model_validate_json(raw)
                if identity.pod_id != incarnation.pod_id or identity.role != role:
                    msg = "Retained Tether role belongs to another incarnation"
                    raise TetherError(msg)
                expected[("container", name)] = identity.container_id
        runtime = self.runtime_identity()
        if runtime is not None and (
            runtime.boot_id != incarnation.boot_id
            or runtime.pod_id != incarnation.pod_id
            or runtime.netns_inode != incarnation.netns_inode
            or runtime.binding_generation != binding_generation
        ):
            msg = "Retained Tether runtime disagrees with current incarnation"
            raise TetherError(msg)
        if runtime is not None and (
            runtime.generation != incarnation.generation
            or runtime.wireguard_id != expected[("container", self.plan.wireguard_container)]
            or runtime.forwarder_id != expected[("container", self.plan.forwarder_container)]
        ):
            msg = "Retained Tether role IDs disagree with its runtime identity"
            raise TetherError(msg)
        matched = tuple(
            self._require_named_runtime_object(kind, name, identity, incarnation)
            for (kind, name), identity in expected.items()
        )
        if not any(matched):
            msg = "Tether retained runtime is neither exactly live nor proven cold"
            raise TetherError(msg)

    def _require_named_runtime_object(
        self,
        kind: str,
        name: str,
        identity: str | None,
        incarnation: IncarnationIdentity,
    ) -> bool:
        """Refuse any extant familiar name that lacks its retained immutable ID."""
        exists = self._exists(kind, "exists", name)
        if exists is False:
            return False
        if exists is not True or identity is None:
            msg = "Tether named runtime object lacks exact retained ownership"
            raise TetherError(msg)
        row = self._inspect_object(kind, name)
        if row.get("Id") != identity or row.get("Name") != name:
            msg = "Tether named runtime object was replaced"
            raise TetherError(msg)
        if kind == "pod":
            valid = row.get("InfraContainerID") == incarnation.infra_id
        else:
            valid = (
                row.get("Pod") == incarnation.pod_id
                and row.get("ImageDigest") == self.plan.envelope.image.split("@", 1)[1]
            )
        if not valid:
            msg = "Tether runtime object differs from retained Pod or image identity"
            raise TetherError(msg)
        return True

    def _exists(self, *arguments: str) -> bool | None:
        result = self.runner.run((self.podman, *arguments), timeout_s=5)
        if result.returncode == 1:
            return False
        return True if result.returncode == 0 else None

    def runtime_identity(self) -> RuntimeIdentity | None:
        """Read the retained loaded identity separately from current desired peer."""
        if self.custody is None:
            return None
        from lychd.domain.tether.models import TetherPeerIntent

        peer_raw = self.custody.read("public", "peer.json")
        if peer_raw is None:
            return None
        TetherPeerIntent.model_validate_json(peer_raw)
        raw = self.custody.read("private", "runtime.json")
        if raw is None:
            return None
        runtime = RuntimeIdentity.model_validate_json(raw)
        if runtime.installation_id != self.plan.envelope.installation_id:
            msg = "Tether runtime identity belongs to another generation"
            raise TetherError(msg)
        return runtime

    def activation(self) -> ActivationAttempt | None:
        """Read the exact current manager start attempt, including pre-Pod crashes."""
        if self.custody is None:
            return None
        raw = self.custody.read("private", "activation.json")
        return ActivationAttempt.model_validate_json(raw) if raw is not None else None

    def _unattested_activation(self) -> bool:
        attempt = self.activation()
        if attempt is None or attempt.boot_id != self.boot_id():
            return False
        incarnation = self.incarnation()
        return (
            incarnation is None
            or incarnation.invocation_id != attempt.invocation_id
            or incarnation.boot_id != attempt.boot_id
            or incarnation.generation != attempt.generation
        )

    def require_prior_activation_attested(self, *, binding_generation: str | None = None) -> None:
        """Reject unmatched attempts across boots until exact fenced reconciliation."""
        attempt = self.activation()
        if attempt is None:
            return
        incarnation = self.incarnation()
        if incarnation is not None and (
            incarnation.invocation_id == attempt.invocation_id
            and incarnation.boot_id == attempt.boot_id
            and incarnation.generation == attempt.generation
            and incarnation.installation_id == attempt.installation_id
            and incarnation.envelope_digest == attempt.envelope_digest
            and incarnation.binding_generation == attempt.binding_generation
        ):
            return
        if self._reconciled_later_generation(attempt, binding_generation):
            return
        msg = "Prior current-boot or retained Tether activation lacks Pod poststart attestation"
        raise TetherError(msg)

    def _reconciled_later_generation(self, attempt: ActivationAttempt, binding_generation: str | None) -> bool:
        if self.custody is None or binding_generation is None or attempt.boot_id == self.boot_id():
            return False
        from lychd.domain.tether.models import TetherPeerIntent

        old_raw = self.custody.read("generations", f"{attempt.generation}.json")
        revoked_raw = self.custody.read("revocations", f"{attempt.generation}.json")
        current_raw = self.custody.read("public", "peer.json")
        if old_raw is None or revoked_raw is None or current_raw is None:
            return False
        old = TetherPeerIntent.model_validate_json(old_raw)
        record = RevocationRecord.model_validate_json(revoked_raw)
        peer = TetherPeerIntent.model_validate_json(current_raw)
        latch = record.latch
        if (
            record.latch_digest != digest(latch)
            or old.generation != attempt.generation
            or old.installation_id != attempt.installation_id
            or attempt.installation_id != self.plan.envelope.installation_id
            or attempt.envelope_digest != self.plan.envelope_digest
            or latch.installation_id != old.installation_id
            or latch.generation != old.generation
            or latch.intent_digest != digest(old)
            or latch.envelope_digest != attempt.envelope_digest
            or latch.binding_generation != attempt.binding_generation
            or peer.installation_id != old.installation_id
            or peer.generation <= old.generation
        ):
            return False
        raw_receipt = self.custody.read("operations", f"{peer.operation_id}.json")
        if raw_receipt is None:
            return False
        receipt = OperationReceipt.model_validate_json(raw_receipt)
        if (
            "cold-proven" not in receipt.stages
            or receipt.startup_admission is None
            or receipt.startup_admission.boot_id != self.boot_id()
        ):
            return False
        receipt.require_enrollment_startup(
            peer,
            envelope_digest=self.plan.envelope_digest,
            binding_generation=binding_generation,
            boot_id=self.boot_id(),
        )
        return True

    @staticmethod
    def _cgroup_empty(group: str) -> bool:
        if not group.startswith("/") or ".." in Path(group).parts:
            return False
        try:
            events = dict(
                line.split()
                for line in (Path("/sys/fs/cgroup") / group.lstrip("/") / "cgroup.events").read_text().splitlines()
            )
            return events.get("populated") == "0"
        except FileNotFoundError:
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def _namespace_absent(runtime: RuntimeIdentity | IncarnationIdentity) -> bool:
        """Refuse live or unobservable namespace holders within the owned UID map."""
        if runtime.boot_id != TetherStopAdapter.boot_id():
            return True
        try:
            for index, entry in enumerate(Path("/proc").iterdir()):
                if index > _MAX_PROC_ENTRIES:
                    return False
                if not entry.name.isdecimal():
                    continue
                try:
                    owner = entry.stat().st_uid
                    if not any(start <= owner < start + count for start, count in runtime.host_uid_ranges):
                        continue
                    if (entry / "ns/net").stat().st_ino == runtime.netns_inode:
                        return False
                except FileNotFoundError:
                    continue
                except OSError:
                    # Relevant opaque process is uncertainty, not absence.
                    return False
        except OSError:
            return False
        return True

    @staticmethod
    def _process_cgroup(pid: int) -> str:
        rows = (Path("/proc") / str(pid) / "cgroup").read_text().splitlines()
        unified = [row.removeprefix("0::") for row in rows if row.startswith("0::/")]
        if len(unified) != 1 or ".." in Path(unified[0]).parts:
            msg = "Tether runtime requires one exact unified container cgroup"
            raise TetherError(msg)
        return unified[0]

    @staticmethod
    def boot_id() -> UUID:
        """Read the kernel incarnation; never infer reboot from filesystem age."""
        return UUID(Path("/proc/sys/kernel/random/boot_id").read_text().strip())

    def _inspect_object(self, kind: str, name: str) -> dict[str, Any]:
        result = self.runner.run((self.podman, kind, "inspect", name), timeout_s=5)
        raw: object = json.loads(result.stdout)
        rows: list[object] = cast("list[object]", raw) if isinstance(raw, list) else []
        if result.returncode or len(rows) != 1 or not isinstance(rows[0], dict):
            msg = "Cannot attest exact Tether runtime object"
            raise TetherError(msg)
        return cast("dict[str, Any]", rows[0])

    def incarnation(self) -> IncarnationIdentity | None:
        """Read current Pod identity, including a partially activated road."""
        if self.custody is None:
            return None
        raw = self.custody.read("private", "incarnation.json")
        if raw is None:
            return None
        value = IncarnationIdentity.model_validate_json(raw)
        if (
            value.installation_id != self.plan.envelope.installation_id
            or value.envelope_digest != self.plan.envelope_digest
        ):
            msg = "Tether incarnation belongs to another installation or envelope"
            raise TetherError(msg)
        return value

    def incarnation_closed(self, value: IncarnationIdentity) -> bool:
        """Prove only the old physical incarnation cold before a same-boot restart."""
        if value.boot_id != self.boot_id():
            return True
        return (
            self._exists("pod", "exists", value.pod_id) is False
            and self._exists("container", "exists", value.infra_id) is False
            and self._cgroup_empty(value.infra_cgroup)
            and self._namespace_absent(value)
        )

    def _manager_invocation(self) -> tuple[UUID, str]:
        result = self.runner.run(
            (
                self.systemctl,
                "--user",
                "show",
                self.plan.pod_unit,
                "--property=InvocationID,ControlGroup,ActiveState",
                "--no-pager",
            ),
            timeout_s=5,
        )
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        invocation = UUID(values.get("InvocationID", ""))
        group = values.get("ControlGroup", "")
        own_group = self._process_cgroup(os.getpid())
        if (
            result.returncode
            or invocation.int == 0
            or values.get("ActiveState") != "activating"
            or not group.startswith("/")
            or (own_group != group and not own_group.startswith(group + "/"))
        ):
            msg = "Tether start attempt lacks actual manager invocation/cgroup authority"
            raise TetherError(msg)
        return invocation, group

    def begin_pod(self, generation: int, binding_generation: str) -> ActivationAttempt:
        """Record the exact manager incarnation before any Pod creation effect."""
        if self.custody is None:
            msg = "Pod startup journaling requires native custody"
            raise TetherError(msg)
        self.require_prior_activation_attested(binding_generation=binding_generation)
        if self.custody.read("revocations", f"{generation}.json") is not None:
            msg = "Tether generation has retained revocation evidence and cannot restart"
            raise TetherError(msg)
        invocation, group = self._manager_invocation()
        value = ActivationAttempt(
            installation_id=self.plan.envelope.installation_id,
            generation=generation,
            envelope_digest=self.plan.envelope_digest,
            binding_generation=binding_generation,
            boot_id=self.boot_id(),
            invocation_id=invocation,
            service_cgroup=group,
        )
        self.custody.write(
            "generations", f"attempt-{value.boot_id.hex}-{value.invocation_id.hex}.json", value, immutable=True
        )
        self.custody.write("private", "activation.json", value)
        return value

    def attest_pod(self, generation: int, binding_generation: str) -> IncarnationIdentity:
        """Durably attest infra namespace before WireGuard's ordered job can start."""
        if self.custody is None:
            msg = "Pod attestation requires fixed native custody"
            raise TetherError(msg)
        attempt = self.activation()
        invocation, _ = self._manager_invocation()
        if (
            attempt is None
            or attempt.invocation_id != invocation
            or attempt.boot_id != self.boot_id()
            or attempt.generation != generation
            or attempt.binding_generation != binding_generation
        ):
            msg = "Pod poststart does not match its durable manager start attempt"
            raise TetherError(msg)
        pod = self._inspect_object("pod", self.plan.pod_name)
        infra = self._inspect_object("container", pod["InfraContainerID"])
        pid = int(infra["State"]["Pid"])
        if (
            pod.get("Name") != self.plan.pod_name
            or infra.get("Pod") != pod.get("Id")
            or pid <= 0
            or infra.get("IsInfra") is not True
        ):
            msg = "Tether Pod infrastructure identity is not exact"
            raise TetherError(msg)
        ranges = tuple(
            (int(line.split()[1]), int(line.split()[2]))
            for line in (Path("/proc") / str(pid) / "uid_map").read_text().splitlines()
        )
        value = IncarnationIdentity(
            installation_id=self.plan.envelope.installation_id,
            generation=generation,
            envelope_digest=self.plan.envelope_digest,
            binding_generation=binding_generation,
            boot_id=self.boot_id(),
            pod_id=pod["Id"],
            infra_id=pod["InfraContainerID"],
            invocation_id=invocation,
            netns_inode=(Path("/proc") / str(pid) / "ns/net").stat().st_ino,
            infra_cgroup=self._process_cgroup(pid),
            host_uid_ranges=ranges,
        )
        old = self.incarnation()
        if old is not None and old.pod_id != value.pod_id and not self.incarnation_closed(old):
            msg = "The previous Tether incarnation remains live or uncertain"
            raise TetherError(msg)
        self.custody.write("generations", f"incarnation-{value.pod_id}.json", value, immutable=True)
        self.custody.write("private", "incarnation.json", value)
        return value

    def attest_role(self, role: str) -> RoleIdentity:
        """Append one fixed role only to its exact attested Pod namespace."""
        incarnation = self.incarnation()
        if incarnation is None or self.custody is None or role not in {"wireguard", "forwarder"}:
            msg = "Tether role has no current Pod creation authority"
            raise TetherError(msg)
        name = self.plan.wireguard_container if role == "wireguard" else self.plan.forwarder_container
        row = self._inspect_object("container", name)
        pid = int(row["State"]["Pid"])
        inode = (Path("/proc") / str(pid) / "ns/net").stat().st_ino
        if (
            row.get("Name") != name
            or row.get("Pod") != incarnation.pod_id
            or row.get("ImageDigest") != self.plan.envelope.image.split("@", 1)[1]
            or row.get("State", {}).get("Running") is not True
            or inode != incarnation.netns_inode
        ):
            msg = "Tether role is foreign, stopped or outside its exact namespace/image"
            raise TetherError(msg)
        value = RoleIdentity(
            pod_id=incarnation.pod_id,
            role="wireguard" if role == "wireguard" else "forwarder",
            container_id=row["Id"],
            image_digest=row["ImageDigest"],
            netns_inode=inode,
            cgroup=self._process_cgroup(pid),
        )
        self.custody.write("generations", f"role-{incarnation.pod_id}-{role}.json", value, immutable=True)
        return value

    def capture_runtime(self, generation: int, binding_generation: str, *, publish: bool = True) -> RuntimeIdentity:
        """Seal immutable IDs, shared network namespace and all service cgroups."""
        pod = self._inspect_object("pod", self.plan.pod_name)
        wg = self._inspect_object("container", self.plan.wireguard_container)
        ssh = self._inspect_object("container", self.plan.forwarder_container)
        if pod.get("Name") != self.plan.pod_name:
            msg = "Tether Pod identity differs"
            raise TetherError(msg)
        for row, name in ((wg, self.plan.wireguard_container), (ssh, self.plan.forwarder_container)):
            if (
                row.get("Name") != name
                or row.get("Pod") != pod.get("Id")
                or row.get("ImageDigest") != self.plan.envelope.image.split("@", 1)[1]
                or row.get("State", {}).get("Running") is not True
            ):
                msg = "Tether role is foreign, stopped or uses another immutable image"
                raise TetherError(msg)
        inode = Path(f"/proc/{int(wg['State']['Pid'])}/ns/net").stat().st_ino
        if inode != Path(f"/proc/{int(ssh['State']['Pid'])}/ns/net").stat().st_ino:
            msg = "Tether containers do not share their dedicated network namespace"
            raise TetherError(msg)
        container_groups = (
            self._process_cgroup(int(wg["State"]["Pid"])),
            self._process_cgroup(int(ssh["State"]["Pid"])),
        )
        uid_rows = (Path("/proc") / str(int(wg["State"]["Pid"])) / "uid_map").read_text().splitlines()
        uid_ranges = tuple((int(row.split()[1]), int(row.split()[2])) for row in uid_rows)
        if not uid_ranges or any(start < 0 or count <= 0 for start, count in uid_ranges):
            msg = "Tether process user namespace has no exact host UID map"
            raise TetherError(msg)
        groups: list[str] = []
        for unit in self.plan.transport_units:
            result = self.runner.run(
                (self.systemctl, "--user", "show", unit, "--property=ControlGroup", "--value"), timeout_s=5
            )
            group = result.stdout.strip()
            if result.returncode or not group.startswith("/") or ".." in Path(group).parts or self._cgroup_empty(group):
                msg = "Tether live process-tree cgroup is not attested"
                raise TetherError(msg)
            groups.append(group)
        identity = RuntimeIdentity(
            installation_id=self.plan.envelope.installation_id,
            generation=generation,
            binding_generation=binding_generation,
            boot_id=self.boot_id(),
            pod_id=pod["Id"],
            wireguard_id=wg["Id"],
            forwarder_id=ssh["Id"],
            netns_inode=inode,
            service_cgroups=(groups[0], groups[1], groups[2]),
            container_cgroups=container_groups,
            host_uid_ranges=uid_ranges,
        )
        if self.custody is not None and publish:
            self.custody.write("generations", f"runtime-{identity.pod_id}.json", identity, immutable=True)
            self.custody.write("private", "runtime.json", identity)
        return identity

    def observe(self) -> ClosureObservation:  # noqa: C901, PLR0912, PLR0915 - independent closure dimensions must all remain explicit
        """Require zero jobs, cgroup processes, containers and owned Pod namespace.

        Podman object absence proves the owned namespace has been released by
        Podman; an inactive WireGuard configuring process alone proves nothing.
        Any failed/unknown query keeps closure incomplete.
        """
        services: list[tuple[str, str]] = []
        processes_empty = True
        terminal = True
        for unit in self.plan.transport_units:
            result = self.runner.run(
                (
                    self.systemctl,
                    "--user",
                    "show",
                    unit,
                    "--property=ActiveState,SubState,MainPID,ControlPID,ControlGroup",
                    "--no-pager",
                ),
                timeout_s=5,
            )
            values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            state = values.get("ActiveState", "unknown")
            services.append((unit, state))
            if result.returncode or state not in {"inactive", "failed"}:
                terminal = False
            if values.get("MainPID") != "0" or values.get("ControlPID") != "0":
                processes_empty = False
            cgroup = values.get("ControlGroup")
            if cgroup:
                location = Path("/sys/fs/cgroup") / cgroup.lstrip("/")
                if ".." in location.parts:
                    processes_empty = False
                else:
                    try:
                        events = dict(line.split() for line in (location / "cgroup.events").read_text().splitlines())
                        if events.get("populated") != "0":
                            processes_empty = False
                    except FileNotFoundError:
                        pass
                    except (OSError, ValueError):
                        processes_empty = False
            elif cgroup is None:
                processes_empty = False
        jobs = self.runner.run((self.systemctl, "--user", "list-jobs", "--no-legend", "--no-pager"), timeout_s=5)
        jobs_absent = jobs.returncode == 0 and not any(
            set(line.split()) & set(self.plan.transport_units) for line in jobs.stdout.splitlines()
        )
        pod_absent = self._exists("pod", "exists", self.plan.pod_name) is False
        containers_absent = all(
            self._exists("container", "exists", name) is False
            for name in (self.plan.wireguard_container, self.plan.forwarder_container)
        )
        runtime = self.runtime_identity()
        if self._unattested_activation():
            processes_empty = False
        if runtime is not None:
            pod_absent = pod_absent and self._exists("pod", "exists", runtime.pod_id) is False
            containers_absent = containers_absent and all(
                self._exists("container", "exists", identity) is False
                for identity in (runtime.wireguard_id, runtime.forwarder_id)
            )
            processes_empty = (
                processes_empty
                and all(self._cgroup_empty(group) for group in (*runtime.service_cgroups, *runtime.container_cgroups))
                and self._namespace_absent(runtime)
            )
        incarnation = self.incarnation()
        if incarnation is not None:
            pod_absent = pod_absent and self._exists("pod", "exists", incarnation.pod_id) is False
            containers_absent = containers_absent and self._exists("container", "exists", incarnation.infra_id) is False
            processes_empty = (
                processes_empty and self._cgroup_empty(incarnation.infra_cgroup) and self._namespace_absent(incarnation)
            )
            if self.custody is not None:
                for role in ("wireguard", "forwarder"):
                    raw = self.custody.read("generations", f"role-{incarnation.pod_id}-{role}.json")
                    if raw is not None:
                        record = RoleIdentity.model_validate_json(raw)
                        containers_absent = (
                            containers_absent and self._exists("container", "exists", record.container_id) is False
                        )
                        processes_empty = processes_empty and self._cgroup_empty(record.cgroup)
        # Inspect all containers too: a renamed, still-running Pod member must
        # not turn familiar-name absence into a successful closure receipt.
        listing = self.runner.run((self.podman, "ps", "--all", "--format", "json"), timeout_s=5)
        try:
            raw: object = json.loads(listing.stdout)
            rows: list[object] | None = cast("list[object]", raw) if isinstance(raw, list) else None
            if listing.returncode or rows is None:
                containers_absent = False
            else:
                for candidate in rows:
                    if not isinstance(candidate, dict):
                        containers_absent = False
                        break
                    row = cast("dict[str, object]", candidate)
                    if row.get("PodName") == self.plan.pod_name:
                        containers_absent = False
                        break
        except (ValueError, TypeError, AttributeError):
            containers_absent = False
        guard_states: list[str] = []
        for unit in (self.plan.guard_unit, self.plan.closure_unit):
            result = self.runner.run(
                (self.systemctl, "--user", "show", unit, "--property=ActiveState,SubState", "--no-pager"), timeout_s=5
            )
            state = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            guard_states.append(
                f"{state.get('ActiveState', 'unknown')}/{state.get('SubState', 'unknown')}"
                if result.returncode == 0
                else "unknown"
            )
        return ClosureObservation(
            closed=terminal and processes_empty and jobs_absent and pod_absent and containers_absent,
            services=tuple(services),
            pod_absent=pod_absent,
            containers_absent=containers_absent,
            jobs_absent=jobs_absent,
            process_trees_empty=processes_empty,
            guard_state=guard_states[0],
            handler_state=guard_states[1],
        )
