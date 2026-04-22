from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from lychd.cli.commands import bind_quadlets, init_codex

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def test_init_codex_success(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify init command orchestrates Codex properly."""
    # Patch the classes inside the command
    mocker.patch("lychd.system.services.layout.LayoutService")
    mocker.patch("lychd.system.services.privilege.PrivilegeService")
    mock_codex_cls = mocker.patch("lychd.system.services.codex.CodexService")
    mock_codex_instance = mock_codex_cls.return_value

    result = runner.invoke(init_codex)

    assert result.exit_code == 0
    assert "Beginning the Inscription" in result.output
    assert "Initialization complete" in result.output

    # Verify interaction
    mock_codex_cls.assert_called_once()
    mock_codex_instance.inscribe.assert_called_once()


def test_init_codex_failure(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify error handling when Codex fails."""
    mocker.patch("lychd.system.services.layout.LayoutService")
    mocker.patch("lychd.system.services.privilege.PrivilegeService")
    mock_codex_cls = mocker.patch("lychd.system.services.codex.CodexService")
    mock_codex_instance = mock_codex_cls.return_value
    # Simulate a filesystem permission error
    mock_codex_instance.inscribe.side_effect = PermissionError("Access Denied")

    result = runner.invoke(init_codex)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output
    assert "Access Denied" in result.output


def test_bind_quadlets_success(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify bind command orchestrates Loader, Scribe, and Systemd."""
    # 1. Mock Loader
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader = mock_loader_cls.return_value
    mock_loader.load_all.return_value = (["stone1"], ["portal1"])

    # 2. Mock Transmuter
    mock_transmuter_cls = mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mock_transmuter = mock_transmuter_cls.return_value
    mock_transmuter.transmute_all.return_value = ["rune1"]

    # 3. Mock Scribe
    mock_scribe_cls = mocker.patch("lychd.system.services.scribe.ScribeService")
    mock_scribe = mock_scribe_cls.return_value

    # 4. Mock Subprocess & Which
    mock_subprocess = mocker.patch("subprocess.run")
    mock_which = mocker.patch("shutil.which")
    mock_which.return_value = "/usr/bin/systemctl"

    result = runner.invoke(bind_quadlets)

    assert result.exit_code == 0
    assert "Transmutation" in result.output
    assert "The circle is bound" in result.output

    # Verify interactions
    mock_loader_cls.assert_called_once()
    mock_loader.load_all.assert_called_once()

    mock_transmuter_cls.assert_called_once()
    mock_transmuter.transmute_all.assert_called_once_with(["stone1"])

    mock_scribe_cls.assert_called_once()
    mock_scribe.generate_all.assert_called_once_with(["rune1"])

    mock_subprocess.assert_called_once_with(["/usr/bin/systemctl", "--user", "daemon-reload"], check=True)


def test_bind_quadlets_systemd_failure(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify we catch subprocess errors if systemd fails."""
    mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mocker.patch("lychd.system.services.scribe.ScribeService")
    mocker.patch("shutil.which").return_value = "/usr/bin/systemctl"

    # Simulate systemd failure
    mock_subprocess = mocker.patch("subprocess.run")
    from subprocess import CalledProcessError

    mock_subprocess.side_effect = CalledProcessError(1, "systemctl")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output
