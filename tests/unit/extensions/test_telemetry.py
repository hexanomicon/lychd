from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lychd.extensions.builtin.observability.telemetry import TelemetryPlugin


def test_httpx_instrumentation_never_blanket_captures_credentials_or_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.extensions.builtin.observability import telemetry

    observed: dict[str, object] = {}

    def ignore_kwargs(**_kwargs: object) -> None:
        return

    def capture_httpx(**kwargs: object) -> None:
        observed.update(kwargs)

    def build_stub(**_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(telemetry.logfire, "configure", ignore_kwargs)
    monkeypatch.setattr(telemetry.logfire, "instrument_pydantic_ai", lambda: None)
    monkeypatch.setattr(telemetry.logfire, "instrument_httpx", capture_httpx)
    monkeypatch.setattr(telemetry.trace, "get_tracer_provider", lambda: object())
    monkeypatch.setattr(telemetry, "OpenTelemetryConfig", build_stub)
    monkeypatch.setattr(telemetry, "OpenTelemetryPlugin", build_stub)
    app_config: Any = SimpleNamespace(plugins=[])

    TelemetryPlugin("http://localhost:4318").on_app_init(app_config)

    assert observed == {
        "capture_all": False,
        "capture_headers": False,
        "capture_request_body": False,
        "capture_response_body": False,
    }
