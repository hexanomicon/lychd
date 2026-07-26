"""Directory-specific settlement evidence."""

from __future__ import annotations

from lychd.system.descriptor_settlement import FailureLedger


class DirectoryRollbackError(RuntimeError):
    """Exact directory settlement could not finish without risking foreign state."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...] = (),
        outcome: str | None = None,
    ) -> None:
        """Retain every peer failure and the last verified namespace outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome


def directory_failure_ledger() -> FailureLedger:
    """Return a generic ledger bound to directory-specific evidence."""
    return FailureLedger(
        error_factory=DirectoryRollbackError,
        subject="Directory settlement",
    )


__all__ = (
    "DirectoryRollbackError",
    "directory_failure_ledger",
)
