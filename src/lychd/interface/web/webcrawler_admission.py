"""Authenticated Bridge declaration and current admission for one public page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.scout.attempts import LocatorInfluence, LocatorSource, PublicLocatorDeclaration
from lychd.domain.scout.authority import ScoutHostAuthorizer
from lychd.domain.scout.transport import FetchError
from lychd.domain.webcrawler.profile import (
    WEBCRAWLER_ANSWER_PURPOSE,
    WebcrawlerBinding,
    WebcrawlerDeclarationProof,
    WebcrawlerProfile,
    WebcrawlerWorkflowCode,
    WebcrawlerWorkflowError,
    parse_page_question,
)

if TYPE_CHECKING:
    from lychd.agents.router import Intent


class WebcrawlerAdmissionService:
    """Issue assertions only from the actual authenticated command handler.

    The operator asserts the complete URL's public classification and source.
    Neither this assertion nor its persisted fields prove publicness or acquire
    a fetch grant. Native consent and the durable Webcrawler claim remain separate.
    """

    def __init__(
        self, *, access: LocalOperatorAccess, authorizer: ScoutHostAuthorizer, profile: WebcrawlerProfile
    ) -> None:
        """Bind the same credential owner and current policy used by acquisition."""
        self._access, self._authorizer, self._profile = access, authorizer, profile

    def declare(self, *, prompt: str, request_id: UUID, authentication: object) -> WebcrawlerDeclarationProof:
        """Bind an explicit command to current credential possession and policy."""
        if not self._access.current(authentication) or not isinstance(authentication, LocalOperatorAuthentication):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
        parsed = parse_page_question(prompt)
        declaration = PublicLocatorDeclaration(
            url=parsed.url,
            subject=authentication.subject,
            authentication_generation=authentication.authentication_generation,
            purpose=WEBCRAWLER_ANSWER_PURPOSE,
            source_manifest=(LocatorSource(source_id=request_id, url=parsed.url),),
            influence_manifest=(LocatorInfluence(source_id=request_id),),
            policy_revision=self._profile.policy_revision,
            declared_at=datetime.now(UTC),
        )
        self._classify(declaration)
        return WebcrawlerDeclarationProof(
            authentication=authentication, declaration=declaration, question=parsed.question, request_id=request_id
        )

    def _classify(self, declaration: PublicLocatorDeclaration) -> None:
        try:
            self._authorizer.require_declaration(
                declaration,
                binding_digest=self._profile.binding_digest,
                resolver_custody_digest=self._profile.resolver_custody_digest,
                revocation_generation=self._profile.revocation_generation,
            )
        except FetchError:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION) from None

    def __call__(
        self, intent: Intent, proof: WebcrawlerDeclarationProof, profile: WebcrawlerProfile
    ) -> WebcrawlerBinding:
        """Recheck the actual proof after awaited admission preparation."""
        if (
            type(proof) is not WebcrawlerDeclarationProof
            or not self._access.current(proof.authentication)
            or profile != self._profile
            or intent.source != "bridge"
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
        parsed = parse_page_question(intent.prompt)
        declaration = proof.declaration
        if (
            parsed.url != declaration.url
            or parsed.question != proof.question
            or declaration.subject != proof.authentication.subject
            or declaration.authentication_generation != proof.authentication.authentication_generation
            or declaration.source_manifest != (LocatorSource(source_id=proof.request_id, url=parsed.url),)
            or declaration.influence_manifest != (LocatorInfluence(source_id=proof.request_id),)
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
        self._classify(declaration)
        return WebcrawlerBinding(
            profile=profile, declaration=declaration, question=proof.question, request_id=proof.request_id
        )
