"""The same generic HTTP catalogue serves unrelated selected observation providers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import pytest

from lychd.agents.workflows import BRIDGE_CHAT
from lychd.domain.oculus.runtime import RegisteredInspection, RegisteredObservation, RuntimeCatalogue, SourceRead
from lychd.domain.weaver.inspection import InspectionContribution, PatternInspectionDescriptor
from lychd.extensions.context import ExtensionContext
from lychd.extensions.host import AssembledExtensions
from tests.unit.domain.oculus.test_runtime import Reader, source

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def test_runtime_and_loom_share_exact_selected_profiles(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    fake_services.runtime_observations = RuntimeCatalogue(
        reader=Reader(
            (
                SourceRead("reach", "builtin:reach", source("reach")),
                SourceRead("weather", "crypt:weather", source("weather")),
            )
        )
    )
    runtime = altar_client.get("/api/v1/orb/runtime")
    assert runtime.status_code == 200
    body = runtime.json()
    assert len(body["activities"]) == 4
    assert {item["source_id"] for item in body["activities"]} == {"reach", "weather"}
    assert {item["run_id"] for item in body["activities"]} == {None, "already-finished-run"}
    catalogue = altar_client.get("/api/v1/loom").json()
    remote = [item for item in catalogue if item["binding"]["executable"] is False]
    assert {item["pattern_id"] for item in remote} == {"reach.pattern", "weather.pattern"}
    for entry in remote:
        assert entry["publication"] == "observed"
        assert entry["active"] is False
        assert entry["default"] is False
        assert entry["route_rank"] is None
        detail_path = entry["detail_path"]
        assert isinstance(detail_path, str)
        path = urlsplit(detail_path)
        response = altar_client.get(f"/api/v1{path.path}?{path.query}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["binding"] == entry["binding"]
        assert detail["digest"] == entry["digest"]
        assert detail["publication"] == "observed"
        assert (
            altar_client.get(
                f"/api/v1{path.path}?{path.query.replace('generation=g1', 'generation=other')}"
            ).status_code
            == 404
        )
        assert altar_client.get(f"/api/v1{path.path}?source_id=reach").status_code == 404
    assert fake_services.workflows.get("reach.pattern") is None


def test_failed_observation_source_keeps_existing_run_routes_available(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    fake_services.runtime_observations = RuntimeCatalogue(
        reader=Reader((SourceRead("reach", "builtin:reach", failure="unsafe"),))
    )
    body = altar_client.get("/api/v1/orb/runtime").json()
    assert body["sources"][-1]["status"] == "unsafe"
    assert body["activities"] == []
    assert altar_client.get("/api/v1/orb/runs").status_code == 200
    assert altar_client.get("/api/v1/loom/bridge_chat/1").status_code == 200


def test_runtime_is_authorized_like_other_altar_reads(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/api/v1/orb/runtime", headers={"Authorization": ""})
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("conflict_with", ["native", "reader"])
def test_conflicting_inspection_quarantines_source_without_breaking_native_apis(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
    conflict_with: str,
) -> None:
    reach = source("reach")
    original = (
        PatternInspectionDescriptor.from_workflow(BRIDGE_CHAT) if conflict_with == "native" else reach.patterns[0]
    )
    inspection = RegisteredInspection(
        registrant_id="crypt:conflicting",
        source_id="conflicting",
        generation="g1",
        profile_id="conflicting.profile",
        profile_revision="1",
        descriptor=original.model_copy(update={"title": "Conflicting exact revision"}),
    )
    fake_services.runtime_observations = RuntimeCatalogue(
        reader=Reader(
            (SourceRead("reach", "operator:reach", reach), SourceRead("weather", "operator:weather", source("weather")))
        ),
        inspections=(inspection,),
    )
    response = altar_client.get("/api/v1/orb/runtime")
    assert response.status_code == 200
    body = response.json()
    conflicted = next(item for item in body["sources"] if item["source_id"] == "conflicting")
    assert conflicted["status"] == "conflict"
    assert conflicted["registrant_id"] is None
    assert conflicted["generation"] is None
    assert all(item["binding"]["source_id"] != "conflicting" for item in body["patterns"])
    assert any(item["binding"]["source_id"] == "weather" for item in body["patterns"])
    if conflict_with == "reader":
        assert next(item for item in body["sources"] if item["source_id"] == "reach")["status"] == "conflict"
    assert altar_client.get("/api/v1/loom").status_code == 200
    native = altar_client.get("/api/v1/loom/bridge_chat/1")
    assert native.status_code == 200
    assert native.json()["title"] == BRIDGE_CHAT.title
    assert altar_client.get("/api/v1/orb/runs").status_code == 200


def test_duplicate_source_custody_has_one_unattributed_conflict_row(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    fake_services.runtime_observations = RuntimeCatalogue(
        observations=(RegisteredObservation("builtin:reach", source("reach", activity_count=0)),),
        reader=Reader(
            (
                SourceRead("reach", "operator:reach", source("reach")),
                SourceRead("weather", "operator:weather", source("weather")),
            )
        ),
    )
    response = altar_client.get("/api/v1/orb/runtime")
    assert response.status_code == 200
    body = response.json()
    rows = [item for item in body["sources"] if item["source_id"] == "reach"]
    assert len(rows) == 1
    assert rows[0]["status"] == "conflict"
    assert rows[0]["registrant_id"] is None
    assert rows[0]["generation"] is None
    assert rows[0]["profile_id"] is None
    assert not any(item["source_id"] == "reach" for item in body["components"])
    assert not any(item["source_id"] == "reach" for item in body["activities"])
    assert not any(item["binding"]["source_id"] == "reach" for item in body["patterns"])
    assert len({item["source_id"] for item in body["sources"]}) == len(body["sources"])
    assert altar_client.get("/api/v1/loom").status_code == 200
    assert altar_client.get("/api/v1/loom/bridge_chat/1").status_code == 200


def test_same_profile_inspection_contributed_twice_has_one_working_exact_link(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    root = ExtensionContext()
    view = root.registration_view("crypt:reach")
    declaration = source("reach", activity_count=0)
    view.observations.add(declaration)
    view.inspections.add(
        InspectionContribution(
            source_id=declaration.source_id,
            profile_id=declaration.profile_id,
            profile_revision=declaration.profile_revision,
            descriptor=declaration.patterns[0],
        )
    )
    assembly = AssembledExtensions(root)
    fake_services.runtime_observations = RuntimeCatalogue(
        observations=assembly.observation_registrations,
        inspections=assembly.inspection_registrations,
    )
    response = altar_client.get("/api/v1/orb/runtime")
    assert response.status_code == 200
    assert len([entry for entry in response.json()["patterns"] if entry["binding"]["source_id"] == "reach"]) == 1
    catalogue = altar_client.get("/api/v1/loom")
    assert catalogue.status_code == 200
    entries = [entry for entry in catalogue.json() if entry["binding"]["source_id"] == "reach"]
    assert len(entries) == 1
    detail_path = entries[0]["detail_path"]
    assert isinstance(detail_path, str)
    detail = altar_client.get(f"/api/v1{detail_path}")
    assert detail.status_code == 200
    assert detail.json()["binding"]["executable"] is False
    assert detail.json()["digest"] == declaration.patterns[0].digest
    assert fake_services.workflows.get_revision("reach.pattern", "1") is None
    assert altar_client.get("/api/v1/loom/bridge_chat/1").status_code == 200
