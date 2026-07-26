from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from lychd.system.operator.process import (
    InputProcessRunner,
    ProcessInvocationError,
    ProcessResult,
    SubprocessRunner,
)
from lychd.system.services.secrets import PodmanSecretStore, PodmanSecretStoreError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


def _runner(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock(spec=SubprocessRunner)


def test_secret_store_requires_podman_binary(mocker: MockerFixture) -> None:
    mocker.patch(
        "lychd.system.services.secrets.trusted_host_tool",
        return_value=None,
    )

    with pytest.raises(PodmanSecretStoreError, match="Podman is required"):
        PodmanSecretStore()


def test_secret_store_exists_uses_bounded_podman_probe(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run.return_value = ProcessResult(
        argv=("/usr/bin/podman", "secret", "exists", "alpha"),
        returncode=0,
    )

    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    assert store.exists("alpha") is True
    runner.run.assert_called_once_with(
        ("/usr/bin/podman", "secret", "exists", "alpha"),
        timeout_s=5.0,
    )


def test_secret_store_treats_only_exit_one_as_absent(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run.side_effect = (
        ProcessResult(argv=("/usr/bin/podman",), returncode=1),
        ProcessResult(
            argv=("/usr/bin/podman",),
            returncode=125,
            stderr="storage unavailable",
        ),
    )
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    assert store.exists("missing") is False
    with pytest.raises(PodmanSecretStoreError, match="storage unavailable"):
        store.exists("unknown")


def test_secret_store_wraps_probe_timeout(mocker: MockerFixture) -> None:
    runner = _runner(mocker)
    runner.run.side_effect = ProcessInvocationError("timed out")
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    with pytest.raises(PodmanSecretStoreError, match="timed out"):
        store.exists("alpha")


def test_secret_store_ensure_present_creates_only_when_missing(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run_with_input.return_value = ProcessResult(
        argv=("/usr/bin/podman", "secret", "create", "alpha", "-"),
        returncode=0,
    )
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )
    mocker.patch.object(store, "exists", return_value=False)

    created = store.ensure_present("alpha", "value")

    assert created is True
    runner.run_with_input.assert_called_once_with(
        ("/usr/bin/podman", "secret", "create", "alpha", "-"),
        timeout_s=30.0,
        input_text="value",
    )


def test_secret_store_ensure_present_preserves_a_raced_secret(
    mocker: MockerFixture,
) -> None:
    """Create-if-absent never replaces an operator secret that wins the race."""
    runner = _runner(mocker)
    runner.run_with_input.return_value = ProcessResult(
        argv=("/usr/bin/podman", "secret", "create", "alpha", "-"),
        returncode=125,
        stderr="secret already exists",
    )
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )
    exists = mocker.patch.object(store, "exists", side_effect=(False, True))

    created = store.ensure_present("alpha", "generated-value")

    assert created is False
    assert exists.call_count == 2
    argv = runner.run_with_input.call_args.args[0]
    assert "--replace" not in argv


@pytest.mark.parametrize("version", ["podman version 5.4.0", "podman version 6.1.2"])
def test_secret_store_accepts_supported_quadlet_version(
    mocker: MockerFixture,
    version: str,
) -> None:
    runner = _runner(mocker)
    runner.run.return_value = ProcessResult(
        argv=("/usr/bin/podman", "--version"),
        returncode=0,
        stdout=version,
    )

    PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    ).require_quadlet_version()


@pytest.mark.parametrize("version", ["podman version 4.9.4", "podman version 5.3.2"])
def test_secret_store_rejects_unsupported_quadlet_version(
    mocker: MockerFixture,
    version: str,
) -> None:
    runner = _runner(mocker)
    runner.run.return_value = ProcessResult(
        argv=("/usr/bin/podman", "--version"),
        returncode=0,
        stdout=version,
    )
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    with pytest.raises(PodmanSecretStoreError, match="Podman >= 5.4"):
        store.require_quadlet_version()


def test_secret_store_create_uses_bounded_non_echoed_stdin(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run_with_input.return_value = ProcessResult(
        argv=("/usr/bin/podman", "secret", "create"),
        returncode=125,
        stderr="boom",
    )
    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    with pytest.raises(PodmanSecretStoreError, match="Failed to create podman secret"):
        store.create("alpha", "value")

    runner.run_with_input.assert_called_once_with(
        (
            "/usr/bin/podman",
            "secret",
            "create",
            "--replace",
            "alpha",
            "-",
        ),
        timeout_s=30.0,
        input_text="value",
    )
