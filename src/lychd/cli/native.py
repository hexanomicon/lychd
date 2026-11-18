"""Bootstrap-safe foreground entry for the selected personal host profile."""

from __future__ import annotations

import asyncio
import json
import os
import sys

import click

from lychd.system.vessel_mode import require_native_user, vessel_mode


@click.command("platform")
def platform() -> None:
    """Show the selected host profile and its configuration path."""
    mode = vessel_mode()
    if mode == "container" and sys.platform in {"darwin", "win32"}:
        from lychd.cli.portable import GUIDE

        click.echo(
            json.dumps(
                {
                    "platform": sys.platform,
                    "profile": "portable-container",
                    "vessel_mode": mode,
                    "project_directory": os.environ.get("LYCHD_CONTAINER_DIR"),
                    "setup": GUIDE,
                }
            )
        )
        return
    from lychd.system.constants import PATH_CACHE_ROOT, PATH_CODEX_ROOT, PATH_CRYPT_ROOT, PATH_LYCHD_TOML

    profile = {"native": "personal-desktop", "container": "managed-linux", "unsupported": "unsupported"}[mode]
    click.echo(
        json.dumps(
            {
                "platform": sys.platform,
                "vessel_mode": mode,
                "profile": profile,
                "config": str(PATH_CODEX_ROOT),
                "data": str(PATH_CRYPT_ROOT),
                "cache": str(PATH_CACHE_ROOT),
                "settings": str(PATH_LYCHD_TOML),
            }
        )
    )


@click.command("start")
def start_native() -> None:
    """Serve the personal Vessel on IPv4 loopback until interrupted."""
    import subprocess

    _check_account()
    from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
    from lychd.system.desktop.credentials import load_credentials
    from lychd.system.desktop.volume_storage import authority

    if authority(PATH_POSTGRES_ROOT_DIR / "native-data").exists():
        # The administrative connection exists only in the short-lived verifier process.
        subprocess.run(
            [sys.executable, "-m", "lychd.system.desktop", "volume", "verify-start"],
            check=True,
        )
    load_credentials()
    from lychd.config.logging import apply_logging
    from lychd.interface.server import run_native_server

    apply_logging()
    run_native_server()


@click.command("stop")
def stop_native() -> None:
    """Request graceful retirement and wait for this database's native Vessel to stop."""
    _check_account()
    from lychd.system.desktop.credentials import load_credentials

    load_credentials()
    from lychd.interface.vessel_owner import stop_native_vessel

    try:
        stopped = asyncio.run(stop_native_vessel())
    except TimeoutError:
        message = "Timed out waiting for native Vessel retirement."
        raise click.ClickException(message) from None
    except (OSError, RuntimeError, ValueError):
        message = "Unable to confirm native Vessel retirement with the configured database and credentials."
        raise click.ClickException(message) from None
    click.echo("Native Vessel stopped." if stopped else "No Vessel owns this database.")


@click.command("desktop", add_help_option=False, context_settings={"ignore_unknown_options": True})
@click.argument("arguments", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def desktop(ctx: click.Context, arguments: tuple[str, ...]) -> None:
    """Manage the personal PostgreSQL installation and login session."""
    from lychd.system.desktop import desktop as commands

    commands.main(args=list(arguments), prog_name=ctx.command_path, standalone_mode=False)


def _check_account() -> None:
    try:
        require_native_user()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
