"""403 matrix over the sigil middleware + `requires_scopes` guard (wave4-design §3.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from litestar import Litestar, Request, get, post
from litestar.testing import TestClient

from lychd.domain.codex import guards as guards_mod
from lychd.domain.codex import middleware as mw_mod
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil


def _settings(*, name: str = "magus", scopes: list[str], enforce: bool) -> SimpleNamespace:
    return SimpleNamespace(sigil=SimpleNamespace(name=name, scopes=scopes, enforce=enforce))


@get("/read", name="read", guards=[requires_scopes("altar:read")])
async def read_handler() -> dict[str, str]:
    return {"ok": "read"}


@post("/write", name="write", guards=[requires_scopes("runs:approve")])
async def write_handler(request: Request[Any, Any, Any]) -> dict[str, object]:
    return {"user_is_sigil": isinstance(request.user, Sigil)}


def _client(monkeypatch: pytest.MonkeyPatch, settings: SimpleNamespace) -> TestClient[Litestar]:
    monkeypatch.setattr(mw_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(guards_mod, "get_settings", lambda: settings)
    app = Litestar(route_handlers=[read_handler, write_handler], middleware=[sigil_auth_middleware()])
    return TestClient(app=app)


def test_narrowed_sigil_allows_read_denies_write(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(scopes=["altar:read"], enforce=True)
    with _client(monkeypatch, settings) as client:
        assert client.get("/read").status_code == 200
        assert client.post("/write").status_code == 403


def test_full_sigil_allows_both(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(scopes=["*"], enforce=True)
    with _client(monkeypatch, settings) as client:
        assert client.get("/read").status_code == 200
        resp = client.post("/write")
        assert resp.status_code == 201
        assert resp.json()["user_is_sigil"] is True


def test_enforce_false_no_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(scopes=["altar:read"], enforce=False)
    with _client(monkeypatch, settings) as client:
        # enforce disabled → the write guard is a no-op even with a narrowed sigil
        assert client.post("/write").status_code == 201
