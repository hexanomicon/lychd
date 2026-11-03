"""Owner-scoped lexicon operations over injected stores; no training or inference."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from lychd.domain.dictation import DictationLexiconRuleRequest
from lychd.domain.dictation_lexicon import (
    DictationLexiconDeleted,
    DictationLexiconError,
    DictationLexiconRule,
    DictationLexiconStore,
    DictationSuggestion,
    DictationSuggestionRequest,
    suggest_dictation,
)
from lychd.domain.dictation_store import DictationStore


def _now() -> datetime:
    return datetime.now(UTC)


class DictationLexiconService:
    def __init__(
        self,
        *,
        store: DictationLexiconStore,
        attempts: DictationStore,
        now: Callable[[], datetime] = _now,
    ) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        self.store = store
        self.attempts = attempts
        self._now = now

    async def list_rules(self, owner: str) -> tuple[DictationLexiconRule, ...]:
        return await self.store.list_rules(owner, self._now())

    async def approve(self, owner: str, request: DictationLexiconRuleRequest) -> DictationLexiconRule:
        return await self.store.approve(owner, request, self._now())

    async def delete(self, owner: str, rule_id: UUID) -> DictationLexiconDeleted:
        await self.store.delete(owner, rule_id, self._now())
        # Absent and foreign IDs have the same idempotent projection.
        return DictationLexiconDeleted(rule_id=rule_id)

    async def suggest(
        self,
        owner: str,
        request: DictationSuggestionRequest,
        *,
        authorize: Callable[[], None],
    ) -> DictationSuggestion:
        authorize()
        rules = await self.store.list_rules(owner, self._now())
        authorize()
        result = await self.attempts.get_result(owner, request.attempt_id, self._now())
        authorize()
        if result is None or result.status != "transcribed" or result.original_text is None:
            msg = "unavailable"
            raise DictationLexiconError(msg)
        return suggest_dictation(
            attempt_id=result.attempt_id,
            original_text=result.original_text,
            language=result.language,
            rules=rules,
            now=self._now(),
        )

    async def purge(self) -> None:
        await self.store.purge(self._now())
