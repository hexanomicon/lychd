"""Server-visible process-count guard at the application factory boundary."""

from __future__ import annotations

import sys

import pytest
from pytest_mock import MockerFixture

from lychd.app import AppInit, create_app
from lychd.interface.server_policy import ServerRuntimePolicyError, evaluate_server_runtime_policy

_POLICY_ENVIRONMENT_KEYS = (
    "GRANIAN_HOST",
    "GRANIAN_PORT",
    "GRANIAN_RELOAD",
    "GRANIAN_WORKERS",
    "LITESTAR_WEB_CONCURRENCY",
    "LITESTAR_HOST",
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
    ("environment", "arguments", "expected_message"),
    [
        ({"GRANIAN_WORKERS": "2"}, (), "GRANIAN_WORKERS=1"),
        ({"LITESTAR_WEB_CONCURRENCY": "2"}, (), "LITESTAR_WEB_CONCURRENCY=1"),
        ({"WEB_CONCURRENCY": "2"}, (), "WEB_CONCURRENCY=1"),
        ({}, ("--workers", "2"), "exactly one ASGI worker"),
        ({}, ("--workers=3",), "exactly one ASGI worker"),
        ({}, ("-W", "2"), "exactly one ASGI worker"),
        ({}, ("-W2",), "exactly one ASGI worker"),
        ({}, ("--wc=2",), "exactly one ASGI worker"),
        ({}, ("--web-concurrency", "3"), "exactly one ASGI worker"),
        ({"LITESTAR_RELOAD": "enabled"}, (), "does not support Litestar reload mode"),
        ({"GRANIAN_RELOAD": "enabled"}, (), "does not support Granian reload mode"),
        ({"LITESTAR_RELOAD_DIRS": "enabled"}, (), "does not support LITESTAR_RELOAD_DIRS"),
        ({"LITESTAR_RELOAD_INCLUDES": "enabled"}, (), "does not support LITESTAR_RELOAD_INCLUDES"),
        ({"LITESTAR_RELOAD_EXCLUDES": "enabled"}, (), "does not support LITESTAR_RELOAD_EXCLUDES"),
        ({}, ("-r",), "does not support Litestar reload mode"),
        ({}, ("--reload",), "does not support Litestar reload mode"),
        ({}, ("-R", "src"), "does not support Litestar reload mode"),
        ({}, ("-Rsrc",), "does not support Litestar reload mode"),
        ({}, ("--reload-dir=src",), "does not support Litestar reload mode"),
        ({}, ("-I*.py",), "does not support Litestar reload mode"),
        ({}, ("--reload-include", "*.py"), "does not support Litestar reload mode"),
        ({}, ("-E*.tmp",), "does not support Litestar reload mode"),
        ({}, ("--reload-exclude=*.tmp",), "does not support Litestar reload mode"),
    ],
)
def test_runtime_policy_rejects_every_multiworker_and_reload_spelling(
    environment: dict[str, str],
    arguments: tuple[str, ...],
    expected_message: str,
) -> None:
    with pytest.raises(ServerRuntimePolicyError, match=expected_message):
        evaluate_server_runtime_policy(
            environment=environment,
            server_arguments=arguments,
        )


@pytest.mark.parametrize(
    ("environment", "arguments", "expected_message"),
    [
        ({"GRANIAN_WORKERS": "2"}, (), "GRANIAN_WORKERS=1"),
        ({}, ("--reload",), "does not support Litestar reload mode"),
    ],
)
def test_app_factory_translates_detected_server_policy_failures(
    monkeypatch: pytest.MonkeyPatch,
    environment: dict[str, str],
    arguments: tuple[str, ...],
    expected_message: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    for variable, value in environment.items():
        monkeypatch.setenv(variable, value)
    monkeypatch.setattr(sys, "argv", ["/venv/bin/litestar", "run", *arguments])
    monkeypatch.setattr(sys, "orig_argv", ["python"])

    with pytest.raises(RuntimeError, match=expected_message):
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
    assert policy.listener_host is None


@pytest.mark.parametrize(
    ("variable", "port"),
    [("LITESTAR_PORT", 9000), ("GRANIAN_PORT", 8000)],
)
def test_runtime_policy_reads_selected_port_from_environment(variable: str, port: int) -> None:
    policy = evaluate_server_runtime_policy(
        environment={variable: str(port)},
        argv=["python"],
        original_argv=["python"],
    )

    assert policy.listener_port == port
    assert policy.listener_host is None


def test_runtime_policy_falls_back_to_configured_listener_port() -> None:
    policy = evaluate_server_runtime_policy(
        environment={},
        default_listener_port=7444,
        server_arguments=(),
    )

    assert policy.listener_port == 7444
    assert policy.listener_host == "127.0.0.1"


@pytest.mark.parametrize(
    "arguments",
    [
        ("-dH::1",),
        ("-dPH::1", "-p7445"),
        ("-dPp7445", "-H127.0.0.1"),
        ("-dPW1", "-H", "::1", "-p", "7445"),
        ("-dP", "-H::1", "-W1"),
    ],
)
def test_native_short_clusters_agree_with_the_delegated_click_parser(
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
) -> None:
    """Compare admitted authority with the real server parser without starting it."""
    from litestar_granian.cli import run_command

    _clear_policy_environment(monkeypatch)
    policy = evaluate_server_runtime_policy(
        environment={},
        default_listener_port=8000,
        server_arguments=arguments,
    )

    with run_command.make_context("run", list(arguments)) as context:
        assert policy.listener_host == context.params["host"]
        assert policy.listener_port == context.params["port"]
        assert context.params["wc"] == 1


def test_native_short_grammar_refuses_unknown_prefixes() -> None:
    with pytest.raises(ServerRuntimePolicyError, match="does not support short option -z"):
        evaluate_server_runtime_policy(environment={}, server_arguments=("-zH127.0.0.1",))


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("LITESTAR_RELOAD", ""),
        ("LITESTAR_RELOAD", "0"),
        ("LITESTAR_RELOAD", "false"),
        ("LITESTAR_RELOAD", "FALSE"),
        ("LITESTAR_RELOAD", "no"),
        ("LITESTAR_RELOAD", "off"),
        ("GRANIAN_RELOAD", "false"),
    ],
)
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
