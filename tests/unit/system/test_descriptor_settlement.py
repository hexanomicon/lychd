"""Regression tests for neutral descriptor-settlement evidence."""

from __future__ import annotations

import pytest

from lychd.system.descriptor_settlement import (
    FailureLedger,
    find_settlement_outcome,
)
from lychd.system.interruptions import iter_exception_graph


class _SettlementError(RuntimeError):
    """Test evidence retaining the complete failure chain."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
    ) -> None:
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = verified


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


def test_repeated_terminal_settlement_preserves_prior_typed_evidence() -> None:
    """Rescoping one terminal cannot sever or cycle its earlier outcome proof."""
    terminal = KeyboardInterrupt()
    inner = FailureLedger(
        error_factory=_SettlementError,
        subject="Inner settlement",
    )
    inner.record(terminal)

    with pytest.raises(KeyboardInterrupt):
        inner.raise_if_any(
            message="inner retirement settled",
            outcome="retired",
            terminal_note="inner settled",
            verified=True,
        )

    inner_evidence = terminal.__cause__
    assert isinstance(inner_evidence, _SettlementError)

    outer = FailureLedger(
        error_factory=_SettlementError,
        subject="Outer settlement",
    )
    outer.record(terminal)
    with pytest.raises(KeyboardInterrupt) as raised:
        outer.raise_if_any(
            message="outer tree partially settled",
            outcome="partial",
            terminal_note="outer settled",
            verified=True,
        )

    assert raised.value is terminal
    outer_evidence = terminal.__cause__
    assert isinstance(outer_evidence, _SettlementError)
    assert outer_evidence is not inner_evidence
    assert outer_evidence.__cause__ is inner_evidence
    assert tuple(iter_exception_graph(terminal)).count(terminal) == 1
    settlement = find_settlement_outcome(terminal)
    assert settlement is not None
    assert settlement.name == "partial"
    assert settlement.verified


def test_explicit_cause_outcome_precedes_stale_exception_context() -> None:
    """Outcome discovery follows Python's explicit causal chain first."""
    explicit = _SettlementError(
        "outer outcome",
        failures=(),
        outcome="partial",
        verified=True,
    )
    contextual = _SettlementError(
        "stale inner outcome",
        failures=(),
        outcome="retired",
        verified=True,
    )
    terminal = KeyboardInterrupt()
    terminal.__cause__ = explicit
    terminal.__context__ = contextual

    settlement = find_settlement_outcome(terminal)

    assert settlement is not None
    assert settlement.name == "partial"
    assert settlement.verified
