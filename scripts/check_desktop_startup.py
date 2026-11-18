"""Qualify the installed personal desktop CLI on a disposable, clean OS account."""

# ruff: noqa: S603 -- run only this installed CLI in an explicitly disposable account.

from __future__ import annotations

import base64
import http.client
import json
import subprocess
import sys
import time
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

from lychd.system.desktop.private import private_directory
from lychd.system.services.local_access import load_local_access


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
    with TemporaryDirectory() as destination:
        parent = Path(destination).resolve()
        private_directory(parent)
        subprocess.run([*cli, "desktop", "backup", "--destination", str(parent)], check=True)
        (receipt,) = parent.glob("lychd-postgres-*/verified.json")
        evidence = json.loads(receipt.read_text(encoding="ascii"))
        if str(evidence["postgres_major"]) != "18" or (receipt.parent / "cluster/postmaster.pid").exists():
            msg = "Expected a verified, inactive PostgreSQL 18 recovery copy."
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
        check_registered_backup(cli)
        local = load_local_access()
        auth = base64.b64encode(f"{local.username}:{local.password.get_secret_value()}".encode()).decode("ascii")
        for _ in range(2):
            _exercise_vessel(cli, f"Basic {auth}")
    finally:
        subprocess.run([*cli, "desktop", "stop"], check=True)


if __name__ == "__main__":
    main()
