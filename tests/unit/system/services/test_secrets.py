from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from lychd.system.services.secrets import PodmanSecretStore, PodmanSecretStoreError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_secret_store_requires_podman_binary(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.services.secrets.shutil.which", return_value=None)

    with pytest.raises(PodmanSecretStoreError, match="Podman is required"):
        PodmanSecretStore()


def test_secret_store_exists_uses_podman_secret_exists(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.services.secrets.shutil.which", return_value="/usr/bin/podman")
    mock_run = mocker.patch("lychd.system.services.secrets.subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    store = PodmanSecretStore()
    assert store.exists("alpha") is True
    mock_run.assert_called_once_with(
        ["/usr/bin/podman", "secret", "exists", "alpha"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_secret_store_ensure_present_creates_only_when_missing(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.services.secrets.shutil.which", return_value="/usr/bin/podman")
    store = PodmanSecretStore()
    mocker.patch.object(store, "exists", return_value=False)
    create = mocker.patch.object(store, "create")

    created = store.ensure_present("alpha", "value")

    assert created is True
    create.assert_called_once_with("alpha", "value")


def test_secret_store_create_raises_domain_error(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.services.secrets.shutil.which", return_value="/usr/bin/podman")
    mock_run = mocker.patch("lychd.system.services.secrets.subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=125,
        cmd=["podman", "secret", "create"],
        stderr="boom",
    )
    store = PodmanSecretStore()

    with pytest.raises(PodmanSecretStoreError, match="Failed to create podman secret"):
        store.create("alpha", "value")
