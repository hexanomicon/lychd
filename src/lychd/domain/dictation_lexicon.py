"""Explicit approved vocabulary; pure suggestions and bounded owner-store contract.

Corrections never create rules. Matching is case-sensitive literal text, scoped
to one canonical language, and scans only original text; no replacement chains.
"""

from __future__ import annotations

import asyncio
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime, timedelta
from typing import Literal, Protocol, Self
from uuid import UUID, uuid4

from pydantic import Field, StrictStr, field_validator, model_validator

from lychd.domain.dictation import (
    MAX_TEXT_CHARS,
    DictationLexiconRuleRequest,
    DictationModel,
    Language,
    validate_text,
)

MAX_LEXICON_RULES = 128
DEFAULT_LEXICON_RETENTION_SECONDS = 604_800
MAX_LEXICON_RETENTION_SECONDS = 2_592_000


_MAX_OWNER_CHARS = 256


def _valid_owner(owner: object) -> bool:
    return isinstance(owner, str) and 1 <= len(owner) <= _MAX_OWNER_CHARS


class DictationLexiconError(ValueError):
    """Content-free operation refusal; text must not appear in diagnostics."""

    def __init__(self, reason: Literal["conflict", "capacity", "invalid", "expansion", "unavailable"]) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        self.reason = reason
        super().__init__(reason)


def validate_lexicon_time(now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        msg = "invalid"
        raise DictationLexiconError(msg)


def normalize_approval(request: DictationLexiconRuleRequest) -> DictationLexiconRuleRequest:
    """Canonicalize language case and Unicode NFC; preserve case and whitespace."""
    return DictationLexiconRuleRequest.model_validate(
        {
            **request.model_dump(),
            "language": request.language.lower(),
            "heard": unicodedata.normalize("NFC", request.heard),
            "replacement": unicodedata.normalize("NFC", request.replacement),
        }
    )


class DictationLexiconRule(DictationModel):
    id: UUID
    language: Language
    heard: StrictStr = Field(min_length=1, max_length=128, repr=False)
    replacement: StrictStr = Field(min_length=1, max_length=128, repr=False)
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        request = DictationLexiconRuleRequest(
            language=self.language,
            heard=self.heard,
            replacement=self.replacement,
            approved=True,
        )
        if normalize_approval(request) != request:
            msg = "invalid"
            raise DictationLexiconError(msg)
        validate_lexicon_time(self.created_at)
        validate_lexicon_time(self.expires_at)
        if not 0 < (self.expires_at - self.created_at).total_seconds() <= MAX_LEXICON_RETENTION_SECONDS:
            msg = "invalid"
            raise DictationLexiconError(msg)
        return self


class DictationSuggestionRequest(DictationModel):
    """Only the owned retained attempt identifies source text and language."""

    attempt_id: UUID


class DictationSuggestion(DictationModel):
    attempt_id: UUID
    language: Language
    original_text: StrictStr = Field(max_length=MAX_TEXT_CHARS, repr=False)
    suggested_text: StrictStr = Field(max_length=MAX_TEXT_CHARS, repr=False)
    applied_rule_ids: tuple[UUID, ...] = Field(max_length=MAX_LEXICON_RULES)
    rules: tuple[DictationLexiconRule, ...] = Field(max_length=MAX_LEXICON_RULES)

    @field_validator("original_text", "suggested_text")
    @classmethod
    def valid_text(cls, value: str) -> str:
        validate_text(value)
        return value


class DictationLexiconDeleted(DictationModel):
    rule_id: UUID
    deleted: Literal[True] = True


def _word(char: str) -> bool:
    # Include combining marks, which Python's Unicode regex \w omits.
    return char == "_" or char.isalnum() or unicodedata.category(char).startswith("M")


def suggest_dictation(
    *,
    attempt_id: UUID,
    original_text: str,
    language: str,
    rules: Sequence[DictationLexiconRule],
    now: datetime,
) -> DictationSuggestion:
    """Left-to-right, longest-at-position literal matching at Unicode word edges.

    Equal-length ties resolve by phrase then UUID, independent of database ordering.
    Applied IDs and visible rules are distinct in first-application order. Expired
    rules are ignored even if a caller retained a stale snapshot.
    """
    validate_lexicon_time(now)
    validate_text(original_text)
    if len(rules) > MAX_LEXICON_RULES:
        msg = "capacity"
        raise DictationLexiconError(msg)
    active = sorted(
        (DictationLexiconRule.model_validate(rule.model_dump()) for rule in rules),
        key=lambda rule: (-len(rule.heard), rule.heard, str(rule.id)),
    )
    active = [rule for rule in active if rule.language == language.lower() and rule.created_at <= now < rule.expires_at]
    pieces: list[str] = []
    applied: dict[UUID, DictationLexiconRule] = {}
    position = size = 0
    while position < len(original_text):
        matched = None
        if position == 0 or not _word(original_text[position - 1]):
            for rule in active:
                end = position + len(rule.heard)
                if original_text.startswith(rule.heard, position) and (
                    end == len(original_text) or not _word(original_text[end])
                ):
                    matched = rule
                    break
        if matched is None:
            piece = original_text[position]
            position += 1
        else:
            piece = matched.replacement
            position += len(matched.heard)
            applied.setdefault(matched.id, matched)
        size += len(piece)
        if size > MAX_TEXT_CHARS:
            msg = "expansion"
            raise DictationLexiconError(msg)
        pieces.append(piece)
    return DictationSuggestion(
        attempt_id=attempt_id,
        language=language,
        original_text=original_text,
        suggested_text="".join(pieces),
        applied_rule_ids=tuple(applied),
        rules=tuple(applied.values()),
    )


class DictationLexiconStore(Protocol):
    async def approve(
        self, owner: str, request: DictationLexiconRuleRequest, now: datetime
    ) -> DictationLexiconRule: ...
    async def list_rules(self, owner: str, now: datetime) -> tuple[DictationLexiconRule, ...]: ...
    async def delete(self, owner: str, rule_id: UUID, now: datetime) -> None: ...
    async def purge(self, now: datetime) -> None: ...


class DictationLexiconOperations(ABC):
    """Shared decisions executed only within an adapter's atomic owner transaction."""

    def __init__(self, *, retention_seconds: int = DEFAULT_LEXICON_RETENTION_SECONDS) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        if type(retention_seconds) is not int or not 0 < retention_seconds <= MAX_LEXICON_RETENTION_SECONDS:
            msg = "invalid"
            raise DictationLexiconError(msg)
        self._retention_seconds = retention_seconds

    @abstractmethod
    def _records(self, owner: str) -> AbstractAsyncContextManager[dict[UUID, DictationLexiconRule]]: ...

    def _current_time(self, supplied: datetime) -> datetime:
        """Memory fixtures use supplied time; durable adapters own a fresh clock."""
        return supplied

    @asynccontextmanager
    async def _working(
        self,
        owner: str,
        now: datetime,
    ) -> AsyncGenerator[tuple[dict[UUID, DictationLexiconRule], datetime]]:
        validate_lexicon_time(now)
        if not _valid_owner(owner):
            msg = "invalid"
            raise DictationLexiconError(msg)
        async with self._records(owner) as rules:
            now = self._current_time(now)
            validate_lexicon_time(now)
            for rule_id, rule in tuple(rules.items()):
                if rule.expires_at <= now:
                    del rules[rule_id]
            if len(rules) > MAX_LEXICON_RULES:
                msg = "capacity"
                raise DictationLexiconError(msg)
            yield rules, now

    async def approve(self, owner: str, request: DictationLexiconRuleRequest, now: datetime) -> DictationLexiconRule:
        request = normalize_approval(request)
        async with self._working(owner, now) as (rules, current_time):
            for rule in rules.values():
                if (rule.language, rule.heard) == (request.language, request.heard):
                    if rule.replacement != request.replacement:
                        msg = "conflict"
                        raise DictationLexiconError(msg)
                    break
            else:
                if len(rules) >= MAX_LEXICON_RULES:
                    msg = "capacity"
                    raise DictationLexiconError(msg)
                rule = DictationLexiconRule(
                    id=uuid4(),
                    language=request.language,
                    heard=request.heard,
                    replacement=request.replacement,
                    created_at=current_time,
                    expires_at=current_time + timedelta(seconds=self._retention_seconds),
                )
                rules[rule.id] = rule
        if self._current_time(current_time) >= rule.expires_at:
            msg = "unavailable"
            raise DictationLexiconError(msg)
        return rule

    async def list_rules(self, owner: str, now: datetime) -> tuple[DictationLexiconRule, ...]:
        async with self._working(owner, now) as (rules, current_time):
            retained = tuple(sorted(rules.values(), key=lambda rule: (rule.created_at, str(rule.id))))
        current = self._current_time(current_time)
        return tuple(rule for rule in retained if current < rule.expires_at)

    async def delete(self, owner: str, rule_id: UUID, now: datetime) -> None:
        async with self._working(owner, now) as (rules, _now):
            rules.pop(rule_id, None)

    @abstractmethod
    async def purge(self, now: datetime) -> None: ...


class MemoryDictationLexiconStore(DictationLexiconOperations):
    """Fixture-only process memory, with rollback and serialized quota admission."""

    def __init__(self, *, retention_seconds: int = DEFAULT_LEXICON_RETENTION_SECONDS) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        super().__init__(retention_seconds=retention_seconds)
        self._owners: dict[str, dict[UUID, DictationLexiconRule]] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def _records(self, owner: str) -> AsyncGenerator[dict[UUID, DictationLexiconRule]]:
        async with self._lock:
            rules = self._owners.get(owner, {}).copy()
            yield rules
            if rules:
                self._owners[owner] = rules
            else:
                self._owners.pop(owner, None)

    async def purge(self, now: datetime) -> None:
        validate_lexicon_time(now)
        for owner in tuple(self._owners):
            async with self._working(owner, now):
                pass
