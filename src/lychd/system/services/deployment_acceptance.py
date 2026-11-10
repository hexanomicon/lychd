"""Bounded server-local acceptance for the native deployment profile.

Credentials remain masked until used in an in-memory loopback request. Redirects,
proxies and exception text cannot carry them into evidence. No ASGI application,
database driver, lifecycle operation or controller dependency is constructed here.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from lychd.system import btrfs_observer, constants
from lychd.system.btrfs_identity import BtrfsSubvolumeObservation
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.local_access import load_local_access

if TYPE_CHECKING:
    from lychd.config.settings import Settings
    from lychd.system.services.deployment import DeploymentInspectionService, DeploymentRequest

_API_PATHS = ("/api/v1/altar/status", "/orchestrator/status", "/orchestrator/queues")
_MAX_RESPONSE_BYTES = 1024 * 1024
_HTTP_OK = 200
_HTTP_UNAUTHORIZED = 401
_SS_LOCAL_ADDRESS_INDEX = 3
_PSQL = """set -eu
psql -U "${POSTGRES_USER:?}" -d lychd -AtX -v ON_ERROR_STOP=1 -c "select count(*) from information_schema.tables where table_schema not in ('pg_catalog','information_schema')"
psql -U "$POSTGRES_USER" -d lychd -AtX -v ON_ERROR_STOP=1 -c "select rolname||':'||rolsuper from pg_roles where rolname in ('lychd_runtime','lychd_phoenix') order by 1"
"""


async def _http_get_async(url: str, token: str | None) -> tuple[int, bytes]:
    from httpx2 import HTTPError

    from lychd.lib.http import create_async_http_client

    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = "Basic " + token
    try:
        async with (
            asyncio.timeout(20),
            create_async_http_client(timeout=20.0) as client,
            client.stream("GET", url, headers=headers) as response,
        ):
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_RESPONSE_BYTES:
                    return 0, b""
            return response.status_code, bytes(body)
    except (HTTPError, OSError, ValueError, TimeoutError):
        return 0, b""


def _http_get(url: str, token: str | None = None) -> tuple[int, bytes]:
    """Use the shared nonambient HTTP client; never follow a redirect."""
    address = urlsplit(url)
    if (
        address.scheme != "http"
        or address.hostname != "127.0.0.1"
        or address.username is not None
        or address.password is not None
    ):
        return 0, b""
    return asyncio.run(_http_get_async(url, token))


def api_checks() -> list[dict[str, Any]]:
    """Use the owned credential source without parsing the human access command."""
    try:
        access = load_local_access()
        base = access.url.rstrip("/")
        token = base64.b64encode(f"{access.username}:{access.password.get_secret_value()}".encode()).decode()
        wrong = base64.b64encode(f"{access.username}:wrong-{os.urandom(16).hex()}".encode()).decode()
    except (ValueError, OSError):
        return [{"name": "api.access", "ok": False, "detail": "local_credential_unavailable"}]
    checks: list[dict[str, Any]] = []
    bodies: dict[str, Any] = {}
    for path in _API_PATHS:
        anonymous, _ = _http_get(base + path)
        refused, _ = _http_get(base + path, wrong)
        status, body = _http_get(base + path, token)
        checks.append(
            {
                "name": f"api{path}",
                "ok": anonymous == refused == _HTTP_UNAUTHORIZED and status == _HTTP_OK,
                "detail": f"anonymous={anonymous} wrong={refused} authenticated={status}",
            }
        )
        try:
            value: object = json.loads(body) if status == _HTTP_OK else None
            bodies[path] = value if isinstance(value, dict) else {}
        except (ValueError, UnicodeError):
            bodies[path] = {}
    altar = bodies.get(_API_PATHS[0], {})
    checks.append(
        {
            "name": "api.database_readback",
            "ok": type(altar.get("pending_consents")) is int,
            "detail": "integer_readback",
        }
    )
    orchestrator = bodies.get(_API_PATHS[1], {})
    checks.append(
        {
            "name": "api.capabilities_empty",
            "ok": orchestrator.get("active_capabilities") == [] and orchestrator.get("all_capabilities") == [],
            "detail": "empty_profile",
        }
    )
    rows = bodies.get(_API_PATHS[2], {}).get("queues", [])
    queues = {row.get("name"): row for row in rows if isinstance(row, dict)} if isinstance(rows, list) else {}
    checks.append(
        {
            "name": "api.queues_idle",
            "ok": all(queues.get(name, {}).get("active") == 0 for name in ("runs", "rites")),
            "detail": "runs_and_rites_idle",
        }
    )
    return checks


def storage_check(service: DeploymentInspectionService) -> dict[str, Any]:
    """Join the existing receipt and descriptor observer without decoding receipt JSON."""
    path = constants.PATH_POSTGRESS_DATA_DIR
    mount = service.operator.storage.observe(path)
    if mount.warning:
        return {"name": "storage.phylactery", "ok": False, "detail": "storage_observation_unavailable"}
    if mount.mounted:
        return {"name": "storage.phylactery", "ok": True, "detail": "exact_mountpoint"}
    recorded = service.receipt.created_subvolume(path)
    if recorded is None:
        return {"name": "storage.phylactery", "ok": False, "detail": "no_creation_subvolume_identity"}
    # The namespace grants only the runtime user's existing subordinate-ID
    # mapping. Reuse the exact source's isolated, stdlib-only observer, including
    # its ABI/filesystem/root checks, rather than decoding an ioctl here.
    script = """import json, os, runpy, sys
fd = os.open(sys.argv[2], os.O_RDONLY | os.O_DIRECTORY | os.O_NONBLOCK | os.O_NOFOLLOW)
try:
    identity = os.fstat(fd)
    result = runpy.run_path(sys.argv[1])["observe"](fd)
    result.update(device=identity.st_dev, inode=identity.st_ino)
    print(json.dumps(result))
finally:
    os.close(fd)
"""
    try:
        import sys
        from pathlib import Path

        content = service.run(
            "podman",
            "unshare",
            str(Path(sys.executable).resolve(strict=True)),
            "-I",
            "-S",
            "-c",
            script,
            str(Path(btrfs_observer.__file__).resolve(strict=True)),
            str(path),
        )
        payload = json.loads(content)
        observed = BtrfsSubvolumeObservation(uuid=payload["uuid"], subvolume_id=payload["subvolume_id"])
        ok = (payload["device"], payload["inode"]) == (recorded.device, recorded.inode) and (
            observed.uuid,
            observed.subvolume_id,
        ) == (recorded.subvolume_uuid, recorded.subvolume_id)
    except (OSError, ValueError, KeyError, TypeError):
        ok = False
    return {"name": "storage.phylactery", "ok": ok, "detail": "receipt_and_live_identity"}


def verify_deployment(
    service: DeploymentInspectionService,
    *,
    settings: Settings,
    request: DeploymentRequest,
    units: dict[str, dict[str, str]],
    image: dict[str, str],
    active_units: set[str],
) -> list[dict[str, Any]]:
    """Observe acceptance; failures never initiate recovery or lifecycle effects."""
    from lychd.system.services.deployment import DeploymentObservationError

    checks = [
        {"name": "configuration.original", "ok": True, "detail": "original_creation_digest_and_profile"},
        {"name": "bindings.exact", "ok": True, "detail": "scribe_generation_and_invoking_cli"},
        *(
            {
                "name": f"unit.{name}",
                "ok": service.unit_active(value) if name in active_units else service.unit_quiescent(value),
                "detail": value["ActiveState"],
            }
            for name, value in sorted(units.items())
        ),
    ]
    migrate = units.get("lychd-migrate.service", {})
    checks.append(
        {
            "name": "migration.completed",
            "ok": migrate.get("Result") == "success" and migrate.get("ExecMainStatus") == "0",
            "detail": "systemd_migration_result",
        }
    )
    try:
        network = service.run("systemctl", "show", "network-online.target", "--property=ActiveState", "--value").strip()
        checks.append(
            {
                "name": "host.network-online",
                "ok": network == "active",
                "detail": network if network in {"active", "inactive", "failed"} else "unknown",
            }
        )
        listeners = []
        for line in service.run("ss", "-Hltn").splitlines():
            fields = line.split()
            if len(fields) > _SS_LOCAL_ADDRESS_INDEX and fields[_SS_LOCAL_ADDRESS_INDEX].endswith(
                f":{settings.server.port}"
            ):
                listeners.append(fields[_SS_LOCAL_ADDRESS_INDEX].rsplit(":", 1)[0].strip("[]"))
        checks.append(
            {
                "name": "listener.loopback_only",
                "ok": bool(listeners) and all(address in {"127.0.0.1", "::1"} for address in listeners),
                "detail": "loopback_listener_inventory",
            }
        )
        vessel = (
            service.run("podman", "container", "inspect", "lychd-vessel", "--format", "{{.Image}}")
            .strip()
            .removeprefix("sha256:")
        )
        checks.append(
            {
                "name": "image.running_identity",
                "ok": vessel == image["id"]
                and image["revision"] == request.revision
                and (request.image_id is None or image["id"] == request.image_id),
                "detail": "running_and_admitted_image_agree",
            }
        )
        lines = service.run("podman", "exec", "lychd-phylactery", "sh", "-c", _PSQL).split()
        checks.append(
            {
                "name": "database.tables",
                "ok": bool(lines) and lines[0].isdigit() and int(lines[0]) > 0,
                "detail": "application_tables_present",
            }
        )
        checks.append(
            {
                "name": "database.restricted_runtime_role",
                "ok": "lychd_runtime:false" in lines[1:],
                "detail": "runtime_role_not_superuser",
            }
        )
        checks.append(storage_check(service))
    except (DeploymentObservationError, LifecycleError, OSError, ValueError):
        checks.append({"name": "host.acceptance_observation", "ok": False, "detail": "observation_unavailable"})
    checks.extend(api_checks())
    return checks
