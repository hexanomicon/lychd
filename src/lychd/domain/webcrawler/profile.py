"""Exact opt-in public-page casting values and its host-owned coordination port."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from ipaddress import ip_address
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lychd.domain.codex.local_access import LocalOperatorAuthentication
from lychd.domain.scout.attempts import (
    Digest,
    Identity,
    PublicLocatorDeclaration,
    ScoutAllowance,
    ScoutBudgetLimits,
    document_digest,
)
from lychd.domain.scout.destination import DestinationError, preflight_destination
from lychd.domain.scout.extraction import ExtractedText

if TYPE_CHECKING:
    from lychd.agents.router import Intent

WEBCRAWLER_ANSWER_PURPOSE = "scout:answer-public-page"
MAX_QUESTION_CHARS = 2000
MAX_CONTEXT_CHARS = 16_000


class WebcrawlerWorkflowCode(StrEnum):
    """Closed outcomes shared by the host coordinator and public-page score."""

    ADMISSION = "admission"
    BINDING = "binding"
    CONSENT = "consent"
    MATERIAL_UNAVAILABLE = "material_unavailable"
    MODEL = "model"
    PROJECTION = "projection"
    SETTLEMENT = "settlement"


class WebcrawlerWorkflowError(ValueError):
    """Closed, content-free workflow refusal, without provider diagnostics."""

    def __init__(self, code: WebcrawlerWorkflowCode) -> None:
        """Retain a closed code without acquired content or provider diagnostics."""
        self.code = code
        super().__init__(f"Webcrawler page answer refused: {code}.")


class WebcrawlerProfile(BaseModel):
    """One explicit host configuration; serialized fields grant no authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    provider_id: Literal["native-static@1"] = "native-static@1"
    profile: Literal["static-public-page@1"] = "static-public-page@1"
    binding_id: Identity
    policy_revision: int = Field(strict=True, ge=1)
    revocation_generation: int = Field(strict=True, ge=0)
    resolver_address: str = Field(min_length=1, max_length=39)
    resolver_port: int = Field(default=53, strict=True, ge=1, le=65535)
    resolver_custody_statement: str = Field(min_length=1, max_length=4000)
    ca_file: Path
    bwrap: Path
    python_root: Path
    libraries: tuple[Path, ...]
    allowance: ScoutAllowance
    budget_limits: ScoutBudgetLimits
    max_context_chars: int = Field(default=MAX_CONTEXT_CHARS, strict=True, ge=1, le=MAX_CONTEXT_CHARS)
    review_ttl_seconds: int = Field(default=300, strict=True, ge=1, le=3600)

    @model_validator(mode="after")
    def bounded_host_configuration(self) -> Self:
        """Check syntax and narrowing without touching files or resolving a name."""
        if str(ip_address(self.resolver_address)) != self.resolver_address:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        if not self.resolver_custody_statement.strip():
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        if any(not path.is_absolute() for path in (self.ca_file, self.bwrap, self.python_root, *self.libraries)):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        if not self.allowance.within(self.budget_limits.binding) or not self.allowance.within(self.budget_limits.host):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        return self

    @property
    def resolver_custody_digest(self) -> str:
        """Bind the operator's explicit custody assertion, not technical proof."""
        return document_digest(self.resolver_custody_statement)

    @property
    def configuration_digest(self) -> str:
        """Bind every selected field, including physical runtime and ceilings."""
        return document_digest(self.model_dump(mode="json"))

    @property
    def binding_digest(self) -> str:
        """Identify the exact named provider/profile and its selected policy."""
        return document_digest(
            {
                "binding_id": self.binding_id,
                "provider_id": self.provider_id,
                "profile": self.profile,
                "policy_revision": self.policy_revision,
            }
        )


@dataclass(frozen=True, slots=True)
class PageQuestion:
    """Exact command operands; parsing does not classify or authorize the URL."""

    url: str = field(repr=False)
    question: str = field(repr=False)


def parse_page_question(prompt: str) -> PageQuestion:
    """Accept only the explicit command line followed by a bounded question."""
    command, newline, question = prompt.partition("\n")
    prefix = "/read-public "
    if (
        not command.startswith(prefix)
        or not newline
        or not question.strip()
        or len(question) > MAX_QUESTION_CHARS
        or "\x00" in question
    ):
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
    url = command[len(prefix) :]
    try:
        preflight_destination(url)
    except DestinationError:
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION) from None
    return PageQuestion(url, question)


class WebcrawlerBinding(BaseModel):
    """Retained admission facts; the declaration is never a reusable grant."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    profile: WebcrawlerProfile
    declaration: PublicLocatorDeclaration = Field(repr=False)
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS, repr=False)
    request_id: UUID

    @model_validator(mode="after")
    def exact_declaration(self) -> Self:
        """Keep the exact policy, purpose and nonblank question together."""
        if (
            not self.question.strip()
            or "\x00" in self.question
            or self.declaration.purpose != WEBCRAWLER_ANSWER_PURPOSE
            or self.declaration.policy_revision != self.profile.policy_revision
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        return self


@dataclass(frozen=True, kw_only=True)
class WebcrawlerDeclarationProof:
    """Ephemeral handler handoff; only the host validates its actual auth marker."""

    authentication: LocalOperatorAuthentication = field(repr=False)
    declaration: PublicLocatorDeclaration = field(repr=False)
    question: str = field(repr=False)
    request_id: UUID


class WebcrawlerAdmission(Protocol):
    """Synchronous current authority check after admission preparation awaits."""

    def __call__(
        self, intent: Intent, proof: WebcrawlerDeclarationProof, profile: WebcrawlerProfile
    ) -> WebcrawlerBinding: ...


class WebcrawlerReviewRef(BaseModel):
    """Only complete native review custody references may enter a checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    attempt_id: UUID
    preparation_digest: Digest
    consent_id: UUID
    native_binding_digest: Digest


@dataclass(frozen=True, kw_only=True)
class WebcrawlerMaterial:
    """Transient attributed extraction, never checkpoint or history payload."""

    attempt_id: UUID
    receipt_id: UUID
    receipt_digest: str
    requested_url: str = field(repr=False)
    contacted_url: str = field(repr=False)
    acquired_at: datetime
    extraction: ExtractedText = field(repr=False)


class WebcrawlerWorkflowPort(Protocol):
    """Host-owned durable attempt coordination and current consumption checks."""

    async def prepare(self, *, run_id: str, binding: WebcrawlerBinding) -> WebcrawlerReviewRef: ...

    async def consent(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef
    ) -> Literal["pending", "granted", "refused"]: ...

    async def acquire(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerMaterial: ...

    def authorize_consume(
        self,
        *,
        run_id: str,
        binding: WebcrawlerBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerMaterial,
        capability_key: str,
    ) -> None: ...

    async def authorize_settle(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef, receipt_id: UUID | None
    ) -> None: ...
