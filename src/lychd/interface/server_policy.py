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
_LISTENER_HOST_ENVIRONMENT_KEYS = ("LITESTAR_HOST", "GRANIAN_HOST")
_ALTERNATE_LISTENER_ENVIRONMENT_KEYS = (
    "LITESTAR_FILE_DESCRIPTOR",
    "LITESTAR_UNIX_DOMAIN_SOCKET",
)
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
_HOST_OPTIONS = frozenset({"-H", "--host"})
_ALTERNATE_LISTENER_OPTIONS = frozenset(
    {
        "-F",
        "--fd",
        "--file-descriptor",
        "-U",
        "--uds",
        "--unix-domain-socket",
    }
)
_LONG_ALTERNATE_LISTENER_OPTIONS = (
    "--fd",
    "--file-descriptor",
    "--uds",
    "--unix-domain-socket",
)
_SHORT_ALTERNATE_LISTENER_OPTIONS = ("-F", "-U")
_LOOPBACK_LISTENER_HOSTS = frozenset({"127.0.0.1", "::1"})
_DEFAULT_NATIVE_LISTENER_HOST = "127.0.0.1"
_MAX_TCP_PORT = 65535


class ServerRuntimePolicyError(ValueError):
    """A server setting would break the one-process, loopback-only runtime."""


@dataclass(frozen=True, slots=True)
class ServerRuntimePolicy:
    """Validated server facts needed by application assembly."""

    listener_port: int | None
    listener_host: str | None


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
    native_serve = server_arguments is not None
    _validate_environment(environment)
    listener_port, listener_host = _validate_arguments(arguments, require_loopback=native_serve)
    if listener_port is None:
        listener_port = _environment_port(environment)
    if listener_port is None and default_listener_port is not None:
        listener_port = _parse_port(str(default_listener_port), source="settings.server.port")
    if native_serve:
        _validate_native_listener_environment(environment)
        environment_host = _native_environment_host(environment)
        listener_host = listener_host or environment_host or _DEFAULT_NATIVE_LISTENER_HOST
    return ServerRuntimePolicy(listener_port=listener_port, listener_host=listener_host)


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


def _validate_arguments(
    arguments: Sequence[str],
    *,
    require_loopback: bool,
) -> tuple[int | None, str | None]:
    listener_port: int | None = None
    listener_host: str | None = None
    for index, argument in enumerate(arguments):
        if require_loopback and _is_alternate_listener_argument(argument):
            message = f"LychD native serve does not support {argument}; use its loopback TCP listener."
            raise ServerRuntimePolicyError(message)
        worker_value = _worker_value(arguments, index)
        if worker_value is not None and not _is_one_worker(worker_value):
            message = "LychD v1 requires exactly one ASGI worker; cross-process RunEventBus is not implemented."
            raise ServerRuntimePolicyError(message)
        if _is_reload_argument(argument):
            message = "LychD v1 does not support Litestar reload mode; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)
        if (port_value := _port_value(arguments, index)) is not None:
            listener_port = _parse_port(port_value, source=argument)
        if require_loopback and (host_value := _host_value(arguments, index)) is not None:
            listener_host = _parse_native_host(host_value, source=argument)
    return listener_port, listener_host


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


def _host_value(arguments: Sequence[str], index: int) -> str | None:
    argument = arguments[index]
    if argument in _HOST_OPTIONS and index + 1 < len(arguments):
        return arguments[index + 1]
    if argument.startswith("--host="):
        return argument.partition("=")[2]
    if argument.startswith("-H") and argument != "-H":
        return argument[2:].removeprefix("=")
    return None


def _is_alternate_listener_argument(argument: str) -> bool:
    return (
        argument in _ALTERNATE_LISTENER_OPTIONS
        or any(argument.startswith(f"{option}=") for option in _LONG_ALTERNATE_LISTENER_OPTIONS)
        or any(
            argument.startswith(option) and len(argument) > len(option) for option in _SHORT_ALTERNATE_LISTENER_OPTIONS
        )
    )


def _environment_port(environment: Mapping[str, str]) -> int | None:
    for variable in _LISTENER_PORT_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "":
            return _parse_port(value, source=variable)
    return None


def _native_environment_host(environment: Mapping[str, str]) -> str | None:
    listener_host: str | None = None
    for variable in _LISTENER_HOST_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "":
            validated = _parse_native_host(value, source=variable)
            if listener_host is None:
                listener_host = validated
    return listener_host


def _validate_native_listener_environment(environment: Mapping[str, str]) -> None:
    for variable in _ALTERNATE_LISTENER_ENVIRONMENT_KEYS:
        if environment.get(variable) not in {None, ""}:
            message = f"LychD native serve does not support {variable}; use its loopback TCP listener."
            raise ServerRuntimePolicyError(message)


def _parse_native_host(value: str, *, source: str) -> str:
    if value not in _LOOPBACK_LISTENER_HOSTS:
        message = f"LychD native serve requires {source} to be 127.0.0.1 or ::1."
        raise ServerRuntimePolicyError(message)
    return value


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
