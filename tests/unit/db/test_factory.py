from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest

from lychd.config.settings.server import DatabaseSettings
from lychd.db import factory as db_factory

_JSON_VALUE = {"name": "LychD", "depth": 2}
_JSON_PAYLOAD = b'{"name":"LychD","depth":2}'


class _Engine:
    sync_engine = object()


class _DriverConnection:
    def __init__(self) -> None:
        self.codecs: dict[str, dict[str, object]] = {}

    def set_type_codec(self, typename: str, **options: object) -> object:
        self.codecs[typename] = options
        return object()


class _DbapiConnection:
    def __init__(self) -> None:
        self.driver_connection = _DriverConnection()
        self.awaited: list[object] = []

    def await_(self, awaitable: object) -> None:
        self.awaited.append(awaitable)


@pytest.fixture
def registered_codecs(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, object]]:
    listener: Callable[[Any, Any], Any] | None = None
    engine = _Engine()

    def capture_listener(
        _target: object,
        event_name: str,
    ) -> Callable[[Callable[[Any, Any], Any]], Callable[[Any, Any], Any]]:
        assert event_name == "connect"

        def register(callback: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
            nonlocal listener
            listener = callback
            return callback

        return register

    def create_engine(**_kwargs: object) -> _Engine:
        return engine

    monkeypatch.setattr(db_factory, "create_async_engine", create_engine)
    monkeypatch.setattr(db_factory.event, "listens_for", capture_listener)
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "db-pass")

    assert db_factory.create_db_engine(DatabaseSettings()) is engine
    assert listener is not None

    connection = _DbapiConnection()
    listener(connection, object())

    assert len(connection.awaited) == 2
    return connection.driver_connection.codecs


def _encoder(codec: dict[str, object]) -> Callable[[bytes], bytes]:
    return cast("Callable[[bytes], bytes]", codec["encoder"])


def _decoder(codec: dict[str, object]) -> Callable[[bytes], object]:
    return cast("Callable[[bytes], object]", codec["decoder"])


def test_plain_json_binary_codec_uses_unversioned_wire_payload(
    registered_codecs: dict[str, dict[str, object]],
) -> None:
    codec = registered_codecs["json"]

    assert codec["schema"] == "pg_catalog"
    assert codec["format"] == "binary"
    assert _encoder(codec)(_JSON_PAYLOAD) == _JSON_PAYLOAD
    assert _decoder(codec)(_JSON_PAYLOAD) == _JSON_VALUE


def test_jsonb_binary_codec_uses_postgres_versioned_wire_payload(
    registered_codecs: dict[str, dict[str, object]],
) -> None:
    codec = registered_codecs["jsonb"]
    framed_payload = b"\x01" + _JSON_PAYLOAD

    assert codec["schema"] == "pg_catalog"
    assert codec["format"] == "binary"
    assert _encoder(codec)(_JSON_PAYLOAD) == framed_payload
    assert _decoder(codec)(framed_payload) == _JSON_VALUE
