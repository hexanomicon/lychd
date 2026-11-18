"""Operator commands for registered, cold desktop PostgreSQL volume captures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from time import monotonic
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import click

from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.private import private_directory, publish_file, verify_private_directory
from lychd.system.desktop.volume_cluster import active_id, bind_installation, cold_control, inventory
from lychd.system.desktop.volume_native import snapshot_view
from lychd.system.desktop.volume_storage import (
    STORAGE,
    authority,
    dedicated_contents,
    read_record,
    select_storage,
    selected,
    write_record,
)

if TYPE_CHECKING:
    from collections.abc import Generator

_DEFAULT = PATH_POSTGRES_ROOT_DIR / "native-data"


@contextmanager
def _operation() -> Generator[None]:
    from lychd.system.desktop import management_lock

    try:
        with management_lock():
            yield
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.group()
def volume() -> None:
    """Capture the registered desktop database on a dedicated APFS or NTFS volume."""


@volume.command("select-storage")
@click.option("--root", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
def select(root: Path) -> None:
    """Select a fresh volume before installing a new desktop database."""
    with _operation():
        click.echo(select_storage(_DEFAULT, root.absolute()))


@volume.command("verify-start", hidden=True)
def verify_start() -> None:
    """Check the selected server with short-lived administrator credentials before Vessel startup."""
    from lychd.system.desktop import desktop_settings, require_cluster

    with _operation():
        require_cluster()
        bind_installation(_DEFAULT, desktop_settings(admin=True).server.database, initialize=False)


@volume.command()
def register() -> None:
    """Grant a new capture generation to the running dedicated cluster."""
    from lychd.system.desktop import desktop_settings, require_cluster

    with _operation():
        root, identity = selected(_DEFAULT)
        require_cluster()
        db = desktop_settings(admin=True).server.database
        bind_installation(_DEFAULT, db, initialize=False)
        source_id = active_id(root / STORAGE / _DEFAULT.name, db)
        generation = str(uuid4())
        write_record(
            authority(_DEFAULT) / "grant.json", generation=generation, volume=identity, system_identifier=source_id
        )
        click.echo(f"Registered generation {generation} for database {source_id} on {identity}.")


@volume.command()
def revoke() -> None:
    """Revoke this generation and its captures without mounting the database volume."""
    with _operation():
        grant = authority(_DEFAULT) / "grant.json"
        record = read_record(grant)
        grant.rename(grant.with_name("revoked-" + str(UUID(record["generation"])) + ".json"))
        click.echo(f"Revoked {record['generation']}.")


def active_grant(identity: str) -> dict[str, str]:
    directory = authority(_DEFAULT)
    record = read_record(directory / "grant.json")
    generation = str(UUID(record["generation"]))
    if record["volume"] != identity or (directory / f"revoked-{generation}.json").exists():
        msg = "This database volume grant is stale or revoked."
        raise ValueError(msg)
    return record


def _frozen(grant: dict[str, str], cut: str, snapshot: str, tool: str) -> tuple[Path, str]:
    view = snapshot_view(grant["volume"], snapshot, cut)
    source = view.root / STORAGE / _DEFAULT.name
    # A redirected top-level PGDATA could otherwise leave the immutable view.
    for path in (source.parent, source):
        if path.is_symlink() or path.is_junction() or path.stat().st_dev != view.root.stat().st_dev:
            msg = "The frozen cluster crosses a volume boundary."
            raise ValueError(msg)
    inventory(source, digest=False)
    if (source / f".lychd-cut-{cut}").read_text(encoding="ascii") != grant["volume"]:
        msg = "The snapshot does not contain this authorized cut."
        raise ValueError(msg)
    cold_control(source, tool, grant["system_identifier"])
    return source, view.provider


@volume.command()
def capture() -> None:
    """Pause the running database for an operator-produced native snapshot and restart it."""
    from lychd.system.desktop import desktop_settings, postgres_program, require_cluster, start_cluster, stop_cluster

    with _operation():
        started = monotonic()
        root, identity = selected(_DEFAULT)
        grant = active_grant(identity)
        dedicated_contents(root)
        require_cluster()
        source = root / STORAGE / _DEFAULT.name
        db = desktop_settings(admin=True).server.database
        if active_id(source, db) != grant["system_identifier"]:
            msg = "The running cluster differs from the registered PostgreSQL system identifier."
            raise ValueError(msg)
        before = shutil.disk_usage(root).free
        cut = str(uuid4())
        marker = source / f".lychd-cut-{cut}"
        request = root / f".lychd-volume-request-{cut}"
        tool = postgres_program("pg_controldata")
        pause = monotonic()
        stop_cluster()
        try:
            inventory(source, digest=False)
            cold_control(source, tool, grant["system_identifier"])
            publish_file(marker, identity.encode("ascii"))
            click.echo(f"Database is stopped. Volume {identity} at {root}. Capture {cut}.")
            if sys.platform == "win32":
                # The separate VSS operator can read this public request without access to PGDATA.
                publish_file(request, identity.encode("ascii"))
                click.echo(f"Run the reviewed volume_vss.ps1 -Volume {identity} -Cut {cut} in the operator console.")
            else:
                click.echo(
                    "Create and mount a protected snapshot of this volume using the authorized snapshot utility."
                )
            snapshot = str(click.prompt("Native snapshot UUID", type=click.UUID))
            _, provider = _frozen(grant, cut, snapshot, tool)
        finally:
            try:
                marker.unlink(missing_ok=True)
                if sys.platform == "win32":
                    request.unlink(missing_ok=True)
            finally:
                # Recheck storage before using an old path to restart PostgreSQL.
                selected(_DEFAULT)
                start_cluster(db.port)
        resumed = monotonic()
        record = dict(
            grant,
            cut=cut,
            snapshot=snapshot,
            provider=provider,
            source=str(source),
            postgres_major="18",
            wal="pg_wal",
            tablespaces="built-in only",
            free_bytes_before=str(before),
            free_bytes_after=str(shutil.disk_usage(root).free),
            pause_seconds=f"{resumed - pause:.6f}",
            total_seconds=f"{monotonic() - started:.6f}",
        )
        write_record(authority(_DEFAULT) / f"capture-{cut}.json", **record)
        click.echo(json.dumps(record, sort_keys=True))


@volume.command()
@click.option("--capture", "cut", type=click.UUID, required=True)
@click.option("--destination", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
def restore(cut: UUID, destination: Path) -> None:
    """Copy the sealed snapshot to a fresh private, inactive target and verify every byte."""
    from lychd.system.desktop import postgres_program

    with _operation():
        root, identity = selected(_DEFAULT)
        grant = active_grant(identity)
        record = read_record(authority(_DEFAULT) / f"capture-{cut}.json")
        if record["cut"] != str(cut) or any(record[key] != value for key, value in grant.items()):
            msg = "The capture does not match the current database volume grant."
            raise ValueError(msg)
        destination = destination.absolute()
        verify_private_directory(destination)
        if destination.stat().st_dev == root.stat().st_dev:
            msg = "Choose a private restore parent outside the captured volume."
            raise ValueError(msg)
        tool = postgres_program("pg_controldata")
        source, provider = _frozen(grant, str(cut), record["snapshot"], tool)
        if provider != record["provider"]:
            msg = "The native snapshot provider has changed."
            raise ValueError(msg)
        output = Path(mkdtemp(prefix="lychd-volume-", dir=destination))
        private_directory(output)
        with TemporaryDirectory(prefix=".stage-", dir=output) as directory:
            staged = Path(directory) / "cluster"
            expected = inventory(source, digest=True)
            shutil.copytree(source, staged, symlinks=True)
            if inventory(staged, digest=True) != expected:
                msg = "Restored files differ from the native snapshot."
                raise ValueError(msg)
            cold_control(staged, tool, grant["system_identifier"])
            (staged / f".lychd-cut-{cut}").unlink()
            staged.rename(output / "cluster")
        write_record(output / "verified.json", **record)
        click.echo(f"Verified inactive database copy: {output}")
