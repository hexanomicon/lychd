"""Recover one committed row, excluding a later write, from a cold macOS APFS copy."""

# ruff: noqa: S603 -- fixed installed CLI and PG tools on the fresh native trial account.
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg
from psycopg.conninfo import make_conninfo

from lychd.config.settings import Settings
from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop import postgres_program
from lychd.system.desktop.credentials import load_credentials
from lychd.system.desktop.volume_cluster import inventory


def main() -> None:
    load_credentials(administrative=True)
    db = Settings().server.database
    if sys.platform != "darwin" or not db.password:
        msg = "Use this probe only in the fresh macOS desktop trial."
        raise RuntimeError(msg)
    endpoint = make_conninfo(
        hostaddr="127.0.0.1",
        host="127.0.0.1",
        user=db.user,
        dbname="postgres",
        password=db.password.get_secret_value(),
        connect_timeout=5,
    )
    with psycopg.connect(endpoint, port=db.port) as source:
        source.execute("CREATE TABLE lychd_apfs_clone_trial (value integer PRIMARY KEY)")
        source.execute("INSERT INTO lychd_apfs_clone_trial VALUES (19)")
    with TemporaryDirectory(dir=PATH_POSTGRES_ROOT_DIR.parent) as directory:
        subprocess.run(
            [sys.executable, "-m", "lychd", "desktop", "backup", "--method", "apfs-clone", "--destination", directory],
            check=True,
        )
        with psycopg.connect(endpoint, port=db.port) as source:
            source.execute("INSERT INTO lychd_apfs_clone_trial VALUES (20)")
        (receipt,) = Path(directory).glob("lychd-postgres-*/verified.json")
        evidence = json.loads(receipt.read_bytes())
        recovered = receipt.parent / "cluster"
        if evidence["method"] != "apfs-file-clone-v1" or evidence["files"] != inventory(recovered, digest=True):
            msg = "The inactive APFS clone differs from its recorded cut."
            raise RuntimeError(msg)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = int(listener.getsockname()[1])
        ctl = [postgres_program("pg_ctl"), "-w", "-D", str(recovered)]
        options = f"-p {port} -h 127.0.0.1 -c unix_socket_directories="
        subprocess.run([*ctl, "-l", str(receipt.parent / "restore.log"), "-o", options, "start"], check=True)
        try:
            with psycopg.connect(endpoint, port=port) as restored:
                rows = restored.execute("SELECT value FROM lychd_apfs_clone_trial ORDER BY value").fetchall()
                if rows != [(19,)]:
                    msg = "Recovered copy did not preserve the committed row at the cut."
                    raise RuntimeError(msg)
            print(  # noqa: T201 -- emit the measured result to the qualification log.
                f"APFS clone verified with a second PostgreSQL instance. Pause {evidence['pause_seconds']:.3f}s, "
                f"total {evidence['total_seconds']:.3f}s."
            )
        finally:
            subprocess.run([*ctl, "-m", "fast", "stop"], check=True)


if __name__ == "__main__":
    main()
