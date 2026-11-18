"""Prove committed rows survive repair and removal of one native program edition."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg

from lychd.config.settings import DatabaseSettings, Settings
from lychd.system.desktop.credentials import load_credentials
from lychd.system.pg_backup import verify


def _recover_before_upgrade(backup: Path, db: DatabaseSettings, password: str) -> None:
    """Boot the verified pre-switch cut separately and read the original generation."""
    (receipt,) = backup.glob("lychd-postgres-*/verified.json")
    pg_bin = Path(os.environ["LYCHD_PG_BIN"])
    control = pg_bin / ("pg_ctl.exe" if os.name == "nt" else "pg_ctl")
    with TemporaryDirectory() as temporary:
        target = Path(temporary).resolve()
        restored = target / "cluster"
        shutil.copytree(receipt.parent / "cluster", restored)
        verify(pg_bin, restored, json.loads(receipt.read_text(encoding="ascii"))["system_identifier"])
        with closing(socket.socket()) as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        command = [control, "-D", restored, "-w"]
        options = f"-p {port} -h 127.0.0.1 -c unix_socket_directories="
        subprocess.run([*command, "-l", target / "recovery.log", "-o", options, "start"], check=True)  # noqa: S603
        try:
            with psycopg.connect(
                host="127.0.0.1", hostaddr="127.0.0.1", port=port, user=db.user, dbname=db.database, password=password
            ) as conn:
                directory = conn.execute("SHOW data_directory").fetchone()
                if not directory or not restored.samefile(directory[0]):
                    msg = "Recovery probe did not reach its independent restored cluster"
                    raise RuntimeError(msg)
                if conn.execute("SELECT generation FROM edition_trial.proof").fetchall() != [(1,)]:
                    msg = "Pre-upgrade recovery did not preserve the original committed row"
                    raise RuntimeError(msg)
        finally:
            subprocess.run([*command, "-m", "fast", "stop"], check=True)  # noqa: S603


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("seed", "repair", "recover", "restore"))
    parser.add_argument("--backup", type=Path)
    arguments = parser.parse_args()
    phase = arguments.phase
    load_credentials(administrative=True, required=True)
    db = Settings().server.database
    if not db.password:
        msg = "Expected the installation's database credential"
        raise RuntimeError(msg)
    if phase == "restore":
        if arguments.backup is None:
            parser.error("restore requires --backup")
        _recover_before_upgrade(arguments.backup, db, db.password.get_secret_value())
        return
    with psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=db.port,
        user=db.user,
        dbname=db.database,
        password=db.password.get_secret_value(),
    ) as conn:
        if conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone() is None:
            msg = "Expected the provisioned application database with pgvector"
            raise RuntimeError(msg)
        if phase == "seed":
            conn.execute("CREATE SCHEMA edition_trial")
            conn.execute("CREATE TABLE edition_trial.proof (generation integer PRIMARY KEY)")
            conn.execute("INSERT INTO edition_trial.proof VALUES (1)")
            return
        expected = [(1,)] if phase == "repair" else [(1,), (2,)]
        if conn.execute("SELECT generation FROM edition_trial.proof ORDER BY generation").fetchall() != expected:
            msg = f"The {phase} trial lost a committed application-database row"
            raise RuntimeError(msg)
        if phase == "repair":
            conn.execute("INSERT INTO edition_trial.proof VALUES (2)")


if __name__ == "__main__":
    main()
