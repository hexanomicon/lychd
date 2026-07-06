"""RuneRegistry: PortReserver merge honesty (P2) + one()/one_or_none() ambiguity (P4)."""

from __future__ import annotations

import pytest

from lychd.config.runes.protocols import PortReserver
from lychd.config.runes.registry import RuneRegistry
from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings


class _Claimer:
    """A PortReserver-shaped rune claiming one labelled port."""

    def __init__(self, label: str, port: int) -> None:
        self._label = label
        self._port = port

    def reserved_ports(self) -> dict[str, int]:
        return {self._label: self._port}


class _Bystander:
    """A rune-like object that is NOT a PortReserver (no reserved_ports)."""

    name = "bystander"


def test_phoenix_is_a_port_reserver() -> None:
    assert isinstance(PhoenixSettings(), PortReserver)
    assert not isinstance(_Bystander(), PortReserver)


def test_reserved_ports_collects_phoenix_claims() -> None:
    registry = RuneRegistry([PhoenixSettings()])
    ports = registry.reserved_ports()
    assert ports == {"Oculus (Phoenix UI)": 6006, "Oculus (Phoenix OTLP)": 4317}


def test_reserved_ports_ignores_non_reservers() -> None:
    """isinstance tightening: a rune that is not a PortReserver contributes nothing."""
    registry = RuneRegistry([_Bystander()])  # type: ignore[list-item]
    assert registry.reserved_ports() == {}


def test_reserved_ports_duplicate_claim_names_both() -> None:
    """A second rune claiming an already-claimed port fails, naming both claimants."""
    registry = RuneRegistry([_Claimer("Oculus (Phoenix UI)", 6006), _Claimer("Intruder", 6006)])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="6006") as exc:
        registry.reserved_ports()
    message = str(exc.value)
    assert "Oculus (Phoenix UI)" in message
    assert "Intruder" in message


def test_one_ambiguity_names_schema_and_count() -> None:
    """P4 / A7-U4 AC: two PhoenixSettings runes -> ValueError naming schema + count."""
    registry = RuneRegistry([PhoenixSettings(), PhoenixSettings()])
    with pytest.raises(ValueError, match="PhoenixSettings") as exc:
        registry.one(PhoenixSettings)
    assert "2" in str(exc.value)


def test_one_or_none_rejects_multiple() -> None:
    registry = RuneRegistry([PhoenixSettings(), PhoenixSettings()])
    with pytest.raises(ValueError, match="PhoenixSettings"):
        registry.one_or_none(PhoenixSettings)


def test_one_or_none_absent_is_none() -> None:
    assert RuneRegistry([]).one_or_none(PhoenixSettings) is None
