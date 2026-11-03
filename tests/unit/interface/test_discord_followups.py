"""Candidates stay quiet before a delivered plan and settle its visible commitment once."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import discord
import pytest
from pydantic import ValidationError

from lychd.compositions.reach.conversation_session import ContextRounds, request_digest
from lychd.compositions.reach.documents import validate_history
from lychd.compositions.reach.expressions import ConversationExpressions, ExpressionGif
from lychd.compositions.reach.operator_wire import (
    ReachHistoryEntry,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
)
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.research_wire import ReachResearchProgress
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.followups import MAX_FINAL_ANCHORS, FollowupLedger
from lychd.interface.discord.live import ReachCog, ReachService, event_from_message
from lychd.interface.discord.rest import EffectResult
from lychd.interface.discord.schemas import DiscordPolicy, DiscordRule

NOW = datetime.now(UTC)


def policy(**changes: Any) -> DiscordPolicy:
    values: dict[str, Any] = {
        "application_id": "11",
        "bot_user_id": "22",
        "guild_id": "33",
        "allowed_channel_ids": ("44",),
        "allowed_reply_channel_ids": ("44",),
        "allowed_adjacent_followup_channel_ids": ("44",),
        "context_message_limit": 6,
        "rules": (DiscordRule(name="person", user_ids=("55",), actions=("converse",)),),
    }
    return DiscordPolicy(**(values | changes))


def anchor(**changes: Any) -> ReachHistoryEntry:
    values: dict[str, Any] = {
        "subject_id": "22",
        "event_id": "99",
        "conversation_id": "44",
        "text": "The completed bot answer.",
        "occurred_at": NOW - timedelta(seconds=5),
    }
    return ReachHistoryEntry(**(values | changes))


def message(**changes: Any) -> Any:
    value = Mock(spec=discord.Message)
    value.id = 100
    value.guild = Mock(id=33)
    value.channel = Mock(spec=discord.TextChannel)
    value.channel.id = 44
    value.author = Mock(spec=discord.Member)
    value.author.id = 55
    value.author.bot = False
    value.author.display_name = "Human"
    value.author.roles = []
    value.webhook_id = None
    value.mentions = []
    value.reference = None
    value.content = "Could you explain the second point?"
    value.created_at = NOW
    for key, item in changes.items():
        setattr(value, key, item)
    return value


def service() -> ReachService:
    configured = policy()
    worker = Mock()
    worker.ready = ReachWorkerReady(
        generation="bd9383c7-46c0-43da-82af-c428a5568362",
        started_at=NOW - timedelta(seconds=20),
        policy_digest=configured.digest,
        corpus_digest="c" * 64,
        model_binding_digest="b" * 64,
        adaptive_context=True,
        expressions=ConversationExpressions(enabled=True),
    )
    worker.available = True
    worker.lock = asyncio.Lock()
    worker.request = AsyncMock(
        return_value=ReachWorkerResult(
            request_id="request",
            status="ignore",
            policy_digest=configured.digest,
            corpus_digest="c" * 64,
        )
    )
    rest = Mock()
    rest.send_message = AsyncMock()
    rest.add_reaction = AsyncMock()
    rest.send_gif = AsyncMock()
    return ReachService(configured, worker, rest, admin_users=frozenset(), history_enabled=True, conversation=True)


def event(kind: Literal["reply", "followup"] = "followup") -> ReachEvent:
    observed = event_from_message(message(), policy(), conversation=True, continuation=(kind, anchor()))
    assert observed is not None
    return observed


def request(kind: Literal["reply", "followup"] = "followup") -> ReachWorkerRequest:
    return ReachWorkerRequest(
        request_id="request",
        event=event(kind),
        history_state="more",
        reply_to_event_id="99" if kind == "reply" else None,
        reply_anchor=anchor() if kind == "reply" else None,
        continuation_anchor=anchor() if kind == "followup" else None,
    )


def test_continuation_configuration_defaults_off_and_requires_exact_channels() -> None:
    configured = policy(allowed_reply_channel_ids=(), allowed_adjacent_followup_channel_ids=())
    assert not configured.to_reach_policy().allowed_reply_conversation_ids
    assert not configured.to_reach_policy().allowed_adjacent_followup_conversation_ids
    for change in ({"allowed_reply_channel_ids": ("45",)}, {"adjacent_followup_window_seconds": 121}):
        with pytest.raises(ValidationError):
            policy(**change)
    with pytest.raises(ValidationError):
        policy(allowed_reply_channel_ids=("44", "44"))


def test_unlisted_candidate_sender_is_rejected_before_body_access() -> None:
    observed = message(content=object())
    observed.author.id = 56
    assert event_from_message(observed, policy(), conversation=True, continuation=("followup", anchor())) is None
    assert event_from_message(message(content=object()), policy(), conversation=True) is None


@pytest.mark.parametrize("kind", ["reply", "followup"])
def test_shared_policy_and_anchor_recheck_candidate_identity(kind: Literal["reply", "followup"]) -> None:
    configured = policy().to_reach_policy()
    current = request(kind)
    assert prepare_turn(configured, current.event, now=NOW).allowed
    validate_history(configured, current)
    for altered in (
        current.event.model_copy(update={"related_subject_id": "56"}),
        current.event.model_copy(update={"related_occurred_at": NOW}),
        current.event.model_copy(update={"related_occurred_at": NOW - timedelta(seconds=121)}),
    ):
        if kind == "reply" and altered.related_occurred_at == NOW - timedelta(seconds=121):
            continue
        assert not prepare_turn(configured, altered, now=NOW).allowed
    key = "reply_anchor" if kind == "reply" else "continuation_anchor"
    reason = "history_anchor_binding" if kind == "reply" else "history_continuation_binding"
    with pytest.raises(ValueError, match=reason):
        validate_history(configured, current.model_copy(update={key: anchor(event_id="98")}))
    with pytest.raises(ValueError, match="history_limit"):
        validate_history(configured.model_copy(update={"context_message_limit": 0}), current)


def test_ambient_anchor_is_distinct_from_actual_reply_and_frozen_between_rounds() -> None:
    current = request()
    with pytest.raises(ValueError, match="history_continuation_binding"):
        validate_history(policy().to_reach_policy(), current.model_copy(update={"reply_to_event_id": "99"}))
    rounds = ContextRounds()
    digest = request_digest(current)
    rounds.admit(current, digest)
    rounds.settled(
        current,
        ReachWorkerResult(
            request_id="request",
            status="need_context",
            policy_digest=policy().digest,
            corpus_digest="c" * 64,
        ),
        adaptive=True,
    )
    changed = current.model_copy(update={"context_round": 1, "continuation_anchor": anchor(text="Changed")})
    assert rounds.reason(changed, request_digest(changed), adaptive=True) == "context_binding"


def test_ignore_has_no_text_or_expression_and_cannot_open_context_continuation() -> None:
    current = request()
    values = {"request_id": "request", "status": "ignore", "policy_digest": policy().digest, "corpus_digest": "c" * 64}
    with pytest.raises(ValidationError, match="result_ignore"):
        ReachWorkerResult.model_validate(values | {"text": "I will ignore this"})
    rounds = ContextRounds()
    rounds.admit(current, request_digest(current))
    rounds.settled(current, ReachWorkerResult.model_validate(values), adaptive=True)
    later = current.model_copy(update={"context_round": 1})
    assert rounds.reason(later, request_digest(later), adaptive=True) == "context_continuation"


@pytest.mark.parametrize("failure", ["different_person", "intervening", "expired", "reference", "used"])
def test_adjacent_invitation_is_one_shot_and_closes_on_other_activity(failure: str) -> None:
    ledger = FollowupLedger()
    ledger.delivered((anchor(),), human_subject_id="55")
    if failure in {"intervening", "used"}:
        ledger.activity(
            "44",
            "100",
            "56" if failure == "intervening" else "55",
            NOW,
            reference_id=None,
            allow_reply=False,
            allow_followup=True,
            followup_window=60,
        )
    outcome = ledger.activity(
        "44",
        "101",
        "56" if failure == "different_person" else "55",
        NOW + timedelta(seconds=60) if failure == "expired" else NOW,
        reference_id="unresolved" if failure == "reference" else None,
        allow_reply=False,
        allow_followup=True,
        followup_window=60,
    )
    assert outcome is None


def test_final_anchor_retention_is_bounded_and_restarts_empty() -> None:
    ledger = FollowupLedger()
    for index in range(MAX_FINAL_ANCHORS + 1):
        ledger.delivered((anchor(event_id=str(index + 1000)),), human_subject_id="55")
    assert len(ledger.finals) == MAX_FINAL_ANCHORS
    assert not ledger.adjacent
    assert not FollowupLedger().finals


@pytest.mark.parametrize("echoed_part", ["99", "100"])
def test_gateway_echo_of_any_completed_final_part_preserves_adjacent_invitation(echoed_part: str) -> None:
    ledger = FollowupLedger()
    final = (anchor(event_id="99"), anchor(event_id="100"))
    ledger.delivered(final, human_subject_id="55")
    assert (
        ledger.activity(
            "44",
            echoed_part,
            "22",
            NOW,
            reference_id=None,
            allow_reply=False,
            allow_followup=True,
            followup_window=60,
        )
        is None
    )
    assert ledger.adjacent == {"44": "100"}
    assert ledger.activity(
        "44",
        "101",
        "55",
        NOW,
        reference_id=None,
        allow_reply=False,
        allow_followup=True,
        followup_window=60,
    ) == ("followup", final[-1])
    assert not ledger.adjacent


def test_successful_decoration_only_preserves_its_open_final_and_is_never_a_reply_target() -> None:
    ledger = FollowupLedger()
    ledger.delivered((anchor(),), human_subject_id="55", origin_event_id="request:one")
    ledger.decorated("44", "100", origin_event_id="request:other")
    assert not ledger.decorations
    ledger.decorated("44", "100", origin_event_id="request:one")
    assert ledger.decorations == {("44", "100"): "99"}
    assert ("44", "100") not in ledger.finals
    assert (
        ledger.activity(
            "44", "100", "22", NOW, reference_id=None, allow_reply=True, allow_followup=True, followup_window=60
        )
        is None
    )
    assert ledger.adjacent == {"44": "99"}
    assert (
        ledger.activity(
            "44", "101", "55", NOW, reference_id="100", allow_reply=True, allow_followup=True, followup_window=60
        )
        is None
    )
    assert not ledger.adjacent
    ledger.activity(
        "44", "100", "22", NOW, reference_id=None, allow_reply=True, allow_followup=True, followup_window=60
    )
    assert not ledger.adjacent
    ledger.decorated("44", "102", origin_event_id="request:one")
    assert ("44", "102") not in ledger.decorations


def test_decoration_ids_share_the_existing_retention_budget() -> None:
    ledger = FollowupLedger()
    ledger.delivered((anchor(),), human_subject_id="55", origin_event_id="request:one")
    for index in range(MAX_FINAL_ANCHORS + 1):
        ledger.decorated("44", str(index + 1000), origin_event_id="request:one")
    assert len(ledger.finals) + len(ledger.decorations) == MAX_FINAL_ANCHORS
    ledger.delivered((anchor(event_id="999"),), human_subject_id="55", origin_event_id="request:two")
    assert not ledger.adjacent
    assert ("44", "999") not in ledger.finals


@pytest.mark.parametrize("interruption", ["unrelated_bot", "gif", "human", "older_final_part"])
def test_other_activity_closes_invitation_and_late_final_echo_cannot_reopen_it(interruption: str) -> None:
    ledger = FollowupLedger()
    ledger.delivered((anchor(event_id="97"), anchor(event_id="98")), human_subject_id="55")
    ledger.delivered(
        (anchor(event_id="99"), anchor(event_id="100")), human_subject_id="55", origin_event_id="request:one"
    )
    ledger.decorated("44", "103", origin_event_id="request:one")
    event_id = "97" if interruption == "older_final_part" else "101"
    subject_id = "56" if interruption == "human" else "22"
    assert (
        ledger.activity(
            "44",
            event_id,
            subject_id,
            NOW,
            reference_id=None,
            allow_reply=False,
            allow_followup=True,
            followup_window=60,
        )
        is None
    )
    assert not ledger.adjacent
    for late_echo in ("99", "100", "103"):
        assert (
            ledger.activity(
                "44",
                late_echo,
                "22",
                NOW,
                reference_id=None,
                allow_reply=False,
                allow_followup=True,
                followup_window=60,
            )
            is None
        )
        assert not ledger.adjacent
    assert (
        ledger.activity(
            "44",
            "102",
            "55",
            NOW,
            reference_id=None,
            allow_reply=False,
            allow_followup=True,
            followup_window=60,
        )
        is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["ignore", "busy", "error"])
async def test_candidate_is_silent_without_any_history_read_or_acknowledgement(failure: str) -> None:
    configured = service()
    configured.followups.delivered((anchor(),), human_subject_id="55")
    observed = message()
    if failure == "busy":
        configured.worker.available = False
    elif failure == "error":
        cast("AsyncMock", configured.worker.request).side_effect = TimeoutError()
    await ReachCog(configured).on_message(observed)
    observed.channel.history.assert_not_called()
    observed.channel.fetch_message.assert_not_called()
    cast("AsyncMock", configured.rest.send_message).assert_not_awaited()
    cast("AsyncMock", configured.rest.add_reaction).assert_not_awaited()
    cast("AsyncMock", configured.rest.send_gif).assert_not_awaited()
    assert not configured.followups.adjacent
    if failure != "busy":
        call = cast("AsyncMock", configured.worker.request).await_args
        assert call is not None
        assert call.kwargs["continuation_anchor"] == anchor()
        assert call.kwargs["reply_anchor"] is None
        assert call.kwargs["reply_to_event_id"] is None


def commitment_cog() -> tuple[ReachService, ReachCog]:
    configured = service()
    configured.worker.ready = configured.worker.ready.model_copy(update={"research_enabled": True})
    configured.message_continuation = Mock(return_value=("followup", anchor()))
    cast("AsyncMock", configured.rest.send_message).return_value = EffectResult(status="succeeded", remote_id="200")
    return configured, ReachCog(configured)


def terminal_result(
    configured: ReachService, status: Literal["error", "refused", "ignore", "conversation"] = "error", *, text: str = ""
) -> ReachWorkerResult:
    return ReachWorkerResult(
        request_id="request",
        status=status,
        text=text,
        policy_digest=configured.policy.digest,
        corpus_digest="c" * 64,
        model_binding_digest="b" * 64,
    )


async def deliver_plan(configured: ReachService, observed: ReachEvent) -> bool:
    callback = configured.worker.progress
    assert callback is not None
    return await callback(
        observed,
        ReachResearchProgress(
            call_id=str(uuid4()),
            request_id="request",
            binding_digest="b" * 64,
            text="I will read the admitted source and return an answer.",
        ),
    )


def sent_phases(configured: ReachService) -> list[str]:
    return [call.kwargs["phase"] for call in cast("AsyncMock", configured.rest.send_message).await_args_list]


def assert_no_error_decoration_or_invitation(configured: ReachService) -> None:
    cast("AsyncMock", configured.rest.add_reaction).assert_not_awaited()
    cast("AsyncMock", configured.rest.send_gif).assert_not_awaited()
    assert not configured.followups.adjacent
    assert not configured.followups.finals


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["error", "refused", "exception", "none"])
async def test_confirmed_candidate_plan_gets_one_terminal_failure_notice(failure: str) -> None:
    configured, cog = commitment_cog()

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult | None:
        assert await deliver_plan(configured, observed)
        if failure == "exception":
            raise TimeoutError
        if failure == "none":
            return None
        return terminal_result(configured, "refused" if failure == "refused" else "error")

    configured.run_event = AsyncMock(side_effect=run)
    await cog.on_message(message())
    assert sent_phases(configured) == ["plan", "final"]
    final = cast("AsyncMock", configured.rest.send_message).await_args_list[-1]
    assert final.kwargs["event_id"] == final.kwargs["reply_to"] == "100"
    assert "can't perform" in final.args[1] if failure == "refused" else "couldn't prepare" in final.args[1]
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
@pytest.mark.parametrize("delivery", ["none", "rejected", "unknown", "exception", "foreign", "ignore"])
async def test_unconfirmed_or_ignored_candidates_stay_quiet(delivery: str) -> None:
    configured, cog = commitment_cog()
    if delivery in {"rejected", "unknown"}:
        cast("AsyncMock", configured.rest.send_message).return_value = EffectResult.model_validate({"status": delivery})
    elif delivery == "exception":
        cast("AsyncMock", configured.rest.send_message).side_effect = OSError

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        if delivery != "none":
            progress_event = (
                observed.model_copy(update={"question": "A different request."}) if delivery == "foreign" else observed
            )
            await deliver_plan(configured, progress_event)
        return terminal_result(configured, "ignore" if delivery == "ignore" else "error")

    configured.run_event = AsyncMock(side_effect=run)
    await cog.on_message(message())
    assert sent_phases(configured) == ([] if delivery == "none" else ["plan"])
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
@pytest.mark.parametrize(("part", "outcome"), [(0, "exception"), (0, "unknown"), (1, "exception"), (1, "unknown")])
async def test_started_final_delivery_never_retries_with_an_error_notice(part: int, outcome: str) -> None:
    configured, cog = commitment_cog()

    async def send(_channel: str, _text: str, **kwargs: Any) -> EffectResult:
        if kwargs["phase"] == "final" and kwargs["part"] == part:
            if outcome == "exception":
                raise OSError
            return EffectResult(status="unknown")
        return EffectResult(status="succeeded", remote_id="200")

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        assert await deliver_plan(configured, observed)
        return terminal_result(configured, "conversation", text="A" * 4000)

    cast("AsyncMock", configured.rest.send_message).side_effect = send
    configured.run_event = AsyncMock(side_effect=run)
    await cog.on_message(message())
    assert sent_phases(configured) == ["plan", *["final"] * (part + 1)]
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
@pytest.mark.parametrize("interruption", ["duplicate_before_plan", "duplicate_after_plan", "other_event"])
async def test_other_invocation_neither_inherits_nor_clears_the_active_plan(interruption: str) -> None:
    configured, cog = commitment_cog()
    entered, resume = asyncio.Event(), asyncio.Event()
    calls = 0

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult | None:
        nonlocal calls
        calls += 1
        if calls != 1:
            return terminal_result(configured) if interruption == "other_event" else None
        if interruption != "duplicate_before_plan":
            assert await deliver_plan(configured, observed)
        entered.set()
        await resume.wait()
        if interruption == "duplicate_before_plan":
            assert await deliver_plan(configured, observed)
        return terminal_result(configured)

    configured.run_event = AsyncMock(side_effect=run)
    first = asyncio.create_task(cog.on_message(message()))
    try:
        async with asyncio.timeout(3):
            await entered.wait()
        before = sent_phases(configured)
        await cog.on_message(message(id=101 if interruption == "other_event" else 100))
        assert sent_phases(configured) == before
        resume.set()
        await first
    finally:
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
    assert sent_phases(configured) == ["plan", "final"]
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
@pytest.mark.parametrize("next_has_plan", [False, True])
async def test_new_candidate_owns_its_plan_while_previous_final_delivery_is_pending(*, next_has_plan: bool) -> None:
    configured, cog = commitment_cog()
    final_started, release_final = asyncio.Event(), asyncio.Event()

    async def send(_channel: str, _text: str, **kwargs: Any) -> EffectResult:
        if kwargs["phase"] == "final" and kwargs["event_id"] == "100":
            final_started.set()
            await release_final.wait()
        return EffectResult(status="succeeded", remote_id="200")

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        if observed.event_id == "100" or next_has_plan:
            assert await deliver_plan(configured, observed)
        return terminal_result(configured)

    cast("AsyncMock", configured.rest.send_message).side_effect = send
    configured.run_event = AsyncMock(side_effect=run)
    first = asyncio.create_task(cog.on_message(message()))
    try:
        async with asyncio.timeout(3):
            await final_started.wait()
        await cog.on_message(message(id=101))
        expected = ["plan", "final", "plan", "final"] if next_has_plan else ["plan", "final"]
        assert sent_phases(configured) == expected
        release_final.set()
        await first
    finally:
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
async def test_cancelled_candidate_propagates_and_releases_its_plan_ownership() -> None:
    configured, cog = commitment_cog()
    entered = asyncio.Event()

    async def run(observed: ReachEvent, *_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        assert await deliver_plan(configured, observed)
        if observed.event_id == "100":
            entered.set()
            await asyncio.Event().wait()
        return terminal_result(configured)

    configured.run_event = AsyncMock(side_effect=run)
    first = asyncio.create_task(cog.on_message(message()))
    async with asyncio.timeout(3):
        await entered.wait()
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert sent_phases(configured) == ["plan"]
    await cog.on_message(message(id=101))
    assert sent_phases(configured) == ["plan", "plan", "final"]
    assert_no_error_decoration_or_invitation(configured)


@pytest.mark.asyncio
async def test_reply_without_ping_uses_exact_retained_bot_part_without_fetching() -> None:
    configured = service()
    configured.followups.delivered((anchor(),), human_subject_id="55")
    observed = message(reference=discord.MessageReference(message_id=99, channel_id=44, guild_id=33))
    await ReachCog(configured).on_message(observed)
    call = cast("AsyncMock", configured.worker.request).await_args
    assert call is not None
    assert call.args[0].trigger == "reply"
    assert call.kwargs["reply_to_event_id"] == "99"
    assert call.kwargs["reply_anchor"] == anchor()
    assert call.kwargs["continuation_anchor"] is None
    observed.channel.fetch_message.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("last_status", ["succeeded", "unknown", "rejected"])
async def test_only_complete_successful_final_seeds_next_candidate(
    last_status: Literal["succeeded", "unknown", "rejected"],
) -> None:
    configured = service()
    remote_ids = [str(discord.utils.time_snowflake(NOW - timedelta(seconds=1))), str(discord.utils.time_snowflake(NOW))]
    cast("AsyncMock", configured.rest.send_message).side_effect = [
        EffectResult(status="succeeded", remote_id=remote_ids[0]),
        EffectResult(status=last_status, remote_id=remote_ids[1]),
    ]
    result = ReachWorkerResult(
        request_id="request",
        status="conversation",
        text="A" * 2000,
        policy_digest=configured.policy.digest,
        corpus_digest="c" * 64,
    )
    configured.run_event = AsyncMock(return_value=result)
    await ReachCog(configured).on_message(message(mentions=[Mock(id=22)]))
    assert bool(configured.followups.adjacent) == (last_status == "succeeded")
    assert len(configured.followups.finals) == (2 if last_status == "succeeded" else 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("gif_status", ["succeeded", "unknown", "rejected"])
async def test_only_known_successful_gif_echo_preserves_completed_final(
    gif_status: Literal["succeeded", "unknown", "rejected"],
) -> None:
    configured = service()
    expressions = ConversationExpressions(
        enabled=True,
        gifs=(
            ExpressionGif(id="begins", description="So it begins", url="https://media.giphy.com/media/ABC/giphy.gif"),
        ),
    )
    configured.worker.ready = configured.worker.ready.model_copy(update={"expressions": expressions})
    final_id = str(discord.utils.time_snowflake(NOW - timedelta(seconds=2)))
    gif_id = str(discord.utils.time_snowflake(NOW - timedelta(seconds=1)))
    cast("AsyncMock", configured.rest.send_message).return_value = EffectResult(status="succeeded", remote_id=final_id)
    cast("AsyncMock", configured.rest.send_gif).return_value = EffectResult(status=gif_status, remote_id=gif_id)
    result = ReachWorkerResult(
        request_id="request",
        status="conversation",
        text="The project begins.",
        gif_id="begins",
        policy_digest=configured.policy.digest,
        corpus_digest="c" * 64,
        model_binding_digest="b" * 64,
    )
    configured.run_event = AsyncMock(return_value=result)
    await ReachCog(configured).on_message(message(mentions=[Mock(id=22)], created_at=NOW - timedelta(seconds=3)))
    cast("AsyncMock", configured.rest.send_gif).assert_awaited_once()
    echoed = message(id=int(gif_id), created_at=NOW - timedelta(seconds=1))
    echoed.author.id = 22
    echoed.author.bot = True
    assert configured.message_continuation(echoed) is None
    assert bool(configured.followups.adjacent) == (gif_status == "succeeded")
    candidate = configured.message_continuation(message(id=101))
    assert (candidate is not None) == (gif_status == "succeeded")
    if candidate is not None:
        assert candidate[0] == "followup"
        assert candidate[1].event_id == final_id
        assert candidate[1].text == "The project begins."
