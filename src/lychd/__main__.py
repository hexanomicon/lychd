from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, ClassVar, cast

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

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
_DISABLED_ENVIRONMENT_VALUES = {"", "0", "false", "no", "off"}
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


class PulseGroup(click.Group):
    """Closed public grammar with lookup-only aliases."""

    _ALIASES: ClassVar[dict[str, str]] = {"st": "status"}
    _PUBLIC_ORDER: ClassVar[tuple[str, ...]] = (
        "init",
        "bind",
        "start",
        "stop",
        "status",
        "logs",
        "run",
        "del",
    )

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Resolve a supported alias without listing it as a ninth root."""
        return super().get_command(ctx, self._ALIASES.get(cmd_name, cmd_name))

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Present the public operator journey before hidden machinery."""
        available = super().list_commands(ctx)
        public = [name for name in self._PUBLIC_ORDER if name in available]
        remainder = sorted(name for name in available if name not in self._PUBLIC_ORDER)
        return [*public, *remainder]


@click.group(
    cls=PulseGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
def cli() -> None:
    """Operate the LychD daemon and its local runtime."""


def _run_litestar(args: Sequence[str], *, prog_name: str) -> None:
    """Enter Litestar only for commands that need the web application.

    Keeping this import behind the command callback is deliberate: ``lychd init``,
    ``lychd bind``, and ``lychd --help`` must work before database, SAQ, AI, or
    ASGI configuration exists.
    """
    from litestar.cli.main import litestar_group

    group = cast("click.Group", litestar_group)
    group.main(
        args=["--app", "lychd.app:create_app", *args],
        prog_name=prog_name,
    )


@cli.command(
    name="serve",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("server_args", nargs=-1, type=click.UNPROCESSED)
def serve(server_args: tuple[str, ...]) -> None:
    """Run the ASGI vessel; remaining options are server options."""
    _enforce_single_worker(server_args)
    _run_litestar(("run", *server_args), prog_name="lychd serve")


def _enforce_single_worker(server_args: Sequence[str]) -> None:
    """Reject process/reload settings that split the v1 event plane."""
    _enforce_server_environment()
    _enforce_server_arguments(server_args)


def _enforce_server_environment() -> None:
    """Reject ambient worker and reload settings incompatible with v1."""
    for variable in _WORKER_ENVIRONMENT_KEYS:
        environment_workers = os.getenv(variable)
        if environment_workers is not None and environment_workers != "" and not _is_one_worker(environment_workers):
            message = f"LychD v1 requires {variable}=1; the run event plane is process-local."
            raise click.ClickException(message)
    reload_environment = os.getenv("LITESTAR_RELOAD")
    if reload_environment is not None and reload_environment.casefold() not in _DISABLED_ENVIRONMENT_VALUES:
        message = "LychD v1 does not support Litestar reload mode; the run event plane is process-local."
        raise click.ClickException(message)
    for variable in _RELOAD_ENVIRONMENT_KEYS:
        if os.getenv(variable) not in {None, ""}:
            message = (
                f"LychD v1 does not support {variable}; "
                "Litestar treats it as reload mode and the run event plane "
                "is process-local."
            )
            raise click.ClickException(message)


def _enforce_server_arguments(server_args: Sequence[str]) -> None:
    """Reject explicit worker and reload arguments incompatible with v1."""
    for index, argument in enumerate(server_args):
        raw_value: str | None = None
        if argument in _WORKER_OPTIONS and index + 1 < len(server_args):
            raw_value = server_args[index + 1]
        elif any(argument.startswith(f"{option}=") for option in _LONG_WORKER_OPTIONS):
            raw_value = argument.partition("=")[2]
        elif argument.startswith("-W") and argument != "-W":
            raw_value = argument[2:].removeprefix("=")
        if raw_value is not None and not _is_one_worker(raw_value):
            message = "LychD v1 requires exactly one ASGI worker; cross-process RunEventBus is not implemented."
            raise click.ClickException(message)
        reload_value = (
            argument in _RELOAD_OPTIONS
            or any(argument.startswith(f"{option}=") for option in _LONG_RELOAD_VALUE_OPTIONS)
            or any(
                argument.startswith(option) and len(argument) > len(option) for option in _SHORT_RELOAD_VALUE_OPTIONS
            )
        )
        if reload_value:
            message = "LychD v1 does not support Litestar reload mode; the run event plane is process-local."
            raise click.ClickException(message)


def _is_one_worker(value: str) -> bool:
    """Return whether one CLI/environment value denotes exactly one worker."""
    try:
        return int(value) == 1
    except ValueError:
        return False


@cli.command(
    name="database",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option(
    "--wait-seconds",
    type=click.FloatRange(min=0.0),
    default=0.0,
    show_default=True,
    help="Wait up to this many seconds for the configured database TCP port.",
)
@click.argument("database_args", nargs=-1, type=click.UNPROCESSED)
def database(database_args: tuple[str, ...], wait_seconds: float) -> None:
    """Run an explicit database lifecycle command, such as ``upgrade``."""
    if wait_seconds:
        _wait_for_database(wait_seconds)
    _run_litestar(("database", *database_args), prog_name="lychd database")


def _wait_for_database(timeout: float) -> None:
    """Wait boundedly for the configured database TCP endpoint without authenticating."""
    import socket
    import time

    from lychd.config.settings.root import get_settings

    db = get_settings().server.database
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((db.host, db.port), timeout=min(1.0, timeout)):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    detail = f": {last_error}" if last_error is not None else ""
    message = f"database {db.host}:{db.port} was not reachable within {timeout:g}s{detail}"
    raise click.ClickException(message)


def _register_local_commands() -> None:
    """Register the bootstrap-safe native command adapters on the Click root."""
    from lychd.cli.commands import COMMANDS
    from lychd.cli.deletion import delete_installation
    from lychd.cli.operator import logs, start, status, stop
    from lychd.cli.run import build_run_command, load_run_operation_catalog

    for command in (*COMMANDS, start, stop, status, logs, delete_installation):
        cli.add_command(command)
    cli.add_command(
        build_run_command(
            catalog_factory=load_run_operation_catalog,
        )
    )


_register_local_commands()


def run_cli() -> None:
    """Configure shared logging, then run the native CLI without eager ASGI assembly."""
    if _effectful_init_requested(sys.argv[1:]) and os.geteuid() == 0:
        error = click.ClickException(
            "LychD initialization is rootless; rerun `lychd init` as your ordinary user.",
        )
        error.show()
        raise SystemExit(error.exit_code)

    from lychd.config.logging import apply_logging

    apply_logging()
    cli()


def _effectful_init_requested(arguments: Sequence[str]) -> bool:
    """Recognize the one bootstrap rite that must refuse root before Settings load."""
    tokens = tuple(arguments)
    if tokens[:1] == ("--",):
        tokens = tokens[1:]
    return bool(tokens and tokens[0] == "init" and "--dry-run" not in tokens and not _help_requested(tokens))


def _help_requested(tokens: Sequence[str]) -> bool:
    """Recognize Click's eager long help and clustered short ``-h`` option."""
    return any(
        argument == "--help" or (argument.startswith("-") and not argument.startswith("--") and "h" in argument[1:])
        for argument in tokens
    )


if __name__ == "__main__":
    run_cli()
