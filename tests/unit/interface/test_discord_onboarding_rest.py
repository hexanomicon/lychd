from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal, EffectResult


def make_rest(tmp_path: Path, client: httpx.AsyncClient) -> DiscordRest:
    return DiscordRest(
        token="synthetic-bot-secret",  # noqa: S106 - synthetic fixture credential
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        journal=EffectJournal(tmp_path / "attempts"),
        client=client,
    )


def transport(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)


def identity(request: httpx.Request) -> httpx.Response | None:
    if request.url.path == "/api/v10/users/@me":
        return httpx.Response(200, json={"id": "102", "bot": True})
    if request.url.path == "/api/v10/oauth2/applications/@me":
        return httpx.Response(200, json={"id": "101"})
    return None


def message(*, author_id: str = "102", channel_id: str = "104") -> dict[str, Any]:
    return {
        "id": "110",
        "channel_id": channel_id,
        "author": {"id": author_id, "bot": True},
        "content": "synthetic introduction",
    }


def member_roles() -> list[dict[str, Any]]:
    return [
        {"id": "106", "permissions": "0", "managed": False},
        {"id": "107", "permissions": "0", "managed": False},
    ]


def bind_introductions(rest: DiscordRest) -> None:
    rest.bind_channels(("104",))
    rest.bind_introduction_channel("104")


@pytest.mark.asyncio
async def test_member_role_put_204_is_success_and_duplicate_is_not_sent(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []
    role_reads: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET" and request.url.path == "/api/v10/guilds/103/roles":
            role_reads.append(request)
            return httpx.Response(200, json=member_roles())
        writes.append(request)
        assert role_reads
        assert rest.journal.inspect()[0].status == "attempting"
        return httpx.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_member_roles(("106", "107"))
        first = await rest.ensure_member_role("108", "106", event_id="109")
        again = await rest.ensure_member_role("108", "106", event_id="109")
    assert first == again == EffectResult(status="succeeded", remote_id="108")
    assert role_reads
    assert [(request.method, request.url.path) for request in writes] == [
        ("PUT", "/api/v10/guilds/103/members/108/roles/106")
    ]
    assert writes[0].headers["Authorization"] == "Bot synthetic-bot-secret"
    assert rest.journal.inspect()[0].status == "succeeded"


@pytest.mark.asyncio
async def test_member_role_requires_identity_verification_before_http(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        rest.bind_member_roles(("106", "107"))
        result = await rest.ensure_member_role("108", "106", event_id="109")
    assert result.status == "rejected"
    assert requests == []
    assert rest.journal.inspect() == ()


@pytest.mark.asyncio
async def test_unbound_member_role_refuses_without_an_attempt(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET" and request.url.path == "/api/v10/guilds/103/roles":
            return httpx.Response(200, json=member_roles())
        writes.append(request)
        return httpx.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_member_roles(("106", "107"))
        result = await rest.ensure_member_role("108", "999", event_id="109")
    assert result.status == "rejected"
    assert writes == []
    assert rest.journal.inspect() == ()


@pytest.mark.parametrize(("permissions", "managed"), [("8", False), ("1024", False), ("0", True)])
@pytest.mark.asyncio
async def test_role_authority_is_rechecked_after_binding_before_a_new_grant(
    tmp_path: Path, permissions: str, *, managed: bool
) -> None:
    requests: list[httpx.Request] = []
    current_roles = member_roles()

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        if request.method == "GET" and request.url.path == "/api/v10/guilds/103/roles":
            return httpx.Response(200, json=current_roles)
        return httpx.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_member_roles(("106", "107"))
        current_roles[0]["permissions"] = permissions
        current_roles[0]["managed"] = managed
        result = await rest.ensure_member_role("108", "106", event_id="109")
    assert result.status == "rejected"
    assert [(request.method, request.url.path) for request in requests] == [("GET", "/api/v10/guilds/103/roles")]


@pytest.mark.parametrize("failure", ["server_error", "timeout"])
@pytest.mark.asyncio
async def test_unknown_role_grant_blocks_restart_and_new_event(tmp_path: Path, failure: str) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET" and request.url.path == "/api/v10/guilds/103/roles":
            return httpx.Response(200, json=member_roles())
        writes.append(request)
        if failure == "timeout":
            diagnostic = "synthetic response uncertainty"
            raise httpx.ReadTimeout(diagnostic, request=request)
        return httpx.Response(500)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_member_roles(("106", "107"))
        first = await rest.ensure_member_role("108", "106", event_id="109")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        restarted.bind_member_roles(("106", "107"))
        same_event = await restarted.ensure_member_role("108", "106", event_id="109")
        new_event = await restarted.ensure_member_role("108", "106", event_id="111")
    assert first.status == "unknown"
    assert same_event.status == new_event.status == "rejected"
    assert len(writes) == 1
    assert restarted.journal.inspect()[0].status == "unknown"


@pytest.mark.asyncio
async def test_introduction_binding_requires_a_previously_bound_channel(tmp_path: Path) -> None:
    async with transport(lambda _request: httpx.Response(200)) as client:
        rest = make_rest(tmp_path, client)
        with pytest.raises(DiscordRestError):
            rest.bind_introduction_channel("104")
        rest.bind_channels(("104",))
        rest.bind_introduction_channel("104")


@pytest.mark.asyncio
async def test_introduction_create_then_fresh_ownership_check_and_exact_message_patch(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        first = await rest.publish_introduction("104", "first profile", subject_id="108", event_id="109")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        bind_introductions(restarted)
        second = await restarted.publish_introduction("104", "updated profile", subject_id="108", event_id="111")
    assert first.status == second.status == "succeeded"
    assert first.remote_id == second.remote_id == "110"
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/v10/channels/104/messages"),
        ("GET", "/api/v10/channels/104/messages/110"),
        ("PATCH", "/api/v10/channels/104/messages/110"),
    ]
    create, _, update = requests
    create_body = json.loads(create.content)
    assert create_body["content"] == "first profile"
    assert create_body["flags"] == 4
    assert create_body["allowed_mentions"] == {"parse": []}
    assert create_body["enforce_nonce"] is True
    assert isinstance(create_body["nonce"], str)
    assert 1 <= len(create_body["nonce"]) <= 25
    update_body = json.loads(update.content)
    assert update_body["content"] == "updated profile"
    assert update_body["flags"] == 4
    assert update_body["allowed_mentions"] == {"parse": []}
    assert len([record for record in restarted.journal.inspect() if record.method == "POST"]) == 1
    retained = b"".join(path.read_bytes() for path in restarted.journal.root.iterdir()).decode()
    assert "first profile" not in retained
    assert "updated profile" not in retained
    assert "synthetic-bot-secret" not in retained


@pytest.mark.asyncio
async def test_introduction_channel_binding_does_not_authorize_other_channels(tmp_path: Path) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(200, json=message(channel_id="105"))

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(("104", "105"))
        rest.bind_introduction_channel("104")
        result = await rest.publish_introduction("105", "profile", subject_id="108", event_id="109")
    assert result.status == "rejected"
    assert writes == []
    assert rest.journal.inspect() == ()


@pytest.mark.parametrize("original", ["missing", "foreign_author", "foreign_channel"])
@pytest.mark.asyncio
async def test_missing_or_foreign_original_never_causes_patch_or_replacement_post(
    tmp_path: Path, original: str
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        if request.method == "GET":
            if original == "missing":
                return httpx.Response(404)
            return httpx.Response(
                200,
                json=message(
                    author_id="999" if original == "foreign_author" else "102",
                    channel_id="999" if original == "foreign_channel" else "104",
                ),
            )
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        first = await rest.publish_introduction("104", "profile", subject_id="108", event_id="109")
        refused = await rest.publish_introduction("104", "new profile", subject_id="108", event_id="111")
    assert first.status == "succeeded"
    assert refused.status in {"rejected", "unknown"}
    assert [request.method for request in requests] == ["POST", "GET"]


@pytest.mark.parametrize("failure", ["server_error", "timeout", "malformed_success"])
@pytest.mark.asyncio
async def test_unknown_introduction_create_fences_new_event_and_changed_body(tmp_path: Path, failure: str) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        if failure == "timeout":
            diagnostic = "synthetic response uncertainty"
            raise httpx.ReadTimeout(diagnostic, request=request)
        if failure == "malformed_success":
            return httpx.Response(200, json={})
        return httpx.Response(500)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        first = await rest.publish_introduction("104", "profile", subject_id="108", event_id="109")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        bind_introductions(restarted)
        same = await restarted.publish_introduction("104", "profile", subject_id="108", event_id="109")
        changed = await restarted.publish_introduction("104", "changed profile", subject_id="108", event_id="111")
    assert first.status == "unknown"
    assert same.status == changed.status == "rejected"
    assert [request.method for request in writes] == ["POST"]
    assert any(record.status == "unknown" for record in restarted.journal.inspect())


@pytest.mark.asyncio
async def test_unknown_introduction_update_fences_later_events_after_restart(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        if request.method == "PATCH":
            return httpx.Response(500)
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        first = await rest.publish_introduction("104", "profile", subject_id="108", event_id="109")
        update = await rest.publish_introduction("104", "changed profile", subject_id="108", event_id="111")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        bind_introductions(restarted)
        refused = await restarted.publish_introduction("104", "third profile", subject_id="108", event_id="112")
    assert first.status == "succeeded"
    assert update.status == "unknown"
    assert refused.status == "rejected"
    assert [request.method for request in requests if request.method != "GET"] == ["POST", "PATCH"]
    assert any(record.status == "unknown" for record in restarted.journal.inspect())


@pytest.mark.asyncio
async def test_get_message_returns_mapping_only_for_bound_channels(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        result = await rest.get_message("104", "110")
        with pytest.raises(DiscordRestError):
            await rest.get_message("999", "110")
    assert result == message()
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/api/v10/channels/104/messages/110")
    ]


@pytest.mark.parametrize(
    "path",
    [
        "/guilds/103/members/108",
        "/guilds/103/members/108/roles/106",
        "/guilds/103/roles/106",
        "/channels/104/messages/110",
    ],
)
@pytest.mark.asyncio
async def test_generic_write_does_not_inherit_onboarding_privilege(tmp_path: Path, path: str) -> None:
    writes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        rest.bind_member_roles(("106", "107"))
        with pytest.raises(DiscordRestError):
            await rest.write("PATCH", path, {"roles": ["106"]}, effect_key="arbitrary", scope="arbitrary")
    assert writes == []
    assert rest.journal.inspect() == ()


@pytest.mark.parametrize("rejection_status", [403, 429])
@pytest.mark.asyncio
async def test_definite_introduction_rejection_can_recover_on_a_new_confirmation(
    tmp_path: Path, rejection_status: int
) -> None:
    requests: list[httpx.Request] = []
    post_statuses: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        requests.append(request)
        if request.method == "POST":
            status = rejection_status if not post_statuses else 200
            post_statuses.append(status)
            return httpx.Response(status, json=message())
        return httpx.Response(200, json=message())

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        bind_introductions(rest)
        rejected = await rest.publish_introduction("104", "profile", subject_id="108", event_id="109")
        recovered = await rest.publish_introduction("104", "profile", subject_id="108", event_id="111")
        updated = await rest.publish_introduction("104", "updated profile", subject_id="108", event_id="112")
    assert rejected.status == "rejected"
    assert recovered.status == updated.status == "succeeded"
    assert recovered.remote_id == updated.remote_id == "110"
    assert post_statuses == [rejection_status, 200]
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/v10/channels/104/messages"),
        ("POST", "/api/v10/channels/104/messages"),
        ("GET", "/api/v10/channels/104/messages/110"),
        ("PATCH", "/api/v10/channels/104/messages/110"),
    ]


@pytest.mark.parametrize("blocked_method", ["GET", "PUT"])
@pytest.mark.asyncio
async def test_concurrent_role_grants_and_introduction_wait_for_the_same_adapter(
    tmp_path: Path, blocked_method: str
) -> None:
    first_suspended = asyncio.Event()
    release_first = asyncio.Event()
    second_started = asyncio.Event()
    introduction_started = asyncio.Event()
    writes: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == blocked_method and not first_suspended.is_set():
            first_suspended.set()
            await release_first.wait()
        if request.method == "GET" and request.url.path == "/api/v10/guilds/103/roles":
            return httpx.Response(200, json=member_roles())
        writes.append(request)
        if request.method == "PUT":
            return httpx.Response(204)
        return httpx.Response(200, json=message())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_member_roles(("106", "107"))
        bind_introductions(rest)

        async def grant_second_role() -> EffectResult:
            second_started.set()
            return await rest.ensure_member_role("113", "107", event_id="114")

        async def publish_introduction() -> EffectResult:
            introduction_started.set()
            return await rest.publish_introduction("104", "profile", subject_id="108", event_id="115")

        first = asyncio.create_task(rest.ensure_member_role("108", "106", event_id="109"))
        await asyncio.wait_for(first_suspended.wait(), timeout=5.0)
        second = asyncio.create_task(grant_second_role())
        introduction = asyncio.create_task(publish_introduction())
        await asyncio.wait_for(asyncio.gather(second_started.wait(), introduction_started.wait()), timeout=5.0)
        release_first.set()
        results = await asyncio.wait_for(asyncio.gather(first, second, introduction), timeout=5.0)
    assert [result.status for result in results] == ["succeeded", "succeeded", "succeeded"]
    assert [result.remote_id for result in results] == ["108", "113", "110"]
    assert sorted((request.method, request.url.path) for request in writes) == [
        ("POST", "/api/v10/channels/104/messages"),
        ("PUT", "/api/v10/guilds/103/members/108/roles/106"),
        ("PUT", "/api/v10/guilds/103/members/113/roles/107"),
    ]
    assert all(record.status == "succeeded" for record in rest.journal.inspect())
