"""Explicit local access display without ambient disclosure or app startup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner
from pydantic import SecretStr

from lychd.__main__ import cli
from lychd.config.settings.root import Settings
from lychd.config.settings.server import ServerSettings, WebSettings
from lychd.system.services import local_access
from lychd.system.services.local_access import LocalAccess, load_local_access
from lychd.system.services.secrets import PodmanSecretStoreError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_PASSWORD = "synthetic-local-access-password-0123456789"  # noqa: S105


def _settings(*, password: str | None) -> Settings:
    return Settings(server=ServerSettings(web=WebSettings(access_password=SecretStr(password) if password else None)))


def test_access_is_explicit_and_help_does_not_read_credentials(mocker: MockerFixture) -> None:
    loader = mocker.patch.object(
        local_access, "load_local_access", return_value=LocalAccess("http://127.0.0.1:7134/", SecretStr(_PASSWORD))
    )
    help_result = CliRunner().invoke(cli, ["access", "--help"])
    assert help_result.exit_code == 0
    assert _PASSWORD not in help_result.output
    loader.assert_not_called()

    result = CliRunner().invoke(cli, ["access"])
    assert result.exit_code == 0
    assert f"Password: {_PASSWORD}" in result.output
    assert "Username: magus" in result.output
    assert f"http://magus:{_PASSWORD}" not in result.output
    loader.assert_called_once_with()


def test_access_refuses_without_leaking_validation_input(mocker: MockerFixture) -> None:
    mocker.patch.object(local_access, "load_local_access", side_effect=ValueError(f"private input {_PASSWORD}"))
    result = CliRunner().invoke(cli, ["access"])
    assert result.exit_code != 0
    assert _PASSWORD not in result.output
    assert "Local access is unavailable" in result.output


def test_runtime_credential_needs_no_podman_or_application(mocker: MockerFixture) -> None:
    mocker.patch.object(local_access.os, "geteuid", return_value=1000)
    mocker.patch.object(local_access, "get_settings", return_value=_settings(password=_PASSWORD))
    tool = mocker.patch.object(local_access, "trusted_host_tool")
    details = load_local_access()
    assert details.password.get_secret_value() == _PASSWORD
    assert _PASSWORD not in repr(details)
    tool.assert_not_called()


def test_host_reads_exact_configured_secret_through_trusted_podman(mocker: MockerFixture) -> None:
    mocker.patch.object(local_access.os, "geteuid", return_value=1000)
    settings = _settings(password=None)
    mocker.patch.object(local_access, "get_settings", return_value=settings)
    mocker.patch.object(local_access, "trusted_host_tool", return_value="/usr/bin/podman")
    store = mocker.patch.object(local_access, "PodmanSecretStore").return_value
    store.read.return_value = SecretStr(_PASSWORD)
    assert load_local_access().password.get_secret_value() == _PASSWORD
    store.read.assert_called_once_with(settings.server.web.access_password_secret)


def test_secret_read_failure_is_safe_for_terminal(mocker: MockerFixture) -> None:
    mocker.patch.object(local_access.os, "geteuid", return_value=1000)
    mocker.patch.object(local_access, "get_settings", return_value=_settings(password=None))
    mocker.patch.object(local_access, "trusted_host_tool", return_value="/usr/bin/podman")
    store = mocker.patch.object(local_access, "PodmanSecretStore").return_value
    store.read.side_effect = PodmanSecretStoreError(_PASSWORD)
    result = CliRunner().invoke(cli, ["access"])
    assert result.exit_code != 0
    assert _PASSWORD not in result.output


def test_access_refuses_root_before_loading_settings(mocker: MockerFixture) -> None:
    mocker.patch.object(local_access.os, "geteuid", return_value=0)
    settings = mocker.patch.object(local_access, "get_settings")
    result = CliRunner().invoke(cli, ["access"])
    assert result.exit_code != 0
    settings.assert_not_called()
