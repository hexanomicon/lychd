from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

import click

if TYPE_CHECKING:
    from collections.abc import Sequence


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Operate the LychD daemon and its local runtime."""


def _run_litestar(args: Sequence[str], *, prog_name: str) -> None:
    """Enter Litestar only for commands that need the web application.

    Keeping this import behind the command callback is deliberate: ``lychd init``,
    ``lychd bind``, and ``lychd --help`` must work before database, SAQ, AI, or
    ASGI configuration exists.
    """
    from litestar.cli.main import litestar_group

    os.environ.setdefault("LITESTAR_APP", "lychd.app:create_app")
    group = cast("click.Group", litestar_group)
    group.main(args=list(args), prog_name=prog_name)


@cli.command(
    name="serve",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("server_args", nargs=-1, type=click.UNPROCESSED)
def serve(server_args: tuple[str, ...]) -> None:
    """Run the ASGI vessel; remaining options are server options."""
    _enforce_single_worker(server_args)
    _run_litestar(("run", *server_args), prog_name="lychd serve")


def _enforce_single_worker(server_args: Sequence[str]) -> None:
    """Reject a process count that would split the v1 in-process event plane."""
    environment_workers = os.getenv("GRANIAN_WORKERS")
    if environment_workers not in {None, "", "1"}:
        message = "LychD v1 requires GRANIAN_WORKERS=1; the run event plane is process-local."
        raise click.ClickException(message)
    for index, argument in enumerate(server_args):
        raw_value: str | None = None
        if argument == "--workers" and index + 1 < len(server_args):
            raw_value = server_args[index + 1]
        elif argument.startswith("--workers="):
            raw_value = argument.partition("=")[2]
        if raw_value is not None and raw_value != "1":
            message = "LychD v1 requires exactly one ASGI worker; cross-process RunEventBus is not implemented."
            raise click.ClickException(message)


@cli.command(
    name="database",
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

    from lychd.config.settings import get_settings

    db = get_settings().db
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
    """Register side-effect-free local commands on the native Click root."""
    from lychd.cli.commands import COMMANDS

    for command in COMMANDS:
        cli.add_command(command)


_register_local_commands()


def run_cli() -> None:
    """Run the native CLI without constructing the ASGI application eagerly."""
    cli()


if __name__ == "__main__":
    run_cli()
