"""Bridge JSON contract: session creation, message admission, and inspector."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def _session(fake_services: SimpleNamespace) -> Any:
    return asyncio.run(fake_services.bridge_sessions.create_session())


def test_create_session_returns_typed_identity(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.post("/api/v1/bridge/sessions")

    assert response.status_code == 201
    session = response.json()["session"]
    assert session["id"]
    assert session["turns"] == []


def test_snapshot_lists_created_session(altar_client: TestClient[Litestar]) -> None:
    created = altar_client.post("/api/v1/bridge/sessions").json()["session"]

    snapshot = altar_client.get("/api/v1/bridge")

    assert snapshot.status_code == 200
    assert snapshot.json()["session"]["id"] == created["id"]
    assert snapshot.json()["sessions"][0]["id"] == created["id"]


def test_send_unknown_session_404(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.post(
        "/api/v1/bridge/sessions/nope/messages",
        json={"prompt": "hi"},
    )
    assert response.status_code == 404


def test_send_empty_prompt_400(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "   "},
    )
    assert response.status_code == 400


def test_send_happy_path(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "raise the dead"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"]
    assert body["turn"]["content"] == "raise the dead"
    assert body["turn"]["role"] == "user"
    assert len(fake_services.run_engine.submitted) == 1
    assert fake_services.run_engine.submitted[0].prompt == "raise the dead"
    assert fake_services.run_engine.submitted[0].sigil_name
    assert fake_services.run_engine.submitted[0].sigil_scopes


def test_inspector_returns_context(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.get(
        f"/api/v1/bridge/sessions/{session.id}/inspector",
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session.id,
        "title": session.title,
        "turn_count": 0,
        "pending_count": 0,
    }
