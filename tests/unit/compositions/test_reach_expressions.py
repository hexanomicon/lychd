"""Frozen expression choices reach native settlement without granting model destinations."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.conversation_workflow import conversation_prompt, parse_conversation_output
from lychd.compositions.reach.expressions import ConversationExpressions, ExpressionGif, validate_gif_url
from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile, canonical_json
from lychd.compositions.reach.operator_wire import ReachWorkerResult
from tests.unit.compositions.test_reach_conversation import completion, policy
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request

GIF = "https://media.giphy.com/media/Example123/giphy.gif"


def expressions() -> ConversationExpressions:
    return ConversationExpressions(
        enabled=True, gifs=(ExpressionGif(id="cheer", description="A cheerful celebration.", url=GIF),)
    )


def binding() -> OperatorConversationProfile:
    return OperatorConversationProfile(
        persona_name="Example Familiar",
        persona_instructions="Be helpful, with occasional warmth.",
        adaptive_context=True,
        expressions=expressions(),
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://media.giphy.com/media/Example123/giphy.gif",
        "https://media.giphy.com.evil.example/media/Example123/giphy.gif",
        "https://media.giphy.com@127.0.0.1/media/Example123/giphy.gif",
        "https://media.giphy.com/media/Example123/giphy.gif?query=private",
        "https://media.giphy.com/media/Example123/giphy.gif#fragment",
        "https://media.giphy.com/media/%2e%2e/giphy.gif",
        "https://media.giphy.com/media/Example123/giphy.mp4",
    ],
)
def test_gif_catalogue_rejects_noncanonical_destinations(url: str) -> None:
    with pytest.raises(ValueError, match="invalid_gif_url"):
        validate_gif_url(url)


def test_catalogue_is_opt_in_unique_and_bound_to_the_model_profile() -> None:
    configured = expressions()
    with pytest.raises(ValidationError, match="expression_catalogue"):
        ConversationExpressions(gifs=configured.gifs)
    with pytest.raises(ValidationError, match="expression_catalogue"):
        ConversationExpressions(enabled=True, gifs=configured.gifs * 2)
    with pytest.raises(ValidationError, match="expressions_require_adaptive_context"):
        OperatorConversationProfile(persona_name="Example", persona_instructions="Be helpful.", expressions=configured)
    original = binding()
    assert original.digest != original.model_copy(update={"expressions": ConversationExpressions()}).digest


def test_prompt_exposes_ids_and_descriptions_but_no_media_url_or_command_choices() -> None:
    request = make_request(action="converse")
    prompt = json.loads(conversation_prompt(binding(), make_corpus(), request))
    assert prompt["available_expressions"]["gifs"] == [{"id": "cheer", "description": "A cheerful celebration."}]
    assert "👍" in prompt["available_expressions"]["reactions"]
    assert GIF not in json.dumps(prompt)
    command = request.model_copy(update={"event": request.event.model_copy(update={"trigger": "command"})})
    prompt = json.loads(conversation_prompt(binding(), make_corpus(), command))
    assert prompt["available_expressions"] == {"reactions": [], "gifs": []}


@pytest.mark.parametrize(
    "decision",
    [
        {"kind": "answer", "text": "Hello.", "reaction": "🔥"},
        {"kind": "answer", "text": "Hello.", "gif_id": "unknown"},
        {"kind": "answer", "text": "Hello.", "gif_url": GIF},
        {"kind": "read_more", "text": "Earlier messages.", "reaction": "👍"},
        {"kind": "clarify", "text": "Which message?", "gif_id": "cheer"},
    ],
)
def test_forged_or_nonterminal_decorations_are_rejected(decision: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=r"conversation_expression|validation error"):
        parse_conversation_output(canonical_json(decision), expressions=expressions())


def test_disabled_expressions_refuse_choices_but_preserve_plain_answers() -> None:
    with pytest.raises(ValueError, match="conversation_expression"):
        parse_conversation_output(
            '{"kind":"answer","text":"Hello.","reaction":"👍"}',
        )
    result = parse_conversation_output(
        '{"kind":"answer","text":"Hello."}',
    )
    assert (result.status, result.text, result.reaction, result.gif_id) == ("conversation", "Hello.", None, None)
    with pytest.raises(ValidationError, match="result_expression"):
        ReachWorkerResult(
            request_id="request", status="need_context", reaction="👍", policy_digest="a" * 64, corpus_digest="b" * 64
        )


@pytest.mark.asyncio
async def test_native_run_settles_admitted_expression_ids_and_fences_replay() -> None:
    profile = binding()

    async def relay(operation: str, _payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [profile.model_id]})
        return completion('{"kind":"answer","text":"We did it!","reaction":"👍","gif_id":"cheer"}')

    runtime = build_runtime(
        policy(), make_corpus(), profile=profile, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        assert runtime.ready.expressions == profile.expressions
        with override_allow_model_requests(True):  # noqa: FBT003 - explicit third-party model permission
            result = await runtime.process(make_request(action="converse"))
            replay = await runtime.process(make_request(action="converse"))
        assert (result.status, result.text, result.reaction, result.gif_id) == (
            "conversation",
            "We did it!",
            "👍",
            "cheer",
        )
        assert result.model_binding_digest == profile.digest
        assert replay.reason == "duplicate"
        assert result.run_id is not None
        turn = await runtime.sessions.settled_turn_for_run(result.run_id)
        assert turn is not None
        assert turn.content == result.model_dump_json()
    finally:
        await runtime.aclose()
