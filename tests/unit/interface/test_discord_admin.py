"""Offline operator-plan contracts; MockTransport has no Discord connection."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from lychd.interface.discord import admin
from lychd.interface.discord.admin import (
    AdminError,
    CategoryLayout,
    ChannelLayout,
    DeveloperLayout,
    PermissionIntent,
    RoleLayout,
    ServerPlan,
    apply_plan,
    developer_layout,
    plan_layout,
    snapshot_guild,
)
from lychd.interface.discord.rest import DiscordRest, EffectJournal

_NOW = datetime(2026, 10, 27, tzinfo=UTC)
_SYNTHETIC = "synthetic-token"


class DiscordFixture:
    """A deterministic server whose writes update subsequent snapshot reads."""

    def __init__(self) -> None:
        self.guild: dict[str, Any] = {"id": "103", "owner_id": "105"}
        self.roles: list[dict[str, Any]] = [
            {"id": "103", "name": "@everyone", "permissions": "0", "position": 0, "managed": False},
            {"id": "106", "name": "UserbotAdmin", "permissions": "8", "position": 5, "managed": True},
        ]
        self.channels: list[dict[str, Any]] = [
            {
                "id": "104",
                "name": "reach",
                "type": 0,
                "parent_id": None,
                "topic": "Old topic",
                "permission_overwrites": [{"id": "109", "type": 1, "allow": "64", "deny": "0"}],
            }
        ]
        self.writes: list[tuple[str, str, dict[str, Any]]] = []
        self.fail_create = False
        self.duplicate_create = False
        self.next_id = 200

    def _read(self, path: str) -> httpx.Response:
        values = {
            "/users/@me": {"id": "102", "bot": True},
            "/oauth2/applications/@me": {"id": "101"},
            "/guilds/103": self.guild,
            "/guilds/103/roles": self.roles,
            "/guilds/103/channels": self.channels,
            "/guilds/103/members/102": {"user": {"id": "102", "bot": True}, "roles": ["106"]},
        }
        if path not in values:
            message = "Unexpected fixed GET route"
            raise AssertionError(message)
        return httpx.Response(200, json=values[path])

    def _create(self, path: str, body: dict[str, Any]) -> httpx.Response:
        self.next_id += 1
        created = {"id": str(self.next_id), **body}
        if path == "/guilds/103/roles":
            for role in self.roles:
                if role["position"] >= 1:
                    role["position"] += 1
            created.update(position=1, managed=False)
            target = self.roles
        elif path == "/guilds/103/channels":
            created.setdefault("parent_id", None)
            created.setdefault("topic", None)
            target = self.channels
        else:
            message = "Unexpected POST route"
            raise AssertionError(message)
        target.append(created)
        if self.duplicate_create:
            target.append({**created, "id": "999"})
        return httpx.Response(200, json=created)

    def request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v10")
        if request.method == "GET":
            return self._read(path)
        body = json.loads(request.content)
        self.writes.append((request.method, path, body))
        if self.fail_create:
            return httpx.Response(500, json={"message": "synthetic failure"})
        if request.method == "POST":
            return self._create(path, body)
        if request.method == "PATCH" and path == "/channels/104":
            self.channels[0].update(body)
            return httpx.Response(200, json=self.channels[0])
        message = "Unexpected write route"
        raise AssertionError(message)


def configured(rest_root: Path, server: DiscordFixture, client: httpx.AsyncClient) -> DiscordRest:
    return DiscordRest(
        token=_SYNTHETIC,
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        journal=EffectJournal(rest_root),
        client=client,
    )


def layout() -> DeveloperLayout:
    return developer_layout(
        application_id="101", bot_user_id="102", guild_id="103", owner_id="105", reach_channel_id="104"
    )


@pytest.mark.asyncio
async def test_pure_plan_roundtrip_and_explicit_reach_patch(tmp_path: Path) -> None:
    server = DiscordFixture()
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        snapshot = await snapshot_guild(rest)
        first = plan_layout(layout(), snapshot, now=_NOW)
        second = plan_layout(layout(), snapshot, now=_NOW)
        assert first == second
        assert first.digest == second.digest
        assert ServerPlan.model_validate_json(first.model_dump_json()).digest == first.digest
        assert first.expires_at - first.created_at == timedelta(minutes=15)
        assert len(first.operations) <= 32
        assert all(item.action in {"create", "patch"} for item in first.operations)
        assert [item.target_id for item in first.operations if item.action == "patch"] == ["104"]
        assert not server.writes


@pytest.mark.asyncio
async def test_default_apply_is_additive_reconciled_and_idempotent(tmp_path: Path) -> None:
    server = DiscordFixture()
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        before = copy.deepcopy(server.channels[0]["permission_overwrites"])
        plan = plan_layout(layout(), await snapshot_guild(rest), now=_NOW)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "succeeded"
        assert len(result.operations) == len(plan.operations)
        assert server.channels[0]["name"] == "the-reach"
        assert server.channels[0]["permission_overwrites"] == before
        assert server.roles[1]["permissions"] == "8"
        assert all(
            body.get("permissions", "0") == "0" for _method, path, body in server.writes if path.endswith("/roles")
        )
        again = plan_layout(layout(), await snapshot_guild(rest), now=_NOW)
        assert again.operations == ()
        assert len({record.effect_key_digest for record in rest.journal.inspect()}) == len(plan.operations)


@pytest.mark.parametrize("change", ["digest", "expired", "stale", "owner"])
@pytest.mark.asyncio
async def test_refused_plan_makes_zero_writes(tmp_path: Path, change: str) -> None:
    server = DiscordFixture()
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        plan = plan_layout(layout(), await snapshot_guild(rest), now=_NOW)
        digest, now = plan.digest, _NOW
        if change == "digest":
            digest = "0" * 64
        elif change == "expired":
            now += timedelta(minutes=15)
        elif change == "stale":
            server.channels[0]["topic"] = "Changed after review"
        else:
            server.guild["owner_id"] = "999"
        result = await apply_plan(rest, plan, expected_digest=digest, now=now)
        assert result.status == "rejected"
        assert not server.writes


@pytest.mark.asyncio
async def test_server_error_fences_the_same_resource_across_new_plans(tmp_path: Path) -> None:
    server = DiscordFixture()
    server.fail_create = True
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        snapshot = await snapshot_guild(rest)
        plan = plan_layout(layout(), snapshot, now=_NOW)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "unknown"
        assert len(server.writes) == 1
        reopened = configured(tmp_path / "journal", server, client)
        next_plan = plan_layout(layout(), snapshot, now=_NOW + timedelta(seconds=1))
        result = await apply_plan(
            reopened, next_plan, expected_digest=next_plan.digest, now=_NOW + timedelta(seconds=1)
        )
        assert result.code == "scope_unresolved"
        assert len(server.writes) == 1


@pytest.mark.asyncio
async def test_successful_create_with_duplicates_is_unknown_and_durable(tmp_path: Path) -> None:
    server = DiscordFixture()
    server.duplicate_create = True
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        plan = plan_layout(layout(), await snapshot_guild(rest), now=_NOW)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "unknown"
        assert result.code == "create_reconciliation_mismatch"
        assert len(server.writes) == 1
        assert rest.journal.inspect()[0].status == "unknown"
        assert result.operations[0].remote_id is not None


@pytest.mark.asyncio
async def test_explicit_channel_patch_preserves_unrelated_overwrite_bits(tmp_path: Path) -> None:
    server = DiscordFixture()
    server.channels.append(
        {"id": "110", "name": "START", "type": 4, "parent_id": None, "topic": None, "permission_overwrites": []}
    )
    desired = DeveloperLayout(
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        owner_id="105",
        categories=(CategoryLayout(key="start", name="START"),),
        channels=(
            ChannelLayout(
                key="reach",
                name="the-reach",
                existing_id="104",
                parent_key="start",
                overwrites=(PermissionIntent(target="member", member_id="109", deny=1 << 10),),
            ),
        ),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        plan = plan_layout(desired, await snapshot_guild(rest), now=_NOW)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "succeeded"
        assert len(server.writes) == 1
        assert server.writes[0][0] == "PATCH"
        assert server.channels[0]["permission_overwrites"] == [{"id": "109", "type": 1, "allow": "64", "deny": "1024"}]
        assert server.channels[0]["topic"] == "Old topic"


@pytest.mark.asyncio
async def test_ambiguous_names_do_not_authorize_adoption(tmp_path: Path) -> None:
    server = DiscordFixture()
    server.roles.extend(
        {"id": identity, "name": "Core", "permissions": "0", "position": 1, "managed": False}
        for identity in ("120", "121")
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        with pytest.raises(AdminError, match="ambiguous_role"):
            plan_layout(layout(), await snapshot_guild(rest), now=_NOW)
        assert not server.writes


@pytest.mark.parametrize("permissions", [8, 16, 32, 1 << 28])
def test_administrative_role_grants_are_not_a_layout_option(permissions: int) -> None:
    with pytest.raises(ValidationError):
        RoleLayout(key="admin", name="Admin", permissions=permissions)


def test_layout_rejects_unknown_fields_and_bool_schema() -> None:
    data = layout().model_dump()
    with pytest.raises(ValidationError):
        DeveloperLayout.model_validate(data | {"delete_channels": True})
    with pytest.raises(ValidationError):
        DeveloperLayout.model_validate(data | {"schema_version": True})


@pytest.mark.asyncio
async def test_plan_expiry_during_apply_retains_completed_results_and_stops_next_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = DiscordFixture()
    elapsed = [100.0]
    monkeypatch.setattr(admin, "monotonic", lambda: elapsed[0])

    def delayed(request: httpx.Request) -> httpx.Response:
        response = server.request(request)
        if request.method == "POST":
            elapsed[0] = 1001.0
        return response

    desired = DeveloperLayout(
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        owner_id="105",
        roles=(RoleLayout(key="first", name="First"), RoleLayout(key="second", name="Second")),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(delayed)) as client:
        rest = configured(tmp_path / "journal", server, client)
        plan = plan_layout(desired, await snapshot_guild(rest), now=_NOW)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "rejected"
        assert result.code == "plan_expired"
        assert len(server.writes) == 1
        assert len(result.operations) == 1
        assert result.operations[0].key == "first"
        assert result.operations[0].status == "succeeded"
        assert len(result.resources) == 1
        assert result.resources[0].remote_id == result.operations[0].remote_id
        assert len(rest.journal.inspect()) == 1


@pytest.mark.asyncio
async def test_explicit_reach_rename_releases_general_without_double_adoption(tmp_path: Path) -> None:
    server = DiscordFixture()
    server.channels[0].update(name="general", parent_id="110", topic=None, permission_overwrites=[])
    server.channels.append(
        {"id": "110", "name": "COMMUNITY", "type": 4, "parent_id": None, "topic": None, "permission_overwrites": []}
    )
    default = layout()
    # Exercise dependency ordering even when the implicit name is listed first.
    desired = default.model_copy(
        update={"channels": tuple(sorted(default.channels, key=lambda item: item.key != "general"))}
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(server.request)) as client:
        rest = configured(tmp_path / "journal", server, client)
        plan = plan_layout(desired, await snapshot_guild(rest), now=_NOW)
        operations = [item.key for item in plan.operations]
        assert operations.index("reach") < operations.index("general")
        assert not any(item.key == "general" for item in plan.existing)
        result = await apply_plan(rest, plan, expected_digest=plan.digest, now=_NOW)
        assert result.status == "succeeded"
        reach = [item for item in server.channels if item["name"] == "the-reach"]
        general = [item for item in server.channels if item["name"] == "general"]
        assert len(reach) == 1
        assert len(general) == 1
        assert reach[0]["id"] == "104"
        assert general[0]["id"] != reach[0]["id"]
        again = plan_layout(desired, await snapshot_guild(rest), now=_NOW)
        assert again.operations == ()
