"""Offline contract tests for reviewed companion dialogue.

Candidate by dialogue_cases_candidate for blockworld-dialogue-20261027.
The async store below owns only in-memory values; no game, model or database runs.
"""

from dataclasses import replace
from typing import Any

import pytest

from lychd.compositions.blockworld.companion import CompanionRequest, CompanionResult, FollowAction, parse_text
from lychd.compositions.blockworld.companion_dialogue import (
    CompanionDialogue,
    ConfirmationMode,
    DialogueContext,
    DialogueDecision,
)
from lychd.compositions.blockworld.companion_memory import CommandRecipe, phrase_key

REQUEST = "10000000-0000-4000-8000-000000000001"
REPLY = "10000000-0000-4000-8000-000000000002"
FRESH = "10000000-0000-4000-8000-000000000003"
RUN = "10000000-0000-4000-8000-000000000004"
TARGET = "20000000-0000-4000-8000-000000000001"
OTHER_TARGET = "20000000-0000-4000-8000-000000000002"


class MemoryStore:
    """Async RecipeStore substitute with observable writes and no external effects."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], CommandRecipe] = {}
        self.saved: list[CommandRecipe] = []
        self.finds: list[tuple[str, str]] = []
        self.fail_find = False
        self.fail_remember = False

    async def find(self, language: str, phrase: str) -> CommandRecipe | None:
        self.finds.append((language, phrase))
        if self.fail_find:
            msg = "storage unavailable"
            raise RuntimeError(msg)
        return self.values.get((language, phrase))

    async def remember(self, recipe: CommandRecipe) -> None:
        self.saved.append(recipe)
        if self.fail_remember:
            msg = "commit unknown"
            raise RuntimeError(msg)
        self.values[(recipe.language, recipe.phrase)] = recipe

    async def forget(self, language: str, phrase: str) -> bool:
        return self.values.pop((language, phrase), None) is not None


def context(**changes: object) -> DialogueContext:
    return replace(
        DialogueContext(REQUEST, 7, TARGET, 10_000, source="transcript"),
        **changes,
    )


async def receive(
    dialogue: CompanionDialogue, text: str, stamp: DialogueContext, language: Any, *, now_ms: int
) -> DialogueDecision:
    # A fresh gesture captures the current question. Stale-input tests call the
    # production API directly with the earlier stamp instead.
    return await dialogue.receive(text, replace(stamp, question_revision=dialogue.revision), language, now_ms=now_ms)


def remembered(phrase: str = "walk beside me", command: str = "follow me", *, skip: bool = True) -> CommandRecipe:
    return CommandRecipe(
        language="en",
        phrase=phrase,
        command=command,
        skip_confirmation=skip,
        learned_request_id=REQUEST,
        learned_run_id=RUN,
    )


def applied(request: CompanionRequest, **changes: object) -> CompanionResult:
    return CompanionResult.model_validate(
        {"request_id": request.request_id, "kind": "applied", "detail": "", **changes}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "yes", "skip"),
    [
        ("sk", "áno", "áno bez potvrdenia"),
        ("cs", "ano", "ano bez potvrzení"),
        ("en", "yes", "yes without confirmation"),
    ],
)
async def test_reviewed_alias_journey_preserves_capture_and_creates_fresh_reuse(  # noqa: PLR0915 - one full user journey
    language: str, yes: str, skip: str
) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    original = context()
    first = await receive(dialogue, "  Walk beside me  ", original, language, now_ms=100)
    assert first.phase == "choose"
    assert first.request is None
    assert "follow me" in first.text
    # Selection and affirmative replies have their own IDs/deadlines. They cannot
    # replace the capture whose concrete action is now being resolved.
    later = context(request_id=REPLY, expires_at_ms=50_000)
    selection = await receive(dialogue, "follow me", later, language, now_ms=200)
    assert selection.phase == "confirm"
    assert "follow me" in selection.text
    assert selection.request is None
    execution = await receive(dialogue, yes, later, language, now_ms=300)
    assert execution.phase == "execute"
    request = execution.request
    assert request is not None
    assert request.request_id == original.request_id
    assert request.expires_at_ms == original.expires_at_ms
    assert request.generation == original.generation
    assert request.source == "transcript"
    assert request.source_artifacts == original.source_artifacts
    assert request.transcript == "  Walk beside me  "
    assert isinstance(request.action, FollowAction)
    assert request.action.target_id == TARGET
    assert store.saved == []
    review = dialogue.complete(request, applied(request), RUN, now_ms=400)
    assert review is not None
    assert review.phase == "review"
    assert store.saved == []
    remember = await receive(dialogue, yes, later, language, now_ms=500)
    assert remember.phase == "remember"
    assert store.saved == []
    saved = await receive(dialogue, skip, later, language, now_ms=600)
    assert saved.phase == "remembered"
    assert len(store.saved) == 1
    recipe = store.saved[0]
    assert recipe.phrase == "walk beside me"
    assert recipe.language == language
    assert recipe.command == "follow me"
    assert recipe.skip_confirmation is True
    assert recipe.learned_request_id == original.request_id
    assert recipe.learned_run_id == RUN
    assert TARGET not in recipe.command
    fresh = context(request_id=FRESH, target_id=OTHER_TARGET, generation=8, expires_at_ms=30_000)
    reused = await receive(dialogue, "WALK BESIDE ME", fresh, language, now_ms=700)
    assert reused.phase == "execute"
    assert reused.request is not None
    assert reused.request.request_id == FRESH
    assert reused.request.generation == 8
    assert reused.request.expires_at_ms == 30_000
    assert isinstance(reused.request.action, FollowAction)
    assert reused.request.action.target_id == OTHER_TARGET
    assert len(store.saved) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["always", "unremembered", "never"])
@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("skip", [False, True])
async def test_effect_confirmation_modes(mode: ConfirmationMode, *, cached: bool, skip: bool) -> None:
    store = MemoryStore()
    if cached:
        store.values[("en", "idle")] = remembered("idle", "idle", skip=skip)
    dialogue = CompanionDialogue(store, confirmation=mode)
    decision = await receive(dialogue, "idle", context(), "en", now_ms=100)
    bypass = mode == "never" or (mode == "unremembered" and cached and skip)
    assert decision.phase == ("execute" if bypass else "confirm")
    assert (decision.request is not None) is bypass
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["always", "unremembered", "never"])
@pytest.mark.parametrize("command", ["state", "inspect 1 2 3"])
async def test_read_only_actions_need_no_effect_confirmation(mode: ConfirmationMode, command: str) -> None:
    dialogue = CompanionDialogue(MemoryStore(), confirmation=mode)
    decision = await receive(dialogue, command, context(), "en", now_ms=100)
    assert decision.phase == "execute"
    assert decision.request is not None
    assert decision.request.action == parse_text(command)


@pytest.mark.asyncio
@pytest.mark.parametrize("opening", ["options", "a little rest please"])
async def test_never_mode_also_applies_after_catalogue_selection(opening: str) -> None:
    dialogue = CompanionDialogue(MemoryStore(), confirmation="never")
    assert (await receive(dialogue, opening, context(), "en", now_ms=100)).phase == "choose"
    decision = await receive(dialogue, "idle", context(request_id=REPLY), "en", now_ms=200)
    assert decision.phase == "execute"
    assert decision.request is not None
    assert decision.request.request_id == REQUEST
    assert decision.request.expires_at_ms == 10_000


@pytest.mark.asyncio
@pytest.mark.parametrize(("language", "yes"), [("sk", "ÁNO!"), ("cs", "ano."), ("en", " YES? ")])
async def test_unambiguous_localized_affirmation_executes_frozen_proposal(language: str, yes: str) -> None:
    dialogue = CompanionDialogue(MemoryStore())
    assert (await receive(dialogue, "idle", context(), language, now_ms=100)).phase == "confirm"
    decision = await receive(dialogue, yes, context(request_id=REPLY), language, now_ms=200)
    assert decision.phase == "execute"
    assert decision.request is not None
    assert decision.request.request_id == REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["yes please", "okay", "yes without confirmation", "áno bez potvrdenia"])
async def test_confirmation_never_infers_or_accepts_skip_as_effect_approval(reply: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    await receive(dialogue, "idle", context(), "en", now_ms=100)
    decision = await receive(dialogue, reply, context(request_id=REPLY), "en", now_ms=200)
    assert decision.phase != "execute"
    assert decision.request is None
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("language", "no"), [("sk", "nie"), ("cs", "ne"), ("en", "no"), ("sk", "zruš")])
@pytest.mark.parametrize("stage", ["choose", "confirm", "review", "remember"])
async def test_negative_reply_discards_every_question_without_learning(language: str, no: str, stage: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    if stage == "choose":
        await receive(dialogue, "options", context(), language, now_ms=100)
    else:
        await receive(dialogue, "idle", context(), language, now_ms=100)
        if stage in {"review", "remember"}:
            execution = await receive(dialogue, "yes", context(request_id=REPLY), language, now_ms=200)
            assert execution.request is not None
            dialogue.complete(execution.request, applied(execution.request), RUN, now_ms=300)
            if stage == "remember":
                await receive(dialogue, "yes", context(request_id=REPLY), language, now_ms=400)
    cancelled = await receive(dialogue, no, context(request_id=REPLY), language, now_ms=500)
    assert cancelled.phase == "cancelled"
    assert cancelled.request is None
    stale = await receive(dialogue, "yes", context(request_id=FRESH), language, now_ms=600)
    assert stale.phase == "no_proposal"
    assert stale.request is None
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["expiry", "generation", "target", "language"])
@pytest.mark.parametrize("stage", ["choose", "confirm", "review", "remember"])
async def test_changed_or_expired_context_discards_question(change: str, stage: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    if stage == "choose":
        await receive(dialogue, "options", context(), "en", now_ms=100)
    else:
        await receive(dialogue, "idle", context(), "en", now_ms=100)
        if stage in {"review", "remember"}:
            execution = await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=200)
            assert execution.request is not None
            dialogue.complete(execution.request, applied(execution.request), RUN, now_ms=300)
            if stage == "remember":
                await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=400)
    now = 61_000 if change == "expiry" else 500
    changed = context(request_id=FRESH, expires_at_ms=100_000)
    if change == "generation":
        changed = replace(changed, generation=8)
    if change == "target":
        changed = replace(changed, target_id=OTHER_TARGET)
    language = "sk" if change == "language" else "en"
    decision = await receive(dialogue, "yes", changed, language, now_ms=now)
    assert decision.phase == "no_proposal"
    assert decision.request is None
    assert store.saved == []


@pytest.mark.asyncio
async def test_expired_incoming_instruction_is_rejected() -> None:
    dialogue = CompanionDialogue(MemoryStore())
    with pytest.raises(ValueError, match="expired"):
        await receive(dialogue, "idle", context(expires_at_ms=100), "en", now_ms=100)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["choose", "confirm", "executing", "review", "remember"])
async def test_stop_cancel_makes_old_answers_and_late_receipts_inert(stage: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    request = None
    if stage == "choose":
        await receive(dialogue, "options", context(), "en", now_ms=100)
    else:
        await receive(dialogue, "idle", context(), "en", now_ms=100)
        if stage in {"executing", "review", "remember"}:
            execution = await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=200)
            request = execution.request
            assert request is not None
            if stage in {"review", "remember"}:
                dialogue.complete(request, applied(request), RUN, now_ms=300)
            if stage == "remember":
                await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=400)
    dialogue.cancel()
    if request is not None:
        assert dialogue.complete(request, applied(request), RUN, now_ms=500) is None
    decision = await receive(dialogue, "yes", context(request_id=FRESH, generation=8), "en", now_ms=600)
    assert decision.phase == "no_proposal"
    assert decision.request is None
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["refused", "expired", "cancelled", "unknown", "no_action", "clarification"])
async def test_every_nonapplied_result_is_terminal_and_never_teaches(kind: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, confirmation="never")
    decision = await receive(dialogue, "idle", context(), "en", now_ms=100)
    request = decision.request
    assert request is not None
    assert dialogue.complete(request, applied(request, kind=kind), RUN, now_ms=200) is None
    assert (await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=300)).phase == "no_proposal"
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["result", "run", "result_identity"])
async def test_absent_or_uncorrelated_receipt_never_offers_review(missing: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, confirmation="never")
    execution = await receive(dialogue, "idle", context(), "en", now_ms=100)
    request = execution.request
    assert request is not None
    result = None if missing == "result" else applied(request)
    if missing == "result_identity":
        result = applied(request, request_id=FRESH)
    review = dialogue.complete(request, result, None if missing == "run" else RUN, now_ms=200)
    assert review is None
    assert (await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=300)).phase == "no_proposal"
    assert store.saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["request_id", "action", "generation", "deadline", "transcript"])
async def test_completion_must_match_entire_frozen_execution(changed: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, confirmation="never")
    execution = await receive(dialogue, "idle", context(), "en", now_ms=100)
    request = execution.request
    assert request is not None
    changes = {
        "request_id": {"request_id": FRESH},
        "action": {"action": parse_text("state")},
        "generation": {"generation": 8},
        "deadline": {"expires_at_ms": 20_000},
        "transcript": {"transcript": "a different instruction"},
    }
    foreign = CompanionRequest.model_validate({**request.model_dump(), **changes[changed]})
    assert dialogue.complete(foreign, applied(foreign), RUN, now_ms=200) is None
    assert store.saved == []


@pytest.mark.asyncio
async def test_duplicate_applied_completion_and_yes_do_not_repeat_writes() -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, confirmation="never")
    execution = await receive(dialogue, "idle", context(), "en", now_ms=100)
    request = execution.request
    assert request is not None
    assert dialogue.complete(request, applied(request), RUN, now_ms=200) is not None
    assert dialogue.complete(request, applied(request), RUN, now_ms=201) is None
    assert (await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=300)).phase == "remember"
    assert (await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=400)).phase == "remembered"
    assert store.saved[0].skip_confirmation is False
    assert (await receive(dialogue, "yes", context(request_id=FRESH), "en", now_ms=500)).phase == "no_proposal"
    assert len(store.saved) == 1


@pytest.mark.asyncio
async def test_unknown_memory_write_is_consumed_and_not_retried_by_another_yes() -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, confirmation="never")
    execution = await receive(dialogue, "idle", context(), "en", now_ms=100)
    assert execution.request is not None
    dialogue.complete(execution.request, applied(execution.request), RUN, now_ms=200)
    await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=300)
    store.fail_remember = True
    with pytest.raises(RuntimeError, match="commit unknown"):
        await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=400)
    assert (await receive(dialogue, "yes", context(request_id=FRESH), "en", now_ms=500)).phase == "no_proposal"
    assert len(store.saved) == 1


@pytest.mark.asyncio
async def test_memory_read_failure_is_not_relabelled_as_cache_miss() -> None:
    store = MemoryStore()
    store.fail_find = True
    dialogue = CompanionDialogue(store)
    with pytest.raises(RuntimeError, match="storage unavailable"):
        await receive(dialogue, "walk beside me", context(), "en", now_ms=100)
    assert store.saved == []


@pytest.mark.parametrize(("phrase", "command"), [("idle", "state"), ("state", "idle"), ("čas noc", "time day")])
def test_recipe_cannot_shadow_any_exact_native_command(phrase: str, command: str) -> None:
    with pytest.raises(ValueError, match="redefine"):
        remembered(phrase, command)


@pytest.mark.asyncio
async def test_forged_recipe_instance_is_revalidated_before_recall() -> None:
    store = MemoryStore()
    store.values[("en", "idle")] = remembered("idle", "idle").model_copy(update={"command": "state"})
    dialogue = CompanionDialogue(store)
    with pytest.raises(ValueError, match=r"Recipe|Phrase|recipe|phrase|validation"):
        await receive(dialogue, "idle", context(), "en", now_ms=100)
    assert store.saved == []


@pytest.mark.asyncio
async def test_lookup_cannot_change_language_or_phrase_binding() -> None:
    class WrongBindingStore(MemoryStore):
        async def find(self, language: str, phrase: str) -> CommandRecipe | None:
            del language, phrase
            return remembered("another phrase", "idle")

    dialogue = CompanionDialogue(WrongBindingStore())
    with pytest.raises(ValueError, match="different binding"):
        await receive(dialogue, "walk beside me", context(), "en", now_ms=100)


@pytest.mark.parametrize("command", [f"follow {TARGET}", f"nasleduj {TARGET}"])
def test_saved_command_cannot_retain_player_uuid(command: str) -> None:
    with pytest.raises(ValueError, match="player identity"):
        remembered("walk beside me", command)


@pytest.mark.asyncio
@pytest.mark.parametrize("bound_target", [TARGET, None])
async def test_strict_explicit_player_identity_is_not_rebound_by_dialogue(bound_target: str | None) -> None:
    dialogue = CompanionDialogue(MemoryStore(), confirmation="never")
    command = f"follow {OTHER_TARGET}"
    decision = await receive(dialogue, command, context(target_id=bound_target), "en", now_ms=100)
    assert decision.phase == "execute"
    assert decision.request is not None
    assert decision.request.action == parse_text(command, target_id=bound_target)
    assert isinstance(decision.request.action, FollowAction)
    assert decision.request.action.target_id == OTHER_TARGET


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "phrase"),
    [("en", "structures"), ("sk", "štruktúru"), ("cs", "strukturu"), ("en", "summon zombie"), ("en", "/summon zombie")],
)
async def test_unsupported_structure_or_summon_never_invents_choices(language: str, phrase: str) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store)
    decision = await receive(dialogue, phrase, context(), language, now_ms=100)
    assert decision.phase == "unavailable"
    assert decision.request is None
    assert store.saved == []
    assert store.finds == []
    assert (await receive(dialogue, "yes", context(request_id=REPLY), language, now_ms=200)).phase == "no_proposal"


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_catalogue_reflects_explicit_environment_permissions(*, enabled: bool) -> None:
    store = MemoryStore()
    dialogue = CompanionDialogue(store, allow_weather=enabled, allow_time=enabled)
    menu = await receive(dialogue, "options", context(target_id=None), "en", now_ms=100)
    assert menu.phase == "choose"
    assert menu.request is None
    assert "state" in menu.text
    assert "idle" in menu.text
    assert "follow me" not in menu.text
    assert ("weather rain" in menu.text) is enabled
    assert ("time toggle" in menu.text) is enabled
    dialogue.cancel()
    for command in ("weather rain", "time toggle"):
        decision = await receive(dialogue, command, context(), "en", now_ms=200)
        assert decision.phase == ("confirm" if enabled else "disabled")
        assert decision.request is None
        dialogue.cancel()


@pytest.mark.parametrize(
    "phrase", ["yes", "áno", "ano", "no", "nie", "ne", "stop", "stůj", "/summon zombie", ":target x", "x\ny"]
)
def test_reserved_or_control_phrases_never_become_aliases(phrase: str) -> None:
    with pytest.raises(ValueError, match=r"Recipe|Phrase|recipe|phrase|validation"):
        phrase_key(phrase)


def test_phrase_normalization_is_exact_and_keeps_language_sensitive_spelling() -> None:
    assert phrase_key("  A\u0301NO BESIDE ME  ") == "áno beside me"
    assert phrase_key("walk beside me!") != phrase_key("walk beside me")
    assert phrase_key("dážď") != phrase_key("dazd")


@pytest.mark.asyncio
async def test_delayed_yes_cannot_confirm_a_replacement_question() -> None:
    dialogue = CompanionDialogue(MemoryStore())
    await receive(dialogue, "idle", context(), "en", now_ms=100)
    old_answer = replace(context(request_id=REPLY), question_revision=dialogue.revision)
    await receive(dialogue, "follow me", context(request_id=FRESH), "en", now_ms=200)
    stale = await dialogue.receive("yes", old_answer, "en", now_ms=300)
    assert stale.phase == "stale_question"
    assert stale.request is None
    fresh = await receive(dialogue, "yes", context(request_id=REPLY), "en", now_ms=400)
    assert fresh.request is not None
    assert fresh.request.action.kind == "follow"


@pytest.mark.asyncio
async def test_reusing_a_reviewed_phrase_does_not_ask_to_learn_it_again() -> None:
    store = MemoryStore()
    store.values[("en", "idle")] = remembered("idle", "idle")
    dialogue = CompanionDialogue(store)
    execution = await receive(dialogue, "idle", context(), "en", now_ms=100)
    assert execution.request is not None
    assert dialogue.complete(execution.request, applied(execution.request), RUN, now_ms=200) is None


@pytest.mark.asyncio
async def test_reply_language_is_independent_of_recipe_matching_language() -> None:
    dialogue = CompanionDialogue(MemoryStore(), response_language="sk")
    decision = await receive(dialogue, "idle", context(), "en", now_ms=100)
    assert decision.text.startswith("Pochopil som správne")
    assert decision.phase == "confirm"
