"""Failure vocabulary for Scribe binding authority and transactions."""

from enum import StrEnum
from pathlib import Path


class ScribeOwnershipError(RuntimeError):
    """The binding-site ownership record is absent where needed or invalid."""


class ScribeConflictError(RuntimeError):
    """A requested filename is occupied by a unit LychD does not own."""


class ScribeGenerationError(ScribeOwnershipError):
    """The live binding generation no longer matches the approved observation."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...] = (),
        outcome: str = "unchanged",
        verified: bool = True,
    ) -> None:
        """Retain peer attestation failures and verified namespace truth."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = verified


class ScribeTransactionState(StrEnum):
    """What Scribe can prove after a mutation or cleanup interruption."""

    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    INDETERMINATE = "indeterminate"


class ScribeTransactionError(RuntimeError):
    """A failed binding transaction with an explicit post-failure state."""

    def __init__(
        self,
        message: str,
        *,
        state: ScribeTransactionState,
        forward_error: BaseException | None = None,
        rollback_error: BaseException | None = None,
        generation: str | None = None,
        cleanup_errors: tuple[BaseException, ...] = (),
        recovery_paths: tuple[Path, ...] = (),
    ) -> None:
        """Retain public state and every settled transaction-side failure."""
        super().__init__(message)
        self.state = state
        self.forward_error = forward_error
        self.rollback_error = rollback_error
        self.generation = generation
        self.cleanup_errors = cleanup_errors
        self.recovery_paths = recovery_paths
