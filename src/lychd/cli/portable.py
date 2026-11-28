"""Operate the explicitly selected portable Compose project on a personal desktop."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import click

_MIN_ENGINE_MAJOR = 28
_MAX_GUEST_UID = 2**31 - 1
GUIDE = "https://hexanomicon.dev/deployments/container-desktop/"


def _docker_output(arguments: list[str]) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True, check=False, timeout=30)  # noqa: S603
    if result.returncode:
        msg = "Could not inspect the local Docker context. Check that the Linux engine is running."
        raise click.ClickException(msg)
    return result.stdout.strip()


def _local_engine() -> list[str]:
    docker = shutil.which("docker")
    if docker is None:
        msg = "Install Docker Desktop with Compose v2 and start its Linux engine."
        raise click.ClickException(msg)
    if os.environ.get("DOCKER_HOST"):
        msg = "Unset DOCKER_HOST and select the local Docker Desktop context."
        raise click.ClickException(msg)
    context = _docker_output([docker, "context", "show"])
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", context):
        msg = "The selected Docker context name is invalid."
        raise click.ClickException(msg)
    endpoint = _docker_output([docker, "context", "inspect", context, "--format", "{{json .Endpoints.docker.Host}}"])
    address = json.loads(endpoint)
    if not isinstance(address, str) or not (
        address.startswith("unix:///") or address.lower().startswith("npipe:////./pipe/")
    ):
        msg = "Select a local Unix socket or Windows named pipe Docker context."
        raise click.ClickException(msg)
    client = [docker, "--context", context]
    info = _docker_output([*client, "info", "--format", "{{.OSType}} {{.ServerVersion}}"])
    version = re.fullmatch(r"linux ([0-9]+)\..+", info)
    if version is None or int(version[1]) < _MIN_ENGINE_MAJOR:
        msg = "Portable Vessel requires a local Linux Docker Engine 28 or newer for loopback-only publication."
        raise click.ClickException(msg)
    return client


def _reactor_overlay() -> bool:
    keys = ("LYCHD_REACTOR_BUNDLE", "LYCHD_REACTOR_INBOX", "LYCHD_REACTOR_JOURNAL")
    paths = [os.environ.get(key, "") for key in keys]
    uid = os.environ.get("LYCHD_REACTOR_UID", "")
    if not any(paths) and not uid:
        return False
    if re.fullmatch(r"[1-9][0-9]{0,9}", uid) is None or int(uid) > _MAX_GUEST_UID:
        msg = "Use the positive guest UID returned by reactor-prepare."
        raise click.ClickException(msg)
    if os.environ.get("LYCHD_GGUF") or not all(Path(path).is_absolute() for path in paths):
        msg = "Use all three prepared Reactor directories together, with LYCHD_GGUF unset."
        raise click.ClickException(msg)
    from lychd.system.constants import PATH_CRYPT_ROOT
    from lychd.system.desktop.private import verify_private_directory

    root = (PATH_CRYPT_ROOT / "desktop-reactor").resolve(strict=True)
    bundle, inbox, journal = map(Path, paths)
    if (
        inbox != root / "inbox"
        or journal != root / "journal"
        or bundle.parent != root / "bundles"
        or re.fullmatch(r"[0-9a-f]{64}", bundle.name) is None
    ):
        msg = "Use the exact sources returned by the current installation's reactor-prepare."
        raise click.ClickException(msg)
    for directory in (bundle, inbox, journal):
        verify_private_directory(directory)
    if inbox.samefile(journal) or inbox.samefile(bundle) or journal.samefile(bundle):
        msg = "Reactor mount sources overlap."
        raise click.ClickException(msg)
    return True


def _compose(*arguments: str, include_model: bool = False) -> None:
    location = Path(os.environ.get("LYCHD_CONTAINER_DIR", ""))
    if not location.is_absolute() or not (location / "compose.yaml").is_file():
        msg = f"Set LYCHD_CONTAINER_DIR to the absolute reviewed portable-container directory. {GUIDE}"
        raise click.ClickException(msg)
    try:
        reactor = _reactor_overlay()
        command = [
            *_local_engine(),
            "compose",
            "--project-directory",
            str(location),
            "-p",
            "lychd-portable-reactor" if reactor else "lychd-portable",
            "-f",
            str(location / "compose.yaml"),
        ]
        if reactor:
            command.extend(["-f", str(location / "compose.reactor.yaml")])
        elif include_model and (model := os.environ.get("LYCHD_GGUF")):
            if not Path(model).is_absolute() or not Path(model).is_file():
                msg = "LYCHD_GGUF must name the absolute path to an existing model file."
                raise click.ClickException(msg)
            command.extend(["-f", str(location / "compose.chat.yaml")])
        result = subprocess.run([*command, *arguments], check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        msg = "Unable to inspect or run the selected local Docker installation."
        raise click.ClickException(msg) from exc
    if result.returncode:
        msg = f"Docker Compose exited with status {result.returncode}. See {GUIDE}"
        raise click.ClickException(msg)


@click.command("start")
def start() -> None:
    """Start the prepared portable container project on the local Linux engine."""
    _compose("up", "--detach", "--no-build", "--wait", "--wait-timeout", "180", include_model=True)


@click.command("status")
def status() -> None:
    """Show the Compose project's containers and published ports."""
    _compose("ps", "--all")


@click.command("logs")
@click.option("--lines", type=click.IntRange(1, 10000), default=100, show_default=True)
def logs(lines: int) -> None:
    """Show recent Vessel output."""
    _compose("logs", "--tail", str(lines), "vessel")


@click.command("access")
def access() -> None:
    """Display the portable Vessel's local browser credential in this terminal."""
    _compose("exec", "-T", "vessel", "cat", "/run/lychd/access/value")
    click.echo("\nAltar: http://127.0.0.1:7134/\nUsername: magus")


@click.command("stop")
def stop() -> None:
    """Report the manual maintenance boundary for the portable stack."""
    msg = f"An active container requires operator-coordinated shutdown. See {GUIDE}"
    raise click.ClickException(msg)
