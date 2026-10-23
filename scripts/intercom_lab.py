"""Explicit single-startup operator session for the outbound public-text profile.

Use --config PUBLIC_CONFIG_JSON and JSON command lines on stdin. The database URL
and signing-key file come from named environment variables. The entered password
is checked against the installation's actual dedicated local-access credential.
A public-source declaration is live only for this startup and this exact owner.
"""

from __future__ import annotations

# Standalone operator script; no Python package is introduced.
import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lychd.db.intercom import IntercomStore, IntercomStoreError
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.peer import CapacityLimit, PeerAuthorityError, PeerPolicy, PublicDeclaration, PublicTextSource
from lychd.system.services.intercom import IntercomService, IntercomUnknownError
from lychd.system.services.local_access import load_local_access
from lychd.system.services.peer_authority import PeerAuthority


def policy_from_record(value: dict[str, Any]) -> PeerPolicy:
    """Decode explicit public selectors; missing fields refuse at startup."""
    limits = value["limits"]
    return PeerPolicy(
        generation=value["generation"],
        actions=frozenset(value["actions"]),
        purposes=frozenset(value["purposes"]),
        categories=frozenset(value["categories"]),
        task_schemas=frozenset(value["task_schemas"]),
        peers=frozenset(UUID(item) for item in value["peers"]),
        endpoints=frozenset(value["endpoints"]),
        host_limit=CapacityLimit(**limits["host"]),
        purpose_limit=CapacityLimit(**limits["purpose"]),
        peer_limit=CapacityLimit(**limits["peer"]),
        task_limit=CapacityLimit(**limits["task"]),
        declaration_seconds=value.get("declaration_seconds", 300),
        task_seconds=value.get("task_seconds", 900),
        network_seconds=value.get("network_seconds", 30),
    )


def _target(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "peer_id": UUID(command["peer_id"]),
        "purpose": command["purpose"],
        "task_schema": command["task_schema"],
        "endpoint": command["endpoint"],
        "category": command.get("category", "public-task"),
    }


def _public_peer(peer: dict[str, Any]) -> dict[str, Any]:
    return {
        key: peer.get(key)
        for key in ("peer_id", "key_version", "policy_generation", "revocation_generation", "revoked")
    }


async def operate(  # noqa: PLR0911 - explicit closed operation dispatcher
    service: IntercomService,
    authentication: object,
    command: dict[str, Any],
    declarations: dict[UUID, PublicDeclaration],
) -> dict[str, Any]:
    """Dispatch named production operations; foreign output is never executed."""
    operation = command["operation"]
    if operation == "declare-public":
        target = _target(command)
        target.pop("category")
        declaration = await service.declare_public(
            authentication, source=PublicTextSource(**command["source"]), **target
        )
        declarations[declaration.declaration_id] = declaration
        return {"declaration_id": str(declaration.declaration_id), "expires_at": declaration.expires_at.isoformat()}
    if operation == "submit":
        return await service.submit(authentication, declaration=declarations[UUID(command["declaration_id"])])
    if operation == "enroll":
        return _public_peer(await service.enroll(authentication, key=command["key"], **_target(command)))
    if operation == "rotate":
        return _public_peer(await service.rotate(authentication, key=command["key"], **_target(command)))
    if operation == "revoke":
        return _public_peer(await service.revoke(authentication, **_target(command)))
    if operation in {"poll", "cancel", "read"}:
        arguments: dict[str, Any] = {**_target(command), "task_id": UUID(command["task_id"])}
        if operation == "poll":
            return await service.poll(authentication, **arguments)
        if operation == "cancel":
            return await service.cancel(authentication, **arguments)
        retained = await service.read(authentication, **arguments)
        return {
            key: retained.get(key)
            for key in (
                "task_id",
                "status",
                "foreign_task_id",
                "foreign_status",
                "context_id",
                "result",
                "cancellation_observation",
            )
        }
    msg = "Unknown operator operation."
    raise ValueError(msg)


async def run_session(configuration: dict[str, Any], password: str) -> None:
    """Own one control loop and dispose its database pool when stdin closes."""
    access = LocalOperatorAccess(access_password=load_local_access().password.get_secret_value())
    authority = PeerAuthority(access=access, policy=policy_from_record(configuration["policy"]))
    authentication = access.authenticate(username=b"magus", password=password.encode())
    if authentication is None:
        msg = "Operator authentication failed."
        raise ValueError(msg)
    key_path = Path(os.environ["LYCHD_INTERCOM_SIGNING_KEY_FILE"])
    if not key_path.is_absolute():
        msg = "Signing-key path must be absolute."
        raise ValueError(msg)
    engine = create_async_engine(os.environ["LYCHD_INTERCOM_DATABASE_URL"], echo=False, hide_parameters=True)
    try:
        service = IntercomService(
            store=IntercomStore(async_sessionmaker(engine, expire_on_commit=False)),
            authority=authority,
            workload_id=UUID(configuration["workload_id"]),
            signing_key=key_path.read_bytes(),  # noqa: ASYNC240 - startup secret read before live effects
            signing_key_id=configuration["signing_key_id"],
        )
        declarations: dict[UUID, PublicDeclaration] = {}
        for line in sys.stdin:
            try:
                result = await operate(service, authentication, cast("dict[str, Any]", json.loads(line)), declarations)
            except IntercomUnknownError as error:
                result = {"error": "unknown", "task_id": str(error.task_id)}
            except (PeerAuthorityError, IntercomStoreError) as error:
                result = {"error": error.code}
            except (KeyError, TypeError, ValueError):
                result = {"error": "input"}
            print(json.dumps(result, sort_keys=True), flush=True)  # noqa: T201 - explicit operator projection
    finally:
        access.revoke()
        await engine.dispose()


def main() -> None:
    """Start an explicit operator session; --help performs no external effect."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    configuration = cast("dict[str, Any]", json.loads(arguments.config.read_text()))
    try:
        asyncio.run(run_session(configuration, getpass.getpass("Dedicated local operator password: ")))
    except Exception:  # noqa: BLE001 - never print startup credential/driver diagnostics
        print('{"error":"startup-refused"}', file=sys.stderr)  # noqa: T201 - closed operator error
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
