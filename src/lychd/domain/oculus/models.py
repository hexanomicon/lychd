"""Closed, bounded structural source snapshots and their host-attributed projection."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator

from lychd.domain.weaver.inspection import (
    InspectionIdentifier,
    InspectionValue,
    PatternInspectionDescriptor,
    PatternInspectionEntry,
)

MAX_SOURCES = 8
MAX_SNAPSHOT_BYTES = 1_048_576
MAX_COMPONENTS = 128
MAX_RELATIONS = 256
MAX_ACTIVITIES = 256
MAX_PATTERNS = 32
MAX_SAFE_INTEGER = 2**53 - 1

type SafeLabel = Annotated[str, StringConstraints(min_length=1, max_length=160, pattern=r"^[\w .,:()\-]+$")]
type SourceFailure = Literal["unavailable", "unsafe", "invalid", "stale", "generation_mismatch", "oversize", "conflict"]


class ComponentDefinition(InspectionValue):
    """A known component is visible even when no activity is instrumented."""

    key: InspectionIdentifier
    label: SafeLabel
    kind: Literal["host", "service", "runtime", "interface", "resource", "external", "capability", "extension", "other"]
    revision: InspectionIdentifier = "1"
    owner: InspectionIdentifier = "oculus"
    instance_id: InspectionIdentifier | None = None
    lifecycle: Literal["configured", "observed", "running", "stopped", "unknown"] = "configured"
    activity_coverage: Literal["unavailable", "partial", "instrumented"] = "unavailable"
    icon: Literal["component", "service", "runtime", "interface", "resource", "external", "capability"] = "component"
    icon_asset: str | None = Field(default=None, pattern=r"^icons/[a-z0-9][a-z0-9_-]{0,63}\.svg$")


class DeclaredRelation(InspectionValue):
    """Declared membership or attachment, never evidence of a transport attempt."""

    key: InspectionIdentifier
    source: InspectionIdentifier
    target: InspectionIdentifier
    relation: Literal["hosted", "attached", "implements", "serves", "references"]


class RuntimeActivity(InspectionValue):
    """One structural observation in a producer generation's local ordering domain."""

    event_id: InspectionIdentifier
    operation_id: InspectionIdentifier
    attempt_id: InspectionIdentifier | None = None
    seq: int = Field(ge=1, le=MAX_SAFE_INTEGER)
    observed_at: AwareDatetime
    received_at: AwareDatetime
    producer_id: InspectionIdentifier
    producer_seq: int | None = Field(default=None, ge=1, le=MAX_SAFE_INTEGER)
    producer_generation: InspectionIdentifier | None = None
    source: InspectionIdentifier
    target: InspectionIdentifier
    operation: InspectionIdentifier
    kind: Literal["transport_attempt", "transport_result", "operation_result", "lifecycle"]
    phase: Literal["started", "succeeded", "failed", "cancelled", "unknown"]
    capture: Literal["process_local"] = "process_local"
    http_status: int | None = Field(default=None, ge=100, le=599)
    error_category: (
        Literal["timeout", "cancelled", "transport", "protocol", "refused", "unavailable", "unknown"] | None
    ) = None
    elapsed_ms: float | None = Field(default=None, ge=0, le=86_400_000, allow_inf_nan=False)
    run_id: InspectionIdentifier | None = None
    station_attempt_id: InspectionIdentifier | None = None
    station_key: InspectionIdentifier | None = None
    step_id: InspectionIdentifier | None = None
    native_event_id: InspectionIdentifier | None = None
    native_seq: int | None = Field(default=None, ge=0, le=MAX_SAFE_INTEGER)
    request_id: InspectionIdentifier | None = None
    job_id: InspectionIdentifier | None = None
    receipt_id: InspectionIdentifier | None = None
    effect_outcome: Literal["succeeded", "failed", "unknown"] | None = None
    pattern_id: InspectionIdentifier | None = None
    pattern_revision: InspectionIdentifier | None = None

    @model_validator(mode="after")
    def distinct_evidence(self) -> RuntimeActivity:
        if (self.producer_seq is None) != (self.producer_generation is None):
            msg = "Relayed observations require both producer sequence and generation."
            raise ValueError(msg)
        if self.kind in {"transport_attempt", "transport_result"} and self.attempt_id is None:
            msg = "Transport observations require an attempt identity."
            raise ValueError(msg)
        if self.kind == "transport_attempt" and self.phase != "started":
            msg = "Transport attempts describe the actual dispatch boundary."
            raise ValueError(msg)
        if self.kind != "operation_result" and self.effect_outcome is not None:
            msg = "Transport observations cannot settle an effect."
            raise ValueError(msg)
        if (self.pattern_id is None) != (self.pattern_revision is None):
            msg = "Pattern correlation requires an exact identity and revision."
            raise ValueError(msg)
        return self


class ObservationCoverage(InspectionValue):
    """A finite replaceable process window; completeness is never inferred."""

    capture: Literal["process_local"] = "process_local"
    completeness: Literal["not_established"] = "not_established"
    first_seq: int | None = Field(default=None, ge=1, le=MAX_SAFE_INTEGER)
    last_seq: int | None = Field(default=None, ge=1, le=MAX_SAFE_INTEGER)
    dropped: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    gaps: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_components: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_relations: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_activities: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_patterns: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    limitations: tuple[InspectionIdentifier, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def ordered_bounds(self) -> ObservationCoverage:
        if (self.first_seq is None) != (self.last_seq is None) or (
            self.first_seq is not None and self.last_seq is not None and self.first_seq > self.last_seq
        ):
            msg = "Observation bounds require one ordered sequence interval."
            raise ValueError(msg)
        return self


class SourceSnapshot(InspectionValue):
    """Unattributed wire snapshot; only a selected custody reader binds provenance."""

    schema_version: Literal[1] = 1
    source_id: InspectionIdentifier
    generation: InspectionIdentifier
    profile_id: InspectionIdentifier
    profile_revision: InspectionIdentifier
    generated_at: AwareDatetime
    components: tuple[ComponentDefinition, ...] = Field(max_length=MAX_COMPONENTS)
    relations: tuple[DeclaredRelation, ...] = Field(default=(), max_length=MAX_RELATIONS)
    activities: tuple[RuntimeActivity, ...] = Field(default=(), max_length=MAX_ACTIVITIES)
    patterns: tuple[PatternInspectionDescriptor, ...] = Field(default=(), max_length=MAX_PATTERNS)
    coverage: ObservationCoverage = Field(default_factory=ObservationCoverage)

    @model_validator(mode="after")
    def closed_references(self) -> SourceSnapshot:
        keys = {component.key for component in self.components}
        unique_groups = (
            tuple(component.key for component in self.components),
            tuple(relation.key for relation in self.relations),
            tuple(activity.event_id for activity in self.activities),
            tuple(activity.seq for activity in self.activities),
            tuple((pattern.pattern_id, pattern.revision) for pattern in self.patterns),
        )
        if any(len(group) != len(set(group)) for group in unique_groups):
            msg = "Snapshot identities and source sequences must be unique."
            raise ValueError(msg)
        if any(relation.source not in keys or relation.target not in keys for relation in self.relations):
            msg = "Declared relations require known component endpoints."
            raise ValueError(msg)
        for activity in self.activities:
            if {activity.source, activity.target, activity.producer_id} - keys:
                msg = "Activity requires known producer and component endpoints."
                raise ValueError(msg)
            if (
                activity.pattern_id is not None
                and (activity.pattern_id, activity.pattern_revision) not in unique_groups[-1]
            ):
                msg = "Activity Pattern correlation must resolve in the exact source profile."
                raise ValueError(msg)
        seqs = [activity.seq for activity in self.activities]
        if seqs and (
            seqs != sorted(seqs) or self.coverage.first_seq != min(seqs) or self.coverage.last_seq != max(seqs)
        ):
            msg = "Snapshot activity must be ordered and report its loaded sequence bounds."
            raise ValueError(msg)
        return self


class ObservationSourceSelection(InspectionValue):
    """Host-owned identity; a payload cannot claim Core or another Registrant."""

    source_id: InspectionIdentifier
    registrant_id: str = Field(pattern=r"^(builtin|crypt|operator):[A-Za-z0-9][A-Za-z0-9._:/-]*$", max_length=160)
    expected_generation: InspectionIdentifier | None = None
    max_age_seconds: int = Field(default=30, ge=1, le=3600)

    @field_validator("source_id")
    @classmethod
    def external_source_identity(cls, value: str) -> str:
        """Reserve the native source identity for the process assembly owner."""
        if value == "native":
            msg = "The native observation source identity is reserved."
            raise ValueError(msg)
        return value


class RuntimeSource(InspectionValue):
    source_id: InspectionIdentifier
    registrant_id: str | None
    generation: InspectionIdentifier | None = None
    profile_id: InspectionIdentifier | None = None
    profile_revision: InspectionIdentifier | None = None
    generated_at: AwareDatetime | None = None
    status: Literal[
        "current", "unavailable", "unsafe", "invalid", "stale", "generation_mismatch", "oversize", "conflict"
    ]
    generation_changed: bool = False
    coverage: ObservationCoverage


class RuntimeComponent(ComponentDefinition):
    source_id: InspectionIdentifier
    source_generation: InspectionIdentifier
    registrant_id: str | None


class RuntimeRelation(DeclaredRelation):
    source_id: InspectionIdentifier
    source_generation: InspectionIdentifier


class ObservedActivity(RuntimeActivity):
    source_id: InspectionIdentifier
    source_generation: InspectionIdentifier
    registrant_id: str


class RuntimeCoverage(InspectionValue):
    source_limit: Literal[9] = 9
    selected_source_limit: Literal[8] = 8
    component_limit: Literal[128] = 128
    relation_limit: Literal[256] = 256
    activity_limit: Literal[256] = 256
    pattern_limit: Literal[32] = 32
    omitted_sources: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_components: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_relations: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_activities: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)
    omitted_patterns: int = Field(default=0, ge=0, le=MAX_SAFE_INTEGER)


class OrbRuntimeSnapshot(InspectionValue):
    schema_version: Literal[1] = 1
    read_at: AwareDatetime
    sources: tuple[RuntimeSource, ...]
    components: tuple[RuntimeComponent, ...]
    relations: tuple[RuntimeRelation, ...]
    activities: tuple[ObservedActivity, ...]
    patterns: tuple[PatternInspectionEntry, ...]
    coverage: RuntimeCoverage
