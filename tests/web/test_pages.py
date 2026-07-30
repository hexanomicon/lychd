"""Static Svelte shell routing and API/fallback separation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

_EXPORTED_OPENAPI = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient


@pytest.mark.parametrize(
    "path",
    ["/bridge", "/nexus", "/loom", "/orb"],
)
def test_pages_return_compiled_svelte_shell(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    response = altar_client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/_app/immutable/" in response.text


def test_root_redirects_to_bridge(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/bridge"


def test_fixed_root_assets_have_narrow_routes_and_exact_media_types(
    altar_client: TestClient[Litestar],
) -> None:
    notices = altar_client.get("/THIRD_PARTY_NOTICES.txt")
    lightning = altar_client.get("/altar-lightning.svg")

    assert notices.status_code == 200
    assert notices.headers["content-type"].startswith("text/plain")
    assert notices.text.startswith("LychD Altar — Third-Party Notices")
    assert lightning.status_code == 200
    assert lightning.headers["content-type"].startswith("image/svg+xml")
    assert lightning.text.lstrip().startswith("<svg")


def test_altar_status_publishes_the_vessel_csrf_names(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/altar/status")

    assert response.status_code == 200
    assert response.json()["csrf"] == {
        "cookie_name": "csrftoken",
        "header_name": "x-csrftoken",
    }


@pytest.mark.parametrize(
    "path",
    ["/bridge/session-x", "/loom/pattern-x/revision-1", "/orb/run-x"],
)
def test_deep_links_return_same_static_shell(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    shell = altar_client.get("/bridge")
    deep = altar_client.get(path)

    assert deep.status_code == 200
    assert deep.content == shell.content


def test_unknown_api_is_not_swallowed_by_spa_fallback(
    altar_client: TestClient[Litestar],
) -> None:
    assert altar_client.get("/api/v1/not-real").status_code == 404


def test_validation_error_matches_the_exported_litestar_contract(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/orb/runs/not-real?after_seq=not-an-integer")
    exported = json.loads(_EXPORTED_OPENAPI.read_text(encoding="utf-8"))
    operation = exported["paths"]["/api/v1/orb/runs/{run_id}"]["get"]
    declared = operation["responses"]["400"]["content"]["application/json"]["schema"]

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert set(response.json()) == {"status_code", "detail", "extra"}
    assert set(declared["required"]) <= set(response.json())
    assert set(declared["properties"]) == set(response.json())


@pytest.mark.parametrize(
    "path",
    ["/reliquary", "/bindings", "/scrying", "/scrying/run-x", "/loom/unversioned"],
)
def test_retired_or_ambiguous_pages_are_not_routes(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    assert altar_client.get(path).status_code == 404
