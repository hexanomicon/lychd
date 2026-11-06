"""Literal naming, optional absence, owner isolation, and revision acceptance."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from lychd.domain.naming import InMemoryNamingStore, NamingAcceptance, NamingConflictError, PersonalNames, suggest_names


def names(**updates: object) -> PersonalNames:
    return PersonalNames.model_validate(
        {
            "magus_name": "Zenith Runeweaver",
            "primus_name": "Liora Shadowdancer",
            "magus_origin": "manual",
            "primus_origin": "self_chosen",
            **updates,
        }
    )


def test_normalized_international_names_and_optional_dictionary() -> None:
    assert names(magus_name="  E\u0301lise  ", primus_name="月").magus_name == "Élise"
    assert names(primus_name="月").primus_name == "月"
    suggestions = suggest_names().names
    assert len(set(suggestions)) == len(suggestions) == 6
    assert all(len(value.split()) == 2 for value in suggestions)
    assert all(names(primus_name=value).primus_name == value for value in suggestions)


@pytest.mark.parametrize("value", ["", "   ", "a" * 97, "a\nb", "a\rb", "a\tb", "a\x00b", "a\u202eb", "a\u2028b", 123])
def test_invalid_literal_names_refused(value: object) -> None:
    with pytest.raises(ValidationError):
        names(magus_name=value)


@pytest.mark.parametrize("revision", [-1, True, "0", 1.0])
def test_review_revision_is_strict(revision: object) -> None:
    with pytest.raises(ValidationError):
        NamingAcceptance.model_validate({"expected_revision": revision, "names": names()})


@pytest.mark.asyncio
async def test_absence_ownership_and_immutable_previous_revision() -> None:
    store = InMemoryNamingStore()
    assert await store.get("alice") is None
    first = await store.accept("alice", names(), 0)
    assert first.revision == 1
    assert await store.get("bob") is None
    with pytest.raises(NamingConflictError):
        await store.accept("alice", names(primus_name="Vesper Moonwhisper"), 0)
    second = await store.accept("alice", names(primus_name="Vesper Moonwhisper"), 1)
    assert second.revision == 2
    assert first.primus_name == "Liora Shadowdancer"
    assert await store.get("alice") == second
    outcomes = await asyncio.gather(
        store.accept("alice", names(), 2), store.accept("alice", names(), 2), return_exceptions=True
    )
    assert sum(isinstance(outcome, NamingConflictError) for outcome in outcomes) == 1
