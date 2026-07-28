"""State and error evidence shared by one file-publication transaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class PublicationRollbackError(RuntimeError):
    """Exact creation rollback could not finish without risking foreign data."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...] = (),
        outcome: str | None = None,
        verified: bool | None = None,
        recovery_paths: tuple[Path, ...] = (),
    ) -> None:
        """Retain peer failures and the last verified publication outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = outcome is not None and outcome != "recovery" if verified is None else verified
        self.recovery_paths = recovery_paths


@dataclass(frozen=True, slots=True)
class FileIdentity:
    """One immutable regular-file identity captured before publication."""

    path: Path
    device: int
    inode: int


@dataclass(slots=True)
class FilePublication:
    """Mutable settlement evidence for one staged file publication."""

    identity: FileIdentity
    parent_fd: int
    staging_name: str
    public_name: str
    published: bool = False
    staging_present: bool = True
    recovery_names: set[str] = field(default_factory=set)
    indeterminate_paths: set[Path] = field(default_factory=set)


__all__ = (
    "FileIdentity",
    "FilePublication",
    "PublicationRollbackError",
)
