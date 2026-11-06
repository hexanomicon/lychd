"""Mirror bootstrap forms of address; no Persona lineage or authority is implied."""

from __future__ import annotations

import secrets
import unicodedata
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_NAME_LENGTH = 96
MAX_OWNER_LENGTH = 256
MAX_NAMING_REVISION = 9223372036854775807

NameOrigin = Literal["manual", "dictionary", "assisted", "self_chosen"]


class PersonalNames(BaseModel):
    """Accepted literal names and operator-declared selection methods."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    magus_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    primus_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    magus_origin: NameOrigin
    primus_origin: NameOrigin

    @field_validator("magus_name", "primus_name", mode="before")
    @classmethod
    def literal_name(cls, value: object) -> object:
        """Normalize spelling while refusing concealed controls and line breaks."""
        if not isinstance(value, str):
            return value
        if not value.isprintable():
            msg = "Names must contain printable single-line text."
            raise ValueError(msg)
        return unicodedata.normalize("NFC", value).strip()


class NamingSnapshot(PersonalNames):
    """One accepted naming revision, suitable for immutable Run admission."""

    revision: int = Field(ge=1, le=MAX_NAMING_REVISION)

    @field_validator("revision", mode="before")
    @classmethod
    def exact_revision(cls, value: object) -> object:
        """Keep revision identity exact under transport validation as well."""
        if type(value) is not int:
            msg = "Naming revision must be an integer."
            raise ValueError(msg)
        return value


class NamingAcceptance(BaseModel):
    """Explicit acceptance against the revision the operator actually reviewed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    expected_revision: int = Field(ge=0, lt=MAX_NAMING_REVISION)
    names: PersonalNames

    @field_validator("expected_revision", mode="before")
    @classmethod
    def exact_expected_revision(cls, value: object) -> object:
        """Refuse booleans and coerced strings at the HTTP boundary as well."""
        if type(value) is not int:
            msg = "Expected naming revision must be an integer."
            raise ValueError(msg)
        return value


class NamingView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    current: NamingSnapshot | None


class NameSuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    names: list[str]


class NamingConflictError(ValueError):
    """The reviewed naming revision is no longer current."""


class NamingStoreError(RuntimeError):
    """Storage is unavailable or its mutation outcome requires a fresh read."""


class NamingStore(Protocol):
    async def get(self, owner: str) -> NamingSnapshot | None:
        """Read only the authenticated owner's accepted names."""
        ...

    async def accept(self, owner: str, names: PersonalNames, expected_revision: int) -> NamingSnapshot:
        """Advance the current revision only if its reviewed revision still matches."""
        ...


def validate_owner(owner: str) -> None:
    if not owner or len(owner) > MAX_OWNER_LENGTH or not owner.isprintable():
        msg = "Invalid naming owner."
        raise ValueError(msg)


class InMemoryNamingStore:
    """Process-local test profile; PostgreSQL owns deployed persistence."""

    def __init__(self) -> None:
        """Retain detached immutable snapshots within this test store."""
        self._revisions: dict[str, list[NamingSnapshot]] = {}

    async def get(self, owner: str) -> NamingSnapshot | None:
        validate_owner(owner)
        revisions = self._revisions.get(owner, ())
        return revisions[-1] if revisions else None

    async def accept(self, owner: str, names: PersonalNames, expected_revision: int) -> NamingSnapshot:
        validate_owner(owner)
        accepted = NamingAcceptance(names=names, expected_revision=expected_revision)
        revisions = self._revisions.get(owner, [])
        if len(revisions) != accepted.expected_revision:
            msg = "Names changed; reload before accepting another revision."
            raise NamingConflictError(msg)
        snapshot = NamingSnapshot(**accepted.names.model_dump(), revision=accepted.expected_revision + 1)
        # No await occurs between comparison and append.
        self._revisions.setdefault(owner, []).append(snapshot)
        return snapshot


def suggest_names() -> NameSuggestions:
    """Offer six distinct dictionary combinations without inference or persistence."""
    given = ("Aster", "Auriel", "Elara", "Liora", "Lyra", "Orion", "Seren", "Solan", "Vesper", "Zephyr", "Zenith")
    surnames = (
        "Runeweaver",
        "Shadowdancer",
        "Dawnkeeper",
        "Stargazer",
        "Moonwhisper",
        "Emberwright",
        "Dreamwalker",
        "Silverleaf",
        "Nightbloom",
        "Stormsinger",
        "Duskweaver",
        "Sunward",
    )
    choices = [f"{first} {last}" for first in given for last in surnames]
    return NameSuggestions(names=secrets.SystemRandom().sample(choices, 6))
