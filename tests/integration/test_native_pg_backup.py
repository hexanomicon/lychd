"""Physical PostgreSQL backup qualification on a disposable single-volume cluster."""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from lychd.system.pg_backup import capture, verify


def test_recovered_cluster_retains_only_the_captured_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = os.environ.get("LYCHD_PG_BIN")
    if not directory:
        pytest.skip("Set LYCHD_PG_BIN to a PostgreSQL 18 bin directory to run physical recovery.")
    pg_bin = Path(directory)
    suffix = ".exe" if sys.platform == "win32" else ""
    source = tmp_path / "original"
    destination = tmp_path / "backups"
    destination.mkdir()
    password = secrets.token_urlsafe(32)
    pwfile = tmp_path / "init-password"
    pwfile.write_text(password, encoding="ascii")
    pg_ctl = pg_bin / f"pg_ctl{suffix}"
    subprocess.run(  # noqa: S603
        [pg_bin / f"initdb{suffix}", "-D", source, "-U", "backup_test", "--pwfile", pwfile, "-A", "scram-sha-256"],
        check=True,
    )
    with closing(socket.socket()) as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])
    passfile = tmp_path / "pgpass"
    passfile.write_text(f"127.0.0.1:{port}:*:backup_test:{password}\n", encoding="ascii")
    passfile.chmod(0o600)
    # Both instances are confined to the private temp directory and IPv4 loopback.
    options = f"-p {port} -h 127.0.0.1 -c unix_socket_directories="
    command = [pg_ctl, "-w", "-l", tmp_path / "postgres.log"]
    database = make_conninfo(host="127.0.0.1", port=port, user="backup_test", password=password, dbname="postgres")
    subprocess.run([*command, "-D", source, "-o", options, "start"], check=True)  # noqa: S603
    try:
        with psycopg.connect(database) as connection:
            connection.execute("CREATE TABLE proof(value text)")
            connection.execute("INSERT INTO proof VALUES ('captured')")
        with pytest.raises(ValueError, match="outside"):
            capture(pg_bin, source, source, port=port, user="backup_test", passfile=passfile)
        monkeypatch.setenv("PGPASSWORD", "unrelated-inherited-password")
        output = capture(pg_bin, source, destination, port=port, user="backup_test", passfile=passfile)
        with psycopg.connect(database) as connection:
            connection.execute("INSERT INTO proof VALUES ('after capture')")
    finally:
        subprocess.run([pg_ctl, "-w", "-D", source, "-m", "fast", "stop"], check=True)  # noqa: S603
    recovered = output / "cluster"
    assert (output / "verified.json").is_file()
    with pytest.raises(ValueError, match="does not belong"):
        verify(pg_bin, recovered, "0")
    subprocess.run([*command, "-D", recovered, "-o", options, "start"], check=True)  # noqa: S603
    try:
        with psycopg.connect(database) as connection:
            assert connection.execute("SELECT value FROM proof").fetchall() == [("captured",)]
    finally:
        subprocess.run([pg_ctl, "-w", "-D", recovered, "-m", "fast", "stop"], check=True)  # noqa: S603
