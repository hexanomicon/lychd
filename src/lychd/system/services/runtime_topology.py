"""Attest the loaded systemd graph against declared Animator topology."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from lychd.domain.animation.conflicts import (
    ConflictTopology,
    ConflictTopologyError,
    build_conflict_topology,
)
from lychd.domain.orchestration.actuator import RuntimePreconditionError, TransitionIntent
from lychd.system.services.systemctl_process import (
    SystemctlClientTimeoutError,
    communicate_systemctl_client,
    validate_systemctl_timeout,
)
from lychd.system.unit_names import (
    animator_service_unit,
    animator_target_unit,
    coven_target_unit,
)

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Callable, Iterable, Mapping

    from lychd.domain.animation.protocols import CapabilityRegistry
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.system.services.scribe import OwnedBindings

__all__ = ["RuntimeTopologyAttestor"]

_LYCHD_POD_SERVICE: Final = "lychd-pod.service"
_SHOW_PROPERTIES: Final = (
    "Id",
    "LoadState",
    "NeedDaemonReload",
    "Wants",
    "Requires",
    "Before",
    "After",
    "Conflicts",
    "ConflictedBy",
    "PartOf",
    "BindsTo",
    "RequiredBy",
    "BoundBy",
    "DropInPaths",
    "FragmentPath",
    "SourcePath",
    "UnitFileState",
)


@dataclass(frozen=True, slots=True)
class _UnitSnapshot:
    """Relevant loaded-unit properties returned by ``systemctl show``."""

    unit_name: str
    load_state: str
    need_daemon_reload: bool
    wants: frozenset[str]
    requires: frozenset[str]
    before: frozenset[str]
    after: frozenset[str]
    conflicts: frozenset[str]
    conflicted_by: frozenset[str]
    part_of: frozenset[str]
    binds_to: frozenset[str]
    required_by: frozenset[str]
    bound_by: frozenset[str]
    drop_in_paths: frozenset[str]
    fragment_path: str
    source_path: str
    unit_file_state: str

    @classmethod
    def parse(cls, expected_unit: str, payload: bytes) -> _UnitSnapshot:
        """Parse one bounded ``systemctl show`` response and reject ambiguity."""
        properties: dict[str, str] = {}
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            msg = f"Loaded systemd graph for {expected_unit} was not valid UTF-8."
            raise RuntimePreconditionError(msg) from exc
        for raw_line in text.splitlines():
            if not raw_line:
                continue
            key, separator, value = raw_line.partition("=")
            if not separator or key in properties:
                msg = f"Loaded systemd graph for {expected_unit} returned malformed property data."
                raise RuntimePreconditionError(msg)
            properties[key] = value

        missing = sorted(set(_SHOW_PROPERTIES) - properties.keys())
        if missing:
            msg = f"Loaded systemd graph for {expected_unit} omitted properties: {', '.join(missing)}."
            raise RuntimePreconditionError(msg)
        if properties["Id"] != expected_unit:
            msg = f"Loaded systemd graph resolved {expected_unit} as unexpected unit {properties['Id']!r}."
            raise RuntimePreconditionError(msg)
        reload_value = properties["NeedDaemonReload"]
        if reload_value not in {"yes", "no"}:
            msg = f"Loaded systemd graph for {expected_unit} returned invalid NeedDaemonReload={reload_value!r}."
            raise RuntimePreconditionError(msg)

        def units(property_name: str) -> frozenset[str]:
            return frozenset(properties[property_name].split())

        return cls(
            unit_name=expected_unit,
            load_state=properties["LoadState"],
            need_daemon_reload=reload_value == "yes",
            wants=units("Wants"),
            requires=units("Requires"),
            before=units("Before"),
            after=units("After"),
            conflicts=units("Conflicts"),
            conflicted_by=units("ConflictedBy"),
            part_of=units("PartOf"),
            binds_to=units("BindsTo"),
            required_by=units("RequiredBy"),
            bound_by=units("BoundBy"),
            drop_in_paths=units("DropInPaths"),
            fragment_path=properties["FragmentPath"],
            source_path=properties["SourcePath"],
            unit_file_state=properties["UnitFileState"],
        )


@dataclass(frozen=True, slots=True)
class _ExpectedGraph:
    """Pure expected unit graph compiled from current Soulstone declarations."""

    runes_by_name: dict[str, SoulstoneConfig]
    topology: ConflictTopology

    @property
    def coven_members(self) -> Mapping[str, tuple[str, ...]]:
        """Return the aggregate projection owned by the pure topology compiler."""
        return self.topology.coven_members

    @property
    def animator_targets(self) -> frozenset[str]:
        return frozenset(animator_target_unit(name) for name in self.runes_by_name)

    @property
    def animator_services(self) -> frozenset[str]:
        return frozenset(animator_service_unit(name) for name in self.runes_by_name)

    @property
    def coven_targets(self) -> frozenset[str]:
        return frozenset(coven_target_unit(name) for name in self.coven_members)

    @property
    def managed_units(self) -> frozenset[str]:
        return frozenset(
            {
                _LYCHD_POD_SERVICE,
                *self.animator_targets,
                *self.animator_services,
                *self.coven_targets,
            }
        )


class RuntimeTopologyAttestor:
    """Prove intent closure and the exact loaded target graph before effects."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        systemctl_bin: str,
        systemctl_timeout_s: float = 120.0,
        owned_bindings_provider: Callable[[], OwnedBindings] | None = None,
    ) -> None:
        """Bind to complete registry truth and an attested systemctl binary."""
        self._registry = registry
        self._systemctl = systemctl_bin
        self._systemctl_timeout_s = validate_systemctl_timeout(systemctl_timeout_s)
        self._owned_bindings_provider = owned_bindings_provider

    async def attest(self, intent: TransitionIntent) -> None:
        """Reject stale declarations, unsafe closures, or altered loaded units."""
        expected = self._compile_expected_graph()
        self._validate_intent(intent, expected)
        sources_by_unit = self._attest_binding_ownership(expected)
        await self._attest_loaded_target_set(expected)

        snapshots: dict[str, _UnitSnapshot] = {}
        for unit_name in sorted(expected.managed_units - {_LYCHD_POD_SERVICE}):
            snapshots[unit_name] = await self._show_unit(unit_name)

        for animator_name in sorted(expected.runes_by_name):
            self._attest_animator_target(
                animator_name,
                expected,
                snapshots,
                sources_by_unit=sources_by_unit,
            )
            self._attest_animator_service(
                animator_name,
                expected,
                snapshots,
                sources_by_unit=sources_by_unit,
            )
        for coven_name in sorted(expected.coven_members):
            self._attest_coven_target(
                coven_name,
                expected,
                snapshots,
                sources_by_unit=sources_by_unit,
            )

    def validate_intent(self, intent: TransitionIntent) -> None:
        """Validate declared conflict closure without querying systemd."""
        self._validate_intent(intent, self._compile_expected_graph())

    def _compile_expected_graph(self) -> _ExpectedGraph:
        try:
            runes = tuple(self._registry.list_soulstone_runes())
            topology = build_conflict_topology(runes)
        except (AttributeError, ConflictTopologyError, ValueError) as exc:
            msg = f"Cannot compile trusted runtime conflict topology: {exc}"
            raise RuntimePreconditionError(msg) from exc
        runes_by_name = {rune.name: rune for rune in runes}
        return _ExpectedGraph(
            runes_by_name=runes_by_name,
            topology=topology,
        )

    def _attest_binding_ownership(self, expected: _ExpectedGraph) -> dict[str, str]:
        """Bind loaded units to the exact Scribe receipt when production supplies it."""
        if self._owned_bindings_provider is None:
            return {}
        try:
            owned = self._owned_bindings_provider()
        except Exception as exc:
            msg = f"Cannot validate Scribe binding ownership before runtime actuation: {exc}"
            raise RuntimePreconditionError(msg) from exc
        if not owned.receipt_present or owned.generation is None:
            msg = "Cannot attest runtime topology without a validated Scribe ownership receipt."
            raise RuntimePreconditionError(msg)

        expected_targets = expected.animator_targets | expected.coven_targets
        owned_units = set(owned.runtime_units)
        missing = sorted((expected_targets | expected.animator_services) - owned_units)
        if missing:
            msg = f"Scribe ownership receipt omits runtime topology units: {', '.join(missing)}."
            raise RuntimePreconditionError(msg)
        owned_topology_targets = {
            unit
            for unit in owned_units
            if unit.startswith(("lychd-animator-", "lychd-coven-")) and unit.endswith(".target")
        }
        if owned_topology_targets != set(expected_targets):
            msg = (
                "Scribe ownership receipt has stale runtime topology targets: "
                f"expected {sorted(expected_targets)}, observed {sorted(owned_topology_targets)}."
            )
            raise RuntimePreconditionError(msg)

        from lychd.system.services.scribe.naming import runtime_unit_for_source

        sources_by_unit: dict[str, str] = {}
        for source in (*owned.quadlet_sources, *owned.systemd_sources):
            unit_name = runtime_unit_for_source(source.name)
            if unit_name in sources_by_unit:
                msg = f"Scribe ownership maps multiple sources to runtime unit {unit_name}."
                raise RuntimePreconditionError(msg)
            sources_by_unit[unit_name] = str(source)
        return sources_by_unit

    async def _attest_loaded_target_set(self, expected: _ExpectedGraph) -> None:
        """Reject stale installed or loaded targets absent from current Rune truth."""
        installed = await self._list_target_units("list-unit-files")
        loaded = await self._list_target_units("list-units")
        wanted = set(expected.animator_targets | expected.coven_targets)
        if installed != wanted or not loaded <= wanted:
            msg = (
                "Installed/loaded runtime target set differs from current Scribe/Rune truth: "
                f"expected {sorted(wanted)}, installed {sorted(installed)}, loaded {sorted(loaded)}."
            )
            raise RuntimePreconditionError(msg)

    async def _list_target_units(self, command: str) -> set[str]:
        """List one exact systemd target namespace through a bounded argv."""
        if command == "list-unit-files":
            arguments = ("--no-legend", "--no-pager")
        elif command == "list-units":
            arguments = ("--all", "--plain", "--no-legend", "--no-pager")
        else:  # pragma: no cover - internal literal invariant
            msg = f"Unsupported systemd target listing command: {command}"
            raise RuntimeError(msg)
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            command,
            *arguments,
            "lychd-animator-*.target",
            "lychd-coven-*.target",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await self._communicate(
            process,
            operation=f"systemctl {command}",
        )
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            msg = f"Cannot enumerate runtime targets; systemctl returned {process.returncode}{suffix}"
            raise RuntimePreconditionError(msg)
        return {
            columns[0]
            for raw_line in stdout.decode("utf-8", errors="replace").splitlines()
            if (columns := raw_line.split())
        }

    @staticmethod
    def _validate_intent(intent: TransitionIntent, expected: _ExpectedGraph) -> None:
        declared_names = set(expected.runes_by_name)
        referenced = {
            *intent.expected_active_animators,
            *intent.evict_animators,
            *intent.launch_animators,
        }
        unknown = sorted(referenced - declared_names)
        if unknown:
            msg = f"Transition '{intent.transition_id}' references undeclared local Animators: {', '.join(unknown)}."
            raise RuntimePreconditionError(msg)

        prior = set(intent.expected_active_animators)
        evicted = set(intent.evict_animators)
        launched = set(intent.launch_animators)
        desired = (prior - evicted) | launched
        RuntimeTopologyAttestor._require_compatible("expected", prior, expected, intent)
        RuntimeTopologyAttestor._require_compatible("launch", launched, expected, intent)
        RuntimeTopologyAttestor._require_compatible("desired", desired, expected, intent)

        # A fresh stop-only compensation is an exact inverse authorized by its
        # rollback receipt; it has no launch-side conflict closure to recompute.
        # Every forward/start-bearing request must still match current graph
        # neighbors exactly.
        active_conflict_closure: set[str] = set()
        if launched:
            active_conflict_closure = {
                neighbor
                for animator_name in launched
                for neighbor in expected.topology.neighbors_for(animator_name)
                if neighbor in prior
            }
        stop_only_inverse = intent.operation == "compensation" and not launched
        if not stop_only_inverse and active_conflict_closure != evicted:
            msg = (
                f"Transition '{intent.transition_id}' conflict closure is stale: "
                f"declared active neighbors {sorted(active_conflict_closure)}, "
                f"intent evictions {sorted(evicted)}."
            )
            raise RuntimePreconditionError(msg)

    @staticmethod
    def _require_compatible(
        label: str,
        animator_names: set[str],
        expected: _ExpectedGraph,
        intent: TransitionIntent,
    ) -> None:
        conflicting_pairs = [
            (lower, higher)
            for lower, higher in expected.topology.oriented_edges
            if lower in animator_names and higher in animator_names
        ]
        if conflicting_pairs:
            rendered = ", ".join(f"{lower}<->{higher}" for lower, higher in conflicting_pairs)
            msg = f"Transition '{intent.transition_id}' has incompatible {label} Animator set: {rendered}."
            raise RuntimePreconditionError(msg)

    async def _show_unit(self, unit_name: str) -> _UnitSnapshot:
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            "show",
            *(f"--property={property_name}" for property_name in _SHOW_PROPERTIES),
            unit_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await self._communicate(
            process,
            operation=f"systemctl show {unit_name}",
        )
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            msg = f"Cannot attest loaded systemd unit {unit_name}; systemctl returned {process.returncode}{suffix}"
            raise RuntimePreconditionError(msg)
        snapshot = _UnitSnapshot.parse(unit_name, stdout)
        if snapshot.load_state != "loaded":
            msg = f"Loaded systemd graph is not ready: {unit_name} has LoadState={snapshot.load_state!r}."
            raise RuntimePreconditionError(msg)
        if snapshot.need_daemon_reload:
            msg = f"Loaded systemd graph is stale: {unit_name} requires daemon-reload."
            raise RuntimePreconditionError(msg)
        if snapshot.drop_in_paths:
            msg = f"Loaded systemd graph for {unit_name} is altered by drop-ins: {sorted(snapshot.drop_in_paths)}."
            raise RuntimePreconditionError(msg)
        return snapshot

    async def _communicate(
        self,
        process: Process,
        *,
        operation: str,
    ) -> tuple[bytes, bytes]:
        """Bound a read-only client and preserve timeout as a no-effect decline."""
        try:
            return await communicate_systemctl_client(
                process,
                timeout_s=self._systemctl_timeout_s,
                operation=operation,
            )
        except SystemctlClientTimeoutError as exc:
            msg = f"Cannot attest loaded systemd graph: {exc}."
            raise RuntimePreconditionError(msg) from exc

    @staticmethod
    def _attest_animator_target(
        animator_name: str,
        expected: _ExpectedGraph,
        snapshots: dict[str, _UnitSnapshot],
        *,
        sources_by_unit: dict[str, str],
    ) -> None:
        unit_name = animator_target_unit(animator_name)
        snapshot = snapshots[unit_name]
        service_unit = animator_service_unit(animator_name)
        predecessors = {
            animator_target_unit(lower) for lower, higher in expected.topology.oriented_edges if higher == animator_name
        }
        covens = {
            coven_target_unit(group) for group, members in expected.coven_members.items() if animator_name in members
        }
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Requires",
            snapshot.requires,
            {service_unit},
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_source(
            snapshot,
            expected_source=sources_by_unit.get(unit_name),
            plain_target=True,
        )
        # Requires=service is forward from this target, so its reverse appears
        # on service.RequiredBy. Only service.BindsTo=target reverses onto this
        # target as BoundBy; target.RequiredBy must remain empty.
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "RequiredBy",
            snapshot.required_by,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "BoundBy",
            snapshot.bound_by,
            {service_unit},
            expected.managed_units,
        )
        # The loaded manager exposes target/service requirement and binding
        # inverses through RequiredBy=/BoundBy=. Ordering and conflict edges
        # remain observable on the canonical forward endpoint that declares
        # them: this target's own Before=service and, for the lexical higher
        # endpoint, After=/Conflicts=predecessors. Do not invent successor
        # edges on the lower target; requiring exact managed Before= and an
        # empty managed ConflictedBy= surface still rejects injected edges.
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Before",
            snapshot.before,
            {service_unit},
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "After",
            snapshot.after,
            predecessors,
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Conflicts",
            snapshot.conflicts,
            predecessors,
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "ConflictedBy",
            snapshot.conflicted_by,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "PartOf",
            snapshot.part_of,
            {_LYCHD_POD_SERVICE, *covens},
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Wants",
            snapshot.wants,
            set(),
            expected.managed_units,
        )

    @staticmethod
    def _attest_animator_service(
        animator_name: str,
        expected: _ExpectedGraph,
        snapshots: dict[str, _UnitSnapshot],
        *,
        sources_by_unit: dict[str, str],
    ) -> None:
        unit_name = animator_service_unit(animator_name)
        snapshot = snapshots[unit_name]
        target_unit = animator_target_unit(animator_name)
        animator_targets = expected.animator_targets
        if set(snapshot.binds_to & animator_targets) != {target_unit} or _LYCHD_POD_SERVICE not in snapshot.binds_to:
            msg = (
                f"Loaded systemd graph mismatch for {unit_name}.BindsTo: "
                f"expected pod plus exact target {target_unit}, observed {sorted(snapshot.binds_to)}."
            )
            raise RuntimePreconditionError(msg)
        if set(snapshot.after & animator_targets) != {target_unit} or _LYCHD_POD_SERVICE not in snapshot.after:
            msg = (
                f"Loaded systemd graph mismatch for {unit_name}.After: "
                f"expected pod plus exact target {target_unit}, observed {sorted(snapshot.after)}."
            )
            raise RuntimePreconditionError(msg)
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "RequiredBy",
            snapshot.required_by,
            {target_unit},
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "BoundBy",
            snapshot.bound_by,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Conflicts",
            snapshot.conflicts,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "ConflictedBy",
            snapshot.conflicted_by,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Before",
            snapshot.before,
            set(),
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_source(
            snapshot,
            expected_source=sources_by_unit.get(unit_name),
            plain_target=False,
        )

    @staticmethod
    def _attest_coven_target(
        coven_name: str,
        expected: _ExpectedGraph,
        snapshots: dict[str, _UnitSnapshot],
        *,
        sources_by_unit: dict[str, str],
    ) -> None:
        unit_name = coven_target_unit(coven_name)
        snapshot = snapshots[unit_name]
        members = {animator_target_unit(name) for name in expected.coven_members[coven_name]}
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "Wants",
            snapshot.wants,
            members,
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "After",
            snapshot.after,
            members,
            expected.managed_units,
        )
        RuntimeTopologyAttestor._require_relation(
            snapshot,
            "PartOf",
            snapshot.part_of,
            {_LYCHD_POD_SERVICE},
            expected.managed_units,
        )
        for property_name, observed in (
            ("Requires", snapshot.requires),
            ("Conflicts", snapshot.conflicts),
            ("ConflictedBy", snapshot.conflicted_by),
        ):
            RuntimeTopologyAttestor._require_relation(
                snapshot,
                property_name,
                observed,
                set(),
                expected.managed_units,
            )
        RuntimeTopologyAttestor._require_source(
            snapshot,
            expected_source=sources_by_unit.get(unit_name),
            plain_target=True,
        )

    @staticmethod
    def _require_relation(
        snapshot: _UnitSnapshot,
        property_name: str,
        observed: Iterable[str],
        expected_values: set[str],
        managed_units: frozenset[str],
    ) -> None:
        observed_managed = {
            unit_name for unit_name in observed if unit_name in managed_units or unit_name.startswith("lychd-")
        }
        if observed_managed != expected_values:
            msg = (
                f"Loaded systemd graph mismatch for {snapshot.unit_name}.{property_name}: "
                f"expected {sorted(expected_values)}, observed {sorted(observed_managed)}."
            )
            raise RuntimePreconditionError(msg)

    @staticmethod
    def _require_source(
        snapshot: _UnitSnapshot,
        *,
        expected_source: str | None,
        plain_target: bool,
    ) -> None:
        """Tie each loaded fragment to its exact receipt-owned source."""
        if expected_source is None:
            return
        if plain_target:
            if snapshot.fragment_path != expected_source or snapshot.unit_file_state != "static":
                msg = (
                    f"Loaded target source mismatch for {snapshot.unit_name}: "
                    f"FragmentPath={snapshot.fragment_path!r}, "
                    f"UnitFileState={snapshot.unit_file_state!r}, expected {expected_source!r} and 'static'."
                )
                raise RuntimePreconditionError(msg)
            return
        if (
            snapshot.source_path != expected_source
            or not snapshot.fragment_path
            or snapshot.fragment_path.rsplit("/", maxsplit=1)[-1] != snapshot.unit_name
            or snapshot.unit_file_state != "generated"
        ):
            msg = (
                f"Loaded Quadlet source mismatch for {snapshot.unit_name}: "
                f"SourcePath={snapshot.source_path!r}, FragmentPath={snapshot.fragment_path!r}, "
                f"UnitFileState={snapshot.unit_file_state!r}, expected source {expected_source!r}."
            )
            raise RuntimePreconditionError(msg)
