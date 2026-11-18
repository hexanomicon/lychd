"""Exercise the public desktop volume CLI on a new, disposable, already mounted native volume."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import psycopg

from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop import _settings, postgres_program
from lychd.system.desktop.private import private_directory
from lychd.system.desktop.volume_native import snapshot_view
from lychd.system.desktop.volume_storage import STORAGE, authority

CLI = [sys.executable, "-m", "lychd.system.desktop"]


def command(*args: str, check: bool = True, answer: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([*CLI, *args], input=answer, capture_output=True, text=True, check=False, timeout=240)  # noqa: S603
    if check and result.returncode:
        msg = f"{args} failed: {result.stdout}\n{result.stderr}"
        raise RuntimeError(msg)
    return result


def vss_capture(root: Path) -> None:
    """Wait for the separate VSS operator and pass its snapshot UUID to the desktop command."""
    with subprocess.Popen(  # noqa: S603
        [*CLI, "volume", "capture"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ) as process:
        try:
            deadline = time.monotonic() + 180
            while process.poll() is None and time.monotonic() < deadline:
                requests = list(root.glob(".lychd-volume-request-*"))
                if len(requests) == 1:
                    cut = str(UUID(requests[0].name.removeprefix(".lychd-volume-request-")))
                    receipt = Path(os.environ["PROGRAMFILES"]) / f"LychD-Volume-{cut}" / "snapshot.json"
                    if receipt.is_file():
                        result, _ = process.communicate(json.loads(receipt.read_bytes())["ID"] + "\n", timeout=60)
                        if process.returncode != 0:
                            raise RuntimeError(result)
                        return
                time.sleep(0.5)
            msg = "The native VSS operator did not produce a seal."
            raise RuntimeError(msg)
        finally:
            if process.poll() is None:
                process.kill()
            output, _ = process.communicate()
            print(output)  # noqa: T201


def trial(root: Path) -> None:
    default = PATH_POSTGRES_ROOT_DIR / "native-data"
    if default.exists() or authority(default).exists() or (root / STORAGE).exists():
        msg = "This trial requires a fresh disposable desktop account and dedicated empty volume."
        raise ValueError(msg)
    command("volume", "select-storage", "--root", str(root))
    command("install")
    try:
        command("volume", "register")
        db = _settings(admin=True).server.database
        if db.password is None:
            msg = "Missing disposable cluster credential."
            raise RuntimeError(msg)
        options = {
            "host": "127.0.0.1",
            "hostaddr": "127.0.0.1",
            "user": db.user,
            "password": db.password.get_secret_value(),
            "dbname": "postgres",
        }
        with psycopg.connect(**options, port=db.port) as connection:
            connection.execute("CREATE TABLE volume_drill(value text PRIMARY KEY)")
            connection.execute("INSERT INTO volume_drill VALUES ('captured')")
        if sys.platform == "darwin":
            rejected = command("volume", "capture", answer=str(uuid4()) + "\n", check=False)
            if not rejected.returncode or "Mount the specified APFS snapshot" not in rejected.stderr:
                raise RuntimeError(rejected.stdout + rejected.stderr)
            command("status")
            if list(authority(default).glob("capture-*.json")):
                msg = "An absent APFS snapshot was sealed."
                raise RuntimeError(msg)
            print("APFS disk image registered; cold cut rejected absent snapshot and resumed PostgreSQL.")  # noqa: T201
            return
        verify_windows(root, default, options, db.port)
    finally:
        command("stop")


def verify_windows(root: Path, default: Path, options: dict[str, str], port: int) -> None:
    vss_capture(root)
    captures = list(authority(default).glob("capture-*.json"))
    if len(captures) != 1:
        msg = "Expected exactly one native capture."
        raise RuntimeError(msg)
    record = json.loads(captures[0].read_bytes())
    try:
        snapshot_view(str(uuid4()), record["snapshot"], record["cut"])
    except ValueError:
        pass
    else:
        msg = "Another volume was admitted."
        raise RuntimeError(msg)
    with psycopg.connect(**options, port=port) as connection:
        connection.execute("INSERT INTO volume_drill VALUES ('later')")
    with TemporaryDirectory() as recovery:
        parent = Path(recovery)
        private_directory(parent)
        args = ("volume", "restore", "--capture", record["cut"], "--destination", str(parent))
        command(*args)
        (backup,) = parent.iterdir()
        verify_restored(backup, options)
        command("volume", "revoke")
        if not command(*args, check=False).returncode:
            msg = "Revocation admitted an old capture."
            raise RuntimeError(msg)
        command("volume", "register")
        if not command(*args, check=False).returncode:
            msg = "A fresh generation admitted an earlier capture."
            raise RuntimeError(msg)
        print(json.dumps(dict(record, recovered_row="captured", wrong_volume="refused", revoked="refused")))  # noqa: T201


def verify_restored(backup: Path, options: dict[str, str]) -> None:
    cluster = backup / "cluster"
    port = 55434
    ctl = [postgres_program("pg_ctl"), "-w", "-D", str(cluster)]
    subprocess.run(  # noqa: S603
        [
            *ctl,
            "-l",
            str(backup / "trial.log"),
            "-o",
            f"-h 127.0.0.1 -p {port} -c unix_socket_directories=",
            "start",
        ],
        check=True,
    )
    try:
        with psycopg.connect(**options, port=port) as connection:
            rows = connection.execute("SELECT value FROM volume_drill ORDER BY value").fetchall()
            location = connection.execute("SHOW data_directory").fetchone()
            if rows != [("captured",)] or not location or not cluster.samefile(location[0]):
                msg = "The recovered committed row or endpoint differs."
                raise RuntimeError(msg)
    finally:
        subprocess.run([*ctl, "-m", "fast", "stop"], check=True)  # noqa: S603


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    trial(parser.parse_args().root)
