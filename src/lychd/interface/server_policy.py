"""Pure server-runtime policy shared by CLI and application assembly."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath

__all__ = (
    "ServerRuntimePolicy",
    "ServerRuntimePolicyError",
    "evaluate_server_runtime_policy",
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
)
_RELOAD_FLAG_ENVIRONMENT_KEYS = ("LITESTAR_RELOAD", "GRANIAN_RELOAD")
_LISTENER_PORT_ENVIRONMENT_KEYS = ("LITESTAR_PORT", "GRANIAN_PORT")
_DISABLED_ENVIRONMENT_VALUES = {"", "0", "false", "no", "off"}
_SERVER_CLI_NAMES = frozenset({"granian", "litestar"})
_WORKER_OPTIONS = frozenset({"--workers", "-W", "--wc", "--web-concurrency"})
_LONG_WORKER_OPTIONS = ("--workers", "--wc", "--web-concurrency")
_RELOAD_OPTIONS = frozenset(
    {
        "-r",
        "--reload",
        "-R",
        "--reload-dir",
        "-I",
        "--reload-include",
        "-E",
        "--reload-exclude",
    }
)
_LONG_RELOAD_VALUE_OPTIONS = (
    "--reload-dir",
    "--reload-include",
    "--reload-exclude",
)
_SHORT_RELOAD_VALUE_OPTIONS = ("-R", "-I", "-E")
_PORT_OPTIONS = frozenset({"-p", "--port"})
_MAX_TCP_PORT = 65535


class ServerRuntimePolicyError(ValueError):
    """A server setting would break the one-process, loopback-only runtime."""


@dataclass(frozen=True, slots=True)
class ServerRuntimePolicy:
    """Validated server facts needed by application assembly."""

    listener_port: int | None


def evaluate_server_runtime_policy(
    *,
    environment: Mapping[str, str],
    default_listener_port: int | None = None,
    server_arguments: Sequence[str] | None = None,
    argv: Sequence[str] = (),
    original_argv: Sequence[str] = (),
) -> ServerRuntimePolicy:
    """Validate worker/reload policy and resolve the effective listener port.

    ``server_arguments`` is the explicit server tail used by ``lychd serve``.
    When omitted, process arguments are admitted only for a detected Litestar or
    Granian entrypoint, keeping unrelated Python arguments inert. Listener-port
    precedence is explicit arguments, ``LITESTAR_PORT``, ``GRANIAN_PORT``, then
    ``default_listener_port``.
    """
    arguments = (
        tuple(server_arguments)
        if server_arguments is not None
        else _detected_server_arguments(argv=argv, original_argv=original_argv)
    )
    _validate_environment(environment)
    listener_port = _validate_arguments(arguments)
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


def _validate_environment(environment: Mapping[str, str]) -> None:
    for variable in _WORKER_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "" and not _is_one_worker(value):
            message = f"LychD v1 requires {variable}=1; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)

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


def _validate_arguments(arguments: Sequence[str]) -> int | None:
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
            listener_port = _parse_port(port_value, source=argument)
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
