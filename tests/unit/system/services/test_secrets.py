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


def test_secret_store_exists_uses_bounded_podman_probe(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run.return_value = ProcessResult(
        argv=("/usr/bin/podman", "--remote=false", "secret", "exists", "alpha"),
        returncode=0,
    )

    store = PodmanSecretStore(
        "/usr/bin/podman",
        runner=cast("InputProcessRunner", runner),
    )

    assert store.exists("alpha") is True
    runner.run.assert_called_once_with(
        ("/usr/bin/podman", "--remote=false", "secret", "exists", "alpha"),
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
        argv=("/usr/bin/podman", "--remote=false", "secret", "create", "alpha", "-"),
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
        ("/usr/bin/podman", "--remote=false", "secret", "create", "alpha", "-"),
        timeout_s=30.0,
        input_text="value",
    )


def test_secret_store_ensure_present_preserves_a_raced_secret(
    mocker: MockerFixture,
) -> None:
    """Create-if-absent never replaces an operator secret that wins the race."""
    runner = _runner(mocker)
    runner.run_with_input.return_value = ProcessResult(
        argv=("/usr/bin/podman", "--remote=false", "secret", "create", "alpha", "-"),
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


def test_secret_store_create_uses_bounded_non_echoed_stdin(
    mocker: MockerFixture,
) -> None:
    runner = _runner(mocker)
    runner.run_with_input.return_value = ProcessResult(
        argv=("/usr/bin/podman", "--remote=false", "secret", "create"),
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
            "--remote=false",
            "secret",
            "create",
            "--replace",
            "alpha",
            "-",
        ),
        timeout_s=30.0,
        input_text="value",
    )


def test_secret_store_ignores_ambient_remote_selection_and_keeps_values_on_stdin(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    monkeypatch.setenv("CONTAINER_HOST", "ssh://wrong-engine.invalid/run/podman.sock")
    monkeypatch.setenv("CONTAINER_CONNECTION", "untrusted-connection")
    value = "private-test-value"
    completed = mocker.Mock(
        returncode=0,
        stdout=json.dumps([{"Spec": {"Name": "alpha"}, "SecretData": value}]),
        stderr="",
    )
    process = mocker.patch("lychd.system.operator.process.subprocess.run", return_value=completed)
    store = PodmanSecretStore("/usr/bin/podman")
    assert store.read("alpha").get_secret_value() == value
    assert store.exists("alpha") is True
    store.create("alpha", value)
    process.side_effect = (mocker.Mock(returncode=1, stdout="", stderr=""), completed)
    assert store.ensure_present("alpha", value) is True
    commands = [call.args[0] for call in process.call_args_list]
    assert commands == [
        ("/usr/bin/podman", "--remote=false", "secret", "inspect", "--showsecret", "alpha"),
        ("/usr/bin/podman", "--remote=false", "secret", "exists", "alpha"),
        ("/usr/bin/podman", "--remote=false", "secret", "create", "--replace", "alpha", "-"),
        ("/usr/bin/podman", "--remote=false", "secret", "exists", "alpha"),
        ("/usr/bin/podman", "--remote=false", "secret", "create", "alpha", "-"),
    ]
    for call in process.call_args_list:
        assert value not in call.args[0]
        if "create" in call.args[0]:
            assert call.kwargs["input"] == value
        else:
            assert "input" not in call.kwargs
        assert "env" not in call.kwargs
