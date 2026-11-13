"""Provider reply projection and exact-session delivery, without native execution."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import discord

from lychd.compositions.reach.conversation_session import ContextTurnOutcome
from lychd.compositions.reach.expressions import ConversationExpressions
from lychd.compositions.reach.operator_session import OperatorSession
from lychd.compositions.reach.operator_trace import TraceName, error_code, uuid_or_none
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerResult
from lychd.compositions.reach.research_wire import ReachResearchProgress
from lychd.interface.discord.followups import FollowupLedger
from lychd.interface.discord.messages import split_message
from lychd.interface.discord.ports import TurnEffects
from lychd.interface.discord.rest import DiscordRestError
from lychd.interface.discord.schemas import DEFAULT_AGENT_DISPLAY_NAME, DiscordPolicy
from lychd.interface.observation import observation_context

_AGENT = "{agent}"


def _named(text: str, agent_name: str) -> str:
    """Insert the configured display name into one fixed notice; it is never a format string."""
    return text.replace(_AGENT, agent_name)


# Templates: ``{agent}`` is replaced by the policy's display name when a notice is rendered.
WORKER_FAILURES = {
    "budget": (
        "My configured context budget was too small for this request. I read the available chat context, "
        "but couldn't fit the instructions and selected sources needed to answer. Please narrow the question."
    ),
    "model_unavailable": "The model service is unavailable. Please try again later; a maintainer should check it.",
    "model_timeout": "The model timed out while preparing the answer. Please try again with a shorter request.",
    "model_refused": "The model refused this request. A maintainer can check its diagnostics.",
    "model_protocol": (
        "The model returned a response {agent} couldn't safely use. A maintainer should check the model adapter."
    ),
    "model_failed": ("The model failed while preparing the answer. A maintainer should check its diagnostics."),
    "run_timeout": "{agent} timed out while preparing the answer. Please try again with a shorter request.",
    "run_missing": (
        "{agent} couldn't find the answer run it started (run_missing). A maintainer should check diagnostics."
    ),
    "run_incomplete": "{agent}'s answer run didn't complete (run_incomplete). A maintainer should check diagnostics.",
    "result_binding": (
        "{agent} received a mismatched answer result (result_binding). A maintainer should check diagnostics."
    ),
    "run_failed": (
        "An internal processing step failed (run_failed). Please try again later; a maintainer can check diagnostics."
    ),
    "worker_unavailable": "{agent}'s answer worker is unavailable or busy. Please try again shortly.",
    "permission_denied": (
        "Discord denied access to earlier channel messages (403). Ask a maintainer to check {agent}'s "
        "View Channel and Read Message History permissions."
    ),
    "conversation_not_allowed": (
        "{agent} isn't enabled in this channel. Ask a maintainer to add it to the allowed channels."
    ),
    "subject_not_allowed": (
        "You're not included in {agent}'s allowed user or role list. Ask a maintainer to check your access."
    ),
    "action_not_allowed": "This type of request isn't enabled for your account or this channel.",
    "action_not_supported": "{agent} doesn't support this request type.",
    "trigger_not_allowed": "{agent} isn't configured to answer this kind of message here.",
    "missing_agent_mention": "Please mention {agent} directly in this message.",
    "wrong_platform": "This request came from an unsupported chat platform.",
    "wrong_account": "This request came from an account {agent} isn't configured to serve.",
    "wrong_space": "{agent} isn't configured for this server or workspace.",
    "self_event": "{agent} can't answer a message sent by the bot itself.",
    "automated_subject": "{agent} can't answer messages from another bot account.",
    "event_expired": "This request expired before {agent} could process it. Please send it again.",
    "event_from_future": "This request has an invalid future timestamp. Please send it again.",
    "question_empty": "Please include a question for {agent}.",
    "question_too_large": "This question is over {agent}'s configured input limit. Please shorten it.",
    "question_invalid": "This question contains text {agent} can't safely process. Please edit and resend it.",
    "context_disabled": "{agent}'s chat history access isn't enabled for this request.",
    "relationship_invalid": "{agent} couldn't verify that this reply belongs to the recent conversation.",
}


def worker_problem(reason: str | None, *, refused: bool = False, agent_name: str = DEFAULT_AGENT_DISPLAY_NAME) -> str:
    """Render only closed worker reasons; never display exception or model text."""
    if reason in WORKER_FAILURES:
        return _named(WORKER_FAILURES[reason], agent_name)
    if refused:
        return _named(
            "I can't perform this request (request_refused). "
            "Ask a maintainer to check {agent}'s channel and access rules.",
            agent_name,
        )
    return _named(WORKER_FAILURES["run_failed"], agent_name)


def failure_text(error: Exception, *, agent_name: str = DEFAULT_AGENT_DISPLAY_NAME) -> str:
    """Translate known edge failures without exposing provider bodies or exception text."""
    if isinstance(error, discord.Forbidden):
        code = "http_403"
    elif isinstance(error, discord.NotFound):
        code = "http_404"
    elif isinstance(error, discord.HTTPException):
        code = f"http_{error.status}"
    elif isinstance(error, DiscordRestError):
        code = error.code if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", error.code) else "discord_error"
    elif isinstance(error, TimeoutError):
        code = "timeout"
    elif isinstance(error, ValueError) and str(error) in {
        "worker_busy_or_unavailable",
        "worker_unavailable",
    }:
        code = "worker_unavailable"
    elif isinstance(error, ValueError) and str(error) == "conversation_budget":
        code = "budget"
    else:
        code = error_code(error)

    messages = {
        "http_401": "Discord rejected {agent}'s bot authentication (401). A maintainer should check the bot token.",
        "http_403": (
            "Discord denied one of {agent}'s channel operations (403). Ask a maintainer to check View Channel, "
            "Read Message History, and Send Messages permissions."
        ),
        "http_404": (
            "Discord couldn't find the configured channel or message (404). "
            "Ask a maintainer to check the channel binding."
        ),
        "network_error": (
            "{agent} couldn't reach Discord. Please try again later; a maintainer should check connectivity."
        ),
        "timeout": "{agent} timed out while preparing the answer. Please try again with a shorter request.",
        "budget": WORKER_FAILURES["budget"],
        "worker_unavailable": WORKER_FAILURES["worker_unavailable"],
    }
    fallback = (
        f"I couldn't prepare an answer. Please try again later (diagnostic code: {code}). "
        "A maintainer can check {agent}'s logs."
    )
    return _named(messages.get(code, fallback), agent_name)


def result_text(result: ReachWorkerResult, *, agent_name: str = DEFAULT_AGENT_DISPLAY_NAME) -> str:
    """Render worker answers and precise safe reasons without attempting an empty message."""
    if result.text.strip():
        return result.text
    if result.status == "refused":
        return worker_problem(result.reason, refused=True, agent_name=agent_name)
    if result.status == "error":
        return worker_problem(result.reason, agent_name=agent_name)
    return "I couldn't prepare an answer. Please try again later (diagnostic code: empty_result)."


def context_text(outcome: ContextTurnOutcome, *, agent_name: str = DEFAULT_AGENT_DISPLAY_NAME) -> str:
    """Render a driver stop here, preserving unrelated native clarifications exactly."""
    if outcome.stop is None:
        return result_text(outcome.result, agent_name=agent_name)
    notices = {
        "permission_denied": (
            "I couldn't read earlier messages in this channel because Discord denied history access (403). "
            "Ask a maintainer to check {agent}'s View Channel and Read Message History permissions, then try again."
        ),
        "unavailable": "Earlier messages are unavailable right now. Please quote the relevant message or clarify your question.",
        "disabled": "Chat history isn't enabled here. Please quote the relevant message or clarify your question.",
        "exhausted": "I'm missing relevant context. Please quote the message or clarify your question.",
        "budget": "I've reached the history limit. Please quote the relevant part of the conversation.",
        "round_limit": "I've reached the history limit. Please quote the relevant part of the conversation.",
        "no_progress": "I couldn't load more relevant messages. Please quote the missing material or clarify your question.",
    }
    return _named(notices[outcome.stop], agent_name)


class DiscordTurnDelivery:
    """Project one session through an audience-bound effect port and one final commitment."""

    def __init__(
        self,
        session: OperatorSession,
        effects: TurnEffects,
        *,
        policy: DiscordPolicy,
        expressions: ConversationExpressions,
        started_at: datetime,
        followups: FollowupLedger,
        observe: Callable[..., None],
        diagnostic: Callable[[str], None],
        conversation: bool,
        failure_diagnostic: str | None = None,
    ) -> None:
        """Bind provider projection to this session's exact audience and effect methods."""
        self.session, self.effects, self.policy = session, effects, policy
        self.expression_choices, self.started_at, self.followups = expressions, started_at, followups
        self._observe, self.diagnostic, self.conversation = observe, diagnostic, conversation
        self.failure_diagnostic = failure_diagnostic
        self.expression_blocked = False

    def observe(self, name: TraceName, **fields: Any) -> None:
        self._observe(name, self.session.event, **fields)

    async def plan(self, progress: ReachResearchProgress) -> bool:
        event = self.session.event
        if event.trigger == "command" or self.session.closed or self.session.terminal_started:
            return False
        self.session.deadline.check()
        try:
            outcome = await self.effects.send_text(progress.text, phase="plan", silent=True)
        except (ValueError, OSError, TimeoutError, DiscordRestError):
            self.observe("research_plan", status="error")
            self.diagnostic("research_plan_failed")
            return False
        self.observe("research_plan", status=outcome.status, remote_id=outcome.remote_id)
        return self.session.confirm_plan(delivered=outcome.status == "succeeded")

    async def acknowledge(self) -> bool:
        if not self.conversation:
            preview = " ".join(self.session.event.question.split())[:240]
            text = f"I'll look into your request: “{preview}”. I'll return here with an answer or a clarification question."
            self.observe("acknowledgement", status="started", operation="ack")
            outcome = await self.effects.send_text(text, phase="ack")
            self.observe("acknowledgement", status=outcome.status, operation="ack", remote_id=outcome.remote_id)
            if outcome.status != "succeeded":
                self.diagnostic("message_failed")
                return False
        choices = self.expression_choices
        if choices.enabled and choices.acknowledge:
            try:
                outcome = await self.effects.react("👀", phase="seen")
                self.observe("expression", status=outcome.status, operation="reaction")
                if outcome.status != "succeeded":
                    self.expression_blocked = True
                    self.diagnostic("expression_failed")
            except (ValueError, OSError, TimeoutError, DiscordRestError):
                self.expression_blocked = True
                self.diagnostic("expression_failed")
        return True

    async def final(self, text: str, *, result: ReachWorkerResult | None = None) -> bool:
        parts = split_message(text)
        self.session.begin_terminal()
        event = self.session.event
        binding = (
            {"run_id": uuid_or_none(result.run_id), "request_id": uuid_or_none(result.request_id)} if result else {}
        )
        anchors: list[ReachHistoryEntry] = []
        can_retain = (
            result is not None
            and (
                result.status in {"conversation", "clarify"}
                or (self.session.outcome is not None and self.session.outcome.stop is not None)
            )
            and event.space_id == self.policy.guild_id
            and event.conversation_id
            in self.policy.allowed_reply_channel_ids + self.policy.allowed_adjacent_followup_channel_ids
        )
        for index, part in enumerate(parts):
            self.session.deadline.check()
            self.observe(
                "delivery",
                status="started",
                operation="final",
                part=index,
                parts=len(parts),
                chars=len(part),
                **binding,
            )
            with observation_context(
                run_id=uuid_or_none(result.run_id) if result else None,
                request_id=uuid_or_none(result.request_id) if result else None,
            ):
                outcome = await self.effects.send_text(part, phase="final", part=index)
            self.observe(
                "delivery",
                status=outcome.status,
                operation="final",
                part=index,
                parts=len(parts),
                remote_id=outcome.remote_id,
                **binding,
            )
            if outcome.status != "succeeded":
                self.diagnostic(
                    self.failure_diagnostic or ("request_failed" if event.trigger == "command" else "message_failed")
                )
                return False
            if can_retain:
                if outcome.remote_id is None or not outcome.remote_id.isdecimal():
                    can_retain = False
                    continue
                try:
                    occurred_at = discord.utils.snowflake_time(int(outcome.remote_id))
                    if not self.started_at <= occurred_at <= datetime.now(UTC):
                        can_retain = False
                        continue
                    anchors.append(
                        ReachHistoryEntry(
                            subject_id=self.policy.bot_user_id,
                            event_id=outcome.remote_id,
                            conversation_id=event.conversation_id,
                            text=part,
                            occurred_at=occurred_at,
                        )
                    )
                except (ValueError, OverflowError):
                    can_retain = False
        if can_retain:
            self.followups.delivered(tuple(anchors), human_subject_id=event.subject_id, origin_event_id=event.event_id)
        return True

    async def expressions(self, result: ReachWorkerResult) -> None:
        event, choices = self.session.event, self.expression_choices
        if (
            not choices.enabled
            or event.trigger == "command"
            or result.status != "conversation"
            or self.expression_blocked
        ):
            return
        self.session.deadline.check()
        try:
            choices.validate_selection(result.reaction, result.gif_id)
            if result.reaction is not None and not (result.reaction == "👀" and choices.acknowledge):
                outcome = await self.effects.react(result.reaction, phase="reply")
                self.observe(
                    "expression",
                    status=outcome.status,
                    operation="reaction",
                    run_id=uuid_or_none(result.run_id),
                    request_id=uuid_or_none(result.request_id),
                )
                if outcome.status != "succeeded":
                    self.diagnostic("expression_failed")
                    return
            if result.gif_id is not None:
                selected = next(item for item in choices.gifs if item.id == result.gif_id)
                self.session.deadline.check()
                outcome = await self.effects.send_gif(selected.url)
                self.observe(
                    "expression",
                    status=outcome.status,
                    operation="gif",
                    run_id=uuid_or_none(result.run_id),
                    request_id=uuid_or_none(result.request_id),
                )
                if outcome.status != "succeeded":
                    self.diagnostic("expression_failed")
                elif outcome.remote_id is not None:
                    self.followups.decorated(event.conversation_id, outcome.remote_id, origin_event_id=event.event_id)
        except (ValueError, OSError, TimeoutError, DiscordRestError):
            self.diagnostic("expression_failed")
