from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from lychd.interface.discord.publications import Publication, PublicationQueue, queue_publication
from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal, EffectResult

CHANNEL = "444444444444444444"


def queued(tmp_path: Path) -> tuple[PublicationQueue, str]:
    body = tmp_path / "operator-body"
    body.write_text("Project milestone: contextual chat is available.")
    body.chmod(0o600)
    root = tmp_path / "queue"
    identifier = queue_publication(root, body_file=body, channel_id=CHANNEL, publication_id=str(uuid4()))
    return PublicationQueue(root, allowed_channels=frozenset({CHANNEL})), identifier


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["succeeded", "rejected", "unknown"])
async def test_publication_receipt_fences_repeat_and_hides_body(
    tmp_path: Path, status: Literal["succeeded", "rejected", "unknown"]
) -> None:
    queue, identifier = queued(tmp_path)
    rest = Mock(application_id="111111111111111111", journal=EffectJournal(tmp_path / "effects"))
    rest.write = AsyncMock(return_value=EffectResult(status=status))
    assert await queue.process_once(rest) == 1
    assert await queue.process_once(rest) == 0
    rest.write.assert_awaited_once()
    receipt = json.loads((queue.root / f"{identifier}.receipt").read_text())
    assert receipt["status"] == status
    assert "milestone" not in json.dumps(receipt)
    assert (queue.root / f"{identifier}.body").exists() == (status == "unknown")


@pytest.mark.asyncio
async def test_expiry_and_destination_are_checked_before_http(tmp_path: Path) -> None:
    queue, identifier = queued(tmp_path)
    rest = Mock(application_id="101", journal=EffectJournal(tmp_path / "effects"), write=AsyncMock())
    assert await queue.process_once(rest, now=datetime.now(UTC) + timedelta(hours=2)) == 1
    rest.write.assert_not_awaited()
    assert json.loads((queue.root / f"{identifier}.receipt").read_text())["code"] == "publication_expired"


@pytest.mark.asyncio
async def test_wrong_destination_is_rejected_without_http(tmp_path: Path) -> None:
    original, identifier = queued(tmp_path)
    queue = PublicationQueue(original.root, allowed_channels=frozenset({"555555555555555555"}))
    rest = Mock(application_id="101", journal=EffectJournal(tmp_path / "effects"), write=AsyncMock())
    assert await queue.process_once(rest) == 1
    rest.write.assert_not_awaited()
    assert json.loads((queue.root / f"{identifier}.receipt").read_text())["code"] == "publication_scope"


@pytest.mark.asyncio
async def test_reply_reference_is_channel_bound_and_never_pings(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/users/@me"):
            return httpx.Response(200, json={"id": "102", "bot": True})
        if request.url.path.endswith("/oauth2/applications/@me"):
            return httpx.Response(200, json={"id": "101"})
        requests.append(request)
        return httpx.Response(200, json={"id": "105"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rest = DiscordRest(
            token="synthetic",  # noqa: S106 - synthetic fixture credential
            application_id="101",
            bot_user_id="102",
            guild_id="103",
            journal=EffectJournal(tmp_path / "effects"),
            client=client,
        )
        await rest.verify_identity()
        rest.bind_channels((CHANNEL,))
        await rest.send_message(CHANNEL, "Reply", event_id="106", reply_to="106")
        with pytest.raises(DiscordRestError, match="invalid_identity"):
            await rest.send_message(CHANNEL, "Reply", event_id="107", reply_to="bad")
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["message_reference"] == {
        "message_id": "106",
        "channel_id": CHANNEL,
        "fail_if_not_exists": False,
    }
    assert payload["allowed_mentions"] == {"parse": [], "replied_user": False}


def test_queue_refuses_symlink_and_open_permissions(tmp_path: Path) -> None:
    body = tmp_path / "body"
    body.write_text("Owner publication")
    body.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(body)
    with pytest.raises(ValueError, match="publication_external_path"):
        queue_publication(tmp_path / "queue", body_file=link, channel_id=CHANNEL, publication_id=str(uuid4()))
    body.chmod(0o644)
    with pytest.raises(ValueError, match="publication_permissions"):
        queue_publication(tmp_path / "queue", body_file=body, channel_id=CHANNEL, publication_id=str(uuid4()))


@pytest.mark.parametrize("ttl", [0, 3601])
def test_ttl_is_at_most_one_hour(tmp_path: Path, ttl: int) -> None:
    with pytest.raises(ValueError, match="publication_identity"):
        queue_publication(
            tmp_path / "queue",
            body_file=tmp_path / "body",
            channel_id=CHANNEL,
            publication_id=str(uuid4()),
            ttl_seconds=ttl,
        )


def test_fifo_body_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    body = tmp_path / "fifo"
    os.mkfifo(body, 0o600)
    with pytest.raises(ValueError, match="publication_permissions"):
        queue_publication(tmp_path / "queue", body_file=body, channel_id=CHANNEL, publication_id=str(uuid4()))


@pytest.mark.asyncio
async def test_consumer_rejects_fifo_body_without_http(tmp_path: Path) -> None:
    queue, identifier = queued(tmp_path)
    body = queue.root / f"{identifier}.body"
    body.unlink()
    os.mkfifo(body, 0o600)
    rest = Mock(write=AsyncMock())
    with pytest.raises(ValueError, match="publication_permissions"):
        await queue.process_once(rest)
    rest.write.assert_not_awaited()


@pytest.mark.parametrize("target", ["body", "queue"])
def test_producer_rejects_checkout_containing_either_private_path(tmp_path: Path, target: str) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").write_text("gitdir: elsewhere")
    body = (checkout if target == "body" else tmp_path) / "body"
    body.write_text("Project milestone")
    body.chmod(0o600)
    root = (checkout if target == "queue" else tmp_path) / "queue"
    with pytest.raises(ValueError, match="publication_external_path"):
        queue_publication(root, body_file=body, channel_id=CHANNEL, publication_id=str(uuid4()))


def test_producer_rejects_symlink_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    body = real / "body"
    body.write_text("Milestone")
    body.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="publication_external_path"):
        queue_publication(tmp_path / "queue", body_file=link / "body", channel_id=CHANNEL, publication_id=str(uuid4()))


@pytest.mark.asyncio
async def test_each_effect_refreshes_expiry_clock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue, _ = queued(tmp_path)
    second = tmp_path / "second"
    second.write_text("Another update")
    second.chmod(0o600)
    queue_publication(queue.root, body_file=second, channel_id=CHANNEL, publication_id=str(uuid4()))
    baseline = datetime.now(UTC)
    times = iter((baseline, baseline + timedelta(hours=2)))

    class Clock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return next(times)

    monkeypatch.setattr("lychd.interface.discord.publications.datetime", Clock)
    rest = Mock(
        application_id="101",
        journal=EffectJournal(tmp_path / "effects"),
        write=AsyncMock(return_value=EffectResult(status="succeeded")),
    )
    assert await queue.process_once(rest) == 2
    rest.write.assert_awaited_once()


@pytest.mark.parametrize("status", ["unknown", "succeeded"])
@pytest.mark.parametrize("boundary", ["expired", "destination_removed"])
@pytest.mark.asyncio
async def test_crash_after_transport_settlement_preserves_prior_result_before_new_eligibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: Literal["unknown", "succeeded"],
    boundary: str,
) -> None:
    queue, identifier = queued(tmp_path)
    posts = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        if request.url.path.endswith("/users/@me"):
            return httpx.Response(200, json={"id": "102", "bot": True})
        if request.url.path.endswith("/oauth2/applications/@me"):
            return httpx.Response(200, json={"id": "101"})
        posts += 1
        if status == "unknown":
            message = "Interrupted after transmission"
            raise httpx.ReadTimeout(message, request=request)
        return httpx.Response(200, json={"id": "106"})

    def crash(_fd: int, _publication: Publication, _result: EffectResult) -> None:
        message = "Crash before queue receipt"
        raise OSError(message)

    journal = EffectJournal(tmp_path / "effects")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rest = DiscordRest(
            token="synthetic",  # noqa: S106 - synthetic fixture credential
            application_id="101",
            bot_user_id="102",
            guild_id="103",
            journal=journal,
            client=client,
        )
        await rest.verify_identity()
        rest.bind_channels((CHANNEL,))
        with monkeypatch.context() as interrupted:
            interrupted.setattr(PublicationQueue, "_receipt", staticmethod(crash))
            with pytest.raises(OSError, match="Crash before queue receipt"):
                await queue.process_once(rest)
        assert journal.inspect()[0].status == status
        if boundary == "destination_removed":
            queue = PublicationQueue(queue.root, allowed_channels=frozenset({"555555555555555555"}))
        review_time = datetime.now(UTC) + (timedelta(hours=2) if boundary == "expired" else timedelta(0))
        assert await queue.process_once(rest, now=review_time) == 1
        assert await queue.process_once(rest) == 0
    assert posts == 1
    receipt = json.loads((queue.root / f"{identifier}.receipt").read_text())
    assert receipt["status"] == status
    assert receipt["code"] not in {"publication_scope", "publication_expired", "publication_binding"}
    assert (queue.root / f"{identifier}.body").exists() == (status == "unknown")
    assert journal.inspect()[0].status == status


@pytest.mark.asyncio
async def test_partial_manifest_write_never_publishes_a_poisoned_queue_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = tmp_path / "body"
    await asyncio.to_thread(body.write_text, "Owner update")
    await asyncio.to_thread(body.chmod, 0o600)
    root = tmp_path / "queue"
    failed = str(uuid4())
    original_write = os.write

    def interrupted_write(fd: int, raw: bytes) -> int:
        if raw.startswith(b'{"publication_id"'):
            original_write(fd, raw[:5])
            message = "Interrupted manifest write"
            raise OSError(message)
        return original_write(fd, raw)

    with monkeypatch.context() as interrupted:
        interrupted.setattr("lychd.interface.discord.publications.os.write", interrupted_write)
        with pytest.raises(OSError, match="Interrupted manifest write"):
            queue_publication(root, body_file=body, channel_id=CHANNEL, publication_id=failed)
    assert not await asyncio.to_thread((root / f"{failed}.json").exists)
    assert not await asyncio.to_thread(lambda: tuple(root.glob(".pending-*")))
    valid = queue_publication(root, body_file=body, channel_id=CHANNEL, publication_id=str(uuid4()))
    rest = Mock(
        application_id="101",
        journal=EffectJournal(tmp_path / "effects"),
        write=AsyncMock(return_value=EffectResult(status="succeeded")),
    )
    assert await PublicationQueue(root, allowed_channels=frozenset({CHANNEL})).process_once(rest) == 1
    rest.write.assert_awaited_once()
    assert await asyncio.to_thread((root / f"{valid}.receipt").is_file)


@pytest.mark.asyncio
async def test_pending_alias_from_crash_after_link_is_retired_before_final_record_validation(tmp_path: Path) -> None:
    queue, identifier = queued(tmp_path)
    final = queue.root / f"{identifier}.json"
    pending = queue.root / f".pending-{uuid4().hex}"
    await asyncio.to_thread(os.link, final, pending, follow_symlinks=False)
    rest = Mock(
        application_id="101",
        journal=EffectJournal(tmp_path / "effects"),
        write=AsyncMock(return_value=EffectResult(status="succeeded")),
    )
    assert await queue.process_once(rest) == 1
    rest.write.assert_awaited_once()
    assert not await asyncio.to_thread(pending.exists)
    assert await asyncio.to_thread((queue.root / f"{identifier}.receipt").is_file)
