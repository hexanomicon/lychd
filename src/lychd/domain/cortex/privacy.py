"""Privacy labels and influence-lineage joins for assembled Context."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from fnmatch import fnmatchcase
from ipaddress import ip_address
from math import isfinite
from typing import Any, Literal, Self, cast

__all__ = [
    "INTERNAL_PRIVATIZATION_LABEL",
    "PUBLIC_PRIVATIZATION_LABEL",
    "RESTRICTED_UNKNOWN_PRIVATIZATION_LABEL",
    "DeterministicCensor",
    "DeterministicTransformation",
    "PrivacyClass",
    "PrivacyCutError",
    "PrivatizationLabel",
    "TransformationKind",
    "TransformationOperation",
    "TransformationReceipt",
    "canonical_privacy_digest",
]

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERNS = ("*key*", "*secret*", "*token*", "*password*", "*credential*")
_PEM_PATTERN = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.DOTALL,
)
_JWT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])"
)
_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?![\w.-])")
_UUID_PATTERN = re.compile(
    r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12})(?![0-9A-Fa-f])"
)
_IPV4_CANDIDATE_PATTERN = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_PHONE_CANDIDATE_PATTERN = re.compile(r"(?<!\w)\+?[1-9]\d(?:[\s().-]?\d){7,14}(?!\w)")
_MIN_PHONE_DIGITS = 8
_MAX_PHONE_DIGITS = 15
_MAX_PRIVACY_DEPTH = 64
_MAX_PRIVACY_NODES = 100_000


class PrivacyClass(StrEnum):
    """Ordered disclosure class carried by one Context influence."""

    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    RESTRICTED = "restricted"


_PRIVACY_CLASS_RANK = {
    PrivacyClass.PUBLIC: 0,
    PrivacyClass.INTERNAL: 1,
    PrivacyClass.PRIVATE: 2,
    PrivacyClass.RESTRICTED: 3,
}


class PrivacyCutError(ValueError):
    """Raised when deterministic privacy processing cannot prove exact input shape."""


class TransformationKind(StrEnum):
    """Transformation vocabulary retained without sensitive source spans."""

    REDACT = "redact"


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationOperation:
    """Counted transformation evidence that contains no source value or reversal map."""

    kind: TransformationKind
    category: str
    count: int

    def __post_init__(self) -> None:
        """Reject empty categories and non-positive evidence counts."""
        if not self.category or self.category != self.category.strip():
            msg = "Transformation category must be a non-blank canonical value."
            raise ValueError(msg)
        if self.count < 1:
            msg = "Transformation operation count must be positive."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class PrivatizationLabel:
    """Immutable privacy and source-influence metadata for one Context block.

    A label is evidence about handling requirements, never egress authority. Unknown
    lineage must be restricted so a future Portal gate cannot treat absent metadata
    as public material.
    """

    privacy_class: PrivacyClass
    weight: float
    categories: frozenset[str] = frozenset()
    subjects: frozenset[str] = frozenset()
    material_parents: frozenset[str] = frozenset()
    handling_constraints: frozenset[str] = frozenset()
    lineage_known: bool = True

    def __post_init__(self) -> None:
        """Validate the closed weight scale and freeze every set-like field."""
        if not isfinite(self.weight) or not 0.0 <= self.weight <= 1.0:
            msg = "Privatization label weight must be finite and between 0.0 and 1.0."
            raise ValueError(msg)
        if not self.lineage_known and self.privacy_class is not PrivacyClass.RESTRICTED:
            msg = "Unknown privacy lineage must use the restricted class."
            raise ValueError(msg)
        for field_name in (
            "categories",
            "subjects",
            "material_parents",
            "handling_constraints",
        ):
            values = frozenset(getattr(self, field_name))
            if any(not value or value != value.strip() for value in values):
                msg = f"Privatization label {field_name} must contain non-blank canonical values."
                raise ValueError(msg)
            object.__setattr__(self, field_name, values)

    @classmethod
    def public(cls) -> Self:
        """Return a known public label with no inherited influences."""
        return cls(privacy_class=PrivacyClass.PUBLIC, weight=0.0)

    @classmethod
    def internal(cls) -> Self:
        """Return the default label for LychD-owned prompt structure."""
        return cls(privacy_class=PrivacyClass.INTERNAL, weight=0.25)

    @classmethod
    def restricted_unknown(cls) -> Self:
        """Return the fail-closed label for material whose lineage is absent."""
        return cls(
            privacy_class=PrivacyClass.RESTRICTED,
            weight=1.0,
            categories=frozenset({"unknown"}),
            handling_constraints=frozenset({"local_only"}),
            lineage_known=False,
        )

    @classmethod
    def join(cls, *labels: PrivatizationLabel) -> Self:
        """Join exact influences without allowing transformation to lower privacy."""
        if not labels:
            return cls.public()
        privacy_class = max(labels, key=lambda label: _PRIVACY_CLASS_RANK[label.privacy_class]).privacy_class
        return cls(
            privacy_class=privacy_class,
            weight=max(label.weight for label in labels),
            categories=frozenset(category for label in labels for category in label.categories),
            subjects=frozenset(subject for label in labels for subject in label.subjects),
            material_parents=frozenset(parent for label in labels for parent in label.material_parents),
            handling_constraints=frozenset(constraint for label in labels for constraint in label.handling_constraints),
            lineage_known=all(label.lineage_known for label in labels),
        )

    def canonical_value(self) -> dict[str, Any]:
        """Return the stable JSON value included in exact branch digests."""
        return {
            "privacy_class": self.privacy_class.value,
            "weight": self.weight,
            "categories": sorted(self.categories),
            "subjects": sorted(self.subjects),
            "material_parents": sorted(self.material_parents),
            "handling_constraints": sorted(self.handling_constraints),
            "lineage_known": self.lineage_known,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationReceipt:
    """Exact deterministic transformation evidence without declassification authority."""

    source_digest: str
    candidate_digest: str
    transformer_revision: str
    policy_revision: str
    operations: tuple[TransformationOperation, ...]
    residual_label: PrivatizationLabel
    removed_categories: frozenset[str]
    uncertainty_assessment: Literal["unassessed"]
    utility_loss_assessment: Literal["unassessed"]
    expires_at: datetime
    egress_eligible: Literal[False] = False

    def __post_init__(self) -> None:
        """Reject ambiguous digests, revisions, time, or removal claims."""
        if not _SHA256_PATTERN.fullmatch(self.source_digest) or not _SHA256_PATTERN.fullmatch(self.candidate_digest):
            msg = "Transformation receipt digests must use canonical sha256:<hex> values."
            raise ValueError(msg)
        if (
            not self.transformer_revision.strip()
            or self.transformer_revision != self.transformer_revision.strip()
            or not self.policy_revision.strip()
            or self.policy_revision != self.policy_revision.strip()
        ):
            msg = "Transformation and policy revisions must be non-blank canonical values."
            raise ValueError(msg)
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            msg = "Transformation receipt expiry must be timezone-aware."
            raise ValueError(msg)
        if self.removed_categories:
            msg = "The deterministic first slice cannot claim that a category was fully removed."
            raise ValueError(msg)
        object.__setattr__(self, "operations", tuple(self.operations))
        object.__setattr__(self, "removed_categories", frozenset())


@dataclass(frozen=True, slots=True, kw_only=True)
class DeterministicTransformation:
    """A newly allocated local candidate and its non-authorizing receipt."""

    candidate: Any
    receipt: TransformationReceipt


def canonical_privacy_digest(value: Any) -> str:
    """Digest one supported JSON value, rejecting lossy or ambiguous coercions."""
    _validate_privacy_value(value)
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        msg = "Privacy material cannot be represented as canonical JSON."
        raise PrivacyCutError(msg) from exc
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


class DeterministicCensor:
    """Local-only typed redaction that never lowers labels or authorizes egress."""

    def __init__(self, *, transformer_revision: str, policy_revision: str) -> None:
        """Bind exact revisions to every receipt this transformer produces."""
        if (
            not transformer_revision.strip()
            or transformer_revision != transformer_revision.strip()
            or not policy_revision.strip()
            or policy_revision != policy_revision.strip()
        ):
            msg = "Transformer and policy revisions must be non-blank canonical values."
            raise ValueError(msg)
        self._transformer_revision = transformer_revision
        self._policy_revision = policy_revision

    def transform(
        self,
        value: Any,
        *,
        source_label: PrivatizationLabel,
        expires_at: datetime,
    ) -> DeterministicTransformation:
        """Rebuild a supported value without lowering its source-influence label."""
        source_digest = canonical_privacy_digest(value)
        counts: dict[str, int] = {}
        candidate = self._transform_value(value, counts=counts)
        candidate_digest = canonical_privacy_digest(candidate)
        operations = tuple(
            TransformationOperation(kind=TransformationKind.REDACT, category=category, count=count)
            for category, count in sorted(counts.items())
        )
        return DeterministicTransformation(
            candidate=candidate,
            receipt=TransformationReceipt(
                source_digest=source_digest,
                candidate_digest=candidate_digest,
                transformer_revision=self._transformer_revision,
                policy_revision=self._policy_revision,
                operations=operations,
                residual_label=source_label,
                removed_categories=frozenset(),
                uncertainty_assessment="unassessed",
                utility_loss_assessment="unassessed",
                expires_at=expires_at,
            ),
        )

    def _transform_value(self, value: Any, *, counts: dict[str, int]) -> Any:
        if value is None or isinstance(value, bool | int):
            return value
        if isinstance(value, float):
            if not isfinite(value):
                msg = "Non-finite numbers are unsupported privacy material."
                raise PrivacyCutError(msg)
            return value
        if isinstance(value, str):
            return self._transform_text(value, counts=counts)
        if isinstance(value, list | tuple):
            sequence = cast("list[Any] | tuple[Any, ...]", value)
            return [self._transform_value(item, counts=counts) for item in sequence]
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, child in cast("dict[Any, Any]", value).items():
                if not isinstance(raw_key, str):
                    msg = "Privacy material object keys must be strings."
                    raise PrivacyCutError(msg)
                if _is_secret_key(raw_key):
                    result[raw_key] = "<redacted:secret>"
                    counts["secret"] = counts.get("secret", 0) + 1
                else:
                    result[raw_key] = self._transform_value(child, counts=counts)
            return result
        msg = f"Unsupported privacy material type: {type(value).__name__}."
        raise PrivacyCutError(msg)

    @staticmethod
    def _transform_text(value: str, *, counts: dict[str, int]) -> str:
        transformed = value
        patterns = (
            ("private_key", _PEM_PATTERN),
            ("jwt", _JWT_PATTERN),
            ("email", _EMAIL_PATTERN),
            ("uuid", _UUID_PATTERN),
        )
        for category, pattern in patterns:
            transformed, count = pattern.subn(f"<redacted:{category}>", transformed)
            if count:
                counts[category] = counts.get(category, 0) + count
        transformed = _replace_validated_candidates(
            transformed,
            pattern=_IPV4_CANDIDATE_PATTERN,
            category="ip_address",
            counts=counts,
            validator=_is_ip_address,
        )
        return _replace_validated_candidates(
            transformed,
            pattern=_PHONE_CANDIDATE_PATTERN,
            category="phone",
            counts=counts,
            validator=_is_phone,
        )


def _validate_privacy_value(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_PRIVACY_NODES:
            msg = f"Privacy material exceeds the {_MAX_PRIVACY_NODES}-node structural limit."
            raise PrivacyCutError(msg)
        if depth > _MAX_PRIVACY_DEPTH:
            msg = f"Privacy material exceeds the {_MAX_PRIVACY_DEPTH}-level nesting limit."
            raise PrivacyCutError(msg)
        if _validate_privacy_scalar(current):
            continue
        if isinstance(current, list | tuple):
            sequence = cast("list[Any] | tuple[Any, ...]", current)
            stack.extend((item, depth + 1) for item in sequence)
            continue
        if isinstance(current, dict):
            mapping = cast("dict[Any, Any]", current)
            for key, child in mapping.items():
                if not isinstance(key, str):
                    msg = "Privacy material object keys must be strings."
                    raise PrivacyCutError(msg)
                stack.append((child, depth + 1))
            continue
        msg = f"Unsupported privacy material type: {type(current).__name__}."
        raise PrivacyCutError(msg)


def _validate_privacy_scalar(value: Any) -> bool:
    if value is None or isinstance(value, bool | int | str):
        return True
    if not isinstance(value, float):
        return False
    if not isfinite(value):
        msg = "Non-finite numbers are unsupported privacy material."
        raise PrivacyCutError(msg)
    return True


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(fnmatchcase(lowered, pattern) for pattern in _SECRET_KEY_PATTERNS)


def _replace_validated_candidates(
    value: str,
    *,
    pattern: re.Pattern[str],
    category: str,
    counts: dict[str, int],
    validator: Any,
) -> str:
    def replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        if not validator(candidate):
            return candidate
        counts[category] = counts.get(category, 0) + 1
        return f"<redacted:{category}>"

    return pattern.sub(replace, value)


def _is_ip_address(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return False
    return True


def _is_phone(value: str) -> bool:
    digits = "".join(character for character in value if character.isdigit())
    return _MIN_PHONE_DIGITS <= len(digits) <= _MAX_PHONE_DIGITS


PUBLIC_PRIVATIZATION_LABEL = PrivatizationLabel.public()
INTERNAL_PRIVATIZATION_LABEL = PrivatizationLabel.internal()
RESTRICTED_UNKNOWN_PRIVATIZATION_LABEL = PrivatizationLabel.restricted_unknown()
