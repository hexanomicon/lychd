"""Static Svelte shell routing and API/fallback separation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient


@pytest.mark.parametrize(
    "path",
    ["/atlas", "/bridge", "/nexus", "/loom", "/orb"],
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
    favicon = altar_client.get("/favicon.svg")

    assert notices.status_code == 200
    assert notices.headers["content-type"].startswith("text/plain")
    assert notices.text.startswith("LychD Altar — Third-Party Notices")
    assert lightning.status_code == 200
    assert lightning.headers["content-type"].startswith("image/svg+xml")
    assert lightning.text.lstrip().startswith("<svg")
    assert favicon.status_code == 200
    assert favicon.headers["content-type"].startswith("image/svg+xml")
    assert favicon.text.lstrip().startswith("<svg")
    assert 'href="/favicon.svg"' in altar_client.get("/bridge").text
    assert "LychD Altar — visual assets" in notices.text


def test_altar_status_publishes_the_vessel_csrf_names(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/altar/status")

    assert response.status_code == 200
    assert response.json()["csrf"] == {
        "cookie_name": "csrftoken",
        "header_name": "x-csrftoken",
    }


def test_every_explicit_error_operation_publishes_the_shared_framework_error(
    altar_client: TestClient[Litestar],
) -> None:
    schema = cast("dict[str, Any]", altar_client.get("/schema/openapi.json").json())
    expected = {
        ("/api/v1/atlas/projects", "post", "404"),
        ("/api/v1/atlas/projects", "post", "409"),
        ("/api/v1/atlas/projects/{project_id}", "get", "404"),
        ("/api/v1/atlas/projects/{project_id}/changes", "post", "404"),
        ("/api/v1/atlas/projects/{project_id}/changes", "post", "409"),
        ("/api/v1/bridge/consents/{consent_id}/decision", "post", "404"),
        ("/api/v1/bridge/runs/{run_id}", "get", "404"),
        ("/api/v1/bridge/runs/{run_id}/cancel", "post", "404"),
        ("/api/v1/bridge/runs/{run_id}/events", "get", "404"),
        ("/api/v1/bridge/runs/{run_id}/events", "get", "429"),
        ("/api/v1/bridge/sessions/{session_id}", "get", "404"),
        ("/api/v1/bridge/sessions/{session_id}/inspector", "get", "404"),
        ("/api/v1/bridge/sessions/{session_id}/messages", "post", "404"),
        ("/api/v1/loom/source/patterns/{pattern_id}/{revision}", "get", "404"),
        ("/api/v1/loom/source/workflows/{workflow}", "get", "404"),
        ("/api/v1/loom/{pattern_id}/{revision}", "get", "404"),
        ("/api/v1/loom/{workflow}", "get", "404"),
        ("/api/v1/nexus/plan", "get", "404"),
        ("/api/v1/nexus/swaps", "post", "404"),
        ("/api/v1/nexus/swaps", "post", "409"),
        ("/api/v1/nexus/swaps", "post", "503"),
        ("/api/v1/nexus/swaps/{ticket_id}", "get", "404"),
        ("/api/v1/nexus/swaps/{ticket_id}/events", "get", "404"),
        ("/api/v1/nexus/transitions/{request_id}", "get", "404"),
        ("/api/v1/orb/runs/{run_id}", "get", "404"),
    }
    declared: set[tuple[str, str, str]] = set()
    paths = cast("dict[str, dict[str, Any]]", schema["paths"])
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for status, response in operation["responses"].items():
                response_schema = response.get("content", {}).get("application/json", {}).get("schema")
                if response_schema == {"$ref": "#/components/schemas/FrameworkError"}:
                    declared.add((path, method, status))

    assert declared == expected


@pytest.mark.parametrize(
    "path",
    ["/atlas/project-x", "/bridge/session-x", "/loom/pattern-x/revision-1", "/orb/run-x"],
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


def test_validation_error_returns_the_framework_contract(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/orb/runs/not-real?after_seq=not-an-integer")
    schema = cast("dict[str, Any]", altar_client.get("/schema/openapi.json").json())
    declared = schema["paths"]["/api/v1/orb/runs/{run_id}"]["get"]["responses"]["400"]["content"]["application/json"][
        "schema"
    ]

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
