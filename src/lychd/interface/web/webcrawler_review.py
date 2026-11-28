"""Current authenticated native review for retained Webcrawler preparation custody."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from lychd.domain.scout.authority import ScoutAction
from lychd.domain.web.consent_reviews import (
    ConsentReviewForbiddenError,
    ConsentReviewUnavailableError,
    NativeReviewResolution,
)
from lychd.domain.webcrawler.review import webcrawler_review

if TYPE_CHECKING:
    from lychd.db.webcrawler import DbWebcrawlerAttemptStore
    from lychd.domain.codex.local_access import LocalOperatorAccess
    from lychd.domain.codex.schemas import ConsentView
    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.scout.authority import ScoutHostAuthorizer
    from lychd.domain.web.consent_reviews import ConsentReviewProducer


class WebcrawlerConsentReviews:
    """Route exact Webcrawler ownership and validate its actual request marker last."""

    def __init__(
        self,
        *,
        access: LocalOperatorAccess,
        authorizer: ScoutHostAuthorizer,
        store: DbWebcrawlerAttemptStore,
        other: ConsentReviewProducer | None = None,
    ) -> None:
        """Keep owner-specific authority separate from other native producers."""
        self._access, self._authorizer, self._store, self._other = access, authorizer, store, other

    async def resolve(
        self,
        *,
        consent: ConsentView,
        reviewer: Sigil,
        purpose: Literal["view", "decide"],
        authentication: object | None = None,
    ) -> NativeReviewResolution:
        """Reproduce retained review and recheck possession after database waits."""
        native = consent.native_binding
        if native is None or native.owner not in {"webcrawler", "scout"}:
            if self._other is None:
                raise ConsentReviewUnavailableError
            return await self._other.resolve(
                consent=consent, reviewer=reviewer, purpose=purpose, authentication=authentication
            )
        if not self._access.current(authentication):
            raise ConsentReviewForbiddenError
        snapshot = await self._store.read(UUID(native.action_id))
        p = snapshot.preparation
        expected, document = webcrawler_review(p, legacy=native.owner == "scout")
        if (
            snapshot.native_binding != native
            or expected != native
            or consent.tool_name != f"{native.owner}.fetch_extract"
            or consent.id != str(snapshot.consent_id)
            or consent.run_id != str(p.run_id)
            or reviewer.name != p.sigil_name
        ):
            raise ConsentReviewUnavailableError
        if not self._access.current(authentication) or not self._authorizer.authorize(ScoutAction.REVIEW, p).allowed:
            raise ConsentReviewForbiddenError
        allowed = self._authorizer.authorize(ScoutAction.JUDGE, p).allowed
        if purpose == "decide" and not allowed:
            raise ConsentReviewForbiddenError
        return NativeReviewResolution(binding=native, document=document, decision_allowed=allowed)
