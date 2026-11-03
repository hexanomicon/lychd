"""Synthetic approval, retention and original-only matching invariants."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from lychd.domain.dictation import DictationCorrectionRequest, DictationLexiconRuleRequest
from lychd.domain.dictation_lexicon import (
    DictationLexiconError,
    DictationLexiconRule,
    DictationSuggestion,
    DictationSuggestionRequest,
    MemoryDictationLexiconStore,
    suggest_dictation,
)
from lychd.domain.dictation_lexicon_service import DictationLexiconService
from lychd.domain.dictation_store import MemoryDictationStore
from tests.unit.domain.test_dictation_store import identity, profile, result, wav

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def approval(heard: str = "lich", replacement: str = "LychD", language: str = "en") -> DictationLexiconRuleRequest:
    return DictationLexiconRuleRequest(language=language, heard=heard, replacement=replacement, approved=True)


def rule(heard: str, replacement: str, language: str = "en", identifier: int = 1) -> DictationLexiconRule:
    return DictationLexiconRule(
        id=UUID(int=identifier),
        language=language,
        heard=heard,
        replacement=replacement,
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
    )


def suggestion(text: str, rules: list[DictationLexiconRule], language: str = "en") -> DictationSuggestion:
    return suggest_dictation(attempt_id=UUID(int=99), original_text=text, language=language, rules=rules, now=NOW)


def test_longest_literal_boundaries_and_original_only_no_chaining() -> None:
    rules = [rule("new", "short"), rule("new york", "NY", identifier=2), rule("NY", "chained", identifier=3)]
    actual = suggestion("new york; new. renewal NY", rules)
    assert actual.original_text == "new york; new. renewal NY"
    assert actual.suggested_text == "NY; short. renewal chained"
    assert actual.applied_rule_ids == (UUID(int=2), UUID(int=1), UUID(int=3))
    assert tuple(item.id for item in actual.rules) == actual.applied_rule_ids


def test_unicode_word_edges_literal_metacharacters_and_exact_language() -> None:
    actual = suggestion(
        "猫 猫咪 é élan e\u0301 (a+b) A+B",
        [
            rule("猫", "cat"),
            rule("é", "e", identifier=2),
            rule("e", "E", identifier=3),
            rule("a+b", "sum", identifier=4),
            rule("élan", "wrong language", language="fr", identifier=5),
        ],
    )
    assert actual.suggested_text == "cat 猫咪 e élan e\u0301 (sum) A+B"
    assert suggestion("lich", [rule("lich", "LychD", language="en-us")], language="en").suggested_text == "lich"


def test_stable_ties_expiry_and_empty_text() -> None:
    a, b = rule("a", "first"), rule("a", "second", identifier=2)
    assert suggestion("a a", [b, a]) == suggestion("a a", [a, b])
    assert suggestion("a a", [a, b]).applied_rule_ids == (a.id,)
    expired = a.model_copy(update={"created_at": NOW - timedelta(days=7), "expires_at": NOW})
    assert suggestion("a", [expired]).suggested_text == "a"
    assert suggestion("", [a]).suggested_text == ""


def test_input_rule_and_expansion_bounds() -> None:
    with pytest.raises(ValueError, match=r"^Invalid transcript text\.$"):
        suggestion("x" * 8193, [])
    with pytest.raises(DictationLexiconError, match="capacity"):
        suggestion("a", [rule("a", "b", identifier=i + 1) for i in range(129)])
    with pytest.raises(DictationLexiconError, match="expansion"):
        suggestion("a " * 4096, [rule("a", "b" * 128)])
    with pytest.raises(ValidationError):
        approval("a" * 129)
    with pytest.raises(ValidationError):
        DictationLexiconRuleRequest.model_validate(
            {"language": "en", "heard": "a", "replacement": "b", "approved": False}
        )
    with pytest.raises(ValidationError):
        DictationSuggestionRequest.model_validate({"attempt_id": uuid4(), "original_text": "browser source"})


@pytest.mark.asyncio
async def test_exact_normalized_retry_preserves_id_and_deadline_and_change_conflicts() -> None:
    store = MemoryDictationLexiconStore()
    first = await store.approve("alice", approval("cafe\u0301", "Café", "en-US"), NOW)
    retry = await store.approve("alice", approval("café", "Café", "en-us"), NOW + timedelta(days=1))
    assert first == retry
    assert first.expires_at == NOW + timedelta(days=7)
    with pytest.raises(DictationLexiconError, match="conflict"):
        await store.approve("alice", approval("café", "Coffee", "en-us"), NOW)
    await store.delete("bob", first.id, NOW)
    assert await store.list_rules("bob", NOW) == ()
    assert await store.list_rules("alice", NOW) == (first,)
    await store.delete("alice", first.id, NOW)
    assert (await store.approve("alice", approval("café", "Coffee", "en-us"), NOW)).id != first.id


@pytest.mark.asyncio
async def test_atomic_quota_parallel_approvals_and_expiry() -> None:
    store = MemoryDictationLexiconStore(retention_seconds=1)
    duplicates = await asyncio.gather(*(store.approve("alice", approval(), NOW) for _ in range(10)))
    assert len({item.id for item in duplicates}) == 1
    results = await asyncio.gather(
        *(store.approve("alice", approval(f"word{i}"), NOW) for i in range(128)), return_exceptions=True
    )
    assert sum(isinstance(item, DictationLexiconError) for item in results) == 1
    assert len(await store.list_rules("alice", NOW)) == 128
    assert await store.list_rules("alice", NOW + timedelta(seconds=1)) == ()
    await store.approve("bob", approval(), NOW)
    await store.purge(NOW + timedelta(seconds=1))
    assert not store._owners  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test


@pytest.mark.parametrize("seconds", [0, -1, 2_592_001, True])
def test_invalid_retention_refused(seconds: int) -> None:
    with pytest.raises(DictationLexiconError, match="invalid"):
        MemoryDictationLexiconStore(retention_seconds=seconds)


@pytest.mark.asyncio
async def test_service_loads_owned_original_and_corrections_never_train() -> None:
    attempts, p = MemoryDictationStore(), profile()
    owned = identity(p)
    await attempts.claim(owned, wav(), NOW, p)
    await attempts.settle(owned, result(owned, "lich"), NOW)
    await attempts.correct("alice", DictationCorrectionRequest(attempt_id=owned.attempt_id, final_text="edited"), NOW)
    store = MemoryDictationLexiconStore()
    service = DictationLexiconService(store=store, attempts=attempts, now=lambda: NOW)
    request = DictationSuggestionRequest(attempt_id=owned.attempt_id)
    assert await service.list_rules("alice") == ()
    approved = await service.approve("alice", approval())
    actual = await service.suggest("alice", request, authorize=lambda: None)
    assert actual.original_text == "lich"
    assert actual.suggested_text == "LychD"
    assert actual.rules == (approved,)
    with pytest.raises(DictationLexiconError, match="unavailable"):
        await service.suggest("bob", request, authorize=lambda: None)
    await attempts.delete("alice", owned.attempt_id, NOW)
    with pytest.raises(DictationLexiconError, match="unavailable"):
        await service.suggest("alice", request, authorize=lambda: None)
