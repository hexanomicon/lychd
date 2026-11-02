"""Bounded read projection of explicitly selected, host-attributed observations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlencode
from uuid import uuid4

from lychd.domain.oculus.models import (
    MAX_ACTIVITIES,
    MAX_COMPONENTS,
    MAX_PATTERNS,
    MAX_RELATIONS,
    MAX_SOURCES,
    ObservationCoverage,
    ObservedActivity,
    OrbRuntimeSnapshot,
    RuntimeComponent,
    RuntimeCoverage,
    RuntimeRelation,
    RuntimeSource,
    SourceFailure,
    SourceSnapshot,
)
from lychd.domain.weaver.inspection import (
    InspectionBinding,
    PatternInspectionDescriptor,
    PatternInspectionEntry,
)

if TYPE_CHECKING:
    from lychd.agents.workflows import WorkflowRegistry


@dataclass(frozen=True, slots=True)
class SourceRead:
    """One selected custody read; failure text and private paths are never exported."""

    source_id: str
    registrant_id: str
    snapshot: SourceSnapshot | None = None
    failure: SourceFailure | None = None

    def __post_init__(self) -> None:
        """Require an exact selected identity for every successful custody read."""
        if self.failure is None and self.snapshot is None:
            msg = "A successful source read requires its validated snapshot."
            raise ValueError(msg)
        if self.snapshot is not None and self.snapshot.source_id != self.source_id:
            msg = "Source read identity does not match selected custody."
            raise ValueError(msg)


class ObservationReader(Protocol):
    """Physical readers return only explicitly selected, validated source windows."""

    def read(self) -> tuple[SourceRead, ...]: ...


@dataclass(frozen=True, slots=True)
class RegisteredObservation:
    """Host-bound immutable declaration contributed during extension assembly."""

    registrant_id: str
    snapshot: SourceSnapshot


@dataclass(frozen=True, slots=True)
class RegisteredInspection:
    """An inspection-only score; this record cannot satisfy a WorkflowRegistry."""

    registrant_id: str
    source_id: str
    generation: str
    profile_id: str
    profile_revision: str
    descriptor: PatternInspectionDescriptor


def inspection_entry(
    descriptor: PatternInspectionDescriptor,
    *,
    binding: InspectionBinding,
) -> PatternInspectionEntry:
    """Preserve exact selection in every remote detail link."""
    path = f"/loom/{descriptor.pattern_id}/{descriptor.revision}"
    if not binding.executable:
        path += "?" + urlencode(
            {
                "source_id": binding.source_id,
                "generation": binding.source_generation,
                "profile_id": binding.profile_id,
                "profile_revision": binding.profile_revision,
            }
        )
    return PatternInspectionEntry(descriptor=descriptor, binding=binding, detail_path=path)


def _conflicting_sources(
    reads: tuple[SourceRead, ...],
    inspections: tuple[RegisteredInspection, ...],
    native_patterns: list[PatternInspectionEntry],
) -> set[str]:
    """Quarantine all conflicting scores and source envelopes before projection."""
    source_ids = [read.source_id for read in reads]
    conflicts = {source_id for source_id in source_ids if source_ids.count(source_id) > 1 or source_id == "native"}
    groups: dict[tuple[str, str], list[tuple[PatternInspectionDescriptor, str]]] = {
        (entry.descriptor.pattern_id, entry.descriptor.revision): [(entry.descriptor, "native")]
        for entry in native_patterns
    }
    envelopes: dict[str, set[tuple[str, str, str, str]]] = {}
    for read in reads:
        if read.snapshot is None:
            continue
        snapshot = read.snapshot
        envelopes.setdefault(read.source_id, set()).add(
            (read.registrant_id, snapshot.generation, snapshot.profile_id, snapshot.profile_revision)
        )
        for descriptor in snapshot.patterns:
            groups.setdefault((descriptor.pattern_id, descriptor.revision), []).append((descriptor, read.source_id))
    for item in inspections:
        envelopes.setdefault(item.source_id, set()).add(
            (item.registrant_id, item.generation, item.profile_id, item.profile_revision)
        )
        groups.setdefault((item.descriptor.pattern_id, item.descriptor.revision), []).append(
            (item.descriptor, item.source_id)
        )
    conflicts.update(
        source_id for source_id, bindings in envelopes.items() if len(bindings) > 1 or source_id == "native"
    )
    for contributions in groups.values():
        first = contributions[0][0]
        if any(descriptor != first for descriptor, _source in contributions):
            conflicts.update(source for _descriptor, source in contributions if source != "native")
    return conflicts


def _inspection_entries(
    inspections: tuple[RegisteredInspection, ...],
    *,
    allowed_sources: set[str],
) -> tuple[list[RuntimeSource], list[PatternInspectionEntry]]:
    """Project only conflict-checked inspection bindings; never resolve executable code."""
    sources: dict[str, RuntimeSource] = {}
    patterns: list[PatternInspectionEntry] = []
    for item in inspections:
        if item.source_id not in allowed_sources:
            continue
        sources[item.source_id] = RuntimeSource(
            source_id=item.source_id,
            registrant_id=item.registrant_id,
            generation=item.generation,
            profile_id=item.profile_id,
            profile_revision=item.profile_revision,
            status="current",
            coverage=ObservationCoverage(limitations=("inspection-only",)),
        )
        binding = InspectionBinding(
            source_id=item.source_id,
            registrant_id=item.registrant_id,
            source_generation=item.generation,
            profile_id=item.profile_id,
            profile_revision=item.profile_revision,
            publication="observed",
        )
        patterns.append(inspection_entry(item.descriptor, binding=binding))
    return list(sources.values()), patterns


class RuntimeCatalogue:
    """Finite observation window, separately assembled from executable authority."""

    def __init__(
        self,
        *,
        reader: ObservationReader | None = None,
        observations: tuple[RegisteredObservation, ...] = (),
        inspections: tuple[RegisteredInspection, ...] = (),
        native_components: Callable[[], tuple[RuntimeComponent, ...]] | None = None,
    ) -> None:
        """Keep one process generation and a bounded last-generation receipt."""
        self._reader = reader
        self._observations = observations
        self._inspections = inspections
        self._native_components = native_components
        self.generation = uuid4().hex
        self._last_generations: dict[str, str] = {}
        self._lock = Lock()

    def snapshot(self, workflows: WorkflowRegistry) -> OrbRuntimeSnapshot:
        """Read native declarations and selected windows without probing endpoints."""
        with self._lock:
            return self._snapshot(workflows)

    def _snapshot(self, workflows: WorkflowRegistry) -> OrbRuntimeSnapshot:
        now = datetime.now(UTC)
        native_binding = InspectionBinding(
            source_id="native",
            registrant_id="core",
            source_generation=self.generation,
            profile_id="vessel",
            profile_revision="1",
            publication="published",
            executable=True,
        )
        patterns = [
            inspection_entry(PatternInspectionDescriptor.from_workflow(workflow), binding=native_binding)
            for workflow in workflows.all()
        ]
        components = list(self._native_components() if self._native_components is not None else ())
        components = [component.model_copy(update={"source_generation": self.generation}) for component in components]
        if not components:
            components = [
                RuntimeComponent(
                    key="vessel",
                    label="Vessel",
                    kind="host",
                    owner="core",
                    source_id="native",
                    source_generation=self.generation,
                    registrant_id="core",
                )
            ]
        sources = [
            RuntimeSource(
                source_id="native",
                registrant_id="core",
                generation=self.generation,
                profile_id="vessel",
                profile_revision="1",
                generated_at=now,
                status="current",
                coverage=ObservationCoverage(limitations=("activity-not-instrumented",)),
            )
        ]
        relations: list[RuntimeRelation] = [
            RuntimeRelation(
                key=f"hosted:{index}",
                source="vessel",
                target=component.key,
                relation="hosted",
                source_id="native",
                source_generation=self.generation,
            )
            for index, component in enumerate(components)
            if component.key != "vessel"
        ]
        activities: list[ObservedActivity] = []
        reads = tuple(
            SourceRead(source_id=item.snapshot.source_id, registrant_id=item.registrant_id, snapshot=item.snapshot)
            for item in self._observations
        )
        if self._reader is not None:
            reads += self._reader.read()
        source_ids = tuple(
            dict.fromkeys(
                source_id
                for source_id in (*[read.source_id for read in reads], *[item.source_id for item in self._inspections])
                if source_id != "native"
            )
        )
        selected_sources = set(source_ids[:MAX_SOURCES])
        conflicts = _conflicting_sources(reads, self._inspections, patterns)
        sources.extend(
            RuntimeSource(
                source_id=source_id,
                registrant_id=None,
                status="conflict",
                coverage=ObservationCoverage(limitations=("source-conflict",)),
            )
            for source_id in source_ids[:MAX_SOURCES]
            if source_id in conflicts
        )
        for read in reads:
            if read.source_id not in selected_sources or read.source_id in conflicts:
                continue
            failure = read.failure
            snapshot = read.snapshot
            changed = (
                snapshot is not None
                and self._last_generations.get(read.source_id, snapshot.generation) != snapshot.generation
            )
            source_coverage = (
                snapshot.coverage if snapshot else ObservationCoverage(limitations=("source-unavailable",))
            )
            if snapshot is not None:
                gaps = sum(
                    right.seq - left.seq - 1
                    for left, right in zip(snapshot.activities, snapshot.activities[1:], strict=False)
                )
                source_coverage = source_coverage.model_copy(update={"gaps": max(gaps, source_coverage.gaps)})
            sources.append(
                RuntimeSource(
                    source_id=read.source_id,
                    registrant_id=read.registrant_id,
                    generation=snapshot.generation if snapshot else None,
                    profile_id=snapshot.profile_id if snapshot else None,
                    profile_revision=snapshot.profile_revision if snapshot else None,
                    generated_at=snapshot.generated_at if snapshot else None,
                    status=failure or "current",
                    generation_changed=changed,
                    coverage=source_coverage,
                )
            )
            if failure == "stale" and snapshot is not None:
                # Dated declarations remain visible, without implying a live instance,
                # current transport activity or an inspectable current profile.
                components.extend(
                    RuntimeComponent.model_validate(
                        {
                            **component.model_dump(),
                            "lifecycle": "unknown",
                            "activity_coverage": "unavailable",
                            "source_id": read.source_id,
                            "source_generation": snapshot.generation,
                            "registrant_id": read.registrant_id,
                        }
                    )
                    for component in snapshot.components
                )
                relations.extend(
                    RuntimeRelation(
                        **relation.model_dump(), source_id=read.source_id, source_generation=snapshot.generation
                    )
                    for relation in snapshot.relations
                )
            if failure is not None or snapshot is None:
                continue
            self._last_generations[read.source_id] = snapshot.generation
            components.extend(
                RuntimeComponent(
                    **component.model_dump(),
                    source_id=read.source_id,
                    source_generation=snapshot.generation,
                    registrant_id=read.registrant_id,
                )
                for component in snapshot.components
            )
            relations.extend(
                RuntimeRelation(
                    **relation.model_dump(), source_id=read.source_id, source_generation=snapshot.generation
                )
                for relation in snapshot.relations
            )
            activities.extend(
                ObservedActivity(
                    **activity.model_dump(),
                    source_id=read.source_id,
                    source_generation=snapshot.generation,
                    registrant_id=read.registrant_id,
                )
                for activity in snapshot.activities
            )
            binding = InspectionBinding(
                source_id=read.source_id,
                registrant_id=read.registrant_id,
                source_generation=snapshot.generation,
                profile_id=snapshot.profile_id,
                profile_revision=snapshot.profile_revision,
                publication="observed",
            )
            patterns.extend(inspection_entry(descriptor, binding=binding) for descriptor in snapshot.patterns)
        inspection_sources, inspection_patterns = _inspection_entries(
            self._inspections,
            allowed_sources=selected_sources
            - conflicts
            - {read.source_id for read in reads if read.failure is not None},
        )
        present_sources = {source.source_id for source in sources}
        sources.extend(source for source in inspection_sources if source.source_id not in present_sources)
        patterns.extend(inspection_patterns)
        # Preflight proved equal descriptors and provenance for each exact link.
        patterns = list({entry.detail_path: entry for entry in patterns}.values())
        selected_components = components[:MAX_COMPONENTS]
        keys = {(component.source_id, component.source_generation, component.key) for component in selected_components}
        closed_relations = [
            relation
            for relation in relations
            if (relation.source_id, relation.source_generation, relation.source) in keys
            and (relation.source_id, relation.source_generation, relation.target) in keys
        ]
        closed_activities = [
            activity
            for activity in activities
            if all(
                (activity.source_id, activity.source_generation, key) in keys
                for key in (activity.producer_id, activity.source, activity.target)
            )
        ]
        return OrbRuntimeSnapshot(
            read_at=now,
            sources=tuple(sources),
            components=tuple(selected_components),
            relations=tuple(closed_relations[:MAX_RELATIONS]),
            activities=tuple(closed_activities[-MAX_ACTIVITIES:]),
            patterns=tuple(patterns[:MAX_PATTERNS]),
            coverage=RuntimeCoverage(
                omitted_sources=max(0, len(source_ids) - MAX_SOURCES),
                omitted_components=max(0, len(components) - len(selected_components)),
                omitted_relations=len(relations) - min(len(closed_relations), MAX_RELATIONS),
                omitted_activities=len(activities) - min(len(closed_activities), MAX_ACTIVITIES),
                omitted_patterns=max(0, len(patterns) - MAX_PATTERNS),
            ),
        )
