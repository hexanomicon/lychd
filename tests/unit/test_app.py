"""Server-visible process-count guard at the application factory boundary."""

from __future__ import annotations

import sys

import pytest
from pytest_mock import MockerFixture

from lychd.app import AppInit, create_app
from lychd.interface.server_policy import evaluate_server_runtime_policy

_POLICY_ENVIRONMENT_KEYS = (
    "GRANIAN_PORT",
    "GRANIAN_RELOAD",
    "GRANIAN_WORKERS",
    "LITESTAR_WEB_CONCURRENCY",
    "LITESTAR_PORT",
    "LITESTAR_RELOAD",
    "LITESTAR_RELOAD_DIRS",
    "LITESTAR_RELOAD_EXCLUDES",
    "LITESTAR_RELOAD_INCLUDES",
    "WEB_CONCURRENCY",
)


def _clear_policy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in _POLICY_ENVIRONMENT_KEYS:
        monkeypatch.delenv(variable, raising=False)


@pytest.mark.parametrize(
    "variable",
    ["GRANIAN_WORKERS", "LITESTAR_WEB_CONCURRENCY", "WEB_CONCURRENCY"],
)
def test_app_factory_rejects_every_server_worker_environment(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv(variable, "2")

    with pytest.raises(RuntimeError, match=rf"{variable}=1"):
        create_app()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--workers", "2"],
        ["--workers=2"],
        ["--wc=2"],
        ["--web-concurrency", "2"],
        ["-W2"],
    ],
)
def test_app_factory_rejects_direct_server_cli_multiworker_arguments(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["/venv/bin/litestar", "run", *arguments])
    monkeypatch.setattr(sys, "orig_argv", ["python"])

    with pytest.raises(RuntimeError, match="exactly one ASGI worker"):
        create_app()


@pytest.mark.parametrize(
    "variable",
    [
        "LITESTAR_RELOAD",
        "LITESTAR_RELOAD_DIRS",
        "LITESTAR_RELOAD_INCLUDES",
        "LITESTAR_RELOAD_EXCLUDES",
        "GRANIAN_RELOAD",
    ],
)
def test_app_factory_rejects_reload_environment(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv(variable, "enabled")

    with pytest.raises(RuntimeError, match="does not support"):
        create_app()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--reload"],
        ["-r"],
        ["--reload-dir=src"],
        ["-Rsrc"],
        ["--reload-include", "*.py"],
        ["-E*.tmp"],
    ],
)
def test_app_factory_rejects_direct_server_reload_arguments(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["/venv/bin/litestar", "run", *arguments])
    monkeypatch.setattr(sys, "orig_argv", ["python"])

    with pytest.raises(RuntimeError, match="does not support Litestar reload mode"):
        create_app()


def test_runtime_policy_accepts_one_worker_and_resolves_direct_granian_port() -> None:
    policy = evaluate_server_runtime_policy(
        environment={},
        argv=[
            "/venv/bin/granian",
            "--interface",
            "asgi",
            "--factory",
            "--workers",
            "1",
            "--host",
            "0.0.0.0",  # noqa: S104 - exact shipped Containerfile topology under test
            "--port",
            "8000",
            "lychd.app:create_app",
        ],
        original_argv=["granian"],
    )

    assert policy.listener_port == 8000


def test_runtime_policy_reads_litestar_selected_port_from_environment() -> None:
    policy = evaluate_server_runtime_policy(
        environment={"LITESTAR_PORT": "9000"},
        argv=["python"],
        original_argv=["python"],
    )

    assert policy.listener_port == 9000


def test_runtime_policy_reads_granian_selected_port_from_environment() -> None:
    policy = evaluate_server_runtime_policy(
        environment={"GRANIAN_PORT": "8000"},
        argv=["python"],
        original_argv=["python"],
    )

    assert policy.listener_port == 8000


def test_runtime_policy_falls_back_to_configured_listener_port() -> None:
    policy = evaluate_server_runtime_policy(
        environment={},
        default_listener_port=7444,
        server_arguments=(),
    )

    assert policy.listener_port == 7444


@pytest.mark.parametrize("variable", ["LITESTAR_RELOAD", "GRANIAN_RELOAD"])
@pytest.mark.parametrize("value", ["", "0", "false", "FALSE", "no", "off"])
def test_runtime_policy_accepts_explicitly_disabled_reload_environment(
    variable: str,
    value: str,
) -> None:
    policy = evaluate_server_runtime_policy(
        environment={variable: value},
        server_arguments=(),
    )

    assert policy.listener_port is None


def test_app_factory_passes_the_selected_listener_port_to_app_init(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv("LITESTAR_PORT", "8000")
    monkeypatch.setattr(sys, "argv", ["python"])
    monkeypatch.setattr(sys, "orig_argv", ["python"])
    litestar = mocker.patch("lychd.app.Litestar")

    create_app()

    plugin = litestar.call_args.kwargs["plugins"][0]
    assert isinstance(plugin, AppInit)
    assert plugin.listener_port == 8000
