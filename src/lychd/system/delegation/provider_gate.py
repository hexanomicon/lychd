"""Pure Provider Gate grants that keep provider credentials outside the guest."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Final, TypeGuard

from lychd.system.delegation.policy import GateEndpoint, validate_identifier

_ROUTE_NAME: Final[re.Pattern[str]] = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,191}")
_MAX_GRANT_LIFETIME: Final[timedelta] = timedelta(hours=24)
_MAX_REQUESTS: Final[int] = 100_000
_MAX_TOKENS: Final[int] = 1_000_000_000
_MAX_COST_MICROUNITS: Final[int] = 10_000_000_000
_MIN_GATE_TOKEN_LENGTH: Final[int] = 32
_MAX_GATE_TOKEN_LENGTH: Final[int] = 512
_FIRST_VISIBLE_ASCII: Final[int] = 33


@dataclass(frozen=True, slots=True)
class ProviderCredentialRef:
    """Opaque trusted-plane reference; never a provider credential value."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        """Validate the opaque vault lookup identifier."""
        validate_identifier(self.value, field="credential reference")


@dataclass(frozen=True, slots=True)
class GuestGateToken:
    """Short-lived authority presented only to LychD's Provider Gate."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        """Reject weak, control-bearing, or unbounded bearer values."""
        if (
            not _MIN_GATE_TOKEN_LENGTH <= len(self.value) <= _MAX_GATE_TOKEN_LENGTH
            or not self.value.isascii()
            or any(character.isspace() or ord(character) < _FIRST_VISIBLE_ASCII for character in self.value)
        ):
            message = "Gate token must be 32-512 visible ASCII characters"
            raise ValueError(message)

    def digest(self) -> bytes:
        return hashlib.sha256(self.value.encode()).digest()


@dataclass(frozen=True, slots=True)
class ProviderBudget:
    max_requests: int
    max_input_tokens: int
    max_output_tokens: int
    max_total_tokens: int
    max_cost_microunits: int

    def __post_init__(self) -> None:
        """Validate every provider-spend ceiling."""
        _bounded(self.max_requests, maximum=_MAX_REQUESTS, field="max_requests")
        _bounded(self.max_input_tokens, maximum=_MAX_TOKENS, field="max_input_tokens")
        _bounded(self.max_output_tokens, maximum=_MAX_TOKENS, field="max_output_tokens")
        _bounded(self.max_total_tokens, maximum=_MAX_TOKENS, field="max_total_tokens")
        _bounded(
            self.max_cost_microunits,
            maximum=_MAX_COST_MICROUNITS,
            field="max_cost_microunits",
        )
        if self.max_total_tokens > self.max_input_tokens + self.max_output_tokens:
            message = "Total-token budget cannot exceed input plus output ceilings"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_microunits: int = 0

    def __post_init__(self) -> None:
        """Keep usage monotonic and non-negative."""
        for name in ("requests", "input_tokens", "output_tokens", "cost_microunits"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                message = f"{name} must be a non-negative integer"
                raise ValueError(message)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def plus(self, other: ProviderUsage) -> ProviderUsage:
        return ProviderUsage(
            requests=self.requests + other.requests,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cost_microunits=self.cost_microunits + other.cost_microunits,
        )


@dataclass(frozen=True, slots=True)
class GuestProviderEnvelope:
    """The complete provider-facing material permitted inside a coffin."""

    grant_id: str
    job_id: str
    provider: str
    model: str
    endpoint: GateEndpoint
    bearer: GuestGateToken = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderCallRequest:
    job_id: str
    provider: str
    model: str
    bearer: GuestGateToken = field(repr=False)
    usage: ProviderUsage

    def __post_init__(self) -> None:
        """Validate the exact route and one-call usage delta."""
        validate_identifier(self.job_id, field="job_id")
        _validate_route_name(self.provider, field="provider")
        _validate_route_name(self.model, field="model")
        if self.usage.requests != 1:
            message = "Each Provider Gate authorization represents exactly one request"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ProviderAuthorization:
    """Trusted-plane authorization; this object is never projected to the guest."""

    grant_id: str
    job_id: str
    provider: str
    model: str
    credential: ProviderCredentialRef = field(repr=False)
    cumulative_usage: ProviderUsage


@dataclass(frozen=True, slots=True)
class ProviderGateGrant:
    """Immutable grant validated per call by the trusted Provider Gate."""

    grant_id: str
    job_id: str
    provider: str
    model: str
    credential: ProviderCredentialRef = field(repr=False)
    endpoint: GateEndpoint
    issued_at: datetime
    expires_at: datetime
    budget: ProviderBudget
    token_digest: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Validate route, lifetime, and bearer-digest shape."""
        validate_identifier(self.grant_id, field="grant_id")
        validate_identifier(self.job_id, field="job_id")
        _validate_route_name(self.provider, field="provider")
        _validate_route_name(self.model, field="model")
        _aware(self.issued_at, field="issued_at")
        _aware(self.expires_at, field="expires_at")
        lifetime = self.expires_at - self.issued_at
        if lifetime <= timedelta(0) or lifetime > _MAX_GRANT_LIFETIME:
            message = "Provider Gate grants must live for more than zero and at most 24 hours"
            raise ValueError(message)
        if len(self.token_digest) != hashlib.sha256().digest_size:
            message = "Provider Gate token digest must be SHA-256"
            raise ValueError(message)

    @classmethod
    def issue(
        cls,
        *,
        grant_id: str,
        job_id: str,
        provider: str,
        model: str,
        credential: ProviderCredentialRef,
        endpoint: GateEndpoint,
        issued_at: datetime,
        expires_at: datetime,
        budget: ProviderBudget,
        bearer: GuestGateToken,
    ) -> ProviderGateGrant:
        return cls(
            grant_id=grant_id,
            job_id=job_id,
            provider=provider,
            model=model,
            credential=credential,
            endpoint=endpoint,
            issued_at=issued_at,
            expires_at=expires_at,
            budget=budget,
            token_digest=bearer.digest(),
        )

    def guest_envelope(
        self,
        bearer: GuestGateToken,
        *,
        now: datetime,
    ) -> GuestProviderEnvelope:
        _aware(now, field="now")
        if now < self.issued_at or now >= self.expires_at:
            message = "Provider Gate grant is not active"
            raise PermissionError(message)
        if not hmac.compare_digest(self.token_digest, bearer.digest()):
            message = "Gate token does not belong to this grant"
            raise PermissionError(message)
        return GuestProviderEnvelope(
            grant_id=self.grant_id,
            job_id=self.job_id,
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            bearer=bearer,
            expires_at=self.expires_at,
        )

    def authorize(
        self,
        request: ProviderCallRequest,
        *,
        consumed: ProviderUsage,
        now: datetime,
    ) -> ProviderAuthorization:
        _aware(now, field="now")
        if now < self.issued_at or now >= self.expires_at:
            message = "Provider Gate grant is not active"
            raise PermissionError(message)
        if not hmac.compare_digest(self.token_digest, request.bearer.digest()):
            message = "Provider Gate bearer is invalid"
            raise PermissionError(message)
        if request.job_id != self.job_id or request.provider != self.provider or request.model != self.model:
            message = "Provider request falls outside its scoped grant"
            raise PermissionError(message)
        cumulative = consumed.plus(request.usage)
        _validate_budget(cumulative, self.budget)
        return ProviderAuthorization(
            grant_id=self.grant_id,
            job_id=self.job_id,
            provider=self.provider,
            model=self.model,
            credential=self.credential,
            cumulative_usage=cumulative,
        )


def _validate_budget(usage: ProviderUsage, budget: ProviderBudget) -> None:
    within_budget = (
        usage.requests <= budget.max_requests
        and usage.input_tokens <= budget.max_input_tokens
        and usage.output_tokens <= budget.max_output_tokens
        and usage.total_tokens <= budget.max_total_tokens
        and usage.cost_microunits <= budget.max_cost_microunits
    )
    if not within_budget:
        message = "Provider request exceeds its grant budget"
        raise PermissionError(message)


def _validate_route_name(value: str, *, field: str) -> str:
    if _ROUTE_NAME.fullmatch(value) is None or ".." in value.split("/") or "//" in value or value.endswith("/"):
        message = f"{field} contains unsupported characters"
        raise ValueError(message)
    return value


def _aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        message = f"{field} must be timezone-aware"
        raise ValueError(message)


def _bounded(value: object, *, maximum: int, field: str) -> None:
    if not _is_strict_integer(value) or not 1 <= value <= maximum:
        message = f"{field} must be between 1 and {maximum}"
        raise ValueError(message)


def _is_strict_integer(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


__all__ = (
    "GuestGateToken",
    "GuestProviderEnvelope",
    "ProviderAuthorization",
    "ProviderBudget",
    "ProviderCallRequest",
    "ProviderCredentialRef",
    "ProviderGateGrant",
    "ProviderUsage",
)
