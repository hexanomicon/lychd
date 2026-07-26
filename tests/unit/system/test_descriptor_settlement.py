"""Regression tests for neutral descriptor-settlement evidence."""

from __future__ import annotations

import pytest

from lychd.system.descriptor_settlement import FailureLedger


class _SettlementError(RuntimeError):
    """Test evidence retaining the complete failure chain."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
    ) -> None:
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome


def test_ordinary_primary_is_retained_with_cleanup_failures() -> None:
    """Do not erase the operation failure when peer settlement also fails."""
    primary = ValueError("operation failed")
    cleanup = OSError("descriptor close failed")
    ledger = FailureLedger(
        error_factory=_SettlementError,
        subject="Test settlement",
    )
    ledger.record(cleanup)

    with pytest.raises(_SettlementError) as raised:
        ledger.raise_primary_after_verified_settlement(
            primary,
            outcome="rolled_back",
            terminal_note="unused for ordinary failures",
        )

    assert raised.value.failures == (primary, cleanup)
    assert raised.value.outcome == "rolled_back"
    assert raised.value.__cause__ is primary


def test_cleanup_terminal_remains_native_with_complete_evidence() -> None:
    """A peer signal stays native without erasing the ordinary primary."""
    primary = ValueError("operation failed")
    terminal = KeyboardInterrupt()
    ledger = FailureLedger(
        error_factory=_SettlementError,
        subject="Test settlement",
    )
    ledger.record(terminal)

    with pytest.raises(KeyboardInterrupt) as raised:
        ledger.raise_primary_after_verified_settlement(
            primary,
            outcome="rolled_back",
            terminal_note="all peers settled",
        )

    assert raised.value is terminal
    assert isinstance(raised.value.__cause__, _SettlementError)
    assert raised.value.__cause__.failures == (primary, terminal)
    assert raised.value.__cause__.__cause__ is primary
    assert raised.value.__notes__ == ["all peers settled"]
