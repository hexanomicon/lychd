"""Pure server-runtime policy shared by CLI and application assembly."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath

__all__ = (
    "ServerRuntimePolicy",
    "ServerRuntimePolicyError",
    "evaluate_server_runtime_policy",
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
_NATIVE_SHORT_FLAGS = frozenset({"-d", "-P", "-r"})
_NATIVE_SHORT_VALUE_OPTIONS = frozenset(
    {"-H", "-p", "-W", *_SHORT_RELOAD_VALUE_OPTIONS, *_SHORT_ALTERNATE_LISTENER_OPTIONS}
)
_LOOPBACK_LISTENER_HOSTS = frozenset({"127.0.0.1", "::1"})
_DEFAULT_NATIVE_LISTENER_HOST = "127.0.0.1"
_MAX_TCP_PORT = 65535
_NATIVE_DEBUG_OPTIONS = frozenset({"-d", "--debug"})
_NATIVE_PDB_OPTIONS = frozenset({"-P", "--pdb", "--use-pdb"})
_NATIVE_VALUE_OPTIONS = _WORKER_OPTIONS | _PORT_OPTIONS | _HOST_OPTIONS | {"--metrics-address"}


class ServerRuntimePolicyError(ValueError):
    """A server setting would break the single-process, owned-listener runtime."""


@dataclass(frozen=True, slots=True)
class ServerRuntimePolicy:
    """Validated server facts needed by application assembly."""

    listener_port: int | None
    listener_host: str | None
    debug: bool = False
    pdb: bool = False


@dataclass(frozen=True, slots=True)
class _NativeServerArguments:
    listener_port: int | None = None
    listener_host: str | None = None
    debug: bool = False
    pdb: bool = False
    metrics_enabled: bool | None = None


def evaluate_server_runtime_policy(
    *,
    environment: Mapping[str, str],
    default_listener_port: int | None = None,
    server_arguments: Sequence[str] | None = None,
    argv: Sequence[str] = (),
    original_argv: Sequence[str] = (),
) -> ServerRuntimePolicy:
    """Validate process and native listener policy, resolving listener authority.

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
    native = _parse_native_arguments(arguments) if native_serve else _NativeServerArguments()
    _validate_environment(environment, metrics_enabled=native.metrics_enabled)
    if native_serve:
        listener_port, listener_host = native.listener_port, native.listener_host
    else:
        listener_port, listener_host = _validate_detected_arguments(arguments), None
    if listener_port is None:
        listener_port = _environment_port(environment)
    if listener_port is None and default_listener_port is not None:
        listener_port = _parse_port(str(default_listener_port), source="settings.server.port")
    if server_arguments is not None:
        environment_host = _native_environment_host(environment)
        listener_host = listener_host or environment_host or _DEFAULT_NATIVE_LISTENER_HOST
    return ServerRuntimePolicy(
        listener_port=listener_port,
        listener_host=listener_host,
        debug=native.debug or _environment_boolean(environment, "LITESTAR_DEBUG"),
        pdb=native.pdb or _environment_boolean(environment, "LITESTAR_PDB"),
    )


def _parse_native_arguments(arguments: Sequence[str]) -> _NativeServerArguments:
    """Parse the complete owned grammar without application or framework imports."""
    tokens = _expand_native_short_arguments(arguments)
    listener_port: int | None = None
    listener_host: str | None = None
    debug = pdb = False
    metrics_enabled: bool | None = None
    index = 0
    while index < len(tokens):
        option, separator, value = _split_native_option(tokens[index])
        if option in _NATIVE_VALUE_OPTIONS:
            if not separator:
                index += 1
                value = tokens[index] if index < len(tokens) else ""
            _validate_native_value(option, value)
            if option in _PORT_OPTIONS:
                listener_port = _parse_port(value, source=option)
            elif option in _HOST_OPTIONS:
                listener_host = _parse_native_host(value, source=option)
        elif option in _NATIVE_DEBUG_OPTIONS and not separator:
            debug = True
        elif option in _NATIVE_PDB_OPTIONS and not separator:
            pdb = True
        elif option in {"--metrics", "--no-metrics"} and not separator:
            metrics_enabled = option == "--metrics"
        elif option.startswith("-"):
            message = f"LychD native serve does not support option {option}."
            raise ServerRuntimePolicyError(message)
        else:
            message = "LychD native serve does not accept extra arguments."
            raise ServerRuntimePolicyError(message)
        index += 1
    return _NativeServerArguments(listener_port, listener_host, debug, pdb, metrics_enabled)


def _split_native_option(argument: str) -> tuple[str, str, str]:
    option, separator, value = argument.partition("=")
    if _is_reload_argument(argument):
        message = "LychD v1 does not support Litestar reload mode; the run event plane is process-local."
        raise ServerRuntimePolicyError(message)
    if _is_alternate_listener_argument(argument):
        option_name = option if option.startswith("--") else option[:2]
        message = f"LychD native serve does not support {option_name}; use its loopback TCP listener."
        raise ServerRuntimePolicyError(message)
    if not option.startswith("--") and option[:2] in _NATIVE_SHORT_VALUE_OPTIONS:
        option, value = option[:2], argument[2:].removeprefix("=")
        separator = "=" if len(argument) > len(option) else ""
    return option, separator, value


def _validate_native_value(option: str, value: str) -> None:
    if not value or value.startswith("-"):
        message = f"LychD native serve requires a value for {option}; option-looking values are not accepted."
        raise ServerRuntimePolicyError(message)
    if option in _WORKER_OPTIONS and not _is_one_worker(value):
        message = "LychD v1 requires exactly one ASGI worker; cross-process RunEventBus is not implemented."
        raise ServerRuntimePolicyError(message)


def _expand_native_short_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    """Expand the supported native short grammar before checking authority.

    Click permits flag clusters such as ``-dH::1``. Only known flags can precede
    a value option; its remaining suffix belongs to that value. Unknown short
    options fail closed so a new server flag cannot silently hide authority.
    The same owned parser handles long options and consumes every token.
    """
    expanded: list[str] = []
    for argument in arguments:
        if not argument.startswith("-") or argument.startswith("--") or argument == "-":
            expanded.append(argument)
            continue
        remaining = argument[1:]
        while remaining:
            option = f"-{remaining[0]}"
            remaining = remaining[1:]
            if option in _NATIVE_SHORT_VALUE_OPTIONS:
                expanded.append(f"{option}{remaining}")
                break
            if option not in _NATIVE_SHORT_FLAGS:
                message = f"LychD native serve does not support short option {option}; use an explicit long option."
                raise ServerRuntimePolicyError(message)
            expanded.append(option)
    return tuple(expanded)


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


def validate_server_environment(environment: Mapping[str, str]) -> None:
    """Validate shared process/listener controls without selecting a TCP profile."""
    _validate_environment(environment)


def _validate_environment(environment: Mapping[str, str], *, metrics_enabled: bool | None = None) -> None:
    for variable in _WORKER_ENVIRONMENT_KEYS:
        value = environment.get(variable)
        if value is not None and value != "" and not _is_one_worker(value):
            message = f"LychD v1 requires {variable}=1; the run event plane is process-local."
            raise ServerRuntimePolicyError(message)

    _validate_native_listener_environment(environment)
    if metrics_enabled is None:
        metrics_enabled = _environment_boolean(environment, "GRANIAN_METRICS_ENABLED")
    if metrics_enabled:
        message = "LychD native serve does not support the Granian metrics listener; use its loopback TCP listener."
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


def _environment_boolean(environment: Mapping[str, str], variable: str) -> bool:
    value = environment.get(variable, "").strip().casefold()
    if value in _FALSE_BOOLEAN_VALUES:
        return False
    if value in _TRUE_BOOLEAN_VALUES:
        return True
    message = f"LychD requires {variable} to name a valid boolean."
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
