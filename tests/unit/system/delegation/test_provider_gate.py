from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from lychd.system.delegation.policy import GateEndpoint
from lychd.system.delegation.provider_gate import (
    GuestGateToken,
    ProviderBudget,
    ProviderCallRequest,
    ProviderCredentialRef,
    ProviderGateGrant,
    ProviderUsage,
)

_NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)
_TOKEN = GuestGateToken("guest-grant-token-0123456789-abcdef")
_OTHER_TOKEN = GuestGateToken("other-grant-token-0123456789-abcdef")


def _budget() -> ProviderBudget:
    return ProviderBudget(
        max_requests=10,
        max_input_tokens=1_000,
        max_output_tokens=500,
        max_total_tokens=1_200,
        max_cost_microunits=50_000,
    )


def _grant() -> ProviderGateGrant:
    return ProviderGateGrant.issue(
        grant_id="grant-1",
        job_id="job-1",
        provider="openai",
        model="openai/gpt-5.6-codex",
        credential=ProviderCredentialRef("vault-openai-primary"),
        endpoint=GateEndpoint("gate.lychd.invalid"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(hours=1),
        budget=_budget(),
        bearer=_TOKEN,
    )


def _request(
    *,
    job_id: str = "job-1",
    provider: str = "openai",
    model: str = "openai/gpt-5.6-codex",
    bearer: GuestGateToken = _TOKEN,
    usage: ProviderUsage | None = None,
) -> ProviderCallRequest:
    return ProviderCallRequest(
        job_id=job_id,
        provider=provider,
        model=model,
        bearer=bearer,
        usage=usage or ProviderUsage(requests=1, input_tokens=100, output_tokens=50, cost_microunits=500),
    )


def test_gate_authorizes_only_the_exact_scoped_route() -> None:
    authorization = _grant().authorize(
        _request(),
        consumed=ProviderUsage(requests=2, input_tokens=200, output_tokens=100, cost_microunits=1_000),
        now=_NOW + timedelta(minutes=1),
    )

    assert authorization.cumulative_usage == ProviderUsage(
        requests=3,
        input_tokens=300,
        output_tokens=150,
        cost_microunits=1_500,
    )


@pytest.mark.parametrize(
    "call_request",
    [
        _request(job_id="job-2"),
        _request(provider="anthropic"),
        _request(model="openai/gpt-5.6"),
        _request(bearer=_OTHER_TOKEN),
    ],
)
def test_gate_rejects_scope_and_token_substitution(call_request: ProviderCallRequest) -> None:
    with pytest.raises(PermissionError):
        _grant().authorize(call_request, consumed=ProviderUsage(), now=_NOW + timedelta(minutes=1))


def test_gate_rejects_before_issue_and_at_expiry_boundary() -> None:
    grant = _grant()

    with pytest.raises(PermissionError, match="not active"):
        grant.authorize(_request(), consumed=ProviderUsage(), now=_NOW - timedelta(microseconds=1))
    with pytest.raises(PermissionError, match="not active"):
        grant.authorize(_request(), consumed=ProviderUsage(), now=grant.expires_at)
    with pytest.raises(PermissionError, match="not active"):
        grant.guest_envelope(_TOKEN, now=grant.expires_at)


@pytest.mark.parametrize(
    "consumed",
    [
        ProviderUsage(requests=10),
        ProviderUsage(input_tokens=950),
        ProviderUsage(output_tokens=475),
        ProviderUsage(input_tokens=1_000, output_tokens=150),
        ProviderUsage(cost_microunits=49_750),
    ],
)
def test_gate_rejects_every_budget_dimension(consumed: ProviderUsage) -> None:
    with pytest.raises(PermissionError, match="budget"):
        _grant().authorize(_request(), consumed=consumed, now=_NOW + timedelta(minutes=1))


def test_guest_projection_contains_no_provider_credential_reference() -> None:
    grant = _grant()
    envelope = grant.guest_envelope(_TOKEN, now=_NOW + timedelta(minutes=1))
    rendered = f"{grant!r} {envelope!r}"

    assert not hasattr(envelope, "credential")
    assert "vault-openai-primary" not in rendered
    assert _TOKEN.value not in rendered
    assert _OTHER_TOKEN.value not in repr(_OTHER_TOKEN)


def test_grant_token_digest_cannot_be_replaced_with_arbitrary_length() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        replace(_grant(), token_digest=b"short")


def test_usage_rejects_fractional_accounting() -> None:
    with pytest.raises(ValueError, match="input_tokens"):
        ProviderUsage(input_tokens=0.5)  # type: ignore[arg-type]


def test_grants_require_bounded_aware_lifetime() -> None:
    grant = _grant()

    with pytest.raises(ValueError, match="timezone-aware"):
        replace(grant, expires_at=_NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="24 hours"):
        replace(grant, expires_at=grant.issued_at + timedelta(hours=25))
