"""Pure server-runtime policy shared by CLI and application assembly."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath

__all__ = (
    "ServerRuntimePolicy",
    "ServerRuntimePolicyError",
    "evaluate_server_runtime_policy",
    "validate_host_actuator",
    "validate_server_environment",
)

_WORKER_ENVIRONMENT_KEYS = (
    "GRANIAN_WORKERS",
    "LITESTAR_WEB_CONCURRENCY",
    "WEB_CONCURRENCY",
)
_RELOAD_ENVIRONMENT_KEYS = (
    "LITESTAR_RELOAD_DIRS",
    "LITESTAR_RELOAD_INCLUDES",
    "LITESTAR_RELOAD_EXCLUDES",
    "GRANIAN_RELOAD_PATHS",
    "GRANIAN_RELOAD_INCLUDE",
    "GRANIAN_RELOAD_EXCLUDE",
)
_RELOAD_FLAG_ENVIRONMENT_KEYS = ("LITESTAR_RELOAD", "GRANIAN_RELOAD")
_LISTENER_PORT_ENVIRONMENT_KEYS = ("LITESTAR_PORT", "GRANIAN_PORT")
_LISTENER_HOST_ENVIRONMENT_KEYS = ("LITESTAR_HOST", "GRANIAN_HOST")
_ALTERNATE_LISTENER_ENVIRONMENT_KEYS = (
    "LITESTAR_FILE_DESCRIPTOR",
    "LITESTAR_UNIX_DOMAIN_SOCKET",
    "GRANIAN_FILE_DESCRIPTOR",
    "GRANIAN_UDS",
)
_DISABLED_ENVIRONMENT_VALUES = {"", "0", "false", "no", "off"}
_FALSE_BOOLEAN_VALUES = _DISABLED_ENVIRONMENT_VALUES | {"f", "n"}
_TRUE_BOOLEAN_VALUES = {"1", "true", "yes", "on", "t", "y"}
_SUPPORTED_GRANIAN_ENVIRONMENT_KEYS = frozenset(
    {
        *_WORKER_ENVIRONMENT_KEYS,
        *_RELOAD_ENVIRONMENT_KEYS,
        *_RELOAD_FLAG_ENVIRONMENT_KEYS,
        *_LISTENER_PORT_ENVIRONMENT_KEYS,
        *_LISTENER_HOST_ENVIRONMENT_KEYS,
        *_ALTERNATE_LISTENER_ENVIRONMENT_KEYS,
        "GRANIAN_METRICS_ENABLED",
        "GRANIAN_METRICS_ADDRESS",
    }
)
_UNSUPPORTED_LITESTAR_ENVIRONMENT_KEYS = frozenset(
    {
        "LITESTAR_SSL_CERT_PATH",
        "LITESTAR_SSL_KEY_PATH",
        "LITESTAR_CREATE_SELF_SIGNED_CERT",
        "LITESTAR_SSL_CLIENT_VERIFY",
    }
)
_SERVER_CLI_NAMES = frozenset({"granian", "litestar"})
_WORKER_OPTIONS = frozenset({"--workers", "-W", "--wc", "--web-concurrency"})
_LONG_WORKER_OPTIONS = ("--workers", "--wc", "--web-concurrency")
_RELOAD_OPTIONS = frozenset(
    {
        "-r",
        "--reload",
        "-R",
        "--reload-dir",
        "--reload-paths",
        "-I",
        "--reload-include",
        "-E",
        "--reload-exclude",
    }
)
_LONG_RELOAD_VALUE_OPTIONS = (
    "--reload-dir",
    "--reload-paths",
    "--reload-include",
    "--reload-exclude",
)
_SHORT_RELOAD_VALUE_OPTIONS = ("-R", "-I", "-E")
_PORT_OPTIONS = frozenset({"-p", "--port"})
_MAX_TCP_PORT = 65535


class ServerRuntimePolicyError(ValueError):
    """A server setting would break the single-process, owned-listener runtime."""


@dataclass(frozen=True, slots=True)
class ServerRuntimePolicy:
    """Validated server facts needed by application assembly."""

    listener_port: int | None


def evaluate_server_runtime_policy(
    *,
    environment: Mapping[str, str],
    default_listener_port: int | None = None,
    argv: Sequence[str] = (),
    original_argv: Sequence[str] = (),
) -> ServerRuntimePolicy:
    """Validate shared single-process controls and resolve the observed port.

    Detectable direct framework launch arguments remain subject to worker and
    reload refusal. Managed entrypoints own their fixed internal listeners.
    """
    arguments = _detected_server_arguments(argv=argv, original_argv=original_argv)
    _validate_environment(environment)
    listener_port = _validate_detected_arguments(arguments)
    if listener_port is None:
        listener_port = _environment_port(environment)
    if listener_port is None and default_listener_port is not None:
        listener_port = _parse_port(str(default_listener_port), source="settings.server.port")
    return ServerRuntimePolicy(listener_port=listener_port)


def _detected_server_arguments(
    *,
    argv: Sequence[str],
    original_argv: Sequence[str],
) -> tuple[str, ...]:
    if not argv:
        return ()
    executable = PurePath(argv[0]).name.casefold()
    original_executables = {PurePath(argument).name.casefold() for argument in original_argv[:4]}
    if executable in _SERVER_CLI_NAMES or not _SERVER_CLI_NAMES.isdisjoint(original_executables):
        return tuple(argv[1:])
    return ()


def validate_host_actuator(platform: str, actuator: str) -> None:
    """Keep the native process supervisor outside the Linux Vessel."""
    if platform in {"darwin", "win32"}:
        if actuator != "native-process":
            message = "Personal desktop hosting requires the native-process actuator."
            raise ServerRuntimePolicyError(message)
    elif actuator == "native-process":
        message = "The native-process actuator is available only on macOS and Windows."
        raise ServerRuntimePolicyError(message)


def validate_server_environment(environment: Mapping[str, str]) -> None:
    """Validate shared process/listener controls without selecting a TCP profile."""
    _validate_environment(environment)


def _validate_environment(environment: Mapping[str, str]) -> None:
    for variable in _WORKER_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "" and not _is_one_worker(value):
            message = f"LychD v1 requires {variable}=1; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)

    _validate_listener_environment(environment)
    if _environment_boolean(environment, "GRANIAN_METRICS_ENABLED"):
        message = "LychD does not support a separate Granian metrics listener."
        raise ServerRuntimePolicyError(message)
    _validate_owned_environment_controls(environment)

    for variable in _RELOAD_FLAG_ENVIRONMENT_KEYS:
        reload_value = environment.get(variable)
        if reload_value is not None and reload_value.casefold() not in _DISABLED_ENVIRONMENT_VALUES:
            server_name = variable.removesuffix("_RELOAD").capitalize()
            message = f"LychD v1 does not support {server_name} reload mode; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)
    for variable in _RELOAD_ENVIRONMENT_KEYS:
        if environment.get(variable) not in {None, ""}:
            message = (
                f"LychD v1 does not support {variable}; "
                "Litestar treats it as reload mode and the run event plane "
                "is process-local."
            )
            raise ServerRuntimePolicyError(message)


def _validate_owned_environment_controls(environment: Mapping[str, str]) -> None:
    for variable, value in environment.items():
        if value and (
            (variable.startswith("GRANIAN_") and variable not in _SUPPORTED_GRANIAN_ENVIRONMENT_KEYS)
            or variable.startswith("LITESTAR_GRANIAN_")
            or variable in _UNSUPPORTED_LITESTAR_ENVIRONMENT_KEYS
        ):
            message = f"LychD server does not support {variable}."
            raise ServerRuntimePolicyError(message)


def _validate_detected_arguments(arguments: Sequence[str]) -> int | None:
    """Guard recognizable external process controls without owning their grammar."""
    listener_port: int | None = None
    for index, argument in enumerate(arguments):
        worker_value = _worker_value(arguments, index)
        if worker_value is not None and not _is_one_worker(worker_value):
            message = "LychD v1 requires exactly one ASGI worker; cross-process RunEventBus is not implemented."
            raise ServerRuntimePolicyError(message)
        if _is_reload_argument(argument):
            message = "LychD v1 does not support Litestar reload mode; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)
        if (port_value := _port_value(arguments, index)) is not None:
            option_name = argument.partition("=")[0] if argument.startswith("--") else argument[:2]
            listener_port = _parse_port(port_value, source=option_name)
    return listener_port


def _worker_value(arguments: Sequence[str], index: int) -> str | None:
    argument = arguments[index]
    if argument in _WORKER_OPTIONS and index + 1 < len(arguments):
        return arguments[index + 1]
    if any(argument.startswith(f"{option}=") for option in _LONG_WORKER_OPTIONS):
        return argument.partition("=")[2]
    if argument.startswith("-W") and argument != "-W":
        return argument[2:].removeprefix("=")
    return None


def _is_reload_argument(argument: str) -> bool:
    return (
        argument in _RELOAD_OPTIONS
        or any(argument.startswith(f"{option}=") for option in _LONG_RELOAD_VALUE_OPTIONS)
        or any(argument.startswith(option) and len(argument) > len(option) for option in _SHORT_RELOAD_VALUE_OPTIONS)
    )


def _port_value(arguments: Sequence[str], index: int) -> str | None:
    argument = arguments[index]
    if argument in _PORT_OPTIONS and index + 1 < len(arguments):
        return arguments[index + 1]
    if argument.startswith("--port="):
        return argument.partition("=")[2]
    if argument.startswith("-p") and argument != "-p":
        return argument[2:].removeprefix("=")
    return None


def _environment_port(environment: Mapping[str, str]) -> int | None:
    for variable in _LISTENER_PORT_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "":
            return _parse_port(value, source=variable)
    return None


def _validate_listener_environment(environment: Mapping[str, str]) -> None:
    for variable in _ALTERNATE_LISTENER_ENVIRONMENT_KEYS:
        if environment.get(variable) not in {None, ""}:
            message = f"LychD does not support {variable}; use the image's fixed TCP listener."
            raise ServerRuntimePolicyError(message)


def _environment_boolean(environment: Mapping[str, str], variable: str) -> bool:
    value = environment.get(variable, "").strip().casefold()
    if value in _FALSE_BOOLEAN_VALUES:
        return False
    if value in _TRUE_BOOLEAN_VALUES:
        return True
    message = f"LychD requires {variable} to name a valid boolean."
    raise ServerRuntimePolicyError(message)


def _parse_port(value: str, *, source: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        message = f"LychD requires {source} to name a valid TCP port."
        raise ServerRuntimePolicyError(message) from exc
    if not 1 <= port <= _MAX_TCP_PORT:
        message = f"LychD requires {source} to name a valid TCP port."
        raise ServerRuntimePolicyError(message)
    return port


def _is_one_worker(value: str) -> bool:
    try:
        return int(value) == 1
    except ValueError:
        return False
