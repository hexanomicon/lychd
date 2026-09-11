"""Generated container hardening is fixed and secrets retain source identity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader
from pydantic import SecretStr, ValidationError

from lychd.config.settings.server import DatabaseSettings, ServerSettings, WebSettings
from lychd.system.operator.process import ProcessResult
from lychd.system.schemas import QuadletContainer, podman_secret_source
from lychd.system.services.secrets import PodmanSecretStore, PodmanSecretStoreError


@pytest.mark.parametrize(
    "spec",
    [
        "source,type=env",
        "source,type=env,target=/run/secrets/password",
        "source,type=env,target=PASSWORD,mode=0600",
        "source,type=env,type=mount,target=PASSWORD",
        "source,type=unknown",
        "source,type=mount,target=PASSWORD",
        "source,uid=1000",
    ],
)
def test_secret_specs_reject_ambiguous_or_mixed_delivery(spec: str) -> None:
    with pytest.raises(ValueError, match=r"secret|Secret"):
        podman_secret_source(spec)


def test_environment_secret_preserves_source_identity() -> None:
    assert podman_secret_source("phoenix-password,type=env,target=PHOENIX_POSTGRES_PASSWORD") == "phoenix-password"


@pytest.mark.parametrize(
    "option",
    [
        "--cap-add=NET_RAW",
        "--cap-add NET_ADMIN",
        "--privileged",
        "--security-opt=no-new-privileges=false",
        "--read-only=false",
        "--read-only-tmpfs=false",
    ],
)
def test_raw_podman_options_cannot_override_fixed_container_policy(option: str) -> None:
    with pytest.raises(ValueError, match="cannot override"):
        QuadletContainer(description="runtime", image="example/runtime", container_name="runtime", podman_args=[option])


@pytest.mark.parametrize("read_only", [True, False])
def test_generated_policy_drops_network_caps_and_bounds_writable_tmpfs(*, read_only: bool) -> None:
    manifest = QuadletContainer(
        description="runtime", image="example/runtime", container_name="runtime", read_only=read_only
    )
    templates = Path(__file__).parents[3] / "src/lychd/system/templates"
    environment = Environment(loader=FileSystemLoader(templates), autoescape=False)  # noqa: S701 - systemd text
    rendered = environment.get_template("container.jinja").render(**manifest.model_dump())
    assert "NoNewPrivileges=true" in rendered
    if read_only:
        assert "DropCapability=all" in rendered
        assert "ReadOnly=true" in rendered
        assert "ReadOnlyTmpfs=true" in rendered
    else:
        assert "DropCapability=CAP_NET_RAW CAP_NET_ADMIN" in rendered


@pytest.mark.parametrize("password", ["short", "x" * 257, "x" * 32 + "\n", "x" * 32 + "é", "x" * 32 + " "])
def test_local_access_password_rejects_guessable_or_terminal_active_value(password: str) -> None:
    with pytest.raises(ValidationError):
        WebSettings(access_password=SecretStr(password))


def test_privileged_credentials_cannot_alias() -> None:
    with pytest.raises(ValueError, match="distinct"):
        ServerSettings(web=WebSettings(access_password_secret="lychd_runtime_db_password"))  # noqa: S106 - secret name
    with pytest.raises(ValueError, match="distinct"):
        DatabaseSettings(runtime_user="lich")


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        [{"Spec": {"Name": "secret-prefix-match"}, "SecretData": "do-not-leak"}],
        [{"Spec": {"Name": "secret"}, "SecretData": "do-not-leak"}, {}],
        [{"Spec": None, "SecretData": "do-not-leak"}],
    ],
)
def test_podman_secret_read_rejects_nonexact_or_malformed_results_without_values(payload: Any) -> None:
    runner = MagicMock()
    runner.run.return_value = ProcessResult(argv=("podman",), returncode=0, stdout=json.dumps(payload))
    store = PodmanSecretStore("/usr/bin/podman", runner=runner)
    with pytest.raises(PodmanSecretStoreError) as error:
        store.read("secret")
    assert "do-not-leak" not in str(error.value)
    assert error.value.__suppress_context__ is True


def test_podman_secret_read_returns_exact_masked_value() -> None:
    runner = MagicMock()
    runner.run.return_value = ProcessResult(
        argv=("podman",),
        returncode=0,
        stdout=json.dumps([{"Spec": {"Name": "secret"}, "SecretData": "synthetic-value"}]),
    )
    value = PodmanSecretStore("/usr/bin/podman", runner=runner).read("secret")
    assert value.get_secret_value() == "synthetic-value"
    assert "synthetic-value" not in repr(value)
    runner.run.assert_called_once_with(
        ("/usr/bin/podman", "secret", "inspect", "--showsecret", "secret"), timeout_s=5.0
    )
