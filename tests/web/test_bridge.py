"""Bridge chat surface: session create, send flow, inspector.

Consent-endpoint tests live in `test_consent_endpoint.py` (the real ConsentLedger).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient

_HX = {"HX-Request": "true"}


def _session(fake_services: SimpleNamespace) -> Any:
    return asyncio.run(fake_services.bridge_sessions.create_session())


def test_create_session_htmx_returns_hx_location(altar_client: TestClient[Litestar]) -> None:
    """An HTMX session-create steers the client via HX-Location onto the new séance."""
    response = altar_client.post("/bridge/sessions", headers=_HX)
    assert response.status_code == 200
    assert "hx-location" in {k.lower() for k in response.headers}


def test_create_session_non_htmx_redirects(altar_client: TestClient[Litestar]) -> None:
    """A non-HTMX session-create falls back to a 303 redirect."""
    response = altar_client.post("/bridge/sessions", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/bridge/")


def test_send_requires_htmx(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """Send is HTMX-only: a plain POST is rejected 400."""
    session = _session(fake_services)
    response = altar_client.post(f"/bridge/{session.id}/messages", data={"prompt": "hi"})
    assert response.status_code == 400


def test_send_unknown_session_404(altar_client: TestClient[Litestar]) -> None:
    """Send to an unknown session is 404."""
    response = altar_client.post("/bridge/nope/messages", headers=_HX, data={"prompt": "hi"})
    assert response.status_code == 404


def test_send_empty_prompt_400(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """An empty offering cannot be spoken (400)."""
    session = _session(fake_services)
    response = altar_client.post(f"/bridge/{session.id}/messages", headers=_HX, data={"prompt": "   "})
    assert response.status_code == 400


def test_send_happy_path(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A valid send returns the user turn, the SSE stream slot, and the OOB rail."""
    session = _session(fake_services)
    response = altar_client.post(f"/bridge/{session.id}/messages", headers=_HX, data={"prompt": "raise the dead"})
    assert response.status_code == 200
    body = response.text
    assert "raise the dead" in body  # the user turn
    assert 'id="run-' in body  # the stream slot
    assert "sse-connect" in body
    assert "hx-swap-oob" in body  # the OOB rail update
    # the engine received exactly one Intent carrying the prompt
    assert len(fake_services.run_engine.submitted) == 1
    assert fake_services.run_engine.submitted[0].prompt == "raise the dead"


def test_inspector_renders(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """The inspector fragment renders for a known session."""
    session = _session(fake_services)
    response = altar_client.get(f"/bridge/{session.id}/inspector")
    assert response.status_code == 200
    assert 'data-fragment="bridge.inspector"' in response.text
