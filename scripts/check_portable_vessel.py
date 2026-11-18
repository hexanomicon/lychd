"""Exercise two installations over persistent Compose volumes on a disposable CI engine."""

from __future__ import annotations

import base64
import http.client
import json
import shutil
import subprocess
import time
from http import HTTPStatus
from uuid import uuid4


def main() -> None:
    docker = shutil.which("docker")
    if docker is None:
        msg = "Docker with Compose v2 is required."
        raise RuntimeError(msg)
    # A unique project owns this test's volumes. All provisioned credentials stay on the runner.
    command = [docker, "compose", "-p", f"lychd-trial-{uuid4().hex}", "-f", "compose.yaml"]

    def compose(*arguments: str) -> str:
        return subprocess.run(  # noqa: S603 -- trusted local CI engine and fixed compose file
            [*command, *arguments], check=True, stdout=subprocess.PIPE, text=True, timeout=240
        ).stdout.strip()

    def check_access() -> str:
        password = compose("exec", "-T", "vessel", "cat", "/run/lychd/access/value")
        auth = "Basic " + base64.b64encode(f"magus:{password}".encode()).decode("ascii")
        for _ in range(120):
            connection = http.client.HTTPConnection("127.0.0.1", 7134, timeout=2)
            try:
                connection.request("GET", "/api/v1/altar/status")
                response = connection.getresponse()
                response.read()
                if response.status == HTTPStatus.UNAUTHORIZED:
                    break
            except (OSError, http.client.HTTPException):
                pass
            finally:
                connection.close()
            time.sleep(1)
        else:
            msg = "The published Vessel did not require browser authentication."
            raise RuntimeError(msg)
        connection = http.client.HTTPConnection("127.0.0.1", 7134, timeout=5)
        try:
            connection.request("GET", "/api/v1/altar/status", headers={"Authorization": auth})
            response = connection.getresponse()
            if response.status != HTTPStatus.OK or not json.loads(response.read()):
                msg = "The provisioned credential did not open Altar."
                raise RuntimeError(msg)
        finally:
            connection.close()
        return password

    postgres = ("exec", "-T", "database", "psql", "-v", "ON_ERROR_STOP=1", "-U", "lich", "-d", "lychd", "-Atc")
    try:
        compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
        password = check_access()
        compose(*postgres, "CREATE TABLE placement_probe AS SELECT 19 AS answer")
        compose("down")
        compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
        if check_access() != password or compose(*postgres, "SELECT answer FROM placement_probe") != "19":
            msg = "The original browser credential and committed database row must survive recreation."
            raise RuntimeError(msg)
    finally:
        compose("down", "--volumes")


if __name__ == "__main__":
    main()
