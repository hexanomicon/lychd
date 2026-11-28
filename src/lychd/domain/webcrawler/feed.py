"""Closed first native feed profile; serialized facts are never current authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lychd.domain.codex.local_access import LocalOperatorAuthentication
from lychd.domain.scout.attempts import (
    SCOUT_FEED_PURPOSE,
    SCOUT_FEED_URL,
    Identity,
    PublicLocatorDeclaration,
    ScoutAllowance,
    ScoutBudgetLimits,
    ScoutFeedConsumer,
    document_digest,
)
from lychd.domain.scout.extraction import ExtractedFeed
from lychd.domain.webcrawler.profile import WebcrawlerReviewRef, WebcrawlerWorkflowCode, WebcrawlerWorkflowError

if TYPE_CHECKING:
    from lychd.agents.router import Intent


class WebcrawlerFeedProfile(BaseModel):
    """One selected RSS host configuration, with no model or context demand."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    provider_id: Literal["native-static@1"] = "native-static@1"
    profile: Literal["rss-public-feed@1"] = "rss-public-feed@1"
    binding_id: Identity
    policy_revision: int = Field(strict=True, ge=1)
    revocation_generation: int = Field(strict=True, ge=0)
    resolver_address: str = Field(min_length=1, max_length=39, repr=False)
    resolver_port: int = Field(default=53, strict=True, ge=1, le=65535)
    resolver_custody_statement: str = Field(min_length=1, max_length=4000, repr=False)
    ca_file: Path = Field(repr=False)
    bwrap: Path = Field(repr=False)
    python_root: Path = Field(repr=False)
    libraries: tuple[Path, ...] = Field(repr=False)
    allowance: ScoutAllowance
    budget_limits: ScoutBudgetLimits
    review_ttl_seconds: int = Field(default=300, strict=True, ge=1, le=3600)

    @model_validator(mode="after")
    def bounded_host_configuration(self) -> Self:
        """Validate local configuration syntax, without inspecting files or names."""
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
        return document_digest(self.resolver_custody_statement)

    @property
    def configuration_digest(self) -> str:
        return document_digest(self.model_dump(mode="json"))

    @property
    def binding_digest(self) -> str:
        return document_digest(
            {
                "binding_id": self.binding_id,
                "provider_id": self.provider_id,
                "profile": self.profile,
                "policy_revision": self.policy_revision,
            }
        )


class WebcrawlerFeedBinding(BaseModel):
    """Reference-only Scavenger admission; complete seed/filter stay application-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    schema_version: Literal["scout.feed-binding@1"] = "scout.feed-binding@1"
    profile: WebcrawlerFeedProfile
    declaration: PublicLocatorDeclaration = Field(repr=False)
    consumer: ScoutFeedConsumer = Field(repr=False)
    request_id: UUID
    expires_at: datetime

    @model_validator(mode="after")
    def exact_declaration(self) -> Self:
        if (
            self.declaration.purpose != SCOUT_FEED_PURPOSE
            or self.declaration.url != SCOUT_FEED_URL
            or self.declaration.policy_revision != self.profile.policy_revision
            or self.expires_at.utcoffset() is None
            or not self.declaration.declared_at
            < self.expires_at
            <= self.declaration.declared_at + timedelta(seconds=self.profile.review_ttl_seconds)
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        return self


@dataclass(frozen=True, kw_only=True)
class WebcrawlerFeedMaterial:
    """Actual transient feed object still needs current CONSUME and storage admission."""

    attempt_id: UUID
    receipt_id: UUID
    receipt_digest: str
    consumer: ScoutFeedConsumer = field(repr=False)
    requested_url: str = field(repr=False)
    contacted_url: str = field(repr=False)
    acquired_at: datetime
    extraction: ExtractedFeed = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class WebcrawlerFeedDeclarationProof:
    """Actual authenticated handler handoff; serialized references grant no authority."""

    authentication: LocalOperatorAuthentication = field(repr=False)
    declaration: PublicLocatorDeclaration = field(repr=False)
    consumer: ScoutFeedConsumer = field(repr=False)
    request_id: UUID
    expires_at: datetime


class WebcrawlerFeedAdmission(Protocol):
    """Synchronous host recheck after awaited admission preparation."""

    def __call__(
        self, intent: Intent, proof: WebcrawlerFeedDeclarationProof, profile: WebcrawlerFeedProfile
    ) -> WebcrawlerFeedBinding: ...


class WebcrawlerFeedWorkflowPort(Protocol):
    """One native feed passage; application storage and retrieval stay separate."""

    async def prepare(self, *, run_id: str, binding: WebcrawlerFeedBinding) -> WebcrawlerReviewRef: ...

    async def consent(
        self, *, run_id: str, binding: WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> Literal["pending", "granted", "refused"]: ...

    async def acquire(
        self, *, run_id: str, binding: WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerFeedMaterial: ...

    def authorize_feed_consume(
        self,
        *,
        run_id: str,
        binding: WebcrawlerFeedBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerFeedMaterial,
    ) -> None: ...
