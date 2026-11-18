"""Retired host-native credential selection refuses without opening a secret owner."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from pydantic_settings import EnvSettingsSource

from lychd.config.settings import Settings, SettingsSnapshot, get_settings
from lychd.config.settings.sources import RuntimeSecretsSource


@pytest.fixture(autouse=True)
def isolated_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", tmp_path / "lychd.toml")
    monkeypatch.setattr("lychd.config.settings.sources.MOUNTED_SECRETS_DIR", tmp_path / "mounts")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("selection", ["podman-core@1", "", "podman-core@2", "private-choice"])
def test_retired_selection_refuses_before_tool_or_credential_io(
    monkeypatch: pytest.MonkeyPatch,
    selection: str,
) -> None:
    monkeypatch.setenv("LYCHD_RUNTIME_SECRETS", selection)
    tool = Mock(side_effect=AssertionError("selected source resolved Podman"))
    store = Mock(side_effect=AssertionError("selected source opened Podman secrets"))
    monkeypatch.setattr("lychd.system.host_tools.trusted_host_tool", tool)
    monkeypatch.setattr("lychd.system.services.secrets.PodmanSecretStore", store)

    def unexpected_read(path: Path, *args: Any, **kwargs: Any) -> str:
        message = "selected source attempted a credential-file read"
        raise AssertionError(message)

    monkeypatch.setattr(Path, "read_text", unexpected_read)
    with pytest.raises(ValueError, match="LYCHD_RUNTIME_SECRETS is retired") as error:
        Settings()
    assert "private-choice" not in str(error.value)
    tool.assert_not_called()
    store.assert_not_called()


def test_retired_selection_refusal_uses_the_captured_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYCHD_RUNTIME_SECRETS", "podman-core@1")
    source = RuntimeSecretsSource(Settings, EnvSettingsSource(Settings))
    monkeypatch.delenv("LYCHD_RUNTIME_SECRETS")
    with pytest.raises(ValueError, match="LYCHD_RUNTIME_SECRETS is retired"):
        source()


def test_container_mount_credentials_and_snapshot_need_no_host_secret_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", "container")
    mounts = tmp_path / "mounts"
    mounts.mkdir()
    values = {
        "lychd_runtime_db_password": "synthetic-runtime-credential",
        "lychd_app_secret_key": "synthetic-signing-credential",
        "lychd_local_access_password": "synthetic-access-credential-" + "x" * 40,
    }
    for name, value in values.items():
        (mounts / name).write_text(value, encoding="utf-8")
    tool = Mock(side_effect=AssertionError("container source resolved Podman"))
    store = Mock(side_effect=AssertionError("container source opened host secrets"))
    monkeypatch.setattr("lychd.system.host_tools.trusted_host_tool", tool)
    monkeypatch.setattr("lychd.system.services.secrets.PodmanSecretStore", store)
    loaded = get_settings()
    snapshot = SettingsSnapshot.capture(loaded)
    monkeypatch.setenv("LYCHD_RUNTIME_SECRETS", "podman-core@1")
    for generation in (loaded, get_settings(), snapshot.materialize(), snapshot.materialize()):
        assert generation.server.database.runtime_password == SecretStr(values["lychd_runtime_db_password"])
        assert generation.server.web.secret_key == SecretStr(values["lychd_app_secret_key"])
        assert generation.server.web.access_password == SecretStr(values["lychd_local_access_password"])
        assert generation.server.database.password is None
        assert generation.server.database.phoenix_password is None
    assert get_settings() is loaded
    for value in values.values():
        assert value not in repr(loaded)
        assert value not in repr(snapshot)
        assert value not in snapshot.payload
        assert value not in loaded.model_dump_json()
    with pytest.raises(ValueError, match="LYCHD_RUNTIME_SECRETS is retired"):
        Settings()
    tool.assert_not_called()
    store.assert_not_called()
