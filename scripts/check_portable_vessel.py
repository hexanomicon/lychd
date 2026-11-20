"""Exercise two installations over persistent Compose volumes on a disposable CI engine."""

from __future__ import annotations

import base64
import http.client
import json
import shutil
import subprocess
import time
from collections.abc import Callable
from http import HTTPStatus
from pathlib import PurePosixPath
from uuid import uuid4


def pids_limit_path(membership: str, mountinfo: str) -> str:
    groups = [line.split(":", 2) for line in membership.splitlines()]
    legacy = next((path for _, controllers, path in groups if "pids" in controllers.split(",")), None)
    group = legacy if legacy is not None else next((path for hierarchy, _, path in groups if hierarchy == "0"), None)
    if group is not None:
        for line in mountinfo.splitlines():
            before, after = line.split(" - ")
            filesystem, _, options = after.split()[:3]
            if (legacy is None and filesystem == "cgroup2") or (
                legacy is not None and filesystem == "cgroup" and "pids" in options.split(",")
            ):
                root, mount = map(PurePosixPath, before.split()[3:5])
                # A private cgroup namespace reports the mounted subtree as its own root.
                relative = PurePosixPath(group).relative_to(root if PurePosixPath(group).is_relative_to(root) else "/")
                return str(mount / relative / "pids.max")
    msg = "Cannot locate the container's pids cgroup controller."
    raise RuntimeError(msg)


def check_container_limits(compose: Callable[..., str]) -> None:
    mountinfo = compose("exec", "-T", "vessel", "cat", "/proc/self/mountinfo")
    mounts = {fields[4]: set(fields[5].split(",")) for fields in map(str.split, mountinfo.splitlines())}
    if "ro" not in mounts["/"] or not {"rw", "nosuid", "nodev", "noexec"} <= mounts["/tmp"]:  # noqa: S108 -- inspecting a container mount
        msg = "The Vessel requires a read-only root and restricted writable /tmp."
        raise RuntimeError(msg)
    for service in ("vessel", "database"):
        membership = compose("exec", "-T", service, "cat", "/proc/self/cgroup")
        service_mounts = (
            mountinfo if service == "vessel" else compose("exec", "-T", service, "cat", "/proc/self/mountinfo")
        )
        limit = compose("exec", "-T", service, "cat", pids_limit_path(membership, service_mounts))
        if limit != "512":
            msg = f"Expected a 512-task cgroup ceiling for {service}, found {limit}."
            raise RuntimeError(msg)


def check_vessel_files(compose: Callable[..., str]) -> None:
    compose("exec", "-T", "database", "test", "-r", "/run/lychd/admin/value")
    compose(
        "exec",
        "-T",
        "vessel",
        "python",
        "-c",
        """import errno
import os
import tempfile
from pathlib import Path

pid1_uid = next(line.split()[2] for line in Path("/proc/1/status").read_text().splitlines() if line.startswith("Uid:"))
if os.geteuid() == 0 or os.geteuid() != int(pid1_uid):
    raise RuntimeError("Probe must use the unprivileged Vessel process identity")
for path, flags, allowed_errors in (
    ("/run/lychd/admin/value", os.O_RDONLY, {errno.ENOENT, errno.EACCES}),
    ("/run/lychd/runtime/value", os.O_WRONLY, {errno.EROFS, errno.EACCES}),
    ("/app/LICENSE", os.O_WRONLY, {errno.EROFS, errno.EACCES}),
):
    try:
        fd = os.open(path, flags | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno not in allowed_errors:
            raise
    else:
        os.close(fd)
        raise RuntimeError(f"Unexpected access to {path}")
with tempfile.NamedTemporaryFile(dir="/home/lich/.local/share/lychd/lab") as probe:
    probe.write(b"lab control")
    probe.flush()
""",
    )


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
        check_container_limits(compose)
        check_vessel_files(compose)
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
