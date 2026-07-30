"""Loopback Host and Origin admission for the local browser surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from litestar import Litestar, get

from lychd.config.components import build_allowed_hosts_config, build_cors_config
from lychd.config.settings.root import Settings
from lychd.config.settings.server import ServerSettings, WebSettings

if TYPE_CHECKING:
    from tests.web.conftest import AsgiClient


@get("/probe", sync_to_thread=False)
def probe() -> dict[str, bool]:
    """Return a side-effect-free response behind the HTTP boundary middleware."""
    return {"ok": True}


def _client(*, origins: list[str], listener_port: int | None = None) -> AsgiClient:
    from tests.web.conftest import AsgiClient

    settings = Settings(
        server=ServerSettings(
            web=WebSettings(allowed_cors_origins=origins),
        ),
    )
    app = Litestar(
        route_handlers=[probe],
        allowed_hosts=build_allowed_hosts_config(settings, listener_port=listener_port),
        cors_config=build_cors_config(settings),
    )
    return AsgiClient(app)


@pytest.mark.parametrize(
    "authority",
    ["127.0.0.1", "127.0.0.1:7134", "localhost", "localhost:7134", "[::1]", "[::1]:7134"],
)
def test_exact_loopback_authorities_are_admitted(authority: str) -> None:
    response = _client(origins=[]).get("/probe", headers={"host": authority})

    assert response.status_code == 200


def test_non_loopback_host_is_rejected_before_routing() -> None:
    response = _client(origins=[]).get("/probe", headers={"host": "attacker.example"})

    assert response.status_code == 400
    assert response.json() == {"message": "invalid host header"}


def test_detected_listener_port_augments_but_does_not_widen_loopback_authorities() -> None:
    client = _client(origins=[], listener_port=8000)

    configured = client.get("/probe", headers={"host": "localhost:7134"})
    actual = client.get("/probe", headers={"host": "localhost:8000"})
    wrong_port = client.get("/probe", headers={"host": "localhost:8001"})
    remote = client.get("/probe", headers={"host": "vessel.example:8000"})

    assert configured.status_code == 200
    assert actual.status_code == 200
    assert wrong_port.status_code == 400
    assert remote.status_code == 400


def test_cors_is_same_origin_by_default_and_allows_only_an_exact_configured_origin() -> None:
    origin = "http://localhost:5173"
    default_response = _client(origins=[]).get(
        "/probe",
        headers={"host": "127.0.0.1:7134", "origin": origin},
    )
    configured_response = _client(origins=[origin]).get(
        "/probe",
        headers={"host": "127.0.0.1:7134", "origin": origin},
    )
    foreign_response = _client(origins=[origin]).get(
        "/probe",
        headers={"host": "127.0.0.1:7134", "origin": "http://127.0.0.1:5173"},
    )

    assert "access-control-allow-origin" not in default_response.headers
    assert configured_response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-origin" not in foreign_response.headers
