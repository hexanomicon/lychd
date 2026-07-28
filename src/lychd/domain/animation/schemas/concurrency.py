from __future__ import annotations

import re
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CONFLICT_DOMAIN: Final = "default-exclusive"
"""Conservative wildcard used by managed runtimes that omit ``conflict_domains``."""

CONFLICT_DOMAIN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$")
"""Grammar for one stable, operator-authored conflict-domain label."""


class ConcurrencyIntent(BaseModel):
    """Orchestration-facing lifecycle hints."""

    model_config = ConfigDict(extra="forbid")

    dedicated: bool = Field(
        default=True,
        description="Whether LychD owns this animator's lifecycle and may stop or start it.",
    )
    persistent_resident: bool = Field(
        default=False,
        description="Whether this capability should stay out of the default eviction set when possible.",
    )
    conflict_domains: list[str] | None = Field(
        default=None,
        description=(
            "Exclusive resource-domain memberships. Omission is a conservative global-unknown "
            "wildcard for managed non-residents; an explicit empty list declares that the "
            "runtime may coexist."
        ),
    )

    @field_validator("conflict_domains")
    @classmethod
    def _validate_conflict_domains(cls, value: list[str] | None) -> list[str] | None:
        """Reject ambiguous or unsafe domain declarations without normalizing intent."""
        if value is None:
            return None
        duplicates = sorted(domain for domain in set(value) if value.count(domain) > 1)
        if duplicates:
            msg = f"conflict_domains contains duplicate labels: {', '.join(duplicates)}"
            raise ValueError(msg)
        invalid = [domain for domain in value if CONFLICT_DOMAIN_PATTERN.fullmatch(domain) is None]
        if invalid:
            msg = (
                "conflict_domains labels must match "
                f"{CONFLICT_DOMAIN_PATTERN.pattern}: {', '.join(repr(domain) for domain in invalid)}"
            )
            raise ValueError(msg)
        if DEFAULT_CONFLICT_DOMAIN in value:
            msg = (
                f"conflict_domains label {DEFAULT_CONFLICT_DOMAIN!r} is compiler-reserved; "
                "omit conflict_domains to request conservative wildcard semantics"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_conflict_authority(self) -> ConcurrencyIntent:
        """Only lifecycle-managed non-residents may claim exclusive domains."""
        if self.conflict_domains and not self.dedicated:
            msg = "non-dedicated runtimes cannot declare conflict_domains"
            raise ValueError(msg)
        if self.conflict_domains and self.persistent_resident:
            msg = "persistent-resident runtimes cannot declare conflict_domains"
            raise ValueError(msg)
        return self

    @property
    def resolved_conflict_domains(self) -> tuple[str, ...]:
        """Resolve omission compatibly while preserving explicit coexistence."""
        if not self.dedicated or self.persistent_resident:
            return ()
        if self.conflict_domains is None:
            return (DEFAULT_CONFLICT_DOMAIN,)
        return tuple(self.conflict_domains)
