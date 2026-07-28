"""Evidence models shared by protected-root retirement and recovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lychd.system.atomic_retirement import (
    AtomicRetirementError,
    RetirementIdentity,
)


@dataclass(frozen=True, slots=True)
class ProtectedRetirementEntry:
    """One authority file that must outlive canonical root detachment."""

    leaf: str
    resource: Path
    expected: RetirementIdentity


@dataclass(frozen=True, slots=True)
class RetainedAuthority:
    """One protected authority retained outside an already detached root."""

    resource: Path
    recovery_path: Path
    expected: RetirementIdentity
    observed: RetirementIdentity | None


@dataclass(frozen=True, slots=True)
class ProtectedRootRecovery:
    """Persistent recovery truth for an interrupted protected-root retirement."""

    root: Path
    root_quarantine: Path | None
    root_retired: bool
    authorities: tuple[RetainedAuthority, ...]
    reason: str


class ProtectedRootRetirementError(AtomicRetirementError):
    """Protected-root retirement stopped with explicit authority recovery truth."""

    def __init__(
        self,
        message: str,
        *,
        root_recovery: ProtectedRootRecovery | None = None,
        failures: tuple[BaseException, ...] = (),
        outcome: str | None = None,
        verified: bool | None = None,
    ) -> None:
        """Retain recovery locations and every failure settled across peers."""
        super().__init__(
            message,
            failures=failures,
            outcome=outcome,
            verified=verified,
        )
        self.root_recovery = root_recovery


@dataclass(frozen=True, slots=True)
class AuthorityTransfer:
    """Mapping from one root authority to its private parent backup."""

    entry: ProtectedRetirementEntry
    backup_name: str
    backup_path: Path


__all__ = (
    "AuthorityTransfer",
    "ProtectedRetirementEntry",
    "ProtectedRootRecovery",
    "ProtectedRootRetirementError",
    "RetainedAuthority",
)
