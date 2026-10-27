"""Pure, fail-closed preparation; no transport, retrieval, model, grants or ledger."""

from __future__ import annotations

from datetime import datetime, timedelta

from lychd.compositions.reach.schemas import (
    PreparedReachTurn,
    ReachDecision,
    ReachEvent,
    ReachEventIdentity,
    ReachPolicy,
    ReachReason,
    require_aware,
)

_ASCII_CONTROL_LIMIT = 32


def prepare_turn(policy: ReachPolicy, event: ReachEvent, *, now: datetime) -> ReachDecision:  # noqa: C901, PLR0911, PLR0912 - explicit closed refusal order
    """Filter one transient event; rejected content never belongs in an Intent or Graph."""
    require_aware(now)
    identity = ReachEventIdentity.from_event(event)

    def refuse(reason: ReachReason) -> ReachDecision:
        return ReachDecision(
            allowed=False, reason=reason, identity=identity, policy_digest=policy.digest, evaluated_at=now
        )

    if event.platform != policy.platform:
        return refuse("wrong_platform")
    if event.account_id != policy.account_id:
        return refuse("wrong_account")
    if event.space_id != policy.space_id:
        return refuse("wrong_space")
    if event.conversation_id not in policy.allowed_conversation_ids:
        return refuse("conversation_not_allowed")
    if event.subject_id == policy.agent_subject_id:
        return refuse("self_event")
    if event.is_automated:
        return refuse("automated_subject")
    if event.trigger not in policy.allowed_triggers:
        return refuse("trigger_not_allowed")
    if event.trigger == "mention" and policy.agent_subject_id not in event.mention_subject_ids:
        return refuse("missing_agent_mention")
    if event.action not in ("answer_docs", "summarize_context"):
        return refuse("action_not_supported")
    rule = next(
        (
            candidate
            for candidate in policy.rules
            if event.subject_id in candidate.subject_ids or set(event.group_ids).intersection(candidate.group_ids)
        ),
        None,
    )
    if rule is None:
        return refuse("subject_not_allowed")
    if event.action not in rule.actions:
        return refuse("action_not_allowed")
    if event.occurred_at > now:
        return refuse("event_from_future")
    expires_at = event.occurred_at + timedelta(seconds=policy.event_ttl_seconds)
    if now >= expires_at:
        return refuse("event_expired")
    if not event.question.strip():
        return refuse("question_empty")
    if len(event.question) > policy.max_question_chars:
        return refuse("question_too_large")
    try:
        event.question.encode("utf-8", errors="strict")
    except UnicodeError:
        return refuse("question_invalid")
    if any(ord(character) < _ASCII_CONTROL_LIMIT and character not in "\t\n\r" for character in event.question):
        return refuse("question_invalid")
    if event.action == "summarize_context" and policy.context_message_limit == 0:
        return refuse("context_disabled")
    return ReachDecision(
        allowed=True,
        reason="prepared",
        identity=identity,
        policy_digest=policy.digest,
        evaluated_at=now,
        prepared=PreparedReachTurn(
            policy_digest=policy.digest,
            identity=identity,
            event=event,
            rule_name=rule.name,
            action=event.action,
            prepared_at=now,
            expires_at=expires_at,
        ),
    )
