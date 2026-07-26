"""Immutable Scribe authority, plan, and public result models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from lychd.system.services.scribe.naming import (
    QUADLET_SUFFIXES,
    SYSTEMD_SUFFIXES,
    validate_owned_filename,
)


class OwnershipManifest(BaseModel):
    """Exact filenames that this installation has authority to replace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    quadlet: tuple[str, ...] = ()
    systemd: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_entries(self) -> OwnershipManifest:
        """Validate uniqueness, namespace, and supported binding kinds."""
        if len(set(self.quadlet)) != len(self.quadlet) or len(set(self.systemd)) != len(self.systemd):
            msg = "The Scribe ownership manifest contains duplicate filenames."
            raise ValueError(msg)
        for filename in self.quadlet:
            validate_owned_filename(filename, suffixes=QUADLET_SUFFIXES, site="quadlet")
        for filename in self.systemd:
            validate_owned_filename(filename, suffixes=SYSTEMD_SUFFIXES, site="systemd")
        return self


@dataclass(frozen=True)
class SitePlan:
    """The selected owned subset to replace at one binding site."""

    directory: Path
    owned_names: frozenset[str]
    previous_names: frozenset[str]
    files: Mapping[str, bytes]


@dataclass(frozen=True)
class BindingBase:
    """Exact authority bytes and full source generation read by the planner."""

    authority: bytes
    ownership: OwnershipManifest
    sources: tuple[Path, ...]
    generation: str


@dataclass(frozen=True)
class BindingWriteSet:
    """One CAS-bound authority manifest and the mutations that establish it."""

    plans: tuple[SitePlan, ...]
    ownership: OwnershipManifest
    base: BindingBase


@dataclass(frozen=True)
class OwnedBindings:
    """Exact binding sources and runtime units authorized by the Scribe receipt."""

    receipt_present: bool
    generation: str | None = None
    quadlet_sources: tuple[Path, ...] = ()
    systemd_sources: tuple[Path, ...] = ()
    runtime_units: tuple[str, ...] = ()

    @property
    def source_count(self) -> int:
        """Return the number of exact generated source files recorded."""
        return len(self.quadlet_sources) + len(self.systemd_sources)


type BindingChangeKind = Literal["create", "update", "remove", "preserve"]


@dataclass(frozen=True)
class BindingChange:
    """One deterministic filesystem effect in a Scribe reconciliation."""

    kind: BindingChangeKind
    path: Path
    detail: str


@dataclass(frozen=True)
class BindingReconcilePlan:
    """Read-only projection of the exact transaction ``reconcile_all`` applies."""

    changes: tuple[BindingChange, ...]
    observed_generation: str
    desired_generation: str

    @property
    def mutates(self) -> bool:
        """Return whether reconciliation would change binding state."""
        return any(change.kind != "preserve" for change in self.changes)
