"""Finite Discord expressions preserve incoming-event and effect-slot binding."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast
from urllib.parse import quote

import httpx2
import pytest

from lychd.compositions.reach.expressions import REACTIONS, Reaction
from lychd.interface.discord.rest import DiscordRestError, EffectResult
from tests.unit.interface.test_discord_rest import identity, make_rest, transport

GIF = "https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif"
OTHER_GIF = "https://media2.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif"


@pytest.mark.asyncio
@pytest.mark.parametrize("emoji", REACTIONS)
@pytest.mark.parametrize("channel_kind", ["guild", "direct"])
async def test_reaction_encodes_only_fixed_emoji_and_accepts_empty_204(
    tmp_path: Path, emoji: Reaction, channel_kind: str
) -> None:
    writes: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET":
            assert request.url.path == "/api/v10/channels/104"
            return httpx2.Response(200, json={"id": "104", "type": 1, "recipients": [{"id": "105"}]})
        writes.append(request)
        return httpx2.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        if channel_kind == "guild":
            rest.bind_channels(("104",))
        else:
            await rest.bind_direct_channel("104", "105")
        result = await rest.add_reaction("104", "106", emoji, event_id="106")
        assert rest.journal.inspect()[0].target == "message_reaction"
    assert result == EffectResult(status="succeeded", remote_id="106")
    assert len(writes) == 1
    assert writes[0].method == "PUT"
    expected_path = f"/api/v10/channels/104/messages/106/reactions/{quote(emoji, safe='')}/@me"
    assert writes[0].url.raw_path == expected_path.encode()
    assert json.loads(writes[0].content) == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel_id", "message_id", "emoji", "event_id", "phase", "code"),
    [
        ("104", "106", "🔥", "106", "reply", "invalid_reaction"),
        ("104", "106", "%F0%9F%91%80", "106", "reply", "invalid_reaction"),
        ("104", "106", "custom:107", "106", "reply", "invalid_reaction"),
        ("104", "107", "👀", "106", "reply", "reaction_message_binding"),
        ("999", "106", "👀", "106", "reply", "reaction_channel_binding"),
        ("104", "106", "👀", "106", "other", "invalid_reaction_phase"),
        ("bad", "106", "👀", "106", "reply", "invalid_identity"),
        ("104", "0", "👀", "106", "reply", "invalid_identity"),
        ("104", "106", "👀", "bad", "reply", "invalid_identity"),
    ],
)
async def test_invalid_reaction_never_sends_or_claims(
    tmp_path: Path,
    channel_id: str,
    message_id: str,
    emoji: str,
    event_id: str,
    phase: str,
    code: str,
) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        rest.bind_channels(("104",))
        result = await rest.add_reaction(
            channel_id,
            message_id,
            cast("Reaction", emoji),
            event_id=event_id,
            phase=cast("Literal['seen', 'reply']", phase),
        )
    assert result == EffectResult(status="rejected", code=code)
    assert requests == []
    assert rest.journal.inspect() == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "server_error", "timeout"])
async def test_reaction_restart_reuses_or_fences_slot_and_changed_emoji(tmp_path: Path, outcome: str) -> None:
    writes: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        if outcome == "timeout":
            message = "synthetic-private-provider-diagnostic"
            raise httpx2.ReadTimeout(message, request=request)
        return httpx2.Response(204 if outcome == "success" else 500)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(("104",))
        first = await rest.add_reaction("104", "106", "👍", event_id="106")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        restarted.bind_channels(("104", "107"))
        repeated = await restarted.add_reaction("104", "106", "👍", event_id="106")
        changed_emoji = await restarted.add_reaction("104", "106", "✨", event_id="106")
        changed_channel = await restarted.add_reaction("107", "106", "👍", event_id="106")
    if outcome == "success":
        assert first == repeated == EffectResult(status="succeeded", remote_id="106")
    else:
        assert first.status == "unknown"
        assert repeated == EffectResult(status="rejected", code="effect_unresolved")
    assert changed_emoji == changed_channel == EffectResult(status="rejected", code="effect_payload_changed")
    assert len(writes) == 1
    record = restarted.journal.inspect()[0]
    assert record.effect_key_digest == sha256(b"reaction:101:106:reply").hexdigest()
    assert record.scope_digest == sha256(b"reaction:101:104:106:reply").hexdigest()


@pytest.mark.asyncio
async def test_seen_and_reply_are_independent_reaction_slots_and_generic_route_stays_closed(tmp_path: Path) -> None:
    writes: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx2.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(("104",))
        seen = await rest.add_reaction("104", "106", "👀", event_id="106", phase="seen")
        reply = await rest.add_reaction("104", "106", "👍", event_id="106", phase="reply")
        path = f"/channels/104/messages/106/reactions/{quote('👀', safe='')}/@me"
        with pytest.raises(DiscordRestError, match=r"^route_not_allowed$"):
            await rest.write("POST", path, {}, effect_key="generic", scope="generic")
    assert seen.status == reply.status == "succeeded"
    assert len(writes) == 2


@pytest.mark.asyncio
async def test_expression_requires_verified_identity_before_journal_or_http(tmp_path: Path) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(204)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        rest.bind_channels(("104",))
        reaction = await rest.add_reaction("104", "106", "👍", event_id="106")
        gif = await rest.send_gif("104", GIF, event_id="106", reply_to="106")
    assert reaction == gif == EffectResult(status="rejected", code="identity_not_verified")
    assert requests == []
    assert rest.journal.inspect() == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_kind", ["guild", "direct"])
async def test_gif_sends_exact_url_silently_without_mentions_with_independent_nonce(
    tmp_path: Path, channel_kind: str
) -> None:
    writes: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET":
            return httpx2.Response(200, json={"id": "104", "type": 1, "recipients": [{"id": "105"}]})
        writes.append(request)
        return httpx2.Response(201, json={"id": "108"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        if channel_kind == "guild":
            rest.bind_channels(("104",))
        else:
            await rest.bind_direct_channel("104", "105")
        text_result = await rest.send_message("104", "A text reply.", event_id="106", reply_to="106")
        gif_result = await rest.send_gif("104", GIF, event_id="106", reply_to="106")
        duplicate = await rest.send_gif("104", GIF, event_id="106", reply_to="106")
        changed = await rest.send_gif("104", OTHER_GIF, event_id="106", reply_to="106")
        records = rest.journal.inspect()
    assert text_result.status == "succeeded"
    assert gif_result == duplicate == EffectResult(status="succeeded", remote_id="108")
    assert changed == EffectResult(status="rejected", code="effect_payload_changed")
    assert len(writes) == 2
    text_body, gif_body = (json.loads(request.content) for request in writes)
    assert writes[1].method == "POST"
    assert writes[1].url.path == "/api/v10/channels/104/messages"
    assert gif_body == {
        "content": GIF,
        "flags": 4096,
        "allowed_mentions": {"parse": [], "replied_user": False},
        "nonce": sha256(b"gif:101:104:106").hexdigest()[:25],
        "enforce_nonce": True,
        "message_reference": {"message_id": "106", "channel_id": "104", "fail_if_not_exists": False},
    }
    assert text_body["flags"] == 4
    assert text_body["nonce"] != gif_body["nonce"]
    assert {record.effect_key_digest for record in records} == {
        sha256(b"message:101:106").hexdigest(),
        sha256(b"gif:101:106").hexdigest(),
    }
    retained = b"".join(path.read_bytes() for path in rest.journal.root.iterdir()).decode()
    assert GIF not in retained
    assert "A text reply." not in retained


@pytest.mark.asyncio
async def test_unknown_gif_remains_fenced_after_restart_and_catalog_choice_change(tmp_path: Path) -> None:
    writes: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        response = identity(request)
        if response is not None:
            return response
        writes.append(request)
        return httpx2.Response(500)

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(("104",))
        first = await rest.send_gif("104", GIF, event_id="106", reply_to="106")
        restarted = make_rest(tmp_path, client)
        await restarted.verify_identity()
        restarted.bind_channels(("104",))
        repeated = await restarted.send_gif("104", GIF, event_id="106", reply_to="106")
        changed = await restarted.send_gif("104", OTHER_GIF, event_id="106", reply_to="106")
    assert first == EffectResult(status="unknown", code="http_500")
    assert repeated == EffectResult(status="rejected", code="effect_unresolved")
    assert changed == EffectResult(status="rejected", code="effect_payload_changed")
    assert len(writes) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel_id", "url", "event_id", "reply_to", "code"),
    [
        ("104", "https://evil.example/reaction.gif", "106", "106", "invalid_gif_url"),
        ("104", "http://media.giphy.com/media/abc/giphy.gif", "106", "106", "invalid_gif_url"),
        ("104", "https://media.giphy.com/media/abc/giphy.gif?x=1", "106", "106", "invalid_gif_url"),
        ("104", "https://media.giphy.com/media/abc/giphy.gif#x", "106", "106", "invalid_gif_url"),
        ("104", "https://user@media.giphy.com/media/abc/giphy.gif", "106", "106", "invalid_gif_url"),
        ("104", "https://media.giphy.com/media/abc/giphy.mp4", "106", "106", "invalid_gif_url"),
        ("104", "https://media.giphy.com.evil.example/media/abc/giphy.gif", "106", "106", "invalid_gif_url"),
        ("104", GIF, "106", "107", "gif_reply_binding"),
        ("999", GIF, "106", "106", "route_not_allowed"),
        ("bad", GIF, "106", "106", "invalid_identity"),
        ("104", GIF, "bad", "106", "invalid_identity"),
        ("104", GIF, "106", "bad", "invalid_identity"),
    ],
)
async def test_invalid_gif_never_sends_or_claims(
    tmp_path: Path, channel_id: str, url: str, event_id: str, reply_to: str, code: str
) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(201, json={"id": "108"})

    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        rest.bind_channels(("104",))
        result = await rest.send_gif(channel_id, url, event_id=event_id, reply_to=reply_to)
    assert result == EffectResult(status="rejected", code=code)
    assert requests == []
    assert rest.journal.inspect() == ()
