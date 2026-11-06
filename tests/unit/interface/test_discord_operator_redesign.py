"""Invocation lifetime, narrow provider ports and indexed legacy-effect receipts."""

from __future__ import annotations

import asyncio
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import httpx2
import pytest
from scripts import reach_operator, reach_operator_transport

from lychd.compositions.reach.conversation_session import ContextTurnOutcome
from lychd.compositions.reach.expressions import ConversationExpressions
from lychd.compositions.reach.operator_limits import TurnDeadline
from lychd.compositions.reach.operator_session import OperatorSession
from lychd.interface.discord.delivery import DiscordTurnDelivery, context_text
from lychd.interface.discord.followups import FollowupLedger
from lychd.interface.discord.history import HistoryPager, anchor_allowed, history_entry
from lychd.interface.discord.lifecycle import EdgeTasks
from lychd.interface.discord.ports import GuildInspection, OnboardingEffects, PublicationEffects, ReplyEffects
from lychd.interface.discord.rest import DiscordRestError, EffectJournal, EffectRecord, EffectResult
from tests.unit.cli.test_reach_operator import Process
from tests.unit.compositions.test_reach_operator_redesign import native_result
from tests.unit.interface.test_discord_followups import message, reply_rest, service
from tests.unit.interface.test_discord_history import (
    anchor,
    channel,
    event,
)
from tests.unit.interface.test_discord_history import (
    message as history_message,
)
from tests.unit.interface.test_discord_history import (
    policy as history_policy,
)
from tests.unit.interface.test_discord_rest import identity, make_rest, transport
from tests.unit.interface.test_nadir_dialogue import policy


def record(journal: EffectJournal, key: str, *, scope: str | None = None) -> EffectRecord:
    claim = journal.claim(
        effect_key=key, payload_digest="a" * 64, scope=scope or key, method="POST", target="channel_messages"
    )
    assert isinstance(claim, EffectRecord)
    return claim


def test_generation_journal_parses_legacy_receipts_once_then_uses_key_and_scope_indexes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = EffectJournal(tmp_path / "effects")
    with journal.session(), journal.lock():
        for index in range(40):
            journal.settle(record(journal, f"old:{index}"), EffectResult(status="succeeded", remote_id="101"))
    parses = 0
    validate = EffectRecord.model_validate_json

    def parse(_cls: type[EffectRecord], raw: Any, **kwargs: Any) -> EffectRecord:
        nonlocal parses
        parses += 1
        return validate(raw, **kwargs)

    monkeypatch.setattr(EffectRecord, "model_validate_json", classmethod(parse))
    with journal.session():
        assert parses == 40
        with journal.lock():
            for index in range(25):
                journal.settle(record(journal, f"new:{index}"), EffectResult(status="succeeded", remote_id="102"))
                assert journal.lookup(f"new:{index}") is not None
                assert not journal.scope_unresolved(f"new:{index}")
            journal.settle(record(journal, "uncertain", scope="shared"), EffectResult(status="unknown"))
            assert journal.scope_unresolved("shared")
            assert len(journal.scope_records("shared")) == 1
            rejected = journal.claim(
                effect_key="another", payload_digest="a" * 64, scope="shared", method="POST", target="channel_messages"
            )
            assert isinstance(rejected, EffectResult)
            assert rejected.code == "scope_unresolved"
        assert parses == 40
        assert len(journal.inspect()) == 66
    with journal.session():
        assert parses == 106
        assert journal.scope_unresolved("shared")


@pytest.mark.asyncio
async def test_journal_generation_excludes_other_instances_but_transactions_are_task_owned(tmp_path: Path) -> None:
    first, second = EffectJournal(tmp_path / "effects"), EffectJournal(tmp_path / "effects")
    with first.session():
        with pytest.raises(DiscordRestError, match="journal_busy"), second.session():
            pytest.fail("A second generation acquired the same journal")
        with first.lock():
            with first.lock():
                assert first.lookup("missing") is None

            async def competing() -> None:
                with first.lock():
                    pytest.fail("Another task entered an owned transaction")

            with pytest.raises(DiscordRestError, match="journal_busy"):
                await asyncio.create_task(competing())
    with second.session(), second.lock():
        assert second.lookup("missing") is None


def test_failed_directory_fsync_poisons_index_and_restart_retains_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = EffectJournal(tmp_path / "effects")
    fsync = os.fsync

    def fail_directory(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            msg = "synthetic persistence failure"
            raise OSError(msg)
        fsync(fd)

    with journal.session():
        with monkeypatch.context() as patch:
            patch.setattr(os, "fsync", fail_directory)
            with pytest.raises(DiscordRestError, match="journal_unavailable"), journal.lock():
                record(journal, "attempt", scope="scope")
        with pytest.raises(DiscordRestError, match="journal_unavailable"), journal.lock():
            record(journal, "replacement", scope="scope")
    with journal.session(), journal.lock():
        retained = journal.claim(
            effect_key="attempt", payload_digest="a" * 64, scope="scope", method="POST", target="channel_messages"
        )
        assert isinstance(retained, EffectResult)
        assert retained.code == "effect_unresolved"
        replacement = journal.claim(
            effect_key="replacement", payload_digest="a" * 64, scope="scope", method="POST", target="channel_messages"
        )
        assert isinstance(replacement, EffectResult)
        assert replacement.code == "scope_unresolved"


@pytest.mark.asyncio
async def test_shutdown_retires_nested_callbacks_and_refuses_late_entry() -> None:
    tasks, started = EdgeTasks(), asyncio.Event()
    retired: list[str] = []

    async def business() -> None:
        async with tasks.callback(), tasks.callback():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                retired.append("callback")

    callback = asyncio.create_task(business())
    await started.wait()
    await tasks.close()
    await tasks.close()
    assert callback.done()
    assert retired == ["callback"]
    assert tasks.retired
    with pytest.raises(asyncio.CancelledError):
        async with tasks.callback():
            pytest.fail("Late callback entered retired dependencies")


@pytest.mark.asyncio
async def test_actual_message_callback_is_joined_before_generation_dependencies_retire() -> None:
    configured = service()
    configured.history_enabled = False
    started = asyncio.Event()
    closed = False

    async def blocked(*_args: Any, **_kwargs: Any) -> Any:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            assert not closed

    configured.worker.request = AsyncMock(side_effect=blocked)
    from lychd.interface.discord.live import ReachCog

    callback = asyncio.create_task(ReachCog(configured).on_message(message(mentions=[Mock(id=22)])))
    async with asyncio.timeout(2):
        await started.wait()
    await configured.tasks.close()
    closed = True
    assert callback.done()
    assert configured.tasks.retired
    reply_rest(configured).send_message.assert_not_awaited()
    with pytest.raises(asyncio.CancelledError):
        await ReachCog(configured).on_message(message(mentions=[Mock(id=22)]))


def bound_delivery(rest: Any, lifetime: float) -> DiscordTurnDelivery:
    now = datetime.now(UTC)
    observed = event().model_copy(
        update={
            "account_id": "101",
            "space_id": "103",
            "conversation_id": "104",
            "subject_id": "105",
            "event_id": "110",
            "mention_subject_ids": ("102",),
            "occurred_at": now,
        }
    )
    selected = policy()
    session = OperatorSession(observed, TurnDeadline.start(now, 300, lifetime, now=now))
    return DiscordTurnDelivery(
        session,
        ReplyEffects(rest, selected).for_event(observed),
        policy=selected,
        expressions=ConversationExpressions(),
        started_at=now - timedelta(seconds=1),
        followups=FollowupLedger(),
        observe=lambda *_args, **_kwargs: None,
        diagnostic=lambda _code: None,
        conversation=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("claimed", [False, True])
async def test_deadline_covers_writer_wait_and_preserves_uncertainty_after_claim(
    tmp_path: Path, *, claimed: bool
) -> None:
    posts: list[str] = []
    entered = asyncio.Event()

    async def handle(request: httpx2.Request) -> httpx2.Response:
        identified = identity(request)
        if identified is not None:
            return identified
        posts.append(request.method)
        entered.set()
        await asyncio.Event().wait()
        msg = "Unreachable"
        raise AssertionError(msg)

    async with transport(handle) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        rest.bind_channels(("104",))
        with rest.journal.session():
            delivery = bound_delivery(rest, 0.02)
            if not claimed:
                await rest._effects_lock.acquire()  # pyright: ignore[reportPrivateUsage] - hold real writer for deadline regression
            try:
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(delivery.session.deadline.remaining()):
                        await delivery.final("One terminal answer.")
            finally:
                if not claimed:
                    rest._effects_lock.release()  # pyright: ignore[reportPrivateUsage] - release injected writer contention
            records = rest.journal.inspect()
            assert len(records) == int(claimed)
            if claimed:
                assert records[0].status == "unknown"
                assert records[0].code == "cancelled"
            assert posts == (["POST"] if claimed else [])


def test_provider_renders_only_typed_history_stop() -> None:
    result = native_result("clarify")
    assert context_text(ContextTurnOutcome(result)) == result.text
    assert "403" in context_text(ContextTurnOutcome(native_result("need_context"), "permission_denied"))


@pytest.mark.asyncio
async def test_inventory_and_each_effect_port_keep_separate_authority(tmp_path: Path) -> None:
    def handle(request: httpx2.Request) -> httpx2.Response:
        return identity(request) or httpx2.Response(200, json=[{"id": "104"}, {"id": "999"}])

    async with transport(handle) as client:
        rest = make_rest(tmp_path, client)
        inventory = GuildInspection(rest)
        await inventory.verify_identity()
        await inventory.get("/guilds/103/channels")
        replies = ReplyEffects(rest, policy())
        foreign = bound_delivery(rest, 10).session.event.model_copy(update={"conversation_id": "999"})
        with pytest.raises(ValueError, match="reply_audience_binding"):
            replies.for_event(foreign)
        assert not hasattr(inventory, "write")
        assert not hasattr(replies, "write")
        port = replies.for_event(bound_delivery(rest, 10).session.event)
        assert not hasattr(port, "write")
        assert not hasattr(port, "journal")
        onboarding = OnboardingEffects(
            rest, roles=frozenset({"201", "202"}), panel_channel="104", panel_message="110", introduction_channel="105"
        )
        assert (await onboarding.ensure_member_role("101", "999", event_id="110")).code == "member_role_binding"
        publications = PublicationEffects(rest, allowed_channels=frozenset({"104"}))
        assert (
            await publications.publish("00000000-0000-0000-0000-000000000001", "999", "No send")
        ).status == "rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("oversized", [False, True])
async def test_lost_diagnostic_drain_retires_both_children_and_exact_owned_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *, oversized: bool
) -> None:
    children: list[Process] = []
    removed: list[Path] = []

    async def create(*_args: Any, **_kwargs: Any) -> Process:
        child = Process()
        child.stdout, child.stderr = asyncio.StreamReader(limit=32), asyncio.StreamReader(limit=32)
        terminate = child.terminate

        def stop() -> None:
            terminate()
            child.stdout.feed_eof()
            child.stderr.feed_eof()

        child.terminate = stop
        if not children:
            if oversized:
                child.stderr.feed_data(b"private-diagnostic-body" * 4 + b"\n")
            else:
                child.stderr.feed_eof()
        children.append(child)
        return child

    async def remove(_engine: str, path: Path, **_kwargs: Any) -> None:
        removed.append(path)

    monkeypatch.setattr(reach_operator_transport.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(reach_operator_transport, "remove_owned", remove)
    ids = tmp_path / "core.cid", tmp_path / "edge.cid"
    if oversized:
        with pytest.raises(ValueError, match="operator_diagnostic_limit"):
            await reach_operator_transport.supervise(
                "docker", (["core"], ["edge"]), ids, read_identity=reach_operator.read_regular
            )
    else:
        assert (
            await reach_operator_transport.supervise(
                "docker", (["core"], ["edge"]), ids, read_identity=reach_operator.read_regular
            )
            == 1
        )
    assert all(child.terminated.is_set() for child in children)
    assert removed == list(ids)
    assert "private-diagnostic-body" not in capsys.readouterr().err


@pytest.mark.asyncio
async def test_history_cutoff_is_inclusive_for_eager_paged_and_reply_anchor_paths() -> None:
    selected, observed = history_policy(), event()
    cutoff = observed.occurred_at - timedelta(seconds=selected.context_max_age_seconds)
    boundary = history_message(age=selected.context_max_age_seconds)
    reply = anchor().model_copy(update={"occurred_at": cutoff})
    assert history_entry(selected, observed, boundary, conversation=True) is not None
    assert anchor_allowed(selected, observed, reply, conversation=True)
    pager = HistoryPager(selected, observed, channel([boundary]), enabled=True, conversation=True, anchor=reply)
    await pager.next_page()
    assert {entry.event_id for entry in pager.entries} == {"999"}
    assert pager.state != "unavailable"


def test_retirement_timeout_kills_process_before_preclaim_work_can_resume(tmp_path: Path) -> None:
    import subprocess
    import sys

    code = """
import asyncio
from pathlib import Path
from lychd.interface.discord import lifecycle, live
from lychd.interface.discord.rest import EffectJournal

async def main():
    lifecycle.SHUTDOWN_SECONDS = 0.01
    tasks, started = lifecycle.EdgeTasks(), asyncio.Event()
    journal = EffectJournal(Path(__import__('sys').argv[1]))
    async def resistant():
        async with tasks.callback():
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await asyncio.sleep(0.1)
                with journal.lock():
                    journal.claim(effect_key='late', payload_digest='a' * 64,
                        scope='late', method='POST', target='channel_messages')
    with journal.session():
        asyncio.create_task(resistant())
        await started.wait()
        await live._retire_generation(tasks)
asyncio.run(main())
"""
    root = tmp_path / "effects"
    child = subprocess.run(  # noqa: S603 - fixed interpreter and authored code, isolated test container
        [sys.executable, "-c", code, str(root)], capture_output=True, timeout=10, check=False
    )
    assert child.returncode == 1
    assert child.stderr == b"reach_discord:retirement_failed\n"
    journal = EffectJournal(root)
    with journal.session():
        assert journal.inspect() == ()


@pytest.mark.asyncio
async def test_background_failure_is_retrieved_and_reports_a_fixed_diagnostic() -> None:
    failed = asyncio.Event()
    tasks = EdgeTasks(on_failure=failed.set)

    async def broken() -> None:
        msg = "private exception details"
        raise RuntimeError(msg)

    task = tasks.spawn(broken())
    async with asyncio.timeout(2):
        await failed.wait()
    assert task.done()
    await tasks.close()
    assert tasks.retired
