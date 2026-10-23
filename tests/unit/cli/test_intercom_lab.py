from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from scripts.intercom_lab import operate

from lychd.domain.codex.peer import PublicDeclaration
from tests.unit.system.services.test_intercom import setup


@pytest.mark.asyncio
async def test_declare_and_source_read_use_actual_production_service_and_marker() -> None:
    service, _, _, marker, peer_id, uri, _ = await setup()
    declarations: dict[UUID, PublicDeclaration] = {}
    command: dict[str, Any] = {
        "operation": "declare-public",
        "peer_id": str(peer_id),
        "purpose": "test-public",
        "task_schema": "public.text@1",
        "endpoint": uri,
        "category": "public-task",
        "source": {"text": "explicit operator public text", "public_assertion": True},
    }
    result = await operate(service, marker, command, declarations)
    assert UUID(result["declaration_id"]) in declarations
    assert declarations[UUID(result["declaration_id"])].target.endpoint == uri
    with pytest.raises(KeyError):
        await operate(
            service,
            marker,
            {"operation": "submit", "declaration_id": "00000000-0000-0000-0000-000000000001"},
            declarations,
        )


@pytest.mark.asyncio
async def test_enroll_command_uses_explicit_endpoint_record() -> None:
    service, custody, _, marker, peer_id, _, key = await setup()
    result = await operate(
        service,
        marker,
        {
            "operation": "enroll",
            "peer_id": str(peer_id),
            "purpose": "test-public",
            "task_schema": "public.text@1",
            "endpoint": custody.peers[peer_id]["endpoint"],
            "key": key,
        },
        {},
    )
    assert result["peer_id"] == str(peer_id)
    assert "current_key" not in result
    assert "endpoint" not in result
