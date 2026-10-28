from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal, EffectResult


def transport(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)


def make_rest(tmp_path: Path, client: httpx.AsyncClient) -> DiscordRest:
    return DiscordRest(
        token="synthetic-bot-secret",  # noqa: S106 - synthetic fixture credential
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        journal=EffectJournal(tmp_path / "attempts"),
        client=client,
    )


def identity(request: httpx.Request) -> httpx.Response | None:
    if request.url.path == "/api/v10/users/@me":
        return httpx.Response(200, json={"id": "102", "bot": True})
    if request.url.path == "/api/v10/oauth2/applications/@me":
        return httpx.Response(200, json={"id": "101"})
    return None


@pytest.mark.parametrize(
    ("user", "application"),
    [
        ({"id": "999", "bot": True}, {"id": "101"}),
        ({"id": "102", "bot": False}, {"id": "101"}),
        ({"id": "102", "bot": True}, {"id": "999"}),
    ],
)
@pytest.mark.asyncio
async def test_separate_user_and_application_identity_checks_allow_zero_writes(
    tmp_path: Path, user: dict[str, Any], application: dict[str, Any]
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        data = user if request.url.path.endswith("/users/@me") else application
        return httpx.Response(200, json=data)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        with pytest.raises(DiscordRestError, match=r"^identity_mismatch$"):
            await rest.verify_identity()
        result = await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="a", scope="role:a")
    assert result.code == "identity_not_verified"
    assert [request.method for request in requests] == ["GET", "GET"]
    assert rest.journal.inspect() == ()


@pytest.mark.asyncio
async def test_post_500_attempts_once_and_blocks_restart_and_new_plan_scope(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(500, json={"message": "do not retain this response"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        with rest.journal.lock():
            first = await rest.write(
                "POST", "/guilds/103/roles", {"name": "safe"}, effect_key="plan1:a", scope="role:a"
            )
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        duplicate = await restarted.write(
            "POST", "/guilds/103/roles", {"name": "safe"}, effect_key="plan1:a", scope="role:a"
        )
        changed_plan = await restarted.write(
            "POST", "/guilds/103/roles", {"name": "safe"}, effect_key="plan2:a", scope="role:a"
        )
    assert first.status == "unknown"
    assert first.code == "http_500"
    assert duplicate.code == "effect_unresolved"
    assert changed_plan.code == "scope_unresolved"
    assert len(writes) == 1
    assert restarted.journal.inspect()[0].status == "unknown"


@pytest.mark.asyncio
async def test_success_duplicate_is_reused_but_changed_payload_refuses(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(201, json={"id": "104"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        first = await rest.write("POST", "/guilds/103/channels", {"name": "safe"}, effect_key="one", scope="channel:a")
        duplicate = await rest.write(
            "POST", "/guilds/103/channels", {"name": "safe"}, effect_key="one", scope="channel:a"
        )
        changed = await rest.write(
            "POST", "/guilds/103/channels", {"name": "other"}, effect_key="one", scope="channel:a"
        )
    assert first == duplicate == EffectResult(status="succeeded", remote_id="104")
    assert changed.code == "effect_payload_changed"
    assert len(writes) == 1


@pytest.mark.asyncio
async def test_failed_create_reconciliation_fences_success_and_new_plan(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        assert rest.journal.inspect()[0].status == "attempting"
        return httpx.Response(201, json={"id": "104"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        with rest.journal.lock():
            result = await rest.write(
                "POST", "/guilds/103/channels", {"name": "safe"}, effect_key="plan1:a", scope="channel:a"
            )
            rest.journal.mark_unknown("plan1:a", code="create_reconciliation_mismatch")
        assert result.status == "succeeded"
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        refused = await restarted.write(
            "POST", "/guilds/103/channels", {"name": "safe"}, effect_key="plan2:a", scope="channel:a"
        )
    assert refused.code == "scope_unresolved"
    assert len(writes) == 1
    record = restarted.journal.inspect()[0]
    assert record.status == "unknown"
    assert record.remote_id == "104"
    assert record.code == "create_reconciliation_mismatch"


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
@pytest.mark.asyncio
async def test_definite_4xx_rejection_never_retries(tmp_path: Path, status: int) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(status, text="a secret provider diagnostic")

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        result = await rest.write("POST", "/guilds/103/roles", {}, effect_key="one", scope="role:a")
    assert result.status == "rejected"
    assert result.code == f"http_{status}"
    assert len(writes) == 1


@pytest.mark.parametrize("permissions", ["8", "9", 8, True, "18446744073709551616"])
@pytest.mark.asyncio
async def test_raw_role_route_refuses_administrator_grant_before_http(tmp_path: Path, permissions: object) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(201, json={"id": "104"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        result = await rest.write(
            "POST", "/guilds/103/roles", {"permissions": permissions}, effect_key="one", scope="role:a"
        )
    assert result.code == "unsafe_permissions"
    assert writes == []


@pytest.mark.parametrize("failure", ["timeout", "invalid_json", "invalid_object", "large", "redirect"])
@pytest.mark.asyncio
async def test_uncertain_responses_persist_unknown_without_leaking_provider_data(tmp_path: Path, failure: str) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        if failure == "timeout":
            message = "synthetic-private-url-and-token"
            raise httpx.ReadTimeout(message, request=request)
        if failure == "invalid_json":
            return httpx.Response(200, content=b"not json")
        if failure == "invalid_object":
            return httpx.Response(200, json={"token": "provider-secret"})
        if failure == "large":
            return httpx.Response(200, content=b" " * (2 * 1024 * 1024 + 1))
        return httpx.Response(307, headers={"Location": "https://evil.example/private"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        result = await rest.write("POST", "/guilds/103/roles", {}, effect_key="one", scope="role:a")
    assert result.status == "unknown"
    assert len(writes) == 1
    assert "private" not in result.model_dump_json()
    assert "provider-secret" not in b"".join(path.read_bytes() for path in rest.journal.root.iterdir()).decode()


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example/api/v10/guilds/103/roles",
        "//evil.example/guilds/103/roles",
        "/guilds/999/roles",
        "/guilds/103/roles?redirect=evil",
        "/guilds/103/%72oles",
        "/guilds/103/../999/roles",
        "/channels/999",
        "/webhooks/101/synthetic-token/messages/@original",
    ],
)
@pytest.mark.asyncio
async def test_unbound_or_arbitrary_paths_refuse_before_http(tmp_path: Path, path: str) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "104"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        with pytest.raises(DiscordRestError, match=r"^route_not_allowed$"):
            await rest.write("PATCH", path, {}, effect_key="one", scope="channel:a")
    assert requests == []


@pytest.mark.asyncio
async def test_authenticated_guild_snapshot_binds_only_its_channels(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": "104", "guild_id": "103"}])
        return httpx.Response(200, json={"id": "104"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        await rest.get("/guilds/103/channels")
        result = await rest.write("PATCH", "/channels/104", {"topic": "safe"}, effect_key="one", scope="channel:a")
        with pytest.raises(DiscordRestError, match=r"^route_not_allowed$"):
            await rest.get("/guilds/999/channels")
    assert result.status == "succeeded"
    assert all(request.url.host == "discord.com" for request in requests)
    assert all(request.headers["Authorization"] == "Bot synthetic-bot-secret" for request in requests)


@pytest.mark.asyncio
async def test_message_nonce_and_mentions_and_webhook_secret_absence(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(200, json={"id": "105"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(["104"])
        await rest.send_message("104", "private-message-content", event_id="106")
        await rest.send_message("104", "private-message-content", event_id="106")
        await rest.edit_interaction_original("private-interaction-token", "private-interaction-content", event_id="107")
    assert len(writes) == 2
    message = json.loads(writes[0].content)
    assert len(message["nonce"]) <= 25
    assert message["enforce_nonce"] is True
    assert message["allowed_mentions"] == {"parse": []}
    assert message["flags"] == 4
    assert writes[1].method == "PATCH"
    assert json.loads(writes[1].content)["flags"] == 4
    assert writes[1].url.path == "/api/v10/webhooks/101/private-interaction-token/messages/@original"
    retained = b"".join(path.read_bytes() for path in rest.journal.root.iterdir()).decode()
    for secret in (
        "synthetic-bot-secret",
        "private-message-content",
        "private-interaction-token",
        "private-interaction-content",
        "/webhooks/",
    ):
        assert secret not in retained
    assert rest.journal.root.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in rest.journal.root.iterdir())


def test_journal_rejects_symlink_directory_and_unsafe_permissions(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(DiscordRestError, match=r"^journal_unavailable$"):
        EffectJournal(link)
    real.chmod(0o755)
    with pytest.raises(DiscordRestError, match=r"^journal_unsafe_permissions$"):
        EffectJournal(real)


def test_journal_refuses_record_symlink_and_cross_instance_lock(tmp_path: Path) -> None:
    journal = EffectJournal(tmp_path / "attempts")
    other = EffectJournal(journal.root)
    with journal.lock(), pytest.raises(DiscordRestError, match=r"^journal_busy$"):
        other.inspect()
    (journal.root / ("a" * 64 + ".json")).symlink_to(tmp_path / "outside")
    with pytest.raises(DiscordRestError, match=r"^journal_unavailable$"):
        journal.inspect()


@pytest.mark.asyncio
async def test_lock_reentrancy_does_not_admit_a_different_task(tmp_path: Path) -> None:
    journal = EffectJournal(tmp_path / "attempts")

    async def contender() -> None:
        with pytest.raises(DiscordRestError, match=r"^journal_busy$"):
            journal.inspect()

    with journal.lock():
        assert journal.inspect() == ()
        await asyncio.create_task(contender())


def test_attempting_record_blocks_replay_without_retaining_labels(tmp_path: Path) -> None:
    journal = EffectJournal(tmp_path / "attempts")
    with journal.lock():
        journal.claim(
            effect_key="private-effect-label",
            payload_digest="a" * 64,
            scope="private-scope-label",
            method="POST",
            target="guild_roles",
        )
    restarted = EffectJournal(journal.root)
    with restarted.lock():
        same = restarted.claim(
            effect_key="private-effect-label",
            payload_digest="a" * 64,
            scope="private-scope-label",
            method="POST",
            target="guild_roles",
        )
        changed = restarted.claim(
            effect_key="other-plan",
            payload_digest="a" * 64,
            scope="private-scope-label",
            method="POST",
            target="guild_roles",
        )
    assert isinstance(same, EffectResult)
    assert same.code == "effect_unresolved"
    assert isinstance(changed, EffectResult)
    assert changed.code == "scope_unresolved"
    retained = b"".join(path.read_bytes() for path in journal.root.iterdir()).decode()
    assert "private-effect-label" not in retained
    assert "private-scope-label" not in retained


def test_effect_result_is_strict_immutable_and_content_free() -> None:
    with pytest.raises(ValidationError):
        EffectResult.model_validate({"status": "unknown", "body": "private"})
    with pytest.raises(ValidationError):
        EffectResult.model_validate({"status": "succeeded", "remote_id": 104})
    result = EffectResult(status="unknown", code="network_error")
    with pytest.raises(ValidationError):
        result.code = "replayed"


def test_repeated_nested_inspection_keeps_attempt_and_unknown_visible(tmp_path: Path) -> None:
    journal = EffectJournal(tmp_path / "attempts")
    with journal.lock():
        claimed = journal.claim(
            effect_key="nested-attempt",
            payload_digest="a" * 64,
            scope="nested-resource",
            method="POST",
            target="guild_roles",
        )
        assert not isinstance(claimed, EffectResult)
        for _scan in range(4):
            with journal.lock():
                records = journal.inspect()
                assert records == (claimed,)
                assert records[0].status == "attempting"
        journal.mark_unknown("nested-attempt", code="create_reconciliation_mismatch")
        for _scan in range(4):
            records = journal.inspect()
            assert len(records) == 1
            assert records[0].status == "unknown"
        blocked = journal.claim(
            effect_key="new-plan",
            payload_digest="a" * 64,
            scope="nested-resource",
            method="POST",
            target="guild_roles",
        )
        assert isinstance(blocked, EffectResult)
        assert blocked.code == "scope_unresolved"
