"""Reject ambient configuration and I/O while constructing the optional Docker fixture."""

from __future__ import annotations

from typing import Any, NoReturn, cast

import pytest

from tests import scout_postgres_fixture


def test_docker_fixture_client_does_not_read_ambient_auth_or_contact_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("docker", reason="This fixture regression requires the optional container-test Docker SDK.")
    from docker.utils import config
    from requests import Request, sessions

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        msg = "Fixture construction attempted ambient config/auth access or a request."
        raise AssertionError(msg)

    untyped_config = cast("Any", config)  # The optional SDK does not type this loader.
    loader = untyped_config.load_general_config
    monkeypatch.setattr(config, "find_config_file", forbidden)
    monkeypatch.setattr(sessions, "get_netrc_auth", forbidden)
    monkeypatch.setattr(sessions.Session, "send", forbidden)
    client = scout_postgres_fixture._client()  # pyright: ignore[reportPrivateUsage] - Verify the fixture's credential boundary.
    try:
        assert client.api.trust_env is False
        assert client.api.proxies == {}
        request = client.api.prepare_request(Request("GET", "http+docker://localhost/info"))
        assert "Authorization" not in request.headers
        assert untyped_config.load_general_config is loader
    finally:
        client.close()
