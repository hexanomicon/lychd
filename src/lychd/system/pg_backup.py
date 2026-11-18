"""Capture and verify a single-volume, dedicated PostgreSQL 18 desktop cluster."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import click
import psycopg


def _control_id(pg_bin: Path, cluster: Path) -> str:
    """Read the identifier from the physical control file in the source or copy."""
    result = subprocess.run(  # noqa: S603
        [_executable(pg_bin, "pg_controldata"), cluster],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C", "LANG": "C"},
    )
    for line in result.stdout.splitlines():
        key, _, value = line.partition(":")
        if key == "Database system identifier" and value.strip().isascii() and value.strip().isdecimal():
            return value.strip()
    msg = "Cannot read the PostgreSQL system identifier."
    raise ValueError(msg)


def _executable(directory: Path, name: str) -> Path:
    path = directory / (name + ".exe" if sys.platform == "win32" else name)
    if not directory.is_absolute() or not path.is_file():
        msg = f"Supply the absolute PostgreSQL 18 bin directory containing {path.name}."
        raise ValueError(msg)
    return path


def verify(pg_bin: Path, cluster: Path, expected_id: str) -> None:
    """Verify the exact cluster identity, backup manifest, data checksums and required WAL."""
    if _control_id(pg_bin, cluster) != expected_id:
        msg = "The backup does not belong to the selected database cluster."
        raise ValueError(msg)
    subprocess.run([_executable(pg_bin, "pg_verifybackup"), cluster], check=True)  # noqa: S603


def capture(pg_bin: Path, source: Path, destination: Path, *, port: int, user: str, passfile: Path) -> Path:
    """Write into a fresh private directory and mark it verified only after physical checks."""
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=True)
    passfile = passfile.resolve(strict=True)
    if destination.is_relative_to(source) or not destination.is_dir():
        msg = "Choose an existing backup directory outside the source cluster."
        raise ValueError(msg)
    if not passfile.is_file() or (os.name == "posix" and passfile.stat().st_mode & 0o077):
        msg = "Select a private PostgreSQL password file readable only by the operator."
        raise ValueError(msg)
    if (source / "PG_VERSION").read_text(encoding="ascii").strip() != "18":
        msg = "The desktop physical backup profile requires PostgreSQL 18 and matching tools."
        raise ValueError(msg)
    source_id = _control_id(pg_bin, source)
    # Override libpq routing explicitly for both connections. An inherited PGSERVICE or
    # PGHOSTADDR must never redirect the physical copy away from this dedicated cluster.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
    env.update(PGPASSFILE=str(passfile), PGHOSTADDR="127.0.0.1", PGSSLMODE="disable", PGGSSENCMODE="disable")
    with psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=port,
        user=user,
        dbname="postgres",
        passfile=str(passfile),
        sslmode="disable",
        gssencmode="disable",
        connect_timeout=5,
    ) as connection:
        identity = connection.execute(
            "SELECT current_setting('data_directory'), system_identifier::text FROM pg_control_system()"
        ).fetchone()
        if identity is None or not source.samefile(identity[0]) or identity[1] != source_id:
            msg = "The running PostgreSQL server does not own the selected data directory."
            raise ValueError(msg)
        if connection.execute("SELECT 1 FROM pg_tablespace WHERE pg_tablespace_location(oid) <> ''").fetchone():
            msg = "This single-volume profile requires every tablespace inside the dedicated cluster."
            raise ValueError(msg)
        output = Path(tempfile.mkdtemp(prefix="lychd-postgres-", dir=destination))
        cluster = output / "cluster"
        click.echo(f"Capture directory: {output}", err=True)
        subprocess.run(  # noqa: S603
            [
                _executable(pg_bin, "pg_basebackup"),
                "--host=127.0.0.1",
                f"--port={port}",
                f"--username={user}",
                "--no-password",
                "--format=plain",
                "--wal-method=stream",
                "--manifest-checksums=SHA256",
                "--no-clean",
                "--pgdata",
                cluster,
            ],
            env=env,
            check=True,
        )
    verify(pg_bin, cluster, source_id)
    with (output / "verified.json").open("x", encoding="ascii") as receipt:
        json.dump({"postgres_major": 18, "system_identifier": source_id}, receipt)
    return output


@click.command()
@click.option("--pg-bin", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--source", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--destination", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--port", required=True, type=click.IntRange(1, 65535))
@click.option("--user", required=True, help="Local database owner with physical replication access.")
@click.option("--passfile", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def main(pg_bin: Path, source: Path, destination: Path, port: int, user: str, passfile: Path) -> None:
    """Capture a dedicated local cluster into a fresh directory on an operator-selected volume."""
    try:
        output = capture(pg_bin, source, destination, port=port, user=user, passfile=passfile)
    except (OSError, ValueError, psycopg.Error, subprocess.CalledProcessError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Verified PostgreSQL backup: {output}")


if __name__ == "__main__":
    main()
