"""Two independent providers exercise the same non-executable observation boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.agents.workflows import BRIDGE_CHAT, builtin_workflow_registry, resolve_pinned_workflow
from lychd.domain.oculus.models import (
    ComponentDefinition,
    DeclaredRelation,
    ObservationCoverage,
    RuntimeActivity,
    SourceSnapshot,
)
from lychd.domain.oculus.runtime import RuntimeCatalogue, SourceRead
from lychd.domain.weaver.inspection import PatternInspectionDescriptor


def descriptor(name: str) -> PatternInspectionDescriptor:
    workflow = replace(BRIDGE_CHAT, name=name, manifest=replace(BRIDGE_CHAT.manifest, key=name))
    return PatternInspectionDescriptor.from_workflow(workflow)


def source(name: str, *, generation: str = "g1", activity_count: int = 2) -> SourceSnapshot:
    now = datetime.now(UTC)
    return SourceSnapshot(
        source_id=name,
        generation=generation,
        profile_id=f"{name}.profile",
        profile_revision="1",
        generated_at=now,
        components=(
            ComponentDefinition(key="edge", label=f"{name} service", kind="service", activity_coverage="partial"),
            ComponentDefinition(key="resource", label="Declared resource", kind="resource"),
            ComponentDefinition(key="endpoint", label="External endpoint", kind="external"),
        ),
        relations=(DeclaredRelation(key="attachment", source="edge", target="endpoint", relation="attached"),),
        activities=tuple(
            RuntimeActivity(
                event_id=f"event-{seq}",
                operation_id="operation-1",
                attempt_id=f"attempt-{seq}",
                seq=seq,
                observed_at=now,
                received_at=now,
                producer_id="edge",
                source="edge",
                target="endpoint",
                operation="fetch",
                kind="transport_attempt",
                phase="started",
                run_id="already-finished-run" if seq == 2 else None,
            )
            for seq in range(1, activity_count + 1)
        ),
        patterns=(descriptor(f"{name}.pattern"),),
        coverage=ObservationCoverage(first_seq=1 if activity_count else None, last_seq=activity_count or None),
    )


@dataclass
class Reader:
    sources: tuple[SourceRead, ...]

    def read(self) -> tuple[SourceRead, ...]:
        return self.sources


def test_two_providers_are_visible_without_executable_admission() -> None:
    workflows = builtin_workflow_registry()
    before = workflows.default
    reach, other = source("reach"), source("weather")
    catalogue = RuntimeCatalogue(
        reader=Reader(
            (
                SourceRead("reach", "builtin:reach", reach),
                SourceRead("weather", "crypt:weather", other),
            )
        )
    )

    snapshot = catalogue.snapshot(workflows)

    assert {item.source_id for item in snapshot.sources} == {"native", "reach", "weather"}
    assert {item.source_id for item in snapshot.components if item.kind == "resource"} == {"reach", "weather"}
    assert all(item.activity_coverage == "unavailable" for item in snapshot.components if item.kind == "resource")
    assert len(snapshot.activities) == 4
    assert sum(item.run_id is None for item in snapshot.activities) == 2
    assert sum(item.run_id == "already-finished-run" for item in snapshot.activities) == 2
    entries = [item for item in snapshot.patterns if not item.binding.executable]
    assert {entry.binding.source_id for entry in entries} == {"reach", "weather"}
    for entry in entries:
        assert entry.binding.publication == "observed"
        assert "generation=g1" in entry.detail_path
        assert workflows.get_revision(entry.descriptor.pattern_id, entry.descriptor.revision) is None
        assert (
            resolve_pinned_workflow(
                workflows, workflow_name=entry.descriptor.pattern_id, snapshot=entry.descriptor.manifest_snapshot()
            )
            is None
        )
    assert workflows.default is before
    assert workflows.route(Intent(session_id="fixture", prompt="ordinary question")) is before


def test_exact_projection_preserves_v2_manifest_and_mermaid() -> None:
    pure = PatternInspectionDescriptor.from_workflow(BRIDGE_CHAT)
    assert pure.manifest_snapshot() == BRIDGE_CHAT.manifest.snapshot()
    assert pure.mermaid() == BRIDGE_CHAT.mermaid()
    assert not hasattr(pure, "graph")
    assert not hasattr(pure, "route")
    assert not hasattr(pure, "make_state")


def test_stale_source_and_generation_replacement_remain_explicit() -> None:
    original = source("reach")
    reader = Reader((SourceRead("reach", "builtin:reach", original),))
    catalogue = RuntimeCatalogue(reader=reader)
    workflows = builtin_workflow_registry()
    first = catalogue.snapshot(workflows)
    assert first.sources[-1].generation_changed is False
    reader.sources = (SourceRead("reach", "builtin:reach", original, "stale"),)
    stale = catalogue.snapshot(workflows)
    assert stale.sources[-1].status == "stale"
    assert not stale.activities
    assert all(
        item.lifecycle == "unknown" and item.activity_coverage == "unavailable"
        for item in stale.components
        if item.source_id == "reach"
    )
    assert len([item for item in stale.components if item.source_id == "reach"]) == 3
    assert not any(entry.binding.source_id == "reach" for entry in stale.patterns)
    reader.sources = (SourceRead("reach", "builtin:reach", source("reach", generation="g2")),)
    changed = catalogue.snapshot(workflows)
    assert changed.sources[-1].generation_changed is True
    assert all(item.source_generation == "g2" for item in changed.activities)
    assert catalogue.snapshot(workflows).sources[-1].generation_changed is False


def test_conflicting_exact_scores_refuse_both_sources() -> None:
    first = source("reach")
    changed_descriptor = first.patterns[0].model_copy(update={"title": "Conflicting descriptor"})
    second = source("weather").model_copy(update={"patterns": (changed_descriptor,)})
    snapshot = RuntimeCatalogue(
        reader=Reader(
            (
                SourceRead("reach", "builtin:reach", first),
                SourceRead("weather", "crypt:weather", second),
            )
        )
    ).snapshot(builtin_workflow_registry())
    assert [item.status for item in snapshot.sources[1:]] == ["conflict", "conflict"]
    assert not snapshot.activities
    assert all(entry.binding.executable for entry in snapshot.patterns)


def test_global_window_overflow_reports_omissions_without_dangling_references() -> None:
    reads = tuple(SourceRead(name, f"crypt:{name}", source(name, activity_count=256)) for name in ("reach", "weather"))
    snapshot = RuntimeCatalogue(reader=Reader(reads)).snapshot(builtin_workflow_registry())
    assert len(snapshot.activities) == 256
    assert snapshot.coverage.omitted_activities == 256
    assert snapshot.sources[1].coverage.last_seq == 256
    keys = {(item.source_id, item.source_generation, item.key) for item in snapshot.components}
    assert all((item.source_id, item.source_generation, item.target) in keys for item in snapshot.activities)


def test_conflicting_score_refuses_all_equal_copies_without_an_order_based_winner() -> None:
    original = source("reach")
    copied = source("weather").model_copy(update={"patterns": original.patterns})
    conflicting = source("calendar").model_copy(
        update={
            "patterns": (original.patterns[0].model_copy(update={"title": "Conflict"}),),
        }
    )
    snapshot = RuntimeCatalogue(
        reader=Reader(
            tuple(
                SourceRead(item.source_id, f"operator:{item.source_id}", item)
                for item in (original, copied, conflicting)
            )
        )
    ).snapshot(builtin_workflow_registry())
    assert [item.status for item in snapshot.sources[1:]] == ["conflict", "conflict", "conflict"]
    assert not snapshot.activities


def test_duplicate_and_forged_records_fail_closed() -> None:
    snapshot = source("reach")
    raw = snapshot.model_dump(mode="json")
    raw["registrant_id"] = "core"
    with pytest.raises(ValidationError, match="Extra inputs"):
        SourceSnapshot.model_validate_json(json.dumps(raw))
    raw.pop("registrant_id")
    raw["activities"][0]["target"] = "unknown"
    with pytest.raises(ValidationError, match="known producer"):
        SourceSnapshot.model_validate_json(json.dumps(raw))
    with pytest.raises(ValidationError):
        SourceSnapshot.model_validate(
            {**snapshot.model_dump(), "activities": (snapshot.activities[0], snapshot.activities[0])}
        )
    with pytest.raises(ValidationError):
        ComponentDefinition(key="endpoint", label="https://private.example/token", kind="external")
    with pytest.raises(ValidationError):
        RuntimeActivity.model_validate({**snapshot.activities[0].model_dump(), "effect_outcome": "succeeded"})


def test_gaps_and_missing_finish_preserve_unknown_capture() -> None:
    snapshot = source("reach", activity_count=3)
    snapshot = snapshot.model_copy(update={"activities": (snapshot.activities[0], snapshot.activities[2])})
    result = RuntimeCatalogue(reader=Reader((SourceRead("reach", "builtin:reach", snapshot),))).snapshot(
        builtin_workflow_registry(),
    )
    assert result.sources[-1].coverage.gaps == 1
    assert result.sources[-1].coverage.completeness == "not_established"
    assert all(item.phase == "started" and item.effect_outcome is None for item in result.activities)


@pytest.mark.parametrize("field", ["seq", "producer_seq"])
def test_activity_sequences_refuse_browser_integer_rounding(field: str) -> None:
    activity = source("reach").activities[0]
    values = activity.model_dump()
    values[field] = 2**53
    if field == "producer_seq":
        values["producer_generation"] = "child-1"
    with pytest.raises(ValidationError, match="less than or equal"):
        RuntimeActivity(**values)


@pytest.mark.parametrize(
    "field", ["dropped", "gaps", "omitted_components", "omitted_relations", "omitted_activities", "omitted_patterns"]
)
def test_coverage_counters_refuse_browser_integer_rounding(field: str) -> None:
    with pytest.raises(ValidationError, match="less than or equal"):
        ObservationCoverage.model_validate({field: 2**53})


def test_loaded_sequence_bounds_refuse_browser_integer_rounding() -> None:
    with pytest.raises(ValidationError, match="less than or equal"):
        ObservationCoverage(first_seq=2**53, last_seq=2**53)
