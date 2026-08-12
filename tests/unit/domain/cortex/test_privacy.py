from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from lychd.domain.cortex.privacy import (
    DeterministicCensor,
    PrivacyClass,
    PrivacyCutError,
    PrivatizationLabel,
    canonical_privacy_digest,
)


def _restricted_label() -> PrivatizationLabel:
    return PrivatizationLabel(
        privacy_class=PrivacyClass.RESTRICTED,
        weight=1.0,
        categories=frozenset({"identity"}),
    )


def _censor() -> DeterministicCensor:
    return DeterministicCensor(transformer_revision="censor:v1", policy_revision="privacy:test")


def test_deterministic_censor_rebuilds_and_redacts_typed_material() -> None:
    source: dict[str, Any] = {
        "email": "alice@example.com",
        "profile": {
            "api_token": "do-not-store",
            "message": "call +421 900 123 456 from 192.0.2.10",
        },
        "ids": ["550e8400-e29b-41d4-a716-446655440000"],
    }

    transformed = _censor().transform(
        source,
        source_label=_restricted_label(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    assert transformed.candidate == {
        "email": "<redacted:email>",
        "profile": {
            "api_token": "<redacted:secret>",
            "message": "call <redacted:phone> from <redacted:ip_address>",
        },
        "ids": ["<redacted:uuid>"],
    }
    assert transformed.candidate is not source
    assert transformed.candidate["profile"] is not source["profile"]
    assert source["profile"]["api_token"] == "do-not-store"  # noqa: S105 - synthetic fixture
    assert {operation.category for operation in transformed.receipt.operations} == {
        "email",
        "ip_address",
        "phone",
        "secret",
        "uuid",
    }
    assert transformed.receipt.egress_eligible is False
    assert transformed.receipt.removed_categories == frozenset()
    assert transformed.receipt.residual_label == _restricted_label()


@pytest.mark.parametrize("key_kind", ["", "RSA ", "EC ", "OPENSSH "])
def test_deterministic_censor_redacts_supported_pem_private_keys(key_kind: str) -> None:
    pem = f"-----BEGIN {key_kind}PRIVATE KEY-----\nsynthetic-private-material\n-----END {key_kind}PRIVATE KEY-----"

    transformed = _censor().transform(
        {"message": f"before {pem} after"},
        source_label=_restricted_label(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    assert transformed.candidate == {"message": "before <redacted:private_key> after"}
    assert [operation.category for operation in transformed.receipt.operations] == ["private_key"]


def test_deterministic_censor_redacts_jwt_shaped_text() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signatureABCDEFG"

    transformed = _censor().transform(
        {"message": f"bearer {jwt}"},
        source_label=_restricted_label(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    assert transformed.candidate == {"message": "bearer <redacted:jwt>"}
    assert [operation.category for operation in transformed.receipt.operations] == ["jwt"]


def test_receipt_contains_no_sensitive_source_values() -> None:
    sensitive_email = "alice@example.com"
    transformed = _censor().transform(
        {"message": sensitive_email},
        source_label=_restricted_label(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    assert sensitive_email not in repr(transformed.receipt)
    assert transformed.receipt.source_digest != transformed.receipt.candidate_digest
    assert transformed.receipt.residual_label.privacy_class is PrivacyClass.RESTRICTED


def test_canonical_digest_is_exact_and_rejects_ambiguous_values() -> None:
    assert canonical_privacy_digest({"value": "a"}) != canonical_privacy_digest({"value": "b"})
    with pytest.raises(PrivacyCutError, match="Unsupported privacy material type"):
        canonical_privacy_digest({"value": object()})
    with pytest.raises(PrivacyCutError, match="Non-finite"):
        canonical_privacy_digest({"value": float("nan")})
    with pytest.raises(PrivacyCutError, match="keys must be strings"):
        canonical_privacy_digest({1: "value"})
    nested: Any = "leaf"
    for _ in range(66):
        nested = [nested]
    with pytest.raises(PrivacyCutError, match="nesting limit"):
        canonical_privacy_digest(nested)


def test_label_join_unions_influences_and_keeps_highest_boundary() -> None:
    internal = PrivatizationLabel(
        privacy_class=PrivacyClass.INTERNAL,
        weight=0.2,
        categories=frozenset({"code"}),
        material_parents=frozenset({"artifact:one"}),
    )
    private = PrivatizationLabel(
        privacy_class=PrivacyClass.PRIVATE,
        weight=0.7,
        subjects=frozenset({"subject:one"}),
        material_parents=frozenset({"message:one"}),
    )

    joined = PrivatizationLabel.join(internal, private)

    assert joined.privacy_class is PrivacyClass.PRIVATE
    assert joined.weight == 0.7
    assert joined.categories == frozenset({"code"})
    assert joined.subjects == frozenset({"subject:one"})
    assert joined.material_parents == frozenset({"artifact:one", "message:one"})
