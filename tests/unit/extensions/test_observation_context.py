"""Observation and inspection contributions are host-bound, sealed and non-executable."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lychd.agents.workflows import builtin_workflow_registry
from lychd.config.settings.observability import ObservabilitySettings, SnapshotSourceSettings
from lychd.domain.oculus.models import SourceSnapshot
from lychd.domain.oculus.runtime import RuntimeCatalogue
from lychd.domain.weaver.inspection import InspectionContribution
from lychd.extensions.context import ExtensionContext
from lychd.extensions.host import AssembledExtensions
from tests.unit.domain.oculus.test_runtime import source


def test_retained_facades_keep_provenance_and_freeze_both_stores() -> None:
    root = ExtensionContext()
    reach = root.registration_view("builtin:reach")
    weather = root.registration_view("crypt:weather")
    reach_source = source("reach", activity_count=0)
    weather_source = source("weather", activity_count=0)
    reach.observations.add(reach_source)
    weather.observations.add(weather_source)
    reach.inspections.add(
        InspectionContribution(
            source_id="reach-inspection", profile_id="reach", profile_revision="1", descriptor=reach_source.patterns[0]
        )
    )
    assembly = AssembledExtensions(root)
    assert [item.registrant_id for item in assembly.observation_registrations] == ["builtin:reach", "crypt:weather"]
    assert assembly.inspection_registrations[0].registrant_id == "builtin:reach"
    assert assembly.observation_registrations[0].snapshot.generation != reach_source.generation
    assert not hasattr(reach, "provenance")
    for facade in (reach, weather):
        with pytest.raises(RuntimeError, match="frozen"):
            facade.observations.add(reach_source)
        with pytest.raises(RuntimeError, match="frozen"):
            facade.inspections.add(
                InspectionContribution(
                    source_id="other", profile_id="other", profile_revision="1", descriptor=reach_source.patterns[0]
                )
            )
    snapshot = RuntimeCatalogue(observations=assembly.observation_registrations).snapshot(builtin_workflow_registry())
    assert {item.registrant_id for item in snapshot.components if item.source_id != "native"} == {
        "builtin:reach",
        "crypt:weather",
    }


def test_registration_refuses_foreign_replay_activity_and_claimed_running_state() -> None:
    context = ExtensionContext()
    one, two = context.registration_view("builtin:one"), context.registration_view("crypt:two")
    declaration = source("test", activity_count=0)
    one.observations.add(declaration)
    with pytest.raises(ValueError, match="already registered"):
        two.observations.add(declaration)
    with pytest.raises(ValueError, match="declarations only"):
        two.observations.add(source("runtime"))
    running = declaration.model_copy(
        update={
            "source_id": "running",
            "components": (
                declaration.components[0].model_copy(update={"lifecycle": "running"}),
                *declaration.components[1:],
            ),
        }
    )
    with pytest.raises(ValueError, match="declarations only"):
        two.observations.add(running)


def test_selected_source_config_is_explicit_bounded_and_cannot_claim_core(tmp_path: Path) -> None:
    assert (
        SnapshotSourceSettings(source_id="reach", registrant_id="operator:reach", path=tmp_path).registrant_id
        == "operator:reach"
    )
    assert (
        SnapshotSourceSettings.model_validate(
            {
                "source_id": "reach",
                "registrant_id": "operator:reach",
                "path": str(tmp_path),
            }
        ).path
        == tmp_path
    )
    with pytest.raises(ValidationError):
        SnapshotSourceSettings(source_id="reach", registrant_id="core", path=tmp_path)
    with pytest.raises(ValidationError, match="reserved"):
        SnapshotSourceSettings(source_id="native", registrant_id="operator:reach", path=tmp_path)
    with pytest.raises(ValidationError):
        SnapshotSourceSettings.model_validate(
            {"source_id": "reach", "registrant_id": "builtin:reach", "path": "relative"}
        )
    sources = tuple(
        SnapshotSourceSettings(source_id=f"source-{index}", registrant_id="crypt:fixture", path=tmp_path / str(index))
        for index in range(9)
    )
    with pytest.raises(ValidationError):
        ObservabilitySettings(sources=sources)
    with pytest.raises(ValidationError):
        ObservabilitySettings(sources=(sources[0], sources[0]))


def test_unknown_source_schema_and_descriptor_checksum_are_refused() -> None:
    snapshot = source("reach", activity_count=0)
    with pytest.raises(ValidationError):
        SourceSnapshot.model_validate_json(
            snapshot.model_dump_json().replace('"schema_version":1', '"schema_version":999', 1)
        )
    altered = snapshot.patterns[0].model_copy(update={"digest": "0" * 64})
    context = ExtensionContext().registration_view("crypt:fixture")
    with pytest.raises(ValidationError, match="semantic digest"):
        context.inspections.add(
            InspectionContribution(source_id="test", profile_id="test", profile_revision="1", descriptor=altered)
        )
