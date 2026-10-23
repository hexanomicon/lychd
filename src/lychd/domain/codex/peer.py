"""Exact local policy and attributed source values for outbound peer work.

These values express proposals and retained evidence. Neither a copied policy,
source nor declaration authenticates the initiating operator or authorizes I/O.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import NoReturn
from uuid import UUID


class PeerAuthorityError(ValueError):
    """A closed refusal without source, credential or foreign diagnostics."""

    def __init__(self, code: str) -> None:
        """Retain only one closed refusal code."""
        self.code = code
        super().__init__(f"Intercom authority refused: {code}.")


def _refuse(code: str) -> NoReturn:
    raise PeerAuthorityError(code) from None


_MAX_DECLARATION_SECONDS = 300
_MAX_TASK_SECONDS = 3600
_MAX_NETWORK_SECONDS = 30


@dataclass(frozen=True, slots=True)
class CapacityLimit:
    """A durable ceiling; consumed capacity is never refunded or renamed."""

    uses: int
    application_bytes: int
    network_bytes: int

    def __post_init__(self) -> None:
        """Refuse malformed or unbounded policy values."""
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            _refuse("capacity")


@dataclass(frozen=True, slots=True)
class PeerPolicy:
    """Host bootstrap selectors; an empty selector always denies.

    Selectors contain exact values and have no wildcard syntax. Generation and
    canonical digest must agree with retained current policy before any effect.
    """

    generation: int
    actions: frozenset[str]
    purposes: frozenset[str]
    categories: frozenset[str]
    task_schemas: frozenset[str]
    peers: frozenset[UUID]
    endpoints: frozenset[str]
    host_limit: CapacityLimit
    purpose_limit: CapacityLimit
    peer_limit: CapacityLimit
    task_limit: CapacityLimit
    declaration_seconds: int = 300
    task_seconds: int = 900
    network_seconds: int = 30

    def __post_init__(self) -> None:
        """Refuse malformed or unbounded policy values."""
        if (
            type(self.generation) is not int
            or self.generation < 1
            or not 1 <= self.declaration_seconds <= _MAX_DECLARATION_SECONDS
            or not 1 <= self.task_seconds <= _MAX_TASK_SECONDS
            or not 1 <= self.network_seconds <= _MAX_NETWORK_SECONDS
        ):
            _refuse("policy")
        for selector in (self.actions, self.purposes, self.categories, self.task_schemas, self.peers, self.endpoints):
            if type(selector) is not frozenset:
                _refuse("policy")

    def record(self) -> dict[str, object]:
        """Return public policy facts for immutable retained comparison."""
        return {
            "generation": self.generation,
            "actions": sorted(self.actions),
            "purposes": sorted(self.purposes),
            "categories": sorted(self.categories),
            "task_schemas": sorted(self.task_schemas),
            "peers": sorted(str(value) for value in self.peers),
            "endpoints": sorted(self.endpoints),
            "limits": self.limits(),
            "declaration_seconds": self.declaration_seconds,
            "task_seconds": self.task_seconds,
            "network_seconds": self.network_seconds,
        }

    def limits(self) -> dict[str, dict[str, int]]:
        return {
            "host": asdict(self.host_limit),
            "purpose": asdict(self.purpose_limit),
            "peer": asdict(self.peer_limit),
            "task": asdict(self.task_limit),
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.record(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PeerObject:
    """Exact object/action selectors presented to current host policy."""

    peer_id: UUID
    purpose: str
    category: str
    task_schema: str
    endpoint: str
    task_id: UUID | None = None
    content_digest: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class PublicTextSource:
    """Explicit human assertion, never an automatic publicness classifier.

    This bounded adapter accepts no inherited private, chat, voice, model or
    artifact material. A human can still falsely assert authorship; this value
    deliberately makes no claim of originality or automatic PII detection.
    """

    text: str = field(repr=False)
    source_manifest: tuple[str, ...] = ("operator-authored-public",)
    influence_manifest: tuple[str, ...] = ("operator-authored-public",)
    category: str = "public-task"
    source_kind: str = "operator-authored-public"
    classification: str = "public"
    public_assertion: bool = False
    lineage_known: bool = True
    local_only: bool = False

    def validate(self) -> None:
        try:
            size = len(self.text.encode("utf-8")) if type(self.text) is str else 0
        except UnicodeError:
            _refuse("source")
        if (
            type(self) is not PublicTextSource
            or type(self.text) is not str
            or not 0 < size <= 32 * 1024
            or self.source_kind != "operator-authored-public"
            or self.classification != "public"
            or self.public_assertion is not True
            or self.lineage_known is not True
            or self.local_only is not False
            or self.source_manifest != ("operator-authored-public",)
            or self.influence_manifest != ("operator-authored-public",)
        ):
            _refuse("source")


@dataclass(frozen=True, slots=True)
class PublicDeclaration:
    """Restricted nonbearer evidence; only the issuing owner's exact object is live."""

    declaration_id: UUID
    operation_id: UUID
    target: PeerObject
    subject: str = field(repr=False)
    authentication_generation: UUID = field(repr=False)
    policy_generation: int
    policy_digest: str
    expires_at: datetime
    text_digest: str = field(repr=False)
    source_digest: str = field(repr=False)
