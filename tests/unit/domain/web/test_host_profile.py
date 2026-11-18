"""Production composition enforces the host boundary before loading any extension or actuator."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from litestar.config.app import AppConfig

from lychd import app
from lychd.interface import server
from lychd.interface.server_policy import ServerRuntimePolicyError


@pytest.mark.parametrize(
    ("platform", "actuator"),
    [("linux", "native-process"), ("darwin", "systemd"), ("win32", "host-reactor")],
)
def test_production_composition_rejects_foreign_actuator_before_assembly(
    monkeypatch: pytest.MonkeyPatch, platform: str, actuator: str
) -> None:
    monkeypatch.setattr(app.sys, "platform", platform)
    monkeypatch.setattr(
        app,
        "get_settings",
        lambda: SimpleNamespace(orchestration=SimpleNamespace(switching=SimpleNamespace(actuator=actuator))),
    )
    assembly = Mock()
    monkeypatch.setattr("lychd.extensions.host.get_extensions", assembly)
    with pytest.raises(ServerRuntimePolicyError):
        app.AppInit()._configure_composition(AppConfig(route_handlers=[]))  # pyright: ignore[reportPrivateUsage]
    assembly.assert_not_called()


@pytest.mark.parametrize("platform", ["darwin", "win32", "linux"])
def test_listener_adapter_refuses_the_wrong_host_before_loading_settings(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    monkeypatch.setattr(server.sys, "platform", platform)
    load_settings = Mock()
    monkeypatch.setattr("lychd.config.settings.root.get_settings", load_settings)
    launch = server.run_native_server if platform == "linux" else server.run_production_server
    with pytest.raises(ServerRuntimePolicyError):
        launch()
    load_settings.assert_not_called()
