"""403 matrix over the sigil middleware + `requires_scopes` guard (wave4-design §3.3)."""

from __future__ import annotations

from typing import Any

import pytest
from litestar import Litestar, Request, get, post

from lychd.domain.codex import middleware as mw_mod
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil
from tests.web.conftest import AsgiClient


def _sigil(*, name: str = "magus", scopes: list[str]) -> Sigil:
    return Sigil(name=name, scopes=frozenset(scopes))


@get("/read", name="read", guards=[requires_scopes("altar:read")])
async def read_handler() -> dict[str, str]:
    return {"ok": "read"}


@post("/write", name="write", guards=[requires_scopes("runs:approve")])
async def write_handler(request: Request[Any, Any, Any]) -> dict[str, object]:
    return {"user_is_sigil": isinstance(request.user, Sigil)}


def _client(monkeypatch: pytest.MonkeyPatch, sigil: Sigil) -> AsgiClient:
    monkeypatch.setattr(mw_mod, "local_sigil", lambda: sigil)
    app = Litestar(route_handlers=[read_handler, write_handler], middleware=[sigil_auth_middleware()])
    return AsgiClient(app)


def test_narrowed_sigil_allows_read_denies_write(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, _sigil(scopes=["altar:read"]))
    assert client.get("/read").status_code == 200
    assert client.post("/write").status_code == 403


def test_full_sigil_allows_both(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, _sigil(scopes=["*"]))
    assert client.get("/read").status_code == 200
    resp = client.post("/write")
    assert resp.status_code == 201
    assert resp.json()["user_is_sigil"] is True


def test_missing_sigil_is_denied() -> None:
    app = Litestar(route_handlers=[read_handler])
    assert AsgiClient(app).get("/read").status_code == 403
