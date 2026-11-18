"""Qualify the installed personal desktop CLI on a disposable, clean OS account."""

# ruff: noqa: S603 -- run only this installed CLI in an explicitly disposable account.

from __future__ import annotations

import base64
import http.client
import json
import os
import subprocess
import sys
import time
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg

from lychd.system.desktop.private import private_directory
from lychd.system.services.local_access import load_local_access

_INTERRUPTED_ROTATION = 74


def request(route: str, credential: str | None = None) -> tuple[int, bytes, str | None]:
    connection = http.client.HTTPConnection("127.0.0.1", 7134, timeout=3)
    try:
        headers = {"Authorization": credential} if credential else {}
        connection.request("GET", route, headers=headers)
        response = connection.getresponse()
        return response.status, response.read(), response.getheader("Location")
    finally:
        connection.close()


def check_routes(credential: str) -> None:
    status, _, location = request("/", credential)
    if status != HTTPStatus.FOUND or location != "/orb":
        msg = f"Unexpected Altar entry: {status}, expected a local redirect to /orb."
        raise RuntimeError(msg)
    for route in ("/orb", "/bridge", "/api/v1/altar/status"):
        status, body, _ = request(route, credential)
        if status != HTTPStatus.OK or not body:
            msg = f"Authenticated {route} returned {status} or an empty response."
            raise RuntimeError(msg)
        if route == "/api/v1/altar/status":
            json.loads(body)
        elif b"_app/" not in body:
            msg = f"The installed Altar assets were absent at {route}."
            raise RuntimeError(msg)


def _exercise_vessel(cli: list[str], credential: str) -> None:
    process = subprocess.Popen([*cli, "start"])
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline and process.poll() is None:
            try:
                if request("/api/v1/altar/status")[0] == HTTPStatus.UNAUTHORIZED:
                    break
            except OSError:
                pass
            time.sleep(0.2)
        else:
            msg = "Vessel failed to present the authenticated local API."
            raise RuntimeError(msg)
        check_routes(credential)
        subprocess.run([*cli, "stop"], check=True, timeout=100)
        if process.wait(timeout=30) != 0:
            msg = "Vessel did not stop cleanly."
            raise RuntimeError(msg)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def check_registered_backup(cli: list[str]) -> None:
    """Exercise the installed backup command and inspect its verified recovery copy."""
    if sys.platform == "darwin":
        subprocess.run([sys.executable, str(Path(__file__).with_name("check_desktop_apfs_clone.py"))], check=True)
    with TemporaryDirectory() as destination:
        parent = Path(destination).resolve()
        private_directory(parent)
        subprocess.run([*cli, "desktop", "backup", "--destination", str(parent)], check=True)
        (receipt,) = parent.glob("lychd-postgres-*/verified.json")
        evidence = json.loads(receipt.read_text(encoding="ascii"))
        if str(evidence["postgres_major"]) != "18" or (receipt.parent / "cluster/postmaster.pid").exists():
            msg = "Expected a verified, inactive PostgreSQL 18 recovery copy."
            raise RuntimeError(msg)


def interrupt_rotation(destination: Path) -> None:
    """Test-only fault at the filesystem publication following the committed role change."""
    from unittest.mock import patch

    from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
    from lychd.system.desktop import desktop, password_rotation
    from lychd.system.desktop.private import publish_file

    active = PATH_POSTGRES_ROOT_DIR / "desktop-credentials" / "lychd_runtime_db_password"

    def interrupt(path: Path, value: bytes, *, replace: bool = False) -> None:
        if path == active and replace:
            os._exit(_INTERRUPTED_ROTATION)
        publish_file(path, value, replace=replace)

    with patch.object(password_rotation, "publish_file", interrupt):
        desktop.main(["rotate-runtime-password", "--recovery-directory", str(destination)], standalone_mode=False)


def check_password_rotation(cli: list[str]) -> None:
    """Keep a real runtime connection open across the CLI operation and retest both passwords."""
    from lychd.config.settings import Settings
    from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
    from lychd.system.desktop import postgres_program
    from lychd.system.desktop.credentials import load_credentials

    load_credentials()
    db = Settings().server.database
    if not db.runtime_password:
        msg = "Missing original runtime credential"
        raise RuntimeError(msg)
    previous = db.runtime_password.get_secret_value()
    from psycopg.conninfo import make_conninfo

    args = {
        "host": "127.0.0.1",
        "hostaddr": "127.0.0.1",
        "user": db.runtime_user,
        "dbname": db.database,
        "port": str(db.port),
    }
    conninfo = make_conninfo(**args)
    with TemporaryDirectory() as directory:
        target = Path(directory).resolve()
        private_directory(target)
        with psycopg.connect(conninfo, autocommit=True, password=previous) as old_session:
            interrupted = subprocess.run([sys.executable, __file__, "--interrupt-rotation", str(target)], check=False)
            if interrupted.returncode != _INTERRUPTED_ROTATION:
                msg = "Rotation failed to reach the injected post-commit interruption."
                raise RuntimeError(msg)
            try:
                old_session.execute("SELECT current_user")
            except psycopg.OperationalError:
                pass
            else:
                msg = "Previously open runtime connection survived rotation"
                raise RuntimeError(msg)
            # A reboot stops this account-owned database. Reproduce its stopped state before retry.
            subprocess.run(
                [
                    postgres_program("pg_ctl"),
                    "-w",
                    "-D",
                    str(PATH_POSTGRES_ROOT_DIR / "native-data"),
                    "-m",
                    "fast",
                    "stop",
                ],
                check=True,
            )
            subprocess.run(
                [*cli, "desktop", "rotate-runtime-password", "--recovery-directory", str(target)], check=True
            )
        try:
            unexpected = psycopg.connect(conninfo, autocommit=True, password=previous)
        except psycopg.OperationalError:
            pass
        else:
            unexpected.close()
            msg = "The previous password still authenticates"
            raise RuntimeError(msg)
        current = (target / "lychd_runtime_db_password").read_text(encoding="ascii")
        with psycopg.connect(conninfo, autocommit=True, password=current) as fresh:
            if fresh.execute("SELECT current_user").fetchone() != (db.runtime_user,):
                msg = "Runtime role identity mismatch after password rotation"
                raise RuntimeError(msg)


def main() -> None:
    if sys.platform not in {"win32", "darwin"}:
        msg = "Use a disposable Windows or macOS account."
        raise SystemExit(msg)
    cli = [sys.executable, "-m", "lychd"]
    profile = json.loads(subprocess.check_output([*cli, "platform"], text=True))
    if profile["profile"] != "personal-desktop" or any(Path(profile[key]).exists() for key in ("data", "config")):
        msg = "A fresh personal installation is required."
        raise SystemExit(msg)
    subprocess.run([*cli, "desktop", "install"], check=True)
    try:
        subprocess.run([*cli, "desktop", "install"], check=True)
        check_password_rotation(cli)
        check_registered_backup(cli)
        local = load_local_access()
        auth = base64.b64encode(f"{local.username}:{local.password.get_secret_value()}".encode()).decode("ascii")
        for _ in range(2):
            _exercise_vessel(cli, f"Basic {auth}")
    finally:
        subprocess.run([*cli, "desktop", "stop"], check=True)


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["--interrupt-rotation", destination]:
            interrupt_rotation(Path(destination))
        case []:
            main()
        case _:
            raise SystemExit(2)
