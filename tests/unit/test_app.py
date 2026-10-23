"""Server-visible process-count guard at the application factory boundary."""

from __future__ import annotations

import sys

import pytest
from pytest_mock import MockerFixture

from lychd.app import AppInit, create_app
from lychd.interface.server_policy import (
    ServerRuntimePolicyError,
    evaluate_server_runtime_policy,
    validate_server_environment,
)

_POLICY_ENVIRONMENT_KEYS = (
    "GRANIAN_HOST",
    "GRANIAN_METRICS_ENABLED",
    "GRANIAN_PORT",
    "GRANIAN_RELOAD",
    "GRANIAN_RELOAD_PATHS",
    "GRANIAN_RELOAD_INCLUDE",
    "GRANIAN_RELOAD_EXCLUDE",
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
            "0.0.0.0",  # noqa: S104 - detected external server topology under test
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
    ("arguments", "host", "port", "pdb"),
    [
        (("-dH::1",), "::1", 8000, False),
        (("-dPH::1", "-p7445"), "::1", 7445, True),
        (("-dPp7445", "-H127.0.0.1"), "127.0.0.1", 7445, True),
        (("-dPW1", "-H", "::1", "-p", "7445"), "::1", 7445, True),
        (("-dP", "-H::1", "-W1"), "::1", 8000, True),
        (("--debug", "--use-pdb", "-H=::1"), "::1", 8000, True),
    ],
)
def test_native_short_clusters_preserve_owned_listener_and_debug_grammar(
    arguments: tuple[str, ...],
    host: str,
    port: int,
    *,
    pdb: bool,
) -> None:
    policy = evaluate_server_runtime_policy(
        environment={},
        default_listener_port=8000,
        server_arguments=arguments,
    )

    assert policy.listener_host == host
    assert policy.listener_port == port
    assert policy.debug is True
    assert policy.pdb is pdb


def test_native_short_grammar_refuses_unknown_prefixes() -> None:
    with pytest.raises(ServerRuntimePolicyError, match="does not support short option -z"):
        evaluate_server_runtime_policy(environment={}, server_arguments=("-zH127.0.0.1",))


@pytest.mark.parametrize(
    ("arguments", "metrics_environment", "enabled"),
    [
        (("--metrics", "--metrics-address=0.0.0.0"), "", True),
        (("--no-metrics", "--metrics"), "false", True),
        (("--metrics", "--no-metrics"), "true", False),
        (("--no-metrics",), "true", False),
        (("--metrics-address=0.0.0.0",), "", False),
        *(((), value, True) for value in ("1", "true", "yes", "on", "t", "y", " TRUE ")),
        *(((), value, False) for value in ("", "0", "false", "no", "off", "f", "n", " FALSE ", " ")),
    ],
)
def test_native_metrics_policy_refuses_only_effective_enablement(
    arguments: tuple[str, ...],
    metrics_environment: str,
    *,
    enabled: bool,
) -> None:
    environment = {
        "GRANIAN_METRICS_ENABLED": metrics_environment,
        "GRANIAN_METRICS_ADDRESS": "0.0.0.0",  # noqa: S104 - inert exporter setting under test
    }
    if enabled:
        with pytest.raises(ServerRuntimePolicyError, match="does not support the Granian metrics listener"):
            evaluate_server_runtime_policy(environment=environment, server_arguments=arguments)
    else:
        policy = evaluate_server_runtime_policy(environment=environment, server_arguments=arguments)
        assert policy.listener_host == "127.0.0.1"


def test_native_policy_uses_only_supplied_environment_without_server_callbacks(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("GRANIAN_METRICS_ENABLED", "true")
    path_conversion = mocker.patch("click.Path.convert")
    application = mocker.patch("lychd.app.create_app")

    policy = evaluate_server_runtime_policy(
        environment={"GRANIAN_METRICS_ENABLED": "false"},
        server_arguments=(),
    )
    assert policy.listener_host == "127.0.0.1"
    with pytest.raises(ServerRuntimePolicyError, match="does not support option --log-config"):
        evaluate_server_runtime_policy(
            environment={"GRANIAN_METRICS_ENABLED": "false"},
            server_arguments=("--log-config", "nonexistent-server-log-config.json"),
        )
    path_conversion.assert_not_called()
    application.assert_not_called()


@pytest.mark.parametrize(
    "variable",
    [
        "GRANIAN_WORKERS_KILL_TIMEOUT",
        "GRANIAN_WORKERS_LIFETIME",
        "GRANIAN_RUNTIME_THREADS",
        "GRANIAN_LOOP",
        "GRANIAN_HTTP",
        "GRANIAN_SSL_CERTIFICATE",
        "GRANIAN_STATIC_PATH_MOUNT",
        "GRANIAN_LOG_CONFIG",
        "GRANIAN_METRICS_PORT",
        "GRANIAN_UNRECOGNIZED_CONTROL",
        "LITESTAR_SSL_CERT_PATH",
        "LITESTAR_GRANIAN_IN_SUBPROCESS",
    ],
)
def test_shared_environment_policy_refuses_retired_controls_without_values(variable: str) -> None:
    with pytest.raises(ServerRuntimePolicyError, match=variable) as error:
        validate_server_environment({variable: "private-value"})
    assert "private-value" not in str(error.value)
    validate_server_environment({variable: ""})


@pytest.mark.parametrize("option", ["--workers", "--wc", "--web-concurrency", "-W"])
def test_native_policy_retains_one_worker_aliases(option: str) -> None:
    policy = evaluate_server_runtime_policy(environment={}, server_arguments=(option, "1"))
    assert policy.listener_host == "127.0.0.1"


@pytest.mark.parametrize(
    ("arguments", "environment", "host", "port"),
    [
        (("--host", "::1", "--port", "7134"), {"LITESTAR_HOST": "127.0.0.1", "LITESTAR_PORT": "7444"}, "::1", 7134),
        (
            (),
            {"LITESTAR_HOST": "::1", "GRANIAN_HOST": "127.0.0.1", "LITESTAR_PORT": "7444", "GRANIAN_PORT": "7555"},
            "::1",
            7444,
        ),
        ((), {"GRANIAN_HOST": "::1", "GRANIAN_PORT": "7555"}, "::1", 7555),
        ((), {}, "127.0.0.1", 7666),
    ],
)
def test_native_listener_precedence(
    arguments: tuple[str, ...],
    environment: dict[str, str],
    host: str,
    port: int,
) -> None:
    policy = evaluate_server_runtime_policy(
        environment=environment,
        default_listener_port=7666,
        server_arguments=arguments,
    )
    assert policy.listener_host == host
    assert policy.listener_port == port


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "t", "y", " TRUE "])
def test_native_debug_and_pdb_environment(value: str) -> None:
    policy = evaluate_server_runtime_policy(
        environment={"LITESTAR_DEBUG": value, "LITESTAR_PDB": value},
        server_arguments=(),
    )
    assert policy.debug is True
    assert policy.pdb is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "f", "n", " FALSE ", " "])
def test_native_debug_and_pdb_environment_accepts_disabled_forms(value: str) -> None:
    policy = evaluate_server_runtime_policy(
        environment={"LITESTAR_DEBUG": value, "LITESTAR_PDB": value},
        server_arguments=(),
    )
    assert policy.debug is False
    assert policy.pdb is False


@pytest.mark.parametrize("variable", ["LITESTAR_DEBUG", "LITESTAR_PDB", "GRANIAN_METRICS_ENABLED"])
def test_native_boolean_environment_errors_do_not_disclose_values(variable: str) -> None:
    with pytest.raises(ServerRuntimePolicyError, match=variable) as error:
        evaluate_server_runtime_policy(environment={variable: "private-value"}, server_arguments=())
    assert "private-value" not in str(error.value)


@pytest.mark.parametrize(
    ("environment", "arguments", "expected_message"),
    [
        ({"GRANIAN_RELOAD_PATHS": "."}, (), "does not support GRANIAN_RELOAD_PATHS"),
        ({"GRANIAN_RELOAD_INCLUDE": "*.py"}, (), "does not support GRANIAN_RELOAD_INCLUDE"),
        ({"GRANIAN_RELOAD_EXCLUDE": "*.tmp"}, (), "does not support GRANIAN_RELOAD_EXCLUDE"),
        ({}, ("--reload-paths", "."), "does not support Litestar reload mode"),
        ({}, ("--reload-paths=.",), "does not support Litestar reload mode"),
    ],
)
def test_runtime_policy_rejects_implicit_reload_controls(
    environment: dict[str, str],
    arguments: tuple[str, ...],
    expected_message: str,
) -> None:
    """Watch selections cannot request a reload process through either path."""
    with pytest.raises(ServerRuntimePolicyError, match=expected_message):
        evaluate_server_runtime_policy(environment=environment, server_arguments=arguments)
    with pytest.raises(ServerRuntimePolicyError, match=expected_message):
        evaluate_server_runtime_policy(environment=environment, argv=("litestar", "run", *arguments))


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
